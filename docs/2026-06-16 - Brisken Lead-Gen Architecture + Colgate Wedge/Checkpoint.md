# Checkpoint: Brisken Lead-Gen Architecture + Colgate Wedge

**Date:** 2026-06-16
**Status:** p2 lead-gen hardened + campaign architecture built out; Colgate set as the focus wedge. Pre-contact, gated on Dirk. Branch `client/brisken/lead-gen-onepilot` (NOT main).

---

## Summary
Hardened the p2 OnePilot lead-gen plan against the 2026-06-12 red-team (honesty + kill gates + attribution + tiers), then built the missing campaign architecture (AEO substrate, Dirk enabler pack, the forwardable one-pager) to a presentable state. Set Colgate as the first account to land and built its execution dossier, catching a stale-sponsor error (Elaine Paik left Colgate Dec 2023) before it reached outreach.

---

## What Was Done This Session

### Hardening (red-team findings A/B/C, baked in)
1. Deck: cold demo terminus no longer claims the >90% warm close ("fed into your close motion"); stat-card labelled "your figure"; Honest Expectations gained the population-split (sourced leads close below warm inbound); "Agreed" -> "your offer as we understood it".
2. Spec: attribution window 12mo -> 18mo from demo date, scoped to a dated account-lock list so "sourced" is falsifiable.
3. Kill gates G1 wk4 / G2 wk8 / G3 wk12 added to orchestration §5.1 and the deck (a defined stop, not an open-ended grind).
4. Radar §6 retagged to §5: only the two write-confirmed-vendor accounts are A1 (Colgate, Corteva); the five vendor-unconfirmed (J&J, Ford, Toyota, Penn, Amtrak) dropped A2 -> B.

### Architecture build (Lane 1, autonomous, zero contact)
5. AEO substrate (`context/lead-generation/aeo-substrate.md`): 30 buyer problem-queries mapped to product, Q&A page spec + 3 exemplar answer blocks, SAP Store AEO + review-seeding plan, third-party presence plan (SAP Community is the dominant cited surface). Grounded in real buyer phrasing via web research.
6. Dirk enabler pack (`context/lead-generation/dirk-enabler-pack.md`): SAP co-sell business case + a 6-vendor relationship matrix (the warm-channel decisions only Dirk can make).
7. Forwardable one-pager (`deliverables/mdh-forwardable-colgate.html`): the hottest A1 account as the concrete exemplar of what travels inside a buying committee. HTML validated, 0 hits.

### Colgate wedge (the focus account)
8. Built `context/lead-generation/account-colgate.md`: verified trigger (live enterprise S/4HANA migration, five ECC -> one digital core), Bloomberg confirmed in their own postings, buying committee mapped.
9. CAUGHT + CORRECTED a stale sponsor: the radar named Elaine Paik (VP & Treasurer), but she left for Impossible Foods (CFO) Dec 2023. Corrected to Gina Grant (current Treasurer) across radar + outreach asset + dossier. Entry persona = GIT Finance Director (reports to CIO David Foster).

### Hygiene
10. Fixed date stamps 2026-06-15 -> 2026-06-16 (the actual day) across deck, specs, dossier; regenerated + content-verified the deck PDF.

---

## Key Decisions Made

### Build to presentable, do NOT contact Dirk yet
- **Choice:** Owner directive overrode the red-team's "email Dirk first" recommendation. Build the campaign + bake in the cheap fixes; engage Dirk only with a presentable package.
- **Rationale:** A concrete, hardened package (especially a worked Colgate example) makes the eventual go-live ask a far easier yes than an abstract plan.

### Colgate is the wedge, not just a target
- **Choice:** Focus the whole motion on landing Colgate first; use it as the worked example that collapses Dirk's go-live decision.
- **Rationale:** Only A1 (besides Corteva) with vendor confirmed in writing; live enterprise migration; the asymmetry (one ~$99/mo seat to test) is the pitch.

### The Dirk ask is operational, not financial
- **Choice:** When engaging Dirk, ask only for go-live operationals (sending identity, Sales Nav seat, demo owner, Bloomberg-relationship status); defer commission to terms after leads prove quality (owner's delivery-before-compensation sequencing).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| deliverables/lead-gen-strategy-2026-06-12.html | Modified | Red-team honesty fixes, kill gates, AEO-prepared bullet, date |
| deliverables/lead-gen-strategy-2026-06-12.pdf | Regenerated | Reflect hardened deck + corrected date |
| deliverables/mdh-forwardable-colgate.html | Created | Forwardable MDH one-pager (Colgate exemplar) |
| specs/1-spec/p2-bant-lead-generation.md | Modified | Attribution window 12->18mo + lock list; hardening note; date |
| specs/2-build/p2-lead-gen-orchestration.md | Modified | Kill gates §5.1; date (also carries a WhatsApp-exclusion note) |
| context/lead-generation/aeo-substrate.md | Created (gitignored) | The always-on AEO trust layer |
| context/lead-generation/dirk-enabler-pack.md | Created (gitignored) | Co-sell case + vendor matrix |
| context/lead-generation/account-colgate.md | Created (gitignored) | Colgate execution dossier |
| context/lead-generation/targeting-radar.md | Modified (gitignored) | Tier retag + Elaine->Gina fix |
| context/lead-generation/mdh-outreach-assets.md | Modified (gitignored) | Elaine->Gina sponsor fix |

Commits (feature branch, NOT main): `9ddced6` (architecture build), `e845b80` (date fix).

---

## Current Status
The p2 campaign is presentable: deck hardened, supporting assets built, Colgate dossier ready. Everything is pre-contact and gated on Dirk. The context/ architecture files are local (gitignored by design); the deck, PDF, forwardable, and two specs are committed to the feature branch. The branch does NOT merge to main (G1 discipline: pre-terms client strategy stays on its own branch).

No automation/orchestrator in play (manual-first service engagement); no ops/platform usage to report.

---

## Next Steps
1. **Owner decision: engage Dirk now or keep sharpening.** The package is presentable. Engaging Dirk requires the outreach-to-Dirk message (held per no-unrequested-drafts; draft on explicit go). Recommended: take Colgate to Dirk as the worked example.
2. (autonomous, if sharpening) Draft the full "Bloomberg into SAP TRM" AEO answer page (cluster A) ready to publish, the trust surround a Colgate buyer would hit.
3. (autonomous) The J&J/Ford/Toyota logged-in vendor scrape (promotes B->A1) + radar batch 2 (evidence-pack rows 1-8, 16-24). Optional depth; not needed for presentable.
4. (go-live, Dirk-gated) Provision one Sales Nav seat, name the Colgate GIT Finance Director + committee, first LinkedIn touch.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/lead-generation/account-colgate.md` (the focus account + committee, corrected)
- `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html` (the hardened deck)
- `workspace/clients/brisken/context/lead-generation/targeting-radar.md` (the spine, retagged)
- `workspace/clients/brisken/context/lead-generation/aeo-substrate.md` + `dirk-enabler-pack.md` (the new architecture)
- `workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md` (§2 terms, hardened)

### Open Questions
- Does the owner engage Dirk now with the Colgate-led package, or build more readiness first?
- The single missing commercial number (OnePilot list ACV) is still uncaptured; it gets settled at terms (delivery-before-compensation), not now.
- Gina Grant's exact current title to re-confirm at send (she is the strongest current-Treasurer candidate; Elaine Paik definitively departed).

### Working Notes
- Elaine Paik departure (Dec 2023, to Impossible Foods CFO) is the load-bearing correction: the radar/outreach asset had her as sponsor. Re-verifying every named persona at send is the discipline that caught it.
- Colgate trigger is enterprise-scale (five ECC -> one global S/4HANA digital core, "currently moving to S4"), stronger than the single expired job req. CIO David Foster leads GIT; the SAP-Treasury role reports to the GIT Finance Director.
- SAP Community (community.sap.com) is the dominant AI-citation surface for these buyer queries (Datafeed config, Monitor Bank Fees CAMT.086, TRM FAQ threads). Competitors in the answer-set: COMPIRICUS, StepStream (point interfaces), SAP-native Datafeed/Market Rates Management. OnePilot's honest differentiator: no-code, multi-vendor, governed, SAP Store-listed (NOT "SAP can't do this").
- AEO/SAP-Store/review execution is Dirk-gated (owned-property + customer-facing), so the substrate is built to "ready to publish," not published.
- The orchestration doc now carries a WhatsApp-as-channel exclusion note (evaluated, rejected for the wave-1 enterprise-SAP motion).

### Reference Materials
- Red-team review: `docs/2026-06-12 - Brisken Lead-Gen Red-Team Review/Checkpoint.md`
- Prior strategy pivot: `docs/2026-06-12 - Brisken Lead-Gen Strategy Pivot/`
- Colgate sources: Elaine Paik departure (Impossible Foods leadership; Comparably); David Foster CIO (SAPinsider, diginomica); S/4HANA five-instance consolidation (iTnews, Global Cosmetics News); FX/derivatives (Colgate FY2025 10-K, SEC cl-20251231).

---

## How to Continue
The campaign is presentable and Colgate is the wedge. The next move is the owner's: take the Colgate-led package to Dirk (which unblocks drafting the outreach-to-Dirk message), or keep sharpening autonomously (the cluster-A AEO answer page is the next build). Everything that actually touches Colgate is gated on one Dirk yes (sending identity + Sales Nav seat + demo owner).

---

## Strategic Feedback

### What Worked Well This Session
- The "build to presentable, verify before asserting" posture caught the Elaine Paik staleness before it became a credibility hit in outreach. Re-verifying named personas at the dossier stage (not at send) paid off immediately.

### Suggestions
- When you want the strategy explained for your own use (to relay to Dirk), say so up front; the first explanation defaulted to a dense strategy-memo register and needed a "human language" redo. A one-word cue ("plain") at the ask would skip the round-trip.

### System Health
- Two recurring patterns surfaced and were caught: the B1 deferral-phrasing reflex (stop-b1-gate held both times, as it has across the long-running cluster) and a human-voice/register drift on an in-chat explanation (the existing human-voice memory covers deliverable cells, not in-chat strategy explanations). The date-stamp slip (wrote the prior day) is a B4 gap with no structural catch for date values specifically.
- Autonomy score: 3 interventions this session (2 B1-hook deferral catches, 1 user voice-register correction); 1 self-caught date error.
