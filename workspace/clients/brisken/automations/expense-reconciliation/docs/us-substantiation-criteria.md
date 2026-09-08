---
project: brisken
workstream: p1-expense-reconciliation
kind: research
backlog_item: 48
state: pending-owner-review
created: 2026-09-08
updated: 2026-09-08
---

# US substantiation criteria vs. what this tool produces

**PENDING OWNER REVIEW. Nothing here has been built.** Round 1 of backlog
item 48 is research and gap analysis only; the report-structure delta in
section 6 is a proposal, not a plan of record.

**This is not tax advice and I am not a lawyer.** Every criterion below
cites a primary source fetched on 2026-09-08 and quoted, so a US CPA can
check the reasoning against the text rather than against my summary of it.
Before the tool's output is relied on in an examination, that CPA signs off.

## 1. The threshold question, answered

**ANSWERED by the owner 2026-09-08: at least one Brisken entity files a US
federal return.** So the criteria below bind, and the ranked gaps in
section 5 are live rather than hypothetical.

The question mattered because the tool reconciles a Chase card, which is a
US bank relationship and not a US filing position; a US card does not make
a US taxpayer, and I had no query path to the entities' filing status. The
entities in play are Corporate Services and Cloud Services
(`context/expense-reconciliation/zoho-entity-card-map.md`).

**Still open, and it decides scope rather than applicability:** WHICH
entities file. The tool already carries a legal entity per row, so the
criteria can be applied to the filing entities' expenses alone rather than
to every month wholesale. Until that list exists, treat every criterion as
applying to every row, which is the conservative reading.

## 2. Sources

All fetched 2026-09-08 in the session that produced this file. Statute and
regulation text is quoted from the source, not from memory.

| # | Source | URL |
|---|---|---|
| S1 | 26 U.S.C. 162(a), ordinary and necessary business expenses | law.cornell.edu/uscode/text/26/162 |
| S2 | 26 U.S.C. 274(a)(1), (d), (k), (n)(1) | law.cornell.edu/uscode/text/26/274 |
| S3 | 26 C.F.R. 1.274-5(c)(2)(iii), documentary evidence | law.cornell.edu/cfr/text/26/1.274-5 |
| S4 | 26 C.F.R. 1.274-5T(b), (c)(2), the elements | law.cornell.edu/cfr/text/26/1.274-5T |
| S5 | 26 C.F.R. 1.6001-1(a), (e), records and retention | law.cornell.edu/cfr/text/26/1.6001-1 |
| S6 | 26 C.F.R. 1.62-2, accountable plans | law.cornell.edu/cfr/text/26/1.62-2 |
| S7 | Rev. Proc. 97-22, 1997-13 I.R.B. 9, electronic storage systems | irs.gov/pub/irs-tege/rp-97-22.pdf |
| S8 | IRS Pub. 583, records and retention periods | irs.gov/publications/p583 |
| S9 | IRS Pub. 463, travel/gift/car substantiation | irs.gov/publications/p463 |
| S10 | IRS "Automated records" page, currency of 97-22 | irs.gov/businesses/automated-records |

**Two source caveats, both material.**

- **The CFR text came from Cornell LII, not eCFR.** eCFR returned a 302 to
  `unblock.federalregister.gov` for every regulation request this session,
  so automated access was blocked. Cornell reproduces the CFR faithfully in
  my experience but it is not the official text. Anyone relying on a
  specific paragraph should re-read it on ecfr.gov by hand.
- **Pub. 463's Table 5-1 did not come back cleanly.** Two fetches returned
  partial and lightly paraphrased content, so I have **not** used Table 5-1
  as authority for anything. The element lists below come from
  1.274-5T(b) (S4), which is the regulation Table 5-1 summarizes, and which
  did come back verbatim.

S7 is current: the IRS "Automated records" page (S10) still points to
Rev. Proc. 97-22 for electronic storage systems, and Rev. Proc. 98-25
superseded Rev. Proc. 91-59 on a different subject (machine-sensible ADP
records), not 97-22.

## 3. What the tool actually produces, and therefore what is in scope

Read from the code on branch `client/brisken/p1-us-substantiation` at
`919ce038`, not from the spec.

**Monthly expense report PDF** (`output/month_report_pdf.py`, assembled in
`web/service.py`): a header with month, entity, per-currency totals and
count; a numbered listing with columns `# / Date / Vendor / Account /
Entity / Paid through / Amount / Ccy / Receipt`; an optional
reimbursements-owed section grouped per person with per-currency sums; an
optional per-person sectioning for trip reports; then every receipt
document appended in listing order behind a caption naming the expense
number it proves. An expense with no document keeps its caption and says so.

**Reconciliation report PDF** (`output/reconciliation_report_pdf.py`):
header with month, statement account, matched count and unreconciled per
currency; a per-card coverage table; exceptions first (unmatched charges,
unmatched receipts, duplicate groups); the full charge listing `# / Date /
Charge / Amount / Ccy / Status / Receipt / Account`; then the receipts.

**Expense CSV** (`output/zoho_expense_export.py`): `Expense Date, Expense
Account, Expense Amount, Currency Code, Exchange Rate, Paid Through,
Vendor, Reference#, Expense Description, Tax Name, Tax Amount, Customer
Name, Legal Entity, Receipt URL`.

**Reconciled CSV** (`output/reconciled_csv.py`): the charge-side sidecar,
37 columns covering statement fields, match provenance, receipt fields and
disposition.

**XLSX** (`output/report_xlsx.py`): Summary, one sheet per card, Needs
Review, Unmatched, Errors, Explain.

**Receipt store** (`hosting/store.py`): content-addressed, each file at the
SHA-256 of its own bytes.

### In scope

Expense documentation and substantiation: what a document has to contain to
prove a business expense, what evidence has to back it, and what a system
holding that evidence electronically has to do. That is 6001 and its
regulation, 274(d) and its regulation for the travel and gift subset,
1.62-2 for reimbursements, and Rev. Proc. 97-22 for the storage itself.

### Out of scope, and why

- **GAAP statement presentation.** The tool produces no financial
  statements. No presentation, classification or disclosure standard has a
  document here to bind.
- **Tax filing and return preparation.** The tool files nothing.
- **274(n)(1), the 50% meals limit** (S2): "The amount allowable as a
  deduction ... for any expense for food or beverages shall not exceed 50
  percent". This is a deduction computation, not a document element. It is
  listed once in section 4 as an adjacent criterion because the preparer
  needs to be able to *identify* meals, which the Account column already
  does; the tool should not compute the limit.
- **274(a)(1) entertainment** (S2): entertainment is disallowed outright,
  and, confirmed against the statute this session, the word "entertainment"
  no longer appears in the 274(d) list of categories needing substantiation
  (it was removed in 2017). So 1.274-5T(b)(3)'s entertainment element list,
  including the attendee and business-relationship elements, does **not**
  bind. This matters: it is the criterion most likely to be added by
  someone working from a pre-2018 checklist.
- **SOX internal control over financial reporting.** Binds SEC registrants.
  UNVERIFIED whether any Brisken entity is one; on the evidence available,
  almost certainly not.

## 4. Criteria matrix

Status is against the tool's outputs as they stand today. "Satisfied" means
the document carries the element; it does not mean the underlying expense
is deductible.

### A. Section 6001 general records, binding every expense

| # | Criterion | Source | Where it lands | Status |
|---|---|---|---|---|
| A1 | Keep "such permanent books of account or records ... as are sufficient to establish the amount of gross income, deductions, credits, or other matters" | 1.6001-1(a) (S5) | Month report PDF listing plus appended receipts; reconciliation PDF proves the month is complete | **Satisfied** |
| A2 | Supporting documents show "the amount paid and that the amount was for a business expense" | Pub. 583 (S8); 162(a) "ordinary and necessary ... in carrying on any trade or business" (S1) | Amount is on every row and traced to the receipt. The business-expense half rests on the Account column implying it | **Partial**, see G1 |
| A3 | Records "retained so long as the contents thereof may become material in the administration of any internal revenue law" | 1.6001-1(e) (S5); periods 3 / 6 / 7 years / unlimited per Pub. 583 (S8) | Receipt store is content-addressed and durable, but `store.delete_run` removes a month and nothing states or enforces a retention period | **Missing** as a control, see G2 |

### B. Section 274(d) substantiation, binding travel, gifts and listed property only

274(d) (S2) disallows the deduction unless the taxpayer substantiates
"(A) the amount of such expense or other item, (B) the time and place of
the travel or the date and description of the gift, (C) the business
purpose of the expense or other item, and (D) the business relationship to
the taxpayer of the person receiving the benefit".

| # | Criterion | Source | Where it lands | Status |
|---|---|---|---|---|
| B1 | Travel, amount: "Amount of each separate expenditure for traveling away from home, such as cost of transportation or lodging, except that the daily cost of the traveler's own breakfast, lunch, and dinner ... may be aggregated, if set forth in reasonable categories" | 1.274-5T(b)(2)(i) (S4) | Per-expense amount and currency on every listing row, tied to the CSV so the document and the export cannot disagree | **Satisfied** |
| B2 | Travel, time: "Dates of departure and return for each trip away from home, and number of days away from home spent on business" | 1.274-5T(b)(2)(ii) (S4) | Trip reports print `trip.start_date to trip.end_date` in the subtitle. Month reports print only per-expense dates. Days-on-business appears nowhere | **Partial**, trips only, see G9 |
| B3 | Travel, place: "Destinations or locality of travel, described by name of city or town or other similar designation" | 1.274-5T(b)(2)(iii) (S4) | `Receipt.expense_location` exists but is populated only by the two Zoho expense-report ingest paths, never by the vision OCR path, and reaches only the API serializer. It is in no PDF, no CSV, no XLSX | **Missing**, see G3 |
| B4 | Travel, business purpose: "Business reason for travel or nature of the business benefit derived or expected to be derived as a result of travel" | 1.274-5T(b)(2)(iv) (S4); 274(d)(C) (S2) | Nothing. A repo-wide search for a business-purpose field returns zero hits. `Expense Description` carries the receipt's own line-item text, which is what was bought, not why | **Missing**, see G1 |
| B5 | Gifts: cost, date, description, business reason, and "occupation or other information relating to the recipient ... sufficient to establish business relationship" | 1.274-5T(b)(5) (S4) | The tool has no gift concept at all | **Missing**, see G10 |
| B6 | Documentary evidence required for "(1) Any expenditure for lodging while traveling away from home, and (2) Any other expenditure of $75 or more except, for transportation charges, documentary evidence will not be required if not readily available" | 1.274-5(c)(2)(iii) (S3) | Receipts are attached where held, and a missing one is stated rather than hidden. But the report does not distinguish a missing receipt that is legally required from one that is not | **Partial**, see G4 |
| B7 | What the evidence must show: for a hotel, "name, location, date, and separate amounts for charges such as for lodging, meals, and telephone"; for a restaurant, "name and location of the restaurant, the date and amount of the expenditure, the number of people served" | 1.274-5(c)(2)(iii) (S3) | The receipt image itself is appended in full and carries these. The extracted structured fields do not capture number of people served or a lodging/meals split | **Satisfied via the image**, thin as data |
| B8 | Adequate records means an "account book, diary, log, statement of expense, trip sheets, or similar record" **and** documentary evidence which "in combination, are sufficient to establish each element", each element recorded "at or near the time of the expenditure or use" | 1.274-5T(c)(2)(i)-(ii) (S4) | The listing is a statement of expense and the receipts are the documentary evidence, so the combination requirement is met by construction. Contemporaneity is not evidenced: the tool holds mail arrival and ingest timestamps but prints none of them | **Partial**, see G6 |

### C. Section 1.62-2 accountable plans, binding the reimbursements section

| # | Criterion | Source | Where it lands | Status |
|---|---|---|---|---|
| C1 | Business connection: the arrangement "provides advances, allowances ... or reimbursements only for business expenses ... allowable as deductions" | 1.62-2(d) (S6) | The private/reimburse flag marks the expense; nothing states the business connection | **Partial**, same root as G1 |
| C2 | Substantiation: for expenses governed by 274(d), "information sufficient to satisfy the substantiation requirements of section 274(d)"; for others, information "sufficient to enable the payor to identify the specific nature of each expense" | 1.62-2(e)(2)-(3) (S6) | The reimbursements-owed section is per person, per currency, with the receipt behind each row. For non-274(d) expenses this identifies the specific nature. For travel it inherits B3 and B4's gaps | **Partial** |
| C3 | Return of excess "within a reasonable period of time" | 1.62-2(f) (S6) | Nothing; the tool tracks what is owed, not what was settled | **Missing**, and arguably out of the tool's range |
| C4 | Fixed-date safe harbor: advance within 30 days of the expense, substantiate within 60 days, return excess within 120 days | 1.62-2(g)(2)(i) (S6) | The tool holds every expense date and every ingest date, so the elapsed clock is derivable, but no output shows it | **Missing**, see G5 |
| C5 | Consequence of failure: amounts under a nonaccountable plan are "included in the employee's gross income, must be reported as wages ... and are subject to withholding and payment of employment taxes" | 1.62-2(c)(5) (S6) | Not a document element. Listed because it is what makes C1-C4 expensive rather than untidy | n/a |

### D. Rev. Proc. 97-22, binding the tool itself as an electronic storage system

This is the body of law that binds the tool most directly. Records in a
system that complies "will constitute records within the meaning of 6001"
(S7 section 1); a system that fails may draw a Notice of Inadequate Records
under 1.6001-1(d) and the penalties in section 9.

| # | Criterion | Source | Where it lands | Status |
|---|---|---|---|---|
| D1 | "ensure an accurate and complete transfer ... must also index, store, preserve, retrieve, and reproduce" | 4.01(1) (S7) | Content-addressed store, `document_id` index, PDF reproduction | **Satisfied** |
| D2 | "reasonable controls to ensure the integrity, accuracy, and reliability" | 4.01(2)(a) (S7) | Strong. The address of a receipt is the SHA-256 of its bytes, and `extracted_receipts` keeps the original OCR reading in a parallel first-write-wins snapshot so a reviewer edit cannot overwrite what the machine first read | **Satisfied** |
| D3 | "reasonable controls to prevent and detect the unauthorized creation of, addition to, alteration of, deletion of, or deterioration of" the records | 4.01(2)(b) (S7) | Content addressing detects byte alteration. Against it: one shared operator code gates the whole app, so no action is attributable to a person, and `delete_run` removes a month leaving nothing behind | **Partial**, see G2 and G11 |
| D4 | "an inspection and quality assurance program evidenced by regular evaluations ... including periodic checks" | 4.01(2)(c) (S7) | None exists | **Missing**, see G8 |
| D5 | An indexing system that "permits the identification and retrieval", for example "assigning each electronically stored document a unique identification number" | 4.01(2)(d), 4.02 (S7) | `document_id` plus `Reference#` on the export plus the content hash | **Satisfied** |
| D6 | Reproductions "must exhibit a high degree of legibility and readability when displayed on a video display terminal and when reproduced in hardcopy" | 4.01(3) (S7) | Receipts are appended as pages, PDFs keeping their own. Nobody has checked a printed page against the paper original | **Satisfied, UNVERIFIED** at print resolution |
| D7 | Cross-reference "in a manner that provides an audit trail between the general ledger and the source document(s)" | 4.01(4) (S7) | The tool holds one end: `Reference#`, `Receipt URL`, and a caption naming the expense number each receipt proves. The general ledger is Zoho, outside the tool | **Partial** by design |
| D8 | Maintain and make available "complete descriptions of (a) the electronic storage system, including all procedures relating to its use; and (b) the indexing system" | 4.01(5) (S7) | BLUEPRINT.md describes the system to us. Nothing describes it to an examiner | **Missing**, see G7 |
| D9 | At examination, "retrieve and reproduce (including hardcopies if requested)" and provide the resources to do so | 4.01(6) (S7) | The PDF download is exactly this | **Satisfied** |
| D10 | "retain electronically stored books and records so long as their contents may become material" | 4.01(8) (S7) | Same gap as A3 | **Missing**, see G2 |
| D11 | Paper originals may be destroyed only after the taxpayer "has completed its own testing of the electronic storage system that establishes that hardcopy or computerized books and records are being reproduced in compliance with all the provisions" and "has instituted procedures that ensure its continued compliance" | section 7 (S7) | No such testing has been done | **Missing**, see G8 |

## 5. Ranked gaps

Ranked by exposure times frequency, following the backlog's own rule that
wrong money beats wrong text and a monthly hand-fix beats a one-off.

**G1. Business purpose is absent from every output.** 274(d)(C),
1.274-5T(b)(2)(iv), 1.62-2(e)(2). This is the one required element the tool
has no field for anywhere. It bites twice: a travel expense missing it is
disallowed outright under 274(d), and a reimbursement missing it can push
the arrangement out of the accountable-plan rules, at which point
1.62-2(c)(5) turns the reimbursement into wages subject to withholding.
Everything else on this list is smaller than G1.

**G2. There is no retention control, and one call deletes a month.**
1.6001-1(e), Rev. Proc. 97-22 section 4.01(8). `store.delete_run` removes
the run; the batch-delete path is already in daily use for test fixtures.
The tool's whole purpose is holding the evidence, and nothing stops the
evidence being dropped, states how long it should live, or records that it
was dropped.

**G3. Place is captured on one path and dies before any output.**
1.274-5T(b)(2)(iii). `expense_location` is read by the Zoho expense-CSV and
expense-report-PDF ingests, reaches `serialize.py` and the API dict, and
appears in no PDF, no CSV and no XLSX. The vision OCR path, which is now
the main entrance, never populates it at all. A required element is being
thrown away, which makes this the cheapest real fix on the list.

**G4. The $75 and lodging thresholds are not flagged.**
1.274-5(c)(2)(iii). The report treats every missing receipt the same. It
should not: a missing receipt on a 12 EUR taxi is fine, and a missing
receipt on a hotel bill or a 400 USD charge is a disallowed deduction. The
report has the amount and the account, so the flag is derivable today.

**G5. The accountable-plan clock is invisible.** 1.62-2(g)(2)(i). The safe
harbor wants substantiation within 60 days of the expense and return of
excess within 120. The tool holds both dates and shows neither, so a
reimbursement drifting past the window is discoverable only by hand.

**G6. The documents carry no preparation stamp.** Rev. Proc. 97-22
section 4.01(4)-(5); 1.274-5T(c)(2)(ii) contemporaneity. `prepared_note` is
a fixed sentence about where the amounts came from. There is no prepared-on
date, no preparer, no run id, no version, so two printings of the same
month are indistinguishable and nothing in the document evidences that its
records were made at or near the time of the expense.

**G7. There is no system description an examiner could be handed.**
Rev. Proc. 97-22 section 4.01(5) requires complete descriptions of the
storage system and the indexing system, on request. This is a writing task,
not a build, and it is the cheapest item on the whole list.

**G8. Criss cannot yet safely bin the paper.** Rev. Proc. 97-22 section 7
permits destroying originals only after the taxpayer's own testing
establishes compliant reproduction and procedures ensure continued
compliance; section 4.01(2)(c) wants a standing quality-assurance program.
Neither exists, so until they do, the paper has to be kept in parallel and
the tool is not yet saving the work it looks like it is saving.

**G9. Days away on business are nowhere.** 1.274-5T(b)(2)(ii). Trip reports
carry the departure and return dates in the subtitle; the count of days
spent on business is not derived. Narrow, and only applies to trips.

**G10. No gift handling.** 1.274-5T(b)(5). Only matters if Brisken gives
business gifts. Owner question, not a defect.

**G11. One shared operator code means no per-user attribution.**
Rev. Proc. 97-22 section 4.01(2)(b). The system can detect that bytes
changed but cannot say who changed a decision. Ranked last because it is an
access-model change, not a report change, and it sits outside item 48's
scope.

## 6. Proposed report-structure delta

**Proposal only. Not scheduled, not designed in detail, not approved.**
Grouped by what each change actually costs, because that is the decision
the owner is making.

### Rendering-only, the data already exists

- **Expense report listing: add a Place column**, sourced from
  `expense_location` where the Zoho path supplied it (G3). Blank where
  unknown rather than guessed.
- **Expense report and reconciliation report: mark receipt-required rows**
  (G4). A missing receipt on a lodging account, or on any expense at or
  above 75 USD, renders differently from an ordinary missing receipt, with
  a one-line footnote naming 1.274-5(c)(2)(iii). The threshold is a dollar
  figure, so the currency conversion has to be honest about which rate it
  used.
- **Both reports: replace the static `prepared_note` with a real
  preparation block** (G6): prepared-on date, preparer, run id, and the
  ingest date range the month's receipts arrived in. The arrival dates are
  the contemporaneity evidence B8 wants, and they are already stored.
- **Trip report: derive and print days away on business** from the trip
  span and the roster (G9).
- **Reimbursements section: show the elapsed days** between each expense
  date and the report date, flagging rows past 60 days (G5), with the
  safe-harbor citation in the section note.

### Needs a new field, so needs a capture decision first

- **Business purpose** (G1). **Capture decided by the owner 2026-09-08:
  per merchant, learned once.** A default purpose lives in the merchant
  registry, which already resolves canonical names and already learns from
  corrections, and is overridable per expense. Recurring subscriptions
  carry a standing purpose after being set once, and only genuinely new
  merchants ask, so the field stays off Criss's monthly path. Per-card,
  per-account and per-expense-only were the alternatives and were not
  taken: a card buys across purposes, an account says what kind of cost it
  is rather than why it was incurred, and per-expense-only puts a manual
  field on every row of every month forever.

  Three design questions this leaves, to settle when the round is specced:
  what a merchant's purpose defaults to before anyone has set one (blank
  and flagged, rather than a guess, is the B4-consistent answer); whether
  the purpose belongs on the listing row or only in the CSV, given the
  listing is already nine columns wide; and whether a purpose set on one
  entity's merchant row should carry to another entity's, which is the same
  question the card registry answered with per-entity chains.
- **Place from the OCR path** (G3, second half). Vision already reads the
  receipt; the merchant's city is usually printed on it. Capturing it is an
  extraction-schema change, so it lands with a re-read cost.

### Not a report change at all

- **A retention policy and a delete that leaves a trace** (G2). Needs a
  decision on the period first, which follows from the entity question in
  section 1 and from Pub. 583's 3 / 6 / 7 / unlimited ladder.
- **A system description document for an examiner** (G7). One markdown
  file, written once, covering the storage scheme, the indexing scheme, the
  retrieval path and the procedures. Cheapest item here.
- **A quality-assurance routine** (G8), so the paper can eventually go. A
  periodic sample of stored receipts reproduced and compared against the
  original, recorded. Rev. Proc. 97-22 wants it "regular"; the shape is
  Brisken's call.

### Deliberately not proposed

- Any attendee or business-relationship capture. Entertainment left 274(d)
  in 2017 and the tool handles no gifts, so there is nothing for it to bind
  to today.
- Any 50% meals computation. Out of scope; the tool documents, it does not
  compute deductions.
- Any change to the reconciliation report's exception ordering. Exceptions
  first is already the right shape for an examiner.

## 7. Open questions for the owner

Answered 2026-09-08: **US filing applies** (section 1) and **business
purpose is captured per merchant, learned once** (section 6). Still open:

1. WHICH entities file US. Decides whether the criteria scope to those
   entities' rows or apply to every month. Conservative reading until
   answered: all rows.
2. What retention period does Brisken want to commit to, and should
   deleting a month be blocked outright or recorded? Pub. 583's ladder is
   3 / 6 / 7 years / unlimited depending on the situation.
3. Does Brisken give business gifts through these cards? If no, G10 closes.
4. Is anyone binning paper receipts today on the assumption the tool has
   them? If yes, G8 is more urgent than its rank suggests, because
   Rev. Proc. 97-22 section 7 does not yet permit it.
