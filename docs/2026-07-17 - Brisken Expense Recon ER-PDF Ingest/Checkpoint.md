# Checkpoint: Brisken Expense Recon ER-PDF Ingest

**Date:** 2026-07-17
**Status:** SHIPPED + DEPLOYED — 4 PRs merged (#244, #245, #246, #248), all live-verified on brisken-expense-recon.fly.dev

---

## Summary

Built the Zoho Expense report-PDF receipts ingest end to end (the paste-ready prompt from the 07-16 prep session), then handled three rounds of live owner feedback in the same session: form-copy/source hints, the receipts-source dropdown, and — from Chris's in-app PT feedback — the replace-a-wrong-file feature on queued intakes.

---

## What Was Done This Session

### ER-PDF ingest (PR #244)
1. Fetched 5 real ER PDFs via Graph app-only creds (ER-00002, ER00009, ER-D-0016, ER-00101 multi-currency, ER-00139) — the fast path was an indexed `from/emailAddress/address eq 'no-reply@zohoexpense.com'` filter; subject-scanning Dirk's mailbox pages forever (22K+ messages before abandoning)
2. New `src/expense_recon/ingest/expense_report_pdf.py`: deterministic text-layer parser (pypdf) for the EXPENSE SUMMARY table — numbered/bare/bracketed row starts, per-diem rows with no merchant, FX-conversion lines (original ccy + rate + USD), multi-line merchant wraps, page-break noise; parsed per-currency sums cross-checked against the report's own printed Total Expense Amount to the cent
3. CLI routing: `receipts.source "expense_report_pdf"`, auto-inferred from a `.pdf` receipts path; NEVER routed through the OCR folder path (4-page cap + vision cost)
4. Web wiring: intake accepts `.pdf` receipts; `prepare_run` sniffs `.pdf` and force-routes regardless of the form dropdown; user form label + trilingual help copy (EN/DE/PT)
5. Real-data bug found + regression-tested: a page-break table-header line immediately after a row's last content line (no page-number marker) swallowed that row's amount
6. Verification: all 5 real PDFs parse 0-issues cent-exact; suite 531 green; calibrate exit 0 on Jun-25 Rome baseline; live local server e2e (both the sync /runs path and intake→operator-run) with real PDFs

### Owner feedback round 1 — operator form (PR #245)
7. `_run_form.html` still said "Receipts file (.csv)" (missed in #244 — B2 enumeration miss, user caught via screenshot); aligned accept + label, added where-to-get-this hints under both file inputs on both forms (EN + PT)

### Owner feedback round 2 — source dropdown (PR #246)
8. Added "Zoho Expense report PDF (the ER-... document)" to the receipts-source dropdown — ADDED alongside the CSV options per the owner's mid-turn correction ("or dont replace just add"), not replacing; reverse-mismatch guard (PDF source picked, non-.pdf uploaded → friendly form error)

### Chris's in-app feedback (PT) — checked + shipped (PR #248)
9. Pulled `/feedback.jsonl` from the live origin: 2 real PT notes from 2026-07-16 16:04 UTC
10. Note 1 ("tem que ter opcao para tirar o arquivo que foi colocado errado") → BUILT: `POST /intakes/{id}/files` + `replace_intake_files` service + `update_intake_files` store method + per-row "Enviou o arquivo errado? Substitua aqui." expander on the user home (received-status only; old file deleted from disk; statement swap refreshes detect-note; EN+PT)
11. Note 2 ("precisa ser baixado a foto do recibo para ser usada") → predates the ER-PDF deploy by ~100 min; most plausibly answered by it — pending confirmation on her next real upload

### Deploys (4, each explicitly ordered / under the session's named order)
12. Fly deploys after #244, #245, #246, #248 — each live-verified with an authenticated session against the deployed origin (operator + user roles, new copy/options/endpoint probed)

---

## Key Decisions Made

### detected_total carries the ORIGINAL currency
- **Choice:** `detected_total`/`detected_currency` = original-currency amount; `base_amount`/`exchange_rate` = the report's own USD conversion
- **Rationale:** matches the by-month OCR ground-truth convention (ER-00194's EUR line items) so the matcher's FX path sees the same shapes

### .pdf sniff overrides the form dropdown
- **Choice:** `prepare_run` force-sets `expense_report_pdf` on any `.pdf` receipts upload
- **Rationale:** the operator can never mis-run Chris's PDF by forgetting a dropdown; the dropdown only matters for CSVs

### No scanned-PDF vision fallback
- **Choice:** a text-layer-less report PDF raises a clean actionable error
- **Rationale:** per the prep prompt — a silent vision fallback would burn cost on a table that should be machine-readable, and a scan is a signal something is wrong upstream

### Replace only while `received`
- **Choice:** intake file replace is blocked once the intake leaves `received`
- **Rationale:** after a run exists the files are that run's provenance; swapping under it would desync the published result

### Missing-receipt flag scoped out
- **Choice:** skipped (noted in PR #244 body)
- **Rationale:** the EXPENSE SUMMARY table carries no per-row receipt-attached marker; detecting picture-presence per section is not cheap/deterministic

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/expense_report_pdf.py` | Created | The ER-PDF parser (#244) |
| `.../src/expense_recon/cli.py` | Modified | `expense_report_pdf` source routing + inference (#244) |
| `.../src/expense_recon/web/service.py` | Modified | `.pdf` intake accept + sniff (#244), mismatch guard (#246), `replace_intake_files` (#248) |
| `.../src/expense_recon/web/store.py` | Modified | `update_intake_files` partial update (#248) |
| `.../src/expense_recon/web/app.py` | Modified | `POST /intakes/{id}/files` endpoint (#248) |
| `.../src/expense_recon/web/templates/home_user.html` | Modified | .pdf accept + labels + source hints (#244/#245), swap expander (#248) |
| `.../src/expense_recon/web/templates/_run_form.html` | Modified | operator form .pdf accept + hints (#245), dropdown option (#246) |
| `.../src/expense_recon/web/templates/base.html` | Modified | PT i18n keys (uh_rcpt, hints, uh_swap_*) |
| `.../src/expense_recon/web/templates/help.html` | Modified | trilingual receipts copy (#244) |
| `.../tests/test_expense_report_pdf.py` | Created | parser unit + routing tests (#244) |
| `.../tests/test_web_expense_report_pdf_upload.py` | Created | web sniff/upload e2e + dropdown/guard tests (#244/#246) |
| `.../tests/test_web_intake.py` | Modified | .pdf intake accept/reject (#244) + 8 replace-flow tests (#248) |
| `.../BLUEPRINT.md` | Modified | Slice-7 lighter-weight partial: report-PDF ingest shipped (#244) |
| `workspace/clients/brisken/context/er-pdf-ingest-prompt.md` | Deleted | consumed build prompt (per its own instruction) |
| `workspace/clients/brisken/context/expense-reconciliation/expense-reports/dirk__ER-*.pdf` (x5) | Created (gitignored) | real ER reference samples fetched via Graph |
| `memory/project_brisken_expense_recon_review_surface.md` + `MEMORY.md` | Modified | ER-PDF ingest + replace feature recorded |

---

## Current Status

All four PRs squash-merged to main (#244 `eed2a27`, #245 `beb2463`, #246 `bca085a`, #248 `38735b9`) and deployed; every deploy live-verified with authenticated sessions. Module suite 541 passed / 2 skipped (pre-existing fastapi-less skips). Chris can now upload the report PDF she natively has, see where each file comes from, pick the PDF source explicitly, and swap a wrongly-uploaded file on a queued intake.

App: `brisken-expense-recon.fly.dev` (FastAPI on Fly, region fra, gated; codes in vault "Expense Recon App"). Not a Make/n8n client — no ops-limit check applicable.

---

## Next Steps

1. Confirm with Chris on her next real upload that the report-PDF flow answers her feedback note 2 ("precisa ser baixado a foto do recibo") — if not, scope what "use the receipt photo" means to her (likely 8.4 hosting surfacing in the workbench)
2. Watch `/feedback.jsonl` for new notes after she touches the new flow (operator session → `https://brisken-expense-recon.fly.dev/feedback.jsonl`)
3. Pending from the module backlog: cards.json authoring (separate item, deliberately not folded in), Exchange Application Access Policy for the Graph credential (compensating hard-allowlist still in force)
4. CI still does not run the expense-recon pytest suite — local gates remain the real gates (open shared-workflow decision)

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/expense_report_pdf.py` (the parser + its docstring = the format spec)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (intake/replace/sniff wiring)
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` (Slice-7 note)

### Open Questions
- Does the ER-PDF flow satisfy Chris's feedback note 2, or does she need receipt IMAGES surfaced in the workbench (8.4 hosting exists but isn't wired into the web view)?
- Should the recon module get its own CI job (suite is local-only today)?

### Working Notes
- **Graph mailbox scans:** Dirk's mailbox is huge; combined `$filter` clauses (from + receivedDateTime) 504; the reliable fast pattern is a single indexed `from/emailAddress/address eq '...'` filter. Zoho sends from `no-reply@zohoexpense.com`. Matthias's mailbox has zero Zoho mail.
- **Real ER PDF layout quirks the parser handles:** category header recognized ONLY between rows (mid-row page breaks land a repeated table-header line directly after content — the 2026-07-16 bug); `Includes Tax €X,XX` and `Non Reimbursable` are markers, not amounts; EU decimal-comma amounts on EUR lines, dual-column `$X $X` on USD lines.
- **Live verification pattern for this app:** no-cookie fetch 303s to `/login`; POST `/login` with a vault code, then fetch with the cookie jar. curl on Git Bash needs Windows-native file paths for `-F` uploads (`/tmp` fails with error 26).
- **The five real PDFs** stay in the gitignored `context/expense-reconciliation/expense-reports/` (prefix `dirk__`) as reference samples; their extracted `.txt` dumps were deleted (W1).

### Reference Materials
- PRs: [#244](https://github.com/011matthias/agentic-ops1.01/pull/244) ingest, [#245](https://github.com/011matthias/agentic-ops1.01/pull/245) form hints, [#246](https://github.com/011matthias/agentic-ops1.01/pull/246) dropdown, [#248](https://github.com/011matthias/agentic-ops1.01/pull/248) intake replace
- Live app: https://brisken-expense-recon.fly.dev (vault: "Expense Recon App")
- Ground truth: `workspace/clients/brisken/context/expense-reconciliation/expense-reports/csv/by-month/` (6 known reports)

---

## How to Continue

`/resume brisken`, then work from the recon worktree `C:/Users/neuma_p1qrsic/Repo/agentic-ops1-recon` (currently detached at merged main; branch fresh off `origin/main` for new work). Run the suite with `uv run --directory <module> --extra dev --extra web pytest -q`; `expense-recon calibrate` on a by-month `run.json` is the regression gate. Deploys are gated: `flyctl deploy <module> -c <module>/fly.toml` only on explicit order, then live-verify with an authenticated session.

---

## Strategic Feedback

### What Worked Well This Session
- Screenshot-driven feedback was extremely efficient: two owner screenshots (operator form, dropdown) each turned into a shipped PR within minutes, and the mid-turn correction ("or dont replace just add") was absorbed without a wasted cycle.
- The in-app feedback widget proved its worth on its first real use: Chris's two PT notes arrived with page/section anchors, and one became a shipped feature the next day.

### Suggestions
- The four ship-cycles (branch → PR → CI watch → merge → deploy → live-verify) were identical mechanical sequences; a `tools/recon-ship.sh` that chains them for this module would cut each round from ~10 minutes to ~3.

### System Health
- The B2 batch-manifest discipline failed once here (receipts inputs existed in TWO templates; only one was updated in #244). A cheap structural catch: when a PR touches a form `accept=` attribute, grep all templates for the same input name before shipping.
- Autonomy score: 2 human interventions this session (screenshot correction on the missed operator form; replace-vs-add dropdown correction).
