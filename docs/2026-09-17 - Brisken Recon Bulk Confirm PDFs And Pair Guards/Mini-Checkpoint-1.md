# Mini-Checkpoint: Brisken Recon Bulk Confirm PDFs And Pair Guards

**Date:** 2026-09-17
**Status:** Five voids-audit defects shipped and live on Fly v166; three owner-note prompts written; five SPA prompts wait on the owner's paste
**Type:** mini

---

## Summary
Parallel builder subagents in separate worktrees shipped audit defects 101, 96+97, 131 (+ 133's bulk half) and 112+111, each reviewed, merged on green CI, deployed and checked against the live API, the live PDF text or a cold SPA drive. Queue items 1-2 (cards-differ drive, item 106 residual) had already been closed by a sibling on origin/main.

## What Was Done
- **#101** (PR #1032, v161): "Confirm all matched" uses the pairing half of the owner's self-confirm rule (`service.confirmable_pair`); `summary.n_confirm_matched`; bulk confirm skips booked rows. Live: July 0 (the raw list held 27 booked rows), August 1. Prompt `lovable-bulk-confirm-dialog-prompt.md`.
- **#96 + #97** (PR #1035, v163): the reconciliation PDF moves workbook-booked charges out of "What needs attention" (July 72 -> 24, booked lines 30 + 18), captions use the screen's words, Why column; month report captions come from one pass, an unreadable total writes a row. Live PDF text: zero "Unmatched receipt" on both months.
- **#131 + #133 bulk half** (PR #1036, v164): a model verdict exactly at 0.20 unbinds unless the pair's rate is in the clean band; below 0.20 unchanged. "Confirm all Ready" also needs `confirmable_pair`. Replay: July review 5/3 -> 5/2, August and six bundles unchanged, scorer 76.0.
- **#112 + #111** (PR #1045, v166): an arrival owes and pays a re-match to the neighbouring month whose statement period covers it (item 113 mark, trigger `adjacent_receipts`); a receipt settling a charge takes that card's company and person on the Expenses payload, CSV and month report (`card_source: "settled_charge"`). Live: July 19 inherited rows, "NO COMPANY OR PERSON 14"; August 2. Prompt `lovable-entity-from-charge-prompt.md`.
- **Owner notes #65, #66, #68, #69** (PR #1040): prompts for items 139, 141, 142.
- Status row in `status/p1-expense-reconciliation.md`.

## What Did NOT Work (and why)
- **Playwright `locator.click` on the month page's summary pills:** only hovered the card; the section stayed on "Receipts without a charge". A JS `element.click()` on the pill button switches it (`?view=reconciled`).
- **Driving `/runs/{id}?view=reconciled` directly:** the SPA strips the param on load; click the pill, then toggle the decided-rows switch via JS.
- **#131 exception on every model rejection (first build):** replay traded NOBRE (wrong, out) for Erste Fracht at 0.10 (wrong, back in review); narrowed to the floor only.
- **#133 rule 1 (merchant must agree past one day):** moves nothing on the eight datasets; all six low-merchant exact-amount pairs are same-day, and same-day right pairs score 0.42-0.46 against a wrong 0.40.

## Current Status
Fly v166 carries everything above. Not applied in the SPA: `lovable-bulk-confirm-dialog`, `lovable-entity-from-charge`, `lovable-private-card-in-picker`, `lovable-one-download-each`, `lovable-booked-hint-names-workbook`. Open: July's company-or-person box reads 14 live against the builder's predicted 12. Siblings hold worktrees for item 132 (`agentic-ops1-item-132`), item 140 (`-item-140`), item 138's card tabs and cost-center cards (`-138-tabs`, `-138-cc`) and note #61 (`-note-61`). Brisken platform line: unknown plan, no ops data; comms-log none.

## Next Steps
1. Trace the two extra rows in July's company-or-person box (14 vs 12), read-only.
2. #103 (one receipt bound to two charges, item 72), #130 (English backend strings), #115 (corrections not recalled).
3. Owner: paste the five prompts.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 101-133, Shipped rows 63-69)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`

---

## Continuation Prompt

````markdown
/comd_resume brisken

Continue the Brisken expense-recon (p1) defect loop. Read first: `docs/2026-09-17 - Brisken Recon Bulk Confirm PDFs And Pair Guards/Mini-Checkpoint-1.md`, then in `workspace/clients/brisken/status/p1-improvement-backlog.md` items 103, 111, 115, 130, 133 (with every "Reviewer corrections" paragraph) and the Shipped table rows 63-69, then `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`, and the memories `project_brisken_expense_recon_usability_loop`, `project_brisken_expense_recon_voids_audit`, `project_brisken_recon_matching_program`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `feedback_continuation_prompt_carries_loop`, `feedback_end_iterations_with_remaining_items`.

## Where it stands

- Shipped 2026-09-17 evening in this line (all merged on green CI, deployed, verified live): #101 Confirm all matched follows the owner's pairing rule (#1032, v161; July 0 was 27 booked rows, August 1); #96 + #97 PDFs say what the screen says (#1035, v163; July to-do 72 -> 24, zero "Unmatched receipt"); #131 at-floor model rejection unbinds unless the rate is clean + #133's bulk half, Confirm all Ready needs the pairing rule (#1036, v164); #112 neighbour re-match on arrival + #111 a settled receipt takes its charge's company and person on the page, CSV and month report (#1045, v166; July 19 rows, box 14); prompts for owner notes #65/#66/#68/#69 = items 139/141/142 (#1040). Queue items "drive cards-differ" and "item 106 residual" were already closed by a sibling (PROMPT-STATUS rows for 137 and 106 are Applied; the three no-expense mails predate v157).
- Sibling sessions the same evening: 113 (v159), 138 PDFs by card (#1028, v160), 114 (v162), 105 classifier half (Shipped row 67). In flight in sibling worktrees (do not touch): item 132 (`agentic-ops1-item-132`), item 140 (`agentic-ops1-item-140`), item 138 card tabs and cost-center cards (`agentic-ops1-138-tabs`, `agentic-ops1-138-cc`), note #61 (`agentic-ops1-note-61`).
- Owner ruling: covered-class defects only until the EUR 600 licence is signed; new function is quoted separately.
- Waiting on the owner or Criss, not on you: paste `lovable-bulk-confirm-dialog-prompt.md`, `lovable-entity-from-charge-prompt.md` (without it the 19 inherited July rows show the card chip with no source line), `lovable-private-card-in-picker-prompt.md`, `lovable-one-download-each-prompt.md`, `lovable-booked-hint-names-workbook-prompt.md`, and any other Not-applied row in PROMPT-STATUS; quotes for #98, #104, #107, #109; operations #119-#128; cost-center data #118; Dirk's statement for card 9693 (#108; a 1176 PDF statement was loaded onto August on 2026-09-17); #129's UI prompt; Criss restoring the two July invoices set aside as statement pages (#105's data half).

## Queue, in order

1. **#111 box discrepancy (read-only first).** Live `GET /api/expense-batches/50622baec444`: 19 rows `card_source: "settled_charge"`, box `needs_company_or_person` 14, but the builder predicted 31 -> 12. Find the two rows (compare which receipts are chosen documents of reconciled charges but did not inherit, e.g. a review-bucket or borrowed pairing, a copy, or a row with a remembered card) and decide whether it is a defect in `settled_charge_cards` / `export_settled_cards` (`web/service.py`) or the prediction was off. Fix only if it is a defect.
2. **#103** (one receipt bound to two charges; item 72): a receipt in a pass-1 human-pick tie (`_ties` in `matching/deterministic.py`) stays free for the greedy pass. Live evidence in the entry (August Anthropic 52.59 on 52.46 vs the 50.52 pick). Matcher change: run `tools/recon-match-attribution.py` on both labelled months before and after (see `project_brisken_recon_matching_program`), never re-run refuted levers.
3. **#130**: every refused request carries a stable `code` beside the English `error`; advisories get a code; SPA prompt maps known codes to EN/PT. Covered.
4. **#115**: corrections stored but not recalled (line-read categories bypass memory; entity-less rows reach no rule; receipt-first sign-off never learns aliases/FX). Covered, effort medium.
5. **#133 rule (b)** only if you judge it worth it: demote an exact-amount pair with a disagreeing merchant to review (0.55) when a rival pair for the same receipt has a matching merchant (vendor >= 0.5 and +0.25). No pair on the eight datasets moves today.
6. Residuals: `books_as` skips the chart-of-accounts gate; the decision-route summary omits the private exclusion.

Before each item: `gh pr list -R 011matthias/agentic-ops1.01 --state open`, `git worktree list`, and a grep of recently modified transcripts in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/*.jsonl` for the item number (skip a claimed item), and read `GET /feedback.jsonl` for new notes (64 on 2026-09-17 evening, all answered but #61, which a sibling holds; a new note outranks the queue).

## How to work

- Parallel builder subagents worked well: one git worktree off origin/main per item (`client/brisken/p1-item-<N>-<slug>`), a `general-purpose` Agent per worktree in the background with a self-contained brief (hard rules below, measurement, docs, commit on the branch, do NOT push), `uv run tools/bg_watch.py watch` per builder. You review the diff of the load-bearing functions, merge origin/main (the backlog Shipped table and PROMPT-STATUS conflict almost every time: keep origin/main's rows first, renumber yours after main's highest; match rows by content, never by precomputed index), push, PR, wait for CI by head SHA, merge on green, deploy, verify. Send a builder back with SendMessage when its result trades one wrong outcome for another or leaves the screen and a document disagreeing.
- Never `git stash`. Stage explicit paths. Siblings edit the backlog all day: merge origin/main before pushing, never rebase a pushed branch. The primary clone is behind origin/main: use `( cd X && ... )` or `git -C`.
- No writes to Criss's live months; reads only. Never probe publish live. `GET /runs/{id}/expense-report.pdf` WRITES render outcomes: never fetch it live (render locally from a read-only DB copy; `reconciliation-report.pdf` is read-only). Never print or save the operator code or a token; tell every subagent the same.
- Live reads: bearer from `POST /api/login` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env`, held in memory only; `MSYS_NO_PATHCONV=1` for `/api/...` args in Git Bash. Windows Python cannot open `/c/...` paths: pass `C:\...` forms.
- Every backend fix: a route-level test through the caller, then `uv run tools/regress_check.py` with single-line literals (sources are CRLF; "no pytest summary line" means reproduce by hand with a cp backup and cp restore). Python heredocs with triple quotes are blocked: write scripts with the Write tool. Do not import a pytest fixture from another test module (CI ruff F811). Full module suite in the FOREGROUND before the PR: `uv run --extra dev --extra web pytest -q -p no:cacheprovider` (no `-n`; about 4.5 min). Deploy with `( cd <module> && flyctl deploy . -a brisken-expense-recon --remote-only )` from a clean detached origin/main worktree (pre-authorized).
- After a deploy: a live API probe of the changed field, then a cold consumer drive. Playwright `channel="chrome"` headless via `uv run` with `playwright` as an inline dependency: goto, wait 4 s, set localStorage `brisken.lang`, fill the first input with the code, Enter, wait 8 s, goto the route, wait 8 s, read `body` inner text, record non-GET requests (must be none besides login). The month page shows one section at a time: switch with a JS click on the summary pill button (`[...document.querySelectorAll('button.rounded-lg.border.px-3.py-2')]`, the last one is Matched) and show decided rows with a JS click on `button[role=switch]`; a Playwright `locator.click` on the pill does not switch it, and a `?view=` param in the URL is stripped on load. agent-browser hung on 2026-09-17.
- In the same PR, update the backlog item's heading/status and its Shipped row. SPA work goes out as a Lovable prompt in the reply inside a FOUR-backtick fence ("Do NOT add Supabase or any database", EN + PT-BR strings, a checking list), saved as `docs/lovable-<slug>-prompt.md` with a Not-applied PROMPT-STATUS row. Verify an applied prompt by bundle field names, then a drive.

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
