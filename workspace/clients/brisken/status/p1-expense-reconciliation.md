---
project: brisken
workstream: p1-expense-reconciliation
group: ""
spec: p1
state: active
updated: 2026-07-01
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
| COA pre-write validation gate | built, pending Fly deploy | BLUEPRINT 4.11 (PR #202/#203) |
| Export idempotency (4.8) | not-started | BLUEPRINT Phase 5 (gap) |

## Open decisions / gates

- COA gate go-live (deploy step, gated floor): upload `context/coa-provision.json` +
  `zoho-books-coa.json` to the Fly `/data` volume, set `EXPENSE_RECON_COA_PROVISION=/data/coa-provision.json`,
  then `flyctl deploy`. Until then the gate is inert on the hosted app (env unset => no-op).
  Target entities Corporate Services (822741658) + Cloud Services (697686691); scope_groups in BLUEPRINT 4.11.
- Joint call with Chris (Brisken finance manager) not yet scheduled (Dirk to brief her).
- Legal retention period to confirm (Dirk's guess ~7 yrs US, unconfirmed).
- No further client data coming: the ER PDFs + Chase export in hand are illustrative
  samples, not a reconciling dataset; build to sample shapes, validate accuracy in
  production (`project_brisken_no_further_data` memory).

## Pointers

- Spec: `specs/1-spec/p1-expense-reconciliation-functional-spec.md` (v2; SaaS scope deferred)
- Build authority: `automations/expense-reconciliation/BLUEPRINT.md`, `ANNEALING.md`
- Platform state: `infrastructure.yaml` (note: its judgment-layer "stubbed" line predates the OpenAI pivot)
