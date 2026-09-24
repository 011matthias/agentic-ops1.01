# Mini-Checkpoint: Recon Vendor Card History Gate

**Date:** 2026-09-24
**Status:** Phase 1 measured, gate FAILED, not built; owner decision pending
**Type:** mini

---

## Summary
Brisken p1 item 200 (a vendor's card from its own receipts, gap 1 of the card-attribution map) was measured leave-one-out over all seven live months and failed its own gate: at N = 2, 3 of 21 answered checkable rows are wrong; at N = 3, 1 of 10. Nothing was built. The backlog item records the owner's two rulings, the table, the offending vendors and the recommendation (do not build), in PR #1336.

## What Was Done
- Scratch replay of all 7 live months (305 receipts) through `build_expense_view` on a read-only DB copy (on-machine `sqlite3.backup`, sftp to the scratchpad, local and remote copies deleted after), capturing the card chain's own inputs.
- Index: registry canonical else exact casefolded `clean_vendor_name`; hard evidence = printed Brisken number or `settled_charge`; silencing = pick, assigned alias, two-digit ending; never = learned, merchant, copies, private, settled-outside; OpenAI/Anthropic/Lovable never pinned.
- Wrong rows read back and confirmed real: GitHub (2838 vs 9693, two orgs, two companies), WILLAMS RONALD DA SIL and Supermercado Fenix (Nicolas's 3876 vs Criss's 0340, same company, wrong person).
- Backlog item 200 written (numbered 200: siblings claimed 198 twice); merged origin/main once to resolve the append conflict with item 198.

## What Did NOT Work (and why)
- **Vendor-history card link, N = 2 or N = 3:** leave-one-out gives 3/21 wrong (N = 2) and 1/10 wrong (N = 3); the link would fill only 6 (resp. 4) SaaS rows today.
- **The motivating July Martino "VISA" x3 and Fenix "TEF" x2:** stay blank under the rule, because April shows Martino printed on 0340 and 2838 and Fenix settled on 0340; the premise "only ever paid on 3876" is false in live data.
- **Starting on the precondition:** the card-type item was not on origin/main at session start (sibling commit `cc2d09c9`, unpushed); measured with that commit's classifier, which later merged byte-identical as item 198 (#1334).

## Current Status
PR #1336 (backlog item 200, docs only) open, CI re-running after the main merge; merges on green. No code, no deploy. Owner decision open: build or not, and at which threshold (recommendation: do not build; the six subscription rows resolve safely via a card typed on the merchant in the Merchants editor).

## Next Steps
1. Owner rules on item 200 (do not re-raise; recorded in the backlog).
2. Separate from item 200: the sign-off card learner (`service._CARD_OBSERVATION_SOURCES`) memorizes `learned`, `hint` and `settled_charge` observations into the registry's `cards_seen` / learned `card_key`; under the 2026-09-24 "only corrections may be memorized" ruling that is a fourth leak. Minimal fix = drop `learned`, with a route-level test through `POST /api/runs/{id}/publish`. Needs an owner go since it was part of the gated build.

## Files to Read First
- workspace/clients/brisken/status/p1-improvement-backlog.md (item 200)
