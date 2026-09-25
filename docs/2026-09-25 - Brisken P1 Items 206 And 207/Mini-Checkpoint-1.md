# Mini-Checkpoint: Brisken P1 Items 206 And 207

**Date:** 2026-09-25
**Status:** Both items merged and deployed (Fly `19f08289`); item 207's chart file replaced live
**Type:** mini

---

## Summary
Item 206: on a GL month, the engine now answers for the company each row shows, wherever the card chain moves it. Item 207's cause was confirmed on production: the volume's chart file was the 1 July pull. The file was replaced (owner yes) and `/healthz` now reports any postable account the file lacks.

## What Was Done
- **206 (PR #1376, `c6626a14`).**
  - `service.grid_card_chain` is the grid's card chain as one callable; `shown_companies` reads the company off it.
  - `recategorize_moved_companies` re-runs the engine on three kinds of row:
    - a row whose shown company moved;
    - a row whose company the reviewer set;
    - a row showing a company while still refused `entity_missing` (the sweep).
  - Wired at: the field PUT (`COMPANY_CHAIN_FIELDS`), entity, private, card hints, refresh-master-data, `rematch_after_change` (only with a learning path), and the attach / re-read jobs.
  - Tests: 8 route-level. Seven wiring points were proven red with `regress_check`. Suite: 3484 passed / 2 skipped.
- **207 diagnosis.** Code rule-outs: org mapping, the E700040-30 near-namesake, and scope_groups. Owner-approved read-only `flyctl ssh`: the live `/data/zoho-books-coa.json` had sha `e4055931`, 199 Cloud Services accounts, and no `E700030-30`. It lacked 18 of Dirk's 64 Cloud Services postable accounts.
- **207 live fix (owner yes, after a plain-language explanation).**
  - Snapshot `vs_V9ka1J80opbTj5qDJOpy9Gg` taken first.
  - The 09-24 pull (442,136 bytes, sha `aa855aea`) was written as `.new`, verified on the server, then moved into place. The old file is kept as `/data/zoho-books-coa.2026-07-01.json`.
  - CSV re-read: SendGrid is named, and 0 rows are unmapped in July, August and September.
- **207 structural (PR #1378, `19f08289`).** `/healthz` gains `coa_chart`, with per-company missing postable codes, cached on the file's mtime and size. Tests: 5 through the route. Three wiring points were proven red.
- **Deploy `19f08289`.**
  - `/healthz` shows the new commit, with `coa_chart.ok` true and 0 missing for all three companies.
  - Cold SPA drive: SendGrid renders "COGS - Other Infra and IT Costs for Cloud Business · E700030-30".
- **Item 210 recorded (owner: record only).** The export gate checks a row against its stamped company, not the company the row shows.

## What Did NOT Work (and why)
- **CSV assertion on the card-change test (206):** a Cloud-only account exports as unmapped. The export gate checks the receipt's stamped company, which is Corporate from the printed card. That is item 210, not a 206 regression, so the test asserts the grid only for that case.
- **Test precondition `review.reason_code == "category_refused"`:** a row with no company reads `needs_entity`, which outranks it. The real precondition is the stored `entity_missing` refusal.
- **First SPA drive:** the feedback widget's "Leave feedback anywhere" hint (`[role=dialog][aria-labelledby=fb-hint-title]`, button "Got it") appears after networkidle and intercepts clicks. Wait for it to appear, then dismiss it.
- **Snapshot poll loop grepping "created":** it matched the table header ("CREATED AT"). Grep the snapshot id's row for `│ created` instead.
- **First chart swap:** it hit "no started VMs" because a sibling deployed v232 at that moment. Retried after `fly status` showed the machine started; the `.new` file had survived on the volume.

## Current Status
- Live: Fly `19f08289`. It carries 206, 207, and the sibling's items 180/181.
- July, August and September: 0 rows that show a company still carry `entity_missing`, except 3 in September. Those are two Lovable invoices (Corporate) and one Anthropic invoice (Cloud), all `card_source: hint`. The shipped sweep re-runs them at September's next re-match or next company-chain edit. No agent write on Criss's month.
- Backlog: 206 and 207 fixed; 210 recorded; 208 and 209 are siblings' items.

## Next Steps
1. None queued from this session. Item 210 waits for an owner decision.
2. On the next chart pull, also replace the volume copy (recipe in backlog item 207), then read `/healthz` `coa_chart.ok`.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 206, 207, 210)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`grid_card_chain`, `recategorize_moved_companies`)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/category_vocabulary.py` (`chart_coverage`)
