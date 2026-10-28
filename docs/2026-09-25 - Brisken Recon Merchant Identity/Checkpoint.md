# Checkpoint: Brisken Recon Merchant Identity

**Date:** 2026-09-25
**Status:** Build 3 (item 216 cause 3) coded, measured and regress-proven on branch `client/brisken/p1-recon-merchant-identity` (`432bad83`, pushed); PR held until Build 1 (correction path) merges; alias learner not yet on the memory plan; nothing deployed, nothing written live

---

## Summary

One merchant resolver now decides identity for memory recall, memory capture, the registry match and `_registry_account`. On the live GL months it lifts registry reach on the 55 model-unsure receipts from 13 to 35 and memory recall from 14 to 41, and gives 17 receiptless charges a rule answer at their next re-match: 11 match Criss's own bookings, 0 disagree, 6 are not booked yet.

---

## What Was Done This Session

### Measurement (one read-only prefetch, 9 GETs 15 s apart, all under 0.7 s)
1. July / August / September batch + run payloads, settings (33 merchants), memory (108 rules). Baseline reproduced the brief: registry 4 live / 17 probe(display, raw) / 13 probe(None, raw) of 55; memory 14 of 55; 164 VENDOR-guessed charges, registry 20, memory 14.
2. Candidate identity rules run over 1,562 distinct strings (three months, memory keys, 24-month Zoho descriptors and vendor names), every merge listed, Criss's Zoho `vendor_name` per descriptor as the wrong-merge check.

### Build (worktree `agentic-ops1-identity`)
3. `merchant_identity.py`: `identity_key` (dba -> trading name; handles; card-network location tail `<domain|phone> <ST>`; `www.` + TLD; phone numbers; reference tokens with a glued word kept; brand echo; trailing legal forms incl. PBC/FZCO/DMCC/PLLC/SE) and `MerchantIdentityResolver.resolve(vendor_clean, raw, descriptor=None) -> MerchantIdentity(canonical, key, source, aliases_matched)`.
4. `MerchantRegistry._probe_pairs` probes the identity key last (every earlier exact hit still wins).
5. `MerchantCategoryLookup` folds stored rules by identity at read time (`fold_rows`: person rows outrank seeded; disagreeing spellings are not folded, reported in `.folds`, and keep answering for their own exact spelling). `with_identity(resolver)`.
6. `categorize_receipts_with_registry` hands memory the registry-aware identity; `_recall_for(receipt, learned, match)` asks about the matched canonical.
7. `capture.category_key` keys on the identity; optional `identity` threaded through `category_groups` / `_learn_categories` / `learn_from_run` / `learn_from_expense_run` / `learn_category_candidate`.
8. `capture.identity_alias_candidates` (pure): a PERSON-confirmed pair where exactly one side resolves to a registry merchant proposes the other side's name as its alias; both resolving to different merchants counts a conflict; neither teaches nothing. NOT yet wired.
9. `tests/test_merchant_identity_216.py`, 36 tests. Full module suite 3727 passed / 2 skipped before the new file. Five wiring points each went red under `regress_check` (recall key, categorize's `with_identity`, registry identity probe, capture key, `_registry_account` match recall).

### Prediction (offline A/B, base tree vs build tree, refusing model)
10. `categorize_charges` replay on all 191 unmatched charges: 7 -> 24 answered by a rule, 17 changed, 0 lost. Joined to `zoho-books-24mo.json`: 11 right, 0 wrong, 6 not booked by 09-18 (BASE44 x4 E100020-10, Wix E600010-30-20, DigitalOcean/ServerPilot September E700030-30).

---

## Key Decisions Made

### Read-time fold instead of a one-time store migration
- **Choice:** memory rules are folded per identity when the lookup is built; the store is not rekeyed.
- **Rationale:** same outcome with no live write, the Memory page and the undo journal (item 163) keep their keys, a disagreement simply stays unfolded. Live memory has exactly ONE fold (Corporate Services `anthropic` + `antropic`, decided by the person row) and zero refusals, so a migration would have moved one row.

### The registry's fuzzy tier left as is
- **Choice:** a one-word name inside a longer merchant still scores 100 (`Google LLC` would read as a lone `Google Ads` merchant; `Twilio Inc` as `Twilio SendGrid`).
- **Rationale:** the same rule carries `LOVABLE` -> Lovable Labs on 65 live rows and `KI-MASSA`, `AUTO POSTO PIMENTEL`; all six fuzzy matches on live strings are right. Recorded as a latent limit, not changed.

### What the identity does not strip
- **Choice:** no split on `*`, `.ai` kept, no place names.
- **Rationale:** measured: `MP *`, `TST*`, `WEB*`, `GOOGLE *CLOUD` vs `GOOGLE*PLAY` are processor prefixes as often as brands; memory already holds `perplexity ai`, `fireflies ai`. Those spellings need a registry alias, a person's call.

---

## What Did NOT Work (and why)

- **First identity rule set:** folded `GOOGLE *ADS9208169978` (Google Ads) into `Google LLC` because the reference-token rule dropped the glued `ADS9208169978`. Fixed by keeping a 3+ letter word glued to 5+ digits; re-measured, the merge is gone.
- **First name dump:** 0 guessed charges, because the filter compared `source != "vendor"` while the payload says `VENDOR`. The brief's expected 164 caught it before any number was used.
- **Test registry holding only `Google Ads` / only `Twilio SendGrid`:** the registry's own fuzzy tier matched `Google LLC` / `Twilio Inc` to them (pre-existing behaviour, see Key Decisions). Test registry now holds both merchants of each pair.
- **A 96-line heredoc** for the capture.py threading was blocked by the heredoc-size gate; redone as Edit calls.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/merchant_identity.py` | Created | The resolver and `identity_key` |
| `.../src/expense_recon/merchant_registry.py` | Edited | Identity probe last in `_probe_pairs` |
| `.../src/expense_recon/learning/consult.py` | Edited | Read-time identity fold, `IdentityFold`, `fold_rows`, `with_identity` |
| `.../src/expense_recon/learning/capture.py` | Edited | `category_key` on the identity; `identity` param; `identity_alias_candidates` |
| `.../src/expense_recon/learning/__init__.py` | Edited | Exports |
| `.../src/expense_recon/categorize.py` | Edited | `with_identity` in `categorize_receipts_with_registry`; `_recall_for(..., match)` |
| `.../tests/test_merchant_identity_216.py` | Created | 36 tests incl. the reach fixture and route tests |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edited (feature branch) | Item 216 row records D built, PR held |
| this folder: `prefetch.py`, `dump_names.py`, `measure_identity.py`, `replay_charges.py`, `truth17.py`, `regress_all.py`, `reg_matches.py` | Added | The measurement, rerunnable (payloads not committed: they carry ACH lines with personal names) |

---

## Current Status

Branch `client/brisken/p1-recon-merchant-identity` at `432bad83` (merged `origin/main` once, `d9eb151e`), pushed, no PR. Build 1's worktree `agentic-ops1-reconfix` had no commits and no PR at 05:40 UTC. Live app untouched. brisken ops status line from `pre`: platform unknown plan, comms-log none (no comms in scope).

---

## Next Steps

1. Wait for Build 1's PR to merge (`gh pr list --search "correction" --state merged`), then `git merge origin/main` in `agentic-ops1-identity`; re-run the 36 tests and the full suite.
2. Wire the alias learner: `registry_upserts_from_expense_run` takes `alias_candidates` and adds each alias to its canonical via `_ensure` (so `memory_lessons` shows it as a "new spelling" lesson, ticked by default, `owner_gated` for Anthropic / OpenAI / Lovable); compute candidates from `reviewer_confirmed_tx_ids(decisions)` at BOTH `memory_lessons.py:249` (the plan) and `service.py:~5405` (the save). Pass the registry-aware identity into `learn_from_expense_run` / `learn_from_run` / `category_groups` at the same call sites. Route test: a person-confirmed pair shows the lesson on `GET /api/runs/{id}/memory-plan`; a tool-confirmed one does not; regress_check the wiring.
3. Record the measurement in backlog item 216 (cause 3 build note: reach numbers, merge list summary, the fuzzy-tier limit, the alias list below).
4. PR, merge on green, deploy via `deploy.py` from a clean origin/main tree if no sibling deployed in the last 15 minutes (check `flyctl logs` for `/jobs/` first); cold read-only drive with replayed payloads; state which rows WILL change at the next re-match (the 17 charges above); no live write.

---

## Context for Next Session

### Files to Read First
- This checkpoint; backlog item 216 (`workspace/clients/brisken/status/p1-improvement-backlog.md`, search `### 216.`)
- `.../src/expense_recon/merchant_identity.py`, `learning/consult.py` (fold), `learning/capture.py` (`identity_alias_candidates`)
- `.../src/expense_recon/web/memory_lessons.py` (~L200-L390: registry lessons, `OWNER_GATED_MERCHANTS`), `web/service.py` `registry_upserts_from_expense_run` (~L4885) and its caller (~L5405)

### Open Questions
- Dirk (his hand edit, gated): aliases `ANTHROPIC* CLAUDE SUB` for Anthropic; OpenAI has no registry entry at all (`OPENAI`, `OPENAI OPENAI.COM CA`, `OPENAI *CHATGPT SUBSCR`, `OPENAI* CHATGPT CREDIT`, 29 live rows); the two Lovable entries (`Lovable Labs`, `Lovable Labs Incorporated`) are one merchant in the registry twice.
- Operator edits, not gated: SAP (no entry; `SAP SE`, `SAP SE WALLDORF`, `SAP IRELAND LIMITED DUBLIN 24`, 20 rows), Zoho aliases (`ZOHO* ZOHO-ONE`, `ZOHO_BOOKS`), AT&T (`AT&amp;T MOBILITY EPAY`, `ATT*BILL PAYMENT`), Amazon (`AMZ*Amazon.D*...`). Registry entries for Wispr Flow, Rize, OpenRouter, Railway, Vercel, Pressmaster would take the 55's reach from 35 to 47 (Rize needs `Rize Labs` as its canonical or an alias).

### Working Notes
- Identity consistency on the 219 rows (55 + 164): rows whose merchant has ONE key 75 -> 117.
- Memory: 108 rules -> 107 (company, merchant) identities; the one fold is decided.
- Registry change over all 1,562 strings: 5, all None -> right merchant (Anthropic x4, `WWW.BRAVE.COM`), 0 different canonical.
- Flagged merges (Zoho vendor names differ) are all one merchant: `Antropic`/`Anthropic`, `Open AI - CHAT GPT`/`OpenAI - ChatGPT`, `REgistro Brasil`/`Registro.BR`, one Uber charge posted as DB.
- Receipts change only when re-categorized (new ingest or the refused-rerun route), not at re-match (item 170); charges re-categorize at re-match.
- `regress_check` needs Windows paths in `--test` (`uv run --directory "C:\..."`).

### Reference Materials
- Branch: https://github.com/011matthias/agentic-ops1.01/tree/client/brisken/p1-recon-merchant-identity
- Base tree for A/B replays: `C:/Users/neuma_p1qrsic/Repo/agentic-ops1-identity-base` (detached origin/main `f6db23f2`)

---

## How to Continue

Resume in `C:/Users/neuma_p1qrsic/Repo/agentic-ops1-identity`. Do step 1 of Next Steps before any edit to `service.py` or `memory_lessons.py`; those are Build 1's until its PR is on main.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring candidate rules against Criss's own Zoho vendor names turned "is this merge wrong?" into a listed check: it surfaced the Google Ads fold before any code depended on it.
- An offline A/B of the real categorizer (base tree vs build tree, refusing model) plus a Zoho join gave a prediction with a truth score (11/0/6) instead of a reach count alone.

### Suggestions
- `tools/recon-categorization-score.py` (PR #1435) could take a `--tree` pair and run this A/B itself, so every categorization build states changed rows and their accuracy the same way.

### System Health
- Autonomy: 0 human interventions (fully autonomous session). Gates B1:0 B2:4 B3:0 skipped:0. One heredoc-size block (gate worked; recall of the cap did not).
