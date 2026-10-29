# Checkpoint: Recon Drop Asked-For Button

**Date:** 2026-10-29
**Status:** Done. The button is gone from the published SPA; docs recorded (PR #1687 merged)

---

## Summary

The owner asked what the "Mark the receipt as asked for" button in the recon SPA's charges-without-receipts list does. The answer: a per-charge flag that sends nothing and closes nothing (item 107). The owner then had it removed through a Lovable prompt. Removal verified on the published bundle; the backend route stays unused.

---

## What Was Done This Session

### Answer
1. Traced the button to `POST /api/runs/{id}/receipt-requested` (`web/app.py:3226`) and to api-contract §2 of the chase section. It writes `receipt_requested_at` / `requested_to` on the charge's decisions row. It does not change `n_charges_need_receipt`; it only feeds the subset counter `n_charges_receipt_requested`.

### Removal (UI only)
1. Handed a Lovable prompt in chat; the owner pasted it. Lovable `21082b4` deleted 120 lines from `ReceiptChasePanel.tsx` and 9 from `RunWorkbench.tsx`.
2. Verified publish with a differential bundle audit over all 49 chunks, lazy ones included: `receipt-requested` 0 files and `receipt_requested_at` 0 files, against 6 reads of that field in the pre-change source. The control `no-receipt-expected` was still 1.
3. Filed the prompt as `docs/lovable-drop-asked-button-prompt.md` and noted in `api-contract.md` that no UI sets "requested" any more. PR #1687: CI green, merged.

---

## Key Decisions Made

### Keep the backend route
- **Choice:** remove only the UI; leave `receipt-requested`, the row fields, the summary counter and the chase-mail preview in place.
- **Rationale:** the route is harmless unused. Removing it touches the summary, the mail composer and tests for no user-visible gain. Stored marks survive, so the button can return without a backend change.

---

## What Did NOT Work (and why)

- **Handing the Lovable prompt only in chat:** the repo convention is a `docs/lovable-*-prompt.md` file per prompt. The `warn-owner-publish-without-named-prompt` pattern rule flagged the miss on the next turn. Fixed retroactively in #1687.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-drop-asked-button-prompt.md` | Created | Prompt record and verify recipe |
| `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` | Edited | Note: no UI sets "requested" since 2026-10-29 |

---

## Current Status

Brisken platform line: unknown plan, ops not assessed in `infrastructure.yaml`. Comms-log 31 days stale.

Every Brisken `status/` file is past the 21-day threshold, `p1-expense-reconciliation.md` included (updated 2026-10-07). I did not bump it: one line changed this session, and re-dating the whole file would mark the other 22 days current without review.

---

## Next Steps

1. Review and update `status/p1-expense-reconciliation.md` + `p1-improvement-backlog.md` against shipped reality (stale 22d); the asked-button removal goes in as one row.
2. Decide whether `receipt-requested` should be deleted from the backend later, or kept dormant (owner call; dormant is the default).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-drop-asked-button-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (chase section §2)

### Open Questions
- Does anyone still want a "chase is out" signal on the list? If yes, it returns as UI only.

### Working Notes
- The bundle audit recipe from `reference_lovable_merge_is_not_live` works as a one-shot curl loop. Follow chunk references for three rounds to reach the lazy chunks (49 here); `grep -al` counts files.

### Reference Materials
- Published SPA: https://brisken-reconcile-dash.lovable.app
- SPA repo: `011matthias/brisken-expense-review` (commit `21082b4`)

---

## How to Continue

Nothing is in flight. Start from Next Steps 1 if the session is about recon status.

---

## Strategic Feedback

### What Worked Well This Session
- Verified the publish differentially. A control string still present and the old field shown in the pre-change diff together proved the probe could see the screen, so the zero was a real absence.

### Suggestions
- `warn-hand-prompt-as-text` fired on a closing message that named an already-applied prompt file. That message had nothing to paste. Narrow the rule to skip when the same message reports the prompt as applied or verified (e.g. "Lovable `<sha>`" / "is live").

### System Health
- The missed-session-header skip recurred again (row below). Every prior fix was `documented` and none held. A structural fix is overdue: a Stop-event check that the session's first substantive reply carries the header.
- Autonomy: 1 human intervention (owner pasted the Lovable prompt; no Lovable MCP connected this session).
