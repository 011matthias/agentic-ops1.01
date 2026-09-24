# Checkpoint: Brisken P1 Private Needs Evidence

**Date:** 2026-09-25
**Status:** Item 203 shipped and live (Fly v225, `f744680b`); session loop done

---

## Summary
Card-attribution case 6 is live: the recon tool suggests a private expense only on positive evidence the payment was not Brisken's, and every other payment text waits for the statement, vendor memory and Criss's assignment. Afterwards the owner corrected the closing list, and the item 200 record was fixed so it no longer reads as a pending owner decision.

---

## What Was Done This Session

### Build (backlog item 203, PR #1340)
1. `cards.positive_non_brisken_evidence(hint, cards) -> reason | None`, wired as the last term of `suggested_private` in `service.resolve_batch_row_cards`; item 198's `names_registry_card_type` folded in and removed. Reasons in order: `number`, `ending`, `cash`, `network`, `kind`, `issuer`; a conflict inside a dimension, or cash beside anything Brisken's, waits; acquirers and wallets are neutral.
2. `cards.payment_words` tokenizer shared by every hint classifier; 17 "a card was used" words added to `GENERIC_TENDER_WORDS` (month-only assignment, never an alias).
3. Docs: api-contract "Private needs positive evidence" plus the supersession beside item 41; backlog item 203 + Shipped row 119; status row.

### Verification
1. Offline rule-per-tree census over all 7 live months (254 hinted rows), with the 198 model first checked against live 198 (0 mismatches). The brief predicted 7 rows losing the suggestion; the measurement found 9, 0 gains.
2. Suite 3320 -> 3417 passed / 2 skipped; both regress proofs RED (wiring 1 failed, tokenizer 5 failed); CI green twice (before and after merging #1335/#1339).
3. Live after deploy over the v224 baseline: exactly 8 rows flipped (GoDaddy had already moved with item 199), month counts as predicted; SPA read-back via agent-browser (cold login): 6 chips before, 4 after.

### Records
1. Mini-checkpoint #1344; item 200 corrected to closed-not-built, no decision pending (#1347).
2. Memory: the two duplicate remaining-items memories merged into `feedback_end_iterations_with_remaining_items.md` with the owner's filter; the recon loop memory gained the census method.

---

## Key Decisions Made

### Standalone function instead of the private-card-list order
- **Choice:** `positive_non_brisken_evidence` stands alone; the private-card-list session folds it in later.
- **Rationale:** that item was not merged; the brief allowed this path and required saying so in PR, backlog and contract (done in all three).

### An empty or type-less registry is not special
- **Choice:** Brisken's networks/kinds/issuers come only from the registry; with none, every network word is evidence.
- **Rationale:** one rule, faithful to "positively not Brisken's"; item 198's two fail-safe tests updated ("VISA CREDIT" still suggests there, "card" and "TEF" wait).

### Free-text network words exclude fragments
- **Choice:** "express", "club", "american" count only in the registry's own wording; in a hint only "american express" counts as a phrase.
- **Rationale:** matched anywhere, "Express checkout" or "Club" would have read as amex / diners and suggested private.

---

## What Did NOT Work (and why)
- **Claiming item 201 before CI finished:** sibling #1339 took 201 and 202 mid-CI; renumbered to 203 at the merge.
- **GoDaddy's "last two digits: 38" as a fixed WAIT case:** item 199 (#1335) merged mid-CI and reads the worded ending, so it depends on the registry; now a registry-dependent test.
- **`regress_check.py --file` relative to the worktree root:** it resolves against `--cwd`; pass `src/...`.
- **Post-deploy read-back as a Python Playwright script:** correct result, but invisible to deploy-consumer-gate, so the Stop hook blocked; repeated with `agent-browser --session recon-evidence eval`.
- **Closing list built from ledger lines as written:** listed sibling-owned items 201/202 and presented closed item 200 as "waiting on you"; the owner corrected both.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/cards.py` | edit | evidence rule, tokenizer, vocabulary |
| `.../expense-reconciliation/src/expense_recon/web/service.py` | edit | wiring at `suggested_private` |
| `.../expense-reconciliation/tests/test_private_needs_evidence.py` | new | classification table + route tests (97) |
| `.../tests/test_card_type_not_private.py`, `test_private_suggestion_not_a_card_r3.py` | edit | superseded assertions |
| `.../expense-reconciliation/docs/api-contract.md` | edit | new section + supersession notes |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 203, row 119; item 200 closed |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | status row |
| memory `feedback_end_iterations_with_remaining_items.md` | rewrite | merged duplicate + owner filter |

---

## Current Status
p1 expense-recon live at `f744680b` (v225); nothing written to live data. Platform: unknown plan, ops not assessed (no `platform` section for this FastAPI app on Fly). Feedback notes: 86, all cited in the backlog.

---

## Next Steps
1. Private-card-list session: fold `positive_non_brisken_evidence` into `cards.classify_payment_evidence` (its step 4 = this list, step 7 = WAIT).
2. Item 200's side finding, a small unbuilt fix: remove `learned` from `service._CARD_OBSERVATION_SOURCES` so a remembered card cannot confirm itself into durable memory at sign-off, with a route test through `POST /api/runs/{id}/publish`.
3. Optional owner call: PayPal / PIX / boleto / cheque stay "no private evidence" until one appears (recommended).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("Private needs positive evidence")
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 200, 203)

### Open Questions
- None pending on the owner beyond the optional PayPal/PIX call.

### Working Notes
- Census method: pull every month with GET only, apply each tree's pure rule to the same payload (`new = live_flag AND rule(hint)`), diff per row; predict summary counts from `boxes` (decided copies carry `[]`). Validate the model on a deploy that already happened first.
- "caixa" on `NON_BRISKEN_ISSUERS` is also the Portuguese word for a till; no live hint prints it.

### Reference Materials
- PRs #1340, #1344, #1347; mini-checkpoint in this folder.

---

## How to Continue
The loop is done. Start with `/comd_resume brisken`; pick up Next Step 2 only if the owner wants the learner leak closed, otherwise wait for the private-card-list session.

---

## Strategic Feedback

### What Worked Well This Session
- Validating the offline rule model on item 198's already-live change (254 rows, 0 mismatches) before trusting it made the post-deploy check exact: 8 predicted rows, 8 changed, every month count on target.

### Suggestions
- deploy-consumer-gate could recognise a foreground `uv run <script>` whose script imports playwright and calls `evaluate`/`inner_text`; until then, do post-deploy read-backs with agent-browser or the Playwright MCP.

### System Health
- Ledger lines like "the threshold is the owner's call" outlive the decision they describe; this session relayed one to the owner as pending. Closing lists should read an item's state, not its heading.
- Autonomy: 2 human interventions (both corrections to the closing list).
