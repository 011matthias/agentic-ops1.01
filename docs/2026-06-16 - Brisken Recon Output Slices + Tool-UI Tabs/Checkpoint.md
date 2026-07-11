# Checkpoint: Brisken Recon Output Slices + Tool-UI Tabs

**Date:** 2026-06-16
**Status:** 8 PRs merged to main + 4 Fly deploys live. The three queued recon slices are done; the tool UI gained embedded docs + boxed tab nav. One misdirected embed (Strategy) is queued for removal.

---

## Summary
Shipped the three remaining bank-side recon slices (CSV reconciled output, web .pdf statement upload, matching precision) each as its own PR, then embedded the user-guide + how-it-works docs into the tool, and (after a sustained intent misread) restyled the tool's own nav into boxed tabs. All merged to main; the hosted Fly tool was redeployed and verified four times.

---

## What Was Done This Session
### The three recon slices (continuation of the 2026-06-16 Dirk-feedback build)
1. **#180 — flat reconciled CSV output.** `output/reconciled_csv.py` (`build_reconciled_rows` + `write_reconciled_csv`), one row per statement line enriched with its matched expense (report #, Zoho category, payment mode, receipt URL, original+statement amounts, explicit match status); bank line preserved verbatim; unmatched charges kept (not dropped). Mirrors `zoho_export` incl. the 8.4/8.3 lookup precedence. Wired into CLI (`output.reconciled_csv`) + web (`regenerate_reconciled` + `GET /runs/{id}/reconciled.csv` + workbench download button).
2. **#181 — web .pdf statement upload.** `prepare_run` branches on `.pdf`: skips the CSV column-map auto-detect; `_build_config` emits a PDF-shaped statement block (no column_map / account_id — per-card id comes from the cycle markers). `index.html` accepts `.pdf`. No parser/app.py change (CLI `_load_statement` already routes on suffix).
3. **#182 — matching precision.** Card-scoped matching (a receipt's Zoho `payment_mode` only reconciles against charges on that card; keyed off digit overlap via `_card_keys`, safe fallback when the named card isn't present) + exact-FX (when the statement captured the charge's original amount/currency, match on the original amount deterministically, no band/LLM). Factored shared scoring into `_match_on_amount`; same-currency reasons unchanged. `card_scoping` kill switch.

### Tool-UI work
4. **#183 — embed user-guide + how-it-works.** `web/guides/{user-guide,tool-flow}.html` (packaged in the wheel), `GET /guide` + `/how-it-works`, nav links in `base.html`.
5. **#185 — embed the strategy deck** as `/strategy` (MISDIRECTED — see friction; now queued for removal).
6. **#184 + #186 — strategy-deck tab polish** (boxed/segmented tabs, then flatten to match the reference screenshot). Also misdirected.
7. **#187 — boxed tab nav in the tool UI.** Restyled `base.html`'s top nav (Runs/Compare/Memory/Guide/How it works/Strategy) into segmented boxed tabs: active page = outlined box + accent-blue bold (client-side `location.pathname` detection); `[`/`]` keyboard jump; new `--border-strong` token (light `#94a3b8` / dark `#4a5d80`). **This was the actual ask all along.**

### Deploys (all Band-3, on explicit user order; verified `/healthz` 200 + `/` 303→/login)
- Slices 1+2; slice 3 + guide embeds; strategy-deck flatten; tool nav tabs.

---

## Key Decisions Made
### Embedded docs live under `src/expense_recon/web/guides/`, not `deliverables/`
- **Choice:** Served copies of the HTML docs are packaged in the wheel under `web/guides/`; the `deliverables/*.html` originals stay separate.
- **Rationale:** `.dockerignore` excludes `deliverables/`, and the container runs from the installed wheel. Verified by building the wheel and confirming the files are inside. **Drift risk:** a doc edit must touch both copies (flagged to user).

### Card-scoping is heuristic + safe-fallback, NOT the Dirk-gated label map
- **Choice:** Scope a receipt to its card via digit overlap between the cycle-marker `account_id` and the payment-mode label; only narrow when the named card is actually present in the statement, else don't scope.
- **Rationale:** The exact payment-mode→account labels are gated on Dirk's walkthrough. The heuristic delivers the precision win now without fabricating the client-specific mapping, and never wrongly excludes a real match (reconciliation guarantee).

### Exact-FX subsumes the same-currency band case
- Once the statement carries the original amount, an in-band same-currency receipt is already within tolerance of it, so exact-FX matches it; the band path only ever drops out-of-band pairs. A test asserting "decline→band→FX_JUDGMENT" was wrong and was corrected to "decline + out-of-band → unmatched" (a real reconciliation-guarantee test).

---

## Files Modified
All under `workspace/clients/brisken/automations/expense-reconciliation/` (recon worktree, main) unless noted.

| File | Action | Purpose / PR |
|------|--------|---------|
| `src/expense_recon/output/reconciled_csv.py` | Created | flat reconciled CSV (#180) |
| `src/expense_recon/cli.py` | Modified | `output.reconciled_csv` wiring (#180) |
| `src/expense_recon/web/service.py` | Modified | `regenerate_reconciled` (#180); `.pdf` ingest branch (#181) |
| `src/expense_recon/web/app.py` | Modified | reconciled/guide/how-it-works/strategy routes (#180/#183/#185) |
| `src/expense_recon/web/templates/index.html` | Modified | `.pdf` accept + hint (#181) |
| `src/expense_recon/web/templates/workbench.html` | Modified | reconciled CSV download button (#180) |
| `src/expense_recon/web/templates/base.html` | Modified | guide/strategy nav links (#183/#185); **boxed tab nav + keyboard jump (#187)** |
| `src/expense_recon/matching/deterministic.py` | Modified | card-scoping + exact-FX + `_match_on_amount` refactor (#182) |
| `src/expense_recon/web/guides/{user-guide,tool-flow}.html` | Created | embedded docs (#183) |
| `src/expense_recon/web/guides/strategy.html` | Created | embedded strategy deck (#185 — TO REMOVE) |
| `tests/test_reconciled_csv.py`, `test_web_reconciled_download.py`, `test_web_pdf_upload.py`, `test_matching_precision.py`, `test_web_guides.py` | Created/Modified | coverage for the above |
| `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html` | Modified | deck tab styling (#184/#186 — misdirected) |

---

## Current Status
- **Live:** https://brisken-expense-recon.fly.dev — all four shipped surfaces deployed + verified. Tool nav is boxed tabs; `/guide`, `/how-it-works`, `/strategy`, `/reconciled.csv` all wired (gated).
- Test suite 364 → **393 passed / 2 skipped**; calibrate exit 0 throughout. Recon subtree still NOT in CI (local pytest+calibrate is the gate).
- p1 stage: **live**. Platform: custom Python CLI + FastAPI (no workflow-engine ops to audit).
- Comms: Dirk inbound 2026-06-16 logged (Session 4); walkthrough still to schedule.

---

## Next Steps
1. **Run the handoff prompt** (written this session, in the user's hands) to: (a) remove **Strategy** from the recon tool — nav link in `base.html`, `GET /strategy` route in `app.py`, `web/guides/strategy.html`, and the strategy assertions in `test_web_guides.py`; (b) update the **Guide** (`user-guide.html`) and **How it works** (`tool-flow.html`) content to reflect the current tool (reconciled CSV output, web PDF upload, card-scoped + exact-FX matching, the new nav). Then redeploy.
2. **Dirk-gated journal routing** (unchanged): payment_mode → credit account, reimbursable → "Expense Reimbursements". Needs CoA names + account→entity map + payment-mode labels from the walkthrough.
3. **Schedule the walkthrough call** with Dirk/Chris.
4. Consider de-duplicating the `deliverables/*.html` ↔ `web/guides/*.html` copies (symlink or single source) to kill the two-edit drift.

---

## Context for Next Session
### Files to Read First
- `src/expense_recon/web/templates/base.html` — nav + tab styling (the Strategy removal target)
- `src/expense_recon/web/app.py` — the embedded-doc routes
- `src/expense_recon/web/guides/{user-guide,tool-flow}.html` — the docs to update
- `BLUEPRINT.md` + the prior checkpoint (`docs/2026-06-16 - Brisken Recon Dirk-Feedback + Statement PDF/Checkpoint.md`)

### Open Questions
- Should the `deliverables/` HTML originals and the `web/guides/` served copies be unified to avoid drift?
- Keyboard jump on the tool nav uses `[`/`]` (not arrows, to avoid scroll conflict on the data-heavy workbench) — confirm that's the wanted shortcut.

### Working Notes
- **All recon work runs in the `agentic-ops1-recon-main` worktree off main.** Per-slice PRs, stage ONLY changed src/test files (never the untracked WIP: `deliverables/tool-flow-2026-06-16.html`, `user-guide-2026-06-16.html`, `recon-web-data/`, and now `brisken-onepilot-website-*`).
- Recon is NOT in CI → run `uv run --directory <recon> --extra dev --extra web pytest` + `expense-recon calibrate --config examples/run.example.json` (exit 0) before every PR.
- The deployed container installs the WHEEL (not /app/src), so any served asset must live under `src/expense_recon/web/**` to ship — verified with `uv build --wheel` + zip listing.
- Deploy: `flyctl deploy "<recon>" --ha=false --remote-only` from merged main; verify `/healthz` 200 + `/` 303→/login. Gated routes can't be auth-verified live without the access code (do NOT dig the vault — it's correctly blocked); rely on local render + wheel-packaging proof + unit tests.
- To visually verify the rendered nav: run the app locally (`expense-recon-web --host 127.0.0.1 --port <p> --data <tmp> --no-open`), `chrome --headless --screenshot` localhost, then `TaskStop` the server.

### Reference Materials
- Live: https://brisken-expense-recon.fly.dev
- PRs: #180 (CSV) #181 (web PDF) #182 (matching) #183 (guides) #184/#186 (deck tabs) #185 (strategy embed) #187 (nav tabs)

---

## How to Continue
Pick up in the recon worktree on main. The three slices + tool-UI tabs are done + live. The immediate next task is the handoff prompt: remove Strategy from the tool and refresh the Guide/How-it-works content, then redeploy. The Dirk-gated journal routing still waits on the walkthrough.

---

## Strategic Feedback

### What Worked Well This Session
- Per-slice PRs + the local pytest/calibrate gate kept each change isolated and verifiable; the wheel-packaging check caught the real prod risk (served assets must be in the wheel) before deploy, not after.
- Rendering the running app headless and comparing to the reference screenshot is the only thing that actually settled "does it match" — behavior verification over CSS reasoning.

### Suggestions
- When a request comes with a screenshot, state the interpreted TARGET surface back before editing ("I read this as: style the tool's nav like this reference"). This session burned ~4 PRs and a deploy because the screenshot was taken as the literal thing to edit (the strategy deck) rather than a style reference for the tool's nav. One confirming sentence up front would have saved the whole detour.

### System Health
- **Recurring intent-misalignment on visual/reference inputs (today: Session 7 ×2, Session 8 ×1).** The pattern is treating an attached artifact (brief, screenshot) as literal spec instead of extracting the intent + confirming the target. This is a Layer-3 (intent-review) gap with no structural gate; candidate for a memory + a pre-edit "restate the target surface" habit. Autonomy score: 5 human interventions (elevated — run /system-dev to close the intent-review gap).
- B1 deferral-phrasing recurred again (stop-gate caught 2×); same class as every session today. The gate holds; the agent keeps emitting soft offers at turn-end.
- Recon-subtree-outside-CI means merge-on-green is green-but-not-recon-tested; the local discipline is load-bearing. A recon pytest CI job remains the standing /system-dev candidate.
