# Mini-Checkpoint: Recon Correspondence Not An Expense

**Date:** 2026-09-24
**Status:** Item 186 shipped, deployed (Fly, commit `0726b428`), cold-driven. Item 185 prompt filed, unpasted.
**Type:** mini

---

## Summary

Owner asked for a view-receipt control on the Email intake page and then for
better duplicate recognition, on the premise that two different invoices never
share an ID. Measuring that premise against all seven live months found the
class it cannot cover: a document that QUOTES an invoice's identity. July 2026
carries a Redis dunning notice booked as a second USD 13,200.00 expense, about
42% of the month's USD total.

## What Was Done

- **Item 185 prompt** (`docs/lovable-intake-receipt-view-prompt.md`, PR #1257):
  open a receipt from the Email intake page. The viewer is already published
  (item 178); this is wiring. Measured first: 72 of 143 mails render `-` in the
  Files column and 61 of those did produce a receipt, because the cell reads
  `files` (attachment names) and a body-only mail has none. Pasteable text was
  handed in-session. A later cold drive shows the published SPA now renders
  "Email text" on those rows, so some or all of it has been applied.
- **Item 186 shipped** (PR #1268, merge `0726b428`, Fly deploy verified):
  `correspondence.py` quarantines a payment reminder / past-due notice so it
  never becomes an expense. Two signals required (dunning marker AND no
  itemization); `NON_RECEIPT_LABELS` carries the exclusion the statement rung
  already uses; the extractor's prompt is untouched (item 105's reason).
- Markers calibrated over 103 readable mail bodies of 143 archives: fires on 2,
  both Redis, nothing else. `remittance`, `balance due` and `amount due` were
  measured and rejected.
- 29 tests. All three wiring points regress-checked RED-when-disabled. Full
  module suite 3205 passed / 2 skipped; accuracy gate unchanged (composite 6.9).

## What Did NOT Work (and why)

- **A date-agreement rung on the duplicate key** (my first recommendation, and
  it was wrong): 21 of 23 repeated reference keys have a 0-day spread, so
  "same number, dates far apart = not a copy" looked clean. Reading the two
  documents killed it. Hostinger `H_46243348` is 25 days apart and IS one
  invoice forwarded twice; the rung would have broken the case it was meant to
  fix while leaving the Redis case wrong in the other direction.
- **`flyctl ssh console -C` with a piped payload** (`echo <b64> | base64 -d |
  python3`) hangs at "Connecting to fdaa:…" and never returns, at both 4.2 KB
  and 1.7 KB. The same wrapper with a short non-piped command works. The
  corpus scan was moved to `GET /api/inbound/{archive}/body` over HTTP instead,
  which is the population that matters anyway.
- **Reading `Receipt.ocr_text` alone** to feed the rule: a rendered mail body
  is a Pillow IMAGE pdf with no text layer, so `ocr_text` holds the model's
  `notes` and the body's words never arrive. It passed every helper test and
  would have missed the exact document the change was written for. Fixed by
  `intake_mail.body_text_by_digest`, which carries the body in for the rendered
  body ONLY (an attachment keeps its own text — a reminder mail legitimately
  attaches the real invoice).
- **`staging / "rendered-body.pdf"`** as the lookup: staging writes files
  position-prefixed (`0000__rendered-body.pdf`), so an exact-name match would
  have found nothing with every test still green. Caught by reading the staging
  writer, now pinned by a test.
- **`flyctl deploy` without `--build-arg GIT_COMMIT`**: stamps `/healthz` with
  an empty commit, so the app cannot say what it is running. Caught by the
  pattern-rule hook; redeployed with the arg and verified the commit matches.

## Current Status

Live app on `0726b428`, `/healthz` commit matches the merge, disk 76.5% free,
intake not refusing. Cold Playwright drive (fresh context, no session, headless
Chrome — the MCP CDP path is pinned to the user's busy Edge and times out)
signed in and read the Email intake page back with real rows.

**Two live rows are wrong and are Criss's to correct, not the agent's:**
July's two Redis rows at USD 13,200.00 each (`0004__invoice-IUS25300.pdf` is
the real invoice; `0070__rendered-body.pdf` is the past-due notice), and the
Hostinger pair `H_46243348` at 172.61 USD twice, where the copy verdict was
overridden but the two are one forwarded invoice.

brisken platform: unknown plan, ops unassessed.

## Next Steps

1. Tell Dirk/Criss about the two July Redis rows and the Hostinger pair; the
   code change stops the next one, it does not rewrite her month.
2. Build the duplicate identity set now that correspondence is out of the way:
   reference + `invoice_number` + `receipt_number` + caption-stripped aliases,
   matched on INTERSECTION. Additive only — naive caption stripping collapsed
   23 working keys to 7 and invented a false family of seven OpenAI receipts.
3. File items 185 and 186 in `p1-improvement-backlog.md` (skipped this session:
   sibling sessions were live in that file).
4. Paste `docs/lovable-intake-receipt-view-prompt.md` if the Files column still
   lacks per-file open controls after the partial application.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/correspondence.py`
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_correspondence_intake.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-intake-receipt-view-prompt.md`
