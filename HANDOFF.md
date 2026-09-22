# Handoff brief

Paste everything between the rules into a fresh Claude Code session started in this
directory. It carries the full context of what this is and why each decision was made.

---

I'm working in `~/Downloads/Rebuild Answers — Agency Website`. Read `README.md`,
`answer-layer/SKILL.md`, and `answer-layer/docs/scoring.md` first, then this brief.

## What this is

Rebuild Answers is a GEO (generative engine optimization) agency. Answer Layer is its open-source
tooling — MIT. The agency sells the work, not the tool.

It was built against a specific gap in `github.com/zubair-trabzada/geo-seo-claude`, a good
open-source AI-search auditor (~8,500 lines, 15 skills, 5 subagents). Every number that tool
produces is a **proxy**: `citability_scorer.py` is regex that rewards `"X is a…"` openings, a
134-167 word count, and low pronoun density. Nothing in it ever asks an AI engine a question
and checks whether the client appeared in the answer.

Answer Layer measures that directly and hangs everything else off it. No code was copied.

## What exists

**7 agents** in `answer-layer/agents/`, Claude Code subagent format:
`prompt-universe` (which questions are worth winning) → `answer-harvest` (fire them at live
engines, 3 runs, verbatim) → `share-of-answer` (competitor share + citation cartel) →
`rewrite-forge` (writes the replacement copy). Plus `hallucination-watch` (what models say
wrong, traced to source), `mention-engine` (earned presence, with hard anti-astroturf rules),
`agent-surface` (can an agent transact with the site — scored /100).

`hallucination-watch` and `agent-surface` have no counterpart in the source repo.

**3 scripts** in `answer-layer/scripts/`:
- `probe.py` — the measurement engine. `claude-opus-5` + `web_search_20260209`, explicit
  `pause_turn` resume, verbatim answers preserved, separate `messages.parse()` extraction
  pass, word-boundary brand matching that flags its own disagreements. **Never yet made a
  live API call** — verified only against mocks.
- `surface_check.py` — stdlib only, tested live. Rebuild Answers page 91, Semrush 53, Ahrefs 38.
- `diff_harvest.py` — tested against synthetic harvests, all four change classes correct.

**The site** in `site/` — five pages, all static, sharing `site.css`:
`index.html`, `method.html`, `work.html`, `pricing.html`, `answer-index.html`, plus
`llms.txt`, `pricing.json`, `robots.txt`, `sitemap.xml` and `CONCEPT.md`.

Built to the rules it argues for: no JS needed to read anything, curated `llms.txt`,
machine-readable prices, deliberate `Content-Signal`. Its published **91/100 is a real
measurement**, re-verified 21 Sep 2026 after the rewrite (1503 words server-rendered).

Two placeholders are live in the markup and flagged in an HTML comment on every page:
the `cal.com` booking URL does not exist yet, and `hello@rebuildanswers.com` must be a real mailbox.
The mailto CTAs work the moment the mailbox is real.

**The Answer Index page is deliberately empty** and says so on its face. It stays that way
until a real harvest exists — publishing invented numbers would contradict the entire pitch.

Social metadata is complete: Open Graph + Twitter Card on all five pages, pointing at a
generated 1200x630 `og.png`. `pricing.html` also carries `FAQPage` schema — added for machine
readability rather than Google rich results, which are restricted for FAQ now.

**`rename.sh`** — changes brand name, domain, slug and the split logo markup across every
file in one pass, then regenerates `og.png` with the new name. Dry run by default, `--apply`
to commit. Self-updating, so chained renames work — verified through two chained renames.
A name change is expected.

**`answer-layer/scripts/make_og_image.py`** — regenerates the social card. Needs Pillow
(in the venv). Takes name, domain, output path.

**`run.sh`** — `check` / `smoke` / `probe` / `full` / `surface` / `diff` / `serve`.
Paid commands confirm before spending. `serve` previews the site on localhost.

## Current target: Rebuild

Pre-launch. Not indexed. Competitors are **Semrush** and **Ahrefs**.

Input files are staged in `answer-layer/out/rebuild/`.

**The name is a problem and it's flagged in `identity.json`.** "Rebuild" is a common English
verb and it's this category's own vocabulary — *rebuild your content strategy*, *rebuild your
backlink profile*. Bare-word matching will be dominated by false positives, engines can't
entity-resolve it, and `hallucination-watch`'s "conflated" class is pre-loaded. A distinctive
second token fixes it for free pre-launch. `aliases` is deliberately empty, three prompts were
cut as undisambiguatable, and `probe.py --baseline` warns loudly if presence comes back
non-zero.

**The prompt set is 18, segmented, and freezes on first run:**
- Space A (12) — AI-visibility/GEO prompts, mean priority 18.2. Winnable.
- Space B (6) — classic SEO prompts, mean priority 6.8. Three are marked
  `FORTIFIED — do not chase` and exist only to prove the segment contrast.

Winnability is scored as *"can a credible new entrant win this within 12 months"*, not "can
Rebuild win today" — which is zero for all 18, because it isn't indexed.

## Strategic position

Both incumbents shipped AI-visibility products at scale we cannot match: Semrush's AI
Visibility Toolkit (130M+ prompts, "Share of Model"), Ahrefs' Brand Radar (150M+ monthly
potential prompts, 6 AI indexes, $199–699/mo).

**So don't compete on measurement volume — we'd lose and the copy would be rebuttable.**

The gap is that both are *monitoring* platforms. Review coverage says of Semrush plainly: not
an optimization platform, limited workflows to fix. Neither writes the copy. That's
`rewrite-forge`, and it's structurally hard for them to copy because per-client remediation is
services work with bad software margins. It's not that they haven't got to it — it breaks
their model.

Free supporting evidence, already measured: both sell AI-visibility tooling and neither has
machine-readable pricing; Ahrefs has no `llms.txt`; neither declares Content-Signal.

## Rules that are not negotiable

These are written into the agents and the method doc. Hold them.

- **State the denominator.** Share of answer is share *of the prompt set*. Whoever picks the
  set picks the number. Freeze it, version it, report both in any transition month.
- **State the engine.** We query one. It is not "AI search."
- **Presence is a fraction, never a boolean.** 1/3 and 3/3 are different findings.
- **Never fabricate prompt volume.** Cite checkable evidence instead.
- **No astroturfing**, no bought reviews, no burying accurate criticism.
- **Say when a competitor genuinely wins.** Mark it fortified and spend the hour elsewhere.

## What to do next

1. `./run.sh check` — free, verifies everything.
2. `./run.sh smoke` — 2 prompts, 1 run, pennies. This is the first live API call `probe.py`
   has ever made. **Watch for an empty citation cartel** — that means the web-search result
   parsing in `ask()` is wrong and needs fixing before spending more.
3. `./run.sh probe` — the trimmed 10-prompt baseline.
4. Then run `share-of-answer` against the harvest. The cartel table is the prize: if Reddit
   and G2 carry these answers rather than semrush.com and ahrefs.com, the launch plan is
   community-first and the incumbents' content moat matters far less than it looks.

Ask before spending money, and don't spawn subagents unless I ask.

## Claims that rot

Every dated claim on the site is a maintenance obligation. A GEO agency caught quoting a
stale self-measurement has a credibility problem, not a typo. These are the lines to touch,
and when:

| Where | Claim | Refresh when |
|---|---|---|
| `index.html` self-audit block | `91 / 100 · measured <date>` | Every re-run of `surface_check.py`. Currently measured against **localhost**, not the live domain — re-run after deploy. |
| `index.html` footer | `Page last measured <date>` | Same run, same date. |
| `answer-index.html` | `Status checked <date> · 0 categories` | Whenever the count changes, and at least quarterly while it reads zero. |
| `llms.txt` | `Status as of <date>: no readings published yet` | Same trigger as above. Keep the two in sync. |
| `pricing.html`, `llms.txt`, `pricing.json` | `Prices as of <date>` | Only when prices actually change. Do **not** bump to look fresh. |
| `method.html` | `last revised <date>` | When the methodology changes. |

Location: Florida. `addressLocality` is deliberately absent from the schema — no city was
invented. Adding one is a single line in `index.html`'s JSON-LD plus the display strings.

