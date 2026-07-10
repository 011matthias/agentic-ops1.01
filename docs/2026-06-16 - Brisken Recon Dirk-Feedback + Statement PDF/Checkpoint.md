# Checkpoint: Brisken Recon — Dirk Feedback Build + Statement PDF Ingest

**Date:** 2026-06-16
**Status:** 3 PRs merged to main + deploy live. Bank-side PDF ingest done end-to-end (CLI). Three follow-up slices queued for the full hosted workflow.

---

## Summary
Processed Dirk's 2026-06-16 review of the hosted recon workbench, then shipped three builds: (1) legal-entity-from-account + unknown-currency-flagging, (2) full Zoho Expense field ingest with Zoho's category carried, (3) a Chase statement **PDF** parser (multi-card, FX detail) for the new workflow. Deployed the entity+Zoho build to Fly and verified it live.

---

## What Was Done This Session
### Client comms captured
1. Dirk's 2026-06-16 email (process-model corrections + a full canonical flow + a request to walk through Chris's process) transcribed verbatim into `context/comms-log.md` (created this session; none existed before).
2. Walkthrough-prep doc mapping his model vs. the build + scoping the reimbursement case: `context/expense-reports/2026-06-16-dirk-feedback-walkthrough-prep.md`.

### Builds shipped (recon worktree off main; recon subtree NOT in CI → verified locally)
3. **PR #177** — legal entity derived from the paying account (run form takes an account→entity map; unmapped → account name, never a fabricated "brisken"); receipts currency no longer silently defaulted to USD (blank = unknown → flagged, matcher no longer treats unknown as same-currency). 352 tests, calibrate exit 0.
4. **PR #178** — full Zoho Expense field set ingested (payment_mode/paid_through/zoho_category/exchange_rate/base_amount/reimbursable/expense_location); lenient-optional column handling; Zoho's GL category carried onto `zoho_account`, AI category is the verify pass; workbench surfaces card/category/reimbursable. 356 tests.
5. **PR #179** — Chase statement **PDF parser** (`ingest/statement_pdf.py`): multi-card grouping via the cycle-total markers, two-line FX detail capture (orig amount/currency/rate, survives page breaks), year resolution across Dec→Jan; Transaction gains original_amount/original_currency/fx_rate; CLI `.pdf` statement source. 364 tests.

### Deploy
6. Deployed the merged #177+#178 build to Fly (`flyctl deploy ... --ha=false --remote-only`). Verified live: `/healthz` 200, `/` → 303 `/login`, login page serves.

---

## Key Decisions Made
### Carry Zoho's category, AI verifies (owner pick)
- **Choice:** Zoho's GL category → `categorization.zoho_account` (authoritative for posting); the tool's AI category (our 8) stays as the verify pass shown alongside.
- **Rationale:** Dirk: "pre-classified... run through our intelligence, verify and fix." Avoids a brittle Zoho-GL→8-category mapping and a new ClassificationSource enum (10-file blast radius).

### Input = Zoho Expense CSV/Excel export, not PDF parsing (owner pick)
- **Choice:** Extend the expense-CSV column map (config-overridable) rather than parse ER PDFs. Headers settle against a real export.

### Statement amount stays USD; FX detail captured separately
- **Choice:** Transaction.amount = USD posted; transaction_currency = USD; original_amount/currency/fx_rate hold the foreign detail. Existing FX-band matching keeps working; precise matching on original amounts is a follow-up.

### Soft-offer phrasing is a B1 deferral
- The B1 stop-gate fired 3× on "if you want, I'll X" phrasing (twice on fixes the user had deselected, once on the gated deploy). Correct behavior was to act-or-state-a-clean-decision, not dangle an offer.

---

## Files Modified
All under `workspace/clients/brisken/automations/expense-reconciliation/` unless noted. Source/test edits live on **main** (merged via PRs #177–#179) in the `agentic-ops1-recon-main` worktree.

| File | Action | Purpose / PR |
|------|--------|---------|
| `.../matching/deterministic.py` | Modified | unknown-currency guard (#177) |
| `.../web/app.py` | Modified | account→entity map field, blank currency default (#177) |
| `.../web/service.py` | Modified | entity derivation, currency surfacing, Zoho default map + receipt-view fields (#177/#178) |
| `.../web/templates/index.html` | Modified | account→entity map + currency hint (#177) |
| `.../web/templates/workbench.html` | Modified | unknown-currency notice + paying-card/category/reimbursable (#177/#178) |
| `.../matching/types.py` | Modified | Receipt Zoho fields (#178) + Transaction FX fields (#179) |
| `.../ingest/expense_csv.py` | Modified | full Zoho field parse + lenient optional (#178) |
| `.../web/serialize.py` | Modified | round-trip Receipt + Transaction new fields (#178/#179) |
| `.../categorize.py` | Modified | carry Zoho category → zoho_account (#178) |
| `.../ingest/statement_pdf.py` | Created | Chase statement PDF parser (#179) |
| `.../cli.py` | Modified | `.pdf` statement source wiring (#179) |
| `.../tests/test_*` | Created/Modified | test_deterministic_matching, test_web_app, test_web_commit, test_expense_csv, test_statement_pdf |
| `.../examples/run.with-expense-csv.example.json` | Modified | documented new optional Zoho columns (#178) |
| `workspace/clients/brisken/context/comms-log.md` | Created | Dirk 2026-06-16 email verbatim (main checkout) |
| `workspace/clients/brisken/context/expense-reports/2026-06-16-dirk-feedback-walkthrough-prep.md` | Created | walkthrough prep + reimbursement scope (main checkout) |

---

## Current Status
- **Live:** https://brisken-expense-recon.fly.dev serving the merged #177+#178 build (gated, EU, scale-to-zero). #179 (PDF parser) is on main but CLI-only; the hosted web doesn't expose `.pdf` upload yet.
- p1 stage: **live** (hosted workbench). Platform: custom Python CLI + FastAPI web, not a workflow-engine op count (no platform section to ops-audit).
- Comms: Dirk inbound 2026-06-16 (logged); staleness 0.

---

## Next Steps
1. **CSV reconciled output** — the Excel report exists; add a flat CSV of the reconciled data (statement line enriched with the matched expense). Smallest slice.
2. **Web upload of `.pdf` statements** — the workbench accepts `.csv`/`.xlsx`; add the `.pdf` path (no column-map step; account_id from the PDF markers) so Chris runs the workflow in the browser. Then redeploy.
3. **Matching precision** — card-scoped matching (expense `payment_mode` → its card / Transaction.account_id) + exact FX using the statement's captured original_currency/original_amount instead of only the implied-rate band.
4. **(gated on Dirk)** Journal-export routing that uses the new fields: payment_mode → credit account, reimbursable → "Expense Reimbursements" account. Needs the CoA account names + the account→entity mapping + payment-mode labels (walkthrough items).
5. **Schedule the walkthrough call** Dirk asked for; drive it from the prep doc.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/context/expense-reports/2026-06-16-dirk-feedback-walkthrough-prep.md` — the process map + reimbursement scope + open decisions
- `workspace/clients/brisken/context/comms-log.md` — Dirk's email verbatim + open items
- `.../automations/expense-reconciliation/src/expense_recon/ingest/statement_pdf.py` — the new parser (start here for matching-precision work)
- `.../BLUEPRINT.md` — the directed plan

### Open Questions
- Joined upload UI (statement + expenses in one run) vs. separate Collect/Reconcile stages? (Dirk unsure.)
- Exact "Expense Reimbursements" CoA account name; account→legal-entity mapping; Zoho payment-mode labels for personal/cash. All owner-supplied (TBD).
- Whether to carry Zoho's category as the AI's input vs. an independent verify (currently independent; both shown).

### Working Notes
- **All p1 work runs in the `agentic-ops1-recon-main` worktree off main**, NOT the primary checkout (which is on `client/brisken/lead-gen-onepilot`). Recon subtree is NOT in CI → run `uv run --directory <reconpath> --extra dev --extra web pytest` + `expense-recon calibrate --config examples/run.example.json` locally before every PR. CI on the PR runs only the platform/spell/playwright/hooks jobs (green ≠ recon-tested).
- **PR flow that worked:** branch off main in the worktree, stage ONLY the changed src/test files (the worktree carries pre-existing untracked WIP: `deliverables/tool-flow-2026-06-16.html`, `deliverables/user-guide-2026-06-16.html`, `recon-web-data/` — do NOT stage these), commit, push, `gh pr create`, watch `gh pr checks <n> --watch` in background, merge on green. Local main auto-syncs to origin/main after `--delete-branch`.
- **PDF parser verified to the cent:** per-card USD sums == printed cycle totals (stmt 20260104: 2838 −16273.49 / 3645 1277.53 / 0340 859.07; stmt 20260204: 2838 1925.32 / 3645 5960.41). FX original×rate == USD posted. Real statements: `context/expense-reports/20260104-statements-2838-.pdf` + `20260204-...` (client financial data — git-ignored, never commit; tests use synthetic text via `parse_statement_text`).
- **PDF structure:** `MM/DD  <merchant+loc>  <USD amt>`; FX = two lines (`MM/DD CCYNAME` then `<orig> X <rate> (EXCHG RATE)`) attaching to the preceding charge, currency carried across page breaks via a `pending_fx` state; card via `TRANSACTIONS THIS CYCLE (CARD nnnn)` markers (charges accumulate then assign on marker); year from `Opening/Closing Date`. Cards 2838/3645/0340 = the Payment Mode card last-4s in the ER reports (1672/3645/340).
- **Deploy:** `flyctl deploy "<reconpath>" --ha=false --remote-only` from the worktree (uses the working tree; ensure it's at merged main first). Verify with `curl /healthz` (200) + `/` (303→/login). flyctl v0.4.52 installed + authed.
- **Read tool can't rasterize PDFs here** (pdftoppm missing); use pypdf via the recon venv to extract text.

### Reference Materials
- Live: https://brisken-expense-recon.fly.dev
- PRs: #177 (entity+currency), #178 (Zoho fields), #179 (statement PDF)
- Dirk's functional spec (in Downloads, authoritative): `C:/Users/neuma_p1qrsic/Desktop/Downloads/ai_expense_reconciliation_functional_spec.md`

---

## How to Continue
Pick up in the `agentic-ops1-recon-main` worktree. The bank-side PDF ingest is done end-to-end via CLI. Next build is the three slices in order: CSV output → web `.pdf` upload (+ redeploy) → matching precision. Run the local pytest + calibrate gate before each PR. The Dirk-gated journal routing waits on the walkthrough.

---

## Strategic Feedback

### What Worked Well This Session
- Grounding every claim in real artifacts before asserting: reading the actual ER PDF, the real pypdf extraction, and reconciling parser output to the bank's printed totals caught zero surprises downstream. Behavior-first verification (e2e CLI run, live URL curl) over "tests pass."

### Suggestions
- The deselect-then-re-ask loop (you deselected the cheap fixes, then asked if they went through, then said "implement them") cost a round-trip. When a fix is cheap and you're likely to want it, selecting it up front is faster than the two-step.

### System Health
- **B1 deferral-phrasing recurred 3× and the stop-gate caught all 3.** The structural backstop works, but the agent kept emitting soft-offer wording on genuinely-gated or user-deselected actions. The gate is doing the job a cleaner internal rule would; no new mechanism needed, but it's the session's main autonomy drag.
- **Autonomy score: 3 human/gate interventions** (the B1 stop-gate fired 3×; one user re-affirmation loop on the fixes). Not elevated past threshold, but all in one category.
- Recon subtree being outside CI means merge-on-green is green-but-not-recon-tested; the local pytest+calibrate discipline is load-bearing. A recon CI job (even haiku-free, just pytest) would close that gap — candidate for /system-dev.
