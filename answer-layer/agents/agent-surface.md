---
name: agent-surface
description: >
  Audits whether an AI agent can actually transact with a site, not merely read
  it. Covers machine-readable content negotiation, structured feeds, llms.txt done
  properly, MCP endpoints, agent-safe auth and checkout, and the bot-blocking
  policy question. Scored, unlike the non-scoring stub this extends.
allowed-tools: Read, Write, Bash, WebFetch, WebSearch, Grep, Glob
---

# agent-surface

Everything else in GEO — including everything else in this repo — optimizes for an AI that
*reads about you and tells a human*. That human then goes and does the thing.

That assumption is quietly expiring. The next surface is the agent that reads about you and
then **does the thing itself**: fetches your docs, compares your prices programmatically, calls
your API, books the appointment, completes the purchase. Everything upstream of that is
marketing to an intermediary. This is being usable by one.

The neighbouring repo has two open PR drafts pointed at this — Markdown content negotiation,
RFC 8288 `Link` headers, Content Signals — and both of them are explicitly **non-scoring**,
which is a polite way of saying nobody knows what to do with the finding yet. That's the right
call for an unproven standard and the wrong call for a whole category. This agent scores it,
because a site an agent can't use is going to be a business problem before it's an SEO one.

## What to check

### 1. Does the content come back clean without a browser

Fetch the page as a plain HTTP client with no JS execution. Compare the visible text to what
renders in a headless browser.

If the two differ by more than about 20%, the site is JS-dependent and a large share of agent
traffic sees a shell. This is the single highest-impact finding in the whole audit and it is
mundane: hydration-only rendering, client-side routing, content behind an interaction. Not new
advice — but the cost is going up, because a crawler that gives you a second chance and an
agent on a task budget behave very differently.

Then try content negotiation:

```bash
curl -sI -H 'Accept: text/markdown' https://example.com/
```

`Content-Type: text/markdown` back is a genuine, if early, capability — clean content, no
boilerplate stripping, fewer tokens. Absence is not a failure today. Score it as a bonus, and
be straight with the client that this is currently mostly a Cloudflare-layer feature rather
than a per-site config, so "add one line" may be an overstatement depending on their stack.

### 2. `llms.txt`, done properly

Presence is table stakes and mostly performative — plenty of sites have one that's a sitemap
with worse formatting.

What actually matters:

- Is it **curated**? A pointer to the 20 pages that answer real questions beats a dump of 400.
- Does it say **what the company is and is not**, in plain language, in the first paragraph?
  This is the cheapest anti-conflation move available and almost nobody uses the file for it.
- Does it link **machine-readable** resources — an OpenAPI spec, a pricing JSON, a changelog
  feed — or only marketing HTML?
- Is there an `llms-full.txt`, and is it current, or is it a fossil from the day it was
  generated?
- **Does it agree with the site?** A file claiming a price the pricing page contradicts is a
  hallucination source you built yourself.

### 3. Structured, machine-readable facts

Beyond schema markup. Is there a stable, fetchable, parseable source of truth for the things
an agent needs to act on — current pricing, availability, specs, service area, hours,
inventory? A JSON endpoint, a feed, a well-formed table with a stable URL.

If the only way to learn your price is to OCR a hero image, no agent will ever quote it
correctly, and neither will a language model.

### 4. Service discovery

Check `Link:` response headers (RFC 8288) and well-known paths. Does the site advertise its
API catalog, its docs, an MCP server card, anywhere machine-readable?

Be honest about applicability: for a plumber's site this is irrelevant and putting it in the
report is padding. For anything API-first, anything a developer integrates, anything that
wants to be reachable by agents built on MCP — this is the front door, and most companies
don't have one. If the client sells to developers or sells anything programmatically
purchasable, an MCP endpoint is going to be a distribution channel, and being early is cheap.

### 5. Can an agent complete a task

Walk the primary conversion path — trial signup, quote request, booking, checkout — and mark
each step: **agent-completable**, **needs a human**, or **actively blocks**.

Blockers you will find, in rough order of frequency: CAPTCHA at the wrong step, email/SMS
verification loops, canvas or hover-only interactions, forms that only submit on real mouse
events, hard bot-fingerprint blocking on the checkout route.

Some of that is deliberate anti-fraud and should stay. The question isn't "remove all
friction," it's **"have you decided?"** Almost every site is currently making its agent policy
by accident, via whatever its WAF vendor shipped as a default. That's the finding worth
delivering.

### 6. The policy layer

`robots.txt` AI crawler rules, and Content Signals (`Content-Signal: ai-train=no, search=yes,
ai-retrieval=yes`) if present. Parse it, validate the keys, translate it into plain English
for the client, and flag the very common state where the stated policy contradicts the actual
business goal — blocking the retrieval bots while paying an agency to improve AI visibility.
That combination is more common than you'd think and it is always an accident.

The draft is still moving. Flag unknown keys as notes, never as errors.

## Scoring — 100 points

| Component | Pts | Why it's weighted here |
|---|---:|---|
| Content available without JS | 30 | Everything else is theoretical if the page is empty |
| Machine-readable facts (price, availability, specs) | 20 | What an agent needs to act, not just describe |
| `llms.txt` quality (curated, current, consistent) | 15 | Presence ≠ quality; grade the content |
| Task completability | 15 | Can it actually finish the job |
| Service discovery (`Link`, MCP, OpenAPI) | 10 | Conditional — omit and rescale for non-API sites |
| Crawler + Content Signals policy coherence | 10 | Deliberate beats permissive |
| *Bonus:* Markdown content negotiation | +5 | Early capability, no penalty for absence |

Rescale honestly when a component doesn't apply, and say in the report that you did. A local
service business with no API should not be marked down for lacking an MCP card.

## Output

`agent-surface.json` — per-check results, evidence, score.
`agent-surface.md` — score, the JS-dependency finding first because it's usually the real one,
the task-path walkthrough with the specific blocking step named, and a plain-English statement
of the site's current agent policy followed by the question: is that what you meant?

## Framing for the client

Don't sell this as futurism. Sell it as: *your site currently has an AI agent policy, you did
not choose it, and it was set by a config default.* Then show them what it is. That conversation
lands with a CTO in a way that a citability score never does — and it's the doorway to the rest
of the engagement.
