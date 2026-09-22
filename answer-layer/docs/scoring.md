# How the numbers are built

Two scored things in this layer: **share of answer** and **agent surface**. Both are opinions
expressed as arithmetic. This page says whose opinion and why, so a client can argue with the
method instead of the number.

That's the point of publishing it. A GEO score you can't interrogate is a vibe with a decimal
place.

---

## Share of answer

### The weighting

Appearances are weighted by position, not counted flat:

| Position | Weight | Why |
|---|---:|---|
| `first` — named as the recommendation | 1.0 | The answer. Most readers stop here. |
| `listed` — one option among several | 0.5 | Real, but you're the alternative |
| `mention_only` — referenced, not offered | 0.2 | Visible, not considered |
| `absent` | 0 | |

```
SoA = Σ(weight per appearance) / (prompts × runs)
```

Flat counting makes a brand that's always named last look competitive with the one being
recommended. They are not in the same business. The 0.5 for `listed` is a judgement call — you
could argue 0.4 or 0.6 and we wouldn't fight you. What isn't arguable is that it must be less
than `first` and more than `mention_only`.

### Presence rate is a different number

`presence_rate` in `harvest.json` is unweighted and stricter: **the share of prompts where the
brand appeared in at least 2 of 3 runs.**

The 2/3 line is doing real work. These systems are non-deterministic — a brand can appear in
run 1 and vanish in run 2 for the same prompt. A single run is close to worthless as evidence.
Three runs gives a stability signal:

| Stability | What it means | What to do |
|---|---|---|
| 3/3 | You own this answer | Protect it. Watch for framing drift. |
| 2/3 | Reliable but not locked | Fine. Don't spend here. |
| 1/3 | Pulled in by luck | **Cheapest fix in the file.** Small changes will hold it. |
| 0/3 | Invisible | The work queue. Goes to `rewrite-forge`. |

Report the fraction. Never the boolean. Collapsing 1/3 and 3/3 into "present" throws away the
most actionable column in the dataset.

### The denominator, stated every time

**Share of answer is share of your prompt set.** Whoever picks the prompts picks the number.

This is not a caveat to bury in a footnote — it's the single biggest integrity risk in the
category. Add ten easy prompts and the line goes up while nothing real changed. So:

- The prompt set is **frozen** for the engagement.
- If it has to change, version it (`prompt-universe.v2.json`), keep both, and report both
  numbers during the transition month.
- Every report states the set, the version, the date, and the engine queried.

An agency that quietly reshuffles its prompt universe to make the trendline go up is running a
scam with extra steps. The client works it out eventually, and then nothing you measured is
believed again.

### The engine, also stated every time

`probe.py` currently queries one engine: Claude with server-side web search. That is a real
answer engine and a reasonable proxy for the others, and it is **not ChatGPT**.

What generalizes across engines is the **source layer** — which domains get retrieved — because
they're drinking from a similar web. What doesn't generalize is exact phrasing, ordering, and
who gets named first. So: cartel findings travel, position findings don't.

Adding a provider is about 30 lines against the same two-pass shape. Until then, no report says
"AI search" when it means one engine.

---

## Agent surface — 100 points

| Component | Points | Reasoning |
|---|---:|---|
| Content without JS | 30 | Everything else is theoretical if the raw fetch returns a shell. Weighted highest because it's both the most common failure and the most consequential. |
| Machine-readable facts | 20 | The gap between *describable* and *actionable*. An agent can't quote a price it can't parse — and neither can a model. |
| `llms.txt` quality | 15 | Graded on content, not presence. A 400-link dump scores near zero; a curated 20 with a plain statement of what the company is scores full. |
| Task completability | 15 | Can an agent finish signup / booking / checkout, or does step 4 need a human. |
| Service discovery | 10 | Conditional. Dropped for non-API sites and the rest rescaled. |
| Policy coherence | 10 | Whether the crawler and Content-Signal policy matches the stated business goal. |
| *Bonus:* markdown negotiation | +5 | Early capability. Never a deduction. |

### Why 30 points on the JS check

Because it's the one that's actually true about most sites and nobody wants to hear it. A
client will happily discuss `llms.txt` for an hour and go quiet when you show them their
homepage renders 40 words to a plain HTTP client.

It also gets *worse* as agents matter more. A crawler that gets a shell comes back later. An
agent working a task budget does not.

### Rescaling

When a component doesn't apply, it's dropped and the remainder rescaled to 100 — and the report
says which ones were dropped, inline, in the score line. A local service business with no API
should not be marked down for lacking an MCP card, and it should not have to guess whether it
was.

### Non-scoring by design

Content Signals unknown keys are **notes, never errors**. The IETF draft is still moving — the
spec author's own site uses a key that isn't in the published set. Penalizing a site for
tracking a draft standard faster than the standard does is bad measurement.

Markdown negotiation is bonus-only for the same reason, plus a practical one: it currently
appears to be a CDN-layer feature rather than a per-site config, so "add one line" may be an
overstatement depending on the client's stack. Say the bonus, don't sell the fix.

---

## What none of this measures

Volume. The engines do not publish how many people ask any given prompt.

Be precise about this, because the big platforms have a real answer to it and overclaiming here
is how you lose an argument in public. Ahrefs' Brand Radar and Semrush's AI Visibility Toolkit
both run prompt databases in the 130M–260M range and model demand from observed search
behaviour — "search-backed prompts, not synthetic," in Ahrefs' phrasing. That is a legitimate
methodology and it is not something we can match at our scale.

What it is not is measured prompt volume. It is demand inferred from adjacent search data, and
the inference is load-bearing. So the honest position is narrower than "nobody knows": *nobody
observes it directly, large platforms model it from search demand at scale, and we don't model
it at all.*

We build prompt sets from first-party evidence instead — sales calls, lost-deal notes, support
tickets, community threads — and cite the evidence rather than a number. *"14 distinct Reddit
threads in six months, near-identical phrasing"* is a claim a client can go and verify. It is
deliberately a smaller claim than `1,200/mo`, and a checkable one.

Different instrument, not a better one. Say so.

It's a weaker-looking claim and a stronger real one.
