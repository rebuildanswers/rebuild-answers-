# Answer Layer

A second layer for AI search work, built on top of what `geo-seo-claude` already does well —
and pointed straight at the thing it doesn't do at all.

## The gap

`geo-seo-claude` is 15 skills, 5 agents, ~8,500 lines. It is genuinely good. It fetches your
page, counts your pronouns, checks whether GPTBot is allowed in `robots.txt`, scores your
passages 0-100 on a five-dimension citability rubric, and hands the client a PDF with a gauge
on the cover.

Every one of those numbers is a **proxy**.

Not once, anywhere in that codebase, does anything ask ChatGPT a question and check whether
the client showed up in the answer.

That's the whole gap. The tool infers visibility from page structure the way you'd infer
someone's health from their gym membership. Useful. Not the same as a blood test.

Read `scripts/citability_scorer.py` in that repo and you'll see it plainly — regex for
`"X is a..."`, a bonus if the passage lands between 134 and 167 words, a penalty for pronoun
density. It's a decent model of what an LLM finds quotable. It is not evidence that an LLM
quoted you.

## What this layer does instead

Ground truth first, then everything hangs off it.

You define the questions your buyers actually type. You fire them at live answer engines.
You record what came back — verbatim, with sources. Then you know:

- whether you appear at all
- who appears instead
- which domains the engines keep reaching for
- what the models believe about you that is **wrong**
- and which specific paragraph, on which specific page, has to change to fix it

Scoring pages is the last step, not the first. You cannot optimize for citation until you
know which citations you're losing.

## The seven agents

| Agent | The question it answers |
|---|---|
| `prompt-universe` | Which questions are actually worth winning? |
| `answer-harvest` | When we ask them for real, what comes back? |
| `share-of-answer` | Who owns these answers today, and can we take any? |
| `hallucination-watch` | What do the models get *wrong* about us? |
| `rewrite-forge` | Here is the replacement copy. Ship it. |
| `mention-engine` | How do we earn the off-site presence the models weight 3x? |
| `agent-surface` | Can an AI agent *use* this site, not just read it? |

Two of these — `hallucination-watch` and `agent-surface` — have no counterpart anywhere in
`geo-seo-claude`. One of them, `rewrite-forge`, exists because fifteen skills that all end
in "you should consider" is fourteen too many.

## Relationship to geo-seo-claude

Complementary, not a fork. Nothing here is copied from it. If you have both installed:

- run `/geo audit` for the page-level diagnostic
- run `/answer probe` for what's actually happening in the engines
- `rewrite-forge` will happily consume a `GEO-AUDIT-REPORT.md` as input

`agents/` files follow the same Claude Code subagent format, so they drop into
`~/.claude/agents/` next to the `geo-*` ones and get picked up the same way.

## Install

```bash
cp answer-layer/agents/*.md ~/.claude/agents/
mkdir -p ~/.claude/skills/answer && cp answer-layer/SKILL.md ~/.claude/skills/answer/
pip install anthropic
export ANTHROPIC_API_KEY=...   # or: ant auth login
```

Then `/answer probe <domain>`.

## License

MIT.
