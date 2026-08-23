# Checkpoint: Brisken Recon Report Documents + Open Intake

**Date:** 2026-08-23
**Status:** p1 live on Fly v83; the 2026-08-21 feedback wave is closed, all owner questions answered

---

## Summary

Two owner directives landed and changed what the expense tool produces: there is no target application any more, so the month's output became two report documents (expenses, reconciliation) instead of a file for an importer, and the mail intake opened to any sender. Six PRs shipped, merged and deployed, each verified against production.

---

## What Was Done This Session

### The output became a document (backlog item 24)

1. **`GET /runs/{id}/expense-report.pdf`** (#584). The listing is built from the export's OWN rows via a shared `_expense_export_inputs`, so money cannot drift between the document and the CSV. Every receipt follows behind a caption naming the expense it proves. Evidence is per DOCUMENT rather than per row, so a receipt split across two accounts appears once, captioned "Expenses 3, 4". Renderability is decided before the caption is written, so a file that exists but cannot be paginated says so rather than leaving a caption with nothing behind it.
2. **Receipt-column fix** (#585). The live April report printed `p. 1`, `p. 2` in the Receipt column: row numbers formatted as page references. Now `attached` / `none`.
3. **`GET /runs/{id}/reconciliation-report.pdf`** (#586). Rendered from the workbench's own `build_view` payload, so a reader and a reviewer cannot be looking at different reconciliations. Exceptions first, then every charge with its receipt and status, then the pages. A clean month says "Nothing. Every charge has a receipt" instead of showing an empty section.

### Mail intake opened to any sender (#587)

4. Deleted the `@brisken.com` allowlist, the envelope/header agreement check, and the `intake.senders` setting. A stored `senders` key is dropped on save rather than rejected, so a dead key cannot 400 an edit to the live keys beside it. Kept: the recipient rule (mail must be addressed to the intake domain), the day budget, in-flight ceiling, disk floor, zip refusal, quarantine.
5. First handler-level test of `handle_DATA`. The deleted gate lived there and nothing had ever exercised it; the old tests only called the pure decision function.

### Carried over from the same working session

6. **Re-ingest for stranded mail** (#582) and its runbook (#583).

---

## Key Decisions Made

### The reconciliation output is a document, not a CSV

- **Choice:** same treatment as the expense report, with exceptions promoted above the listing.
- **Rationale:** the owner delegated the format ("we just need to think of what the best course of action is"). A reconciliation's product is evidence that a month is complete; a CSV carries the charge list and none of the proof, and nothing reads it now that there is no importer. Putting exceptions first means a reader who stops after page one has still seen everything that is wrong.

### Open the sender, keep the recipient closed

- **Choice:** delete the sender allowlist outright; leave the relay rule and the spend guards untouched.
- **Rationale:** From is forgeable, so the allowlist bought tidiness rather than security while bouncing every receipt that arrived by any route other than a Brisken mailbox. Opening the recipient side instead would have made the app a spam relay on Brisken's IP.

### The ack stays inside the tenant

- **Choice:** rely on `graph_notify`'s own `@brisken.com` recipient guard; outside submitters are ingested and never replied to.
- **Rationale:** the ack's recipient is now attacker-controlled. Without that guard the tool would mail confirmations to strangers as Brisken. The test enables the Graph sender before asserting the refusal, because with no creds in CI every send is already False and the test would have passed for the wrong reason.

### Name the new module `month_report_pdf`, not `expense_report_pdf`

- **Choice:** `output/month_report_pdf.py`.
- **Rationale:** `ingest/expense_report_pdf.py` already exists and is the input-side parser. The obvious name collided; the first attempt silently clobbered 598 lines of that parser's tests.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/output/month_report_pdf.py` | new | the month's expense report document |
| `src/expense_recon/output/reconciliation_report_pdf.py` | new | the statement reconciliation document |
| `src/expense_recon/output/_pdf_common.py` | new | shared fonts, styles, evidence preparation, stitching |
| `src/expense_recon/web/service.py` | edit | `_expense_export_inputs`, `build_expense_report`, `build_reconciliation_report` |
| `src/expense_recon/web/app.py` | edit | the two PDF routes |
| `src/expense_recon/web/intake_mail.py` | edit | allowlist deleted; ack docstring states what now guards it |
| `src/expense_recon/web/smtp_server.py` | edit | `sender_decision` deleted; docstring states the remaining boundaries |
| `tests/test_month_report_pdf.py`, `test_reconciliation_report_pdf.py` | new | 17 tests |
| `tests/test_intake_mail.py` | edit | 5 new tests incl. the first `handle_DATA` coverage |
| `docs/lovable-month-report-prompt.md`, `lovable-open-intake-prompt.md` | new | the SPA halves |
| `docs/lovable-mail-intake-prompt.md` | edit | the senders instruction marked superseded |
| `status/p1-expense-reconciliation.md`, `p1-improvement-backlog.md`, `p1-recon-loop-prompt.md` | edit | shipped rows, items 25/26, fresh-chat brief |
| memory `project_brisken_expense_recon_mail_intake.md` | edit | allowlist fact replaced |

---

## Current Status

Fly v83, healthz 200, nine runs intact, `processing: 0`. Both report endpoints were fetched from production and read: April 2026 = 74 pages with totals matching the CSV exactly; January = 39 pages, 80 charges, 0 matched, USD 20,228.68 unreconciled. The SMTP listener was probed at the wire post-deploy: an outside envelope sender is accepted and relay to `victim@gmail.com` still answers 550, with the connection dropped before DATA so nothing was delivered.

Suite 1190 passed / 2 skipped; calibrate gate OK (7/7, floor 57.1%).

brisken platform status: unknown plan, `~?/?` ops/mo, last assessed `?` — `infrastructure.yaml` has no platform section for a client that runs on FastAPI.

---

## Next Steps

1. **Backlog item 25 — the OCR year misread.** Line two of the live April report dates a 2026 receipt to 2023. Money-adjacent (it decides the month and whether a charge can ever match), undiagnosed, and it outranks every text item open.
2. Zoho layers 2 and 3 (item 23): rename `zoho_account` via a parallel field plus a Lovable prompt; give the chart gate a chart source that is not a Books export. Layer 4 is resolved — nothing imports the columns now, so `EXPENSE_COLUMNS` can be renamed on its own schedule.
3. Cards R4 leftovers (item 10): persisted cards migration, intake dropdown unification.
4. The six p2 status files are 31-63 days stale. Untouched this session and no fresh information exists for them, so bumping the dates would be false currency; they need a lead-gen session.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` — rewritten this session as the fresh-chat brief
- `workspace/clients/brisken/status/p1-improvement-backlog.md` — the one list; items 25 and 26 are new
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- Is the 2023 date an extraction defect, a normalization defect, or a receipt that genuinely prints an old date? The backlog entry names the three cases and how to separate them.
- Does the SPA's Settings screen actually carry an "Accepted senders" editor? If it never got built, `lovable-open-intake-prompt.md` is a no-op.

### Working Notes
- Live reconciliation of January: 78 of 80 charges have no receipt at all. That is the data, not a bug, and it is worth the owner's attention.
- The card registry gap accounts for the live MISSING ENTITY count: four cards carry no entity and the 0340 card is absent entirely (8 rows). Nine more are generic tenders that by design never auto-resolve. Data entry, not code.
- PDF text extraction wraps table-cell text mid-phrase, so assertions on a rendered phrase need whitespace collapsed first (`_flat` helper in both report test modules).
- reportlab's built-in Helvetica is Latin-1 only and cannot render `Cartão` or `Gebühr`, which is exactly where this client's receipts live; `_pdf_common.register_fonts` finds DejaVu in the container and Arial on the dev box.
- An external test mail from a non-Brisken address is the one piece of the intake change not proven at the wire; it writes to the live system, so it waits on the owner simply mailing one in.

### Reference Materials
- `https://brisken-expense-recon.fly.dev` (machine `48ee133c363758`, fra, v83)
- `%TEMP%/claude/recon-probe/api.py` and `dom_probe.py` — read the live app without anyone's help
- PRs #582 through #587

---

## How to Continue

Open a fresh chat, paste `p1-recon-loop-prompt.md`, and start on backlog item 25. Work in the `agentic-ops1-recon` worktree, refreshed to `origin/main`, on a `client/brisken/...` branch cut before the first edit.

---

## Strategic Feedback

### What Worked Well This Session

- Regressing the real source to watch each new test go red caught two tests that would have passed for the wrong reason: the intake ack test (no Graph creds in CI means every send is already False) and, earlier, the report end-to-end test whose stub JPG hid an unrenderable-file bug.
- Reading the actual rendered PDF from production rather than trusting the deploy caught the `p. 1` receipt column within minutes of shipping it.

### Suggestions

- The `Write` tool clobbered an existing 598-line test module because the file had been read before a context compaction, which satisfied the tool's read-before-overwrite check. Only the suite count dropping from 1168 to 1153 exposed it. A pre-write existence check on new-file writes, or a suite-count assertion in the ship chain, would make that visible at the moment it happens rather than several steps later.

### System Health

- The friction register is at 359 KB and past its 200 KB archive threshold; archived in this checkpoint's docs PR.
- Autonomy: 2 human interventions (one output-format correction, one directive change). Not elevated.
