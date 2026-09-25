# Checkpoint: Brisken Recon Categorization Analysis

**Date:** 2026-09-25
**Status:** Analysis complete, recorded as backlog item 216 (PR #1427 merged `79cfdf05`); four owner decisions taken; build session next

---

## Summary

Measured why half the receipts on the GL months carry no account, scored the engine against Criss's own Zoho postings for the first time (21 of 97 answered charges agree; rules right, model wrong), ranked the levers, had six independent skeptics plus a critic re-derive every claim, and put four decisions to the owner. No code, no deploy, no live write.

---

## What Was Done This Session

### Measurement (offline, one prefetch)
1. Prefetched every month once (`GET /api/expense-batches/{id}` + `GET /api/runs/{id}`, 15 s apart, all under 2.2 s), plus settings, memory, cards status and the 87-note feedback store.
2. Baseline under the screen rule: July 33/71, August 29/50, September 32/68 categorized; 95 open receipts = 55 model unsure + 35 no company (24 waiting for a statement) + 5 partial. The screen's counts agree row for row.
3. Ground truth without a Books call: `context/expense-reconciliation/zoho-books-24mo.json` (pull 2026-09-18) holds Criss's July postings for all three companies. Joined 135 charge rows (company + amount + date within 3 days). Registry 9/9 on real codes, memory 2/2, model line read 1/11, model descriptor guess 9/74. On the 23 rows she still had to book: right once.
4. Lever replays through the module's own code (`MerchantRegistry.resolve` + `company_account`, `_categorize_one_gl` with a fake client) and the item-180 suggestion list.

### Verification (Workflow, 7 agents, 28 min)
5. Six skeptics with distinct lenses (recount, stricter join + name-resolution audit, vendor matching, code trace + offline tests, export code trace, guard measurement) and a completeness critic. All six returned; three claims were corrected before anything was written (see What Did NOT Work).

### Record and decisions
6. Backlog item 216 written with the verified numbers and the ranked lever table (PR #1427, merged on green).
7. Owner decisions via AskUserQuestion: (1) derive the per-company account map from history, route split vendors to Dirk, then write the uncontested rows; (2) a receiptless charge takes an account from a rule or a person only, the model's guess is a labelled suggestion; (3) the correction path is the first build; (4) a model pick may not land on a parent account, people and rules may.
8. Memory `project_brisken_recon_categorization_analysis.md` written and indexed.

---

## Key Decisions Made

### Truth is Criss's booking, stated as such
- **Choice:** "right" means the account Criss posted to; where Dirk might post differently (Google to Google Ads) her booking still counts.
- **Rationale:** it is the only ground truth that exists; the chart's intent is Dirk's to state, and the write-up says which one each number is.

### Owner's four rulings (2026-09-25, this session)
- **Choice:** account map derived and written after Dirk answers the split vendors; rule-or-person-only accounts on receiptless charges; correction path first; no parent picks by the model.
- **Rationale:** each was the recommended option with its consequence stated; the three gated vendors were counted, never proposed.

---

## What Did NOT Work (and why)

- **"Fix the one taught memory rule and the Anthropic receipts get decided":** refuted by an end-to-end offline run. Memory recall keys on `receipt.detected_vendor` (`categorize.py` ~640, ~882); the receipts read `Anthropic, PBC`, which never normalizes to the rule key `anthropic`. 19/19 stay refused with or without the fix; the fix changes 14 of 15 receiptless Corporate Services ANTHROPIC charges through the registry tier.
- **"The account list decides 47 of the 55 unsure receipts":** through the app's own path (`_registry_gl` fires only on a registry match) it decides 4 (live `vendor.source`) to 17 today; the extraction names (`Anthropic, PBC`, `Wispr AI, Inc. (dba Wispr Flow)`, `Rize Labs, Inc.`) have no registry alias. My 39 came from a synthetic registry that already carried aliases.
- **"The wrong guesses would post to Zoho":** no web path writes a receiptless VENDOR guess into `zoho_journal.csv` or `expenses.csv` (receipt-first); the poster reads only the latter. The guess reaches `statement-categorized.xlsx` as `<account> (confirm)`, `report.xlsx`, `reconciled.csv` and the PDF (unlabelled).
- **Seeded rules "14/14 right":** with the engine's exact recall key it is 4/4; my longest-prefix matcher counted rules the engine would not recall.
- **First prefetch script:** died on `GET /api/runs` (405; POST-only, recorded in the usability-loop memory). The months list is `GET /api/expense-batches`.
- **First hand-over prompt:** prescribed a live Zoho Books read for the ground truth; the on-disk 24-month pull already held it (B7 E1, enumerate before proposing).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edited (PR #1427) | Item 216: findings, accuracy table, ranked levers, ceilings, instruments |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edited (this checkpoint PR) | Element rows for the categorization analysis and the four rulings |
| `memory/project_brisken_recon_categorization_analysis.md` + `MEMORY.md` | Created / indexed | Facts that outlive the item |
| `docs/2026-09-25 - Brisken Recon Categorization Analysis/measure.py`, `truth.py` | Added | The two offline scripts (baseline + refusal breakdown; Zoho join + accuracy); rerun against fresh payloads under `uv run --directory <module> --extra dev --extra web python <script>` with `RECON_DIR`, `SUGG_MD`, `ZOHO_JSON` set |
| `.../verification-verdicts.json` | Added | The six verdicts and the critic's report (workflow `wf_d4d8c27a-fed`) |

---

## Current Status

Item 216 is on `main`. Nothing in the app changed. brisken ops status line from `pre`: platform unknown plan, comms-log none (no comms ask). The live months read exactly as before the session; the one prefetch was read-only.

Owner decisions taken (this session): account map (derive, split cases to Dirk, then write), receiptless charges rule-or-person only, correction path first, no parent picks by the model. OpenAI / Anthropic / Lovable stay out of any registry write unless the owner raises it himself.

---

## Next Steps

Owner direction 2026-09-25 (mid-checkpoint): **the builds tackle root causes and structural problems, not symptoms.** Five causes, each with the structural change; a build that patches a symptom (one alias, one threshold, one label) without the structure is out of scope.

1. **Cause: a human category or account decision does not land, so the only learning input the owner allows has zero throughput** (0 corrections in seven months of payloads; Criss's 2026-09-14 and 2026-09-17 reports). Structure: ONE decision write path for a category/account pick (receipt line or charge) that stores the decision with provenance, survives every re-match, is what memory learns from at Publish and is what the export reads. Reproduce her two reports offline first (`confirm_expense_category` `web/service.py` ~3012, the field PUT `web/app.py` ~5345, the SPA's locked `<fieldset>` on statement months), then a route-level test that a pick is visible on the grid, the CSV, the sheet and the memory plan; regress_check through the caller.
2. **Cause: the account is treated as text classification when it is master data plus a human call.** Criss's postings follow a per-company convention a vendor name cannot reveal (COGS accounts for SaaS in Cloud and Corporate Services, `E100020-10` for CorpServ IT); the model picks from 62-68 labels with no history or convention shown. Structure: a rule (registry per-company map, memory) or a person is the ONLY source of `posting_category`; the model is a suggester whose output is `suggested_*` on every surface (grid, `sheet_writeback` never prints `(confirm)` on it, report and PDF labelled) and never a posting value; a model suggestion may not name a parent with postable children (owner ruling). Populate the map from her history: derive per (company, vendor) from `zoho-books-24mo.json` with the registry's own normalization, split open vs posted rows, hand Dirk the split vendors (Lovable CorpServ 37/15, Microsoft 23/20/14, Network Solutions 18/8, NameCheap 10/7, OpenAI CorpServ 19/5) plus the 7 questions and the parent-account policy question in one message; after his answers one `PUT /api/settings` for the uncontested rows (owner yes per action; the three gated vendors excluded, never re-asked).
3. **Cause: merchant identity is keyed on raw extracted text.** Memory recall and the registry match key on `detected_vendor` (`Anthropic, PBC`), so rules never reach the receipts they were written for, and three spellings hold three rules (item 170's measurement). Structure: one canonical merchant resolver (registry canonical + aliases + normalization) that memory keys on, the registry map consults and the export prints; a person-confirmed pairing of a receipt with a charge teaches the receipt's name as an alias of the descriptor's merchant (identity, not a category; tool-confirmed pairings excluded per the 2026-09-24 leak ruling). Measure reach before/after on the 55 unsure receipts (4 to 17 today).
4. **Cause: every receipt is assumed to be a card expense waiting for a statement.** Four wire-paid invoices (EUR 15,972 + USD 13,200 + EUR 900 + BRL 27,203) sit in the card queue for a statement that will never cover them, and the Redis invoice is counted twice. Structure: payment-mode routing at ingest (wire / bank transfer leave the card queue for a Bills path; `payment_mode` already exists on doc 0017); "waits for statement" only for card receipts; owner call on the destination.
5. **Cause: "categorized" counts answers, not their source or quality**, and `n_charges_category_guessed` hides most guesses. Structure: source-of-answer (rule / person / suggestion) on every count and surface, and a reproducible accuracy score: turn `measure.py` + `truth.py` into `tools/recon-categorization-score.py` (payload dir + Zoho pull in; per-source accuracy out), run after every re-pull; today's open-row figure is 1/23.
6. Re-pull Zoho once Criss books August and September and rescore open rows. `MEMORY.md` is 161 lines; compact under 140 (hook advisory).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 216 (the record; read it before the memories)
- memory `project_brisken_recon_categorization_analysis.md`, `project_brisken_recon_learning_rules.md`, `feedback_recon_no_live_writes_criss_acts.md`
- `docs/2026-09-25 - Brisken Recon Categorization Analysis/verification-verdicts.json` (the critic's `missing_analyses` list is the second half of the backlog for this theme)

### Open Questions
- Dirk: the split vendors and the 7 questions in the suggestions file; whether the model may ever post to a parent account.
- Owner (his to raise): the three gated vendors' registry entries.
- Whether Cloud Services' app months should be shown with their statement period beside them (the "August" run holds 14 July-dated charges).

### Working Notes
- Join rule that works: company + amount to the cent + |date| <= 3 days; Criss books on the Chase post date (one day after the charge on 95 of 120 strict joins), so same-day joins almost nothing. 112 of the 135 joined rows are July Corporate Services; Consulting has one row.
- The engine's parent picks: 58 of 164; Criss: 1 of 152. `E500010-10 ZOHO ERP` misread as generic cloud subscriptions on 29 of 31 picks; Microsoft office, LinkedIn Ads, Google Ads picks all name their vendor.
- History map out of sample (critic's `critic_truth.py` section B): majority account per (company, descriptor first token) from postings before 2026-07-01 covers 132/152 Jul-Sep bookings, agrees 124 (Cloud 28/28, CorpServ 95/103). Ceiling: 22 of 84 vendors split; 12% of their postings are minority bookings.
- Zero human category or account corrections in any of the seven months' payloads; `edited_fields` hold card, company, paid-through, private, date only.
- `n_charges_category_guessed` counts a guess only on a charge whose receipt requirement is otherwise closed; July shows 0 with 49 guesses.
- Sibling sessions were pulling the same four months at 03:27 UTC; none used this branch name. Machine healthy throughout (health 0.09 s).

### Reference Materials
- Workflow run `wf_d4d8c27a-fed`; transcript dir `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/11d1b2ff-7cd3-4113-b51c-7ac0a606a908/subagents/workflows/wf_d4d8c27a-fed/`
- PR #1427 `https://github.com/011matthias/agentic-ops1.01/pull/1427`
- Suggestions: `workspace/clients/brisken/context/expense-reconciliation/merchant-account-suggestions-260925.md`

---

## How to Continue

`/resume brisken`, read item 216, then start Build 1 (correction path) on a fresh `client/brisken/p1-correction-path` worktree off `origin/main`. Measure before touching code: reproduce her two reports with the route tests. Every build ships behind a regress_check proof and a read-only drive; no live write on Criss's months.

---

## Strategic Feedback

### What Worked Well This Session
- Enumerating the truth source before calling an API: the on-disk Zoho pull turned a risky live read into a file join, and the whole accuracy measurement cost zero external calls.
- Adversarial verification before writing: three of six headline claims were corrected by the skeptics (the memory-fix lever, the receipt reach of the account list, the "would post" claim). The item that landed is the corrected one.

### Suggestions
- Give the recon analysis a fixed instrument: turn `measure.py` + `truth.py` into `tools/recon-categorization-score.py` (payload dir + Zoho pull in, accuracy table out), so the next re-pull is one command and the number Criss's next month is judged by is reproducible.

### System Health
- Autonomy: 1 human intervention (the owner-decision round, itself a designed stop). Gates B1:1 B2:2 B3:1 skipped:0. The heredoc-size gate blocked one 139-line heredoc (a documented recurrence; the gate holds, recall does not).
