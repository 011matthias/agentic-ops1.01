# Mini-Checkpoint: Brisken P1 Item 195 And Attach Leftovers

**Date:** 2026-09-25
**Status:** loop queue empty; both items live on Fly `5bbb0ac2`
**Type:** mini

---

## Summary
Item 195 (a re-read re-stamping a PDF's charges as company "card") and the three items 196/197 outage leftovers shipped, deployed and were driven cold. This loop's queue is empty, and no feedback note is open (86 notes; #86 is already cited).

## What Was Done
- **Item 195, PR #1355 (Shipped row 121).** Two of the backlog's premises were wrong. The live PDFs WERE filed under an account: the SPA always sends the chosen card's key, and August's 1176 file sits on Consulting and its 9693 file on Cloud Services. What got lost was the record: a PDF's config block has no `account_id`, so both entries hold `""`. The worse shape was a PDF borrowing `config.statement`'s account, so it re-read under the LAST upload's company (Corporate Services when a workbook came later), not "card". Fix in `web/service.py`: `statement_entry_account` records a PDF's filed-under account; the re-read never lends a PDF the config's account; `pdf_entity_from_printed_cards` gives a PDF with no account the company its printed cards resolve to (blank on two companies or an unnamed card), at attach and re-read alike. `statement_period_overlap` no longer calls two unrecorded accounts "the same account" (leftover 3). Tests: 9 in `tests/test_reread_pdf_entity_item_195.py` (8 red on origin/main); four wires proven RED under `regress_check`.
- **Leftovers 1 + 2, PR #1357 (Shipped row 122).** `GET /api/inbound/log` stops presenting `error` on an `ingested` row (read-side; the archive keeps the 429 text), which was 1 of 146 live rows, `20260924T162158-0f4f64aa`. `service.discard_unrecorded_upload`, called from `app._run_attach_statement_job`'s failure path, removes a dead attach's file so the retry keeps its name, and never removes a file `statements[]` names. Tests: 6 in `tests/test_attach_leftovers_196_197.py` (3 red on origin/main, including a reproduced `statement-2.csv`); three wires proven RED.
- **Deploy and verification.** A sibling's v227 (`071b19d7`) already carried #1355. I deployed `5bbb0ac2` for #1357; `/healthz` confirms it. A row-by-row snapshot diff over all 7 months showed 0 changes from item 195. After #1357 it showed 136 changes, all attributed to the sibling's item 205 GL conversion: `posting_category` on July/August expenses plus `n_unmapped_accounts`, with 0 changes to charge entities or `statements[]`. The live inbound log now shows 127 ingested rows, none carrying an error. Scripted agent-browser drive, cold from the login gate: `/inbound` renders the recovered mail as "Added" with no 429 text, and August renders "Consulting from card · Chase Visa - 1176" and "Cloud Services from card · Chase Visa - 9693".

## What Did NOT Work (and why)
- **Advisory test with non-overlapping periods:** the first two-PDF advisory test passed on origin/main because its cycles did not overlap, so it could not bite. Rewritten with an overlapping 9693 cycle, plus an assertion on the overlap.
- **Tailing the CI merge loop's output file:** I launched the loop piped through `tail -15`, so its `.output` stayed empty until exit and gave no progress (the pattern rule `warn-tail-task-output-file` fired). Later loops ran unpiped.
- **agent-browser default open:** hung at 300 s and was stopped. `--session <name> --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe"` opened in seconds.

## Current Status
Live: item 195 plus the three leftovers on Fly `5bbb0ac2`. August's two PDF entries still read `account_id: ""`, and the 9693 entry keeps its old "same account" advisory. Both correct themselves at the month's next re-read, which is Criss's to trigger and is not triggered here. Nothing waits on the owner. Waits on Dirk: the 0113 (Apple Card) statement export. Waits on Criss: nothing new. Sibling-owned: item 196's decision (land deterministic rows when the model is down), 201/202, the item 205 GL conversion in progress, and the private-card-list fold.

## Next Steps
1. None in this loop: the queue is empty and no feedback note is open (step 9 of the SESSION LOOP: no new continuation prompt).
2. When Dirk sends the 0113 export: parse it locally first (`parse_statement_pdf_tolerant`) to predict rows and pairs, then attach and diff.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 195 resolution; item 196 "Both leftovers FIXED"; Shipped rows 121-122)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("A PDF entry's `account_id`..." and the inbound-log paragraphs)
