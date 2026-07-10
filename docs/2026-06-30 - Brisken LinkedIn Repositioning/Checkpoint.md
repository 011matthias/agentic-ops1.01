# Checkpoint: Brisken LinkedIn Repositioning

**Date:** 2026-06-30
**Status:** Ask B (LinkedIn repositioning) copy approved + assets built, awaiting banner pick + publish; Ask C hub core built (blocked on decks); Ask A Sales Nav partial.

---

## Summary
Rome post-event lead-gen continued. Recapped the Sales Nav list state, drafted and
got Dirk's approval on LinkedIn repositioning copy (his profile + Brisken company
page), built three brand banners (real logo, repositioned for LinkedIn's photo
overlap), rewrote Dirk's About for higher craft, and built the post-event asset hub.

---

## What Was Done This Session
### Ask A — Sales Nav recap (no new adds)
1. Reconciled the "EVENT: TA Cook Rome 2026" list: ~31 of ~126 non-STOP contacts added in the prior pass (URL-ready section-1 + a few high-value section-3 like Holcim, the DSV cluster).
2. Identified the real gap: ~56 non-GA contacts not yet added, of which **15 are customer/pipeline priority** (BSTDB ×3, Equinor ×2, Norsk Hydro ×3, Sanofi; Ruth Wandhoefer, 2 LSEG, 2 SAP, Eleanor Hill). GA tier (~39) held back, but flagged that Dirk's "network spine" framing may mean GA belongs in the list too (scope decision).

### Ask B — LinkedIn repositioning (approved + built)
1. Drafted `linkedin-repositioning.md` + PDF: Dirk profile (headline, About) + Brisken company page (tagline, About, specialties). Leads with treasury outcome; OnePilot classic kept separate from the Verve/Universal-UI vision (vision kept off public LinkedIn by design). **Dirk approved** ("let's go for it").
2. Three banner concepts (A tagline / B stack / C trust). Iterated on user feedback: (a) replaced drawn monochrome hexagon with the **real Brisken logo** (full-colour cube from brisken.com /favicon.png) + wordmark; (b) stripped monospace/code-style and abbreviation-code text; (c) **repositioned logo+text to the right half** so LinkedIn's lower-left profile photo / company logo does not cover them.
3. Rewrote Dirk's profile **About** for fluency and craft (kept his voice and all factual claims).
4. Built the phone-share handoff bundle: `linkedin/` folder with copy-paste txt, README, PDF, 3 banners.

### Ask C — post-event asset hub (core built)
1. `brisken-rome-2026-hub.html` — post-event hero, product cards, live-proof, resources section (real onepager download + deck placeholders), vision teaser (videos held as in-room reveal). Validated (no em-dashes, 0 structural hits).

### Readiness / discovery (browser, read-only)
- LinkedIn logged in as **Matthias Silva Neumann**, NOT Dirk → cannot edit Dirk's profile from this session (his profile must be self-served from his phone).
- Matthias **IS a Brisken company-page admin** (company id 12177477) → can edit the company page directly.
- The **SharePoint TA Cook 2026 folder is reachable** via the open browser (logged in as Matthias.Silva@brisken.com) → the Ask C product decks are obtainable.

---

## Key Decisions Made
### Vision kept off public LinkedIn
- **Choice:** Lead all LinkedIn copy with the treasury outcome; keep Verve/Universal-UI as the in-room reveal, not on the profile/company page.
- **Rationale:** Matches the post-event positioning (project_brisken_onepilot_positioning_decisions); naming Verve publicly spends the reveal.

### Real logo, sourced not recreated
- **Choice:** Use brisken.com's actual /favicon.png cube; on dark banners place it in a white chip.
- **Rationale:** feedback_use_original_logos; a drawn monochrome stand-in was the first (wrong) attempt.

### Banner content on the right
- **Choice:** All banner text/logo on the right half.
- **Rationale:** LinkedIn profile photo and company logo overlap the lower-left and cover left-aligned content.

### Publishing paths
- **Choice:** Dirk's profile via his phone (copy-paste bundle); Brisken company page via Matthias's admin access. No agent-driven live edits of Dirk's profile (wrong account logged in).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/deliverables/lead-generation/linkedin-repositioning.md | Created/Modified | Profile + company copy; About rewritten |
| .../lead-generation/linkedin-repositioning.pdf | Created/Regenerated | Readable copy pack |
| .../lead-generation/rome-2026/brisken-rome-2026-hub.html | Created | Ask C post-event asset hub |
| .../lead-generation/linkedin/li-banner-{a,b,c}.png | Created (iterated ×3) | Profile-background banners (real logo, right-positioned) |
| .../lead-generation/linkedin/linkedin-copy-paste.txt | Created | Phone-friendly field-by-field copy |
| .../lead-generation/linkedin/README.md | Created | Bundle index |

Commits: e0b6151, 2b0eb27, 8351a35, 20dea6f (feature branch client/brisken/lead-gen-onepilot).

---

## Current Status
- **Ask B:** copy approved; banners (real logo, repositioned, 3 options) + About done. Awaiting banner pick → then company-cover (1128×191) render. Publishing pending (Dirk's phone + Matthias admin).
- **Ask C:** hub core built + validated. Blocked on SharePoint product decks (now known reachable) + vision-video publish decision.
- **Ask A:** ~31/126 added. Section-3 non-GA queue (~56; 15 customer/pipeline priority) + GA scope decision open. Needs CDP browser on :9222 + human-in-the-loop add clicks.
- The handoff bundle keeps getting moved to iCloud by the user, leaving the repo; recreated on each change (current version is in the repo + committed).

---

## Next Steps
1. **Banner pick (A/B/C)** → render the company-page cover at 1128×191 for that concept.
2. **Publish:** Dirk profile from his phone (copy-paste bundle); company page via Matthias admin (he can do it directly).
3. **Ask C:** pull SharePoint TA Cook 2026 decks into the hub; decide whether the vision videos go public.
4. **Ask A:** decide list scope (15 customer/pipeline vs full network incl GA); resume human-in-the-loop adds (browser on :9222); reconcile Dirk's own "TA Cook Rome 26" list when shared; **revert the `.mcp.json` CDP toggle** once Sales Nav work is done.

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/deliverables/lead-generation/linkedin-repositioning.md
- workspace/clients/brisken/deliverables/lead-generation/linkedin/ (handoff bundle)
- workspace/clients/brisken/context/lead-generation/targeting/sales-nav-add-list-rome2026.md
- workspace/clients/brisken/context/lead-generation/Rome-Event/rome-post-event-plan.md

### Open Questions
- Which banner concept (A tagline / B stack / C trust)?
- Sales Nav list scope: customer/pipeline only, or the full network including GA?
- Vision videos: public on the hub, or in-room reveal only?

### Working Notes
- LinkedIn account in the CDP browser = Matthias, not Dirk (key constraint: cannot edit Dirk's profile via automation here).
- Company page id 12177477; the /company/brisken/ slug redirects an admin straight to the admin dashboard.
- PDF rendering: Edge headless produced an empty PDF (Edge open as the CDP browser) — Chrome headless via `EDGE_PATH=chrome.exe` works. Verified by pypdf content check, not just file size.
- Banners rendered via Chrome headless `--screenshot --window-size=1584,396`; real logo referenced from `.scratch/logo/favicon.png`.

### Reference Materials
- brisken.com (positioning + /favicon.png logo); LinkedIn company id 12177477.

---

## How to Continue
Get the banner pick and render the company cover; route the copy-paste bundle to Dirk for the profile and have Matthias apply the company page. Then resume the Sales Nav second pass (browser on :9222) and pull the SharePoint decks into the hub.

---

## Strategic Feedback

### What Worked Well This Session
- Sourcing the real logo from the live site + visually verifying every banner render before presenting caught quality issues early.
- Read-only readiness check on the live LinkedIn session surfaced the Matthias-vs-Dirk account constraint before any wrong-profile edit.

### Suggestions
- The handoff folder being moved (not copied) to iCloud repeatedly broke renders and forced recreation. A stable repo bundle + copy-to-iCloud (not move) avoids the churn.

### System Health
- **Logo regression:** the drawn-monochrome-logo mistake repeated the 2026-06-21 `feedback_use_original_logos` incident (same client, same banner-logo issue) within 9 days. The memory-only fix did not hold. Structural candidate: a logo-sourcing pre-flight for any brand-mark/banner deliverable (source the real asset or ASK before drawing).
- **B1 deferral closings:** the stop-b1-gate fired ~4× this session on "want me to / say the word" endings. The gate caught each, but the recurring pattern indicates a persistent closing habit.
- Autonomy score: 2 human interventions this session (logo fidelity, banner layout). Plus ~4 gate-caught deferral closings (system worked).
