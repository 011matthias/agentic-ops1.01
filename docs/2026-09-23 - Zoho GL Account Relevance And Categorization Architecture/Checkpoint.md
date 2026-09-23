# Checkpoint: Zoho GL Account Relevance And Categorization Architecture

**Date:** 2026-09-23
**Status:** Design settled, marking data complete, Phase 1 build handed off to a fresh session

---

## Summary

Dirk left three feedback notes asking that the recon tool's categories BE Brisken's
Zoho chart of accounts rather than eight internal buckets, that a merchant's GL
account stop applying itself automatically, and that Criss's Cloud Services
accounts not be forgotten. He then hand-marked an `Expense Relevant` column on the
CorpServ chart. This session read his scheme off those marks, applied it to the
other two legal entities, and wrote the Phase 1 build brief.

---

## What Was Done This Session

### Read the live feedback
1. Pulled `/feedback.jsonl` from the deployed app: **85 notes**, three more than the
   82 the previous round consumed. Notes **#83, #84, #85** are all Zoho GL and
   category feedback, all unitemized in the backlog.
2. Scanned all 85 for the same theme and established that notes #25, #27 and #58
   ("cards do not need zoho accounts since we want to gain independence from
   zoho", "shouldnt the app be zoho free?") are superseded by the 2026-09-22
   reversal that made Zoho the month-end destination again.

### Read Dirk's chart-of-accounts sheet
3. `CoA BRISKEN BCS BTS CorpServ 260923.xlsx`, three tabs, one per legal entity.
   Identified each tab against a real Zoho org by matching every `Account ID`
   against `context/zoho-books-coa.json` rather than trusting the label:
   BCS = Cloud Services `697686691`, **BTS = Consulting LLC `808232536`**,
   CorpServ = Corporate Services `822741658`.
4. Re-read the sheet after he updated it mid-session: `Expense Relevant` went from
   76 Y / 21 N to **68 Y / 29 N**, the eight payroll and payroll-tax rows moving to
   N while `Payroll Service` and `Continuing Education` stayed Y.

### Derived the marking for the two unmarked entities
5. Wrote `derive_expense_relevant.py` and produced
   `CoA-expense-relevant-BCS-BTS-260923.xlsx`: 229 active expense accounts, all
   decided, BCS 67 Y / 58 N, BTS 64 Y / 40 N, zero conflicts with his own marks.
   156 came straight off his marks by shared account code; the rest from his
   demonstrated classes, with 2026 posting history as the tiebreak.
6. Flagged six rows `SPOT-CHECK` as judgement calls rather than rule applications.

### Handed off
7. Wrote the Phase 1 continuation prompt for the direct-to-Zoho categorization
   build, carrying the corrected counts, the three-tier touchless design, and the
   breaking-change hazards a fresh session cannot discover.
8. Saved `project_brisken_coa_expense_relevant` to memory with the index line.

---

## Key Decisions Made

### The buckets are retired, the reviewer never picks an account
- **Choice:** Classify receipts directly into Dirk's curated Zoho leaf accounts per
  entity, through a three-tier automated chain: (entity, vendor) registry, then
  trip-purpose inheritance, then a direct LLM match against that entity's curated
  leaves, then refusal. Criss stays an exception-only reviewer.
- **Rationale:** The receipt to bucket to translation-table to account path is the
  mechanism behind both known silent mis-posts. Removing the middle step removes
  the place the meaning was lost.

### Dirk's test, stated
- **Choice:** Y means a real purchase can be booked here and arrives as a receipt,
  card charge or expense claim. Not "is this an expense account".
- **Rationale:** He kept `Payroll Expenses: Payroll Service` and `Continuing
  Education` as Y while moving salaries and the five payroll taxes to N. The cut is
  whether a card can pay for it.

### Inside COGS you post to a leaf; outside, the parent is postable
- **Choice:** Treat COGS roll-ups as non-postable, other parents as postable.
- **Rationale:** His own marks: `COGS - CORE BUSINESS` N with its infrastructure and
  travel children Y, against `IT: Computer and Internet Expenses` and
  `Marketing & Selling Expenses` both Y.

### Allocation stays in Zoho
- **Choice:** The tool does not split a charge across companies.
- **Rationale:** Owner ruling this session. The CoA carries the rules and 48 of the
  marked CorpServ accounts split cleanly, but the split happens downstream.

---

## What Did NOT Work (and why)

- **Structural name rules alone as a substitute for his marking (first pass):**
  a "no card charge lands here" class list marked `Management Services` and
  `Tax Paid` as N, both of which he keeps as Y. Corrected by making his own mark on
  the same account code outrank every inferred rule.
- **Inheriting a verdict from a COGS roll-up (third pass):** the roll-up is N
  precisely because its leaves are where you post, so propagating N downward killed
  four accounts that should be Y, including `COGS - Travel Expenses (paid by
  Brisken)` in two entities and the SAP/AWS infrastructure account in Consulting
  that has seven real 2026 expenses on it. Fixed by never inheriting from a
  roll-up and by matching his marks on account NAME as well as code.
- **A `depreciat` keyword rule:** it caught `Computer expenses depreciated`, which
  is a purchase, not the non-cash charge. He marks the CorpServ twin Y. Fixed with
  a computer/equipment exemption.
- **Heredocs carrying Python triple-quoted blocks:** blocked by
  `heredoc-size-gate` twice, twenty minutes apart. The Write tool is the path.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/context/expense-reconciliation/CoA-expense-relevant-BCS-BTS-260923.xlsx` | Create | Dirk's workbook with BCS and BTS marked, plus Why and How-decided columns |
| `workspace/clients/brisken/context/expense-reconciliation/derive_expense_relevant.py` | Create | The derivation, re-runnable when he re-issues the sheet |
| `workspace/clients/brisken/context/expense-reconciliation/CoA-expense-relevant-proposal-260923.xlsx` | Delete | Superseded by the file above in the same change (W1 §4) |
| `~/.claude/.../memory/project_brisken_coa_expense_relevant.md` | Create | Dirk's scheme, the tab-to-org map, the allocation ruling |
| `~/.claude/.../memory/MEMORY.md` | Edit | Index line for the above |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | CoA marking element added, notes 83-85 recorded |

---

## Current Status

The categorization design is settled and the data it needs exists. Nothing was
built: no code changed in the recon module, no deploy, no PR beyond this
checkpoint's ledger. The live app is untouched.

brisken platform: unknown plan, ~?/? ops/mo, last assessed unknown. Feedback notes
#83, #84 and #85 are open and unitemized in `p1-improvement-backlog.md`; the
backlog's highest item is 170.

---

## Next Steps

1. Run the Phase 1 continuation prompt in a fresh session: taxonomy module,
   precedence chain, tests that bite, July and August dry-run diffs, architecture
   doc, PR.
2. Put the six SPOT-CHECK accounts to Dirk (per diem, Tax Management Services -
   Holding in both orgs, R&D, COGS - Support BRISKEN Tech / JB, third-party-
   reimbursement travel).
3. Itemize notes #83, #84, #85 in the backlog as items 171-173, and state whether
   Phase 1 subsumes items 163-166 or runs beside them.
4. Phase 2, already agreed: month-end totals per GL account with last month beside
   them, and a vendor-moved flag. These are what answer "we would not notice for
   months" and work on today's mapping.
5. Two status files are stale and were not touched this session:
   `p2-product-decks.md` (62d) and `p2-targeting.md` (63d).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/expense-reconciliation/CoA-expense-relevant-BCS-BTS-260923.xlsx`
- `workspace/clients/brisken/context/expense-reconciliation/derive_expense_relevant.py` (its docstring is the decision order)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/category_accounts.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/types.py` (line 61, the eight buckets)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 163-166, 169, 170)

### Open Questions
- Do the six SPOT-CHECK accounts stand as marked?
- Does Phase 1 subsume backlog items 163-166, or run beside them?
- Retiring `EXPENSE_CATEGORIES` touches stored month configs, the shipped scorer
  asset, settings validation and the published SPA. Which of those keeps a
  parseable-and-dropped shim, on the item 168 `_RETIRED_TUNABLES` precedent?

### Working Notes
- Real usage is far smaller than the allowlist. 2026 to date: Cloud Services posted
  to 7 distinct accounts across 86 rows, Consulting 8 across 49, Corporate Services
  29 across 614. Any picker or LLM prompt should surface what is used, not all
  seventy allowed.
- 73 active expense codes are shared across all three tabs, so one mapping written
  on the code works in all three with a short exception list.
- The chart holds the same dinner in three places (`Travel Expense | Food`,
  `Conferences: Travel Expenses | Food`, `Business Travel Expenses - CRM | Food`).
  No vendor rule can resolve that, which is why trip purpose is its own tier.
- The sheet was open in Excel during the read, so the values are its 18:56 save.
- `zoho-books-24mo.json` covers 2024-09-01 to 2026-09-18, pulled 2026-09-18.
  Account names in it match the sheet exactly for all three orgs.

### Reference Materials
- Source sheet: `C:\Users\neuma_p1qrsic\Desktop\Downloads\CoA BRISKEN BCS BTS CorpServ 260923.xlsx`
- Live feedback: `curl -s -A "$UA" -H "$AUTH" "$API/feedback.jsonl"` per `docs/operating.md`
- Memory: `project_brisken_coa_expense_relevant`

---

## How to Continue

Paste the Phase 1 continuation prompt from this session into a fresh chat. It is
self-sufficient and carries the corrected counts; the directive that preceded it
quoted the stale 76 Y / 21 N figures.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the rule off Dirk's own marks instead of asking him for it. The two
  payroll rows he kept as Y stated the test more precisely than a question would
  have, and it cut his remaining decisions from 229 to 6.
- Identifying the sheet tabs by matching account IDs against the Zoho pull. The BTS
  label reads as the sandbox and is not; a label-based assumption would have aimed
  the whole mapping at a test company.

### Suggestions
- Review derived output row by row before reporting it. Four of the derived
  verdicts were wrong on the third pass and all four came from one rule. Printing
  every non-trivial row and reading it is what caught them; a summary count would
  not have.

### System Health
- `bg_watch` state is one file per working tree, not per session, so a watch a
  sibling registered in this clone nagged every tool call of this session with an
  ETA it could not act on. `session_state.py` had the same shape and was fixed on
  2026-09-17 by going per-session.
- Autonomy: 1 human intervention (the sheet had been updated and needed re-reading).
