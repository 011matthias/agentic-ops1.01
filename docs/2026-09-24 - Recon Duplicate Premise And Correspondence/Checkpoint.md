# Checkpoint: Recon Duplicate Premise And Correspondence

**Date:** 2026-09-24
**Status:** Item 186 shipped, deployed (`0726b428`), cold-driven. Item 185 prompt filed, partly applied. Duplicate identity-set work scoped, not built.

---

## Summary

The owner asked for a view-receipt control on the Email intake page, then for
better duplicate recognition on the premise that two different invoices never
share an ID. Measuring that premise against all seven live months found the one
class it cannot cover — a document that QUOTES an invoice's identity — and July
2026 turned out to hold a Redis dunning notice booked as a second USD 13,200.00
expense, roughly 42% of the month's USD total.

---

## What Was Done This Session

### Item 185: open a receipt from the intake page (PR #1257)
1. Measured the live log before writing anything: 72 of 143 mails render `-` in
   the Files column and **61 of those 72 did produce a receipt**, because the
   cell reads `files` (attachment names) and a body-only mail has none.
2. Read the published bundles: `chunk-inbound` names no receipt call at all
   while `chunk-x` carries the `?as=png` helper and every `receipt.*` string, so
   the viewer exists and the page simply never asks it for anything.
3. Prompt handed as pasteable text and filed at
   `docs/lovable-intake-receipt-view-prompt.md`.

### The premise, measured
4. 201 expenses, 146 distinct reference keys, 23 keys on 2+ documents. **22 of
   23 hold.** The single refusal (`NQTJA4FE`, five Anthropic July top-ups at
   five amounts) is an account id, not a document number.
5. The existing account-id guard needs **two differing totals in one pool** to
   fire, so Hostinger `H_46243348` (same amount, 25 days apart) sailed past it
   and a human had to override the tool.
6. Labelled `invoice_number` / `receipt_number` already exist, are stored, and
   `duplicates.py` ignores them — but they cover 20% of rows and **twin nothing
   on their own**, because an invoice and its receipt carry two different
   numbers. Their value is as a TYPE signal.

### Item 186: a payment reminder is not a purchase (PR #1268)
7. `correspondence.py` quarantines a dunning notice / payment reminder so it
   never becomes an expense, wired through `NON_RECEIPT_LABELS` into both
   quarantine sites plus the intake reason labels.
8. `intake_mail.body_text_by_digest` carries the mail body to the rendered-body
   PDF only, never an attachment.
9. Markers calibrated over 103 readable mail bodies of 143 archives; 29 tests;
   three wiring points regress-checked; suite 3205 / 2; accuracy gate unchanged.
10. Deployed to Fly, `/healthz` commit matches the merge, cold Playwright drive
    signed in and read the Email intake page back with real rows.

---

## Key Decisions Made

### Quarantine the class rather than sharpen the key
- **Choice:** Build a correspondence rung before touching the duplicate key.
- **Rationale:** A notice prints the number, the date and the amount, which is
  the exact triple every duplicate key matches on. It is a flawless duplicate
  by construction, so no key can tell it apart, and "copy" is the wrong verdict
  anyway — it is not an expense at all. Put to the owner via AskUserQuestion
  with this recommendation; they chose it.

### Two signals, not one
- **Choice:** Require a dunning marker AND no itemization.
- **Rationale:** A marker alone would quarantine a real invoice printing a
  past-due footer — a shape the mail-body corpus cannot rule out, since it
  holds no vendor PDFs. No itemization alone is ordinary: taxi slips, card
  slips and tickets legitimately print a total and nothing else.

### Leave the extractor's prompt alone
- **Choice:** A deterministic post-check, not a new `document_type` enum value.
- **Rationale:** Item 105's measured reason — a prompt edit moves unrelated
  readings across the estate and invalidates every cached one.

### Do not touch the live rows
- **Choice:** Ship the code fix, report the two wrong July rows, write nothing.
- **Rationale:** `feedback_recon_no_live_writes_criss_acts`. The change stops
  the next one; the existing rows are Criss's to correct.

---

## What Did NOT Work (and why)

- **A date-agreement rung on the duplicate key** (my first recommendation,
  disproved before it was built): 21 of 23 repeated reference keys have a 0-day
  spread, so "same number, dates far apart = not a copy" looked clean on the
  metadata. Opening the documents killed it. Hostinger `H_46243348` is 25 days
  apart and IS one invoice forwarded twice, so the rung would have broken the
  case it was meant to fix while leaving Redis wrong in the other direction.
- **`flyctl ssh console -C` with a piped payload** (`echo <b64> | base64 -d |
  python3`): hangs at "Connecting to fdaa:…" and never returns, at 4.2 KB and
  again at 1.7 KB, while the same `sh -c` wrapper with a short non-piped
  command returns fine. Cost roughly 15 minutes across two attempts before the
  corpus scan moved to `GET /api/inbound/{archive}/body` over HTTP.
- **Reading `Receipt.ocr_text` alone** to feed the rule: a rendered mail body is
  a Pillow IMAGE pdf with no text layer, so `ocr_text` holds the model's `notes`
  and the body's words never arrive. It passed every helper test and would have
  shipped a rung that could not see the one document it was written for.
- **`staging / "rendered-body.pdf"`** as the carry lookup: staging writes files
  position-prefixed (`0000__rendered-body.pdf`), so an exact-name match finds
  nothing with every test still green.
- **`flyctl deploy` without `--build-arg GIT_COMMIT`**: stamps `/healthz` with
  an empty commit, so the app cannot say what it is running and the standard
  verification instrument for this app goes dead. Required a second deploy.
- **Naive caption stripping** of the untyped reference (28 of 177 carry caption
  text like `"NFC-e no 130232"`, `"DOC=145314"`): collapses the 23 working keys
  to 7 and invents a false family of seven OpenAI receipts carrying seven
  different amounts. Any alias work has to be additive.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `…/expense_recon/correspondence.py` | Added | The rung: markers, itemization guard, quarantine |
| `…/expense_recon/cli.py` | Edited | `CORRESPONDENCE` label + call in `split_non_receipt_documents` |
| `…/expense_recon/web/service.py` | Edited | Mid-month quarantine call, `text_by_digest` threaded to `_add_receipts_locked` |
| `…/expense_recon/web/intake_mail.py` | Edited | `body_text_by_digest`, set-aside reason labels |
| `…/tests/test_correspondence.py` | Added | 23 rule tests; the negatives are the contract |
| `…/tests/test_correspondence_intake.py` | Added | 6 wiring tests through the mail path |
| `…/docs/lovable-intake-receipt-view-prompt.md` | Added | Item 185 prompt |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edited | Roll-up for items 186 + the identity-set scope |

---

## Current Status

Live on `0726b428`; `/healthz` commit matches the merge, disk 76.5% free,
intake not refusing. brisken platform: unknown plan, ops unassessed.

Three PRs merged: #1257 (item 185 prompt), #1268 (item 186), #1270 (mini-
checkpoint). #1270 needed a `merge origin/main` first — a sibling landed
conflicting ledger edits while it sat in CI.

**Two live rows are wrong.** July holds Redis IUS25300 at USD 13,200.00 twice
(`0004__invoice-IUS25300.pdf` real, `0070__rendered-body.pdf` the past-due
notice), and the Hostinger pair `H_46243348` counts 172.61 twice because the
copy verdict was overridden. Both are Criss's to correct.

brisken comms-log is 16 days stale.

---

## Next Steps

1. Tell Dirk and Criss about the two July Redis rows and the Hostinger pair.
2. Build the duplicate identity set: `reference` + `invoice_number` +
   `receipt_number` + caption-stripped aliases, matched on INTERSECTION,
   strictly additive.
3. File items 185 and 186 in `p1-improvement-backlog.md` — skipped this session
   because sibling sessions were live in that file.
4. Resolve the two stale status files the sweep flagged: `p2-product-decks.md`
   (63d) and `p2-targeting.md` (64d). Update or delete; do not invent progress.
5. Run `/ops-audit brisken` — `infrastructure.yaml` has no assessed platform
   plan or ops figure for this client.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/correspondence.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/duplicates.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-intake-receipt-view-prompt.md`

### Open Questions
- Was the Hostinger "not a copy" override a slip? Two rows, one invoice,
  forwarded 25 days apart — the tool's copy verdict looks right.
- What is the safe alias rule for caption-stripped references, given that the
  naive form invents a seven-member false family?
- Does the correspondence rung need a German/Portuguese calibration set? Those
  markers carry zero hits either way in today's estate.

### Working Notes
- `reference_keys()` drops a reference that appears with two different totals,
  which is why `NQTJA4FE` is caught and `H_46243348` is not. Same-amount
  recurring charges on a stable customer reference defeat that guard by design.
- The duplicate ladder already has `printed_reference` (one page printing the
  other's number), which fired 5 times across the estate. The identity set
  should subsume it rather than sit beside it.
- Live duplicate-group tally: `reference`→copy 20, `printed_reference`→copy 5,
  `reference`→reviewer-distinct 2, `distinct_reference` 2, `vendor_date` 2.
- The published SPA now renders "Email text" on body-only intake rows, so some
  of the item-185 prompt has been applied since it was handed.

### Reference Materials
- PR #1268 body carries the full verification table.
- `docs/2026-09-24 - Recon Correspondence Not An Expense/Mini-Checkpoint-1.md`

---

## How to Continue

Read `correspondence.py` and `duplicates.py`, then build the identity set as
step 2 above. The correspondence class is out of the pool now, so a matching
number can decide on its own for the rest — which is the owner's premise, made
safe. Do not re-derive the caption-stripping experiment; it is recorded above
as a measured dead end.

---

## Strategic Feedback

### What Worked Well This Session
- Opening the two disputed documents instead of trusting their metadata. The
  date-rung recommendation was already written and would have shipped a
  regression; reading two PDFs killed it in one step.
- `regress_check.py` caught that the mail path — the one the live defect
  actually took — had no biting test, while the helper suite was fully green.

### Suggestions
- `warn-flyctl-deploy-git-commit` is advisory and its text reaches the agent
  alongside the deploy result, which is too late to prevent the blank
  `/healthz`. Promoting it to `ask` would cost one prompt and save a redeploy.

### System Health
- Three of four hook-raised friction candidates repeat rows logged EARLIER THE
  SAME DAY by sibling sessions (chained `gh pr checks` + `gh pr merge`, Python
  in heredocs). The gates fire correctly every time; what does not hold is the
  reflex between sessions, which is the signature of a structural fix that
  warns instead of blocking.
- Autonomy score: 2 human interventions (one AskUserQuestion answer on build
  order, one stop-b1-gate block on a deferral-shaped close).
