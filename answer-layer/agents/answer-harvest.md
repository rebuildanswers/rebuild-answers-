---
name: answer-harvest
description: >
  Runs a prompt set against live AI answer engines and records what actually came
  back — the verbatim answer, whether the brand appeared, in what position, framed
  how, and which sources the engine cited. This is the ground-truth measurement the
  rest of the Answer Layer is built on. Consumes prompt-universe.json, produces
  harvest.json. Requires ANTHROPIC_API_KEY.
allowed-tools: Read, Write, Bash, WebFetch, WebSearch, Grep, Glob
---

# answer-harvest

This is the blood test.

Every other GEO tool on the market — including the good open-source one this layer sits next
to — infers AI visibility from the shape of your HTML. This agent asks the engine and writes
down the answer.

The difference matters more than it sounds. A brand can be structurally perfect and invisible.
A brand can have terrible schema and own the answer because one well-liked Reddit comment from
2024 keeps getting retrieved. You will not predict either from a page audit. You have to look.

## Before you run

You need `prompt-universe.json`. If it isn't there, stop and run `prompt-universe` first.
Harvesting a prompt set you invented on the spot produces a number that feels like data and
isn't one.

You also need to know what "the brand appeared" means for this client. Get it in writing:
- brand name and every spelling people use for it
- the domain, plus any docs/blog subdomains
- product names that are distinct from the brand name
- names of the 3-6 competitors that matter

Put that in `answer-layer/out/<domain>/identity.json` before the first run. Half of all bad
harvests are a matching problem, not a visibility problem.

## Running the probe

`scripts/probe.py` does the mechanical part. Read it before you trust it.

```bash
python answer-layer/scripts/probe.py \
  --prompts answer-layer/out/example.com/prompt-universe.json \
  --identity answer-layer/out/example.com/identity.json \
  --out answer-layer/out/example.com/harvest.json \
  --runs 3
```

Three things about how it works that you need to hold in your head:

**`--runs 3` is not optional padding.** These systems are non-deterministic. One run tells
you almost nothing; a brand can appear in run 1 and vanish in run 2 for the same prompt. Three
runs of the same prompt gives you a stability signal, which is more useful than the appearance
itself. A brand that appears 3/3 owns that answer. A brand that appears 1/3 is being pulled in
by luck and will drop out the moment anything shifts. Report the fraction, never a boolean.

**It queries Claude with web search, which is a real answer engine and a proxy for the
others.** Be honest about this in the report. It is not ChatGPT. Retrieval and synthesis
differ. What generalizes across engines is the *source layer* — which domains get pulled in —
because they're all drinking from a similar web. What doesn't generalize is exact phrasing and
ordering. If the client needs per-engine numbers, add the keys for the other providers; the
script is written so a provider is ~30 lines. Don't quietly present one engine as "AI search."

**It stores the full answer text.** Not a score. The text. Six months from now the diff
between two harvests is the most valuable artifact you own, and you cannot diff a score.

## What to extract from each answer

The script's second pass pulls structured findings out of each raw answer. Verify a sample of
them by hand on the first run — model-extracted structure is right most of the time and wrong
in ways that are easy to miss.

For every (prompt × run):

| Field | What you're capturing |
|---|---|
| `brand_present` | Did the brand appear anywhere in the answer |
| `position` | 1 = named first / recommended. 2-N = in the list. `mention_only` = referenced without being an option. `absent` |
| `framing` | `recommended` / `neutral` / `caveated` / `negative`. A caveated mention is not a win |
| `competitors_present` | Every rival named, in order |
| `cited_domains` | Every source the engine actually pulled from |
| `own_domain_cited` | Did the engine cite the client's own site, or talk about them using someone else's page |
| `claims_about_brand` | Every factual assertion made about the brand — this feeds `hallucination-watch` |

That second-to-last row is the one people miss. Being *mentioned* while every citation points
at a competitor's comparison page means the competitor is writing your marketing. It's a
different problem than absence and it has a different fix.

## Reading the result

Compute and report:

- **Presence rate** — prompts where brand appeared ≥2/3 runs, over total prompts. This is
  the headline number. It is a percentage of *your* prompt set, not of "AI search," and it
  moves if you change the prompt set — so freeze the set between runs or the trend is fiction.
- **Stability** — count of 3/3, 2/3, 1/3, 0/3. The 1/3 bucket is your fragile edge and the
  cheapest thing to fix.
- **First-position rate** — of prompts where you appear, how often you're the recommendation.
- **Self-citation rate** — how often your own domain is a source. Low here with high presence
  means you're visible through other people's pages.
- **The zero list** — every prompt where you appeared 0/3. Sorted by priority from the
  universe file. This is the work queue. Hand it to `rewrite-forge`.

## Output

`harvest.json` — full records, every run, verbatim answers preserved.
`harvest.md` — the five numbers above, the zero list, and 3-5 verbatim answer excerpts.

Always quote real answers in the human report. A client who reads the actual sentence an AI
said about their business — especially a wrong one — understands the problem in four seconds.
No chart does that.

## Cost and manners

Each prompt × run is one API call with web search enabled. A 30-prompt set at 3 runs is 90
calls plus 90 cheap extraction calls. That's dollars, not hundreds. Still: don't loop it
hourly. Weekly is plenty, monthly is fine for most clients, and the script rate-limits itself
because hammering anyone's endpoint is how tools get blocked for everybody.

## Do not

- Do not report a single run as a finding.
- Do not present Claude-with-search results as ChatGPT results.
- Do not let the brand match on a substring. "Notion" matches "notional." The identity file
  exists to stop this; use word boundaries and check the misses by hand on run one.
- Do not celebrate a mention that's framed as "some users report issues with X." That's a
  finding for `hallucination-watch`, not a win.
