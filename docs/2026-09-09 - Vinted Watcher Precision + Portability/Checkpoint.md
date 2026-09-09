# Checkpoint: Vinted Watcher Precision + Portability

**Date:** 2026-09-09
**Status:** Watcher live and recording again; hashtag generation shipped; portability assessed and gated

---

## Summary

A rating button the owner pressed did nothing, and the cause was a schema
migration that had never reached the production table: every INSERT into
`alerts` had been failing for two hours behind a warning nobody could see.
Fixing it exposed a second silent gate (the local preflight ran a strict subset
of CI), and a third gap the owner had named three times without being told it
was absent (the listing bot generated no hashtags at all). All three are closed
and shipped. The session closes with a researched answer on extending the engine
to other trading fields, and a hard gate against doing so yet.

---

## What Was Done This Session

### The alert-recording outage (PR #749)

1. Diagnosed from the owner's report that the ntfy buttons "don't work". They
   did: both taps were sitting on the feedback topic. The watcher read them,
   advanced its cursor, and discarded them because `ingest_feedback` required
   an `alerts` row that no longer existed.
2. Root cause: `alerts.quality` was added to the DDL, `CREATE TABLE IF NOT
   EXISTS` is a no-op on an existing table, and the migration loop only ever
   walked `listings`. Every `record_alert` raised `OperationalError`.
3. Four failures had to line up for two hours of silence: the INSERT sits
   behind the ntfy call so alerts kept arriving; the per-search handler caught
   the error as a flaky poll; the warning went to a stdout `run-hidden.vbs`
   discards; and the feedback path consumed the taps regardless.
4. Measured cost: 21 of 26 buttoned alerts unrecorded, plus both real taps.
5. Fixes: `reconcile_ddl_columns` derives migrations from the DDL literal for
   every table; `alterable` reports the columns SQLite refuses in place
   (PRIMARY KEY, UNIQUE, NOT NULL without default, non-constant default);
   index creation is per-statement so a broken table shape cannot brick
   `db_connect`; `log()` writes `data/watcher.log`; `is_schema_error`
   escalates a shape mismatch to a non-zero exit; `feedback_target` stores a
   rating for any listing the database has seen, with a null `alert_id`.
6. Recovered 34 lost alert rows from the delivered ntfy notifications, stamped
   `recovered-from-ntfy` in `settings_json`, `quality` left NULL because it was
   never in the message. Both owner ratings recorded and linked.

### Real posting time and the owner's heart rule (PR #752)

1. Answered the owner's question about a likes-per-time ratio with a
   measurement: the denominator is the poll interval (median 3.18 min over
   33,231 live rows), not a market fact, and 64% of candidates carry zero
   hearts. Rejected as a ratio.
2. Found the larger defect it exposed: `listing_age_min` measures time since
   WE saw a listing and read 0.0 on every alert. 7 of 107 alerts were on
   listings 3.8 hours to 5.05 days old, four of them ringing.
3. The clock was already in the database: the Vinted photo URL ends in the
   image's upload epoch. Validated four ways (35,392 of 35,393 rows parse;
   live-poll median 3.18 min vs seed-crawl median 3.7 days; zero negative
   ages; Spearman 0.993 against Vinted's ascending listing ids; and hearts
   rise monotonically with age to 24h then fall).
4. Implemented the owner's own rule, which resolved the sign question the
   analysis could not: hearts count only under 60 minutes, as a capped +35%
   lift inside the existing ring budget rather than an absolute rule.

### Hashtags (PR #756)

1. Established that the bot the owner had asked for three times did not exist:
   `MAX_HASHTAGS` lived only in the validator, and the generator emitted none.
2. First draft was worse than nothing: drawing from corpus terms it offered
   `#cargo #knee #chino` for one pair of trousers and `#nuptse` for a jacket
   whose model nobody entered. A keyword in prose is a search word; a hashtag
   is a claim, and unrelated tags are an enumerated hide trigger.
3. Shipped the split that works: chosen tags come only from supplied fields
   (model, cut, era, brand+type fallback); corpus terms return as candidates
   to confirm. Three filters keep the slots worth having (Vinted-filtered
   words are inert, singular/plural stem to one, a candidate must add a word).

### Local gate repair (in PR #752)

`tools/preflight-hooks.py` ran pytest without httpx and pyyaml while the CI
`hooks` job passes both, so every `importorskip`-guarded module was silently
skipped, including the entire 151-test Vinted suite, while the tool printed
"the CI hooks job should pass". Matching the dependency list moved the local
count from 1178 to 1329.

### Portability assessment (no code)

Measured the split of the 3,297 lines: at most 52% marketplace-bound (upper
bound; a function counts as bound if any line touches the API), 31% vocabulary,
17% pure engine; 27 of 33 database columns are market-neutral. Then ran a
13-agent workflow with web research over six candidate fields, each judged
against seven preconditions, each verdict attacked by a skeptic. Result in
Working Notes.

---

## Key Decisions Made

### Hearts count only on young listings, and only as a ranking lift

- **Choice:** A listing under 60 minutes old with hearts gets up to +35%
  quality, capped, inside the existing 15-per-day ring budget. No age penalty
  for old listings.
- **Rationale:** The owner's own formulation, which answers what the data could
  not: on a young listing hearts mean demand arrived within minutes; on an old
  one they mean the market looked and did not buy. An absolute rule would have
  flooded the loud channel (35% of candidates carry at least one heart), so the
  lift makes young liked candidates win the existing slots instead of adding
  new ones. Stale listings need no penalty; the relative bar demotes them.

### Hashtags are claims, so only supplied fields may fill them

- **Choice:** Corpus-mined terms never become chosen tags; they return as
  candidates for the seller to confirm.
- **Rationale:** The corpus describes the cell, not the garment. Two concrete
  falsehoods were produced before the rule existed. Vinted's hide trigger is
  "besonders viele oder nicht zugehoerige Hashtags", with no refund on a paid
  push, so an unverifiable tag has negative expected value.

### No second trading field before 30 completed round trips

- **Choice:** Portability work is gated on a measured correlation between the
  predicted comp median and the realised sale price, over 30 round trips, with
  a pre-registered abort criterion.
- **Rationale:** The comp median is a median of ASKING prices. Whether it
  predicts realised price has never been measured, not even in the one market
  where both sides are visible. If it does not hold there, it holds nowhere,
  and every ranked opportunity below inherits the same unproven assumption.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/projects/vinted-reselling/watcher/vinted_watcher.py` | edit | DDL reconciliation, log file, schema-error escalation, feedback survival, posting time, heart lift |
| `workspace/projects/vinted-reselling/listing/keyword_engine.py` | edit | `build_hashtags`, `slug_tag`, hashtag CLI block |
| `tools/tests/test_vinted_watcher_session.py` | edit | 151 tests (was 128) |
| `tools/tests/test_vinted_keyword_engine.py` | edit | 26 tests (was 16) |
| `tools/preflight-hooks.py` | edit | pytest dependency list matched to the CI hooks job |
| `workspace/projects/vinted-reselling/listing-reference.md` | edit | the chosen-vs-candidate hashtag rule |
| `workspace/projects/vinted-reselling/status/watcher.md` | edit | outage record, posting time, portability gate |

---

## Current Status

Watcher live from `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-watcher` (detached
on origin/main, `data/` and `context/` junctioned to the primary clone),
scheduled task green, ~36,600 listings growing at ~13,800/day. Alert recording
verified working on the live 5-minute task, not by hand: the 21:50 run wrote
`alerts` rows carrying `quality`, and the 21:55 run ingested a freshly
published feedback tap (77 to 78 rows). Six PRs merged this session (#749,
#750, #752, #753, #756) plus two from a parallel session (#755, #757) that
executed the seven-point prompt written here.

`vinted-reselling`: no `infrastructure.yaml`, no comms log; both correct for a
self-operated project.

Outcome data remains the binding constraint: 3 trustworthy gone events, 3 owner
ratings, 1 purchase made on a recommendation, `my_listings` at 0 rows.

---

## Next Steps

1. Build the round-trip ledger (~300 lines: purchase, landed cost, holding
   days, listing, realised price) and start the 30-trip run. Nothing else in
   this project is worth more.
2. Register the Gewerbe before that run rather than after; a tax adviser on the
   §25a record-keeping is the one point not to self-serve.
3. Two ten-minute probes that each open or close a field: a mail to Reverb API
   support describing exactly what would be stored, and a leaf-key dump of a
   Vinted electronics response against the clothing census.
4. Manual, no code, no ToS contact: check the 200 comp-densest cells on
   Kleinanzeigen within pickup radius against the Vinted median. Decides the
   top-ranked expansion before a line is written.
5. The ~12 unverified findings from the 2026-09-08 adversarial review remain
   open (`brand_report` splits gone-rate across two populations, `poll_search`
   untested, `refresh_session` bypasses the backoff).

---

## Context for Next Session

### Files to Read First
- `workspace/projects/vinted-reselling/status/watcher.md`
- `workspace/projects/vinted-reselling/listing-reference.md`
- `.scratch/synthesis.md` (the full portability analysis, 17.5k chars)

### Open Questions
- Does the comp median predict the realised sale price? Unmeasured, and
  everything else rests on it.
- Kleinanzeigen: robots-compliant polling only, or the app JSON API? The first
  is 125 unsorted, unfiltered results per query; the second circumvents a
  technical measure rather than a prose clause. Owner decision, before code.
- Do Reverb's API terms actually forbid storing a corpus? Quoted by an agent,
  not independently confirmed (the page returns 403/404 to fetching).
- Is Grailed viable? It was dismissed on an invalid test and reportedly has a
  public index with sizes, conditions and visible sold prices.

### Working Notes

**Portability, the one criterion.** The engine works only where identity is
DERIVABLE but the median is UNPUBLISHED. A canonical id (set number, card name)
makes identity free and the median public, so repricers have taken the spread.
Free text (Kleinanzeigen listings) makes the median incomputable. Second-hand
branded clothing sits in the narrow band between, which is why it works.

**Ranked outcome.** (1) Kleinanzeigen as a BUY-side feeder into the existing
Vinted sell side, because the sell side already exists and local pickup
structurally excludes remote competition. Verified personally: the robots.txt
disallows `/*/sortierung:*`, `/*/preis:*`, `/*/anbieter:*`, `/*.json`, `/api`
and everything from `seite:6`, so a compliant client sees 125 unsorted results
per query. (2) Canonical-id inversion: buy where no price guide exists, sell
where one is published; corpus cost zero. (3) Vinted electronics: same adapter,
needs a title-to-model extractor.

**Ranked out.** eBay as a sourcing market fails on quota arithmetic (brand and
size are not in the search response, only in a per-item call, sharing 5,000
calls/day against 13,800 items/day). Collectibles as a second instance are dead
on access closure (Cardmarket, TCGplayer) and anonymised sale details
(BrickLink). Sellpy/Momox/Zircle are dealers with algorithmic prices, so the
mispricing population does not exist. Useful correction: eBay is not blind on
the sell side, Terapeak is free in Seller Hub with up to three years of real
sold prices; only the unauthenticated automatable route closed.

**Cross-market rule.** Extend sourcing where prices are unobserved; never
extend selling where the realised price is invisible. A second selling venue on
eBay fails on P3, not on fees: used clothing has no GTIN and the
Vinted-to-eBay resolver has no precedent.

**Method note.** Both workflows this session refuted nearly every lens (6 of 6,
then 5 of 6). The skeptic prompt said "default to refuted=true when you cannot
reproduce", which makes the refutation signal nearly uninformative. Next
workflow: ask the skeptic to grade confidence per claim instead of returning a
binary on the whole verdict.

### Reference Materials
- Workflow transcripts: `subagents/workflows/wf_40c9d59e-353` (like velocity),
  `wf_c0ef798d-fbe` (portability)
- `.scratch/synthesis.md`, `.scratch/portability_audit.py`

---

## How to Continue

The watcher needs no attention; it runs. Start with the round-trip ledger, and
treat every portability item as blocked until the 30-trip result exists. If the
owner asks about extending to another field before then, the answer is in
status/watcher.md open point 7.

---

## Strategic Feedback

### What Worked Well This Session

- Measuring before designing repeatedly changed the answer. The likes-ratio
  question dissolved once the poll interval was measured; the "build a
  continuous collector" framing dissolved once the existing cycle was measured
  at 13,800 listings/day and a full corpus mine at 37ms.
- Testing the hashtag output on three real items caught two fabricated claims
  before merge. Writing the test cases found a third defect unprompted
  (`alterable` did not reject UNIQUE, which would have crashed the connect on
  the next DDL column).

### Suggestions

- Verify the premise before explaining the mechanism. The owner asked three
  times for hashtag definition and twice received usage instructions for a
  tool that produced none. A single run of the actual output against the
  capability he named would have caught it on the first ask.

### System Health

- The parallel-session hazard bit twice: a sibling committed this session's
  uncommitted work as "abandoned" and removed the worktree from under it. The
  content was correct and nothing was lost, but the safe pattern is committing
  each coherent change immediately rather than accumulating in a shared clone.
- Autonomy: 4 human interventions (elevated). Three were the hashtag miss and
  its follow-ups; one was a genuine design decision the owner answered better
  than any of the four options offered.
