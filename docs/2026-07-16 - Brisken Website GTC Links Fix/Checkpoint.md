# Checkpoint: Brisken Website GTC Links Fix

**Date:** 2026-07-16
**Status:** COMPLETE — live on brisken.com, PR #241 merged

---

## Summary
Executed Dirk's Teams task (due 2026-07-16): fixed the footer terms links on brisken.com. The versioned GTC document (enGLOBAL.V09-2019-10, 16 pages) sits behind the old "Market Data Hub Terms" link; that link is now labeled "General Terms & Conditions" and the separate "Terms & Conditions" link (incomplete, unversioned 9-page PDF) is removed.

---

## What Was Done This Session
### Verification before edit
1. Located the links in `workspace/clients/brisken/website/treasury.html` footer (only page carrying them; onepilot.html has none).
2. Text-extracted both PDFs (pypdf) to confirm Dirk's read: `brisken-market-data-hub-terms.pdf` = full versioned GTC; `brisken-cloud-services-gtc.pdf` = incomplete unversioned copy.
3. Confirmed live www.brisken.com footer matched the repo state before editing.

### Edit + ship
1. Renamed the link to "General Terms &amp; Conditions" (href unchanged — the old WordPress redirect in vercel.json keeps resolving), removed the incomplete-GTC link, bumped footer stamp to 2026-07-16.
2. `validate-html.py` 0 hits. Committed via isolated worktree off origin/main (branch `client/brisken/website-gtc-links`) to avoid entangling the lead-desk-cockpit WIP in this clone; PR #241, CI green, squash-merged (94754a6); worktree + branch cleaned up.
3. Deployed Vercel `brisken-onepilot` production with `VERCEL_BRISKEN_TOKEN` from the gitignored Brisken context/.env (site is NOT git-connected; deploys publish the local tree).
4. Live verification: footer shows Privacy Statement / General Terms & Conditions / Accenture case study; GTC PDF serves 200 (215 KB); stamp 2026-07-16.

---

## Key Decisions Made
### Keep the incomplete PDF file hosted, remove only the link
- **Choice:** `brisken-cloud-services-gtc.pdf` stays in /docs; only the footer link was removed.
- **Rationale:** Dirk's instruction was link-scoped, and a legacy Wix-era redirect in vercel.json still points at the file. Removing it is a separate decision for Dirk.

### Deploy from the worktree, not the shared clone
- **Choice:** `vercel deploy --prod --cwd <worktree>/website` from the clean worktree (main + this fix only).
- **Rationale:** Vercel publishes the local tree; the main clone carries other sessions' WIP. Also verified the website folder was identical between origin/main and the cockpit branch first (no unmerged drift — the 2026-06-21 direct-deploy commits are in main).

### Planner check-off NOT performed
- **Choice:** Dirk's Planner/Teams task left unchecked.
- **Rationale:** state-changing write in Brisken's live tenant = invasive; needs an explicit per-action owner yes.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/website/treasury.html | Modified (PR #241, merged) | Footer GTC link rename + incomplete-link removal + date stamp |

---

## Current Status
Done and verified live. brisken.com footer now carries one terms link, "General Terms & Conditions", pointing at the versioned GTC. Platform: expense-recon custom SaaS, ops budget TBD (not a workflow-engine op count), last assessed 2026-05-24.

---

## Next Steps
1. Optional, gated: mark Dirk's Planner task "Fix GTC links on website" complete via Graph — invasive tenant write, needs owner yes.
2. Optional, Dirk's call: delete or keep `/docs/brisken-cloud-services-gtc.pdf` (still directly reachable; a vercel.json legacy redirect points at it).
3. Log this session's time via /comd_brisken-hours when convenient.

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/website/treasury.html (footer, lines ~1283-1291)
- workspace/clients/brisken/website/vercel.json (redirects incl. the legacy GTC path)

### Open Questions
- Should the incomplete GTC PDF be removed from hosting entirely (breaks the legacy `/_files/ugd/...` redirect)?

### Working Notes
- Deploy path for brisken.com: Vercel project `brisken-onepilot` (org team_MNNYUo2DofKqKUISX0X01rre, scope matthias-neumanns-projects), token `VERCEL_BRISKEN_TOKEN` in `workspace/clients/brisken/context/.env`, `.vercel/project.json` is NOT tracked — copy it into any worktree before deploying. Site serves brisken.com (→ /treasury) and onepilot.brisken.com (→ /onepilot) via host rewrites.
- `gh pr merge` returned empty output; remote merge succeeded (known gotcha — verify with `gh pr view --json state`).

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/241
- Live: https://www.brisken.com/ (footer)

---

## How to Continue
Nothing pending on this task. If Dirk wants the incomplete PDF fully unreachable, remove the file + its redirect from vercel.json and redeploy (same worktree + token path as above).

---

## Strategic Feedback

### What Worked Well This Session
- The forwarded Teams screenshot plus "here" was enough: source verification (PDF text extraction) caught exactly what made the rename safe, and the whole chain (edit → PR → CI merge → deploy → live verify) ran without a single user touch.

### Suggestions
- The brisken.com deploy knowledge (token env var name, non-git-connected project, worktree deploy pattern) lived only in session logs until now; it's in this checkpoint's Working Notes — worth a `reference_` memory if the site keeps getting edits.

### System Health
- The cd-guard hook blocks `cd X && ...` but not `cd X; ...` or a standalone `cd` — exactly that gap caused this session's only real friction (persisted cwd broke two follow-on commands). Extending the guard pattern is the recurrence-kill.
- Autonomy score: 0 user interventions — fully autonomous; 3 friction events, all agent/hook-detected.
