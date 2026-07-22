---
date: 2026-07-22
session: recon-ui-del
projects_touched: [brisken]
friction_events: 1
work_types: [client-dev]
---

### Session — Brisken Expense-Recon Fly UI Deletion + Deploy
**Type:** client-dev
**Focus:** Undid the shared-clone mess from the failed 2026-07-22 SPA-cutover session (19 untracked + 16 dirty ledger entries blocking `git pull`, two stray clones, four orphaned vite/npm processes pinning `C:\br-spa`), then redid the Fly HTML-UI deletion ast-first from the checkpoint's verified manifest and deployed it on the owner's order.
**Projects:** brisken (p1-expense-reconciliation)
**Built:** PR #350 (17 HTML route blocks + 14 bare decorator twins deleted via ast with exact-match assertions; `_wants_json` collapsed; templates/ + static/ + jinja2 gone; operator-only auth — `flyctl secrets list` verified ACCESS_CODE was never set before stripping it; tests: 3 files deleted, ~18 rewritten onto /api; suite 772 -> 712 green, app.py 1518 -> 1071); PR #351 (dedupe of the duplicate frontmatter #330 left in `sessions/2026-07-21.md`); Fly **v31 deployed + live-verified** (healthz 200, `/` + `/login` = JSON 401, gate on, SPA-origin CORS reflected); memories + p1 status updated.
**Friction:** 1 — `slow-path` (cd-guard fired 2x on `cd X && ...` compounds and the Edit tool rejected 2 edits on files read only via Bash grep/sed instead of Read; all self-corrected same turn. The cd class is a documented recurrence — the hook holds, the habit persists).
**Gates:** B1:4 (flyctl secrets/process enumeration instead of asking; checkpoint read from origin/main when absent locally) · B2:5 (712-test suite; route-table enumeration of the imported app; live-origin probes post-deploy incl. CORS preflight; merge state verified via gh pr view after a known false-fail gotcha) · B3:2 (br-spa "resource busy" -> found the 4 orphaned processes via Win32_Process before retrying; pull abort -> re-fetched and re-verified against the moved tip instead of forcing) · B4:1 (status-file numbers traced to wc/pytest/flyctl) · B7:2 (Fly secrets + Dockerfile/packaging enumerated before the auth strip) · skipped:0
**Autonomy:** 0 human interventions (two owner directives, zero corrections)
**Outcome:** Live origin is API-only at Fly v31; the Lovable SPA is the sole review surface. Shared clone unblocked (a live sibling's fresh WIP left alone, correctly). Open: Criss-on-SPA confirmation, /api/login rate limit.
