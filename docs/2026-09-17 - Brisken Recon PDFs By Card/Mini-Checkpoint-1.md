# Mini-Checkpoint: Brisken Recon PDFs By Card

**Date:** 2026-09-17
**Status:** item 138 shipped and live (PR #1028, Fly v160); items 137 and 106 Lovable prompts applied and verified; five new feedback notes (#65-#69) open
**Type:** mini

---

## Summary
Backlog item 138 went end to end: both expense-recon PDFs are organized by card, deployed, and proven by downloading the live August reconciliation report through the SPA from a cold login. The owner pasted the two pending Lovable prompts mid-session; both verified.

## What Was Done
- **Shared infra** (`output/_pdf_common.py`): `card_sections(view, receipt_cards)` (charges on `rows[].coverage_key`, a held receipt follows its charge's card, an unheld one the card item 137 resolved via `service.report_receipt_cards`, a last never-dropped "No card" section), `card_statement_line(section)` used by both documents, `caption_mark` + `stitch(..., caption_pages)` so receipt pages sit behind their own card section (mismatched marks append, never misfile). `service.report_view` wraps `build_view` over the live pool.
- **Reconciliation report**: per card its statement line + receipt count, "What needs attention" for that card (unmatched charges, receipts with no charge, open duplicate groups by first member), copies set aside, charges (status "matched, cards differ" plus a named line), then its receipt pages; the caption of a cards-differ receipt names its own card. Flat document unless two or more CARD sections.
- **Month report** (background builder agent, separate worktree, merged): card sections through the existing `sections` mechanism with `detail`/`notes`, `receipts_by_section` interleaving; cost-center and trip sectioning untouched.
- **Found and fixed**: `build_reconciliation_report` never passed `field_overrides` to `build_view`, so a reviewer's card pick never reached the document and `cards_differ` could not print.
- **Verification**: route-level `test_reconciliation_report_by_card_item_138.py` (3) + `test_expense_report_by_card_item_138.py` (7), regress_check red on all five wires; full suite 2179 passed / 2 skipped before the final origin/main merge, CI green (both workflows) on the merged head; real August rendered locally from a read-only DB copy (73 and 68 pages; month-report header unchanged: 20 expenses, EUR 668.00, USD 2,033.86); after deploy, the SPA's "Download reconciliation (PDF)" from a cold login returned the identical 73-page document (sections 3645, 3876, 2838, 1176, 9693, No card; cards differ on p4). Only non-GET in every drive: `POST /api/login`. DB copy and extracts deleted from the scratchpad.
- **Lovable prompts** (owner pasted): 137 bundle + cold drive (August LOVABLE 2026-08-05, one chip "Card 3645 charge, receipt on card 2838", picked-by-hand tip, PT string; visible only under Matched, "Show 2 decided rows"); 106 bundle + cold drive (`/inbound` "Nothing added: 3" amber badge + three amber rows = API `n_no_expense` 3). PROMPT-STATUS "Not applied" is empty.
- Backlog item 138 heading + Shipped row 62 (sibling item 113 took 61), headings 137/106 "SPA APPLIED", p1 status rows.

## What Did NOT Work (and why)
- **Sectioning whenever there were two sections (one card + No card):** full suite 3 failures; a one-card month with one no-card receipt lost the flat document the one-card tests pin on purpose. Rule is now two or more card sections, in both PDFs.
- **`flyctl ssh sftp get` with target `"$S\\$f"` in a loop:** the documented quoting trap again (file landed as `scratchpad$f`, second refused). Single-quoted literal Windows target works.
- **Finding the 137 chip right after load:** the LOVABLE row is decided (hidden until Matched, "Show 2 decided rows") and a first-visit "Leave feedback anywhere" dialog blocks Playwright clicks until "Got it"; JS `click()` works.
- **`report_view` without `field_overrides`:** no `cards_differ` in the document; the route test only passed after forwarding it.

## Current Status
Fly v160 carries item 138 (v159 was a sibling's, included). Brisken platform line: unknown plan, no ops data. No friction candidates. Stale status files flagged by `pre` are p2 (`p2-product-decks.md` 56d, `p2-targeting.md` 57d), outside this session's scope. Five feedback notes arrived 15:13-15:19 UTC while item 138 was building; they are the next queue.

## Next Steps
1. Feedback notes #65-#69, per the continuation prompt below.
2. Owner calls recorded on item 138: nest card sections inside cost centers once cost centers exist; the months-page per-card tabs Criss asked for (build now or quote under the licence).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 138 shipped notes, the months-page paragraph)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`

## Continuation Prompt
Delivered in chat 2026-09-17; the same text:

````markdown
/comd_resume brisken

Continue the Brisken expense-recon (p1) loop where the 2026-09-17 item-138 session stopped. Read first: `docs/2026-09-17 - Brisken Recon PDFs By Card/Mini-Checkpoint-1.md`, then backlog items 138 and 137 in `workspace/clients/brisken/status/p1-improvement-backlog.md`, `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`, and the memories `project_brisken_expense_recon_usability_loop`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `project_brisken_expense_recon_testing_loop`, `feedback_continuation_prompt_carries_loop`.

## Where it stands

- Shipped this session: **item 138 (PR #1028, merge 99d2853e, Fly v160)**. Both PDFs are organized by card once a month has two or more cards: per card one shared line (`_pdf_common.card_statement_line`: statement or "not recorded", period, charges, matched, unreconciled, booked without a receipt), its exceptions, its charges or expenses, then its receipt pages (`caption_mark` + `stitch(..., caption_pages)`); a last "No card" section is never dropped; cost-center and trip sectioning unchanged. `service.report_view` now forwards `field_overrides`, so `cards_differ` reaches the document. Live proof: the SPA download of August's reconciliation report after a cold login, 73 pages, sections 3645/3876/2838/1176/9693/No card, cards differ on p4. The month report cannot be fetched live (it writes render outcomes, item 67); it was proven by a local render from a read-only DB copy (68 pages, header unchanged).
- Lovable prompts: item 137 (`lovable-cards-differ-prompt.md`) and item 106 (`lovable-no-expense-mail-prompt.md`) APPLIED and verified cold this session. Nothing is waiting to be pasted.
- Owner ruling still standing: covered-class defects only until the EUR 600 licence is signed. No new functions without a build-or-quote answer.
- Waiting on the owner or Criss, not on you: #61 (GL account codes, item 23), Criss restoring the two July invoices set aside as statement pages (AWS USD 3,352.59, Tricarico BRL 27,203), "refresh master data" on June, the Pressmaster FZCO 96.00 line category, a yes for `intake.alert_recipients`, Criss's own call on her August card picks (LOVABLE 25.00 now shows "cards differ"), whether card sections nest inside cost centers once cost centers exist, and build-or-quote for the months-page tabs per card Criss asked for (item 138's last paragraph).

## Queue, in order

Five feedback notes arrived 2026-09-17 15:13-15:19 UTC (operator login, July month `50622baec444`), after the notes #1-#64 baseline. Read each in `GET /feedback.jsonl` (lines 65-69: `comment`, `anchor`, `selector`, `page`) before acting; confirm what the named element renders today with a cold drive, then classify under the licence (defect covered, or new function to put to the owner).

1. **Notes #65 + #66 (`/expenses/50622baec444`, anchor "Leave blank (resolve from card) / Pick the card that paid" and "Paid with a private card"):** "no 'paid with a private card' function" then "I need this 'paid with private card' button as one of the options in the 'pick the card that paid' dropdown. preserves space". The backend already carries the function (`expenses[].can_mark_private`, the `private` + `reimburse_to` field overrides, refusals `company_card` / `private_card`, PR #987; SPA prompt `lovable-private-card-prompt.md` applied). Likely an SPA-only move of the button into the card picker as an option, gated by `can_mark_private`: a Lovable prompt. Check first why #65 says there is no such function on the row she was looking at (a company-card row where `can_mark_private` is false would hide it by design).
2. **Note #68 (`/runs/50622baec444`, anchor "Downloads / Report / Reconciled CSV / Statement"):** "we do not need more than one button to download the different output files, make sure there is only one button for each output file download." The workbench header already has "Download reconciliation (PDF)", "Report", "Reconciled CSV" beside a Downloads group (seen on August 2026-09-17). Enumerate every download control on both month pages (Matching and Expenses), map each to its route, and write one Lovable prompt that keeps exactly one control per file. Never fetch `expense-report.pdf` live to test it.
3. **Note #69 (`/runs/50622baec444`, anchor "This charge is marked yellow in your statement workbook, so it is already booked. Nothing…"):** "where do you get this information from?" Answer from code: the fill colour Criss put on the statement workbook row (`entry_status == "posted"`, the xlsx fill-colour path). Find where the sentence is produced (SPA string or backend reason), and if it does not name the file and row, make it say which workbook and row it read the colour from (a covered explanation defect). Reply to the question in the closing summary so the owner can pass it on.
4. **Note #67 (`/expenses/50622baec444`, anchor "Aposto Karlsruhe"):** "if this is a potential duplicate, the tool needs to show all the available data to each of the duplicates next to each other for manual comparison. Just labeling it is not going to cut it..." This reads as new presentation (a side-by-side compare). Check what the row and "Show N groups" show today for Aposto Karlsruhe; if nothing on screen lets her see the other copy, the missing link is a defect; the full side-by-side view is a build-or-quote question for the owner.

When the queue is empty and no newer note is open, follow SESSION LOOP step 9.

Before each item: `gh pr list -R 011matthias/agentic-ops1.01 --state open` and `git worktree list` for a sibling claim (skip a claimed item), and re-read `GET /feedback.jsonl` for newer notes (69 notes at this stop).

## How to work

- One git worktree off origin/main per item, branch `client/brisken/p1-item-<N>-<slug>` (or `p1-notes-<range>` for a note batch). Never `git stash`. Stage explicit paths. Siblings edit the backlog all day and take Shipped row numbers (row 62 was the last): merge origin/main before pushing and again before merging, renumber on conflict, never rebase a pushed branch.
- No writes to Criss's live months; reads only. `GET /runs/{id}/expense-report.pdf` WRITES render outcomes to the run (item 67), so never fetch it live; `reconciliation-report.pdf` is read-only. If a fix needs a live data action, name it and stop.
- Live API: bearer from `POST https://api.expenses.brisken.com/api/login` with the operator code (memory `project_brisken_expense_recon_review_surface`). Months list `GET /api/expense-batches`; readiness `GET /api/runs/{id}` `.summary`. Windows Python cannot open `/c/...` paths: pass `C:\...` forms.
- A read-only live DB copy: `flyctl ssh console --pty=false -C "sh -c 'python3 -c ...sqlite3 backup to /tmp...'"`, then `MSYS_NO_PATHCONV=1 flyctl ssh sftp get -a brisken-expense-recon /tmp/<f> 'C:\...\scratchpad\<f>'` with a single-quoted literal target (never `"$S\\$f"`), then delete the `/tmp` copies. The DB's `runs.work_dir` is `/data/runs/<id>`: rewrite it in the LOCAL copy to render documents locally. Delete the copy when done.
- Every backend fix: a route-level test through the caller, then `uv run tools/regress_check.py --test "<cmd>" --cwd <module dir> --file <src> --replace <wire> --with <disabled>` (watch it go red). Python heredocs containing triple quotes are blocked by a hook: write scripts with the Write tool. Do not import a pytest fixture from another test module (CI ruff F811); plain helpers are fine. Ruff: `uv run --no-project --with ruff ruff check src tests` from the module dir. Full module suite before the PR (about 4 minutes, 2,179+ tests, no `-n`); CI also runs it (`expense-recon-tests.yml`). Commit, push and open the PR autonomously; wait for CI with `gh run list --branch <b>` filtered by head SHA, merge on green, then `flyctl deploy . -a brisken-expense-recon --remote-only` from a clean detached origin/main worktree (pre-authorized). After the deploy: a live API probe of the changed field and a cold browser read-back.
- Cold browser drives: headless Playwright with `channel="chrome"` (`uv run --no-project --with playwright python <script>`) works in about 20 s; agent-browser has hung before. Log in by filling the gate's input and pressing Enter, wait for localStorage `erc-token`, set `brisken.lang` to `en`/`pt`. Dismiss the first-visit "Leave feedback anywhere" dialog ("Got it") and use JS `click()`; decided rows are hidden until "Show N decided rows". Record every non-GET request and assert it is only the login.
- A Lovable prompt is verified by a bundle audit (fetch every `/assets/*.js` from `https://expenses.brisken.com`, confirm the decisive field and i18n key names plus the controls `ready_to_post` and `coverage`) and a cold drive of the named row; then move its PROMPT-STATUS row to Applied.
- In the same PR, update the backlog item's heading/status and add its Shipped row. SPA work goes out as a Lovable prompt in the reply inside a FOUR-backtick fence with EN + PT-BR strings and a "checking it landed" list, saved as `docs/lovable-<slug>-prompt.md` with a Not-applied row in `docs/PROMPT-STATUS.md`.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````
