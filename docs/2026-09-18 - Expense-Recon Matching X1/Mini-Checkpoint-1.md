# Mini-Checkpoint: Expense-Recon Matching X1

**Date:** 2026-09-18
**Status:** shipped, deployed (Fly v186), cold-driven; checkpoint pending merge
**Type:** mini

---

## Summary
Owner note X1 (backlog item 151, PR #1096, merge `232c7d53`): the statement description now counts correctly in matching (its reference tokens no longer dilute the merchant score) and the no-card fallback is defined once (`card_evidence`), with a review clause for a no-card receipt that two cards' charges both fit. Measured first on July, August, September and the six bundles; the description-token promotion and the masked-fragment rule were measured as dead ends and not built.

## What Was Done
- Measured before (read-only DB copy, `tools/recon-match-attribution.py` on the branch tree): July 30 right / 0 wrong, August 6 right / 1 wrong (`0025` on BASE44 50.00, item 133, pre-existing), September 0 charges (49 receipts, 27 naming no card), bundles 70/95; one shared-token pair in nine datasets (`Microsoft-G173514057` / receipt `G173514057`, already exact and unique); 0 masked card digits in any description; the no-card review clause would fire 0 times (its one candidate, July `0063` Marinho vs GITHUB 10.00, is spoken for).
- Shipped in `matching/deterministic.py`: `strip_reference_tokens` + knob `vendor_ignore_reference_tokens` (July Microsoft `vendor_pct` 50 to 100 at the next re-match, crossing the self-confirm floor 75; Amazon `Z11US7DF5` 57 to 100; bundle CASUALFOOD 0.50 to 1.00 and 0.43 to 0.64, 7-ELEVEN 0.50 to 1.00 and 0.46 to 0.92, no class moves); `card_evidence(tx, receipt)` on every candidate as `card_evidence: {receipt, charge}`; the review clause `review_code: no_card_rival_on_other_card` + knob `no_card_rival_review`; `Match.review_code` persisted. Contract section, view-contract pin, Lovable prompt `docs/lovable-no-card-evidence-prompt.md` (not applied), PROMPT-STATUS row, backlog item 151 + Shipped row 91, status row.
- Verified: suite 2513 collected before, 2541 passed / 2 skipped after the merge from main; three `regress_check.py` runs each RED on a named route-level or gate test; CI green twice (before and after merging main, where M1 and T2 took 149, 150 and row 90).
- Deployed Fly v186 from a detached worktree at `232c7d53`; authenticated API read: 41 of 41 July candidates and 10 of 10 August carry `card_evidence` (July receipt sources printed 5 / hint 16 / none 20), `review_code` on 0; cold headless-Chrome drive of `/runs/50622baec444` (Matched box, decided rows) rendered the Microsoft row with its receipt, no fallback, login POST the only non-GET.
- Memory `project_brisken_recon_matching_program` appended with the X1 outcome and the two dead ends.

## What Did NOT Work (and why)
- **Reference tokens shared between description and receipt numbers as a promoting signal (tie-break, uniqueness dominance, merchant precedence):** exactly one such pair across July, August, September and the six bundles, already exact and unique, and `reference_match` already fires on it; 0 rows move, so it was not built (the prompt's own stop rule).
- **A masked card fragment inside a statement description as card evidence:** none exists on any of the nine datasets; not built.
- **The first token scan glued hyphenated tokens** (`Microsoft-G173514057` read as one token) and reported 0 shared pairs; fixed by splitting on every non-alphanumeric before the measurement was trusted (instrument-validity check, B2).
- **`gh pr create --repo akkton/agentic-ops1`:** the remote is `011matthias/agentic-ops1.01` (memory `reference_repo_tooling_gotchas`); the first merge attempt then hit conflicts because #1095 (T2) landed on the four shared files in between; resolved by merging main and keeping both sides.

## Current Status
Live (v186) with the fields on every candidate; the stored July outcome still shows Microsoft `vendor_pct` 50 until Criss's next natural re-match (no live write made, per `feedback_recon_no_live_writes_criss_acts`). September's statement is the first live test of the review clause. Item 41 (suggest private) and item 72 (raw vs effective) untouched. brisken platform: unknown plan (no `platform` section in `infrastructure.yaml`).

## Next Steps
1. Owner pastes `docs/lovable-no-card-evidence-prompt.md` (three EN/PT-BR strings, one line under a candidate), then `uv run tools/lovable-bundle-audit.py`.
2. When September's statement lands, read `review_code` counts on `GET /api/runs/51a22ad72864` and the attribution replay; 27 no-card receipts are the population.
3. Do not re-run the two dead ends above without a freshly labelled month that carries shared reference tokens.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 151 and Shipped row 91
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "Matching when the card cannot be identified, and the description's reference tokens (item X1)"
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_match_x1_description_and_no_card.py`
