# Checkpoint: Brisken P1 US Substantiation Criteria

**Date:** 2026-09-08
**Status:** Backlog item 48 round 1 delivered and merged (PR #722), pending owner review. Nothing built.

---

## Summary

Researched what US law actually requires of the expense tool's documents and
mapped 27 verified criteria onto its real outputs, producing a ranked
eleven-gap list. The scope guard in the brief held and narrowed further than
expected: the body that binds the tool most directly is Rev. Proc. 97-22, the
electronic storage system rules, which nobody had named.

---

## What Was Done This Session

### Research gate (primary sources only, B4)

1. Fetched and quoted 26 U.S.C. 162(a) and 274(a)/(d)/(k)/(n); 26 C.F.R.
   1.6001-1, 1.62-2, 1.274-5, 1.274-5T; Rev. Proc. 97-22 in full; IRS Pub.
   583 and 463. Every criterion in the deliverable cites one of these.
2. Confirmed Rev. Proc. 97-22 is still current via the IRS "Automated
   records" page: Rev. Proc. 98-25 superseded 91-59 on machine-sensible ADP
   records, a different subject, not 97-22.
3. Two source failures handled by disclosure rather than substitution:
   eCFR 302-redirected every regulation request to
   `unblock.federalregister.gov`, so the CFR text is Cornell LII and the
   file says so; and Pub. 463's Table 5-1 came back partial and paraphrased
   across two fetches, so it is used as authority for nothing and the
   element lists come from 1.274-5T(b) verbatim instead.

### Reading the tool's real outputs (so the scope stayed honest)

4. Read the two PDF builders, both CSV writers, the XLSX sheet set, the
   receipt store, and the `Receipt`/`Transaction` dataclasses on the merged
   tree, not the spec. Verified three claims by grep rather than assertion:
   business purpose has zero hits anywhere in the source; `expense_location`
   reaches only `serialize.py` and the API dict and appears in no output;
   the Zoho expense-report PDF parser recognizes an `Attendees :` metadata
   label and keeps only `Location`.

### Deliverable

5. `docs/us-substantiation-criteria.md` (353 lines): scope statement, source
   table with both caveats, what the tool actually produces, the 27-criterion
   matrix in four sets (6001 general records, 274(d) T&E, 1.62-2 accountable
   plans, Rev. Proc. 97-22 storage), eleven ranked gaps, a proposed
   report-structure delta grouped by what each change costs, and five open
   questions.
6. Backlog item 48's block records the outcome. No other backlog row touched.

---

## Key Decisions Made

### Two criteria a pre-2018 checklist would have added are OUT

- **Choice:** No attendee or business-relationship element, and no 50% meals
  computation.
- **Rationale:** Confirmed against the statute this session that
  "entertainment" no longer appears in the 274(d) list (removed 2017), so
  1.274-5T(b)(3)'s entertainment element list does not bind. 274(n)(1) is a
  deduction computation, not a document element, and the tool does not
  compute deductions. This is the most likely place for an invented
  requirement to enter, so it is called out explicitly in the file.

### Rev. Proc. 97-22 is the centre of gravity, not 274(d)

- **Choice:** Gave the electronic storage rules their own criteria set (D1
  to D11), the largest of the four.
- **Rationale:** The brief anticipated 274(d) T&E substantiation. That does
  bind, but only the travel and gift subset, and most Brisken charges are
  software subscriptions. Rev. Proc. 97-22 binds the tool itself on every
  receipt it holds: compliance is what makes its records count as section
  6001 records at all. The tool scores well here (content-addressed store,
  first-write-wins OCR baseline) and its gaps are cheap.

### The entity question was left open rather than assumed

- **Choice:** Marked UNVERIFIED, made it section 1 of the file and the first
  open question, and made every criterion conditional on it.
- **Rationale:** A Chase card is a US bank relationship, not a US filing
  position. There is no query path to whether Corporate Services or Cloud
  Services files a US return. Asserting it would have made a legal document
  rest on a guess.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/docs/us-substantiation-criteria.md` | created | The criteria matrix, gap list and proposed delta |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edited (item 48 block only) | Records round 1 delivered, the three top gaps, the two source caveats, and the blocking entity question |

---

## Current Status

PR #722 merged to main on green CI (all seven checks) and both worktrees
removed. The tool is untouched: no backend code, no report change, no
deploy, no writes to the live app; the only live reads were of the merged
source tree.

Brisken ops status: platform plan unknown, last assessed unknown. Comms-log
touched 1 day ago, current.

Six p2 status files are stale (48 to 79 days: `p2-lead-gen-general`,
`p2-onepilot-site`, `p2-outreach`, `p2-product-decks`, `p2-rome`,
`p2-targeting`). Deliberately not touched: p2 is lead-gen, and editing them
from a p1 session would put lead-gen edits on a p1 branch
(rule_branch_isolation section 2).

---

## Next Steps

1. **Owner answers section 1:** does any Brisken entity file a US federal
   return? Everything else waits on it. If no, round 2 is the same exercise
   against DE and BR rules instead.
2. **Owner reviews the matrix and picks from section 6.** The rendering-only
   items (Place column, receipt-required flags, preparation stamp, days-away,
   the 60-day reimbursement clock) need no new data and could ship as one
   round. The business-purpose capture needs a design call first.
3. **G7 is free and unblocked either way:** write the examiner-facing system
   description Rev. Proc. 97-22 4.01(5) requires. One markdown file.
4. **Ask Criss whether anyone is already binning paper receipts** on the
   assumption the tool holds them. If yes, G8 outranks its position.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/us-substantiation-criteria.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 48 block)

### Open Questions

- US filing position of the Brisken entities (blocks everything).
- Where business purpose comes from: per merchant, per card, per account, or
  per expense.
- Retention period to commit to, and whether deleting a month should be
  blocked or merely recorded.
- Whether Brisken gives business gifts through these cards (closes G10 if no).

### Working Notes

**eCFR blocks automated fetch.** Every `ecfr.gov/current/title-26/...`
request returned 302 to `unblock.federalregister.gov`. Cornell LII
(`law.cornell.edu/cfr/text/26/...`) served the same sections cleanly and is
the working path for CFR text, with the caveat that it is a reproduction.
Do not spend calls retrying eCFR.

**IRS PDFs need local extraction.** WebFetch on
`irs.gov/pub/irs-tege/rp-97-22.pdf` returned the raw PDF structure and the
fetcher declined to guess at it, but it saved the bytes to the tool-results
directory; `pypdf` extraction of that file produced Rev. Proc. 97-22 in
full, all eleven sections. Same route for any other IRS PDF.

**Pub. 463's Table 5-1 does not fetch cleanly** (tried twice, both partial
and paraphrased). 1.274-5T(b) is the regulation it summarizes and returns
verbatim; use that.

**Where the tool's own gaps live in code**, so the next session need not
re-derive them: business purpose has zero hits repo-wide;
`expense_location` is written by `ingest/expense_csv.py` and
`ingest/expense_report_pdf.py`, read by `web/serialize.py` and
`web/service.py:2058`, and consumed by nothing in `output/`; the static
`prepared_note` is composed at `web/service.py:5651`; the delete path is
`web/store.py:493 delete_run`.

**The tool scores better than expected on storage integrity.**
`hosting/store.py` addresses each receipt at the SHA-256 of its bytes, and
`extracted_receipts` keeps the machine's first OCR reading in a parallel
first-write-wins snapshot. Together those are a real answer to
Rev. Proc. 97-22 4.01(2)(a)-(b), and neither was built for that reason.

### Reference Materials

- law.cornell.edu/uscode/text/26/274 and /162
- law.cornell.edu/cfr/text/26/1.274-5, /1.274-5T, /1.6001-1, /1.62-2
- irs.gov/pub/irs-tege/rp-97-22.pdf (extract locally with pypdf)
- irs.gov/publications/p583, irs.gov/businesses/automated-records

---

## How to Continue

Open the criteria file, take the owner through section 4's matrix and
section 5's ranked gaps, and get an answer to the entity question in section
1. Nothing should be built until that answer exists; if it comes back "no US
filing", the whole delta is void and the correct move is the same research
against German and Brazilian rules.

---

## Strategic Feedback

### What Worked Well This Session

- Reading the outputs from source before touching the law. The scope guard
  in the brief was right, and reading `output/*.py` first is what let it
  narrow further: knowing the tool appends the receipt image in full is what
  turned criterion B7 from a gap into a satisfied row, and knowing the
  listing is built from the same rows as the CSV is what made B1 defensible.
- Verifying absence by grep rather than by memory. "Business purpose exists
  nowhere" is the single load-bearing claim in the whole gap list, and it is
  a search result, not an impression.

### Suggestions

- The rendering-only half of section 6 is five changes that share one
  surface and need no new data. If the entity question comes back yes, ship
  them as one round rather than five, and let the business-purpose design
  call run in parallel rather than gating them.

### System Health

- **Autonomy: 0 human interventions.** Fully autonomous session.
- `rule_session-start` step 6 mandates bulk-loading every memory file and
  budgets it at "~1,800 tokens, 0.2% of budget". The store is now 128 files
  and 659 KB, roughly 100x that estimate. The rule is no longer followable
  as written, so it gets deviated from and the deviation is invisible unless
  a session says so. Logged as `infrastructure-deferred`; the fix is either
  a searchable memory index or an amended rule, not more discipline.
- The heredoc-size gate fired before the 354-line write instead of after,
  cost one call, and pointed at the Write tool. Three prior register rows
  (2026-08-22, -24, -25) logged this failure discovering it the expensive
  way. The structural fix is holding.
