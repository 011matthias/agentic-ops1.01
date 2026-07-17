# Checkpoint: Brisken SAP One-Pager Redesign

**Date:** 2026-07-13
**Status:** Shipped — live on resources.brisken.com, byte-verified, pushed to remote

---

## Summary
Rebuilt the six SAP one-pagers on resources.brisken.com so each has its own
composition (not one shared skeleton with a swapped middle diagram), filled
each to full A4, deployed to production, and pushed the source. Driven by four
rounds of user design feedback: vary structure → no top room → fill the bottom
→ still too short.

---

## What Was Done This Session
### Redesign (tools/brisken-sap-onepagers.py)
1. Replaced the single centred template with six distinct body layouts:
   market-data-hub (asymmetric left-rail + convergence), smart-trading
   (left editorial + 01/02/03 timeline band), remittance (before→after
   diptych + dark proof bar), bank-fee (dashboard: charged-vs-agreed variance
   bar chart with hatched overcharge zone + line-by-line ledger),
   treasurycentral (radial cockpit: centre hub + six spokes), onepilot (dark
   architecture panel).
2. Added a credentials/proof band (SAP Co-Innovation Partner · SAP Store ·
   ISO 27001 · SOC 1 Type II · Live with customers) at the foot of every sheet.
3. Added "How it works" 3-step strips to the two thinnest sheets (MDH, Bank Fee).
4. Switched vertical model to `justify-content:space-between` so content fills
   top-to-bottom (after a wrong "top-anchor / pinned bottom" detour).
5. Hardened the tool: `main()` now `args.out.resolve()` (Chrome --print-to-pdf
   needs an absolute target; a relative --out silently writes to Chrome's cwd).

### Ship
6. Rendered all 6 → 1-page each, banned-content gate PASS, zero em-dashes,
   copy unchanged from the gated set.
7. Regenerated into `deliverables/lead-generation/sap-assets/` and copied to
   `resources-site/` under the short names.
8. Deployed resources-site to production with the user-provided Vercel token
   (account `matthias-5647`, the team that owns the project). Verified: all 6
   PDFs on resources.brisken.com return 200 with byte counts matching local.
9. Pushed the redesign commit to the remote feature branch via an isolated
   worktree cherry-pick (`4086adc`), avoiding the stale/dirty local clone.

---

## Key Decisions Made
### Six bespoke compositions, shared frame
- **Choice:** Vary the body composition per product; keep header/logo, footer,
  font pairing and per-product accent constant.
- **Rationale:** The complaint was "same structure six times." A shared frame
  keeps it a product family while the body carries the variety.

### Fill with real content, not fabricated detail
- **Choice:** Fill the thin sheets with a credentials band + "How it works"
  steps drawn from existing true copy; refused to invent metrics/customers.
- **Rationale:** B4 — client-facing collateral; every claim traces to the
  gated copy. Steps reframe asserted facts as process, no new claims.

### Worktree cherry-pick to push
- **Choice:** Cherry-pick the one new commit onto the remote tip in a detached
  worktree, then push; did not rebase/stash the main clone.
- **Rationale:** Main clone was 6-ahead/84-behind with a dirty tree and live
  parallel worktrees (leadgen-task-6/7). 5 of the 6 local commits were
  byte-duplicates of the remote tip; only the redesign was new.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| tools/brisken-sap-onepagers.py | Modified | Six-layout redesign + proof band + step strips + space-between fill + `--out` resolve |
| workspace/clients/brisken/deliverables/lead-generation/sap-assets/brisken-{market-data-hub,smart-trading,remittance-advice-gate,bank-fee-portal,treasurycentral,onepilot}-onepager.pdf | Regenerated | Canonical deliverables |
| workspace/clients/brisken/resources-site/{market-data-hub,smart-trading,remittance-advice-gate,bank-fee-portal,treasurycentral,onepilot}.pdf | Regenerated | Live site short-name copies |

Committed local `eb557c9`; pushed to remote as `4086adc`.

---

## Current Status
Live and verified on resources.brisken.com (6/6 PDFs 200, byte-identical to
local). Source pushed to `client/brisken/lead-gen-onepilot` (remote tip
`4086adc`). This local clone's branch pointer is still on the old base
(`eb557c9`) — stale, do not push from it; up-to-date worktrees will pick up
`4086adc` on fetch.

---

## Next Steps
1. **Rotate the Vercel token** `vcp_3gG…` — pasted in plaintext this session,
   treat as exposed. Revoke + reissue in Vercel account settings.
2. Optional: share the refreshed resources.brisken.com set with Dirk if he is
   circulating SAP collateral for Rome follow-ups.
3. If future one-pager edits are needed, edit `tools/brisken-sap-onepagers.py`
   (source of truth) and re-run; it regenerates + gates all six.

---

## Context for Next Session
### Files to Read First
- tools/brisken-sap-onepagers.py (the generator; all layout logic + copy)
- workspace/clients/brisken/resources-site/index.html (links the short-name PDFs)

### Open Questions
- None blocking. The two thinnest sheets (MDH, Bank Fee) are filled with real
  content; packing them further would need genuinely new product detail.

### Working Notes
- Chrome headless is the only working PDF engine while Edge is open; the tool
  keeps an isolated user-data-dir. `--print-to-pdf` MUST be absolute (fixed).
- Vertical model that works: `main{display:flex;flex-direction:column}` +
  per-layout `justify-content:space-between` fills the page. Watch CSS
  specificity: a per-layout `.l-*{justify-content:flex-start}` silently
  overrides `main{space-between}` (this cost an iteration round — the "fill"
  didn't take until the layout rules were also flipped).
- resources-site Vercel project lives under account `matthias-5647`
  (org `team_MNNYUo2DofKqKUISX0X01rre`), NOT the `akkton`/`akktons-projects`
  login the CLI defaults to. Deploy needs that account's token/login.
- Live verify pattern: `curl -s -o /dev/null -w "%{http_code} %{size_download}"`
  per PDF vs local `stat -c%s` — byte-length match proves the new file shipped.

### Reference Materials
- Live: https://resources.brisken.com/ (noindex, public)
- Preview PDFs (gitignored): .scratch/onepager-preview/
- Related memory: [[project_brisken_resources_subdomain_and_dns]],
  [[reference_html_deck_pdf_chrome_when_edge_open]], [[feedback_use_original_logos]]

---

## How to Continue
The deliverable is shipped. If revising: edit the generator, run
`uv run tools/brisken-sap-onepagers.py` (writes sap-assets + gates), copy the
6 to resources-site short names, then `vercel deploy --prod --yes --cwd
"workspace/clients/brisken/resources-site" --token <matthias-5647 token>`, and
byte-verify against resources.brisken.com.

---

## Strategic Feedback

### What Worked Well This Session
- Self-QA-with-vision loop: rendering each PDF and reading it back as an image
  caught the Bank Fee label collision and the empty-band issues before the user
  saw them. The render→view→fix cycle is the right harness for visual work.
- The user's incremental, concrete direction ("no top room", "fill the bottom",
  "still too short") was fast to act on once each was pinned to a CSS lever.

### Suggestions
- For subjective visual redesigns, one upfront alignment on the vertical model
  (top-anchored vs filled vs framed) would have saved ~1 round. Consider stating
  the intended fill behaviour and confirming before iterating on renders.

### System Health
- Autonomy score: 3 human interventions this session (1 B1 deferral phrasing
  caught by stop-b1-gate; 2 slow-paths — the relative `--out` Chrome miss and
  the CSS-specificity override that delayed the fill). Not elevated.
- The generator now self-heals the `--out` footgun (`.resolve()`). No structural
  gap opened; the CSS-override slow-path is agent discipline, not tool-fixable.
- Deploy access split (resources-site under a different Vercel account than the
  CLI default) is a recurring friction surface — the correct account/token is now
  documented here and in the resources-subdomain memory.
