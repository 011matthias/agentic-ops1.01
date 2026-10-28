# Checkpoint: Brisken Recon Items 114 And 105

**Date:** 2026-09-17
**Status:** Items 114 and 105 shipped and deployed (Fly v162, v165), both recorded; owner notes #65-#69 in the backlog; stopped at HIGH pressure (~500k)

---

## Summary
Two voids-audit defects closed end to end. A drop cut off by a restart now runs again at boot instead of stranding its files (114). An invoice the reader calls a statement page now stays an expense and asks for a look (105). Five new owner feedback notes became backlog items 139-142.

---

## What Was Done This Session

### Step 0
1. `/feedback.jsonl` held 69 notes (last recorded #64). Notes #65-#69, owner, 15:13-15:19 UTC, recorded as items 139-142 (PR #1031): private card inside the card picker, duplicates side by side, one download button per file, booked-row hint names the workbook.
2. Sibling check found session 3d5a3bae running a parallel queue (131+133, 101, 103, 130, 111, 112, 115, 114, 132, 105); items were taken from the end of its list.

### Item 114 (PR #1033 merge 50425571, Fly v162; record #1034)
1. Live read: `/data/drops` empty, no stranded staging folders, zero jobs ever interrupted by a restart, 18 drops since 09-08.
2. Narrowed by the reviewer corrections (the operator keeps originals, re-drop is dedupe-safe, delete needs the typed label): month-delete custody not built.
3. Sidecar `drops/<job>.json` `{month, resumed, created_at}`; boot pass after the stale-job sweep re-runs each interrupted drop once under its job id, gives up a second cut-off, deletes leftover drop folders and `drop-add-*` copies.
4. Adversarial review found 3 defects in the first draft (queued drops given up on a second restart, a failing folder leaving a job running with no thread, one failing run stopping the rest); each reproduced by a test first, fixed by bumping `resumed` at run start and guarding per folder and per run.
5. Suite 2186 -> 2196; 10 tests; nine regress proofs by hand, all red. Deploy check: new boot pass in the running image, Receipts page driven cold.

### Item 105 (PR #1037 merge c5b00852, Fly v165; record #1038)
1. Stored readings of the three July invoices carry vendor, total, invoice number and line items (10, 2, 2). Eight real statements read through the production reader (July run config, gpt-5-mini): seven Chase card statements and an SAP AR statement, all without reference and line items. Two billing-notice emails: reference, no line items.
2. `cli.keep_invoice_read_as_statement` (vendor, non-zero total, reference, a non-zero line amount) wired into both quarantine sites; prompt untouched.
3. Adversarial review: the kept row landed in the ready box and could self-confirm. Fixed: `check` / `invoice_read_as_statement`, `category_confirmable` true until every line's category is the reviewer's own.
4. Replay over a read-only DB copy: keeps exactly the 3 invoices, 0 stored expenses touched. Suite 2236; 13 tests; seven regress proofs by hand, all red. Deploy check: July Expenses page driven cold, set-aside strip unchanged.
5. Optional SPA copy prompt `lovable-invoice-read-as-statement-prompt.md` (PROMPT-STATUS Not applied).

---

## Key Decisions Made

### 114: resume at boot, not soft delete
- **Choice:** re-run an interrupted drop once from the files on the volume; no month-deletion custody.
- **Rationale:** reviewer corrections 1 and 3 refute the delete half; the restart half leaked the pile and lost the month pick.

### 114: `resumed` written at run start
- **Choice:** the boot pass only queues; the thread bumps the count right before each run.
- **Rationale:** bumping at boot gave up drops that never ran when a second restart landed mid-queue.

### 105: deterministic rule, not a prompt edit
- **Choice:** second-guess only the `statement` verdict, on stored reading fields.
- **Rationale:** prompt edits move unrelated readings (memory, item 77); the four fields separate 3 invoices from 10 non-invoices on real documents.

### 105: a sticky-free check
- **Choice:** the check clears through the note #62 Confirm.
- **Rationale:** a check that never clears is the note #62 defect Criss reported.

---

## What Did NOT Work (and why)
- **`regress_check.py` for item 114 proofs:** printed "RED (no pytest summary line)" for all nine mutations, including one (sidecar validation) whose suite was actually GREEN; every proof was re-run by hand with backup and byte-identical restore.
- **Probing set-aside readings with keys `vendor` / `total`:** the stored dict uses `detected_vendor` / `detected_total`, so every field read None and a "storage drops the header fields" defect was announced before being retracted.
- **Identical mock receipts in the 114 resume test:** the second copy was ruled a duplicate (item 94 keeps copies out of `n_expenses`), 1 instead of 2; fixed with distinct vendor and total.
- **Bash heredoc with a Python triple-quoted payload (105 test edit):** refused by the heredoc gate; redone with Edit.
- **`cd /c/.../agentic-ops1 && git show` at session start:** refused by cd-guard in the primary clone; used `git -C`.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `expense-reconciliation/src/expense_recon/web/app.py` | Edit | 114 sidecar, boot resume, per-folder/per-run guards |
| `expense-reconciliation/src/expense_recon/cli.py` | Edit | 105 `keep_invoice_read_as_statement` + create-path wiring |
| `expense-reconciliation/src/expense_recon/web/service.py` | Edit | 105 add-path wiring, review check, confirmable |
| `expense-reconciliation/tests/test_drop_resume_item_114.py` | Create | 10 tests |
| `expense-reconciliation/tests/test_invoice_read_as_statement_item_105.py` | Create | 13 tests |
| `expense-reconciliation/docs/api-contract.md` | Append | two sections |
| `expense-reconciliation/docs/lovable-invoice-read-as-statement-prompt.md`, `PROMPT-STATUS.md` | Create/Edit | 105 SPA copy |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | Edit | items 139-142; 114 + 105 shipped records |

---

## Current Status
Live: Fly v165 (114 + 105 on top of siblings' 101, 131, 96/97). July's AWS USD 3,352.59 and Tricarico BRL 27,203.34 invoices still sit in the set-aside strip for Criss's restore. brisken ops status: platform unknown plan (no `platform` assessment in infrastructure.yaml). Comms log: none. Stale status files p2-product-decks (56d) and p2-targeting (57d) are p2 workstreams not touched here.

---

## Next Steps
1. Sibling-claim check, then queue: 103, 115, 130, 93, 132, 133's matcher half (111 + 112 claimed in sibling worktree `agentic-ops1-item-112-111`; prompts for 139-142 in `agentic-ops1-prompts-139-142`).
2. Items 139-142 wait on the owner (SPA prompts; 140's licence class).
3. Add a platform feasibility assessment to brisken `infrastructure.yaml` (carried pre-flight flag).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (grep `### 103.` etc.)
- memory `project_brisken_expense_recon_voids_audit`, `project_brisken_expense_recon_usability_loop`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `feedback_loop_iterations_list_remaining_items`
- `automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

### Open Questions
- None blocking.

### Working Notes
- Regress proofs by hand: scratchpad `regress114.py` / `regress105.py` pattern (copy source, single-line replace, run pytest, restore, assert byte-identical, print FAILED lines).
- Negatives for a classifier rule: `.scratch/criss-recon-may/receipts/*statements-2838-.pdf` (7 Chase) and `.scratch/recon-july/mail-receipts/*AR_STATEMENT_SAP*` read through `receipts_folder._extract_file` with the run's own llm config and a scratch cache.
- Consumer drives: headless Playwright channel=chrome scripts (`drive114.py`, `drive105.py`), non-GET requests printed.

### Reference Materials
- PRs #1031, #1033, #1034, #1037, #1038; Fly v162, v165

---

## How to Continue
Paste the continuation prompt from the chat into a fresh session; it carries the pressure-stop, checkpoint and "list what's left" loop.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring the rule on real negatives before building 105: eight statements through the production reader turned a guessed rule into one with 3/3 and 0/10 on real documents.
- Adversarial review again caught what the planned tests did not: 3 defects in 114's boot pass and the ready-box self-confirm in 105.

### Suggestions
- `tools/regress_check.py` should report a run with no pytest summary line as UNKNOWN, never RED; it called a green suite red here, which is the exact failure the tool exists to prevent.

### System Health
- The trap memory for `regress_check.py` ("reproduce by hand") has existed since 2026-09-16 and was needed again; the tool fix is overdue.
- Autonomy: 0 human interventions (fully autonomous session).
