# Checkpoint: Brisken Recon ECB Band And Merchant Precedence

**Date:** 2026-09-17
**Status:** Items 93, 90 + 132 and 133 rule (b) shipped, deployed (Fly v167, v170) and recorded; stopped at HIGH pressure (~500k)

---

## Summary
Three queue items closed end to end. The ECB monthly rate now has its own 2% clean band, measured at five settings before the number was chosen, and a Settings rate that has drifted from it says so per month. An exact-amount pair from the wrong merchant now yields the receipt to the right merchant. The untrusted-text flag got its Portuguese copy as a prompt.

---

## What Was Done This Session

### Step 0
1. `/feedback.jsonl` holds 69 notes; the last recorded is #69, so nothing new. Sibling check found 3d5a3bae running the parallel queue (it shipped 101, 96/97, 131 + 133's bulk half, 112/111 and the note prompts, then checkpointed) and a fresh session registered on its handoff queue, so items were taken from the end of that queue.

### Item 93 (PR #1041, docs only)
1. `docs/lovable-untrusted-flag-prompt.md`: EN + PT copy for `expx.review.reason.untrusted_instructions` and the six kinds, and each `untrusted_instructions[].quote` rendered as plain text under the reason (never markup, never a link).
2. Live read first: 0 of 135 expense rows across the six months carry a flag, and every row already carries the key. PROMPT-STATUS row + backlog heading tagged.

### Items 90 + 132 (PR #1048, Fly v167; record #1050)
1. `MatchingConfig.fx_ecb_match_pct` (0.02) with one home, `reference_match_pct(source)`, read by `match_one`, `pair_reference_gap_band` (item 131's floor rule) and the view's `FxReference`. Settings and self-derived rates keep 3%.
2. The number was measured before it was chosen, on a read-only DB copy with the Settings rates removed: July 29 / 31 / 32 / 33 / 33 right at 3 / 2.5 / 2 / 1.75 / 1.5%, coincidental auto-matches 2 / 2 / 1 / 1 / 1, August unchanged; six bundles on ECB rates alone 68 / 70 / 70 / 70 / 69 of 95, 0 wrong.
3. `setup_advisories[]` gains `code: "fx_rate_drift"` with pair, both rates, the month, the gap and the receipt count when a typed rate sits more than 1 point (3% - 2%) from the month's ECB average.
4. Adversarial review: band wiring clean at all three consumers; three findings fixed with tests (`1e30` failed the whole month, a lower-case Settings key gave a false advisory, nothing pinned that derived rates keep 3%). One residual documented.
5. Suite 2263 on the merged tree; 10 route-level tests; ten regress proofs by hand, all red. Live at deploy: July's 24 and August's 3 FX candidates all read `settings` / `match`, no month carries the advisory, both Matching pages driven cold.

### Item 133 rule (b) (PR #1053, Fly v170; record #1054)
1. An exact-amount same-currency pair whose merchant disagrees reads `requires_review` at 0.55 with "the merchants differ", but only against a rival charge for the same receipt whose merchant agrees, where that receipt is the rival's own first choice and the rival is not awaiting a human pick; applied after the ambiguity pass.
2. Replay old vs new over July, August and the six labelled bundles: 0 receipts moved, as the backlog entry predicted. Scorer 76.0, guard PASS.
3. Adversarial review found two defects in the first draft, both reproduced and pinned by matcher-level tests: a rival that will take a better receipt of its own could strand this receipt, and the demotion could break a pass-1 tie a person should settle.
4. Suite 2281 on the merged tree; 11 tests; six regress proofs by hand, all red.

---

## Key Decisions Made

### 2% for the ECB band, not the measured optimum
- **Choice:** 2%, though 1.75% resolved one more July receipt.
- **Rationale:** 1.5% loses a holdout bundle pair, so a true pair sits between 1.5 and 1.75%; 2% keeps headroom above it for a volatile month, and the cost is one receipt (E A LOCACOES) sitting in review with its right charge first.

### An ECB-only knob, not a tighter shared band
- **Choice:** a new `fx_ecb_match_pct`, leaving `fx_reference_match_pct` alone.
- **Rationale:** the S1 optimize run refuted 1.5% for the self-derived path, which needs its 3% headroom; scoping the change to the ECB rung leaves the scorer asset (76.0) and every month matched at a Settings rate byte-identical.

### The drift advisory's threshold is derived, not picked
- **Choice:** fire above `fx_reference_match_pct - fx_ecb_match_pct` (1 point).
- **Rationale:** a receipt the ECB rate pairs within 2% stays inside a typed rate's 3% band only while the two rates are within 1 point; the number moves with the knobs instead of being a constant to defend.

### Rule (b) built, rules (1) and (3) not
- **Choice:** build only the precedence rule.
- **Rationale:** the entry's own measurement refutes rule (1) as written (no floor fits between 0.40 and 0.42) and rule (3) contradicts item 137's design call; rule (b) moves nothing on eight datasets while closing the shape where the right charge lists no candidate at all.

---

## What Did NOT Work (and why)
- **Multi-line anchors in the by-hand regress scripts:** the module sources are CRLF, so a `"...\n..."` anchor matched 0 times and the run aborted before mutating (nothing was changed); fixed by translating anchors to the file's own newline.
- **A heredoc for the test append and for the conflict resolver:** refused twice by the heredoc gate (a Python triple-quoted payload, then a double backslash); redone with Edit and with a Write-then-run script.
- **Asserting the matcher's reason text in the route test:** the judgment layer replaces `reason` with the model's, so the band wording is pinned on `match_one` directly instead.
- **`gh pr merge` on the record PR straight after a green poll:** a sibling had merged into the same backlog rows, so the PR was CONFLICTING and the merge silently did nothing; resolved by merging main, keeping main's rows first and renumbering mine to 80.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `expense-reconciliation/src/expense_recon/matching/deterministic.py` | Edit | `fx_ecb_match_pct` + `reference_match_pct`, `_pct_text`, `_merchant_precedence` |
| `expense-reconciliation/src/expense_recon/web/service.py` | Edit | band at the view's `FxReference`, `_fx_rate_drift_advisories` |
| `expense-reconciliation/src/expense_recon/cli.py` | Edit | judgment-layer docstring: the band now follows the rate's source |
| `expense-reconciliation/tests/test_ecb_band_item_132.py` | Create | 10 tests |
| `expense-reconciliation/tests/test_same_amount_other_merchant_item_133.py` | Edit | +5 tests (shape, no-rival pin, three matcher edges) |
| `expense-reconciliation/docs/api-contract.md` | Append | two sections |
| `expense-reconciliation/docs/lovable-untrusted-flag-prompt.md`, `PROMPT-STATUS.md` | Create/Edit | item 93 SPA copy |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | Edit | items 93, 90 + 132, 133 records (Shipped rows 71 and 80) |

---

## Current Status
Live: Fly v170 (133 on top of 132's v167 and the siblings' v166). Both new behaviours are inert on today's months by design: July and August match at the Settings rates, which win over the ECB, and no live pair meets rule (b). The ECB band reaches live rows once the owner removes the two Settings rates (item 90 step 4, a per-action owner yes). brisken ops status: platform unknown plan (no `platform` assessment in `infrastructure.yaml`). Comms log: none. Stale status files `p2-product-decks` (56d) and `p2-targeting` (57d) belong to p2 workstreams not touched here.

---

## Next Steps
1. Sibling-claim check, then the queue: 103, 130, 115 (a fresh session is running 3d5a3bae's handoff queue in that order, so take from its end).
2. Items 139-142 wait on the owner: the SPA prompts to paste, and 140's licence class.
3. Item 90 step 4: offer the owner the removal of the two Settings FX rates (EUR:USD 1.162275, BRL:USD 0.192448), which is what makes the new band reach live months.
4. Add a platform feasibility assessment to brisken `infrastructure.yaml` (carried pre-flight flag).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (grep `### 103.`, `### 130.`, `### 115.`)
- memory `project_brisken_expense_recon_voids_audit`, `project_brisken_expense_recon_usability_loop`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `feedback_loop_iterations_list_remaining_items`
- `automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

### Open Questions
- None blocking. The owner's call on removing the two Settings rates decides when the ECB band starts moving rows.

### Working Notes
- Band simulation: `scratchpad/sim/sim132.py` (attribution tool imported, `cli.build_match_cfg` patched to drop the Settings rates and inject an ECB table; the pinned scorer's `evaluate_bundle` called with a modified config). ECB table cached at `scratchpad/sim/ecb-table.json`.
- Replay old vs new: `scratchpad/sim133/replay133.py` runs `tools/recon-match-attribution.py` from two trees (a detached origin/main worktree is "old") and diffs the per-receipt JSON.
- Regress proofs: `scratchpad/regress132.py` / `regress133.py` (backup, single replace translated to the file's newline, targeted pytest, restore, byte-identical assert).
- Cold SPA drive: `scratchpad/drive132.py` (headless Chrome, code from `context/.env`, reads both Matching pages back and prints non-GET requests).
- A sibling merged owner rulings meanwhile: both July invoices were restored on the owner's order (Tricarico recorded as a wire transfer), and `intake.alert_recipients` is now Criss + Matthias.

### Reference Materials
- PRs #1041, #1048, #1050, #1053, #1054; Fly v167, v170

---

## How to Continue
Paste the continuation prompt from the chat into a fresh session; it carries the pressure-stop, the checkpoint and the "list what's left" loop.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring five band values against labels before picking one, and reporting the one the data preferred (1.75%) next to the one shipped (2%) with the reason for the difference. The same habit caught that 1.5% loses a holdout pair, which no single-point measurement would have shown.
- The adversarial reviewer paid for itself twice: three fixable findings on 132 and two real defects on 133 that the planned tests and a 0-change replay both missed.

### Suggestions
- `tools/regress_check.py` (and any by-hand equivalent) should translate multi-line anchors to the target file's newline. Every CRLF source in this module makes a literal `\n` anchor match zero times, which reads as "the anchor is wrong" rather than "the file is CRLF"; it cost a run here and is already in the register from an earlier session.

### System Health
- The deploy-consumer gate still advises "STILL NOT DRIVEN" after a headless Playwright drive that reads page text back, because it only recognizes agent-browser and Playwright MCP calls. Third session in a row; the advisory now reads as noise, which is the failure mode the gate's own rule warns about.
- Autonomy: 0 human interventions (fully autonomous session).
