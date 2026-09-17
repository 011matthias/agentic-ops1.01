# Lovable prompt status: what is applied to the published SPA

**Audited 2026-08-25 against `brisken-reconcile-dash.lovable.app`** by
driving the app, not by reading this repo. Re-run the audit and update this
file whenever the owner publishes; a prompt's presence in `docs/` says
nothing about whether it was ever pasted.

The audit script is `%TEMP%/claude/recon-probe/prompt_ledger.py`. Signatures
are VERBATIM strings from each prompt.

**Re-audited 2026-09-01**, by a different method: fetch every JS chunk the
published app can load (44 chunks, 921 KB) and grep the lot. A string
rendered from an i18n key still lives in a chunk, so this sees copy the DOM
only shows after a click, and it needs no browser. Where display copy is
ambiguous, the decisive signature is the API FIELD NAME the applied code has
to read (`seen_undefined`, `n_duplicate_copies`, `is_extra`, `coverage`,
`period_suggestion`): a renderer cannot show a field it never names.

**Re-audited 2026-09-06 after the owner published: every prompt in this
file is applied. The Not-applied table is empty for the first time.**

**Re-audited 2026-09-07 after the owner pasted and published the four
pending prompts (R1 person/private, months origin + refusals, R3 trips,
R4 settled-by): every prompt is applied again. Method: fetched the live
index + 45 JS chunks (937 KB) and grepped the decisive field names; for
the two whole-object-replace gates, read the settings chunk's save-payload
construction to confirm the writes carry `person` and `travel_alias`.**

**Re-audited 2026-09-08 evening (46 chunks): the receipts-drop prompt's v1
was published by the owner mid-day** — `chunk-receipts` reads `n_filed` /
`n_needs_month` / `needs_month`, `/api/receipts` + "Recibos" + "Dos
recibos" live in the i18n chunk. The same-day amendments are NOT in the
bundle (`upload-cap` zero hits; "Start a new month" and `expenses/new`
still referenced), so the pending paste is now the DELTA in the reworked
`lovable-receipts-drop-prompt.md`. Lesson pinned: the operator reporting a
behavior only a live page could show ("can only accept 80 files") IS a
publish signal — re-audit then, not at the next session boundary.

**Re-audited 2026-09-15 evening (48 chunks, 1,012 KB, lazy route chunks
crawled through their imports): 11 of the 14 prompts pasted since 2026-09-08
are applied.** Instrument controls `period_suggestion`, `seen_undefined` and
`n_duplicate_copies` all hit, so the crawl can see renderers. Still out:
view-receipt (item 52), settled-outside (item 62) and the API host switch.
The six assets `index.html` names are NOT the bundle: the renderers live in
chunks reached only by dynamic import, and grepping those six alone reports
every recent prompt as missing.

**Re-audited 2026-09-16 after the owner pasted and published month-edits
(item 70) and card-chips (item 71): both applied, the Not-applied table is
empty again.** Bundle: 49 chunks, 1,015 KB, all five controls hit, all six
decisive keys present. Then driven in a browser, cold from the login gate at
1440x900 (bundle presence alone is not the verification). Evidence is in each
row below.

**Re-audited 2026-09-16 evening after the owner published month-views (item
79) and journal-callers (item 23 round 4): both applied.** 48 chunks, 1,022 KB,
controls hit; then browser-driven cold from the login gate. The other pending
rows (date-gap, fx-reference, row-type) were not pasted in this publish:
`date_gap_zone`, `reference_gap_band` and `row_type` are 0 hits in every chunk.

**Re-audited 2026-09-16 late evening: date-gap (item 80), fx-reference (81),
row-type (73), month-move (77) and duplicates-decided (74) are all applied, so
the Not-applied table is empty again.** 48 chunks, 1,033 KB, all five controls
hit; 19 of the 20 decisive names present. The one absent,
`n_duplicate_groups_open`, is harmless: the prompt's render rule partitions each
group by its own `state`, and nothing on screen was ever asked to print the
count. Then driven cold from the login gate (`agent-browser --session
recon-verify`, 1440x900, waiting on text), payloads re-read minutes before, EN
on both months and PT on August, **0 POST/PUT/PATCH/DELETE after login**.
Evidence per prompt in the Applied rows. Not driven: item 80's "Warnings only
27 -> 23" count (the month is split into views now, so the prompt's
whole-month count has no single screen).

**Re-audited 2026-09-16 night after the owner published the turn prompt (item
76): applied, the Not-applied table is empty again.** 48 chunks, 1,035 KB, all
five controls hit, all five decisive names present. Driven cold from the login
gate in a fresh named session (`recon-turn`), every view of both months, EN and
PT on August, 0 POST/PUT/PATCH/DELETE after login. Evidence in the Applied row.

**Re-audited 2026-09-17 after the owner published unmatched-reasons (items 83 +
75), expense-boxes (84), controls-as-buttons (85 + 86) and memory-at-signoff
(88): all four applied, the Not-applied table is empty again.** 48 chunks,
1,047 KB, all five controls hit, all 15 decisive names present. Payloads re-read
first and unchanged from the 2026-09-16 handoff (July 11 unmatched receipts + 2
set aside, August 10 + 11; July boxes 49 / 3 / 14 / 33 / 24 / 0, August 27 / 4 /
10 / 13 / 8 / 0; nothing published). Driven cold from the login gate in a fresh
named session (`rv917`, 1440x900, waiting on text), EN on both months, PT on
both, **236 GET and 7 OPTIONS, 0 POST/PUT/PATCH/DELETE after login**. One dialog
was opened (Confirm private expense) and closed with Escape. Evidence in the
four Applied rows.

**Re-audited 2026-09-17 later, after the owner published card-fix (item 87),
matched-with-statement (item 89) and ecb-rates (item 82): all three applied,
the Not-applied table is empty again.** 48 chunks, 1,050 KB, all five controls
hit, all 11 decisive names present, and both old `set.fx.desc` strings ("update
them when you start a new month", "atualize ao começar um novo mês") absent.
Driven cold in a fresh named session (`rv82b`), EN and PT; one card select
opened and closed with Escape, nothing picked. July and August `updated_at`
unchanged before and after. Evidence in the three Applied rows.

**Re-audited 2026-09-17 evening after the owner published settings-tabs (item 91): applied, the Not-applied table is empty again.** 43 chunks, 878 KB, controls hit, all five new keys present, `applied` read by the save. Driven cold in Chrome, EN, no Save pressed. Evidence in the Applied row.

**Re-audited 2026-09-17 evening after the owner published entity-order (item 92), backend v146 deployed the same pass: applied.** 49 chunks, 1,063 KB, controls hit, all six new keys present, the save sends `{entity_order}` alone and checks `applied`. Driven cold in headless Chrome, EN, nothing reordered or saved. Evidence in the Applied row.

**Re-audited 2026-09-17 night after the owner published entity-order round 2 (press, hold, drag): applied, and the order is now in live use.** 49 chunks, 1,114 KB, controls hit, all six `set.entities.dnd.*`/`dragHandle` keys and dnd-kit (`DndDescribedBy`, `DndLiveRegion`) in `chunk-settings`, `set.entities.moveUp` and the native drag handlers gone from it. Driven cold in headless Chrome; one lift cancelled with Escape, nothing dropped or saved. Evidence in the Applied row.

Two display strings misread on the 2026-09-01 pass, both resolved by reading
the surrounding key: `"Not a duplicate"` is `wb.dups.notDup` from the workbench
duplicates panel, which predates `lovable-duplicates-prompt.md` and is not
its row badge; `"Card account id"` survives on purpose as the Other-account
free-text label, so it is not evidence that the attach-dialog prompt is
missing.

**Two traps this audit hit, both of which produced a wrong answer first:**

1. A loose regex matched a Cards help line ("every company card the tool can
   recognise") and reported the known-senders editor as present. Match exact
   strings.
2. Per-row actions on the intake table are an icon-only
   `button[aria-label="Actions"]` opening a Radix menu, so enumerating button
   TEXT reports no actions on any row. Click it and read `[role=menuitem]`.

## Applied

| Prompt | Verified by |
|---|---|
| `lovable-month-health-prompt.md` (item 57) | `chunk-runs._runId` reads `month_health` + `n_exact_pairs`; `chunk-i18n` carries `wb.health.*` + `zero_match_with_exact_pairs` (bundle audit 2026-09-15, 48 files / 975 KB, controls validated). The blocked bar itself has no live case: both months are `state: ok` |
| `lovable-charge-entity-prompt.md` (item 59) | `chunk-runs._runId` reads `n_charges_no_entity`; `chunk-i18n` carries `chargesNoEntity` + `cardNotDefined`. CHARGES WITHOUT A COMPANY renders 0 on both live months (browser-driven). The "Card not defined" chip has no live case: every card is defined |
| `lovable-receipts-drop-prompt.md` v1 (#709 text; §1 page + §3 badge + §4 empty state + §2 upload-area removal) | `chunk-receipts` reads `n_filed`/`n_needs_month`/`needs_month`; `/api/receipts` POST; "Recibos" nav + "Dos recibos" badge strings in i18n (bundle audit 2026-09-08; badge wiring + §4 to be eyeballed on the next browser drive) |
| `lovable-mail-intake-prompt.md` | Email intake section in Settings; alias rows; "Receipts can be emailed to any-name@expenses.brisken.com" |
| `lovable-intake-quickwins-prompt.md` §1 §2 | Files column; Month column with real labels |
| `lovable-body-only-prompt.md` | Held-row menu offers View body / Add to month as PDF / Dismiss |
| `lovable-month-pool-prompt.md` §1-§11 (file now banner-marked APPLIED) | "Waiting: 6" badge; "August 2026 (waiting)"; Dismiss on pooled rows; "Retry held and add waiting mail" |
| `lovable-month-report-prompt.md` | "Download expense report (PDF)", "Download CSV (data export)", "Download reconciliation (PDF)" |
| `lovable-cards-prompt.md` | Cards section; "every number that identifies this card"; "from legacy maps" badge |
| `lovable-cards-r3-prompt.md` | "Legal entity (optional; leave empty when receipts mix companies)"; card-review strip with "Assign to card..."; generic-tender note; MISSING ENTITY tile; Refresh master data |
| `lovable-zoho-decoupling-prompt.md` §1 | "Zoho GL account (optional)" + "overrides the chart-derived account when a category is set" |
| `lovable-merchants-prompt.md` | Merchants editor with Canonical name / Aliases / Category |
| `lovable-variance-books-as-prompt.md` | "Books as" depiction; "Mixed categories" chip; "This vendor uses multiple categories" toggle |
| `lovable-set-aside-prompt.md` | Set-aside strip + "This is a receipt" restore |
| `lovable-language-receipt-prompt.md` §1 §4 | "(uncategorized - assign)"; MISSING RECEIPT IMAGE tile |
| `lovable-memory-edit-prompt.md` | Validate action; "Needs review" filter; per-row edit |
| `lovable-feedback-capture-prompt.md` | Double-click opens the popover (Feedback on "..." / Comment / Send). The footer discoverability hint is absent; the widget works |
| `lovable-feedback-r1-prompt.md` | "Leave blank (resolve from card)"; currency under Advanced |
| `lovable-ready-tile-prompt.md` | Stat row reads EXPENSES / CATEGORIZED / NEEDS CATEGORY / READY / TOTALS |
| `lovable-months-list-prompt.md` | `/months` renders a table: 6 rows, 6 `/expenses/{id}` links, real labels (January 2026, May 2026, April 2026). Backlog item 32 CLOSED |
| `lovable-known-senders-prompt.md` | "People we recognise" editor present AND the stale "Accepted senders" editor is GONE. Backlog item 31 CLOSED |
| `lovable-inbound-status-refusals-prompt.md` | Status cells render the backend `status_label` ("Waiting for August 2026"); the refusals strip is present, worded **"turned away"** |
| `lovable-attach-dialog-prompt.md` | `months.attach.cardOther` = "Other account..." and `months.attach.cardFilled` in the i18n dictionary (2026-09-01) |
| `lovable-card-strip-prompt.md` | "Card ending" and "No card number on the receipt" (2026-09-01) |
| `lovable-zoho-copy-prompt.md` | "Download journal CSV" and "matched against this month's receipts" (2026-09-01) |
| `lovable-month-suggestion-prompt.md` | The bundle reads `period_suggestion`. Gated on PR #657 deploying the field; pasted 2026-09-01 (2026-09-01) |
| `lovable-coverage-prompt.md` | "Coverage by card", "Add a statement", "not in your card list"; `coverage` read twice (2026-09-06) |
| `lovable-duplicates-prompt.md` | `n_duplicate_copies` and `is_extra` both read; `expx.dup.*` keys in EN and PT, including the singular "1 duplicate copy" (2026-09-06) |
| `lovable-card-definition-prompt.md` | `seen_undefined`, `suggested_key` and `n_charges` all read; "Define this card" present (2026-09-06) |
| `lovable-months-open-prompt.md` | `months.open` = "Open" / "Abrir" wired to a menu item, "Actions for" label present, and the hover-only `underline-offset-2 hover:underline` is GONE (2026-09-06) |
| `lovable-r1-person-private-prompt.md` | Settings chunk reads AND writes `person`: card rows hydrate `person: e.person ?? ""` and the save payload carries `person: t.person` (same for the intake alias-to-person map). Grid chunk reads `suggested_private`, `reimburse_to_prefill`, `n_needs_person`, `spellings`. Person data entry is safe (2026-09-07) |
| `lovable-months-origin-refusals-prompt.md` | `created_by` read in the months chunk; `n_refused_ours`, `n_probes`, `kind_label` read in the inbound chunk (2026-09-07) |
| `lovable-trips-prompt.md` | `trip_id` / `batch_type` / `pool_kind` / `trip_suggestion` / `n_pooled_travel` across the trips, inbound and NewExpenseBatch chunks (a dedicated `chunk-trips-*` exists). §5 verified: the settings chunk hydrates `travel_alias` from the intake object, re-syncs it on object change, and the save payload carries `travel_alias: C.trim()...` — alias entry through the SPA is now safe (2026-09-07) |
| `lovable-r4-settled-by-prompt.md` | `settled_by` read in the run chunk (x3) and the batch chunk (2026-09-07) |
| `lovable-receipt-taken-prompt.md` | `held_by` (x9) + `n_charges_receipt_taken` (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-receipt-coverage-prompt.md` | `n_receipts_in_report` (x3) (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-receipts-drop-prompt.md` | `upload-cap` present. Two leftovers from §2: the `/` route's page title and meta description still read "Start a new month", and the i18n chunk still carries `months.startMonth`. Cosmetic; the create UI itself is gone (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-cost-centers-prompt.md` | `cost_centers` (x6), `default_cost_center` (x2), `/api/cost-centers/totals`. **Whole-map gate LIFTED**: the settings chunk saves per section (`b.mutate({cost_centers:e})`, `b.mutate({cards:e})`, `b.mutate({fx_reference_rates:e})`), so saving one editor never sends, and never erases, another's map. Cost centers can be typed (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-rejected-pairing-prompt.md` | `n_rejected_pairings` (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-amounts-unreadable-prompt.md` | `n_amounts_unreadable` (x3) (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-adjacent-month-prompt.md` | `from_batch` (x7) + `n_adjacent_borrowed` (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-render-failed-prompt.md` | `receipt_render` + `n_receipts_unrenderable` (x3) (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-statement-record-prompt.md` | `card_currency` (x4), `column_map` (x3), `readAs` (x12) (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-workbench-filter-sort-prompt.md` | the amount parse (`[^0-9.-]`) and `sort=` in the query string are present. The prompt asks for a browser drive and none has been run, so treat the row order as unverified (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-failure-probe-prompt.md` | `/api/client-errors` + `seconds_ago`, both halves present. Item 50's SPA half is shipped; the probe is silent by design, so nothing on screen confirms it (bundle audit 2026-09-15 evening, 48 chunks / 1,012 KB) |
| `lovable-settled-outside-prompt.md` (item 62) | `n_settled_outside` (x1), `suggested_settled_outside` (x1), `/settled-outside` (x2), `wb.settledOutside` (x29) (bundle audit 2026-09-15 after the owner's 13:41-13:47 UTC publish, 49 chunks / 1,009 KB, the five controls found) |
| `lovable-view-receipt-prompt.md` (item 52) | `receipt.view.failed` (x4), `application/pdf` (x3), same audit. **Browser-driven 2026-09-15:** on August's workbench `/runs/074a7b8905d7` a click opened the dialog "Receipt · SARL TRAIN'S · 32.00 EUR" with the PDF rendered in an `<iframe>` from a `blob:` URL. On Review expenses of a statement month the button is still unusable: the grid's `<fieldset disabled={hasStatement}>` disables it (31 of 31 buttons inside a disabled fieldset on August); `lovable-month-edits-prompt.md` (item 70) lifts that lock. **Browser-driven 2026-09-16 after that publish:** on August's Review expenses a View receipt click fired `GET .../receipts/0000__rendered-body.pdf/image` 200 and opened "Receipt · rendered-body.pdf" in an `<iframe>` on a `blob:` URL. Usable on both pages now |
| `lovable-brisken-domain-prompt.md` half 2 (API base URL) | `api.expenses.brisken.com` (x1) AND `brisken-expense-recon.fly.dev` (x0), same audit |
| `lovable-workbench-filter-sort-prompt.md`, the row order | **Browser drive 2026-09-15 FAILED on the counts:** every Card option reads the total (July: "112" on all nine cards, including the five with 0 charges), because `countWith(patch, skip)` skips the dimension it just patched. Fix carried by `lovable-card-chips-prompt.md` section 1. **Fixed, driven 2026-09-16:** chips count per option, and clicking `3645 · 27` leaves "27 of 112 charges" |
| `lovable-month-edits-prompt.md` (item 70) | `posting_category_proposed` (x1, `chunk-runs._runId`), `wb.category.proposedNote` + `expx.review.toast.rematchFailed` (i18n), bundle audit 2026-09-16. **Browser-driven 2026-09-16:** August Review expenses renders 0 disabled fieldsets and 0 of 412 buttons disabled; the proposed-category note shows 7 times on July's workbench, matching the 7 rows the API flags `posting_category_proposed`. Edit round-trip on a statement month: tax label on `0025__Invoice-H0LHY2WQ-0032.pdf` set to `TEST-0916` (PUT 200, the call that used to 400), survived a full reload, cleared, reload shows the empty placeholder; August counts identical before and after (8 / 2 / 100 / 1, READY 10). NOT verified: the §3 re-match-failure toast, which needs a re-match to genuinely fail |
| `lovable-card-chips-prompt.md` (item 71) | `wb.filter.card.empty`, `cov.attn.receiptsNoCharges`, `expx.cards.strip.summary.choose` (i18n), bundle audit 2026-09-16. **Browser-driven 2026-09-16, the prompt's four checks:** (1) July has no coverage table on top, one statement line, chips `3876 · 48`, `2838 · 36`, `3645 · 27`, `0340 · 1`, `+ 5 cards with nothing this month`, no banner; 3645 active shows "Credit Card Chase Visa - 3645 · Dirk Neumann - Corp Services · Corporate Services · 3 matched · 0 need a look · 24 no receipt · USD 1,054.48". (2) August banner lists 1176 (Consulting) 4 receipts and 9693 (Cloud Services) 2 receipts; buckets 2 / 100 / 8 / 1. The prompt predicted 2 receipts and 3 / 96 / 11 / 1: those numbers predate the round A and B re-matches, the live data moved. (3) August strip collapsed to "8 receipts not matched to a company card · 8 look private · Review". (4) July's first charge row sits at 963px against a 945px viewport with "How this works" expanded (126px), so it clears the fold only with that block collapsed; was 1.7 screen heights |
| `lovable-month-views-prompt.md` (item 79) | Bundle 2026-09-16 evening (48 chunks, 1,022 KB, controls `posting_category_proposed`, `wb.filter.card.empty`, `n_settled_outside`, `period_suggestion`, `seen_undefined` all hit): `month.tab.matching` + `month.tab.addStatement` in the shared `chunk-ReceiptViewer` (not a route chunk, as predicted); `wb.view.receipts`, `wb.view.refund`, `wb.decided.switch`, `wb.decided.foldPosted.many` in `chunk-runs._runId`; `expx.recon.credits.one` + `expx.cards.strip.rows.one` in `chunk-expenses._batchId`; `wb.backToDashboard`, `wb.bucket.posted`, `sum.matchRate`, `sum.unmatchedTx`, `sum.unmatchedRec` 0 in the runs chunk; `months.locked.*` 0 and `expx.landing.title` 1 in the expenses chunk; route title "Matching · Brisken" in `index-*`, no em-dash title. **Browser-driven the same evening** (named session, cold from the login gate, 1440x900, payloads re-read first): September `/runs/51a22ad72864` lands on `/expenses/51a22ad72864` with the strip "← Months · September 2026 · Expenses 36 · Add a statement", no read-only box, no raw badge key. July Matching: cards 14 (9 open) / 73 (24 open) / 7 (0 open) / 1 (0 open) / 31 (3 open), "Blocked · 3 rows to decide", "USD 1,054.48 still open", "1 receipt from next door", no tile bar, no Journal CSV, sticky = Menu + strip only; folds "5 copies set aside" (view 1), "49 already posted in your workbook" with chips 3876 · 31, 2838 · 18, 3645 · 24, 0340 · 0 and "24 of 73 charges" (view 2), "Nothing open here" + "7 already posted" (view 3), "Nothing open here" + "1 already posted" (view 4), "28 already posted" + caption "1 receipt line without a category" + "Confirm 3 shown" (view 5); duplicates "6 decided". July Expenses: "Reconciliation: 31 matched · 7 need review · 73 charges without a receipt · 14 receipts without a charge · 1 credit", Add receipts present. August Matching: 21 (10 open) / 100 / 2 / 1 (0 open) / 8, "Blocked · 10 rows to decide", "USD 10,950.12 still open", the 1176 / 9693 banner, "11 decided". **Not observed:** August view 2's new caption "1 waits on a receipt another charge holds" (`n_charges_receipt_taken` 1 on the payload); three clicks on that card did not switch the view, while the same click switched July's views. A `?view=unmatched` deep link opened on view 1 with the query stripped in a fresh session, so the URL may not seed the view on load; unconfirmed whether that is the SPA or the drive. PT pass not driven |
| `lovable-journal-callers-prompt.md` (item 23 round 4, consumer half) | ABSENCE, same crawl with the controls hitting: `zoho.csv`, `export_approved_only`, `sum.dl.zoho`, `dash.pub.download`, `set.export.help` 0 hits in every chunk (2026-09-16 morning: `zoho.csv` in `chunk-classic` and `chunk-runs._runId`, `export_approved_only` in the settings chunk). July's Downloads row renders Report, Reconciled CSV, Statement and no Journal CSV (browser, same drive). **The round-4 backend PR (route deletion) is unblocked** |
| `lovable-date-gap-prompt.md` (item 80) | Bundle 2026-09-16 late evening (48 chunks, 1,033 KB, controls hit): `date_gap_zone` in `chunk-runs._runId`; `wb.dateGap.chargedAfter` + `wb.dateGap.receiptAfter` in `chunk-i18n`. **Browser-driven cold:** "date mismatch" appears 0 times on July's Matching view (all five views) and 0 on August's; the live payload has 31 chosen candidates on July and 8 on August, every one zone `none`, so no neutral lag chip has a live case. "Warnings only" 27 -> 23 not driven (see the re-audit note) |
| `lovable-fx-reference-prompt.md` (item 81) | Same crawl: `reference_gap_band` + `reference_rate_source` in `chunk-runs._runId`; `wb.fx.referenceRate`, `wb.fx.receiptIn`, `wb.fx.source.settings` in `chunk-i18n`. **The prompt's five checks, driven:** (1) July AMAZON* Z11US7DF5 reads `276.08 EUR x 1.162275 = 320.88 USD · difference -5.32 USD (-1.66%)`; Details rows in order Bank statement 315.56 USD, Receipt 276.08 EUR, Reference rate 1.162275 (USD per EUR) · Settings, Receipt in USD 320.88, Difference -5.32 (-1.66%), This match needs 1.143002 last. (2) SUPERMEC SAO JOSE `41.85 BRL x 0.192448 = 8.05 USD · difference +0.24 USD (+2.93%)`. (3) NOBRE ATACAREJO `+2.52 USD (+4.01%)` line carries the amber class. (4) August ANTHROPIC* CLAUDE SUB 247.32 `214.20 EUR x 1.162275 = 248.96 USD · difference -1.64 USD (-0.66%)`, PETIT TRAIN TOUR `32.00 EUR x 1.162275 = 37.19 USD · difference +0.29 USD (+0.77%)`. (5) PT on August: "diferença", "Taxa de referência", "· Configurações", "Recibo em USD". Residue seen, not this prompt's: the row warning chip "amount mismatch" stays English under PT |
| `lovable-row-type-prompt.md` (item 73) | Same crawl: `row_type` in `chunk-runs._runId`; `wb.rowType.payment`, `wb.entity.fromUpload`, `wb.credits.tip` in `chunk-i18n`. **Driven:** July "Credits on the statement" view, posted fold opened: "Payment Thank You-Mobile" -9,664.81 carries "Card payment", and its "Corporate Services" chip's tooltip reads "Company of the card on this row: Credit Card - 2838". August: "ANNUAL MEMBERSHIP FEE" 150.00 in Charges without a receipt carries "Card fee"; "Payment Thank You-Mobile" -7,823.16 carries "Card payment". No purchase row text carried a type chip. The same July payoff row still reads "Awaiting decision" with Reject and a disabled Confirm (item 76) |
| `lovable-month-move-prompt.md` (item 77) | Same crawl: `month_move` + `n_month_moves` in `chunk-expenses._batchId`; `expx.review.monthMove` in `chunk-i18n`. The renderer itself has no live case (see Cannot verify); July's Expenses view renders with no "Move to" line and no fallback string |
| `lovable-duplicates-decided-prompt.md` (item 74) | Same crawl: `decided_by` in `chunk-runs._runId`; `wb.dups.setAside.title`, `wb.dups.basis.printed_reference`, `wb.dups.notCopy` in `chunk-i18n`. **`n_duplicate_groups_open` 0 hits**: harmless, the panel partitions each group by its own `state` and the prompt never asked it to print the count. **Driven**, read-only (folds opened, no undo clicked): July reads "Copies set aside (2) · 3 kept apart" with no "Possible duplicates", "Advisory only", "Duplicate charges" or "Real duplicate"; opened, Aposto 80.00 "Set aside by a reviewer", Lovable 200.00 "Same document number", each with one "Not a copy"; Google 71.64 x2, Hostinger 172.61 x2 and Redis 13,200.00 x2 "Kept apart by a reviewer", each with one "Same document". August: "Copies set aside (11)", 7 "Same document number", 2 "One prints the other's number" (Lovable HMVWDWIL0029/0030), 2 "Same vendor, date and amount" (OpenAI, Obsidian), 11 "Not a copy" buttons. PT on August: "Cópias separadas (11)", "Um traz o número do outro" x2, "Não é cópia" x11. The prompt's July prediction (5 copies) predates two reviewer rulings made 2026-09-16 16:17 UTC that turned the Hostinger and Redis groups into kept-apart |
| `lovable-turn-prompt.md` (item 76) | Bundle 2026-09-16 night: `n_self_confirmed` + `wb.selfConfirmed.count` in `chunk-runs._runId`; `row.status.confirmedByTool`, `row.status.posted`, `row.status.none` in `chunk-i18n`. **Driven, payloads re-read first (July decide 1 / self-confirmed 2, August 7 / 3):** July Matched caption "2 confirmed automatically"; ELEVENLABS.IO 5.00 and ANTHROPIC 50.54 read "Confirmed automatically" with the undo icon and no Reject / Confirm; AMAZON* Z11US7DF5 315.56 reads "Confirmed" with its undo; every row in its posted fold reads "Already booked" with no Reject / Confirm; WEB*NETWORKSOLUTIONS 7.98 reads "Awaiting decision" with Reject + Confirm match; Credits view "Payment Thank You-Mobile" -9,664.81 reads "Already booked", no buttons; the 24 open charges without a receipt read "Nothing to decide" with Attach receipt only. August, all five views: 100 charges without a receipt "Nothing to decide" + Attach receipt; Needs review 2 + Matched 5 rows "Awaiting decision" with both buttons (= `n_undecided` 7); payoff -7,823.16 "Already booked"; LOVABLE 15.00, LOVABLE 25.00, ANTHROPIC 51.38 "Confirmed automatically" with undo; caption "3 confirmed automatically". PT on August: "3 confirmadas automaticamente", "Confirmada automaticamente", "Já lançada", "Nada a decidir", "Aguardando decisão" + Rejeitar / Confirmar par. **Not observed:** the badge tooltips (a hover on "Already booked" rendered no tooltip in the drive; the keys are in the bundle) |
| `lovable-unmatched-reasons-prompt.md` (items 83 + 75) | Bundle 2026-09-17 (48 chunks, 1,047 KB, controls hit): `copies_set_aside`, `wb.reason.breakdown` in `chunk-runs._runId`; `wb.reason.receipt.card_statement_not_loaded`, `wb.reason.charge.receipt_held_by_another_charge` in `chunk-i18n`. **The prompt's checks, driven:** (2) August Receipts without a charge reads "10 · 10 open", 10 table rows, one reason line each: 1 "No charge on the loaded statement matches this receipt.", 4 "Paid with a card whose statement is not loaded.", 4 "Dated at the edge of this statement; ...", 1 "Paid by debit card, cash or transfer, not on this card." (= the payload's 1 / 4 / 4 / 1); breakdown "Why: 1 no charge found · 4 card not loaded · 4 next or previous month · 1 not a card payment" adds to 10; the fold "11 copies set aside" with an outline "Show 11 copies" opens a table of 11 rows (= `n_copies_set_aside`). (3) July Charges without a receipt "72 · 24 open", breakdown "Why: 24 no receipt yet" over the 24 open rows; with the booked fold open, 72 rows: 47 "Marked yellow in your statement workbook, so already booked.", 24 "No receipt for this charge has arrived yet.", and GOOGLE *Workspace_bris 71.64 USD reads "The receipt found for this charge is paired with another charge." (4) PT on August: "Motivo: 1 sem transação · 4 cartão sem extrato · 4 mês vizinho · 1 não é cartão"; Charges without a receipt "Motivo: 98 sem recibo · 1 recibo em outra transação · 1 não é compra" (= 100 open). (5) 0 writes. No raw `wb.` key and no "undefined" in either view |
| `lovable-expense-boxes-prompt.md` (item 84) | Bundle 2026-09-17: `n_needs_company_or_person`, `expx.box.active`, `expx.box.tile.companyOrPerson`, `expx.box.fixCard.link` in `chunk-expenses._batchId`. **Driven on July Expenses:** clickable tiles EXPENSES 52, CATEGORIZED 49, NEEDS CATEGORY 3, READY 14, NO COMPANY OR PERSON 33 with "24 suggested private" inside it; MISSING ENTITY and NEEDS PERSON absent; MISSING RECEIPT IMAGE 0 is not a button. Each click, rows listed: CATEGORIZED "Showing 49: categorized" 49; clicking it again clears to 52; NEEDS CATEGORY "Showing 3: need a category" 3; READY 14; the merged tile "Showing 33: no company or person yet" 33 with "Add a card and its person once, and every receipt paid with it is fixed: Settings, Cards" linking `/settings`; the caption "Showing 24: suggested private" 24; EXPENSES clears to 52. PT: tile "SEM EMPRESA OU PESSOA 33 · 24 sugeridas como particulares", banner "Mostrando 33: sem empresa ou pessoa", 33 rows. **Residue, item 87's:** the fix-card line promises that defining a card fixes every row in the box, and on July it cannot fix 24 of the 33 (16 print only a tender word, 8 print no card at all) |
| `lovable-controls-as-buttons-prompt.md` (items 85 + 86) | Bundle 2026-09-17: `wb.decided.foldBooked.many`, `wb.decided.showBooked.many`, `wb.dup.showGroups.many`, `wb.fx.showDetails`, `wb.filter.card.showEmpty` in `chunk-runs._runId`. **Driven on July Matching:** (2) Charges without a receipt fold reads "48 rows marked yellow in July2026.xlsx, already booked"; the hover (label `span.cursor-help`) opens the tooltip "The workbook is the statement spreadsheet uploaded for this month. A row coloured yellow there is already booked; a grey row is a subscription. ..."; the toggle is an outline `h-7 px-2 text-xs` button "Show 48 booked rows" -> "Hide 48 booked rows". (3) **Not the predicted shape, correct by the prompt's own section 4:** Matched's fold reads "31 decided · Hide 31 decided rows", because 3 of its 31 rows are grey subscription rows (28 posted + 3 subscription on the payload), so the every-row-booked branch does not apply; note #51's "16 already posted" predates two re-matches. (4) duplicates panel "Copies set aside (2) · 3 kept apart" with the outline button "Show 5 groups" (August "Show 11 copies" / PT "Mostrar 11 grupos"). Also rendered: "Show 5 cards with nothing this month", 18 "Show FX details". (5) July Expenses: 24 "Confirm private expense" outline buttons, none underlined; a click opened the "Confirm private expense" dialog (Confirm / Close), closed with Escape, nothing saved. (6) No `button` or `a` under `main` carries `underline`, `hover:underline`, `underline-offset-*` or `decoration-dotted` on the Charges and Matched views. (7) PT on July: "48 linhas marcadas em amarelo em July2026.xlsx, já lançadas", "Mostrar 48 linhas lançadas", "Mostrar 5 grupos", 24 "Confirmar despesa particular". Seen, not this prompt's: a fresh session's first click on the Expenses page opens the "Leave feedback anywhere" hint dialog instead of the control |
| `lovable-memory-at-signoff-prompt.md` (item 88) | Bundle 2026-09-17: `toast.publishedSaved`, `toast.publishedMemoryFailed` in `chunk-runs._runId` (x2 each). Bundle-only by the prompt's own section 6: `/api/operator/state` `published_runs` is still empty, and publishing Criss's month is a memory write. Read the toast the first time a month is published |
| `lovable-card-fix-prompt.md` (item 87) | Bundle 2026-09-17: `card_source` in `chunk-expenses._batchId`; `expx.cardFix.pick`, `expx.cardFix.source.learned`, `expx.cardFix.boxHint` in `chunk-i18n`. **Driven on July Expenses (PT):** 33 selects read "Escolher o cartão que pagou", matching the 33 rows the API gives `card_source: none`; one opened to the nine registry cards and closed with Escape. Picking a card on Criss's month is a write, so the save path and the `override` / `learned` notes stay route-tested only |
| `lovable-matched-with-statement-prompt.md` (item 89) | Bundle 2026-09-17: `months.state.matchedStatement`, `months.state.matchedStatement.tip` in `chunk-i18n`. **Driven on `/months`:** July and August read "Matched with statement" (0 "Reconciled"), tooltip "A statement is loaded and its charges were matched against this month's receipts. Open the month to see what is still open."; PT "Comparado com o extrato" on both |
| `lovable-ecb-rates-prompt.md` (item 82) | Bundle 2026-09-17: `reference_rate_period` in `chunk-runs._runId`; `wb.fx.source.ecbMonth`, "ECB average, {month}", the new `set.fx.desc` EN + PT in `chunk-i18n`; old copy absent. **Driven:** Settings shows the new FX description in EN and PT; July's AMAZON FX panel still reads "1.162275 (USD per EUR) · Settings" / "· Configurações" (no regression). The ECB label itself has no live case, see Cannot verify |
| `lovable-settings-tabs-prompt.md` (item 91) | Bundle 2026-09-17 (43 chunks, 878 KB; controls `seen_undefined`, `merchants_inert`, `cc.title` hit): `set.tabs.advanced`, `set.tabs.unsaved`, `set.save.nothing`, `set.export.approvedOnly`, `set.export.scope` in `chunk-i18n` and `chunk-settings`; `export_approved_only` in `chunk-settings`. Save construction read: the mutation checks `applied` covers every patched key before the success toast (else `set.save.nothing`), writes the PUT response into the settings cache instead of re-fetching, panels `forceMount` + `hidden`, unknown `tab` falls back to `cards`; the intake save still spreads the loaded object (minus `senders`). Driven cold from the login gate in Chrome (`agent-browser --session tabs918`): `?tab=intake` lands on Email intake; seven triggers Cards 9 / Merchants 28 / Cost centers 0 / Legal entities 5 / Email intake 3 / FX reference rates 2 / Advanced, matching `GET /api/settings`; new subtitle rendered; Advanced shows Export policy (switch off, help + scope sentences) above Clear memory (button disabled); `?tab=nonsense` opens Cards. No Save pressed. Tab 6 reads "FX reference rates", the reused `set.fx.title` text, where the prompt's label column said "Currency"; the URL value is `currency` |
| `lovable-entity-order-prompt.md` (item 92) | Backend v146 first: `GET /api/settings` serves `entity_order: []`; differential probe with no write, `{"entity_order": "x"}` answers 400 "entity_order must be a list" while the control `{"entity_orderr": []}` answers "unknown settings key(s)", settings byte-identical before and after. Bundle 2026-09-17 (49 chunks, 1,063 KB; controls `seen_undefined`, `ready_to_post`, `n_duplicate_copies`, `set.tabs.advanced` hit): `set.entities.moveUp`/`moveDown`/`orderHint`/`orderSaved`/`rowEmpty`/`removeHint` in `chunk-i18n` and `chunk-settings`; the mutation sends `{entity_order: e}` alone, checks `applied` includes it, restores the previous order and shows `set.save.nothing` otherwise; the list seeds from `entity_options` then appends registry keys, no sort; no `.sort(` beside any `entity_options` read in any chunk. Driven cold from the login gate (headless Chrome, Playwright): 8 rows in `entity_options` order, including the three with no registry entry ("Nothing set yet"); 8 Move up / 8 Move down, first up and last down disabled; 8 draggable rows; clicking a row sets `aria-expanded=true` and opens its fields; `/expenses/51a22ad72864` entity dropdown lists the same 8 in the same order. Only non-GET request: `POST /api/login`. Limit: `entity_order` is empty, so today's order equals A-Z and the rendered order alone cannot tell payload order from a local sort; the bundle read carries that half until Criss saves an order |
| `lovable-entity-order-r2-prompt.md` (item 92 round 2) | Bundle 2026-09-17 night (49 chunks, 1,114 KB; controls `seen_undefined`, `ready_to_post`, `set.tabs.advanced`, `entity_order` hit): `set.entities.dragHandle` and `set.entities.dnd.instructions`/`picked`/`moved`/`dropped`/`cancelled` in `chunk-settings`; dnd-kit present (`DndDescribedBy`, `DndLiveRegion`); `set.entities.moveUp` and native `onDrop` absent from `chunk-settings`. **`entity_order` is now saved live by the operator** (Brisken Consulting, LLC / Consulting / Brisken Holding, LLC / Brisken Cloud Services, LLC / Brisken Corp Services, LLC / Brisken GmbH / Cloud Services / Corporate Services), which closes round 1's limit: the rendered order is that non-alphabetical list, so the page follows the payload, not A-Z. Driven cold from the login gate (headless Chrome, Playwright): hint reads "Click and hold a row"; 0 Move up/down buttons; 8 grip handles labelled "Reorder {name}" in `entity_options` order; screen-reader instructions in the DOM; row header is `div[role=button]` in a `cursor: grab` bar; a quick click opens then closes a row; press, hold 350 ms and move lifts it into a `shadow-lg` overlay; Escape returns it, order unchanged; pressing and moving at once does not lift. Only non-GET request: `POST /api/login`; `entity_order` identical before and after. Not driven: a real drop (a live write to the operator's order), touch, keyboard reorder |

These four were drafted 2026-08-28/29, pasted from chat, and lived only in a
gitignored scratch directory until 2026-09-01. They are in `docs/` now
because the pasted text is the record of what production was asked to do,
and a rollback would otherwise have nothing to re-apply.

## Not applied

| Prompt | Decisive field names | Gate |
|---|---|---|
| `lovable-feedback-0917-prompt.md` (notes #54-#60, item 78) | `card_ending`, `expx.reimburse.mark`, `expx.category.undo`, `wb.statement.loaded`, `set.merchants.howTo`, `set.entities.help.defaultPaidThrough`; ABSENCE of `set.export.approvedOnly` and `export_approved_only` in `chunk-settings` | Written 2026-09-17, not pasted. Section 6 reads `card_ending`, live with the notes-#54/#60 backend deploy |

The previous clean slate (2026-09-07) lasted one day; the backlog's habit
holds. Verify by field names, not display copy.

## Cannot verify (no live state exercises them)

| Prompt | Needs |
|---|---|
| `lovable-month-health-prompt.md`, the blocked bar itself | A month with `month_health.state: "broken"`. Both live months are `ok`, which is the correct state and not something to manufacture in Criss's data; the renderer's presence is bundle-audited |
| `lovable-charge-entity-prompt.md`, the "Card not defined" chip | A charge whose card the registry cannot name. All nine cards are defined, so `n_charges_no_entity` is 0 everywhere; same reasoning |
| `lovable-issue-codes-prompt.md` | A batch carrying `upload_issues`. All six live batches have zero |
| `lovable-rejected-pairing-prompt.md`, the muted candidate and the undo | A charge with a `rejected` verdict. All 223 charge rows across the two live months are `pending` (probed 2026-09-15): nobody has rejected anything, and manufacturing one in Criss's data is a production mutation, not a test |
| `lovable-re-ingest-prompt.md` | An archive with `batch_deleted: true` AND delivered files AND a non-terminal status |
| `lovable-month-pool-prompt.md` §7 §8 §9 | Creating, renaming and deleting a month. §8 refers to "the existing rename dialog": there is none, which is why prompt 1 builds it |
| `lovable-amounts-unreadable-prompt.md`, the line itself | An expense whose amount was never read. `n_amounts_unreadable` is 0 on both live months, which is the correct state and not something to manufacture in Criss's data; the report's caption and footer are route-tested on constructed fixtures |
| `lovable-month-move-prompt.md`, the move offer and its banner | A row whose reviewer-typed date falls outside its month's window. `n_month_moves` is 0 on July, August and every other batch since the owner-approved Parada move emptied January 2026; typing a wrong date into Criss's month to raise one is a production mutation |
| `lovable-ecb-rates-prompt.md`, the "ECB average, {month}" label | An FX candidate with `reference_rate_source: "ecb_month"`. July and August keep their frozen Settings rates, and the two Settings rates win for new months until backlog item 90 removes them; the first month matched on an ECB rate is the live case |

## Not a Lovable prompt

`api-contract.md` is the internal backend/SPA contract. It is never pasted
into Lovable; it is what the prompts are written against.

Item 69 round A (2026-09-15, duplicate groups by the document's number,
`duplicate_groups[].basis`): no SPA change is needed. The duplicates prompt
already renders every group and every row marker, a reference group renders
through the same shape, and `basis` is optional display. No prompt written.
