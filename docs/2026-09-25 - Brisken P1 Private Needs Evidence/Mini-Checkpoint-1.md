# Mini-Checkpoint: Brisken P1 Private Needs Evidence

**Date:** 2026-09-25
**Status:** Shipped, deployed (Fly v225, `f744680b`), live-verified. Session loop done.
**Type:** mini

---

## Summary
Card-attribution case 6 is live: a private expense is suggested only on positive evidence the payment was not Brisken's, and every other payment text waits for the statement, vendor memory and Criss's assignment. Backlog item 203, superseding item 41's trigger; PR #1340.

## What Was Done
- Precondition held: item 198 (#1334) merged at `59354b9b` before any code was cut; the private-card-list item was not merged, so the standalone `cards.positive_non_brisken_evidence(hint, cards) -> reason | None` was built and wired at the one `suggested_private` term in `service.resolve_batch_row_cards`, replacing item 198's `names_registry_card_type` (removed).
- Evidence order: `number` (outranks words), `ending`, `cash`, `network` / `kind` / `issuer` the active cards do not carry (read from label + account, never stored). Conflict within a dimension, or cash beside anything Brisken's, waits. Acquirers and wallets are neutral. Fragments "express" / "club" / "american" count only in the registry's own wording, never in free text.
- `cards.payment_words`: one tokenizer for `is_generic_tender`, `registry_card_types` and the evidence rule (case boundary, 5+ letter prefix split with a 3-letter remainder floor, known words kept whole).
- Seventeen "a card was used" words joined `GENERIC_TENDER_WORDS`; "Link" assigns month-only and is refused as an alias, "CorpServ" is still learned (route-tested).
- Live census before building (read-only, 254 hinted rows): the brief predicted 7 rows losing the suggestion, the measurement found 9 (May and July Lovable "Link" are the same class), 0 gains. The offline 198 model matched live 198 on every row before it was trusted.
- Suite 3320 -> 3417 passed / 2 skipped (+97, the new module). Regress proofs both RED: suggestion wiring (1 failed), tokenizer (5 failed).
- Live after deploy (v225, over the v224 / item 199 baseline): exactly the 8 predicted rows flipped `suggested_private` true -> false with `can_mark_private` true, no other row moved in 7 compared fields, summary counts April 5 -> 4, May 3 -> 0, June 3 -> 2, September 5 -> 4, the rest unchanged. Scripted cold Playwright drive (headless Chrome) of September's Expenses view: 6 chips before, 4 after; OpenAI "saved payment method" clear, Deutsche Post "girocardOLV" kept; only non-GET request = login.

## What Did NOT Work (and why)
- **Claiming backlog item 201 before CI finished:** sibling PR #1339 took 201 and 202 while #1340 was in CI; the merge conflicted and the item became 203 at merge time. Claim the number after the last `merge origin/main`, not before CI.
- **Pinning GoDaddy's "last two digits: 38" as WAIT:** item 199 (#1335) merged mid-CI and reads the worded ending, so with no card ending 38 the phrase is `ending` evidence. It is now a registry-dependent test (with 2838: no evidence).
- **`regress_check.py --file` relative to the worktree root:** it resolves against `--cwd` (the module dir); pass `src/...`.

## Current Status
p1 expense-recon live at `f744680b` (v225). No SPA change needed (the chip hides on `suggested_private: false`). 86 feedback notes, all cited in the backlog. Nothing live was written.

## Next Steps
1. Private-card-list session: fold `positive_non_brisken_evidence` into `cards.classify_payment_evidence` (its step 4 = this evidence list, step 7 = WAIT); a number on that list is private outright.
2. Item 200 (vendor card history) waits on the owner's threshold call; items 201 and 202 (GL hand-picked account exports unmapped; US date read day-first) are open from the GL prompt drive.
3. Named for the owner, not built: PayPal / PIX / boleto / cheque are no private evidence now (no live suggestion carried one); "caixa" on the issuer list is also the Portuguese word for a till.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("Private needs positive evidence")
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 203)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_private_needs_evidence.py` (the classification table is the contract)
