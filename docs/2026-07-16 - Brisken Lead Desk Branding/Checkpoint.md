# Checkpoint: Brisken Lead Desk Branding

**Date:** 2026-07-16
**Status:** COMPLETE — Brisken brand system live on the Lead Desk app

---

## Summary

Ported the Brisken brand system (design tokens, real logos, favicon) from the expense-recon workbench onto the Lead Desk app so it reads as a Brisken surface. Shipped as one PR (#243, squash `a5a123a`), merged on green CI, deployed, and live-verified with screenshots of login and board in both themes.

---

## What Was Done This Session

### Branding port (PR #243)
1. Copied the proven asset set from the expense-recon app: `brisken-logo-light.png` / `brisken-logo-dark.png` / `favicon.png` (verified real PNGs, 292x64 logos / 128x128 favicon) and `tokens.css` (Brisken website palette — navy heading, teal accent, brand cyan — light + dark themes), with `--blue-bg` remapped into the teal accent family to fit the Lead Desk's existing stage-badge classes.
2. `app.py`: added the ungated, basename-only `GET /static/{name}` route (traversal-safe, unknown names 404) and a real `/favicon.ico` → `favicon.png`.
3. `auth.py`: `path_is_open()` now also matches any `/static/*` prefix, so the login page can pull tokens/logo before authentication.
4. `base.html`: dropped the old inline `:root`/`[data-theme]` palette in favor of `<link rel="stylesheet" href="/static/tokens.css">`; nav now carries the theme-swapping logo + a monospace `LEAD DESK` product tag; buttons use `--btn-ink` (was hardcoded `#fff`, wrong contrast in dark theme); headings take `--heading` (brand navy).
5. `login.html`: rewritten on the same branded-card pattern as expense-recon's login (logo, tokens, theme toggle button, teal CTA).

### Verification
1. **252 tests** (246 baseline + 6 new `test_branding.py`: ungated static with correct content-types, traversal 404, unknown-name 404, cookie gate still intact post-change, branded login markup, branded post-login nav markup, real favicon PNG bytes).
2. CI green (4 checks) → squash-merged → `flyctl deploy` → live HTTP verification: `/static/tokens.css` 200 with brand tokens present, logo PNG 200, traversal 404, branded login HTML pre-auth, branded board HTML post-auth, no-send engine state unchanged (`kill_switch=1`, rome-2026 `'done'`).
3. Playwright screenshots (fresh tab on the user's live Edge, closed after use — the user's other tabs were never touched): login light/dark on the live app, board light/dark on a throwaway local instance (gate off, empty DB). All four confirmed on-brand by visual inspection. Saved to `.scratch/ld-login-{light,dark}.png` and `.scratch/ld-board-{light,dark}.png` (Playwright's default save path is the repo root / MCP server cwd — relocated per file-placement rules).

---

## Key Decisions Made

### Reuse the expense-recon brand system verbatim, don't redesign
- **Choice:** same token names, same asset files, same `/static/{name}` route shape, same login-card structure as `expense-recon` PR #228.
- **Rationale:** two Brisken-internal tools with divergent design systems reads as sloppier than one shared system; the expense-recon pattern was already validated (live, tested) so porting it is close to zero-risk.

### Extend `path_is_open()` with a prefix check, not per-file `OPEN_PATHS` entries
- **Choice:** `path.startswith("/static/")` in `auth.py` rather than listing each asset.
- **Rationale:** matches the expense-recon precedent; any future static asset (new logo variant, another CSS file) needs no auth-layer change.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../src/lead_desk/web/static/tokens.css` | Created | Brisken design tokens, both themes |
| `.../src/lead_desk/web/static/brisken-logo-{light,dark}.png`, `favicon.png` | Created | Real brand assets (copied from expense-recon git history) |
| `.../src/lead_desk/web/app.py` | Modified | `/static/{name}` route (basename-only), real `/favicon.ico` |
| `.../src/lead_desk/web/auth.py` | Modified | `path_is_open()` prefix match for `/static/*` |
| `.../src/lead_desk/web/templates/base.html` | Modified | tokens link, logo nav, product tag, `--btn-ink`, brand-navy headings |
| `.../src/lead_desk/web/templates/login.html` | Rewritten | Branded login card |
| `.../tests/test_branding.py` | Created | 6 branding tests |

---

## Current Status

Live on `brisken-lead-desk.fly.dev`. All branded surfaces verified over HTTP and visually via screenshot in both themes. The engine (campaigns, cadence, kill switch) is completely untouched by this change — this was a pure presentation-layer port. Lead Desk 4d (Graph sender + cloud capture, shipped earlier the same day, PRs #239/#240/#242) remains dormant behind the kill switch; that status is unaffected by branding.

---

## Next Steps

1. Nothing required for branding — it's done. Optional: mention to Dirk/Matthias that the internal tool now carries the Brisken look, next time either logs in.
2. Carried over from the 4d build (unrelated to branding, still open): schedule the owner-present watched send-gate drill on the Graph path before any real send; this is the sole remaining blocker on the first Graph-path campaign.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/static/tokens.css`
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/templates/base.html`

### Open Questions
None for this piece of work.

### Working Notes
- Playwright MCP's `browser_take_screenshot` saves to the MCP server's cwd (repo root here), not the session scratchpad — always `mv` the result into `.scratch/` after capture.
- The Playwright session is attached to the user's live Edge profile (their other tabs, e.g. Planner, are open there); work only in a freshly-navigated tab and `browser_close()` only that tab.
- The local throwaway server used for the board screenshot (`lead-desk-web --port 8791 --data <scratchpad>/ld-brand-demo`) was stopped via `TaskStop` after use; its data dir has no PII (empty DB, gate off).

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/243
- Precedent: expense-recon branding PR #228 (`brisken p1: ... Brisken branding`)
- Live app: https://brisken-lead-desk.fly.dev

---

## How to Continue

Nothing pending on this thread. If picking Lead Desk work back up, the live item is the 4d send-gate drill (see `project_lead_desk_4d_graph_send` memory) — not branding.

---

## Strategic Feedback

### What Worked Well This Session
- Having a very recent, structurally identical precedent (expense-recon branding, one day prior) made this a low-risk, high-confidence port rather than a design exercise — same tokens, same route pattern, same test shape, done in one clean PR.

### Suggestions
- None specific to this piece.

### System Health
- Autonomy score: 0 — fully autonomous (no corrections; one stale background-task wakeup was correctly recognized as already-completed work and answered without redoing anything).
