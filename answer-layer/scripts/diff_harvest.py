#!/usr/bin/env python3
"""
diff_harvest.py — what changed between two probes.

Backs `/answer watch`. A harvest on its own is a snapshot; the diff is the only real
feedback loop this discipline has. It is the artifact that tells you whether the thing
you shipped last month actually did anything -- which is why probe.py stores answers
verbatim instead of storing a score. You cannot diff a score.

    python diff_harvest.py old-harvest.json new-harvest.json

Refuses to diff across different prompt sets. Share of answer is share OF THE PROMPT SET;
comparing two different sets produces a trend line that measures nothing but the edit.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

FRAMING_RANK = {"recommended": 4, "neutral": 3, "caveated": 2, "negative": 1, "none": 0}


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def by_prompt(harvest: dict) -> dict[str, dict]:
    """Collapse runs into a per-prompt state. The fraction survives; the boolean doesn't."""
    grouped: dict[str, list[dict]] = {}
    for record in harvest["records"]:
        if "error" not in record:
            grouped.setdefault(record["prompt_id"], []).append(record)

    out = {}
    for prompt_id, runs in grouped.items():
        hits = sum(1 for r in runs if r["brand_present"])
        framings = [r["framing"] for r in runs if r["brand_present"]]
        best = max(framings, key=lambda f: FRAMING_RANK.get(f, 0)) if framings else "none"
        out[prompt_id] = {
            "prompt": runs[0].get("prompt", ""),
            "hits": hits,
            "runs": len(runs),
            "share": hits / len(runs),
            "framing": best,
            "first": any(r["position"] == "first" for r in runs),
            "self_cited": any(r["own_domain_cited"] for r in runs),
            "hosts": {h for r in runs for h in r["cited_hosts"]},
            "competitors": {c for r in runs for c in r["competitors_present"]},
        }
    return out


def diff(old: dict, new: dict) -> dict:
    if old.get("prompt_set") != new.get("prompt_set"):
        print(f"  note: prompt set changed\n    old: {old.get('prompt_set')}\n"
              f"    new: {new.get('prompt_set')}", file=sys.stderr)
    if old.get("engine") != new.get("engine"):
        sys.exit(f"refusing to diff across engines: {old.get('engine')} vs {new.get('engine')}")

    a, b = by_prompt(old), by_prompt(new)
    shared = set(a) & set(b)
    if not shared:
        sys.exit("no prompts in common — these are different sets, the diff would be fiction")

    result: dict = {"from": old.get("harvested"), "to": new.get("harvested"),
                    "prompts_compared": len(shared),
                    "lost": [], "gained": [], "framing_worse": [], "framing_better": [],
                    "now_first": [], "lost_first": [], "self_citation_gained": [],
                    "cartel_entered": [], "cartel_left": [], "new_competitors": []}

    for prompt_id in sorted(shared):
        before, after = a[prompt_id], b[prompt_id]
        row = {"id": prompt_id, "prompt": after["prompt"],
               "was": f"{before['hits']}/{before['runs']}",
               "now": f"{after['hits']}/{after['runs']}"}

        # 2/3 is the reliability line. Crossing it in either direction is the event;
        # 3/3 -> 2/3 is noise and reporting it as a loss trains clients to ignore you.
        if before["share"] >= 2 / 3 > after["share"]:
            result["lost"].append(row)
        elif after["share"] >= 2 / 3 > before["share"]:
            result["gained"].append(row)

        rank_before = FRAMING_RANK.get(before["framing"], 0)
        rank_after = FRAMING_RANK.get(after["framing"], 0)
        if rank_after < rank_before and after["hits"]:
            result["framing_worse"].append({**row, "was_framing": before["framing"],
                                            "now_framing": after["framing"]})
        elif rank_after > rank_before and before["hits"]:
            result["framing_better"].append({**row, "was_framing": before["framing"],
                                             "now_framing": after["framing"]})

        if after["first"] and not before["first"]:
            result["now_first"].append(row)
        if before["first"] and not after["first"]:
            result["lost_first"].append(row)
        if after["self_cited"] and not before["self_cited"]:
            result["self_citation_gained"].append(row)

    # A new domain entering the cited sources is the leading indicator for everything
    # else -- it moves before presence does.
    hosts_before = Counter(h for v in a.values() for h in v["hosts"])
    hosts_after = Counter(h for v in b.values() for h in v["hosts"])
    result["cartel_entered"] = sorted(
        [(h, c) for h, c in hosts_after.items() if h not in hosts_before and c >= 2],
        key=lambda kv: -kv[1])[:10]
    result["cartel_left"] = sorted(
        [(h, c) for h, c in hosts_before.items() if h not in hosts_after and c >= 2],
        key=lambda kv: -kv[1])[:10]

    comp_before = {c for v in a.values() for c in v["competitors"]}
    comp_after = {c for v in b.values() for c in v["competitors"]}
    result["new_competitors"] = sorted(comp_after - comp_before)

    reliable_before = sum(1 for v in a.values() if v["share"] >= 2 / 3)
    reliable_after = sum(1 for v in b.values() if v["share"] >= 2 / 3)
    result["presence_rate"] = {
        "was": round(reliable_before / len(a), 3),
        "now": round(reliable_after / len(b), 3),
        "delta": round(reliable_after / len(b) - reliable_before / len(a), 3),
    }
    return result


def report(d: dict) -> None:
    rate = d["presence_rate"]
    arrow = "+" if rate["delta"] > 0 else ""
    print(f"\n  {d['from']} -> {d['to']}   {d['prompts_compared']} prompts")
    print(f"  presence {rate['was']:.0%} -> {rate['now']:.0%}  ({arrow}{rate['delta']:.0%})\n")

    def section(title: str, key: str, extra: str = "") -> None:
        rows = d[key]
        if not rows:
            return
        print(f"  {title} ({len(rows)})")
        for row in rows[:8]:
            tail = f"  [{row.get('was_framing')} -> {row.get('now_framing')}]" if extra else ""
            print(f"    {row['id']}  {row['was']} -> {row['now']}  {row['prompt'][:52]}{tail}")
        print()

    section("LOST — was reliable, now isn't. investigate today", "lost")
    section("GAINED — trace this to the change that caused it", "gained")
    section("framing got worse", "framing_worse", extra="framing")
    section("now the recommendation", "now_first")
    section("lost the recommendation", "lost_first")
    section("own domain now cited", "self_citation_gained")

    if d["cartel_entered"]:
        print("  new sources the engines are reaching for:")
        for host, count in d["cartel_entered"]:
            print(f"    {count:>3}  {host}")
        print()
    if d["new_competitors"]:
        print(f"  competitors appearing for the first time: {', '.join(d['new_competitors'])}\n")
    if not any(d[k] for k in ("lost", "gained", "framing_worse", "now_first", "lost_first")):
        print("  no movement past the reliability line. normal for a 30-day window —\n"
              "  off-site work takes 3-6 months to show up in answers.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old")
    parser.add_argument("new")
    parser.add_argument("--json", help="write the diff here")
    args = parser.parse_args()

    result = diff(load(args.old), load(args.new))
    report(result)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
