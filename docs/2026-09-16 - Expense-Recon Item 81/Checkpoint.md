# Checkpoint: Expense-Recon Item 81

**Date:** 2026-09-16
**Status:** Backend live (PR #903, Fly v135); SPA prompt pasted into Lovable by the owner and running, not yet published or verified

---

## Summary

Backlog item 81 (note #43) shipped end to end under the parallel-round protocol: every cross-currency candidate's `fx` block carries the receipt converted at the rate the matcher used, and the Lovable prompt that renders it is now running in the owner's Lovable project.

---

## What Was Done This Session

### Build (PR #903, merge `6131d698`)
1. `web/service.py`: `fx_reference_lookup` + `FxReference` + `_fx_reference_fields`; `build_view` builds the lookup once and passes it to `_fx_breakdown` at both call sites (auto candidate, synthesized hand-match candidate). Six parallel keys: `reference_rate`, `reference_rate_source`, `reference_converted`, `reference_gap`, `reference_gap_pct`, `reference_gap_band`.
2. Tests: 5 route-level in `tests/test_fx_breakdown.py`, 6 parametrized absent-or-typed pins in `tests/test_view_contract.py`.
3. Three `regress_check` proofs (candidate call site, hand-match call site, frozen config), each re-run after the rebase.
4. Suite 1832 -> 1843 alone -> 1855 after rebasing onto #899/#900 -> 1875 after merging #901/#902. CI 7/7.

### Ship + verify
1. Deployed v135 from a detached `origin/main` worktree; live API: AMAZON `1.162275 / settings / 320.88 / -5.32 / -1.66 / match`, SUPERMEC `0.192448 / 8.05 / +0.24 / 2.93 / match`, ANTHROPIC `248.96 / -1.64 / -0.66`, PETIT TRAIN `37.19 / +0.29 / 0.77`; July 23 `match` + 1 `review`, August 3 `match`; printed rate appears in every `fx_reference` reason.
2. SPA drive, cold from the login gate: July (112 rows) and August (111 rows) render, FX summaries and Details unchanged, no "undefined" / "NaN" / error boundary. Renderer for the new keys not verified (it did not exist yet).
3. Mini-Checkpoint-1 on PR #906; cleanup proofs clean.

### Delivery
1. `docs/lovable-fx-reference-prompt.md` handed as text, then re-handed as one fenced block on the owner's ask; owner is running it in Lovable now.

---

## Key Decisions Made

### The rate comes from the run's frozen config, through the matcher
- **Choice:** `cli.build_match_cfg(run.config)` then `deterministic.derive_fx_reference_rates` and `deterministic._reference_rate_for`, looked up on the module at call time; no read of live Settings.
- **Rationale:** the screen must show the rate the month was matched against, the fields must appear on deploy with no re-match, and a test can swap `_reference_rate_for` to prove there is no second derivation.

### Arithmetic split between display and decision
- **Choice:** `reference_gap` = charge minus the converted amount AS PRINTED; `reference_gap_pct` and the band use the unrounded deviation.
- **Rationale:** the two printed figures add up to the charge to the cent, and the band agrees with the matcher's own 3% / 13% test (SUPERMEC 2.9309% stays `match`).

### Source is an open enum without a parallel label field
- **Choice:** only `configured` is renamed (`settings`); every other source passes through raw, and the prompt tells the SPA to show an unknown value raw.
- **Rationale:** item 82 adds `ecb_month`; the SPA fallback is the rule-5 mitigation without a seventh key the brief did not ask for.

### Receipts-derived rates re-derived from the current pool
- **Choice:** accept and document the residual rather than mirror the matcher's pool filters (collapsed copies, foreign claims) in the view.
- **Rationale:** most `build_view` callers pass no duplicate resolutions, so a mirror would be inconsistent across routes; no live month uses a receipts-derived rate.

### Summary line placement
- **Choice:** the reference line replaces only the no-Zoho branch of `FxSummary`; every `zoho_*` conditional untouched; `FxPanel` adds three rows before "This match needs".
- **Rationale:** item 23 renames `zoho_*` in round 7; an expense-report PDF receipt still fills them.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` | Edit | lookup, fields, both call sites |
| `.../tests/test_fx_breakdown.py` | Edit | 5 route-level tests |
| `.../tests/test_view_contract.py` | Edit | 6 absent-or-typed pins |
| `.../docs/api-contract.md` | Edit | `fx.reference_*` section |
| `.../docs/lovable-fx-reference-prompt.md` | Create | SPA half |
| `.../docs/PROMPT-STATUS.md` | Edit | Not-applied row |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edit | item 81 SHIPPED, Shipped row 47 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | status row |
| `docs/2026-09-16 - Expense-Recon Item 81/Mini-Checkpoint-1.md` | Create | protocol mini checkpoint (PR #906) |
| memory `feedback_prompts_are_pasteable_text.md`, `project_brisken_expense_recon_usability_loop.md` | Edit | outer-fence rule; item 81 state |

---

## Current Status

Backend live on v135 and verified field by field on both months. The prompt is pasted and running in Lovable; PROMPT-STATUS still reads Not applied, which stays correct until the bundle audit. brisken ops line from pre-flight: `platform: unknown plan, ~?/? ops/mo. Last assessed: ?.`

---

## Next Steps

1. After the owner publishes: `uv run tools/lovable-bundle-audit.py` for `reference_gap_band`, `reference_rate_source`, `wb.fx.referenceRate`, `wb.fx.receiptIn`, `wb.fx.source.settings`; then browser-drive the prompt's five checks (July AMAZON / SUPERMEC / NOBRE amber, August ANTHROPIC / PETIT TRAIN, PT copy); move the PROMPT-STATUS row to Applied and update the status row.
2. Fix `deploy-consumer-gate.py` `backgrounded()`: also treat a foreground call the harness moved to the background on timeout as not-yet-observed; add the case to `tools/tests/test_deploy_consumer_gate.py` with a regress proof.
3. Fix `tools/checkpoint_scaffold.py`: `finalize` must reuse `pre`'s target when that file already exists (it renumbered Mini-Checkpoint-1 to -2), and the skill text should show `--root` before the subcommand.
4. Stop-hook advisory for prompt hand-over (see Suggestions); third recurrence of the rendered-markdown prompt.
5. Item 82's prompt adds a `wb.fx.source.ecb_month` label.
6. Add a `platform` block for brisken p1 to `infrastructure.yaml` (Fly `brisken-expense-recon`, always-on, 1024 MB, `recon_data_v2`) so pre-flight stops printing unknowns.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-fx-reference-prompt.md` (section 7 is the verification script)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`, section "The FX block at the tool's own rate"
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`

### Open Questions
- None for the owner. The receipts-derived residual is recorded, not open.

### Working Notes
- `agent-browser wait --load networkidle` never settles on this SPA (it polls); use `wait --text "<vendor>"`. Charge rows carry `id="charge-{transaction_id}"`, which makes a DOM `eval` probe exact.
- Vault entry "Expense Recon App" prints the login code as `operator_code`; `POST /api/login` returns `token`.
- Live transaction ids: July AMAZON `1f01a80db08f72b0`, SUPERMEC `aaf3a54ba1b179cf`, NOBRE `aa0d0e77d1ea210c` (its only candidate is not chosen, so check 3 needs the candidate expanded); August ANTHROPIC 247.32 `f841620f320f2dc4`, PETIT TRAIN `b05298fff3363d0e`.
- `gh pr list --search "item N"` matches sibling PR BODIES that cite item N (#905 cited #903); use `in:title` for the cleanup proof.
- A prompt that contains its own ``` fences must be handed inside a longer outer fence (````), or the reply renders it as markdown and it cannot be copied.

### Reference Materials
- PR #903, PR #906; Fly release v135
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

---

## How to Continue

`/resume brisken`, then wait for the owner's publish signal (or run the bundle audit if they say it is published) and work Next Step 1. Steps 2 and 3 are system-dev items for a `sys` session, not this client branch.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the four named pairs off the live API and recomputing them before writing any code meant every number in the tests, the contract and the prompt's checks came from Criss's real data, and the post-deploy read matched to the cent with nothing to reconcile.
- Enforcing "no second derivation" by swapping `deterministic._reference_rate_for` in a route test turned a design instruction into something that fails loudly if someone later reads Settings directly.

### Suggestions
- Build the structural check for prompt hand-over: a rendered-markdown Lovable prompt in a final reply has now cost the owner a re-ask three times (item 61 on 2026-09-15, items 80 and 81 on 2026-09-16), and the memory was updated after each. A Stop-hook advisory that fires when a reply names a `lovable-*-prompt.md` and carries `## ` headings outside any fence would catch all three.

### System Health
- The parallel round cost two conflict rounds in six shared files in one hour, including a Shipped-row number collision (items 80 and 81 both took 46). Append-at-end still collides when two siblings append to the same end; assigning the Shipped row number at merge time would remove the renumbering step.
- **Autonomy:** 1 human intervention (the owner re-asked for the prompt as one copyable block).
