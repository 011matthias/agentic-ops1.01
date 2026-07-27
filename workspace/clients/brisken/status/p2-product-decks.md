---
project: brisken
workstream: p2-product-decks
group: lead-generation
spec: p2
state: active
updated: 2026-07-27
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Product decks (p2)

## 2026-07-27 — Logo-wall redesign (Dirk direction) built, awaiting upload greenlight

Dirk's 2026-07-27 mail (relayed): his `MN - ...Overview 2026-07-27.pptx` carries
a before/after customer wall (old slide 6 -> new slide 5) with his intended
changes, and asks to (a) apply them across the decks, (b) use TRANSPARENT logos,
(c) build multiple walls swappable per customer. His changes decoded off the file:
transparent logos replace white-boxed marks (Nike/ADM/ASR done, Angus still boxed),
Ford + Siemens Energy added, Beautycounter/Global Brands dropped, headline
"...run on TreasuryCentral." Owner calls (this session): apply to Overview + all 4
product decks; build master + 3 industry cuts; his named logos are all confirmed
customers.

Built (engine-first; his pptx = design spec, not the artifact to hand-edit):
- **Curated transparent logo library** (25 logos) at
  `context/decks/customer-logos/normalized/`, re-derivable via tracked
  `deckgen/build-logo-library.py` from three durable sources: SharePoint "CUSTOMER
  LOGOS" folder (`20_Assets/BRISKEN logos and icons/CUSTOMER LOGOS`; his 6 new
  2026-07-27 transparent files live here), Commons renders (Nestle/Sony/LG), and 4
  reference-only marks (accenture/ab-inbev + white-keyed medmix/entegris). Angus
  upgraded to transparent (improves on his still-boxed slide 5). KAUST + Grupo
  Moura found in the folder; **Tradeweb/ICD flagged** (no clean source, ambiguous
  ICD-vs-Tradeweb name) for Dirk.
- **Named-logo-set engine**: `native/logosets.py` (`LOGO_SETS`: master + agri-food
  + chemicals-industrials + financial-services); `customers(logo_set=...)`
  grammar; assets.py overlays the transparent library + tripwires on a missing
  wall logo; compose validates `logo_set`. DESIGN.md §2 documents it.
- **Walls applied**: Overview -> master (Dirk's slide 5, improved); MDH + Smart
  Trading -> financial-services; MDH Commodities -> agri-food; Digital Co-Worker
  -> chemicals-industrials. All 5 rebuilt as `NEW - ... 2026-07-27` (product decks
  +1 slide; Overview wall replaced in place). Caught + fixed a real 4-row-master
  headline collision (2-line "...TreasuryCentral." over the top logo row).
- **Gates**: em-dash zero + banned-terms pass on all 5; 15/15 engine pytest
  (incl. 2 new logo-set tests); full-size visual review of all 5 walls (clean).

NOT YET DONE: upload to Asset Testing (SharePoint write = owner-gated); PDFs.
Local pptx in `.scratch/deckgen-v2/dist/*/NEW - ... 2026-07-27.pptx`.

## 2026-07-24 — Dirk notification SENT

Owner-approved notification sent to Dirk 2026-07-24 09:03Z (Graph,
matthias.silva → dirk.neumann, verified real send, logged verbatim in
comms-log.md): the four `NEW - ... 2026-07-23` decks in Asset Testing, ask
= per-deck approval. Next inbound from Dirk triggers the swap runbook
(per-deck, invasive) or a spec regen if he comments. Nothing else changed.

## 2026-07-23 — NEW Overview APPROVED; engine promoted; product-deck rebuild wave

- **Dirk approved the NEW Overview** (`NEW - Brisken - TreasuryCentral
  Solutions Overview 2026-07-21.pptx`, owner relay 2026-07-23). The
  Overview DIRECTION decision (clone-and-patch vs NEW) is resolved: NEW.
  Approval read as content approval; promotion into Product Assets and
  the fate of the superseded `2026-08 PROPOSAL` + `MN - ` variants stay
  Dirk's call (swap runbook unchanged).
- **Build source promoted** out of the session scratchpad into
  `automations/lead-generation/deckgen/native/` (tokens / draw / grammar /
  assets / compose / render / montage + specs + tests). Regression proof:
  composing `native/specs/overview.yaml` reproduces the approved deck
  **part-for-part (121/121 zip parts md5-identical** to the committed
  deliverable). The "build source ephemeral" debt is closed.
- **Standard codified** in `deckgen/DESIGN.md` (tokens + per-deck palettes,
  slide grammar + content contracts, gates G0-G6, rollout rules);
  MESSAGING.md carries the Dirk-review vocabulary additions; six Dirk
  decisions became fixture-enforced banned terms (`demo-banned-terms.json`:
  your live SAP data, SAP OneExposure, AI Digital Workforce, ChatGPT,
  central repository, cockpit). `context/deck-fix-pass-prompt.md` deleted
  (superseded; surviving rules folded into DESIGN.md §2).
- **Wave SHIPPED (same day):** all four product decks rebuilt from scratch
  on the approved system (one family, per-deck accent + layout signature)
  and uploaded to Asset Testing as `NEW - Brisken - <Deck> 2026-07-23`
  pptx+pdf pairs. Gates: banned-terms/em-dash PASS (11 terms), native
  font/rIds/hidden clean, slop scan clean, 14-checker adversarial
  source-trace (6 REAL findings fixed, incl. a subject-drop that made the
  platform "in production across six industries" claim read app-level),
  full-size app-slide visual review (caught one hidden-overflow bug,
  fixed), upload re-list 8/8 verified + all four pptx re-downloaded and
  slide-text-identical to the local builds. Deliverables of record + full
  provenance: `deliverables/product-decks-redesign/` (CHANGELOG.md).
- **Folder note (2026-07-23 upload):** the approved Overview pptx now sits
  in Asset Testing WITHOUT the "NEW - " prefix (renamed since the last
  session; its PDF still carries it), and the non-MN "2026-08 PROPOSAL"
  pairs are gone; "MN - " copies remain. Reconciliation stays Dirk's call.

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
| Build system (native v3) | done | From-scratch engine promoted from scratchpad; Overview regression 121/121 parts identical; 12 pytest green; CI gate `deckgen-native-tests.yml` | Build the four product decks on it | none | `deckgen/native/` + `deckgen/DESIGN.md` |
| Build system (deckgen v2, clone-and-patch) | dormant | Superseded for product decks; still owns the PROPOSAL artifacts + library mechanics | Keep until Dirk rules on PROPOSAL variants; prospect decks (Sanofi/Zalando) still reference it pending their rebuild | none | `automations/lead-generation/deckgen/README.md` |
| Market Data Hub NEW (13 sl) | review | In Asset Testing 2026-07-23, G0-G6 verified; 4 use cases; FSI success story | Dirk per-deck pick | Dirk | `Asset Testing/NEW - Brisken - Market Data Hub 2026-07-23.*` |
| MDH Commodities NEW (10 sl) | review | In Asset Testing 2026-07-23, G0-G6 verified; 2 use cases; no success slide (none sourced) | Dirk per-deck pick | Dirk | same folder |
| Smart Trading NEW (11 sl) | review | In Asset Testing 2026-07-23, G0-G6 verified; 3 use cases; ACT/LSEG stats in-sentence | Dirk per-deck pick | Dirk | same folder |
| Digital Co-Worker NEW (14 sl) | review | In Asset Testing 2026-07-23, G0-G6 verified; 5 use cases (internal-demo label kept); Agri+Chem success | Dirk per-deck pick | Dirk | same folder |
| v2 PROPOSAL variants (clone-and-patch) | superseded | Non-MN PROPOSAL pairs observed gone from Asset Testing 2026-07-23; MN- copies remain | Fate of remaining variants = Dirk's call | Dirk | `deckgen/README.md` (v2 section) |
| Overview NEW (31 sl) | **approved** | Dirk approved (owner relay 2026-07-23); review integrated, 0 placeholders | Swap into Product Assets on Dirk's word (runbook); naming reconciliation of PROPOSAL + MN- variants = Dirk's call | Dirk (filing) | `Asset Testing/NEW - ...2026-07-21.*`; repo copy `deliverables/tc-overview-redesign/` |
| Overview revision proposal (32 sl, clone-and-patch) | superseded | Direction decision went to NEW; artifact still in Asset Testing | Fate = Dirk's call (archive or delete) | Dirk | same folder |
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
