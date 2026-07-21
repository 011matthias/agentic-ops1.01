---
project: brisken
workstream: p1-expense-reconciliation
group: ""
spec: p1
state: active
updated: 2026-07-20
---

# Brisken / Expense Reconciliation (p1)

AI-assisted expense reconciliation tool for Brisken: turn Criss's multi-day
reconciliation grind into minutes of review, with a 1:1 Zoho journal export.
(Key user is Criss = Cristiane Cavalcanti, she/her, cristiane.cavalcanti@brisken.com;
NOT "Chris".)
Scope is the "working tool" (single-tenant, Brisken-only) per Dirk's directive;
the multi-tenant SaaS in spec v2 is deferred. Per-slice authority is
`automations/expense-reconciliation/BLUEPRINT.md` + `ANNEALING.md`; this is the
roll-up.

The tool is hosted and running on real data at brisken-expense-recon.fly.dev.
As of 2026-07-20 there is a SINGLE page, the operator/dev surface, gated by one
code `mn040307` in `EXPENSE_RECON_OPERATOR_CODE`; the separate user page was
removed (owner directive: all operations run from the operator view) by unsetting
`EXPENSE_RECON_ACCESS_CODE` on Fly. Criss, Dirk and Matthias all log in with
`mn040307` (verified live: 303 in, old codes 401). Verify the deployed origin,
not localhost, after UI edits (`flyctl deploy`).

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
| Cross-run memory (Phase 2) | in-progress | BLUEPRINT Phase 2; now consulted for receiptless charges too (Slice 10) |
| Review workbench (web, Fly-hosted) | live | BLUEPRINT; brisken-expense-recon.fly.dev |
| Zoho journal CSV export | in-progress | BLUEPRINT slice 4; receiptless-LEARNED charges postable behind `zoho.export_receiptless_learned` (Slice 10) |
| Receiptless-charge categorization + subscription status (Tier 2) | done (PR #287, merged) | BLUEPRINT Slice 10/11; `categorize_charges.py` |
| Run history + doctor pre-flight | done | BLUEPRINT slice 5/5b |
| COA pre-write validation gate | live (Fly, per-entity) | BLUEPRINT 4.11 (PR #202/#203/#205) |
| Export idempotency (4.8) | not-started | BLUEPRINT Phase 5 (gap) |
| Match ground-truth labeling (`label propose/accept/check`) | done | `labeling.py`; optimize-loop prep — labels per month-bundle in gitignored context |
| Label fixture: 6 production-shape bundles (CSV stmt + ER PDF) | done (2026-07-17) | `context/.../csv/by-month/`: labels.csv per month, `label check` OK on all 6; 141/218 labeled (95 confirmed / 46 no_charge), 77 excluded as ambiguous; decisions corroborated offline via 2026 stmt-PDF FX originals + payment-mode card refs |
| ER-PDF ingest hardening (ISO-ccy amounts, inline rows, per-token format) | done (PR #263) | `expense_report_pdf.py`; all 6 real ERs parse to-the-cent vs printed totals |
| SPA JSON API surface (Lovable React frontend) | live | memory `project_brisken_expense_recon_lovable_frontend`; PRs #290/#291/#293 deployed — `/api/login`+bearer+CORS, `GET /api/runs/{id}` (workbench), `POST /api/runs` (run kickoff). Login+dashboard built in Lovable + works; workbench+upload prompts handed. Next: cutover (co-host bundle on Fly, retire Jinja) after screens validated |

## Open decisions / gates

- COA gate DEPLOYED 2026-07-01: `coa-provision.json` + `zoho-books-coa.json` on the Fly `/data`
  volume, `EXPENSE_RECON_COA_PROVISION` set, deployed (v10). Verified in-container on the real
  files: Corporate Services (822741658, 177 accts) + Cloud Services (697686691, 199 accts) resolve;
  a `(DO NOT USE)` account diverts. Remaining: authenticated end-to-end confirm with Chris on a real
  statement (the app is password-gated, so only a logged-in run exercises the full upload->review path).
- Login + link sent to Criss (PT) and Dirk (EN) on 2026-07-20 via Graph (verified in
  Sent Items). Next: Criss to test; Matthias to sit with her on a real month-end run.
  Joint working call not yet on the calendar.
- **Criss's first test run 2026-07-20 (run `b67133b8df98`) reconciled 0/94.** Root-caused
  on her exact files (retrieved from the Fly volume, run locally NO-LLM): (1) Chase
  activity CSV lists purchases negative (`Type=Sale`) → matcher rejects non-positive
  charges → 0 candidates (abs() → 34); (2) cross-currency BRL-vs-USD is LLM-gated unless
  the statement carries original foreign amounts (the activity CSV lacks them, the Chase
  statement PDF has them); (3) receiptless USD SaaS charges are never categorized. BLUEPRINT
  revised for all three (PR #284, merged; see its "Using-the-data revision (2026-07-20)").
  Two isolated build tiers queued as ready-to-paste prompts (plan file
  `glimmering-herding-glade.md`): **Tier 1** = sign-fix + PDF-first + deterministic FX
  (`ingest/*`+`matching/*`) — STILL PENDING; **Tier 2** = categorize every charge
  (`categorize*`+`output/*`) — **SHIPPED 2026-07-20 (PR #287, merged)**. Tier 2 verified
  no-LLM on Criss's April files: 6 Anthropic charges categorized LEARNED and posted to the
  real Books account (COGS - Other Infra and IT Costs for Cloud Business) through the COA
  gate; Adobe/OpenAI/GitHub VENDOR-tier review-only; 39 charges flagged subscription from
  statement history. Journal debits still carry the Chase-CSV negative sign until Tier 1's
  ingest sign-normalization lands (Tier 2 passes `tx.amount` through verbatim).
- **Notifier blind spot:** now that everyone uses the operator page, uploads create
  *unpublished runs*, which `/api/operator/state` (the dev-side notifier's source) does not
  report → no upload notification fires. Fix in Tier 1 or a follow-up (extend the state API),
  plus schedule `tools/brisken-recon-notify.py`. Standing test loop is retrieve-from-Fly +
  run-local NO-LLM (`calibrate`), memory `project_brisken_expense_recon_testing_loop`.
- Legal retention period to confirm (Dirk's guess ~7 yrs US, unconfirmed).
- No further client data coming: the ER PDFs + Chase export in hand are illustrative
  samples, not a reconciling dataset; build to sample shapes, validate accuracy in
  production (`project_brisken_no_further_data` memory).

## Pointers

- Spec: `specs/1-spec/p1-expense-reconciliation-functional-spec.md` (v2; SaaS scope deferred)
- Build authority: `automations/expense-reconciliation/BLUEPRINT.md`, `ANNEALING.md`
- Platform state: `infrastructure.yaml` (note: its judgment-layer "stubbed" line predates the OpenAI pivot)
