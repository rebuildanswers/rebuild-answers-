# Scripts

Three. Read them before you trust their output — that's the whole premise of the layer.

| Script | Needs | What it does |
|---|---|---|
| `probe.py` | `anthropic`, `pydantic`, an API key | Asks live engines your prompt set, records verbatim answers + citations |
| `surface_check.py` | stdlib only (`playwright` optional) | Scores whether an agent can use a site, /100 |
| `diff_harvest.py` | stdlib only | Diffs two harvests into lost / gained / framing shifts / cartel movement |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install anthropic pydantic
export ANTHROPIC_API_KEY=...        # or: ant auth login
pip install playwright && playwright install chromium   # optional, real JS diff
```

Only `probe.py` needs any of that. The other two run on a bare Python 3.9+.

## Running

```bash
# 1. ground truth. freeze prompt-universe.json first -- see SKILL.md.
python probe.py \
  --prompts   ../out/example.com/prompt-universe.json \
  --identity  ../out/example.com/identity.json \
  --out       ../out/example.com/harvest.json \
  --runs 3

# 2. agent readiness. no keys, no cost, run it on anything.
python surface_check.py https://example.com --json ../out/example.com/agent-surface.json

# 3. next month, against the SAME frozen set
python diff_harvest.py ../out/example.com/harvest-2026-07.json \
                       ../out/example.com/harvest-2026-08.json
```

## Cost

`probe.py` is the only one that costs money: two API calls per (prompt × run), the first with
web search enabled. A 30-prompt set at 3 runs is 90 + 90 calls. Dollars, not hundreds.

It sleeps 1.5s between calls by default. Don't set `--delay 0`. Weekly is plenty; monthly is
fine for most clients.

## Things that will bite you

**`--runs 1`.** The number it gives you is noise. These systems are non-deterministic and a
brand appears in run 1 and vanishes in run 2 for the same prompt. Three minimum.

**A bad `identity.json`.** Substring matching is why a tool reports a client appearing in 80%
of answers when the brand is "Notion" and the model said "notional". `probe.py` uses word
boundaries and cross-checks the model extraction against the regex — the
`match_disagreements` count in the summary is the number of records to look at by hand on the
first run. Do look at them.

**Changing the prompt set between runs.** `diff_harvest.py` warns; it can't stop you. Share of
answer is share of the set. Freeze it.

**Missing playwright.** `surface_check.py` falls back to a heuristic for the JS check and says
so in the evidence (`"method": "heuristic"`). It's directionally right and it is not a real
diff. Install playwright before you put a JS-dependency finding in front of a CTO.
