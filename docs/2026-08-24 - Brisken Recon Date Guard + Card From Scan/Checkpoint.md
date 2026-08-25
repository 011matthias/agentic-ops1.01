# Checkpoint: Brisken Recon Date Guard + Card From Scan

**Date:** 2026-08-24
**Status:** Backlog items 25 and 28 shipped and deployed (Fly v85); item 27 narrowed, not closed

---

## Summary

Two money-adjacent reading defects on the receipt-first pipeline: a receipt's
year read as 2023 in an April 2026 month, and the paying card that decides
which company an expense books to. Both were diagnosed by measurement rather
than inference, both shipped with the mechanism the measurement supported, and
what the measurement refuted is recorded so nobody re-runs it.

---

## What Was Done This Session

### Item 25 — an implausible date stops being accepted quietly (PR #590)

1. Diagnosed by pulling the stored readings off the Fly volume and comparing
   each to its receipt image. It was ELEVEN of the April batch's 36 readings,
   not the one row the backlog described.
2. Separated the three cases the backlog named. Parse: innocent (every row
   equals the cached payload verbatim; the layer is a plain `fromisoformat`).
   Genuine old print: false (the receipts print 2026). Model: confirmed, two
   mechanisms — `receipt_33` prints `Data: 2026-04-22` in its fiscal block and
   `26-04-22` (YY-MM-DD) on the card slip and the model read the slip
   day-first; `receipt_03` prints `02/04/2026` and the model invented the year.
3. Tightened the extraction prompt and MEASURED it both directions: 6 of 11
   misreads fixed, 24 of 25 already-correct readings byte-identical, the 25th
   changed to the value the receipt actually prints. A control run (old text 3x,
   new text 3x) proved that last change was the prompt, not re-read noise.
4. Because five stay wrong, shipped the deterministic half: `batch_period.py`
   plus a `date_outside_period` review state, and the month report PDF names
   the expense numbers it distrusts. Nothing is auto-corrected; a date the
   reviewer typed is believed.

### Item 28 — the paying card, read off the scan (PR #592)

1. Measured the defect: asked to TRANSCRIBE four faded digits the extractor
   landed 2 in 5 and invented the rest. `1234` came back three separate times,
   once for a receipt that plainly prints 1672.
2. Refuted three cheaper fixes before building anything. Repeat reads return
   the identical wrong answer (stable, not noisy). A verbatim field beside the
   interpreted one agrees even when both are wrong, and sometimes loses digits
   the interpretation kept. gpt-4o reads no better than gpt-4o-mini.
3. Changed the question instead: the extractor gets the last-4s of the cards
   the payer actually holds and picks one or declines. Deny-by-default, and the
   card list joins the extraction-cache key.
4. Moved vision to gpt-5-mini (categorization stays gpt-4o-mini). Measured 3
   runs each over 7 problem receipts: dates 0/6 live to 3.0/6 with the list to
   5.0/6 with the model; cards 1/5 to 3.0/5 to 3.7/5; zero false positives.

### Bookkeeping and a trap removed

1. PRs #591 and #593 moved both items to Shipped and opened item 27 (wrong day
   inside the right month) with the trade named: better year reading makes that
   class harder to see, because an error that used to trip the date guard now
   lands in the right month.
2. PR #594 fixed a stale paragraph that still told the next session to ask the
   owner what the CSV gets imported into — a question the 2026-08-23 directive
   closed and the loop brief lists as do-not-re-ask.

---

## Key Decisions Made

### The guard judges the month, and refuses to guess one
- **Choice:** period from the operator's label, failing that the batch's own
  dates by strict plurality, failing both nothing at all.
- **Rationale:** a guessed month puts good rows under suspicion, and every
  flag costs the reviewer a look. Silence beats a wrong period.

### A date the reviewer typed is believed
- **Choice:** `date_is_human` suppresses the flag for an edited or manual date.
- **Rationale:** the guard questions the MACHINE's read. Without the valve a
  genuinely re-issued old invoice could never be cleared and would sit in
  review forever, which is how a guard becomes noise people ignore.

### The card is a choice, not a transcription
- **Choice:** hand the model the payer's known last-4s; it picks or declines.
- **Rationale:** four faded digits are not reliably readable by any model
  tried, but the answer only ever has to be one of about six cards. Recall rose
  and the hallucinations stopped, with zero false positives.

### Vision moves to gpt-5-mini, categorization does not
- **Choice:** split the models.
- **Rationale:** reading a receipt and categorizing a line of text are
  different calls and only the reading was failing. gpt-5 rejects
  `temperature=0`; reading correctly is worth more than pinning a parameter,
  and the extraction cache still makes re-runs byte-identical.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/batch_period.py` | new | Which month a batch is; refuses to guess |
| `src/expense_recon/web/service.py` | edit | `date_outside_period` review state, report note, `VISION_MODEL` |
| `src/expense_recon/llm/client.py` | edit | Date prompt, `card_last4` as a constrained choice, cache key, gpt-5 temperature |
| `src/expense_recon/cli.py` | edit | `_known_card_digits` from the run's registry snapshot |
| `src/expense_recon/ingest/receipts_folder.py` | edit | Confirmed card replaces guessed digits in `payment_mode` |
| `tests/test_batch_period_dates.py` | new | 16 tests; the live April readings are the fixture |
| `tests/test_card_from_receipt.py` | new | 11 tests incl. the wiring test |
| `status/p1-improvement-backlog.md` | edit | Items 25/28 shipped, 27 opened and narrowed, layer 4 unblocked |
| `status/p1-expense-reconciliation.md` | edit | Two shipped rows with the registry caveat |
| `status/p1-recon-loop-prompt.md` | edit | Next session no longer pointed at a closed item |

---

## Current Status

Fly v85, suite 1217 passed / 2 skipped, calibrate green. PRs #590-#594 all
merged on green CI. Live-verified twice with a namespaced TEST batch (deleted
after; app confirmed clean): a receipt printing `VISA - ******2838` came back
date 2026-04-11 (the cache held 2023-04-11), hint `VISA ...2838`, card-2838,
Corporate Services via `card`.

The April report PDF now reads "The date read on expenses 2, 8, 11, ... falls
outside this month"; expense 2 is the 2023 row the owner spotted on line two.
Across all five live batches the guard behaves: Criss's real May month flags
none of its 20 genuine receipt rows.

Ops status: `platform: unknown plan, ~?/? ops/mo. Last assessed: ?` — Brisken
has no `platform` section in `infrastructure.yaml` and runs on FastAPI/Fly, so
the line is structurally empty rather than a signal.

---

## Next Steps

1. **Owner: card registry data entry** (item 26). Entities on 0113/6013/9693/
   8311, create the 0340 card, add 1672 to the Chase card. This now gates the
   item-28 feature, not just the MISSING ENTITY count — the model can only pick
   cards the registry knows, and production has neither 0340 nor 1672.
2. **Owner: apply `docs/lovable-month-report-prompt.md`.** The only unapplied
   prompt that changes what Criss can DO; the month's deliverable is a document
   and she has no button to reach it.
3. **Owner: one restore click** on Dirk's rendered credit notice in the January
   set-aside strip.
4. Item 10 leftovers when a code round comes: persisted cards migration (every
   card still reads `source: "legacy"`) and intake dropdown unification.
5. Zoho layers 2 and 3: the `zoho_account` field renames (SPA-coordinated
   parallel-field migration) and the chart gate's rename plus a non-Books chart
   source. Layer 4 is unblocked and sequences after layer 2.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`

### Open Questions
- None outstanding with the owner. Everything the loop was blocked on has been
  answered; item 26 is data entry, not a question.

### Working Notes

**Do not re-run these. They were measured and refuted this session:**
- Repeat reads as a misread detector. Three reads of each problem image return
  the IDENTICAL wrong answer for both date and card, and the model reports
  0.9-0.95 confidence on every one, so confidence is useless as a signal too.
- A verbatim transcription field beside the interpreted value (`date_text`,
  `payment_line`). Same look at the page, so they corroborate each other even
  when both are wrong; verbatim also lost digits the interpretation kept.
- gpt-4o for extraction. No better than gpt-4o-mini and it broke a date mini
  had right.

**Ground truth read off the images by eye**, expensive to re-derive:
`receipt_03` 2026-04-02 / card 1672; `receipt_12` 2026-04-02 / 0340;
`receipt_21` 2026-04-11 / 2838; `receipt_32` 2026-04-21 / no card printed;
`receipt_33` 2026-04-22 / 0340; `receipt_34` 2026-04-21 / 0340; `receipt_35`
illegible. Images at `.scratch/test-receipts-ER-00215/`.

**Reading the stored extractions** (the diagnosis that separated the three
cases): `flyctl ssh console -a brisken-expense-recon -C "python3 -c \"...\""`
with a read-only sqlite open on `/data/extraction-cache.sqlite`. Base64-piping
image bytes out through `ssh console` does NOT work (empty files); the same
receipts were already local.

**A live behavioral probe is cheap and worth it:** create a `TEST - ...`
labelled batch through `POST /api/expense-batches`, poll the job (the batch row
404s until the pipeline finishes), read the row, then delete via
`POST /api/runs/{id}/delete` with `{"confirm": "<the exact label>"}`. Confirm
zero `TEST -` batches remain afterwards; one probe batch materialized after the
first listing and needed a second sweep.

### Reference Materials
- PRs #590, #591, #592, #593, #594
- Probe scripts (throwaway): `%TEMP%/claude/recon-item25/`

---

## How to Continue

`/comd_resume brisken`, then read the loop brief and take the top open backlog
item. Nothing in this session is half-finished: every PR is merged, the deploy
is verified, and the test batches are cleaned up. The highest-value moves are
owner-side (items 26 and the month-report prompt), so a code round should wait
on evidence from Criss's next month unless the owner directs otherwise.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring before building, and recording the refutations. Three plausible
  fixes for the card (re-reads, verbatim corroboration, a bigger model) each
  cost a handful of API calls to disprove and would each have cost a full
  round to build and then discover. The negative results are now in the backlog
  and the memory, which is where their value actually is.
- Regressing the real source on every guard. It caught that 9 of 10 card tests
  exercised the helper directly and would have passed a fix that never shipped;
  the wiring test exists because the regression exposed that, not because it
  was planned.

### Suggestions
- The `gate-skip-iteration-3x` hook fired four times on a legitimate
  measurement series (four DIFFERENT one-shot experiment scripts sharing a
  `uv run --directory "$R" ... python .../recon-item25/*.py` prefix) and twice
  on distinct heredoc edits. Six false positives in one session is enough to
  suggest the shape-match should compare the invoked SCRIPT PATH, not the
  command prefix. Filed here rather than built, since it is a system-dev change
  and this was a client session.

### System Health
- Autonomy: 1 human-visible intervention — the Stop hook's B1 block on a
  closing deferral ("say the word and I'll run it") about the checkpoint. The
  user corrected no work product this session; the gate caught the one lapse
  structurally, which is the layer working as designed.
- The friction register is at 360 KB and trips the >200 KB archive advisory,
  but `archive-register` has nothing to move: every row is newer than its
  2026-06-25 cutoff. The register is large because the last two months were
  dense, not because it is carrying dead weight, so the advisory is currently
  unactionable and will stay noisy until the cutoff rolls forward.
