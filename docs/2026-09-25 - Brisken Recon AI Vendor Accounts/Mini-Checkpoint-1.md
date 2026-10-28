# Mini-Checkpoint: Brisken Recon AI Vendor Accounts

**Date:** 2026-09-25
**Status:** Item 219 shipped, deployed (`9d945667`) and written to live settings; loop queue empty
**Type:** mini

---

## Summary
OpenAI and Anthropic now carry decided per-company accounts that post as a rule and that no learner can re-point (`accounts_locked`, backlog item 219, owner raised the gate). A booking against a decided account comes back on the Publish checklist as one unticked "change the default" lesson.

## What Was Done
- Owner answered one design batch (all three recommendations): the flag on the merchant entry; 4 decided cells (Anthropic and OpenAI x Cloud Services `E700030-19` / Corporate Services `E700030-30`); the drift lesson. Lovable and Consulting stay with Criss until Dirk answers.
- PR #1457 (squash `9d945667`): `merchant_registry.ACCOUNTS_LOCKED` (settings PUT keeps a stored flag when omitted), `registry_upserts_from_expense_run` skips locked merchants (`skipped_locked`), `memory_lessons._drift_lessons` + `apply_selection`. `tests/test_decided_accounts_item_219.py` (11), regress_check red on 5 wires, suite 3870 passed, CI 8/8 green. Deployed with `deploy.py`; memory plans identical before and after the deploy.
- Settings write on the owner's yes: Anthropic (aliases, accounts, lock), new OpenAI entry (2 descriptor aliases, accounts, lock). The second write, also on the owner's yes, set `OpenAI.cards_seen = ["3645","card-9693"]` (see below).
- Measured: offline proof 46 of 52 gated charges decided (19/19 joined agree; baseline 15), 20 of 31 gated receipts (baseline 23; the 3 Lovable held). Live score map section: 32 answered, 32 agree, 0 broken. The SPA was driven cold (Settings > Merchants) and renders both entries' accounts.
- Backlog item 219 + status paragraph written in this docs PR.

## What Did NOT Work (and why)
- **The first settings write alone:** the new OpenAI entry had no `cards_seen`, and `MerchantRegistry.vouches_one_card` answers yes for `len(cards_seen) <= 1`, so Criss's minority remembered card 3645 lent itself at read time to 6 September OpenAI receipts (card 3645 / Corporate Services instead of "No card on this receipt"). The post-write read caught it; the second write fixed it; all 224 receipts on the three months read as before.
- **Heredoc with a Python triple-quoted block to patch the proof script:** blocked by the heredoc gate, the same dead end the WHAT NOT TO RETRY list already named; Edit calls did it.
- **`pytest -n auto`:** this project has no xdist; exit 4 before any test ran.

## Current Status
Live on Fly `9d945667`. Decided accounts written; charges take them at each month's next natural re-match, existing receipts only when re-categorized (a new ingest or the owner-ordered refused-rerun). No drift lesson on any live month (no booking disagrees). No SPA paste needed. Open finding: any merchant added in Settings with no `cards_seen` vouches one card (`<= 1`); item 173's call, needs measurement over the 28 seeded merchants first.

## Next Steps
1. Owner: send Dirk the draft `context/drafts/account-map-questions-to-dirk.md` (questions 1, 5, 8 decide Lovable Corporate Services, OpenAI's older split and every Consulting cell); on his answers, add those cells to the locked entries by a settings write.
2. Owner decision (not queued): whether `vouches_one_card` should require exactly one observed card (`== 1`), measured first over the seeded merchants with no `cards_seen`.
3. After Criss's next natural re-match of July/August/September: re-run `tools/recon-categorization-score.py` on the three batches to read the charges that moved to the decided accounts.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 219
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "Decided accounts: `accounts_locked`"
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/memory_lessons.py` (`_drift_lessons`)
