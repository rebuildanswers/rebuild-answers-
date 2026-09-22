---
name: hallucination-watch
description: >
  Finds what AI engines say about a brand that is factually wrong, stale, or
  confused with a competitor — then traces each error to the source that caused it
  and the specific fix that corrects it. This is reputation triage, not SEO.
  Nothing in geo-seo-claude or any mainstream GEO tool checks for it.
allowed-tools: Read, Write, Bash, WebFetch, WebSearch, Grep, Glob
---

# hallucination-watch

Every GEO tool asks "are we visible." This one asks the question that actually keeps founders
up: **what are they saying about us when we're not in the room.**

A model confidently telling ten thousand people that your product starts at $99 when you moved
to $149 last year is not a ranking problem. It's a pricing leak, a support ticket generator,
and — depending on the industry — a compliance issue. It also does not show up anywhere in a
citability score, a schema audit, or a Core Web Vitals report. Nobody is checking. That's why
this exists.

Everyone's worried about hallucination in their own AI features. Almost nobody has checked
what the models hallucinate *about them*.

## Step 1 — build the truth file

You cannot detect a wrong answer without a right one written down. This is the unglamorous
part and it is the whole job.

Sit with the client and fill `answer-layer/out/<domain>/truth.json`. Every entry needs a value
and a URL where that value is publicly stated. If there's no public URL, that's your first
finding — the model has nowhere to learn it from.

```json
{
  "brand": "Example",
  "facts": [
    {"k": "founded",        "v": "2019",                "src": "https://example.com/about"},
    {"k": "hq",             "v": "Austin, TX",          "src": "https://example.com/about"},
    {"k": "entry_price",    "v": "$149/mo",             "src": "https://example.com/pricing"},
    {"k": "free_tier",      "v": "no, 14-day trial",    "src": "https://example.com/pricing"},
    {"k": "founders",       "v": "A. Rivera, D. Okafor","src": "https://example.com/about"},
    {"k": "not_a",         "v": "not a CRM; often confused with one", "src": null},
    {"k": "discontinued",   "v": "Example Lite, ended 2024", "src": null}
  ]
}
```

Those last two rows matter more than the rest. Negative facts — what you are *not*, what you
*stopped selling* — are where models fail hardest, because the internet keeps the old page up
forever and nothing on the live site contradicts it.

## Step 2 — interrogate

Two prompt families, both run 3x (same non-determinism rules as `answer-harvest`):

**Direct.** "What is Example?" "Who founded Example?" "How much does Example cost?" "Does
Example have a free tier?" "Is Example still in business?" "What happened to Example Lite?"

**Oblique** — where the real damage lives, because the model is being casual rather than
careful. "I'm choosing between Example and [Competitor], what should I know?" "Why do people
leave Example?" "Is Example good for enterprise?" "What are the downsides of Example?"

Ask a few you know the answer to and a few you don't. And ask at least one deliberately loaded
question — "why is Example so expensive" — because a model will often accept the premise and
generate a justification out of nothing. What it invents to justify a false premise tells you
what it believes.

## Step 3 — classify every discrepancy

Not all wrong is equally wrong. Sort into five:

| Class | What it is | Typical fix |
|---|---|---|
| **Stale** | Was true, isn't now | Update the live page; the model is quoting a real source |
| **Fabricated** | Never true, no source | Publish an explicit correct statement it can retrieve |
| **Conflated** | Your facts fused with a competitor's / same-name company | Entity disambiguation — `sameAs`, distinct naming, Wikidata |
| **Distorted** | Technically sourced, badly framed — one angry review becomes "users report" | Volume of counter-evidence, not a takedown |
| **Omission** | Model says you don't do a thing you do | Nowhere states it plainly; the info is trapped in a video or a PDF |

Score each: **severity** (does it cost a deal, mislead on price, or create legal exposure) ×
**frequency** (of runs it appeared in). A fabricated price appearing 3/3 is a fire. A distorted
tone note appearing 1/3 is a note.

## Step 4 — trace it

This is what separates this agent from a complaint. For each error, find *why*.

Ask the engine for its sources on that specific claim. Search the wrong value yourself and see
where it lives. Common culprits, in the order you'll find them:

1. An old page on the client's own site, still indexed, never redirected. **Most common by
   far.** People update the pricing page and leave `/pricing-2023` live.
2. A stale third-party listing — a directory, an aggregator, an "alternatives to" page
   somebody wrote in 2023 and never touched.
3. A press release announcing something that later changed.
4. A single popular forum thread, now load-bearing for the entire model's opinion.
5. Genuinely nothing — the model interpolated from category norms. Hardest to fix; requires
   putting an explicit, retrievable statement where one has never existed.

Record the trace. "Model says $99. Source: `example.com/legacy-pricing`, still 200 OK, last
modified 2023-04." That line is worth more than the finding.

## Step 5 — write the correction plan

Per error, one row, ordered by severity × frequency:

- what the model says
- what's true
- where it learned the wrong thing
- the exact action (kill the page / add the paragraph / add the schema / earn the mention)
- who owns it and roughly when it should re-check clean

Then set the recheck. Corrections take weeks to months to propagate — the model isn't looking
at your site live, it's working from an index and a training run. Tell the client that up
front, or the second report reads like failure.

## Output

`hallucination-watch.json` — every discrepancy with class, severity, frequency, trace, fix.
`hallucination-watch.md` — the client version, and it opens with a verbatim quote of the worst
thing an AI said about them. Nothing you can write is more persuasive than that sentence.

## One hard rule

**Never fix a true negative by burying it.** If the models say support is slow because support
is slow, that is not a hallucination and this agent does not touch it. Write it down as
customer feedback that happens to have arrived through a language model and hand it to the
client. Astroturfing a genuine complaint out of the answer layer is the fastest way to earn a
real reputation problem, and it is not work we do.
