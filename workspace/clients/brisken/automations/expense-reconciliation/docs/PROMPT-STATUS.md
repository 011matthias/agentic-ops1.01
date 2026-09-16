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

These four were drafted 2026-08-28/29, pasted from chat, and lived only in a
gitignored scratch directory until 2026-09-01. They are in `docs/` now
because the pasted text is the record of what production was asked to do,
and a rollback would otherwise have nothing to re-apply.

## Not applied

| Prompt | Decisive field names | Gate |
|---|---|---|
| `lovable-date-gap-prompt.md` (2026-09-16, item 80: a one-day gap is not a date mismatch; the chosen candidate's `date_gap_zone` decides the "date mismatch" warning, `lag` becomes a neutral chip outside the Warnings filter) | `date_gap_zone`, `wb.dateGap.chargedAfter`, `wb.dateGap.receiptAfter` present in `chunk-runs._runId` / `chunk-i18n` | Backend live first (Fly, `date_gap_zone` on July's candidates). Browser-drive July: no row says "date mismatch"; "Warnings only" 27 -> 23 on the 2026-09-16 payload |
| `lovable-fx-reference-prompt.md` (2026-09-16, item 81: the FX block shows the receipt converted at the tool's own rate) | `reference_gap_band` + `reference_rate_source` read in `chunk-runs._runId`; `wb.fx.referenceRate`, `wb.fx.receiptIn`, `wb.fx.source.settings` in the i18n chunk | Backend fields deployed first (item 81 PR). Browser-drive the five checks at the end of the prompt |
| `lovable-row-type-prompt.md` (2026-09-16, item 73: a statement row says what it is; a "Card payment" / "Card fee" chip beside the company chip, the company chip says whether it came from the card or the upload, the credits label) | `row_type`, `entity_source` read in `chunk-runs._runId`; `wb.rowType.payment`, `wb.entity.fromUpload`, `wb.credits.tip` in the i18n chunk | Backend live first (Fly, `row_type` on July's rows). Browser-drive July: "Payment Thank You-Mobile" carries "Card payment" and its company tooltip names card 2838; August's "ANNUAL MEMBERSHIP FEE" carries "Card fee"; no purchase row carries a type chip |
| `lovable-month-move-prompt.md` (2026-09-16, item 77: a row whose typed date belongs to another month offers "Move to {month}", one POST moves it; `time` beside the date) | `month_move`, `n_month_moves`, `/move`, `expx.review.monthMove` | Backend deployed with item 77. Paste AFTER `lovable-month-views-prompt.md` if both are still pending: the offer attaches to the date cell of an Expenses-view row. Live case: January 2026 (`4ceaeb461386`) carries one offer until the owner-approved move runs |
| `lovable-duplicates-decided-prompt.md` (2026-09-16, item 74: duplicates mean one thing each; the Matching view's duplicates panel becomes a collapsed record "Copies set aside ({n})" with the reason each group was decided and one undo button, no "Possible duplicates" title or advisory sentence, copy-row undo reads "Not a copy") | `n_duplicate_groups_open`, `decided_by` read in `chunk-runs._runId`; `wb.dups.setAside.title`, `wb.dups.basis.printed_reference`, `wb.dups.notCopy` in the i18n chunk | Backend live first (Fly, `state` / `verdict` on July's `duplicate_groups`, `n_duplicate_groups_open` 0 on both months). Browser-drive the five checks at the end of the prompt; re-read the payloads first, the July count moves with the Google ruling |

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

## Not a Lovable prompt

`api-contract.md` is the internal backend/SPA contract. It is never pasted
into Lovable; it is what the prompts are written against.

Item 69 round A (2026-09-15, duplicate groups by the document's number,
`duplicate_groups[].basis`): no SPA change is needed. The duplicates prompt
already renders every group and every row marker, a reference group renders
through the same shape, and `basis` is optional display. No prompt written.
