---
project: brisken
workstream: p1-expense-reconciliation
kind: improvement-backlog
state: active
updated: 2026-09-17
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
| 4 | Delete the journal artifact | **UNBLOCKED 2026-09-16 evening**: `docs/lovable-journal-callers-prompt.md` (the workbench Downloads button, the `/classic` Published-runs button, the Settings `export_approved_only` card) published by the owner; bundle audit reads `zoho.csv` and `export_approved_only` 0 in every chunk (2 and 1 that morning), July's Downloads row renders without Journal CSV. Next: the backend PR deleting the route, the journal module and `export_approved_only` with its store default |
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

**Note #61 (owner, 2026-09-17): Account picks removed (Shipped row 73; SPA APPLIED 2026-09-17 night, bundle-verified).** "Make these dropdown so user does not have to know the exact numbers by heart" on Settings, Legal entities, Account picks. Asked in plain language what the box is for (it shortens the list of accounts a company's expense rows offer; empty means the full chart), the owner ruled the same day: remove the box, every row always offers the full chart. Shipped: `account_options` always comes from the company's chart, `PUT /api/settings` accepts an entity still carrying `account_picks` in any shape and drops it (the published SPA sends it on every save), and neither settings response serves a stored value. None of the five live entities carried the key, so no row moved. SPA half: `docs/lovable-remove-account-picks-prompt.md`, not yet pasted.

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

**Item 103 owns both halves (SHIPPED 2026-09-17, pending PR).** The tie rule
and the counts ship there: a tie holds its receipts, a receipt spoken for by a
clean exact candidate elsewhere no longer sustains one, and the months list,
the stored summary and the `rematch_log` event count the effective verdict the
page shows. `0023`'s own instance had already gone by then, for an unrelated
reason: item 137 gives it a resolved card, so it no longer ties with `0021` on
50.52.

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

**2026-09-16 evening: notes #47-51 read (the store now holds 51), plus #33 which
no item had cited.** All five new notes are Matthias on July, #48-51 on the
Matching view between 16:08 and 16:16 UTC (#47 at 13:45 UTC), after the item-79 views and the
item 73/74/77/80/81 prompts were published. #47, #50 and #51 (controls that read
as text) are item 85; #48 (what "posted in your workbook" means) is item 86; #49
(a clean match still offers Reject / Confirm) amends item 76; #33 (a card that
cannot be read or is not known) is item 87. Item 88 records an owner question
from the same session, not a note.

### 73. A statement row has a type; a card payment is not a refund (note #42) (SHIPPED PR #905 - see Shipped row 48)

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

**Shipped 2026-09-16 (PR #905), and the live read corrected the secondary
half.** The payment row DID print a card: both workbooks' `Card` cell reads
2838, the stored charge carries `card_last4: "2838"`, and "Corporate Services"
came from the registry through item 59, not from the upload. The provenance
field (`rows[].entity_source`: card / batch / none) shipped anyway, because the
page never showed the basis in either case, and it now reads `card` on that
row. Across all 9 stored runs (the 6 month batches and 3 older runs) the
only `is_credit` rows are the two payoffs;
August also holds `ANNUAL MEMBERSHIP FEE` 150.00 (Type `Fee`), which now reads
`fee` in unmatched. The two live months needed no re-read: the stored
`raw_text` still holds each row's Type cell, and the loader reads it back.
Open, named: a PDF statement has no Type label, so its payoff still reads
`refund` (sign fallback); nothing live is a PDF month today.

### 74. Duplicates mean one thing each (notes #37 and #41) (SHIPPED PR #914 - see Shipped row 50)

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

### 75. The Unmatched list says why (note #40) (SHIPPED PR #932 with item 83 - see Shipped row 52)

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

**Shipped 2026-09-16 with item 83 (PR #932); the full record is under item
83.** The five receipt codes shipped as named. Charges got their own four,
because the receipt vocabulary is false about a charge: `not_a_purchase`,
`receipt_held_by_another_charge`, `already_booked`, `no_receipt_found`.

### 76. Reconciled means reconciled, and clean rows confirm themselves (notes #38, #39) (SHIPPED PR #925 - see Shipped row 51)

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

**Amendment 2026-09-16 evening, note #49 (Matthias, July Matching view, on the
row's `Reject / Confirm match` cell):** "why is it asking this if its been
matched with no uncertainties?" The row is charge `1f01a80db08f72b0`, AMAZON*
Z11US7DF5 315.56 USD on 2026-07-24, candidate `0007__rendered-body.pdf` (276.08
EUR): `match_type: fx_reference`, `confidence: 0.99`, `requires_review: false`,
`vendor_pct` 57, `date_gap_zone: none`, `effective_bucket: reconciled`. It is
also a yellow row in `July2026.xlsx` (`entry_status: posted`, `section:
posted`). Read shortly after the note it carries `status: confirmed`, so it was
probably confirmed after the note; the note stands for the class. Two things it
adds to this item:

- **A posted row never asks.** July has 85 posted rows. The measurement above
  found posted rows block nothing (`review.state: none`), yet this one was
  offered Reject / Confirm. The label half of this item has to cover the buttons
  as well as the status text.
- **The ruling does not reach this row.** "Exact pairs only" plus the working
  vendor floor leaves an `fx_reference` pair at vendor 57 asking. That is correct
  under the ruling, so do not widen it on this note. Show the owner which
  non-exact clean pairs keep asking when this ships, with their count.

**Owner ruling 2026-09-16 late evening (do not re-ask): the vendor floor is 75.**
Measured on the live payloads minutes before the question, the literal rule
(chosen `match_type: exact`, `requires_review: false`, one candidate,
`review.state: ready`) still selects the same six rows, and `labels.csv` /
`notes.csv` confirm all six as correct pairs. At 75, five confirm themselves:
July ELEVENLABS.IO 5.00 (75) and ANTHROPIC 50.54 (100), August LOVABLE 15.00,
LOVABLE 25.00 and ANTHROPIC 51.38 (100). July WEB*NETWORKSOLUTIONS 7.98 (46)
keeps asking although its label says it is right: a floor that low would also
pass the BASE44 / Lovable shape (vendor 40), which was wrong.

**Shipped 2026-09-16 (PR #925).** `rows[].turn` (`decide` / `confirmed` /
`rejected` / `posted` / `none`) says whose move a row is; `decide` is exactly
the `n_undecided` set, and a booked row reads `posted` and never offers Reject /
Confirm. `rows[].decided_by` (`tool` / `reviewer`) and `decided_rule` name who
gave a verdict; `summary.n_self_confirmed` counts the tool's. After every
re-match commit the tool confirms each pending, unbooked, reconciled row whose
category is `ready` and whose single chosen candidate is `exact`, unflagged, not
borrowed, held or rejected, with vendor 75 or more. It is an ordinary confirm
marked as the tool's, re-judged at every re-match (withdrawn when the pair stops
qualifying), and never written over a person's verdict, pending included, which
the store enforces in the upsert itself. Two narrowings of the ruling, both
deny-by-default: a candidate borrowed from another batch or held by another
charge never self-confirms. Predicted on the live payloads: July ELEVENLABS.IO
5.00 and ANTHROPIC 50.54, August LOVABLE 15.00, LOVABLE 25.00 and ANTHROPIC
51.38; it happens at each month's next re-match, not at deploy. **Clean
non-exact pairs that still ask, as the ruling intends: 2, both August
`fx_reference`:** ANTHROPIC* CLAUDE SUB 247.32 (vendor 52) and PETIT TRAIN TOUR
37.48 (vendor 61). July has none left (its AMAZON pair of note #49 was confirmed
by a person). Not built: a `PROBABLE` / `POSSIBLE` pair flagged
`requires_review` can still land in Reconciled (none on either month); it never
self-confirms and reads `decide`. SPA half: `docs/lovable-turn-prompt.md`.

### 77. Dates read in the source locale, and a corrected date moves the receipt (note #34) (SHIPPED PR #910 - see Shipped row 49)

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

**Prompts APPLIED 2026-09-16 evening** (PR #899 text, published by the owner):
both bundle audits pass with the controls hitting, and a cold browser drive
read the cards, folds, captions, status line and the Expenses reconciliation
line on July, August and September at the expected counts (evidence row in
PROMPT-STATUS). Two residues: August view 2's new caption ("1 waits on a
receipt another charge holds") was not observed because the drive's clicks on
that card did not switch the view; and a `?view=` deep link opened on view 1
with its query stripped, so the URL may not seed the view on load (unconfirmed,
re-check by hand before writing a fix). PT pass not driven.

**Open, and not blocking the paste:** PT wording of the new keys (Criss's read
is the check); whether "ordered in their respective overview pages" meant the
listed sequence or only "organised into" (any card is one click away either
way); the first-row pixel position after the trim (the drive measures it).

### 80. A one-day gap is not a date mismatch (note #44) (SHIPPED PR #902 - see Shipped row 46)

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

### 81. The FX block shows the conversion at our rate (note #43) (SHIPPED PR #903 - see Shipped row 47)

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

### 82. A reference rate per month, from the ECB (note #43, owner ruling 2026-09-16) (SHIPPED PR #951 - see Shipped row 56)

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

**Simulation 2026-09-17, before building** (DB copy off the Fly volume at v143,
`tools/recon-match-attribution.py` imported, no model call; ECB Data API
queried the same morning: July EUR:USD 1.141748 / BRL:USD 0.195341, August
1.159310 / 0.194241, June BRL:USD 0.195256). The instrument first reproduced
both hosted outcomes at the Settings rates (parity 0, judgment cache 13 + 2
hits, 0 misses). Keying by the label month and by each charge's own month gave
identical results everywhere.

- **The rate is more accurate.** July's 22 labelled FX pairs: mean absolute
  deviation 1.78% at Settings, 0.44% at ECB (max 2.93% -> 1.41%). August's 3:
  0.68% -> 0.60%.
- **It buys no correct pair on the live months.** Every true pair was already
  inside the 3% clean band. August: nothing changes. July, three receipts
  move, and none for the better:
  - `0067` MARINHO 41.85 BRL, labelled to SUPERMEC SAO JOSE 8.29: clean ->
    review. At 0.195341 the rival charge 'JoseliMariaDos' 8.40 (+2.75%) enters
    the band and the uniqueness gate demotes the true pair to FX judgment.
  - `0034` Erste Fracht 21.00 EUR, labelled excluded ("HOTEL AM TIERGARTEN
    24.02 is another merchant"): unmatched -> auto-matched to that charge,
    +0.2%. At Settings its rival MP *24HBEBIDAS 24.88 sat in the band, the gate
    demoted it and the model said no.
  - `0066` Mega Center 14.90 BRL, labelled excluded: unmatched -> auto-matched
    to '48.247.796 BEATRYZ RI' 2.97 two days later, +2.0%.
- **Six bundles** (deterministic-correct of 95 / wrong / composite): shipped
  asset (self-derived receipt rates) 70 / 0 / 76.0; one Settings rate for all
  six 64 / 3 / 65.2 (Nov 2024 is 9% off it: three wrong matches); ECB monthly
  68 / 0 / 74.3. The ECB beats a static rate across time and trails the
  receipts' own booked rates by two Oct 2024 pairs.
- **The band, not the rate, is the lever** (measured, not built): ECB with a
  2% clean band gives July 32 right (POSTO ARCA and NATHALIA promoted, `0067`
  kept, `0066` to review, `0034` still auto-matched), August unchanged,
  bundles 70 / 0 / 75.7. `fx_reference_match_pct` 0.015 was refuted in the S1
  run under self-derived rates; a 2% band under ECB rates is a new lever and
  its own item, owner call.

**Shipped 2026-09-17 (PR #951), built as ruled and inert on the live months.**
The run config gains `matching.fx_ecb_monthly_rates` (the ECB's monthly
averages as published, units per EUR, all 29 currencies, one request),
fetched at company-month creation (labelled month +/- 1) and at statement
attach / re-read (those months plus every charge's month), fail-open at 4 s.
The matcher reads the cross through EUR for the CHARGE's month (nearest
month when absent). Rung order: typed Settings rate, statement-derived,
receipts-derived, `ecb_month`; the self-derived rates stay above the ECB on
the bundle evidence. The FX block carries `reference_rate_source: "ecb_month"`
and a parallel `reference_rate_period`; the setup advisory stops telling the
operator to add a rate by hand. July and August keep their frozen Settings
rates (EUR:USD 1.162275, BRL:USD 0.192448), which win, so the deploy moves
neither month: replayed on the shipped code, parity 0 on both. The same code
with Settings rates absent reproduces the simulation's charge-month result
exactly (empty diff). The two Settings rates also win for every new month
until someone removes them in Settings, so today the ECB fires only for a
currency Settings does not hold. SPA half: `docs/lovable-ecb-rates-prompt.md`
(Settings copy, the ECB source label).

### 83. A decided duplicate leaves the month's work (note #46, Criss) (SHIPPED PR #932 with item 75 - see Shipped row 52)

**Criss, July, anchored on `Duplicate charges (4) / Real duplicate / Not a
duplicate`:** "Acoes resolvidas deveriam ser retiradas da area que constam para
ser removidas." Restated by the owner 2026-09-16: once someone has ruled whether
a duplicate is real, it should disappear from the month instead of staying where
it waits for action. Item 74(d) recorded the author as uncertain (shared operator
code, same IPv6 /64 as the owner's notes); the owner attributes it to Criss.

Item 74 took the question away from the reviewer (the tool decides every group)
and 74(d) folded decided groups into a collapsed "Copies set aside (N)" record.
That answers the duplicates PANEL. It does not answer the month, and nothing has
checked what Criss sees.

**Live read 2026-09-16, both months after v138:** every group is `state:
decided` (`n_duplicate_groups_open` 0; July 5 groups, 2 by reviewer and 3 by
tool; August 11, all by tool). The set-aside copies are still in the month's
work lists: `unmatched_receipts` carries July 4 of 13 and August 11 of 21 rows
whose `duplicate.is_extra` is true, and `assignable_receipts` carries the same 4
and 11. So the backend still presents a decided copy as a receipt waiting for a
charge, and the Unmatched receipts count includes it. The SPA's item-79 month
views fold `is_extra` rows into a collapsed record; whether that is what renders
on July and August has not been driven.

Done means: after a ruling (by the tool or a reviewer), the copy appears in no
open list and no open count on the month (duplicates panel, unmatched receipts,
the hand-match receipt picker), and stays reachable only in the set-aside record
with its undo. A "Not a duplicate" ruling returns both receipts as ordinary
receipts with no duplicate marker in any list.

Build order:

1. Browser-drive July and August cold, both languages, and write down every
   place a set-aside copy still shows as open work. If the SPA already hides
   them everywhere, the remaining defect is the counts, not the rows.
2. Backend, if the drive confirms it: move `is_extra` copies out of
   `unmatched_receipts` and `assignable_receipts` into a parallel list, and take
   them out of the unmatched counts. The copies were put back into
   `unmatched_receipts` on purpose so the reconciliation invariant holds
   (recorded under item 75), so the invariant has to count the new list, and
   the SPA's by-index pairing of `duplicate_groups` with
   `duplicate_receipts` must not move. Item 75's `reason_code:
   duplicate_copy` is the same set of rows seen from the other side; build
   whichever lands first so the other reuses it.
3. SPA half as one Lovable prompt, gated on the backend field being live.

**Shipped 2026-09-16 with item 75 (PR #932).** Step 1 was a read of the
published SPA source rather than a drive: the Matching view's first card
already folds `is_extra` rows into a "copies set aside" record, but its whole
count is `n_unmatched_rec` (copies included), the hand-match picker lists them,
and a copy could be offered as another charge's near miss. The backend now
splits at VIEW time, the stored outcome untouched: a copy of a group whose
verdict is `copy` (tool or reviewer) that the effective outcome leaves
unmatched moves from `unmatched_receipts` and `assignable_receipts` into
`copies_set_aside[]`, out of `n_unmatched_rec` and out of the near-miss pool,
with `summary.n_copies_set_aside`. A copy a reviewer hand-matched renders as
that match. `duplicate_groups` / `duplicate_receipts` are untouched, so the
by-index pairing holds. The accounting is a route-tested partition: every
receipt is held, unmatched, settled outside or set aside, and
`receipt_match_rate` reads over receipts a card could settle.

Every unmatched receipt and charge carries a parallel `reason_code`
(`unmatched_reasons.py`). The receipt rules are item 69's attribution rules
with the date edge read BEFORE the card, bounded to a month either side, and
tender words counting only when no card digits are printed. Measured on the 14
live receipts whose label names a coverage kind: 11 name the labelled kind
(card-first: 9); Redis 13,200 and 360Crossmedia 900 (bank transfers, no
payment method printed) read `no_charge_on_any_loaded_statement`, true of
them; Konsultancy 15,972 EUR dated 07-30 reads `charge_in_neighbouring_period`
and is a bank transfer, the one wrong claim.

Predicted live after deploy, from the payloads (the view computes it, no
re-match needed): July unmatched receipts 13 -> 11 (7 no charge found, 2
neighbouring period, 2 not a card charge) + 2 set aside; August 21 -> 10 (4
card not loaded, 4 neighbouring period, 1 not a card charge, 1 no charge) +
11 set aside. Charges: July 47 already booked, 1 held (GOOGLE Workspace
71.64), 24 no receipt; August 1 not a purchase (ANNUAL MEMBERSHIP FEE), 1
held, 98 no receipt. Receipt match rate July 75.0% -> 78.0%, August 32.3% ->
50.0%. Suite 1929 -> 1958 passed / 2 skipped; four regress proofs bite. SPA
half: `docs/lovable-unmatched-reasons-prompt.md`. The July Hostinger and Redis
groups a reviewer ruled "Not a copy" stay unmatched, as ruled.

### 84. The Expenses view's tiles open the expenses they count (owner, 2026-09-16) (SHIPPED PR #935 - see Shipped row 53)

**Owner, on a screenshot of July's Expenses view tiles:** "these should be the
overview boxes, that a user should be able click on and see all of the belonging
data. It already works like that in the matching page."

The Matching view's cards (item 79) are one click to the rows they count. The
Expenses view still has the older tile bar: EXPENSES, CATEGORIZED, NEEDS
CATEGORY (with an "N suggested private" caption), READY, TOTALS, then a second
row with MISSING ENTITY, NEEDS PERSON and MISSING RECEIPT IMAGE (the first two
render only when their count is above 0). Published bundle 2026-09-16 (`chunk-expenses._batchId`):
none is a filter. NEEDS PERSON is the only link, and it goes to `/settings`, not
to the 33 expenses.

**Live read 2026-09-16** (`GET /api/expense-batches/{id}`), tile vs a count
rebuilt from `expenses[]`:

| Tile | July tile | July rows | August tile | August rows | Row field |
|---|---|---|---|---|---|
| Expenses | 52 | 52 | 31 | 31 | all |
| Categorized | 49 | 51 | 27 | 28 | `posting_category.category` set (does NOT reproduce) |
| Needs category | 3 | not rebuilt | 4 | not rebuilt | `n_uncategorized` |
| Suggested private (caption) | 24 | 24 | 8 | 8 | `suggested_private` |
| Ready | 14 | 14 | 10 | 10 | `review.state == "ready"` |
| Missing entity | 33 | 33 | 13 | 13 | `legal_entity_id` empty |
| Needs person | 33 | 33 | 13 | 13 | `person` empty |
| Missing receipt image | 2 | 2 | 1 | 1 | `has_receipt_image` false |

Three things the table says before anyone writes a filter:

- **A filter must show exactly its tile's number.** Categorized is counted by
  `service.categorized_counts` (item 22), and the obvious row rule misses by 2
  on July and 1 on August. The SPA cannot rebuild it; the row needs the verdict
  the count uses.
- **MISSING RECEIPT IMAGE may be the item-52 disagreement.** The tile counts
  `has_receipt_image: false`, while `receipt_image_available` reads true on every
  row of both months, and on 2026-09-15 item 52 found every July and August
  receipt serving 200 from the image endpoint. Check whether these rows'
  receipts open before turning the tile into a filter; a click that lists
  receipts which open would be a new wrong claim.
- **MISSING ENTITY and NEEDS PERSON are the same rows** (33 and 33 on July, 13
  and 13 on August, identical document sets), and every suggested-private row is
  inside them. Two tiles for one set is a design question for this item, not a
  reason to drop either click.

Build:

1. Backend: one parallel per-row field naming the tiles a row belongs to (for
   example `expenses[].tiles[]`), produced by the same code that produces each
   `summary` count, so tile and filter cannot drift. Contract-test it, and add a
   test that for every tile the count equals the rows carrying it.
2. SPA: each tile with a count is a button that filters the Expenses list to
   its rows, with the active tile marked and a way back to all expenses, on the
   pattern of the Matching view's cards. NEEDS PERSON filters the rows; the link to
   Settings > Cards moves into the filtered view. The "N suggested private"
   caption is its own target. TOTALS stays a display.
3. Decide first, in the same round: which receipt-image field the tile means,
   and whether MISSING ENTITY and NEEDS PERSON stay two tiles.

Browser-drive July after publish: click each tile, and the list length equals
the tile.

**Owner ruling 2026-09-16 late evening (do not re-ask): MISSING ENTITY and NEEDS
PERSON become one box.** Why they coincide, read off both batch payloads: every
expense with a resolved `card` carries both a company and a person (July 19,
August 18, none missing a person), and every expense without one carries
neither (July 33, August 13; 24 and 8 of them `suggested_private`). The fix is
one action either way: pick the card, or mark the receipt private. The merged
box opens those rows, and the suggested-private caption sits inside it. The
backend still needs one row membership that equals the box's count (build
step 1 unchanged); `n_needs_entity` and `n_needs_person` keep their names and
questions per the counts table, and the box gets its own.

**Shipped 2026-09-16 (PR #935).** `expenses[].boxes[]` names every box a row
belongs to (a count name without `n_`), and every box count on the expense
summary is now summed from those rows (`service.expense_boxes`), so a filter
cannot show a different number than its tile. The two questions were resolved
first, off the live payloads. **Categorized 49 vs 51** is three two-line
receipts (July `0006`, `0062`; August `0019`) whose second line has no
category: the row shows line 1's category, and `categorized_counts` requires
every line. The count was right, and `is_categorized` gives the box that rule.
**MISSING RECEIPT IMAGE was a false claim:** its 2 July rows (the `0000`
rendered mail body, the moved Parada slip) and 1 August row read
`has_receipt_image: false`, and the image endpoint served all three (200,
PDF). A row now counts as missing only when the app can show no file AND no
image is referenced, on both payloads, so the tile reads 0 on both months.
MISSING ENTITY + NEEDS PERSON became `needs_company_or_person` /
`n_needs_company_or_person` (rows missing either; the two old counts keep
their questions). The box list also covers suggested private, private, cost
center and not-in-report. Predicted live: July 49 / 3 / ready 14 / 33 / 24 /
0, August 27 / 4 / 10 / 13 / 8 / 0. Suite 1958 -> 1968 passed / 2 skipped;
five regress proofs bite. SPA half: `docs/lovable-expense-boxes-prompt.md`.

### 85. Controls that read as text are buttons (notes #47, #50, #51) (APPLIED 2026-09-17, prompt PR #938)

**Matthias, July, 2026-09-16:**
- #47, Expenses view, on "Confirm private expense": "this should be real button".
- #50, Matching view, on the duplicates panel's "5 decided / Hide": "make
  "Hide/View" a button".
- #51, Matching view, on the Matched card's "16 already posted in your workbook /
  Show": "Make "Hide/Show" a button".

Published bundle 2026-09-16: the "Confirm private expense" trigger
(`expx.private.confirm`, `chunk-expenses._batchId`) is a `<button>` styled
`text-[11px] underline underline-offset-2 text-muted-foreground`, so it reads as
a grey link; the dialog's save behind it is a real button.

SPA only, one Lovable prompt. Every action or toggle on the month pages uses the
app's button component (outline, small), and a fold toggle names what it shows
or hides, e.g. "Show 16 posted" / "Hide 16 posted". Before writing the prompt,
list every underlined text control in `chunk-expenses._batchId` and
`chunk-runs._runId` so all of them go in one prompt, not three. Browser-drive
July after publish.

**Prompt written 2026-09-16 (PR #938), together with item 86:**
`docs/lovable-controls-as-buttons-prompt.md`. The inventory was read from the
SPA repo at head `dcd875a7`, not the bundle, and anchored by i18n key, because
line numbers move with every publish (the brief's list had already drifted by
3 to 14 lines). The prompt covers 10 controls in `RunWorkbench.tsx` and 10 in
`ExpensesReviewGrid.tsx`, all as outline small buttons. Fold toggles now name
what they show ("Show 48 booked rows", "Show 5 groups"). Two listed entries are
not in it: `wb.credits.tip` is a card's `title` attribute, not a text control,
and the NEEDS PERSON Settings link belongs to the item-84 boxes prompt, which
replaces that tile.

**Applied 2026-09-17** (owner published; bundle-audited and browser-driven cold,
EN + PT, 0 writes; evidence in `PROMPT-STATUS.md`). On July the booked fold's
toggle is an outline button "Show 48 booked rows" / "Hide 48 booked rows", the
duplicates panel's is "Show 5 groups", 24 "Confirm private expense" controls are
outline buttons that open the same dialog, and no button or link on the Charges
or Matched views carries an underline class. Matched's fold reads "31 decided",
not the booked shape, because 3 of its 31 rows are grey subscription rows: the
prompt's own rule, and note #51's "16 already posted" predates two re-matches.

### 86. "Already posted in your workbook" says what the workbook is (note #48) (APPLIED 2026-09-17, prompt PR #938 with item 85)

**Matthias, July Matching view, on "30 already posted in your workbook" under
"Charges without a receipt 72":** "what is the workbook? where does this come
from".

The workbook is the Chase statement spreadsheet Criss uploads for the month
(`July2026.xlsx`). She colours a row yellow once she has entered it in Zoho, and
`ingest/statement_xlsx.py` reads the fill of the mapped cells: yellow ->
`entry_status: posted`, gray -> `subscription`. July carries 85 posted rows
(`summary.n_already_posted`). Nothing on the page says any of that, so the caption
states a fact whose source the reader cannot see.

Build, SPA copy only: the caption names the file and the rule, e.g. "30 marked
yellow (already booked) in July2026.xlsx", with a tooltip for the gray rule. The
statement's filename is already on `statements[].file`. PT wording goes to Criss.
Worth deciding with item 23: "posted" means "entered in Zoho" in her process, and
the app no longer mentions Zoho, so "already booked" is the neutral word.

**Prompt written 2026-09-16 (PR #938, with item 85).** The booked fold reads
"{n} rows marked yellow in {file}, already booked", with `{file}` taken from
`statements[].file` (live: `July2026.xlsx`, `August2026.xlsx`), falling back
to "the statement workbook" when no file is recorded. Its tooltip gives the
yellow and grey rule and says the colours are read when the statement is
loaded. The PT wording in the prompt ("já lançadas") is a draft for Criss.

**Applied 2026-09-17.** July's fold reads "48 rows marked yellow in
July2026.xlsx, already booked"; hovering it opens the yellow / grey tooltip; PT
reads "48 linhas marcadas em amarelo em July2026.xlsx, já lançadas". The PT
wording is still the draft; Criss has not commented on it.

### 87. A card that cannot be read or is not known gets a fix that sticks (note #33) (SHIPPED PR #947 - see Shipped row 55)

**Shared operator code, 2026-09-09, July Expenses view, anchored on "Assignments
here apply to this month only; the tool will not remember them.":** "need to
create a process to manually correct and fix this when card is not readable or
not recognized from system database".

No item cited this note for a week. The anchor is the card-review strip's notice.
Pieces that exist: Cards R3 assignment on that strip (a digit-bearing hint learns
as an alias; a digit-less tender assigns for the month only, by the 2026-08-22
ruling), "Define card" from `/api/cards` `seen_undefined` (item 30), the
suggested-private route for unknown tenders (item 41), and item 35's grouping.
What the note says is missing is one clear path from "this receipt's card is
wrong or unknown" to "fixed, and next month knows".

First step is a read, not a build: drive July's strip as the note's author saw it,
list which rows it holds and which of the paths above each one would take, and
check whether "the tool will not remember them" is true for digit-bearing hints
(R3 says they learn). If the notice is wrong for those rows, the copy is the
defect. If the paths are right but scattered, this is one "fix card" action per
row. Item 88's finding is adjacent: corrections made per month are not saved as
rules unless someone presses Save corrections to memory.

**Read 2026-09-17 (live July and August, `/api/cards`, code).**

- **The notice is true where it shows.** It renders only above the "No card
  number on the receipt" section, whose hints are generic tender words the
  backend refuses to learn. So the copy is not the defect.
- **Two remembered assignments never stuck.** The strip answered
  `learned: true` for both, and each would have come back unresolved next
  month (replayed offline against the live registry):
  - "Paid via Corp Services card" (July) stayed ambiguous, because four
    cards carry the word alias "Corp".
  - "42463153XXXXXX38" (August) was taught as the card number "42463153",
    which `_card_keys` skips as a masked BIN since item 69 round B.
- **The paths were scattered, and some rows had none.** July's 33 rows in "No
  company or person" split three ways:
  - 16 print only a tender word (VISA 7, VISA CREDIT 4, DEBIT, DEBIT
    MASTERCARD, Cash, TEF, Cartao Credito 30 Dias). The strip's only move
    assigns every receipt printing that word to one card at once.
  - 8 print no card at all. They are not in the strip, not suggested private,
    and "Define card" lists nothing (`seen_undefined` reads statement charges,
    and every statement card is defined). Their only way out was "Confirm
    private".
  - 9 print a specific hint. August: 7 / 5 / 1 of 13.

  The item-84 box line "Add a card and its person once, and every receipt
  paid with it is fixed" cannot fix 24 of July's 33.

**Shipped 2026-09-17 (PR #947): one card fix per row, remembered at sign-off.**

- **This month.** `PUT /api/runs/{id}/expenses/{doc}` takes `card_key`, an
  active registry card. A card defined after the month was created is copied
  into the month's card snapshot. The row's company, person and paid-through
  account follow the card. No re-match. `expenses[].card_source` reads hint /
  override / learned / none.
- **Next month.** Publish saves the fix as a field correction for the vendor.
  A later receipt from that vendor takes it only when it prints no card
  number, so a printed number, known or not, always wins. The Memory page's
  Forget is the undo.
- **The strip's learning sticks.** A whole-string alias now beats a word alias
  other cards share, and a masked BIN learns as its string. Every learnable
  live hint on both months now resolves next month in the offline replay.
- **Tests.** Suite 1974 -> 1983 passed / 2 skipped. Seven regress proofs bite:
  per-row override, remembered card, printed number wins, learned at Publish,
  route refusal (reproduced by hand: 200 instead of 400), exact alias, masked
  BIN.
- **SPA half:** `docs/lovable-card-fix-prompt.md` (a card select under each
  unresolved row, the source line, and a box line that stops overstating).
- **Nothing moves on Criss's months until someone picks a card:** no stored
  override exists, and memory holds 0 field corrections.

### 88. Corrections are learned only when someone presses a button nobody presses (owner question 2026-09-16) (SHIPPED PR #940 - see Shipped row 54)

The owner asked what "Save corrections to memory" on the Expenses view is for. It
calls `POST /api/runs/{id}/commit-memory`, which folds that month's hand edits
(vendor spelling, category, company, paying account) and match decisions into
the learning store, so the next receipt from the same vendor arrives pre-filled
("Auto-filled from a prior correction"). `commit_to_memory` has exactly one
caller, that route: editing an expense teaches nothing until the click.

Live 2026-09-16 (`GET /api/memory`): 103 learned categories (the count recorded
on 2026-08-21), 0 learned entities, 0 field corrections. July carries a
hand-edited row (date, company, paying account) that is not in memory. So the
July and August corrections have most likely never been saved as rules.

Recommendation, not ruled: save a month's corrections automatically at a natural
point (month sign-off, or each edit), and keep the Memory page as the undo. Trade-
off to put to the owner: a one-off exception would also become a rule until
someone deletes it there. Decide before building item 87, which depends on
fixes being remembered.

**Owner ruling 2026-09-16 late evening (do not re-ask): save a month's
corrections to memory automatically at month sign-off, with the Memory page as
the undo.** Accepted trade-off: a one-off exception becomes a rule until someone
deletes it there. Item 87 is unblocked by this ruling and still starts with a
read of July's card strip, not a build.

**Shipped 2026-09-16 (PR #940).** In code, the month's sign-off is **Publish**
(`POST /api/runs/{id}/publish`). The SPA's copy says "Open a run, resolve every
row, then hit Publish" and disables the button with "Resolve the blockers above
before publishing". Publishing now saves the month's corrections through
`commit_month_memory`, which the button uses too, and the reply carries
`memory` (saved + learned / unchanged / error). A failed save never fails the
publish. A digest of verdicts, overrides and edits, kept per run in a new
`memory_commits` table, stops unpublish + publish or button + publish from
counting the same corrections twice. The run summary could not hold it,
because every re-match rebuilds it. The undo is the Memory page's per-merchant
Forget (all five learned tables) and category edit; registry aliases are
undone in the Merchants editor. **Nothing live has fired it yet:**
`published_runs` is empty, so the first automatic save happens when a month is
first published. Suite 1968 -> 1974 passed / 2 skipped; four regress proofs.
SPA half: `docs/lovable-memory-at-signoff-prompt.md` (a publish toast with the
count).

### 89. "Reconciled" on the months list claims a month is done (owner, 2026-09-17) (PROMPT WRITTEN PR #947, pending the owner's paste)

**Owner, with a screenshot of the two green badges:** "these green marking should
state 'matched with statement' not reconciled".

The badge is the Statement column of `/months` (`MonthsHome.tsx`), shown when
`has_statement` is true, reading `months.state.reconciling` ("Reconciled", PT
"Conciliado"). It appears the moment a statement is attached. July carries it
with 24 charges without a receipt and 11 receipts without a charge, so it states
a conclusion the month has not reached. No other visible status badge reads
"Reconciled". `sum.reconciled` and `wb.bucket.reconciled` are in the
dictionary but not rendered by the month pages. Left alone, not this note: the
"Reconciled CSV" download and the guide's bucket list.

SPA only: `docs/lovable-matched-with-statement-prompt.md`. The badge reads
"Matched with statement" with a tooltip ("A statement is loaded and its charges
were matched against this month's receipts. Open the month to see what is still
open."). PT "Comparado com o extrato" is a draft for Criss. Worth asking her
separately: on the Matching view the PT card for matched rows reads
"Conciliadas" while EN reads "Matched".

### 90. A tighter clean band for the ECB rate, then the Settings rates go (owner ruling 2026-09-17, follows item 82) (band SHIPPED with item 132, PR #1048, Fly v167; step 4 OFFERED and DECLINED 2026-09-17 evening, see the decision below; do not re-ask)

**Owner ruling 2026-09-17 (do not re-ask):** tighten the clean band first, then
remove both Settings FX rates (EUR:USD 1.162275, BRL:USD 0.192448) so new
months use the ECB monthly average. Until this item ships, the two typed rates
stay and win for every month.

Why the order: item 82's simulation (backlog item 82, 2026-09-17) found the
ECB rate more accurate (July's 22 labelled FX pairs 1.78% -> 0.44% mean
deviation) but, at the 3% `fx_reference_match_pct`, it moved July -1 right
(`0067` MARINHO demoted by the rival JoseliMariaDos 8.40) and +2 coincidental
auto-matches (`0034` Erste Fracht -> HOTEL AM TIERGARTEN 24.02, `0066` Mega
Center -> 48.247.796 BEATRYZ RI 2.97). A 2% band under ECB rates, measured
once and not built: July 30 -> 32 right (POSTO ARCA and NATHALIA promoted,
`0067` kept, `0066` to review), `0034` still auto-matched at +0.2%, August
unchanged, six bundles 70 / 0 wrong / 75.7 (shipped 76.0).

Build:

1. Decide the scope of the tighter band: ECB-sourced rates only (a new knob,
   e.g. `fx_ecb_match_pct`, leaving `fx_reference_match_pct` and the scorer
   asset untouched) or the shared band. `fx_reference_match_pct` 0.015 was
   refuted in the S1 run under self-derived rates
   (`docs/optimize/brisken-recon-tuning-v1/SUMMARY.md`); read it first.
2. Simulate on a fresh DB copy and the six bundles with
   `tools/recon-match-attribution.py`, at 3%, 2.5% and 2% under ECB rates
   with the Settings rates removed (not 1.5%: refuted in the S1 run); report
   bucket changes against `labels.csv` and bracket the knee. `0034` is not fixable by the band
   (+0.2%): name it as the residual.
3. Ship with the scorer guard green; route-level tests; regress proof.
4. Then, and only on a per-action owner yes at that point: remove the two
   Settings rates via `PUT /api/settings`. July and August keep their frozen
   rates either way; the change reaches months created or statement-attached
   afterwards.

**Step 4 offered 2026-09-17 evening; owner answer: leave both rates. Do not
re-ask.** The step stays open and unactioned until the owner raises it himself.
Nothing was written to Settings; the two rates are live and unchanged.

**The reads taken before offering, and the correction they force on step 4's
own wording.** Settings holds exactly the two rates (`GET /api/settings`:
`EUR:USD 1.162275`, `BRL:USD 0.192448`). Off a read-only DB copy of the same
evening, `runs.config` `matching.fx_reference_rates` is present on July
(`50622baec444`) and August (`074a7b8905d7`) and **null on September, May, June
and January**. So "July and August keep their frozen rates either way" holds,
but "the change reaches months created or statement-attached afterwards"
understates who is exposed: four EXISTING months carry no rate of their own.
`apply_master_data` folds Settings in with `setdefault`, and only at month
creation and statement attach (`service.py` 406 and 11243; `rematch_month`
never calls it), so each of those four copies today's typed rates in and
freezes them the next time a statement lands. That is item 132 in its live
shape, not a future risk, and it is what step 4 would prevent.

**The drift, measured against the ECB table stored in the August month:**

| pair | typed | ECB 2026-07 | gap | ECB 2026-08 | gap |
|---|---|---|---|---|---|
| EUR:USD | 1.162275 | 1.141748 | +1.80% | 1.159310 | +0.26% |
| BRL:USD | 0.192448 | 0.195341 | -1.48% | 0.194241 | -0.92% |

July's euro gap is wider than the 1% the two bands leave between them
(`fx_reference_match_pct` 0.03 minus `fx_ecb_match_pct` 0.02, both defaults in
`deterministic.py`), so item 132's advisory should fire on July at its next
re-match. It reads zero on both months today and that is expected, not a fault:
each month's stored summary predates the code. July's last re-match was
16:59:25Z and August's 11:35:23Z, while v167 shipped at 17:28:24Z. The
advisory is carried on the stored summary, so it appears on the next re-match
of either month with no action needed.

### 91. Settings is one scroll of seven editors (owner, 2026-09-17) (SHIPPED PR #969, SPA APPLIED 2026-09-17)

**Owner 2026-09-17:** "group the different settings in the settings page into
tabs of each setting."

`/settings` renders every editor in one column: FX reference rates, Cards
(with the seen-but-undefined block), Cost centers, Expense categories,
Merchants, Email intake, Legal entities, then the Clear memory danger zone.
Reaching the last one means scrolling past six, and nothing on the way says
which one needs attention. Each editor already saves only its own key
(`PUT /api/settings` with `{"cards": ...}` alone), so the grouping is a
layout change, not a contract change.

Seven tabs, the first six reusing the titles the page already carries as
their labels: Cards, Merchants (the read-only category list folds in under
the table, where the merchant category picker uses it), Cost centers, Legal
entities, Email intake, Currency, and Advanced. Advanced holds the Clear
memory block plus `export_approved_only`, a live setting enforced in the
Zoho export that no screen has ever offered; the page subtitle is that
setting's scope sentence, orphaned above seven unrelated groups, and it
moves down with the switch.

What tabs break, and the mitigation: a scrolling page showed the
seen-but-undefined cards and the inert merchants on the way past, and tabs
hide both. So the triggers carry counts, and the two states the backend
actually reports (`seen_undefined`, `merchants_inert`) carry an amber
marker. Nothing else gets one.

**Backend half, shipped:** `PUT /api/settings` now refuses an unknown
top-level key (400, naming it, writing nothing) instead of dropping it under
a 200, and answers `applied[]` / `ignored[]` so a tab shows "saved" on its
own key landing rather than on the status code. One group per request is the
page's contract; under tabs that request is the only feedback the group
gets. api-contract "What a settings save wrote";
`tests/test_settings_put_contract.py`.

SPA half: `docs/lovable-settings-tabs-prompt.md`, published by the owner and verified 2026-09-17 (bundle + cold drive, PROMPT-STATUS Applied row).

### 92. The entity list is in nobody's order (Criss via owner, 2026-09-17) (APPLIED 2026-09-17: backend PR #971 deployed v146; round 1 arrows and round 2 press-hold-drag prompts published and verified; order in live use; see PROMPT-STATUS)

**Criss, relayed by the owner 2026-09-17:** she wants to select entities that
have been saved and reorder them.

Every entity list in the tool is alphabetical: the Settings editor and the
entity dropdown on every expense row both render `entity_options`, which was
`sorted()`. Nobody chose that order, and the entity Criss books all day sits
wherever its initial puts it with no way to move it.

Two defects sit underneath the ordering ask, both visible in the Settings
editor:

- It lists `entities` (the registry someone typed) while the pickers offer
  the union of the provisioning file, the card map and that registry. Live
  (read 2026-09-17): the registry holds 5 entries, the pickers 8. Ordering
  only the registry rows would have left 3 of the 8 immovable.
- Every field of every entity is on screen at once, so the list is a wide
  table to read rather than a list to pick from.

**Backend half, shipped:** `settings['entity_order']`, a list of entity
names. `available_entities` returns the names it lists first, in that order,
then everything it does not name alphabetically, so `entity_options` carries
the order to every picker (settings payload, `GET /api/cards`, each batch's
grid) with no per-caller change. A separate list rather than a field on each
registry entry, because most entities never reach that registry. A stale
name is ignored at read time and kept on save: an entity leaving the card
map must not refuse the operator's ordering, and an entity the order never
names must still appear (at the back) so a charge on it stays bookable.
Unset: alphabetical, exactly as before. api-contract "The writable keys";
`tests/test_master_data_settings.py` (ordering) and
`tests/test_web_expense_settings.py` (the grid route reads it).

SPA half: `docs/lovable-entity-order-prompt.md`. The list renders
`entity_options` (never sorted locally), a row opens its fields, drag or the
move buttons save `{"entity_order": [...]}` on their own. Published and
verified 2026-09-17.

**Open, owner-side data (found verifying this item, not fixed: Criss's
settings):** the three extra entities are the cards' names for the same
companies. All 9 cards point at `Corporate Services` / `Cloud Services` /
`Consulting`, while the entity settings are filed under `Brisken Corp
Services, LLC` / `Brisken Cloud Services, LLC` / `Brisken Consulting, LLC`.
`entity_from_settings` matches names exactly (case-insensitive only), so an
LLC row's org id, default paid through and account picks do not reach a
charge whose card names the short form; that charge falls back to the
`/data` provisioning file or gets nothing. The fix is one choice in the
Cards tab: point each card at its LLC name, after which the three short rows
disappear from the list on their own. Needs the owner's or Criss's call on
which name is canonical; nothing to build.

### 93. The untrusted-text flag reads in English and hides what the mail said (follows ECC item 6, 2026-09-17) (SPA prompt written 2026-09-17: `docs/lovable-untrusted-flag-prompt.md`, not pasted)

PR #973 flags a receipt whose document or carrying mail contains text written
at the tool ("ignore previous instructions", "mark this as matched"). The SPA
has no i18n key for `reason_code: untrusted_instructions`, so `reviewReason`
falls back to the backend's English prose, which names the matched kinds as
machine slugs (`ignore-previous-instructions, instructs-a-status-change`).
Criss works in Portuguese, and the row does not show the quoted text the
backend already sends in `expenses[].untrusted_instructions[].quote`, so she
is told to "read it" without being shown what to read.

SPA half only (the payload is already contracted in `docs/api-contract.md`):
add `expx.review.reason.untrusted_instructions` in EN and PT, render each
flag's `quote` under the reason as quoted text (never as a link, never as
HTML), and localize the six kinds. No backend change. Low urgency: 0 of 131
live rows are flagged at deploy time.

### The 2026-09-17 voids audit (items 94-133, unranked; owner chose "append all")

Ten independent reviewers read the code at origin/main c233237f (items 82, 87
and 90 included) in a detached audit worktree, the live app read-only (GET
only; no live writes, per the standing ruling), this backlog, the status
roll-up, the API contract, the prompt ledger, the memory files and the 56
in-app feedback notes (notes #52-#54 were not yet in this file). Their 152 raw
findings were merged into 50; 30 of those were adversarially checked (three
skeptics each for critical/high, one combined skeptic for medium), and 20 were
checked by hand in code or live data after the run hit the session quota. The
eight "important function" entries (pairing engine, mailbox, self-filing,
statement reader, living month, money arithmetic, self-confirmation, the CI
gate) are protect-lines, not work, and are not items. Items are in the audit's
rank order (wrong money first), NOT ranked against items 1-93; ranking is the
owner's pass. Each carries a licence tag for the October arrangement. The open
PR first drafted these as 92-131 and PR #979 cites that draft ("audit 101",
"audit 108", "audit 130"); every heading keeps its draft number, so those
references still grep (draft N = item N+2). Draft #108 shipped in PR #979. Full
method and the two run outputs: session 2026-09-17 (memory
`project_brisken_expense_recon_voids_audit`).


### 94. The month total counts the invoice and the receipt for one purchase as two expenses (2026-09-17 audit draft #92, unranked; licence: defect, covered) (SHIPPED PR #998 + #1009, Fly v152/v155; SPA prompt `lovable-copies-out-of-totals-prompt.md` pending)

**Audit rank 1 of 40; severity critical as merged; verification: three reviewers agreed.** Stripe-style vendors mail an invoice and a receipt for the same charge. The matcher already sets the extra copy aside, but the month report and the CSV list both documents and add both into the printed total. August's report says 31 expenses, USD 2,663.95 and EUR 700.00; USD 630.09 and EUR 32.00 of that is the eleven copies the tool itself set aside, so August overstates by about a quarter. July counts an Aposto meal (EUR 80) and a Lovable invoice (USD 200) twice. The cross-month cost-center roll-up inherits the same double count. This is the first figure an accountant reads.

**Evidence:** Live 2026-09-17, read-only probe: GET /api/runs/074a7b8905d7 copies_set_aside = 11 docs; GET /runs/074a7b8905d7/expenses.csv has 31 rows with every copy present as a duplicate row (Obsidian 96.00 x2, Zoho 576.00 x2, Pressmaster 135.00 x2, Anthropic 52.59/51.38/100.00 x2 each, Lovable 15/25/25/50 x2 each, Petit Train 32.00 EUR x2). July copies 0030 Aposto 80.00 EUR and 0044 Lovable 200.00 USD both in the CSV. Code: src/expense_recon/output/zoho_expense_export.py:255-318 (build_expense_rows iterates every receipt, no copy filter); web/service.py:6449-6528 and 6851-6960 (cost-center totals sum the same rows). Backlog item 56 (lines 2450-2483): 'Nothing is dropped: the copy stays in the snapshot, the counts and the exports'.

**Already tracked:** Item 56 ruled copies stay in 'the counts and the exports' for the matching side; items 74/83 moved copies off the review to-do list only. The consequence for the printed month total and the cost-center roll-up is framed nowhere.

**Proposed change:** A document the tool has decided is a copy of another leaves the month's expense listing and its totals and appears in a short 'copies set aside' line under the listing (count, vendor, amount), with its pages behind the original's caption. The existing Not-a-copy ruling brings it back. Cost-center totals follow the same rule.

**Value:** The headline figure on the auditor-facing document becomes the real spend; today August overstates by roughly 24 percent and nobody reading the PDF can tell. (effort medium)

**Reviewer corrections:** (evidence) Figures are one receipt stale: live August is 30 expenses / USD 2,638.95 / 10 copies / USD 605.09 + EUR 32.00 (22.9 percent), not 31 / 2,663.95 / 11 / 630.09; direction and magnitude unchanged. "Framed nowhere" is overstated: docs/api-contract.md lines 985-993 and service.py 6282-6287 document the grid's totals_by_ccy summing duplicates as a deliberate contract ("honestly too high with the reason marked on the row"), with DELETE /api/runs/{id}/expenses/{doc} as the intended remedy; that framing covers the on-screen grid where the duplicate marker sits beside the row, not the PDF/CSV/roll-up, which carry no marker, and it predates items 74/83 under which the tool now decides copies itself. A  (ledger) (1) "The consequence ... is framed nowhere" is wrong: it is framed, as a deliberate ruling. docs/api-contract.md:991 says "Totals still count every row. `totals_by_ccy` sums the duplicates too. The detector's whole contract is that it flags and never drops, and a total that quietly disagreed with the rows printed above it would be worse than one that is honestly too high with the reason marked on the row", and the status file's item-33 row says "Totals still sum every row: the tool flags, the reviewer deletes." The finding should cite that and argue the premise has since collapsed: the ruling assumed a reviewer-decided group, a marker on the row, and a manual `DELETE /api/runs/{id}/expenses/ (value) (1) The live numbers moved by one row since the finding's read: today August has 10 copies / 30 CSV rows / USD 2,638.95, copies USD 605.09 + EUR 32.00 (about 23%, not "about a quarter"); the "Zoho 576.00 x2" example is no longer in the CSV, while OpenAI 80.12 (0014 copy of 0001) is a copy the finding did not list. (2) July's double count is 0.4% of EUR and 0.7% of USD (July totals USD 28,430.03 / EUR 18,087.84), so the July example is minor; August is where it bites. (3) "This is the first figure an accountant reads" is a forecast, not a realised harm: `published_runs` is 0, no month has ever been signed off, so no reader has yet received a wrong PDF; the damage lands at the first sign-off (

### 95. Rows Criss or the AI categorized print as '(uncategorized - assign)' once the row has a company (2026-09-17 audit draft #93, unranked; licence: defect, covered) (SHIPPED PR #993, Fly v151; live CSV placeholders = grid open lines, July 3 / August 2)

**Audit rank 2 of 40; severity high as merged; verification: three reviewers agreed.** The screen shows July 49 of 52 expenses categorized; the document prints 7 rows as uncategorized, August 9 against 4. The extra ones are exactly rows with a company (GitHub 10.00, Anthropic 214.20 and 180.00, OpenAI 80.12/80.04, Zoho 576.00). A half-categorized receipt (Microsoft 693.00 Software + 25.20 unread) collapses into one uncategorized row of 718.20. The reconciliation PDF prints the category for the same purchases, so the two documents disagree. Cause: the per-company chart-of-accounts check runs only inside the export and forces a category that is not a chart account back to 'needs review'. As Criss assigns cards, more rows flip.

**Evidence:** output/zoho_expense_export.py:251-253 (chart gate inside build_expense_rows only); coa_gate.py:278-330 (failing line forced to REVIEW), 167-212, 369-436 (only provisioned companies gated); output/posting_common.py:112-130 (REVIEW prints the placeholder); the grid's split depiction skips the gate (service.py:5796-5799, 5980-5992). fly.toml:30 EXPENSE_RECON_COA_PROVISION=/data/coa-provision.json. Live 2026-09-17 crosstab of GET /runs/50622baec444/expenses.csv: Corporate Services x placeholder = 5 vs grid 1; August Cloud 2 vs 0, Corporate 5 vs 2; entity-less rows never demoted. Mechanism inferred; no API exposes the run's gate config.

**Already tracked:** none. Item 23 layer 3 (lines 210-214) keeps the chart gate; Shipped row 18 made it per-company. Nothing records that the gate makes the document contradict the screen.

**Proposed change:** Make the document print what the screen shows: run the same chart check on the screen, or stop the export from demoting a categorized line and print the category with a separate 'account unmapped' note. A partly categorized receipt keeps its categorized part as its own row. Add a route-level test that walks a categorized row with a company through the CSV and fails on the placeholder.

**Value:** The accountant stops re-categorizing rows Criss already did, and the two PDFs stop naming different accounts for the same purchase. (effort medium)

**Reviewer corrections:** (evidence) (1) August is understated: live now 17 placeholder rows in the CSV vs 4 on the grid (14 grid rows that book an account print the placeholder; 13 Corporate Services, 2 Cloud Services, 2 Consulting), not 9 vs 4; the growth since the finding's morning read, with many rows at entity_source=override, corroborates "as Criss assigns, more rows flip". (2) "Mechanism inferred" is now confirmed (CSV regenerates per request; local reproduction). (3) The trigger is not "the row has a company on screen" but "the receipt object carries a stamped legal_entity_id": MultiEntityCoaGate._partition (coa_gate.py:396) keys on r.legal_entity_id, not on the export's entity_by_doc. Stamping comes from the rematch ba (ledger) (1) "already_tracked: none" is slightly too strong for one half: the placeholder-on-a-categorized-row outcome for rows Criss RE-categorizes is an accepted design in item 70's account rule ("a category edit without an explicit account stores none ... the export then books the row ... to (account unmapped - assign) with [a chart], never a guessed account"), repeated in docs/api-contract.md lines 1971-1978. What is untracked is AI-categorized, never-edited rows getting the same treatment, the screen not reflecting the divert, and the reconciliation PDF disagreeing. (2) The ledger names the wrong placeholder: on every live batch the gate is a MultiEntityCoaGate (per-entity `coa_validation.entiti (value) (1) "August 9 against 4" was true at 08:30Z; by ~10:00Z it is 17 placeholder rows against 4 on screen, after someone assigned entities on 7 rows today. (2) July's extra rows also include Parada Obrigatoria 32.00 (Meals & Entertainment, entity by override), not only GitHub and Anthropic. (3) The precise verdicts are UNKNOWN (zoho_account = the category label, e.g. "Software & Subscriptions") and MISSING_ACCOUNT (override rows with an empty account: SARL Train's, Petit Train, Pressmaster), so the gate hits the tool's own 8-category taxonomy wholesale, not a few odd accounts. (4) has_coa:false on both batch payloads is the ingest-time chart flag, not the gate flag, so it neither confirms nor re

### 96. The reconciliation PDF contradicts the screen: 47 booked charges read 'no receipt', copies read 'unmatched', no reasons (2026-09-17 audit draft #94, unranked; licence: defect, covered) (SHIPPED 2026-09-17, pending PR)

**Shipped.** Everything is read off the payload the month page renders, flat and inside item 138's card sections. (a) A charge booked without a receipt (`rows[].section` `posted`, bucket `unmatched`; one predicate, `_pdf_common.booked_without_receipt`, which `card_statement_line` now shares) leaves "What needs attention" for one line, "Already booked in your workbook: N charges with no receipt, marked already posted in the listing below.", and its Status reads `already posted`. (b) Captions (`service.reconciliation_captions`) say where the screen puts each receipt: `Copy set aside` with "copy of <original vendor> (<file>), set aside" (vendor added because live originals are often `rendered-body.pdf`), `Waiting for review` naming the charge, the tender words for settled outside, and `Receipt with no charge` with the screen's reason line; "Unmatched receipt" is gone. (c) A Why column with the screen's short labels (`unmatched_reasons.RECEIPT_REASON_SHORT`, verbatim from the SPA i18n). Real data, rendered locally from a read-only DB copy: July to-do 72 -> 24 charges (booked line 30 on 3876 + 18 on 2838 = 48), captions 31 charge / 21 "Unmatched receipt" -> 31 charge / 11 no charge / 8 waiting for review / 2 copies; August has no booked rows, captions 9 / 16 -> 9 / 10 / 1 / 5, 73 pages both before and after. Tests: `tests/test_pdfs_match_the_screen_items_96_97.py` (`test_the_reconciliation_report_uses_the_screens_status_and_caption_words` flat and per-card, `test_a_month_with_only_booked_charges_left_says_nothing_is_open`) and the status words added to `tests/test_coverage_surface.py::test_the_document_headline_agrees_with_the_screen`; regress_check red on every wire (status word 2 of 6, to-do split 3 of 6, captions 2 of 6, Why column 2 of 6). Left as is: the coverage table's "No receipt" column is the coverage panel's `n_unmatched_tx` and still counts booked charges.

**Audit rank 3 of 40; severity high as merged; verification: three reviewers agreed.** Criss colours a statement row yellow when it is in the books, and the screen respects it. The PDF does not: 'What needs attention' prints '72 charges with no receipt' for July although 47 are yellow rows, while the same page's headline says only USD 1,054.48 is unreconciled. The evidence captions call every receipt no charge holds 'Unmatched receipt', including the eleven August copies the document lists as 'Copies set aside' a few pages earlier and any receipt marked paid by bank transfer. The receipts-with-no-charge table lacks the reason the screen shows (statement not loaded, neighbouring month, not a card charge).

**Evidence:** output/reconciliation_report_pdf.py:64-82 (status from decision status and bucket only; a posted row prints 'no receipt'), 200-211 (no reason column), 213-225 and 238-255; web/service.py:7027-7046 (caption has no branch for copies or settled-outside). Live 2026-09-17 GET /api/runs/50622baec444: unmatched_transactions 72 with reason_code already_booked 47 / no_receipt_found 24 / held 1; 48 rows entry_status posted with effective_bucket unmatched; August copies_set_aside 11, unmatched-receipt reasons card_statement_not_loaded 4 / neighbouring 4 / no_charge 1 / not_a_card_charge 1. api-contract.md:495-500: posted charges carry no unreconciled money.

**Already tracked:** Items 75 and 83 (reason codes and copies, screen only, lines 3605 and 4187); item 62 shipped the month-report caption but not the reconciliation caption; item 79 collapses decided rows on screen. The PDF is named in none.

**Proposed change:** Take already-booked charges out of 'What needs attention' into their own short block ('47 charges already in your workbook') and label them 'already posted' in the listing; give the captions the screen's words ('copy of X, set aside', 'paid by bank transfer', 'charge is in the neighbouring month'); add a Why column to the receipts-with-no-charge table. Extend the route-level parity test to the PDF's status words.

**Value:** The printout matches the screen and Criss's own workbook; the to-do section shrinks from 72 rows to the 24 that are open. (effort small)

**Reviewer corrections:** (evidence) (1) August has moved since the 08:30 read: the live view now shows 114 charges, unreconciled USD 11,001.12 and 10 copies set aside (PDF prints "Copies set aside (10)"), not 11. (2) "any receipt marked paid by bank transfer" is a code-path claim only: summary.n_settled_outside is 0 on both live months, so no receipt is mis-captioned on that branch today. (3) The caption code sits at service.py ~7036-7058 (the "Unmatched receipt" label is line 7052), not 7027-7046; the api-contract sentence is at ~502-505, not 495-500. Both off by a few lines, substance unchanged. (4) The "48 rows posted + unmatched" figure includes the one receipt_held_by_another_charge row, so 47 print as already_booked on s (ledger) (1) Count: 48 July rows, not 47, are workbook-yellow and print "no receipt": 47 `already_booked` plus GOOGLE Workspace 71.64, also yellow but taking the earlier `receipt_held_by_another_charge` rule; the SPA fold reads "48 rows marked yellow in July2026.xlsx, already booked" and 72 - 48 = the 24 open the finding cites. The finding's own evidence line says 48; its title and body say 47. (2) The PDF already has an `already posted` status word; it is reachable only from the reviewer's z-key decision, so the fix is widening that branch to `entry_status == "posted"` / `turn == "posted"`, not inventing a new label. (3) Since item 83 (#932) moved copies out of `unmatched_receipts`, the PDF's "recei (value) (1) The "paid by bank transfer" caption facet is code-true (the month report at service.py:6748-6760 has the item-62 caption branch, the reconciliation caption does not) but has NO live instance: both months carry 0 settled-outside receipts today, so that half is theoretical for now. (2) The finding under-counts the caption defect: July's 21 "Unmatched receipt" captions are 11 unmatched + 2 copies + 8 receipts that are candidates of pending review rows (a review row holds no chosen_document_id, so a receipt a charge is waiting on is captioned "no charge on the statement settles this receipt"); August 23 captions = 11 + 10 copies + 2 review candidates. (3) August live state has moved this mor

### 97. July's receipt pages are captioned with the wrong expense numbers, and an unreadable amount leaves no row at all (2026-09-17 audit draft #95, unranked; licence: defect, covered) (SHIPPED 2026-09-17, pending PR)

**Shipped.** The listing and the captions come from one pass: `zoho_expense_export.build_expense_row_groups` returns the rows written per receipt (`build_expense_rows` flattens it, so the CSV is unchanged when every total read), and `build_expense_report` numbers each caption from those rows, flat, per trip or cost center, and in item 138's card sections. The width pass without the chart and the gate is gone. A receipt whose total was never read writes one row (amount blank, its lines' account or the uncategorized placeholder, vendor, date) in the listing and the CSV; the report is told its number (`amounts_unreadable`), so the row reads "amount unreadable, not in total" and the footer names it. A receipt that still writes no row is captioned `Receipt · <vendor>` with "not in the listing", never a borrowed number; rows that fail to line up keep the flat listing and say so in the closing note. File name on the caption was already shipped (item 67), not redone. Real data, rendered locally: the defect does not reproduce on today's months. July lists 50 receipts (2 copies out since item 94) as 54 rows, the old width pass also counts 54, and the Microsoft receipt is "Expenses 22, 23" (its two rows); August 20 receipts, 20 rows. A caption-to-row check over every non-copy caption (vendor and date of each named row) found 0 mismatches before and after on both months; last three July captions "Expenses 51, 52 · NATHALIA", "Expense 53 · MEGA CENTER", "Expense 54 · Redis" name their rows. Tests: `tests/test_pdfs_match_the_screen_items_96_97.py` (`test_an_unreadable_total_writes_a_row_and_every_caption_names_its_own`, `test_a_split_receipt_is_captioned_with_both_rows_and_the_next_with_its_own`, `test_inside_per_card_sections_the_unreadable_row_and_the_captions_hold`), and the two item-65 tests in `tests/test_report_totals_decimal.py` moved to the new seam; regress_check red on every wire (unreadable row 2 of 6, one-pass numbers 1 of 6, footer wiring 2 of 6).

**Audit rank 4 of 40; severity high as merged; verification: two reviewers agreed.** The report numbers listing rows and captions each receipt with the row it proves. When the listing has a different row count than the report expects (today the collapsed Microsoft row, tomorrow any receipt whose amount could not be read), it falls back to numbering receipts 1..52 while the listing runs 1..55; from the first split receipt on, every caption names someone else's purchase and rows 53-55 read 'none'. A receipt with no readable total produces no listing row at all, so it is absent from the table and the total while its page is still appended under a wrong number; item 65's 'amount unreadable' caption can never fire through the app.

**Evidence:** web/service.py:6689-6690 (row count checked against fan-out widths; any mismatch flips to fallback), 6768-6771 (fallback numbers receipts 1..N), 6693-6701; output/month_report_pdf.py:184-208. Live 2026-09-17: July grid 52 expenses, fan-out expectation 56, CSV 55 rows, so the check fails today. output/zoho_expense_export.py:341-371 (no total -> 0 -> row dropped); tests/test_report_totals_decimal.py:1-22 and 346-368 ('the drop path is unreachable from the route'). Backlog item 68 lines 2630-2637 ('wants its own item'). Live n_amounts_unreadable 0 on both months.

**Already tracked:** Item 68 records the caption finding as a leftover with no item number; item 65 (Shipped row 37) shipped the caption and counter, and its test docstring records that the real case produces no row. Neither is an open item.

**Proposed change:** Build the listing and the captions from one pass so a caption always names the rows actually written for that document, print the file name on the caption, and print a visible note rather than silently renumbering when counts disagree. Write one listing row for a receipt with no readable amount (amount blank, existing caption, vendor and date) so the footer count fires on the real case.

**Value:** Every receipt page in the PDF belongs to the row it names, and a month cannot print a total quietly short by a receipt that is physically in the PDF. (effort small)

**Reviewer corrections:** (evidence) (1) Evidence line refs: the fallback numbering is service.py:6753-6755, not 6768-6771 (that range is the reimbursements block). (2) "print the file name on the caption" in the proposed change is already shipped: live caption pages print the file name ("rendered-body.pdf") under the detail line (month_report_pdf.py caption block, `name`). (3) Mechanism is sharper than "row count checked against widths": the width pass and the row builder run the SAME receipts but only the row builder gets the chart and the COA gate, which is what collapses Microsoft's two parts into one uncategorized row. (4) The no-total case IS reachable through the app (OCR reading no total; the payload test constructs it  (ledger) 1) "print the file name on the caption" is already shipped: output/month_report_pdf.py:339-349 prints the file name (from _evidence_item's _display_name) under every caption since item 67 (PR #839); drop that from the proposal. 2) Item 65's caption is not strictly unreachable: it fires when a listing row's Amount cell fails to parse, which the ledger itself calls unreachable through the app; the accurate statement (and the ledger already makes it at api-contract line 172) is that the real case, detected_total None, yields no row because expense_posting_parts (zoho_expense_export.py:341, 369-371) coerces it to 0 and drops zero-amount groups. The payload half summary.n_amounts_unreadable does 

### 98. The month report gives no single-currency total and no conversion for foreign receipts (2026-09-17 audit draft #96, unranked; new function, quote separately) (SHIPPED 2026-09-18, PR #1076, Fly v179 - see Shipped row 85; owner reversed the quote-separately ruling)

**Audit rank 5 of 40; severity medium as merged; verification: one reviewer.** July's report closes with three totals (USD 28,430.03, EUR 18,087.84, BRL 2,361.90) and nothing that says what the month cost in one currency. The Exchange Rate column is empty on all 55 rows because scanned receipts carry no rate. A BRL supermarket slip on a USD card shows the BRL figure only; the USD amount actually charged sits in the other document, for matched rows only. The owner confirmed on 2026-09-08 that US filing applies, so the deductible figure is the USD one. The ECB monthly rate the tool now fetches reaches the screen's FX block but neither document.

**Evidence:** output/month_report_pdf.py:152-169 (per-currency totals only); output/zoho_expense_export.py:268 (rate from the receipt's own exchange_rate); live GET /runs/50622baec444/expenses.csv: Exchange Rate filled on 0 of 55, currency mix USD 21 / BRL 20 / EUR 14; reference rates only in the FX candidate block (service.py:2138-2340); docs/us-substantiation-criteria.md section 1 and section 6.

**Already tracked:** none for the documents; items 81/82/90 concern the on-screen rate and settings rates; item 48 G4 mentions conversion only as a prerequisite for the USD 75 threshold.

**Proposed change:** Add a 'USD equivalent' column and one USD total to the month report and CSV: the statement amount where a charge matched, otherwise the ECB monthly rate, with the rate and its source printed on the row and one footer note. Keep the receipt currency column.

**Value:** One figure per month for the books and the filing, traceable to the rate used, instead of three totals the accountant converts by hand. (effort medium)

**Reviewer corrections:** (combined) (1) "nothing that says what the month cost in one currency" is overstated for the run as a whole: `report.xlsx` (`output/report_xlsx.py:457-461, 580-582`) prints Spend per card and a card total summed from the statement charges in the card currency, i.e. a USD figure for the charge side, and `reconciled.csv` carries the USD charge beside each matched receipt. What is missing is a USD equivalent on the RECEIPT side (the expense report PDF and expenses.csv) and any figure for the 11 unmatched July receipts. (2) "55 rows" are expense LINES; July has 52 expenses (two-line receipts split rows). (3) The ECB rate "reaches the screen's FX block" is true only for cross-currency candidates and is iner

**SHIPPED 2026-09-18 (PR #1076, Fly v179).** Built under the owner's
2026-09-17 reversal ("we build it all and then agree on the 600 EUR license"),
which put the quote-separately items back in scope. New pure module
`output/single_currency.py`; three rungs in order of how much they know about
what happened: a USD row is itself, a receipt a reconciled USD charge settled
converts at THAT CHARGE (the money that actually left the account, spread and
fees included), anything else at the matcher's own `_reference_rate_for`.

Narrowed against the item's text in one place, deliberately: no new CSV
column. `EXPENSE_COLUMNS` is a live import contract whose target system the
owner has explicitly left open (item 23), and `Exchange Rate` already means
exactly this and was empty on all 57 live rows. Filling it carries the same
information without touching the header. If the owner wants a literal USD
column it is a one-line follow-up.

Live after deploy, read-only: **July `Total in USD: 58,187.69`** with 34 of 56
rows carrying a rate (19 at their real statement rate, 15 at the typed rate),
**August `2,808.91`**; both match the pre-build prediction to the cent. Amazon.de
reads 1.143002 off its own charge against the typed 1.162275, and the month
lands USD 14.76 below what the typed rate alone would give. The CSV was driven
live; the month report PDF was NOT, because that route writes render outcomes
into the run (item 67) and that would be a live write on Criss's month; its
rendering is pinned by route-level tests through the real app.

**An adversarial review of the diff found a dead rung and three smaller
defects**, all fixed and each proven red by hand: (1) the ECB rung never fired,
because `ecb_monthly_rate` takes a `date` or "YYYY-MM" and was handed the
listing's ISO date cell, so rung 3 had silently become typed-rates-only and a
hosted month (ECB table, nothing typed) would have read "no rate" on every
foreign receipt; (2) the CSV named rows by a listing number it does not print
and which is not the report's either, so one receipt was "expense 4" in one
document and "expense 3" in the other; (3) a blank amount parsed as zero and
took a rate; (4) rung 2 was an `elif` and blocked the fallback when a charge
implied no positive rate; (5) a rate the receipt itself printed was
overwritten.

**Correction to the item's own premise, from the review:** the two documents do
NOT always print the same total, and should not. The CSV exports every expense
while the report lists company expenses only (private ones go to their own
reimbursements section), so a month with a private expense totals differently
in each, correctly. What is shared is the per-row conversion, so one purchase
can never be converted at two rates.

Both documents stay silent unless the figure says something new: a month
entirely in USD, a month that priced nothing, and a month where nothing was
actually converted all render byte-identically to before. A month that priced
only some rows reads "Partial total", not "Total".

### 99. July reads 'Ready to post' with Publish enabled while 24 charges have no receipt and carry the tool's own 'confirm first' note (2026-09-17 audit draft #97, unranked; licence: defect, covered) (SHIPPED PR #997, Fly v152; owner ruling: ready means complete; SPA prompt `lovable-ready-publish-gate-prompt.md` pending)

**Audit rank 6 of 40; severity high as merged; verification: three reviewers agreed.** The month turns green and enables Publish as soon as nothing is left to click, not when the month is complete. July reads ready with 24 charges that have no receipt, 11 receipts that match no charge and USD 1,054.48 open, because a charge without a receipt is 'nothing to decide'. The same 24 rows carry a 'check' state whose text says 'Confirm the category or attach the receipt before it posts', with categories the model guessed from the bank line; those guesses flow into the CSV and PDF on download. The guide tells Criss 'when every charge is decided, the bar turns to Ready to post', and publishing now saves that month's corrections into memory (item 88).

**Evidence:** web/service.py:3063-3073 (only pending reconciled/review rows count as undecided), :3562-3564 (ready_to_post = n_undecided == 0 and health ok); month_health.py:1-30 (refuses only unproposed exact pairs). SPA main d08e352 SummaryBar.tsx:35, :88-91 (Publish enabled on ready_to_post; verified 2026-09-17 via gh api, mounted in RunWorkbench.tsx:1391); RunWorkbench.tsx:1669-1727; i18n.tsx:645, :89. Live 2026-09-17 GET /api/runs/50622baec444: ready_to_post true, n_undecided 0, n_unmatched_tx 72 (turn none 24), n_unmatched_rec 11, unreconciled USD 1,054.48; 24 rows review.reason_code receiptless_suggested, charge_category.source VENDOR. /api/settings export_approved_only false.

**Already tracked:** Item 57 (2491-2502) fixed the zero-match case only; item 89 (4549-4569) renames the months-list badge for the same reason but leaves the pill and the Publish gate; item 76 (3702-3706) notes sign-off gates only this tile. The readiness rule ignoring receiptless charges is not tracked.

**Proposed change:** Split readiness into 'nothing left to decide' (today's rule, a caption) and 'month complete' (no open charge without a receipt unless it carries a verdict such as settled outside or no receipt expected, no receipt without a charge unless set aside). The green pill, the guide sentence and the Publish button key on the second, and a receiptless charge whose category is still a machine guess counts as undecided until confirmed. July then reads amber with '24 charges still need a receipt'.

**Value:** Criss cannot sign off a month missing 24 receipts by trusting a green bar, no guessed category reaches the books under a green light, and memory is taught only from finished months. (effort medium)

**Reviewer corrections:** (evidence) (1) The merged sub-claim "the month sign-off sits on a page nothing links to" is wrong: MonthHeader.tsx:111-121 renders a Matching tab linking to /runs/$runId whenever has_statement is true (/months -> /expenses/{id} -> Matching -> SummaryBar with Publish); drop it. (2) "CSV and PDF": the guess reaches reconciled.csv, report.xlsx, the writeback and the reconciliation-report PDF, but NOT the month expense-report PDF (month_report_pdf.py has no receiptless charge rows) and NOT the Zoho journal (receiptless VENDOR guesses are withheld there; only LEARNED with an opt-in flag). The cited export_approved_only=false is not load-bearing: that flag filters only the Zoho journal's matches, none of the (ledger) (1) The merged sub-claim "the month sign-off sits on a page nothing links to" is wrong for the live months: item 79 records that `/months` sends every statement month to `/runs/{id}`, the workbench where `SummaryBar` mounts Publish; the page reachable only by URL is the Review expenses page of a statement month, not the sign-off. (2) "Those guesses flow into the CSV and PDF" is by design and labelled, not silent: the reconciled CSV carries receiptless-charge categories in their own "Charge Category" / "Charge Category Source" columns (Slice 10, `reconciled_csv.py:126-130`; status row "Web-download exports carry Tier-2 receiptless categories", PR #294), and the reconciliation PDF prints `post (value) (1) July's 24 receiptless rows are ALL gray "subscription" rows in Criss's own July2026.xlsx (entry_status subscription: Anthropic x9, Network Solutions x3, COMPUTER x4, Lovable x2, OpenAI, Adobe, Microsoft, Proton, Base44, ENT PRO); her walkthrough says gray = subscription, "já estão no recurring". "24 charges still need a receipt" overstates July; July has zero uncoloured receiptless charges. (2) "No guessed category reaches the books under a green light" is wrong as stated: readiness gates nothing that produces a document. The PDF button in SummaryBar, the CSV, the XLSX and the writeback are all ungated, so the proposed readiness change would not keep a guess out of them. The real gap the

**2026-09-17 night, owner ruling (PR #1020, Fly v158): a GRAY workbook row (Criss: "já estão no recurring") closes the receipt requirement like a yellow one, and its guessed category no longer counts.** `summary.n_charges_closed_recurring` shows them; a subscription mark derived from history (`entry_status_source: "derived"`, CLI only, the hosted app never derives) closes nothing. Live after deploy: July need-receipt 24 -> 0, closed 24, still incomplete on 11 receipts without a charge; August 100 -> 61, closed 40 (the gray ANNUAL MEMBERSHIP FEE included, guessed 1 -> 0). SPA prompt applied and driven the same night.

### 100. Publish is the sign-off in name only: no readiness check on the route, nothing frozen, nobody recorded, and /classic publishes any run (2026-09-17 audit draft #98, unranked; licence: defect, covered) (SHIPPED PR #997, Fly v152; owner ruling: gate only, no frozen copy; same SPA prompt)

**Audit rank 7 of 40; severity high as merged; verification: checked by hand in code (publish route has no readiness check; no reviewer pass).** Publishing sets a flag and saves the month's corrections to memory, then stops. The route accepts any month (August with 7 open decisions, a month whose health says broken); the SPA gates its own button but the legacy /classic page (reachable by URL, listing three July test runs with 94 charges each) publishes with one ungated click, which would teach memory from test data. After publish every edit, re-match and arriving receipt still changes the month, every PDF and CSV is rebuilt from live state at download, nothing stores who published, and Unpublish clears the flag but leaves what the publish taught. No month has ever been published, so the first real sign-off is the first test.

**Evidence:** app.py:1222-1248 (publish: flag + commit_month_memory, no readiness check, no snapshot), :1250-1260 (unpublish flag only); store.py:502-509 (bool + timestamp, no operator); grep '.published' in app.py/service.py: only app.py:1228, 1256, 1388, 1416, no route or re-match reads it; download routes app.py:3901-4130 regenerate. SPA routes/classic.tsx:6-24, OperatorDashboard.tsx:306-323 (Publish disabled only while pending). Live: published_runs [], operator_runs includes f639bef7813a / 1e09b8362948 / b67133b8df98 (2026-07-20/24). docs/electronic-storage-system-description.md section 12 rows 2 and 9; docs/us-substantiation-criteria.md G6; api-contract.md:2624.

**Already tracked:** Item 88 (4506-4548) made Publish the sign-off and is shipped; item 48 G6/G2b frames retention and stamping. Nothing tracks that publish freezes nothing, records no person, leaves learned rules on unpublish, or that /classic bypasses the gate.

**Proposed change:** Refuse publish server-side unless the month is ready (F07's rule) or the caller says it is overriding, record who and when from the session label, store the two PDFs and the CSV at sign-off and serve those for a published month, show a 'reopened' notice when anything changes after publish with the option to publish again, make Unpublish say whether it unlearns, and retire /classic (redirect to /months). The gate is closing a hole in the existing sign-off; the frozen copy is new function to quote separately.

**Value:** Brisken can point to the exact document that was signed off, a month cannot close by accident with decisions open, and test data cannot be published into the real memory. (effort medium)

**Reviewer corrections:** none recorded

**2026-09-17, the three legacy test runs are gone (owner yes, this session).** f639bef7813a / 1e09b8362948 / b67133b8df98 (card 2838 statement + April 2026 Zoho expense-report lines, 94 charges each, no receipt images, no mail behind them) were deleted through the typed-confirm route after a read-only readiness check (unpublished, no borrowed or lent receipts, July/August referencing none). Each id now 404s; `pooled_back` 0; learned memory kept. /classic can no longer publish them.

### 101. One click on 'Confirm all matched' or 'Reject N shown' commits up to 1,000 rows with no dialog, using a looser rule than the owner set (2026-09-17 audit draft #99, unranked; licence: defect, covered) (SHIPPED 2026-09-17, pending PR; SPA prompt `lovable-bulk-confirm-dialog-prompt.md` not applied) (SPA APPLIED + VERIFIED 2026-09-17 night: owner published, cold-driven EN and PT, 0 writes; see PROMPT-STATUS)

**Audit rank 8 of 40; severity high as merged; verification: checked by hand in code (bulk confirm reads the raw matched list; no reviewer pass).** 'Confirm all matched' confirms every pending row in the matcher's raw matched bucket in one click. It does not apply the owner's self-confirm rule (exact pairs only, vendor agreement 75 or more, not held by another charge, not rejected), so a vendor-40 exact pair of the Base44/Lovable kind would be booked by that click. 'Reject N shown' rejects every open row in the current view the same way. Both reverse only one row at a time, and nothing records that a bulk action happened. Raw and effective matched sets coincide on both live months today, so the damage is potential.

**Evidence:** SPA main d08e352 SummaryBar.tsx:66-75 -> RunWorkbench.tsx:1394 -> app.py:2425-2456 -> web/service.py:1413-1434 (matched_autopick_decisions reads outcome.matches raw, skips only decided rows). Self-confirm rule: service.py:11473, docs/api-contract.md:2399-2440 (owner ruling 2026-09-16). Bulk reject RunWorkbench.tsx:1014-1024, :1504-1532 -> app.py:2501-2558, _BULK_DECISION_LIMIT = 1000 (app.py:561). Live: July n_reconciled 31 = raw 31, August 8 = 8.

**Already tracked:** Item 76 (3649-3805) set the narrow self-confirm rule and names ready_confirm_pairs as the safe selection; the older confirm-matched route and the two bulk buttons were not brought under it. No item covers a dialog on bulk actions.

**Proposed change:** Make the one-click confirm use the same selection the tool uses to confirm rows by itself (or the effective reconciled rows with no review flag), put a short dialog in front of both bulk buttons naming the count and the rule, and record the bulk action as one history entry (F27).

**Value:** A stray click can no longer book wrong pairs into the reconciliation report or wipe a view's open work; the buttons match the rule Dirk approved. (effort small)

**Reviewer corrections:** none recorded

**Shipped 2026-09-17 (pending PR):** 'Confirm all matched' confirms only rows passing the pairing half of item 76's rule (`service.confirmable_pair`, shared with the self-confirmation): pending, `turn: decide` (never booked), reconciled, one candidate, chosen, exact, not flagged for review, vendor 75 or more, not borrowed / held / rejected, intersected with the matcher's pending auto-pick. The category is not part of it (a person pressed the button; the category keeps its own question), and the writes are ordinary reviewer confirms. The route reads the payload `GET` serves and answers `{ok, confirmed, remaining, skipped_rule, summary}` with the per-call cap; `summary.n_confirm_matched` is the same count, for the dialog and the disabled button. The bulk route's confirm now skips a booked row too; confirm-ready never could (a booked row is never `ready`). Live before, read-only: July's button would have confirmed 27 rows, all yellow; August's all 7 open pairs, among them BASE44 50.00 at vendor 40, two `fx_reference` pairs, one `probable` pair and vendor 62/67 exact pairs. Tests: `tests/test_confirm_matched_rule.py` (10: booked row, vendor 40, fx and probable, clean pair with category `check`, a reviewer's reject kept, count equals what is confirmed, cap remainder, bulk confirm skips booked, confirm-ready never confirms booked, a real re-match month), `test_view_contract.py::test_confirm_matched_count_is_an_int_inside_the_undecided_set`; `test_web_app.py`'s confirm-all test now pins the rule (the example month's Uber 62 and Amazon 61 stay open). SPA half (count badge, dialogs on both bulk buttons): `docs/lovable-bulk-confirm-dialog-prompt.md`. Not built: a history entry for a bulk action, item 104, quoted separately.

### 102. A yellow row hides a missing receipt: 47 July charges worth USD 3,385 leave the gap figure (2026-09-17 audit draft #100, unranked; licence: defect, covered) (SHIPPED - see Shipped row 58; SPA prompt written)

**Audit rank 9 of 40; severity high as merged; verification: checked by hand against the live July payload (47 rows, USD 3,385.47); no reviewer pass.** Criss colours a row yellow when she has keyed it into Zoho. The tool reads that as done in every sense: the 47 July charges that are yellow but have no receipt are folded away as already booked, leave the open work, and are not counted in the month's unreconciled money (USD 1,054 shown; USD 3,385 more is receiptless but yellow). Booked and evidenced are two different questions, and the month's headline no longer answers the second.

**Evidence:** Live July 2026-09-17: reason_code already_booked 47 rows, sum USD 3,385.47; unreconciled_by_ccy USD 1,054.48 covers the 24 no_receipt_found rows only; n_already_posted 85. web/service.py:7974 (entry_status posted = already-posted); SPA RunWorkbench.tsx:358 folds section posted as decided. Memory project_brisken_expense_recon_chris_process: yellow = entered in Zoho, nothing about a receipt. docs/us-substantiation-criteria.md (item 48) ranks receipt thresholds as live gaps.

**Already tracked:** Item 86 (wording of 'already posted in your workbook') and item 48 touch the edges; no item names the effect of the yellow fold on the receipt gap figure.

**Proposed change:** Keep the fold for the books view, add a separate 'booked without receipt' count and amount on the month, and put those rows into the missing-receipts list (F16) beside the unposted ones. The unreconciled figure stays as is; the new number sits next to it.

**Value:** The month tells the truth about evidence, not only about bookkeeping, and the receipt chase covers the money that is actually uncovered. (effort small)

**Reviewer corrections:** none recorded

**Shipped 2026-09-17:** `summary.n_booked_no_receipt` + `summary.booked_no_receipt_by_ccy` on the review payload count yellow rows no receipt settles (`effective_bucket: unmatched`), beside `unreconciled_by_ccy`, never inside it. Live July before the change: 48 such rows (47 `already_booked` + 1 whose receipt another charge holds); 8 more booked rows wait in review with a candidate and are not counted. Not built: the missing-receipts list (item 107, new function). SPA half `docs/lovable-booked-no-receipt-prompt.md`.

### 103. One receipt can be bound to two charges, so the months list, the change log and the month page disagree (item 72, live today) (2026-09-17 audit draft #101, unranked; licence: defect, covered) (SHIPPED 2026-09-17, pending PR)

**Audit rank 10 of 40; severity high as merged; verification: three reviewers agreed, severity lowered to medium.** When two receipts tie for a charge, the tool sets that charge aside for a human pick but leaves its receipts free, so the same receipt is also handed to another charge in the same pass. The stored numbers (months list, re-match notifications, cross-month claim table) count the second pairing; the screen, PDFs and CSV drop it, and which charge keeps the receipt depends on statement row order, not score. Live: August's Anthropic 52.59 invoice is stored as matched to the 52.46 charge (score 93) while the screen shows it held by the undecided 50.52 pick (score 83) and reports 52.46 as 'no receipt'; the list says 9 matched, the page 8; July list 9 review / 71 unmatched / 13 receipts vs page 8 / 72 / 11. Item 72 said round B would dissolve this instance; it did not.

**Evidence:** matching/deterministic.py:1681-1694 (tie detection: 'receipts they tie over are left free'), :1696-1718 (greedy pass does not exclude tied receipts); web/service.py:1261-1405 (apply_decisions resolves by transaction order), :10097-10116 (claims from raw matches), :10231, :10263-10280, :5683-5735 (batch_list_summary re-derives only n_expenses/n_receipts/n_categorized); app.py:1416-1420, :3013-3045. Live 2026-09-17 August row 6d474e9e8e964bd4 initial_bucket matched / effective unmatched, candidate 0023 held_by c632cb75a5098253; stored n_matched 9 vs run n_reconciled 8; July stored n_review 9 / n_unmatched_tx 71 / n_unmatched_rec 13 vs run 8 / 72 / 11. Backlog item 72 lines 3328-3360. No test compares list and page counts.

**Already tracked:** Item 72 (OPEN), framed as a persistence decision deferred to 'when round B lands'; round B shipped 2026-09-15 without closing it, so it is unowned, and the matcher-level cause (a tied receipt stays free) is not named.

**Proposed change:** A receipt in a human-pick tie is not free for the rest of the pass (or goes to the clearly stronger pairing when the weaker one is undecided), so one receipt is never bound to two charges; then persist the effective outcome so the list, the notification mail and the claim table report the same numbers the page shows. Add one test that opens the list and the page for one month and fails when counts differ. Replay on both labelled months.

**Value:** The count on the months list and in the notification mail becomes the count Criss sees, and one real August expense stops being reported as undocumented. (effort medium)

**Reviewer corrections:** (evidence) (1) The August figures are stale: live is list 8 matched / 101 unmatched vs page 7 / 102 (not 9 vs 8); the one-row delta is what persists. (2) The receipts delta (July 13 vs 11, August 21 vs 11) is the duplicate copies set aside (page n_copies_set_aside 2 / 10), a separate raw-vs-effective split, not the tie. (3) The workbench no longer reports 52.46 as "no receipt": a 2026-09-16 fix (service.py ~2882-2891, which names this exact instance) labels the row receipt_held_by_another_charge with the holder named and counts it in n_charges_receipt_taken (=1); only the PDF/CSV builders, which have no held_by state, render it as plain unmatched. (4) No mail carries these counts: intake_mail.py has no (ledger) (1) "The matcher-level cause is not named" is overstated: the ledger names it precisely, three times, just without an item number or owner. Backlog item 69 round-B review (lines 3094-3101): "0023 is stopped by pass-1 AMBIGUITY detection (`_ties` over deterministic candidates), a different mechanism the gate never reaches. Extending 'spoken for' into tie detection is a real and probably correct change; it is not in round B's scope and was not made." Same in memory project_brisken_recon_matching_program.md ("is its own round") and the loop brief p1-recon-loop-prompt.md:255-259. Unowned, yes; unnamed, no. (2) The ledger's fix pointer differs from the finding's: the ledger would DISSOLVE the tie (value) (1) The SPA does not report 52.46 as "no receipt": the live row has section "attention", reason_code receipt_held_by_another_charge and its candidate carries held_by -> 50.52; the reconciliation PDF headline reads n_reconciled (effective), not the stored n_matched. (2) "The matcher-level cause is not named" is wrong: the matching-program memory and p1-recon-loop-prompt.md lines 255-259 name it (pass-1 ambiguous tie, uniqueness gate never reaches it, extend spoken-for into tie detection); only backlog item 72's last paragraph is stale on round B. (3) The "notification mail" with raw counts is the dev-side tools/brisken-recon-notify.py polling rematches[] and mailing Matthias; Criss and Dirk n

**Shipped (2026-09-17, pending PR).** The rule as built, both halves in pass 1
of `matching/deterministic.py`. (1) **Held:** every receipt a tie lists is held
by it, so the greedy pass skips it, the way `apply_decisions` already holds it
for the pending pick (the item's fix A). (2) **Spoken for:** before the tie is
taken, a tied receipt that holds a CLEAN exact candidate on another charge,
while its own candidate here is not one, no longer sustains it
(`uniqueness_spoken_for`, round B's rule carried into tie detection, the
ledger's fix B); under two tied receipts left, the charge is not ambiguous and
goes to the assignment like any other. B only ever dissolves a tie, never
creates one, and clean matters: the card pass leaves a cards-differ exact at
confidence 0.55, below every clean deterministic candidate, so it is not the
stronger claim elsewhere the rule reasons from.

The labels decided which of the two leads. August's `0023` is `excluded`, and
the note says why: "no charge of 52.59; eight ANTHROPIC charges between 50.52
and 54.12 within two days; ambiguous". Neither `6d474e9e8e964bd4` (52.46) nor
`c632cb75a5098253` (50.52) carries a labelled receipt. So no evidence makes
either pairing right, and the outcome the labels support is the one where a
human picks: A is what keeps the pick a pick. B is in for the receipt that IS
spoken for, `0021` (exact to ANTHROPIC 51.38, the label's verdict carried by
its copy `0022`): without it, A would hold `0021` in a tie it cannot win and
the month would lose a real, bank-printed pairing. Two exact twins over two
identical charges are each other's equal, so neither is spoken for there and
both charges keep waiting for a human (live July, below).

**The live instance has moved since the audit, and the ledger's `0023` case is
gone for an unrelated reason.** On a DB copy pulled 2026-09-17 19:46 (after Fly
v167), August holds no tie at all: `0023` now carries a resolved card (hint,
Visa ...3645, item 137), so its card signal is 0.75 against `0021`'s 0.5, the
two no longer tie on 50.52, and `0023` is a plain probable match to 52.46 (93)
that the label cannot verify. August's list and page already agree: 9 matched /
1 in review / 101 unmatched / 3 refunds on both. What remains live is JULY's
shape, which is the same defect one bucket over: the two GOOGLE *Workspace
71.64 charges of 07-01 (`b7abd111d69921a3` and `b7abd111d69921a3-1`) each tie
over BOTH `0036` and `0037`, so each receipt is listed on two charges; the
effective layer gives both to whichever charge comes first in statement order
and the second reads unmatched with its candidates held. Stored and list: 8 in
review / 72 unmatched. Page: 7 / 73. Same month, same day, two screens.

**Persistence half, built.** `service.effective_charge_counts` (apply_decisions
then `charge_states`) is the one derivation, and `bucket_counts` names its
buckets in the stored summary's vocabulary. `batch_list_summary` re-derives the
four charge counters and `match_rate` on READ, so a confirm or reject taken
after the re-match moves the list too; the re-match commit writes the same
counts into the stored summary, the `rematch_log` event the notifier mails and
the reply the drop page shows, and `execute_run` does the same at creation.
`n_unmatched_rec` and `n_receipts_matched` stay as the match stored them: the
receipts delta is the copies-set-aside split (reviewer correction 2), a
different question with a different fix. Contract updated in
`docs/api-contract.md` ("The four charge counters count the effective verdict",
plus a line on `rematches[]`).

**Measured before (origin/main `8fc84dec`) and after, one DB copy, one tool
(`tools/recon-match-attribution.py`, `RECON_MODULE_SRC` naming each tree).**
Both live months and the six scorer bundles: class tables byte-identical, and
per row, 0 of 79 live receipt rows and 0 of 218 bundle rows changed class or
bucket. The parity block is identical too, so the pairings the next live
re-match will write do not move. Pinned scorer and guard, identical on both
trees: train 56.8, holdout 19.2, all 76.0, determ_ok 70/95, determ_wrong 0,
nc_matched 0, invariant OK, guard 4/4 PASS. The matcher half changes no month
anyone holds today; it closes the mechanism that produced the August case and
would produce the next one.

List against page, measured by calling `batch_list_summary` and `build_view` on
the same DB copy: July before, list 31 / 8 / 72 / 1 against page 31 / 7 / 73 /
1; after, list 31 / 7 / 73 / 1, the page's own numbers. August 9 / 1 / 101 / 3
on both screens, before and after. Across all six runs in the store those two
July numbers are the only ones that move, and the months with no statement keep
their empty counts.

**Tests:** `tests/test_tied_receipt_item_103.py`, six. Three pin the matcher's
shapes (the tie dissolves for a spoken-for receipt and both charges land; a
surviving tie holds its receipts and the rival charge goes unmatched with no
receipt named twice; two exact twins stay a human pick). Three run through the
routes: upload, statement attach, then `GET /api/expense-batches` against `GET
/api/runs/{id}` on the twin shape (one in review, one unmatched, counts equal
on both screens, and the re-match event carrying the same numbers), and a
reject that moves both screens. regress_check red on four wires: the tie
dissolve (2 of 6), the greedy skip (1 of 6), the list derivation (1 of 6), the
commit's effective `n_review` (1 of 6). Suite 2268 -> 2274 (2272 passed, 2
skipped); ruff clean on the diff.

**Predicted live change at the next deploy:** the months screen's July row
reads 7 in review and 73 unmatched instead of 8 and 72, which is what the
workbench has been saying; no re-match is needed for that and no pairing moves
anywhere. The next re-match of either month then stores and mails the effective
counts rather than the raw ones.

**One contract moved with it.** `tests/test_same_amount_other_merchant_item_133.py::test_the_rule_never_breaks_a_tie_a_person_should_settle`
(item 133's bulk-confirm half, PR #1036) pinned the raw outcome where a charge
outside the tie still took a tied receipt. The page never rendered that pairing
(`held_by` gave the receipt to the pick and labelled the charge "receipt held by
another charge"), which is precisely the raw-vs-effective split this item
closes, so the test now asserts the held outcome. The cost is named: while a
pick is open the other charge waits, and the freed receipt reaches it at the
next re-match, because a decision does not re-match a month. No live row is in
that shape on either month or the six bundles.

**Not built.** Round-B vendor dominance as a second spoken-for basis: no tie in
either live month or the six bundles would use it, and a dominance-kept
rate-derived pair is not provably stronger than a same-currency tied candidate,
so it would widen the rule on a hypothesis. Twin-charge auto-pairing: two
identical charges with two equally fitting receipts stay a human pick rather
than being paired by row order, which is the matcher's standing rule against an
arbitrary assignment. The receipt-side counts (`n_unmatched_rec`,
`n_receipts_matched`) still differ between list and page by the copies set
aside. `cli.py` and `runlog` keep the raw counts; they are not the web
surfaces this item is about. And `execute_run`'s own wire has no test that
bites it: the shape where its raw and effective counts differ (a tie holding
another charge's only receipt) does not arise on the classic intake path the
suite exercises.

### 104. Every decision overwrites the previous one, nobody's name is on it, and one shared password is still live with sessions that never expire (2026-09-17 audit draft #102, unranked; new function) (HISTORY HALF SHIPPED PR #1081, Fly v180, see Shipped row 86; CREDENTIAL HALF DECLINED by the owner 2026-09-18, do not re-ask)

**Audit rank 11 of 40; severity medium as merged; verification: one reviewer, plus no-expiry confirmed by hand.** A confirm, reject, undo, category change or duplicate ruling replaces the previous value in place; there is no timeline and no way to see that a bulk reject or a re-match changed forty rows since yesterday. The tool knows 'tool' versus 'reviewer' but not which person: named login codes exist and carry a label, yet the label is written only on feedback notes and the month's operator column comes from the server's environment. Criss logs in with the shared code, so her notes read 'operator' while the developer's read 'matthias'; the sign-off memory cannot say who taught it. The original shared code is still accepted beside the named ones, the laptop script uses it, and a session once issued is valid forever; revoking one person means rotating the signing secret, which logs everyone out.

**Evidence:** store.py:969-1000 (set_decision INSERT ON CONFLICT DO UPDATE, no history), :234 (decided_by tool/reviewer); auth.py:15-18, :20-28 (legacy shared code and named codes both honored), :89-109 (token = label + signature, no expiry); app.py:200-205 (_operator() from env, used at 1120, 1192, 2963, 3402), :672 (token label used only for feedback 1462-1500); live /feedback.jsonl #35 (Criss) operator 'operator', #52 operator 'matthias'; flyctl secrets list: EXPENSE_RECON_OPERATOR_CODE and _CODES both deployed; tools/brisken-recon-notify.py:30; OWNERSHIP-HANDOFF.md:367-373, :490-495, :542. Backlog grep 'audit trail' / 'who decided': 0.

**Already tracked:** Item 48 lists record-keeping gaps generally; item 78 is one concrete irreversible edit; OWNERSHIP-HANDOFF step 8 / decision 4 (per-person sign-in is TARGET-ARCHITECTURE P3). No backlog item for a decision history, Criss's named code, or session expiry.

**Proposed change:** Append one line per change to a month-level history (row, old value, new value, who from the login label, when, trigger: click, bulk, re-match, tool) at the four write points, shown as a collapsed 'History' fold with per-line undo where undo exists. Hand Criss her named code (it is in the vault), switch the tooling to a named code, delete the shared code, rotate the signing secret once outside close week, and put an expiry inside the signed session. Per-person sign-in stays separately quoted.

**Value:** Dirk can answer 'who confirmed this and when' for any figure, a wrong bulk action or re-match is visible and reversible, and access can be taken from one person without disturbing the others. (effort medium)

**Shipped 2026-09-18 (PR #1081, Fly v180), the decision-history half.** An
append-only `decision_history` table beside the decisions, a pure
`web/decision_history.py` (what a line is, whether a write moved anything, how
it reads, what putting it back means), `GET /api/runs/{id}/history` (newest
first, `limit` / `before_id` / `row_key`) and
`POST /api/runs/{id}/history/{entry_id}/undo`. `who` is the label inside the
SIGNED SESSION TOKEN, never `_operator()`, which reads the server's
environment and is why Criss's notes read `operator` while the developer's
read `matthias`. Three rules: only writes that actually moved a value get a
line (a re-match writes every charge on the month); values that must move
together ride one line (a status and its chosen receipt, so an undo cannot
half-revert a row); an undo appends its own line and stamps the original,
never erases. **The item's text said "four write points"; enumerating every
`set_decision` / `set_disposition` / `set_category_override` /
`set_duplicate_resolution` call in `src/` found TWELVE**, three of which were
reviewer-driven and would have shipped silent (note #62's confirm-the-guess,
the expense-field category edit, and the manual receipt attach, which records
a confirmed decision). Not recorded, deliberately and documented:
`set_tool_decision` (the matcher's own re-match writes) and header-field
corrections (vendor, date, total), a data edit rather than one of the five
verdicts the item names. The undo is refused with `history_superseded` unless
the row still holds exactly what that line left there, and it re-runs the R4
cross-run claim check. A duplicate ruling is recorded but has no one-click
undo: reversing it has to re-match the month (item 56), so it is reversed by
making the opposite ruling. An adversarial review of the committed diff
returned fifteen findings; the one that mattered was a DATA-LOSS defect
(`_category_value` collapsed "no override" and "an account with no category"
to the same value, so an undo of a stale line compared equal to a row that
had moved and destroyed the later account pick, and an account-only pick
recorded no line at all). Fixed with seven tests written before the fixes and
watched go red then green; three of the original tests did not bite and were
rewritten. 36 tests in `tests/test_decision_history_item_104.py`, zero skips,
route-level through the real app with two named operator codes; nine wiring
points proven red by hand (`regress_check.py` is not used here: it reports
"RED (no pytest summary line)" even for a green suite); module suite 2476
passed / 2 skipped, exit 0; ruff clean. **Not built:** the SPA's collapsed
History fold and its per-line Undo button
(`docs/lovable-decision-history-prompt.md`, EN + PT, NOT pasted), and the
machine's own re-match writes. **Owner ruling 2026-09-18: the credential half
(Criss's named code, deleting the shared code, rotating the signing secret,
session expiry) is left entirely for now, do not re-ask.** Lines written from
a shared-code session read `operator`, which is the truth about a shared code
rather than a bug. Live months untouched: the history starts empty on every
existing month, which is the honest answer for a period nothing recorded.

**Reviewer corrections:** (combined) (1) "already_tracked" understates the ledger: item 48 does not list this "generally", its G2b/G11 gaps and the round-2 line "a ledger row for every edit and every deletion" name this exact change, and the storage-system description ranks the attribution/audit-log gap Highest; the backlog-file grep of 0 hits is literally true but the item-48 docs it points to contain both phrases. (2) OWNERSHIP-HANDOFF step 8 already IS the plan for handing Criss and Dirk named codes, deleting EXPENSE_RECON_OPERATOR_CODE and rotating the secret once, so that half of the proposal is a pending owner/ops action, not an untracked void. (3) The cited file is web/store.py, not store.py (hosting/store.py is a differ

### 105. Two real July invoices were filed as 'statement pages' and are missing from the month (2026-09-17 audit draft #103, unranked; licence: defect, covered) (SHIPPED PR #1037, Fly v165, see Shipped row 67)

**Audit rank 12 of 40; severity high as merged; verification: three reviewers agreed (F36 half: one reviewer).** The reader that decides whether a file is a receipt judged an 11-page AWS invoice (USD 3,352.59, invoice 2704896057) and a consultant invoice (Rodrigo Tanure Tricarico, BRL 27,203.34) to be bank statement pages. Both sit in July's set-aside list, neither became an expense, so the July report and its totals omit them. The only trace is the set-aside strip, which cannot be opened (F36), and the intake row reads 'Added'. Nothing on the months list counts what was set aside.

**Evidence:** Live GET /api/expense-batches/50622baec444 set_aside[] read 2026-09-17: 0015__2026-07-01__BRISKEN_CLOUD_SERVICES__AWS_-_Amazon_Web_Services__Invoice_2704896057.pdf and 0017__...Rodrigo_Tanure_Tricarico...Invoice_20_2318.pdf, reason 'statement', restored false; neither amount appears in the July or August run payload. Code: web/service.py:8928-8935 excludes any file the model labels statement / report_summary / other; llm/client.py:434-440 is the classification prompt; docs/api-contract.md:168 has summary.n_set_aside but no months-list count. tests/test_document_type_quarantine.py pins the mechanism, not this false-positive class.

**Already tracked:** Item 3 ('put the set-aside statement pages to work', assumes they ARE statements, unscheduled); item 52 covers only the row viewer; item 4 mentions restore. The false-quarantine class is untracked.

**Proposed change:** Treat the model's 'statement' verdict as a suggestion when the document prints an invoice number, a 'total due' or 'total for this invoice' line, or a single vendor: keep it as a receipt with a 'check: read as a statement page' note instead of excluding it. Put the set-aside count on the months list. The two July invoices need a restore click by Criss.

**Value:** USD 3,352.59 and BRL 27,203 of real July cost stop vanishing from the month report; exclusions become visible instead of being found at audit time. (effort medium)

**Reviewer corrections:** (evidence) (1) "Nothing on the months list counts what was set aside" is wrong at the API level: GET /api/expense-batches list rows carry summary.n_set_aside (July 4, September 3), matching api-contract.md:168; only the SPA rendering is unverified. (2) "The only trace is the set-aside strip, which cannot be opened": the API serves the set-aside file (both PDFs returned 200 via /image); the open failure is the SPA View-receipt half (item 52), and the add-time ingest summary `issues` announced the exclusion ("looks like a bank/card statement page ... excluded"). (3) Value claim overstated: the Tricarico invoice is a wire transfer and the AWS 3,352.59 has no charge on the loaded July statement, so restori (ledger) (1) "Nothing on the months list counts what was set aside" is wrong on both halves: `GET /api/expense-batches` already carries `batches[].summary.n_set_aside` (service.py `batch_list_summary` ~8686-8699; live July 4, September 3), `docs/lovable-months-list-prompt.md` line 74 specifies a "Set aside" column, and the SPA's `src/components/MonthsHome.tsx` renders it (`s.n_set_aside`, `months.col.setAside`, lines 301/340/496). Drop that part of the proposal. (2) "Cannot be opened" is an SPA-strip gap only: the API serves both files 200 on the runs route (the batch route `/api/expense-batches/{id}/receipts/{file}/image` 404s); the strip has no view control, which is note #52 (untracked). (3) July' (value) (1) "Nothing on the months list counts what was set aside" is wrong at the API: GET /api/expense-batches already returns summary.n_set_aside per month (July: 4); only the SPA's rendering is unverified, so that half is at most a Lovable prompt line, not backend work. (2) The two files arrived by drop, not mail: no inbound-log entry exists at 2026-09-08T20:15Z, so "the intake row reads Added" does not describe them; the 09-08 "excluded" issue text is gone because expense_ingest keeps only the last add (2026-09-12). (3) The finding undercounts: a third July invoice (Microsoft G173514057, USD 718.20) got the same verdict and, once restored, matched a real card charge, which is stronger evidence 

**Folded in (F36): Set-aside files cannot be looked at, so Criss decides 'is this a receipt?' blind (note #52).** When the tool sets a file aside as a statement page or 'other', the strip shows the file name, the reason and one button, 'This is a receipt, restore'. There is no way to open the file. The owner's note: 'need to be able to view these, or else user has really nothing to go by'. A wrong restore turns a statement page into an expense with an amount; a wrong non-restore loses a real receipt (F02's two invoices are exactly this). The backend already serves these files through the existing receipt viewer route, so this is a front-end button. Evidence: web/service.py:8516-8530 (set_aside_view: file, display, reason, restored, at; no URL), :8603 (files in the same receipts folder); app.py:2738, :2782-2796 (image route resolves receipts/{document_id} inside the batch dir). SPA main d08e352 ExpensesReviewGrid.tsx:2980-3060 (SetAsideStrip: name, reason, Restore only), :815-819. Live July set_aside 5 entries (4 unrestored), September 3; feedback note #52 (2026-09-16T22:23Z, /expenses/50622baec444). PROMPT-STATUS.md:43 records the row-level viewer as applied. Proposed change: Add a 'View' button on each set-aside row that opens the existing receipt viewer on that file (same dialog the expense rows use), with the reader's reason beside it, in EN and PT. One Lovable prompt, no backend change. Verify by opening one July set-aside file in the browser. Reviewer corrections: (combined) Minor: /feedback.jsonl now holds 56 notes, not 54 (two arrived after the 08:30 read; note #52 is still index 51 and unchanged). The finding's numbers otherwise check out: July 5 set-aside entries with 4 unrestored is exactly the live payload; `summary.n_set_aside` reads 4. The proposal's "no backend change" is accurate since the image route already resolves `receipts/{file}` for expense batches.

**2026-09-17, note #52 backend half shipped (PR #988, Fly v150).** `set_aside[].receipt_image_available` on the expense batch payload, resolved by the image endpoint's own rule; live, all five July entries read `true` (the two invoices above included) and serve 200. The View button is `docs/lovable-feedback-0917b-prompt.md` section 4, not pasted yet. The false-quarantine class itself (the proposed change above) is untouched, and the two invoices still need Criss's restore click.

**Shipped 2026-09-17 (PR #1037, Fly v165), the classifier half.** A `statement` verdict whose reading carries a vendor, a non-zero total, a reference and at least one line item with a non-zero amount is kept as an expense with a `data_quality_note` ("read as a statement page, but it prints its own invoice number and line items, so it was kept as an expense: check it"), on both quarantine sites (`cli.split_non_receipt_documents` for a create with files, the add path in `service.py`); the reader's prompt is untouched. The row reads `check` / `invoice_read_as_statement` with `category_confirmable` until every line's category is the reviewer's own (the note #62 Confirm); a missing category still ranks first. Evidence behind the rule: the three July invoices' stored readings carry vendor, total, invoice number and line items (10, 2, 2); eight real statements read through the production reader (seven Chase card statements Jan-Jul 2026, an SAP AR statement) carry no reference and no line items; two billing-notice emails carry a reference and no line items. Replay over a read-only DB copy: old rule 8 of 8 stored set-aside readings out, new rule keeps exactly the 3 invoices, 0 stored expenses touched. The first draft only added the note; the adversarial review showed the kept row landed in the ready box and could self-confirm, fixed with the check above (reproduced first), plus a zero total and amount-less lines no longer qualify. Suite 2236 passed; `tests/test_invoice_read_as_statement_item_105.py` (13) through the drop, add and confirm routes; seven regress proofs by hand, all red under mutation. Deployed v165: new code confirmed in the running image; July's Expenses page driven cold, set-aside strip unchanged. **Stored months are not re-sorted: the AWS USD 3,352.59 and Tricarico BRL 27,203.34 invoices still need Criss's restore click in July's set-aside strip; nothing on July or August changes at the next re-match.** SPA copy for the new reason code (EN + PT): `docs/lovable-invoice-read-as-statement-prompt.md`, optional, Not applied (without it the row shows the backend's English reason). Not built: `other` verdicts (billing notices) are not second-guessed.

**2026-09-17 ~17:00 UTC, the two July invoices restored on the owner's order ("you move them to where they belong, no need for manual work here").** By file name through `POST /api/expense-batches/50622baec444/set-aside/restore`, then the Tricarico invoice (it prints "Payment Method: Wire Transfer") recorded through `POST .../receipts/{doc}/settled-outside` `{how: bank_transfer}`, the same disposition July's Redis and Konsultancy Finance invoices carry. AWS prints no payment method and bills Brisken Cloud Services, none of whose cards (7292, 9693, 8311, 6013) has a July statement loaded, so it stays a receipt waiting for its charge rather than a guessed transfer. Verified after: both entries `restored: true`, `n_expenses` 50 -> 52, `n_set_aside` 4 -> 2, `n_settled_outside` 0 -> 1, AWS in `unmatched_receipts`. Both re-matches reused 13 judgments and made 0 new model calls. **One unconfirmed suggestion moved** (row-by-row diff of all 112 July rows before/after): the 2026-07-12 charge NOBRE ATACAREJO SAO JOS USD 65.23 on 3876 (yellow in the workbook, `already_booked`) went from `review` to `unmatched` with no candidate, so receipt `0059__20260711_Receipt_Groceries_Fenix.pdf` (Supermercado Fenix BRL 325.88, prints VISA x3876) is now a receipt without a charge. Nothing confirmed moved. Cause not established: the two restored receipts had no candidate near that charge, so the likelier reading is that July had not been re-matched since today's matcher deploys and this re-match applied them; unverified. Company left to Criss on the owner's call: both rows still ask for one (file labels say Cloud Services and Consulting).

### 106. A mailed forward that created no expense still reads 'Added' and gets a 'landed in July' reply (2026-09-17 audit draft #104, unranked; licence: defect, covered) (SHIPPED PR #1017, Fly v157; SPA APPLIED 2026-09-17)

**Audit rank 13 of 40; severity high as merged; verification: checked by hand against the live inbound log (4 mails); no reviewer pass.** When the reader excludes a mailed file (statement page, bill notification, blank photo), the month already holds identical bytes, or the only attachment is an unsupported type (an iPhone HEIC photo is skipped; only PDF, PNG, JPEG, WebP are kept), the mail is stamped ingested with an empty list of expenses. The intake page shows 'Added', and the sender's confirmation says the files 'landed in the July 2026 expense month'. Four real forwards (two AWS 'billing statement available' from Dirk, an AT&T bill notice and an August card summary from Criss) delivered no receipt and nobody was told to fetch the PDF.

**Evidence:** web/intake_mail.py:1870-1878 (ingested with documents [] then ack), :1356-1364 and :1344-1350 (ack from batch label only), :169-170 (ingested -> 'Added'), :476-500 (accepted suffixes; others appended to skipped, never to the ack), :1370-1397; exclusion sentence only in the add summary (service.py:8928-8935). Live GET /api/inbound/log?detail=1: 2026-08-24T17:17 and 2026-09-07T06:47 (AWS, documents []), 2026-09-09T13:58 (AT&T) and 14:00 (card summary), all status_label 'Added', documents []; 2 archives with skipped parts. docs/electronic-storage-system-description.md:166-173 (HEIC). tests/test_intake_mail.py:949, :1393 pin documents == [] for the duplicate case only.

**Already tracked:** Item 30 (acks) and item 33 (dedupe) assume ingested means an expense exists; item 12 / Shipped row 10 built body rendering. The 'added nothing' outcome, the HEIC skip and the ack wording are untracked.

**Proposed change:** When a mail creates no expense, say so: a status label such as 'Received, set aside as a statement page' / 'already on file' / 'bill is behind a link, please forward the PDF', an intake-page kind that draws the eye, an acknowledgement that names the reason and any skipped attachment, and the exclusion reason carried on the mail record so the intake page links to the set-aside strip. Convert HEIC to JPEG at the mail boundary.

**Value:** Dirk and Criss learn in the same minute that a forward did not count, instead of finding the hole at month end. (effort small)

**Reviewer corrections:** none recorded

**Shipped 2026-09-17 (PR #1017, Fly v157).** The add summary and the mail archive carry `not_added` per file (`set_aside` with its reason, `already_on_file`, or the upload-issue code, plus the stored `document_id`); the intake row reads `Nothing added: read as a statement page` and its variants (status and `status_kind: done` unchanged, so `n_held` keeps its meaning and the published SPA shows the new text today), with a top-level `n_no_expense`; the acknowledgement's subject is `No expense added: ...`, one line per file, asking for the PDF or a photo and naming the restore path. An adversarial review found six more defects, all fixed in the same PR: a crash-replay counts the mail's own stored receipt (intake provenance now records `archive`), a restored set-aside file ends "Nothing added" at read time, echoed attachment names are flattened, a pooled mail that later adds nothing gets one correction, a mail-created month records upload rejections, and bytes matching a set-aside page read `set_aside`. Live after deploy: the four forwards (two AWS billing notices, AT&T, the card summary; 3 mails) read "Nothing added" on the published intake page (headless Chrome drive, read-only), `n_no_expense` 3. They were stamped before the fix, so they carry no per-file reason; new mail does. NOT built: HEIC conversion (no HEIC in the 121-row live log, and it needs a native library); an unreadable attachment type is named in the acknowledgement instead. SPA half (amber row, per-file reasons, a count badge): `docs/lovable-no-expense-mail-prompt.md`, not pasted. Suite 2154 -> 2167 passed on the merged tree; ten `regress_check` proofs bit.

### 107. Receipt chasing is the biggest monthly time sink and the tool does nothing with what it knows (2026-09-17 audit draft #105, unranked; new function, quote separately) (SHIPPED 2026-09-17, pending PR; owner reversed the quote-separately ruling; sends still owner-gated)

**Audit rank 14 of 40; severity high as merged; verification: checked by hand (no request path in code; August coverage per card); no reviewer pass.** August has 100 charges with no receipt (USD 10,950): Nicolas's card 3876 37 charges and 0 receipts, Dirk's 3645 35 of 40, 2838 28 of 34; July still has 24 on 3645. Every card names its holder, each charge carries a reason and a suggested category, and most missing July money is a SaaS invoice re-downloadable from a portal (OpenAI 16, Anthropic 5, Base44 3, Network Solutions 3 in August). Criss builds that list by hand and chases Dirk and Nicolas by mail herself; there is no per-person list, no request to the card holder, no 'asked on this date', and no 'no receipt expected' mark for fees and interest, so the annual fee counts as unreconciled money.

**Evidence:** Live 2026-09-17 August: n_unmatched_tx 100, reason no_receipt_found 98 / not_a_purchase 1 / held 1; coverage 3876 37/0 USD 1,031.15, 3645 40/4, card-2838 34/4 USD 7,438.36; ANNUAL MEMBERSHIP FEE 150.00 bucket unmatched; cards_effective names a person per card; inbound log has no mail from Nicolas. unmatched_reasons.py:126-136; categorize_charges.py:80-122 (annotation only); service.py:3076-3080 (fee counted as unreconciled); grep src for remind|request_receipt|nudge: 0; intake_mail.py:1398-1400 already sends mail to @brisken.com recipients. status/p1-expense-reconciliation.md:239-255 (44 of 89 July charges portal-recoverable). Backlog grep remind: 0.

**Already tracked:** none; item 48 round 2 names receipt thresholds (not scheduled), item 79 a page per class, item 26 statements not loaded. A per-person missing-receipt request is not tracked.

**Proposed change:** A missing-receipts list per card holder on the month page (vendor, date, amount, portal hint), a 'send request' button that mails the holder that list from the intake address so replies land in the tool, per-charge states 'requested on date' and 'no receipt exists (reason)', and a 'no receipt expected' mark for fees and interest that leaves the unreconciled total. In the meantime hand Dirk the recurring-vendor list with who holds each login. New function, quoted separately.

**Value:** The chase becomes one click and a reply, Dirk and Nicolas see exactly what is owed, and August's undocumented figure drops to the genuinely missing ones. (effort medium)

**Reviewer corrections:** none recorded

**Shipped 2026-09-17 (pending PR).** `receipt_chase[]` on `GET /api/runs/{id}` groups the month's charges that need a receipt by CARD HOLDER (the registry's `person` on the card the coverage panel totals the charge under), each charge with its date, vendor, amount, currency, card and any portal hint a merchant entry now carries (`receipt_portal`, optional, unset everywhere today). Membership is item 99's own `charge_needs_receipt`, read off the payload's rows, so the groups sum to `summary.n_charges_need_receipt` and the list and the count cannot disagree. Two reviewer-set states ride the charge's own `decisions` row, so both survive a re-match and a statement re-read's id rekey: `receipt_requested_at` + `requested_to` (`POST .../receipt-requested`) records the ask and closes NOTHING, counted as `n_charges_receipt_requested`, a subset of the open charges; `no_receipt_expected` with its reason (`POST .../no-receipt-expected`, blank reason refused) is a verdict that closes the charge, counted as `n_charges_no_receipt_expected`, and moves that money out of `unreconciled_by_ccy` into `no_receipt_expected_by_ccy` beside it (item 102's shape), so the annual fee stops reading as unevidenced money. `month_complete` follows both. The request mail is COMPOSED AND NEVER SENT: `GET .../receipt-requests` returns one plain-text mail per holder, EN and PT-BR, from and reply-to the intake address so replies land in the tool, with `to: null` + `blocked: "no_address"` for a holder nobody has given an address; `POST .../receipt-requests/send` answers 403 `receipt_requests_disabled` with the new `settings.receipt_requests.enabled` flag off (the default and the live value) and 403 `receipt_send_not_wired` with it on, because `receipt_chase.py` imports no mail transport at all. The owner approves the first real send separately. Live read-only before the deploy: August would list 61 charges across the three names the registry's `person` field holds ("Nicolas Neumann" 36 on 3876 USD 1,011.15, "Dirk Neumann - Corp Services" 24 on card-2838 USD 6,361.53, "Brisken Consulting" 1 on card-1176 USD 36.00), July none, because every July charge without a receipt is gray-filled and already closed. Not built: the UI (prompt `docs/lovable-receipt-chasing-prompt.md`, Send described as disabled), a bulk mark-all-requested, and any sender.

### 108. Cloud Services and Consulting card spend cannot close: 5 of 9 cards have never had a statement loaded, and the UI offers one statement (2026-09-17 audit draft #106, unranked; UI prompt for the owner to paste)

**Audit rank 15 of 40; severity high as merged; verification: checked by hand against live August coverage; no reviewer pass.** All 223 live charges belong to Corporate Services because the only workbook ever attached is the Chase export for account 2838. Receipts paid with the Cloud card 9693 and the Consulting card 1176 arrive monthly and park as 'card statement not loaded' (August: OpenAI 80.12 and 80.04; Anthropic 100; Lovable 50); 0113, 6013 and 8311 have no statement either. The backend accepts one workbook per card, but the Lovable page offers one 'Attach bank statement' dialog and one download, so Criss cannot add a second. Nothing checks that the card typed in the dialog matches the card printed in the file, so a workbook with no card column uploaded under the default would book to Corporate Services.

**Evidence:** Live August coverage[]: card-0113, card-6013, card-8311, card-1176, card-9693 statements [] n_transactions 0; rows legal_entity_id Corporate Services 111/111 (July 112/112); unmatched_receipts reason card_statement_not_loaded 4 (0001/0003 OpenAI on 9693, 0015 Anthropic and 0025 Lovable on 1176); statements[] one file per month, account_id card-2838, card_key ''. web/service.py:7810-7850 (advisory only for same card_key under two ids), :220 (account_id defaults to 'card'); item 59 record (2514-2554). Backlog 2742 and 3182 ('owner's call to load them'); item 53 (2032-2047).

**Already tracked:** Item 53 (open, framed as an unreachable UI affordance) and the matching close-out note; not framed as 'two entities are outside month close'. The typed-card-versus-file check is untracked.

**Proposed change:** Ask Dirk for the Chase 9693 and 1176 statements (and Apple 0113) for July to September and attach them; paste the coverage prompt and add an 'Add another statement' control to the month page; in the back end compare the card typed in the dialog with the digits printed in the file and warn or refuse on disagreement.

**Value:** Cloud Services and Consulting spend gets reconciled in the same tool, the parked receipts pair with their charges, and a dialog default cannot book a whole workbook to the wrong company. (effort small)

**Reviewer corrections:** none recorded

### 109. Charges without a receipt get an AI category nobody can correct, and the tool never learns it (2026-09-17 audit draft #107, unranked; new function, quote separately) (SHIPPED 2026-09-17, PR #1059, Fly v172; owner reversed the quote-separately ruling) (SPA APPLIED and DRIVEN 2026-09-18, EN and PT; CLOSED)

**2026-09-18: closed on screen.** August's Charges-without-a-receipt view renders
205 category comboboxes and 89 visible "Guess" chips; the LOVABLE 15.00 row of
Aug 31 carries a 176x32 px picker reading "Meals & Entertainment" with the chip
beside it, which is the prompt's check 1 word for word, and SAP SE 1,574.24 reads
"Software & Subscriptions / Guess". Portuguese renders "PALPITE" and "Sem
categoria ainda". The 2026-09-17 pass that reported the control missing had
counted native `select` elements on a page whose every picker is a Radix
`button[role=combobox]`, and had matched "Guess" case-sensitively against
`innerText`, which returns the CSS-uppercased "GUESS". Two blind instruments on
one control, and both read as evidence the feature was absent.

**Audit rank 16 of 40; severity high as merged; verification: checked by hand in code (category route needs a receipt); no reviewer pass.** Criss's real job is to give every charge a category. 71 of July's 112 charges and 98 of August's 111 have no receipt, each with a category the AI guessed from the bank description ('AI?' badge). There is no control on those rows to change it: the dropdown exists only inside a candidate receipt card, the category route needs a receipt, and learning reads receipts only. The guesses go into the reconciled CSV as they are and the same charge is guessed again next month. The recall half (learned rows for charges) already exists.

**Evidence:** Live: July charge_category source VENDOR on 71 rows, 0 EDITED, 0 LEARNED; August 98 VENDOR. SPA RunWorkbench.tsx:2255-2300 (posting_category read-only), CandidateRow 2882-2905 calls onCategory(c.document_id). app.py:2560-2607 (POST /api/runs/{id}/categories requires a receipt document_id); web/service.py:2452-2515; learning/capture.py:271-273 (skips non-receipt ids); output/reconciled_csv.py:275-330; categorize_charges.py:19-25 (reads learned rows for charges).

**Already tracked:** none (item 79 restructures the pages around receiptless charges but adds no edit; item 75 covers why a receipt is unmatched)

**Proposed change:** Let a category be set on a charge row (stored under the charge, shown as EDIT, carried into the CSV and report), and at sign-off remember it under the bank's description so the same subscription is recalled next month. Only the edit and the teach are missing.

**Value:** The largest part of every month's work becomes something Criss does once per vendor instead of every month, and the deliverable stops carrying uncorrectable guesses. (effort medium)

**Reviewer corrections:** none recorded

**Shipped 2026-09-17 (pending PR).** `PUT /api/runs/{id}/charges/{tx}/category`
stores a category against the CHARGE, in the same `category_overrides` table
the receipt edits use, under the pseudo-receipt id `charge:{tx}` the charge
categorizer already mints. Nothing but deleting the month clears that table, so
the pick outlives a re-match that rewrites the whole snapshot. It reads
`source: "EDITED"` with `is_edited: true` on `rows[].charge_category` and
`rows[].posting_category`, the row's review state drops to `none` (an answer is
not a question, so it leaves `n_charges_category_guessed`, which keeps its
meaning), and it reaches the reconciled CSV, `report.xlsx`, the statement
writeback, the reconciliation PDF's posts-to column, and, behind the existing
`zoho.export_receiptless_learned` flag, the journal rows a LEARNED charge
posts. A guess still never posts. At Publish, the month's sign-off since item
88, the pick is learned under the bank's normalized description through the
shared `_learn_categories` pass, conflict-skip included, so next month's same
subscription arrives LEARNED; a category that came from the model writes no
override and teaches nothing. The guessed row's own copy now says the tool
guessed it from the bank's description and that the row can be picked on.
Live scale on the 2026-09-17 payloads: 174 receiptless charges across July
(73) and August (101), 146 of them carrying a guess, 0 editable before this.
SPA half `docs/lovable-charge-category-prompt.md` (owner applies).

### 110. A receipt arriving into an existing month resolves its card against that month's stale copy of the registry; September has 40 expenses with no person (2026-09-17 audit draft #108, unranked; licence: defect, covered; SHIPPED PR #979: every arrival refreshes the month's card list first)

**Audit rank 17 of 40; severity medium as merged; verification: one reviewer.** Each month keeps a copy of the card registry from the day it was created, and an arriving receipt is resolved against that copy, not Settings. September was opened by mail on 7 Sept before the card list was finished; today every September expense has no person, 23 of 39 no company, and 'Visa ...3645' / 'Visa ...3876' read as unknown cards with 'maybe private' suggested, although Settings knows all nine cards. July and August look right only because someone pressed 'refresh master data' on 16 Sept; May, June and September were not refreshed, and two receipts added on the evening of 16 Sept inherited the stale copy. This is the 'no' half of note #54.

**Evidence:** web/service.py:8948 (card entities from the batch snapshot, _batch_cards :5163-5167); app.py:3389-3410 (refresh per batch, manual); live GET /api/expense-batches/51a22ad72864: n_needs_person 39, n_needs_entity 23, n_suggested_private 7, unresolved_hints 'Visa ...3645' (3 rows) and 'Visa ...3876' (2 rows), person_source none on every row; /api/settings cards_effective has entity and person on all nine; operator state master_data refreshes on 50622baec444 and 074a7b8905d7 only (2026-09-14 to 09-16); item 59 record.

**Already tracked:** Item 10 R3 (snapshot trap + manual refresh, shipped) and its residue ('re-stamp semantics after a registry correction', parked); item 26 (registry gaps). Not framed as 'every arrival resolves against a stale copy'; note #54 not yet an item.

**Proposed change:** Resolve an arriving receipt's card against the live registry, refresh every open month automatically when a card, person or entity is saved in Settings (statement or not), and re-stamp rows whose card had no person or company at the time. Keep the snapshot and the manual refresh for the audit trail.

**Value:** Person and company attribution stop depending on a button, September stops asking Criss to assign 39 persons the registry already knows, and note #54's promise holds for cards too. (effort small)

**Reviewer corrections:** (combined) September has 40 expense rows, not 39 (n_needs_person 40, n_needs_entity 24, not 23). September WAS refreshed once, on 2026-09-08 (backlog item 26 calibration: "refresh-master-data on all three open batches July/August/September"), before persons and cards 3645/3876 were entered; the live rematch log only covers events since 2026-09-12, so its silence is not proof May/June/September were never refreshed, only that none was since 09-12. The "two receipts added on the evening of 16 Sept" is understated: the inbound log shows September arrivals at 09-16 08:10, 11:37, 16:25, 22:52 and 09-17 07:26 UTC, all ingested against the same stale snapshot. Item 87 (shipped PR #947) already copies a card i

### 111. 19 of July's 33 'no company or person' receipts already settled a charge that names both (2026-09-17 audit draft #109, unranked; licence: defect, covered) (SHIPPED 2026-09-17, pending PR) (SPA APPLIED + VERIFIED 2026-09-17 night: owner published, cold-driven EN and PT, 0 writes; see PROMPT-STATUS)

**Audit rank 18 of 40; severity medium as merged; verification: one reviewer, plus the 19-of-33 count reproduced by hand.** On the Expenses page 33 July receipts (13 in August) ask Criss to pick a company and a person because the scan printed no readable card. Yet 19 of the July ones (3 in August) are already paired with a bank charge, and every charge carries its card, company and holder. The tool decided the answer on the matching page and asks the question again on the expenses page. The shipped fix (item 87) helps only when the receipt itself prints a card.

**Evidence:** Live July expenses: 33 with box needs_entity; 19 of those document ids are chosen_document_id of rows with effective_bucket reconciled, legal_entity_id Corporate Services, coverage_key card-2838 or 3645 (e.g. 0000__rendered-body.pdf, 0029 Aposto); August 3 of 13. Expenses payload has no per-receipt reconciliation field (item 79 decision 9 deferred). Item 87 text: 'The item-84 box line cannot fix 24 of July's 33'. Live July CSV: 35/55 rows print '(entity - assign)'.

**Already tracked:** Items 84 and 87 cover the box and the per-row card fix from the receipt's own hint; item 79 deferred the per-receipt match field; items 26/40/41 are the owner-data side. Inheriting company and person from the settled charge is not tracked.

**Proposed change:** When a receipt is paired with a charge, fill its company and person from that charge's card (marked inherited, editable) and count it as answered; show the per-receipt pairing on the Expenses page. Criss works the remainder with the one-click card fix or Confirm private before the report is handed on.

**Value:** Roughly six in ten of her monthly company/person clicks disappear, the two pages stop disagreeing about the same receipt, and the first document handed to an accountant does not read as unfinished. (effort small)

**Reviewer corrections:** (combined) (1) August is stale: the batch was edited at 09:53Z today and now has 30 expenses, 5 needs_entity (7 needs_company_or_person) and 7 reconciled rows, with 0 overlap; the "3 of 13" no longer holds live. (2) "Item 87 helps only when the receipt prints a card" is wrong: item 87's `card_key` per-row override applies to any row (the 8 no-card rows were its motivation); what is true is that it still asks Criss to pick the card the statement already names. (3) "Every charge carries its card, company and holder": rows carry `legal_entity_id` and `coverage_key` (two shapes: `card-2838` and bare `3876`); the person is resolved from the registry, not stored on the row. (4) "Six in ten clicks disappear e

**Shipped 2026-09-17 (pending PR).** On the Expenses payload (`GET /api/expense-batches/{id}`, its `boxes` and counts), and since the second commit the CSV and the month report, a receipt of the month that a charge of the same month settles (`service.settled_charge_cards`: the workbench's effective bucket `reconciled` with the receipt as `chosen_document_id`, pending or confirmed; a rejected pair or one in review lends nothing; a receipt borrowed from a neighbour or a trip lends nothing) takes that charge's registry card through the item-87 per-row path (`resolve_batch_row_cards(settled_cards=...)`): `card`, company (`entity_source: card`), person (`person_source: card`) and paid-through follow it, and it counts as answered for `needs_entity` / `needs_person`. `card_source` gains the value `settled_charge`. Order: a `card_key` pick, a printed method or assigned hint, any printed card number, and a confirmed private expense all win; a card remembered from an earlier month gives way. The row is a company-card row (`can_mark_private: false`, `suggested_private: false`, the private route refuses `company_card`). Live prediction, read-only against today's payloads and registry: July 19 of its 31 company-or-person rows inherit (12 on card-2838, 7 on 3876; all 19 get both company and person, so the box goes 31 -> 12; 15 of the 19 lose a "suggested private" flag, tender words VISA CREDIT, Link, VISA, TEF), August 2 of 4 (both on 3645, box 4 -> 2). Tests: `tests/test_entity_from_settled_charge_item_111.py` (7, route-level: inherit and box count, no pairing unchanged, rejected pair, row pick wins, printed number wins, settled beats remembered, private refused); `test_view_contract.py` closed set gains the value; `test_reference_duplicates.py`'s ignored-copy invoice now reads `entity_source: card` / `card_source: settled_charge` on corp-2838 (same company as the CSV). `regress_check` red on all six wires (payload wire 4 of 7, pick-first 4 of 6, printed-number guard 3 of 6, reviewer verdicts 1 of 6, source value 2 of 6, settled before memory 1 of 7). Suite 2228 passed / 2 skipped. SPA half: `docs/lovable-entity-from-charge-prompt.md` (source line + "Change card" on the new value; a stale SPA shows the card chip only). Exports follow (same day, second commit): the Zoho CSV and the month report resolve these rows through the same resolver and verdicts (`export_settled_cards` into `_expense_export_inputs` and the report's card pass), so an inherited row never prints `(entity - assign)` and a rejected pair still does; neither document has a person column for a company month. July's CSV rendered locally from a read-only DB copy (deleted after): 56 rows, `(entity - assign)` 35 -> 16; August 21 rows, 3 -> 1 (the payload model gave the same counts). Two export tests; `regress_check` red on all four export wires (resolver 2 of 9, CSV caller 2 of 9, report caller 2 of 9, verdicts 1 of 9). Suite 2253 passed / 2 skipped after merging origin/main. NOT built: the run payload, the matcher, the reconciliation PDF (prints no company or person) and the cost-center totals roll-up do not inherit; the per-receipt pairing field on the Expenses page (item 79 decision 9).

**Box trace 2026-09-17.** Live July after the deploy reads 19 `settled_charge` rows but `n_needs_company_or_person` 14, not the predicted 12. Not a defect: the month changed between the prediction and the deploy. The 19 inheriting rows are the predicted set (12 on card-2838, 7 on 3876, each the chosen receipt of one reconciled pending or confirmed charge, each with company and person from the card and no to-do box), and August reads exactly as predicted (2 inherit on 3645, box 2). The two extra rows are `0015__2026-07-01__BRISKEN_CLOUD_SERVICES__AWS_-_Amazon_Web_Services__Invoice_2704896057.pdf` (USD 3,352.59, prints no payment method) and `0017__2026-07-30__BRISKEN_Consulting_LLC__Rodrigo_Tanure_Tricarico_Con__20260803_July2026_Invoice_20_2318.pdf` (BRL 27,203.34, "Wire Transfer"), which item 105 restored from set-aside at ~17:00 UTC on the owner's order: after the prediction read July (50 expenses, box 31), before PR #1045 merged (17:17 UTC). So the box was 33 at deploy and 33 - 19 = 14. The restore left its trace in the live payload (both restored rows appended after `0070`, the last ingest of 09-12; Tricarico's `settled_outside.at` 17:00:31, the batch's `updated_at`). Neither is chosen or a candidate on any July charge (AWS waits in `unmatched_receipts` for a Cloud Services statement, Tricarico is settled outside by bank transfer), so neither can inherit. `n_suggested_private` closes the same way: predicted 22 - 15 = 7, live 8 (Tricarico's "Wire Transfer" matches no card). The other 12 box rows ask correctly: 9 are named by no charge (`0002` Hostinger "Paid via Corp Services card", an alias four cards share; `0003` Konsultancy, `0004` and `0070` Redis, `0008` 360Crossmedia, no method; `0027`, `0028`, `0034`, `0066` tender words only) and 3 are only candidates on charges in review or unmatched, which lend nothing by design (`0036` and `0037` Google on `b7abd111d69921a3`, card-2838, which also print a card number of their own; `0062` Bezerra on `7b7284d43889d1f4`, 3876). Nothing fixed. Seen on the way, not item 111's and untracked: a receipt recorded settled outside by bank transfer (`0017`) still reads `suggested_private` and sits in the company-or-person box.

### 112. A receipt filed in the neighbouring month reaches this month's statement only by luck (2026-09-17 audit draft #110, unranked; licence: defect, covered) (SHIPPED 2026-09-17, pending PR)

**Audit rank 19 of 40; severity medium as merged; verification: one reviewer, plus trigger callers confirmed by hand; severity lowered.** A receipt is filed by its printed date, a charge by the statement that billed it, and the boundaries differ (August's workbook opens on 31 July). Since 2026-09-15 a month borrows the neighbours' receipts whose dates fall inside its statement period, but only when this month happens to re-match. When a receipt dated 31 July lands in July after August's last re-match, nothing re-matches August; the receipt waits for an unrelated event. Trips have exactly this trigger; company months do not. A borrowed receipt also cannot be picked by hand.

**Evidence:** web/service.py:9531 (rematch_months_after_trip_change) called only at :4919 and :8791 (trip paths); :8725-8797 (a receipt add re-matches its own month only); :10460-10551 (adjacent_pool_for_month read at match time, no arrival trigger); :11017-11060 (month move re-matches both, the one path that does). Memory project_brisken_expense_recon_usability_loop item 61 entry ('a neighbour's receipt arriving does not re-match this month; a borrowed receipt is not hand-pickable'). Live 2026-09-17: July n_adjacent_borrowed 1 (June's Fenix 55.74 BRL, in review), August 0; August unmatched-receipt reason charge_in_neighbouring_period 4.

**Already tracked:** Item 61 shipped; the two open halves are recorded in memory only, not in the backlog.

**Proposed change:** When a receipt lands in a company month, also re-match the neighbouring month whose statement period covers the receipt's date (the one-line trigger trips already have), and let a borrowed receipt appear in the hand-pick list with its home month named.

**Value:** End-of-month subscriptions dated the 31st settle their charges on arrival instead of sitting as 'no charge on any loaded statement' until the next accident. (effort small)

**Reviewer corrections:** (combined) (1) "waits for an unrelated event" overstates it: the neighbouring month re-matches on any expense edit, set-aside, duplicate resolution, card change, statement re-read or the per-batch POST /api/expense-batches/{id}/refresh-master-data (trigger set: cards, duplicates, expense_edit, master_data, month_move, receipts, reread, set_aside, statement, trip), so the operator has a one-click recovery; only decisions (confirm/reject/manual match) do not re-match. (2) In the ordinary month-end flow the gap does not bite: the next month's statement is attached after the prior month's receipts arrived, and the statement attach re-matches with the adjacent pool; the gap is confined to a receipt arriving

**Shipped 2026-09-17 (pending PR), first half only.** A receipt added to a company month (the one add every entrance shares: mail intake, drop, the batch's receipts upload) or moved into one owes a re-match to each neighbouring company month (label +-1, `service.adjacent_months`, now also item 61's definition) holding a statement whose period (min..max of its charge dates) covers the receipt's effective date. The owed mark (item 113's `rematch_pending`, trigger `adjacent_receipts`) is written inside the arrival's own lock span, so a restart before the neighbour's turn keeps the debt for the boot pass; the neighbour re-matches after the month's own re-match, outside the lock, through `rematch_after_change`, and a failure lands on its mark and never fails the add or the move. A trip batch owes nothing here (the `trip` trigger stays the only path); a month move owes the target's other neighbour only; the add and move replies carry `months_rematched`. Live prediction, read-only: 0 receipts in the gap today (`rematch_pending` [], every July receipt dated inside August's period arrived before August's last re-match at 09-17 11:35, June's last add 09-10 before July's 09-16), and August's 4 `charge_in_neighbouring_period` receipts wait on September, which has no statement. Worth knowing: August's loaded period is 07-06..08-31 because the 1176 PDF statement opens 07-06, so almost every July arrival will also re-match August (judgments are cached; the cost is the pass, not the model). Tests: `tests/test_neighbour_rematch_item_112.py` (8, route-level: add, drop, outside the period, a trip named like a month, a failure inside the match and at the entry point, a restart before the neighbour's turn, a month move); `regress_check` red on all seven wires (add owe 5 of 8, add pay 4, move owe 1, move pay 1, trip guard 1, period check 1, failure record 1; the last five measured before the drop test joined). Suite 2221 passed / 2 skipped. NOT built: the hand-pick half (a borrowed receipt in `assignable_receipts`: that list is the month's own pool and the decision route checks the id against it, a new function rather than a filter change), and a month CREATED by its first receipts (its create runs under the month-creation lock every arrival waits on).

### 113. A re-match that fails or is interrupted by a restart leaves the month quietly stale, and 'run it again' does not repair it (2026-09-17 audit draft #111, unranked; licence: defect, covered) (SHIPPED PR #1026, Fly v159)

**Audit rank 20 of 40; severity medium as merged; verification: one reviewer each, severity lowered; error path confirmed by hand.** Every arrival re-matches the month after the receipt is stored. If that re-match throws (model outage, a statement upload at the same moment, a bad row), the error rides back in a result the mail and drop callers discard: the mail is stamped ingested, the job says done, no event is written, the notification mail sees only successes. If the machine restarts between filing and re-pairing (every deploy is a restart; 24 deploys in the last 48 hours), the receipt sits as 'no charge found' with a wrong reason and nothing records that the second step never ran; the job says 'interrupted, run it again', but a re-run finds no new files, skips the receipt as a duplicate and therefore skips the re-pairing. The month catches up only when something else changes it. No live failure observed; the one arrival after a statement produced its event.

**Evidence:** web/service.py:10385-10424 (_rematch_or_error returns the error, never raised or logged), :8779-8790 (re-pair gated by n_added), :10263-10280 (rematch_log only on commit); web/intake_mail.py:1826-1878, :3137-3185; app.py:351-390 (job marked done, result not stored); store.py:899-920 (boot sweep relabels running jobs only); grep 'rematch pending' across web/*.py: 0; tools/brisken-recon-notify.py:122-139 (diffs event ids only); flyctl releases v121..v144 between 2026-09-15 and 09-17; backlog lines 604-608 document the error contract as intended; item 50 (2276) names the killed ingest, not the re-pair half.

**Already tracked:** Item 58 (events for successful re-matches) and api-contract.md:1943-1954 (edit routes return the error to the SPA). The mail and drop callers, the restart gap and the no-op re-run are untracked.

**Proposed change:** Write a 'needs re-pairing' mark into the month record before a change and clear it when the re-pairing commits; at start-up re-run the pairing for any month still carrying it, the way pooled mail is claimed at boot; log a failed re-match into the same event log with its error so the notification reports it, show it as a month-health suspect, retry on the next arrival or on a timer, and let an interrupted job's re-run re-pair even with no new files.

**Value:** A receipt Dirk mailed cannot silently miss its charge for days because the model was down for a minute or a deploy happened at the wrong second; the month's counts always describe the month as it is. (effort small)

**Reviewer corrections:** (combined) (1) Deploy count: flyctl releases shows v121 (2026-09-15 09:55) through v145 (2026-09-17), 25 releases in ~46h; "24 in 48 hours" is accurate for v121-v144. (2) The restart window is not "the wrong second": it spans the whole re-match (minutes when FX/ambiguous judgment calls the model), which is larger than the finding implies. (3) "sits as 'no charge found' with a wrong reason" is not verified: with no re-match the stored outcome simply predates the receipt, so the receipt is in the pool but absent from the match outcome; whether the SPA renders that as a reason code was not checked. (4) The month self-heals on the NEXT successful trigger (any later receipt, card assignment, master-data ref

**Shipped 2026-09-17 (PR #1026, Fly v159).** A month owing a re-match carries snapshot `rematch_pending` `{id, since, changed_at, trigger, error?, failed_at?, attempts?}`: written in the same write as an arrival's receipts, by a month move on both months inside its lock span, and before every re-match, each write with a new id; a `rematch_month` commit clears only the id it read, so a change landing mid-match or its failure keeps its debt. A failed attempt is recorded on the mark (the mail and drop callers still discard the result, the mark does not); an arrival re-pairs when a mark existed even if every file was a duplicate (the no-op re-run); startup re-pairs every owed month in a background thread (trigger `resume`). `/api/operator/state` lists `rematch_pending[]`; `tools/brisken-recon-notify.py` mails each failure once per `(run_id, failed_at)` (live once the main clone the laptop task runs from is pulled). `rematch_log` keeps one event per commit. Adversarial review found four defects; three fixed with tests (an older re-match clearing a newer change's debt, erasing a newer failure, a month move leaving no debt), one accepted (a duplicate arrival during a running re-match costs one extra re-match). Live after deploy: `rematch_pending` [] (nothing owed), July 112 and August 114 rows unchanged, intake page drive clean. NOT built: the F34 periodic in-app sweep (the reviewer's correction stands: a crash restarts the machine and runs the boot passes); trip batches carry no mark of their own. Suite 2169 -> 2176 passed; eight `regress_check` proofs bit (one needed a direct test before it did).

**Folded in (F34): Housekeeping that rescues stuck mail runs only at start-up, and the machine no longer restarts.** Four clean-ups (jobs killed mid-run, mail interrupted while being read, expired archives, pooled mail waiting for a month since opened) run only when the app boots. Until 2026-09-10 the app restarted almost daily; it is now pinned always-on, so they run only on a deploy. A crash or out-of-memory during a large read leaves a mail showing 'Filing' indefinitely with no alert until someone deploys or presses 'Retry held emails'; under the licence, deploys become rare. The estate plan said the always-on pin and the periodic sweep must ship together; the outage recovery shipped only the first. Evidence: app.py:577-615 (the sweeps inside app creation, comments assume scale-to-zero); web/intake_mail.py:2969-2984 (transient state older than 600 s retryable only via the replay endpoint), :3137-3198 (alerts only from the boot sweep); grep Timer|periodic|interval in web/app.py, intake_mail.py, smtp_server.py: 0; fly.toml:2-5 (min_machines_running = 1 since 2026-09-10); TARGET-ARCHITECTURE.md:281-285; OWNERSHIP-HANDOFF.md:127; live /healthz started 05:59Z today (only this morning's deploy ran them). Proposed change: Run the same four passes on a timer inside the app (every 15 minutes is plenty) and alert when a mail has sat in a transient state for more than ten minutes. The passes are already written. Reviewer corrections: (combined) "A crash or out-of-memory ... leaves a mail showing 'Filing' indefinitely with no alert until someone deploys": wrong. A crash/OOM kills the process, Fly restarts the always-on machine, and the restart runs the boot sweeps; the stranded case needs a stall that neither raises nor kills the process. "Alerts only from the boot sweep" (intake_mail.py:3137-3198): wrong; _maybe_alert also fires from the ingest-job except path (:1884), the routing except path (:2410) and auto-render (:1968). "Filing" is the label for `routing` only; a killed ingest shows "Arriving" (`received`), not "Filing" (:164-165). "Retryable only via the replay endpoint": true for the >600 s transient case, and that endpoint 

### 114. Receipts dropped on the page have no safety copy: a restart mid-drop strands them and deleting a month erases them for good (2026-09-17 audit draft #112, unranked; licence: defect, covered) (SHIPPED PR #1033, Fly v162, see Shipped row 64)

**Audit rank 21 of 40; severity medium as merged; verification: one reviewer, severity lowered.** Mail is written to the volume before the sender gets an acknowledgement and is replayed after a restart; deleting a month returns mail to the pool. The drag-and-drop entrance has none of that: files go to a temporary folder, a background job reads them, and if the machine restarts the job is marked 'interrupted, run it again' while the files stay in the temporary folder with nothing that re-drives or lists them. A receipt dropped or uploaded into a month lives only inside that month's folder; deleting the month (a confirmed action) erases it with no way back except asking the sender. The drop folder is empty today; the deploy cadence makes it a matter of time.

**Evidence:** app.py:3237-3290 (/api/receipts writes to /data/drops/<job> and hands off to a BackgroundTask), :393-427 (finally: rmtree only if the process survives), :1299-1360 (delete removes the month folder), :390, :426; store.py:899-920; web/intake_mail.py:1162-1223 (mail archives returned to the pool), :3599-3660 (drop routing content-deduped, so a re-drive is safe); live ls /data/drops = 0 on 2026-09-17.

**Already tracked:** Item 48 gap G2 (retention and delete_run, compliance framing, nothing built); items 44/45 defined the drop entrance and its cap. Neither covers an interrupted drop or the custody asymmetry.

**Proposed change:** Treat a drop like mail: keep dropped and uploaded files as a ledger entry on the volume keyed by content, re-run any interrupted drop at start-up relying on the duplicate check, show stranded drop folders on the intake log meanwhile, and make month deletion a soft delete with a grace period or rebuildable from that custody area.

**Value:** A receipt Criss dropped cannot disappear because of a badly timed deploy or a misclick on Delete, which is exactly the class of loss the licence covers. (effort small)

**Reviewer corrections:** (combined) (1) "no way back except asking the sender" is wrong for drops: the sender IS the operator, whose originals are on her own disk; recovery is re-dropping the pile, which `route_dropped_receipts`'s docstring states is safe by content dedupe. What is lost is the vision reading, categorization and review decisions, and those are deleted with the month regardless of entrance. (2) An interrupted drop is not silent: the job row reads "interrupted by a server restart; run it again" to the polling SPA; what is missing is the per-file ledger (which files landed before the kill), so the retry has to be the whole pile. (3) Month deletion is not a misclick: it needs the typed month label or run id in the 

**Shipped 2026-09-17 (PR #1033, Fly v162), narrowed by the corrections.** The drop route writes a sidecar `drops/<job>.json` `{month, resumed, created_at}` beside the folder; the job removes both when it ends. At boot, after the stale-job sweep, each drop whose job reads "interrupted by a server restart" runs again under its own job id with the stored month (stages `waiting to resume after a server restart`, then `resuming after a server restart`, then `done` with the normal ledger); content dedupe skips files that landed before the kill. `resumed` is written when a drop's turn starts, so a drop cut off again after running once is given up ("drop the files again") while a queued one is not; each folder and each run is guarded on its own. Leftover drop folders with no interrupted job or no trustworthy sidecar, and `drop-add-*` copies inside month folders, are deleted at boot. Not built: month-deletion custody (corrections 1 and 3), the other upload entrances (`add-staging-*`, `folder-staging-*`), and a month folder a kill leaves mid-create before its row commits (older than this item; found by the review). Live before the fix: `/data/drops` empty, zero jobs ever interrupted by a restart, 18 drops since 2026-09-08, so no instance to repair. Evidence: suite 2186 -> 2196; `tests/test_drop_resume_item_114.py` (10) through the real route and a second `create_app` as the restart; the adversarial review found 3 defects in the first draft (queued drops given up on a second restart, a failing folder leaving a job running with no thread, one failing run stopping the rest), each reproduced first; nine regress proofs by hand, all red under mutation (the tool printed a false red on one). Deployed v162: the new boot pass is in the running image, the drops folder is empty, and the published Receipts page renders cold with no error strings. No SPA field changed; the resume stages only appear when a deploy lands mid-drop.

### 115. Corrections are stored but not recalled: itemized receipts, entity-less rows and confirmed pairs all bypass memory (2026-09-17 audit draft #113, unranked; licence: defect, covered) (SHIPPED 2026-09-17, pending PR)

**Audit rank 22 of 40; severity high as merged; verification: checked by hand in code (three holes confirmed); no reviewer pass.** The sign-off promise is that a corrected category arrives pre-filled next time. Three holes: for a receipt with readable line items (55 of 84 categorized July lines came from line reads) the AI's line reading always wins and memory is never consulted, and the existence of a remembered row stops the merchant default from applying, so that receipt goes back to the AI every month; the learned lookup needs the receipt's company, and 33 of 52 July and 13 of 31 August receipts have none, so the 103 seeded rules reach no live row (has_learned false on all 223 rows; Anthropic rows re-categorized by the model despite a rule); and only the statement-mode sign-off branch learns vendor spellings and exchange rates, while every live month is receipt-first, so publishing July teaches the matcher nothing (aliases 0, fx 0, and it will stay so).

**Evidence:** categorize.py:358-371 ('memory is never consulted here'), 378-386, 322-328 (registry stamp only when no learned row), 441-469 (lookup keyed on legal_entity_id + vendor, None when entity empty); learning/capture.py:255-303 vs 58-129; web/service.py:4127-4165 (expense branch returns) vs 4167-4190 (statement branch, only caller of learn_from_run); docs/api-contract.md:2600-2601 ('confirmed statement pairs teach aliases and FX'). Live 2026-09-17: /api/memory categories 103 (validated 0, count 1, last 2026-08-06), aliases 0, fx 0; both months has_learned false 112/112 and 111/111, n_learned_lines 0; July line sources LINE 55 / REGISTRY 63 / VENDOR 10 / EDITED 16.

**Already tracked:** none; items 88 and 4 assume a corrected merchant is recalled ('the merchant name book and learned memory already outrank the AI for every merchant Criss has corrected once'); item 88 notes only that nothing has fired.

**Proposed change:** When a remembered category or merchant default exists for company + vendor, apply it to the receipt's total (or let it beat a disagreeing line read, flagged for a glance) and never let a remembered row block the merchant default; let a rule apply on vendor alone when the company is unknown, recording which rule fired; on a month with a statement, run the pair-learning step after the expense step at sign-off.

**Value:** The categories Criss fixes in July are the ones August arrives with, and the same truncated bank descriptions stop needing a manual match every month; the 'gets better every month' claim in the licence pitch becomes observable. (effort medium)

**Reviewer corrections:** none recorded

**Shipped 2026-09-17 (pending PR).** Three rules, as built.

1. **A correction outranks a line read, visibly.** A receipt with readable line items now consults memory. A rule a PERSON taught (saved at sign-off or by the button, a Memory-page edit, or a row someone validated) applies to every line; when the model's line read said something else the line carries `decision: "learned_over_line"` and the row reads `check` / `vendor_guess`, the existing code, sentence and `Keep "<category>"` button, so the glance is one click and teaches the rule again. A validated rule applies without the flag and without paying for the line read. A merchant marked `multi_category` is never flattened. A remembered row no longer BLOCKS the merchant default either: where the registry also names a category the learned row applies over the line read whatever taught it (2026-08-07 said learned outranks the registry, the registry already outranked a line read, and the old code dropped both to the line read instead).
2. **A rule reaches a row whose company it does not name.** The lookup takes the rule saved under the receipt's own company and vendor first; a receipt with a company but no rule of its own falls back to a rule saved with NO company, which is what every live sign-off writes today (a month's corrections are keyed on the company each expense carried, and the 11 rules a July sign-off would write are all company-less). Only a receipt with no company and no company-less rule reaches the vendor's other companies' rules, and then only when they agree on the category (or exactly one exists); the account is carried only when they also agree on it, because an account belongs to one company's chart. The provenance names the rule that fired.
3. **A month with a statement teaches its pairs at sign-off.** Publishing (and the button) now runs the pair step over the charges and receipt pool the matcher read, on pairs a verdict CONFIRMED, and reports `confirmed_pairs` / `vendor_aliases` / `merchant_fx`. An alias whose statement description or receipt vendor names no merchant is refused, item 117's guard on this path. Borrowed trip and neighbour receipts are folded in, so a cross-month pair teaches too.

**NOT built, needs an owner ruling: may a Zoho-seeded rule nobody has validated beat a line read?** Today it does not (it still fills a receipt with no readable items, as since Phase 2). Live evidence for the question: all 103 rules are seeded, count 1, validated 0; the seed files `slack`, `supabase`, `perplexity ai` and `hugging face` under Marketing & Advertising and `burger king` / `baeckerei` under Travel & Transport, while Criss's own August edits put Perplexity and Pressmaster under Software & Subscriptions. Also not built: teaching a category under the company the CARD resolved (rules stay keyed on the company the expense carried, which rule 2 then works around), FX sample dedupe across re-saves, and any re-categorization of stored rows.

**Measured live (read-only copy of `/data`, 2026-09-17).** Replayed both months' stored readings through origin/main and through this code: with today's memory, **0 of 201 expense lines and 0 of 173 receiptless charges change** -- every rule is seeded and unvalidated, and the three receipts a rule reaches at all (Redis Inc., GitHub Inc., Eleven Labs Inc.) have line items. The instrument was proven against a fabricated person-taught rule (10 lines moved, 4 flagged). Replayed again with the memory a July sign-off would write: July's sign-off teaches 4 vendor aliases (`AMAZON* Z11US7DF5` == Amazon.de, `ANTHROPIC` == Anthropic PBC, `ELEVENLABS.IO` == Eleven Labs Inc., `WEB*NETWORKSOLUTIONS` == Network Solutions) and 1 FX rate where it taught 0, and August's next arrivals change on 10 of 42 lines: 7 from the model's line read, 2 from no category at all, 1 from the registry default to the same category under her name. No line contradicts a reviewer edit or the registry (the pre-existing 3 stored rows that contradict her edits drop to 1). It reaches her screen on the NEXT arrival into a month (creation, a mailed or uploaded receipt, a restored set-aside page), never by rewriting a reviewed row: nothing re-categorizes stored rows, and a re-match re-pairs without re-reading.

**Tests.** `tests/test_memory_recall_item_115.py` (6, route-level: the corrected category arriving on next month's receipt, a seeded rule staying below the line read, a company-less rule reaching a row with a company, publish teaching spelling and rate, the generic-description refusal, and a reviewer edit surviving a remembered category); precedence in `tests/test_categorize_memory.py`; the accuracy gate's fixture now guards both halves. Five regress proofs, each red under its own mutation. Suite 2266 -> 2279 passed / 2 skipped.

### 116. Signing off a month silently erases 'multiple categories' flags and merchant cost centers (2026-09-17 audit draft #114, unranked; licence: defect, covered) (SHIPPED PR #993, Fly v151; route tests only, a live proof needs a real publish)

**Audit rank 23 of 40; severity high as merged; verification: one reviewer (evidence) plus reproduced by hand.** When a month is published (or 'Save corrections to memory' is pressed) the tool rewrites the whole merchant list from a copy that keeps only aliases, category and account. The 'this vendor uses multiple categories' flag and the merchant's cost center are dropped from every merchant. Nothing is lost today because no merchant carries either yet, but the first publish after Dirk fills in cost centers (item 47) or marks Amazon multi-category wipes them all without an error.

**Evidence:** Proven locally at c233237f: a commit with zero edits on a registry holding one multi_category entry and one cost_center entry returned a changed map with both keys gone. web/service.py:4024-4030 (rebuilds entries with aliases/category/zoho_account only), 4092-4096, 4160-4164; publish reaches it via commit_month_memory (app.py:1239-1244, service.py:11674-11679). tests/test_web_merchant_registry.py:206-216 seeds without those keys. Live: 28 merchants, none with either key; published_runs empty.

**Already tracked:** none (backlog grep multi_category: 1 hit, Shipped row 6, the feature itself)

**Proposed change:** Copy each merchant entry whole and change only the aliases and category the edits touched; add the regression test with both fields present. One small change before any month is published.

**Value:** Dirk's cost-center and multi-category entries survive month end instead of vanishing the first time Criss signs off. (effort small)

**Reviewer corrections:** (evidence) None wrong. Two refinements: (1) the strip is also silent in the API reply, since `reg_summary` reports aliases_added 0 / categories_set 0 while settings are rewritten, so the caller sees "nothing learned"; (2) the backlog's item 47 D2 lists the merchant signal as a "learned merchant -> cost center" SQLite table, but the code implements it as the registry entry's `cost_center` (merchant_registry.py:26, service.py:5394), so the finding's "merchant's cost center" is accurate for the shipped code.

### 117. One-word merchant aliases act as wildcards and file unrelated vendors under the wrong name and category (2026-09-17 audit draft #115, unranked; licence: defect, covered; SHIPPED PR #1003, Fly v153)

**Audit rank 24 of 40; severity high as merged; verification: two reviewers agreed, plus 42 single-word aliases read live.** The merchant list carries single generic words as aliases ('Sports', 'Cafe', 'Mercado', 'Comida', 'Drink', 'Doces', 'Material de Construcao'). Any vendor containing such a word is a certain hit, so 'Mercado Livre' becomes NOBRE ATACADO / Meals, 'Decathlon Sports' becomes ERICK SPORTS / Travel, 'Leroy Merlin Material de Construcao' becomes MEGA CENTER / Professional Services. The AI is skipped, the rows read 'ready', and the report prints the wrong merchant. It bites the first time a new vendor shares a word with one of the 28 seeded Brazilian merchants.

**Evidence:** Proven locally against a copy of the live registry (GET /api/settings merchants, 28 entries): 8 of 8 probe vendors resolved 'fuzzy 100.0' to a wrong canonical name. merchant_registry.py:162-176 (rapidfuzz token_set_ratio >= 88 over every alias; token_set_ratio('cafe nero london','cafe') = 100), :66 threshold; categorize.py:243-249 (confidence 1.0 / REGISTRY); web/service.py:2519 (REGISTRY trusted, reads ready). Live July: 10 rows / 63 lines already from the registry; no wrong hit on a live row yet.

**Already tracked:** none (backlog grep fuzzy/token_set_ratio: 0 hits; memory project_brisken_expense_recon_merchant_registry names only casing duplicates and one mislabeled category)

**Proposed change:** Let an alias match only as a whole name: exact after normalization, fuzzy only when the alias has two or more words. Refuse a single generic word as a merchant alias at save time (as card aliases already refuse tender words) and sweep the 28 live entries once (about 20 such aliases).

**Value:** A receipt from a new vendor keeps its own name and category instead of inheriting a Brazilian grocer's, and the expense report stops naming the wrong merchant. (effort small)

**Reviewer corrections:** (evidence) (1) The one-word aliases were not seeded: seed_registry.build_merchants emits only whole raw vendor strings as aliases, so 'Sports', 'Mercado', 'Doces', 'Caipirinha' etc. were hand-entered later in the Merchants editor (the memory anticipated 'every editor fix teaches the registry'); the code accepting them without a guard is still the developer's side, but the framing 'seeded' is wrong. (2) Count understated: the live registry holds 42 single-word alias strings (plus single-word canonicals 'Americanas' and 'RAC'), of which roughly 25 are generic (Supermercado x5, Mercado x4, Atacado x4, Varejo x4, Comida x2, Doces x2, Cafe, Drink, Bebida, Sports, Gasolina, Diesel, Alcool, Sushi, Pastel, Tap (ledger) (1) "About 20 such aliases" understates it: 42 of 59 live aliases are single words, roughly 25 of them generic nouns; a few single-word ones are distinctive brand fragments (Caldinho, Espetinho, Borracharia) that the proposed rule would stop matching fuzzily, a trade-off the proposal should name. (2) The proposed guard "fuzzy only when the alias has two or more words" does not close the finding's own third example: 'Material de Construcao' is three words and 'Auto Posto' is two, and token_set_ratio still scores 100 whenever the alias's tokens are a subset of the probe, so the fix has to penalize the unmatched remainder (ratio/token_sort_ratio, or alias tokens covering most of the probe), not

**Shipped 2026-09-17 (PR #1003, Fly v153).** An alias made only of generic words (`GENERIC_MERCHANT_WORDS`: kinds of shop, products, fuels, plurals) is ignored by the resolver and refused when newly added at the settings PUT (stored ones stay accepted, so the editor never fails on its own data); a fuzzy hit needs the merchant's first distinctive word and is discounted by the vendor's uncovered distinctive words; a vendor with exactly the merchant's distinctive words matches ("KI-MASSA CAFE"); the seed no longer proposes a generic alias. Owner ruling: the stored generic aliases stay in live settings, inert, no settings write. Named trade-off: none of the 42 live one-word aliases matches on its own; "NOBRE ATACADO E VAREJO" and brand-plus-place vendors fall to the model rather than guess (the same shape reads "Farmacia Pimentel" as the petrol station). Verified: replay over all six live months (133 stored receipts) plus the local ER exports, 0 stored receipts changed and no new hit; the same check re-run inside the v153 container against the live merchant list read 0 changes and the audit's wildcards unresolved. An adversarial review of the first draft found three defects (place-name wildcards, lost KI-MASSA hits, seed `--put` refusal), all fixed before merge. api-contract "A generic word is not a merchant alias".

### 118. Cost centers are built, the list is empty, and a pick on a row teaches nothing (2026-09-17 audit draft #116, unranked; owner data)

**Audit rank 25 of 40; severity medium as merged; verification: one reviewer.** The cost-center feature Dirk ordered is live in the backend and the SPA, but the list in Settings is empty, so the roll-up shows 132 expense rows across the months as unassigned (USD 34,622, EUR 19,102, BRL 3,922, inflated by F01) and nothing can be required against an empty list. The design said a cost center picked on a row would be remembered per merchant; the build resolves from the row's pick, the trip, the merchant entry and the card, and neither a row pick nor sign-off folds anything into the merchant list, so each new vendor must be typed by hand once Dirk defines the centers.

**Evidence:** Live /api/settings cost_centers {}, cost_center_options []; /api/cost-centers/totals unassigned n_rows 132, n_batches 5; every expense payload n_needs_cost_center 0. cost_centers.py:169-200 (chain); web/service.py:5340-5402 (merchant_cc from the registry entry only), :4061-4091 (registry upsert handles vendor and category only); learning/capture.py:154 (learnable fields: vendor, tax_label, paid_through, card_key); docs/api-contract.md:1279-1283. Backlog item 47 (1499-1530): 'D1 - the list is owner-authored'; D2 step 3 'learned merchant -> cost center' listed in the build order, reported BUILT.

**Already tracked:** Item 47 (open, backend+UI shipped; owner data pending); the learning half is listed there as built and is not there.

**Proposed change:** Hand Dirk the four names he gave (Lidar, Brazil, tool work, marketing) as the first entries and ask him to add them in Settings; then, after fixing F10 so entries survive, fold a row's cost-center pick into its merchant's entry at sign-off with the same conflict-skip rule categories use.

**Value:** 'What has Lidar cost since January' becomes answerable from the tool, and Dirk types a cost center once per vendor, not once per receipt. (effort small)

**Reviewer corrections:** (combined) Live USD unassigned is 34,677.52 (not 34,622); totals also reports n_batches 6 scanned (5 carry unassigned rows) and n_undated 1. "Dirk must define the centers" is already possible from the SPA: PROMPT-STATUS records the settings chunk saving cost_centers per section since the 2026-09-15 bundle, so the data-entry path is open, not blocked. The design did not say "remembered per merchant" loosely; it specified a learned merchant->cost-center table (D2 step 3), which was silently replaced by the registry `cost_center` carrier. The strongest fact is missing from the finding: sign-off learning erases merchant `cost_center` entries (service.py:4025-4033), which makes the "fix F10 first" ordering 

### 119. No copy of the ledger exists outside one 1 GB disk on a personal account, and a restore has never been rehearsed (2026-09-17 audit draft #117, unranked; operations) (SHIPPED 2026-09-17, pending PR)

**Audit rank 26 of 40; severity high as merged; verification: checked by hand (5 snapshots, 5-day retention, single volume); no reviewer pass.** Every month, every mailed receipt and the learned memory live on one disk in Frankfurt under the developer's personal Fly account. The platform keeps five days of snapshots and nothing else: no copy Brisken controls, no nightly export, no export route, and nobody has restored a snapshot. A deleted month is gone after five days; a lost disk takes the ten-year receipt archive with it. Database changes apply at start-up with no version and no backup-first step. The unattached rollback volume from 2026-09-10 is frozen and the handoff document still names it as live.

**Evidence:** fly.toml:1-8 and [mounts] (single volume recon_data_v2); live flyctl volumes snapshots list 2026-09-17: 5 snapshots, retention 5 days, 27-138 MiB; vol_4m3p65dn1nqkowzv unattached; df /data 87 MB used; grep litestream|backup across src/, fly.toml, Dockerfile: 0; no export route among app.py's 78 routes; store.py:404-457 (_migrate ad hoc, no schema version); docs/electronic-storage-system-description.md:378-382 and gap row 5 (High); OWNERSHIP-HANDOFF.md:67, :127, :313-317 step 1(c)/(e) UNVERIFIED, :530; backlog grep backup: 0.

**Already tracked:** none in the backlog. OWNERSHIP-HANDOFF step 1(c)/(e) and storage gap 5 name it as a departure task and a compliance footnote.

**Proposed change:** Copy the whole data folder (under 100 MB) off the machine nightly to a place Brisken owns (SharePoint via the Graph credential the estate already holds), raise snapshot retention to the platform maximum, run one timed restore into a throwaway app and write the steps down, add 'take a copy first' to the deploy steps for schema changes, and correct the handoff lines that name the old volume.

**Value:** A lost disk, a wrong Delete month or a hosting incident stops being a rebuild of Criss's months from her inbox, and Brisken holds its own records. (effort small)

**Reviewer corrections:** none recorded

**Shipped 2026-09-17 (pending PR).** `web/backup.py` zips the whole data folder and uploads it to a SharePoint library Brisken controls, through the app-only Graph credential the estate already holds (drive API, no mailbox). Live databases are copied through SQLite's own backup API rather than off the disk, because a byte copy of a database being written to restores as "disk image is malformed" and looks like a backup until the day it is needed. Three ways to run it: `expense-recon backup --dry-run` (the default: says what it would upload and how big, reads nothing but the volume), `--check` (read-only Graph: resolves the target and lists the folder), `--go` (takes one copy), plus an in-app scheduler thread on the same pattern as the boot sweeps. The schedule is OFF unless `EXPENSE_RECON_BACKUP=1`, so this deploy changes nothing by itself. Refusals are plain, never exceptions into a boot thread: no credential, no target, or a folder over the 100 MB ceiling each come back with a reason (half a ledger is not a backup). The Graph path was validated read-only against the live tenant on 2026-09-17: token minted, `brisken.sharepoint.com:/sites/MARKETING` and its default library resolved, root listed (15 folders), and the intended backup folder read as empty because it does not exist yet. Nothing was uploaded. Restore procedure: `docs/backup-and-restore.md`, and it says plainly at the top that **no restore has been rehearsed** because rehearsing it needs a throwaway app and the owner's go-ahead. `docs/electronic-storage-system-description.md` §5.4 and gap row 5 are corrected from "no application-level backup or restore" to narrowed-not-closed. **Owner actions:** (a) pick the site and set `EXPENSE_RECON_BACKUP_SITE` (MARKETING is what the credential demonstrably reaches; a finance-owned site is a grant question); (b) `EXPENSE_RECON_BACKUP=1` to turn the schedule on; (c) a rehearsal run into a throwaway app, which is the only thing that turns the runbook into a proven restore; (d) snapshot retention beyond 5 days is still a Fly-side change, untouched here.

### 120. Only the developer can restart, redeploy or recover the app, and nothing in the repository would let a stand-in do it (2026-09-17 audit draft #118, unranked; operations)

**Audit rank 27 of 40; severity high as merged; verification: finder's evidence only, not independently rechecked.** The app, its disk, the mail address, the Lovable seat and the code all run under the developer's personal accounts with a single login and no delegated access. The 2026-09-10 outage (about 50 minutes) needed the developer to destroy the machine, fork the disk and redeploy; nobody at Brisken could have. All 249 commits are by one person, 13 releases went out in 36 hours by hand from a temporary checkout, the running app does not say which commit it carries, the working knowledge is spread over fifteen memory files outside the repo, and the README still describes a May command-line tool with a Zoho export, 98 tests and the retired UI address.

**Evidence:** OWNERSHIP-HANDOFF.md:12-16, :63-73 ('Zero org or app tokens exist'), :79-86, :462-469; status/p1-expense-reconciliation.md:33-36 (outage); git log: 249/249 module commits by 011matthias, 64 since 2026-09-01; flyctl releases v132-v144 all by one account; /healthz has no commit id (app.py:742); web/service.py 11,729 lines with build_view 952 / build_expense_view 696 / rematch_month 625 lines; README.md:98, :244, :286-321, :334, :519-532; BLUEPRINT.md:358-377 dated 2026-05-31; memory project_brisken_retainer_600_licence ('Transfer OWNERSHIP fully as its own funded piece').

**Already tracked:** OWNERSHIP-HANDOFF (draft, never sent) and TARGET-ARCHITECTURE P5, undated, waiting on Dirk naming an owner; ANNEALING E4 and SPEC-GAP-REGISTER item 1 (reconcile docs, never done). Not in the backlog.

**Proposed change:** Before the October arrangement is signed, move the app into a hosting organisation Brisken pays for with Dirk as admin, hand over the secrets list and a one-page 'if it is down, do this' card, rehearse the move on a throwaway app, and send Dirk a short transfer-of-ownership version of the runbook. In the module, write one operating page (deploy, roll back, read live state, audit a publish, where labels and the notifier live), make /healthz report the commit, cut the README to what is true, and keep a short map of which function owns which screen field. No refactor under the licence.

**Value:** Brisken can restart its own tool on a Sunday and keeps its records whatever happens to the developer's accounts; a stand-in can deploy, verify and restore from the repository alone. (effort medium)

**Reviewer corrections:** none recorded

### 121. Every alarm the tool raises goes to the developer only, through a script on his laptop (2026-09-17 audit draft #119, unranked; owner data; held-mail half SHIPPED PR #1001, Fly v153)

**Audit rank 28 of 40; severity high as merged; verification: checked by hand (default recipients in code; settings key absent live); no reviewer pass.** Held or refused mail, failed reads, re-matches and Criss's feedback notes are reported to one mailbox: the developer's. The alert-recipient setting has never been filled so the built-in default applies, Criss's address for a 'your month is ready' ping was never set, and the outside-address list treated as 'ours' holds only Dirk's iCloud (Criss's Hotmail is not on it, so a forward from it is held without an ack). The event mails come from a scheduled task on the developer's Windows laptop every 15 minutes, logging in with the shared code, from a checkout that was 11 commits behind on 2026-09-11; every mail is sent from his mailbox with failures swallowed. From October he is a licence holder, not the operator.

**Evidence:** web/intake_mail.py:95 (DEFAULT_ALERT_RECIPIENTS = matthias.silva), :277-279, :556-582 (known-sender rule), :1407-1432; live /api/settings intake = {aliases 3, known_senders ['dirk_.neumann@icloud.com'], travel_alias}, no alert_recipients / auto_ack; web/graph_notify.py:43, :47, :67-90 (send silently skipped); tools/brisken-recon-notify.py:6-11, :30, :64, :69-70, :399-405; Windows task BriskenReconNotify LastRun 2026-09-17 08:32; OWNERSHIP-HANDOFF.md:133, :313-317, :325-328; TARGET-ARCHITECTURE.md:263 (P4); memory project_brisken_retainer_600_licence and chris_process (cavalcanticris@hotmail.com). Backlog grep alert_recipients: 0.

**Already tracked:** Item 58 covers only the developer's re-match ping; OWNERSHIP-HANDOFF step 1(a)/(d) and step 2 and the retainer memory name it. Not in the backlog.

**Proposed change:** With Dirk's yes, one settings write: alert recipients to Criss and Dirk (developer in copy for now), Criss's address for the ready-ping, and the private addresses our own people forward from. Move the notifier into the app itself (it already holds the mail credential and a guarded sender; a 15-minute thread replaces the laptop task), send from a Brisken system mailbox read from configuration, log a failed send, and show the current recipients on the Settings page so an empty value is visible.

**Value:** Held receipts, re-match results and Criss's notes reach the person who closes the month the same hour, with no dependency on one person's inbox or computer. (effort small)

**Reviewer corrections:** none recorded

**Held-mail half shipped 2026-09-17 (PR #1001, Fly v153), owner ruling: "one to matthias and one to the email it was sent by".** The operator alert is unchanged (recipients `intake.alert_recipients`, still unset, so the default matthias.silva). The address a held mail came from now gets one plain-English notice ("Receipt not filed yet", worded per held status), under exactly the ack's guards: `intake.auto_ack` on, not auto-generated, no agent-directed text, and only @brisken.com or `intake.known_senders` (a stranger gets nothing, per rule_untrusted_inbound); stamped once per archive in `held_notice_at`. No settings write was made. Still open from this item: the laptop notifier (feedback notes, re-matches, publish pings) stays Matthias-only, Criss's Hotmail is not a known sender, and the owner is correcting the misspelled known sender `neuamth4@icloud.com` by hand.

**Alert recipients set 2026-09-17 ~16:55 UTC, owner ruling "Criss + you".** One `PUT /api/settings` `{intake}` carrying the stored object back with only `alert_recipients` changed to `["cristiane.cavalcanti@brisken.com", "matthias.silva@brisken.com"]` (`applied: ["intake"]`); re-read after: every other intake key identical (aliases, `auto_ack` true, `known_senders` now spelled `neumath4@icloud.com`, `travel_alias`). Held-mail operator alerts now go to both, sent from the matthias.silva mailbox; the alert body is English. Unchanged and still open: the laptop notifier (feedback notes, re-match and publish pings) is Matthias-only, and Criss's Hotmail is not a known sender.

### 122. The mailbox starts refusing all receipts once the 1 GB disk is half full, and a stranger can fill it in a day (2026-09-17 audit draft #120, unranked; operations) (SHIPPED 2026-09-17, pending PR)

**Audit rank 29 of 40; severity high as merged; verification: checked by hand (constants in code; 88 MB of 974 MB used); no reviewer pass.** The mailbox turns mail away with a temporary error when less than 500 MB is free on a 1 GB disk, so refusals start at about 474 MB used. After a month of real use it holds 87 MB (47 MB month folders, 38 MB mailed receipts), everything is kept ten years, nothing is trimmed, 'dismiss' keeps the bytes, and no health check shows free space, so at this pace refusals begin around early 2027 with Dirk's receipts bouncing mid-close as the first sign. Anyone can send 25 MB messages 200 times a day to any address at expenses.brisken.com (98 relay probes in seven days show it is being scanned), so one afternoon of junk reaches the floor. Meanwhile our own people are capped at 40 files a day, which a month-end backfill exceeds.

**Evidence:** web/intake_mail.py:108 (floor 500 MiB), :649-653, :93-94 (40 per sender, 200 global), :97-100 (ten-year retention), :3200-3230 (retention deletes only at boot), :3559-3590 (dismiss keeps archive); web/smtp_server.py:56 (25 MB), :125-128 (452 storage low), :134; app.py:749-757 (health check has no disk); live flyctl volumes list 1GB; df -h /data 2026-09-17: 974M size, 87M used; du: runs 47M, inbound 38M; inbound log n_probes 98. TARGET-ARCHITECTURE.md:240 sizes 3 GB inside the unscheduled consolidation. Backlog grep disk/500 MB/1 GB: 0.

**Already tracked:** none in the backlog; items 42 and 30b make refusals visible; TARGET-ARCHITECTURE 4.2 sizes a future volume.

**Proposed change:** Grow the disk to 5 GB now (one command, cents per month), make the refusal floor a share of the disk or a fixed 200 MB, put free space on the health endpoint, give unknown senders a much smaller message size and a daily byte budget, let known senders bypass the 40-file cap, and add a purge for dismissed archives.

**Value:** Receipts keep arriving through 2027 instead of bouncing with no warning, and a prank or a scanner cannot stop Brisken's own receipts. (effort small)

**Reviewer corrections:** none recorded

**Shipped 2026-09-17 (pending PR).** The floor is read from the volume instead of a constant: 5% of the disk, never below 200 MB, never above half of it. On the live 1 GB volume that is 200 MB where it was 500 MiB, so usable space goes from about 500 MB to about 800 MB; on a 5 GB volume the same code asks for 256 MB and leaves 4.75 GB. `/healthz` carries a `disk` block (total, free, used, free percent, the floor, and `intake_refusing`), so a monitor sees a filling disk rather than learning about it from bounced receipts; an unreadable volume answers `available: false` and still never refuses mail. An unrecognised sender is held to 5 MB per message (552, permanent) and all strangers together to 50 MB a day (452, so their own mail system retries tomorrow); the daily budget is global rather than per-sender because From is forgeable, and it re-seeds from the acceptance log after a restart (rows now record `n_bytes` and `known_sender`). Our own people (inside @brisken.com or listed in `intake.known_senders`) keep the full 25 MB and are exempt from the 40-file per-sender cap a month-end backfill exceeds; the 200-file global cap still binds everyone, because that is the ceiling on a day's vision spend. The dismissed-archive purge is built and ships INERT: `intake.dismissed_purge_days` defaults to 0 (never) and the boot sweep does nothing until it is set. Live numbers read while building (2026-09-17, `flyctl ssh`): /data is 997,076 KB with 97,876 KB used and 831,208 KB free, 11% used, on the 1 GB `recon_data_v2` volume. **Owner actions:** (a) `flyctl volumes extend` to 5 GB, still worth doing and untouched here (the code is tested on both sizes); (b) one settings write to turn the purge on, if deleting dismissed junk after N days is wanted - deleting Brisken's mail is not an agent's call.

### 123. Nobody is told when the app is down; the last outage was surfaced by the owner, not by a monitor (2026-09-17 audit draft #121, unranked; operations)

**Audit rank 30 of 40; severity medium as merged; verification: one reviewer, plus health check read by hand.** There is no outside check on the app or its mailbox and no alert to anyone at Brisken; hosting notices go to the developer's personal account; logs die with the machine. The 2026-09-10 outage lasted about 50 minutes and was noticed when Criss's upload failed. During close week an hour down is an hour she cannot work, and a mailbox down means receipts bounce.

**Evidence:** fly.toml [http_service.checks] (platform-internal, no alerting target, no log drain); web/machine.py:1-14 ('its logs went with it'); backlog item 50 (1836-1934: the probe records browser-side failures after the fact); status/p1-expense-reconciliation.md:33-36; OWNERSHIP-HANDOFF.md:63-73; app.py:749-757 (health check has no disk or listener state).

**Already tracked:** Item 50 (client-side probe built; SPA half pending) covers 'prove a recurrence', not 'tell Brisken it is down'.

**Proposed change:** Point a free external monitor at the health check and at the mailbox's port-25 greeting every few minutes, alerting a Brisken mailbox and the developer; add free disk space and the mail listener's state to the health check so the same monitor warns before a refusal.

**Value:** An outage is known within minutes by someone who can act, and a filling disk is known a month before it bites. (effort small)

**Reviewer corrections:** (combined) (1) "found by Criss" is not what the record says: the 2026-09-10 checkpoint and friction-register row 318 state "the owner surfaced the outage, not me"; Criss's "Failed to fetch" screenshot (item 50, 10:00:43Z) is recorded as unexplained and 42 minutes before the failed deploys, so tying it to the 50-minute wedge is unproven. The outage was triggered by the agent's own HTTP probing that woke a scale-to-zero machine which then wedged on a capacity-exhausted host. (2) A free-disk check already exists in code: intake_mail.py disk_low() refuses inbound mail below MIN_FREE_DISK_BYTES (500 MB); what is missing is only surfacing that floor via /healthz before it refuses, so "add free disk space to 

### 124. Each deploy installs whatever library versions are newest that day, not the tested ones (2026-09-17 audit draft #122, unranked; operations) (SHIPPED 2026-09-17, pending PR)

**Audit rank 31 of 40; severity medium as merged; verification: one reviewer, plus Dockerfile read by hand.** The repository keeps an exact list of tested library versions, but the container build ignores it and installs from open-ended ranges. Two deploys a week apart can run different versions of the web framework, the OpenAI client, the PDF reader or the mail listener. The suite runs against the locked set, so a green build does not prove the production set; a breaking upstream release lands in Criss's app on the next deploy with no code change.

**Evidence:** Dockerfile:15-20 (copies pyproject.toml and src only; uv pip install --system --no-cache '.[web]'); pyproject.toml dependencies all open ranges (openai>=1.50, fastapi>=0.110, aiosmtpd>=1.4, pypdf>=5.0, reportlab>=4.0); uv.lock (156 KB) never copied into the image; README.md:237-242 (deploy by hand). Backlog grep uv.lock: 0.

**Already tracked:** none

**Proposed change:** Copy the lockfile into the image and install from it, so production runs exactly the versions the tests ran against; upgrades then happen on purpose in a commit.

**Value:** A deploy changes only what the developer changed; a bad library release cannot take the month down by itself. (effort small)

**Reviewer corrections:** (combined) The install command is Dockerfile line 21, not within the cited 15-20 (15-17 are WORKDIR + the two COPYs). No actual drift incident is documented; the risk is latent, not observed. The lock is in sync with pyproject (both last changed in #584, 2026-08-23), so "install from the lock" needs no re-lock first. Note the lock already carries openai 2.x (2.38.0), so the major-version jump has already been absorbed on the tested side; the exposure is future releases, not a pending known break.

**Shipped 2026-09-17 (pending PR).** The Dockerfile copies `uv.lock` into the image and installs from it: `uv export --frozen --no-dev --extra web --no-emit-project` writes a fully pinned, hash-checked requirements file, that is installed first, and the project itself goes in with `--no-deps` so nothing re-resolves behind the lock. `--frozen` means a drifted lock fails the build instead of quietly resolving something new. Built locally (`docker build`, no deploy) and the image's versions read back: fastapi 0.136.3, openai 2.38.0, pypdf 6.13.2, aiosmtpd 1.4.6, uvicorn 0.49.0, reportlab 5.0.1, pillow 12.2.0, and `expense-recon-web` still on PATH. The drift the reviewer called latent is real and live: the running machine (v169, read over `flyctl ssh` 2026-09-17) carries fastapi 0.141.1, **openai 3.14.1**, pypdf 6.19.0, uvicorn 0.53.0, pillow 12.3.0 - a major openai version the suite has never run against. **Owner action:** the first deploy after this lands moves production back onto the locked set, openai 3.14.1 down to 2.38.0 included; that is the point of the change (run what was tested), and it is a real behaviour change to make deliberately rather than notice afterwards. An upgrade from here is `uv lock --upgrade`, the suite, then a deploy (README Deploy section).

### 125. Receipts travel to the mailbox without encryption on the wire (2026-09-17 audit draft #123, unranked; operations)

**Audit rank 32 of 40; severity medium as merged; verification: one reviewer (inferred from the listener config, no live transit observed).** The listener on port 25 does not offer STARTTLS, so a sending mail system that would normally encrypt falls back to plain text for this domain. Every forwarded invoice, card slip and receipt crosses the internet readable, with card digits, names, addresses and amounts, into an archive kept ten years. Nothing is lost, but the compliance write-up rates this High and a client's IT department may reject it at ownership transfer.

**Evidence:** web/smtp_server.py:183-189 (Controller with no TLS context, no STARTTLS requirement); fly.toml [[services]] raw TCP pass-through on port 25, so the proxy cannot add it; docs/electronic-storage-system-description.md gap row 6 (High); SPF/DMARC exist for outbound only (memory project_brisken_expense_recon_mail_intake). Microsoft 365 cleartext fallback is standard behaviour; not observed on a live transit. Backlog grep STARTTLS/TLS: 0.

**Already tracked:** Storage write-up gap 6 only; TARGET-ARCHITECTURE P7 plans retiring the listener for ownership reasons. Not in the backlog.

**Proposed change:** Add an opportunistic STARTTLS certificate to the listener (Let's Encrypt for the mail host name, renewed by the app), or bring forward the move to an Exchange mailbox read through Graph, which Microsoft encrypts end to end.

**Value:** Receipts and card data stop crossing the internet in the clear; the handover to Brisken IT loses one objection. (effort medium)

**Reviewer corrections:** (combined) "SPF/DMARC exist for outbound only" is loosely phrased: the DNS records for expenses.brisken.com are `v=spf1 -all` and DMARC `p=reject` (memory project_brisken_expense_recon_mail_intake), i.e. anti-spoofing declarations that nothing legitimately sends from that domain; they say nothing about transport encryption either way, so they are not counter-evidence, just irrelevant to this risk. The cleartext fallback is inferred from standard Exchange Online behaviour, as the finding itself admits; no live transit was observed (a live EHLO probe was not run to avoid adding refused-log entries). Otherwise numbers and citations check out; smtp_server.py line span is ~182-188, not 183-189.

### 126. No month has ever been closed by Criss, so 'done' has never been tested on the only test that counts (2026-09-17 audit draft #124, unranked; operations)

**Audit rank 33 of 40; severity high as merged; verification: published_runs 0 confirmed live; no reviewer pass.** Every item ships as done after the developer reads the live data, greps the published bundle and drives the app. Nobody has signed off a month: published months are zero, the sign-off memory feature has never fired, and the blueprint's done-state list is unticked. Criss's notes have waited a week. From October the licence covers 'the software doing the wrong thing', and without one month closed by her alone there is no baseline for what right looks like.

**Evidence:** Live /api/operator/state 2026-09-17: published_runs 0. BLUEPRINT.md:1148-1160 (checklist unticked, 'Chris runs expense-recon --config without help'). SPEC-GAP-REGISTER.md shortlist item 7. Memory project_brisken_expense_recon_usability_loop (note #32 waited a week, #34 five days); project_brisken_retainer_600_licence ('Criss cannot run the tool unaided'). docs/PROMPT-STATUS.md: every verification is a developer-driven drive.

**Already tracked:** SPEC-GAP-REGISTER item 7 and the BLUEPRINT checklist; no backlog item.

**Proposed change:** Before 2026-10-01, ask Criss to close one month (August) on her own, timed, with the developer watching only; treat the sign-off as the acceptance event and record it; every note she leaves in that hour becomes the defect list the licence starts from. Clean the test runs out of the list first (also_noted).

**Value:** Turns done from the developer's word into a closed month and gives the licence a measured starting point. (effort small)

**Reviewer corrections:** none recorded

### 127. Matching accuracy is measured by hand, offline, and nothing runs it before a deploy (2026-09-17 audit draft #125, unranked; operations)

**Audit rank 34 of 40; severity high as merged; verification: finder's evidence only, not independently rechecked.** The one instrument that catches a silent wrong auto-match (the labelled-month scorer with its holdout guard and the attribution tool) lives outside the automated checks: the labels are Brisken data in a git-ignored folder, the pipeline runs unit tests only, and the shipped fixtures hold one synthetic seven-row file. The scorer was broken for seven weeks and nobody noticed until a session tried to use it. Criss's own verdicts (rejected pairings, re-picks, withdrawn self-confirmations) are recorded but never added up, so an October precision slip would be found by her one wrong row at a time.

**Evidence:** .github/workflows/expense-recon-tests.yml (pytest only); tests/fixtures/ (sample_amex_export.csv); labels in the main clone's gitignored context/expense-reconciliation/expense-reports/csv/by-month/ (8 bundles, 307 rows, mtime 2026-09-15); backlog item 69 (2684-2700): 'recon-match-accuracy.py exited on the first bundle and the anti-overfit guard had been non-functional since 2026-08-25'; tools/recon-accuracy-guard.py, tools/scorers/recon-match-accuracy.py, tools/recon-match-attribution.py run by hand; service.py:10251-10254 (llm cost replaced per re-match), n_rejected_pairings 0 on both months; memory project_brisken_recon_matching_program ('re-run the attribution before AND after any matcher change').

**Already tracked:** Item 69 (CLOSED) repaired the scorer and prescribed the habit; ANNEALING E8. Nothing makes the run mandatory, visible, or continuous.

**Proposed change:** Make the scorer and guard a required deploy step with the score pasted into the PR; commit a small anonymised month bundle so the pipeline can run it on every change; add a per-month tally the tool computes from what it stores (tool pairings the reviewer rejected or re-picked, self-confirmations taken back, total model spend), shown on the operator state and mailed with the re-match notices.

**Value:** A matcher regression that keeps the tests green is caught before it reaches Criss's months, and the licence promise on wrong figures gets a number every month. (effort medium)

**Reviewer corrections:** none recorded

### 128. Three defect classes that repeated still have no automatic guard: reader drift, prompt edits, and the mail path end to end (2026-09-17 audit draft #126, unranked; operations)

**Audit rank 35 of 40; severity medium as merged; verification: one reviewer.** The CSV and Excel statement readers are separate code with no test that feeds the same statement through both and demands the same result; the September sign defect was exactly the two drifting apart. A repaired reader cannot find the months it already misread (the per-statement version stamp was not built; the re-read route is terminal-only). Status vocabularies added since item 21 (turn, row_type, reason_code, month_health.state, duplicate state) are mapped by hand in the SPA with no label pin, so a new backend value renders as someone else's label. Any edit to the receipt-reading prompt moves 12 to 41 of 129 stored readings and empties the cache, with no check that notices a prompt edit. The mailbox tests stub routing at the acceptance reply; no test starts the real listener and follows a message to a receipt in a month.

**Evidence:** Backlog item 55 (2400-2449): 'Store a parser fingerprint per statements[] entry ... Not built'; grep tests/ for a CSV/XLSX parity test: none; docs/api-contract.md:99-106, :639-678 rule 5; tests/test_intake_mail.py:2643 (label test, intake statuses only), :240-257 ('Routing is stubbed'); RunWorkbench.tsx:1745-1746 (hand maps); llm/extraction_cache.py:20-26, :54-60; memory usability_loop item 77 ('ANY instruction edit perturbs readings'); tools/ has no extraction A/B script; grep tests/ for smtp_server start-up: none; PROMPT-STATUS.md:8, :39-46 (audit scripts in %TEMP%).

**Already tracked:** Item 55 follow-up (unnumbered, 'Not built'); items 21/22 shipped with guards scoped to list shapes; api-contract rule 5 names the enum hole; items 4 and 7 describe the prompt-drift symptom; item 50 covers the machine being up. None is a ranked item.

**Proposed change:** One test that reads the same Chase workbook as CSV and as Excel and fails on any difference; a reader-version stamp on each loaded statement shown as a month advisory when the reader changed; extend the has-a-label test to every status vocabulary the UI maps; pin the prompt fingerprint in a test so an edit fails until bumped with the comparison attached, and commit the comparison runner, the bundle audit and the prompt ledger to tools/; one test that starts the listener on a spare port and follows a message to a receipt in a month.

**Value:** The next parser drift, count flip, unlabelled status, prompt tweak or listener regression is caught in the pipeline instead of by Criss on a live month. (effort medium)

**Reviewer corrections:** (combined) (1) "nothing automated proves a mailed receipt lands in a month" is wrong: test_intake_mail.py:392 test_mail_lands_in_open_batch_with_provenance runs process_message(synchronous=True) on a raw mail and asserts the receipt appears in /api/expense-batches/{id} with provenance; only the SMTP listener leg (Controller on a port to handle_DATA) is untested. (2) "the bundle audit lives in a temp folder" is wrong: tools/lovable-bundle-audit.py is committed in the main repo's tools/ (with controls and exit codes); only prompt_ledger.py and the A/B runner are in %TEMP%. (3) "no label pin" is overstated for turn: tests/test_view_contract.py:1115 pins TURNS as a literal closed set, so a new backend turn

### 129. A re-match happens silently: neither the drop page nor the month page says it ran or which rows moved (notes #53, #54) (2026-09-17 audit draft #127, unranked; UI prompt for the owner to paste)

**Audit rank 36 of 40; severity medium as merged; verification: one reviewer.** When a receipt arrives, a card is fixed or master data changes, the month is re-matched in the background. The only record is a counts-only event on an operator endpoint and a developer mail; the app shows nothing but a toast if it fails. The drop page tells Criss which month a file was filed into, not whether it found its charge; the month page has no 'last re-match' line and no way to see what changed since she last looked. The owner's notes #53 and #54 ask whether dropped or mailed receipts get the full treatment; the answer is yes (F27) but she cannot observe it, and finding rows she already looked at silently changed is how trust is lost.

**Evidence:** Live rematches[] event shape: run_id, label, event_id, at, trigger, counts, no row ids; SPA grep for 'rematch': only ExpensesReviewGrid.tsx:1663-1669 failure toast; ReceiptsDropScreen.tsx:166-296 renders filed / needs_month rows with month names only; backlog item 75 residue lines 3640-3642 ('a re-match happens silently ... the reviewer has no way to tell'); feedback #53 (2026-09-16T22:25Z) and #54 (22:27Z).

**Already tracked:** Item 58 (developer-side notification, shipped) and item 75's residue sentence; note #40 closed in item 75 as 'a visibility gap'; notes #53/#54 not in the backlog. The gap is tracked in pieces; nobody owns the screen half.

**Proposed change:** On the drop page, after filing into a month with a statement, one line per file ('matched with ANTHROPIC 51.38' / 'no charge on the statement yet' / 're-match failed, the month will retry'); record which rows changed bucket or pairing in each re-match event; show 'Last re-match: date, trigger, N matched' and a 'since you last looked' line on the month strip with the moved rows marked. Answer #53 and #54 with the verified yes.

**Value:** Criss sees in the same minute whether a receipt she dropped or mailed found its charge, learns what changed without re-reading 112 rows, and the owner's two open questions close with evidence. (effort medium)

**Reviewer corrections:** (combined) (1) "the app shows nothing but a toast if it fails" is true only for the in-app edit/upload routes (app.py:2051, 2873 return `rematch`); the receipts-drop route drops the rematch object before replying, so the drop page shows nothing even on failure, and mail intake has no screen at all. (2) "no 'last re-match' line" is overstated: both payloads carry `updated_at` (shipped 2026-09-16, api-contract.md:2093), which the SPA prints as "Last updated" and which advances on every re-match commit; what is missing is the trigger and the result, not the time. (3) Live rematches[] count is 23, not 18 (brief snapshot); August's latest event reads 114 charges / 30 receipts / 21 unmatched receipts, so the

**2026-09-17, note #53 answered and the drop-page half shipped (PR #988, Fly v150).** Answer: yes, each dropped file is read and filed into the month printed on it (created when absent; an unreadable date is held as `needs_month` and asks for a month), and a month that already holds a statement re-matches on the arrival. The drop ledger now carries `months[].has_statement` and `months[].rematch` (`{ok, n_transactions, n_matched, n_review, n_unmatched_tx}` or `{ok: false, error}`) instead of discarding the arrival's re-match result; the matching line is `docs/lovable-feedback-0917b-prompt.md` section 5. Still open from this item: the per-file "matched with X" line, which rows moved, and the month page's "last re-match" line.

### 130. English sentences from the backend still reach Criss's Portuguese screen: every error toast, the setup advisories and the crash page (2026-09-17 audit draft #128, unranked; licence: defect, covered) (SHIPPED 2026-09-17, pending PR; SPA prompt written; Shipped row 72) (SPA §1-§5 APPLIED AND VERIFIED 2026-09-18; §6 the two error screens NOT applied, prompt `docs/lovable-error-page-lang-prompt.md` written 2026-09-18, awaiting paste)

**2026-09-18 verification, and one half that has to be re-asked.** Five of the
six sections are live and driven. The `errorText` helper and the advisory helper
are both in the shipped bundle with their `hasKey` guard, and they are WIRED, not
merely present: the workbench route chunk holds 16 `toast.error(errorText(e, t))`
call sites and zero remaining `.message)`, and no chunk anywhere still shows a
caught error's raw `.message` to the reader. The row chips render in both
languages on the same row: NEAR MISS in EN, QUASE IGUAL in PT.

**§6 did not land, and the note saying it could not be checked was wrong.** The
crash screen and the not-found screen are client React components in the entry
chunk (the TanStack root `errorComponent` and `notFoundComponent`) with their
English written straight into the JSX, so a bundle crawl sees them perfectly
well. Driven cold in Portuguese, `/this-route-does-not-exist-xyz` renders "404 /
Page not found / The page you're looking for doesn't exist or has been moved. /
Go home" while every other surface is Portuguese. These are the two screens a
reader meets when something has already gone wrong, which makes them the worst
two to leave in a language she does not read. Copy only, no backend gate.

**The prompt's own check 4 could never have passed** and should not be counted
against the work: `/runs/does-not-exist-abc123` renders the SPA's own missing-run
screen, which has always had its own Portuguese string and issues no API refusal,
so no `code` reaches `errorText` there. `err.run_not_found` is in the dictionary
in both languages and fires on a refusal that carries the code, such as a
download against a deleted month.

**Audit rank 37 of 40; severity medium as merged; verification: one reviewer, severity lowered.** The front-end dictionary is complete (1,403 keys in both languages), but the text Criss reads at the worst moments is not in it. A refused save or decision shows the backend's English sentence verbatim; the two amber advisory boxes at the top of a month print English prose; the 'amount mismatch' chip is a hard-coded English string; the crash page is English only; the two PDFs and CSV headers are English. Criss's August note was 'language should not differ from what is set by user'; the shipped fix covered review reasons and upload issues only, and the Portuguese wording of the newest screens has never been read by her.

**Evidence:** SPA main d08e352 lib/api.ts:166 and :1333 (msg = String(d.error)), toast.error(e.message) at 12 sites in RunWorkbench.tsx, 16 in ExpensesReviewGrid.tsx, 3 in SettingsScreen.tsx; RunWorkbench.tsx:1462-1487 (advisories raw), :1688, :593 ('amount mismatch' literal; PROMPT-STATUS item 81 row); lib/error-page.ts EN only; i18n.tsx 1403 EN = 1403 PT keys. Backend app.py:3627-3640 (English strings without a code). Feedback note #20 (2026-08-21). Backlog item 79 (3971) 'PT wording of the new keys' open; item 89 PT wording draft.

**Already tracked:** Items 14+15 (Shipped row 12) and item 20 (row 16) moved review reasons and upload issues to codes; item 79 leaves the PT pass open. Error toasts, advisories, the mismatch chip and the crash page are not tracked.

**Proposed change:** Every refused request carries a stable code beside the English error, and the front-end shows its own Portuguese sentence for known codes (English as fallback); give the advisory blocks and the health detail a code, replace the hard-coded chip with a dictionary key, localize the crash page, and have Criss read the Portuguese screens once. The PDFs stay English (the auditor reads English) unless Dirk asks.

**Value:** When the tool refuses something, Criss can read why in her language instead of guessing or asking. (effort medium)

**Reviewer corrections:** (combined) Feedback note #20 (2026-08-21, "language should not difer from what is set by user") was recorded under operator code "matthias", not by Criss; the backlog's Shipped row 12 attributes it to "her notes" but the record does not prove Criss wrote it. The advisory blocks are structured `{setting, message}` objects, so "print English prose" is accurate but they already carry a machine-readable `setting` field the SPA keys off (`a.setting === "cards"`); only the sentence lacks a code. i18n key count could not be reproduced exactly (2,802 key lines in i18n.tsx, consistent with ~1,401 per language, not verified as 1,403).

**Shipped 2026-09-17 (pending PR).** Every refusal the API sends is now `{error, code, ...named values}`: the English sentence is UNCHANGED and stays what an English reader, a log and every existing client sees, `code` is a stable snake_case name for the CONDITION (never the wording), and whatever the sentence names (a file, a month, a card, a count, a limit) rides as its own field, so the screen composes a Portuguese sentence from data instead of translating English with numbers baked in. 155 codes over 285 sites: `web/app.py` (every `JSONResponse` refusal, the auth 401, the login 401, the rate-limit 429), `web/service.py` (65 `RunInputError` raises, the helpers that RETURN a sentence, the trip refusal dicts), `web/intake_mail.py` (26 mail refusal dicts), `web/ratelimit.py`, and the three settings normalizers (`cards.py`, `merchant_registry.py`, `cost_centers.py`, plus `normalize_intake_setting`). Three carriers in the new `error_codes.py`, each chosen so no caller's type changes: `Refusal` IS a `str` (every `==` against a sentence and every `if err:` still holds), `CodedValueError` IS a `ValueError` (the normalizers' callers catch it unchanged), and `RunInputError` gained `code` + fields. The framework's own refusals joined the shape: a body FastAPI cannot bind answers `validation_failed` and a path no route serves answers `not_found`, both keeping FastAPI's `detail`; the four download 404s that answered HTML now answer JSON (the SPA's `downloadFile` parses JSON and showed "Download failed (404)" for them). A service refusal dict keeps its int HTTP status under `code` and adds `error_code`, which `app._refusal_response` turns into the body's `code`, so the int never reaches the wire. Advisories: the three older `setup_advisories` entries carry a code and their numbers beside item 132's `fx_rate_drift`, and the two statement advisories carry a PARALLEL `statement_advisory_detail` / `statements[].advisory_detail` rather than retyping the prose field the SPA already reads (the 2026-08-22 lesson). `month_health` was already coded (`reason` + `suspects` + `n_exact_pairs`) and is untouched. Tests: `tests/test_error_codes_item_130.py`, 20 of them, and the first half is what keeps this true next month: a SOURCE SCAN that fails a new `JSONResponse` error body with no code, a `RunInputError` raised without one, a service refusal dict with no `error_code`, a helper returning a bare English sentence, a normalizer raising a plain `ValueError`, an advisory with no code, a code that is not snake_case, and a plain-text 4xx; the second half drives one refusal of each family through the app (auth, unknown run, unknown path, 422, a field edit, the company-card decision, the publish gate, a set-aside input refusal, a trip refusal dict, two settings refusals) plus the advisories on a real run. regress_check red on four wires: the 401's code (source scan + route both red), an advisory's code, the service-dict `error_code` plumbing in `_refusal_response`, and one `RunInputError` code. Suite 2286 passed / 2 skipped. Contract: api-contract "Error codes (item 130)", the full table plus the advisory tables. SPA half: `docs/lovable-error-codes-prompt.md` (the `err.*` / `adv.*` / `warn.*` dictionaries in EN + PT-BR, the mismatch chip, the crash page off `brisken.lang`), written, NOT pasted; PROMPT-STATUS row added. Not built: the SPA itself until that prompt is pasted, so today nothing on Criss's screen changes; the PDFs and the CSV stay English by the item's own ruling (the auditor reads English); background job errors (`GET /jobs/{id}`) still carry prose only, because a job's error reports work that already started rather than refusing a request; and Criss has still never read the Portuguese wording of these screens, which is the one thing no test here can stand in for.

### 131. The tool suggests pairs its own model calls 'likely NOT the same purchase' (2026-09-17 audit draft #129, unranked; licence: defect, covered) (SHIPPED 2026-09-17, pending PR; Shipped row 65)

**Audit rank 38 of 40; severity medium as merged; verification: one reviewer, plus the 0.20 floor read by hand; severity lowered.** For foreign-currency pairs the tool cannot settle, a model gives a same-purchase probability; the owner ruled on 2026-07-24 that a pair the model rejects must not be shown. The cut-off is 'below 0.20', the model commonly answers exactly 0.20, so those pairs are shown with the model's own text 'likely NOT the same purchase (p=0.20)', and that sentence replaces the tool's arithmetic (same day, 1.5% off the reference rate) in the reason the reviewer reads. July has two such rows: a wrong pair (NOBRE 65.23 against a Fenix 325.88 BRL receipt) and a right pair the model got wrong (NATHALIA 5.61 against a 28.73 BRL receipt). Both are booked rows, so nothing was lost this month.

**Evidence:** cli.py:367 (full.confidence < suggest_floor suppresses; 0.20 passes), :357-364 (verdict replaces reason); matching/deterministic.py:354-366 (floor 0.2, owner ruling in the docstring). Live 2026-09-17 July review rows: NOBRE ATACAREJO 65.23 candidate 0059 fx_judgment 0.2; NATHALIA KEILA FIRMIN 5.61 candidate 0062 fx_judgment 0.2; labels 0059 excluded, 0062 confirmed (notes.csv: '28.73 BRL at the month rate = 5.53, 1.5% off, same merchant name, same day').

**Already tracked:** none (the ruling lives only in a code comment)

**Proposed change:** Treat 0.20 as rejected as the ruling intends, but keep a pair whose own rate arithmetic sits inside the clean band in Needs review with the tool's reason first and the model's disagreement second. A pair with neither goes to unmatched.

**Value:** The reviewer stops reading suggestions that argue against themselves, and a true pair is not lost because a model was unsure. (effort small)

**Reviewer corrections:** (combined) (1) "the model commonly answers exactly 0.20": in the live July month 2 of 7 fx_judgment candidates sit at 0.20, the other 5 at 0.85; "commonly" is unsupported, it is a boundary value seen twice. (2) "that sentence replaces the tool's arithmetic in the reason the reviewer reads" is overstated since item 81 (PR #903, 2026-09-16, applied in the SPA per PROMPT-STATUS row 166, the NOBRE +4.01% amber line was browser-driven): every fx_judgment candidate carries `fx.reference_rate / reference_converted / reference_gap_pct / reference_gap_band` and the SPA renders the conversion line beside the row; only the free-prose `reason` leads with the model verdict, and NATHALIA's reason even includes "~5.4

**Shipped 2026-09-17 (pending PR).** `cli._apply_judgment` keeps the owner's 2026-07-24 cut exactly as ruled: a model verdict BELOW `fx_judgment_suggest_floor` (0.20) is final and unbinds the pair, whatever its rate says. A verdict EXACTLY AT the floor now counts as a rejection too (it used to pass), with one exception: a pair whose own rate arithmetic sits in the clean band stays in review, `reason` = the tool's arithmetic, then "Kept for review although the model disagrees: " and the model's text; confidence stays the model's 0.2. The band is item 81's, not a copy: the conversion, deviation and band moved into `matching.deterministic.reference_gap`, which `_fx_reference_fields` (the `fx.reference_*` block) and the judgment layer (`pair_reference_gap_band`, at the matcher's `_reference_rate_for`) both call. The three callers pass `cfg=match_cfg`; `tools/recon-match-attribution.py` passes it too when the module takes it, so the judge replays the rule. A first build applied the exception below the floor as well and was narrowed the same day: on July it brought back `0034` (Erste Fracht 21.00 EUR vs HOTEL AM TIERGARTEN 24.02, -1.59%, model 0.10, notes.csv "another merchant") in exchange for dropping NOBRE, one wrong pair for another. Measured on a fresh DB copy (2026-09-17 evening; before = merged base `50425571`, after = this branch; `RECON_MODULE_SRC` proving the tree): class tables identical on July and August; July `review_other` 3 -> 2, the one move being `0059` (NOBRE 65.23, 4.01%, model 0.20, labelled excluded) review -> unmatched; `0062` (NATHALIA, labelled right) stays in review with the reason reordered; `0034` stays out; August replay diffs identical before and after. The bundle replay runs no judgment layer (70/95, scorer 76.0, nc_matched 0, measured on the first build). Tests: `tests/test_rejected_fx_pair_item_131.py` (4, route-level through statement attach and `GET /api/runs/{id}`: at-floor clean band kept, BELOW-floor clean band unbound, at-floor outside band unbound, 0.21 shown); `tests/test_fx_judgment_llm.py::test_apply_judgment_suggest_floor_keeps_stub_and_confident_pairs` pins 0.21 kept, 0.20 unbound without a config. regress_check red on every wire: the at-floor rejection (2 of 4), the exception's `at_floor` guard (the below-floor test, 1 of 4), the band exception (1 of 4), the `cfg=` pass in `rematch_month` (1 of 4). Contract: api-contract "A pair the model rejects (item 131)". No SPA change.

### 132. Every new month still matches foreign receipts at one September rate, and the gap is already 1.8% (2026-09-17 audit draft #130, unranked; licence: defect, covered) (SHIPPED PR #1048, Fly v167 - see Shipped row 71)

**Audit rank 39 of 40; severity medium as merged; verification: one reviewer, severity lowered; item 90 covers the fix.** Two typed rates (EUR to USD 1.162275, BRL to USD 0.192448, September values) are copied into every month at creation and always beat the per-month ECB rate the tool fetches since 2026-09-17. The clean band is 3%; the ECB July average is already 1.8% off the typed EUR rate, so about 1.2 points of headroom remain before true pairs drop into review or the band admits a coincidence. The agreed plan (tighten the band, then delete the typed rates) is right, but until it ships each month created (October on 1 November) is matched at a September rate, and nothing warns when the drift crosses the band.

**Evidence:** web/service.py:477-529 (apply_master_data copies settings fx_reference_rates with setdefault), :11704-11729 (apply_ecb_rates), called at month creation :4800 and statement attach/re-read :9216; matching/deterministic.py:908-910 (configured rate wins). Live /api/settings fx_reference_rates {BRL:USD 0.192448, EUR:USD 1.162275}; both months' FX candidates read reference_rate_source 'settings' (July 25, August 3). Backlog item 82 (4099): ECB July EUR:USD 1.141748 (1.8% off), August 1.159310; item 90 (4570) orders band first, rates second.

**Already tracked:** Item 90 (OPEN), framing complete; missing only the time dimension and a warning when the typed rate leaves the band.

**Proposed change:** Ship item 90 as planned, and in the same change make the setup advisory say, per month, how far the typed rate sits from the ECB average for that month. Removing the two typed rates stays an owner action per the ruling.

**Value:** Foreign-currency pairings (about a quarter of July's reconciled rows) keep resolving on their own as rates move, instead of decaying into review work. (effort medium)

**Reviewer corrections:** (combined) "About a quarter of July's reconciled rows" is understated: July has 31 reconciled rows and item 82 counts 17 chosen FX pairs (22 labelled), i.e. over half; live, 25 FX candidates sit on July rows, only 1 of them on a confirmed row. "About 1.2 points of headroom" is a mean figure: item 82's simulation measured July's worst pair at 2.93% deviation under the Settings rate, so the worst true pair already sits at the 3% edge (headroom ~0.07 points), and the ECB rate cut that to 1.41% max. The "true pairs drop into review" effect is prospective, not observed: the 2026-09-17 simulation found every live true pair inside the band at the Settings rate and the ECB rate bought no correct pair on July o

**Shipped 2026-09-17 (PR #1048, Fly v167), with item 90's band.** `matching.fx_ecb_match_pct` 0.02 is the clean band for a pair whose rate is the ECB monthly average and for no other source; a typed Settings rate and the self-derived rates keep 3% (one home, `MatchingConfig.reference_match_pct(source)`, read by `match_one`, `pair_reference_gap_band` for item 131's floor rule, and the view's `fx.reference_gap_band`). Measured before choosing, Settings rates removed, on a read-only DB copy at v165 (judgment from the snapshot cache, no model call): July 29 / 31 / 32 / 33 / 33 right at 3 / 2.5 / 2 / 1.75 / 1.5%, coincidental auto-matches 2 / 2 / 1 / 1 / 1 (Erste Fracht `0034` at +0.2% is out of any band's reach), August unchanged; the six bundles on ECB rates alone 68 / 70 / 70 / 70 / 69 of 95, 0 wrong. 1.5% loses a holdout pair, so 2% keeps headroom above it at the price of one July receipt (E A LOCACOES 340.00 BRL) staying in review with its right charge first. Scorer asset 76.0 and guard PASS unchanged. `summary.setup_advisories[]` gains `code: "fx_rate_drift"` (pair, settings_rate, ecb_rate, ecb_month, gap_pct, limit_pct, n_receipts) when a typed pair this month's receipts use sits more than 1 point (3% - 2%) from the month's ECB average, read through the matcher's own lookup. **Live at deploy: nothing moved.** July's 24 and August's 3 FX candidates all read `settings` / `match`, no month carries the advisory (July has no ECB table in its config; August's typed rates sit +0.3% EUR / -0.9% BRL from its average), and the SPA Matching pages render as before (driven cold, only non-GET the login). The band reaches live rows once the owner removes the two Settings rates (item 90 step 4), at each month's next re-match. 10 route-level tests; ten regress proofs by hand, all red; suite 2263 on the merged tree. Residual documented in api-contract: the judgment layer and the view derive self-derived rates from the whole receipt list, so a month holding three receipts with a booked exchange rate could read an ECB pair as receipts-derived (3%); no hosted month holds such receipts.

### 133. A same-amount receipt from another merchant, a few days apart, still files as Reconciled (2026-09-17 audit draft #131, unranked; licence: defect, covered) (bulk-confirm half SHIPPED 2026-09-17 with item 131, PR #1036; matcher rule (b) SHIPPED PR #1053, Fly v170 - see Shipped row 80)

**Audit rank 40 of 40; severity high as merged; verification: three reviewers; the value reviewer refuted it as already ruled parked (item 69).** When a receipt and a charge carry the same amount in the same currency, the tool pairs them without looking at who was paid: same day is a clean match, two to five days apart a 'probable' one, and both land in Reconciled, take the receipt from any other charge, and flow into every export (approval is not required for export). The merchant check from 2026-09-15 guards only pairs whose amounts differ; the 'card this statement does not carry' demotion guards only foreign-currency pairs. August produced this twice (Lovable 50 took BASE44 50.00; Anthropic 100 took BASE44 100.00 four days later), cured only because the receipts' card belonged to another company. Round subscription amounts recur across vendors monthly.

**Evidence:** matching/deterministic.py:711-718 (merchant floor only when amount_probable), :763-782 (EXACT: amount + date, no vendor), :784-808 (PROBABLE on exact amount within 5 days), :1326 and :1436-1438 (card demotion only for rate-derived pairs), :1467-1481. web/service.py:7950-7969 (any effective match is bucket reconciled, PROBABLE included), :3783 (export_approved_only gates the journal export only; live settings false). Backlog item 69 ~line 2710 and item 76 points 1 and 3 (3658-3680). August labels 0015/0025 record the two cured cases.

**Already tracked:** Item 76 shipped as row 51 without point 3; the exact-amount-with-day-gap hole and the absent-card guard for same-currency pairs are named nowhere.

**Proposed change:** Three small rules inside the pairing engine: a pair whose dates differ by more than a day must also agree on the merchant; a receipt naming a card this statement does not carry never settles a charge on its own (review, as foreign-currency pairs already do); a pair the tool flags for review is listed under Needs review, not Reconciled. Replay on the two labelled months first.

**Value:** Closes the last way a wrong pairing reaches the reports without a person touching it, which is the wrong-money class the licence must cover. (effort medium)

**Reviewer corrections:** (evidence) "Without a person touching it" is overstated: since item 76 (PR #925) a vendor-disagreeing EXACT pair (vendor_pct < 75) and any requires_review PROBABLE pair never self-confirm (service.py:11440-11470, SELF_CONFIRM_VENDOR_FLOOR = 75), read turn=decide, count in n_undecided and hold ready_to_post False (service.py:3563). The true leak is narrower: the pair sits in the Reconciled bucket, holds the receipt, and reaches zoho.csv / reconciled.csv / report.xlsx and /publish because none of those is gated on the decision. "Named nowhere" is wrong: item 69 (CLOSED) names the exact-amount 4-day BASE44/Anthropic hole verbatim (~backlog 2708-2712), item 76 point 1 names vendor-blind EXACT (3658-3666),  (ledger) Three points. (1) "named nowhere" is overstated: the exact-amount-with-day-gap hole IS recorded in item 69's round-0 paragraph (backlog ~line 2707-2712: "the Anthropic 100 invoice bind BASE44 100.00, exact amount, 4 days, which the vendor floor of item 63 does not guard because it applies to non-exact amounts only"), in item 76 mechanism 1 ("EXACT has none") and its note-#44 line ("Widening `date_exact_window_days` while `EXACT` ignores the vendor would add wrong automatic matches of the BASE44/Lovable shape"), and item 54's closing measurement (every exact-amount far-date candidate on both live months was wrong, recurring subscriptions; a guard would need "card agreement plus no second same (value) (1) "named nowhere" is false: backlog item 69 (~line 2710-2712) names this exact hole ("Anthropic 100 invoice bind BASE44 100.00, exact amount, 4 days, which the vendor floor of item 63 does not guard because it applies to non-exact amounts only"), item 76 records "Not built: a PROBABLE/POSSIBLE pair flagged requires_review can still land in Reconciled (none on either month); it never self-confirms and reads decide" (~line 3794), and item 76's note-#44 paragraph names the "BASE44/Lovable shape" as the reason EXACT's window stays at one day. (2) "both land in Reconciled ... without a person touching it" overstates: since PR #925 a vendor<75 exact pair or any requires_review pair is turn=decid (value) REFUTED: The code reading is accurate (deterministic.py:711-718 floor only on the tip band, :763-808 EXACT/PROBABLE on bare amount+date, :1436-1438 card demotion only inside uniqueness_verdicts for RATE_DERIVED_TYPES, :1467-1481 an absent card leaves the receipt unscoped; service.py:7950-7969 buckets any effective match as reconciled; pending pairings do reach the reconciliation PDF via build_view rows and

**Characterization 2026-09-17, before the bulk-confirm half.** Measured route-level on the code as it stood: an "Anthropic, PBC" USD 100.00 receipt, categorized by the merchant book so only the pairing is in question.

- BASE44 100.00 four days later (PROBABLE) or the same day (EXACT), alone: Reconciled, holds the receipt, vendor_pct 22; `requires_review` true on PROBABLE, false on EXACT; `turn: decide`, never self-confirms (`n_self_confirmed` 0), blocks `month_complete`, so `/publish` answers 400 `month_not_complete`. zoho.csv carries "Payment to BASE44" and reconciled.csv reads MATCHED with Receipt Vendor "Anthropic, PBC" while undecided. One bulk click booked it: `POST .../decisions/confirm-matched` AND `.../confirm-ready` both confirmed the vendor-22 pair (confirm-ready reads the CATEGORY verdict, not the match), after which the month was complete and published (200).
- With an ANTHROPIC 100.00 rival at the same distance, the right merchant takes the receipt (score carries the vendor); on the same day it self-confirms (vendor 100).
- The matcher gap 76/99/100/137 leave open: BASE44 the same day (EXACT, 0.99) outranks ANTHROPIC three days later (PROBABLE, 0.85) on confidence before the vendor is compared, holds the receipt, and the right charge lists NO candidate.

**Bulk-confirm half, shipped 2026-09-17 (pending PR).** Item 101 (PR #1032) put "Confirm all matched" under `service.confirmable_pair`; `ready_confirm_pairs` ("Confirm all Ready") now requires it too, so neither bulk route can book a vendor-disagreeing or review-flagged pair. `tests/test_same_amount_other_merchant_item_133.py` (6, route-level): both routes leave the vendor-22 BASE44 pair pending on both shapes and publish stays refused; with the ANTHROPIC rival the right merchant takes the receipt and neither route books the PROBABLE pair. regress_check: dropping `and confirmable_pair(r)` reddens 3 of 6. `tests/test_web_review_state.py` updated: its synthetic pairs carry a vendor score so only the category separates them, and the endpoint test now expects the ready rows the pairing rule passes (one of the example month's two ready rows does not). Exports of undecided pairs stay by design unless Settings `export_approved_only` is turned on (owner setting, false live).

**It is live now.** On the 2026-09-17 15:16 UTC DB copy, August `0025__Invoice-H0LHY2WQ-0032.pdf` (Lovable 50.00, labelled `no_charge:unloaded_card`) is back on BASE44 50.00 (`6893f70af91095cb`, 08-22, card 3645, gray fill), EXACT, vendor 40, `turn: decide`, in the hosted outcome (parity OK on that pair; attribution August `wrong_exact_no_charge` 1, $50). Cause: Criss deleted the receipt copy `0026__Receipt-2714-0234.pdf` (the one naming Visa 1176) at 11:32:39 UTC, so round A's card inheritance has nothing to lend and the invoice is unscoped again. Deleting a card-bearing copy removes the evidence that scoped its twin.

**What item 69 ruled.** Nothing parks this hole. Round 0: "freeing the ATT pairing let the Anthropic 100 invoice bind BASE44 100.00, exact amount, 4 days, which the vendor floor of item 63 does not guard because it applies to non-exact amounts only), July 1 -> 0, nothing else moves. Taken as given." Round A then cured both BASE44 pairs through card inheritance, not a merchant rule, and the stop condition ("Stop after B: the next class (the Google twins ...) recovers at most 1 receipt a month, under the 3-a-month floor") is about recall, not this precision hole. The nearest rulings: item 76 note #44 keeps EXACT's window at one day because a wider one "would add wrong automatic matches of the BASE44/Lovable shape", and item 76's "Not built: a PROBABLE / POSSIBLE pair flagged requires_review can still land in Reconciled". Neither backlog nor api-contract records an owner decision parking it.

**The three proposed rules against what shipped.** (2) absent card: covered for any card the registry resolves (item 137 `cards_differ` demotion, plus entity scope; live `0015` Anthropic 100 naming ...1176 stays off BASE44 100.00 that way); residual only for printed digits no card names. (3) requires_review pairs under Needs review: contradicts item 137's design call ("the review bucket is the model's lane"), and 76/99/100 already make them `decide`, `n_undecided` and publish-blocking; do not build. (1) merchant must agree past one day: across all eight datasets there are 29 same-currency exact-amount candidates and 6 below the 0.50 floor, and all 6 are same-day EXACT, so the rule as written moves nothing today and misses the live pair (`0025`, one day, EXACT). Extending it to EXACT is where the score fails to separate: July Network Solutions 7.98 (0.46, labelled RIGHT, chosen), the July Google Workspace 71.64 twins (0.42, both RIGHT pairs), August `0025` -> BASE44 (0.40, wrong). A drop at 0.50 would silently remove right pairs, and no floor fits between 0.40 and 0.42.

**Matcher rule (b): proposed, NOT built.** Precedence only, in item 137's demotion shape: an exact-amount same-currency pair whose merchant disagrees yields to a rival for the SAME receipt whose merchant agrees (round B's dominance test: rival >= 0.5 and ahead by 0.25) by taking `requires_review` + a "the merchants differ" reason + confidence 0.55; with no such rival nothing changes. Evidence: no pair on the eight datasets moves (none of the 6 vendor-disagreeing exact-amount candidates has an agreeing rival: Network Solutions, the Google twins and `0025`); the live August `0025` on BASE44 50.00 is a reviewer's-turn pair with no rival, which rule (b) would not change, and which the bulk-confirm half now keeps from being booked by a click. It closes only the characterization's third shape (a same-day wrong merchant outranking a 2-5 day right one), which has no live instance; item 69's stop condition applies until one appears.

**Matcher rule (b) shipped 2026-09-17 (PR #1053, Fly v170).** An exact-amount same-currency candidate whose merchant disagrees (vendor below `uniqueness_vendor_dominance_min`) reads `requires_review`, confidence 0.55 and a reason saying the merchants differ, but only when a rival charge's candidate for the SAME receipt agrees on the merchant (>= 0.5 and ahead by 0.25), that receipt is the rival charge's own top-ranked candidate, and the rival is not awaiting a human pick; it runs after the ambiguity pass. The characterization's third shape is closed: BASE44 the same day no longer outranks ANTHROPIC three days later, and the right charge stops listing no candidate. Replay old vs new over July, August and the six labelled bundles moved 0 receipts, as this entry predicted; scorer 76.0, guard PASS; suite 2281. The adversarial review found two defects in the first draft, both reproduced and pinned: a rival that will take a better receipt of its own could strand this receipt, and the demotion could break a pass-1 tie a person should settle. Live: nothing moved (no live pair meets the rule); it applies at each month's next re-match. Rules (1) and (3) stay unbuilt for the reasons this entry records.

### 134. A right category guess could never leave "needs a look" (note #62, Criss, 2026-09-17) (SHIPPED PR #988, Fly v150; SPA APPLIED 2026-09-17)

Criss on August, row `0003__rendered-body.pdf` (OpenAI 80.04): "Já foi resolvido mas ainda aparece 'needs a look'". Live store, read-only: she set `paid_through` at 09:58:41 UTC and wrote the note at 10:19:42. The row's flag was `review.reason_code: vendor_guess` (category guessed from the vendor's name). Two causes: only a category override clears that verdict, so a correct guess had no exit short of picking a different category; and the SPA's copy for the code says the VENDOR was guessed (EN "The vendor was guessed from the file name", PT "O fornecedor foi deduzido pelo nome do comerciante"), so she checked the vendor, found it right, and considered the row done. Live at deploy: `vendor_guess` is the headline on 4 July and 4 August rows; `category_confirmable` is true on 10 July and 5 August rows (judged on the category alone, so rows headlined by another exception count too).

**Shipped:** `POST /api/runs/{id}/expenses/{doc}/confirm-category` keeps each line's current category as the reviewer's own (undo = the category PUT with `""`), plus `expenses[].category_confirmable`. SPA: "Keep {category}" under the reason line and corrected `vendor_guess` / `unknown_provenance` copy, `docs/lovable-feedback-0917b-prompt.md` sections 1-2.

### 135. The card could not be changed on a row whose receipt printed one, and a pick never reached the matcher (note #63, Criss, 2026-09-17) (SHIPPED PR #988, Fly v150; SPA APPLIED 2026-09-17)

Criss on August, row `0004__rendered-body.pdf` (Obsidian 96.00, printed "CorpServ & DN ••3645"): "Não consigo alterar o cartão caso precise." The item-87 picker renders only for `card_source` none / override / learned, so a printed card could not be corrected; at 10:20:31 UTC she set `paid_through` to "Credit Card - 2838" instead. Underneath, two backend gaps: a `card_key` edit never re-matched, and the matcher scopes a receipt by its printed `payment_mode`, so a picked 2838 would still have been scoped to 3645.

**Shipped:** `card_key` is a match field (a changed pick re-matches a statement month); in the matcher's pool only, a pick that contradicts a printed card replaces it (`hand_picked_card_mode`); receipts that printed no number, and re-picks of the printed card, match exactly as before. SPA: "Change card" on `hint` rows, `docs/lovable-feedback-0917b-prompt.md` section 3. Row 0004 keeps her `paid_through` override: a card pick changes the card, company and person, and a typed paid-through account still outranks the card's.

### 136. A receipt with one uncategorized line keeps asking for a category, and the row gives no way to set it (note #64, Criss, 2026-09-17) (SPA APPLIED 2026-09-17)

Criss on August, 11:29 UTC, row `0019__Invoice-B2EA98DF-0020.pdf` (Pressmaster FZCO 135.00): "Fiz as devidas alterações, dei refresh e ainda pede para informar a categoria." Live, read-only: the receipt has two lines, "Workspace / Team Member Aug 23-Sep 23, 2026" 39.00 (`LINE`, Software & Subscriptions) and "CUSTOM Aug 23-Sep 23, 2026" 96.00 (no category, `REVIEW`), so `review.reason_code` is `partial_uncategorized` and Books as reads "Software & Subscriptions 39.00 · (uncategorized - assign) 96.00". The one category override on the row is line 0 from 2026-09-16 08:17; at 11:28 today she set company, card and paid-through, never a category. The row's category dropdown displays "Software & Subscriptions" (the categorized line), so re-picking it fires nothing, and nothing on the Expenses row addresses a single line.

**No backend change needed:** `POST /api/runs/{id}/categories` with `{document_id, line_index, category}` already writes one line, and every row carries `line_items[]` with `index`, `description`, `line_total`, `category`. The fix is a per-line picker for the uncategorized lines on the row (SPA prompt).

**Prompt written 2026-09-17:** `docs/lovable-line-category-prompt.md`. Probed first on the current code with a two-line receipt: `line_index: 1` turns `partial_uncategorized` into the row's next exception, the line reads `EDITED`, and Books as loses its unassigned part.

**Applied 2026-09-17 12:42 UTC**, cold-driven: the Pressmaster row shows the one open line with its picker (EN + PT), no other row does. The pick itself is Criss's; the row leaves `partial_uncategorized` when she makes it.

### 137. Receipts are matched against every card's charges unless the receipt prints the card (owner, 2026-09-17; licence: defect) (SHIPPED 2026-09-17, Shipped row 59; SPA APPLIED 2026-09-17)

**Shipped.** Design calls made on live evidence, recorded so they can be revisited:

- **A hand pick scopes hard only while its card offers a candidate.** Live August, all 9 picks name 2838, and the one pick that contradicts a charge (`0027`, LOVABLE 25.00) is itself contradicted by the bank line and the label (charge on 3645, tool-confirmed 2026-09-16 before the pick). A pure hard scope would have silently un-matched that real pair, so a pick with no candidate on its card falls back to the other cards' charges, each demoted. In any contest between cards the pick decides.
- **Demoted = `requires_review` + reason + confidence 0.55, not the review bucket.** The review bucket is the model's lane (`judgment_required` sends every entry through the FX judge and replaces its reason); a demoted pair stays deterministic, cannot confirm itself (item 76), and loses every contest to a clean candidate.
- **A printed card outranks a resolved one in a tie** (signal 1.0 vs 0.75). Without it, ZOHOCORP 576.00 turned into a tie between `0007` (prints ...2838, the labelled receipt) and its Zoho Books copy `0006` (picked 2838).
- **Predicted live change:** on deploy, August's LOVABLE 25.00 row carries `cards_differ` (`n_cards_differ` 1, July 0). At Criss's next August re-match that pair stays but asks for review, so the tool's own confirmation of it goes back to pending. Nothing else moves (attribution class tables identical on a 2026-09-17 DB copy).

**Owner:** "the expense to statement matching is not separated by cards."

**What the code does.** `match_month` scopes a receipt to a card only through `receipt_card_scope` (`matching/deterministic.py`): the card digits have to be printed in the receipt's own `payment_mode` AND appear among the statement's charges. Everything else is unscoped and competes for charges on every card. The card the tool itself resolved for the receipt (Settings card hint, a hand pick on the row, a learned card) never reaches the matcher; the one exception is item 135's pick that contradicts a printed card (`hand_picked_card_mode`), and a pick on a receipt that prints no card was left matching as before on purpose. `card_scoping` is on (default `True`, `settings.matching` is empty live), and the LLM judgment layer only sees the pairs `pair_in_scope` lets through, so it inherits the same gap.

**Live, read-only 2026-09-17** (four cards with charges in each month):

- July: 19 of 52 receipts are card-scoped; 33 carry no card and compete across 3876 (48 charges), 2838 (36), 3645 (27) and 0340 (1). 19 of those 33 are matched.
- August: 10 of 25 are card-scoped; 11 have a card the tool knows but that does not scope (9 picked by hand, 2 from a Settings hint) and 4 have none.
- One confirmed pair crosses cards: the LOVABLE 25.00 charge of 2026-08-05 on card 3645 is confirmed with `0027__Invoice-HMVWDWIL-0028.pdf`, whose card is hand-picked as Credit Card - 2838. Either the pair or the pick is wrong, and neither the matcher nor the screen says so.

**Proposed change.** The receipt's resolved card (override, hint, learned, printed) scopes its candidates the same way a printed one does, and the charge side keys on `coverage_key`. Open design call before building: a hand pick is Criss's word and can scope hard; a hint or a learned card can be wrong, so a card disagreement from those should demote the pair to review with a "the cards differ" reason rather than drop it (the reconciliation guarantee: a real match is never silently excluded). A confirmed pair whose cards disagree, like the LOVABLE one, needs its own flag on the month page.

### 138. The PDFs are not organized by the cards that were reconciled (owner, 2026-09-17; licence: defect) (SHIPPED 2026-09-17, PR #1028, Shipped row 62; cards inside cost centers Shipped row 70; months-page half: backend SHIPPED 2026-09-17, PR #1049, Shipped row 72, SPA prompt written) (SPA APPLIED + VERIFIED 2026-09-17 night: owner published, cold-driven EN and PT, 0 writes; see PROMPT-STATUS)

**Shipped (both PDFs).** One grouping, `_pdf_common.card_sections`, feeds both documents: charges on `rows[].coverage_key`, a receipt a charge holds follows that charge's card, an unheld receipt goes to the card item 137 resolved for it (`service.report_receipt_cards`), and a last "No card" section is never dropped. Each card section opens with one shared line (`card_statement_line`: statement or "not recorded", period, charges, matched, unreconciled, booked without a receipt), then its exceptions (reconciliation report), its charges or expenses, then that card's receipt pages (`caption_mark` + `stitch(..., caption_pages)`). A held pair whose cards disagree is named inside its charge's section. Design calls, so they can be revisited:

- **A month with fewer than two cards keeps the flat document** (both PDFs), even when some receipts carry no card: a heading restating the only card is structure the content does not earn, the old one-card tests encoded that on purpose, and the flat document's "What needs attention" already lists the receipts nobody placed.
- **Cost centers and trips**: a trip still sections per person. Cost centers were the owner call this item left open; ruled 2026-09-17, shipped below.
- **Found on the way:** `build_reconciliation_report` called `build_view` without `field_overrides`, so a reviewer's card pick never reached the document and item 137's "cards differ" could not appear in it. Fixed in `report_view`.
- **Real August 2026, rendered locally from a read-only DB copy:** reconciliation report 73 pages (was 69), sections 3645, 3876, 2838, 1176, 9693, No card, all 25 receipts placed, LOVABLE 25.00 flagged; month report 68 pages, 3876 has no listed expense so no section, header unchanged (20 expenses, EUR 668.00, USD 2,033.86). Card 9693 (item 108, statement never loaded) now has its own section with its two OpenAI receipts.

**Owner ruling 2026-09-17: cards inside cost centers.** "When a month has both cost centers and cards, the PDFs are organized cards inside cost centers: one section per cost center (spending per project), with each section's expenses grouped by the card that paid." **Shipped (Shipped row 70), month report:** a month whose cost centers resolve keeps "Listing by cost center", one section per cost center in the same order, and when its listed receipts reach two card sections or more (the card listing's own rule) each center's expenses run in `card_sections` order and key, "No card" last. A center spanning two card groups or more gets a sub-heading per card, that card's table and its sums per currency, then the center's sums; a center on one card gets no card heading. `card_statement_line` stays out of the sub-groups (its figures are the whole statement's, not the center's share); a held pair whose cards differ is still named under its card ("on this card" under a heading, the card's name otherwise). Design calls: receipt pages stay at the end in listing order, as a cost-center month had them (moving them behind each center is the existing `receipts_by_section` switch); a one-card month with cost centers stays exactly as before. **Reconciliation report: unchanged.** It never sectioned by cost center (a charge has no cost center of its own; the center is resolved on the receipt), so it keeps its card sections whatever the settings say. No live document changes today: `cost_centers: {}`. Real data, rendered locally from a read-only DB copy with a synthetic assignment in memory (every third receipt Lidar / Marketing / none, no receipt files): July 56 expenses as Lidar 20 (3876 6, 2838 7, 3645 1, No card 6), Marketing 18, Unassigned 18; August 21 as 9 / 7 / 5; per-card sums add to each center's, center counts to the header, captions 1..N once; reconciliation report sections per card as before (63 and 36 pages without receipt files).

**Found on the way:** both PDFs cut table columns off the page. Built as item 143.

**Owner:** "the output (PDF) is also not organized in the different cards that were reconciled."

**What each document does today:**

- **Month report** (`GET /runs/{id}/expense-report.pdf`, the Expenses page download, `build_expense_report`): a company month sections its listing only by cost center (item 47), and only when a cost center resolves; the live registry is empty (`cost_centers: {}`), so the listing is one flat table with the card as a "Paid through" column, one total per currency, and the receipts behind it in listing order. No per-card section, no per-card total.
- **Reconciliation report** (`GET /runs/{id}/reconciliation-report.pdf`, the month page download): the coverage table and the full charge listing ARE per card (Shipped row 28). The header's matched count and unreconciled total, the exceptions block (unmatched charges, unmatched receipts, duplicates) and the receipt pages are not. August, read 2026-09-17 (69 pages): page 1 "114 charges · 9 matched (7.9%) · unreconciled USD 10,898.66" over four cards, exceptions on pages 2-4 across all cards, per-card listings on pages 5-7, receipts from page 8 in one run.

**Proposed change.** One per-card structure in both documents: per card, its charges with their receipts, its exceptions, its total and its unreconciled figure, then that card's receipt pages; receipts with no card, and charges no coverage entry claims, in a last section that is never dropped. Group on `coverage_key` for charges and on the item 137 resolved card for receipts, so the document and the matcher agree on which card a receipt belongs to. The cost-center partition (item 47) nests inside a card section or stays a separate roll-up; that is an owner call once cost centers exist.

**2026-09-17, Criss (via owner): the months page should show it plainly and be organized separately by the card whose statement each expense was reconciled against.** Same principle as this item and 137 (the card is the unit of reconciliation), on the screen. Recommended shape, not built: tabs per card that has charges or receipts this month plus All and No card, each with a header (statement loaded or not, matched count, still-open amount, receipts on that card without a charge); cards with nothing collapse to one line. Not the stacked coverage panels item 71 removed from the top on 2026-09-15. Order: 137 first (a per-card view over a matcher that does not scope by card would file receipts under the wrong card; one confirmed August pair already crosses cards), then the page and this item's PDFs on the same grouping key. It will make item 108 (9693 and 1176 statements never loaded) visible every month. Open: which surface Criss means (inside a month, the months list with one status line per card, or both), and build now at the hourly rate or quote as a piece under the licence (new presentation, not a defect).

**Owner ruling 2026-09-17: build now.** Told it is new screen layout under the licence hold, he chose to build "a tab per card showing whether its statement is loaded, how many charges matched and what's still open, plus 'All' and 'No card'". The surface was decided for him (he did not want to be involved): tabs inside the month on both pages, Matching `/runs/{id}` and Expenses `/expenses/{id}`, one card key and one tab bar component, All selected by default, the choice remembered per month. The months list keeps its one line per month.

**Shipped (months-page backend, SPA prompt written).** Both month GETs carry `card_sections[]` and a `card_section` key on every row, receipt and expense the page lists (`rows[]`, `unmatched_receipts[]`, `copies_set_aside[]`, `assignable_receipts[]`, `expenses[]`). The grouping is `_pdf_common.card_sections` over the view and card chain the PDFs use, and every figure is `card_statement_figures`, which `card_statement_line` now reads too, so a tab and its PDF section cannot disagree: statement `loaded` / `not_recorded` / `not_loaded`, statements, period, charges, matched, still open per currency, booked without a receipt, receipts, receipts without a charge; the Expenses payload adds expenses and totals per tab. Design calls, so they can be revisited:

- **Fewer than two cards, or a trip, sends `[]`**: the PDFs' flat rule (a tab bar restating the only card organizes nothing), and a trip sections per traveler.
- **No card is key `""`**, as on `coverage[]`: the registry drops a blank card key, so it can never name a card. The prompt tells the SPA to compare keys with `===`.
- **A card with nothing this month is no tab**; the tab row ends with item 71's "+ N cards with nothing this month", counted from `coverage[]`.
- **Only the two page GETs build the tabs**; the edit routes that reply with the expense payload's summary do not pay for the extra view build.
- **Each page files by its own PDF's pool** (Matching by the snapshot's receipts, Expenses by the month report's). Measured on a 2026-09-17 DB copy: July and August file every charge and receipt identically on both pages and in both PDFs; only September (no statement) differs, by the copy card inheritance the Expenses page already shows.

Live August over the live payloads: 3645 loaded, 40 charges, 5 matched, USD 2,393.15 open, 8 receipts, 5 expenses; 3876 loaded, 37, 0, USD 1,031.15, no receipt; 2838 loaded, 34, 4, USD 7,438.36, 11 receipts (5 without a charge), 10 expenses; 1176 not recorded, 3 charges, USD 36.00, 2 receipts (1); 9693 not loaded, 2 receipts (2); No card, 2 receipts (2). The tab counts add up to the page's whole counts (101 charges without a receipt, 10 receipts without a charge, 20 expenses, EUR 668.00 / USD 2,033.86). SPA half: `docs/lovable-card-tabs-prompt.md` (Not applied): the tab bar, one header line per tab, both pages filtered by `card_section`, All unchanged, EN + PT-BR, and a cold-drive check list for August.

### 139. "Paid with a private card" is a separate button instead of a choice in the card picker (notes #65, #66, owner, 2026-09-17; SPA only) (SPA APPLIED + VERIFIED 2026-09-17 night: owner published, cold-driven EN and PT, 0 writes; see PROMPT-STATUS)

**Matthias, July Expenses view (`/expenses/50622baec444`), row `0000__rendered-body.pdf` (Hostinger), 15:13 and 15:14 UTC.** On the picker "Leave blank (resolve from card) / Pick the card that paid": "no 'paid with a private card' function". A minute later, on the "Paid with a private card" button of the same row: "I need this 'paid with private card' button as one of the options in the 'pick the card that paid' dropdown. preserves space".

The function exists: the live row carries `can_mark_private: true` and the button renders (PR #987, SPA applied #990). The first note read it as missing because it sits outside the picker. **Proposed change, SPA only:** a "Paid with a private card" option at the end of the card picker, offered only when `can_mark_private` is true, doing what the button does today; the button goes. The backend refusals stay as they are (400 `company_card` on a company-card row, 400 `private_card` on a company-card pick for a private row).

**Prompt written 2026-09-17:** `docs/lovable-private-card-in-picker-prompt.md`, not applied. Live on July the card column stacks the entity picker, the card picker (nine cards, "Credit Card Chase Visa - 3645" to "Credit Card - 2838") and the button under them; the 32 eligible rows are all `card_source: none`, the Hostinger row of 2026-07-28 (`0002`) has the picker but `can_mark_private: false`, and every hint row is ineligible, so the option never hides behind "Change card".

**Check eligibility before believing a negative on this item.** A second, independent check of the same evening opened the picker on whatever row came first, read nine cards with no tenth entry, and looked exactly like "not applied". The row was ineligible, where nine is the correct rendering after the change as well as before, so the probe could not tell the two states apart and its negative meant nothing. Opening it on a row the API reports as `can_mark_private: true` (July `0003` Konsultancy Finance, `0004` Redis Inc.) shows ten options ending "Paid with a private card". Grepping the shipped bundle does not settle it either: `expx.privateCard.mark` is in the build whether or not the control moved, and the i18n keys resolve at runtime, so no grep locates the control. Only an eligible row answers it. Same class as the instrument-validity clause in `rule_behaviors.md`.

### 140. A possible duplicate shows a label, not the copies side by side (note #67, owner, 2026-09-17; SPA only; owner ruled build) (PROMPT WRITTEN 2026-09-17, not applied) (SPA APPLIED + VERIFIED 2026-09-17 night: owner published, cold-driven EN and PT, 0 writes; see PROMPT-STATUS)

**Matthias, July Expenses view, row `0030__...Aposto_Karlsruhe__ZE_8100599.jpg`, 15:15 UTC:** "if this is a potential duplicate, the tool needs to show all the available data to each of the duplicates next to each other for manual comparison. Just labeling it is not going to cut it because then user has to search for the other duplicate and this slows comparison process."

Live row: `duplicate {group_id 3b0029eea1b11643, kind receipt, n_copies 2, copy 2, of 0029__...ZE_7150901.jpg, is_extra true, resolution confirmed}`. The payload already names the other copy (`duplicate.of`), so a side-by-side panel (date, vendor, total, currency, card, reference, receipt image for each copy, then the ruling buttons) needs no backend field. **Owner ruling 2026-09-17:** "duplicates should be shown next to each other for easier comparison". Build it; that settles the licence question.

**Prompt written 2026-09-17:** `docs/lovable-duplicates-side-by-side-prompt.md`, not applied. A "Compare copies" button on every marked row of the Expenses page, on every card of the Matching page's duplicates panel and on the marked rows of "Receipts without a charge" opens one dialog with every copy of the group in columns, the differing values highlighted, both receipt images inline, and the ruling buttons the opener already has. Live read-only on July and August: all 10 members of each month's 5 groups are `expenses[]` rows with every field the dialog shows (the set-aside copy included), and the image route served both copies 200 (the Aposto pair as JPEGs). The batch rows do not say which copy holds a charge; the run payload does (`rows[].chosen_document_id` on a reconciled row, e.g. Aposto `0029` on the UZR*Aposto Karlsruhe 91.70 USD charge), and both pages already load it, so the dialog reads it from there. Nothing needs a backend field.

### 141. The month page repeats download buttons (note #68, owner, 2026-09-17; SPA only) (SPA APPLIED + VERIFIED 2026-09-17 night: owner published, cold-driven EN and PT, 0 writes; see PROMPT-STATUS)

**Matthias, July Matching view (`/runs/50622baec444`), section "Receipts without a charge 11", anchor "Downloads Report Reconciled CSV Statement", 15:19 UTC:** "we do not need more than one button to download the different output files, make sure there is only one button for each output file download." **Proposed change, SPA only:** one download control per output file on the page (report PDF, reconciled CSV, statement), in one place; before writing the prompt, list where each download renders today in `brisken-expense-review` so the prompt removes the repeats and keeps one of each.

**Prompt written 2026-09-17:** `docs/lovable-one-download-each-prompt.md`, not applied. Live July Matching has five buttons for four files in three places: the header's "Download" beside "Statement July2026.xlsx" (`statement-categorized.xlsx?file=`), the primary "Download reconciliation (PDF)" in the action row, and the Downloads row's "Report" (`report.xlsx`, not the PDF), "Reconciled CSV" and "Statement" (the same workbook again); August has no Statement button in the row (`writeback_available: false`) and offers its workbook only inside the collapsed "2 statements" table.

### 142. A booked charge's hint says "your statement workbook" without naming it or the rule (note #69, owner, 2026-09-17; SPA copy) (SPA APPLIED + VERIFIED 2026-09-17 night: owner published, cold-driven EN and PT, 0 writes; see PROMPT-STATUS)

**Matthias, July Matching view, section "Charges without a receipt 72", on the row hint "This charge is marked yellow in your statement workbook, so it is already booked. Nothing…", 15:19 UTC:** "where do you get this information from?"

Answer: from the fill colour of that charge's row in the Chase workbook Criss uploads for the month (`July2026.xlsx`): she colours a row yellow once it is booked, and `ingest/statement_xlsx.py` reads the fill when the statement loads (yellow -> `entry_status: posted`). Item 86 fixed the same question on the fold caption ("48 rows marked yellow in July2026.xlsx, already booked", with the yellow / grey tooltip); the per-row hint still says "your statement workbook". **Proposed change, SPA copy:** the row hint names the file from `statements[].file` (fallback "the statement workbook") and says the colour is read when the statement is loaded, same wording as item 86's tooltip; PT wording for Criss.

**Prompt written 2026-09-17:** `docs/lovable-booked-hint-names-workbook-prompt.md`, not applied. Live the phrase sits in two places, the "Already booked" badge tooltip on all 84 booked July rows and the line under the vendor on the 47 in "Charges without a receipt" ("Marked yellow in your statement workbook, so already booked."), and item 86's fold on August names a PDF that carries no colours ("August2026.xlsx, 20260804-statements-1176-.pdf"), so the prompt names only workbooks (`writeback` true), matched on the row's `account_id`.

**Where the hint lives, for whoever checks it next.** It renders inside a tooltip on a collapsed section, so three drives of the live Matching page never put it on screen; the copy is readable in the shipped bundle instead, as `row.status.posted.tipFile` and `wb.reason.charge.already_booked.file` beside their no-file fallbacks.

### 143. Both PDFs cut table columns off the page (found building item 138, 2026-09-17; licence: defect) (SHIPPED 2026-09-17, PR #1052, Shipped row 74)

**Defect.** Both documents lay out on A4 portrait with 14 mm margins, and reportlab's frame keeps 6 pt of padding inside them, so a table has 503.9 pt, not the 516 pt between the margins. reportlab centers a table that is too wide, so it spills past both sides of the frame by half the excess; past 45.7 pt a side (margin plus padding) it runs off the paper. The text layer still held the clipped cells, which is why no text-extraction test saw it; a raster of the August pages did.

| Table | Before | After |
|---|---|---|
| Month report listing (flat, per card, per cost center, per card inside a cost center, per trip person) | 732 pt: `#` and Date cut on the left, Ccy and Receipt on the right, on every month report since item 24 (2026-08-23) | 503 pt |
| Reconciliation charge table (flat and per card) | 672 pt: `#`, part of Date and part of Account cut | 503 pt |
| Reconciliation coverage by card | 572 pt: 34 pt into each margin, still on the paper | 502 pt |
| Reimbursements owed 466, charges with no receipt 430, receipts with no charge 455, open duplicates 460, copies set aside 470 | fit | unchanged |

**Shipped.** Portrait kept, widths rebalanced, no column dropped, no font change. Every column reads at 8 pt once the text columns wrap, and landscape listing pages would have made a mixed-orientation document, since item 138 puts each card's receipt pages (portrait) right behind its section. Counts, dates, amounts up to 123,456.78 and currency codes fit on one line in DejaVu Sans, the container's font and the widest `register_fonts` picks; vendor, account, entity, paid through, status and receipt wrap between words, so most listing rows run two lines. `_pdf_common.PAGE_MARGIN_MM` and `TABLE_WIDTH_MAX` carry the page, and both builders read their margins from it. A single token wider than its column still breaks at the column edge (nothing lost, nothing past the edge): on July and August that is three charge-table cells, once each, `AMZ*Amazon.D*X37L83BI5` (Charge), `POPULAR-MARAIAL` (Receipt) and `Subscriptions-Others` (Account).

**Test.** `tests/test_pdf_tables_fit_the_page.py` (8) records every Table the document template places while the real builder runs, and asserts each is within its frame, no cell's text is wider than its column, and no count, date, amount or currency breaks a word. Fixtures: a 105-row flat listing with an unreadable amount, a per-card month with receipts, reimbursements and copies, cost centers with cards inside, a trip, the reconciliation report with three cards and with one, and both downloads of a two-card month through the routes. `regress_check` with the old widths: month report 5 red, reconciliation report 3 red; a listing Date column narrowed to 40 pt goes red on the word-break check alone.

**Real data**, read-only DB copy of 2026-09-17 rendered locally in DejaVu Sans with the receipt files, July and August, both documents plus a synthetic cost-center assignment: every table 502 or 503 pt. Rasters of the August listing, the July listing and cost-center listing, and both months' coverage and charge pages show every column inside both edges.
### 144. Residuals: grid Books-as, decision-reply summary, bank-transfer private suggestion (licence: defect, covered) (SHIPPED 2026-09-17, pending PR) (SPA copy APPLIED and DRIVEN 2026-09-18, EN and PT; CLOSED)

**2026-09-18: the copy is live and driven.** July's RODRIGO TANURE TRICARICO
CONSULTORIA row of 2026-07-31 (BRL 27,203.34) reads the prompt's own sentence in
both languages instead of the backend prose, with no generic "Assign this
expense's paying card" anywhere on the page, and the row's state beside it is
unchanged and correct: "Paid by bank transfer", the paid-through picker, no
person question. Check 3 holds by live API read: July `summary.n_needs_person` is
still 13.

Found by the re-crawl rule, not by being told: the owner had already published it,
and the prompt was minutes from being handed over for the second time in two
sessions. That rule is the one thing standing between this loop and repeating the
2026-09-18 five-prompt hand-over, and it works only because PROMPT-STATUS now
phrases it as a rule about actions rather than a fact about audits.

Three leftovers of items 95, 99 and 111: in each the software states something
it knows to be otherwise. Found by reading the code against the shipped items,
checked live read-only against July (`50622baec444`) and August
(`074a7b8905d7`).

**R1. The Expenses grid's `books_as` skipped the chart-of-accounts gate.** Item
95 made the export gate judge the ACCOUNT and keep the line's category; the
grid's own depiction (`build_expense_view`, `service.py`) still called
`expense_posting_parts` on ungated receipts with no chart, while the export
called it on gated ones with the run's chart. A line whose account the
company's chart rejects therefore read as that account on screen and as its
category (many-entity gate, no chart) or `(account unmapped - assign)`
(a batch naming one company) in the CSV, for the same purchase. **Built:** one
function, `zoho_expense_export.gated_for_posting`, called by
`build_expense_row_groups` and by the grid, plus the same chart on the grid's
fan-out. **Measured live before the change:** no row differs today. Every
account cell of both months' `expenses.csv` equals the grid's `books_as`
(July 56 parts / 56 rows, August 20 / 20), because live accounts are the
tool's own category labels, which both paths render alike. The defect was
reachable, not live.

**R2. A write's reply carried a summary the next refetch contradicted.** The
SPA renders the `summary` a route replies with until it refetches the run.
Eight routes built theirs as `build_view(run, decisions, overrides)`: no
duplicate resolutions, no cross-month settlements, and no expense FIELD
overrides, which is where the month's header edits live. So a receipt
confirmed private read as still needing a charge (`n_receipts_need_charge`,
and `month_complete` with it) in every reply. **Built:** `app._run_view`, the
dispatch `GET /api/runs/{id}` uses, and every one of those routes
(`decisions`, `decisions/bulk`, `decisions/confirm-ready`, `disposition`,
`duplicates/resolve`, `manual-match`, the per-charge receipt upload, the
settled-outside write) now replies with it. The expense-edit routes and the
month move keep the Expenses payload's summary, which is what their own page's
GET serves. **Measured:** route-level, a decision reply's summary now equals
the `GET /api/runs/{id}` summary taken immediately after, count for count.

**R3. A wire is not a card.** The private suggestion fires on any payment
method that resolves to no registered card, so July's restored Tricarico
invoice (BRL 27,203.34, prints "Payment Method: Wire Transfer", recorded
settled outside by bank transfer on 2026-09-17) asked Criss to name a private
card for a bank payment, while the tool's own ruling of 2026-09-15 calls a
settled-outside receipt real company spend. **Built:** a bank-transfer tender
(`service.bank_transfer_tender`, the settled-outside chip's own rule minus the
word TEF, which is a card payment on a Brazilian cupom fiscal: July's Fenix
receipt prints TEF and settles a card charge) and a receipt with a
settled-outside record raise no suggestion. `can_mark_private` is untouched.
**Measured live (read-only prediction):** exactly one row moves, July's
Tricarico invoice; `summary.n_suggested_private` 8 to 7 (row flags 10 to 9,
two of them copies that sit in no box), August unchanged at 1.

**Open question for the owner (R3, NOT decided here).** That invoice still
sits in "No company or person": `needs_entity` + `needs_person`, and the
review line now reads `needs_entity`. The file names BRISKEN Consulting LLC
and it was paid by bank, so a COMPANY is meaningful; a card HOLDER is not, and
today the box's two sanctioned exits are both wrong for it (pick a company
card, or confirm it private). A company override answers half; nothing answers
`needs_person`, because person resolution is card-only by the item-40 ruling
and neither the code nor `api-contract.md` says what a bank-paid company
invoice should be asked. Box membership was left exactly as it was.

Tests: `tests/test_books_as_chart_gate_r1.py` (3),
`tests/test_decision_reply_summary_r2.py` (2),
`tests/test_private_suggestion_not_a_card_r3.py` (3), all route-level.
Every wire watched go red with the fix disabled: the grid's gate call (1 of
3), the grid's chart (1 of 3), the decision route's `_run_view` (1 of 2, on
`n_receipts_need_charge` 1 vs 0), the settled-outside route's (1 of 2), the
tender rule (2 of 3), the grid's settled-outside wire (1 of 3). The two app.py
wires were hand-regressed (the helper's mutated write left `regress_check`
with no pytest summary line). Suite 2274 passed / 2 skipped. Docs:
`docs/api-contract.md` (books_as gate, the reply-summary paragraph, "A wire is
not a card"). Nothing deployed; no SPA half needed (the payload fields keep
their names and meanings).

**Bank-transfer exit (owner ruling 2026-09-17; this closes the open question above).** Asked what a bank-paid company invoice should be asked for, the owner ruled: add a bank-transfer exit. A row the reviewer has settled OFF the card system now behaves as what it is, a row no card paid.

**Built.** One predicate, `service.settled_off_card` (the row's settled-outside record carries a `how`), called ONCE per row by `resolve_batch_row_cards`, which stamps the answer on the row's resolution as `settled_off_card`. Every surface that acts on it reads that stamp rather than deciding again, which is what keeps the four answers below consistent with each other. The trigger is the reviewer's disposition, never the printed tender: a printed "Wire Transfer" with no disposition is the document's claim about itself and still moves only `suggested_private`.

* `expense_boxes` drops `needs_person`, and `needs_company_or_person` follows from `needs_entity` alone. Person resolution is card-only by the item-40 ruling, so the box was holding the row on an ask nobody could answer: the Tricarico invoice could not leave it by any sanctioned action.
* `card_review.n_needs_person` takes the same exemption, so the two person counts that sit beside each other on one payload agree about every row. The first draft of this change moved only the boxes, and the strip then read 1 where the summary read 0 on the settled row: one payload contradicting itself about one row, which is the defect class item 103 closed the same evening. The strip's own comment says the fix it points at is "a person on the card (Settings > Cards)", and on a row no card paid that fix does not exist, which is the same reasoning that took the box away. `card_review.n_needs_entity` deliberately does NOT take it: the company question stands.
* `can_mark_private` is false, so the private-card button is not offered. `POST .../private` and the field PUT already refuse what that flag is false on, so the button and the routes still agree.
* The review reason is its own, `needs_entity_settled_outside`: "This expense was settled outside the card system, so no card will name the company it belongs to. Set the legal entity on the row; the export shows a placeholder until then." The generic sentence opened by telling Criss to assign the paying card, the one instruction this row cannot follow. The `needs_person` sentence goes quiet on the same rows the box drops, so the screen and the box cannot disagree.

**The limitation, stated plainly: the entity is NOT auto-filled, and `needs_entity` stays.** The row carries no bill-to field. On the live payload `customer`, `legal_entity_id` and `entity_source` are all empty, and the company name exists only inside the FILE NAME (`0017__2026-07-30__BRISKEN_Consulting_LLC__Rodrigo_Tanure_Tricarico_Con__`). Reading a company out of a file name would be inventing a data value (B4), so the tool still does not know which company this is. It only stops naming a card as the way to tell it: Criss sets the entity on the row, one action, and the row is done.

**Measured, and the honest gap in it.** Only rows carrying a `settled_outside` record move; every other row's payload is byte-for-byte what it was. No LOCAL fixture records reviewer dispositions at all, so the before/after count could not be taken here: the eight bundles under `context/expense-reconciliation/expense-reports/csv/by-month` (the six labelled months plus `July-2026_live_50622baec444`, 50 receipt rows, and `August-2026_live_074a7b8905d7`, 31) hold matcher INPUT only, their `run.json` carries just `matching` / `receipts` / `statement`, and a search of the whole gitignored client context finds the key `settled_outside` in no file. The dispositions live in the app's SQLite on the Fly volume, which this session did not query (read-only session by instruction, no live API calls). From the live read that opened this item, July's Tricarico invoice is the one known row: it leaves `needs_person` and `needs_company_or_person` (`summary.n_needs_person` one lower), keeps `needs_entity`, loses its private-card button, and its review line changes sentence. Whether either month holds a second settled-outside row is unverified from here; `summary.n_settled_outside` on a live GET is the number to read before deploying.

Tests: `tests/test_bank_transfer_exit_item_144.py` (11; four route-level through `GET /api/expense-batches/{id}`, one of them `test_the_two_person_counts_agree_on_every_row` pinning EQUALITY of `summary.n_needs_person` and `card_review.n_needs_person` before, during and after a disposition, because equality is the property that broke; one the negative contract that an ordinary card-less row is untouched), plus `tests/test_private_suggestion_not_a_card_r3.py` rewritten to the new ruling, its settled-outside case having asserted the old contract and gone red first. `regress_check` run three times, each green to red to green: the predicate, the grid's box wiring, and the stamp itself (`"settled_off_card": settled_off` to `False`: 4 red, 3 route-level), plus the counter's own condition reverted to its old form, which turns the equality test red and nothing else (1 of 19). Suite 2421 passed / 2 skipped; CI ruff clean. Docs: `docs/api-contract.md`, where the earlier "A wire is not a card" section was corrected IN PLACE (section order untouched) to be true of the tender half only and to point forward, rather than left standing against the appended section; the `can_mark_private` field row and the counter paragraph were corrected with it. Nothing deployed; no SPA half needed (every field keeps its name and meaning, and an SPA that does not know the new `reason_code` falls back to the English sentence, per item 130).

### 145. Both PDFs title themselves with an em-dash, which the house deliverable standard bans outright (2026-09-17; licence: defect) (SHIPPED 2026-09-17, PR #1058, Shipped row 79)

**Defect.** `.claude/rules/rule_deliverables.md` bans every dash form from a client-facing document: the em-dash character, `&mdash;`, and ` -- ` standing in for one. Both documents broke it in the first string a reader sees. Live on Fly v171, page 1 of August's reconciliation joined "Reconciliation" to its month with an em-dash, and the month and trip reports titled themselves the same way. The three before-and-after strings are in the table below.

| Where | Before | After |
|---|---|---|
| `service.build_expense_report` title | `Expense report — August 2026` | `Expense report: August 2026` |
| the same, trip branch | `Trip report — TEST - Rome` | `Trip report: TEST - Rome` |
| `service.build_reconciliation_report` title | `Reconciliation — August 2026` | `Reconciliation: August 2026` |

The colon is what the rest of both documents already uses for a label ("Statement: August2026.xlsx", "Owed to Dirk: EUR 18.00", "Lidar: 3 expenses"), so the titles now read like the pages under them. The middle-dot separators are untouched.

**Scope.** Every string in `src/expense_recon` that reaches a rendered page was swept by parsing each module and reading only its string LITERALS, so a docstring or comment could not be mistaken for printed text. Three hits, all three titles, all three in `service.py`. Neither builder nor `_pdf_common` carries a banned form in printed text, and the captions, headings, statement lines, sums lines and footers are clean. Out of scope and left alone: the em-dashes in the ingest issues list and the statement-source advisory (app screens, not the PDFs), in the XLSX sidecar's status cells and the Zoho journal CSV, and in the categorizer's reasoning field, which no PDF prints.

**Why no test saw it.** The titles are composed in `service.py`; every existing PDF test passes its own `title=` to the builder, so none of them ever rendered the product's real title.

**Test.** `tests/test_pdfs_have_no_em_dashes.py` (3) drives the ROUTES, where the title is composed: a two-card August with a statement, four receipts and a reviewer's card pick for both documents, and a trip batch for the third title. Each reads every page's extracted text for all three banned forms, and pins the title it expects, because "nothing contains an em-dash" also passes on a document that renders nothing. `regress_check` run once per title, each red on its own test alone (1 failed, 2 passed), so all three wires are covered. The em-dash arm was regressed separately, by hand and byte-for-byte, because `regress_check` cannot carry the character through the Windows command line: putting the real em-dash back into each title turns its own test red and nothing else, which is the live defect reproduced. The character in `BANNED` is built with `chr(0x2014)` rather than typed, so a later strip-gate pass over this client path cannot quietly empty the check.

### 146. The card strip counts decided copies the boxes deliberately do not, so two person counts on one payload differ by the number of copies (found verifying item 144, 2026-09-17; licence: defect, covered) (SHIPPED 2026-09-18; Shipped row 87)

**It was three counters, not two.** A live read on 2026-09-18 before the build
found `n_suggested_private` disagreeing as well, 7 against 9, by the same two
copies, which the item as filed never mentioned. `n_private` is the fourth of the
same family and reads 0 against 0 today only because July holds no confirmed
private row; it would have disagreed the moment one appeared. All four take the
exemption together: leaving a twin unexcluded moves the disagreement to another
chip rather than closing the class. August agrees on all four either way, so July
is the only month that shows it.

**`n_needs_entity` DOES take this exemption**, though it deliberately does not
take item 144's. Two rulings about two different populations: item 144 says the
company question still stands on a row settled off the card system, because a
card was never going to answer it; item 94 says a decided copy is in no box at
all, `needs_entity` included, because nothing done to its company, person, cost
center or private flag changes the month. `expense_boxes` is the authority for
both and already reads them that way.

**The grouping still counts copies, deliberately.** `unresolved_hints`,
`resolved`, the per-entry `n_rows`, `n_resolved_rows`, `n_unresolved_rows` and
`n_no_hint` describe the card-assignment surface, where a decided copy is still a
row on screen carrying an assignable payment hint. None of them has a `summary`
twin, so none can disagree with anything, and dropping them would take a row
Criss is looking at off the strip.

**Live now** (`GET /api/expense-batches/50622baec444`, read after the item-144
deploy): `summary.n_needs_person` 13, `card_review.n_needs_person` 15;
`summary.n_needs_entity` 14, `card_review.n_needs_entity` 16. July holds 54
expenses, 16 of them with no person. Two of those 16 are decided copies (Aposto
Karlsruhe and Lovable Labs Incorporated), and item 94's ruling puts a decided
copy in NO box: `expense_boxes` returns `[]` for it, because a copy writes no
CSV row, no listing row and no reimbursement, so nothing done to its person
changes the month. `build_card_review` does not know that. It counts straight
off `resolution.values()`, which is every receipt, copies included. 16 minus the
2 copies is the 14 the boxes see; 16 minus the 1 settled-outside row is the 15
the strip prints.

The gap is the copy count and predates item 144. Before that deploy both counts
were 2 apart in the same direction (14 and 16); the item-144 exemption reached
both, each dropped by exactly 1, and the standing difference survived because it
was never about settled-outside rows.

**Why it is a defect.** It is the disagreement class item 103 closed for the
months list and the month page: one payload, two surfaces, two answers to the
same question, and no way for a reader to tell which is right. The strip sits
beside MISSING ENTITY on the same screen that renders the boxes, so Criss can
see 15 and 13 at once.

**The fix** is one condition, the same shape item 144 used: `build_card_review`
skips a row the grid treats as a decided copy, the way `expense_boxes` does. The
honest question underneath is whether the strip should count copies at all, and
item 94's ruling already answered it for every other counter.

**What made it visible.** Item 144's route test asserted the two counts equal on
a constructed fixture with no copies, so it passed and the equality claim reached
a PR body before the live read contradicted it. The transferable lesson is in the
checkpoint: a fixture that omits a population the live data has does not test
equality, it tests equality-in-the-absence-of-the-thing-that-breaks-it. Where a
claim is about two counters agreeing, the fixture has to contain every row class
the real month contains.

### Set aside by the 2026-09-17 audit (not items; one line each so nothing is lost)

- [learning] The 'validated' stamp on learned rows changes nothing; unreviewed rules apply as trusted: The owner accepted the one-off-becomes-rule trade-off in item 88; revisit after F11 makes recall work and the first real sign-off fires.
- [intake] A mailed receipt with an unreadable date is filed into the month it arrived in, silently: Changes a 2026-08-24 ruling (item 29 PR 1, item 44); one live instance, needs an owner yes before it is work.
- [architecture] Nothing stops a second machine from starting, and a second machine is a second empty ledger: Ten-line instance lock already prescribed in TARGET-ARCHITECTURE 4.2; no product change, fold into F20's ownership move.
- [money-reports] An auditor finds no business purpose, no place, no approval, no preparation stamp and no page numbers: Item 48 frames all eleven gaps completely and is owner-ruled; nothing new to add beyond quoting the rendering-only round.
- [operations] Three credentials the tool depends on have no recorded expiry, owner or rotation date: OWNERSHIP-HANDOFF steps 0 and 9 cover it; belongs in F20's secrets handover list.
- [matching] The health check only fires when the tool matched nothing at all: Item 57 stated the boundary as a design choice; becomes relevant only once a second workbook per month is live (F18).
- [matching] Refunds and credit notes have no matching path; fees have no closing path except 'already booked': ANNEALING A5, no live refund yet; the fee mark is folded into F16.
- [intake] The statement reader takes one shape of file, and the licence does not cover the next shape: Items 51 and 37 cover the in-app levers; the remainder is licence wording, not software.
- [learning / architecture] Sign-off and the Merchants editor can overwrite each other's settings save; two people editing Settings can silently undo each other: Item 10 residue and item 23 round 7; single-operator in practice today, a timestamp check when it first bites.
- [learning] Two spellings of the posting account and no check on the live months: Item 23's rename rounds own the account layer; the vocabulary merge fits its round 5.
- [criss-fit] Recurring subscriptions are read off the grey rows but never treated as a class: New function neighbouring item 48 and item 8; F16 and F17 deliver most of the value first.
- [criss-fit] What happens after the PDF is undefined: Criss still re-keys every charge into Zoho Books by hand: A one-question decision for Dirk and Criss (item 23 layer 4 is blocked on it); build nothing until answered.
- [operations / live-state] The AI cost shown per month is wrong: receipt reading priced at zero and the figure overwritten per operation: Real but small (llm/cost.py price table + running total); matters once the licence carries the OpenAI bill.
- [live-state] Three July test runs, an empty January month and two statement-less months clutter the live state: Owner-side deletes via the existing typed-confirm route; do it before F24's acceptance close.
- [money-reports] The Excel and CSV sidecars and the workbook writeback are built without Criss's expense edits: Short window on statement months; inherits item 72's persistence split (F08).
- [money-reports / architecture] Zoho still shapes the CSV headers and two dead controls, and three legacy layers are stitched on every read: Item 23 rounds 2-7 and item 10 frame it completely, including the rename hazard; one scripted retirement after the licence is signed.
- [learning] 'Person' on the cards is free text carrying company names; the merchant seed carries duplicates and shared aliases: Owner tidy in Settings and the Merchants editor; F09 removes the alias hazard on the tool side.
- [operations] Every note Criss leaves is stored with her network address and browser fingerprint, forever: Small privacy fix in app.py:1489-1505; no money or process impact.
- [architecture] A second client or the lead desk must get its own copy of the app, never a seat in this one: Record the rule in TARGET-ARCHITECTURE; no code change.
- [architecture] The seam that would resist a rewrite does not exist yet: the month store is four functions inside a 12,000-line file: Owner said stop shipping; an import-boundary test is the only cheap step and rides with F20's operating page.
- [review-spa] Working 100+ rows is mouse-only, one row at a time, with a full reload after every click: Speed, not correctness; new function after the licence.
- [architecture] One write lock for every month: a big drop into one month blocks receipts arriving for all months: Does not bite at Brisken's 30-60 receipts a month; the folder path already shows the better shape.
- [quality] The 'watch the test go red first' proofs leave no record, and the helper can report a false red: Two small edits to tools/regress_check.py; developer process, not client-facing.
- [review-spa / criss-fit] The in-app feedback widget is the project's best signal, and Criss never sees that a note was acted on: Important function, proven (54 notes); the 'answered' marker is a nice-to-have, and notes #52-#54 are now covered by F36, F42 and F31.
- [learning] Memory: built end to end, never exercised on real data: Important function whose protect line is F11 plus reading the counts after the first real sign-off (F24).
- [learning] Categorization tiers with honest trust marking, and the card registry resolves company and person from the paying card: Both proven on live data; protect by a real-receipt fixture in the categorization gate and keeping card digits current (owner data).
- [operations] The login gate and its guessing throttle, and the spend guards on receipt reading: Both hold live (401 unauthenticated, 98 probes refused, cache in use); protect via F39 (shared code, expiry) and F19 (cache in the backup).

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
| 87 | The card strip counts the rows the boxes count: `build_card_review` takes the month's decided copies (`copy_docs`, the same `decided_copies` set every listing surface reads) and its four box-twin counters skip them, so `card_review.n_needs_entity` / `n_needs_person` / `n_suggested_private` / `n_private` cannot answer differently from their `summary` twins. The GROUPING keeps every copy on purpose: `unresolved_hints`, `resolved` and the three row counts describe the card-assignment surface, where a decided copy is still a row on screen with an assignable hint, and none of them has a twin to disagree with | Item 146. One payload gave two answers to the same question on one screen, with nothing telling a reader which was right. Live July read `summary.n_needs_person` 13 beside the strip's 15, `n_needs_entity` 14 beside 16, and (not in the item as filed, found by a live read before the build) `n_suggested_private` 7 beside 9; the gap is exactly the two decided copies. `n_needs_entity` takes THIS exemption though it refuses item 144's, because the two rulings govern different populations and `expense_boxes` already reads them that way | 2026-09-18, PR #1085; `tests/test_card_review_copies_item_146.py` (3, route-level through the real app, fixture asserting its own premise: the copy reads `counts_in_total: false`, `boxes: []`, `n_copies_set_aside: 1`, so a refactor that stops producing a copy reddens the module instead of leaving the counts agreeing about nothing). Proven to bite by hand at the WIRING point, not the helper: reverting the call site alone failed 2 of 3 with all four counters named in the diff (3/3/2/0 against 2/2/1/0), restored byte-identical by sha256; suite 2479 passed / 2 skipped |
| 86 | A decision history with a name on every line: an append-only `decision_history` table records one line per change that ACTUALLY MOVED a value (row, old, new, who, when, trigger) at TWELVE write sites, not the four the item named; `who` is the label in the signed session token, never the server's environment, so Criss and the developer are finally told apart; `GET /api/runs/{id}/history` (newest first, `limit` / `before_id` / `row_key`, and `n_entries` follows the filter) and `POST .../history/{entry_id}/undo`, refused with `history_superseded` unless the row still holds exactly what that line left there, re-running the R4 claim check, appending its own line and stamping the original rather than erasing anything. A duplicate ruling is recorded but not undone here (reversing it has to re-match the month, item 56) | Item 104's history half, audit rank 11 and the highest-ranked unshipped item. Every verdict was an upsert, so "who confirmed this, and when" had no answer and a bulk action that moved forty rows left no trace; live July carried 108 of 112 rows with a null `decided_by`. The credential half is DECLINED by the owner (2026-09-18) | 2026-09-18, PR #1081, Fly v180; 36 tests route-level through the real app with two named operator codes, zero skips; nine wiring points proven red by hand; suite 2476 passed / 2 skipped; an adversarial review of the committed diff found a DATA-LOSS defect (an undo destroying a later account-only pick, because two different stored states compared equal) plus a dead 409 arm, an undo button that could never work, orphaned rows on month delete, and three tests that did not bite; all fixed, seven of them with a test watched go red then green |
| 85 | One currency for a month's receipts: `output/single_currency.py` converts each listing row and both documents state the month's figure. Three rungs, in order of what they know: a base-currency row is itself; a receipt settled by a reconciled USD charge converts at THAT CHARGE (implied rate = charge / receipt total, allocated with the remainder on a row that has an amount so a split receipt ties to its charge to the cent); anything else at the matcher's own `_reference_rate_for`, handed a `date` so the ECB rung actually fires. `expenses.csv` fills the EXISTING `Exchange Rate` column (header untouched: the importer is still an open question, item 23) and states the total under the rows, naming any unpriced row by vendor and date because the CSV prints no row numbers; the month report prints each figure and rate as a small second line under the amount (item 65's device, so no tenth column reopens item 143's page width) plus a per-card/cost-center figure on each sums line | Item 98, the audit's rank 5 of 40 and the highest-ranked unshipped item, built under the owner's 2026-09-17 reversal of quote-separately. July closed with three totals and nothing saying what the month cost in one currency while `Exchange Rate` was empty on all 57 rows. Narrowed in one place on purpose: no new CSV column, because the header is a live import contract and the column that exists already means this | 2026-09-18, PR #1076, Fly v179; live July `Total in USD: 58,187.69` (34 of 56 rows priced, 19 at their statement rate) and August `2,808.91`, both matching the pre-build prediction to the cent; 19 tests in `tests/test_single_currency_item_98.py`, route-level through both documents; nine wiring points proven red by hand; suite 2440 passed / 2 skipped; an adversarial diff review found a dead ECB rung plus four smaller defects, all fixed with a test each proven red |
| 84 | A company invoice paid by wire has an exit that is not a lie: a row the reviewer settled OFF the card system leaves `needs_person` on BOTH counts that ask it (`summary.n_needs_person` and `card_review.n_needs_person`, so the payload cannot contradict itself), is not offered the private-card button, and reads its own review reason `needs_entity_settled_outside` asking for the entity instead of for a paying card. One fact, `settled_off_card`, stamped on the row's resolution by the card pass and read by every surface; the printed tender alone still changes nothing but the suggestion | Item 144's open question, ruled by the owner 2026-09-17. July's Tricarico invoice (BRL 27,203.34, Wire Transfer, settled outside by bank transfer) sat in all three boxes with two exits that both stated something untrue, and person resolution is card-only, so no sanctioned action could move it. `needs_entity` deliberately STAYS and nothing is auto-filled: the row carries no bill-to field and the company name exists only in the file name | 2026-09-17, pending PR; `tests/test_bank_transfer_exit_item_144.py` (11, four route-level, one pinning the two counts EQUAL) plus `test_private_suggestion_not_a_card_r3.py` rewritten to the ruling; regress_check red on all four wires (the predicate 5 of 13, the box wiring 3 of 13, the stamp 4 of 14, the counter's own condition 1 of 19); suite 2421 passed / 2 skipped; not deployed |
| 81 | Every refusal carries a stable `code` beside its unchanged English sentence, and the values the sentence names ride as their own fields: 155 codes over 285 sites, the setup advisories and the two statement advisories carry a code and their numbers, and a source scan fails any NEW refusal that has none | Item 130. A refused save, decision or upload showed Criss the backend's English verbatim on a screen she reads in Portuguese; the code is what the front end translates, with the English sentence as the fallback for a code it does not know. Not built: the SPA half (prompt written, not pasted), the English PDFs and CSV (the auditor's, by ruling), and Criss's own read of the Portuguese wording | 2026-09-17, pending PR; `tests/test_error_codes_item_130.py` (20: 9 source-scan, 11 route-level), regress_check red on all four wires (the 401 code, an advisory code, the service-dict `error_code` plumbing, a `RunInputError` code); suite 2286 passed / 2 skipped; SPA half `docs/lovable-error-codes-prompt.md` |
| 80 | A correction comes back next month: a receipt with line items consults memory, and a rule a person taught (sign-off, the button, a Memory-page edit, a validated row) applies over the model's line read with `decision: "learned_over_line"` and the existing `check` / `vendor_guess` glance when they disagree; a rule saved with NO company (what every live sign-off writes) reaches a row whose card names one, and a row with no company takes the vendor's other rules only when they agree; a month with a statement teaches its CONFIRMED pairs' vendor spellings and FX at sign-off, generic descriptions refused (item 117's guard). A Zoho-seeded row nobody validated still stays below a line read, left for the owner | Item 115. The sign-off promise was that a fixed category arrives pre-filled, and none of it fired: 55 of July's 84 categorized lines came from a line read that never consulted memory, the lookup needed a company that 33 of 52 July and 13 of 31 August receipts do not carry, and only the classic statement page taught aliases and FX, so two reconciled months left the store at 0 aliases / 0 FX. Replay of both live months: 0 lines change today (every rule is seeded), 10 of August's 42 change once July is signed off, and July's sign-off teaches 4 bank spellings instead of 0 | pending PR, 2026-09-17; suite 2266 -> 2279 passed / 2 skipped |
| 79 | No client-facing PDF page carries a banned dash form: the three titles `service.py` composes read "Expense report: August 2026", "Trip report: TEST - Rome" and "Reconciliation: August 2026" instead of an em-dash, matching the colon the rest of both documents already uses for a label; middle-dot separators untouched | Item 145. `rule_deliverables.md` bans the em-dash, `&mdash;` and ` -- ` from a client-facing document, and both PDFs broke it in the first string a reader sees (live Fly v171, page 1 of August's reconciliation). The titles are composed in `service.py` while every existing PDF test passes its own `title=`, so nothing rendered the real one. A literal-only sweep of `src/expense_recon` found these three and nothing else printed | 2026-09-17, pending PR; route-level `tests/test_pdfs_have_no_em_dashes.py` (3), `regress_check` run once per title, each red on its own test alone (1 failed, 2 passed), plus a byte-level hand regression putting the real em-dash back into each title (`regress_check` cannot carry the character through the Windows command line), red on its own test alone each time; suite 2328 passed / 2 skipped on the tree merged with main; PR #1058, 2026-09-17; not deployed |
| 76 | Three residuals of items 95 / 99 / 111: the Expenses grid's "Books as" line runs the chart-of-accounts gate the CSV runs (one function, `gated_for_posting`, and the run's chart), every write route answers with the summary `GET /api/runs/{id}` serves (`_run_view`, so a receipt marked private stops reading as still needing a charge until the next refetch), and a bank-transfer tender or a receipt settled outside the card suggests no private card | Each is the software stating something it knows to be otherwise: the screen naming one account and the document another, counts that correct themselves a request later, and July's Tricarico wire (BRL 27,203.34) asking Criss to name a private card for a bank payment. Live: `n_suggested_private` 8 to 7 on July, no other row moves; grid and CSV already agreed account for account on both months (the Books-as defect was reachable, not live) | Item 143, pending PR, 2026-09-17 |
| 75 | One receipt is never bound to two charges, and the months list counts what the page counts: a pass-1 tie HOLDS its receipts against the greedy pass, a tied receipt holding a clean exact candidate on another charge no longer sustains the tie (round B's "spoken for", carried into tie detection), and `service.effective_charge_counts` is the one derivation behind `n_matched` / `n_review` / `n_unmatched_tx` / `n_refunds` on the months list, the stored summary, the `rematch_log` event and the re-match reply | Items 103 and 72. August at round B stored `0023` against ANTHROPIC 52.46 while the page showed it held by the undecided 50.52 pick; the labels call `0023` ambiguous and give neither charge a receipt, so the pick is the right outcome and the holding rule is what keeps it, with the spoken-for rule protecting `0021`'s bank-printed 51.38. Live today the remaining instance is July's two GOOGLE Workspace 71.64 charges, each tied over both invoices: list 8 in review / 72 unmatched against the page's 7 / 73. Not built: vendor dominance as a second spoken-for basis, twin-charge auto-pairing, the receipt-side counts | 2026-09-17, pending PR; route-level `tests/test_tied_receipt_item_103.py` (6), regress_check red on all four wires (tie dissolve 2 of 6, greedy skip 1 of 6, list derivation 1 of 6, the commit's effective `n_review` 1 of 6); suite 2274 (2272 passed / 2 skipped); measured on a 2026-09-17 DB copy: both live months and the six bundles byte-identical, 0 of 79 and 0 of 218 receipt rows moved, scorer 56.8 / 19.2 / 76.0 and guard 4/4 unchanged; predicted live change is July's list row reading 7 / 73 |
| 74 | Every PDF table fits the A4 frame (503.9 pt): month report listing 732 to 503 pt, reconciliation charge table 672 to 503 pt, coverage table 572 to 502 pt. Portrait kept, widths rebalanced so counts, dates, amounts and currencies fit one line in DejaVu Sans and text columns wrap; no column dropped; `_pdf_common.TABLE_WIDTH_MAX` | Item 143, found building item 138. reportlab centered the too-wide tables past both page edges, so every month report since item 24 printed without `#`, Date, Ccy and Receipt, and the reconciliation report without `#` and part of Date and Account; text extraction still read the clipped cells | PR #1052, 2026-09-17; `tests/test_pdf_tables_fit_the_page.py` (8), regress_check red on both builders; not deployed |
| 78 | A category can be set on a charge that has no receipt, and sign-off learns it: `PUT /api/runs/{id}/charges/{tx}/category` writes into the one `category_overrides` table under the charge's pseudo-receipt id, so the pick survives a re-match; it reads `EDITED` on `charge_category` + `posting_category`, drops the row's review state to `none` (leaving `n_charges_category_guessed` its meaning), and carries into the reconciled CSV, `report.xlsx`, the writeback, the reconciliation PDF and the journal's receiptless rows. Publish teaches it under the bank's normalized description, conflict-skip included; a model guess teaches nothing | Item 109. Criss's real month-end job is categorizing every charge, and most charges have no receipt: 174 across July and August on 2026-09-17, 146 carrying a category the model guessed from the bank's description with no control to change it. The guess went into the deliverable as it was and the same subscription was guessed again the next month. Owner reversed the quote-separately ruling on 2026-09-17 evening | 2026-09-17, pending PR; suite 2276 -> 2287; six regressions of the real source proven RED first; SPA half `docs/lovable-charge-category-prompt.md` (owner applies) |
| 77 | The month knows which receipts to chase and from whom: `receipt_chase[]` groups the charges needing a receipt by card holder (vendor, date, amount, currency, card, optional `receipt_portal` hint), membership read off item 99's `charge_needs_receipt` so the groups sum to `n_charges_need_receipt`; `receipt_requested_at` / `requested_to` records the ask and closes nothing, `no_receipt_expected` with a reason closes the charge and moves its money into `no_receipt_expected_by_ccy`; the request mail is composed EN + PT-BR from the intake address and nothing sends. SPA half: `docs/lovable-receipt-chasing-prompt.md` | Item 107, owner ruling 2026-09-17 (build the whole voids list, quote-separately items included). Criss builds this list by hand every month and chases Dirk and Nicolas herself; live August holds 61 charges across three holders and nothing in the tool said whose they were, who had been asked, or which will never have a receipt. Sends stay owner-gated: the send route refuses in both flag states and the module imports no transport | 2026-09-17, pending PR; route-level `tests/test_receipt_chasing_item_107.py` (11), regress_check red on all eight wires (predicate closes 3 of 11, row states 4 of 11, payload list 5 of 11, unreconciled exclusion 1 of 11, settings into `build_view` 2 of 11 and the settings PUT 3 of 11, both reproduced by hand after regress_check printed no summary line, requested count 2 of 11, store upsert 2 of 11); suite 2287 passed / 2 skipped |
| 82 | The three infrastructure items in one round. **124:** the image copies `uv.lock` and installs from it (`uv export --frozen`, then the project with `--no-deps`), so a deploy ships the versions the suite ran against. **122:** the mail intake's free-disk floor is read from the volume (5%, never below 200 MB, never above half), `/healthz` carries a `disk` block (free bytes, percent, the floor, whether mail is being refused), an unrecognised sender is capped at 5 MB a message and all strangers share 50 MB a day, our own people skip the 40-file per-sender cap, and a dismissed-archive purge ships inert behind `intake.dismissed_purge_days`. **119:** `expense-recon backup` zips the data folder (live databases through SQLite's backup API) to a SharePoint library Brisken controls via the app-only Graph credential, as a CLI (dry run by default, `--check` read-only, `--go`) and an in-app schedule that is off until `EXPENSE_RECON_BACKUP=1`; restore runbook in `docs/backup-and-restore.md` | The drift in 124 was live, not latent: production ran openai 3.14.1 against a lock pinning 2.38.0, a whole major version the suite has never seen. 122 was arithmetic waiting to happen: a 500 MiB floor on a 1 GB volume meant refusals from about half full, at 95 MB used and rising, with bounced receipts mid-close as the first sign, while anyone could mail 25 MB two hundred times a day. 119 is the one with no second chance: every month, every mailed receipt and the learned memory sat on one disk with five days of snapshots and no copy Brisken holds | 2026-09-17, pending PR; `tests/test_intake_disk_limits_item_122.py` (29) and `tests/test_backup_item_119.py` (20), driven through `handle_DATA`, `GET /healthz`, `PUT /api/settings`, the boot path and the `expense-recon backup` CLI; regress_check red on all thirteen wires (122: floor 6 of 29, healthz 3, stranger size limit 1, byte charging 1, known-sender flag 2, boot purge 1, logged size 1; 119: CLI dispatch 3 of 20, app scheduler 1, credential guard 2, size ceiling 1, SQLite snapshot 1, folder create 2, off-by-default 2); image built locally with `docker build` and its versions read back against the lock; Graph target validated read-only against the live tenant, nothing uploaded. Owner actions open: `flyctl volumes extend` to 5 GB, the first deploy moving production back to the locked versions, turning the backup schedule on, and a restore rehearsal |
| 83 | An exact-amount pair from another merchant yields to the right merchant: such a pair reads `requires_review` at 0.55 with "the merchants differ", but only when a rival charge for the same receipt agrees on the merchant, that receipt is the rival's own first choice, and the rival is not awaiting a human pick; after the ambiguity pass (item 133 rule (b)) | The last way a wrong pairing reached the reports with the right charge showing no candidate at all; replay over both live months and the six bundles moved 0 receipts, so precision improves with no measured cost | PR #1053, Fly v170, 2026-09-17 |
| 73 | Account picks removed from Legal entities: `account_options` always comes from the company's chart, `PUT /api/settings` accepts `entities[].account_picks` in any shape and stores nothing, and neither settings response serves a value stored before; SPA half in `docs/lovable-remove-account-picks-prompt.md` | Note #61 (item 23). The owner asked for the box as a dropdown, learned it only shortened the account list a company's rows offer, and ruled to remove it: every row offers the full chart. No live entity carried a value | PR #1044, not yet deployed |
| 72 | The month page split by card, backend: `card_sections[]` on both month GETs (statement loaded / not recorded / not loaded, period, charges, matched, still open, booked without a receipt, receipts, receipts without a charge; expenses and totals on the Expenses payload) and `card_section` on every row, receipt and expense the pages list; `[]` below two cards and on a trip. `card_statement_figures` feeds both the PDF heading line and the tabs. SPA half: `docs/lovable-card-tabs-prompt.md` | Item 138, owner ruling 2026-09-17 ("build now"). The PDFs were organized by card while both month pages mixed every card, so Criss could not check one card's statement against its receipts on screen. The tabs reuse the PDFs' grouping and figures, so a tab and its PDF section cannot disagree; on a 2026-09-17 DB copy July and August file every charge and receipt identically on both pages and in both PDFs | 2026-09-17; route-level `tests/test_card_tabs_item_138.py` (8) plus contract pins in `tests/test_view_contract.py`, regress_check red on all nine wires (run GET 6 of 8, expense GET 4 of 8, charge keys 2, expense keys 4, figures 4, without-a-charge count 3, two-card rule 1, trip rule 1, shared booked figure 1); suite 2274 passed / 2 skipped on the tree merged with main (cost-center half included) |
| 71 | The ECB rate gets its own 2% clean band, and a drifted Settings rate says so: `fx_ecb_match_pct` 0.02 for `ecb_month` pairs only (Settings and self-derived keep 3%), measured at 3 / 2.5 / 2 / 1.75 / 1.5% on July with Settings rates removed (29 / 31 / 32 / 33 / 33 right) and on the six bundles (68 / 70 / 70 / 70 / 69); `setup_advisories[]` `code: "fx_rate_drift"` beyond 1 point from the month's ECB average (items 90 + 132) | Owner ruling: tighten the band before the typed September rates go, so new months stop matching at a stale rate without auto-matching coincidences; nothing moves live until the Settings rates are removed | PR #1048, Fly v167, 2026-09-17 |
| 70 | Month report with cost centers and two cards or more: cards inside cost centers. Each cost center's expenses run in `card_sections` order and key ("No card" last); a center spanning two card groups gets a sub-heading, table and per-currency sums per card, then the center's sums; no statement line in the sub-groups; a held pair whose cards differ still named. Reconciliation report unchanged (it never sectioned by cost center) | Item 138, owner ruling 2026-09-17. Item 138 left cost-center months on their own partition with no card structure, so a month with both could not be read per card inside a project. Changes no live document today (`cost_centers: {}`) | 2026-09-17; route-level `tests/test_expense_report_by_card_item_138.py` (3 new, the old cost-center test rewritten to the ruling) and the builder fallback in `tests/test_month_report_pdf.py`, regress_check red on all six wires (subsections attached 2 of 9, card order inside a center 1 of 9, builder renders subsections 2 of 9, one-card note 1 of 9, two-card trigger 1 of 9, slices must cover the section 1 of 11); suite 2238 passed / 2 skipped; July and August rendered locally from a read-only DB copy with a synthetic assignment |
| 69 | A receipt settling a charge takes its company and person: on the Expenses payload a receipt this month's charge settles (reconciled, pending or confirmed, never rejected) with no card of its own takes the charge's registry card through the per-row card path, `card_source: "settled_charge"`, and leaves the company-or-person box; a pick, a printed card, a hint or a confirmed private wins, a remembered card gives way, `can_mark_private` false. SPA half: `docs/lovable-entity-from-charge-prompt.md` | Item 111. July asked Criss for a company and a person on receipts the matching page had already paired with a charge whose card names both. Live prediction: July 19 of 31 rows (box 31 -> 12), August 2 of 4. The Zoho CSV and the month report follow the same card: July's CSV `(entity - assign)` 35 -> 16 of 56 rows. Not built: the run payload and the matcher do not inherit | 2026-09-17, pending PR; route-level `tests/test_entity_from_settled_charge_item_111.py` (9), regress_check red on all ten wires (payload wire 4 of 7, pick-first 4 of 6, printed-number guard 3 of 6, reviewer verdicts 1 of 6, source value 2 of 6, settled before memory 1 of 7, export resolver / CSV caller / report caller 2 of 9 each, export verdicts 1 of 9); suite 2253 passed / 2 skipped |
| 68 | A receipt arriving re-matches the neighbouring month it belongs to: an add (mail, drop, upload) or a month move owes each label-adjacent company month whose loaded statement period covers the receipt's date a re-match (`rematch_pending` trigger `adjacent_receipts`, written in the arrival's lock span), paid after the month's own re-match, a failure recorded on the neighbour's mark | Item 112. Item 61's borrow was read only when the borrowing month re-matched, so a 07-31 receipt landing in July after August's last re-match waited for an unrelated August event, while trips already had this trigger. Live today 0 receipts in the gap. Not built: the hand-pick half, and a month created by its first receipts | 2026-09-17, pending PR; route-level `tests/test_neighbour_rematch_item_112.py` (8), regress_check red on all seven wires (add owe 5 of 8, add pay 4 of 8, move owe, move pay, trip guard, period check, failure record 1 each); suite 2221 passed / 2 skipped |
| 67 | An invoice read as a statement page stays an expense: a statement verdict with vendor, non-zero total, reference and a line amount is kept with a note, and reads `check` / `invoice_read_as_statement` until its category is confirmed | Item 105. Three real July invoices (AWS USD 3,352.59, Microsoft USD 718.20, Tricarico BRL 27,203.34) left the month as statement pages; eight real statements and two billing notices fail the rule, the three invoices pass it | PR #1037, Fly v165 |
| 64 | An interrupted drop runs again at boot: a sidecar keeps the operator's month pick, the boot pass re-runs each interrupted drop once under its own job id (content dedupe skips what landed), gives up a drop cut off again after running, and deletes leftover drop folders and `drop-add-*` copies | Item 114. A restart mid-drop left the files on the volume for good with nothing re-running or removing them, lost the month pick, and asked the operator to drop the whole pile again | PR #1033, Fly v162 |
| 65 | A model rejection at the floor is not shown unless the tool's own rate is clean, and "Confirm all Ready" follows the pairing rule: a verdict exactly at `fx_judgment_suggest_floor` (0.20) now unbinds the pair (below it was already final and stays so), except a pair with `fx.reference_gap_band` "match", which stays in review with the tool's reason first and "Kept for review although the model disagrees: ..." after it (one band function, `matching.deterministic.reference_gap`, feeds the FX block and the judgment layer); `ready_confirm_pairs` also requires `confirmable_pair` | Items 131 and 133. The model answers exactly 0.20, so "below 0.20" let two rejected July pairs through with "likely NOT the same purchase" as their reason, one wrong (NOBRE 65.23, 4.01% off) and one right (NATHALIA 5.61, 1.5% off); and "Confirm all Ready" read the category verdict only, so one click booked a same-amount receipt on another merchant's charge (BASE44 vs an Anthropic receipt, vendor 22). Measured on a fresh 2026-09-17 DB copy: class tables identical on July and August, July `0059` leaves review, `0062` stays with its reason reordered, `0034` stays out | 2026-09-17, pending PR; route-level `tests/test_rejected_fx_pair_item_131.py` (4) and `tests/test_same_amount_other_merchant_item_133.py` (6), regress_check red on all five wires (at-floor rejection 2 of 4, below-floor guard 1 of 4, band exception 1 of 4, `cfg=` in `rematch_month` 1 of 4, `confirmable_pair` in `ready_confirm_pairs` 3 of 6); suite 2217 passed / 2 skipped |
| 63 | 'Confirm all matched' follows the owner's pairing rule: `service.confirmable_pair` (item 76's rule without the category condition, shared with the self-confirmation), `summary.n_confirm_matched` from the same function, the route answers `{ok, confirmed, remaining, skipped_rule, summary}` under the per-call cap; the bulk route's confirm skips a booked row. SPA half: `docs/lovable-bulk-confirm-dialog-prompt.md` (count badge, disabled at 0, a dialog on both bulk buttons) | Item 101. The button confirmed the matcher's raw matched list: live that meant 27 yellow July rows that never offer Confirm, and every open August pair including BASE44 50.00 at vendor 40 (the Base44/Lovable wrong-pair shape), two `fx_reference` and one `probable` pair. Not built: a history entry for a bulk action (item 104) | 2026-09-17, pending PR; suite 2197 passed / 2 skipped; route-level `tests/test_confirm_matched_rule.py` (10), red under mutation on every wire (route selection 4 of 10, reproduced by hand after regress_check printed no summary line; summary count 2 of 10, bulk booked skip 1 of 10, category kept out of the rule 4 of 10) |
| 66 | Both PDFs say what the screen says: booked charges leave the reconciliation to-do for one line and read "already posted", receipt captions name copy / waiting for review / settled outside / no charge with the screen's reason, a Why column; the month report numbers its captions from the rows actually written and gives an unreadable total a row, its caption and a footer line | Items 96 and 97. July's reconciliation printed 72 charges to do while 48 were yellow in Criss's workbook, and 21 "Unmatched receipt" captions over copies and receipts waiting on review; the month report numbered captions from a second fan-out that could count differently and dropped a receipt with no readable total from the listing while keeping its page | 2026-09-17; route-level `tests/test_pdfs_match_the_screen_items_96_97.py` (6) plus the parity test in `tests/test_coverage_surface.py`, regress_check red on all seven wires; July and August rendered locally from a read-only DB copy (July to-do 72 -> 24, captions 0 mismatches before and after) |
| 62 | Both PDFs organized by card: per card its statement line (statement, period, charges, matched, unreconciled, booked without a receipt), its exceptions, its charges or expenses, then its receipt pages; a last No card section never dropped; a held pair whose cards differ named in its charge's section | Item 138. The reconciliation report was per card only in its coverage table and listing, the month report not at all (flat listing, receipts after it), so nobody could take one card's statement and its receipts and check them together. The document and the matcher now agree on a receipt's card (item 137's chain), and the report had never received the reviewer's card pick at all | 2026-09-17; route-level `tests/test_reconciliation_report_by_card_item_138.py` (3) and `tests/test_expense_report_by_card_item_138.py` (7), regress_check red on all five wires (receipt cards, caption marks, field_overrides to the view; card sectioning 5 of 7, per-section receipt pages 2 of 7); real August rendered locally from a DB copy (73 and 68 pages) |
| 61 | An owed re-match is recorded, retried and repaired at boot: snapshot `rematch_pending` (new id per change, cleared only by the commit that read it), failures on the mark, `/api/operator/state` `rematch_pending[]`, the notifier mails failures | Item 113. A failed or restart-cut re-match left the month quietly stale, and re-running the job skipped the re-pairing | PR #1026, Fly v159 |
| 60 | A mail that added nothing says so: `entries[].not_added` + `n_no_expense` on the intake log, a "Nothing added: ..." label, a "No expense added" acknowledgement naming each file and what would help | Item 106. Four real forwards (AWS billing notices, an AT&T bill notice, a card summary) read "Added" and told their senders the files "landed in July"; nothing reached a month and nobody was asked for the PDF | PR #1017, Fly v157 |
| 59 | Matching separated by card: the card the tool resolved for a receipt (picked, hinted, remembered) scopes and ranks its candidates; a pair on another card asks for review; `rows[].cards_differ` + `summary.n_cards_differ` name a held pair whose cards disagree | Item 137. Only a PRINTED card ever scoped a receipt, so unprinted receipts competed across every card and a confirmed pair could sit on the wrong card unseen (August LOVABLE 25.00 on 3645, receipt picked as 2838). Measured on a live DB copy: July and August class tables identical before and after, six bundles 70/95 unchanged; the cost found on the way (a printed card losing a tie to a picked one, ZOHOCORP 576.00) was designed out | 2026-09-17; route-level `tests/test_card_scope_item_137.py` (7), regress_check red on both wires (bake 5 of 14, view flag 3 of 6, tie signal 1 of 7); SPA half `docs/lovable-cards-differ-prompt.md` |
| 58 | Booked without a receipt: `summary.n_booked_no_receipt` and `summary.booked_no_receipt_by_ccy` count the charges the workbook marks as booked (yellow) that no receipt settles | Item 102. The posted fold is right for the books and hid the evidence question: July read USD 1,054.48 still open while 47 yellow rows (USD 3,385.47) had no receipt at all. The new figure sits next to the unreconciled one so neither changes meaning | 2026-09-17; route-level `tests/test_booked_without_receipt.py` (3), regress_check red 2 of 3 under mutation; SPA half `docs/lovable-booked-no-receipt-prompt.md` |
| 57 | Four feedback notes: `POST .../expenses/{doc}/confirm-category` + `expenses[].category_confirmable` (#62); `card_key` re-matches and a hand-picked card replaces a contradicting printed one in the matcher's pool (#63); `set_aside[].receipt_image_available` (#52); drop ledger `months[].has_statement` + `rematch` (#53). SPA half: `docs/lovable-feedback-0917b-prompt.md` | Items 134, 135, 105 (note #52), 129 (note #53). Notes #28 and #29 (2026-08-21, Inbound) checked on the live page and superseded: 0 held rows, the Month column prints month labels, `-` only on four dismissed TEST mails. Note #61 waits on item 23 | PR #988, 2026-09-17, Fly v150; suite 2080 passed / 2 skipped; six regress proofs RED first |
| 56 | A reference rate per month, from the ECB: the run config's `matching.fx_ecb_monthly_rates` (the ECB's monthly averages as published, all currencies, units per EUR) is fetched at company-month creation and at statement attach / re-read, fail-open; the matcher crosses through EUR for each CHARGE's month, below the typed Settings rate and the self-derived rates; the FX block carries `reference_rate_source: "ecb_month"` + `reference_rate_period`; the setup advisory stops asking for a hand-typed rate. SPA half: `docs/lovable-ecb-rates-prompt.md` | Item 82, note #43, owner ruling 2026-09-16. Simulated before building on a DB copy at v143 and the six bundles: the ECB rate is more accurate (July's 22 labelled FX pairs 1.78% -> 0.44% mean deviation) but on the live months it buys no correct pair (July `0067` clean -> review, `0034` and `0066` newly auto-matched to charges the labels call other merchants; August unchanged), while across the bundles it beats one static rate (68 vs 64 right, 0 vs 3 wrong). Built inert on July and August: their frozen Settings rates still win, replay parity 0 on both. The Settings rates also win for new months until removed there | PR #951, 2026-09-17; suite 1983 -> 1998 / 2 skipped; four regress proofs RED first (matcher call site, view lookup, statement attach, month creation); scorer unchanged 70/95, SCORE 76.0, guard 4/4 PASS |
| 55 | One card fix per expense row, remembered at sign-off: header field `card_key` (active registry card, copied into the month's snapshot when defined later), `expenses[].card_source` (hint / override / learned / none), saved at Publish as a vendor field correction and applied next month only to a receipt that prints no card number; the strip's learning sticks for whole-string aliases shadowed by a shared word alias and for masked BINs. SPA half: `docs/lovable-card-fix-prompt.md`; item 89's months badge prompt rides the same PR | Item 87, note #33. 24 of July's 33 rows with no company or person had no path but "Confirm private" (16 tender words, 8 no card), and two hints the strip called learned would never have resolved again. Suite 1974 -> 1983 / 2 skipped, seven regress proofs | PR #947 |
| 54 | Publishing a month saves its corrections to memory: the publish reply carries `memory` (saved + learned / unchanged / error), through `commit_month_memory`, the helper the button now uses too; a digest per run in `memory_commits` keeps a re-publish from counting the same corrections twice; a failed save never fails the publish. SPA half: `docs/lovable-memory-at-signoff-prompt.md` | Item 88, owner ruling 2026-09-16. `commit_to_memory` had one caller, a button nobody pressed, and the live learning store held 0 learned companies and 0 field corrections, so no month's corrections reached the next. No month has been published yet; the first save happens at the first publish. Suite 1968 -> 1974 / 2 skipped, four regress proofs | PR #940 |
| 53 | The Expenses view's boxes open their rows: `expenses[].boxes[]` (a count name without `n_`) on every row, every box count summed from those rows, `summary.n_needs_company_or_person` for the merged MISSING ENTITY + NEEDS PERSON box, Categorized decided per row by `is_categorized` (every line), and a row whose receipt the app can show is never "missing its image" (both payloads). SPA half: `docs/lovable-expense-boxes-prompt.md` | Item 84. A box that opens its rows must list exactly its number, and two of them could not: Categorized's row rule differed from its count (three two-line receipts), and MISSING RECEIPT IMAGE 2 / 1 named receipts whose files the endpoint served. Suite 1958 -> 1968 / 2 skipped, five regress proofs | PR #935 |
| 52 | The unmatched lists say what they hold: a decided duplicate copy leaves `unmatched_receipts`, `assignable_receipts`, `n_unmatched_rec` and the near-miss pool for `copies_set_aside[]` + `summary.n_copies_set_aside` (view-time split, stored outcome and duplicate lists untouched), and every unmatched receipt and charge carries `reason_code` (receipts: duplicate_copy / card_statement_not_loaded / not_a_card_charge / charge_in_neighbouring_period / no_charge_on_any_loaded_statement; charges: not_a_purchase / receipt_held_by_another_charge / already_booked / no_receipt_found). SPA half: `docs/lovable-unmatched-reasons-prompt.md` | Items 83 + 75, notes #40 and #46. August's "Receipts without a charge" was 21 rows of which 11 were copies of documents that had settled their charge, and no unmatched row on either list said why it was there. Receipt rules are item 69's attribution rules with the date edge read before the card: 11 of 14 labelled live receipts name the labelled kind (card-first 9), one wrong claim (a bank transfer dated 07-30). Suite 1929 -> 1958 / 2 skipped, four regress proofs | PR #932 |
| 51 | A row says whose turn it is and clean exact pairs confirm themselves: `rows[].turn` (decide / confirmed / rejected / posted / none, `decide` == the `n_undecided` set), `rows[].decided_by` (tool / reviewer) + `decided_rule`, `summary.n_self_confirmed`; `apply_self_confirmations` after every `rematch_month` commit (exact, one candidate, category ready, vendor >= 75, not borrowed / held / rejected), withdrawn when it stops qualifying, never over a person's verdict (`RunStore.set_tool_decision` conditional upsert; `decisions.decided_by` / `decided_rule` migrated in place). SPA half: `docs/lovable-turn-prompt.md` | Item 76, notes #38/#39/#49. `status` was `pending` on all 223 live rows, so a booked row asked Reject / Confirm as loudly as the 13 real decisions, and a same-amount same-day same-vendor pair needed a click. Owner rulings 2026-09-16: exact pairs only, vendor floor 75. Predicted live: 5 of the 6 literal exact pairs confirm themselves at the next re-match; 2 clean `fx_reference` pairs (August) keep asking | PR #925, 2026-09-16; suite 1907 -> 1929 passed / 2 skipped; three regress proofs RED first (pass wiring in `rematch_month`, `turn` wiring, the store's reviewer guard) |
| 50 | Duplicates are receipts only, and the tool decides every group: `find_duplicate_charges` deleted (`duplicate_charges` always `[]`, no charge group, no charge row marker, none in the reconciliation PDF); each receipt group is decided by a ladder recorded as `duplicate_groups[].basis` (hash / reference / printed_reference / distinct_reference / receipt_card / vendor_date, then the statement check once per re-match), with parallel `state` (open / decided), `decided_by` (tool / reviewer), `verdict` (copy / distinct) and `summary.n_duplicate_groups_open`. The byte digest is persisted in expense-batch snapshots (`receipt_digests`); rung 3 reads a PDF's own text layer locally, no model call. A reviewer's `confirmed` / `ignore` outranks the tool and never moves `basis`. The PDF lists decided copies under "Copies set aside" instead of asking. SPA half: `docs/lovable-duplicates-decided-prompt.md` | Item 74, notes #37/#41/#45/#46. The panel asked Criss "Real duplicate / Not a duplicate" about pairs nothing needed deciding on, and listed two real charges to one vendor as duplicate charges. Replayed on both live months with the real receipt files: all 16 groups land on the rung the answer key named (July 3 `reference`, 1 `distinct_reference`, 1 `vendor_date`; August 7 `reference`, 2 `printed_reference`, 2 `vendor_date`), and the statement check restores nothing. Matching measured identical before and after: July resolved_clean 31, August 8, wrong 0; bundles determ_ok 70/95, determ_wrong 0; scorer 76.0; guard 4/4. July's Google group `03ba84fadeebe2a5` reads `decided_by: reviewer, verdict: copy` because of a July "Real duplicate" click on two different invoices (5608449734, 5614551183); the tool reads it `distinct_reference`. Rung 7 fires only when the kept copy settled a charge, so identical documents against identical charges stay a pick | PR #914, 2026-09-16; suite 1900 -> 1907 passed / 2 skipped; four regress proofs RED first on the rebased tree (ladder wiring, rung 3 text-layer wiring, rung 7 re-match wiring, `state` field). Deployed Fly v138: live on both months, 16 groups on the answer-key rungs, `n_duplicate_groups_open` 0, no charge group; July's and August's Matching panels driven. Google reset owner-approved and sent (`resolution: ignore`, 200, July re-matched): the group reads `decided_by: reviewer, verdict: distinct`; n_reconciled 32 -> 31, n_review 7 -> 8, `n_charges_receipt_taken` 0 -> 1, copies 5 -> 4; charge `b7abd111d69921a3` holds both invoices as exact candidates and waits on Criss's pick |
| 49 | A reviewer-typed date that belongs in another month offers the move and one POST makes it: `expenses[].month_move {month, label, batch_id?}` (absent otherwise) + `summary.n_month_moves`, and `POST /api/runs/{id}/expenses/{doc}/move` files the receipt into its month (created when absent, `created_by: "move"`), carrying its reading, file, header and category edits and provenance, leaving a soft delete that names the target, and re-matching both months. Amendment (note #45): `time`, `invoice_number`, `receipt_number` read in the same extraction call and carried to `expenses[]` (absent-or-string) | Item 77. A Mercado Pago slip printing 04/07/26 was read as a January date, the drop created "January 2026" for it, and Criss's correction to July left it there, while July's statement holds its charge (`MP *PARADAOBRIGAT` USD 6.20, unmatched). **The locale half was measured and not built:** 129 stored receipts re-read, two runs per arm, and the reported misread is a glyph (gpt-5-mini transcribes the line as `04/01/26`); a locale rule moved 0 dates, and none of the 4 dates off their ground-truth proxy is a swapped order. **The amendment fields cost more than expected:** listed in the instructions they moved 39-41 stable readings, among them a Microsoft invoice re-read as a statement (it would be set aside) and an Amazon.de order re-read as Yubico; asked for in the response schema only, with the instruction text byte-identical, they moved 31, none of them a date, total, currency, document type or resolvable card, against a 12-reading floor that a one-word wording change produces on its own. A machine reading outside the window never offers a move (moving on a reading the guard distrusts would misfile twice) | PR #910, 2026-09-16; suite 1887 -> 1900 passed / 2 skipped; four regress proofs RED first (offer wiring, edits carried, target re-match, stored time). SPA half `docs/lovable-month-move-prompt.md` (owner applies). Deployed Fly v137 (API read: January the only month with an offer, naming July `50622baec444`; five months carry none). Live fix on owner yes: the receipt moved into July and settled `MP *PARADAOBRIGAT` USD 6.20 as `fx_reference` +0.68%; exactly one July row changed, 0 new model calls; January 2026 is empty and kept |
| 48 | Every run row says what kind of statement line it is and where its company came from: `rows[].row_type` (purchase / payment / refund / reversal / fee / interest, from the statement's Type label, else the sign's old reading) and `rows[].entity_source` (card / batch / none). Stored on `Transaction`; snapshots from before read the stored Type cell back out of `raw_text` (`ast`, never evaluated). `is_credit`, matching, buckets and every count unchanged. `month_health` skips card payments; the reconciliation PDF prints "card payment"; the report workbook's credits section gains a Type column. SPA half: `docs/lovable-row-type-prompt.md` | Item 73, note #42. July's -9,664.81 and August's -7,823.16 "Payment Thank You-Mobile" rows are the card balance being paid, and the page filed them under "Refund" because the parsers read the workbook's `Payment` label only as "credit". The item's secondary claim (entity inherited from the upload) did not reproduce: the row printed card 2838 and the registry named its company. Both live payment rows' stored `raw_text` read back `payment` before deploy | PR #905. Suite 1832 -> 1844 on `178827a7`; 1876 after rebasing onto `a101c755` (main 1864). Eight regress proofs, all red first: view wiring, entity_source, raw_text read-back, xlsx label, csv label, month-health skip, PDF label, workbook Type cell |
| 47 | The FX block shows the receipt converted at the tool's own rate: `rows[].candidates[].fx` gains `reference_rate`, `reference_rate_source` (`settings` / `statement` / `receipts`, open for item 82's `ecb_month`), `reference_converted`, `reference_gap`, `reference_gap_pct` and `reference_gap_band` (`match` / `review` / `outside`, on the unrounded deviation), all absent when the pair has no rate. The rate is the matcher's own: `fx_reference_lookup` runs `build_match_cfg` over the run's frozen config, then `derive_fx_reference_rates` and `_reference_rate_for`, once per view | Item 81, note #43. The block printed only the rate a pairing NEEDS (1.143002) while the rate the matcher USED (Settings 1.162275) sat in the reason string, and "Receipt is worth" read `zoho_converted`, which none of the 27 FX candidates on the two live months carries. So the one calculation that answers "same purchase?" never reached the screen. Read live first: all four named pairs reproduced to the cent under the live rates (AMAZON 320.88 / -5.32 / -1.66, SUPERMEC 8.05 / +0.24 / +2.93, ANTHROPIC 248.96 / -1.64 / -0.66, PETIT TRAIN 37.19 / +0.29 / +0.77), and every live FX candidate has a rate: 26 `match`, 1 `review` (NOBRE ATACAREJO, +4.01%). Reading the frozen config instead of Settings is what makes the fields appear on deploy without a re-match, and keeps the screen on the rate the month was actually matched against. A test swaps `_reference_rate_for` and watches the screen move; every `fx_reference` reason carries the printed rate verbatim across all three sources. The printed difference is charge minus the converted amount as printed, so the two figures add up to the cent; the percentage keeps the matcher's basis. One residual, stated in the contract: a `receipts`-derived rate is re-derived from the month's current pool. `zoho_*` untouched (item 23 amendment) | PR #903, 2026-09-16; suite 1832 -> 1843 alone, 1855 after rebasing onto #899/#900, 1875 after merging #901/#902; three regress proofs RED first (candidate call site, hand-match call site, frozen config), re-run after the rebase; Fly deploy after merge; SPA half `docs/lovable-fx-reference-prompt.md` (owner applies) |
| 46 | Every `rows[].candidates[]` entry says how far apart its two dates are: `date_gap_days` (charge `transaction_date` minus receipt `detected_date`, calendar days, signed) and `date_gap_zone` (`none` -1..+1, `lag` +2..+7 or -3..-2, `mismatch` otherwise), parallel and absent when either date is missing, on both emission sites (matcher candidates and the reviewer's hand match). One constant, `service.DATE_GAP_ZONES`, carries the 141-label-pair and Visa / Mastercard / Chase evidence; the matcher, its windows, `score` and `date_pct` are untouched. SPA half: `docs/lovable-date-gap-prompt.md` | Item 80, note #44. The SPA warned "date mismatch" whenever the chosen candidate's `date_pct` was below 99, i.e. any gap of a day or more, so six reconciled July rows that the labels confirm (AMAZON 315.56, MP *24HBEBIDAS 24.88, GOOGLE Workspace 71.64, three ANTHROPIC top-ups) wore a warning and sat in the Warnings filter for an ordinary midnight / time-zone / charged-at-shipment lag. Live read held exactly: July 38 candidates (31 at 0 days, 7 at +1) all `none`; August 12 (9 / 2 at -1 / 1 at -2) is 11 `none` and 1 `lag`, 0 `mismatch` anywhere. After the prompt, July's Warnings-only set goes 27 -> 23 (AMAZON and MP keep "amount mismatch") | PR #902. Suite 1832 -> 1852 on `d8b66307` (1864 after rebasing onto item 79's #900). Three regress proofs: zone call -> `"mismatch"` (red: 0d, +1d, -1d, +3d, -3d, hand match), matcher spread disabled (red: all six offsets), hand-match spread disabled (red: hand match) |
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
