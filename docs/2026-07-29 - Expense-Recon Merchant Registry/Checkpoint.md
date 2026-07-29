# Checkpoint: Expense-Recon Merchant Registry

**Date:** 2026-07-29
**Status:** Shipped, deployed, and seeded in production; feature complete

---

## Summary
Built the receipt-first canonical merchant registry for Brisken expense-recon end to end: a seeded, editable, self-improving phone-book of merchants that names vendors consistently and categorizes them deterministically before the LLM. Merged (#476/#481), deployed to Fly, and seeded 28 merchants into live settings; the owner published the matching Lovable UI mid-session.

---

## What Was Done This Session
### Backend (PR #476, 1011→1013 tests)
1. `vendor_clean` at extraction (vision brand + deterministic `vendor_names.clean_vendor_name` fallback); `Receipt.vendor_clean`/`canonical_vendor`/`vendor_source`.
2. `merchant_registry.MerchantRegistry` — `settings["merchants"]` read-model; exact-alias → `rapidfuzz.token_set_ratio ≥ 88` → unmatched. Added `rapidfuzz` dep.
3. `settings["merchants"]` key + PUT validation mirroring `entities`; `categorize.categorize_receipts_with_registry` wired into `generate_expenses` + the incremental-add path.
4. Grid provenance scoped to `build_expense_view`: `vendor={display,raw,source}`, `posting_category.source` coarsened to registry|learned|llm|override; `REGISTRY` joins `_TRUSTED_SOURCE`.
5. Self-improving upsert (`service.registry_upserts_from_expense_run`) on `/commit-memory`.
6. `expense-recon-seed-registry` CLI (LLM-free ER-summary clustering).

### Ship + deploy + seed
1. PR #476 merged (CI green); Fly deploy from a clean origin/main worktree, verified live (healthz 200, `/api/settings` returns `merchants`).
2. Seeded 28 merchants from the 5 live runs, applied via `PUT /api/settings`, round-trip verified.
3. Caught a live bug pre-apply (all-Travel + noise) → fixed the seed's label→bucket to read the nested-chart leaf + a noise filter; shipped PR #481.

---

## Key Decisions Made
### Registry and learned coexist (not replace)
- **Choice:** A correction seeds BOTH `settings["merchants"]` and the Phase-6 SQLite; registry wins (source reads `registry`). `/memory/forget` clears the learned SQLite but not the registry.
- **Rationale:** Spec said "reuse Phase-6, don't rebuild" AND "upsert into the registry." Additive coexistence honors both; the registry is the durable, human-curated layer.

### Grid `vendor` became an object (breaking), UI shipped first
- **Choice:** `vendor` string → `{display,raw,source}` per spec. Held the Fly deploy until the owner published the matching Lovable UI.
- **Rationale:** Deploying the shape change against the old string-reading grid would crash Criss's live tool. Owner published the UI, then deploy was safe.

### Seed categories from the chart LEAF, drop noise
- **Choice:** `label_to_bucket` reads the leaf (`… | Food` → Meals), not the "Travel Expense" parent; filter amount fragments / locations / payment processors.
- **Rationale:** Brisken's chart nests categories under an entity-bucket parent (the vision_ws2 finding). Naive keyword-on-parent bucketed everything as Travel.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/merchant_registry.py` | new | resolver + settings validator |
| `.../vendor_names.py` | new | deterministic brand cleaner |
| `.../seed_registry.py` | new | seed CLI (leaf mapping + noise filter) |
| `.../categorize.py`, `cli.py` | edit | registry-aware categorization in generate_expenses |
| `.../web/{service,app,store,serialize}.py`, `matching/types.py`, `llm/client.py`, `learning/consult.py`, `ingest/*` | edit | settings key, grid provenance, upsert, data model |
| `.../tests/test_merchant_registry.py`, `test_web_merchant_registry.py` | new | +39 tests |
| `.../docs/lovable-merchants-prompt.md` | new | UI handoff |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | roll-up row (bundled here deliberately) |

---

## Current Status
Feature is **live in production** on `brisken-expense-recon.fly.dev` and seeded (28 merchants). Backend, deploy, seed, and the owner-published Lovable UI are all aligned and verified. brisken platform: unknown plan, ~?/? ops/mo (no `platform` section in infrastructure.yaml). p1 status file current as of today.

---

## Next Steps
1. **Owner, in the Merchants editor:** merge OCR/casing duplicate entries (MEGA CENTER/CENTRE; the Fenix and Ki-Massa pairs) and fix chart-mislabeled categories (MEGA CENTER = construction materials, reads Travel). Each fix teaches the registry.
2. **Pre-existing receipt-first tail (owner):** validate `EXPENSE_COLUMNS` against the tenant's real Zoho Books Expenses import template; send Criss the SPA URL + run her first real month (Phase 8 e2e proof — she has not used the tool since 2026-07-20 and has never been sent the SPA URL).
3. **Optional:** re-seed as more months process (current corpus is a narrow Brazil travel/meals set of 5 runs).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (the merchant-registry row)
- memory `project_brisken_expense_recon_merchant_registry`
- `automations/expense-reconciliation/src/expense_recon/merchant_registry.py`

### Open Questions
- Should the seed be re-run at scale once more months are processed, or grown purely via reviewer corrections?
- Do the chart-mislabeled ER categories (construction booked as Travel) warrant a chart-level fix, or just per-merchant registry overrides?

### Working Notes
- Seed corpus = 5 live runs (Brazilian travel/meals). Threshold 88 over-merged (ERICK SPORTS 27 aliases), 93 under-merged (dup variants). Chose 93 (under-merge is the safe direction — two entries for one shop is harmless; wrongly merging two shops is not).
- CI does NOT run this subtree's pytest/ruff (CI ruff scope = `tools .claude/hooks tools/tests`), so the local full suite (1013) is the real gate for this app.
- flyctl is now logged in as matneumann07 (the 2026-07-20 "logged out" note is stale).

### Reference Materials
- PRs #476 (backend), #481 (seed fix)
- `docs/lovable-merchants-prompt.md` (the UI handoff)

---

## How to Continue
The feature is done and live; nothing is blocked. Pick up from Next Steps — the highest-value item is the pre-existing Phase-8 e2e (get Criss actually using the tool), which is bigger than anything in the registry itself.

---

## Strategic Feedback

### What Worked Well This Session
- Mapping the whole codebase with one thorough Explore agent up front made the 12-file build land clean with zero architecture backtracking.
- Catching the seed-quality bug by inspecting real output BEFORE applying to production (rather than trusting the heuristic) kept garbage out of live settings.
- Holding the deploy on the breaking vendor-shape change instead of auto-running the pre-auth — the owner had already published the UI, so the pause surfaced exactly the right coordination point.

### Suggestions
- The seed's `label_to_bucket` should have been leaf-first from the start — the vision_ws2 memory already documented Brisken's nested entity-bucket chart. A pre-build re-read of the client's own COA-quirk memories would have caught it before the live run.

### System Health
- One friction event: `missed-memory-recall` (the nested-chart quirk was in memory but not applied to the seed mapper; caught + fixed same session, structural fix shipped).
- Gates: B1:2 (both legitimate owner-only decisions, not deferrals) B2:many (full-suite + live deploy + seed round-trip all verified) B3:1 (seed-garbage root-caused to nested chart) skipped:0.
- Autonomy: ~3 human interventions (2 scope-question answers I requested; 1 "UI published, deploy" readiness signal). No corrections of delivered work — high-autonomy session.
