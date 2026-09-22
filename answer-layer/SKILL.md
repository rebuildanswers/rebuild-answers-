---
name: answer
description: >
  Answer Layer — measures and improves whether a brand actually appears in AI
  answers, rather than inferring it from page structure. Runs live prompt probes
  against answer engines, computes share of answer against competitors, detects
  what models say wrong about the brand, writes the replacement copy, plans earned
  off-site presence, and audits whether AI agents can transact with the site. Use
  when the user says "answer layer", "share of answer", "AI visibility",
  "are we in ChatGPT", "what does AI say about us", "AI citations", "agent
  readiness", "GEO", or gives a domain and asks how it shows up in AI search.
allowed-tools: Read, Write, Bash, WebFetch, WebSearch, Grep, Glob
---

# Answer Layer

Measure first. Everything else is an opinion until you've asked the engine and written down
what it said.

## Commands

| Command | What happens |
|---|---|
| `/answer universe <domain>` | Build the buyer-prompt set. **Run this first.** |
| `/answer probe <domain>` | Fire the prompts at live engines, record verbatim answers + sources |
| `/answer share <domain>` | Share of answer vs competitors, citation cartel, takeable prompts |
| `/answer truth <domain>` | What models say that's wrong, traced to its source, with fixes |
| `/answer forge <domain>` | Write the replacement copy for the lost prompts |
| `/answer earn <domain>` | 90-day earned-presence plan against the cartel |
| `/answer surface <domain>` | Can an agent use this site — scored |
| `/answer watch <domain>` | Re-probe against a frozen set, diff, alert on losses |
| `/answer full <domain>` | The whole sequence, in order |

## Order matters

```
universe ──> probe ──┬──> share ────> forge
                     ├──> truth ────> forge
                     └──> earn
                          surface  (independent, run anytime)
                          watch    (repeats probe on a frozen set)
```

`universe` before `probe`, always. A probe on prompts you invented in the moment produces a
percentage that looks like data and isn't one.

`share` and `truth` both feed `forge`. Run them before you write anything.

`surface` is independent — no prompt set required. It's the cheapest first deliverable and
often the one that opens the conversation, because it surfaces a decision the client didn't
know they'd made.

## Directory

Everything lands under `answer-layer/out/<domain>/`:

```
identity.json           brand names, domains, competitors — write this by hand, first
truth.json              the facts, with public source URLs — by hand, with the client
prompt-universe.json    the frozen prompt set
harvest.json            every answer, verbatim, every run
share-of-answer.json
hallucination-watch.json
agent-surface.json
forge/                  paste-ready copy, one file per fix
```

`identity.json` and `truth.json` are human inputs. Don't generate them and don't skip them —
they're the difference between a measurement and a vibe.

## Freeze the prompt set

Once `prompt-universe.json` exists for a client, it is frozen for the engagement. Version it
(`prompt-universe.v2.json`) if it genuinely has to change, keep both, and report both numbers
in the transition month.

Share of answer is share *of the prompt set*. Whoever picks the set picks the number. An
agency that quietly reshuffles the set to make the line go up is running a scam with extra
steps, and the client will eventually work it out.

## Non-determinism is a feature

Never run once. Three runs minimum, report the fraction. `2/3` is a real, useful, honest
finding: you're in the answer, but not reliably, and small changes will move you. A boolean
throws that away.

## `/answer watch`

Re-run `probe` on the frozen set, diff against the last harvest, and report only what changed:

- **Lost** — was ≥2/3, now ≤1/3. Investigate immediately; something got reindexed or a
  competitor shipped.
- **Gained** — trace it to the change that caused it, if you can. This is how you learn what
  actually works, and it's the only real feedback loop in this discipline.
- **Framing shift** — same presence, worse framing. Early warning.
- **Cartel movement** — a new domain entering the top cited sources is the leading indicator
  for everything else.

Weekly is plenty. Monthly is fine for most clients. Don't schedule it hourly — it costs money
and tells you nothing at that resolution.

## What to say to clients

Say what the denominator is. Say which engine you queried. Say that off-site work takes three
to six months to show up in answers. Say when the honest answer is "a competitor genuinely
serves this buyer better, we should target a different question."

The category is full of dashboards with confident numbers behind them. Being the one that
shows its working is a durable position.

## Agents

`agents/` — drop into `~/.claude/agents/`:

`prompt-universe` · `answer-harvest` · `share-of-answer` · `hallucination-watch` ·
`rewrite-forge` · `mention-engine` · `agent-surface`

## Scripts

`scripts/probe.py` — live probe runner. Needs `ANTHROPIC_API_KEY` or an `ant auth login`
profile. Read it before you trust its output.
