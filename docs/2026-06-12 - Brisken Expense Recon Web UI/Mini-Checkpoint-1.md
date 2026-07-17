# Mini-Checkpoint: Brisken Expense Recon Web UI

**Date:** 2026-06-12
**Status:** Shipped to main (PR #152, squash `fe6ac6d`)
**Type:** mini

---

## Summary
Built and shipped a local browser UI for the standalone expense-reconciliation
tool (p1): `expense-recon-web`, a FastAPI app wrapping the existing CLI pipeline
with an editable review workbench (confirm / reject / pick-candidate /
reclassify-category, persisted, applied to the xlsx export). Loopback-only;
financial data stays on the machine. Owner chose local-app + editable-workbench
over hosted + read-only-console.

## What Was Done
- `cli.py`: extracted a side-effect-free `reconcile()` core shared by the CLI
  `run()` and the web app. `run()` behavior unchanged; the 255 prior tests
  stayed green.
- New `src/expense_recon/web/` package: `serialize` (snapshot round-trip of the
  frozen dataclasses, Decimal/date exact), `store` (SQLite: runs + decisions +
  category overrides), `service` (run + render view model + apply-decisions /
  apply-overrides preserving the reconciliation guarantee), `app` (FastAPI),
  `serve` (uvicorn launcher, `expense-recon-web` console script). Jinja2
  templates (upload + workbench) with a working dark/light toggle, no em-dashes,
  no emoji nav.
- `pyproject.toml`: `[web]` optional extra (fastapi, uvicorn, python-multipart,
  jinja2) + `httpx` in `[dev]` for TestClient.
- Tests: 6 TestClient e2e in `tests/test_web_app.py`. Suite 255 -> 261 green.
- Verified live over real HTTP (httpx to the running uvicorn process) + a
  browser screenshot of the workbench. Not just TestClient.
- README: added a "Browser UI (review workbench)" section.

## Current Status
- p1 expense-recon: `live`. Path A complete + now a browser front end on main.
- The xlsx report (with reviewer decisions + category overrides applied) is the
  live deliverable from the UI. Zoho journal CSV export is NOT wired into the UI
  yet (depends on a chart-of-accounts, sensitive Brisken data, gated/not in
  repo). Journal POSTING to Zoho (4b) stays gated, same as the CLI.
- Branch hygiene: built in a worktree off `main` (`client/brisken/expense-recon-web-ui`,
  merged + remote branch deleted). This checkpoint lands via a `docs/...` PR off
  main (G1). The main clone stays on the p2 lead-gen branch.

## Next Steps
1. (p1 UI follow-ons, optional) Wire the Zoho journal CSV export + receipt-image
   upload/OCR into the workbench once a chart-of-accounts path exists; add a
   batch "confirm all exact matches" action.
2. (p1 GATED, unchanged) 4b journal POSTING to Zoho needs Dirk's API access.
3. (housekeeping) Delete the stale `agentic-ops1-reconui` worktree directory on a
   fresh shell (git already unregistered it; Windows cwd-lock blocked the rmdir
   this session).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/README.md` (Browser UI section)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (the run + view + apply-decisions logic)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/cli.py` (`reconcile()` shared core)
