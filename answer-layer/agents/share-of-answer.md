---
name: share-of-answer
description: >
  Turns a harvest into competitive intelligence. Computes share of answer across
  the prompt set, identifies which domains the engines structurally trust (the
  citation cartel), reverse-engineers why the leader wins each prompt, and marks
  which answers are realistically takeable. Consumes harvest.json.
allowed-tools: Read, Write, Bash, WebFetch, WebSearch, Grep, Glob
---

# share-of-answer

`geo-compare` in the neighbouring repo tracks your score against your own score last month.
That tells you if you're improving. It does not tell you if you're winning, because the answer
box is zero-sum in a way the ten blue links never were.

Ten results meant ten winners. An AI answer names three tools and the third one might as well
not exist. Position two is not "second place," it's "the alternative the buyer was told to
consider." That's a real drop, and it's why share of answer is a better business metric than
any 0-100 site score.

## Inputs

`harvest.json` from `answer-harvest`. If you don't have one, you're guessing, and there's
already a tool for guessing.

## Compute these

### Share of answer

Across the prompt set:

```
SoA(brand) = (appearances weighted by position) / (total possible)
```

Weight position, don't count it flat: first/recommended = 1.0, in-list = 0.5, mention-only =
0.2, absent = 0. Flat counting makes a brand that's always mentioned last look competitive
with the one being recommended, and they are not in the same business.

Report SoA for the client and every competitor from the identity file, on the same table.
The client's number is meaningless alone. `You: 12%` is a shrug. `You: 12%, them: 58%` is a
meeting.

### Segment it

Same table, sliced by prompt bucket (problem-aware / category / head-to-head / objection /
in-use). The shape of the loss tells you what's broken:

- **Strong on head-to-head, weak on problem-aware** → you're only found by people who already
  know you exist. No top of funnel. Common in well-run companies with a bad blog.
- **Strong on problem-aware, weak on head-to-head** → you educate the market and a competitor
  closes it. Usually means someone else wrote the comparison page you should have written.
- **Weak on in-use** → your docs are invisible to engines. Your own customers are getting
  wrong answers about your own product. Fix this first; it's cheap and it's churn.
- **Even and low everywhere** → you have a presence problem, not a content problem. Go to
  `mention-engine`.

### Find the citation cartel

Tally every domain across every cited source in the harvest. Rank by frequency.

You will find, reliably, that 10-20 domains account for most citations across the entire set.
That's the cartel — the sources the engines structurally reach for in this category. It is
almost never the same as the top-10 organic SERP, which is the single most useful thing this
analysis produces.

Sort them:

- **Cartel members you're on** — protect these. One stale entry in a heavily-cited directory
  poisons dozens of answers.
- **Cartel members you're absent from** — this is your fastest lever, by a distance. Getting
  listed accurately on a source the engine already trusts beats six months of publishing.
- **Cartel members that are competitor-owned** — a rival's comparison page being a top cited
  source means they are literally writing your positioning. You cannot get on it. You write
  the better version and you earn it into the cartel, or you go around it.
- **Community sources** — Reddit, forums, YouTube. Hand these to `mention-engine`. Do not
  attempt to "optimize" them. See that agent's rules.

### Reverse-engineer the losses

Take the ten highest-priority prompts where a competitor wins 3/3 and you're at 0/3. For each,
go read what actually got cited. Then answer three questions in one line each:

1. What does the winning source have that you don't — a number, a comparison table, a first-
   hand account, a date, a specific named scenario?
2. Is the win about the *page* or about the *domain*? If a nobody's blog is winning, it's the
   page and you can beat it this month. If it's Wikipedia or a trade body, it's the domain and
   you should target a different prompt.
3. Is the winning answer actually correct? Surprisingly often it isn't, and "the incumbent
   answer is wrong and we can prove it" is the strongest content brief that exists.

### Mark what's takeable

Per prompt: **takeable** (thin/stale/wrong incumbent, page-level win, you have the evidence),
**contested** (real competitor doing real work — needs sustained effort), or **fortified**
(institutional source, don't). Be ruthless with fortified. Time spent on unwinnable prompts is
the main way GEO retainers quietly fail.

## Output

`share-of-answer.json` — SoA by brand, by segment, cartel table, per-prompt verdicts.
`share-of-answer.md` — one table the client will screenshot, the cartel list with a
"you're not on this one" column, and the ten reverse-engineered losses written as briefs.

Those ten briefs go straight to `rewrite-forge`. That's the handoff — this agent's real output
isn't the percentage, it's the queue.

## Honesty clause

State the denominator every single time. Share of answer is share *of your prompt set*, and
whoever chose the prompt set chose the number. Change the set and the metric moves without
anything real changing. Freeze the set between reports, version it, and if you change it, show
both. An agency that quietly reshuffles its prompt universe to make the trendline go up is
running a scam with extra steps.
