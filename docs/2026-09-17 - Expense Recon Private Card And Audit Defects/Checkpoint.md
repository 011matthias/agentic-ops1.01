# Checkpoint: Expense Recon Private Card And Audit Defects

**Date:** 2026-09-17
**Status:** Private card option and audit defects 94/95/99/100/116 shipped and live (Fly v149-v158); one SPA prompt (item 106) waits on the owner's paste; the loop continues on the remaining covered defects

---

## Summary
A receipt on a card that is not in Settings can now be booked as paid with a private card, which makes the person eligible for reimbursement. Five voids-audit defects shipped behind it, all under the owner's rulings: ready means complete, publish is a gate only, and decided copies leave every count and total. Gray "já no recurring" charges now close the receipt requirement (owner ruling), and #109 is recorded as quote-separately.

---

## What Was Done This Session

### Private card (owner request)
1. PR #987 (Fly v149): `expenses[].can_mark_private`, refusals `company_card` / `private_card` on `POST .../private` and both PUT paths via `app._paid_by_conflict`; `resolve_batch_row_cards` computes `private` before card memory, so a remembered card no longer hides the option. Lovable prompt handed, published by the owner, verified (PR #990).

### Voids-audit defects (licence-covered)
1. **#95 + #116** (PR #993, v151): gated rows keep their category in the Zoho export; sign-off keeps merchant keys and cost centers.
2. **#99 + #100** (PR #997, v152): `summary.month_complete` plus the `n_charges_need_receipt` / `n_receipts_need_charge` / `n_charges_category_guessed` counts; publish returns 400 `month_not_complete` / `no_statement` / `not_a_month` unless `{"override": true}`, recording `published_at` / `published_by` / `published_override`.
3. **#94** (PR #998 v152, PR #1009 v155): one `decided_copies` predicate; `counts_in_total: false`, `n_copies_set_aside`, `copies_set_aside_by_ccy`; the box counts exclude copies too.
4. **Gray ruling** (PR #1020, v158): hosted `entry_status: "subscription"` counts as closed (`n_charges_closed_recurring`); `entry_status_source: "derived"` closes nothing.
5. Backlog records: #109 quote-separately and Criss's by-card months page idea on item 138 (PR #1015); prompts pending (PR #1004), then applied and driven (PR #1022).

### Verification
1. Route-level tests through each caller, `regress_check` red on each wire, full module suite before each PR, CI green before every merge.
2. Cold Playwright drives on v158: July "Not complete · 11 receipts have no charge" + "Nothing left to decide" + "USD 3,457.11 booked without a receipt (48 charges)"; August "Not complete · 8 rows to decide · 61 charges still need a receipt · 10 receipts have no charge"; August expenses "5 set aside as copies"; `/classic` lands on `/months`. No non-GET requests.
3. Prompt audit at close: the cards-differ keys (`cards_differ`, `wb.cardsDiffer`, `wb.cardsDiffer.tip.override`) are in the live bundle; item 106's (`n_no_expense`, `not_added`, `mail.noExpense.badge`) are not.

---

## Key Decisions Made

### Ready means complete (#99)
- **Choice:** `ready_to_post` stays as it was; a separate `month_complete` drives the badge and the publish gate.
- **Rationale:** a month with charges missing receipts is not done, even when no row is left to decide.

### Publish is a gate, not a snapshot (#100)
- **Choice:** refuse publish on an incomplete month unless overridden, record who published and whether it was an override; no frozen copy.
- **Rationale:** owner ruling; a frozen copy is new function outside the licence.

### Copies out everywhere (#94)
- **Choice:** decided copies leave totals, tiles and box counts, shown only as "N set aside as copies".
- **Rationale:** owner ruling; two figures for one purchase was the defect.

### Gray recurring closes; #109 quoted
- **Choice:** Criss's gray fills (`subscription`) close the receipt requirement; #109 (category learning for receiptless charges) is quoted separately.
- **Rationale:** owner rulings 1-2, 2026-09-17.

---

## What Did NOT Work (and why)
- **agent-browser for the consumer drive:** hung with no output and had to be stopped; Playwright `channel="chrome"` worked.
- **Playwright drive that fills the code immediately after goto:** timed out; the login needs about 4 s before the code input accepts, then about 8 s after Enter.
- **`pytest -n auto`:** xdist is not installed in the module env; run serially.
- **Multi-line `regress_check --replace` literals:** matched 0 times because the sources are CRLF; single-line literals work, and "no pytest summary line" is reproduced by hand.
- **Deleting doc rows by precomputed line indices (PR #1022):** indices shifted after the first deletion and removed the wrong line; content matching fixed it.
- **Background builder agents running the suite in the background:** they ended their turns before the result; resumed via SendMessage with a foreground instruction.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/web/service.py` | Edit | private option, card memory order, copies predicate, readiness counts |
| `.../expense-reconciliation/src/expense_recon/web/app.py` | Edit | `_paid_by_conflict`, publish gate |
| `.../expense-reconciliation/src/expense_recon/web/month_readiness.py` | New | `month_complete` and its counts |
| `.../expense-reconciliation/src/expense_recon/output/zoho_expense_export.py`, `coa_gate.py` | Edit | #95/#116 |
| `.../expense-reconciliation/tests/test_private_expense.py`, `test_month_complete_publish_gate.py`, `test_copies_out_of_totals.py`, `test_cost_center_totals.py` | New/Edit | route-level proofs |
| `.../expense-reconciliation/docs/api-contract.md`, `docs/PROMPT-STATUS.md`, `docs/lovable-*-prompt.md` | Edit/New | contract + prompts |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | Edit | shipped rows, rulings, 138 addendum |
| `docs/friction-register.md`, `docs/friction-register-archive.md` | Edit | 4 resolved rows archived |

---

## Current Status
Fly v158 is live with everything above. PROMPT-STATUS still lists two prompts as not applied. `lovable-cards-differ-prompt.md` (item 137, sibling session) is live in the bundle but no drive has confirmed it yet. `lovable-no-expense-mail-prompt.md` (item 106) is not pasted. Live inbound log: `n_no_expense` 3, but no entry carries `not_added`. Siblings hold dirty worktrees for item 113 (`agentic-ops1-item-113`) and item 138 (`agentic-ops1-item-138`, `-138b`). Brisken platform line: unknown plan, no ops data; comms-log none.

---

## Next Steps
1. Drive August's LOVABLE 25.00 row cold for the cards-differ chip, then move its PROMPT-STATUS row to Applied.
2. Diagnose why no inbound entry carries `not_added` while `n_no_expense` is 3 (read-only first).
3. Continue the covered defects not claimed by a sibling (queue in the continuation prompt below).
4. Owner: paste the item 106 prompt; decide the by-card view's surface and build-vs-quote.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 96-133 audit entries, 137-138)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Not applied table)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`

### Open Questions
- Is `not_added` written only for mail processed after v157, or is item 106's field missing on the three counted entries?
- By-card view (Criss): inside a month, on the months list, or both; build now or quote?

### Working Notes
- Live figures on v158: July need-receipt 0, closed recurring 24, 11 receipts need a charge; August 8 undecided / 61 need a receipt / 10 need a charge / 0 guessed / 40 closed recurring; August 20 expenses, USD 2,033.86 / EUR 668.00.
- All hosted `subscription` marks come from fills (the web app never sets `store`).
- Residuals: `books_as` skips the chart-of-accounts gate; the decision-route summary omits the private exclusion.

### Reference Materials
- https://expenses.brisken.com, API https://api.expenses.brisken.com, Fly app `brisken-expense-recon`

---

## How to Continue
Paste the continuation prompt below into a fresh chat.

---

## Strategic Feedback

### What Worked Well This Session
- Putting the three rulings to the owner as one AskUserQuestion with recommendations before building let four defects ship in parallel worktrees with no rework.

### Suggestions
- Every builder subagent prompt that touches the live API should state "never write the token or login response to disk"; one agent saved `login-resp.json` with a live bearer to the scratchpad (deleted the same session).

### System Health
- The primary clone runs hooks 45 commits behind origin/main, so the cd-guard subshell rewrite (#1018) is not live for sessions started there.
- Autonomy: 1 human intervention (the standing instruction to list remaining items at each close).

---

## Continuation Prompt
Delivered in chat 2026-09-17; the same text:

````markdown
/comd_resume brisken

Continue the Brisken expense-recon (p1) defect loop. Read first: `docs/2026-09-17 - Expense Recon Private Card And Audit Defects/Checkpoint.md`, then in `workspace/clients/brisken/status/p1-improvement-backlog.md` the voids-audit entries 96-133 and items 137-138, then `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`, and the memories `project_brisken_expense_recon_usability_loop`, `project_brisken_expense_recon_voids_audit`, `project_brisken_recon_matching_program`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `feedback_continuation_prompt_carries_loop`, `feedback_end_iterations_with_remaining_items`.

## Where it stands

- Shipped 2026-09-17 in this line: private card option where no company card paid (#987, v149; SPA applied #990); #95 + #116 (#993, v151); #99 + #100 month_complete + publish gate (#997, v152); #94 copies out of totals and box counts (#998 v152, #1009 v155); gray "já no recurring" charges close the receipt requirement (#1020, v158); #109 recorded as quote-separately and Criss's by-card months idea on item 138 (#1015); three prompts applied and driven (#1022). Sibling sessions shipped 102 (v154), 117/121 (v153), 137 (v156), 106 (v157).
- Live on v158, driven cold: July "Not complete · 11 receipts have no charge", "USD 3,457.11 booked without a receipt (48 charges)"; August "Not complete · 8 rows to decide · 61 charges still need a receipt · 10 receipts have no charge", "5 set aside as copies".
- In flight in sibling worktrees (do not touch): item 113 (`agentic-ops1-item-113`, dirty) and item 138 (`agentic-ops1-item-138`, `agentic-ops1-item-138b`, dirty). #96 and #97 wait on 138.
- Owner ruling: covered-class defects only until the EUR 600 licence is signed; new function is quoted separately.
- Waiting on the owner or Criss, not on you: paste `lovable-no-expense-mail-prompt.md` (item 106); the by-card view's surface (inside a month, the months list, or both) and build-vs-quote; quotes for #98, #104, #107, #109; operations #119-#128; cost-center data #118; Dirk's statements for cards 9693 and 1176 (#108); #129's UI prompt; #61 GL codes; Criss restoring the two July invoices set aside as statement pages (#105's data half).

## Queue, in order

1. **Cards-differ prompt (item 137) is live but not driven.** The bundle carries `cards_differ` (`chunk-runs._runId`) and `wb.cardsDiffer` / `wb.cardsDiffer.tip.override` (`chunk-i18n`); `GET /api/runs/074a7b8905d7` has `summary.n_cards_differ` 1 (LOVABLE 25.00, 2026-08-05, charge 3645, receipt picked 2838). Drive that row cold, confirm the chip renders, move its PROMPT-STATUS row to Applied.
2. **Item 106 residual.** `GET /api/inbound/log` returns `n_no_expense` 3 but no entry carries `not_added`. Find out read-only whether the field is written only for mail processed after v157 or is missing on the counted entries; if it is a defect, fix it (covered).
3. **Covered defects not claimed by a sibling**, each with evidence and a fix sketch in its backlog entry: #131 (suggests pairs its own model calls "likely NOT the same purchase") and #133 (same amount, other merchant, days apart still files Reconciled) together; #101 (bulk confirm/reject up to 1,000 rows with no dialog, looser rule than the owner set); #103 (one receipt bound to two charges, item 72); #130 (English backend strings on Criss's Portuguese screen); #111; #112; #115; #114; #132; #105's classifier half.
4. After a sibling merges 138: #96 and #97.
5. Residuals: `books_as` skips the chart-of-accounts gate; the decision-route summary omits the private exclusion.

Before each item: `gh pr list -R 011matthias/agentic-ops1.01 --state open` and `git worktree list` for a sibling claim (skip a claimed item), and read `GET /feedback.jsonl` for new notes (a new Criss note outranks the queue).

## How to work

- One git worktree off origin/main per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog all day: merge origin/main before pushing, never rebase a pushed branch. The primary clone is behind origin/main; its hooks predate #1018, so use `( cd X && ... )` or `git -C`.
- No writes to Criss's live months; reads only. Never probe publish live. `GET /runs/{id}/expense-report.pdf` WRITES render outcomes (item 67): never fetch it live. Never print or save the operator code or a token; tell every subagent the same.
- Live reads: bearer from `POST /api/login` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env`; `MSYS_NO_PATHCONV=1` for `/api/...` args in Git Bash. Windows Python cannot open `/c/...` paths: pass `C:\...` forms.
- Every backend fix: a route-level test through the caller, then `uv run tools/regress_check.py` with single-line literals (sources are CRLF; "no pytest summary line" means reproduce by hand with a cp backup and cp restore). Python heredocs with triple quotes are blocked: write scripts with the Write tool. Do not import a pytest fixture from another test module (CI ruff F811). Full module suite in the FOREGROUND before the PR: `uv run --extra dev --extra web pytest -q -p no:cacheprovider` (no `-n`; about 4.5 min). Commit, push, PR autonomously; wait for CI with `gh run list --branch <b>` filtered by head SHA; merge on green; deploy with `( cd <module> && flyctl deploy . -a brisken-expense-recon --remote-only )` from a clean detached origin/main worktree (pre-authorized).
- After a deploy: a live API probe of the changed field, then a cold consumer drive. Playwright `channel="chrome"` headless: goto, wait 4 s, fill the first input with the code, Enter, wait 8 s, goto the route, read `body` inner text, record non-GET requests (must be none). agent-browser hung on 2026-09-17.
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
