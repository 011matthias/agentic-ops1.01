# Mini-Checkpoint: Brisken Recon Note 64 And Card Separation Items

**Date:** 2026-09-17
**Status:** item 102 shipped (PR #1007, Fly v154), SPA prompt pending paste; items 137 and 138 queued; stopped at 350k own context
**Type:** mini

---

## Summary
Mini-Checkpoint-1 stopped on a sibling session's pressure reading; this session's own context was 307k, so work resumed and item 102 shipped end to end. Items 137 and 138 each need an estimated 150-250k and would cross 500k from 350k, so the loop stopped again with the continuation prompt below.

## What Was Done
- **Pressure instrument corrected:** `tools/session_state.py --status` printed `session=4310562e` (474k), then `b5b01897` (495k); this session is `043738ec`, and its own transcript read 307k, matching the per-session `[PRESSURE: MODERATE] ~305k` advisory. The SESSION LOOP's step 1 now measures the session's own transcript; memory `feedback_continuation_prompt_carries_loop` carries the trap.
- **Item 102 (PR #1007, merge dbcb8bac, Fly v154):** `summary.n_booked_no_receipt` + `summary.booked_no_receipt_by_ccy` on `GET /api/runs/{id}` count posted (yellow) charges whose `effective_bucket` is `unmatched`, beside `unreconciled_by_ccy` and never inside it. Route-level `tests/test_booked_without_receipt.py` (3); regress_check red 2 of 3 under mutation, green restored; full suite 2109 passed / 2 skipped. Live after deploy: July 48 / USD 3,457.11 (the audit's 47 / 3,385.47 plus 1 row whose receipt another charge holds), August 0 / `{}`, both `unreconciled_by_ccy` unchanged. Cold Chrome drive of `/runs/50622baec444`: "USD 1,054.48 still open" renders as before, only non-GET `POST /api/login`. API contract rows, backlog item 102 + Shipped row 58, `docs/lovable-booked-no-receipt-prompt.md` with a Not-applied PROMPT-STATUS row.

## What Did NOT Work (and why)
- **Stopping on `session_state.py --status`:** it reports the most recently active session on the machine, not this one (474k sibling reading vs 307k own); fixed in the SESSION LOOP.
- **Python heredoc with a triple-quoted string to write the item 102 docs:** blocked by the heredoc hook ("HEREDOC CONTAINS A PYTHON TRIPLE-QUOTED BLOCK"); wrote the prompt with the Write tool and the edits as a script file.
- **`uv run ruff` in the module directory:** "Failed to spawn: ruff" (not in the module env); `uvx ruff check` worked.

## Current Status
Fly v154 carries item 102. Its SPA half waits on the owner's paste, as do the item 94/99/100 prompts (PR #1004). Queue: 137 -> 138. Brisken platform line: unknown plan, no ops data. The friction candidate `pre` listed (`gate-fired-red-merge`, PR #1009) belongs to a sibling session and was left in place.

## Next Steps
1. Item 137 (resolved card scopes matching), then item 138 (per-card PDFs), per the continuation prompt.
2. After the owner publishes `lovable-booked-no-receipt-prompt.md`: bundle audit `wb.status.bookedNoReceipt`, cold drive July's status line, PROMPT-STATUS row to Applied.
3. Owner/Criss items unchanged from Mini-Checkpoint-1.

## Files to Read First
- `docs/2026-09-17 - Brisken Recon Note 64 And Card Separation Items/Mini-Checkpoint-1.md` (items 137/138 evidence)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 137, 138)

## Continuation Prompt
Delivered in chat 2026-09-17; the same text:

````markdown
/comd_resume brisken

Continue the Brisken expense-recon (p1) defect loop exactly where the 2026-09-17 session stopped. Read first: `docs/2026-09-17 - Brisken Recon Note 64 And Card Separation Items/Mini-Checkpoint-2.md`, then backlog items 137 and 138 in `workspace/clients/brisken/status/p1-improvement-backlog.md`, and the memories `project_brisken_expense_recon_usability_loop`, `project_brisken_recon_matching_program`, `project_brisken_expense_recon_testing_loop`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `feedback_continuation_prompt_carries_loop`.

## Where it stands

- Shipped on 2026-09-17 in this line of work: the note #64 per-line category picker applied and verified (PR #995); backlog items 137 and 138 written from the owner's report (PR #1002); item 102 backend (PR #1007, Fly v154): `summary.n_booked_no_receipt` + `summary.booked_no_receipt_by_ccy` on `GET /api/runs/{id}`, live July 48 rows / USD 3,457.11, August 0. Its SPA half `docs/lovable-booked-no-receipt-prompt.md` is NOT applied (the owner pastes it; once published, bundle-audit `wb.status.bookedNoReceipt` and drive July's status line cold, then move its PROMPT-STATUS row to Applied).
- Feedback notes #1-#64 are answered except #61 (parked on item 23; the question is with the owner).
- Siblings shipped items 94, 95, 116, 99 and 100 the same day; item 117 was in PR #1003 and item 121 in PR #1001 at the stop. Re-check before assuming.
- Owner ruling: covered-class defects only until the EUR 600 licence is signed. No new functions.
- Waiting on the owner or Criss, not on you: #61 (does Brisken still want GL account codes), Criss restoring the two July invoices set aside as statement pages (AWS USD 3,352.59, Tricarico BRL 27,203), "refresh master data" on June, the Pressmaster FZCO 96.00 line category, a yes for `intake.alert_recipients`, pasting the pending Lovable prompts (items 94/99/100 from PR #1004, item 102).

## Queue, in order

1. **Item 137: receipts are matched across cards.** `match_month` scopes a receipt only when its own `payment_mode` prints a card present on the statement (`receipt_card_scope`, `pair_in_scope` in `matching/deterministic.py`). The card the tool resolved (Settings hint, hand pick, learned; `resolve_batch_row_cards` in `web/service.py`) never scopes; item 135's `hand_picked_card_mode` only covers a pick that contradicts a printed card. Build: the resolved card scopes candidates. A hand pick (`card_source == "override"`) scopes hard. A hint or learned card that disagrees with the charge's card (`coverage_key` / `_tx_card_keys`) demotes the pair to review with a "the cards differ" reason and never silently drops a real match. A confirmed pair whose cards disagree gets a flag in the month payload. Live case to re-read: August LOVABLE 25.00 on card 3645 (2026-08-05), confirmed with `0027__Invoice-HMVWDWIL-0028.pdf` whose card override is 2838. Measured 2026-09-17: July 19 of 52 receipts card-scoped, 33 with no card compete across four cards; August 10 of 25 scoped, 11 card-known-but-unscoped (9 override, 2 hint), 4 no card. Measure the before on a fresh DB copy (July and August right/wrong counts, the six-bundle score, 70/95 at last measure) per `project_brisken_recon_matching_program`, and report the cost next to the gain (pairs that stop matching). The attribution tool imports the matcher's rules; keep it importing them.
2. **Item 138: the PDFs are not organized by card.** `expense-report.pdf` (`build_expense_report`, `output/month_report_pdf.py`: flat listing, cost-center sections only, registry empty live) and `reconciliation-report.pdf` (`output/reconciliation_report_pdf.py`: per card only in the coverage table and the charge listing; header totals, the exceptions lists and the receipt pages are not) get one per-card structure: per card its charges with their receipts, its exceptions, its total and unreconciled figure (and item 102's booked-without-receipt figure), then its receipt pages; a last, never-dropped section for receipts with no card and charges no coverage entry claims. Charges group on `coverage_key`, receipts on item 137's resolved card. Where the cost-center partition goes is the owner's call; leave it as today.

Before each item: `gh pr list -R 011matthias/agentic-ops1.01 --state open` and `git worktree list` for a sibling claim (skip a claimed item), and read `GET /feedback.jsonl` for new notes (a new Criss note outranks the queue).

## How to work

- One git worktree off origin/main per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog all day: merge origin/main before pushing, never rebase a pushed branch.
- No writes to Criss's live months; reads only. `GET /runs/{id}/expense-report.pdf` WRITES render outcomes to the run (item 67), so never fetch it live; `reconciliation-report.pdf` is read-only. If a fix needs a live data action, name it and stop.
- Match live data exactly (no substring card checks). Python DNS to api.expenses.brisken.com failed intermittently on 2026-09-17 while curl worked (bearer from `POST /api/login`, code in memory `project_brisken_expense_recon_review_surface`). The months list is `GET /api/expense-batches`; readiness is `GET /api/runs/{id}` `.summary`.
- Every backend fix: a route-level test through the caller, then `uv run tools/regress_check.py` (disable the fix, watch it go red; "no pytest summary line" means reproduce by hand with a cp backup and cp restore). Python heredocs containing triple quotes are blocked by a hook: write the script with the Write tool and run the file. Full module suite before the PR (about 4 min, 2,109 tests at v154, no `-n`). Commit, push and open the PR autonomously, merge on CI green, then `flyctl deploy . -a brisken-expense-recon --remote-only` from a clean detached origin/main worktree (pre-authorized). After the deploy: a live API probe of the changed field and a real-Chrome read-back from a cold login (`agent-browser --session <name> --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe" open <url>` in the background, then `get url` / `snapshot` / `eval` in the foreground; a Radix Select opens with focus + `press ArrowDown`).
- In the same PR, update the backlog item's heading/status and add its Shipped row (row 58 was the last). SPA work goes out as a Lovable prompt in the reply inside a FOUR-backtick fence with EN + PT-BR strings and a "checking it landed" list, saved as `docs/lovable-<slug>-prompt.md` with a Not-applied row in `docs/PROMPT-STATUS.md`.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement or a two-builder PDF restructure costs far more (budget 150-250k). Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. At critical (700k): stop right after step 4's commit and push, then do steps 5 and 6.
8. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````
