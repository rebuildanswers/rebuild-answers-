#!/usr/bin/env python3
"""
surface_check.py — can an AI agent actually USE this site, or only read about it?

Backs the `agent-surface` agent. Everything else in GEO optimizes for an AI that reads
about you and tells a human. This checks whether the next thing -- an agent that fetches,
compares, and transacts on its own -- can get anything done here.

Stdlib only. Playwright is used if installed, and skipped honestly if not.

    python surface_check.py https://example.com
    python surface_check.py https://example.com --json out/example.com/agent-surface.json

Scored /100. Components that don't apply to the site type are dropped and the remainder
rescaled -- a plumber with no API should not be marked down for lacking an MCP card.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 (compatible; AnswerLayer-surface-check/1.0; +agent-readiness audit)"
TIMEOUT = 20

# The AI crawlers worth reporting on. Split by what they're FOR, because the two
# columns are different business decisions and clients conflate them constantly.
CRAWLERS = {
    "retrieval": ["OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Perplexity-User",
                  "Claude-User", "Claude-SearchBot", "Google-Extended", "Applebot-Extended"],
    "training": ["GPTBot", "ClaudeBot", "anthropic-ai", "cohere-ai", "Meta-ExternalAgent",
                 "Bytespider", "CCBot"],
}

CONTENT_SIGNAL_KEYS = {"ai-train", "search", "ai-personalization", "ai-retrieval"}


@dataclass
class Check:
    name: str
    applicable: bool = True
    points: float = 0.0
    max_points: float = 0.0
    verdict: str = ""
    evidence: dict = field(default_factory=dict)


def fetch(url: str, headers: dict | None = None, method: str = "GET") -> tuple[int, dict, str]:
    """Plain HTTP. No JS, no cookies, no retries -- deliberately, that's the point."""
    request = Request(url, method=method, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            charset = response.headers.get_content_charset() or "utf-8"
            return response.status, dict(response.headers), raw.decode(charset, "replace")
    except HTTPError as exc:
        return exc.code, dict(exc.headers or {}), ""
    except (URLError, TimeoutError, OSError) as exc:
        return 0, {"_error": str(exc)}, ""


TAG_STRIP = re.compile(
    r"<(script|style|noscript|template|svg)\b[^>]*>.*?</\1>|<[^>]+>", re.S | re.I
)


def visible_words(html: str) -> list[str]:
    text = TAG_STRIP.sub(" ", html)
    text = re.sub(r"&[a-z#0-9]+;", " ", text)
    return re.findall(r"[A-Za-z][A-Za-z'-]+", text)


# ── 1. Content without JS ────────────────────────────────────────────────────

def check_no_js(url: str) -> Check:
    """
    The highest-impact finding in the whole audit, and the most boring.

    A crawler that gets a shell gives you a second chance later. An agent on a task
    budget does not. Real diff needs a browser; without one we infer from the shape
    of the document and SAY that we inferred it.
    """
    check = Check("content_without_js", max_points=30)
    status, headers, html = fetch(url)
    if status != 200 or not html:
        check.verdict = f"could not fetch ({status or headers.get('_error', 'error')})"
        check.evidence = {"status": status}
        return check

    raw_words = visible_words(html)
    raw_count = len(raw_words)
    mount = bool(re.search(r'<(?:div|main)[^>]+id=["\'](?:root|app|__next|__nuxt)["\']', html, re.I))
    scripts = len(re.findall(r"<script\b", html, re.I))

    rendered_count = None
    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=UA)
            page.goto(url, timeout=TIMEOUT * 1000, wait_until="networkidle")
            rendered_count = len(re.findall(r"[A-Za-z][A-Za-z'-]+", page.inner_text("body")))
            browser.close()
    except Exception:
        rendered_count = None  # not installed, or the launch failed. Not an error here.

    if rendered_count:
        ratio = raw_count / rendered_count if rendered_count else 0
        check.evidence = {"raw_words": raw_count, "rendered_words": rendered_count,
                          "raw_share": round(ratio, 3), "method": "playwright"}
        if ratio >= 0.8:
            check.points, check.verdict = 30, "server-rendered; an agent sees the real page"
        elif ratio >= 0.5:
            check.points, check.verdict = 18, f"{1 - ratio:.0%} of content is JS-only"
        else:
            check.points, check.verdict = 4, f"JS-dependent — raw fetch gets {ratio:.0%} of the text"
    else:
        check.evidence = {"raw_words": raw_count, "mount_div": mount, "script_tags": scripts,
                          "method": "heuristic (playwright unavailable — install it for a real diff)"}
        if raw_count > 400:
            check.points, check.verdict = 27, f"{raw_count} words in the raw HTML; looks server-rendered"
        elif raw_count > 150:
            check.points, check.verdict = 16, f"only {raw_count} words in raw HTML — partial hydration likely"
        else:
            check.points, check.verdict = 3, (
                f"{raw_count} words in raw HTML"
                + (" with a client-side mount point — an agent sees an empty shell" if mount else "")
            )
    return check


# ── 2. Machine-readable facts ────────────────────────────────────────────────

def check_machine_facts(url: str) -> Check:
    """
    Can an agent learn the price without OCR'ing a hero image.

    Looks for a JSON-LD offer with an actual number, or a fetchable structured
    endpoint. Marketing HTML doesn't count -- an agent can't act on a <h2>.
    """
    check = Check("machine_readable_facts", max_points=20)
    _, _, html = fetch(url)
    found: list[str] = []

    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I
    )
    priced = False
    for block in blocks:
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        blob = json.dumps(data)
        if re.search(r'"price"\s*:\s*"?\d', blob):
            priced = True
            found.append("JSON-LD with a numeric price")
        for kind in ("Product", "Offer", "LocalBusiness", "SoftwareApplication", "Service"):
            if f'"{kind}"' in blob:
                found.append(f"JSON-LD {kind}")

    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    for path in ("/openapi.json", "/pricing.json", "/.well-known/ai-plugin.json", "/feed.json"):
        status, headers, _ = fetch(urljoin(base, path), method="HEAD")
        if status == 200 and "json" in headers.get("Content-Type", "").lower():
            found.append(f"structured endpoint {path}")

    check.evidence = {"found": sorted(set(found))}
    if priced and len(set(found)) > 1:
        check.points, check.verdict = 20, "price and entity facts are machine-readable"
    elif found:
        check.points, check.verdict = 11, "some structured data, but no retrievable price"
    else:
        check.points, check.verdict = 0, (
            "no machine-readable facts — an agent cannot quote a price, and neither can a model"
        )
    return check


# ── 3. llms.txt quality ──────────────────────────────────────────────────────

def check_llmstxt(url: str) -> Check:
    """
    Presence is table stakes and mostly performative. Grade the content.
    A sitemap with worse formatting scores near zero here, on purpose.
    """
    check = Check("llmstxt_quality", max_points=15)
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    status, _, body = fetch(urljoin(base, "/llms.txt"))

    if status != 200 or not body.strip():
        check.verdict = "no llms.txt"
        check.evidence = {"status": status}
        return check

    links = re.findall(r"\]\((https?://[^)]+)\)", body)
    prose = [ln for ln in body.splitlines() if ln.strip() and not ln.strip().startswith(("#", "-", "*"))]
    words = len(body.split())
    machine_links = [l for l in links if re.search(r"\.(json|ya?ml|xml|csv)$|openapi|/api/", l, re.I)]
    negative = bool(re.search(r"\b(is not|isn't|not a|does not|rather than)\b", body, re.I))

    points = 4  # it exists
    notes = ["present"]
    if 10 <= len(links) <= 60:
        points += 4; notes.append(f"curated ({len(links)} links)")
    elif len(links) > 60:
        notes.append(f"{len(links)} links — a dump, not a curation")
    if prose and words > 60:
        points += 3; notes.append("has orienting prose")
    else:
        notes.append("link list with no explanation of what the company is")
    if negative:
        points += 2; notes.append("states what it is NOT — cheapest anti-conflation move there is")
    if machine_links:
        points += 2; notes.append(f"links {len(machine_links)} machine-readable resources")

    _, _, full = fetch(urljoin(base, "/llms-full.txt"))
    check.evidence = {"links": len(links), "words": words,
                      "machine_readable_links": machine_links[:5],
                      "llms_full_txt": bool(full.strip()), "notes": notes}
    check.points = min(points, 15)
    check.verdict = "; ".join(notes)
    return check


# ── 4. Service discovery ─────────────────────────────────────────────────────

def check_discovery(url: str, api_first: bool | None) -> Check:
    """
    RFC 8288 Link headers and well-known paths. Conditional on purpose --
    for a plumber's site this is padding, and padding is how reports lose trust.
    """
    check = Check("service_discovery", max_points=10)
    _, headers, html = fetch(url)
    link_header = headers.get("Link", "")
    rels = re.findall(r'rel="?([a-zA-Z0-9_.:-]+)"?', link_header)

    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    well_known = []
    for path in ("/.well-known/mcp.json", "/.well-known/ai-plugin.json", "/.well-known/openapi.json"):
        status, _, _ = fetch(urljoin(base, path), method="HEAD")
        if status == 200:
            well_known.append(path)

    if api_first is None:
        api_first = bool(
            re.search(r"\b(API|SDK|developers?|documentation|endpoint)\b", html[:60000], re.I)
        )

    check.evidence = {"link_rels": rels, "well_known": well_known, "api_first_guess": api_first}

    if not api_first:
        check.applicable = False
        check.verdict = "not an API-first site — omitted and remaining components rescaled"
        return check
    if well_known or rels:
        check.points = 10 if well_known else 6
        check.verdict = f"discoverable: {well_known or rels}"
    else:
        check.verdict = "API-first site with no machine-readable front door (no Link rels, no well-known)"
    return check


# ── 5. Crawler + Content Signals policy ──────────────────────────────────────

def check_policy(url: str) -> Check:
    """
    The finding here is rarely 'you blocked the wrong bot'. It's that nobody decided --
    the policy came from a WAF default. Report the state, then ask if that was the intent.
    """
    check = Check("policy_coherence", max_points=10)
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    status, _, robots = fetch(urljoin(base, "/robots.txt"))
    if status != 200:
        check.verdict = "no robots.txt — everything is allowed by default, probably not deliberately"
        check.points = 3
        return check

    blocked: dict[str, list[str]] = {"retrieval": [], "training": []}
    for purpose, agents in CRAWLERS.items():
        for agent in agents:
            block = re.search(
                rf"^user-agent:\s*{re.escape(agent)}\s*$(.*?)(?=^user-agent:|\Z)",
                robots, re.I | re.M | re.S,
            )
            if block and re.search(r"^disallow:\s*/\s*$", block.group(1), re.I | re.M):
                blocked[purpose].append(agent)

    signals: dict[str, str] = {}
    unknown: list[str] = []
    for line in re.findall(r"^content-signal:\s*(.+)$", robots, re.I | re.M):
        for pair in line.split(","):
            if "=" in pair:
                key, value = (part.strip().lower() for part in pair.split("=", 1))
                signals[key] = value
                if key not in CONTENT_SIGNAL_KEYS:
                    unknown.append(key)

    check.evidence = {"blocked": blocked, "content_signal": signals,
                      "unknown_signal_keys": unknown}  # notes, never errors — draft still moving

    points = 5
    verdict = []
    if blocked["retrieval"]:
        verdict.append(
            f"BLOCKING retrieval bots ({', '.join(blocked['retrieval'])}) — "
            "these are the ones that put you in answers"
        )
        points = 1
    else:
        verdict.append("retrieval bots allowed")
    if blocked["training"]:
        verdict.append(f"training bots blocked ({len(blocked['training'])}) — a legitimate, separate choice")
    if signals:
        points += 5
        verdict.append(f"Content-Signal declared: {signals}")
    else:
        verdict.append("no Content-Signal directive — preference is undeclared")

    check.points = min(points, 10)
    check.verdict = "; ".join(verdict)
    return check


# ── 6. Bonus: markdown negotiation ───────────────────────────────────────────

def check_markdown(url: str) -> Check:
    check = Check("markdown_negotiation", max_points=0)  # bonus only; absence never penalised
    status, headers, _ = fetch(url, headers={"Accept": "text/markdown"}, method="HEAD")
    content_type = headers.get("Content-Type", "")
    if status == 200 and "text/markdown" in content_type.lower():
        check.points, check.verdict = 5, "serves text/markdown to agents that ask — leading edge"
    else:
        check.verdict = f"standard HTML ({content_type.split(';')[0] or 'no content-type'})"
    check.evidence = {"content_type": content_type}
    return check


def run(url: str, api_first: bool | None) -> dict:
    checks = [
        check_no_js(url),
        check_machine_facts(url),
        check_llmstxt(url),
        check_discovery(url, api_first),
        check_policy(url),
    ]
    bonus = check_markdown(url)

    scored = [c for c in checks if c.applicable]
    earned = sum(c.points for c in scored)
    possible = sum(c.max_points for c in scored)
    dropped = [c.name for c in checks if not c.applicable]

    # Rescale honestly, and say so in the output rather than burying it.
    score = round(earned / possible * 100) if possible else 0
    score = min(score + int(bonus.points), 100)

    return {
        "url": url,
        "checked": date.today().isoformat(),
        "score": score,
        "scale_note": (
            f"scored out of {int(possible)} applicable points, rescaled to 100"
            + (f"; dropped as not applicable: {', '.join(dropped)}" if dropped else "")
            + (f"; +{int(bonus.points)} bonus" if bonus.points else "")
        ),
        "checks": [asdict(c) for c in checks] + [asdict(bonus)],
    }


def report(result: dict) -> None:
    print(f"\n  {result['url']}")
    print(f"  agent surface  {result['score']}/100")
    print(f"  {result['scale_note']}\n")
    for check in result["checks"]:
        if not check["applicable"]:
            mark, points = "  --", "n/a"
        else:
            mark = "  ok" if check["points"] >= check["max_points"] * 0.7 else "  !!"
            points = f"{check['points']:g}/{check['max_points']:g}"
        print(f"{mark}  {check['name']:<26} {points:>7}  {check['verdict']}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--json", help="write full results here")
    parser.add_argument("--api-first", dest="api_first", action="store_true", default=None,
                        help="force service-discovery to count (default: inferred)")
    parser.add_argument("--not-api-first", dest="api_first", action="store_false",
                        help="force service-discovery to be dropped and the rest rescaled")
    args = parser.parse_args()

    result = run(args.url, args.api_first)
    report(result)
    if args.json:
        from pathlib import Path
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2)
        print(f"  -> {args.json}\n")


if __name__ == "__main__":
    main()
