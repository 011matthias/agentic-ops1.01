# Checkpoint: Brisken Recon Items 106 And 113

**Date:** 2026-09-17
**Status:** Items 106 and 113 shipped and deployed (Fly v157, v159); stopped past the HIGH pressure band on the owner's "checkpoint here"

---

## Summary
Two voids-audit defects closed end to end: a mailed forward that created no expense now says so on the intake page and in the sender's acknowledgement (106), and a re-match that fails or is cut off by a restart is now recorded on the month, retried by the next arrival, re-paired at boot and mailed to the operator (113).

---

## What Was Done This Session

### Item 106 (PR #1017 merged 19b5b21c, Fly v157; record PR #1021)
1. Live read first: 3 mails (4 log rows) finished `ingested` with `documents: []` and read "Added": Dirk's AWS billing notice (08-24, re-ingested 09-07), Criss's AT&T notice and card summary (09-09); each was the rendered email text set aside (`statement` / `other` / `report_summary`). No HEIC in the 121-row log.
2. `_add_receipts_locked` summary + archive meta `not_added[]` per file (`set_aside`+reason, `already_on_file`, upload-issue code, `document_id`); intake label "Nothing added: ..." with status and `status_kind: done` unchanged; `n_no_expense`; acknowledgement "No expense added: {subject}" per file.
3. Adversarial review found 6 defects in the green draft, all reproduced and fixed: crash-replay counted the mail's own stored receipt as a copy (provenance now records `archive`), restore did not end "Nothing added" (read-time overlay), raw attachment names echoed with newlines/URLs (flattened), pooled-then-empty mail got no correction (one `no_expense_ack_at` correction), mail-created month dropped upload rejections, set-aside bytes read "already on file".
4. `test_render_retry_after_commit_failure_does_not_duplicate` pinned the finding-1 defect (`documents == []` on a retry whose first attempt stored the row); pin changed to the mail's own row.
5. Contract doc, storage description 11.3, view-contract pin `expense_ingest.not_added[]`, Lovable prompt `lovable-no-expense-mail-prompt.md` (handed to the owner in chat; PROMPT-STATUS Not applied).
6. Deploy check: published `/inbound` shows "Nothing added" on the 3 forwards (headless Chrome, read-only), `n_no_expense` 3.

### Item 113 (PR #1026 merged af7555fd, Fly v159; record PR #1027)
1. Snapshot `rematch_pending` `{id, since, changed_at, trigger, error?, failed_at?, attempts?}` written in the arrival's receipts write, by a month move on both months in its lock span, and before every re-match; every write a new id; a `rematch_month` commit clears only the id it read.
2. Failures recorded on the mark; an arrival re-pairs when a mark existed even with zero new files; boot thread `resume_pending_rematches`; `/api/operator/state` `rematch_pending[]`; notifier mails each failure once per `(run_id, failed_at)`.
3. Adversarial review found 4 defects: older re-match clearing a newer change's debt (high) and erasing a newer failure (high) fixed by always-new ids; month move leaving no debt (medium) fixed in the move's lock span; duplicate arrival mid-match costing one extra re-match (low) accepted and documented.
4. Deploy check: `rematch_pending: []`, July 112 / August 114 rows, intake page drive clean. No SPA consumer for the field.

### Owner directive
1. "When ending loop iterations, lay out what items are left": saved as memory `feedback_loop_iterations_list_remaining_items`, carried into the continuation prompt's loop section.

---

## Key Decisions Made

### 106: kind stays `done`
- **Choice:** honest `status_label` + parallel `not_added` / `n_no_expense`; no sixth `status_kind` and no `held`.
- **Rationale:** `n_held` counts `held_*` statuses, so a held kind would disagree with the Held badge (the 2026-08-24 dismissed-row incident); the published SPA renders `status_label`, so the text fix is live without a paste.

### 106: HEIC conversion not built
- **Choice:** name an unreadable attachment type in the acknowledgement instead.
- **Rationale:** no HEIC in the live log; conversion needs a native library in a Dockerfile that ignores uv.lock (item 124).

### 113: `rematch_log` meaning kept
- **Choice:** failures live on the mark and in `rematch_pending[]`, not as log events.
- **Rationale:** the log is documented as one event per commit and the notifier prints counts from it.

### 113: periodic sweep (F34) not built
- **Choice:** boot re-pair only.
- **Rationale:** the reviewer correction stands: a crash restarts the always-on machine and runs the boot passes.

---

## What Did NOT Work (and why)
- **First 106 draft through the full suite:** `test_expense_batch_view_list_contract` failed on the unpinned `expense_ingest.not_added[]`; the first pin went into RUN_MUST_COVER instead of EXPENSE_BATCH_MUST_COVER and failed the run-view coverage check.
- **Provenance match by `received_at` for 106 finding 1:** arrival stamps `_now_iso()` while replays pass meta `at`, so the two differ; recording `archive` in provenance was the working key.
- **regress_check "failure new id" on the first 113 test set:** TEST DOES NOT BITE, because `_ensure_rematch_pending` already issued a new id before the failure; needed a test that records a failure with no ensure step.
- **Bash heredocs for test appends:** refused twice (a double backslash in a Python payload, and 87 lines over the 80-line cap); redone with Write/Edit.
- **`cd "$TEMP/..." && python` in Bash:** cd-guard refused it (primary-clone hooks); rerun with absolute paths.
- **First `gh pr merge 1017`:** "Pull Request has merge conflicts" after item 137 landed an api-contract.md append; merged main, kept both sections, re-ran the suite (2167).
- **Stop hook on "confirm ... is live":** the consumer gate does not recognize a `uv run drive106.py` Playwright script as a drive; answered by stating the drive and that 113's field has no SPA consumer.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `expense-reconciliation/src/expense_recon/web/service.py` | Edit | 106 `not_added`; 113 mark helpers, clear rule, failure record, month-move marks, owed re-pair |
| `expense-reconciliation/src/expense_recon/web/intake_mail.py` | Edit | 106 stamp, label, ack body, own-outcome, restore overlay, safe echo, correction ack |
| `expense-reconciliation/src/expense_recon/web/app.py` | Edit | 106 `n_no_expense` + restore overlay; 113 boot resume + operator `rematch_pending[]` |
| `expense-reconciliation/tests/test_intake_mail.py` | Edit | 10 item-106 tests, retry pin corrected |
| `expense-reconciliation/tests/test_view_contract.py` | Edit | pin `expense_ingest.not_added[]` |
| `expense-reconciliation/tests/test_rematch_log.py` | Edit | 6 item-113 tests |
| `expense-reconciliation/tests/test_month_move.py` | Edit | 113 month-move debt test |
| `tools/brisken-recon-notify.py`, `tools/tests/test_recon_notify_diff.py` | Edit | failed owed re-match mail |
| `expense-reconciliation/docs/api-contract.md` | Append | two sections |
| `expense-reconciliation/docs/electronic-storage-system-description.md` | Edit | 11.3 acknowledgement content |
| `expense-reconciliation/docs/lovable-no-expense-mail-prompt.md`, `PROMPT-STATUS.md` | Create/Edit | 106 SPA half |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | Edit | 106 + 113 shipped records (#1021, #1027) |

---

## Current Status
Live: Fly v159 (106 + 113 on top of siblings' 137 and gray-recurring). Record PR #1027 (113) in CI at checkpoint time. Owner-side: paste `lovable-no-expense-mail-prompt.md` (optional styling); the laptop notifier task runs from the primary clone, so failure mails go out once main is pulled there. brisken ops status: platform unknown plan (no `platform` assessment in infrastructure.yaml). Comms log: none for brisken. Stale status files p2-product-decks (56d) and p2-targeting (57d) are p2 workstreams this session did not touch.

---

## Next Steps
1. Merge #1027 on green if the checkpoint session did not.
2. Queue, sibling-claim check before each: 114 (confirm the "defect" tag first), 103, 101 backend half, 105, 111, 112, 115, 130, 93.
3. After owner item 138 (PDFs by card) lands: 96, 97, then 131, 132, 133 (137 shipped #1016).
4. Add a platform feasibility assessment to brisken `infrastructure.yaml` (pre-flight flag, carried from earlier checkpoints).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (grep `### 114.` etc., read the entry in full)
- memory `project_brisken_expense_recon_voids_audit`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `feedback_loop_iterations_list_remaining_items`
- `automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

### Open Questions
- None blocking.

### Working Notes
- Sibling-claim check that worked: `git worktree list` + `git -C <wt> status --porcelain` + a transcript scanner (`scratchpad/sibs.py`: last user prompts, last replies, regex hits) over the sessions from `tools/session_registry.py --list`.
- Background-work pattern that held: full suite in background, adversarial review agent in background (read-only, targeted pytest only), regress proofs only AFTER both finish (they mutate source).
- CI waiter: bounded loop on `gh pr view N --json headRefOid,statusCheckRollup`, break when head moves or every check is COMPLETED; re-merge main if `gh pr merge` reports conflicts.
- Consumer drive: `scratchpad/drive106.py` (Playwright channel=chrome, code from `context/.env` `EXPENSE_RECON_OPERATOR_CODE`, wait 4 s, fill, Enter, wait 8 s, reload route).

### Reference Materials
- PRs #1017, #1021, #1026, #1027; Fly v157, v159

---

## How to Continue
Paste the continuation prompt from the chat into a fresh session; it carries the pressure-stop, checkpoint and "list what's left" loop.

---

## Strategic Feedback

### What Worked Well This Session
- Adversarial review after a green suite: 10 real defects across two items, each reproduced by running code, two of them high (a debt cleared by an older re-match) that no planned test covered.
- Live read before building 106: it showed every instance was a rendered email body and there was no HEIC case, which kept the HEIC conversion out of scope with evidence.

### Suggestions
- `deploy-consumer-gate.py` should close on a foreground `uv run` of a Playwright script that reads page text back (`inner_text` / `wait_for` on the route), the drive shape this client's sessions now use instead of agent-browser.

### System Health
- Status lines that end a turn while CI runs in the background read to the owner as "blocked" ("what do you need from me?"); a closing line should say nothing is needed and what continues on its own.
- Autonomy: 1 human intervention (the "what do you need from me" nudge); the remaining owner messages were direction (list remaining items, hand the prompt, checkpoint).
