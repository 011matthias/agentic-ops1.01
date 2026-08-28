---
project: brisken
workstream: p1-expense-reconciliation
kind: improvement-backlog
state: active
updated: 2026-08-26
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
about which card a charge is on. The SPA half is
`docs/lovable-coverage-prompt.md`, outstanding until the owner pastes it.

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

### 26. Card registry gaps put 8 rows in MISSING ENTITY (owner-side, 2026-08-23)

Four of the five known cards (0113, 6013, 9693, 8311) carry no legal entity,
and the 0340 card is absent from the registry entirely — the 0340 rows alone
account for 8 of the 29 unresolved entity rows. Nine more rows are generic
tenders (cash, personal), which by design never auto-resolve and stay
per-month assignments.

No code needed: this is data entry in Settings > Cards, plus creating the
0340 card. Listed here so it is not mistaken for a defect in the chain.

### 16. Rejected matches need a "what now" (2026-07-27 note, untracked)

STATUS_REJECTED sends the transaction back to unmatched and is reversible
pre-export, but no rejected bucket exists in the API and no affordance
answers "what happens to rejected matches?". Spec fresh.

### 17. Workbench filter/sort (2026-07-27 note, untracked)

"There should be a filter somewhere: alphabetic, unmatched elements."
Natural home: the grouped-queue render (PR #454/#455's remaining Lovable
half). Spec with it.

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
