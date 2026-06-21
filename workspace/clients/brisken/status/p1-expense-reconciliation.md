---
project: brisken
workstream: p1-expense-reconciliation
group: ""
spec: p1
state: active
updated: 2026-06-20
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

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Statement ingest (CSV + XLSX) | done | Parsers shipped; tests green | none | none | `automations/expense-reconciliation/src/ingest/` |
| Receipt OCR (vision + PDF text) | done | Folder ingest + live OCR calibration done | none | none | BLUEPRINT slice 2 |
| LLM categorizer (gpt-4o-mini) | live | Runs on the "OpenAI Brisken" key; degrades gracefully when key absent | Confirm rotated key with Dirk | none | BLUEPRINT "Provider Pivot"; `project_brisken_openai_key` memory |
| Deterministic matcher | done | Card-scoped + exact-FX precision; 32 tests green | none | none | `src/matching/`; BLUEPRINT slice 3 |
| Cross-run memory (Phase 2) | in-progress | Store + capture + consult + CLI + in-browser view built | Land remaining Phase 2 slices | none | BLUEPRINT Phase 2 |
| Review workbench (web) | live | Triage, manual match, match transparency, run progress, compare | none | none | brisken-expense-recon.fly.dev |
| Zoho journal CSV export | in-progress | Download from the workbench shipped | Full Zoho Books API replication | Zoho API access / file-export confirm | BLUEPRINT slice 4 |
| Run history + doctor pre-flight | done | SQLite run-log, history/diff, slice 5.14 doctor | none | none | BLUEPRINT slice 5/5b |
| COA pre-write gate + export idempotency (Phase 5) | not-started | Gap | Build pre-write chart-of-accounts gate | none | `project_brisken_expense_recon_review_surface` memory |

## Open decisions / gates

- Joint call with Chris (Brisken finance manager) not yet scheduled (Dirk to brief her).
- Legal retention period to confirm (Dirk's guess ~7 yrs US, unconfirmed).
- No further client data coming: the ER PDFs + Chase export in hand are illustrative
  samples, not a reconciling dataset; build to sample shapes, validate accuracy in
  production (`project_brisken_no_further_data` memory).

## Pointers

- Spec: `specs/1-spec/p1-expense-reconciliation-functional-spec.md` (v2; SaaS scope deferred)
- Build authority: `automations/expense-reconciliation/BLUEPRINT.md`, `ANNEALING.md`
- Platform state: `infrastructure.yaml` (note: its judgment-layer "stubbed" line predates the OpenAI pivot)
