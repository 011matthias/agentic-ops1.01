# Checkpoint: Brisken Marketing Website Prototype

**Date:** 2026-06-16
**Status:** Prototype v1 built (content correct, aesthetic wrong); restyle prompt handed back. Pre-build for v2.

---

## Summary
Researched how the category leaders market (Kyriba, HighRadius, FIS, Serrala, TIS, the SAP-ecosystem ISVs), turned it into a marketing plan for Brisken's OnePilot, and started building a Brisken marketing website. The first website prototype carried the right content but the wrong look (matched our proposal deck, not brisken.com). Direction now locked: it is BRISKEN's own OnePilot site, aesthetic follows brisken.com, content is our Brisken marketing strategy. A restyle prompt was written for the v2 edit.

---

## What Was Done This Session
### Research + strategy
1. Fanned out three competitive-research agents over TMS leaders, AI-finance challengers, and SAP-ecosystem ISVs; distilled the recurring playbook (name the problem, publish proprietary research, govern the AI, named/numbered proof, ride the SAP relationship + migration).
2. Gap analysis of the p2 lead-gen plan against that playbook; four real gaps surfaced, then re-explained in plain language on request.
3. Named the enemy: **"shadow integrations"** (hand-keyed data + brittle scripts moving financial data into SAP), with the category "governed, no-code financial-data orchestration for SAP."

### Deliverables
4. **The Shadow Integration Report (benchmark), N=21 pilot.** Three data-research agents read public SAP-treasury job ads; deduped to 21. Result: 17/21 describe building or hand-running the data plumbing into SAP, 13/21 tied to an S/4HANA migration, 8/21 name a market-data vendor. Saved with method + sources + honest caveats.
5. **Marketing Plan tab** added to the Dirk strategy deck (two-tab layout: Campaign Engine + Marketing Plan), validator-clean, zero em-dashes.
6. **Website blueprint** + **website prototype v1** (Brisken/OnePilot, all the strategy content, FAQ JSON-LD, theme/search/print). Content correct; aesthetic matched the deck, not brisken.com.
7. Studied brisken.com's real aesthetic (WebFetch): deep navy ~#003D7A + accent blue on white, split hero with abstract blur graphic, sharp corners (2 to 4px), logo trust strip, soft-shadow card grids, RAPSODY package with a right-aligned week count, cert-badge footer.
8. Wrote the **restyle prompt** to take prototype v1 to brisken.com's aesthetic while keeping the content.

### Course corrections
9. A detour into an UnpauseAI lead-gen landing page (from an attached brief) was stopped by the user: the deliverable is Brisken's site, not UnpauseAI's.

---

## Key Decisions Made
### Named enemy = "shadow integrations"
- **Choice:** One owned problem-name across deck, site, AEO, outreach.
- **Rationale:** The leaders all own a problem (Kyriba "liquidity gridlock", HighRadius "autonomous finance"); OnePilot was selling itself as a generic "platform."

### The benchmark is built from the radar's own job-ad corpus
- **Choice:** Turn the weekly targeting-radar job-ad sweep into a published stat.
- **Rationale:** Proprietary research is the highest-leverage marketing flywheel and the dataset already exists; numbers must stay real (currently a labeled N=21 first sample).

### The website is Brisken's OnePilot site, aesthetic = brisken.com
- **Choice:** Restyle prototype v1 to brisken.com's visual language; keep the content.
- **Rationale:** It is Brisken's own site, so matching their brand is correct (unlike the UnpauseAI detour, where claiming SAP/ISO/SOC marks would have been false).

---

## Files Modified
Deliverables live in the `agentic-ops1-recon-main` worktree; the benchmark in the `agentic-ops1` (lead-gen branch) worktree. Note the split.

| File | Action | Purpose |
|------|--------|---------|
| `…recon-main/workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html` | Modified | Added the two-tab layout + Marketing Plan tab |
| `…recon-main/…/deliverables/brisken-onepilot-website-blueprint.md` | Created | Build blueprint for the OnePilot site |
| `…recon-main/…/deliverables/brisken-onepilot-website-prototype.html` | Created | Website prototype v1 (content correct, aesthetic = deck; awaits restyle) |
| `workspace/clients/brisken/context/lead-generation/shadow-integration-benchmark.md` | Created | The benchmark dataset, method, N=21 pilot numbers |

---

## Current Status
The marketing strategy and content are settled. Prototype v1 has the right content but the wrong look. The restyle prompt (in the conversation) is the immediate next action: edit `brisken-onepilot-website-prototype.html` to brisken.com's aesthetic, keep content. No client contact; p2 stays pre-Dirk-gate. Branch: `client/brisken/lead-gen-onepilot` (not main).

---

## Next Steps
1. Run the restyle prompt on `brisken-onepilot-website-prototype.html` (navy/blue, split hero + abstract graphic, sharp corners, logo trust strip, card grids, time-to-value block, cert footer). Validate-html + em-dash grep + open in Edge.
2. Widen the benchmark from 21 to ~50 US-only SAP-treasury ads (radar sweep + scrapling/agent-browser on walled boards) for a publishable figure.
3. The remaining marketing moves: name + number the AI Digital Workforce (one real customer metric, Dirk-gated) and merchandise the SAP relationship harder (Endorsed App, SAPinsider, co-content).
4. Reconcile the worktree split: decide whether the website deliverables and the benchmark should sit on one branch.

---

## Context for Next Session
### Files to Read First
- `…recon-main/workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html` (the file to restyle)
- `…recon-main/…/deliverables/brisken-onepilot-website-blueprint.md` (the build plan)
- `workspace/clients/brisken/context/lead-generation/shadow-integration-benchmark.md` (the benchmark)
- `…recon-main/…/deliverables/lead-gen-strategy-2026-06-12.html` (Marketing Plan tab = the source of the site's content)
- `workspace/clients/brisken/context/lead-generation/brisken-product-catalog.md` (all product facts)

### Open Questions
- How closely should the OnePilot site mirror brisken.com? brisken.com sells the treasury-consulting business; this site sells the OnePilot products. Same brand, evolved positioning. Worth a Dirk check before publish.
- Real AI customer metric for the AI Digital Workforce section (Dirk-gated; currently qualitative).
- Production build path: per the landed-client split this should later move to `agentic-dev1`, not stay a self-contained HTML.

### Working Notes
- brisken.com aesthetic captured via WebFetch (palette/layout above). The restyle is navy + sharp corners + split hero + logo strip, dropping the deck's green/orange/purple multi-accent.
- No dedicated UnpauseAI lead-gen plan file exists in the repo; the UnpauseAI positioning lives in `workspace/projects/platform/upwork-agency/profile-copy.md` + `service-descriptions.md`. That detour is dropped.
- Benchmark numbers are real but a small, consulting-skewed sample; the prototype labels them "first sample."

### Reference Materials
- brisken.com (aesthetic reference)
- Restyle prompt: in this conversation, just above the checkpoint call.

---

## How to Continue
Open the prototype, run the restyle prompt against it, validate, open in Edge, and show the user. Then widen the benchmark. Everything is pre-Dirk-gate; no outreach.

---

## Strategic Feedback

### What Worked Well This Session
- The parallel research-agent fan-out (3 agents per pass) produced citable, deduped findings fast; the benchmark came together the same way.
- The user's plain-language correction sharpened the deliverable; the gap analysis landed once stripped of jargon.

### Suggestions
- When a task says "aesthetically similar to {site}", name the reference site explicitly and fetch it before building. The first prototype matched the wrong referent because the reference was assumed, not fetched.

### System Health
- The website deliverables and the benchmark ended up in two different worktrees (recon-main vs the lead-gen branch). That split is a drift risk for `/resume`; worth consolidating the brisken website work onto one branch.
- Autonomy score: 2 human interventions this session (both direction corrections: wrong aesthetic referent, then wrong site subject). Not elevated.
