# Mini-Checkpoint: Zoho GL Chart Pull And Registry Reads

**Date:** 2026-09-24
**Status:** Queue items 1 and 2 of the direct-to-Zoho-GL change shipped to main; items 3-8 open
**Type:** mini

---

## Summary

Queue item 1 (backlog 182) turned out to be misdiagnosed: the chart pull was
not short because it stopped paginating, and the fix that reading implied
cannot work. Shipped a puller that judges completeness against the curated
taxonomy instead, taking Cloud Services from 199 accounts to 255. Queue item
2 closed the registry read/write asymmetry that made a stored leaf code
silently unreachable.

## What Was Done

- **#1246 (backlog item 182), `tools/pull-brisken-zoho-coa.py`.** Zoho's
  `/chartofaccounts` under-reports for org 697686691 and reports completion
  every time: 199 rows at `per_page=200`, 89 at 100, 47 at 50, all
  `has_more_page: false`. A smaller page returns fewer TOTAL rows, so no
  pagination strategy helps. The two listings are not nested either (7
  accounts only under the default params, 55 only under `showbalance`, whose
  documented spelling `show_balance` is accepted and ignored), and their
  union of 254 still omits one account `GET /chartofaccounts/{id}` returns
  as active. The tool merges both listings, tops up by id against the
  compiled curated taxonomy as an outside answer key, and fails when a
  postable account cannot be obtained at all. Live: Cloud Services 199 ->
  255 (+56, -0), every org a strict superset, 67/64/68 present. Driven
  through the consumer: `load_entity_chart` moves two probes False -> True
  with a control that does not move. Compiler cross-check 19 -> 0 absent,
  asset sha unchanged. 18 tests, 3 regress proofs red-first at the caller.
- **#1249 (queue item 2).** `merchant_registry._match` and
  `categorize.apply_registry_category` now use `category_vocabulary.recognize`
  instead of filtering against the eight buckets. A leaf code was accepted on
  save (#1236) and discarded on read, so the rule went inert and the receipt
  went to the LLM at full cost with no error and no log line. 9 tests, all
  asserting through callers; 2 regress proofs, each reddening the production
  entrance. Suite 3134 -> 3156 passed / 2 skipped.
- **#1250.** Status file corrected: it still carried the page-boundary
  reading that the measurement refuted.
- **Unblocked a lint failure on main.** #1245 landed
  `test_receipt_render_178.py` with an unused `pathlib.Path` import, so the
  `Enforcement hook tests` ruff step was failing on main itself and on every
  PR merged against it. Removed in #1246.
- **Corrected memory `project_brisken_zoho_books`** and its index line: the
  Zoho token is no longer read-only.

## What Did NOT Work (and why)

- **Following the pagination, as backlog item 182 specified.** The existing
  `.scratch/zoho_coa_refresh.py` already walked `has_more_page` at
  `per_page=200` and returned the same 199 rows. A count assertion on short
  pages would fire on every single call, because the server reports a short
  page as the last page every time.
- **Using a smaller `per_page` to expose the hidden rows.** The opposite
  happened: 100 returned 89 total and 50 returned 47, both claiming
  completion. Fewer rows per page means fewer rows overall on this endpoint.
- **Taking the union of every listing parameterization as complete.** 254
  accounts, and `2031056000023745007 E600010-30-10 Marketing Expenses -
  people` still absent. Only `GET /chartofaccounts/{id}` returns it.
- **`show_balance=true`, the documented spelling.** Accepted and silently
  ignored, returning the unchanged 199. `showbalance` (no underscore) is the
  one that changes the result set.
- **First draft of `tools/tests/test_pull_brisken_zoho_coa.py`.** One
  assertion joined tool-call paths into a single string and matched
  `/chartofaccounts/` across the boundary between two entries. The test was
  wrong, not the tool.
- **Guessing the module's test fixtures.** `Receipt(vendor=...)` and
  `resolve("ANTHROPIC")` are both wrong signatures; 8 tests failed on
  `TypeError` before reading `tests/test_merchant_registry.py` for the real
  shapes.

## Current Status

Three PRs merged: #1246 (`4ca8298f`), #1249 (`212a2d67`), #1250
(`51dd891c`). Nothing is deployed, and nothing calls the posting chain; the
engine still classifies into the eight buckets. `brisken` platform ops
status is unknown plan (`infrastructure.yaml` has no assessed figure).
Comms-log is 16 days stale.

The complete chart now unblocks queue item 5 (delete `category_accounts.py`
and lift `NON_LEAF` / `OUT_OF_SCOPE` into `resolve_account_id`), which was
gated on it because an account absent from the chart answers `UNKNOWN`
before `OUT_OF_SCOPE` is evaluated.

**The Zoho token is no longer read-only.** Granted scope reads
`ZohoBooks.expenses.CREATE expenses.READ contacts.READ accountants.READ`.
`settings.READ` went with it, so `GET /organizations` 401s code 57. Nothing
in this session used the write grant.

## Next Steps

1. Queue item 3 (backlog 183): `registry_upserts_from_expense_run` fires on
   Publish rather than a deliberate save, and its conflict check compares
   `prior["category"] != category` only (`web/service.py:4745-4750`), so a
   second row naming a different `zoho_account` is not a conflict and the
   first wins. Prerequisite for item 4.
2. Queue item 4: convert the engine to call `resolve_posting_account`, with
   4a (the `bool(cat.category)` invariant), 4b (a refusal stores `None`,
   never `"(assign)"`) and 4c (an explicit clear stays distinct from a drop)
   each decided before code.
3. Queue item 5, now unblocked.
4. Queue items 6, 7, 8.
5. Ask the owner whether the `expenses.CREATE` grant was deliberate.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-gl-categorization-architecture.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 183, 184)
- `tools/pull-brisken-zoho-coa.py`
- `C:\Users\NEUMA_~1\AppData\Local\Temp\claude\c--Users-neuma-p1qrsic-Repo-agentic-ops1\fa5d7d33-e79f-4610-bacd-f914ca17b99e\tasks\wbr3odfy8.output`
  (the 7-agent map of queue items 2-8, with verified line numbers and
  regress anchors; ~222 KB, read the sections you need)
