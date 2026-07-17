---
project: brisken
workstream: p2-product-decks
group: lead-generation
spec: p2
state: active
updated: 2026-07-17
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Product decks (p2)

The OnePilot product-deck estate and its build system. Owner directive
2026-07-17 (voice memos `pptx.m4a` + `pptx foundation.m4a`): Dirk's own
`OnePilot Solutions Overview 2026.pptx` is the design + story foundation;
the four product decks were rebuilt on it as replacement proposals, plus a
proposed Overview revision. Build system: clone-and-patch on a library
derived from the reference (`automations/lead-generation/deckgen/`,
engine `tools/pptx_slide_ops.py`).

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Build system (deckgen v2) | done | Engine + library + composer + render + upload live; 10 pytest green; 5 decks built end-to-end | Reuse for future decks; refresh library when Dirk's reference changes (RENAMES tripwire fails loudly) | none | `automations/lead-generation/deckgen/README.md` |
| MDH Commodities proposal (8 sl) | review | In Asset Testing, verified 2026-07-17 | Dirk review | Dirk | `Asset Testing/Brisken - Market Data Hub Commodities 2026-08 PROPOSAL.*` |
| Market Data Hub proposal (10 sl) | review | In Asset Testing, verified | Dirk review | Dirk | same folder |
| Smart Trading proposal (8 sl) | review | In Asset Testing, verified; Trade Automation renamed throughout text | Dirk review | Dirk | same folder |
| Digital Co-Worker proposal (11 sl) | review | In Asset Testing, verified; 4 use-case one-pagers, internal demo labeled | Dirk review | Dirk | same folder |
| Overview revision proposal (32 sl) | review | In Asset Testing, verified; platform reframe, hierarchy slide, appendix drawer | Dirk review | Dirk | same folder |
| Swap into Product Assets | blocked | Runbook documented; NOT executed | Per-deck swap after explicit Dirk approval | Dirk approval per deck | deckgen README "Swap runbook" |
| Old dark-cockpit generators | dormant | Superseded for product decks; TC prospect decks (Sanofi/Zalando) still on old pipeline | Rebuild TC prospect decks on the new foundation (next wave, per owner scope decision) | none | `.scratch/deckgen/build-treasurycentral.js` |

## Open decisions (Dirk; listed in the proposal report)

1. BTP wording: proposals say "on SAP's own cloud"; his reference prints
   BTP text + the certification badge image. Opt-in restores it per deck.
2. "Digital Worker / Digital Co-Worker" rename (his memo: term feels dated).
3. Ring graphic on the platform slide bakes old names into the image
   (Trade Automation, ChatGPT mention, BTP badge): needs his source art.
4. Success-story expansion (ADM, Nike, Nestle, Ford) waits on his
   consultant-interview mechanism; no unsourced claims shipped.
5. ST/DCW product-logo images on use-case one-pagers reuse the generic
   brisken mark; product-specific logo assets would tighten them.
