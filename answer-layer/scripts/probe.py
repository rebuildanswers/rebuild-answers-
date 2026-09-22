#!/usr/bin/env python3
"""
probe.py — ask real answer engines real buyer questions, write down what came back.

This is the part nobody else does. Every GEO tool on the market infers AI visibility
from the shape of your HTML. This asks the engine.

Two passes per (prompt x run):

  pass 1  the answer      Claude + server-side web search. A real retrieval-and-synthesis
                          answer with real citations. Stored verbatim, never summarized.
  pass 2  the extraction  A separate structured call over pass 1's text. Kept separate on
                          purpose -- structured outputs and citations don't mix, and you
                          want the raw answer preserved regardless of how extraction goes.

Usage:
    python probe.py --prompts prompt-universe.json \
                    --identity identity.json \
                    --out harvest.json \
                    --runs 3

Requires: pip install anthropic
Auth:     ANTHROPIC_API_KEY, or `ant auth login`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

try:
    import anthropic
    from pydantic import BaseModel, Field
except ImportError:
    sys.exit("pip install anthropic pydantic")


ANSWER_MODEL = "claude-opus-5"
EXTRACT_MODEL = "claude-opus-5"

# The probe must behave like someone asking a question, not like a brand checking on itself.
# Any hint of the latter and you're measuring the model's helpfulness, not its retrieval.
ASKER_SYSTEM = (
    "You are answering a question from someone researching a purchase. "
    "Search the web and give the answer you would actually give them: specific, "
    "current, and willing to name products or companies by name when that is what "
    "the question calls for. Do not hedge into a list of generic considerations."
)


class Extraction(BaseModel):
    """What we pull out of one answer. Deliberately small -- every field is a decision."""

    brand_present: bool = Field(description="Is the target brand mentioned anywhere at all")
    position: Literal["first", "listed", "mention_only", "absent"] = Field(
        description=(
            "first = named as the recommendation or first option. "
            "listed = one option among several. "
            "mention_only = referenced but not offered as an option. "
            "absent = not present."
        )
    )
    framing: Literal["recommended", "neutral", "caveated", "negative", "none"] = Field(
        description="How the brand is characterized. 'none' if absent."
    )
    competitors_present: list[str] = Field(
        default_factory=list, description="Competitor names appearing, in order of appearance"
    )
    claims_about_brand: list[str] = Field(
        default_factory=list,
        description=(
            "Every factual assertion made about the target brand, verbatim or near-verbatim. "
            "Prices, dates, features, ownership, status. Empty if the brand is absent. "
            "These feed hallucination detection -- do not paraphrase them into vagueness."
        ),
    )


def load(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def registrable(url: str) -> str:
    """Host of a URL, www stripped. Good enough for tallying; not a PSL implementation."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def brand_regex(identity: dict) -> re.Pattern:
    """
    Word-boundary match over every known name for the brand.

    Substring matching is how you end up reporting that a client appears in 80% of
    answers because their name is 'Notion' and the model said 'notional'. Half of all
    bad harvests are a matching problem, not a visibility problem.
    """
    names = [identity["brand"], *identity.get("aliases", [])]
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"(?<!\w)(?:{alt})(?!\w)", re.IGNORECASE)


def ask(client: anthropic.Anthropic, prompt: str) -> dict:
    """
    Pass 1. One question, web search on, answer + sources returned.

    pause_turn is handled explicitly: the server-side search tool can hit its iteration
    limit mid-turn and stop. Not an error, and not the end of the answer -- you resend to
    continue. Miss this and you silently record truncated answers as real ones.
    """
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]

    for _ in range(5):  # cap resumes; a turn that won't finish is a finding of its own
        response = client.messages.create(
            model=ANSWER_MODEL,
            max_tokens=8000,
            system=ASKER_SYSTEM,
            tools=tools,
            messages=messages,
        )
        if response.stop_reason != "pause_turn":
            break
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response.content},
        ]
    else:
        raise RuntimeError("turn still paused after 5 resumes")

    text_parts: list[str] = []
    cited: list[str] = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "web_search_tool_result":
            # Server-tool errors come back HTTP 200 with content as a single error
            # object rather than a list. Branch before indexing or this raises on a
            # perfectly ordinary rate-limit.
            content = block.content
            if isinstance(content, list):
                for result in content:
                    url = getattr(result, "url", None)
                    if url:
                        cited.append(url)

    return {
        "text": "\n".join(text_parts).strip(),
        "cited_urls": cited,
        "stop_reason": response.stop_reason,
    }


def extract(client: anthropic.Anthropic, answer_text: str, identity: dict) -> dict:
    """
    Pass 2. Structure the answer. Separate call, no tools, no search.

    Kept apart from pass 1 because output_config and citations are mutually exclusive,
    and because the raw answer is the artifact you actually want to keep. If extraction
    fails you still have the text; the reverse is not true.
    """
    competitors = ", ".join(identity.get("competitors", [])) or "(none listed)"
    instruction = (
        f"Target brand: {identity['brand']}\n"
        f"Also known as: {', '.join(identity.get('aliases', [])) or '(no aliases)'}\n"
        f"Known competitors: {competitors}\n\n"
        "Below is an answer an AI search engine gave to a buyer's question. "
        "Report only what the text actually says. Do not use outside knowledge about "
        "any of these companies, and do not infer a mention that isn't there.\n\n"
        f"---\n{answer_text}\n---"
    )

    response = client.messages.parse(
        model=EXTRACT_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": instruction}],
        output_format=Extraction,
    )
    return response.parsed_output.model_dump()


def run(args: argparse.Namespace) -> None:
    universe = load(args.prompts)
    identity = load(args.identity)
    client = anthropic.Anthropic()
    pattern = brand_regex(identity)
    own_hosts = {registrable(d) for d in identity.get("domains", [])}

    prompts = [p for p in universe["prompts"] if p.get("priority", 0) >= args.min_priority]
    prompts.sort(key=lambda p: p.get("priority", 0), reverse=True)

    records: list[dict] = []
    total = len(prompts) * args.runs
    done = 0

    for prompt in prompts:
        for run_index in range(1, args.runs + 1):
            done += 1
            print(f"[{done}/{total}] {prompt['id']} run {run_index}  {prompt['text'][:58]}",
                  file=sys.stderr)

            try:
                answer = ask(client, prompt["text"])
            except anthropic.APIStatusError as exc:
                print(f"    api error {exc.status_code}: {exc}", file=sys.stderr)
                records.append({"prompt_id": prompt["id"], "run": run_index,
                                "error": f"{exc.status_code}"})
                time.sleep(5)
                continue

            hosts = [registrable(u) for u in answer["cited_urls"]]

            try:
                found = extract(client, answer["text"], identity)
            except anthropic.APIStatusError as exc:
                # Fall back to the regex. Weaker, but the raw answer is preserved either
                # way, so a re-extraction later is always possible.
                print(f"    extraction failed ({exc.status_code}), regex fallback",
                      file=sys.stderr)
                present = bool(pattern.search(answer["text"]))
                found = {"brand_present": present,
                         "position": "listed" if present else "absent",
                         "framing": "none", "competitors_present": [],
                         "claims_about_brand": [], "_fallback": True}

            # Cross-check the model against the regex. When they disagree, keep both and
            # look at it by hand -- the disagreements are where the interesting cases are
            # (nicknames, possessives, the brand named only inside a URL).
            regex_present = bool(pattern.search(answer["text"]))

            records.append({
                "prompt_id": prompt["id"],
                "prompt": prompt["text"],
                "bucket": prompt.get("bucket"),
                "priority": prompt.get("priority"),
                "run": run_index,
                "answer_text": answer["text"],          # verbatim. always. you diff this later.
                "cited_urls": answer["cited_urls"],
                "cited_hosts": sorted(set(h for h in hosts if h)),
                "own_domain_cited": any(h in own_hosts for h in hosts),
                "regex_brand_present": regex_present,
                "match_disagreement": regex_present != found["brand_present"],
                **found,
            })

            time.sleep(args.delay)

    out = {
        "domain": universe.get("domain"),
        "brand": identity["brand"],
        "harvested": date.today().isoformat(),
        "engine": f"anthropic:{ANSWER_MODEL}+web_search",
        "runs_per_prompt": args.runs,
        "prompt_set": args.prompts,
        "records": records,
        "baseline_mode": args.baseline,
        "summary": summarize(records, args.runs),
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    report(out, baseline=args.baseline)


def summarize(records: list[dict], runs: int) -> dict:
    """
    Presence is a fraction, never a boolean.

    A brand at 1/3 is being pulled in by luck and will drop out the moment anything
    shifts. A brand at 3/3 owns that answer. Collapsing both to "present" throws away
    the most actionable thing in the dataset.
    """
    by_prompt: dict[str, list[dict]] = {}
    for record in records:
        if "error" not in record:
            by_prompt.setdefault(record["prompt_id"], []).append(record)

    stability: dict[str, list[str]] = {f"{i}of{runs}": [] for i in range(runs, -1, -1)}
    first_position = 0
    self_cited = 0
    host_tally: dict[str, int] = {}
    competitor_tally: dict[str, int] = {}

    for prompt_id, runs_for_prompt in by_prompt.items():
        hits = sum(1 for r in runs_for_prompt if r["brand_present"])
        n = len(runs_for_prompt)
        bucket = f"{round(hits / n * runs)}of{runs}" if n else f"0of{runs}"
        stability.setdefault(bucket, []).append(prompt_id)

        if any(r["position"] == "first" for r in runs_for_prompt):
            first_position += 1
        if any(r["own_domain_cited"] for r in runs_for_prompt):
            self_cited += 1

        for r in runs_for_prompt:
            for host in r["cited_hosts"]:
                host_tally[host] = host_tally.get(host, 0) + 1
            for competitor in r["competitors_present"]:
                key = competitor.strip()
                competitor_tally[key] = competitor_tally.get(key, 0) + 1

    prompt_count = len(by_prompt) or 1
    reliable = len(stability.get(f"{runs}of{runs}", [])) + len(stability.get(f"{runs - 1}of{runs}", []))

    return {
        "prompts": len(by_prompt),
        "presence_rate": round(reliable / prompt_count, 3),
        "first_position_rate": round(first_position / prompt_count, 3),
        "self_citation_rate": round(self_cited / prompt_count, 3),
        "stability": {k: len(v) for k, v in stability.items()},
        "zero_list": sorted(stability.get(f"0of{runs}", [])),
        "fragile_list": sorted(stability.get(f"1of{runs}", [])),
        "citation_cartel": sorted(host_tally.items(), key=lambda kv: -kv[1])[:25],
        "competitors_seen": sorted(competitor_tally.items(), key=lambda kv: -kv[1])[:15],
        "match_disagreements": sum(1 for r in records if r.get("match_disagreement")),
    }


def report(out: dict, baseline: bool = False) -> None:
    """
    In baseline mode the presence number is 0 by construction -- the brand isn't indexed.
    Printing it as a headline trains people to read a structural fact as a failure. What
    matters before launch is who owns the answers and which sources the engines reach for,
    because that list IS the launch plan.
    """
    s = out["summary"]
    print(f"\n  {out['brand']} — {s['prompts']} prompts × {out['runs_per_prompt']} runs")
    print(f"  engine: {out['engine']}")

    if baseline:
        print("\n  baseline run — brand is pre-launch. presence is 0 by construction,")
        print("  not a finding. the two tables below are the deliverable.")
        if s["presence_rate"]:
            print(f"\n  !! unexpected: presence {s['presence_rate']:.0%} on a pre-launch brand.")
            print("     almost certainly a name-collision false positive. check the identity file.")
    else:
        print(f"\n  presence (>={out['runs_per_prompt'] - 1}/{out['runs_per_prompt']}) "
              f"{s['presence_rate']:.0%}")
        print(f"  first position            {s['first_position_rate']:.0%}")
        print(f"  own domain cited          {s['self_citation_rate']:.0%}")
        print(f"  stability                 {s['stability']}")

    if s["citation_cartel"]:
        print("\n  citation cartel:")
        for host, count in s["citation_cartel"][:10]:
            print(f"    {count:>4}  {host}")

    if s["competitors_seen"]:
        print("\n  who shows up instead:")
        for name, count in s["competitors_seen"][:8]:
            print(f"    {count:>4}  {name}")

    if s["zero_list"] and not baseline:
        print(f"\n  invisible on {len(s['zero_list'])} prompts -> forge queue:")
        print(f"    {', '.join(s['zero_list'][:12])}")

    if s["match_disagreements"]:
        print(f"\n  {s['match_disagreements']} regex/model disagreements — review by hand")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", required=True, help="prompt-universe.json")
    parser.add_argument("--identity", required=True, help="identity.json")
    parser.add_argument("--out", required=True, help="harvest.json to write")
    parser.add_argument("--runs", type=int, default=3,
                        help="runs per prompt. below 3 the number is noise (default: 3)")
    parser.add_argument("--min-priority", type=int, default=0,
                        help="skip prompts below this priority")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="seconds between calls. don't set this to 0 (default: 1.5)")
    parser.add_argument("--baseline", action="store_true",
                        help=("brand is pre-launch or unindexed. Suppresses the presence headline "
                              "(0%% by construction, not a finding) and leads with the cartel and "
                              "who currently owns the answers."))
    run(parser.parse_args())


if __name__ == "__main__":
    main()
