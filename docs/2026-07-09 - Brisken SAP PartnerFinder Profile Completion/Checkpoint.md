# Checkpoint: Brisken SAP PartnerFinder Profile Completion

**Date:** 2026-07-09
**Status:** Shipped. Resources shelf + demo film live on the profile. One field (Services tab) still stale.

---

## Summary

Closed the two remaining PartnerFinder work items (the demo video and the Resources
brochures) end to end: built a 58-second Market Data Hub film from real product screens
in `~/Repo/video-gen`, rebuilt the 10-card Resources shelf around six non-duplicative
replacements, found and fixed a silently-broken SAP Store link, and hosted everything on
`resources.brisken.com`. Both Planner tasks marked complete.

---

## What Was Done This Session

### Video (built in `~/Repo/video-gen`, per owner directive)
1. Found the only real product footage Brisken owns: `BRISKEN MDH WALKTHROUGH DEMO SLIDES
   250710.pptx` in SharePoint `2026_PPTX`, 46 slides of genuine Market Data Hub UI.
2. Extracted embedded images at native resolution (PyMuPDF, no page re-raster, no upscale).
3. PII screen rejected four candidates: two name a customer (BASF), one shows
   `larissa.teixeira@brisken.com`, one repeats a named individual in a log column.
4. Built `specs/brisken-mdh.spec.yaml` + `composition/src/brisken/{brand.ts,BriskenVideo.tsx}`
   + `pipeline/render-brisken.mjs`, registered alongside the CREW composition (not a refactor).
5. Rendered 16:9 and 1:1. Owner uploaded to YouTube (`Rk6YPOY8u7E`) and set the media slot.
6. Wrote `mdh-demo-recording-shotlist.md` so live screen capture can replace the stills.

### Brochures / Resources shelf
1. Pulled the latest SharePoint decks (MDH `2026-07`, Smart Trading) and hosted them.
2. Read all four incumbent brochures off `brisken.io` to build an overlap matrix; our MDH
   deck and Smart Trading one-pager were **excluded** as duplicates on that test.
3. Six replacements chosen on "no incumbent covers this subject": TreasuryCentral, OnePilot,
   Remittance Advice Gate, Bank Fee Portal, Digital Co-Worker, SAP Store card.
4. Built `sap-resources-cards.html` walk-in pack (dialog-field order, hover-to-copy,
   155-char validation, dark/light, Ctrl+K).
5. Stripped 3 em-dashes from the hosted Smart Trading deck at source (pptx XML rewrite +
   PowerPoint COM re-export). SharePoint original left untouched.
6. Deployed `resources.brisken.com` twice (both on explicit order).

### YouTube channel assets
1. `brisken-youtube-avatar.png` (800x800), `brisken-youtube-banner.png` (2560x1440),
   `brisken-youtube-thumbnail.jpg` (1280x720), all from the real logo artwork.
2. Caught a safe-area bug by drawing the 1235x338 box and looking: the subtitle sat 67px
   below the boundary and would have been cropped on TV and mobile.

### The broken SAP Store link (user-reported)
1. Root cause: card pointed at product id `0000004063`, retired. That URL returns **200**
   and then silently redirects to an empty SAP Store search. It looks alive to any checker.
2. Live listing is a **different id**: `2001008447`. Verified by rendering it: "Market Data
   Hub by BRISKEN LLC", showing "(0) Write a review".
3. Filled the `[your SAP Store listing link]` placeholder in the review-seeding email.

---

## Key Decisions Made

### Hero frames are real product screens, never generated
- **Choice:** Source every frame from Brisken's own walkthrough deck; drop any screen with
  a customer name, personal name or address; drop the whole 9:16 format.
- **Rationale:** `video-gen/CLAUDE.md` #1 (product truth) and #3 (a format that only
  "mostly works" is a failing format). Portrait shrinks 1869px-wide tables to unreadable
  and the only fix would be cropping real UI.

### MDH + BST cards point at the SharePoint decks, not our concise sheets
- **Choice:** Owner's call. Host the latest SharePoint PDFs verbatim.
- **Rationale:** Those decks were edited by someone else the same day (they carry "Citi
  Pulse" and sourced stats absent from our build script), so SharePoint is genuinely ahead.

### The em-dash fix went to the hosted copy only
- **Choice:** Rewrite the pptx XML locally, re-export, host. Do not touch SharePoint.
- **Rationale:** The em-dashes sat in someone else's edit. Correcting the file we publish
  is our remit; overwriting Dirk's live deck is an invasive write.

### Card 04 is a swap, not an addition
- **Choice:** Repoint the TraderPlus slot at the 2026 Smart Trading deck.
- **Rationale:** Our deck duplicates the 2019 flyer while the flyer stands. It can only
  enter by replacing it, which also purges the retired name.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `~/Repo/video-gen/specs/brisken-mdh.spec.yaml` | Created | Film spec, single source of truth for copy |
| `~/Repo/video-gen/composition/src/brisken/brand.ts` | Created | Brisken brand tokens |
| `~/Repo/video-gen/composition/src/brisken/BriskenVideo.tsx` | Created | Title / problem / shots / outro composition |
| `~/Repo/video-gen/composition/src/Root.tsx` | Modified | Register brisken-16x9 / 1x1 / 9x16 |
| `~/Repo/video-gen/pipeline/render-brisken.mjs` | Created | Spec-driven render, bt709 tv-range |
| `workspace/clients/brisken/resources-site/index.html` | Modified | Decks section + Digital Co-Worker card |
| `.../resources-site/market-data-hub-deck.pdf` | Created | Latest SharePoint MDH deck |
| `.../resources-site/smart-trading-deck.pdf` | Created | Latest BST deck, em-dashes stripped |
| `.../resources-site/digital-co-worker.pdf` | Created | Card 09 target |
| `.../deliverables/lead-generation/sap-resources-cards.html` | Created | 10-card walk-in pack |
| `.../deliverables/lead-generation/mdh-demo-recording-shotlist.md` | Created | Dirk's shot list |
| `.../deliverables/lead-generation/sap-surfaces-repositioning.md` | Modified | Video note, deck links, Store URL |
| `.../deliverables/lead-generation/youtube/*` | Created | Avatar, banner, thumbnail |
| `memory/project_brisken_mdh_demo_film.md` | Created | Where the film lives, what's disqualified |

---

## Current Status

The PartnerFinder profile (`0001663611`) now serves, per SAP's own published payload
(`/sap/details/api/partnerProfile/findByPartnerProfileId/0001663611`):

- **Heading + Description:** new spine copy, live.
- **`videoUrl`:** `https://www.youtube-nocookie.com/embed/Rk6YPOY8u7E?mute=1` — our film.
- **Resources:** the rebuilt 10-card shelf, live.
- **`serviceSummary`:** **STILL THE OLD TEXT** (1494 chars) with `< A >`, "TraderPlus",
  "Refinitv". This is the last place the retired name survives.
- **`logoUrl`:** a `.bmp` from September 2021.

`resources.brisken.com` serves 8 PDFs, all zero em-dashes, verified against the deployed
origin. Both Planner tasks marked 100% (verified by read-back).

Platform: brisken `tier: unknown`, expense-reconciliation (p1) is a custom SaaS build, not
a workflow-engine op count. Last assessed 2026-05-24.

---

## Next Steps

1. **Paste the Services copy** into the PartnerFinder editor (1322 chars, in
   `sap-surfaces-repositioning.md` §Services). This is the last TraderPlus reference on the
   profile. Needs Dirk's partner login; the editor rejects browser automation.
2. **Rotate the Vercel token** — `vcp_3gGZ...` was pasted in plaintext chat.
3. **Refresh the SAP Discovery Center mission 3904** (separate Planner task, untouched).
4. **Fix the profile social links** — 6 of 7 (Instagram, Facebook, Xing, WeChat, Twitter,
   YouTube) all point at `store.sap.com/dcp/en/search/brisken`. Only LinkedIn is real, and a
   Brisken YouTube channel now exists.
5. **Rename the SAP Store BST listing** — still titled "Brisken OnePilot - Trade Automation"
   on an SAP-owned page. Dirk's click in the publisher console.
6. Replace the 2021 `.bmp` logo on the profile.
7. Run `/comd_system-dev` — autonomy score elevated (see System Health).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/deliverables/lead-generation/sap-surfaces-repositioning.md`
- `workspace/clients/brisken/deliverables/lead-generation/sap-resources-cards.html`
- `~/Repo/video-gen/specs/brisken-mdh.spec.yaml`
- `memory/project_brisken_mdh_demo_film.md`

### Open Questions
- Was the Services field saved as a draft and never Published (Save and Publish are separate
  buttons), or never touched? The published payload cannot distinguish.
- Are cards 01 to 06 on the live shelf correct? The "6 More Resources" control would not
  expand under CDP, so only cards 07 to 10 were verified visually.

### Working Notes
- **`store.sap.com` is a soft-404 trap.** Product pages return HTTP 200 with an identical
  SPA shell whether the product is live or retired; a dead id silently redirects to an empty
  search. Never trust a status code there. Render it. `sapappcenter.com` no longer resolves.
- **The PartnerFinder public DOM lies.** An `iframe` probe of the profile found no video
  because the embed lazy-loads. The authoritative source is
  `/sap/details/api/partnerProfile/findByPartnerProfileId/{id}` (sniffed via CDP Network).
  `logoUrl` and `videoUrl` are separate fields; do not conflate the logo with the media slot.
- **A `youtu` substring match on that payload is a false positive** — `YOUTUBE` is a
  `socialMediaType` enum value.
- Remotion renders `yuvj420p` (full range) unless `colorSpace: 'bt709'` is passed; full range
  crushes blacks on a dark backdrop.
- Ken Burns must scale the **card**, not the `<img>` inside an overflow-hidden card, or it
  shaves readable pixels off a UI screenshot.
- `.scratch/logo/brisken-logo.svg` is a saved 404 page, not a vector. Highest-resolution real
  logo anywhere is 790x173 raster. Ask Dirk for the vector.
- New read-only CDP helpers: `.scratch/sap_read.py`, `sap_sniff.py`, `sap_profile_fields.py`,
  `sp_download.py`, `planner_complete.py`.

### Reference Materials
- Live SAP Store listing: `https://store.sap.com/dcp/en/product/display-2001008447_live_v1/brisken-onepilot-market-data-hub`
- Dead id (soft-404): `display-0000004063_live_v1`
- Film: `https://youtu.be/Rk6YPOY8u7E` · masters in `~/Repo/video-gen/out/brisken-mdh/`
- Profile: `https://partnerfinder.sap.com/profile/0001663611`

---

## How to Continue

The only thing standing between the profile and a clean repositioning is the Services tab.
Open `sap-surfaces-repositioning.md`, copy the Services block (1322 chars), paste it into the
PartnerFinder editor's Services tab, and press **Publish**, not just Save. Then re-run
`.scratch/sap_profile_fields.py` and confirm `serviceSummary` no longer contains "TraderPlus".

---

## Strategic Feedback

### What Worked Well This Session
- Answering "what are we replacing them with" by **reading the four incumbent PDFs first**
  turned a plausible plan into a correct one: it disqualified two cards we were about to add.
  Overlap questions deserve source reading, not recall.
- The owner's "make sure our replacements aren't doubles" constraint was the single most
  valuable instruction of the session. It forced the swap-vs-add distinction on card 04.

### Suggestions
- The `videoUrl` / `logoUrl` confusion cost a wrong "not done" report. When a surface has a
  published API, read the API, never the rendered DOM. Worth adding to the B2 gate: *if the
  target exposes a data endpoint, the endpoint is the verification surface.*

### System Health
- **Autonomy score: 4 human interventions this session (elevated — run `/comd_system-dev`).**
  Two B1 phrasing-reflex deferrals (hook-caught, long-running cluster), one user-reported
  broken link we recommended without verifying, one wrong "media slot is stale" claim.
- Verification theater remains the dominant failure class today (this is the 7th+ entry).
  The common shape: **checking the artifact I touched rather than the surface that serves it.**
  Today it was a DOM probe standing in for a published payload; earlier sessions it was a
  source edit standing in for a deploy. A rule exists; it is not holding.
- `.scratch/` has accumulated ~10 single-use CDP probes this session. Several
  (`sap_read.py`, `sp_download.py`, `planner_complete.py`) are genuinely reusable and belong
  in `tools/` with an INDEX row.
