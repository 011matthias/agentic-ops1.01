---
project: brisken
workstream: p1-expense-reconciliation
group: ""
spec: p1
state: active
updated: 2026-07-22
---

# Brisken / Expense Reconciliation (p1)

AI-assisted expense reconciliation tool for Brisken: turn Chris's multi-day
reconciliation grind into minutes of review, with a 1:1 Zoho journal export.
Scope is the "working tool" (single-tenant, Brisken-only) per Dirk's directive;
the multi-tenant SaaS in spec v2 is deferred. Per-slice authority is
`automations/expense-reconciliation/BLUEPRINT.md` + `ANNEALING.md`; this is the
roll-up.

The backend is hosted and running on real data at brisken-expense-recon.fly.dev
(API-only since v31; gated by `EXPENSE_RECON_OPERATOR_CODE`). The UI is the
Lovable SPA at brisken-reconcile-dash.lovable.app. Verify the deployed origin,
not localhost, after backend edits (`flyctl deploy`).

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
| Card as a matching signal (WS3) | live (PR #317, deployed 2026-07-22) | `Transaction.card_last4` + optional `card` column map (CSV/xlsx + hosted guess); card-scoped candidates now key on the CHARGE's card, not the account id. On the real 01-05 month software-vs-Food FX-false-pairs 4 -> 0. Also: `Match.card_score` (tie-break + workbench), card into the FX-judgment prompt, optional `matching.llm_second_pass_unmatched` (OFF) |
| Sign canonicalization + refunds bucket + deterministic FX (Tier-1) | done (PR #285) | BLUEPRINT 3.15; no-LLM 0/36->29/36 on Criss's April |
| Dev notifier: operator "run now" uploads fire an email | **live + scheduled 2026-07-22** | `tools/brisken-recon-notify.py`. Was doubly broken: unscheduled AND dead since the v31 cutover (logged in via the deleted `POST /login`, and all 4 mail links pointed into the deleted HTML UI, including the publish ping that goes to the USER). PR #373 moves it to `/api/login` + bearer, handles the throttle's 429, and points links at `APP_URL` (the SPA). Registered as Windows task `BriskenReconNotify` (15-min repeat), `LastTaskResult 0` over two fires, 0 missed; state baselined so the first fire did not mail the backlog. NOTE: the task runs from the PRIMARY clone (it needs the gitignored `context/.env`), which currently carries the fix as an uncommitted local edit identical to main — `git checkout -- tools/brisken-recon-notify.py` before pulling there |
| Cross-run memory (Phase 2) | in-progress | BLUEPRINT Phase 2 |
| Jinja HTML UI retirement (API-only backend) | DONE — deployed Fly v31, 2026-07-22 | PR #350, redone ast-first per the SPA-cutover checkpoint manifest: 17 HTML routes + 14 bare decorator twins removed, `_wants_json` collapsed, `templates/` (12 files) + `static/` (4 files) deleted, role plumbing stripped (operator is the only role; gate keyed on `EXPENSE_RECON_OPERATOR_CODE`, the only code set on Fly). app.py 1518 -> 1071 lines; suite 772 -> 712 green. Deployed on owner order + live-verified (healthz 200; `/` + `/login` answer JSON 401, no HTML; SPA-origin CORS intact). Rollback = redeploy v30 via `flyctl releases` |
| Zoho journal CSV export | in-progress | BLUEPRINT slice 4 |
| Run history + doctor pre-flight | done | BLUEPRINT slice 5/5b |
| COA pre-write validation gate | live (Fly, per-entity) | BLUEPRINT 4.11 (PR #202/#203/#205) |
| Export idempotency (4.8) | not-started | BLUEPRINT Phase 5 (gap) |
| Match ground-truth labeling (`label propose/accept/check`) | done | `labeling.py`; optimize-loop prep — labels per month-bundle in gitignored context |
| Label fixture: 6 production-shape bundles (CSV stmt + ER PDF) | done (2026-07-17), **trustworthiness OPEN as of 2026-07-22** | `context/.../csv/by-month/`: labels.csv per month, `label check` OK on all 6; 141/218 labeled (95 confirmed / 46 no_charge), 77 excluded as ambiguous; decisions corroborated offline via 2026 stmt-PDF FX originals + payment-mode card refs. **2026-07-22:** replaying the 6 bundles deterministically (no LLM) resolves only 37/95 confirmed pairs to the labelled charge; for 53 the receipt is claimed by a DIFFERENT charge, 2 are free, 3 name a charge absent from that month's statement. Cause not established: on amount-proximity to the receipt's `base_amount` the LABEL is closer 32x and the MATCHER 20x (1 tie), so this is neither clean label-id drift (post-#285 ingest changes shifted positional ids) nor a clean matcher precision bug — both are present and this instrument cannot separate them. **Re-validate before using these labels as a scorer fixture** (blocks the S1 optimize design, which scores against them) |
| ER-PDF ingest hardening (ISO-ccy amounts, inline rows, per-token format) | done (PR #263) | `expense_report_pdf.py`; all 6 real ERs parse to-the-cent vs printed totals |
| Web-download exports carry Tier-2 receiptless categories | done (PR #294) | `service._charge_cats` threaded into all 4 `regenerate_*`; zoho honors `export_receiptless_learned` |
| SPA JSON API for the Lovable front end | live, SPA at PARITY + published | `/api` + bearer + CORS, Lovable-hosted (PRs #290/#291/#293); NOT `/api/v1`; SPA repo `011matthias/brisken-expense-review` (TanStack Start). Path 1 chosen 2026-07-21: extend this SPA, do NOT rebuild from the plan's prompt. 2026-07-22: production URL = **brisken-reconcile-dash.lovable.app** (existing CORS regex already covers `*.lovable.app`, no backend change). PRs brisken-expense-review #1 (runs made reachable: all-runs + intake tables, publish/unpublish, 8 bare paths -> `/api`, §18 resolve, `/settings`, `/compare`, `/intakes/$intakeId`, `card_pct`) and #2 (publish control names the action) merged AND published; full review loop verified live incl. a publish round-trip with state restored |
| §17 disposition, §16 export-approved gate, §18 duplicate resolve | backend live (deployed 2026-07-21, verified) | PRs #296/#297/#298; `/api/runs/{id}/disposition`, `/duplicates/resolve`, `GET/PUT /api/settings` all live + inert-by-default; run detail carries `duplicate_groups` + `disposition` |
| Local no-API-key test loop: `run.local.json` per run | live (PR #299, deployed 2026-07-21) | `prepare_run` writes a self-contained config (minus `llm`/`coa_validation`) beside the uploads in `/data/runs/<id>/`, so `flyctl sftp` + `expense-recon --config run.local.json` reconciles locally with NO OpenAI call. Existing live run `b67133b8df98` backfilled |
| SPA mutation parity (`/api` twins) | live (PR #318, deployed 2026-07-22) | 11 mutations mounted on `/api` (decisions, confirm-matched, categories, manual-match, forget, commit-memory, feedback, publish, unpublish, memory/reset, intakes+files+run). `_wants_json` branches one handler across both surfaces. `auth.path_requires_operator` now canonicalizes the `/api` prefix — future twins inherit their operator rule, do NOT add duplicate regexes. SPA can now finish a full review |
| SPA compare (server-computed diff) | live (PR #301, deployed 2026-07-21) | `GET /api/compare?a=&b=` wraps `compare_runs`; closes the last frontend-computation hole so Lovable computes no diff |
| §14 configurable automation | planned | plan Phase 6 (`~/.claude/plans/async-beaming-perlis.md`), optional; behavior-changing (auto-confirm), default-OFF |
| SPA memory screen (`/api/memory`) | live (deployed v25, verified 2026-07-21) | PR #304: `GET /api/memory` + `POST /api/memory/forget`, operator-gated (mirrors HTML `/memory`); serializes `build_memory_view` / reuses `forget_memory_vendor` |
| LLM owns category+account + AI Category CSV columns + hosted LLM default-on (WS1) | live (PR #313, deployed 2026-07-21) | `categorization.override_er_category` keeps the LLM/learned account; reconciled CSV gains `AI Category`/`AI Zoho Account`/`AI Category Source`; hosted runs use LLM by default (`EXPENSE_RECON_DEFAULT_LLM`/`_OVERRIDE_ER_CATEGORY`) |
| Vision receipt-image read + deterministic root-group adjudication (WS2) | live (PR #315, deployed 2026-07-21) | `ingest/expense_report_images.py` reads the ER PDF's receipt IMAGES (fills the ~9/20 summary rows with no vendor); `adjudicate_receipts` overrides the report's category only on a heavy Zoho root-group mismatch (`Category Decision` column: kept ER / AI override (heavy) / review); categorizer chart now built from `coa_validation` so override+adjudication fire on hosted runs; vision default-on (`EXPENSE_RECON_VISION_RECEIPTS`, ~$0.14/run). NOTE: ADOBE/ANTHROPIC are receiptless statement charges (FX-false-paired to Food receipts) -> a MATCHING problem = WS3, NOT fixed here. Plan: `~/.claude/plans/plan-out-how-we-playful-boole.md` |
| Login throttle on `/api/login` | live (PRs #367 + #369, deployed Fly v32/v33 2026-07-22) | `web/ratelimit.py` + `login_failures` table. Per-caller 5 failures/15min then 60s lockout doubling to a 1h cap; global 50/15min then 300s. Only failures count, a success clears the caller, the throttle runs BEFORE the code check. Callers bucket by IPv6 **/64** (a /128 key gave one end site 2^64 fresh buckets). Verified live: 5x401 -> 429 `Retry-After: 60` scope=ip -> right code still 429 while locked -> expiry -> 200 -> record cleared. Live-probe finding: Fly's proxy OVERWRITES `Fly-Client-IP`, so the per-caller key is the real peer and is not forgeable; stored key confirmed on the volume as `2003:c6:3f3c:3200::/64`. Stdlib only, env-tunable, no-op when the gate is off |
| Matching: card signal + FX-judgment card enrichment + second-chance pass (WS3) | not-started | the real ADOBE/ANTHROPIC fix (they FX-false-pair to unrelated Food receipts); card as a first-class matching signal + FX-judgment enriched with card + optional second-chance pass over unmatched. Plan WS3 |

## Open decisions / gates

- Spec-incorporation backend (§16/§17/§18 + `/api/settings`) DEPLOYED to Fly 2026-07-21
  from `origin/main` #299 (full suite 670-green first; idempotent DB migration verified safe
  on Criss's live 94-row run). Live app now at #299.
- SPA production URL DECIDED 2026-07-22: `brisken-reconcile-dash.lovable.app`. A custom
  `recon.brisken.com` stays optional; it would need the CORS regex widened + a Fly deploy.
- **Lovable merge != live:** merging the SPA repo's main syncs the Lovable EDITOR only; the
  published site keeps serving the last explicitly-published build. Verify with a structural
  DOM probe, not a label. Publishing is a dashboard action the agent cannot perform.
- Fly HTML-UI deletion DEPLOYED (v31, 2026-07-22, owner order). If Criss surfaces on the
  old UI instead of the SPA, rollback = redeploy v30 via `flyctl releases`. The
  `/api/login` rate-limit half of the hardening is now CLOSED (v33, PRs #367/#369);
  one shared operator code is still the whole boundary, so a second factor or a
  per-person code remains the open half.
- **`matching.llm_second_pass_unmatched`: RECOMMEND LEAVING OFF** (evaluated 2026-07-22,
  zero LLM spend). The pass can only pair an unmatched charge with a still-unclaimed
  receipt, so its ceiling is computable deterministically: across all 6 labelled
  bundles it is **1-2 rescues out of 95 confirmed pairs**. The structural reason is
  that only 13 receipts remain unclaimed across the 6 months against 559 unmatched
  transactions; the unmatched bucket is dominated by receiptless statement charges
  (the ADOBE/ANTHROPIC class), and no matching pass can find a receipt that does not
  exist. Realising <=2 rescues would cost ~40 LLM calls per run (the `max_calls` cap,
  hit every month) and each rescue lands in `judgment_required` = MORE review for
  Criss, not less. Flipping the default needs an owner order; there is no case for one.
- **Criss has not used the tool since 2026-07-20** (checked 2026-07-22, read-only):
  latest run 2026-07-21T10:19Z, latest feedback note 2026-07-20T17:22Z, zero intakes,
  zero published runs; a both-mailbox all-folders Graph scan since 07-14 shows her
  active on normal finance mail and silent on the tool. So she did NOT hit the old UI
  after v31 and no rollback is indicated. The live gap is forward-looking: her
  2026-07-20 PT email gave her exactly one link, `brisken-expense-recon.fly.dev`,
  which now answers `{"error":"authentication required"}` as raw JSON. **She has never
  been sent the SPA URL.** Owner call pending; no outbound sent.
- Concurrency: two sessions share this module (active `agentic-ops1-recon` worktree); before
  any backend build here, `git fetch origin main` + `git log` first (4th collision-class event).
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
