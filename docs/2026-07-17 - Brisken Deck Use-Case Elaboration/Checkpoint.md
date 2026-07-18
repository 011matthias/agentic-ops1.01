# Checkpoint: Brisken Deck Use-Case Elaboration

**Date:** 2026-07-17
**Status:** Shipped (PR #266 merged to main); 10/10 decks live in Asset Testing; 2026_PPTX reorg at 31/32 (loop retrying)

---

## Summary
Deepened and roughly doubled the use-case content across the five rebuilt Brisken product decks, grounding every use case in the real Brisken customer base (Zoho active cloud subscriptions), and re-uploaded all five to SharePoint `2026_PPTX/Asset Testing` for Dirk's review.

---

## What Was Done This Session
### Client-context grounding
1. Mined live Zoho CRM (`context/zoho-crm.json`): 465 accounts, 143 real customers, 41 on active cloud subscription. Extracted the real industry spread (Food & Drink 6, Chemicals 5, Automotive 3, Financial Services 3, Fashion 3, Oil & Gas 3, Agriculture 2, Pharma 2, Commodity 2 among active subscriptions).
2. Confirmed the reference deck's three named success stories (chemicals funding, agricultural remittance, FSI market-data) each map to a real active-customer industry.

### Use-case elaboration (spec edits)
1. **Smart Trading** 1 → 3 use cases: One FX Trade (elaborated six-step journey); Derivatives & Securities (financial-services base); OTC Commodity Swaps (commodity + oil & gas base).
2. **Market Data Hub** 3 → 4: added Credit & Counterparty Data (financial-services base).
3. **MDH Commodities** 1 → 2: elaborated the composite curve; added Valuation & Exposure Prices (commodity/oil & gas base).
4. **Digital Co-Worker** 4 → 5: added Bank Statement Intake (logistics base); elaborated Intercompany Funding (chemicals, real story) and Cash-Management demo.
5. **Overview**: elaborated the Intercompany Funding one-pager; folded a sourced customer-base credential line into the hierarchy caption.

### Build + ship
1. Rebuilt all five (library + compose + banned-terms gate + COM render + PDF gate): fonts 10 parts OK, rIds OK, no hidden slides, PASS on pptx and PDF.
2. QA-eyeballed the new slides; caught and shortened three use-case titles that ran behind the top-right logo lockup (Anomaly Catch and Governance; Derivatives and Securities; OTC Commodity Swaps).
3. Uploaded all 10 files (5 pptx + 5 pdf) to Asset Testing via CDP :9223; 10/10 verified.
4. Shipped as PR #266 (resolved a squash-merge conflict inherited from #264; CI green; squash-merged to main).

---

## Key Decisions Made
### Use cases are capability one-pagers; only the three real deployments carry customer attribution
- **Choice:** New use cases describe capabilities (sourced from Dirk's own reference deck) set in a *generalized, anonymized* industry the CRM confirms as a paying customer. The three named success stories (chemicals/agricultural/FSI) keep their real attribution. No fabricated per-use-case deployments.
- **Rationale:** B4 + Dirk's explicit "no overselling something we do not really have" directive. Per-deck breadth credential lines name only industries with real active cloud subscriptions.

### Terminology anchored to brisken.com
- **Choice:** AI application = "AI Digital Workforce" everywhere (hierarchy box + captions); "TreasuryCentral, the shipped edition of OnePilot"; "Brisken Smart Trading (BST)".
- **Rationale:** User directive — source of truth is brisken.com and up-to-date assets.

### DCW deck keeps its filename/title, hierarchy uses the site name
- **Choice:** hierarchy/captions say "AI Digital Workforce"; the DCW deck's filename stays "Digital Co-Worker" for parity with the file it replaces. One parameter flip when Dirk decides on a full rename.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| deckgen/specs/smart-trading.yaml | Modified | 1 → 3 use cases; BST caption; shortened 2 titles |
| deckgen/specs/market-data-hub.yaml | Modified | +Credit & Counterparty Data; title fix; breadth caption |
| deckgen/specs/mdh-commodities.yaml | Modified | curve elaborated; +Valuation & Exposure Prices |
| deckgen/specs/digital-co-worker.yaml | Modified | +Bank Statement Intake; Funding + Cash-Mgmt elaborated |
| deckgen/specs/overview-revision.yaml | Modified | Funding one-pager elaborated; sourced credential caption |
| deckgen/make-library.py, library-manifest.json | Modified | pc-app-dw = "AI Digital Workforce" (terminology pass) |
| workspace/clients/brisken/status/p2-product-decks.md | Modified | workstream status roll-up |

---

## Current Status
Five product-deck proposals (`... 2026-08 PROPOSAL.pptx/.pdf`) live in `2026_PPTX/Asset Testing`, 10/10 verified, awaiting Dirk's review. Use-case elaboration + terminology pass merged to main (PR #266). The 2026_PPTX deck-library reorg is at 31/32: one file, `Brisken - Digital Co-Worker 2026-07.pptx`, is still locked by Dirk's open PowerPoint; the retry loop (pid alive, every 30 min) will complete the last move once he closes it.

---

## Next Steps
1. Notify Dirk that the five revised decks are in Asset Testing (draft prepared; awaiting explicit send confirmation — invasive-action gate).
2. Let the reorg loop finish the last move once Dirk closes `Brisken - Digital Co-Worker 2026-07.pptx`; then report 32/32.
3. On Dirk's review: per-deck swap runbook (live file → Archive, drop "PROPOSAL" suffix, promote to Brisken Product Assets) — invasive, per-deck approval only.

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/automations/lead-generation/deckgen/README.md
- workspace/clients/brisken/automations/lead-generation/deckgen/specs/*.yaml
- workspace/clients/brisken/status/p2-product-decks.md

### Open Questions (for Dirk)
- Full rename of the Digital Co-Worker deck to "AI Digital Workforce"? (currently one parameter flip)
- BTP wording: keep "on SAP's own cloud" everywhere, or restore "SAP Business Technology Platform" per deck? (badge image unchanged)
- Which decks to promote from Asset Testing to Brisken Product Assets (the swap runbook, per-deck)?

### Working Notes
- Reorg last state: move 1/32 (`Brisken - Digital Co-Worker 2026-07.pptx` → Brisken Product Assets) LOCKED 423; all other 31 moves ALREADY at destination. Its PDF sibling and `...with UCs.pptx` already moved.
- Asset Testing now holds the 10 proposal files (separate from the reorg's Brisken Product Assets destination).
- Build chain: `uv run deckgen/make-library.py` → `compose.py {deck}` → `render.py {deck}` → `CDP_PORT=9223 upload.py --all`.
- Title-vs-logo rule of thumb from QA: use-case titles under ~28 chars clear the top-right logo lockup; longer collide.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/266
- QA renders: `.scratch/deckgen-v2/qa/{deck}/sNN.png`
- Zoho source: `workspace/clients/brisken/context/zoho-crm.json`

---

## How to Continue
The decks are shipped and live in Asset Testing. Send the prepared Dirk notification once confirmed. Watch for the reorg loop's COMPLETE flag (or re-run `.scratch/deckgen/_sp_reorg_execute.py` with `CDP_PORT=9223` to check whether Dirk's file has unlocked) and then report 32/32.

---

## Strategic Feedback

### What Worked Well This Session
- The clone-and-patch deck pipeline made a substantial content expansion (10 → 15 use cases across decks) a matter of spec edits + one rebuild command, with the banned-terms gate and COM render as automatic backstops. The infrastructure investment from the prior session paid off directly.

### Suggestions
- After a feature branch is squash-merged, reconcile it with main (or cut a fresh branch) before continuing work on it. Reusing `client/brisken/deck-foundation-v2` post-#264 produced a foreseeable CONFLICTING PR that cost one extra merge-resolve cycle.

### System Health
- The QA aesthetic-review workflow surfaced the title/logo collisions and one stale terminology flag (already fixed in source). A cheap structural add: a compose-time assert that flags any `uc-title` over ~28 chars, since the logo collision is now a known, repeatable failure mode.

---
