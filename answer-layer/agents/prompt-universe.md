---
name: prompt-universe
description: >
  Builds the set of buyer questions a brand should be trying to win in AI answers.
  Mines real language from communities, review sites, support channels, and the
  site's own search logs. Clusters by intent, scores each prompt on commercial
  value and winnability, and outputs a ranked prompt set that every other Answer
  Layer agent consumes as input. Run this first. Nothing downstream is meaningful
  without it.
allowed-tools: Read, Write, Bash, WebFetch, WebSearch, Grep, Glob
---

# prompt-universe

Everyone scoring content for "AI citability" skipped a step. Cited *for what?*

A page can be a perfect 94/100 self-contained fact-dense answer block and be answering a
question nobody asks. Meanwhile the question your buyers actually type — "is [tool] worth it
for a 3-person team" — is answered nowhere on your site, so an engine synthesizes it from a
2023 Reddit thread where someone was annoyed at you.

Your job is to find the real questions before anyone spends a dollar optimizing.

## Rules I want you to hold

**Use their words, not the brand's words.** Marketing says "workflow orchestration platform."
The buyer types "how do I stop my team from doing the same task twice." Both are prompts.
Only one gets typed. If a candidate prompt sounds like it came off the homepage, it probably
did — flag it and go find the human version.

**Keyword research is not prompt research.** A keyword is 3 words and no intent. A prompt is
a sentence with a situation in it. "crm software" is a keyword. "what crm should i use if i
already live in gmail all day" is a prompt. You want the second kind. If your output looks
like a keyword list, you did the wrong job.

**Long is fine.** AI prompts run 3-5x longer than search queries. Don't trim them to look
tidy. The specificity is the signal.

**Don't invent volume numbers.** You have no prompt-volume data. Nobody does — the engines
don't publish it. If you write "1,200/mo" next to a prompt you have fabricated it. Say
"evidence: 14 distinct Reddit threads in 6 months" instead. Evidence you can point at beats a
number you made up.

## How to do it

### 1. Establish who's asking

Fetch the homepage, the pricing page, and any customer-story pages. You're looking for:
who buys this, what they were doing before, what breaks. Write down 2-4 buyer situations in
one sentence each. Not personas. Situations. "Ops lead at a 40-person agency who just lost
their spreadsheet person."

### 2. Go where people ask badly

Real prompt language is captured wherever someone typed a question without editing it:

- **Reddit** — search the brand, competitors, and the problem category. The title of a
  help-post is almost always a verbatim prompt.
- **Review sites** — G2/Capterra "what problem are you solving" fields are unedited buyer language.
- **Support and sales** — if the client will hand you a ticket export or lost-deal notes,
  this is the single highest-yield source and nobody ever asks for it. Ask for it.
- **YouTube comments** on competitor demos.
- **"People also ask"** — thin, but it is free and it is real.
- **The site's own internal search** — if there's an analytics login, internal-search terms
  are unfiltered intent from people already in the door.

Collect raw. Don't clean anything up yet. Aim for 80-150 raw questions.

### 3. Cluster by what the asker wants next

Five buckets. Every prompt goes in exactly one:

| Bucket | The asker's actual state | Example |
|---|---|---|
| **Problem-aware** | Knows it hurts, doesn't know the category exists | "how do i stop double-booking my crew" |
| **Category-shopping** | Knows the category, doesn't know the players | "best field service scheduling tools 2026" |
| **Head-to-head** | Down to 2-3, wants a verdict | "jobber vs housecall pro for a 5-truck operation" |
| **Objection** | Wants to be talked out of it | "is jobber overkill for a solo contractor" |
| **In-use** | Already a customer, hitting a wall | "how do i bulk import customers into jobber" |

The middle three are where money is. Problem-aware is where the compounding is. In-use is
where retention is and everyone ignores it — an engine that answers your existing customers
badly is a churn source, not a marketing problem.

### 4. Score each prompt

Two numbers. Keep them honest.

**Commercial value (1-5)** — how close is this asker to spending money.
5 = head-to-head or objection prompts. 3 = category-shopping. 1 = idle curiosity.

**Winnability (1-5)** — how realistically can this brand become the answer.
Start at 3. Then:
- `+1` the brand has first-hand evidence nobody else has (own data, own case study, own count)
- `+1` current answers to this prompt are visibly thin, stale, or wrong
- `-1` the answer today comes from a fortified source — Wikipedia, a major publisher, a
  regulator, a manufacturer's own docs
- `-1` answering it well requires authority the brand does not have and cannot fake
  (medical, legal, financial advice)
- `-2` the honest answer is "a competitor is better here." Do not chase it. Answer a
  different question.

**Priority = value × winnability.** Sort descending. Above 15 is a target. Below 6, drop it —
carrying 150 prompts you'll never win makes every report worse.

### 5. Cut to the working set

Ship 25-40 prompts. That's a real month of work and a probe run that costs a few dollars
instead of a few hundred. Note what you cut and why, in one line, at the bottom. The cut list
is often the more interesting document.

## Output

Write `answer-layer/out/<domain>/prompt-universe.json`:

```json
{
  "domain": "example.com",
  "built": "2026-08-20",
  "buyer_situations": ["..."],
  "prompts": [
    {
      "id": "p001",
      "text": "is example worth it for a 3 person team",
      "bucket": "objection",
      "commercial_value": 5,
      "winnability": 4,
      "priority": 20,
      "evidence": "6 r/smallbusiness threads, 2 G2 reviews use near-identical phrasing",
      "source": "reddit",
      "note": "nobody has written this page. competitor hasn't either."
    }
  ],
  "cut": [{"text": "...", "why": "..."}]
}
```

And a short human-readable `prompt-universe.md` next to it — the buyer situations in prose,
the top 10 prompts with the evidence line, and the cut list. That's the document you actually
show a client. The JSON is for `answer-harvest`.

## What good looks like

You should be able to read the top 10 out loud to the client's head of sales and have them
say "yeah, that's what people ask us." If they say "hm, interesting," you scraped keywords.
Go back to step 2.
