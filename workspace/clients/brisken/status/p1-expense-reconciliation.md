---
project: brisken
workstream: p1-expense-reconciliation
group: ""
spec: p1
state: active
updated: 2026-07-17
---

# Brisken / Expense Reconciliation (p1)

AI-assisted expense reconciliation tool for Brisken: turn Chris's multi-day
reconciliation grind into minutes of review, with a 1:1 Zoho journal export.
Scope is the "working tool" (single-tenant, Brisken-only) per Dirk's directive;
the multi-tenant SaaS in spec v2 is deferred. Per-slice authority is
`automations/expense-reconciliation/BLUEPRINT.md` + `ANNEALING.md`; this is the
roll-up.

The tool is hosted and running on real data at brisken-expense-recon.fly.dev
(gated by `EXPENSE_RECON_ACCESS_CODE`). Verify the deployed origin, not localhost,
after UI edits (`flyctl deploy`).

## Elements (index)

State at a glance only. Live slice-level status, next actions, and detail are in
`automations/expense-reconciliation/BLUEPRINT.md` + `ANNEALING.md` (the authority);
this table is the index, not a second record.

| Element | State | Tracked in |
|---|---|---|
| Statement ingest (CSV + XLSX) | done | BLUEPRINT (ingest) |
| Receipt OCR (vision + PDF text) | done | BLUEPRINT slice 2 |
| LLM categorizer (gpt-4o-mini, OpenAI Brisken key) | live | BLUEPRINT "Provider Pivot" |
| Deterministic matcher | done | BLUEPRINT slice 3 |
| Cross-run memory (Phase 2) | in-progress | BLUEPRINT Phase 2 |
| Review workbench (web, Fly-hosted) | live | BLUEPRINT; brisken-expense-recon.fly.dev |
| Zoho journal CSV export | in-progress | BLUEPRINT slice 4 |
| Run history + doctor pre-flight | done | BLUEPRINT slice 5/5b |
| COA pre-write validation gate | live (Fly, per-entity) | BLUEPRINT 4.11 (PR #202/#203/#205) |
| Export idempotency (4.8) | not-started | BLUEPRINT Phase 5 (gap) |
| Match ground-truth labeling (`label propose/accept/check`) | done | `labeling.py`; optimize-loop prep — labels per month-bundle in gitignored context |
| Label fixture: 6 production-shape bundles (CSV stmt + ER PDF) | done (2026-07-17) | `context/.../csv/by-month/`: labels.csv per month, `label check` OK on all 6; 141/218 labeled (95 confirmed / 46 no_charge), 77 excluded as ambiguous; decisions corroborated offline via 2026 stmt-PDF FX originals + payment-mode card refs |
| ER-PDF ingest hardening (ISO-ccy amounts, inline rows, per-token format) | done (PR #263) | `expense_report_pdf.py`; all 6 real ERs parse to-the-cent vs printed totals |

## Open decisions / gates

- COA gate DEPLOYED 2026-07-01: `coa-provision.json` + `zoho-books-coa.json` on the Fly `/data`
  volume, `EXPENSE_RECON_COA_PROVISION` set, deployed (v10). Verified in-container on the real
  files: Corporate Services (822741658, 177 accts) + Cloud Services (697686691, 199 accts) resolve;
  a `(DO NOT USE)` account diverts. Remaining: authenticated end-to-end confirm with Chris on a real
  statement (the app is password-gated, so only a logged-in run exercises the full upload->review path).
- Joint call with Chris (Brisken finance manager) not yet scheduled (Dirk to brief her).
- Legal retention period to confirm (Dirk's guess ~7 yrs US, unconfirmed).
- No further client data coming: the ER PDFs + Chase export in hand are illustrative
  samples, not a reconciling dataset; build to sample shapes, validate accuracy in
  production (`project_brisken_no_further_data` memory).

## Pointers

- Spec: `specs/1-spec/p1-expense-reconciliation-functional-spec.md` (v2; SaaS scope deferred)
- Build authority: `automations/expense-reconciliation/BLUEPRINT.md`, `ANNEALING.md`
- Platform state: `infrastructure.yaml` (note: its judgment-layer "stubbed" line predates the OpenAI pivot)
