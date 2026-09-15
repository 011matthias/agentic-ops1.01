# Mini-Checkpoint: Expense-Recon Item 16

**Date:** 2026-09-15
**Status:** Shipped (PR #828, merged `9d6b8849`), live on Fly v118, SPA half pending the owner's paste
**Type:** mini

---

## Summary

Backlog item 16: a rejected match released its receipt and then re-rendered it
underneath the same row as though it were still on offer, with nothing saying
it had been turned down. `rows[].candidates[].rejected` and
`summary.n_rejected_pairings` are the missing fact; the undo the item asked for
turned out to exist already, so none was added.

## What Was Done

- **Live read first, and it moved the build.** Zero rejected decisions exist in
  production. All 223 charge rows across the two statement-bearing months
  (August `074a7b8905d7`, July `50622baec444`) are `pending`, and the other four
  batches carry no charge rows at all, so the reported symptom cannot be
  observed live and neither can "did another charge pick the rejected receipt
  up". Fixture constructed, same as items 60 and 56.
- **`rows[].candidates[].rejected`** — parallel, absent (not `false`) unless the
  charge's current verdict is `rejected`. Charge-level by construction, not
  preference: `apply_decisions` pass 3, `effective_settlements` and
  `sync_claim_for_decision` all read the status alone and ignore
  `chosen_document_id`, and `bulk_decisions` writes that column NULL on a
  reject, so a flag keyed on a named document would have left the commonest
  path unmarked.
- **`summary.n_rejected_pairings`** — run payload only, like every count derived
  from `rows[]`. Pairings, not rows: a rejected charge that never had a
  candidate refused nothing and counts nothing.
- **No new undo route.** `POST /api/runs/{id}/decisions` with
  `"status": "pending"` already resets the charge under the same lock,
  re-derives the claim through `sync_claim_for_decision` and hands the receipt
  back. What was missing was the payload saying there was anything to undo.
  `test_the_undo_path_is_the_same_route_with_pending` drives the whole reversal
  (status, bucket, `chosen_document_id`, flags, count, receipt leaving the pool)
  instead of asserting it ought to work.
- Suite 1550 to 1555 passed / 2 skipped. Two regress proofs RED first: the
  stamping (`**_rejected_pairing(status),` to `**{},`) and the count's own sum.
  Both bite through the caller — every red test posts to the decision route and
  reads `GET /api/runs/{id}`.
- Deploy skipped per protocol §7: a sibling's deploy carried the merge. Absent
  at v117, present from v118 (the first release built after `9d6b8849` landed).

## Current Status

Backend live. `n_rejected_pairings: 0` on both months, and all 55 candidates
across them carry no `rejected` key, which is the parallel-field guarantee
holding on real data. Consumer drive on `expenses.brisken.com` was cold (login
gate through to `/runs/074a7b8905d7`): the workbench renders with no regression,
3762 snapshot lines, zero fallback strings. The renderer itself is NOT verified
and cannot be: the SPA has no case for the field yet (the one "Rejected" string
in the DOM is the existing status-filter chip), and no live month carries a
reject to exercise it. Recorded in PROMPT-STATUS under both Not-applied and
Cannot-verify.

`tools/lovable-bundle-audit.py` will report the two field names as not applied
until the owner publishes; that is the correct reading today, not a failure.

## Next Steps

1. Owner pastes `docs/lovable-rejected-pairing-prompt.md` into the Lovable
   project, publishes, then re-run `uv run tools/lovable-bundle-audit.py` with
   `rejected` / `n_rejected_pairings` / `wb.cand.rejected` added to `NEW` and
   move the PROMPT-STATUS row to Applied.
2. The muted-candidate render and the undo button stay unexercised until a real
   month carries a reject. Do not manufacture one in Criss's data.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  ("A pairing the reviewer turned down")
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_rejected_pairings.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (Shipped row 35)
