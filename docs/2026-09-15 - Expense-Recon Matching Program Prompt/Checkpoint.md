# Checkpoint: Expense-Recon Matching Program Prompt

**Date:** 2026-09-15
**Status:** Prompt delivered (v1 in chat 2026-09-11/14, v2 corrected below); program not started

---

## Summary

The owner asked for a pasteable prompt that makes a fresh session raise the
expense-recon matcher's success rate on Criss's real months. The prompt is a
measure-first program: label the live July and August months, attribute every
unmatched receipt to the one gate that lost it, then fix in ranked rounds with
the pinned six-bundle scorer kept as a regression floor. Between delivery and
this checkpoint the parallel round shipped two of the items the prompt treated
as open, so the corrected prompt (v2) is the one to paste.

---

## What Was Done This Session

### Read the matcher and its instruments (origin/main, not the stale checkout)
1. `matching/deterministic.py` `match_one` + `match_month`: same-currency
   exact/probable bands (0.00 / 20 %, 1 / 5 days), exact-FX off the statement's
   original amount, self-derived monthly rates, card scoping on the charge's
   card keys, entity scoping (empty entity unscoped since 2026-09-11),
   bilateral-uniqueness gate plus card-contradiction gate on rate-derived
   pairs, greedy bipartite assignment, ties to `ambiguous`.
2. `matching/judgment.py` (LLM layer for FX_JUDGMENT / AMBIGUOUS / POSSIBLE)
   and `web/service.py` `rematch_month` (bakes reviewer edits into the pool,
   borrows trip receipts, calls `match_month`, then the three judgment passes
   through the judgment cache).
3. `tools/scorers/recon-match-accuracy.py` + `tools/recon-accuracy-guard.py`:
   218 labels over six Zoho-ER months (95 confirmed / 46 no_charge / 77
   excluded), +1.0 / +0.3 / -2.0 composite, 2024 months held out, fixture only
   in the main clone's gitignored context. Train composite 31.5 -> 49.5 after
   matcher-v2 (PR #418), 0 wrong.
4. Backlog items 27, 56, 59-64 and the 2026-09-11 void list.

### Wrote the prompt
Delivered in the reply as one fenced block (per
`feedback_prompts_are_pasteable_text`). No repo file changed for it.

---

## Key Decisions Made

### The program measures before it tunes
- **Choice:** Phase 0 is a labeled fixture from the live months plus a
  per-receipt failure attribution table; no matcher change before that table
  exists.
- **Rationale:** The only pinned scorer measures Zoho expense-report receipts
  (base amount, payment mode, entity present). Live receipts are mailed or
  dropped vision reads with none of those fields, so the scorer no longer
  measures the population the owner is unhappy with. The 2026-09-11 void list
  names six gaps but not what each costs.

### Coverage is reported apart from matching
- **Choice:** Every report splits "unmatched, charge exists somewhere" from
  "unmatched, no charge on any statement".
- **Rationale:** January had 78 of 80 charges with no receipt at all; a
  matched-charges figure keeps reading as matcher failure however good the
  matcher gets.

### Known dead ends are listed in the prompt
- **Choice:** The refuted levers from `docs/optimize/brisken-recon-tuning-v1/
  SUMMARY.md` and backlog item 28 are named so the session does not re-run
  them.

### No status-file or backlog edit from this session
- **Choice:** Ledger only (this checkpoint); the backlog entry for the program
  waits for the next p1 client branch.
- **Rationale:** Ten sibling sessions hold `client/brisken/p1-item-*` branches
  under the parallel-round protocol (#824); a docs branch must not carry
  client paths (rule_branch_isolation §1).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `docs/2026-09-15 - Expense-Recon Matching Program Prompt/Checkpoint.md` | created | this record, carries prompt v2 |
| `docs/INDEX.md`, `docs/sessions/2026-09-15.md`, `docs/sessions/2026-09-15-context.yaml` | scaffold | ledger entries |

---

## Current Status

brisken platform: unknown plan (pre-flight could not read `infrastructure.yaml`
platform section); Fly app `brisken-expense-recon` pinned always-on, live
**v116** as of 2026-09-14.

Live months after PR #815 (items 56 + 59) and the owner-approved refresh:
July 2026 27 clean + 11 review of 111 charges / 50 receipts; August 2026 14
clean + 3 review of 111 charges / 31 receipts; every ambiguous invoice+receipt
pick gone. Item 60 shipped (#820, `held_by`). Items 61-68 plus 16 and 17 are
in flight, one session each (`agentic-ops1-item61` ... `item68` worktrees).

The matching program has not started. Prompt v1 (in the chat reply) is stale
on two points; v2 below is corrected.

Stale p2 status files flagged by pre-flight, untouched here (not this
session's scope): `p2-lead-gen-general.md` (86 d), `p2-product-decks.md`
(54 d), `p2-rome.md` (55 d), `p2-targeting.md` (55 d).

---

## Next Steps

1. Paste prompt v2 (Working Notes) into a fresh session AFTER the parallel
   round's items 61, 62, 63 have merged, or tell that session to read
   `git log origin/main` first and drop any class a merged item already fixed.
2. In that session, Phase 0 first: pull July + August off the Fly volume,
   label, attribute, print the table. No matcher edit before the table.
3. Add a "matching improvement program" entry to
   `workspace/clients/brisken/status/p1-improvement-backlog.md` on a
   `client/brisken/...` branch (not from a docs branch).
4. p2 owner session: refresh or delete the four stale p2 status files.
5. `BriskenReconNotify` runs from the main clone, which is 24 commits behind
   origin/main and blocked by a sibling's dirty meji file; re-match mails
   (item 58) stay dark until main is pulled.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` (house loop,
  constraints, probe helpers)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 27, 56,
  59-68; the parallel-round protocol section)
- `docs/optimize/brisken-recon-tuning-v1/SUMMARY.md` (dead ends)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/deterministic.py`
- `tools/scorers/recon-match-accuracy.py`, `tools/recon-accuracy-guard.py`

### Open Questions
- Whether the parallel round's item 63 (same-currency band across vendors)
  and item 61 (neighbouring statement period) land before the program starts;
  each removes a class from the attribution table.
- Whether Criss's own confirm/reject decisions in the live snapshots are
  numerous enough to serve as labels, or the propose -> accept flow has to be
  run by hand.

### Working Notes

**What the v1 prompt got wrong by the time it was read.** It asked for owner
rulings on items 56 and 59; both were ruled and shipped 2026-09-14 (#815,
v116: duplicate groups collapse to one candidate automatically, a `not a
duplicate` ruling re-expands; a charge's entity comes from its own card and
is blank when the registry cannot name the card). It cited July 24/15 and
August 14/7; the live figures are July 27/11 and August 14/3. Its class list
includes items 61, 62, 63, which the parallel round is building now.

**The prompt, v2 (paste as is):**

```
Brisken expense-reconciliation (p1): matching improvement program

Load the Brisken p1 project in a fresh worktree off origin/main (other
sessions are live on the main clone). First run `git log origin/main
--oneline -40` and read workspace/clients/brisken/status/
p1-improvement-backlog.md: items 61-68 were built in a parallel round
starting 2026-09-15, and any of them that merged removes a failure class
from this program. Then read p1-recon-loop-prompt.md beside it and the
memories project_brisken_expense_recon_usability_loop,
project_optimize_s1_recon_scorer_design and
project_brisken_expense_recon_testing_loop. Module root:
workspace/clients/brisken/automations/expense-reconciliation.

THE PROBLEM
The matcher pairs too few receipts with charges on Criss's real months. Live
on Fly v116 (2026-09-14): July 2026 has 111 charges and 50 receipts, 27
matched clean and 11 in review; August has 111 charges and 31 receipts, 14
clean and 3 in review. Every receipt that ends in review or unmatched is a
manual step for Criss. The goal: raise the share of receipts that resolve
deterministically and correctly, with zero wrong auto-matches, measured on
her real data.

Two things this program is NOT. It is not coverage: a charge with no receipt
anywhere (78 of January's 80) is not a matching failure, and every report
must separate the two so a coverage gap is never read as a matcher defect.
And it is not the old tuning run: docs/optimize/brisken-recon-tuning-v1/
SUMMARY.md and backlog item 28 list what was tried and refuted (date window
below 5 days, base-amount pct 0.005, reference pct 0.015, repeat vision
reads, verbatim fields beside interpreted ones, a stronger model alone, a
vendor gate as precision separator, fuzzy learned-store lookup). Do not
re-run any of them.

PHASE 0: MEASURE BEFORE TOUCHING THE MATCHER
1. Pull July and August 2026 off the Fly volume (/data/runs/<run_id>/,
   flyctl ssh sftp with MSYS_NO_PATHCONV=1; the machine is pinned always-on)
   and replay each month locally from its stored snapshot with NO llm block:
   receipts are already extracted, so this costs nothing and reproduces the
   hosted match (rates are inlined into the run's matching block).
2. Build a labeled fixture for both months with the existing flow
   (expense-recon label propose -> human-edit -> accept, labeling.py). Where
   Criss or the reviewer already confirmed or rejected a pair in the live
   snapshot, that decision is the label. Keep the exclusion discipline: an
   ambiguous receipt is excluded, never guessed; a receipt that never posts
   to a card (bank transfer, PayPal, cash) is no_charge.
3. Write a failure-attribution script (scratch first, tools/ if it earns it):
   for every receipt not matched clean, name the ONE gate that lost it, in
   the order the code applies them: currency unknown; no date; entity
   mismatch; card scope; no candidate inside the date window; amount outside
   the band; same-currency pair offered across different vendors (item 63);
   demoted by the uniqueness or card-contradiction gate; correct pair present
   but a rival won the greedy assignment; receipt dated in the neighbouring
   statement period (item 61); no charge on any statement (item 62: coverage,
   not matching). Print a table: class, count per month, money per class,
   three example pairs each. This table is the deliverable of Phase 0 and
   decides everything after it. Do not propose a fix before it exists.
4. Extend the same attribution to the existing six-bundle scorer
   (tools/scorers/recon-match-accuracy.py, hash-pinned). That scorer stays a
   regression FLOOR for every round: train composite and holdout must not
   drop, determ_wrong stays 0.

PHASE 1: RANK AND PLAN
From the table, rank classes by receipts recovered per unit of change,
cheapest structural fix first. Write a one-page plan as a user walkthrough
(what Criss sees before and after), technical detail in an appendix. Present
it and stop. If a class needs an owner ruling, put it as a decision with a
recommendation and its consequence, not as an open offer.

PHASE 2: ROUNDS
One failure class per round, in ranked order. Each round:
- a regression test proven RED first by regressing the real source (snapshot
  the working tree in memory, never git checkout to restore), then green;
- both scorers run BOTH directions: the broken pairs move, the already-correct
  pairs stay byte-identical, wrong auto-matches stay at 0;
- expense-recon calibrate and the full suite green; ruff clean on the diff;
- ship per B6 (feature branch, PR, merge on green CI), deploy from a clean
  origin/main worktree (pre-authorized after a green merge), then re-match
  July and August live through the API and confirm month_health and the
  counts moved as predicted; drive the SPA workbench for one changed row.
MatchingConfig defaults and config/match-tuning.json stay in lockstep; the
hosted image never reads the tuning file. Structural changes to match_month
or rematch_month beat threshold changes; the two gates that won before
(bilateral uniqueness, card contradiction) are the model.
Stop after three rounds or when the next class recovers fewer than 3
receipts a month, whichever comes first, and report.

REPORT FORMAT (end of program, also as a backlog entry)
Per month, before and after: receipts total, matched clean, in review,
unmatched with a charge somewhere (matching gap), unmatched with no charge
(coverage gap), wrong matches. Per round: class fixed, receipts recovered on
the live months, scorer delta on the six-bundle floor, PR and Fly version.
Open rulings and dead ends appended to p1-improvement-backlog.md; update
p1-expense-reconciliation.md and the loop brief.

STANDING CONSTRAINTS
Never message Criss or Dirk. Never invent a number: every count comes from
the replay or the live API. Live fixtures are TEST- namespaced and removed
after use; never seed a fabricated receipt into a real month. No LLM calls
for measurement (judgment cache and no-llm replay exist for this); the
OpenAI key bills Dirk. Read-only against the live app under autonomy; a
live re-match after a deploy is the one write, and it goes through
rematch_month, never a hand-edited snapshot. No stash; worktrees only.
Ledger files never on the client branch.
```

**Facts the prompt rests on** (read off origin/main this session, all
in-code): same-currency exact tolerance 0.00, probable 20 %; date exact
1 day, probable 5; FX date window 5; `fx_base_amount_match_pct` 0.01 (the
one lever the 2026-07-23 run kept); `card_scoping` on; blend weights
0.55 / 0.30 / 0.15 (amount / date / vendor), card weight 0. Receipts from
mail and drop carry `payment_mode` only from the vision hint
(`receipts_folder.py` `_payment_mode`), no `base_amount`, no
`detected_reference` beyond what the extractor returns.

### Reference Materials
- `docs/optimize/RECIPES.md` (constructed-metric protocol, if a second
  scorer is pinned)
- `%TEMP%/claude/recon-probe/api.py` (live API probe helper)
- Fixture (main clone only, gitignored):
  `workspace/clients/brisken/context/expense-reconciliation/expense-reports/csv/by-month/`

---

## How to Continue

Paste prompt v2 into a fresh session once the parallel round has merged what
it will merge. That session owns Phase 0 end to end before any code.

---

## Strategic Feedback

### What Worked Well This Session
- Reading every file through `git show origin/main:` instead of the checkout,
  which was 13 and then 24 commits behind; the stale-checkout advisory at
  session start was the cue.
- Designing the program around a measurement the existing instrument cannot
  give (live vision receipts vs Zoho-ER receipts) rather than around the
  backlog's guesses.

### Suggestions
- A prompt written against a moving parallel round should open with "check
  what merged since this was written" (v2 does). More generally, a delivered
  prompt is stale the moment a sibling merges; the checkpoint, not the chat
  reply, is where the current version has to live.

### System Health
- 17 worktrees, ten of them one-item p1 sessions; the main clone is 24
  commits behind and cannot fast-forward past a sibling's dirty
  `meji-media/status/enquiry-automation.md`. The `BriskenReconNotify`
  scheduled task runs from that stale clone, so item 58's re-match mails are
  not live yet.
- Autonomy score: 0 human interventions (fully autonomous session).
