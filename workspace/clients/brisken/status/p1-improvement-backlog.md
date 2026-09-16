---
project: brisken
workstream: p1-expense-reconciliation
kind: improvement-backlog
state: active
updated: 2026-09-16
---

# Expense tool: improvement backlog (the one list)

Every improvement idea for the receipt-first expense tool lives HERE and
only here. The status file (`p1-expense-reconciliation.md`) records what
shipped; this file records what we think should happen next and why. When
an item ships, move it to the "Shipped" section at the bottom with its PR
number. New ideas from any session get appended here, never scattered
across checkpoints or chat.

Ranking rule (from the loop brief): wrong money beats wrong text, things
that stop the tool from learning beat cosmetics, and anything Criss would
have to hand-fix every month beats a one-off.

## Open

### The 2026-08-21 feedback wave (14 notes, sequencing decided)

The operator walked the whole tool on 2026-08-21 and left 14 notes via the
in-app widget (the first full wave since capture went global, iteration 7).
Every note maps to a planned PR round; the user picked cards-first
sequencing the same day. Items 10-17 below are that wave; the cards
program is item 10. Full design: the 2026-08-21 plan (checkpoint folder).

### 10. Cards as first-class identities, Zoho-independent (notes 1/6/9/11)

**Owner direction:** "cards do not need zoho accounts... we must create
our own identification system"; stop asking for the legal entity at batch
creation — lay out the card identities, let the user assign each to an
entity once, learn it.

**The design fact that drove the model:** one physical card carries TWO
digit identities (Chase statement marker "2838", plastic last-4 "1672";
Zoho labels print both). The last4-keyed map could never resolve
"Visa ...1672" — the January batch's 13 unassigned rows are this bug.

**Rounds:** R1 registry + read-time composition (settings `cards` key,
GET /api/cards, zero behavior change) — SHIPPED PR #555; R2 Zoho decoupling
(per-card OPTIONAL warning wording, conservative export resolution:
bare-digit keys resolve labels, ambiguity placeholders, merchants
inert-hint, dropdown relabels answering notes 5/7) — SHIPPED PR #556; R3
entity-less batch + card-review strip + hint-to-card assignment that
persists ("learning") + refresh-master-data endpoint (snapshot-trap fix)
— SHIPPED PR #559 (3-lens adversarial review; every HIGH fixed + pinned:
single-digit-run learn rule, compound/DE generic tenders, ambiguity
blocks the paid-through flat map, graduation bakes chain entities —
pre-fix an assigned entity-less batch reconciled 0 silently; restore +
attach final-write now serialized under the batch lock. Lovable half:
`docs/lovable-cards-r3-prompt.md`, owner applies); R4 mixed-entity
export + persisted migration (pending owner answers: per-entity export
files? cash/personal tenders as cards? per-entity zoho_account?).

**R3 review residue (logged, not built):** re-stamp semantics after a
registry correction (stale ingest-stamped entity shows source "learned";
chain + provenance make it visible, operator overrides per row — design
call whether refresh should re-stamp, vs memory-origin stamps);
settings PUT whole-map RMW race (single-operator, cosmetic); GET->PUT
settings round-trip 400s if a generic alias was stored PRE-R3 behind the
API (read-side the alias is inert; verify prod settings clean at
deploy); assignment during an in-flight attach match window is not baked
into that match (assignments happen on the batch page pre-attach in
practice; the pool-based mismatch warning fires on a 0-match outcome).

**Export policy (user ruling 2026-08-21):** unresolved card/entity never
blocks an export — placeholders, adjustable later, re-export folds it in.

**R4 owner answers (2026-08-22):**

1. *Mixed-entity export:* **one file with the entity as a column.** Shipped
   (Shipped row 18). The export already wrote per-row entities after R3, so
   the work was pinning the ruling and closing the gate gap beside it: an
   entity-less batch was provisioned against NO chart, and now every row is
   validated against the chart of the entity that pays it.
2. *Cash and personal tenders as cards:* **no, handled at end of month.** No
   code: the per-batch "assign this hint, this month only" path from R3 is
   exactly that, and generic tenders are already refused as learned tokens so
   they cannot silently become permanent.
3. *Per-entity `zoho_account`:* moot. "Zoho does not matter anymore, the app
   should have no connection or ties to zoho anymore" became item 23, and
   layer 1 shipped the same day.

**Still open in item 10:** persisted cards migration (the registry still
composes read-time from the legacy maps; every card reads `source: "legacy"`)
and intake dropdown unification.

### 11. Intake: delivered files + Month column + delete month (SHIPPED — PR #561)

Shipped with the delete-month cascade (note 2, which had no own item) as
the quick-wins round; see the Shipped table row 9. Review residue worth
knowing: item 18 below (pre-existing async lock acquirers), and the
stranded-mail design call folded into item 12.

### 12. Body-only mail handling (SHIPPED — see Shipped row 10)

Shipped: sanitized body view, body-to-PDF render through the normal
pipeline, per-mail dismiss. The leftover design call moved to item 19.

### 19. Re-ingest for attachment mail stranded by a deleted month (SHIPPED - see Shipped row 19)

Owner said build it (2026-08-22). `POST /api/inbound/{archive}/re-ingest`
puts ONE archive's delivered attachments back into the month that is open
now. Deny-by-default: only mail carrying the `batch_deleted` stamp
qualifies, so it can never become a way to copy one month's receipts into
another, and a second click hits the same live-month refusal because the
first cleared the stamp. No bulk version, on purpose. SPA half:
`docs/lovable-re-ingest-prompt.md`.

### 13. Learned memory: validate + adjust (SHIPPED — see Shipped row 11)

Shipped: PUT/DELETE per row, validation stamps + unvalidated filter,
reset confirm gate. NOTE: the live SPA's Reset button is a silent no-op
until `docs/lovable-memory-edit-prompt.md` is applied (fails closed).

### 14+15. Language contract + honest receipt column (SHIPPED — see Shipped row 12)

Shipped: structured missing list, books_as sentinel, reason_label
dropped, honest receipt_image_available + source_file. The tile and the
i18n keys are SPA work in `docs/lovable-language-receipt-prompt.md`
(item 1 there is APPLY FIRST — the deployed split depiction shows a
blank account label on uncategorized parts until applied). The
parse/upload-issue prose piece moved to item 20.

### 20. Issue codes on upload/parse-issue prose (SHIPPED - see Shipped row 16)

Shipped 2026-08-22 exactly as the parked shape proposed: `issues` /
`upload_issues` keep their English prose and their `string[]` type, and a
parallel `issue_details` / `upload_issue_details` carries
`{code, file, suffix, limit}` at the same three emission sites (batch
create, folder ingest, add receipts). Four codes: `unsupported_type`,
`empty_or_unreadable`, `too_large`, `upload_cap` (the backlog's
"password-protected" case does not exist in the code). `service.upload_issue`
builds the sentence and the code in one call, so a reworded message cannot
drift from what the SPA localizes. Pinned in `tests/test_view_contract.py`
(the pin bites: an empty details list fails the non-vacuity guard, and
retyping `upload_issues` into objects fails the element check). SPA half:
`docs/lovable-issue-codes-prompt.md` — optional, the English sentences render
unchanged until it is applied.

### 21. Backend view shapes reach the SPA unverified (SHIPPED - see Shipped row 13)

2026-08-22, found live: the batch page died on React error #31 for every
batch that HAS a parse issue. `parse_issues` ships as objects
(`{file, line, message, severity}`, service.py:2745 and :4300, added
2026-07-22 beside the raw `parse_errors`); the SPA typed the field
`string[]` and rendered each item directly, so React threw and the root
error boundary ate the whole page. Latent from the 2026-08-21 SPA commit
that added the block until a batch finally carried an issue.

This is item 20's proposed pattern already having failed once: adding a
richer parallel field is only safe if something CHECKS that the SPA
absorbed it. Nothing does — the SPA is a separate repo with no type-check
against the live API, and our tests assert the backend's shape only.

The SPA fix is PUBLISHED and live-verified 2026-08-22 (bundle handles
`ParseIssue[]` with a string-tolerant fallback; batch ae61e122a505 renders
36 rows and shows the quarantine note, zero console errors). The
recurrence-kill shipped the same day: `tests/test_view_contract.py` pins the
element type of every list field on BOTH view payloads, probed over HTTP so
`jsonable_encoder` is included, with a non-vacuity guard (a MUST_COVER set
the fixtures have to actually populate) and `docs/api-contract.md` as the
prose the Lovable prompts cite. Proven by regressing both emission sites to
`string[]`: 3 of the 4 tests fail. Scalar-type flips are NOT covered by
design (see the doc); lists are where the crash class lives.

### 22. "Categorized" meant two different things (SHIPPED - see Shipped row 15)

Operator note, 2026-08-22 13:34 on /expenses: "it sayz 35 categorized but
when you click on open it says only 5 categorized". Both numbers came from
`n_categorized` on the same batch (April 2026, ae61e122a505): the list
screen counted expenses that carry a category (35 of 36 — true), the batch
page counted rows whose review state was `ready`, so the 30 rows that were
categorized but had no legal entity yet were reported as uncategorized. The
NEEDS CATEGORY tile claimed 31 rows when exactly 1 needed a category, right
beside a MISSING ENTITY tile already saying 30.

The page's count was `ready`-based since Phase 4; Cards R3's `needs_entity`
review state turned a small discrepancy into a 30-row one. Fixed by giving
each count one question (`service.categorized_counts` is the single rule,
readiness keeps its own `n_ready`) and by deriving the list screen's counts
from the same live overlay the batch page renders, so a reviewer's edit
moves both. Sibling class to item 21: not a type flip, a MEANING flip, which
no type contract could have caught — `docs/api-contract.md` now carries the
counts table and the one-name-one-question rule.

### 23. Cut every tie to Zoho (owner directive 2026-08-22)

**Owner direction:** "zoho does not matter anymore, the app should have no
connection or ties to zoho anymore" (answering the Cards R4 question about
per-entity Zoho accounts).

The surface splits into four layers, and they do NOT ship together:

1. **The live connection — DONE (Shipped row 17).** The API client, the
   journal-posting CLI, the `coa_source: "api"` live chart pull, and the
   `seed-zoho` importer are deleted. ~1,600 lines plus their tests. Nothing
   hosted ever used them (the Fly app has no `ZOHO_*` env and the web layer
   never imported the client), so hosted behavior is unchanged.
   `tests/test_no_zoho_connection.py` keeps them gone.
2. **The field names** (`zoho_account` on cards, merchants, learned memory,
   `posting_category.zoho_account`). The SPA reads these, so the rename is a
   parallel-field migration plus a Lovable prompt, per the api-contract
   rules. Not started.
3. **The chart-of-accounts gate** (`coa_gate.py`, `coa_provision.py`,
   `has_coa`, the `/data` chart file). The mechanism is "validate categories
   against the operator's account list" and is worth keeping; what it needs
   is a rename and a chart source that is not a Books export. Not started.
4. **The export artifact** (`output/zoho_expense_export.py`, the
   `EXPENSE_COLUMNS` Zoho-import headers, the `/runs/{id}/zoho.csv` route,
   the SPA's "Download Zoho Expenses CSV" button). **UNBLOCKED 2026-08-23 —
   do not re-ask.** The question this was waiting on ("what does the CSV get
   imported into now?") was answered by the output-is-a-document directive:
   there is no target application at all, so nothing imports the headers and
   they stop being a contract. `EXPENSE_COLUMNS` can be renamed to plain
   English on its own schedule, and the button's wording is part of
   `docs/lovable-month-report-prompt.md`. Sequence it AFTER layer 2, which
   moves the same names on the SPA-facing payloads.

**2026-08-28 user test confirmation (the account dropdown):** the GL
dropdown on the batch grid (E600010-* / E500010-* codes) surfaced in live
testing and the user's read was "pretty sure this is not necessary
anymore." To be exact about what it is: the codes are the chart-of-accounts
master data in the app's settings, seeded once from the Zoho Books chart on
2026-08-06; no live Zoho tie remains (layer 1 deleted). Its remaining
consumers are the deliverable documents (the workbook annotation and the
report PDFs show the resolved account per row) and the layer-3 chart gate.
Whether Brisken still wants code-level GL classification in those documents
at all, or categories only, is the one product question left here; it
decides how much of layers 2-4 is a rename and how much is a removal. Ask
Dirk/Criss at the table.

**Same test, minutes later, and it escalates the priority of layer 2:** the
reconciliation page reads "94 charges from the bank statement, matched
against Zoho Expense receipts", and the setup banner warns "Card 'Brisken'
has no Zoho paid-through account set ... only the Zoho journal export uses
it". The user's immediate read was "why are we still matching things
against zoho data? i dont want this connected to zoho." The matching is
against the uploaded scans, and the journal export the banner serves has no
destination since the output-is-a-document ruling; the words alone made a
disconnected system read as a connected one, in front of the operator, on
demo day. The stale copy is now actively costing trust, not just tidiness:
sweep the user-visible "Zoho" strings (run page copy, the paid-through
banner, the CSV button) in the next code round rather than on layer 2's
own schedule, and drop the paid-through warning outright if the journal
export goes with layer 4.

**Owner ruling 2026-09-15: "rename or delete whatever is necessary to make the
app better."** The open product question in this item (whether the deliverable
documents should carry GL account codes at all) is answered, with evidence
rather than by preference: on the live July workbook, 341 cells carry an account
value, and **64 of them are a real GL code the category alone does not give**
("Meals & Entertainment" resolving to "E100010-31 - Travel Expense | Food");
236 are the fallback echo of the category and 41 are blank. So the account layer
stays and gets renamed. What has no job left is the Zoho SHAPE: the journal
export emits 3 of July's 26 reconciled charges and every account line is a
placeholder. Layers 2-4 are therefore a rename, plus one deletion.

**Ordered plan, from a four-way inventory (106 classified items, 2026-09-15).**
Three constraints set the order, and every round is a consequence of one:

1. A removal inverts the usual order. For an ADD the backend ships first; for a
   DELETE the consumer stops calling first. The published bundle calls
   `/runs/{id}/zoho.csv` from TWO lazy chunks (`chunk-runs._runId` via
   `sum.dl.zoho`, and `chunk-classic`), so the Lovable prompt publishes and is
   re-audited BEFORE the route dies. The visible labels no longer say "Zoho", so
   only the route string finds them.
2. The journal file is load-bearing before it is deletable: `zoho_export.py`
   defines nine helpers that two surviving modules import.
3. A parallel field is two deploys with a publish between them, and the snapshot
   reader has to be tolerant one deploy EARLIER, because `serialize.py:69` reads
   `d["zoho_account"]` with a bare subscript.

| Round | What | Gate |
|---|---|---|
| 1 | Lift the nine shared posting helpers to `output/posting_common.py` | **SHIPPED PR #881** |
| 3 | Backend-owned human strings + the download filename | **SHIPPED PR #881** |
| 6a | Writeback column to "Posting account (tool)", old header read forever | **SHIPPED PR #881** |
| 2 | Dead code + free internal renames (`read_journal_csv`, `_carry_zoho_account`, `zoho_account_for`, `ClassificationResult.zoho_account`, `LineVerdict.zoho_account`, `from_api`) | backend only |
| 4 | Delete the journal artifact | **SPA-GATED**: prompt publishes, re-audit, THEN the backend PR. Prompt written 2026-09-16: `docs/lovable-journal-callers-prompt.md` (three callers: the workbench Downloads button, the `/classic` Published-runs button, the Settings `export_approved_only` card). Gate: `zoho.csv` 0 hits in every chunk (2 today) |
| 5 | Rename `zoho_expense_export.py` + `EXPENSE_COLUMNS` to plain English | backend only, atomic |
| 6b | The remaining pure-copy i18n strings | Lovable paste |
| 7 | ADD the parallel fields (`posting_account` beside `zoho_account`), accept both on every write | backend only, additive |
| 8 | SPA flips to the new keys, then re-audit | **SPA PUBLISH** |
| 9 | Remove the old keys + the internal renames that waited on them | backend only |
| 10 | Reissue the two June client deliverables | comms-gated |

**Round 7 is where the silent failures live.** Three, all found by reading:
`normalize_cards_setting` and `normalize_merchants_setting` DROP unknown keys
instead of rejecting them and `settings["cards"]` is whole-map replace, so a
backend that stopped accepting `zoho_account` would answer 200 and erase every
card's posting account on the next Settings save; `app.py:2281`
`keep_account = "zoho_account" not in body` is a load-bearing absent-means-keep
contract the SPA exploits deliberately, so the parallel version must compute
absence across BOTH spellings; and `merchants_inert` derives from
`entry.get("zoho_account")`, so renaming without it gives a permanently empty
hint list with no error. `test_view_contract.py` green is NOT evidence for any
of this: it records list element kinds, and every field here is a scalar inside
an object.

**Round 5's sharp edge:** `month_report_pdf.py:138` builds a name-to-index map
and returns `""` on a miss, so renaming an `EXPENSE_COLUMNS` entry silently
blanks the month report listing and the per-currency totals with no exception.
Nine literals must move in the same commit, and the rename needs a
`regress_check` proof that a test goes red THROUGH the PDF builder.

**Decisions taken, do not re-ask.** `export_approved_only` is deleted with the
journal in round 4: its only consumer is `regenerate_zoho`, and the SPA ships a
live Settings toggle whose help text names "the Zoho journal", so the moment the
route dies it becomes a control that changes nothing. The two SQLite columns
(`category_overrides.zoho_account`, `merchant_category.zoho_account`) are NOT
migrated; they are mapped at the read boundary in round 9, because neither store
has a RENAME path and a live-volume migration for a name no human reads is the
worst risk-to-benefit trade here. `has_coa` and `coa_gate.py` keep their names:
"COA" is ordinary accounting vocabulary, not a vendor name.

**Kept deliberately, in every round:** "Zoho Expense report PDF". That is the
real name of a file format Criss receives, and the backend error has to match
the SPA dropdown label or it stops telling her which file to pick. Also
`docs/electronic-storage-system-description.md`, where naming Zoho Books as the
external book of record is what the GoBD audit-trail argument rests on.

**Vocabulary, decided once** so she does not read three words for one thing:
**Account** in the report PDFs (already there), **Posting account** wherever a
distinction is needed (workbook, CSV, Settings, writeback), **Expense report
category** only for the source document's own category.

**Open, needs a live read before round 9:** the legacy `card_accounts` /
`card_entities` settings keys are composed at read time (`cards.py:572`), so
retiring them silently drops any card mapping still living only in the legacy
map. Read the settings row on the volume first.

**Amendment 2026-09-16 (note #43, item 81): four FX field names the inventory
missed.** The candidate `fx` block (`_fx_breakdown`, `web/service.py`) carries
`zoho_rate`, `zoho_converted`, `converted_gap` and `converted_gap_pct`, and the
SPA labels the first "Zoho's rate" (`wb.fx.zohoRate`). None is in the ordered
plan above. They are a RENAME, not a deletion: an expense-report PDF receipt
still fills them from `base_amount` / `exchange_rate`, and that file format is
kept deliberately. Round 7 adds `report_rate`, `report_converted`, `report_gap`,
`report_gap_pct` beside them (the expense report's own booked conversion), round
8 flips the SPA, round 9 removes the old keys; `wb.fx.zohoRate` joins round 6b.
Item 81's new `reference_*` fields are a different quantity (the tool's own rate)
and do not replace these.

### 24. The output is a document now (owner directive 2026-08-23)

**Owner:** there is no target application at all. "The output should be first
an expense report like in Zoho with an organized listing then all the
receipts", and for reconciliation "we wont be specifically exporting it into
any application, so we just need to think of what the best course of action
is."

**Shipped (Shipped row 20):** the month's report PDF —
`GET /runs/{id}/expense-report.pdf`. Listing built from the export's own
rows (money cannot drift between document and file), then every receipt
behind a caption naming the expense it proves. Evidence is per DOCUMENT, so
a split receipt appears once captioned "Expenses 3, 4". Missing and
unrenderable documents are stated, never dropped. SPA half:
`docs/lovable-month-report-prompt.md` (PDF primary, CSV demoted to
"data export", the word "Zoho" leaves the button).

**Both halves are shipped AND deployed (Shipped rows 20/21).** The
reconciliation half went out the same day, as the recommendation described: the same document shape, not a CSV. A reconciliation's product
is evidence that a month is complete: each statement charge with its matched
receipt and status, then the exceptions (unmatched charges, unmatched
receipts, duplicates), then the receipt pages. Keep the XLSX beside it as the
working sidecar (Criss works in Excel and her fill-colour is real data), keep
a CSV available but demoted. This also resolves Zoho layer 4 of item 23: the
export's column names stop mattering once nothing imports them, so
`EXPENSE_COLUMNS` can be renamed to plain English on its own schedule.

### 25. OCR reads the year wrong on some receipts (SHIPPED - see Shipped row 23)

Diagnosed and shipped 2026-08-24. It was not one row: ELEVEN of the April
batch's 36 readings were dated 2020-2023. Of the three cases this item named,
only the first survived. The stored extractions already held those years
(parse is a plain `fromisoformat` on the model's ISO string, so that layer was
innocent), and the receipts do not print old dates. Two model mechanisms, both
readable off the images: `receipt_33` prints `Data: 2026-04-22` in its fiscal
block and `26-04-22` (YY-MM-DD) on the card slip, and the model read the slip
day-first as 2022-04-26; `receipt_03` prints `02/04/2026` and the model
returned 2023-04-02, day and month right and the year invented.

The prompt was tightened and MEASURED rather than assumed: six of the eleven
move into April, 24 of the 25 already-correct readings are byte-identical, and
the twenty-fifth changed to the value the receipt actually prints. Five stay
wrong, so the load-bearing half is the deterministic guard beside it.

**Live-verified after deploy (2026-08-24), all five batches on the volume.**
The April batch flags 13 of 38: the eleven misreads plus the two August
receipts added by hand on 08-22/23, which really are not April expenses. The
report PDF now names them ("The date read on expenses 2, 8, 11, ... falls
outside this month"), and expense 2 is the 2023 row the owner spotted on line
two. The no-noise check that matters: in Criss's REAL May month every one of
the 20 genuine receipt rows falls inside the window and none flags. Its four
flags are Chase STATEMENT pages that leaked in as expenses before the
quarantine shipped, whose dates are Jan/Feb/Mar/Jul — the guard finding
already-known phantom rows, not a date defect. The two January test batches
are genuinely mixed-month agent fixtures spanning Nov 2025 to Aug 2026, so
their flags are honest.

**Noted behavior, not built:** a label naming a month with NO year ("January")
is refused as a month claim, so that batch falls to its own dates and the
consensus can pick a different month than the label's word. Real labels carry
the year, so this only shows up on agent fixtures. The cheap fix if it ever
matters is to take the year from the batch's dates for the month the label
names.

### 27. The date guard catches a wrong month, not a wrong day (2026-08-24)

**Narrowed, not closed, 2026-08-24 (see Shipped row 24).** The vision model
moved to gpt-5-mini after measuring: dates went 3.0 -> 5.0 of 6 over the
problem receipts, three runs each. Everything cheaper was tried and refuted
first — repeat reads return the IDENTICAL wrong answer (stable, not noisy), a
verbatim transcription beside the interpreted value agrees even when both are
wrong, and gpt-4o is no better than gpt-4o-mini.

What is left: `receipt_12` still reads a wrong DAY inside the right month
(2026-04-27 against a printed 02/04/2026). And better year reading makes this
class HARDER to see, not easier: an error that used to land in 2023 and trip
the date guard now lands in the right month and passes silently. The guard
judges the month; nothing judges the day. Still parked until Criss reports one,
but that is the trade to know about.

Residue from item 25, deliberately left. `batch_period` judges a date against
the batch's month plus its two neighbours, so a reading that lands in the
right month with the wrong DAY passes silently: after the prompt fix
`receipt_12` reads 2026-04-22 against a printed 02/04/2026, and `receipt_34`
reads 2026-04-23 against a printed 21/04/2026.

Lower severity on purpose, and the ranking rule says so: a wrong day does not
change which month the expense belongs to, which was the harm item 25 named.
It can still cost a statement match, since matching weighs date proximity.

No obvious deterministic catch exists (nothing in the batch says which day a
receipt is), so the honest options are a second read that must agree, or
surfacing low extraction confidence. Both cost money per receipt. Worth
picking up only if Criss reports a day error, or if the item-4 category watch
gives us a reason to add a second-read pass anyway.

### 28. The paying card, read off the scan (2026-08-24)

**Owner direction:** make sure the card an expense should be attributed to can
be extracted from the receipt scan as well.

It could not be. Measured over the April batch: asked to transcribe four faded
digits the extractor landed 2 in 5 and INVENTED the rest. "1234" came back
three separate times, once for a receipt that plainly prints 1672 and once for
one that prints 0340. Several live hints are near-misses of a real card (9340,
2038, 7312, 6742, 07009 against the real 0340 / 2838). Repeat reads do not help:
three reads of each problem image returned the identical wrong answer, so the
misreads are stable rather than noisy, and no amount of re-asking finds them.
Nor does a second field in the same call: `date_text`/`payment_line` verbatim
transcriptions agreed with the interpreted values even when both were wrong,
because they come from the same look at the page.

What worked was changing the QUESTION. The answer only ever has to be one of
the handful of cards Brisken holds, so the extractor is now handed those last-4s
(from the run's own card registry snapshot) and asked which one it can see, or
none. Deny-by-default: no registry means no list and `card_last4` always null.

**Shipped (Shipped row 24).** `card_last4` beside `payment_hint`; a confirmed
pick replaces whatever digits the free-text hint guessed and keeps the tender
words around it; a hint with no confirmed pick passes through untouched (an
unlisted run resolves to no card anyway, and dropping it would hide a card the
registry has not been told about yet — the live 0340 case); a number that does
not reduce to exactly four digits never reaches the entity chain. The card list
is part of the extraction-cache key, since the same photo asked against a
different set of cards is a different question.

### 29. The living month: date-pooled mail, gradual statements (2026-08-24)

**Owner directives (2026-08-24), a three-PR plan.** The month stops being
"upload everything, then sit an exam" and becomes a workspace the accountant
works across the whole month.

**PR 1 - the mail pool. SHIPPED (#599 + #601), see Shipped row 25.** Incoming mail stopped
filing into whatever month happened to be open (which is how Dirk's August
receipts landed in the April 2026 batch). It now files by the month printed
ON the receipt, and rests in a pool when that month has no batch yet.

**PR 2a - stable transaction identity. SHIPPED.** The prerequisite, split
out of PR 2 because the other four parts sit on it and it carries no
behavior change of its own. Transaction ids are now derived from what the
row SAYS (sha1 over account / card / date / canonical amount / currency /
vendor / reference, 16 hex chars, `-{n}` suffix for repeat charges) instead
of where it sat in the file. Stamped by one shared `assign_content_ids`
post-pass in `ingest/_common.py` that all three parsers call at the end of
a parse, AFTER sign canonicalization, so a mapped `type` column and an
inferred sign majority cannot give the same charge two identities. Nothing
at rest migrates: stored snapshots keep their positional ids and their
decisions still resolve.

The find, which the plan did not name: `sheet_writeback._anchor_row`
recovered the spreadsheet row by taking the positional id apart, so a
content id would have silently written NOTHING into Chris's workbook (it
degrades by design, no error). The row now travels in its own
`Transaction.source_row` field and the id-parsing path stays only as the
fallback for pre-2a snapshots. Related: the occurrence suffix separator is
`-` and not `:` precisely because that fallback reads the last `:` as a row
number, and `transaction_id` also travels as a URL path segment.

**PR 2b-1 - `rematch_month` + the judgment cache. SHIPPED.** The match that
used to live inline in `execute_statement_attach`, fused to the one-shot
attach, is now `service.rematch_month`: bake the reviewer's corrections into
the pool, match, judge, categorize receiptless charges, commit under
`_BATCH_ADD_LOCK` against a fresh re-read. The attach path is its first
caller and did not move by a byte. Every incremental path in 2b-2 calls the
same function rather than growing a second copy that drifts.

Beside it, `web/judgment_cache.py`: the living month re-matches on every
receipt arrival, and without a cache each one re-asks the model about pairs
it has already judged, on Dirk's key. Both judgment entry points reach the
model through exactly two client methods, so a proxy over those two covers
everything without the judgment layer knowing. Keyed by the CALL's content
plus the model that answered it, NOT by `(transaction_id, document_id)` as
the plan said: a reviewer can correct a receipt's amount after it was
judged, and an id key would hand back the verdict the model gave for the old
numbers. Entries merge onto the fresh row at commit, so a concurrent
re-match does not lose what it paid for.

**Open for 2b-2, from enumerating the guard:** `has_statement` refuses at
NINE call sites in three different classes, not one, so "lift the refusal"
is not a single switch. Must open: `POST .../receipts`, `POST .../statement`,
`POST .../set-aside/restore`. Should open, and only means anything once a
re-match follows: `POST .../cards`, `POST .../refresh-master-data`. Must
stay closed or needs a real decision: the four expense-edit overlay routes,
because the attach BAKES edits into the snapshot receipts and reopening the
overlay over a baked pool risks double-application.

**PR 2b-1b - the extraction baseline. SHIPPED.** The guard triage ran first,
as planned, and it refuted its own premise while finding something worse.
Double-application is NOT the risk: the overlay is idempotent by
construction, and deliberately so. `add` is guarded by an `existing_ids`
check written for exactly this case, `delete` is set membership, and every
header edit is an absolute assignment. Re-applying any of them is a no-op.

What the bake actually does is DESTROY the audit baseline. The snapshot is
not just the matcher's pool, it is the pre-edit record the grid composes the
overlay on top of and reads `raw` from ("the ORIGINAL extracted name ...
always kept for audit"). Measured on a batch whose reviewer corrected vendor
and total, then attached:

    pre-bake   snapshot {'vendor': 'OriginalVendor', 'total': '42.50'}
    post-bake  snapshot {'vendor': 'EDITED-BY-REVIEWER', 'total': '99.99'}

`raw` then echoed the reviewer's own edit, so the audit field reported the
edit it exists to distinguish. Clearing the edit -- documented on
`set_expense_field_override` as "the expense reverts to its extracted value"
-- silently did nothing, because there was no longer an extracted value to
revert to. The 42.50 the OCR read was gone from the system. Same root cause
in the learning harvest, which keys corrections on the ORIGINAL extracted
vendor and post-bake was keying them on the corrected one, so a month that
had been attached taught the merchant book nothing.

This is live behavior on every attached month today, not a 2b-2 regression.
2b-2 is what makes it urgent: once a re-match runs on every receipt arrival,
the erasure stops being a month-end event and happens continuously, minutes
after a correction.

Shipped as `extracted_receipts`, a parallel snapshot key holding the
pre-bake receipts, first-write-wins PER DOCUMENT (a second re-match reads an
already-baked snapshot, so refreshing would capture the baked values; growing
per document is what lets receipts that arrive later join). The four
overlay-composing reads -- grid, export, learning harvest, batch-list counts
-- start from it; matching, the reports and the reconciliation views keep
reading the baked pool, which is baseline + overlay by construction. Runs
attached before this shipped have no baseline and fall back to what they had;
nothing at rest migrates. Snapshot receipt bytes roughly double (the baseline
carries `ocr_text` too), accepted rather than stripping fields the export
composes from. Neutral against the whole suite: 1312 -> 1316, the +4 being
these tests, no pre-existing test moved.

**The overlay-route decision, now evidence-backed:** the four routes STAY
CLOSED in 2b-2. Not because re-applying an edit is dangerous (it is not), but
because opening a reviewer-facing edit surface is only worth doing once the
edits it takes are reversible and honestly attributed, which is what the
baseline restores. Reopening them is its own round, with the re-match wiring
that has to follow an edit, and it is not on the critical path for the living
month.

**PR 2b-2a - the month stays open. SHIPPED.** The guard was TWO layers, not
the nine call sites the enumeration found: those nine are routes through one
gate (`_mutable_expense_run_or_error`), and beneath five of them sat five
more refusals inside the service functions themselves
(`_add_receipts_locked`, `restore_set_aside_file`, `assign_batch_cards`,
`refresh_batch_master_data`, `prepare_statement_attach`). Lifting only the
routes would have moved the 400 one layer down and changed nothing.

Four operations now stay open all month: receipts arriving, a set-aside page
restored, a card assigned, master data refreshed. Each is followed by
`service.rematch_after_change`, because allowed-but-inert is worse than
refused: the receipt would sit in the pool while the match outcome still
described the month as it was before. It runs OUTSIDE the caller's lock span
(`_BATCH_ADD_LOCK` is not reentrant and `rematch_month` takes it to commit),
and it is skipped when an upload added nothing, so an all-duplicate add pays
for no model calls.

A re-match failure is REPORTED, not raised. The caller's change is already
committed when it runs, so a throw would mark a receipt that safely landed as
`held_failed` and replay it -- an OpenAI outage would do that to every receipt
Dirk sends. The error rides back in the result and the next trigger retries,
so the month's match state is a truthful stale rather than a wrong fresh.

Pool side: a month with its statement now claims its pooled mail instead of
declining, and `pool_month_state` reports `reconciling` where it said
`closed` (parallel value; `closed` is retired but still handled, and
`status_label` already carries the prose so no SPA change is needed).
A statement-less month still wins a same-month tie.

**The adversarial find, and the recurrence-kill:** the item-18 AST guard that
stops an `async def` route from parking the event loop derives its locked set
by scanning for `with _BATCH_ADD_LOCK` in a function's OWN body. Every
lock-taker held it that way until `rematch_after_change`, which takes it one
call deeper -- so the guard reported it as safe, and a future async route
calling it directly would have frozen every endpoint including `/healthz` for
the minutes a re-match runs, exactly the failure that had Fly restarting the
machine mid-ingest. The locked set is now a transitive closure. Proven by
mutation: adding that call to a real async handler turns the guard red.

Still closed, each pinned by a test: a second statement upload (append is its
own round, below) and the four expense-edit overlay routes.

Suite 1316 -> 1325, calibrate exit 0, ruff clean on the diff. Both halves
proven by mutation: restoring the guard reddens 5 tests, unwiring the
re-match reddens the 2 that specifically catch allowed-but-inert.

**PR 2b-2b-1 - the fold. SHIPPED (#632).** The parse / content-id / dedupe
foundation, landed and proven neutral before the `statements[]` surface goes
on top of it. `merge_transactions` (`ingest/_common.py`) folds a freshly
parsed statement into a month's charges by identity, keyed on the content id
2a made stable. It adds no second definition of sameness: two rows are the
same charge exactly when `transaction_content_id` says so, and the occurrence
suffix already keeps two identical coffees apart ACROSS uploads, not only
within a parse. Three properties the append route leans on: first-write-wins
(a re-supplied row keeps the object the month committed, so decisions and
`source_row` stay pointed at it), `existing` passes through untouched (the
fold filters what an upload contributes, it never edits the month), and a
sign contradiction lands as two rows rather than being deduped to whichever
arrived first.

Beside it, two seams the append path needs: `read_statement_upload` splits
the STATEMENT half out of `execute_statement_attach` so a second file is read
exactly the way the first was, and `month_transactions` reads the charge
block alone instead of rebuilding every receipt to reach it.

**The neutrality is real, and so is its limit.** `prepare_statement_attach`
still refuses a second upload, so on the attach path `existing` is empty and
the fold IS the identity function. No test can tell an attach that routes
through it from one that does not, and `tests/test_statement_merge.py` says
that in its own comments rather than dressing an inert call up as a wiring
proof. What DID bite, by mutation: disabling the dedupe reddens 7, stubbing
the extracted read reddens 6 (four of them pre-existing living-month tests).
Suite 1325 -> 1336, calibrate exit 0.

**PR 2b-2b-2 - the `statements[]` surface. SHIPPED.** `POST .../statement` is
append-capable and repeatable. The refusal came out of BOTH layers it sat in,
deliberately: the route gate (`_mutable_expense_run_or_error`, now the plain
expense-run check) and `prepare_statement_attach`'s own check beneath it, which
2b-2a had already shown is where a route-only lift dies. Two tests pinned the
closed door and now pin the open one, in `test_living_month.py` and
`test_web_expense_lifecycle.py`; the second was found by the full suite, which
is the gate working. The fold stops being inert: `existing` is now whatever the
month holds, and 16 tests in `tests/test_statement_append.py` fail if it is
unwired.

`statements[]` records every upload as a parallel field on BOTH review payloads
(`{file, upload_name, card_key, account_id, sheet_name, period_start,
period_end, n_rows, n_new, uploaded_at, writeback, advisory}`), written by
`rematch_month` inside the commit lock so the month has one writer.

**The wrong-cell hazard, and what the fix had to become.** The plan said the
per-row source travels with the row. It cannot. A charge occupies a row in
EVERY file that prints it, at a different row in each, because a mid-month
partial and the closing cycle both contain it; a field on the charge can only
name one file, and first-write-wins (rightly) keeps the first. Built that way
first and caught it in adversarial review by walking the canonical scenario:
the closing cycle is the workbook Criss works from and the default download,
and it would have been annotated ONLY for the charges it introduced, every
repeat left blank, looking like charges the tool could not resolve. So the
anchors are recorded per UPLOAD instead: `statement_anchors`
(`{file: {transaction_id: row}}`), snapshot-only, never in a payload, and
`write_sheet_writeback(anchors=...)` writes exactly the charges that file
contains at the rows it puts them on. `Transaction.source_file` was reverted;
nothing read it once anchors existed. Proven by mutation both ways: disabling
the anchor path reddens the cycle-after-partial test and the cross-workbook
test.

Two more found in the same review. A second upload with the same basename
overwrote the first on disk (`_unique_upload_name` now gives each its own
name), and a recorded-but-EMPTY anchor map read as "not recorded", which would
drop a zero-row workbook back to placing every charge in the month by row
number.

**The account-id hazard, decided once for both cases.** Surface it, dedupe
nothing. Two uploads that disagree really are two rows (that was already 2a's
call for a flipped sign), so the addition is saying so: `advisory` fires when
one `card_key` is typed against two account ids, or when an upload lands 100%
new over a period the same account already covers. Advisory only, on the entry
and on the job's warning channel beside `entity_mismatch`; nothing is dropped,
merged, or refused on a heuristic about what an operator meant. A clean
per-card append stays silent, which is pinned.

**A race the round opened, closed with it.** Both the attach path and every
re-match read their charges minutes before committing them, and a concurrent
upload can now genuinely add rows in between; the older set would have erased
them silently. `rematch_month` now refuses, inside the lock, any commit that
would DROP a charge the month already holds. Strictly stronger than the
`require_no_statement` check it replaces (which stopped meaning anything once
a second statement was allowed), and it covers the receipt re-match path too.

Also: `GET /runs/{id}/statement-categorized.xlsx?file=` selects which statement
to write back, resolved against `statements[]` (a name not in it is a 404, so a
query string cannot address a file the month never took). Per-upload
`sheet_name` is recorded because `config.statement` only ever describes the
latest one.

Suite 1336 -> 1352, calibrate exit 0, ruff clean on the diff. Nine mutations
run, every guard red under its own.

**Closed by PR 3 below**, whose Lovable prompt carries the `statements[]`
panel and the `?file=` selector along with the coverage panel.

**PR 2b-2 - the living month (the original plan item).** The statement stops
being a closing event
and becomes an input stream:

1. **Stable transaction identity** (the prerequisite). Transaction ids are
   positional today (`f"{account_id}:{row_index}"`, `ingest/statement_csv.py`),
   and operator decisions key on them, so an appended or partial upload
   renumbers every decision onto the wrong charge. Replace with a
   content-derived id: `sha1(account_id | card_last4 | transaction_date |
   amount | transaction_currency | vendor_from_statement | reference)[:16]`
   plus an occurrence counter, so two identical coffees on one day stay two
   charges. One shared helper in `ingest/_common.py`, applied in all three
   parsers. Stored snapshots keep their positional ids; old decisions resolve.
2. **Gradual uploads.** `POST /api/expense-batches/{run_id}/statement` becomes
   append-capable and repeatable (per card, several times a month): parse,
   content-id, dedupe against the existing set, append. Snapshot gains a
   `statements` list (parallel field). The one-shot attach is the degenerate
   case of the same path.
3. **The month stays open.** `has_statement` stops meaning closed; the
   `_mutable_expense_run_or_error` refusal is lifted, so receipts join a
   statement-bearing month freely. PR 1's `pool_month_state: "closed"` becomes
   `"reconciling"` (parallel value).
4. **Incremental re-match.** Every receipt add and every transaction append
   re-runs deterministic matching over the full sets, preserving operator
   decisions (keyed by the stable id) and persisting LLM FX/ambiguous
   judgments by `(transaction_id, document_id)` so a re-match never re-spends
   on a pair it already judged. `execute_statement_attach`'s bake logic
   refactors into `rematch_month(run, ...)`, which both paths call.

**PR 3 - the coverage surface. SHIPPED**, see Shipped row 28.
`coverage[]` on both review payloads: one row per card the month knows about,
carrying which uploads covered it, the span of ITS charges, the run summary's
own four bucket counts for its charges alone, and its share of the
unreconciled money. Per-card sections in the reconciliation document, grouped
on `rows[].coverage_key` so a section and the coverage table cannot disagree
about which card a charge is on. The SPA half,
`docs/lovable-coverage-prompt.md`, went live 2026-09-06.

**The registry cards with NOTHING loaded are the point, not padding.** The
question is "which cards have statements", and it is only answerable from a
list that includes the ones that do not; an entry reading 0 charges and no
statements is the only place a reviewer sees what she still has to load.

**One derivation, because two screens.** `charge_states` is now the single
place a charge's effective bucket is decided, and the workbench rows, the
summary's four counters and the roll-up all read it. The grid pays for its
own `snapshot_from_dict` + `apply_decisions` on a reconciling month so it can
answer with the reviewer's decisions applied; a cheaper pre-decision answer
would have been a second meaning on the same five names, which is the
`n_categorized` failure of 2026-08-22 with money on it.

**Two defects the adversarial review found, both in card identity.** A card
is keyed by an operator-chosen slug, and nothing stops that slug from being
digits that are not the card's own; without a namespace on the unknown-card
key, charges on the REAL 2838 would have landed in a card merely KEYED "2838"
and its money would have been reported against the wrong plastic and the
wrong entity. And resolution was reached only when the observed string
carried digits, so a card named by alias alone ("CorpServ", which is how
Zoho's payment modes name them) fell to "No card on the charge" even though
the registry knew exactly which card it was. Both are pinned.

**Ruling pinned, no build needed:** statement charges with no receipt (fees,
direct debits; January reality was 78 of 80) stay exceptions in the
reconciliation report and are never auto-created as expense rows. Expense count
is not expected to equal transaction count.

### 30. The intake cannot tell anyone whether a receipt arrived (2026-08-24)

Surfaced by an owner question ("Dirk has sent way more than 2 emails, make
sure they are there") that took a full investigation to answer and still
ended partly unanswerable. Three defects compounded into one: nobody,
inside or outside, could establish whether a mailed receipt landed. **All
three shipped 2026-08-24 (Shipped rows 26 and 27); this entry is now
history.**

**a. Outside senders get total silence. SHIPPED.** Dirk sends from
`dirk_.neumann@icloud.com` as well as his work account, and
`graph_notify.send_mail` hard-refused any recipient not ending
`@brisken.com` (the anti-backscatter guard from PR #587), so an iCloud
send produced no ack and an accepted-but-held mail produced no bounce
either. Shipped as settings `intake.known_senders` (NOT the
`ack_addresses` this entry first proposed: the same list also gates (c),
and a name that says "ack" would have been one name answering two
questions). `send_mail` takes an explicit per-call `allow_external` and
asserts the structural recipient guard BEFORE consulting it, so a listed
address widens the rule by exactly itself. Operator edit, no deploy;
Settings editor is `docs/lovable-known-senders-prompt.md`.

**b. A refused RCPT leaves no trace anywhere. SHIPPED.**
`rcpt_decision` returned the SMTP error line and nothing was written: no
archive, no log row, no counter. Shipped as `inbound/refusals.jsonl` +
`record_refusal`, covering the DATA-stage guards too (disk floor,
in-flight ceiling, day budget, archive failure) — those matter more,
because each one turns away a real submission whose envelope we already
accepted. `GET /api/inbound/log` gains `n_refused` (a 7-day window, not
the whole file, because the ledger is size-trimmed) and `refusals[]`.
Deliberately NOT rows in `entries`: a refusal has no archive, and a row
there with a status nothing recognises is exactly the enum-growth trap
that made pooled mail read as "Arriving".

**c. Forwarded vendor receipts are body-only. SHIPPED.** All SIX mails
held on 2026-08-24 carried NO attachment (`n_files: 0`, nothing skipped):
AWS billing, two OpenAI purchases, an OpenAI credits confirmation, the
CIC/Monetico card ticket, Hostinger. The receipt is the HTML body. That is
not the exception the render path was built for, it is the normal shape of
a forwarded vendor receipt, and every one sat held until an operator
clicked render. Shipped as auto-render at arrival for KNOWN senders only,
reusing the operator render path unchanged. The gate is the answer to the
spend question the click was really protecting: submission is open to
anyone, and rendering every stranger's newsletter costs a vision call and
puts junk in the pool. Every one of the six real mails came from Dirk
(work + iCloud) or Criss, so the gate covers the real traffic and the
`known_senders` list widens it.

**Not in scope:** the mailbox only exists since the dedicated IPv4 was
created 2026-08-21 09:17, so anything Dirk sent before that had no MX to
reach and is unrecoverable. Worth telling him once so he stops looking
for it.

### 31. A Settings control that silently discards what you type (CLOSED 2026-08-25)

**Owner applied `lovable-known-senders-prompt.md`; verified live by driving the app — the stale "Accepted senders" editor is gone and "People we recognise" is in its place.**

Found by driving the published SPA. The Settings > Email intake section still
carries the **"Accepted senders — Full addresses or @domain entries"** editor.
That is the retired `intake.senders` allowlist: submission opened to any
sender on 2026-08-23 (PR #587) and the backend now DROPS the key on save
rather than rejecting it, so whatever an operator types there is discarded
without a word. A dead control that looks alive is worse than a missing one,
and this one sits exactly where someone would go to authorise a sender during
testing — they would get a false result and reasonably conclude the tool is
broken.

Fix is entirely SPA-side and is now ONE paste:
`docs/lovable-known-senders-prompt.md` section 0 deletes the dead editor and
section 1 puts the field that DOES work (`intake.known_senders`) in its
place. The separate `lovable-open-intake-prompt.md` was folded into it and
deleted 2026-08-24, because two prompts for one Settings section is how the
paste order gets lost.

Beside it, two stale help lines that predate the month pool: "People who can
email receipts straight into the open month" and "the sender gets a short
reply when their receipts land in the open month". Receipts land in the month
PRINTED on them, or wait in the pool; the ack says which. That copy is what
sets a tester's expectations, so it is worth the same pass.

### 32. There is no way into an existing month (CLOSED 2026-08-25)

**Owner applied `lovable-months-list-prompt.md`; verified live — `/months` renders 1 table, 6 rows, 6 `/expenses/{id}` links and real month labels. The blocker is gone.**

Found by driving the published SPA. The "Months" nav item goes to `/months`,
which renders the "New expense batch" upload form and nothing else: **0
tables, 0 rows, 518 characters of body text, and no batch label anywhere in
the HTML**. `/`, `/expenses` and `/expenses/new` all render the same page.

The page DOES call `GET /api/expense-batches`; it answers 200 with six
batches. The response is fetched and discarded.

So a reviewer who opens the app cannot reach last month's receipts. The only
working paths are the `/expenses/{id}` links that happen to sit in the Email
intake page's Month column, and typing the URL by hand. Everything else works
once you are there: `/expenses/ae61e122a505` renders 40 expenses, the
card-review strip, the set-aside strip and both download buttons. It is only
the way IN that is missing.

No prompt ever asked for this screen, which is presumably why it does not
exist: every prompt since assumed a months list was already there.
`docs/lovable-months-list-prompt.md` is written and covers the list, rename
(the label decides which mail joins the month), delete (homeless since
`lovable-intake-quickwins-prompt.md` section 3), and the create advisory.

This blocks effective testing more than anything else open, including the
card-registry gaps: those make a month noisy, this makes a month
unreachable.

### 33. Duplicates reached the workflow before anyone saw them (SHIPPED 2026-08-25)

**Owner directive:** "we also need to be able to sort duplicates out before
they are ingested into the tool's workflow."

The only dedupe was the receipt pool's content check at ADD time. It created
no second expense, but the intake row still said "Added" about a mail that
added nothing, and a repeat routing to a DIFFERENT month landed in a batch the
first copy was not in, where that check had nothing to compare against. Live
evidence: three archives of "TEST - month pool drill (March 2026)" carrying
one identical PNG, and then the real thing while this was being built.

**Shipped:** arrival-time detection ahead of everything else, including the
body-only branch, so a re-sent body-only receipt no longer spends a vision
call. New `duplicate` status (kind `resting`, label names the original),
`duplicate_of`, `n_duplicates`, `POST .../not-a-duplicate` as the
deny-by-default escape hatch, dismiss widened. Attachments hash as
`sha1(bytes)[:16]` -- the SAME shape the receipt pool uses, so the two layers
cannot disagree about what "the same file" means; a body-only mail hashes its
whitespace-collapsed, casefolded body. Only a mail that ENTERED the workflow
owns its content, and every piece must be known before a mail is parked.

**Live, and NOT cleaned up:** Dirk forwarded the same Hostinger invoice
(H_46243348) three times at 22:50:32 / 22:50:57 / 22:51:15 on 2026-08-24,
about six minutes BEFORE this deployed. All three are pooled for 2026-07 and
all three will become expenses when July opens. Verified read-only that the
detector would have caught copies 2 and 3 (identical body fingerprint
`body:4c6f42927cd37c87`, 485 chars each). Dismissing two is terminal, so it
waits on an owner yes.

### 34. The way into a month is invisible (CLOSED 2026-09-06)

**Owner pasted `lovable-months-open-prompt.md`. Verified in the published
bundle: `months.open` = "Open" / "Abrir" wired to a row-menu item, an
"Actions for" label on the trigger, and the hover-only
`underline-offset-2 hover:underline` is gone.**

**Operator note, left on `/months` and anchored on a row's Created cell:**
"why cant the user enter and view or edit the month"

Nothing is broken, which is why this took reading the published bundle to
explain. Every month opens: `GET /api/runs/{id}` and
`GET /api/expense-batches/{id}` both answer 200 with real data for all six
batches, and item 32's prompt built the links.

What the published build actually renders (`chunk-months-Bvb2xrOV.js`,
fetched 2026-08-28):

- The month name is the only clickable thing in the row, and it carries
  `className="underline-offset-2 hover:underline"`. At rest it is styled
  like the plain text in every other cell; it becomes a link only once the
  pointer is on it.
- The table row has no click handler, so the counts, the Statement badge
  and the Created date are inert. The Created cell is where the note was
  left.
- The per-row menu holds exactly two items, Rename and Delete. Someone
  opening it to look for the way in finds no Open.

So the complaint is an affordance gap, not a routing bug, and it is entirely
SPA-side: `docs/lovable-months-open-prompt.md` asks for rest-state link
styling on the name, a clickable row (with the actions cell excluded), an
Open item at the top of the row menu, and an `aria-label` on the menu
trigger that says "Actions for ..." instead of repeating the month name.

No backend work. Nothing to deploy on our side.

### 35. The unknown-card strip lists spellings and tender words, not cards (2026-08-28 user test)

**User, testing the April demo pack on the live app:** "too much ambiguity
in this section, it must be improved; there should only be clearly defined
cards listed and not stuff like 'cartao de credito', we want the card
number."

What the strip showed for the fresh April batch: "26 receipts name a card
the tool does not know yet", across nine-plus rows. Five of those rows are
ONE card, 0340, under five spellings (`***********0340` x4,
`VISA - ******0340` x3, `****0340` x2, `*****0340` x1,
`CARTAO ***********0340` x1 = 11 receipts). Four more rows are digit-less
tender phrases (`CARTAO TEF`, `COMPRA CREDITO VISA`,
`Cartao Credito 30 Dias`, `Cartao de Credito`), each offering the same
Assign control as a real card.

Two defects in one surface:

1. **No canonical grouping.** CORRECTED 2026-08-28 after reading both
   repos: the grouping is SERVER-side already — `build_card_review`
   (web/service.py:4174-4231) emits `card_review.unresolved_hints[]`
   `{hint, n_rows, documents[], generic, ambiguous}` — but it groups by
   VERBATIM hint string, which is what renders five spellings of 0340 as
   five rows. The durable fix lands in `build_card_review`: key
   digit-bearing hints by their canonical digit run (the strict last-4
   rules in `cards.py`, leading zero preserved for display) and emit the
   member spellings per group as a PARALLEL field per the api-contract
   rules. Interim relief needs no backend change at all: the SPA can
   partition on the existing `generic` flag and display-group by trailing
   digit run, and `POST .../cards` already accepts a LIST of assignments,
   so one grouped Assign can submit every member spelling in one call
   (see `docs/lovable-*` prompt handed 2026-08-28).
2. **Tender words presented as cards.** Digit-less hints CAN be
   batch-assigned by design (R3 owner ruling: they assign for this batch
   only and never learn), but rendering them in the same list as
   digit-bearing rows presents them as card identities. Split them into a
   separate, labeled sub-strip ("no card number readable on the receipt;
   assignment applies to this month only") or fold them into a count with
   an expandable control. The capability stays; the ambiguity goes.

Halves: backend grouping (small, view-only, contract-test pinned per item
21's rules) + a Lovable prompt for the two-part rendering. Note the demo-day
interaction depends on item 26 either way: assigning the 0340 rows requires
the 0340 card to exist in the registry first.

**Vocabulary half SHIPPED 2026-08-29 (this round):** `tef`, `compra`,
`dias` added to `GENERIC_TENDER_WORDS`, and `is_generic_tender` now
tolerates number words below the card-digit floor (the "30" of
`Cartao Credito 30 Dias`) while requiring at least one vocabulary word (a
bare "30" stays non-generic). All four April tender phrases now come back
`generic: true`; proven green-red-green by regressing the vocabulary. The
canonical last-4 server grouping remains open; the interim display
grouping is the SPA prompt handed 2026-08-28.

**Assigned 2026-09-06: the canonical-grouping half rides R1 as its FIRST
commit.** Item 41's `suggested_private` surfaces inside the digit-less
sub-strip this item creates, and R1 rewrites the strip's Lovable prompt
anyway; shipping the grouping separately would rework the same SPA surface
twice, with the second prompt having to describe the first prompt's output
to modify it. One R1 prompt describes the final strip once.

### 36. Month auto-suggestion at manual upload (2026-08-28 user question)

**User, same test session:** "why does the tool not automatically recognize
what month the receipts inserted are from?"

It half does. The MAIL path reads every arriving receipt at once and files
it by the month printed on it (item 29's pool). The MANUAL path deliberately
does not: the operator's label declares the month, and the receipt dates are
used the other way around, to flag rows that do not look like the declared
month (`date_outside_period`). That direction was chosen with evidence: the
extracted date is the least reliable field on a scan (11 of 36 April
readings carried wrong YEARS before #590; 3 dates come back blank in the
current rehearsal set), so routing by it silently misfiles, while
distrust-by-declaration only ever asks a human to look.

The gap worth closing is the missing SUGGESTION, not missing automation:
`batch_period.py` already derives a strict-plurality month from the batch's
own dates (it is the fallback when the label names no month). Surface that
derivation in the manual flow, confirm-first: after extraction, when the
plurality month is confident and differs from (or is absent from) the
label, say "these receipts read as April 2026" and offer to set/rename the
label. Never silent, so the item-25 ruling (nothing auto-corrected, the
operator's declaration stays authoritative) holds unchanged. Backend piece
is small (expose the existing derivation on the view); SPA piece is a
Lovable prompt.

**Backend half SHIPPED 2026-08-29 (this round):** the expense-batch view
now carries top-level `period_suggestion` (object or null:
`{month, label_month, n_dates, n_in_month}`), documented in
api-contract.md with its consensus rules. Proven by regression (nulling
the emission reddens all three view tests). The SPA half is the gated
month-banner prompt handed 2026-08-28; it activates once this deploys.

### 37. The attach dialog's column-mapping retry is dead on the wire (LIVE DEFECT, found 2026-08-28)

Found by the adversarial verify pass on the attach-dialog Lovable prompt.
When the statement attach 400s with the file's headers, the SPA lets the
operator pick which column is which and retries, appending FormData keys
`map_date`, `map_description`, `map_amount`, `map_currency`
(ExpensesReviewGrid.tsx:2128-2132). The backend route accepts
`map_transaction_date`, `map_amount`, `map_vendor`, `map_posting_date`,
`map_transaction_currency`, `map_card` (app.py:2543-2548). Only
`map_amount` aligns; FastAPI silently drops the rest, so the operator's
date, description and currency picks never reach the parser and the retry
resubmits effectively unmapped. Nobody has hit it loudly because Chase
exports carry recognizable headers. Fix is SPA-side (rename the three
appended keys; shipped inside the attach-dialog Lovable prompt handed
2026-08-28, section 4); an optional backend nicety is accepting the old
names as aliases so an un-updated SPA still works.

**Alias half SHIPPED 2026-08-29 (this round):** the statement route now
accepts `map_date` / `map_description` / `map_currency` alongside the
canonical names, canonical winning on conflict, so the deployed SPA's
retry works BEFORE the Lovable prompt is applied and keeps working after.
Proven by regression (unwiring the date fold turns the alias attach test
red: 400 with the file's headers).

**Item 35 companion note (same verify pass):** of the four tender phrases
on the April strip, only `Cartao de Credito` is `generic: true` under the
deployed vocabulary; `tef`, `compra`, `dias` are not in
`GENERIC_TENDER_WORDS` (cards.py:90-119), so `CARTAO TEF`,
`COMPRA CREDITO VISA` and `Cartao Credito 30 Dias` come back
generic:false, and the last one prints the digits "30". The strip prompt
was written to be truthful against this (3-digit floor on grouping,
generic-first partition); the small backend half is adding those words to
the vocabulary and deciding sub-3-digit-run tolerance in
`is_generic_tender`, after which the three phrases move under the
no-card-number section with no SPA change.

### 38. Two functions: monthly company expenses and trips (owner directive 2026-09-06)

**Owner:** "Expense creation should be split and separated into 2 functions:
One for overall monthly company expenses and one for travel expenses." One of
three directives given together (with items 39 and 40); they ship as one
program, rounds at the end of this item.

**Rulings, asked and answered 2026-09-06:**

1. *How the tool knows which is which:* **declared at entry, never
   inferred.** A batch is created as a company month or as a trip, and mail
   routes by ADDRESS (the existing receipts@ stays company; a travel alias on
   the same intake domain routes to travel). No content classification in the
   split. To-alias already beats From-sender in the intake, so the routing
   mechanism exists.
2. *The travel unit:* **a trip — named, date-ranged, with a VARIABLE roster
   of travelers.** Explicitly "not just one traveller per trip, that number
   needs to be variable." Trips span month boundaries freely.
3. *Reconciliation:* **both functions reconcile.** Travel expenses paid on
   company cards participate in statement matching; travel is not a
   receipts-only report.

**Design consequences, stated now so they are not re-derived:**

- Ruling 3 is the deep half: a month's statement charges must be matchable
  against receipts sitting in TRIPS, so the match pool for a statement spans
  batch types, and a receipt must never settle two charges across two
  batches (a global claim, the same shape as `rematch_month`'s drop-refusal
  but across runs). Everything else in the split is surface by comparison.
- The trip document is the existing report pattern (listing + receipt
  evidence per expense); with a variable roster it sections per person,
  which is item 40's field.
- Travel mail with no open trip RESTS in the pool like month mail. A trip
  cannot be auto-created (it has a name and a roster only a human knows);
  whether a receipt dated inside exactly one open trip's range auto-joins it
  is the round's design call — deny-by-default is the house pattern.
- SPA: batch creation gains the declared type; a trips list beside /months;
  Lovable prompts per the api-contract rules.

**Rounds for the 38/39/40/41 program:** R1 = items 40 + 41 (person on the
card + the private-expense suggestion for payment methods that resolve to no
card — one round, same surfaces), R2 = item 39 (auto-materialization),
R3 = the trip entity + declared-type creation + travel alias routing,
R4 = cross-batch reconciliation + the trip report. Each round the house
loop: worktree, RED-proven tests, adversarial review, suite + calibrate,
deploy, Lovable prompt, PROMPT-STATUS ledger.

### 39. Mailed receipts become expenses on their own (owner directive 2026-09-06)

**Owner:** "Receipts injected via Email should be automatically categorized
and turned into expenses without having to start a reconciliation for the
corresponding month."

**This supersedes the 2026-08-24 ruling that pre-creating months intrudes**
(recorded in the loop brief; it retired a "create the two months" step). The
owner now directs the opposite: mail materializes the month itself. The
POOL'S ROUTING HALF STAYS — filing by the month printed ON the receipt (item
29 PR 1) is exactly what makes auto-creation safe.

Design: arrival already runs the full extraction read (cache-warm) and
arrival-time dedupe (item 33). The new step: a pooled receipt whose printed
month is confidently known ENSURES the month batch — create it if absent,
ingest, categorize through the normal pipeline, `rematch_after_change` when
the month holds a statement. Guards that stay or get added:

- An implausible month still rests. Bound the auto-create window: wrong-year
  OCR (item 25: 11 of 36 April readings) is why a 2023 misread must never
  create a 2023 batch. The `batch_period` neighbor logic is the reference.
- `create_expense_batch` refuses an empty batch; the auto-create carries its
  first receipt, so the ordering (create-with-receipt, not create-then-add)
  is part of the design, not an accident.
- Auto-created batches carry their origin (parallel field, e.g.
  `created_by: "intake"`), so /months shows which months materialized on
  their own.
- The ack changes meaning: "filed into July 2026" instead of "waiting for
  July 2026". `status_label` rules (api-contract rule 5) cover the new
  wording.

Live consequence to handle at deploy: the pool held 23 resting mails as of
the 2026-09-06 audit (12 Aug / 5 Jul / 6 Sep), three of them the SAME
Hostinger invoice (pre-dedupe arrivals). On auto-materialization the receipt
pool's add-time content check keeps copies 2+3 from becoming expenses, but
their intake rows will read as processed; dismissing two first (item 33's
open owner yes) is the tidy path and GATES the flag flip.

**Rollout protocol (settled 2026-09-06, binding for the R2 round):**

- Ensure-month lives ONLY in `route_archived`'s no-open-batch branch, gated
  on `receipt_month_source == "receipt"`, the plausibility window, and a new
  env flag `EXPENSE_RECON_AUTO_MATERIALIZE` (default OFF). `claim_pooled`
  stays create-free: deploy or boot must never backfill three months
  unattended. Once a month IS open (created by an arrival), the normal pool
  drain claims that month's resting mail — coherent, and stated here so it
  is not read as a backfill leak.
- The EXISTING pool backfills only on an explicit operator trigger:
  `materialize: true` on `POST /api/inbound/replay-held` runs
  claim-with-ensure-month over confidently-stamped pooled mail.
- The 7 stranded `batch_deleted` archives get a re-pool sweep in the same
  round: lazily month-stamp stampable archives the way `replay_held` stamps
  pre-stamp mail, flip them to `pooled` (dismissed excluded, unstampable
  stay legacy). They then REST like any pooled mail; materializing their
  months stays the operator's explicit backfill call. The legacy per-archive
  `re_ingest` path 409s with zero months open and targets "newest open
  batch" rather than the receipt's month, so without this sweep seven real
  receipts are unreachable.
- Staged flip: dismiss the 2 Hostinger copies → snapshot the pool via API →
  deploy flag-off → verify inert → flip → operator backfill → verify each
  materialized month against the snapshot (labels, `created_by`, counts,
  dedupe held, acks) → Playwright SPA drive → stranded-archive triage.
- Rollback story, already shipped: deleting a month returns its stamped mail
  to the pool; flip the flag off and the tool is back to today's behavior.
- Creating the 0340 card (2026-09-06) changed the extraction-cache salt, so
  the backfill re-pays ~23 vision calls. Accepted; correctness beats cache.

**Subsumed:** the "create-month-from-pool button" candidate from the
2026-09-06 manual-input audit. Auto-materialization does the same job
without a new surface; do not build the button.

**LIVE (2026-09-07).** Flag `EXPENSE_RECON_AUTO_MATERIALIZE=1` set on Fly
with the owner watching. The backfill minted July, August and September 2026
(`created_by: intake`, 0 failures, all 24 pooled mails claimed); the
stranded sweep re-pooled 10 legacy archives, triaged with the owner in the
same session: 5 TEST- drills dismissed, 5 real mails (all
`receipt_month_source == "receipt"`) claimed into August by their
receipt-read dates. Pool 0, held 0. SPA verified rendering "Filed into
{month}" labels and the three intake-minted months.

**Built (R2, PR #687, 2026-09-06; deploy + staged flip pending).** The
protocol above shipped verbatim, plus three guards a 3-lens adversarial
review added: the arrival half fires for KNOWN senders only (an open
mailbox must not let a stranger's dated PDF decide when months exist;
strangers' mail pools, the explicit backfill files it); the stranded
re-pool sweep runs only on `materialize: true` calls and LAST, so a
plain retry click stays inert and re-pooled mail rests one full
round-trip before any call can act on its just-guessed stamps; and
every back-to-pool transition clears previous-life stamps (`job_id`,
`materialized`), because a stale done job blinded the boot sweep's
claiming recovery and a stale flag relabelled a later normal claim as
"Filed into". The operator-vs-intake same-month create race aborts at
commit via a pre-commit re-check (`execute_expense_batch(pre_commit=)`)
and the mail joins the winner. Item 42 (refusals split) shipped ahead as
PR #683. Residuals in item 43.

### 40. Every expense belongs to a person, through the card (owner directive 2026-09-06)

**Owner:** "All injected expenses whether email or manual need to be
attributed to a person." Ruling on the mechanism, near-verbatim: "The person
attribution should really only happen depending on what card was used. Each
card is attributed to a name and therefore every expense can be attributed
to a person. Even the ones injected via email."

So: a cards-registry entry gains `person` beside `entity`, and person
resolution is the LAST LINK of the existing card chain (extraction pick,
item 28 → hint → registry → stamped → needs). No parallel person chain, and
NO sender-based attribution: `submitted_by` stays what it is (ingest
provenance, a claim about who MAILED the file), and the person on the
expense comes from the card even for mailed receipts — the owner said so
explicitly, so do not "improve" this with sender inference later.

Consequences:

- Coverage is bounded by the registry, which makes item 26 three-ways
  load-bearing: a card with no `person` resolves an entity but no person;
  a generic tender resolves neither (per the 2026-08-22 ruling those are
  per-month assignments, so the batch-assignment path takes a person the
  same way it takes an entity — this month only, never learned); the 0340
  card exists as of 2026-09-06 (entity still blank). Data entry decides how
  much of a real month attributes.
- **Person data entry can only happen AFTER this round deploys.**
  `normalize_cards_setting` whitelists its fields, so a `person` typed into
  settings today is silently discarded; the field must round-trip through
  all five card code points (`normalize_cards_setting`, `cards_to_setting`,
  `Card`/`_card_from_setting`, `card_to_dict`, the snapshot/refresh path).
  And because the settings cards map is whole-map replace, person entry
  waits until the round's Lovable prompt is verified in the published SPA
  (JS-chunk field-name grep): a stale SPA save would silently erase every
  person value. Round-0 collects the values; nobody types them early.
  **Gate CLEARED 2026-09-07:** `lovable-r1-person-private-prompt.md` is
  applied and bundle-verified (settings chunk round-trips `person` in the
  cards save payload; see PROMPT-STATUS.md), so person entry is safe. What
  is still missing is the DATA, per item 26: the person per card plus the
  0340 entity and the 3645/plastic-1672 identities, Criss/Dirk only.
  **Person data after the ALL BANKS list, 2026-09-08: still zero written.**
  The list carries person SIGNAL but the owner confirmed only the entity
  half, so no `person` value was written in the calibration round. What the
  round assembled, every row sourced, none inferred from initials alone:
  4921 → Dirk and 5126 → Rafael (the list prints `DN` / `RR`, and Zoho's
  own COA account names for org `696750461` independently read "Volksbank
  Visa 4921 (Dirk)" and "5126 (Rafael)", so two sources agree; Rafael's
  surname is still unknown); 0113 and 8311 → Dirk Neumann, from the Zoho
  account names already stored on those cards. A third signal turned up in
  the live August batch: an Obsidian receipt whose payment hint reads
  `CorpServ & DN ••3645`, which points at 3645 being a Corp Services card
  of Dirk's. That is a merchant's rendering of a statement descriptor, not
  the owner's record, so it is asked rather than written. 6013, 9693, 2838,
  0340 and 1176 have no person source anywhere (the list's sixth Cloud
  Services card was read as 3693 and is actually 9693, already counted here;
  see the correction in item 26). All of it is in the
  draft `context/drafts/2026-09-08-card-gaps-criss-dirk.md`; enter persons
  only against a reply, never against the initials.
- Rows gain `person` + `person_source` as PARALLEL fields (api-contract
  rules, view-contract pinned); unattributed rows get their own review
  surface and count beside MISSING ENTITY, with a rule-5 label.
- Settings > Cards editor gains the person column (Lovable prompt), and the
  card strip's Assign control carries the person half.
- Trips (item 38): the roster is people; a trip receipt whose card person is
  not on the roster is worth a flag — design call in that round.

### 41. Unknown payment methods suggest a private expense (owner directive 2026-09-06)

**Owner:** "When payment methods arise that have not been defined in the
system they must be suggested to the user as private expenses that will
require reimbursement to the person who expensed." Fourth directive of the
2026-09-06 program; rides in the same round as item 40 (same surfaces: card
chain, review states, the strip, Settings).

Today the same situation — a payment hint that resolves to no registered
card, whether unlisted digits (the live 0340 case before item 26's data
entry) or a digit-less tender ("Cartao de Credito") — lands in the
unknown-card strip or MISSING ENTITY and just waits. This directive gives it
a default reading: not-a-company-card SUGGESTS private money.

Design:

- SUGGESTED, never stamped. A new review state (working name
  `suggested_private`, own rule-5 label and count) that the operator
  resolves one of two ways: confirm private (the row becomes a
  reimbursement row) or register/assign the real card through the existing
  flows, which clears the suggestion. Nothing auto-books; deny-by-default
  holds.
- A confirmed private expense carries `reimburse_to`, a person. This is the
  one place person attribution CANNOT ride the card chain (there is no
  company card), so it is a deliberate, bounded exception to item 40's
  card-only rule, created by this directive: operator-confirmed, pre-filled
  from `submitted_by` on mailed receipts (shown as the claim it is), blank
  on manual uploads. Do not generalize this into sender-based attribution
  anywhere else.
- Private rows report as their own section — reimbursements owed, grouped
  per person with sums — in the month report and the export, instead of
  carrying an entity placeholder that reads like an unfinished company row.
- The 2026-08-22 ruling (cash/personal tenders handled at end of month,
  per-batch, never learned) keeps its timing; this item gives those rows a
  name, a person, and a document section instead of a bare assignment.
- Interaction with item 35's strip: the digit-less sub-strip it proposed is
  where the suggestion surfaces naturally ("no card number readable;
  suggested as a private expense").

### 42. Refusals counter drowned by relay probes (2026-09-06 audit)

`n_refused` counts every ledger row in the 7-day window, and the 2026-09-06
audit measured all 55 of them as `*@flyio.net` spam relay probes (`stage:
"rcpt"`, "relay not permitted"). The counter was built to answer "is
anything bouncing this week?"; with a permanent probe floor a REAL refused
submission is invisible in the number.

The ledger already records `stage: "rcpt" | "data"`, so the fix is a
view-only split in `refusal_view`/`count_refusals`: parallel fields
(`n_refused_ours` for data-stage refusals of mail addressed to the intake
domain, `n_probes` for rcpt-stage relay probes, a per-row `probe` flag with
a rule-5 label), with `n_refused` itself unchanged — the api-contract warns
against silently redefining an existing field's meaning. SPA degrades
gracefully; the Lovable line is optional and small.

Assigned: standalone micro-PR at the head of the R2 chat, deployed with or
before the R2 flip so the counter is meaningful exactly when the operator
watches the first auto-materialization.

**Shipped (PR #683, merged 2026-09-06):** view-only split keyed on the
ledger's existing `stage` field — `n_refused_ours` (data-stage), `n_probes`
(rcpt relay probes), per-row `probe` + `kind_label`; `n_refused` unchanged.
A rcpt-stage "too many recipients" row is deliberately neither bucket.
Deploys with the R2 flip.

### 43. Materialize residuals (adversarial review 2026-09-06, watch-only)

Accepted residuals from item 39's three-lens review; none load-bearing for
the flip, each evidence-gated before any build:

- A process death mid-create AFTER the run row commits converges on replay
  (content dedupe absorbs the re-ingest) but stamps `documents: []` and no
  `materialized` flag, and fires a false held alert — archive-to-row
  lineage is lost. A boot reconciliation matching `created_by: "intake"`
  batches against stuck `routing` archives would close it; build only if a
  real death produces one.
- `_is_replayable` reads a >600s `routing`/`claiming` as dead-owner, and a
  cold-cache create legitimately runs longer, so a concurrent replay can
  take a LIVE owner's archive. The CAS-guarded final stamps make this lose
  lineage, never rows, and never reverse a dismissal.
- A pooled ack still in flight when the month materializes seconds later
  can double-ack with contradictory verbs (`ack_at` is check-then-act).
- The operator half of the same-month create race (their commit landing
  after the intake's) still yields two same-label batches; newest wins the
  pool, and deleting the loser re-pools its mail. Self-healing; runbook
  line: two same-label months means an upload raced an arrival.

### 44. Receipt entry is decoupled from month creation (owner directive 2026-09-08)

**Owner:** "Criss needs a page inside the reconciliation tool in which she can
just drop any new receipts into manually. Mind you, the expense creation
should only happen this way ... we dont want receipt injection and expense
creation to be limited to the start of a month's reconciliation." Asked
directly whether receipt injection should come out of "create a new month":
**yes, and it only works as a pair with legal empty months.**

**Why removal, not merely allowing both.** The create-month upload slot was
the last surface filing receipts by OPERATOR CONTEXT (whatever month was
being created) rather than by what the receipt says. That is the exact class
that put Dirk's August receipts in the April batch and drove item 29's
rebuild of mail routing. Leaving it would leave two filing brains, one of
which is the one already replaced.

**The pairing, and why it is not optional.** `create_expense_batch` refused an
empty batch, which is why the whole intake stream once waited on a manual
first-receipt upload. Stripping receipts out of creation without lifting that
refusal would leave Criss unable to open a month at all — and statement-first
is her real workflow (January: 78 of 80 charges had no receipt). So a company
month is now a legal empty container that a statement lands in, and the
refusal survives exactly where it is load-bearing: `allow_empty` is opt-in
per caller, and it never sanctions an upload whose every file was REJECTED
(the mail materializer's floor — a month is never created from files that
could not be read).

**Shipped (Shipped row 31).** `POST /api/receipts` is the one manual
entrance: each dropped FILE routes on its own dates through the same
`resolve_receipt_month` brain mail uses, materializing absent months
(`created_by: "drop"`). Deliberate asymmetries with mail, each with a reason:
a MAIL routes as one unit by its earliest date because its files arrived
together, a DROP is a pile of unrelated receipts; mail materialization is
flag-gated because a stranger's mail could mint months, while an operator
dropping a file is the opposite of that, so the drop is unconditional; and a
file with no readable date RESTS as `needs_month` rather than falling to the
arrival month, because a silent guess is what the routing rebuild removed.
The release valve is an explicit `month` override, believed like a typed
date. Zips are refused (one file per receipt) — a zip's members would each
need their own verdict, and the page is a drag-and-drop of files.

**Scope not taken:** mail intake and the travel alias stay, since they route
through the identical brain; "only this way" was read as the only MANUAL
entrance, confirmed against the directive's own framing ("even the ones
injected via email" is item 40's language for mail as a first-class path).

SPA half: `docs/lovable-receipts-drop-prompt.md` (owner applies; §2 removes
the create-month upload area, which the server already 400s).

### 45. Drop cap raised + honest overflow; nav redesign (owner directives 2026-09-08)

**Owner, same day as item 44 shipped:** the drop page's 80-file bound "must
be increased"; the Receipts page needs a button back to the main menu; and
on every page except the main menu the top bar should disappear completely,
replaced by an always-visible button back to the menu.

**Backend shipped:** `FOLDER_MAX_FILES` 80 → 500 (`service.py` — the cap
bounds vision cost and zip blast radius PER INGEST CALL; sized now for a
multi-month backfill pile). Found and fixed beside it: when one month's
drop group exceeded the cap, the create/add call truncated silently while
the drop ledger still read `filed` for the skipped files. The router now
marks the overflow `rejected` / `upload-cap` (with `limit`) BEFORE the
ingest call; recovery is re-dropping the pile (content dedupe skips what
landed). Both proven by mutation: cap regressed to 80 reddens the 81-file
test, unwiring the pre-slice reddens the overflow-ledger test.

**SPA half (all three asks):** folded into
`docs/lovable-receipts-drop-prompt.md` (still one paste) — §1 gains the
`upload-cap` rejected copy and client-side chunking at 300 files per POST
(Starlette parses ~1000 form parts max), §5 is the nav redesign: top bar
only on `/months` (the main menu), a sticky "← Menu" button on every other
page, language toggle + logout consequently menu-only.

### 46. Month creation leaves the UI (owner ruling 2026-09-08)

**Owner, rebutting the "three surviving jobs" analysis:** receipts flow in
continuously through the drop page and mail and the tool organizes them
into months itself, so the "Start a new month" ceremony is useless. Ruled
after an explicit decision round: **no statement-first month creation**
("we will not be creating new months with statement first"); "Add a
statement" stays where it is, inside each month's page; the create button
and `/expenses/new` company-month form die entirely.

**What replaces the button's one real residual job:** the pooled-mail
release. Mail from unknown senders and mail with unreadable dates
deliberately rest in the pool (`pool_month_state: "no_batch"`); those
intake rows get a one-click "Open {month}" that calls the EXISTING create
route with a label and no files — the post-create pool claim then drains
the waiting mail in automatically. No backend change anywhere in this
item; the create route survives as plumbing (mail materializer, drop,
Open-month, trips).

**Consequence accepted in the decision:** a month that reaches statement
time with zero receipts has no container until one receipt of that month
is dropped (the drop page's month override makes that a 10-second act).
Named to the owner before the greenlight; their call stands.

**SPA half:** `docs/lovable-receipts-drop-prompt.md`, reworked 2026-09-08
evening into a DELTA prompt after the bundle audit showed the owner had
already published v1 mid-day (the drop page is LIVE; the operator's
"only accepts 80 files" report was the tell). Delta = cap copy +
chunking, this item's create-UI removal, the nav redesign, the
Open-month release (travel rows excluded).

### 47. Cost centers: attribute expenses to projects and purposes (owner directive 2026-09-08)

**Owner (Dirk's ask):** a cost-center view deriving which costs belong to
which projects/purposes — examples given: Nicolas's Brazil expenses, the
Lidar project Nicolas works on, Matthias's work on this tool, marketing.

**BUILD ORDERED 2026-09-10** (owner: add cost centers, with the configuration and setup discussed, into the UI and the backend). Nothing exists yet: `grep -rn cost_center src/` returns zero hits, so this is backend AND Lovable, in that order. The design below stands unchanged and is the spec; build to it rather than re-deciding it. Sequence: (1) `settings["cost_centers"]` whole-map replace + the empty-registry contract (resolve nothing, flag nothing) with its mutation test FIRST, (2) the resolution chain override > trip > learned merchant > card `default_cost_center` > unresolved, with person and category deliberately not resolvers, (3) the parallel API fields plus `cost_center_source_label`, (4) the month report grouped by cost center (reuses the `sections` partition item 38 built), (5) `GET /api/cost-centers/totals` for the cross-month roll-up, (6) the Settings editor and the row picker in Lovable. The stated limit rides both surfaces: this tool sees card and receipt spend only, never contractor invoices or salaries, so a cost-center figure is not a total project cost.

**DESIGN ANSWERED 2026-09-08** in an owner decision round (four questions
put with recommendations; three taken, D1 answered against the
recommendation). Nothing was built — the build is a separate order.

The shape is a cost-center DIMENSION on the expense row, sibling to
category, legal entity and person, resolved through the same
override > learned > registry chain the rest of the tool already uses and
never guessed silently. Dirk's four examples are deliberately
heterogeneous — Lidar is a project, marketing is a function, Brazil is a
trip, tool work is a person's — so the registry is ONE FLAT LIST carrying a
display-only `kind`; no hierarchy in v1.

**D1 — the list is owner-authored, full stop.** Owner answer: "Dirk creates
and defines the cost centers manually." `settings["cost_centers"]`, whole-map
replace, edited in Settings exactly like `cards` / `merchants` / `entities`:

```
settings["cost_centers"] = {
    "<name>": {"kind": "project"|"function"|"trip"|"", "note": "", "active": bool},
    ...
}
```

The tool never invents a cost center and never learns a new NAME; the
learning in D2 only ever re-uses a name Dirk has already defined. `kind`
groups the roll-up and never participates in resolution.

The load-bearing consequence, and the thing to build FIRST: **an empty
registry must resolve nothing AND flag nothing.** This is the merchant
registry's own contract ("an empty registry resolves nothing, so a tenant
with no `merchants` key behaves exactly as before"), and without it the day
the field ships every row in every month reads `needs_cost_center` — a
review state at 100% is noise, not signal. The review state starts firing
only once at least one active cost center exists. Item 26 (card identities,
open since 2026-08-23) is the standing evidence that an owner-side data-entry
prerequisite can sit for weeks; the field has to be inert, not loud, while
it does.

The whole-map-replace hazard is the one that already bit `person` on cards:
a Settings screen that does not read AND write the map erases it on save.
The Lovable half must round-trip the whole map, and data entry waits until
the published bundle proves it does.

**D2 — resolution precedence.** Highest first, first hit wins:

1. **explicit per-row override** — rides `edited_fields` like every other
   override; always beats everything below.
2. **trip** — a `batch_type: "trip"` batch whose trip carries a
   `cost_center` fills every row in it. Strongest automatic signal because a
   human DECLARED it at creation (item 38), not because anything inferred it.
3. **learned merchant → cost center** — per legal entity, `decision_count`
   weighted; the structural twin of the existing `merchant_entity` table.
4. **card `default_cost_center`** — for a card that belongs to one project.
   One line in `normalize_cards_setting`'s string-field loop.
5. otherwise **unresolved**.

**Person is NOT a resolver, by decision.** It ranks the picker (Nicolas's
usual cost centers first) and nothing more. Person is precisely the signal
that cannot separate two of Dirk's own examples: Nicolas is on both sides of
"Brazil" and "Lidar", so a person-first chain would fill one of them in
wrong and confidently — the failure mode item 25 and rule 5's "Arriving"
incident both punish. **Category is not a resolver either:** letting the two
dimensions co-vary destroys the point of cutting the money a second way.

Learned outranking the static card/registry default is deliberate
consistency with the 2026-08-07 merchant reversal (owner call: a per-entity
learned row outranks the registry default; registry-preempts-learned is
dead).

Unresolved reads `check` / `reason_code: "needs_cost_center"`, firing
**LAST** — after `needs_person` — because it is registry work of the same
class and must never hide a more actionable per-row exception. Silent
entirely while the registry is empty (above).

**D3 — v1 refuses splits.** One expense, one cost center. Named
consequence, accepted: a genuinely shared cost (a hotel bill half Lidar,
half marketing) lands wholly on one side and that roll-up is slightly wrong.
No real shared-cost example was on the table when this was decided; if one
appears, the v2 shape is **per line item**, reusing the `books_as` fan-out
(the report already handles the doubled listing rows, and evidence stays per
DOCUMENT captioned "Expenses 3, 4"). Operator-typed percentage splits are
NOT the path: they would be new machinery through the export, the report
numbering and the receipt captions.

**D4 — surface, in two steps, in this order.**

*Step 1, the month report groups its listing by cost center.* Nearly free:
`build_expense_report_pdf` already takes `sections`, contiguous slices of
the listing with their own caption, per-currency sums and continuous
numbering, built for the per-person trip report (item 38). Partitioning on
cost center instead of person is the same call with a different key.
Unassigned rows get their own final section, named as unassigned, never
hidden.

*Step 2, a cross-month view.* This is the only genuinely new surface: all 57
routes were enumerated and nothing aggregates across batches (months list,
trips list, per-batch, per-run). "What has Lidar cost since January" is the
question a project actually raises, and a month report cannot answer it.
`GET /api/cost-centers/totals?from=&to=`.

NOT building: a dedicated cost-center page with its own tiles. The
cross-month view is most of what would land on it.

**Stated limit, on both surfaces.** This tool only sees money that flows
through a Brisken card or a receipt. Contractor invoices, salaries and
anything paid another way never enter it, so "what did Lidar cost" answered
from here is CARD-AND-RECEIPT SPEND, not total project cost. Both surfaces
label themselves that way. A number that reads as a project total and is not
one is worse than no number (B4), and it is the same class of error as the
`pooled` rows that confidently read "Arriving".

**API-contract implications — parallel fields only (rule 1).** Nothing
existing changes type or meaning, so a stale SPA renders exactly what it
renders now.

Expense-batch payload:

| Path | Element | Meaning |
|---|---|---|
| `expenses[].cost_center` | string | the resolved name; `""` unresolved |
| `expenses[].cost_center_source` | string | `override` \| `trip` \| `learned` \| `card` \| `none` |
| `expenses[].cost_center_source_label` | string | the parallel human-readable label |
| `summary.n_needs_cost_center` | int | beside `n_needs_person` |
| `cost_center_options[]` | string | beside `account_options[]` / `entity_options[]` |

`cost_center_source_label` is not optional politeness: rule 5 says an
enum-ish field the SPA maps by hand ships WITH a parallel label, so an
un-updated consumer degrades to correct text instead of somebody else's copy
(the `pooled` / `routing` / `claiming` → "Arriving" hole). New `reason_code`
value `"needs_cost_center"`, prose in `reason` per the same rule.

Settings and cards:

- `GET /api/settings` emits `cost_centers`; `PUT /api/settings` accepts it,
  normalized + validated at the edge like `merchants` / `cards` (blank name
  dropped, unknown `kind` rejected, whole-map replace).
- card entry gains `default_cost_center`, emitted as
  `cards[].default_cost_center` on `GET /api/cards` (`""` unset). It reaches
  an EXISTING batch only through `POST .../refresh-master-data`, whose
  `changes` gains a `row_cost_centers` count — same contract as item 40's
  `row_persons`.
- trip object gains `cost_center`; `POST` / `PUT /api/trips` accept it.

New route: `GET /api/cost-centers/totals?from=&to=` — per cost center, per
currency, with a row count and an explicit unassigned bucket.

Re-pin `tests/test_view_contract.py` and `docs/api-contract.md` in the same
round (rule 4), and ship the SPA half in the same round (rule 2).

**Lovable half: PROMOTED 2026-09-15 to `automations/expense-reconciliation/docs/lovable-cost-centers-prompt.md`** (registered in PROMPT-STATUS as not applied; §1 + §2 ship first because both maps are whole-map replace). The backend emits every field the prompt names (steps 1-5). The draft below is the design record the prompt was written from.

1. *Settings > Cost centers.* A list editor over the whole `cost_centers`
   map: name, `kind` (project / function / trip / blank), optional note,
   active toggle. Saves the WHOLE map back on every save, including entries
   it did not touch — a partial write erases the rest (the trap that hit
   `person` on cards). An empty list is a normal state with an explanatory
   empty view, not an error.
2. *Settings > Cards.* One added field per card, `default_cost_center`, a
   picker over the defined list plus blank. Same whole-map-replace warning:
   the cards save payload must keep carrying `entity` and `person`.
3. *The expense row.* A cost-center picker offering only defined names,
   ordered with the row's person's most-used first, blank allowed. Show
   `cost_center_source_label` beside the value so a filled-in row says WHY
   it is filled in. Setting it by hand adds `cost_center` to `edited_fields`
   like any other override.
4. *Review.* Render `reason_code: "needs_cost_center"` from `reason`, and
   surface `n_needs_cost_center` beside `n_needs_person`. Both stay
   invisible while the count is zero, which is the whole first phase.
5. *Trip page.* One cost-center field on the trip, saved through
   `PUT /api/trips/{id}`; the roster save must keep carrying `travelers`.
6. *Cross-month view (step 2).* One screen over
   `GET /api/cost-centers/totals`: a date range, one row per cost center
   with per-currency sums and a row count, an unassigned row that is never
   hidden, and a standing caption that these are card and receipt expenses
   only, not total project cost.

Render defensively throughout (rule 3): a missing or unexpected
`cost_center*` field degrades to blank, never to an error boundary.

**Build order when the build is ordered:** registry + resolution chain +
review state (inert while empty) → report sections → learning table →
cross-month route. The cross-month view last, because it is the only piece
that needs data the earlier pieces produce.

### 48. Report structures against US accounting law, tool-scope only (owner directive 2026-09-08)

**Owner:** the tool's output is lawfully regulated; there are specific
report structures and criteria that must be fulfilled — reference
American accounting law, incorporating ONLY what falls within the
expense-reconciliation tool's range.

**Scope guard (the load-bearing constraint):** the tool produces expense
DOCUMENTATION — monthly expense report PDF with receipt evidence,
reconciliation report (statement vs receipts + exceptions), CSV/XLSX
sidecars. It is not a general ledger and files nothing; financial
statements, tax filings and bookkeeping are out of range, so GAAP
statement-presentation rules mostly do NOT bind here. The plausible
binding body is IRS substantiation for business expenses (accountable-
plan rules, the T&E substantiation elements — amount / date / place /
business purpose, receipt thresholds, retention) — but every criterion
must be verified against PRIMARY sources in a research gate before any
report change is proposed (B4: no invented legal claims, ever; each
criterion cites its source or is dropped). Deliverable of round 1: a
verified criteria list mapped onto the tool's actual outputs + a gap
analysis, reviewed by the owner BEFORE any build. Session prompt handed
2026-09-08 (checkpoint of the same day); full brief there.

**Round 1 DELIVERED 2026-09-08, pending owner review, nothing built:**
`automations/expense-reconciliation/docs/us-substantiation-criteria.md`.
27 criteria in four sets, each citing a primary source fetched that
session (26 U.S.C. 162/274; 26 C.F.R. 1.6001-1, 1.62-2, 1.274-5,
1.274-5T; Rev. Proc. 97-22; Pub. 583/463). The scope guard held and
narrowed: GAAP presentation and filing are out as predicted, and TWO
criteria a pre-2018 checklist would have added are out on the statute's
own text (entertainment left the 274(d) list in 2017, so no attendee /
business-relationship element binds; the 274(n) 50% meals limit is a
deduction computation, not a document element). The body that binds the
tool most directly turned out to be **Rev. Proc. 97-22**, the electronic
storage system rules, which nobody had named: the tool IS the storage
system, and compliance is what makes its records count as 6001 records.

Eleven gaps ranked. The top three: **business purpose exists nowhere in
the tool** (a repo-wide search returns zero hits; it is a required 274(d)
element and its absence can turn a reimbursement into wages under
1.62-2(c)(5)); **no retention control and `delete_run` drops a whole
month** (1.6001-1(e), 97-22 4.01(8)); **`expense_location` is captured on
the Zoho ingest path and dies at the API layer**, reaching no PDF, CSV or
XLSX, so a required element is being thrown away. Two source caveats
recorded in the file: eCFR blocked automated access all session so the
regulation text is Cornell LII rather than official, and Pub. 463's
Table 5-1 never came back cleanly so it was used as authority for
nothing (the element lists come from 1.274-5T(b) verbatim instead).

**Owner answers, same day, both recorded in the file:** (1) **US filing
applies** to at least one entity, so the criteria bind and the gaps are
live; the DE/BR fallback is off the table. Still open is WHICH entities
file, which scopes the criteria rather than deciding whether they apply,
and until it is answered every row is treated as in scope. (2) Business
purpose (G1) is captured **per merchant, learned once**: a default in the
merchant registry, overridable per expense, so recurring subscriptions
carry a standing purpose after one setting and only new merchants ask.
Per-card, per-account and per-expense-only were rejected (a card buys
across purposes; an account says what kind of cost, not why; per-expense
puts a manual field on every row forever).

**G7 CLOSED same day, and it corrected round 1.**
`automations/expense-reconciliation/docs/electronic-storage-system-description.md`
is the examiner-facing description Rev. Proc. 97-22 4.01(5) requires, drafted
against the deployed code and then refuted line by line by eight independent
reviewers (97 challenges, 53 confirmed, 7 rejected as misreadings). Draft
pending owner + CPA review; two blanks to fill before hand-over (which
entities file US, the deployed access-code configuration).

Writing it is what caught a **material error in round 1**: D1/D2/D5 were
graded Satisfied on the content-addressed receipt store, and that store is
CLI-only. `ReceiptStore` is instantiated only in `cli.py` behind an optional
`hosting:` block; nothing under `web/` imports it. The deployed paths compute
a truncated SHA-1 for de-dup and discard it, so **no digest survives and
nothing can detect that a stored receipt changed**. D2 and D3 are now
Missing, five more rows downgraded, D12/D13 added, and G2b leads the gap list
beside G1. Cause worth keeping: round 1 read the docstrings, which describe
the store accurately, and never checked whether the deployed entry point
imports it. The estimate that G7 was "a writing task, not a build, the
cheapest item on the list" was wrong in the useful direction: describing a
system completely is what exposes what it actually does.

**Round 2 shape, not yet scheduled:** the five rendering-only changes
(Place column, receipt-required flags at the lodging / $75 thresholds, a
real preparation block replacing the static `prepared_note`, days-away on
trip reports, the 60-day reimbursement clock) need no new data and share
one surface, so they ship as ONE round. The business-purpose capture is a
separate round with three design questions still to settle (default before
anyone sets one - blank and flagged, not a guess; listing row vs CSV only,
given the listing is already nine columns; and whether a purpose carries
across entities, the question the card registry answered with per-entity
chains). G7, the examiner-facing system description Rev. Proc. 97-22
4.01(5) requires, is one markdown file and blocked by nothing.

### 49. Correctness defects found by the item-48 code audit (2026-09-08)

Not a compliance item. The eight-reviewer audit behind item 48's system
description read the deployed paths looking for overstatements and turned up
defects that stand on their own, none of which needs a US filing position to
matter. Ranked by the loop brief's own rule (wrong money first). Every one is
recorded with its evidence in
`docs/electronic-storage-system-description.md` section 12; this row exists so
they are not lost inside a compliance document nobody opens for bug reports.

**Wrong money.** The report totals are summed in binary floating point, and a
row whose amount cannot be parsed is dropped from the PDF total **with nothing
on the report saying so**. Amounts are stored as strings precisely so
precision is not lost, and then the reports throw that away. A month can print
a total that is quietly short by one receipt.

**Silent data loss.** Two paths rewrite the whole period record without taking
the batch lock (the manual per-charge attach and the bulk folder ingest), so a
concurrent write on either can be lost. Separately, replacing a file on a
queued upload deletes the file it replaces, and re-attaching a receipt to the
same charge under the same filename overwrites the stored bytes, both with no
version and no record.

**A period that cannot be reported at all.** The renderability check opens a
PDF's index only, so a password-protected or structurally damaged receipt
passes it and then fails during assembly: the request 500s and NO report is
produced for the whole month, with no caption, no partial output and no
message naming the file. One bad receipt makes a month unreproducible until
someone finds and removes it by hand. A large month can hit the same wall for
a different reason: the whole report is assembled in memory on a 512 MB
machine.

**The listing overstates receipt coverage.** The Receipt column reads
"attached" once the file was read off disk, which is decided before
renderability is known, so the count of expenses with a usable receipt page
can be too high. The caption pages are the truth.

**Two reports can disagree.** An expense the reviewer deleted leaves the
expense report immediately but stays in the reconciliation report until the
next re-match, because the two are built from different sources.

**Smaller, same family.** A borrowed trip receipt is listed in the
reconciliation report with no pages behind it; a lost stored file prints the
same caption as an expense that never had one; a byte-identical mail duplicate
arriving inside the same second overwrites the earlier archive's recorded
arrival time; image receipts lose EXIF rotation and transparency in the
report.

None of this is scheduled. The float-total and the lock-bypass are the two
worth doing regardless of what happens with item 48.

### 50. The attach dialog dies with "Failed to fetch", and the app is allowed to stop (hosting half CLOSED 2026-09-11; PROBE BUILT 2026-09-15)

**What Criss saw.** She mailed Matthias a screenshot at 10:00:43Z, subject
"Error", no text. The image is the **Attach bank statement** dialog with
`August2026.xlsx` chosen, card `card-2838 · 2838`, and a red **"Failed to
fetch"** where a validation message would normally render.

**What it is not.** Ruled out by probe the same day:

- The endpoint is healthy: two statements attached to a throwaway month in
  0.1s each, one per card.
- CORS is clean on every path the dialog can provoke (200, 401, 404, and the
  column-map 400), tested from the SPA's own origin. This mattered: a
  response missing `Access-Control-Allow-Origin` surfaces as exactly this
  message.
- Not the failed deploys. v111/v112 failed at 10:42Z, **42 minutes after** her
  error; v113 succeeded 10:44Z.

**What it probably is, and the bigger bug beside it.** "Failed to fetch" is a
browser-level rejection, so the request never got a response. The serving
machine was replaced at 10:44 by v113 and its logs went with it, so the cause
cannot be proven from here. But `fly.toml` says:

```
auto_stop_machines = true
min_machines_running = 0     # one shared-cpu-1x 512MB machine, no redundancy
```

A stopped machine cold-starting under a multipart upload is where the
connection drops. **And this app is the MX target for expenses.brisken.com.**
A mail host allowed to stop is a mail host that can delay or refuse inbound
receipts, which is worse than the upload it was noticed through, and would be
invisible: a refused delivery leaves no row in our own inbound log.

**Fix:** `min_machines_running = 1`, and more headroom than 512MB (the sync
statement parse and the vision path share it). Both are production config on
the client's app, so they need an owner order and a deploy. Add a probe that
records whether the machine was stopped when a request failed, or the next
occurrence is just as unprovable.

**HOSTING HALF CLOSED 2026-09-11.** The `fly.toml` quoted above is not what
the live machine was actually running, which is why this was worth reading
the record rather than the file: `flyctl machine status --display-config`
showed `min_machines_running: 1` ALREADY set on both services (8080 web and
2525 MX) with `autostop_machines` unset, so the app was not in fact allowed
to stop. Only the memory half was still open. Raised to 1024MB on owner
order (`flyctl scale memory 1024`); verified after: 1024MB, `min_machines_running: 1`
on both ports, `/healthz` 200. The cold-start theory for Criss's "Failed to
fetch" therefore loses its mechanism -- a machine pinned always-on does not
cold-start -- so the dialog error remains UNEXPLAINED and the probe that
records machine state at failure time is still the thing that would make a
recurrence provable. That probe is the open half of this item.

**PROBE BUILT 2026-09-15** (backend; the SPA half is written and waiting).
The design follows from the one fact that makes this item hard: a fetch that
rejects never reached the app, so NO server-side log can ever contain it and
no amount of logging would have helped. The only instrument that can see it
is the client, so the client reports and the server stamps.

- `web/machine.py`: one home for this process's identity and age, read by
  `/healthz` and by every report, so the two cannot disagree about which
  machine answered. Uptime is monotonic, so an NTP correction cannot age a
  process.
- `GET /healthz` keeps `status` untouched and gains a parallel `server`
  block (machine, region, app, started_at, uptime_s), empty off Fly rather
  than invented.
- `POST /api/client-errors` records one client-side failure; `GET` reads
  them back newest-first. Authenticated like every other API route: the
  failures worth catching happen inside a live session, so the gate costs
  no coverage and keeps an unauthenticated write off a public host.
- **The decisive field is `process_predates_failure`.** If the client says
  the failure was N seconds ago and this process has been up for less than
  N, the process did not exist when the request was made and the machine
  was replaced underneath it. That is the question this item asks, answered
  from the row alone rather than from logs that die with the machine. It is
  driven by the client's own `seconds_ago`, never by comparing two clocks:
  a browser clock skewed by minutes would fabricate or hide a restart.
  Unknown stays `null` and never collapses to `false`, because a fabricated
  restart would send the next investigation back to the hosting theory that
  already cost this item a cycle.
- The probe never becomes a second failure: any body is recorded rather
  than rejected, the reply is always 200, and a retry loop is dropped
  (`recorded: false`, 20/caller/minute) so it cannot push the interesting
  rows out of the bounded 500-row table.

**The stated limit, which the payload carries and every reader must keep.**
A row exists only when the browser could reach the app AFTER the failure.
An empty log is not proof that nothing failed. Fly's machine event log is
the corroborating source and outlives the machine, so a report timestamp is
enough to look the event up later.

12 tests in `tests/test_client_error_probe.py`, all through the routes;
six wiring points regress-checked green to red to green. Contract section
in `docs/api-contract.md`. **The item stays OPEN until the SPA half ships**:
`docs/lovable-failure-probe-prompt.md` is written and registered in
PROMPT-STATUS as not applied, and until it is pasted the browser reports
nothing and the backend records nothing.

### 51. A statement that parses to zero rows reports success (SHIPPED 2026-09-15 - see Shipped row 44)

While reproducing item 50 the attach returned `200 {"ok": true}` and the run
recorded `statements[{... "n_rows": 0, "n_new": 0}]`. The file was a valid
xlsx whose columns the parser could not read as charges, and nothing said so:
no error, no advisory, no count in the response the SPA reads.

The column-map 400 catches a MISSING required column. It does not catch a
file that maps cleanly and yields nothing, which is what a wrong sheet, a
header row in the wrong place, or a date format the parser rejects all look
like. Criss would see a green attach and an unchanged month.

**Fix:** refuse, or at minimum carry a loud advisory, when an attach adds zero
charges. `n_rows == 0` on a freshly uploaded statement is never a legitimate
outcome. Pin it with a test that mutates the guard and goes red.

**SHIPPED 2026-09-15: refused, not advised.** Reproducing it through the real
route found the item understated by one step. The month does not merely stay
unchanged: `rematch_month` stamps `has_statement: True` on commit, so a month
that took an empty file GRADUATED to the reconciliation workbench holding zero
charges, which on screen is what a month whose statement reconciled looks like.
That settled refuse-vs-advise. The upload is now refused before the fold
(`execute_statement_attach`), so no charge, no `statements[]` entry, no
`statement_anchors` entry and no graduation; the reason rides the job's
existing `error` status, the same channel the re-read already refuses on.

Keyed on `n_rows`, never on `n_new`: zero NEW charges is the same file arriving
twice, which the fold exists to absorb, and refusing that would break the
living month. The message names the file and the worksheet, because the wrong
worksheet is the likeliest cause.

**The re-read half, found while fixing this one.** The same shape reaches
`reread_statements`, where it is worse: the re-read REPLACES the charge set, so
a stored file that recorded rows and now reads none takes its charges out of a
live month silently. That is the identical failure mode the function's own
deny-by-default contract already covers for a missing file and an unresolvable
column map, so it was closed in the same round. Exempt when the entry was
already recorded with `n_rows: 0`, so the guard cannot wedge a month that took
an empty file before it existed; a live probe of all 6 months confirmed none
holds such an entry today, so the exemption is precaution, not repair.

### 52. "Recibo nao estar abrindo" (Criss, 2026-09-08; DIAGNOSED 2026-09-15, SPA half open)

Reviewer note left on `074a7b8905d7`: the receipt will not open.

Not the API: `GET /api/runs/{id}/receipts/{doc}/image` returns 200 for the
rows tested. (A first probe 404'd on `.../receipts/{doc}` without `/image`
and that was the probe's own wrong URL, not a defect. Named here because it
is the third instrument-validity slip in one session.)

**Lead worth checking first:** `0000__rendered-body.pdf` reports
`receipt_image_available: true` and `has_receipt_image: false` at the same
time, while the file itself serves 200. If the SPA gates its viewer on the
second flag, that row refuses to open exactly as she describes. Needs a
browser drive on the published SPA to confirm, then either the flag or the
viewer's condition is wrong.

**The lead was refuted by the drive, and the drive found the cause
(2026-09-15).** The flag observation was accurate and the inference from it
was not. The SPA gates on NEITHER flag: a fetch of the published index plus
every chunk it loads returns zero hits for `receipt_image_available` and
zero for `has_receipt_image`. And the symptom is not one row, it is all of
them.

**What Criss is seeing.** On **Review expenses** (`/expenses/{batchId}`),
every row's **View receipt** button is enabled, carries a React click
handler, and does nothing. Driven on the live app with `window.fetch`,
`window.open`, `URL.createObjectURL` and anchor clicks all instrumented: a
click produced no request, no dialog, no iframe, no tab and no error. 31
rows on August, 32 on September, so it is not the read-only banner a
statement month wears either. The reconciliation workbench is worse: its
UNMATCHED RECEIPTS table's Document column is plain text with no handler at
all, so there is no way into a receipt from that screen in the first place.
The instrument was positively controlled each time (an unrelated
`/api/settings` call logged, the clicks logged nothing), because a confident
negative from an unvalidated probe is the third instrument-validity slip
this item has already produced.

The API is not involved: all 31 August and 51 July receipts serve 200 with
a correct content type, and `expenses[].receipt_image_available` is true for
every one. SPA half: `docs/lovable-view-receipt-prompt.md`, registered in
PROMPT-STATUS as not applied. Verify it by browser drive, not bundle grep:
the defect IS a click with no visible effect, so a silent console is not a
pass.

**Found underneath, and fixed (backend, Shipped row 45).** The same name
answered differently on the two payloads. `build_expense_view` resolved
`receipt_image_available` against disk and was right; `_receipt_view`, which
builds the RUN payload, resolved it from the SHAPE of the document id
(`manual:`, `folder:`, or a vision-mapped page). Every receipt that arrives
by mail or through the drop is `NNNN__name.pdf` and is none of those, so the
run payload reported `false` for all 17 unmatched receipts of the live
August month while the endpoint served each of them 200. Nothing renders
that field today, so it was latent rather than active; but it is the exact
answer a viewer would ask for, and the lead above is what a reader gets when
a field lies. One resolver now, `service.receipt_image_file`, gated the way
the endpoint gates itself.

### 53. Multiple statements per month works in the backend and may not in the UI (2026-09-10)

Owner raised it as missing. It is not: `POST /api/expense-batches/{id}/
statement` has appended by identity since PR 2b-2b-2 (#636, merged
2026-08-25, live on v113), and a drill attached two statements for two cards
to one month, both recorded in `statements[]`.

What was never applied is the SPA half. `docs/lovable-coverage-prompt.md` is
still in the not-applied column, so a month with two workbooks still offers
one download button, and Criss's dialog is titled "Attach bank statement",
singular, with no visible way to add a second. The capability exists and is
unreachable, which is worse than absent because nobody goes looking for it.

**Fix:** apply the coverage prompt, and add a second-statement affordance to
the month page. Verify by bundle audit on the field names (`statements`,
`coverage`) plus a browser drive, not by reading the prompt.

### 54. OCR date misreads silently prevent a match (2026-09-10, July sweep; CLOSED 2026-09-15, neither instance is a misread, not built)

Two receipts sit in the July month unmatched purely because their extracted
date is wrong:

- **Crossmedia EUR 900.** File `2026-07-16__..._Crossmedia_360172592.pdf`,
  charge `2026-07-16 900.00 EUR Crossmedia Invoice# 360172592` — the same
  invoice number. Date read as **2026-03-30**. This one is certain.
- **Anthropic USD 100**, receipt `2197-2579-4644`, date read as
  **2026-06-21** against a file dated 07-03; intended for the 07-10 charge.

Correcting the Crossmedia date alone closes the entire EUR gap on July.

The general defect behind the two instances: a date the extractor read wrongly
produces a receipt that will never pair, and nothing surfaces the near-miss.
An amount that matches exactly while the date sits months away is a strong
signal, and the workbench says nothing about it.

**Fix:** surface amount-matches-date-doesn't as a review candidate rather
than leaving the row unmatched and silent.

**CLOSED 2026-09-15: both instances were read correctly, and the general rule
would only have added wrong suggestions.** Checked before any code, against
four independent records: the stored extraction, the printed document (both
PDFs pulled from the image endpoint and read), the item-69 human labels in the
July live bundle, and the live run payload.

- **Crossmedia** prints `Invoice Date : 30 Mar 2026`, `Balance Due €900,00`.
  2026-03-30 is the invoice date, extracted correctly. The "charge" quoted
  above is not a card charge: it comes from
  `context/zoho-receipts-july-2026/july-2026-charges-without-a-receipt.csv`,
  a bank-transfer payment. July's only statement (`July2026.xlsx`) holds 112
  charges, all USD, none of them 900. Label: `no_charge:bank_transfer`. This
  is item 62's case, already shipped on the backend (`settled-outside`); what
  is left is the SPA paste of `docs/lovable-settled-outside-prompt.md`.
- **Anthropic USD 100** prints `Date paid June 21, 2026` on `Visa - 3645`,
  service period `Jun 21–Jul 21`. Extracted correctly. Its charge belongs to
  June, whose month carries no statement. Label: `no_charge:neighbour_period`.
  Item 61's adjacent pool is the mechanism that pairs it once June has one.

**The rule, measured before building it.** Every (free charge, free receipt)
pair with the same currency and the exact amount, over both live statement
months: July 4 pairs, August 3. With a vendor floor of 0.5 the ones a
far-date rule would surface are July's Anthropic 06-21 receipt against the
ANTHROPIC 100.00 charges of 07-10 (vendor 1.00, 19 days) and 07-21 (0.52, 30
days). The labels say both are wrong. Without the floor July adds LOVABLE
100.00 (vendor 0.20), and August adds Google 71.64 08-31 against both 08-01
Google Workspace charges (labelled `no_charge:neighbour_period`, it posts in
September) and a collapsed duplicate copy of a Lovable 50 invoice against
BASE44 50 (labelled `excluded`). Zero right answers out of every candidate. The exact-amount population in these months is
recurring subscriptions at identical amounts, so "same amount, far date" says
"same subscription, different period" far more often than "misread date".

**What would reopen it:** one live receipt whose EXTRACTED date differs from
its PRINTED date while a free charge carries its exact amount. The class is
real on the receipt grid (item 25's wrong years, item 28's residue of a wrong
day inside the right month), and item 25's `date_outside_period` already
flags the out-of-window half there. No statement month has produced an
instance yet. A rebuild would also need a guard against the subscription
pattern above (card agreement plus no second same-vendor same-amount charge
is the first thing to measure), because without one it misleads on exactly
the months Criss works in.

### 26. Card registry gaps put 8 rows in MISSING ENTITY (owner-side, 2026-08-23)

**Entity half DONE 2026-09-06** (authorized operator-API write, verified on
`/api/cards` re-read): 0113 → Corporate Services; 6013/9693/8311 → Cloud
Services; card-0340 created (digits `0340`). Values from the Zoho entity map
in `context/expense-reconciliation/zoho-entity-card-map.md`.

**Calibrated against the owner's ALL BANKS list 2026-09-08** (screenshot
transcribed to
`context/expense-reconciliation/all-banks-brisken-group-2026-09-08.md`; owner
confirmed the mapping table in-chat before any write). Registry went 6 cards
→ 15, verified field by field on an `/api/cards` re-read, then
`refresh-master-data` on all three open batches (July/August/September).
Measured on real rows: **30 of 40 rows had no card and no entity before, 28
after.** The two that flipped are the `Visa ...1176` rows (Brave Software,
September; Anthropic, August), now card-1176 → Consulting with
`entity_source: card`. No row lost a card or an entity.

What the list settled:

- **New cards:** 1176 → Consulting, 4921 + 5126 → BRISKEN GmbH.
  Confirmed-existing: 0113, 2838 (Corporate Services); 6013, 8311, 9693
  (Cloud Services).
- **CORRECTION, same day (2026-09-08 pm).** The round also created
  `card-3693` from the Cloud Services row read as "CHASE VISA 3693". Criss
  mailed the same sheet directly and a 10x re-read says that row is **9693**;
  the first transcription misread a 9 as a 3. Three sources agree and nothing
  supports 3693: the screenshot at pixel resolution, Zoho's own COA name for
  org 697686691 ("Chase Visa | 9693 | Cloud Expenses", the ONLY 3693-or-9693
  match across all eight orgs), and six live payment hints carrying 9693
  against zero ever carrying 3693. `card-3693` was a phantom of this round
  and has been DELETED from the live registry (operator API, re-read
  verified: 14 cards, no card-3693, everything else byte-identical), followed
  by `refresh-master-data` on all three open batches. No expense was ever
  misfiled by it: both digits mapped to Cloud Services and 3693 resolved no
  row, so the unresolved count is unchanged at 28/40 and the six 9693 rows
  and two 1176 rows are intact. Two consequences: 9693 is CONFIRMED on the
  list rather than absent from it, so that open question is closed and the
  ask was struck from the Criss/Dirk draft; and the transcription's own
  correction note flags three Wise bank-ACCOUNT digits as suspect on the same
  re-read (2932 may be 2992, 0173 may be 0179, 9137 may be 9197). Those are
  statement-coverage account ids, not cards, so nothing in the registry
  depends on them; verify against the source before using any as an
  account_id. The transferable lesson is in the checkpoint: a digit read off
  a screenshot is a MEASUREMENT, and this round cross-checked 1176 against
  live rows but accepted 3693 on the transcription alone because it resolved
  nothing to contradict it. Absence of contradicting rows is not
  confirmation; the Zoho COA cross-check was available and would have caught
  it in one grep.
- **The four crossed-out cards** (2448 → Cloud Services, 7531 → entity
  pending, 1160 → Consulting, 3344 → Corporate Services) plus the
  owner-marked-closed 1930 → Cloud Services are registered **active**, with
  the retirement carried in the `label`. This is the opposite of the
  originally planned `active: false`, on a code finding: `resolve_card`
  filters to `live = {k: c for k, c in cards.items() if c.active}` and
  `legacy_card_accounts` skips inactive cards, so deactivation means "never
  resolve" in BOTH directions. An inactive card does not resolve a
  historical receipt either, so `active: false` would have left behaviour
  identical to today (absent = resolves nothing) and bought only a
  Settings-screen entry. Owner confirmed active-plus-label 2026-09-08. A
  cancelled card cannot be charged, so the usual risk of leaving one active
  is nil. Past batches are unaffected either way: each snapshots the
  registry at creation.
- **No backend round was needed.** `active` already round-trips through all
  five card code points (`normalize_cards_setting`, `cards_to_setting`,
  `Card`/`_card_from_setting`, `card_to_dict`, the snapshot/refresh path).
- **Entity naming:** owner confirmed the tool keeps `Corporate Services`;
  the list's "Corp Service / LLC" and Zoho's "BRISKEN, LLC (Corporate
  Services)" are the same entity. Renaming would have meant re-keying the
  `/data` COA provisioning and re-stamping live rows.
- **Consulting is now charted** (owner: "add cards now and chart"), via
  `settings["entities"]` rather than the `/data` volume, because
  `coa_validation_from_settings` prefers the settings registry and falls
  back to the file's `chart_path` (the volume chart already holds all 8
  Zoho orgs). org_id `808232536`, six scope groups derived from the live
  chart under the same exclusion rule as the 2026-07-01 derivation (drop
  COGS, payroll, tax, depreciation/amortization/interest, R&D, discounts).
  They come out identical to Cloud Services' six. Proved, not assumed:
  `load_entity_chart` over the live `/data/zoho-books-coa.json` resolves
  all six to real chart roots covering 60 accounts, and
  `coa_validation_from_settings("Consulting", ...)` builds an enabled
  block. `entity_options` is now BRISKEN GmbH, Cloud Services, Consulting,
  Corporate Services.

Still open, Criss/Dirk only (all carried in the draft
`context/drafts/2026-09-08-card-gaps-criss-dirk.md`):

- **Cloud Solutions.** A separate entity block on the list matching no Zoho
  org. Owner reads it as a second name for Cloud Services and asked for
  Dirk to confirm, so card-7531 is registered with **no entity** pending
  the answer. Do not fold it into Cloud Services on our own read.
- **Six pending numbers:** three Ed Jones (one Cloud Solutions, two Corp
  Service / LLC), CHASE VISA CONS NEW, CORP SERV NEW, CORP SERV NEW2.
- **3645** is the largest live gap: four unresolved rows across
  July-September (`Visa ...3645` ×2, `[Visa] - 3645`,
  `Credit Card: xxxxxxxxxxxx3645`). An August Obsidian receipt prints
  **`CorpServ & DN ••3645`**, a sourced hypothesis (Corp Services card,
  Dirk) but a merchant's rendering, not the owner's own record. Not
  written; asked.
- **2544 and 9129**, two Google charges in August, in neither the list nor
  the registry. Found by this enumeration.
- **1042** (is `6013 - 1042` one card with two digit identities?) and
  **1672** (the 2838 plastic, still NOT registered live despite `cards.py`
  using it as its worked example). Same question shape; register both
  digits on one card once confirmed.
- **0340** still has no entity.
- **GmbH stays chartless.** Its Zoho chart (org `696750461`) is flat and
  German with no operating-subtree structure to mirror, so deriving a scope
  would be inventing one, and the entity is dormant in Zoho since
  2024-12-30 with zero live rows. Surfaced, not filled.
- Zoho knows two cards the list omits: GmbH **1940 (Firma)** and Holding
  **Wise Visa 4872**; Holding does not appear on the list at all.
- The `(P)` printed on Wise Visa 3344 is unexplained (personal?). Filed
  under Corporate Services per the list; low risk, retired card, no rows.
- Nine generic-tender rows stay per-month assignments by design.

Historical text (for the ranking's sake): four of the five known cards
carried no legal entity and 0340 was absent entirely; the 0340 rows alone
accounted for 8 of the 29 unresolved April entity rows. No code needed then
or now; listed here so it is not mistaken for a defect in the chain.

### 16. Rejected matches need a "what now" (SHIPPED PR #828 - see Shipped row 35)

STATUS_REJECTED sends the transaction back to unmatched and is reversible
pre-export, but no rejected bucket exists in the API and no affordance
answers "what happens to rejected matches?". Shipped 2026-09-15: no bucket
was added, because the reject is not a place a charge goes; it is a verdict
on a pairing. `rows[].candidates[].rejected` marks every candidate of a
rejected charge (parallel, absent otherwise) and
`summary.n_rejected_pairings` counts them, so the SPA stops re-offering a
receipt the reviewer just pushed away. The undo turned out to exist already:
`POST .../decisions` with `"status": "pending"` resets the charge under the
same lock, re-derives the claim and hands the receipt back, so no `DELETE`
route was added and the test drives that reversal end to end instead.
Charge-level by construction: `apply_decisions`, `effective_settlements` and
`sync_claim_for_decision` all read the status alone, and a bulk reject writes
`chosen_document_id` NULL.

### 17. Workbench filter/sort (SHIPPED - see Shipped row 40)

"There should be a filter somewhere: alphabetic, unmatched elements."
Natural home: the grouped-queue render (PR #454/#455's remaining Lovable
half). Read live 2026-09-15: that half is published and most of the item
with it. The bar carries a vendor search, BUCKET toggles, STATUS, SORT
(Default / Vendor A-Z / Date x2 / Amount x2) and six FILTERS toggles, and
Vendor A-Z is already case-insensitive on the live August month
(AngelaClaudiaDos before ANNUAL MEMBERSHIP FEE, the two GOOGLE / Google
Workspace spellings adjacent) - so the `vendor_sort_key` this round was
scoped to add would have duplicated a working collator with a worse one,
and was built, measured against the page, and reverted. What the drive DID
find is a live defect nobody had reported: `amount` is a display string
(`f"{v:,.2f}"`), so "Amount, high to low" on August's 93-row unmatched
group puts `ZOHO* ZOHO-ONE 2,484.00` and `SAP SE 1,574.24` at the BOTTOM,
below `MarceloEzequiel 1.16`. The month's two largest unreviewed charges
are last under "highest first". That plus card / company / has-candidates
filters, per-option counts and URL state is the SPA delta.

### 18. Async endpoints acquire the batch lock on the event loop (SHIPPED - see Shipped row 14)

Found by the delete-month adversarial review (2026-08-21): the delete
handler was fixed (kept sync), but `restore-set-aside` and the cards
assignment endpoint are `async def` and take `_BATCH_ADD_LOCK` directly —
while an OCR ingest holds that lock for minutes, either call parks the
EVENT LOOP and freezes every endpoint including `/healthz` (Fly health
checks fail, machine restart kills the in-flight ingest). Shipped 2026-08-22: both
handlers read a JSON body first, so they stay `async def` and hand the
locked span to `run_in_threadpool`. Reproduced first (hold the lock from
another thread, call the endpoint against a REAL batch id, probe /healthz:
it never answered), then fixed, then re-run: 42s of timeouts became 2.2s.
A static AST guard now flags any `async def` route that calls a
lock-taking service function outside a sync closure, with the locked set
derived from `service.py` so a new one joins for free; proven by
regressing the cards handler back inline. `_BATCH_ADD_LOCK` carries the
in-process-only + no-async-blocking note.

### 3. Put the set-aside statement pages to work (later)

**What happens today:** statement pages found among the receipts are set
aside and that is the end of it.

**Why it matters (eventually):** those pages are exactly what the OTHER
half of the tool (statement reconciliation, Mode B) needs as input. Criss
uploading them "wrong" is actually her handing us the month-end statement
early.

**The fix, someday:** offer set-aside statements to the statement side of
the same batch instead of only quarantining them. Do this only after the
statement-attach flow is in daily use; until then it is speculative.

**Status:** idea, deliberately not scheduled.

### 4. Category flips on identical inputs (watch, do not build yet)

**What happens today:** the reading cache (shipped 2026-08-15) pins what
the AI SEES on each photo, but the categorize step still asks the AI
fresh every run. Across the August test runs the same PagBank receipt was
filed three ways on three days (no category, "Professional Services",
"Software & Subscriptions") while its money never moved. In the two
back-to-back runs after the cache shipped, categories came out identical
both times, so with pinned inputs the wobble may be rare in practice.
2026-08-16 check: a third smoke10 run (R7) came out byte-identical to
R6, categories included; the watch stays quiet. 2026-08-18 (round 5):
the May fresh-read pair showed one category change, but it was caused by
the item-6 vendor flip (bank-as-vendor carries no category signal), not
by categorize-call wobble on a pinned input — the watch condition has
still never fired.

**Why it might matter:** a category that flips between runs creates the
same trust problem as a vendor spelling that flips. But the merchant name
book and learned memory already outrank the AI for every merchant Criss
has corrected once, so the exposed surface shrinks on its own as she uses
the tool.

**The fix, if needed:** extend the same store to categorize calls (keyed
on the line-item descriptions + the account list). Only build this if a
flip is actually observed on cache-pinned inputs.

**Status:** watching; re-check the diff on the next loop iteration.

### 5. Stale "excluded" warning after a restore (cosmetic)

**What happens today:** when a reviewer restores a set-aside file, the
strip entry flips to "restored" but the original technical parse warning
("excluded from expenses, no row exported") stays in the issues list,
now contradicting the grid.

**Why it barely matters:** the strip is the surface Criss reads; the
issues list is ours. Fix only if the contradiction confuses someone in
practice.

**Status:** open, cosmetic, low priority.

### 7. Round-5 fresh-read drift record (evidence, no action)

Two fresh reads of Criss's May folder 5 days apart (2026-08-13 vs
2026-08-18, no cache in the local config): all 20 rows kept identical
amounts, currencies, and dates, and the statement quarantine held 7 of 7
both times. All drift was in text fields: the item-6 vendor flip, one
vendor spelling (Enimove vs Enilive, real brand Enilive), tax-label and
reference noise, and one row that lost its card-hint Paid-Through
resolution. Set 6 (13 never-tested receipts: Uber email-forwards, MBTA,
DB tickets, BRL service invoices) produced exact sums against every
source total spot-checked (three Uber trips to the cent, DB 6.65 EUR);
its misses were vendor names only ("CIV" instead of DB AG, "Uber
Receipts" instead of Uber). Conclusion: money is stable across fresh
reads; residual noise is text-field-only and shrinks as the merchant
book grows.

### 8. Cross-month vendor history in the drill-down (build on demand)

The shipped variance chip (row 6 below) covers THIS batch. The richer
half — "this vendor was Meals in May, Software in June" — needs a small
backend endpoint over run history. Build it only when Criss confirms the
within-batch drill-down is something she uses.

**Status:** deliberately deferred; evidence-gated.

### 9. Multi-category vendors (SHIPPED as row 6 — design record)

**The situation (owner direction, 2026-08-19):** the same vendor can
legitimately produce receipts in different categories (reality), or the
same kind of purchase can flip categories by AI wobble (error). No rule
distinguishes them; a human seeing the vendor's receipts side by side
can. Criss raised the underlying problem in her r1 feedback
(vendor→multi-category, previously parked in the status file).

**The design (pending Criss's concrete example):**

- **Variance chip:** a receipt row whose vendor carries different
  categories within the batch gets an indicator; click →
  **vendor drill-down** (all of that vendor's receipts). Within-batch
  half is nearly free (SPA already holds the rows, Lovable-only);
  cross-month history needs a small backend endpoint over run history —
  add when she confirms she'd use it.
- **Blind spot this fixes:** a vendor with a merchant-book default
  category is auto-stamped and the LLM never runs, so registry-covered
  vendors can never show variance, right or wrong — exactly Criss's
  complaint. Resolution: a per-vendor **multi-category flag** in the
  merchant book — the book keeps canonicalizing the NAME (spelling
  stability) but stops auto-stamping the CATEGORY for flagged vendors;
  each receipt judged on contents, variance auditable via the chip.
  Decouples name stability from category flexibility; no global
  precedence reversal.

**Still needed from Criss:** which vendors actually get the flag turned
on, and what tells her the category on such a receipt (items? card?
entity?) — that answer is Merchants-editor data entry now, not code.

### 55. Excel statements reached the matcher with the printed sign (LIVE DEFECT, Criss 2026-09-11, SHIPPED same day)

Criss, on August 2026 (PT): "ele ve que tem recibo mas nao associa com o que
la embaixo ele mostra que tem" - the tool shows the receipt in the pool and
never links it to the charge above. Read off the live API before touching
code: July `50622baec444` 112 charges / 50 receipts / 0 reconciled, August
`074a7b8905d7` 111 / 31 / 0, every charge `pending` with zero candidates,
exact same-day same-amount pairs in both (LOVABLE 15.00 on 08-31, OBSIDIAN
96.00 on 08-30, ZOHOCORP 576.00 on 08-30, PRESSMASTER 135.00 on 08-23).
Both months hold a Chase multi-card workbook (`Card, Transaction Date, Post
Date, Description, Category, Type, Amount, Memo`): purchases printed
negative, one payment positive, `refunds` empty.

**Cause, in the parser.** `statement_csv` has canonicalized the sign since
3.15 (a mapped `type` column per row, else the majority inference with a
warning); `statement_xlsx` had neither and kept the printed sign, so the
matcher compared `-15.00` with `15.00`. Nothing else was wrong: the same
file through the CSV parser matches. Two more things stood behind it once
the sign was right, measured on the real August file offline: the hosted
column guess never mapped Chase's `Type`, so the sign was only ever
inferred; and `match_month` dropped any receipt whose entity differed from
the charge's, which for a mailed or dropped receipt (entity `""` until a
card hint or the reviewer names one) meant every one of them. 23 of
August's 31 receipts and 46 of July's 50 have no entity.

**Fix (this round).** Parser: the xlsx parser mirrors both CSV paths.
Guess: `type` is mapped on `^type$` / `^transaction type$` only (an `Account
Type` column would abs() every credit into a purchase). Matcher: an empty
entity on either side is unscoped; a receipt that NAMES another entity still
never pairs (`test_entity_scope_prevents_cross_entity_match` untouched).
Repair: `POST /api/expense-batches/{id}/statements/reread` rebuilds the
charges from the files in `statements[]` and replaces the set - a re-upload
could not do it, because `transaction_id` derives from the canonical amount
and the corrected rows would have folded in beside the wrong ones. Decisions
ride over by sheet row through `statement_anchors`; a missing file, an
unresolvable map, a stranded decision or an upload that landed mid-read
refuses with nothing written. Offline on the real files after the fix:
August 5 exact + 4 FX-judgment + 23 charges with candidates to pick, 7
receipts still unmatched; July 13 + 27 + 12, 6 unmatched. Before: 0 and 0.

Also fixed on the way: `fly.toml` in the module still said scale-to-zero,
`recon_data` and 512 MB while the platform runs always-on, `recon_data_v2`
and 1024 MB, so a deploy from the module directory would have undone the
2026-09-10 recovery. It now mirrors `flyctl config show`.

Follow-up (void 7 of the 2026-09-11 list): a repaired parser cannot repair
the months it already parsed except through this curl-only re-read. Store
a parser fingerprint per `statements[]` entry (the extraction cache does
this for vision) and flag or re-read stale months on load. Not built.

### 56. An invoice and its receipt for one purchase make the pairing ambiguous (2026-09-11, found by item 55)

Stripe-style vendors (Lovable, Anthropic, Pressmaster) mail BOTH an invoice
PDF and a receipt PDF for one charge; the drop and the mail intake keep both,
and `find_duplicate_receipts` flags them as a group (same vendor, date, total,
currency). The matcher still sees two candidates for one charge and files the
pair as **ambiguous**, so the reviewer picks one of two identical documents
for every such purchase: in August, 23 of the 31 receipts sit in such pairs
and the LOVABLE 15.00 / OBSIDIAN 96.00 / ZOHOCORP 576.00 charges are
"ambiguous" rather than exact. The duplicate resolution
(`POST /api/runs/{id}/duplicates/resolve`) is display-only and never
narrows the pool.

Proposal, not built: collapse a duplicate group to ONE candidate in the
matcher pool (`rematch_month`, before `match_month`), keeping copy 1 and
leaving the extras in the snapshot flagged as duplicates, unless the group
was resolved as "not a duplicate" (two real purchases, same day, same
amount). A receipt-side collapse is the smaller change; the alternative is
teaching the matcher that candidates within one duplicate group count as
one. Owner call: whether an unresolved group may be collapsed automatically
or only after the reviewer confirms it. Until then the pairs surface as
candidates and Criss picks.

**RULED + SHIPPED 2026-09-14 (void 6).** Owner ruling: collapse
automatically. `duplicates.collapsed_duplicate_copies` names every copy
after the first in each unresolved or confirmed group;
`rematch_month` keeps those out of the candidate pool, so the pair is one
exact match instead of two indistinguishable candidates. Nothing is
dropped: the copy stays in the snapshot, the counts and the exports, and
surfaces as unmatched with its `duplicate` marker. A group ruled `ignore`
(two real purchases, same merchant, same day, same amount) is not
collapsed, and `POST /api/runs/{id}/duplicates/resolve` now re-matches a
reconciling month so that ruling is not recorded-and-inert. Tests:
`test_duplicate_collapse.py` (5, route-level); three regress proofs.

### The 2026-09-11 void list (items 57-64, ranked; 6 = item 56, 7 = the re-read under item 55)

Ten functionality voids found in the same session that fixed item 55, each
grounded in the live July / August data. Items 57 and 58 are the first
round; 59 and 56 need an owner ruling before code.

### 57. Readiness said "ready to post" on a zero-match month (2026-09-11)

August 2026 carried `ready_to_post: true` with 0 of 111 charges matched and
31 receipts in the pool, four of them exact same-day same-amount pairs of
a charge (LOVABLE 15.00, OBSIDIAN 96.00, ZOHOCORP 576.00, PRESSMASTER
135.00). Readiness checks undecided rows and unmapped accounts only, so a
month the matcher could not see at all read as finished. Rule: when the
matcher proposed nothing and exact pairs sit in the pool, the sign, the
entity, the currency or the card scoping is broken; refuse readiness and
name which. Surface it on both review payloads (`summary.month_health`).
Built 2026-09-11 evening, this round.

### 58. No notification on living-month re-matches (2026-09-11)

`tools/brisken-recon-notify.py` pings on new runs only. Attaches, re-reads
and mail-driven re-matches (every path through `rematch_month`) report
nothing, so the 2026-09-10 uploads that reconciled 0 were invisible to the
dev until Criss wrote. Each commit of `rematch_month` now records one event
(`rematch_log` in the snapshot, surfaced as `rematches[]` on
`/api/operator/state`), and the notifier mails one line per event:
"August 2026: 14 of 111, pool 7 (statement)". Built 2026-09-11 evening,
this round.

### 59. A multi-card workbook stamps every charge with the upload's entity (2026-09-11)

August was uploaded as `account_id` card-2838, so all 111 rows read
Corporate Services, while `coverage[]` shows cards 3645 (40 charges) and
3876 (37) as "not in your card list" with a blank entity. The parsed card
column is already on every row (`card_last4`); the entity should resolve
per row through the card registry, and a card the registry does not know
should not inherit the upload's entity.

**RULED + SHIPPED 2026-09-14.** Owner ruling: blank entity for unknown
cards. `service.stamp_charge_entities` resolves each row that printed a
card through the batch's registry snapshot (`resolve_card`, ambiguity to
nothing, the same identity the coverage panel and the card scoping use)
and leaves the entity empty when the registry cannot name the card or
names it without an entity; a workbook with no card column keeps the
upload's entity, because there the account id IS the card. Re-stamped on
every re-match, so defining the card once and refreshing master data fills
the rows in place. `summary.n_charges_no_entity` on both payloads counts
the gap. The hand-match guard was sharpened to the matcher's own rule
(empty on either side is unscoped; only two NAMED entities refuse), since
a charge can now legitimately carry none. Tests: `test_charge_entity.py`
(6, route-level); two regress proofs. SPA half:
`docs/lovable-charge-entity-prompt.md`.

**What the live months actually showed, against the prediction.** The
expectation going in was that ~77 of August's charges would move to a
blank company. They did not, and the reason matters: cards 3645, 3876 and
0340 ARE defined in the live registry (all nine cards carry an entity; the
owner finished the item-26/40 data entry at some point after these
batches were uploaded). What the coverage panel called "not in your card
list" was the BATCH's registry snapshot, frozen at upload time, not the
live registry. Refreshing each month's master data pulled the current
registry in and every charge resolved to its real card: `n_charges_no_entity`
0 on both months, the three "not in your card list" rows replaced by
"Credit Card Chase Visa - 3645 / 3876 / 0340", each Corporate Services.
The gap the item was written against was stale-snapshot, not missing data.
Lesson for the next read: `coverage[].known` answers "did THIS BATCH know
the card", never "is the card defined"; ask `/api/settings` for the
second question.

### 60. A charge with waiting candidates renders "No receipt found" (2026-09-11)

LOVABLE 25.00 on 2026-08-05: `initial_bucket: review`, `effective_bucket:
unmatched`, section `attention`, two candidates (0027 ambiguous, 0028
exact 99%), neither chosen, and the SPA prints "No receipt found" while
both receipts show elsewhere as "Awaiting decision". The row is in the
attention section with candidates, so the label the SPA derives from the
bucket is the wrong half; decide bucket-vs-label on the backend first, then
hand the SPA half as a Lovable prompt.

**SHIPPED 2026-09-15. The label was the wrong half, and the bucket is
right.** `candidates[]` comes from the RAW outcome, which keeps every
receipt the matcher paired with the charge; the bucket comes from the
EFFECTIVE verdict after `apply_decisions`, and one receipt settles exactly
one charge. So a charge that loses its receipt keeps the candidate on
display and falls to `unmatched` truthfully; what was missing was WHO has
it. `rows[].candidates[].held_by` names the holding charge (parallel,
ABSENT when nobody else holds it), and `summary.n_charges_receipt_taken`
counts rows whose every candidate is held elsewhere. It follows the
effective verdict, so handing the receipt back clears it. Tests:
`test_receipt_taken.py` (3, route-level, the steal driven through
`POST /manual-match`); two regress proofs. SPA half:
`docs/lovable-receipt-taken-prompt.md`.

**The reported instance no longer reproduces.** Read live before building:
both months now show ZERO rows with candidates in the `unmatched` bucket,
because item 56's duplicate collapse gave the LOVABLE 25.00 charge its own
exact match. The mechanism is still reachable (any reassignment produces
it), which is why the fix shipped, but the fixture had to be built rather
than observed. A first attempt to reproduce it with two identical charges
competing for one receipt was WRONG: the loser lands in
`unmatched_transactions`, which carries no candidates at all.


### The 2026-09-15 parallel round (items 61-68 + 16 + 17, one session each)

Ten open items run as ten simultaneous sessions, each on its own worktree
under `automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`.
Items 65-68 carve the four standalone defects out of item 49 so each has a
number a session can own and a Shipped row can close; item 49 stays the
evidence record (section 12 of the storage-system description).


### 68. The receipt column overstates coverage, and the two reports can disagree (item 49)

The Receipt column reads "attached" once the file was read off disk, which
is decided before renderability is known, so the count of expenses with a
usable receipt page can be too high; the caption pages are the truth. And
an expense the reviewer deleted leaves the expense report immediately but
stays in the reconciliation report until the next re-match, because the two
are built from different sources. Make the column and the count answer
"has a page in the report", and build both reports from the one live
overlay.

**SHIPPED 2026-09-15 (PR #838). Neither half reproduced on the live months, and both
mechanisms are reachable.** Read before building: August 31 expenses, 31
called attached, 31 receipt pages in the built report; July 51, 51, 51. Zero
"could not be rendered" captions on either month, and the expense set is
identical across the two documents (31/31 and 51/51), because no delete is
pending on either. So the fixtures are constructed, like item 60's.
`expenses[].receipt_in_report` (parallel boolean, ABSENT until known) and
`summary.n_receipts_in_report` (absent while ANY row is undecided) answer
"has a PAGE". Item 67 landed first with the channel this needed, so the
verdict is DERIVED from its `receipt_render` rather than decided a second
time: 67 answers "did this file break", 68 is the positive form over every
expense (a row with no file has no page, and that needs no build), which is
what a coverage count can be summed from. The report's own Receipt column
now reads the pages `prepare_evidence` admitted instead of the files it was
handed. `build_reconciliation_report` takes the
expense overlay and hands the live pool to `build_view` rather than
filtering its output, because the unmatched list, the duplicates, the
candidates and the counts are all derived in there. The renderability check
itself is untouched (item 67 owns per-file failure handling). Tests:
`test_receipt_coverage.py` (8, route-level through both report routes and
the grid); three regress proofs RED first.

**One live finding this item does not cover, left open.** July's expense
report listing has 54 rows for 51 expenses (the account fan-out), and rows
52-54 read "none" in the Receipt column although every expense has a file:
`aligned` is false there, so the evidence falls back to one caption per
receipt numbered 1..51 while the listing numbers 1..54. The captions past
the first fan-out row therefore name the wrong expense number. That is the
numbering fallback in `build_expense_report`, not the coverage question, and
it wants its own item.

### 69. Matching improvement program: measure first, then two structural rounds (2026-09-15)

Owner program (prompt in the 2026-09-15 checkpoint "Expense-Recon Matching
Program Prompt"): raise the share of receipts that resolve deterministically
and correctly on Criss's real months, zero wrong auto-matches, coverage
reported apart from matching, none of the refuted tuning levers re-run.

**Phase 0 is done (2026-09-15).** Both live months replayed locally from
the hosted snapshot with no model call, byte-identical to the outcome the
app committed (`tools/recon-match-attribution.py --live`). Labelled through
the existing `expense-recon label` flow into two bundles beside the six
scorer bundles (`context/.../by-month/July-2026_live_50622baec444`,
`August-2026_live_074a7b8905d7`; 82 decisions, notes.csv carries each
rationale; a no_charge label records WHY in its evidence column). Zero
reviewer decisions exist on either month, so every label is the labeler's
call under the exclusion discipline: 12 excluded as ambiguous, duplicate
copies excluded, bank transfers and private cards no_charge.

Attribution, one gate per receipt in code order, live v117 code:

| class | July (51) | August (31) |
|---|---|---|
| resolved clean, correct | 26 ($2,658) | 7 ($1,147) |
| wrong auto-match | 1 ($173: Hostinger re-mail copy dated 07-28 took ANTHROPIC 205.56, 16% off) | 5 ($251: Lovable 50 took BASE44 50 exact; Perplexity 25 took ISABELE 24.84; Lovable 25 took RECANTO 26.94; Anthropic 100 took ATT 105.23; an Anthropic invoice copy 51.38 took ANTHROPIC 51.16 while its receipt copy held the 51.38 charge) |
| matched, unverifiable | 0 | 2 (Zoho Books 576 took MICROSOFT 718.20 at 19.8%, a copy of the ZOHO invoice that holds the real charge; Anthropic 52.59 took one of eight ANTHROPIC charges between 50.52 and 54.12 with no exact) |
| duplicate copy, collapsed (item 56) | 2 | 8 |
| duplicate copy, undetected | 1 (Redis invoice + body) | 2 (Anthropic 100 receipt copy; the Petit Train card slip) |
| duplicate false positive | 1 (Google 71.64: two Workspace accounts, two charges on 07-01, collapsed as one) | 0 |
| demoted by the uniqueness gate, correct charge teed up in review | 10 ($181) | 2 ($246) |
| coverage: card statement not loaded (9693, 1176) | 0 | 2 (+2 counted under wrong) |
| coverage: charge posts in the neighbouring period (item 61) | 1 | 2 (+1 under wrong) |
| coverage: cash / debit / EC-Karte | 1 | 1 |
| coverage: bank-transfer invoice | 3 ($32,810) | 0 |
| excluded as ambiguous | 4 | 0 |
| no date read (private debit) | 1 | 0 |

In the prompt's shape. July: 51 receipts; 27 matched clean (26 right, 1
wrong); 11 in review (10 with the correct charge teed up, 1 ambiguous); 1
unmatched with a charge on the statement (the Google twin); 6 unmatched with
no charge on any loaded statement; 3 duplicate copies; 3 excluded. August:
31 receipts; 14 matched clean (7 right, 5 wrong, 2 unverifiable); 3 in review
(2 correct, 1 a duplicate copy offered a wrong charge); 0 unmatched with a
charge; 5 unmatched with no charge; 10 duplicate copies. The "14 clean" the
app reports for August is 7 right and 7 not.

**The six-bundle scorer was broken and is repaired.** Every confirmed label
still carried the positional ids (`chase-2838-family:177`) the parsers stopped
producing at PR 2a (2026-08-25), so `recon-match-accuracy.py` exited on the
first bundle and the anti-overfit guard had been non-functional since (the
item-63 session hit the same wall). All 95 labels re-keyed through
`{account_id}:{source_row}` with no collision (`labels.positional.csv` kept
beside each); scorer and guard reproduce the 2026-07-23 record exactly (train
49.5, all 65.2, 55/95 deterministic, 0 wrong, guard 4/4). One label corrected
with evidence in its row: `ER-00214#025` "Decarestauran te" belongs to the
same-day `MP *DECARESTAURAN` 28.84 (vendor identical, 2.2% off Zoho's base
amount), not the FENIX charge three days later that the labeler's 2% E3 tier
had proposed; train 49.5 -> 49.8, all 65.5. Second breakage, NOT fixed
(pinned file): the scorer's inline dependency list predates `rapidfuzz`, so
`uv run tools/scorers/recon-match-accuracy.py` fails on import; it runs
through the module venv (`uv run --directory <module> python
tools/scorers/recon-match-accuracy.py ...`), and the one-line re-pin needs the
`SCORER_LOCK_ALLOW=1` seam (owner order). The same attribution runs on the six
bundles (`--bundle DIR --asset config/match-tuning.json`): 55/95 clean, 36
demoted by the uniqueness gate with the correct charge teed up, 0 wrong.

**Plan (each round simulated against the labels on all eight datasets before
it is built; `.scratch`-class simulator, not shipped):**

- Round 0 is the sibling's item 63 (PR #829, the probable band needs the
  merchant to agree): August wrong 5 -> 3 (not 2, corrected 2026-09-15 on
  the origin/main measurement: freeing the ATT pairing let the Anthropic 100
  invoice bind BASE44 100.00, exact amount, 4 days, which the vendor floor of
  item 63 does not guard because it applies to non-exact amounts only),
  July 1 -> 0, nothing else moves. Taken as given.
- Round A, one purchase is one candidate by its number: `find_duplicate_
  receipts` gains a second key (invoice/receipt reference + total + currency,
  vendor spelling and date ignored), and the kept copy inherits a payment
  mode / entity it lacks from its copies. With #829: August wrong 2 -> 0 (the
  Lovable 50 invoice inherits its receipt copy's card 1176, Consulting, and
  leaves the Corporate Services statement's scope; the Anthropic 51.38 copy
  collapses), July wrong -> 0 without #829, August review 3 -> 2. Predicted
  zero wrong on both months. No recall gain; precision is the goal's hard
  constraint and "wrong money beats wrong text".
- Round B, a clean pair keeps its match when its rivals are spoken for or
  name another merchant: two refinements of the bilateral-uniqueness gate in
  `match_month`, never a threshold. (1) A rival charge that holds a
  bank-printed exact candidate with another receipt, or a rival receipt with
  an exact candidate elsewhere, is spoken for and does not block uniqueness.
  (2) A demoted clean pair auto-resolves when its own vendor agreement is at
  least 0.5 and beats every rival's by 0.25 (`_vendor_score`, aliases
  included); vendor is used only to PROMOTE a pair that already carries clean
  rate evidence, never to reject one, which is the opposite direction from
  the refuted vendor gate. Plus the masked-BIN fix in `_card_keys` (a digit
  run followed by a mask character is a card PREFIX, so
  `42463153XXXXXX38` stops reading as an absent card). Simulated for the two
  gate refinements: July clean 26 -> 31 (review 10 -> 5), August 7 -> 8, six
  bundles 55 -> 71 of 95 (holdout 13 -> 19 of 22), wrong 0 everywhere,
  scorer train 49.8 -> 56.8. The masked-BIN fix is reasoned, not simulated:
  it should add the Petit Train receipt in August (7 -> 9 with round A).
- Stop after B: the next class (the Google twins, two identical charges for
  two identical receipts) recovers at most 1 receipt a month, under the
  3-a-month floor; recorded below. Coverage classes stay coverage: item 61
  (live, waits for the June and September statements), item 62 (sibling),
  the 9693 / 1176 card statements (owner's call to load them).

**Decisions (the prompt's items 56 and 59 were ruled and shipped 2026-09-14;
nothing to rule there):**

1. The July Google pair (`0036` / `0037`, 71.64 each) was confirmed as a
   duplicate by the reviewer on 2026-09-14; the statement holds TWO `GOOGLE
   *Workspace` 71.64 charges on 07-01 and the receipts carry distinct Google
   invoice numbers and account refs (`...2544`, `...9129`, the same two that
   recur in August at 75.09 and 71.64). Recommend resetting that group to
   "not a duplicate" (`POST /api/runs/50622baec444/duplicates/resolve`, a live
   write, per-action yes): both receipts return to the pool, the two
   identical pairs tie, the reviewer picks once; today one charge stays
   unmatched for good.
2. Accept the fixture correction above (train baseline 49.5 -> 49.8 before any
   matcher change).
3. Re-pin the scorer with `rapidfuzz` in its inline deps (SCORER_LOCK_ALLOW=1,
   its own PR); until then the module-venv invocation is the floor.
4. Go on rounds A then B as above, each: RED-first regression, both scorers
   both directions, calibrate + suite, ship per B6, deploy, live re-match of
   July and August through `rematch_month`, SPA drive of one changed row.

Decision 1 (Google pair) ruled 2026-09-15: leave the reviewer's ruling; the
group stays confirmed and one Google charge stays unmatched. Decision 3
ruled 2026-09-15: re-pinned, PR #871.

**Round A shipped (2026-09-15, PR #874, merge `65031158`, Fly v130, and both
live months re-matched through `refresh-master-data` the same evening).** One
purchase is one candidate by its number.

**What the live re-match did, read off the app afterwards.** July: unchanged,
26 reconciled / 12 review / 73 unmatched charges, 16 judgments reused, 0 new
model calls. August: matched 11 -> 8 and unmatched charges 96 -> 100, which is
exactly the three wrong pairings plus the unverifiable one being released (2
new judgments). On the live API afterwards, `0025` (Lovable 50 invoice) and
`0015` (Anthropic 100 invoice) hold no charge, and `0021` holds the exact
ANTHROPIC 51.38 on card 3645; the reference-keyed groups render 3 on August
(Petit Train, Anthropic 100, Anthropic 51.38) and 2 on July (Hostinger bodies,
Redis invoice + body). Browser-driven on August's workbench: both BASE44
charges now read NEAR MISS / "Awaiting decision" with a "closest free receipt"
note instead of holding a stranger's invoice, and the Aug 05 ANTHROPIC 51.38
charge renders its own receipt at 99%. September was not re-matched and did
not need to be: the grid and the export apply the inheritance to every batch,
so its MISSING ENTITY count drops 21 -> 17 on the deploy alone (measured
before the ship on a copy of the live DB).

`duplicates.find_duplicate_receipts_by_reference` is the second key:
upper-cased alphanumerics of `detected_reference` (at least 5 characters;
a digit-only string equal to the receipt's own date in YYYYMMDD / DDMMYYYY /
MMDDYYYY / YYMMDD / DDMMYY / MMDDYY or to the digits of its total is no
reference) + total + currency, vendor spelling and date ignored.
`find_duplicate_receipt_groups` lists the vendor/date groups first, then the
reference-only groups; a reference group whose membership equals a
vendor/date group is that group (same id), overlapping memberships stay two
groups, nothing merges, so every saved resolution keeps its group.
`duplicate_groups[]` gains `basis: "reference"` on the reference-only groups
(parallel, absent on every vendor/date group; pinned in
`test_view_contract.py`, documented in `api-contract.md`).
`collapsed_duplicate_copies` collapses both kinds the same way (every member
after the first sorted one, unless that group is ruled `ignore`); a row in
two live groups carries the marker of the group in which it is the extra
copy. `inherit_card_from_copies`, over the full effective list, gives every
member of a reference group with no card-bearing payment mode the card its
copies name (only when every card-bearing copy names the same card) and an
empty entity the one entity the group names; applied in `rematch_month`
before `resolve_batch_row_cards`, so the card chain derives the entity from
the inherited card and the Lovable 50 invoice leaves the Corporate Services
scope. **Persistence choice:** the inherited payment mode and entity persist
into the snapshot's `receipts` exactly as the entity bake does (they ride
`snapshot_to_dict` with it), and are re-derived from the extraction baseline
on every re-match (item 70), so nothing accumulates; the grid and the export
apply the same function after the overlay, so the row's `payment_hint` /
`card` / `legal_entity_id`, the workbench's rendered receipt and the match
outcome say one thing (the coverage panel reads charges and is unaffected).
The attribution tool now CALLS `baseline_receipts`, `inherit_card_from_copies`
and `collapsed_duplicate_copies` in the app's order (no re-implementation),
uses the module's reference rule for its twin classes, and reads labels at
the document level: a kept copy labelled `excluded` whose collapsed twin
carries the verdict inherits it, so the measurement does not depend on which
copy the collapse keeps (the same aliasing the Phase 0 simulator used).

What the extractor puts in `detected_reference`, read off the DB copy of both
months: a real invoice / receipt number on most rows (`H0LHY2WQ-0032` and
`H0LHY2WQ0032` for one Lovable purchase, `DZ9BH3VA0037` on both Anthropic
copies, `IUS25300` on the Redis invoice and its rendered body, `H_46243348`
on both Hostinger bodies, `16530` on both Petit Train documents); Anthropic's
account id `NQTJA4FE` on five July receipts with five different totals (the
total in the key keeps them apart); 4-digit till counters on the Karlsruhe
slips (`4563`, `1514`, under the floor); 5-15 digit NFC-e / CV numbers on
the Brazilian receipts, none equal to a date or a total. Twin groups the key
finds: July 2 new (Redis invoice + body; the Hostinger re-mail copy, which
Phase 0 had counted under "wrong", not "undetected") plus the Lovable 200
and Aposto pairs where both keys agree; August 3 new (the Petit Train slip,
the Anthropic 100 copy, the Anthropic 51.38 copy, likewise counted under
"wrong" in Phase 0) plus 4 pairs where both keys agree (Pressmaster, Lovable
50, Anthropic 52.59, Lovable 25 on 08-05). Neither the Google twins (distinct
invoice numbers) nor the Zoho Books / ZOHO Corporation pair (distinct
references) twin.

Measured, labels as judge, before = origin/main `c19325ae`, after = this
branch, `tools/recon-match-attribution.py --live` on the DB copy:

| class | July before | July after | August before | August after |
|---|---|---|---|---|
| resolved_clean | 26 ($2,658) | 26 | 7 ($1,147) | 7 |
| wrong_exact_no_charge | 0 | 0 | 1 ($50 Lovable 50 -> BASE44) | 0 |
| wrong_probable_no_charge | 0 | 0 | 1 ($100 Anthropic 100 -> BASE44) | 0 |
| wrong_dup_copy | 0 | 0 | 1 ($51.38 Anthropic copy -> ANTHROPIC 51.16) | 0 |
| matched_unverifiable | 0 | 0 | 1 ($52.59) | 0 |
| dup_copy_collapsed | 2 | 4 | 8 | 11 |
| dup_copy_undetected | 2 | 0 | 2 | 0 |
| dup_false_positive | 1 (Google) | 1 | 0 | 0 |
| demoted_uniqueness | 10 | 10 | 2 | 1 |
| demoted_card | 0 | 0 | 0 | 1 |
| coverage_unloaded_card | 0 | 0 | 2 | 4 |
| coverage_neighbour_period | 1 | 1 | 3 | 3 |
| coverage_non_card_tender | 1 | 1 | 1 | 1 |
| coverage_bank_transfer | 3 | 3 | 0 | 0 |
| coverage_unknown_card | 0 | 0 | 1 | 1 |
| excluded_ambiguous | 4 | 4 | 1 | 2 |
| unlabeled_unmatched | 1 | 1 | 0 | 0 |
| review (correct teed up / other) | 10 / 2 | 10 / 2 | 2 / 1 | 2 / 1 |

Pairs that moved, August: `0025` Lovable 50 invoice, took BASE44 50.00 ->
unmatched, coverage_unloaded_card (label `no_charge:unloaded_card`; the grid
now shows it on card 1176 / Consulting); `0015` Anthropic 100 invoice, took
BASE44 100.00 -> unmatched, coverage_unloaded_card (same label); `0021`
Anthropic 51.38 invoice, took ANTHROPIC 51.16 -> exact match to ANTHROPIC
51.38 on card 3645 (the label's verdict, carried by its copy `0022`, which
is now collapsed); `0016` Anthropic 100 receipt copy, undetected ->
collapsed; `0018` Petit Train billet (in review, correct charge teed up) ->
collapsed, with `0000` SARL TRAIN'S kept and in review with the same correct
charge teed up (demoted_card: its `42463153XXXXXX38` masked BIN reads as an
absent card, the round-B fix); `0023` Anthropic 52.59 invoice (label
`excluded`), an unverifiable match to ANTHROPIC 52.46 (`6d474e9e8e964bd4`,
08-03) -> with card 3645 inherited it also ties with `0021` on ANTHROPIC
50.52 (`c632cb75a5098253`, 08-03), a charge on which the matcher lists
`0021` as a candidate although `0021` holds an exact match to 51.38
elsewhere; the RAW outcome keeps `0023` -> 52.46 as a probable match, the
effective layer drops it because the receipt is tied on the other charge,
and 52.46 is the charge that leaves the reconciled list (the persistence
split is item 72; round B's "spoken for" in tie detection resolves this
instance). July: `0002` Hostinger re-mail copy and `0070` Redis body,
undetected -> collapsed; nothing else moved. Six bundles: 55/95 clean, 0
wrong, class tables unchanged; NOTE (review, 2026-09-15): the pinned scorer
replays `match_month` on the raw bundle receipts and does not see pool
assembly, so its floor is unchanged by construction, and the "byte-identical"
bundle tables this paragraph first reported were the same raw replay; the
attribution bundle tables in the review paragraph below are the measurement
of this round. Scorer + guard: train 49.8, holdout 15.7, all 65.5, 55/95
deterministic, determ_wrong 0, guard 4/4 PASS, calibrate exit 0; the floor
held exactly. Suite 1746 -> 1785 passed / 2 skipped; four regress proofs RED
first (the second key, the collapse of reference groups, the inheritance
call in `rematch_month`, the `basis` field). Deviations from the prediction:
August review stays 3 (predicted 2): the copy offered a wrong charge left
review and `0023` entered it from an unverifiable match, which is the
precision direction (matched_unverifiable 1 -> 0); August wrong 3 -> 0, July
0 -> 0, no clean pair lost anywhere, as predicted. No SPA change is needed:
the duplicates prompt already renders groups and row markers, and `basis` is
optional display.

**Round A review fixes (2026-09-15, same branch, eight findings applied).**
(1) A normalized reference that appears on two or more receipts of one list
with DIFFERENT totals is an account id, not a document number, and no
receipt carrying it gets a reference key (`duplicates.reference_keys`, the
list-level rule that `find_duplicate_receipts_by_reference` and the
inheritance now read): July's five Anthropic top-ups `0047`-`0051` all carry
`NQTJA4FE`, bundle 01-10-2024_ER-00181 has two Bella Sky receipts on one
folio; the totals kept them apart by luck, and two top-ups of one amount
under one account id would have twinned and lost a match silently. A
digit-only reference is measured against the 5-character floor without its
leading zeros (`00144` / `00184` on 01-06-2025_ER-00194 are the till
counters `144` / `184`). Measured: silences `NQTJA4FE` on July, nothing on
August, every real twin shares one total; both live-month tables and the
six bundle tables are unchanged from the tables above. (2) The pinned
scorer replays `match_month` on the RAW bundle receipts and never sees pool
assembly (inheritance, collapse), so its floor cannot move with a
duplicate-key change; `recon-match-attribution.py --bundle` now assembles
the pool as `rematch_month` does (inheritance with an empty resolution map,
then `collapsed_duplicate_copies`) and is the measurement of this round on
the bundles: no bundle holds a reference or vendor/date twin (pool = N of N
on all six under the `c19325ae`, the round-A and the fixed module alike),
so the class tables equal the raw ones, 55/95 clean, 0 wrong. (3) A
reviewer's `ignore` on a reference group now also stops the card lend
(`inherit_card_from_copies(receipts, resolutions, card_hints)` at all three
callers: `rematch_month`, `build_expense_view`, `_expense_export_inputs`,
the last reached by the CSV route, the month PDF, the cost-center roll-up
and the trip / adjacent pools), so the card-less copy takes its own charge
after the ruling (`test_not_a_duplicate_frees_the_card_less_copy_for_its_
own_charge`, through `POST /duplicates/resolve`, the grid and the CSV);
consequence in the earlier re-expand test: the copy naming the statement's
card wins the charge outright and the card-less copy is unmatched, no
longer an ambiguous pair. (4) A member whose current payment mode is a hint
the operator assigned in the batch (`expense.card_hints`) is never
rewritten, because `resolve_hinted_card_ex` keys that assignment on the
exact stored string (route test through `POST /cards`; both live months
carry no hints today). (5) The export wiring has a test that bites: `GET
/runs/{id}/expenses.csv` carries `Legal Entity` Consulting on the
borrowed-card row. (6) September 2026 (`51a22ad72864`, no statement, 33
expenses on today's DB copy): the grid and the export apply the inheritance
on deploy with no re-match. Measured `build_expense_view` +
`regenerate_expense_export` on the DB copy, before (`c19325ae`) -> after:
`n_needs_entity` 21 -> 17, duplicate groups 7 -> 8 (the new one is `0015`
Invoice-890D70BF-0032 + `0016` Receipt-2547-4241-0916, basis reference);
four rows leave "No legal entity yet": `0003` Invoice-EF742DD0-0061, `0013`
Invoice-890D70BF-0033 and `0015` take card 9693 / Cloud Services from their
receipt copies, `0019` Invoice-214D91B6-0006 takes card 1176 / Consulting
from `0020`; the CSV (34 rows) changes on exactly those four rows (`Legal
Entity` from the placeholder to the entity; `Paid Through` from the
placeholder to `Chase Visa | 9693 | Cloud Expenses` on the three 9693 rows,
unchanged on the 1176 row because that card has no Zoho account set). The
owner will see MISSING ENTITY drop by four on September when this deploys.
(7) The attribution tool proves `RECON_MODULE_SRC` was the tree imported
(`SystemExit` otherwise; the resolved module path in every month / bundle
header line), so a "before" run can no longer silently measure the venv's
module. (8) The collapsed branch of the attribution classes consults the
live twin's label: a collapsed `confirmed` receipt whose kept twin is
confirmed / no_charge to a different verdict is `dup_false_positive` naming
the other charge. Pinned as today's behaviour for round B to flip
consciously (`test_a_masked_bin_lends_today_and_round_b_flips_it`):
`_card_keys("42463153XXXXXX38")` is `{"42463153", "3153"}`, so the
inheritance treats the SARL TRAIN'S slip `0000` as card-bearing and lends
that string to the `PAYE` billet `0018` (persisted `0018` payment_mode
"PAYE" -> "42463153XXXXXX38"), while the card chain reads it as an absent
card; the masked-BIN fix in `_card_keys` closes both. Suite 1785 -> 1800
passed / 2 skipped; eleven regress proofs RED first (the account-id rule,
the padded floor, the ignore skip and its wiring in `rematch_month` and in
the CSV route, the export wiring, the grid wiring, the hint skip and its
grid wiring, the reference groups in the receipts-add headline, the legacy
`duplicate_receipts` alignment). Scorer 49.8 / 15.7 / 65.5, 55/95,
determ_wrong 0, guard 4/4, calibrate exit 0 on all six bundles, unchanged.

**Round B built and measured (2026-09-15, this branch).** A clean pair keeps
its match when its rivals are spoken for or name another merchant. Three
changes in `matching/deterministic.py`, no threshold moved.

`uniqueness_verdicts(candidates, cfg)` is now the gate, public, taking the
FULL candidate set before assignment and returning a verdict per
rate-derived pair. `match_month` applies it and
`tools/recon-match-attribution.py`'s `trace_candidates` imports it instead
of mirroring the rules, so the matcher and the judge that measures it cannot
drift apart (that was a real exposure: the tool carried its own copy of the
rules and would have gone on reporting the old gate's classes). The verdict
decides in order: a contradicted card is demoted, always, and neither
refinement can rescue it; a pair with no rate-derived rival is kept with its
reason untouched; **(1) spoken for** subtracts any rival CHARGE that holds an
EXACT candidate with some receipt, or rival RECEIPT that holds an EXACT
candidate with some charge, because bank-printed evidence has already
claimed it and it cannot take this pairing too; **(2) vendor dominance**
keeps a pair that still has a live rival when its own `_vendor_score` is
>= `uniqueness_vendor_dominance_min` (0.5) and beats every rate-derived
rival's by `uniqueness_vendor_dominance_margin` (0.25). Vendor only ever
PROMOTES a pair that already carries clean rate evidence, the opposite
direction from the FX vendor floor the S1 run refuted. Knobs
`uniqueness_spoken_for` (bool), `uniqueness_vendor_dominance_min` and
`_margin` (float), in `_TUNABLE_BOOL` / `_TUNABLE_FLOAT` and written into
`config/match-tuning.json` at the same values, so `test_match_tuning.py`'s
`from_file(TUNING_FILE) == MatchingConfig()` proves the lockstep; `min` 0.0
disables rule 2, and both knobs off is exactly the 2026-07-23 gate. A pair
kept by (1) or (2) says so in its reason, which the SPA renders verbatim
("... Kept deterministic: the rival pairing is spoken for." / "... the
merchant agrees (1.00) and no rival's does (best 0.31)."); a pair that never
had a rival keeps its reason byte for byte, so no existing string moves.
Documented in `api-contract.md` (no new field, none retyped).

Third change, the masked BIN in `_card_keys`: a digit run IMMEDIATELY
followed by a mask character (`X x * #` or a bullet) is the issuer's BIN, so
`_card_keys("42463153XXXXXX38")` is now the empty set (unknown card, no
scoping) instead of `{"42463153", "3153"}` (a card absent from every
statement). Round A deliberately pinned the old behaviour so round B had to
flip it consciously; `test_a_masked_bin_lends_today_and_round_b_flips_it` is
now `test_a_masked_bin_no_longer_lends_round_b_flipped_it` and asserts the
`PAYE` billet keeps `PAYE`. Every existing spelling keeps its keys
(`"VISA - ******0340"` -> `{"340"}`, `"CorpServ 2838/1672 (Chase)"` ->
`{"2838", "1672"}`, `"************3876"` -> `{"3876"}`, `"...2544"` ->
`{"2544"}`), all pinned. **Correction to this round's prompt:** it listed
those as `{"2838","838","1672","672"}` and `{"3876","876"}`; `_card_keys`
emits the run and its leading-zero-stripped LAST FOUR, which for a 4-digit
run is the run itself, so the three-digit forms never existed. The tests pin
what the function actually returns. **Boundary, stated rather than assumed:**
the rule is "immediately followed", so a grouped spelling
(`"4246 3153 **** **38"`) still reads its groups as identifiers. Neither
live month contains one, and widening across separators would drop a real
card out of an ordinary label like `"Card 1234 - XYZ Ltd"`, where losing the
card also loses the contradiction gate's protection. Pinned as a boundary
test; reopen with a spelling that occurs, not with a hypothesis. `cards.py`
keeps its own digit logic for the card-review strip (item 35's
canonical-grouping half is still open) and is untouched here: it still
prints `42463153` as a card ending.

Measured, labels as judge, on a DB copy pulled after round A's live re-match
(before = `origin/main` `63209b67`, after = this branch, same copy,
`RECON_MODULE_SRC` proving which tree measured each). Both months' BEFORE
read parity OK with the hosted outcome, so the baseline IS what Criss sees
today:

| class | July before | July after | August before | August after |
|---|---|---|---|---|
| resolved_clean | 26 ($2,658.25) | **31 ($2,739.28)** | 7 ($1,147.34) | **8 ($1,184.53)** |
| wrong (any) | 0 | 0 | 0 | 0 |
| matched_unverifiable | 0 | 0 | 0 | 0 |
| demoted_uniqueness | 10 ($181.13) | **5 ($100.10)** | 1 ($209.21) | 1 ($209.21) |
| demoted_card | 0 | 0 | 1 ($37.19) | **0** |
| dup_copy_collapsed | 4 | 4 | 11 | 11 |
| dup_false_positive | 1 | 1 | 0 | 0 |
| coverage (all four classes) | 5 | 5 | 9 | 9 |
| excluded_ambiguous | 4 | 4 | 2 | 2 |
| unlabeled_unmatched | 1 | 1 | 0 | 0 |
| review (correct teed up / other) | 10 / 1 | 5 / 1 | 2 / 1 | 1 / 1 |

Six bundles: deterministic 55 -> **70 of 95**, demoted_uniqueness 36 -> 21,
wrong 0 throughout. Pinned scorer + guard (standalone since PR #871): train
49.8 -> **56.8**, holdout 15.7 -> **19.2**, all 65.5 -> **76.0**, determ_ok
55/95 -> 70/95, determ_wrong 0, nc_matched 0, invariant OK, guard 4/4 PASS,
calibrate exit 0 on all six. No split dropped, no resolved_clean receipt
lost anywhere.

Every one of the six live-month gains is label-confirmed and lands on a
charge whose merchant is visibly the receipt's: `0031` Enchilada Karlsruhe
30.00 EUR -> `ENCHILADA KARLSRUHE` 34.39 (the rival was `Wix.com` 34.36),
`0052` -> `WILLAMS RONALD DA SIL` 1.97 (rival `BEATRYZ RI` 1.98), `0057` ->
`MP *24HBEBIDAS` 24.88, `0058` -> `SUPERMERCADO FENIX` 9.82 (rival
`POSTO SANTOS` 9.80), `0063` -> `SUPERMEC SAO JOSE` 10.23 (rival
`GITHUB INC.` 10.00), and August `0000` SARL TRAIN'S 32.00 EUR ->
`PETIT TRAIN TOUR` 37.48 through the masked-BIN fix.

**Deviations from the plan's prediction, all measured, none tuned away.**
July landed exactly as predicted (26 -> 31, review 10 -> 5). August was
predicted "7 -> 8 plus the Petit Train receipt from the masked-BIN fix"; the
actual is 7 -> 8 total, because the Petit Train receipt IS the SARL TRAIN'S
billet `0000` and the gate refinements moved nothing else in August. The
prediction double-counted one receipt. Six bundles 55 -> 70, not 71;
holdout 13 -> 18 of 22, not 19. Train scored 56.8, the predicted figure
exactly.

**The one honest cost, reported rather than netted out.** On the six
bundles, 12 receipts moved `excluded_ambiguous` -> `matched_unverifiable`:
receipts the labeler refused to rule on under the exclusion discipline,
which the matcher now auto-resolves. Every one is a vendor-dominance
promotion onto a charge naming the SAME merchant: `Hotel Giolli Nazionale`
-> `HOTEL GIOLLI NAZIONALE`, `Mega Center Comercio De Materiais De
Construcao Ltda` -> `MEGA CENTE CONSTR` (the truncation the vendor scorer
was built for), `Bella Sky Hotel AP` -> `BELLA SKY HOTEL APS`, `Lagkagehuset`
-> `271 LAGKAGEHUSET`, `NOVOTEL LISBOA` -> `REST NOVOTEL LISBOA` (twice, on
distinct amounts), `FraSec Services GmbH` -> `FraSec Services GmbH / MW`,
and five more of the same shape. None contradicts a label: no `no_charge`
receipt was auto-matched anywhere (`nc_matched` 0 on every bundle) and
`review_no_charge` is unchanged at 30/1/0/0/5/6. The class name means "the
label set cannot verify it", not "the evidence is thin". Recorded because it
is the precision surface a later round would have to re-examine if a wrong
pair ever surfaces there.

**Item 72's live instance is NOT closed, contrary to the plan's guess.**
`0023` (Anthropic 52.59) is still `ambiguous` on August after the change,
byte for byte. The plan expected the spoken-for rule to dissolve its tie
with `0021` on ANTHROPIC 50.52. It does not: "spoken for" lives in the
bilateral-uniqueness gate, and `0023` is stopped by pass-1 AMBIGUITY
detection (`_ties` over deterministic candidates), a different mechanism the
gate never reaches. Extending "spoken for" into tie detection is a real and
probably correct change; it is not in round B's scope and was not made. Item
72's persistence split stays open with its live instance intact.

Suite 1800 -> **1831 passed / 2 skipped** (+31). Four regress proofs, each
green -> RED -> green, one per fix: disabling `if
cfg.uniqueness_spoken_for:` reddens the spoken-for shape AND the route test;
disabling `cfg.uniqueness_vendor_dominance_min > 0.0` reddens the dominance
shape and both keep-side margin cases; disabling the mask check in
`_card_keys` reddens the masked-BIN pin and the flipped round-A test. The
fourth is the wiring proof that matters most: mutating the MATCHER's
spoken-for clause reddens `tools/tests/test_recon_match_attribution_gate.py`,
which can only happen because the tool imports the shared gate rather than
mirroring it. Ruff clean on the diff; `preflight-hooks.py --full` OK (1509
passed, 1 skipped). No SPA change and no Lovable prompt: `reason` is already
rendered verbatim on every candidate.

**Round B shipped (2026-09-15, PR #877, merge `5af6a9a4`, Fly v131, both
live months re-matched through `refresh-master-data` the same evening).**

**What the live re-match did, read off the app afterwards.** July: `n_review`
12 -> 7 and `n_matched` 31, 11 judgments reused, **0 new model calls**;
`n_unmatched_tx` unchanged at 73, because the five receipts that resolved
came out of the review pile, not off the unmatched-charge list. August:
`n_review` 3 -> 2, raw `n_matched` 8 -> 9, 2 judgments reused, 0 new. A fresh
DB copy pulled after the write reads **parity OK with the hosted outcome on
both months**, and its attribution equals the predicted table exactly: July
31 clean / 0 wrong / 0 unverifiable / 5 in review with the correct charge
teed up; August 8 clean / 0 wrong / 1 in review. September was not
re-matched and did not need to be: round B changes matching only, and
September holds no statement.

**A live sighting of item 72, in passing.** August's re-match event reported
`n_unmatched_tx` 99 while the run summary re-derived 100 immediately after.
That is the raw-vs-effective split exactly as item 72 describes it: the
effective layer drops `0023`'s probable pairing because the receipt is
consumed by its tie elsewhere, freeing that charge back to unmatched, while
the committed event counted it. Same for `n_matched` 9 raw vs 8
label-confirmed clean. Item 72 is untouched by this round and its live
instance is intact.

**Which clause carried each pair, off the live API.** Four of July's five
were vendor dominance and one was spoken-for: `SUPERMEC SAO JOSE` 10.23
("Kept deterministic: the rival pairing is spoken for."), and
`Enchilada Karlsruhe` 34.39 (1.00 vs best rival 0.11),
`WILLAMS RONALD DA SIL` 1.97 (1.00 vs 0.05), `SUPERMERCADO FENIX` 9.82
(1.00 vs 0.36), `MP *24HBEBIDAS` 24.88 (0.82 vs 0.27). All five read
`effective_bucket: "reconciled"`, `is_chosen: true`,
`requires_review: false`. August carries no "Kept deterministic" clause at
all, which is the right tell: its single gain came from the masked-BIN fix,
and that pair became uncontradicted rather than rescued from a rival, so its
reason is untouched.

**SPA drive (agent-browser, session `recon-roundb`, `expenses.brisken.com`,
logged in through a script reading the vault so the code never reached the
transcript).** July's workbench renders **RECONCILED 31 / REVIEW 7** (26 / 12
before), and the Jul 13 `Enchilada Karlsruhe` 34.39 row holds its own
receipt, "Enchilada Karlsruhe · 99% · CROSS-CURRENCY · 30.00 EUR", with no
fallback ("No receipt found", "--", a blank cell) in its place. The row's
state column reads "Awaiting decision" with Reject / Confirm match, which is
the reviewer-confirmation state and NOT a fallback: the pre-existing
reconciled rows on the same page (the ANTHROPIC exact matches) read
identically, which is the comparison that rules out the 2026-08-24
consumer-gate failure mode.

**Stated as a split, because it is one.** The reason clause itself was
verified on the authenticated API for all five rows; it was NOT observed
rendering in the SPA. The row's "Details" control surfaced no reason text in
the accessibility tree or in the cell's HTML after clicking and hovering, so
the SPA appears to have no renderer for `reason` at that spot. The changed
STATE is verified in the browser; the changed STRING is verified at the API
only. No Lovable prompt is proposed for it: the clause is explanatory, the
reconciled state is what the reviewer acts on, and inventing a renderer the
owner did not ask for is scope the round does not carry.

**Where item 69 now stands.** Both live months: 0 wrong, 0 unverifiable.
July 51 receipts, 31 matched clean and right (26 before round B, 26 before
round A); August 31 receipts, 8 matched clean and right (7 / 7). The program's
two structural rounds are done and the stop condition holds: the next class
(July's two Google Workspace charges against two identical receipts) recovers
at most one receipt a month, under the three-a-month floor, and the owner
ruled on 2026-09-15 that the reviewer's duplicate ruling there stands. What
remains is coverage, not matching: cards 9693 and 1176 have no statement
loaded, June and September have no statement (item 61), and cash, debit and
bank transfers never post to a card (item 62).

### 70. Changes in a month that did not stick (Criss 2026-09-14, owner report 2026-09-15)

Criss, app feedback 2026-09-14 06:57 UTC, July: "Qdo entro na categoria e
eu coloco a categoria certa, nao acontece nada... permanece sem categoria
mesmo dando refresh." Owner approved the full fix 2026-09-15. Three causes,
audited the same day against the live months:

- **A. A reclassified needs-review row saved and never showed.** `POST
  /api/runs/{id}/categories` stored the override on the candidate receipt,
  but `build_view` resolved `posting_category` from the HELD receipt, and a
  review row holds none until it is confirmed. 12 July rows and 3 August rows.
- **B. On a month with a statement, five expense-edit routes answered 400**
  ("a statement is attached; review this month in the reconciliation
  workbench") through `_mutable_expense_run_or_error`: the field PUT, the
  entity PUT, private, manual add, delete. Both live months have statements,
  so company, category, paid-through and cost center could be set nowhere on
  July or August. Deliberate since item 29's overlay-route round: a re-match
  bakes the overlay into the pool, so the surface waited for reversible edits
  (PR #628) and the re-match an edit has to trigger.
- **C. Reclassify half-applied.** The SPA always sent `line_index: 0`, so a
  33-line Lidl receipt read two categories, and it sent no account, so the old
  one survived (iCloud: "Software & Subscriptions" booked to the account
  chosen for "Utilities & Premises"). The grid's PUT category path carried the
  stored account the same way.

**Shipped (branch `client/brisken/p1-month-edits`).**

- B: the refusal gate is retired; all five routes take the edit all month and
  reply through one helper that runs `rematch_after_change` (trigger
  `expense_edit`) off the event loop, after the edit is committed, with its
  result or error under `rematch` (absent when nothing re-matched). Every other
  validation stands.
- **The re-match field list, from the matcher, not from intuition:**
  `match_month`, `reference_match` and `matching/judgment.py` read
  detected_date, detected_total, detected_currency, detected_vendor,
  detected_reference and legal_entity_id (plus payment_mode, which no edit
  writes). So a re-match follows `vendor`, `date`, `total`, `currency`,
  `reference` (when the value changed), a changed `legal_entity`, a manual
  add and a delete. Differs from the brief twice: `reference` IS in the list
  (a tie-break the matcher reads), and `private` / `reimburse_to` are NOT
  (the card chain derives a row's entity from override / card / stamped value
  and never from the private flag, so confirming a private expense moves no
  pairing). Never: category, zoho_account, tax, tax_label, paid_through,
  cost_center, customer.
- **The reversibility hole the reopening exposed, fixed:** `rematch_month`
  baked from the snapshot pool, which is already baked, so a CLEARED edit left
  the old value in the matcher's pool (measured before the fix: total edited
  to 99.99 then cleared, grid 42.50, pool still 99.99, charge unmatched). It
  now bakes from `baseline_receipts(run)`. Two supporting changes:
  `apply_expense_edits` rebuilds a baked manual add from its payload in place
  (a manual add edited before its first bake had no baseline to revert to),
  and a manual re-attach drops the superseded file's baseline entry.
- A: a review row holding no receipt resolves `posting_category` from the
  candidate carrying a reviewer category edit, else `candidates[0]` (what the
  SPA's Confirm takes), and carries `posting_category_proposed: true`, absent
  everywhere else. Readiness, `resolve_review` and every count unchanged; the
  reconciliation PDF leaves its posts-to column blank on such a row.
- C: `line_index` absent or null reclassifies every line of the receipt
  (resolved from the effective set, 404 for an unknown receipt); an explicit
  int keeps the per-line edit. **Account rule:** no deterministic category ->
  account map exists (`EXPENSE_CATEGORY_ROOT_GROUP` names a root group, not a
  postable leaf; registry and memory are per merchant), so a changed category
  keeps no account: an override inherits the line's own account only when it
  keeps the line's category (read time, `apply_overrides` and
  `_row_posting_category`), and a category edit without an explicit account
  stores none unless the category is unchanged (both routes). The export then
  books the row to the category label with no chart wired and to `(account
  unmapped - assign)` with one, never a guessed account. Rows whose stale
  account was already baked into a live month's pool correct at that month's
  next re-match (the bake now starts from the baseline); the expense CSV reads
  the baseline and is correct at once.

**Evidence.** Suite 1724 -> 1746 passed (2 skipped), calibrate exit 0, ruff
clean on the diff. `tests/test_month_edits.py` (21, all through the routes)
plus a contract pin in `tests/test_view_contract.py`; the closed-door pins in
`test_living_month.py` and `test_web_expense_lifecycle.py` now pin the open
door. Seven regress proofs, each RED first with the right failure: route
refusal re-added (400 "a statement is attached"), re-match call disabled
(8 red, `KeyError: 'rematch'`), bake from the snapshot (the total-revert
test), proposed category off, line 0 only (the every-line test), account
inheritance at read time (3 export tests; the workbench posting test), the
PUT store keeping the old account, and the manual add not rebuilt. SPA half
`docs/lovable-month-edits-prompt.md` (owner applies).

**Closed 2026-09-16.** Backend shipped PR #870, Fly v129. The SPA half was
published and driven live: August's Review expenses has no disabled control
left, View receipt opens there, and a tax-label edit on a statement month
(`0025__Invoice-H0LHY2WQ-0032.pdf`, `TEST-0916`, reverted) answered 200 and
survived a full reload. Evidence row in `PROMPT-STATUS.md`. Found on the way,
recorded as item 78: a category cannot be cleared once set.

### 71. The card list at the top of a month buries the work (owner, 2026-09-15; SPA prompt written)

**Owner:** "the card list at the start of a month's page makes everything
harder to overview; come up with something better." Measured on the live
pages at 1440x900 (read-only drive, 2026-09-15):

- **Workbench `/runs/{id}`**: "Coverage by card" is 9 rows on both months
  (July 4 with charges and 5 "nothing loaded yet"; August 3 and 6), 424px,
  plus a Statements box (one file each, no advisory, the same download the
  summary bar already offers). The first charge row sits at y=1563 (July),
  about 1.7 screens down under the 301px sticky header.
- **Review expenses `/expenses/{id}`**: the same two panels plus the card
  review strip, 941px on July (11 groups, 25 receipts) and 673px on August
  (7 groups, 8 receipts). First expense row 2.3 to 3 screens down.
- **What the reviewer decides from it this month: almost nothing.** Every
  card is `known`, `n_charges_no_entity` is 0 on both months, 24 of July's
  25 strip receipts and all 8 of August's are `suggested_private` (a
  decision the rows already offer). The one real signal is August's: cards
  1176 (Consulting) and 9693 (Cloud Services) have 2 receipts each in
  `card_review.resolved[]` and no charge on any loaded statement, and the
  table renders those two exactly like the four cards that have neither.

**Found on the way, live:**

1. The Card filter's option counts are all the month total ("112" on every
   card, including five with no charges): `countWith(patch, skip)` in
   `RunWorkbench.tsx` applies the option and then skips the same dimension.
   `lovable-workbench-filter-sort-prompt.md` had been marked applied by
   bundle grep only; this drive is its first behavioral check.
2. The strip prints "Card ending 42463153" for the hint
   `42463153XXXXXX38`, whose ending is 38 (item 35's canonical grouping
   half, still open, and the same masked-BIN shape item 69's round B fixes
   in the matcher's `_card_keys`).
3. The strip's "no card number readable" private note appears under units
   that carry a card number (2544, 9129).

**Owner pick (2026-09-15): card chips + an action-only banner.** Coverage
becomes a chip row in the filter bar (`3876 · 48`, empty cards folded behind
one link), the statements box becomes one line unless there are several
files or an advisory, a banner renders only for a card the month did not
know, a card with receipts but no charges, or charges without a company, and
the strip collapses to one line. SPA only; every field was read off the live
payloads first. Prompt: `docs/lovable-card-chips-prompt.md` (PROMPT-STATUS,
Not applied), with four browser checks to run after the publish. Optional
backend nicety, not built: a per-card receipt count on `coverage[]` would
spare the workbench the batch fetch the banner needs.

**Closed 2026-09-16.** Published and driven live; all four checks pass (the
evidence row is in `PROMPT-STATUS.md`). One residue for item 79: July's first
charge row is 18px under a 945px fold while "How this works" is expanded.

### 72. `rematch_month` persists the raw outcome while the view shows the effective one (2026-09-15, found by the round-A review)

Live instance, August 2026 after the round-A re-match on the DB copy:
receipt `0023` (Anthropic 52.59 invoice, label `excluded`) sits in TWO raw
buckets, a probable match on `6d474e9e8e964bd4` (ANTHROPIC 52.46, 08-03)
and an ambiguous tie on `c632cb75a5098253` (ANTHROPIC 50.52, 08-03) beside
`0021` (which holds an exact match to 51.38). `rematch_month` commits the
RAW outcome: `summary.n_matched` 8 counts the 52.46 pairing, the
`rematch_log` event carries the same counts, and `receipt_claims` is synced
from the raw matches (`effective_settlements` over `outcome.matches`, so
`0023` -> 52.46 is a claim). The effective layer (`apply_decisions`, which
`build_view` and `charge_states` read) drops that match because the receipt
is consumed by the tie on the other charge, so the workbench, the coverage
panel and the reconciliation PDF show 52.46 as "no receipt" with
`chosen_document_id` null while the persisted numbers say it is matched.

Which SPA-facing surfaces read which layer (read off `app.py` /
`service.py`): `GET /api/runs/{id}` and the reports build from
`build_view` (effective); the months list (`GET /api/expense-batches`,
`batch_list_summary`) re-derives only `n_expenses` / `n_receipts` /
`n_categorized` and serves the stored `n_matched` / `n_review` /
`match_rate` (raw); `GET /api/operator/state` `rematches[]` is the
persisted `rematch_log` (raw); `receipt_claims` (the cross-run settlement
protocol, R4) is raw. A month can therefore list as further along than its
own workbench says.

Cause and fix pointer: round B extends "spoken for" to tie detection (a
tied deterministic candidate whose receipt holds an EXACT candidate on
another charge does not tie), which resolves this instance (`0021` is
spoken for by 51.38 -> no tie on 50.52 -> `0023` -> 52.46 deterministically).
The persistence split itself stays open here: the commit should persist
the effective outcome, or the list / log / claims should read the effective
layer; decide which when round B lands and the instance is gone.

### The 2026-09-15 feedback wave (7 notes, read off `/feedback.jsonl`)

The in-app widget has collected 42 notes since 2026-07-15. Seven were left on
2026-09-15 (six on July `50622baec444`, one on August `074a7b8905d7`), and the
whole file was read for the first time that evening. Notes #36 and #35 are
already answered by items 71 and 70 and are waiting on a Lovable paste, not on
code. Note #34 (2026-09-10) is the report item 27 was parked on and nobody saw
for five days.

One cause runs through the rest: **the tool states conclusions it has not
established, and asks about the ones it has.** It auto-commits pairs whose
vendors disagree, demotes pairs it already solved, calls a card payoff a
refund, and calls two real charges one duplicate. Every label prints as fact
rather than as a claim with a basis, so the reviewer cannot tell which of the
tool's statements to trust.

Owner decisions, 2026-09-15: apply item 71 as written; clean rows confirm
themselves but only AFTER the precision work; delete charge-side duplicate
detection; honest labels are the first round. Items 73-75 are that first round,
76 and 77 follow. Ranking rule holds: wrong money beats wrong text.

**2026-09-16: notes #43-46 planned into this wave.** Four more notes on July,
read 2026-09-16 (the store now holds 46). #44 (date mismatch on a one-day gap)
is item 80; #43 (show the conversion at our rate) is item 81, with the per-month
rate as item 82; #45 (the tool decides duplicates) and #46 (resolved items leave
the to-do area) amend item 74 as (b) and (d). Amendments also appended to items
23, 76, 77 and 79. Build order: 76 (in flight, nothing added to its scope), then
80 and 81 as two parallel sessions, then 73, 74, 75, 77, then 82. The ruled order
of 73-77 is unchanged. Owner rulings 2026-09-16 are recorded in items 80, 77 and
82; do not re-ask them.

### 73. A statement row has a type; a card payment is not a refund (note #42)

**Criss/owner, July, anchored on `Payment Thank You-Mobile / Corporate
Services`:** "how can this item be 'refund' if you dont even know which card it
was payed with and the criteria for a refund is the fact that it was payed with
by a non company card".

Live: that row is **-9,664.81 USD** with `initial_bucket: "refund"`; August
carries the same shape at -7,823.16. Both are Chase's descriptor for the
cardholder paying down the credit line. Neither is a refund.

`ingest/_common.py:62-73` collapses `payment, return, refund, credit, reversal`
into one `is_credit` boolean; `matching/deterministic.py:1206-1212` puts all
five into `MatchOutcome.refunds`; `web/service.py:2668-2680` renders that as the
bucket the SPA prints "Refund" and `output/report_xlsx.py:744-751` prints
`REFUND`. There is no row-type taxonomy anywhere, and no transfer concept.

Build: a parallel `row_type` on `Transaction` (`purchase | payment | refund |
reversal | fee | interest`), read from the Type column where one is mapped
(item 55 made that mapping exist on xlsx) and falling back to today's sign
inference. **Keep `is_credit`**: it is what the matcher partitions on, and
nothing about matching changes here. Display derives from `row_type`. Exclude
`payment` rows from `month_health.py:107-109`, which currently reads any credit
as evidence of a broken sign convention. Pin `rows[].row_type` in
`test_view_contract.py` and document it in `api-contract.md` (rule 1).

The owner's stated criterion ("refund = paid with a non-company card") is item
41's `suggested_private` rule, which lives on receipts
(`web/service.py:4980-4987`) and never emits "refund". The two mechanisms are
unrelated; say so when this ships rather than silently building something else.

Secondary, same item: a charge row that printed no card inherits the UPLOAD's
entity (`web/service.py:7563-7600`), which is why this payment row reads
"Corporate Services" when nothing identified a card. Carry the provenance so
the SPA can show an inherited entity as inherited.

### 74. Duplicates mean one thing each (notes #37 and #41)

**Owner, July:** "duplicates can only exist as the same receipt injected twice.
otherwise there are no duplicates in the statement since our truth of
transactions with the card is grounded there. If there are 2 from the same
vendor, that is because its true." And, on the Possible duplicates panel: "the
definition of duplicates needs to be defined in a way that only ACTUAL
duplicates appear here".

`duplicates.py` answers three different questions with one key, one group id,
one panel and two buttons. Item 33 defined a duplicate as byte-identical
content; item 56 deliberately re-used the vendor+date+total+currency key to mean
"one purchase, two documents" so a Stripe invoice+receipt pair stops reading as
ambiguous. Those two intents now share everything, so "Real duplicate" is asked
to mean both "this is a redundant copy" and "these two files are one purchase".

**(a) Delete charge-side detection.** Every charge group on both live months is
a set of genuinely distinct transactions: July 4x `COMPUTER` 15.96 (07-21,
07-22), 2x `POSTO SANTOS` 9.80 (07-18, 07-19), 2x `GOOGLE *Workspace` 71.64
(both 07-01); August 2x `OPENAI` 86.06 (08-08, 08-10). Remove
`find_duplicate_charges` (`duplicates.py:118-163`) from the view builders
(`web/service.py:3122-3176`, `:5742-5763`), the payload, the counts and
`output/reconciliation_report_pdf.py:166-210`. Double-ingest is already
prevented by stable transaction identity (item 29), so the detector has no
remaining job. Keep the `kind` discriminator so the SPA does not break; it just
never carries `"charge"` again.

**(b) Finish splitting the receipt side.** Item 69 Round A (#874, merged
2026-09-15, after these notes were left) already built the identity half:
`find_duplicate_receipts_by_reference` keys on `detected_reference` + total +
currency with vendor spelling and date ignored, tags those groups
`basis: "reference"`, collapses them like the others, and lets the kept copy
inherit the card and entity its copies name. That is the right half, and it
covers the invoice-plus-receipt pairs: six of August's nine groups are literally
`Invoice-*.pdf` beside `Receipt-*.pdf`.

What Round A did not touch is the ORIGINAL key, and that is the one these notes
are about. `find_duplicate_receipts` (`duplicates.py:166-186`) still declares a
duplicate on normalized vendor + exact date + `str(total)` + currency, which is
a statement about printed facts rather than about identity, and it is what
collapsed the two Google Workspace invoices. Two changes:

- **Add a content-hash key.** The same document arriving through two channels
  (the Redis invoice and its rendered body; the Anthropic 100 copy; the Petit
  Train slip) is a false NEGATIVE today, because the bytes differ and the OCR'd
  vendor or date differ too. `document_id` already carries `sha1(bytes)[:16]` in
  statement mode but not in expense-batch mode; persist the digest either way
  and key on it.
- **Stop the vendor/date key from declaring a duplicate on its own.** Where a
  reference or a hash is present and DISAGREES, it must not collapse: the two
  Google receipts carry distinct invoice numbers (`5608449734`, `5614551183`)
  and distinct account refs, so the reference key already knows they are two
  purchases. Where both are absent it may still raise a question.
- Everything else is not a duplicate.

And either way the panel stops asking. A collapse established by identity is
reported, not put to the reviewer; that is the whole content of note #41.

**(c) The July Google group is live damage, not a hypothetical.** Group
`03ba84fadeebe2a5` (`0036__...google_com__5608449734.pdf` and
`0037__...brisken_com__5614551183.pdf`) carries `resolution: confirmed`, and a
confirmed group stays collapsed (`web/service.py:9330-9333`), so one of the two
real 71.64 charges on 07-01 can never be matched. Two Workspace accounts, two
distinct Google invoice numbers, two true charges. Reset it with `POST
/api/runs/50622baec444/duplicates/resolve` `{"resolution": "ignore"}`. **Live
write on Criss's data: per-action yes required** (PARALLEL-ROUND-PROTOCOL §3).
The code fix alone does not undo it.

**Amendment 2026-09-16, note #45 (Matthias, July, on Possible duplicates):**
"duplicates should be decided entirely by you. bank statement duplicates means 2
transaction to the same vendor, receipt duplicates need to be compared on date
time amount vendor etc... usually you can tell by comparing receipts".

**(b) as written above would split two true copies.** The line "where a
reference or a hash is present and DISAGREES, it must not collapse" fails on
August: `0008__Invoice-HMVWDWIL-0029.pdf` / `0009__Receipt-2247-1655-6392.pdf`
read `HMVWDWIL0029` vs `2247 1655 6392`, and `0012` / `0013` read
`HMVWDWIL0030` vs `2506 5524`, because a Stripe receipt's own number was read
instead of the invoice's. The labels call both pairs one purchase. Replace that
line with a ladder the tool always finishes, first rung that applies wins, each
recorded as the group's `basis`:

1. `hash`: identical bytes (the digest (b) adds) -> copy.
2. `reference`: equal `reference_key` + total + currency -> copy (exists).
3. `printed_reference`: one document's PDF text layer prints the other's
   normalized reference -> copy. Read live 2026-09-16 through the image
   endpoint: `0009` prints `HMVWDWIL0029`, `0013` prints `HMVWDWIL0030`; the
   two Google invoices do not print each other's numbers; the
   `rendered-body.pdf` files have no text layer, so they fall through.
4. `distinct_reference`: both receipts carry a usable `reference_key` (a till
   counter under the floor counts as absent), the keys differ, rung 3 negative
   -> two purchases.
5. `receipt_card`: the receipts name different cards -> two purchases.
6. `vendor_date`: vendor + date + total + currency with nothing disagreeing ->
   copy.
7. After matching: a receipt set aside as a copy while an exact same-currency
   charge for it sits unmatched on a loaded card is restored and the month
   re-matched once (`basis: statement`). This is the check that catches July's
   Google pair from the other side.

Measured on the 16 receipt groups the two live months carry (July 5, August
11), against `labels.csv` + `notes.csv`: 15 are copies and 1 is two purchases
(Google). The ladder reaches the labelled verdict on 16 of 16; today's grouping
calls all 16 duplicates, 15 correctly. Expected rung per group, the answer key
for the build: rung 2 on 10 (July `223358239c9911df`, `7dd5f822b6c9d13d`,
`5409c62362824053`; August `fd07bcd04d462511`, `5274a5300cd27a6a`,
`06dd72881174d4c7`, `620aa2aeda415518`, `be1642db8b72aa99`,
`24c61c428c3e81f0`, `8c9170f68b503742`), rung 3 on 2 (August
`da109dc56459efa7`, `2f898a54812eb117`), rung 4 on 1 (July `03ba84fadeebe2a5`,
distinct), rung 6 on 3 (July `3b0029eea1b11643`; August `2e3ef5581a738121`,
`5c7c063743f32f29`); rung 1 may pre-empt any of them with the same verdict.
(Corrected 2026-09-16 from "15 groups", a miscount.) Rung 5 fires on none of
the 16 ahead of an earlier rung: every copy pair names one card or none
(`payment_mode` read 2026-09-16). Time of day decides none of the 16;
it would only separate two photographed POS slips with no usable number, and the
one live instance (Aposto `0029`/`0030`, till counter `4563` below the floor) is
a true copy that rung 6 already gets right. Time of day joins item 77's prompt
change (owner ruling 2026-09-16, recorded there); this ladder never requires it.
The reviewer is no longer asked; "Not a copy" remains as an undo that writes a
reviewer verdict.

**(d) new, note #46 (shared operator code, Portuguese, July, anchored on
`Duplicate charges (4) / Real duplicate / Not a duplicate`):** "Acoes resolvidas
deveriam ser retiradas da area que constam para ser removidas." Live 2026-09-16:
July's panel lists three resolved groups (`4bc95012abf2bfb5` ignore,
`3b0029eea1b11643` and `03ba84fadeebe2a5` confirmed) beside five open ones, and
the SPA only dims them (`opacity-75`) with both buttons still live
(`RunWorkbench.tsx` duplicates panel). The anchor itself is the unresolved
4-member COMPUTER group, whose rows are all `entry_status: subscription`, so
"resolved" may mean clicked or already booked; the design below covers both.
The note came from the same IPv6 /64 as the owner's notes #41-45, so the author
is not certain.

- Backend: `duplicate_groups[]` gains parallel `state` (`open` | `decided`),
  `decided_by` (`tool` | `reviewer`), `verdict` (`copy` | `distinct`), and
  `summary.n_duplicate_groups_open`. `resolution` keeps its meaning
  (`confirmed` -> copy, `ignore` -> distinct, `decided_by: reviewer`).
- Every group stays in the payload. The SPA pairs `duplicate_groups` with
  `duplicate_charges` / `duplicate_receipts` BY INDEX within a kind, and round A
  regress-pinned that alignment; filtering decided groups out of one list would
  mislabel rows.
- SPA half, folded into 74's one Lovable prompt (no interim prompt): the panel
  becomes "Copies set aside (N)", collapsed; open groups (none expected after
  (b)) render as today; decided groups render as a record with the basis and a
  "Not a copy" undo.
- Proof: route-level in `tests/test_web_duplicates.py`; regress by forcing
  `state` to `open` at its wiring point. `test_view_contract.py` gains
  absent-or-enum-never-null tests for the three scalars (pattern:
  `test_duplicate_group_basis_is_absent_or_reference_never_null`).
- Live check after deploy: both months read `n_duplicate_groups_open` 0. The
  Google group stays wrong until (c)'s reset, which keeps its own per-action
  yes.

### 75. The Unmatched list says why (note #40)

**Owner, July, anchored on `Unmatched73`:** "receipts from this month inserted
by general receipt injection function in the tool or per email should be matched
to the receiptless items in the month automatically".

**They already are.** Every arrival path funnels through
`add_receipts_to_expense_batch` (`web/service.py:8204-8272`), which calls
`rematch_after_change(..., trigger="receipts")` unconditionally at `:8256-8264`:
the in-app upload (`app.py:3148-3196`), the receipts drop (`app.py:3198-3253` →
`intake_mail.py:3807`) and email intake (`intake_mail.py:1843`). The pool is the
whole month, not a delta (`baseline_receipts(run)`, `web/service.py:9264`), and
it explicitly includes charges already sitting in Unmatched. The app has no
manual "re-match" button because it needs none.

So the note is not about a missing trigger. It is about a list that does not say
what it contains. Measured on the live payloads:

- **8 of August's 17 unmatched receipts and 3 of July's 14 are collapsed
  duplicate copies** whose twin is reconciled, put back into
  `unmatched_receipts` by `web/service.py:9390-9397` so the reconciliation
  invariant holds. They read as misses.
- Of the remainder, **only 2 per month have an exact same-currency amount twin
  among the unmatched charges**. The rest were never card charges on a loaded
  statement: Redis 13,200 and Konsultancy 15,972 are bank transfers, the German
  EUR receipts are DEBIT/EC, and cards 1176 and 9693 have no statement loaded.

Build: a parallel `reason_code` per unmatched receipt, from facts the payload
already holds. `duplicate_copy` · `card_statement_not_loaded` ·
`not_a_card_charge` · `charge_in_neighbouring_period` (item 61) ·
`no_charge_on_any_loaded_statement`. Same on the charge side. "Unmatched 73"
then resolves into a short actionable list plus a long explained remainder.
Item 69 already classifies these receipts exactly this way in its attribution
table; this puts the same classification on the screen.

Residue, not built: a re-match happens silently. Item 58's notification is
dev-facing (`/api/operator/state` plus an email). The reviewer has no way to
tell "the tool tried and found nothing" from "the tool did not try".

### 76. Reconciled means reconciled, and clean rows confirm themselves (notes #38, #39)

**Owner, July, on `Awaiting decision`:** "why do you need manual confirming on a
date, vendor and amount match?" And on the `Reconciled26` header: "things that
are reconciled and there are no mismatches should not need confirmation."

Three separate mechanisms wear that label, and the tool is wrong in both
directions at once.

1. **It auto-commits on evidence that excludes the vendor.** The `EXACT` tier
   (`matching/deterministic.py:642-661`) is amount + date ±1 + currency; the
   vendor is not consulted. Live August: `BASE44 50.00 2026-08-22` took
   `0025__Invoice-H0LHY2WQ-0032.pdf` (Lovable Labs) as `match_type: "exact"`,
   `confidence: 0.99`, `requires_review: false`, `vendor_pct: 40`, reason
   "Exact amount, date within 1 day(s), same currency". Item 63 (#829) added a
   vendor floor to the PROBABLE band (`_same_currency_band_allowed`,
   `:529-552`); EXACT has none.
2. **It demotes pairs it already solved.** All 12 of July's review rows are
   `fx_judgment`, and **7 carry `vendor_pct: 100` with `date_pct: 100`**
   (POSTO SANTOS x2, POSTO ARCA DE NOE, SUPERMERCADO FENIX x2, Enchilada
   Karlsruhe, WILLAMS RONALD), the amount differing only by the exchange rate.
   The bilateral uniqueness gate (`:1286-1358`) strips a clean rate-derived
   pair of its auto-resolution when any rival clean candidate merely EXISTS on
   either side; the rival need not be better or even plausible on vendor. The
   row's own reason says it: "another charge or receipt agrees just as cleanly".
   Item 69 counts 10 of July's 11 review receipts with the correct charge
   already at `candidates[0]`.
3. **"Reconciled" is not "no mismatches".** `PROBABLE` (amount up to 20% off)
   and `POSSIBLE` (receipt has no date) land in `outcome.matches` too
   (`:1279`, `:1393-1396`), so they render in the Reconciled section carrying
   `requires_review: true`. Three August rows are exactly that, and reconciled
   `vendor_pct` runs down to 22. Item 69 measured August's 14 "clean" as 7 right
   and 7 not.

And `rows[].status` is `pending` on **all 223 live rows**, so the SPA prints
"Awaiting decision" on finished work as readily as on real questions. Same shape
as item 60: the backend was right and the label was wrong.

Build, and only after the round-2 precision work lands, because auto-confirming
August's present reconciled set would bless 7 wrong rows:

- A row confirms itself when `effective_bucket == "reconciled"`, the chosen
  candidate has `requires_review: false`, and `review.state == "ready"`. The
  selection already exists as `ready_confirm_pairs`
  (`web/service.py:2499-2520`) behind `POST
  /api/runs/{id}/decisions/confirm-ready` (`web/app.py:2418-2459`).
- Record that a row was auto-confirmed and by which rule, so it can be found and
  reversed.
- Give the SPA a field that separates "nothing to do" from "your turn", instead
  of deriving the label from `status == "pending"`.
- Move `PROBABLE`/`POSSIBLE` rows carrying `requires_review: true` out of
  Reconciled. That is a precondition, not a nicety.

Worth stating when this ships: confirmation buys less than it looks like today.
`export_approved_only` defaults to `False` (`web/store.py:140`), so unconfirmed
clean rows already flow to the Zoho journal; the sign-off gates only the "Ready
to post?" tile.

**Owner rulings 2026-09-16:** work items 73-77 as one wave in order, 76 first,
each shipped and deployed on its own; auto-confirm is **exact pairs only**.
Do not re-ask either.

**Measured 2026-09-16 on the live API, before any build.** The build as
written above no longer matches the data, so read this first:

- **The precondition is met.** Round B landed, and `requires_review` is false
  on every reconciled row on both months (July 0 of 31, August 0 of 8). The
  last bullet above (move PROBABLE/POSSIBLE out of Reconciled) has nothing
  left to move today; keep a test that pins it.
- **The ceremony is 13 rows, not 223.** `n_undecided` counts pending rows in
  reconciled or review that are not posted: July 3 (28 of its 31 reconciled
  rows are already posted and block nothing, `review.state: none`), August 10.
- **"Exact pairs only", read literally, auto-confirms 6 of the 13 and one of
  the six is this item's own bug.** Literal rule: chosen candidate
  `match_type: exact`, `requires_review: false`, single candidate,
  `review.state: ready`. July qualifies WEB*NETWORKSOLUTIONS 7.98 (vendor_pct
  46), ELEVENLABS.IO 5.00 (75), ANTHROPIC 50.54 (100); August LOVABLE 15.00,
  LOVABLE 25.00, ANTHROPIC 51.38 (all 100). The 46 is mechanism 1 above: an
  exact pair on amount and date with the vendor disagreeing.
- **Working rule, therefore: the literal rule plus vendor agreement.** That is
  the faithful reading of the ruling, since the item's first finding is that
  vendor-blind EXACT is wrong. Cost: July clears 2 of 3 instead of 3 of 3.
  The owner can drop the floor to clear July fully; the threshold (75 vs 80)
  is still to set against the six rows above.
- **The labelling half is probably the larger win.** `rows[].status` is
  `pending` on all 223 live rows, so posted work prints "Awaiting decision" as
  loudly as the 13 rows that are the reviewer's turn. That half changes no
  sign-off and should ship regardless of the auto-confirm threshold.
- `ready_confirm_pairs` (`web/service.py`) is the existing selection to build
  on, but `review.state == "ready"` is a CATEGORY verdict
  (`_matched_category_review`), not a match-quality verdict, so the match
  test has to be added beside it, not assumed from it.
- Sequencing: item 79 (the month page restructure) is an IA change that sits
  under 73-77; settle its order before building this.

**Note 2026-09-16 (note #44, matcher half): EXACT's date window stays at one
day.** Nothing is added to this item's scope; the label half of #44 is item 80.
Across 141 confirmed label pairs on eight statement months (the six bundles plus
July and August), the charge's Transaction Date equals the receipt date on 124
and is within one day on 136; only five fall outside, and `PROBABLE` already
reaches five days. Widening `date_exact_window_days` while `EXACT` ignores the
vendor would add wrong automatic matches of the BASE44/Lovable shape. Reopen
only if a labelled month shows more than 5% of confirmed pairs outside one day
after this item's vendor floor is live, measured with the S1 scorer.

### 77. Dates read in the source locale, and a corrected date moves the receipt (note #34)

**Criss, 2026-09-10, batch `4ceaeb461386`, anchored on `2026-01-04`:** "A leitura
da data está errada. Em Portugues usamos dd-mm-aa ou aa-mm-dd."

This is the report item 27 was parked on ("Still parked until Criss reports one"),
and it arrived five days before anyone read it.

Live state of that batch: it is labelled **"January 2026"** and holds exactly one
expense, `20260704_Receipt_Food_ParadaObrigatoria.pdf`. The filename says 4 July.
`date` now reads `2026-07-05` with `edited_fields: ["date"]`, so the date was
corrected by hand; the receipt is still in the January batch and the label still
says January.

Two defects, and the second is the expensive one:

- **The locale prior.** Criss is describing the source convention: Brazilian and
  German receipts print day-first. Item 25 fixed a year-reading class by
  tightening the prompt and MEASURING (6 of 11 moved, 24 of 25 byte-identical);
  do the same here against the receipts already on the volume rather than
  assuming. Item 27's residue is the same class: `receipt_12` reads 2026-04-22
  against a printed 02/04/2026, `receipt_34` reads 2026-04-23 against 21/04/2026.
- **A misread date misfiles the receipt, and correcting it does not move it.**
  `batch_period` judges a date against the batch's month plus two neighbours, so
  a July receipt read as January passed the January guard, created or joined a
  January batch, and stayed there after the correction. When an edit moves a date
  outside the batch's window, offer the move and carry it out; every edit route
  already runs `rematch_after_change` since item 70.
- Fix the live January batch once the behaviour exists. Live write, per-action
  yes.

Item 27 noted that better year reading makes this class harder to see, not
easier: an error that used to land in 2023 and trip the guard now lands in the
right month. That trade is now real rather than predicted.

**Amendment 2026-09-16 (note #45), owner ruling: bundle three extraction fields
into this item's prompt change.** `_EXTRACT_SCHEMA` (`llm/client.py`) gains
`time` (HH:MM as printed, or null), `invoice_number` and `receipt_number` beside
`reference`, in the same prompt edit, so the reading cache takes ONE fingerprint
bump and the stored receipts ONE measurement run, not two. The locale
measurement already has to re-read what is on the volume. Item 74's duplicate
ladder may use the fields once present (a different printed time on two
same-vendor, same-day, same-amount slips -> two purchases; a receipt whose
`invoice_number` equals the other document's number -> copy) and never requires
them. Time of day cannot help charge-to-receipt matching: Chase exports carry no
time (recorded by the 2026-07-23 accuracy program, PRs #404-#406). Report in the
measurement how many stored readings changed outside the three new fields.

### 78. A category cannot be cleared once set (found 2026-09-16, driving item 70)

The category dropdown on Review expenses offers the eight categories and no
blank option, so a row that has a category can be recategorized but never put
back to "Pick a category". Found when a reversible edit test on August's
uncategorized `0025__Invoice-H0LHY2WQ-0032.pdf` had to move to the tax-label
field instead. Three August rows are uncategorized today (Pressmaster FZCO
135.00, two Lovable Labs 50.00 copies), so a mis-click on any of them is
permanent from the UI. Check first whether the field PUT already accepts an
empty category (then this is SPA only, one Lovable line: a "Clear category"
option), and how a cleared category interacts with the item-70 account rule
and with learned memory.

### 79. A month's page is structured by what the reviewer is looking at (owner direction 2026-09-16)

**Owner, verbatim:** "A month's page needs to be structured differently. A user
needs overview and visibility of the following: 1) the expenses that were
created just with receipts; 2) (if a statement has been attached) a separate
overview of the transaction-expense matching. The transactionless receipts,
receiptless transactions, needs-review, refund should all be ordered in their
respective overview pages."

Today the four classes share one workbench page as sections plus a side list:
transactionless receipts = UNMATCHED RECEIPTS (and all of Review expenses on a
month with no statement), receiptless transactions = Unmatched, needs review =
Needs review, refund = Refund. Planning only so far; the self-contained
planning prompt was handed to the owner on 2026-09-16 (walkthrough first in
plain language, technical appendix second, owner decisions as questions). It
is an information-architecture change underneath items 73-77, so the first
decision is whether it ships before that wave or after it. Nothing built, no
Lovable prompt in `docs/`.

**Design constraint 2026-09-16 (note #46):** every action list on the
restructured pages (transactionless receipts, receiptless transactions, needs
review, refund, duplicates) shows open items as the work and moves decided ones
(confirmed, posted, settled outside, copy set aside) to a collapsed record with
an undo. Item 74(d)'s `state` / `decided_by` shape is the model. Items 80 and 81
change single cells and do not depend on this item's order; if this item ships
before 74, 74(d)'s SPA half goes into this item's duplicates page instead.

**Planned and approved 2026-09-16; SPA prompt written, not pasted.** Grounded on
the live API (July, August, September), a read-only browser drive of the
published app, the backend code and SPA main `c9f30bf8b5`. What the drive found
that the item text did not have:

- The two pages are joined one way only: Review expenses links to the workbench,
  the workbench links back to nothing but "Menu" and a "Dashboard" link to the
  old upload form at `/`, and `/months` sends every statement month to `/runs`.
  July's and August's Review expenses page is reachable only by URL.
- `/runs/{id}` crashes ("This page didn't load") on every month without a
  statement (September, June, May, January): the backend correctly serves the
  expense payload there, and `RunWorkbench.tsx` reads `data.rows.length`
  (FilterBar `totalRows`) and `data.unmatched_receipts.length` unguarded.
- July has 85 of 112 charges posted in the workbook (49 unmatched, 28
  reconciled, 7 review, 1 refund), rendered as open work, while the "Posted"
  bucket chip reads 0 and cannot be turned back on once off.
- The thirteen-tile bar pins 301 of 900 px; the workbench is 12,000 to 15,000 px
  tall with every section stacked.
- Six Category cells print `expx.review.badge.short.override; llm` and similar:
  not a missing key (both key sets exist), `SourceBadge` keys on the
  `"; "`-joined `posting_category.source`.

**Decisions taken with the approved plan** (the recommendation on each owner
question; reopen any by saying so): (1) two routes kept, one shared month strip
with tabs Expenses / Matching on both; (2) `/months` link rule unchanged; (3) one
view at a time; (4) the owner's order, receipts without a charge, charges
without a receipt, needs review, credits, then Matched fifth; (5) decided rows
stay in their view, folded, whole counts on the cards plus "N open"; (6) the tile
bar retires into the cards, a status line and >0-only captions, match rate leaves
the screen, only Menu and the strip stay sticky; (7) card 4 is "Credits on the
statement" until item 73; (8) restructure first, not gated on 76, and 76 first
in the wave per the owner ruling recorded under item 76; (9) no per-receipt
match column on Expenses yet: a five-count line instead, the parallel
`expenses[].reconciliation` field after 76; (10) item 23 round 4 as its own
prompt; (11) two small backend fields alongside (below); (12) `/` and
`/expenses` untouched here; (13) no "Confirm all ready" button before 76; (14)
no Matching tab on a trip; (15) on a statement month, overview 1 is the whole
Expenses view and its no-charge subset is card 1 of Matching.

**The SPA half:** `automations/expense-reconciliation/docs/lovable-month-views-prompt.md`.
It applies the design constraint above with today's fields: a copy set aside
(`duplicate.is_extra`), a settled-outside receipt (`expenses[].settled_outside`),
a posted row (`section === "posted"`) and a confirmed or already-posted row
(`status`) fold into a collapsed record with the existing undo; a `rejected`
row stays open. Duplicate groups with a `resolution` fold the same way,
partitioned at render time only (the index pairing stays intact); when 74(d)
ships `state`, its prompt swaps the test. **For item 76's session:** this prompt
leaves `RowStatusBadge` and the Status cell untouched and says so, so write
76's SPA half against the five cards (the Matched card's rows and the pill),
not against today's bucket sections.

**Backend alongside, SHIPPED 2026-09-16 (PR #900, Fly v133):** a real top-level
`updated_at` on both payloads (the "Last updated" line printed the creation
date: September read Sep 07 while its last receipt arrived Sep 16), and
`candidates[].held_by` widened to receipts held by a pending review row (August
`6d474e9e8e964bd4`, ANTHROPIC 52.46, showed candidate `0023` with no holder
while `c632cb75a5098253` held it, and `n_charges_receipt_taken` read 0). Suite
1832 -> 1844, every wiring point regress-checked red first. Live after deploy:
August `n_charges_receipt_taken` 1 with `held_by` naming `c632cb75a5098253`;
`updated_at` present on both payloads of all three months. Consumer driven,
before any prompt paste, because the published SPA already renders both
fields: September's Review expenses reads "Last updated: Sep 16, 2026, 01:37
PM", and August's workbench row reads "Receipt is on another charge ·
ANTHROPIC · 50.52 USD · Aug 03, 2026" with WAITING ON A PICK 1, no console
errors. Known limit, recorded in `api-contract.md`: clearing a field edit
deletes its row, so `updated_at` can read earlier than that clear.

**Prompts shipped to `docs/` (PR #899), not yet pasted:** the owner pastes
`lovable-month-views-prompt.md` and `lovable-journal-callers-prompt.md` in
either order; each carries its own bundle signatures and drive checks, and
PROMPT-STATUS lists both as Not applied.

**Open, and not blocking the paste:** PT wording of the new keys (Criss's read
is the check); whether "ordered in their respective overview pages" meant the
listed sequence or only "organised into" (any card is one click away either
way); the first-row pixel position after the trim (the drive measures it).

### 80. A one-day gap is not a date mismatch (note #44)

**Matthias, July, on the `date mismatch` chip of ANTHROPIC 47.23:** "happens
often because transactions sometimes take a while to get processed in the bank.
do research to find the green zone on how much time differing is typical."

The chip is SPA-derived: `getRowWarnings` (`RunWorkbench.tsx`) pushes "date
mismatch" when the chosen candidate's `date_pct` is below 99, which is any gap
of one day or more, and the chip also counts toward the Warnings filter. The
named pair is `exact` (receipt 07-13, charge 07-14, `date_pct` 80). Six July
rows carry the chip, all reconciled and all correct by the labels (AMAZON,
MP *24HBEBIDAS, GOOGLE Workspace, three ANTHROPIC top-ups); every one of July's
38 candidates sits 0 or 1 day from its charge.

**Evidence, internal.** The Chase parser matches on `Transaction Date` and keeps
`Post Date` as `posting_date` (`inspect.py` `guess_column_map`). Over 141
confirmed label pairs on eight statement months, charge Transaction Date minus
receipt date: 0 days 124, +1 9, -1 3, -3 2 (one is MSFT 4.26 USD against a Hotel
Ibis 4.00 EUR receipt, very likely a wrong label), +5 and +6 one each (MEGA
CENTE CONSTR, Zoho-era dates), +14 one (Namecheap, May). Post Date minus
Transaction Date: 0 days 7, 1 day 94, 2 days 26, every 2-day case starting on a
Friday. The processing lag the note describes is real and lives in Post Date,
which the tool does not match on. The one-day Transaction-Date cases are
midnight and time-zone boundaries (Anthropic receipts, a late bar tab in Brazil,
Google's 06-30 invoice charged 07-01) and Amazon charging at shipment.

**Evidence, external (fetched 2026-09-16).** Visa Core Rules (Apr 2026):
"Transaction Date: The date on which a Transaction between a Cardholder and a
Merchant or an Acquirer occurs", e-commerce "on or after the date on which the
goods are shipped"
(https://usa.visa.com/dam/VCOM/download/about-visa/visa-rules-public.pdf).
Mastercard Transaction Processing Rules (Moneris-hosted copy; mastercard.com
returned 403): the DE 12 date is the exchange of goods, shipment, hotel checkout
or ticket issue; presentment within 7 calendar days
(https://www.moneris.com/-/media/Files/Terms-and-Conditions/Card-Brands/Mastercard/Mastercard-Transaction-Processing-Rules.pdf).
Chase: "The transaction date is when you make a purchase ... the posting date is
when your credit card issuer processes this transaction", a Saturday purchase
may post Monday or Tuesday
(https://www.chase.com/personal/credit-cards/education/basics/how-to-track-credit-card-spending).
Amazon charges at shipment, multi-item orders "after all items have shipped or
five days after the order date, whichever occurs first"
(https://www.amazon.com/gp/help/customer/display.html?nodeId=GCSEVDU4VHLPD4VX).
Stripe attempts invoice payment one hour after `invoice.created`
(https://docs.stripe.com/invoicing/integration/workflow-transitions). Weekends
and Fed holidays move Post Date, not Transaction Date
(https://federalreserve.gov/aboutthefed/k8.htm). No primary source gives a
typical lag per merchant class; per-class figures are inference from these
rules.

**Owner ruling 2026-09-16 (do not re-ask):** gap = charge Transaction Date minus
receipt date, calendar days. -1..+1: no signal. +2..+7: a neutral note, "charged
N days after the receipt". -3..-2: a neutral note, "receipt dated N days after
the charge". Beyond either: "date mismatch". The matcher does not change (item
76's note).

Build, the label only:

- Backend: every `rows[].candidates[]` entry gains parallel `date_gap_days`
  (int, signed) and `date_gap_zone` (`none` | `lag` | `mismatch`), both absent
  when either date is missing. The zone bounds are one module constant in
  `web/service.py` with the evidence in its docstring, not a matcher tunable.
  `date_pct` and every score are untouched.
- SPA prompt: `getRowWarnings` reads `date_gap_zone`. `mismatch` -> "date
  mismatch" (a warning); `lag` -> neutral chip, EN + PT for both directions (not
  a warning); `none` -> nothing; field absent -> today's `date_pct` rule. Ride
  with item 76's labelling prompt if that one is still unpasted.
- Contract: `docs/api-contract.md` candidate section; `test_view_contract.py`
  `test_date_gap_zone_is_absent_or_enum_never_null`.
- Proof: `tests/test_date_gap_zone.py`, route-level through
  `GET /api/runs/{id}`, receipts at 0, +1, -1, +3, -3, +9 days. Regress: the
  zone wiring replaced by the constant `"mismatch"`; the +1 and +3 assertions go
  red.
- Live check: July `86fdc73d70668ccb` reads `date_gap_days` 1, zone `none`;
  every July candidate reads `none`; August's -2 ANTHROPIC 50.52 reads `lag`.
- Regressions to watch: the Warnings filter count drops (July, 6 rows); PT
  wording for a negative gap; a candidate with no receipt date stays absent, not
  `none`.

### 81. The FX block shows the conversion at our rate (note #43)

**Matthias, July, on the FX block of AMAZON 315.56 USD vs the Amazon.de receipt
276.08 EUR ("This match needs 1.143002 USD per EUR"):** "maybe in cross currency
cases show the calculation of what the receipt's amount is in $ using our FX
rate."

Live 2026-09-16: the chosen candidate's `fx` carries `implied_rate` 1.143002
and empty `zoho_rate` / `zoho_converted` / `converted_gap`, because
`_fx_breakdown` (`web/service.py`) fills those from `receipt.base_amount`, and
none of the 83 receipts on the two live months carries one. The tool's rate
(Settings `fx_reference_rates`, EUR:USD 1.162275) appears only inside the reason
string. The SPA already renders a "Receipt is worth" row and a gap line, gated
on `zoho_converted`.

Build:

- Backend: `_fx_breakdown` gains parallel `reference_rate` (string, charge
  currency per receipt currency, same direction as `implied_rate`),
  `reference_rate_source` (`settings` | `statement` | `receipts`, gaining
  `ecb_month` with item 82), `reference_converted`, `reference_gap` (signed, 2
  dp), `reference_gap_pct` (signed number, 2 dp, relative to the converted
  amount, the basis the matcher's deviation uses) and `reference_gap_band`
  (`match` within `fx_reference_match_pct`, `review` within
  `fx_reference_review_pct`, else `outside`). All absent when the pair has no
  rate. The rate comes from the run's frozen config through the matcher's own
  `_reference_rate_for` + `derive_fx_reference_rates`
  (`matching/deterministic.py`), so the fields appear on deploy without a
  re-match. `zoho_*` untouched (item 23 amendment).
- SPA prompt: `FxSummary` reads `276.08 EUR x 1.162275 = 320.88 USD · difference
  -5.32 USD (-1.66%)`, amber when the band is not `match`; `FxPanel` adds
  Reference rate (with its source), Receipt in {currency}, Difference, with
  "This match needs" last. EN + PT. Keep the `zoho_*` conditionals: an
  expense-report PDF receipt still fills them.
- Contract: api-contract `fx` section; `test_view_contract.py` absent-or-typed
  tests for the six scalars.
- Proof: `tests/test_fx_breakdown.py`, route-level: EUR 276.08 receipt, USD
  315.56 charge, Settings rate -> `320.88`, `-5.32`, `-1.66`, `settings`,
  `match`; plus every `fx_reference` candidate's `reference_rate` appears in its
  `reason`, so the screen and the decision cannot drift. Regress: the rate
  lookup at the `_fx_breakdown` call site returns None; the fields vanish, red.
- Live check: July AMAZON 320.88 / -5.32 / -1.66; August ANTHROPIC 247.32 vs
  214.20 EUR -> 248.96 / -1.64 / -0.66; PETIT TRAIN 37.48 vs 32.00 EUR -> 37.19 /
  +0.29 / +0.77.

### 82. A reference rate per month, from the ECB (note #43, owner ruling 2026-09-16)

**One rate per pair, not per month.** `apply_master_data` (`web/service.py`)
copies Settings `fx_reference_rates` into a run's config with `setdefault` at
creation and at statement attach; `rematch_after_change` reads that frozen
config. The reason string's "monthly reference rate" is wording only. July and
August both cite EUR:USD 1.162275, which equals the ECB daily rate of
2026-09-04..10: a September rate applied to both months. The 2026-07-23
self-derived monthly rates (`derive_fx_reference_rates`) cannot fire today: a
configured rate always wins, the Chase export has no FX columns, and no live
receipt carries a Zoho rate.

Measured on July's 17 chosen FX pairs: deviation at the Settings rate 0.70% to
2.93% (the AMAZON pair -1.66%); at the ECB July monthly average 0.05% to 1.41%
(the AMAZON pair +0.11%); mean absolute deviation 1.79% against 0.50%. ECB Data API,
`EXR/M.USD.EUR.SP00.A` and `EXR/M.BRL.EUR.SP00.A`, BRL:USD as a cross rate,
queried live 2026-09-16. Card networks lock the rate at authorization (Visa
since April 2021,
https://corporate.visa.com/en/sites/visa-perspectives/company-news/pay-the-same-exchange-rate-every-time.html;
Mastercard,
https://www.mastercard.com/us/en/personal/get-support/currency-exchange-rate-converter.html),
so the purchase month's rate is the right granularity; a daily rate adds little
at a 3% match threshold.

**Owner ruling 2026-09-16 (do not re-ask):** per month, from the ECB, and a rate
the operator types still wins.

Build: rates keyed by month in the run config, fetched when a month is created or
its statement attached, `reference_rate_source` `ecb_month`, Settings copy no
longer telling the operator to update rates by hand. This moves matcher inputs,
so it ships after 77 and only after a simulation on the six bundles and both
live months with the S1 scorer and guard green; report which July and August
pairs change bucket. Independent of item 79.

## Related but tracked elsewhere (do not duplicate here)

- Merchant name book seed cleanup (merge the MEGA CENTER/CENTRE duplicate
  entries, fix the mislabeled construction-materials category): an owner
  task in the Merchants editor; noted in the status file row "Canonical
  merchant registry". Round 5 adds the non-BRL vendor families the book
  does not know yet: DB AG (one ticket read the "CIV" tariff marker as
  the vendor), Uber (email-forwards read as "Uber Receipts"), Enilive
  (read once as "Enimove").
- Two parked design questions from the r1 feedback round (entity from an
  upload column, currency guessing): status file row "Zoho import headers
  + card-first fix". The third (one merchant, different categories)
  shipped as row 6 below.
- Remaining Lovable halves (confirm-all queue rendering, folder-attach
  picker, paid-through cell): each named in its status file row.

## Shipped (loop history)

| Iteration | What | Why it mattered | Shipped |
|---|---|---|---|
| 45 | `receipt_image_available` is resolved against DISK on both review payloads, by one resolver (`service.receipt_image_file`) gated exactly as the image endpoint gates itself | Item 52's underneath-defect. The field was computed twice: the batch payload read the files and was right, the RUN payload read the SHAPE of the document id (`manual:` / `folder:` / a vision-mapped page). A receipt that arrives by mail or through the drop is `NNNN__name.pdf` and is none of those, so the run payload answered `false` for all 17 unmatched receipts of the live August month while the endpoint served every one of them 200. Latent rather than active (nothing renders that field today) but it is the precise answer a receipt viewer asks for, and a field that lies is what sent item 52's recorded lead at the wrong cause. An id-shape test cannot answer this at all: what the endpoint serves depends on what is on disk, and the two drift the moment a new road into a month is added, which is exactly what the mail intake and the receipts drop were | PR #860, 2026-09-15, DEPLOYED Fly v128 and driven live (the August run payload read 0 of 17 available before the deploy and 17 of 17 after, with the endpoint serving all 17 throughout; the batch payload still carries `source_file` on 31 of 31, so the shared-resolver refactor dropped nothing); suite 1719 -> 1724; both wiring points regress-checked green to red to green; contract section added. The SPA half of item 52 (a View receipt button that does nothing) is NOT this and stays open as `docs/lovable-view-receipt-prompt.md` |
| 44 | A statement upload that parses to no charge at all is refused before the fold, on the job's existing `error` status, and the same guard closes the re-read door where a stored file that recorded rows and now reads none would replace a live month's charges with nothing | Item 51. The drill's file was a valid workbook whose columns mapped cleanly and whose rows read as nothing, which is what a wrong worksheet, a header row below the first row and a rejected date format all look like; the column-map 400 does not catch it, because that guard fires on a MISSING column and this file has every column it needs. Reproducing it through the route found the item understated: the month did not stay put, it graduated to the workbench holding zero charges, indistinguishable on screen from a month that reconciled. Keyed on `n_rows` and never on `n_new`, so the same file arriving twice still lands. One existing test used an empty workbook as the vehicle for a different property ("recorded and empty is not not-recorded"); the refusal makes that state unreachable for a workbook, so it was rewritten to pin the refusal's writeback half, and `statement_anchors` now cites the PDF statement, which is where the distinction still lives | PR #859, 2026-09-15, DEPLOYED Fly v128 and driven live (an empty CSV attached to a throwaway TEST- month came back a job `error` with the new message and left the month untouched; month deleted after); suite 1712 -> 1719; both wiring points regress-checked green to red to green; contract section added; no new field and no SPA half |
| 43 | The two writers that rewrote a period record from a stale copy now commit under `_BATCH_ADD_LOCK` against a fresh re-read (the manual per-charge attach and the bulk receipt-folder ingest, the `rematch_month` commit shape), and no write destroys stored bytes any more: a re-attach archives the file the charge already holds under a versioned name and the snapshot records the replacement (`receipt_files`), a queued-upload replacement archives instead of deleting | Item 66. Both paths read the record, worked for seconds to minutes (vision, then the matcher), and then rebuilt the WHOLE record from the copy they had read, unlocked. A concurrent mail intake, card assignment or re-match was erased with no error on either side, which is the worst shape a data loss can take: the reviewer's evidence for the gap is its absence. The file half was the same defect against bytes rather than rows, in a system whose stated purpose is retaining what arrived. One correction to the item as written: keeping only the same-NAME re-attach from overwriting would have left the different-name case, where both files stay in the glob the image endpoint reads and `sorted(...)[0]` can serve the superseded one, so a charge now holds exactly ONE current file and every earlier one is archived. Four regressions of the real source proven RED first, the interleaving one driven through both routes at once | PR #846, 2026-09-15; suite 1550 -> 1557 (1562 after rebasing onto #828); no payload change, so no SPA half |
| 42 | A receipt settled outside the card leaves the reconciliation pool without leaving the month: `POST`/`DELETE /api/runs/{id}/receipts/{doc}/settled-outside` (`how` = bank_transfer / cash / paypal / other, plus a note), counted by `summary.n_settled_outside` on both payloads, carried on the grid row as `settled_outside {how, note, at}` and suggested (never applied) as `unmatched_receipts[].suggested_settled_outside` | Item 62. July's Redis 13,200.00 USD, Konsultancy 15,972.00 EUR and 360Crossmedia 900.00 EUR invoices were paid by bank transfer, so no statement line will ever settle them and they sat in the pool, the counts and month health's pair scan forever. Bookkeeping, not matching: applied at VIEW time from a snapshot key, so it costs no model call and the undo is immediate. **The live read killed the item's own premise:** all three named invoices carry an EMPTY `payment_mode`, so the auto-suggestion fires on none of them, and the one live receipt reading "Pay $15.00 with a bank transfer" (August, Lovable) is MATCHED to a card charge, because that string is an invoice's payment-OPTION line rather than a record of tender. No unmatched receipt on either month carries a non-card tender today; the disposition is what retires the three, and the fixture is constructed. Two owner rulings: the row still PRINTS in the month report behind a caption naming the tender (real company spend whose evidence is the invoice; dropping it would hide ~30k of July from the accountant), and the chip fires on the payment-option line too, with the caveat recorded. `n_receipts` deliberately does not move; `receipt_match_rate` is read over the receipts a card COULD settle, so a month whose only stragglers were paid by transfer reads 100%. The route refuses a receipt that currently settles a charge, so the month can never claim both that a card paid it and that none did. Four regressions of the real source proven RED first | PR #843, 2026-09-15, this round; suite 1550 -> 1565, and 1675 after rebasing onto the siblings that landed meanwhile; SPA half `docs/lovable-settled-outside-prompt.md` (owner applies) |
| 41 | One unrenderable receipt no longer costs the month its report. The renderability probe copies each page into a throwaway writer, which is the operation assembly performs, so a password-protected or damaged receipt is caught BEFORE its caption is written; assembly guards every file on its own; the caption names the file and the reason; `expenses[].receipt_render` and `summary.n_receipts_unrenderable` put that on the review screen (both absent until a report was built); and a receipt contributes at most 60 pages so one upload cannot decide whether the month reports at all | Item 67, carved from item 49. The old check was `PdfReader(BytesIO(bytes))` and nothing else, which parses the index: a password-protected receipt passed it and raised at `add_page`, the request 500ed, and the period produced NO report, no caption, no partial output, nothing naming the file. Two live facts shaped the build. The defect does not reproduce on Criss's data today: both months render (200; 4.27 MB August, 8.81 MB July) and a read-only census of all 102 stored receipts found 0 encrypted and 0 whose pages the reader cannot copy, so the fixtures are constructed. And ingest tolerance is not the reason it has not bitten: `receipts_folder` skips a file whose extraction raises, but `_pdf_text` reads at most 4 pages while assembly copies all of them, so a PDF damaged on page 5 is extracted happily and only breaks in the report. The damaged fixture proved the sharper point: it constructs AND enumerates its pages, and only the page COPY raises, so a probe that counted pages would have passed it too. Three regressions of the real source proven RED first, and a fourth mutation was discarded as a semantic no-op after `regress_check` reported it green | 2026-09-15, this round; suite 1550 -> 1561; SPA half `docs/lovable-render-failed-prompt.md` (owner applies) |
| 40 | Workbench filter/sort, read against the published page: NO backend change, and `docs/api-contract.md` gains the field guide for the controls (which field answers which control, and the two that do not mean what their name says). SPA delta in `docs/lovable-workbench-filter-sort-prompt.md` | Item 17, and the round's lesson is the read. The item's home, PR #454/#455's Lovable half, turned out to be published already, with a control bar the backlog text predates: search, BUCKET, STATUS, SORT, six FILTERS toggles. Vendor A-Z, the operator's "alphabetic", already works - so the one parallel field this round was scoped to add (`vendor_sort_key`, built, tested green at 1557, regress-proven) was measured against the live sort, found redundant against a better client-side collator, and reverted rather than shipped for the sake of shipping. The drive found the real defect instead: `amount` is `f"{v:,.2f}"`, so `parseFloat("1,574.24")` is 1 and August's two largest unmatched charges (2,484.00 and 1,574.24) render at the BOTTOM of "Amount, high to low", below a 1.16 charge. Two traps recorded beside it: `section` is a display lane where `is_posted` wins (July's 85 `posted` rows are really 49 unmatched / 24 reconciled / 11 review / 1 refund, so an "unmatched" filter keyed on it reports 24 of 73), and `coverage_key` has two live shapes, so a card filter joins `coverage[]` rather than parsing it | 2026-09-15, this round; docs only, no deploy, no regress proof and none invented; suite unchanged at 1550 passed / 2 skipped after the revert; SPA half `docs/lovable-workbench-filter-sort-prompt.md` (owner applies) |
| 39 | The tip band is merchant-scoped: a same-currency pair whose amounts differ stays a candidate only when the two sides agree on the vendor by the matcher's own `_vendor_score`, or when either side names no vendor (absence is missing evidence, not conflicting evidence, so the receipt returns to the pool and the guarantee holds). `amount_probable_min_vendor_score` ships at 0.50, file-tunable, 0.0 disables. Exact amounts and every FX path untouched | Item 63. The 20% band is the restaurant-tip allowance, and a tip never changes who was paid, but the band ignored the merchant: it offered ADOBE 16.23 a Lovable 15.00 receipt and ANTHROPIC 104.95 an Obsidian 96.00 one. The live months were worse than the item knew, with five wrong pairs not offered but BOUND (`chosen`) — MICROSOFT 718.20 settled by Zoho Books 576.00, ATT*BILL PAYMENT 105.23 by Anthropic 100.00. Not a knee: 41 different-merchant pairs all scored <= 0.40 against 30 true pairs all at exactly 1.00, and the cut is flat from 0.45 to 0.90. FX deliberately excluded (S1 measured vendor non-separable there, 26/55 true pairs <0.2) | PR #829, 2026-09-15; August pairs 71 -> 30 with 41 different-merchant gone and all 30 true kept, exact 5 -> 5, calibrate invariant OK / no double-binding both sides; suite 1557 -> 1570 collected |
| 37 | Report totals are formed in `Decimal`, and a row the total cannot read has a visible place instead of a silent drop. `output/_pdf_common.py` owns the arithmetic for both documents (`parse_amount` / `sum_amounts` / `format_totals` / `excluded_note`); the month report's header total and its per-person section sums both go through it. An unreadable amount gets a caption on its own listing row (`amount unreadable, not in total`) and a footer naming the numbers (`2 receipts excluded from the total: expenses 4, 7.`), both silent at zero. `summary.n_amounts_unreadable` is the payload half (parallel scalar), counting expenses whose amount was never read, which is the same population `totals_by_ccy` already skipped in silence | Section 12 row 13 of the storage-system description discloses both halves: amounts are carried as strings so no precision is lost, and the report threw that away by re-summing in binary float, while a cell that would not parse was skipped with `continue`. **Live first, and the prediction was wrong in the useful direction:** both months' reports were built through the route and their printed totals equal a Decimal sum over the same amounts to the cent, with zero unreadable rows on either. Through the app the Amount cell is always a finite two-decimal string (`_amount` formats a Decimal; `validate_expense_field` refuses a non-finite total at the edge), so the drop path is unreachable from the route and the float error stays below the printed digit (August accumulated USD `2663.9500000000007` against an exact `2663.95`). What shipped is therefore the arithmetic class removed plus defence in depth on a public builder whose row contract is "export rows", not two decimals; `NaN` is the trap that made it worth doing, because it parses as both and a float sum would have carried it into every other row's total | PR #831, 2026-09-15, Fly release TBD; suite 1550 -> 1562 passed / 2 skipped; three regress proofs RED first (the silent drop, the float sum, the payload count). SPA half `docs/lovable-amounts-unreadable-prompt.md` (Pending; renders nothing at 0, which is both live months) |
| 37 | The Receipt column answers "is it in the report": `expenses[].receipt_in_report` (parallel boolean, absent until the verdict is known) and `summary.n_receipts_in_report` (absent while any row is undecided), both decided by `prepare_evidence`, the function the builder uses to admit a page. The report's own listing column reads the same verdicts. And `GET /runs/{id}/reconciliation-report.pdf` is built from the reviewer's live overlay, the pair the expense report and the grid already use | Item 68, carved from item 49. "Attached" was an answer about a file, given before renderability was known, so a password-protected PDF or a receipt whose image lives inside an uploaded expense-report PDF counted as covered while its caption page, thirty pages later, said the file could not be rendered. The caption pages were right the whole time. Second half: the reconciliation document read the stored receipt pool, which only catches up at the next re-match, so an expense the reviewer deleted left the expense report at once and stayed in the one document whose entire job is to be the evidence that a month is complete. The live pool is handed to `build_view` rather than filtered out of its output, because the unmatched list, the duplicates, the candidates and the counts are all derived in there and a second derivation is exactly what let the two documents disagree. Renderability is decided once, by `prepare_evidence`, and this reads item 67's record of it rather than opening a second channel for one fact; deciding it per payload would put a decode of every receipt in front of the grid. Read live first and reported: neither half reproduces on August or July today, so the fixtures are constructed. Three regressions of the real source proven RED first | PR #838, 2026-09-15, this round; suite 1550 -> 1559 alone, 1570 after merging main; SPA half `docs/lovable-receipt-coverage-prompt.md` (owner applies) |
| 36 | A month's candidate pool reaches the company months either side of it: `adjacent_pool_for_month` joins the trip pool inside `rematch_month`, neighbours decided by LABEL and eligibility by this statement's OWN period (`statement_period_for_month`, min..max of its charges). Borrowed copies ride the existing `borrowed_receipts` / `receipt_sources` keys with `kind: "adjacent"`, so the claims protocol is untouched and one receipt still settles one charge. `rows[].candidates[].from_batch` names where a borrowed candidate lives, and `summary.n_adjacent_borrowed` counts what the month actually holds | Item 61. A receipt is filed by the month printed ON it while a charge lands in the statement that BILLED it, and Chase does not cut those at the same place: August's workbook opens 07-31, July's 06-30. The named instance did NOT reproduce (July's 06-30 Google receipt is in July's batch and matched, because month routing stamped it from the 07-01 mail, not the printed date), and the literal count the item predicted is 0 on both live months. The real instance is the one the item's own mechanism produces at the OTHER end: August holds two Google receipts dated 08-31 (71.64 and 75.09) for charges that post 09-01, while its own 08-01 Google 71.64 charge carries no candidate at all. Today exactly one receipt would move (June's 06-30 Fenix 55.74 BRL into July, where no charge matches it); the fix is for September's statement and every month after. The period rule rather than a calendar rule is the recommendation the PR states: no calendar predicts a workbook that opens on the 31st. One regression of the real source proven RED first, through the caller | 2026-09-15, this round; suite 1550 -> 1556; SPA half `docs/lovable-adjacent-month-prompt.md` (owner applies) |
| 38 | Both statement parsers keep the printed sign for a `Type` label they do not recognise, reporting one info-severity `parse_issues` note per distinct label with its row count; each `statements[]` entry records the `column_map` and `card_currency` it was read with, and the re-read reuses them | Item 64, two gaps that are inert on today's data and both silent when they bite. (a) Canonicalization ran on "is it a credit", so every OTHER label was read as a purchase and abs'd: a German export's "Lastschrift" would have turned its credits into charges with nothing on screen. "Recognised" now means "in the credit set or the debit set", which is load-bearing: `Sale` and `Fee` are not credits either, and reading those as unknown would flip all 109 August purchases. (b) The re-read recovered each file's map from `config.statement`, which describes only the LATEST upload, so on a two-statement month the earlier file was re-guessed (losing the operator's manual picks) and every file was re-read at the last upload's currency, which moves a charge's currency and stops it matching its receipt. Live check first: both months hold one statement each, carrying only `Sale` / `Payment` / `Fee`, so neither gap reproduces in production and both fixtures are constructed | 2026-09-15, PR #830; suite 1550 -> 1557; three regressions of the real source proven RED first; SPA half `docs/lovable-statement-record-prompt.md` (owner applies) |
| 35 | A rejected pairing says so, and the page can offer the way back: `rows[].candidates[].rejected` on every candidate of a rejected charge (parallel, absent otherwise) and `summary.n_rejected_pairings` | Item 16. Rejecting frees the receipt and stays reversible until export, but `candidates[]` comes from the RAW outcome, so the receipt just pushed away re-rendered under the row exactly as before, offered again as though it were still on the table, with nothing saying it had been turned down. Two findings shaped the build. The live one: ZERO rejected decisions exist in production. All 223 charge rows across the two months with statements are `pending`, and the four receipt-only batches carry no charge rows at all, so the symptom cannot be observed and the fixture is constructed. The design one: the flag has to be charge-level, because `apply_decisions`, `effective_settlements` and `sync_claim_for_decision` all read the status alone and ignore `chosen_document_id`, and a bulk reject writes that column NULL, so a flag keyed on a named document would leave the commonest path unmarked. The undo needed no route: `POST .../decisions` with `"status": "pending"` already resets the charge, re-derives the claim and returns the receipt; a second spelling of an existing reversal is a second thing to keep correct, so the test drives the existing one end to end rather than asserting it ought to work. Two regressions of the real source proven RED first | PR #828, 2026-09-15, this round; suite 1550 -> 1555; SPA half `docs/lovable-rejected-pairing-prompt.md` (owner applies) |
| 34 | A candidate another charge holds says so: `rows[].candidates[].held_by` names the holding charge (parallel, absent when nobody else holds it), and `summary.n_charges_receipt_taken` counts rows whose every candidate is held elsewhere | Item 60. A charge can carry candidates and still be bucketed `unmatched`, because `candidates[]` keeps every receipt the matcher paired with it while the bucket reflects the ASSIGNMENT, and one receipt settles one charge. The bucket was right; the SPA's bucket-derived label was not, so it said "No receipt found" about a receipt sitting on the row above. Two things worth keeping from the build: the reported instance no longer reproduced (item 56's collapse had given that charge its own exact match), so the fixture had to be constructed rather than observed, and the first construction was wrong in an instructive way (two identical charges competing for one receipt leaves the loser in `unmatched_transactions`, which carries no candidates at all). The real path is a reassignment, driven through `POST /manual-match`. Two regressions of the real source proven RED first | 2026-09-15, this round; suite 1547 -> 1550; SPA half `docs/lovable-receipt-taken-prompt.md` (owner applies) |
| 33 | A charge's legal entity comes from ITS card (`stamp_charge_entities`), blank when the registry cannot name that card, counted by `summary.n_charges_no_entity`; and an invoice and its receipt are ONE matcher candidate (`collapsed_duplicate_copies`), with a `not a duplicate` ruling re-matching the month | Items 59 + 56, round 2 of the void list, both on owner rulings taken the same day. A Chase workbook filed as card-2838 posted all 111 of August's charges to Corporate Services while 77 were on cards 3645 / 3876, which the coverage panel already called "not in your card list": a wrong posting is silent, a blank one is a count on screen and one card definition away from fixed. And 23 of August's 31 receipts sat in invoice+receipt pairs that reached the reviewer as `ambiguous` picks between two copies of the same document; collapsing the pool turns each into the exact match it always was, while every copy stays in the snapshot, the counts, the exports and its duplicate marker. The `ignore` escape hatch (two real purchases, same merchant, same day, same amount) re-expands the pool, and the resolve route now re-matches so the ruling is not recorded-and-inert. Five regressions of the real source proven RED first, one of them re-run after the first mutation turned out to be a semantic no-op | 2026-09-14, this round; suite 1547 passed / 2 skipped; SPA half `docs/lovable-charge-entity-prompt.md` (owner applies) |
| 32 | A broken month is never "ready to post": `summary.month_health` on both payloads (`state` broken when the matcher proposed nothing while exact same-day same-amount pairs sit in the pool; `suspects` names sign / currency / entity / card from the matcher's own scoping rules), and `ready_to_post` = no undecided AND health ok. Every commit of `rematch_month` leaves one event (`rematch_log`, trigger + counts) that `/api/operator/state` lists as `rematches[]` and `brisken-recon-notify.py` mails as one line per event | Items 57 + 58, round 1 of the 2026-09-11 void list. August 2026 as uploaded on 2026-09-10 read `ready_to_post: true` with 0 of 111 matched and 31 receipts in the pool: nothing was undecided because nothing had been proposed, and nobody was told, because the notifier pinged on new runs only. The rule only ever refuses; a healthy month is judged by the reviewer's decisions as before, and a month with no exact pair is not its business. Three regressions of the real source proven RED first (readiness wiring, grid wiring, the log append); the 2026-09-10 state reproduced through the real attach route (no Type column, inference off) reads `broken` / `sign` | 2026-09-11 evening, this round; suite 1538 collected; SPA half `docs/lovable-month-health-prompt.md` (owner applies) |
| 31 | Excel statements canonicalize the sign; Chase's `Type` column is guessed; an entity-less receipt is unscoped in the matcher; `POST .../statements/reread` rebuilds a month's charges from its stored files without doubling it | Criss's July and August 2026 reconciled 0 of 111/112 with the receipts in the pool ("ele ve que tem recibo mas nao associa"): the xlsx parser kept Chase's printed negative purchases, the CSV parser had canonicalized them since 3.15, and the matcher compared -15.00 with 15.00. The repair had to be a re-read, not a re-upload, because content-derived ids would have folded the corrected rows in beside the wrong ones. Three regressions of the real source proven RED first (Type path, majority inference, entity rule), offline on the real August file 0 -> 5 exact + 4 judgment + 23 with candidates. Item 55; item 56 records the invoice+receipt-pair ambiguity it uncovered | 2026-09-11, this round |
| 30 | The card screen shows the cards that actually charge. `GET /api/cards` gains `seen_undefined[]`: the card identities the loaded months charge but the registry cannot name, busiest first, each carrying the digits to define it as, its charge count and the months it appears in | `/api/cards` composed the settings registry plus the shipped presets and nothing else, so it listed 2838 and four cards carrying no charges, while 3645 (46 charges), 3876 (19) and 0340 (10) appeared nowhere on the very screen where a card gets defined. The reviewer's actual move, define the card these charges are on, was the one move the screen could not start. Identity comes from the same `_charge_card_identity` the `coverage[]` panel uses, because two derivations would be two answers about the same plastic. One defect caught by its own test before it could reach the table: the suggested name first came off the internal match key, which strips leading zeros on purpose so Chase's "0340" and the Zoho payment mode's "340" land on one key, and a reviewer would have been offered "340" for a card they know as 0340. Human-facing fields now show what the statement printed; the key stays normalized. Four regressions of the real source, each proven RED first, and a fifth candidate dropped with its reason recorded (a fast path with no observable behaviour, so a test for it would assert the implementation) | PR #651, 2026-08-28, deployed Fly `7acbd983`; suite 1398 passed / 2 skipped, calibrate green, CI green; live `/api/cards` on the real Brisken data returns the three undefined cards with the leading zero intact. SPA half `docs/lovable-card-definition-prompt.md`, applied by the owner 2026-09-06 |
| 29 | Duplicates the reviewer can see on the row. Every member of a live duplicate group carries `duplicate` on its own row (`expenses[]` on the grid; `rows[]`, `unmatched_receipts[]` and `assignable_receipts[]` on the workbench), naming the group, this row's place in it, and the first copy it repeats. `summary.n_duplicate_copies` is how many copies are redundant, its own name because it is its own question. A dismissal clears the marker from every row, the count and the document; the reconciliation PDF now names the groups instead of counting them | Owner: "we need to build in a function that recognizes duplicates". It already did, and had since Tier-1 #4: the live April batch carried the Pressmaster FZCO invoice at 135.00 USD as two files, correctly grouped. The gap was that `duplicate_groups` is a side list of ids, so the 40-row grid above it showed both copies with nothing to tell them apart and finding the duplicate meant noticing the amount twice by eye. A flag nobody sees is not a flag. The hand-match picker is included because it holds every receipt: it is the one place both copies could be assigned to two different charges, and it is what keeps the new count backed by rows on screen. One defect fixed alongside: `POST /duplicates/resolve` always replied with the workbench summary, so on an expense batch the grid header's own fields were missing from the reply to its own click. Seven regressions of the real source, each proven RED first | this round, 2026-08-28; suite 1392 passed / 2 skipped, calibrate green, CI green; live check on the April batch shows both Pressmaster rows marked and `n_duplicate_copies` 1; SPA half `docs/lovable-duplicates-prompt.md` (owner applies) |
| 28 | Per-card coverage: `coverage[]` on both review payloads answers which cards a month has loaded, from which uploads, over what span, and how far each has got, with the run summary's own four bucket counts and unreconciled money per card; the reconciliation document gains a coverage table and sections its charge listing per card; `charge_states` becomes the ONE place a charge's effective bucket is decided | Backlog item 29 PR 3. `statements[]` answered the FILE question and nothing answered the CARD one, which is how the loading is actually organized: a card arrives across several files and one file prints several cards, so neither list derives from the other. The live January month is the argument: 80 charges over THREE card identities, zero reconciled, and one flat USD 20,228.68 that tells a reviewer nothing about which pile of receipts to find. Registry cards with nothing loaded get a row on purpose, because "which cards have I not loaded" is unanswerable from a list of the ones she has. Adversarial review found both of the round's defects, both in card identity: an unknown-card key could collide with a registry slug and attribute money to the wrong plastic, and alias-only card names ("CorpServ") fell to the no-card row. Eleven regressions of the real source, each proven RED first | this round, 2026-08-26; suite 1375 passed / 2 skipped, calibrate exit 0, ruff clean on the diff; SPA half `docs/lovable-coverage-prompt.md` (owner applies) |
| 27 | The intake says what it did. Every refusal is written down (`inbound/refusals.jsonl`: envelope sender, recipient, stage, reason, peer), covering the DATA-stage guards as well as a refused RCPT, size-trimmed so a scanner cannot fill the volume, and surfaced as `n_refused` (a 7-day window) + `refusals[]` on the intake log. Separately, every log row now carries `status_kind` (`resting` / `held` / `working` / `done` / `unknown`) and a composed `status_label` ("Waiting for July 2026", "Needs one click to read"), and an unrecognised status degrades to the raw value instead of borrowing a label | Backlog item 30 (b) plus the out-of-Lovable half of the "Arriving" bug. Two silences: mail we turned away left no trace at all, so "did anything bounce?" had no answer anywhere; and `status` had grown three values with nothing checking that the SPA absorbed them, so `pooled` / `routing` / `claiming` all fell through to its in-flight label and six resting receipts announced "Arriving" indefinitely. A confident wrong label is worse than a raw one. api-contract rule 5 now covers enum growth (a grown status set ships a parallel label), and `test_every_status_has_a_label` fails the suite on a new status until someone decides what it SAYS — the contract test pinned element TYPES and had nothing to say about a new VALUE. Eleven regressions of the real source, each proven RED first | this round, 2026-08-24; suite 1256 passed / 2 skipped, calibrate green; SPA half is section 0 + section 12 of `docs/lovable-month-pool-prompt.md` |
| 26 | The intake knows who its own people are. Settings `intake.known_senders` lists outside addresses that count as ours; `graph_notify.send_mail` takes an explicit per-call `allow_external` and asserts the structural recipient guard BEFORE consulting it, so a listed address widens the rule by exactly itself and a smuggled second recipient stays refused. A known sender's body-only mail is now RENDERED ON ARRIVAL instead of waiting for a click, reusing the operator render path unchanged (same CAS, same month stamps, same pool), with a failure alerting because nobody watches an automatic render | Backlog item 30 (a) + (c). Dirk mails receipts from a private iCloud address as well as his work one, and the anti-backscatter guard meant that send produced no ack and no bounce: a delivered receipt and a lost one looked identical from his chair. Meanwhile every one of the six mails held on 2026-08-24 delivered NO file at all — a forwarded vendor receipt IS the email body — so the normal shape of a forwarded receipt read as a fault and sat there. Strangers still hold: the mailbox takes mail from anyone and we do not pay a vision call to read every newsletter. Eight regressions of the real source were each proven RED first, including the two that matter most (a malformed address ON the allowlist must still be refused; a look-alike domain must not read as internal) | this round, 2026-08-24; suite 1245 passed / 2 skipped, calibrate green, ruff clean on the diff; Settings editor `docs/lovable-known-senders-prompt.md` (owner applies) |
| 25 | Emailed receipts file by the month printed ON the receipt, not by whichever month happens to be open. A receipt whose month has no batch RESTS in a pool (new status `pooled`, deliberately not `held_*`) with its month on it, and is added automatically when that month is created or renamed into. Deleting a month returns its mail to the pool, so re-creating the month re-claims it. Every attachment mail is read at ARRIVAL by the full extraction pipeline, which costs nothing extra: the cache is content-addressed and the arrival read warms it for the batch ingest | Dirk's August receipts landed in the April 2026 batch, because `route_archived` picked the newest statement-less batch and never looked at the receipt. Month identity is the operator's label read by `month_from_label`, which refuses day-bearing labels, so the DEFAULT full-date label names no month and can never claim; the create response says so and a rename is the fix path. Decisions are atomic under a new `_POOL_LOCK` held across the "is this month open?" query and the status CAS, so a batch created mid-arrival cannot leave one mail both ingested and pooled. Every new test was proven red first against a targeted regression of the real source (7 of them) | PRs #599 + #601, 2026-08-24, deployed Fly v87; suite 1237 passed / 2 skipped, calibrate green; SPA half `docs/lovable-month-pool-prompt.md`. Live drill on the deployed app, TEST-namespaced and cleaned to zero: a receipt printing 2026-03-15 mailed in August pooled under 2026-03 (source `receipt`, state `no_batch`), opening "TEST - March 2026" claimed it with its printed date intact, deleting that month returned it to the pool, dismiss cleared it. The drill also caught the one defect v86 shipped: `n_pooled` counted log ROWS, so one waiting mail that had been through a claim read as 2 (#601) |
| 24 | The paying card is read off the scan by CHOICE, not transcription: the extractor is handed the last-4s of the cards the payer actually holds (from the run's own registry snapshot) and asked which one it can see, or none. A confirmed pick replaces whatever digits the free-text hint guessed; a hint with no pick passes through untouched; a number that does not reduce to exactly four digits never reaches the entity chain. Vision moves to gpt-5-mini (categorization stays on gpt-4o-mini) | Owner: make sure the card an expense should be attributed to can be extracted from the receipt scan. It could not be — asked to transcribe four faded digits the extractor landed 2 in 5 and INVENTED the rest ("1234" three times, once for a receipt that prints 1672). Three cheaper fixes were refuted by measurement before anything was built: repeat reads return the identical wrong answer, a verbatim field in the same call agrees even when both are wrong, and gpt-4o reads no better than gpt-4o-mini. Measured 3 runs each over 7 problem receipts: dates 0/6 live -> 3.0/6 with the list -> 5.0/6 with the model; cards 1/5 -> 3.0/5 -> 3.7/5; ZERO false positives on the two receipts printing no readable card | PR #592, 2026-08-24, deployed; suite 1217 passed / 2 skipped, calibrate green. Live-verified with a namespaced TEST batch (deleted after): a receipt printing "VISA - ******2838" resolved date 2026-04-11 (the cache held 2023-04-11), hint "VISA ...2838", card-2838, entity Corporate Services via `card` |
| 23 | An implausible expense date stops being accepted quietly: a date outside the batch's month reaches the reviewer as `check` / `date_outside_period`, and the month's report PDF names the expense numbers it distrusts. The month comes from the operator's label, failing that from the batch's own dates by strict plurality, failing both from nowhere (no period = nothing is ever flagged). Extraction prompt tightened for two-digit years, year-first card slips, and fiscal-block-beats-slip | Eleven of the April batch's 36 readings were dated 2020-2023, one of them on line two of the month's report. The date decides which month an expense belongs to and whether a statement charge can ever match it. Nothing is auto-corrected: inventing the "right" date would be the same mistake with better manners, and a date the reviewer typed is believed so a genuinely old invoice can be cleared. Prompt measured, not assumed (6 of 11 fixed, 24 of 25 good readings unchanged, none worse); regressed the real source to watch all four e2e tests go red at 0 flagged of 11 | PR #590, 2026-08-24; suite 1206 passed / 2 skipped, calibrate green |
| 21 | The reconciliation downloads as a document too: `GET /runs/{id}/reconciliation-report.pdf` puts what needs attention FIRST (charges with no receipt, receipts with no charge, duplicate groups), then every charge with its matched receipt and status, then the receipts — matched ones captioned with the charge they settle, unmatched ones captioned as unmatched | Owner: the reconciliation is not exported into any application either, so the question was what actually serves the work. A CSV carries the charge list and none of the evidence, and nothing reads it. Built from `build_view` — the workbench's own payload — so the document and the review screen cannot state different reconciliations. A clean month SAYS "Nothing", because an empty section reads as a missing one | this round, 2026-08-23; suite 1187 passed / 2 skipped, calibrate green; SPA half is section 5 of `docs/lovable-month-report-prompt.md` |
| 22 | Anyone can email a receipt in: the intake's @brisken.com sender allowlist is gone (owner directive), so a hotel sending an invoice directly, a faculty member mailing from a private address, and a supplier's billing robot all land instead of bouncing. The recipient rule stays (mail must be addressed to the intake domain, so the listener is never an open relay) and so do the spend guards; the global day cap is now the real ceiling because a rotating From evades the per-sender one. Outside submitters are ingested but never replied to — the ack's @brisken.com recipient guard is what keeps confirmations inside the tenant | PR #587, deployed Fly v83 |
| 20 | The month downloads as a REPORT, not an import file: `GET /runs/{id}/expense-report.pdf` renders the numbered listing from the export's own rows, then appends every receipt behind a caption naming the expense it proves | Owner directive: nothing imports the output any more, so the deliverable has to stand on its own for a human and an auditor. Building the listing FROM the export rows is what keeps the document and the file from ever disagreeing about money; evidence is per document so a split receipt appears once captioned with both expense numbers, and a missing or unrenderable file is stated on its caption rather than leaving a caption with nothing behind it | this round, 2026-08-23; suite 1178 passed / 2 skipped, calibrate green; SPA half `docs/lovable-month-report-prompt.md` |
| 19 | Stranded mail can come back: `POST /api/inbound/{archive}/re-ingest` re-ingests one archive's delivered attachments into the open month, guarded so only mail whose month was deleted qualifies | A mail whose receipts were ingested into a month that was later deleted had no path back. Replay skips it (status `ingested` is not replayable, correctly), the expenses went with the month, and the bytes sat in the custody archive unreachable from the app — stranding, not loss, but indistinguishable to the operator. Guard proven by regressing it: dropping the `batch_deleted` requirement fails exactly the two tests written for it | this round, 2026-08-23; suite 1168 passed / 2 skipped, calibrate green; SPA half `docs/lovable-re-ingest-prompt.md` |
| 18 | Cards R4, export half: a month whose receipts belong to different companies exports as ONE file with the entity as a column (owner ruling), and the chart gate became per-entity — `MultiEntityCoaGate` judges each row against the chart of the entity that actually pays it | The export half already worked after R3 and is now pinned by tests, but the gate beside it had a live hole: `CoaGate` was built when "a run targets ONE legal entity" was true, and provisioning looked up that one entity, so every entity-less batch (which is every Cards R3 batch) got NO `coa_validation` block and exported completely un-gated — exactly the batches most able to post an account to the wrong company. Proven both ways: the e2e test fails without the provisioning fix, and forcing one gate for all rows fails the per-entity test | this round, 2026-08-22; suite 1163 passed / 2 skipped, calibrate green |
| 17 | The live Zoho connection is gone: API client, journal-posting CLI (`zoho-post`), the `coa_source: "api"` chart pull and the `seed-zoho` importer deleted, with a guard test that fails on any Zoho host, `ZOHO_*` credential read, or re-added subcommand | Owner directive: the app should have no connection or ties to Zoho. This layer was the actual connection — roughly 1,600 lines that could authenticate against and post into the live books. Nothing hosted used it (no `ZOHO_*` env on Fly, the web layer never imported the client), so removal is behavior-neutral where Criss works, and the credentials now have nowhere to be read. Doctor gained a real fix on the way: it rejected `coa_source: "none"`, which is the default | this round, 2026-08-22; suite 1158 passed / 2 skipped (65 tests of the deleted code went with it), calibrate green |
| 16 | Upload rejections carry a stable code beside the English sentence (`issue_details` / `upload_issue_details`: `{code, file, suffix, limit}`) at all three emission sites, so the SPA can say "not a supported file type" in Portuguese without the backend ever retyping the prose list | The prose was English-only on a surface Criss meets when an upload goes wrong, and the obvious fix (enrich `issues` in place) is precisely the move that blanked the batch page on 2026-08-22. Parallel field instead, pinned in the contract test — proven by regressing both ways: an unpopulated details list fails the non-vacuity guard, and retyping `upload_issues` into objects fails the element check | this round, 2026-08-22; SPA half `docs/lovable-issue-codes-prompt.md` (optional, prose unchanged until applied) |
| 15 | One meaning per count: `n_categorized` / `n_uncategorized` answer "how many still need a category" on BOTH screens (one implementation, `service.categorized_counts`), readiness moves to its own `n_ready`, and the batch list derives its counts from the live overlay instead of the summary frozen at ingest — so a category edit or a manual add moves the landing screen too | The operator saw "35 categorized" on the list and "5" on the batch page for the same April batch, with NEEDS CATEGORY claiming 31 rows when 1 needed a category: the page was counting export-readiness under the categorized label, so every Cards-R3 row awaiting an entity read as uncategorized. A count that contradicts itself across two screens costs exactly the trust the loop is buying. Both tests fail on the pre-fix code (page said 0 where 1 was categorized; list stayed 1 after an edit made it 2) | this round, 2026-08-22; suite 1223 passed / 2 skipped; SPA needs no change, optional READY tile in `docs/lovable-ready-tile-prompt.md` |
| 14 | The batch writer lock never blocks the event loop: `set-aside/restore` and the cards-assignment endpoint hand their locked span to the threadpool, and a static AST guard fails CI on any future `async def` route that calls a lock-taking service function outside a sync closure (locked set derived from `service.py`, so a new one joins for free) | Pre-existing since Cards R3, found by the delete-month adversarial review. An OCR ingest holds that lock for MINUTES; an `async def` blocking on it parks the loop, so every endpoint including `/healthz` stops answering, Fly's health check fails, and the machine restart kills the very ingest that held the lock. Reproduced as a real freeze (/healthz never answered while the lock was held), fixed, re-run: 42s of timeouts became 2.2s. Guard proven by regressing the cards handler back inline | this round, 2026-08-22; suite 1221 passed / 2 skipped |
| 13 | View-shape contract test: every list field on the expense-batch and run payloads has its ELEMENT type pinned in CI, probed over HTTP so the pin is what actually ships. A new list field fails until pinned (the moment to decide whether the SPA needs a prompt); a str->object flip fails at once; and a MUST_COVER set keeps the fixtures from passing vacuously by covering nothing. `docs/api-contract.md` carries the same table in prose plus the change rules (enrich via a PARALLEL field, never retype under a live renderer; ship the SPA half in the same round; render defensively) | The 2026-08-22 crash: `parse_issues` had been objects since 2026-07-22, the SPA typed it `string[]`, and Criss's batch page went blank behind the root error boundary for every batch carrying an issue. Nothing in either repo could see the mismatch. Proven by regressing both emission sites back to strings: 3 of 4 tests fail | this round, 2026-08-22; suite 1218 passed / 2 skipped |
| 8 | Mail intake (the app's own mailbox): faculty mail receipts to any-name@expenses.brisken.com and they land in the open month batch automatically — in-app SMTP listener on Fly port 25, raw mail archived on the volume as system of record, per-file "submitted by" provenance (To-alias beats From-sender), deny-by-default sender allowlist answered in-protocol (550, we send nothing), day spend budget + disk/in-flight guards, held-mail strip + one-click replay. Hardened pre-ship by a 3-lens adversarial review (6 highs fixed: archive-before-250 custody, batch-mutation lock killing a silent receipt-loss race, snapshot-keyed dedupe so killed jobs can't make loss resend-proof, raceproof caps, zip refusal, replay/status truth) | Dirk's directive (2026-08-20): one address collects expenses and their paraphernalia; Criss's workload shrinks to review + reconcile. Direct faculty mail also removes her relay role and attributes each expense to a person | PR #548, 2026-08-20; Lovable half `docs/lovable-mail-intake-prompt.md` |
| 1 | Non-receipt quarantine: the tool now recognizes bank-statement pages and report summary sheets among the uploads and sets them aside loudly instead of inventing an expense from them | Criss's real May folder had 7 statement PDFs among 27 files; a report summary page had become a phantom 8,796.35 BRL "expense" | PR #516, Fly v58, 2026-08-13 |
| 2 | The word "null" can no longer appear as an expense account in the export; those rows now show the honest "(uncategorized - assign)" placeholder | The AI sometimes answers "no category" as the literal word "null", which Zoho cannot import and Criss would trip over monthly | PR #518, Fly v58, 2026-08-13 |
| 3 | Same photo, same answer: once a photo has been read, the reading is stored keyed on the photo's content fingerprint and reused instead of asking the AI again; re-runs are identical by construction and cost nothing | The identical image had come back MEGA CENTER / CENTRO / CENTRE across runs, and the 2026-08-15 baseline added a BRL-to-EUR currency flip and a tax drift; every new spelling fragmented learned memory. Verified: smoke10 run twice on the fixed code, the two CSVs byte-identical, second run made zero extraction calls | PR #536, 2026-08-15 |
| 3b | Test runs use the merchant name book too: a run config can carry expense.merchants (inline) or expense.merchants_path (JSON file or full settings dump), and the exported CSV now shows the canonical merchant name over the raw OCR spelling | Offline quality runs were judging the tool WITHOUT the canonicalization Criss actually gets, so the loop was steering on the wrong signal | PR #536, 2026-08-15 |
| 4 | Set-aside strip: the review screen now gets a first-class list of what the quarantine set aside (file, reason code for PT wording, restored state) plus a one-click "this is a receipt" restore that reuses the stored reading (no second AI read) and runs the normal categorize pass. Mid-month exclusions survive later adds; the May run derives its strip from the old warnings. Lovable UI half handed to the owner (`docs/lovable-set-aside-prompt.md` in the module) | Trust: a tool that silently ignores an upload reads as broken; one that says "I set these aside, tap here if I'm wrong" reads as careful. Also closed a real hole: a mid-month exclusion vanished from view on the NEXT add | PR #538, 2026-08-16 |
| 6 | Multi-category vendors: a merchant-book entry can carry multi_category: true — the book still corrects the vendor's NAME everywhere but stops auto-applying its category, so each of that vendor's receipts is judged on its own contents; and every grid row carries category_variance (does this vendor have receipts in other categories in this batch), powering a "Mixed categories" chip + vendor drill-down in the UI | Her own r1 feedback: one vendor legitimately books to different categories, but the book's default silently overrode that; variance was invisible whether right or wrong. Owner direction 2026-08-19: surface it, let a human judge | PR #543, 2026-08-19 |
| 6b | Split depiction ("Lançado como"): every grid row carries books_as — the exact per-account fan-out the Zoho export writes (same shared code path, so grid and export cannot disagree) + an is_split flag; the UI renders one receipt booking to N accounts instead of N mystery rows | Owner ruling: splits ARE the truth and must not be collapsed; what was missing was seeing the fan-out ON the receipt instead of discovering it in the export | PR #543, 2026-08-19 |
| 7 | Feedback capture on every page (owner directive 2026-08-19): the double-click location-specific note widget becomes a single global mount across all SPA pages; `POST /api/feedback` now accepts an explicit `run_id` so notes on expense-batch pages attribute to the batch regardless of route shape (path parse stays as fallback) | The existing widget captured exact click locations and produced Criss's r1 notes, but only on the home/run/memory pages; the receipt-first batch pages — the surface she actually reviews — had no capture at all (0 notes ever) | PRs #544+#545, 2026-08-19; Lovable half `docs/lovable-feedback-capture-prompt.md` published + live-verified end-to-end (batch note attributed run_id 7d2fea33d39a) |
| 6c | Vendor is the merchant, never the card-terminal bank: one extraction-prompt line (backlog item 6) so a card slip showing both the shop and the acquiring bank reads the SHOP; invalidates the reading cache by design (fingerprint bump) | Round-5 evidence: the same French card slip read ANNADA ROUEN one day and CREDIT AGRICOLE NORMANDIE another; the bank name teaches the merchant book garbage | PR #543, 2026-08-19 |
| 12 | Language contract + honest receipt column: review reasons ride as stable codes with structured data (the missing-fields list as data, the SPA composes localized sentences), the grid's split depiction gets a sentinel instead of the export's English placeholder, dead English labels dropped; and the receipt column stops lying — a typed-in expense with no document says so instead of rendering a View button that 404s, attached receipts keep their preview, every file-backed row names which upload/mail it came from | Her notes 4 ("language should not difer from what is set by user") and 8 ("if there is no receipt, please let that be known"); the review carry fixed a false-negative that would have hidden real attached receipts on graduated batches | PR #567, 2026-08-21; Lovable half `docs/lovable-language-receipt-prompt.md` (item 1 APPLY FIRST) |
| 11 | Learned memory validate + adjust: the 103 learned categories are editable (single-row PUT, count-preserving — an operator correction is not another confirmation; category-only edits never wipe the learned Zoho account), deletable one row at a time (aliases/FX stay), and reviewable (validated stamps + a "needs review" filter; ANY value change clears the stamp so machine re-teaches can never wear an old sign-off); reset now previews what it would delete and requires typed-through confirmation | Her note 10 ("this must be validated and adjustable") on the /memory page; the review caught stale sign-off stamps, a migration race on the live store, and a silent account-wipe before they shipped | PR #565, 2026-08-21; Lovable half `docs/lovable-memory-edit-prompt.md` (REQUIRED — old Reset button becomes a safe no-op until applied) |
| 10 | Body-only mail handling: held mail with no attachment (Uber forwards, credit notices) gets three per-mail actions — view the body (sanitized text off the custody eml, never the raw archive), render it to a PDF and add it to the open month through the NORMAL pipeline (same vision reading and quarantine as any scanned receipt; deterministic bytes so a retry can never double-ingest), and dismiss as junk (terminal, custody untouched, held strip can reach zero). Transient `rendering` status makes render/dismiss/replay mutually exclusive; replay now rescues body-only mail a router crash left as "received"; interrupted renders reconcile to retryable at startup; container gets a full-Latin font so German bodies ("Gebühr", "27,90 €") render legibly for extraction | Her note 12 ("where can user handle this?") + Dirk's first real organic mail sat stuck in held_body_only with no path; adversarial review caught a Pillow timestamp defect that would have let retries create duplicate expense rows | PR #563, 2026-08-21; Lovable half `docs/lovable-body-only-prompt.md` |
| 9 | Intake quick-wins: the Email-intake log shows WHICH files each mail delivered (recorded at accept time; legacy archives derived from parts/) and an honest Month column (batch_label resolved for every routed row, held rows say held, deleted months say "month deleted" instead of misreporting each expense as operator-removed); and Delete month exists behind a typed confirm phrase — cascade under the batch writer lock, job rows purged, mail archives stamped batch_deleted but NEVER deleted (custody/retention), response reports where inbound mail routes next + that learned memory is kept. 3-lens adversarial review pre-commit: sync handler (async version froze the event loop on the OCR-held lock), deleted-run refusal at every locked batch writer, DONE-stamp re-check, replay clears stale stamps, atomic serialized meta writes | Her notes 2/3/13: "need to see which files were delivered", "month says no date", "there needs to be some kind of delete month option" — plus the review closing a real freeze + three race defects before they shipped | PR #561, 2026-08-21; Lovable half `docs/lovable-intake-quickwins-prompt.md` |
