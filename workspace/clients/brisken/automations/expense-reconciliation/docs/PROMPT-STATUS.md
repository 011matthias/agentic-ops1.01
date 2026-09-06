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

These four were drafted 2026-08-28/29, pasted from chat, and lived only in a
gitignored scratch directory until 2026-09-01. They are in `docs/` now
because the pasted text is the record of what production was asked to do,
and a rollback would otherwise have nothing to re-apply.

## Not applied

| Prompt | Decisive field names | Gate |
|---|---|---|
| `lovable-r1-person-private-prompt.md` | settings chunk reads AND writes `person`; grid chunk reads `suggested_private`, `reimburse_to_prefill`, `n_needs_person`, `spellings` | R1 backend deployed 2026-09-06. **Person data entry waits for this prompt's verification** (cards map is whole-map replace; a stale save erases stored persons). Supersedes the client-side grouping half of `lovable-card-strip-prompt.md` |
| `lovable-months-origin-refusals-prompt.md` | `created_by` on the batches list; `n_refused_ours` + `n_probes` + `refusals[].kind_label` on the inbound log | R2 (#683 merged, #687) deploys with the staged flip |
| `lovable-trips-prompt.md` (R3, 2026-09-06) | `trip_id`, `batch_type`, `pool_kind`, `trip_suggestion`, `n_pooled_travel`, `travel_alias` | §5 (Settings travel-alias field) GATES alias entry: the intake object is whole-object-replace, and a stale SPA save would erase the alias. Do not set the alias through the SPA before §5 is verified in the bundle |

The clean slate lasted from the 2026-09-06 audit until R1 shipped the same
day; the backlog's habit holds. Verify by the field names above, not
display copy.

## Cannot verify (no live state exercises them)

| Prompt | Needs |
|---|---|
| `lovable-issue-codes-prompt.md` | A batch carrying `upload_issues`. All six live batches have zero |
| `lovable-re-ingest-prompt.md` | An archive with `batch_deleted: true` AND delivered files AND a non-terminal status |
| `lovable-month-pool-prompt.md` §7 §8 §9 | Creating, renaming and deleting a month. §8 refers to "the existing rename dialog": there is none, which is why prompt 1 builds it |

## Not a Lovable prompt

`api-contract.md` is the internal backend/SPA contract. It is never pasted
into Lovable; it is what the prompts are written against.
