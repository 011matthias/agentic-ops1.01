# Mini-Checkpoint: Expense-Recon Item 81

**Date:** 2026-09-16
**Status:** Backend shipped and deployed (PR #903, merge `6131d698`, Fly v135); SPA prompt pending owner paste
**Type:** mini

---

## Summary

Item 81 (note #43): every cross-currency candidate's `fx` block now carries the receipt converted at the rate the matcher used (`reference_rate`, `reference_rate_source`, `reference_converted`, `reference_gap`, `reference_gap_pct`, `reference_gap_band`), read from the run's frozen config through the matcher's own lookup, so it populated on deploy with no re-match.

## What Was Done

- Live read before building: July 24 and August 3 FX candidates, 0 with `zoho_converted`, every one with a Settings rate (EUR:USD 1.162275, BRL:USD 0.192448). All four named pairs reproduced to the cent; predicted bands 26 `match`, 1 `review` (July NOBRE ATACAREJO, +4.01%).
- `web/service.py`: `fx_reference_lookup` (`build_match_cfg` over `run.config`, then `derive_fx_reference_rates` + `_reference_rate_for`, looked up on the module at call time), built once in `build_view` and passed to `_fx_breakdown` at both call sites; `_fx_reference_fields` does the arithmetic (gap = charge minus converted as printed; pct and band on the unrounded deviation, the matcher's basis). `configured` maps to `settings`; any other source passes through raw.
- Tests: 5 route-level in `tests/test_fx_breakdown.py` (AMAZON + SUPERMEC at the live rates, GBP pair with no rate has no keys, hand match renders `outside` 115.10%, swapping `_reference_rate_for` moves the screen and `ecb_month` passes raw, every `fx_reference` reason carries the printed rate across settings/statement/receipts); 6 absent-or-typed pins in `test_view_contract.py`.
- Regress proofs, all green -> red -> green, re-run after the rebase: candidate call site (9 red incl. the AMAZON test), hand-match call site (1 red), frozen config `run.config` -> `{}` (9 red).
- Suite 1832 -> 1843 alone -> 1855 after rebasing onto #899/#900 -> 1875 after merging #901/#902. CI 7/7 green.
- Docs: `api-contract.md` section, `docs/lovable-fx-reference-prompt.md`, PROMPT-STATUS Not-applied row, backlog Shipped row 47, status row.
- Deployed v135 from a detached `origin/main` worktree; live API re-read: AMAZON 1.162275 / settings / 320.88 / -5.32 / -1.66 / match, SUPERMEC 0.192448 / 8.05 / +0.24 / 2.93 / match, ANTHROPIC 248.96 / -1.64 / -0.66, PETIT TRAIN 37.19 / +0.29 / 0.77; 0 reason/rate drift on either month.
- SPA drive (`agent-browser --session recon-item81`, cold from the login gate): July `/runs/50622baec444` 112 rows and August `/runs/074a7b8905d7` 111 rows render; the AMAZON and PETIT TRAIN summaries and Details panels show today's rows with no "undefined", "NaN" or error boundary. The renderer for the new keys does not exist yet, so this verified no regression plus the API field, not the renderer.

## Current Status

Backend live on v135. `lovable-fx-reference-prompt.md` is Not applied; its five checks (July AMAZON / SUPERMEC / NOBRE amber, August ANTHROPIC / PETIT TRAIN, PT copy) are the drive after the owner publishes.

## Next Steps

1. Owner pastes `docs/lovable-fx-reference-prompt.md`; then run `uv run tools/lovable-bundle-audit.py` for `reference_gap_band` / `wb.fx.referenceRate` and browser-drive the prompt's five checks.
2. Item 82 (ECB monthly rates) adds `reference_rate_source` `ecb_month`; the view already passes it through, the SPA shows it raw until a label is added.
3. Item 23 round 7 renames the `zoho_*` FX keys; `reference_*` are a different quantity and stay.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (section "The FX block at the tool's own rate")
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-fx-reference-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (Shipped row 47, items 82 and 23)

Working notes: a `receipts`-derived rate is re-derived from the month's current pool (collapsed copies and receipts settled elsewhere are not removed), so it can differ from the match-time median; `settings` and `statement` reproduce exactly. `agent-browser wait --load networkidle` hangs on this SPA (it polls); wait on text instead.
