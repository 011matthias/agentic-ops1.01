# Checkpoint: Brisken Receipt-First Expense Engine Live

**Date:** 2026-07-28
**Status:** Engine + lifecycle merged (PRs #460, #461, #462), deployed to Fly with `EXPENSE_RECON_RECEIPT_FIRST=1`, live-verified end to end; Lovable month-lifecycle UI published by owner.

---

## Summary

Built and shipped the receipt-first "generate expenses" engine for Brisken expense-recon (Dirk's note #1, "the flow is backwards"): web layer, definable entities, learning, and the batch LIFECYCLE (receipts gradually all month, statement + card id only at month end, graduation into the normal workbench on the same run). Deployed with the flag on; live verification caught and fixed a real Decimal-serialization bug; the full month loop is verified against the deployed origin.

---

## What Was Done This Session

### Engine (branch `client/brisken/expense-recon-receipt-first`, worktree `agentic-ops1-rcpt1st`)

1. **Phase 4 — web layer** (PR #460): `expense_field_overrides` + `expense_edits` tables; `POST/GET /api/expense-batches` (decoupled upload → background OCR job); receipt-spine `build_expense_view` (ready/check/pick review vocabulary reused); `PUT {field,value}` edits (category folds into `category_overrides`, merge not clobber), manual add, soft delete, per-expense entity; `GET /runs/{id}/expenses.csv` with the view's exact overlay order; mode dispatch on `GET /api/runs/{id}`; everything 404s while the flag is unset.
2. **Phase 5 — categories + entities** (PR #460): categories fixed-8 read-only in settings; `settings.entities` registry (org_id / chart_path / scope_groups / default_paid_through / account_picks) wins over the /data provisioning file (`coa_validation_from_settings`, fail-open); curated `account_options`; entity default Paid Through folds into batch config.
3. **Phase 6 — learning** (PR #460): `merchant_entity` + `field_correction` tables; ONLY explicit edits teach (entity overrides under BOTH vendor spellings, vendor/tax_label/paid_through corrections keyed on the ORIGINAL extracted vendor, category reclassifications via shared `_learn_categories`); `ExpenseMemory.apply` consulted in `generate_expenses` only, never `reconcile`; grid-visible provenance; `/api/memory` + forget/reset cover the new tables.
4. **Phase 4b — batch lifecycle** (PR #461, owner directive 2026-07-28): `POST /api/expense-batches/{id}/receipts` (incremental adds, sha1 dedup, background OCR + memory + categorization); `POST /api/expense-batches/{id}/statement` (graduation — the FIRST place card/account id is asked; sync column-map fail-fast with headers re-prompt; reviewer edits BAKED into the pool; `_load_statement` → `match_month` → judgment passes → `categorize_charges`, `reconcile()` untouched); graduated run serves the normal workbench; expense overlay frozen post-attach; `entity_mismatch` warns loudly.
5. **Live-caught fix** (PR #462): `CostTracker.total_cost_usd` (Decimal) fed into `json.dumps` killed the add-receipts save — same latent bug in the 07-27 folder ingest; `float()` both call sites + 2 regression tests with a real-shaped Decimal tracker.

### Deploy + verification

1. Two Fly deploys from the detached `agentic-ops1-deploy` worktree at origin/main (account matneumann07), flag staged into the first release.
2. Full live loop verified via `verify_lifecycle.py` (scratchpad): healthz → operator login → flag ON → batch create + real-LLM OCR → incremental add (cost 0.0014 recorded as float) → statement attach → workbench 5 charges `invariant_ok` → both CSV exports 200 → post-attach freeze 400 → test batch deleted (nothing left for Criss). Stale batch from the failed first run also deleted.

### SPA (Lovable, owner-driven)

1. Read the live feedback log: six older notes all map to shipped features; two NEW notes (2026-07-27, run f639bef7813a) → prompts handed (rejected-row actions + reopen/manual-match; filter/sort toolbar).
2. Four Lovable prompts handed total: receipt-first screens, compact upload-folder button, feedback fixes, and the month-lifecycle restructure (months list primary, "Start a new month" without statement/card, attach dialog at month end, classic form secondary). Owner reports Lovable done + published.

### Bookkeeping

1. Status row in `p1-expense-reconciliation.md` (shipped via #460, updated to LIVE in this checkpoint's sibling PR), project memory rewritten to final state, MEMORY.md compacted below the 17.1 KB limit on hook advisory, plan file extended with the Phase 4b design (pre-compaction pin).

---

## Key Decisions Made

### Graduation on the SAME run row

- **Choice:** Attaching a statement mutates the batch run (snapshot gains transactions/outcome; mode marker stays; workbench dispatch keys on `has_statement`) instead of creating a linked second run.
- **Rationale:** Every statement-mode surface (decisions, confirm-ready, exports) works unchanged with zero duplication; `reconcile()` stays byte-for-byte untouched — the graduation reuses the same module-level primitives the folder-ingest already sanctioned.

### Post-attach freeze + baked overlays

- **Choice:** Reviewer edits are baked into the snapshot receipts at attach time; the expense-edit overlay then returns 400 ("review in the workbench"); edit rows are KEPT (they still feed learning) with an add-guard making re-application idempotent.
- **Rationale:** The pool becomes the reconciliation's provenance; a post-attach vendor edit would silently never reach the journal export otherwise.

### Learning teaches only explicit edits, keyed for next month's OCR

- **Choice:** Batch default entity never teaches; entity overrides teach under both original and corrected vendor spellings; field corrections key on the ORIGINAL extracted vendor.
- **Rationale:** Next month's OCR reproduces the original spelling — a mapping keyed only on the corrected name would never hit.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/web/store.py` | edit | expense edit tables, settings entities default, summary/config update methods |
| `src/expense_recon/web/service.py` | edit | batch create/execute, views, exports, lifecycle (add + attach), Decimal fix |
| `src/expense_recon/web/app.py` | edit | all expense-batch + lifecycle endpoints, dispatch, freeze guard |
| `src/expense_recon/cli.py` | edit | `generate_expenses` memory consult hook |
| `src/expense_recon/coa_provision.py` | edit | settings-registry-aware COA provisioning |
| `src/expense_recon/learning/{store,consult,capture,__init__}.py` | edit | merchant_entity + field_correction, ExpenseMemory, learn_from_expense_run |
| `tests/test_web_expense_{batches,settings,learning,lifecycle}.py` | new | 41 new tests; suite 858 → 901 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | receipt-first element row (updated to LIVE) |
| `~/.claude/plans/start-agentic-ops-expense-cheeky-blanket.md` | edit | Phase 4b design appended |

(Engine paths under `workspace/clients/brisken/automations/expense-reconciliation/`.)

---

## Current Status

Merged to main through PR #462 (`f654761e`); deployed and verified on brisken-expense-recon.fly.dev with the flag ON; Lovable published. brisken platform: unknown plan, ops n/a (FastAPI/Fly app, no orchestrator ops metering). The whole receipt-first month loop works live; Criss has not yet been onboarded to it.

---

## Next Steps

1. Validate `EXPENSE_COLUMNS` (one-edit tuple in `output/zoho_expense_export.py`) against the tenant's REAL Zoho Books Expenses import — one trial import settles it (owner/Criss).
2. Dirk's call: send Criss the SPA URL; first real month through the tool (receipts all month → statement at month end) is the Phase-8 proof.
3. Watch the first real batches + the in-app feedback log for SPA rough edges (rejected-row actions and filters were just added from her/your notes).
4. Register >200 KB advisory: archive run found nothing before its 2026-05-29 cutoff (the register is large but recent) — revisit when older rows age past the cutoff.

---

## Context for Next Session

### Files to Read First

- `~/.claude/plans/start-agentic-ops-expense-cheeky-blanket.md` (full design incl. Phase 4b)
- memory `project_brisken_expense_recon_receipt_first` (final state + remaining human steps)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions

- Do the Zoho Expenses CSV headers match Brisken's real tenant import template?
- When does Criss get the link (and does the classic statement-first form stay visible for her transition month)?

### Working Notes

- Fly deploys for this app: detached worktree `agentic-ops1-deploy` at origin/main, `flyctl deploy --yes` from the engine dir, account matneumann07; `flyctl secrets set ... --stage` before deploying folds a secret into the same release.
- The live verification script is reusable: scratchpad `verify_lifecycle.py` (creates + deletes its own UTIL batch; needs the operator code from `context/.env`).
- MockLLM's tracker-less default hides Decimal-cost serialization paths — regression tests now pin both, but any NEW summary that touches `tracker.total_cost_usd` must `float()`/`str()` it.
- Expense-batch document ids are FILENAMES in the batch's `receipts/` dir; manual adds are `manual:<uuid>`; graduation bakes and freezes.

### Reference Materials

- PRs: #460 (Phases 4–6), #461 (lifecycle), #462 (Decimal fix)
- Live app: https://brisken-expense-recon.fly.dev · SPA: https://brisken-reconcile-dash.lovable.app

---

## How to Continue

`/resume brisken`, read the memory + status row. Anything engine-side starts from the `agentic-ops1-rcpt1st` worktree (branch still exists, fully merged). SPA-side changes are Lovable prompts + owner publish. The next milestone is entirely human: Zoho import validation + Criss's first real month.

---

## Strategic Feedback

### What Worked Well This Session

- Live verification as a first-class step: the deployed-origin test run caught a real production bug (Decimal cost serialization) that 899 green tests missed, and the fix shipped with regression coverage inside the same hour.
- The reuse-first architecture held: graduation + incremental adds required zero edits to `reconcile()` — the folder-ingest precedent of composing module-level primitives paid off twice.

### Suggestions

- The register now shows 9 verification-theater rows in a week, most sharing one shape: "declared live/verified while one execution path was never exercised" (here: the folder ingest's cost path shipped 07-27 with a tracker that no test ever instantiated). A structural counter: when a PR adds a background job or summary that serializes runtime objects, require one test with real-shaped (non-mock-default) collaborators — could be a review-checklist line in the build skill.

### System Health

- Autonomy: 1 human intervention (one tool-call rejection redirecting priorities); otherwise fully autonomous across five ship cycles (3 engine PRs + 2 deploys).
- Register exceeded 200 KB; the archive run found nothing before its 2026-05-29 cutoff, so the size is all recent rows — the growth rate itself is the signal (9 verification-theater rows in a week).
