# Mini-Checkpoint: Brisken Recon Account Map

**Date:** 2026-09-25
**Status:** Map derived, tested and proven through the module; write plan and Dirk draft ready, nothing written or sent
**Type:** mini

---

## Summary
Derived the per-company merchant account map from Criss's 24-month Zoho Books card postings (item 216, Build 2 data half), tested it out of sample, bounded the split ceiling, planned the settings write and drafted the one message for Dirk. No code, no settings write, no send.

## What Was Done
- `context/expense-reconciliation/derive_account_map.py` (gitignored; docstring = decision order): descriptor-first merchant key through the module's `clean_vendor_name` / `strip_reference_tokens` / registry `_distinctive`, platform products kept apart (Google Ads vs Workspace, Microsoft Ads vs 365), `code_of` + `is_postable` per org. Outputs `account-map-260925.{json,md}` and `-write-plan.json`.
- Classes: 561 single, 8 majority, 57 split, 58 never-booked (most single rows are one-off meals). Item-180 cross-check: 52 same code, 8 where the list picks one side of a split, 0 different.
- Out of sample (train < 2026-07-01, test Jul to Sep 18, 148 rows): map answers 100, agrees 98 (Cloud 28/28, CorpServ 69/71, Consulting 1/1 untested); open app rows 23/23; USD 7,248 of 7,420 answered. Critic's majority-for-all cut: 114/121. Through the module's own resolver on raw Books text: 86 of 87 decided.
- Proof via `categorize_receipts_with_registry` (client=None, learned=None), one prefetch of Jul/Aug/Sep (8 reads, all under 1 s): live registry 0/164 charges, 0/55 receipts; plus write plan 26/164 (13 join Books, 13 agree) and 4/55; plus Build-3 aliases 7/55; full map incl. gated (count only) 54/164 (15 gated), receipts with Build-3 aliases 34/55 (23 gated).
- Draft `context/drafts/account-map-questions-to-dirk.md`: 11 one-line calls (splits, 7 item-180 questions, parent-account policy); comms critic run, 3 of 4 fixes applied.

## What Did NOT Work (and why)
- **First-word merchant key (critic's `desc_key`):** merges Google Ads/Workspace/Cloud and Microsoft Ads/365 into one merchant, which is where the "Microsoft 23/20/14" split came from; the real Microsoft 365 split is 23 / 15 / 1.
- **Canonical = Criss's majority vendor name:** Books typo "Antropic" became the canonical and the gated-count variant missed the live `Anthropic` entry (exact-key collision); fixed by preferring a vendor name that spells the key.
- **Build-3 simulation keyed on the receipt's own first word:** pulled person names into merchants ("Jose Claudio Cavalcanti" -> "jose"); replaced by the paired charge's descriptor. Only 2 of 55 unsure receipts carry a person-confirmed pairing; 36 are tool-proposed.
- **Books-derived aliases for statement charges:** 14 charges of written merchants still miss. Chase prints `TWILIO SENDGRID WWW.TWILIO.CO CA`; the fuzzy tier discounts every uncovered word (score x covered/total length), so `TWILIO SENDGRID` never clears 88. A resolver gap for Build 3, not patched with per-spelling aliases.
- **Critic finding "58 of 164 unsourced":** it read the main clone's backlog (141 commits behind, no item 216); origin/main item 216 carries the figure.

## Current Status
Map, report, write plan and Dirk draft sit in the gitignored brisken context. brisken ops: platform unknown plan, comms-log none. Worktree `../agentic-ops1-accountmap` (branch `client/brisken/p1-recon-account-map`) is clean, nothing to ship.

## Next Steps
1. Owner reviews and sends the Dirk draft (attach `account-map-260925.md` or the item-180 file).
2. After Dirk answers: rebuild the plan from a fresh `GET /api/settings`, fold his answers into `HOLD_FOR_DIRK` / the split rows, re-run, then one owner-approved `PUT /api/settings` (the three gated vendors stay out; never re-ask the owner about them).
3. Build 3 (canonical merchant resolver) must read bank descriptions: strip reference, URL and state tails before the fuzzy tier; re-run this script's proof to measure (26 -> ?).
4. Re-pull Zoho once Criss books August/September; re-run `derive_account_map.py`.

## Files to Read First
- `workspace/clients/brisken/context/expense-reconciliation/account-map-260925.md`
- `workspace/clients/brisken/context/expense-reconciliation/derive_account_map.py` (docstring)
- `workspace/clients/brisken/context/drafts/account-map-questions-to-dirk.md`
