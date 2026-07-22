---
project: brisken
workstream: p2-product-decks
group: lead-generation
spec: p2
state: active
updated: 2026-07-22
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Product decks (p2)

## 2026-07-21 update — Dirk review pass + distinct aesthetics

Dirk reviewed by commenting slide 2 of `Brisken - TreasuryCentral - Sanofi
2026.pptx` (8 comments, 2026-07-19) and hand-renaming his own overview to
`TreasuryCentral - Solutions Overview 2026.pptx`. Actions taken:

- **Message map locked** (`deckgen/MESSAGING.md`): cockpit→workspace, drop
  "your live SAP data", trading→autonomous trading, broaden "manual middle"
  to include legacy interfaces, no central-repository claim, TreasuryCentral =
  product / OnePilot = platform.
- **Sanofi deck** revised per his comments (17 edits) and placed in Asset
  Testing.
- **5 Asset-Testing decks** each given a distinct aesthetic (Overview =
  teal/Century Gothic/wedge; Market Data Hub = green/Bahnschrift terminal;
  MDH Commodities = rust/Sitka serif/cream; Smart Trading = indigo/Franklin
  condensed/wedge; Digital Co-Worker = teal/Candara soft), TreasuryCentral
  naming on covers/transitions/fd-headers, "manual middle" broadened, "powered
  by OnePilot" cover eyebrow. All re-uploaded to Asset Testing 2026-07-21,
  verified. Restyle engine: `.scratch/restyle_engine.py` (ephemeral).
- Overview file renamed to "Brisken - TreasuryCentral Solutions Overview
  2026-08 PROPOSAL" (old OnePilot-named pair recycled 2026-07-21). Asset
  Testing = 6 decks (5 product + Sanofi), pptx+pdf each.
- Per-deck layout signatures added (Overview top rule, MDH left rail, Trading
  right bar, Commodities bottom rule, Co-Worker corner dots); dark section
  dividers preserved. Brisken logo/lockup/SAP badges kept throughout.
- Naming model confirmed (owner 2026-07-21): OnePilot = the PLATFORM, not the
  AI; TreasuryCentral = the shipped screen on it; apps run inside. The AI app
  "AI Digital Workforce" renamed to **Digital Co-Worker** across all decks
  (0 remaining). "WHERE IT SITS" now shows a 4th "+ your own apps" open slot +
  strengthened OnePilot line ("runs these apps and any you build on it") to
  display extensibility.
- Open: ecosystem-wheel image (overview s8) keeps baked OnePilot branding
  and cyan ring — it is an image, not restyleable; needs Dirk's source art.

## 2026-07-21 (later) — Overview REBUILT from scratch (new visual system)

Owner directive: build a NEW modern Overview, not clone-and-patch; donor-verbatim
mandate suspended for this pass. Full from-scratch python-pptx rebuild (blank
presentation, single design-token system: ink/paper/neutral/teal + one focal
bright per slide, Century Gothic display / Segoe UI body, 12-col grid, card-based
layouts, ink full-bleed dividers, footer signature). 30 slides. Functional slides
rebuilt as Sources -> [platform, on SAP's own cloud, governed] -> Destinations with
ONE protocol connector strip + a governance panel (not the old acronym walls);
"Where it sits" rebuilt natively as layered TreasuryCentral -> OnePilot (4 app
cards incl. "+ your own apps") -> SAP. Real assets reused from the reference media:
Brisken lockup (light + reversed), the 20 real customer logos off donor slide 4,
and the SAP Certified badge (image12, NOT image34 which is Fortitude Re). Language
map applied throughout (workspace not cockpit; autonomous trading; legacy
interfaces + brittle integrations + manual middle; no central-repository; on SAP's
own cloud; no ChatGPT). Rendered via PowerPoint COM (LibreOffice not installed),
inspected slide-by-slide, fixed (wrong badge, use-case tick/label overlap x6,
customers grid overflow, missing footer, page-number gaps), re-verified clean.

### Substance pass + rename (same day)

Second pass on owner directive: make it legible to a non-treasury/non-SAP reader,
adding real information (never filler), truth-rules strict. Now 31 slides (added a
plain-language Governance slide). Rebuild engine `tools`-style `build2.py` (reuses
build.py helpers). What changed:
- Every jargon term glossed inline on first use (remittance advice, intercompany
  funding, in-house bank, exposure, book of records, CAMT.086/camt.053/MT940,
  security master, autonomous trading, ESG, SAP module names).
- Each app slide now answers, in order: problem removed -> mechanism step by step
  -> what you no longer do by hand, + a grounded CONNECTS TO strip (real venues,
  formats, SAP targets, so "any" is backed by instances).
- Use-case slides turned into concrete BEFORE (manual today) / AFTER (numbered
  steps) with the human checkpoint named.
- Success stories carry the real SAP deployment type (S/4HANA public/private/
  on-premise, REF s28-30) + 3 visible [NEEDS INPUT: before->after] placeholders
  (no metric exists in source; NOT invented).
- All copy traces to source: the app specs + Dirk's reference-deck text
  (extracted). Provenance in `deliverables/tc-overview-redesign/CHANGELOG-substance-pass.md`.
- Verified: slop-scan clean + 7-agent adversarial source-trace (one per cluster).
  6 findings fixed (dropped unsourced "we do not hold your data"; regrounded a
  generic line; MDH "rates"->"rates/prices/ratings"; glossed "exposure"; spelled
  out "ACT"; re-credited appendix hubs to their own app, not the Digital
  Co-Worker). Em-dashes stripped to zero (deliverable standard).
- **Renamed** to `NEW - Brisken - TreasuryCentral Solutions Overview 2026-07-21`
  (NEW prefix so it reads as new in the folder). Uploaded pptx+pdf to Asset
  Testing next to the clone-and-patch "...2026-08 PROPOSAL" pair (untouched); the
  interim "...- new design 2026-07-21" pair recycled. Asset Testing Overview
  family = 2 variants (PROPOSAL + NEW).
- Deliverable: `deliverables/tc-overview-redesign/` (pptx + pdf + changelog).
  Build source ephemeral (session scratchpad `tc-overview-new/build2.py`).
- Open for Dirk: (1) choose the Overview DIRECTION (clone-and-patch vs NEW);
  (2) About headline is now grounded ("An SAP co-innovation partner, live in
  production."). Ecosystem wheel still dropped (story folded into "Where it sits").

### Dirk review integrated (same day, later)

Dirk reviewed the NEW deck in SharePoint: 7 comments + 4 in-place text edits
(pulled off the live file via CDP, comments extracted from the modern-comment
parts). All folded back into `build2.py`/`build.py`, re-rendered + re-inspected
(2 layout fixes: MDH step overflow, success-card collision), re-uploaded to Asset
Testing (pptx 457,659 B; pdf 435,967 B byte-exact). Changes:
- **His 3 success-story fills** (closed the last [NEEDS INPUT]): FSI "Replaced a
  manual solution", Agriculture "Replaced an expensive custom third-party
  solution", Chemicals "Replaced a manual solution". **0 placeholders remain.**
- His 4 verbatim edits (S22 validate-against-customer-master, S23 cash-flow
  reorder, S30 credit rating/feed wording) adopted as-is.
- His 7 comments resolved: S8 "TreasuryCentral = one workspace on OnePilot" +
  "connects SAP and non-SAP alike"; S9/S13 dropped too-specific "SAP OneExposure"
  (generalized to deployment types / "exposure & risk systems"); S10 governance
  now carries the AI vocab (grounded in SAP, human-in-the-loop / HITL); S12 MDH
  emphasizes SAP AND non-SAP + audit-trail; S18 DCW workload-removed sharpened +
  logging; S19 "SAP process steps"/"records & notes" not "SAP postings"/"memo".
- Provenance appended to `deliverables/tc-overview-redesign/CHANGELOG-substance-pass.md`
  ("Dirk review integration" section).
- **Folder note (surfaced, not acted on):** "MN - " prefixed copies of the
  Overview pair + the PROPOSAL pair appeared in Asset Testing at 12:18 (user
  action). The "MN - Overview" copy is byte-content-identical to Dirk's
  PRE-integration edited version (same 7 comments, 0 text diffs) so it does NOT
  hold the integration; the integrated deck is the "NEW - " pair. Naming
  reconciliation left to owner.

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
| MDH Commodities proposal (9 sl) | review | In Asset Testing, re-verified 2026-07-17; 2 use cases (curve + Valuation & Exposure Prices) | Dirk review | Dirk | `Asset Testing/Brisken - Market Data Hub Commodities 2026-08 PROPOSAL.*` |
| Market Data Hub proposal (11 sl) | review | In Asset Testing, re-verified; 4 use cases (adds Credit & Counterparty Data) | Dirk review | Dirk | same folder |
| Smart Trading proposal (10 sl) | review | In Asset Testing, re-verified; 3 use cases (One FX Trade, Derivatives & Securities, OTC Commodity Swaps); BST naming | Dirk review | Dirk | same folder |
| Digital Co-Worker proposal (12 sl) | review | In Asset Testing, re-verified; 5 use-case one-pagers (adds Bank Statement Intake), internal demo labeled | Dirk review | Dirk | same folder |
| Overview revision proposal (32 sl) | review | In Asset Testing, re-verified; Funding one-pager elaborated, sourced customer-base credential caption | Dirk review | Dirk | same folder |
| Swap into Product Assets | blocked | Runbook documented; NOT executed | Per-deck swap after explicit Dirk approval | Dirk approval per deck | deckgen README "Swap runbook" |
| Old dark-cockpit generators | dormant | Superseded for product decks; TC prospect decks (Sanofi/Zalando) still on old pipeline | Rebuild TC prospect decks on the new foundation (next wave, per owner scope decision) | none | `.scratch/deckgen/build-treasurycentral.js` |

## Open decisions (Dirk; listed in the proposal report)

1. BTP wording: proposals say "on SAP's own cloud"; his reference prints
   BTP text + the certification badge image. Opt-in restores it per deck.
2. Deck rename: hierarchy/captions now use brisken.com's "AI Digital
   Workforce"; the DCW deck filename stays "Digital Co-Worker" for parity
   with the file it replaces. Full deck rename = one parameter flip.
3. Ring graphic on the platform slide bakes old names into the image
   (Trade Automation, ChatGPT mention, BTP badge): needs his source art.
4. Success-story expansion (ADM, Nike, Nestle, Ford) waits on his
   consultant-interview mechanism; no unsourced claims shipped.
5. ST/DCW product-logo images on use-case one-pagers reuse the generic
   brisken mark; product-specific logo assets would tighten them.
