# Lovable prompt status: what is applied to the published SPA

**Audited 2026-08-24 against `brisken-reconcile-dash.lovable.app`** by
driving the app, not by reading this repo. Re-run the audit and update this
file whenever the owner publishes; a prompt's presence in `docs/` says
nothing about whether it was ever pasted.

The audit script is `%TEMP%/claude/recon-probe/prompt_ledger.py`. Signatures
are VERBATIM strings from each prompt.

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

## Not applied

These three are the whole paste list. Each was **rewritten 2026-08-24** to
open with a measured inventory of what the published app already has, so
Lovable adds the delta instead of rebuilding working screens. They touch
different screens and are independent; the numbering is a suggested order,
not a dependency.

| Prompt | What is missing |
|---|---|
| **1. `lovable-months-list-prompt.md`** | **The blocker.** `/months` renders only the create form: 0 tables, 0 rows, no batch label in the HTML. The page calls `GET /api/expense-batches`, gets 200 with six batches, and discards them. No way into an existing month except the intake page's Month links or a hand-typed `/expenses/{id}`. Also carries Rename (no rename dialog exists anywhere today) and Delete month, homeless since `lovable-intake-quickwins-prompt.md` §3 |
| **2. `lovable-known-senders-prompt.md`** | Settings > Email intake. Deletes the dead "Accepted senders" editor (live, and it silently discards what an operator types: backlog item 31), rewords three help lines that still say "the open month", and adds the `intake.known_senders` field. Opens with the exact live inventory of that section so nothing else in it is lost. `lovable-open-intake-prompt.md` was folded in and deleted |
| **3. `lovable-inbound-status-refusals-prompt.md`** | The Email intake page. Renders the Status cell from `status_kind` / `status_label` instead of a local map (the durability fix: the next status value added mislabels again without it), and adds the refusals strip. **Supersedes `lovable-month-pool-prompt.md` §0 and §12**, which have been removed from that file so it cannot be double-pasted |

## Cannot verify (no live state exercises them)

| Prompt | Needs |
|---|---|
| `lovable-issue-codes-prompt.md` | A batch carrying `upload_issues`. All six live batches have zero |
| `lovable-re-ingest-prompt.md` | An archive with `batch_deleted: true` AND delivered files AND a non-terminal status |
| `lovable-month-pool-prompt.md` §7 §8 §9 | Creating, renaming and deleting a month. §8 refers to "the existing rename dialog": there is none, which is why prompt 1 builds it |

## Not a Lovable prompt

`api-contract.md` is the internal backend/SPA contract. It is never pasted
into Lovable; it is what the prompts are written against.
