# Mini-Checkpoint: Brisken P1 July To September On Zoho Accounts

**Date:** 2026-09-25
**Status:** July, August and September switched to the Zoho accounts live; item 201 live; items 206 and 207 recorded as leads
**Type:** mini

---

## Summary
On the owner's order, July, August and September were re-categorized on the GL engine through a new operator route. Criss's bucket picks were ignored, per the owner's ruling. Item 201 shipped with it, so a hand-picked account now exports under its name. Both are live on Fly `071b19d7` (PR #1356; record PR #1359).

## What Was Done
- **Nothing was still stalled from the OpenAI outage.** Both 9693 statements and the held mail were loaded on 2026-09-24, and the GL drive ran then. The inbound log reads `n_held: 0`.
- **Item 201 (owner: fix now).**
  - What changed: a picked leaf code reads its account name at read time. The name is resolved in the company the row shows: the card chain (`resolve_batch_row_cards`) on the grid and in the CSV, and the charge's company for a receiptless charge. The fix is threaded through `apply_overrides`, the charge-override builder and `_row_posting_category`.
  - Where the lookup lives: `category_vocabulary.gl_leaf_account_name`, because `web/` may not import `..zoho`.
  - Tests: `tests/test_gl_hand_pick_account_item_201.py` (6).
- **Item 205, the month switch.**
  - The route: `POST /api/runs/{id}/convert-to-gl` in `web/gl_conversion.py`. It needs a typed confirm and runs as a job.
  - What it does:
    - config gets `apply_to_config`, as a new month does;
    - every receipt line is re-categorized for the company the grid shows, and every receiptless charge for its own company;
    - the overrides are deleted after being archived under the snapshot key `gl_conversion`.
  - When it refuses or writes nothing:
    - it refuses an already-GL, published or trip month, a month with no provisioned company, and a run with no model client;
    - a model failure writes nothing, and neither does a month that changed while the model ran.
  - Tests: `tests/test_gl_conversion.py` (7).
  - 12 wiring points across 201 and 205 were regress-checked. Full suite 3460 passed / 2 skipped; CI 8/8.
- **Live run** (snapshot `vs_V9ka1J80opbTj8gxvqQ59X5` taken first; months switched one at a time):

  | Month | Lines categorized | Charges categorized | Bucket picks retired | Model cost |
  |---|---|---|---|---|
  | July | 154 / 261 | 44 / 57 | 20 | USD 0.025 |
  | August | 91 / 133 | 86 / 92 | 9 | USD 0.032 |
  | September | 38 / 111 | 25 / 25 | 6 | USD 0.020 |

  - Refused lines: 81 have no company yet, 126 the model would not place (mostly AI vendors on Corporate Services, which item 181 covers), and 15 are on Brisken GmbH, which has no curated chart.
  - Read-back: every category is a code, and "category with no account" went from 16/12/12 to 0/0/0. The CSVs name real accounts on 37/34/25 rows.
  - Cold SPA drive in EN: passed, with the login as the only write.
- **Recorded (PR #1359):** item 205 applied, item 206 (a card fix does not re-run the engine), item 207 (the live export gate blanks E700030-30), and the status roll-up. The memory entry was added to `project_brisken_expense_recon_usability_loop`.

## What Did NOT Work (and why)
- **`pytest -n 4`:** xdist is not installed in the module env, so it exits with a usage error. Run serially (about 8 min).
- **The first full-suite run on item 201:** 1 failed. `test_zoho_posting_is_gated` forbids `web/` importing `..zoho`, so the lookup moved to `category_vocabulary`.
- **Item 201 fixtures:**
  - An empty chart diverts every line at the export gate, so the fixture has to hold the real curated accounts.
  - A month created FOR one company gets a single-company gate that blanks a row moved to another company. The live months are created with no company, so the fixture must be too.
- **`flyctl deploy` with a POSIX path under `MSYS_NO_PATHCONV=1`:** flyctl chdir'd to `C:\c\Users\...` and failed. Pass the Windows path.
- **My code regex `^E\d{6}(-\d{2})+$`:** it misread suffix-less leaf codes (`E500010`) as buckets. Use `(-\d{2})*`.
- **The drive's "retired Zoho picker" probe** (`aria-autocomplete=none` plus "|"): it also matches the Paid through select, and flagged two such controls on August.
- **A 78-line heredoc carrying a Python triple-quoted block:** blocked by the heredoc gate. Use the Write tool and run the file.

## Current Status
Fly `071b19d7` runs item 201 and the switch route. July, August and September read `category_vocabulary: "gl"`; the switch is one-way per month (a repeat answers `month_already_gl`). Criss's retired picks sit in each month's `gl_conversion` snapshot key. Ops status: platform unknown plan (no `platform` section for this FastAPI client). Worktrees `agentic-ops1-recat`, `-item201`, `-glconv`, `-glrec` and `-deploy-0925` are merged and clean, ready to prune.

## Next Steps
1. **Item 206:** after any edit that can move a row's company (card_key, a card hint), re-run the engine for the resolved company. Test route-level through the card fix.
2. **Item 207:** read the live chart file's entry for E700030-30 (Cloud 697686691). This is a production read that was refused earlier; put it to the owner. Refresh the chart if it is stale.
3. **Item 181 (Dirk):** registry accounts for Anthropic, OpenRouter, Lovable, Wispr and Rize per company. This removes most of the 126 "model unsure" lines.
4. **Item 196 (owner: land the sure rows),** then item 202 (measure first) and item 195 (red test first).
5. Small leftovers: the sticky `error` on rendered entries; a dead attach leaving a file; the review xlsx (delete only when the `~$` lock is gone and the sha matches); Dirk to export 0113.

## Files to Read First
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 201, 205, 206, 207)
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/gl_conversion.py
- workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md ("Switching a bucket-era month")

## Continuation prompt

````
resume brisken

Continue Brisken p1 expense-recon. Read this whole brief before acting.

Repo: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1`
Module root: `workspace/clients/brisken/automations/expense-reconciliation`
Lovable SPA repo: `011matthias/brisken-expense-review` (live at expenses.brisken.com)

**Zoho token rule: `expenses.CREATE` is strictly NOT authorized for production.
Production orgs remain strictly read-only; writes are locked to sandbox 822116290.**

## 0. Handshake
- `git fetch origin` first; shared clone with live siblings; work in a worktree off origin/main, one branch per item.
- Live Fly = `071b19d7`. Module suite 3460 passed / 2 skipped (serial; xdist is not installed).
- Claim backlog numbers only after grepping `^### ` on origin/main AND the open PR diffs.

## 1. ESTABLISHED (2026-09-25). Do not re-derive.
- July, August and September are GL months (owner directive; Criss's bucket picks IGNORED by owner ruling, archived under each snapshot's `gl_conversion`). The switch is one-way; never re-run it. Restore = snapshot `vs_V9ka1J80opbTj8gxvqQ59X5` or the archive key.
- Item 201 is live: a hand pick's account name is read in the company the row SHOWS (card chain), via `category_vocabulary.gl_leaf_account_name`. `web/` must not import `..zoho`.
- Refusals left on the three months: 81 lines with no company, 126 "model unsure" (AI vendors on Corporate Services: several accounts fit; item 181 is Dirk's registry accounts), 15 Brisken GmbH (no curated chart).

## 2. This session, in order
1. Item 206: a card fix (card_key, card hint) that gives a row its company must re-run the engine for the resolved company, like a company edit does. Route-level test through the card fix; regress-check the trigger.
2. Item 207: the live export gate blanks E700030-30 on Cloud (SendGrid, September) while the local Sep 24 chart passes it. Reading the live chart file is a production read: ask the owner first (AskUserQuestion), then refresh the chart if it is stale.
3. Item 196 (owner: land the sure rows). Then item 202 (measure first), item 195 (red test first).

## 3. Hazards
- Never inject July. Do not write to production orgs. No agent writes on Criss's months beyond an owner order.
- Deploy with `--build-arg GIT_COMMIT=$(git rev-parse HEAD)` from a clean detached origin/main worktree, passing the WINDOWS path to flyctl under MSYS_NO_PATHCONV=1; verify `/healthz` commit, then drive the consumer cold.
- SPA drive: `uv run --with playwright`, headless `channel="chrome"`. On the gate, type the code until Log in enables, then click. GL picker = `button[role=combobox][aria-haspopup=dialog]`; the Paid through select also matches `aria-autocomplete=none` plus "|".
- Leaf codes include suffix-less parents (`E500010`): regex `^E\d{6}(-\d{2})*$`.
- Force-push is gated. Heredocs: no Python triple-quoted blocks, nothing >80 lines. Bash mangles leading-slash args: prefix MSYS_NO_PATHCONV=1.
- The review xlsx `CoA BRISKEN - 6 accounts for Dirk to decide 260924.xlsx`: delete only when the `~$` lock is gone AND sha256 is still `eed95ea3785b1bd7caabde8d8151ec1e0efe57ba9d3e16e7832adb3c8b350789`.

## SESSION LOOP
[Standard checkpointing bands at 300k/500k apply; commit before checkpointing; never start items crossing 500k. End each iteration by listing the remaining queue items. Carry this SESSION LOOP block verbatim into the next continuation prompt.]
````
