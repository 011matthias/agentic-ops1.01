# Mini-Checkpoint: Brisken Recon Categorization Analysis

**Date:** 2026-09-25
**Status:** Build 1 (cause 1) live (PR #1437, Fly `63325aee`); Build 2 code half handed to a fresh session
**Type:** mini

---

## Summary
Build 1's premise was refuted and its real cause fixed. Criss's picks do land: 35 existed until the GL conversion retired them. The defect was that every output decided "who answered" on its own, so her own account on a charge printed `(confirm)` in her statement sheet. One mapping, `answer_origin`, now serves every surface.

## What Was Done
- Pulled the 03:05 UTC SharePoint backup read-only and ran the real app in-process on copies (no model, no live write). On July: a receipt pick and a charge pick reach the grid, `expenses.csv` and `reconciled.csv`, and survive a re-match and the refusal re-run. The three 2026-09-24 learner leaks were already closed in code, and the SPA grid is not locked on statement months.
- Found the 35 human picks (July 20, August 9, September 6) archived in `snapshot.gl_conversion.category_overrides`. The conversion at 2026-09-24 23:17-23:23 UTC deleted them by ruling.
- Reproduced the defect on July's copy: her pick on OPENAI 80.04 printed `COGS - Other Infra and IT Costs for Cloud Business (confirm)`. Six separate source-to-meaning maps disagreed.
- Built `answer_origin()` / `origin_of_source_value()` in `matching/types.py`. The statement sheet, the Zoho journal's receiptless rows, the row review and the report colour now read it, and the payload serves `origin` on `charge_category` / `posting_category`.
- Tests and proof: 18 tests in `tests/test_answer_origin_item_216_cause1.py`, and `test_web_review_state.py` updated to the new rule. Three `regress_check` proofs bit. Local suite 3743 passed plus the 2 updated; CI green after one re-run of a timing flake.
- Deployed via `deploy.py`; `/healthz` reports `63325aee`. Live reads with controls: Supermercado Fenix 134.48 reads `origin: rule`, review none, sheet cell `CorpServ | Travel Expense | Food`. The Lovable control reads `origin: suggestion`, review check, `Marketing Expenses (confirm)`. The August workbench rendered with no error.
- Backlog item 216 records the correction and Shipped row 136. Both memories corrected (categorization analysis: "zero corrections" was wrong; drive replay: the SPA's API host).
- Sized Build 2 on the backup: the model is offered 10-11 parent accounts per company. Model lines on a parent 17 / 5 / 21 and model charges on a parent 23 / 34 / 1 (July / August / September). Model answers that become suggestions: receipt lines 42 / 48 / 43, charges 45 / 89 / 30.

## What Did NOT Work (and why)
- **Taking "0 corrections in seven months" from the payload scan:** a payload shows only live overrides. The conversion had deleted all 35 picks the night before, so the store's archive, not the API, held the answer.
- **First sheet probe:** it read only the run's default statement file, which does not hold the charge. The sheet renders per statement (`?file=`).
- **Browser drive, attempts 1-2:** login typed before hydration (no request fired), then the route guard keyed on `brisken-expense-recon.fly.dev` while the SPA calls `api.expenses.brisken.com`. The guard replayed nothing and would have aborted nothing, and the page made 4 live GETs (each under 1 s, no writes). The workbench's default view does not list answered rows, so the row state was proven from the payload and the sheet file, not the page.
- **CI `test` first run:** `test_drop_speed_item_148::test_parallel_beats_the_serial_wall_clock` hit 0.88 s against a 0.7 s bound on the runner. It passed 3/3 locally with the change; `gh run rerun --failed` went green.

## Current Status
Build 1 is live. On today's months it moves little, because the conversion cleared her picks: August's sheet loses one `(confirm)`, and three August rows stop asking. Every pick from now on prints as hers. The journal's receiptless rows are off on every live month. brisken ops status line from `pre`: platform unknown plan, comms-log none.

## Next Steps
1. Build 2 code half, in a fresh session (continuation prompt handed to the owner). Offer the model leaf-only labels, with `_gl_model_result` refusing a parent as backstop. Then model answers become `suggested_*` everywhere, and counts split person / rule / suggestion. Measure what `expenses.csv` loses before changing it, and put the numbers to the owner if rows she relies on lose an account.
2. Session D (merchant identity) is unblocked now that Build 1 merged.
3. Sessions B and C continue in their lanes (Dirk's draft; the wire-invoice destination question to the owner).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 216, "Cause 1, corrected and built", and Shipped row 136
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/types.py` (`answer_origin`)
- `docs/2026-09-25 - Brisken Recon Categorization Analysis/Mini-Checkpoint-1.md` (the five-session file ownership)
