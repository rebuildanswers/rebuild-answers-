# Answer Layer and geo-seo-claude

They solve different halves. Run both.

## What each one is for

| | geo-seo-claude | Answer Layer |
|---|---|---|
| **Question** | Is this page *shaped* to be cited? | Are we *actually* in the answers? |
| **Method** | Static analysis of HTML, robots, schema | Live queries against answer engines |
| **Evidence** | Regex, heuristics, structural rules | Verbatim answers with their citations |
| **Output** | 0-100 GEO score, client PDF | Presence fractions, cartel, replacement copy |
| **When** | Before you write. Diagnostic. | After you ship. Verification. |
| **Cost** | Free, no API spend | Real API calls — dollars per run |

Neither replaces the other. A page can score 94 on citability and be invisible; a page can have
bad schema and own the answer because one Reddit comment keeps getting retrieved. You need both
views or you're guessing about which.

## The honest summary of the split

`geo-seo-claude` is a genuinely good static analyzer with an excellent client-deliverable
pipeline. Fifteen skills, five parallel subagents, a real PDF. Its weakness is that every number
it produces is a proxy — nothing in it ever asks an engine a question.

Answer Layer measures the thing directly and is weaker everywhere else. No PDF pipeline, no CRM,
no schema template library, no local-business specialization. It costs money to run.

So: their audit, our measurement.

## Running them together

```bash
# 1. Static diagnostic — free, fast, tells you what's structurally broken
/geo audit https://example.com          # -> GEO-AUDIT-REPORT.md

# 2. Ground truth — what's actually happening in the answers
/answer universe example.com            # -> prompt-universe.json  (freeze this)
/answer probe example.com               # -> harvest.json
/answer share example.com               # -> who's winning, and the cartel

# 3. Reconcile the two. This is where the value is.
/answer forge example.com               # consumes BOTH reports
```

`rewrite-forge` reads `GEO-AUDIT-REPORT.md` as an input. That's the interop point, and it's the
most useful moment in the whole workflow — you get to ask:

**Where does the static audit disagree with reality?**

- **High citability score, 0/3 presence** → the page is well-built and nobody can find it.
  Distribution problem, not a content problem. Go to `mention-engine`.
- **Low citability score, 3/3 presence** → you're winning through somebody else's page. Fragile.
  Find out whose, before they change it.
- **Both low, high commercial value** → the actual work queue. Start here.
- **Both high** → protect it. Set a `watch`.

That table is the reason to run both. Either tool alone gives you one column.

## Non-overlapping coverage

Things `geo-seo-claude` does that this doesn't:
schema template generation, Core Web Vitals, E-E-A-T scoring, PDF reports, prospect CRM,
proposal generation, local-business specialization.

Things this does that `geo-seo-claude` doesn't:
live engine queries, competitor share of answer, citation-cartel identification,
misinformation detection with source tracing, actual replacement copy, scored agent-readiness.

The last two are the ones we'd argue matter most, and it's why they got built.

## Installation side by side

Both use the standard Claude Code layout, so they coexist without conflict:

```
~/.claude/agents/
    geo-ai-visibility.md      geo-content.md      geo-schema.md
    geo-platform-analysis.md  geo-technical.md
    prompt-universe.md        answer-harvest.md   share-of-answer.md
    hallucination-watch.md    rewrite-forge.md    mention-engine.md
    agent-surface.md

~/.claude/skills/
    geo/        (their orchestrator, /geo)
    answer/     (ours, /answer)
```

Different command namespaces, no filename collisions, no shared state. Their runtime data lives
in `~/.geo-prospects/`; ours lives in the project under `answer-layer/out/`.

## Credit

`geo-seo-claude` is MIT, by [zubair-trabzada](https://github.com/zubair-trabzada/geo-seo-claude).
No code from it is used here — this layer was written against the gap, not against the source.
Its two open agent-readiness PR drafts (Markdown negotiation, RFC 8288, Content Signals) are
where `agent-surface` started, and it's a good instinct that deserved a scored home.
