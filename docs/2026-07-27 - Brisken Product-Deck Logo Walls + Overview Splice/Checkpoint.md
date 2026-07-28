# Checkpoint: Brisken Product-Deck Logo Walls + Overview Splice

**Date:** 2026-07-27
**Status:** Both deliverables built + verified locally; two gated SharePoint writes await owner greenlight

---

## Summary
Two Dirk requests from 2026-07-27, both delivered to the readiness-checked-artifact
boundary: (1) transparent, per-prospect-swappable customer logo walls pushed into
the native deck engine and applied across the Overview + 4 product decks; (2) a
merged Overview that keeps Dirk's reworked front (MN slides 1-11) and grafts the
approved deck's reviewed back-half (slides 11-31). Nothing written to his live
tenant yet.

---

## What Was Done This Session

### Logo-wall redesign (engine track)
1. Read Dirk's change straight off his `MN - ...2026-07-27.pptx` (two walls, old
   slide 6 -> new slide 5): transparent logos, Ford + Siemens Energy added,
   Beautycounter/Global Brands dropped, "run on TreasuryCentral" headline.
2. Built a curated 25-logo TRANSPARENT library (`context/decks/customer-logos/
   normalized/`) from his SharePoint "CUSTOMER LOGOS" folder + Commons renders
   (Nestle/Sony/LG) + 4 reference-only marks (white-keyed medmix/entegris).
   Improved on his slide 5: Angus now transparent (his was still boxed).
3. Named-logo-set engine: `native/logosets.py`, `customers(logo_set=...)`
   grammar, assets.py transparent-overlay + tripwire, compose validation.
   Master + 3 industry cuts (agri-food, chemicals-industrials, financial-services).
4. Applied walls: Overview->master; MDH + Smart Trading->financial-services;
   MDH Commodities->agri-food; Digital Co-Worker->chemicals-industrials. Rebuilt
   all 5 as `NEW - ... 2026-07-27`. Fixed a real 4-row-master headline collision
   found in the visual review.
5. Shipped code to the client branch (Band 1); promoted `build-logo-library.py`
   to tracked, re-derivable tooling; DESIGN.md §2 + 2 new tests (15/15 green).

### Overview splice (hand-assembly track)
6. Fetched both live Overviews; render-diffed the seam to confirm MN's back-half
   is OLD pre-review content and the approved back-half carries Dirk's review
   fixes (audit-trail bullet, "SAP and non-SAP").
7. Merged via PowerPoint COM `InsertFromFile`: MN 1-11 + approved 11-31 = 32
   slides, seam invisible (shared native design), footer numbers continuous.

---

## Key Decisions Made

### Splice boundary = MN[1-11] + approved[11-31], not [12-31]
- **Choice:** Start the graft at the approved deck's slide 11 (its MDH divider),
  not 12.
- **Rationale:** The two decks are off-by-one at "slide 11" (MN-11 = Governance;
  approved-11 = MDH divider). Literal "after 11" from approved would drop the
  section divider. 11-31 keeps it and reads as the true intent.

### Engine-first for the logo walls; his pptx = design spec
- **Choice:** Push the change into the engine, not hand-edit his file.
- **Rationale:** The engine reproduces the approved deck and is the source of
  truth; his file is the design reference.

### Both SharePoint writes held for owner yes
- **Choice:** Stop at verified local artifacts; do not upload.
- **Rationale:** Live-tenant writes are invasive (rule_brisken_graph_first /
  feedback_no_invasive_action_without_ask); "execute the instructions" does not
  authorize the write. Dirk has the MN file open in edit mode -> overwriting
  risks a co-authoring clobber, so a NEW "(filled)" file is the recommendation.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `deckgen/native/logosets.py` | create | Named LOGO_SETS (master + 3 cuts) |
| `deckgen/native/assets.py` | edit | Overlay curated transparent library + tripwire |
| `deckgen/native/grammar.py` | edit | `customers(logo_set=)`, adaptive collision-safe grid |
| `deckgen/native/compose.py` | edit | Validate `logo_set` |
| `deckgen/native/specs/*.yaml` (5) | edit | Wall per deck; output date -> 2026-07-27 |
| `deckgen/native/tests/test_native_engine.py` | edit | 2 new logo-set tests; badge-pin decoupled |
| `deckgen/build-logo-library.py` | create | Tracked, re-derivable library builder |
| `deckgen/common.py` | edit | `customer_logos_dir()` durable path |
| `deckgen/DESIGN.md` | edit | §2 logo-set model |
| `status/p2-product-decks.md` | edit | 2026-07-27 logo-wall + splice sections |

---

## Current Status
Code committed + pushed to `client/brisken/deckgen-native` (rode onto the nightly
sweep PR #430, which is CONFLICTING/DIRTY with main for unrelated reasons — not
auto-merged; the sweep process resolves it). Five `NEW - ...2026-07-27` decks and
the merged `MN - ...(filled)` Overview are built + fully visually verified in
`.scratch/deckgen*`. brisken platform ops: unknown plan (no platform section in
infrastructure.yaml). Two gated writes pending an owner call.

---

## Next Steps
1. Owner decision on the merged Overview write: upload as NEW `(filled)` file
   (recommended) vs overwrite MN in place (only if Dirk closes it) vs hold.
2. Owner decision on staging the 5 logo-wall decks: all five, product-decks-only
   (the engine Overview may be moot now Dirk hand-builds his), or hold.
3. On any yes: generate PDFs, run the pre-upload readiness check, upload, re-list
   to verify.
4. Flag Tradeweb/ICD to Dirk (no clean logo source; ambiguous name).
5. Flag the two-wall duplicate-"03" in Dirk's MN front (final deck likely wants one).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p2-product-decks.md` (both 2026-07-27 sections)
- `workspace/clients/brisken/automations/lead-generation/deckgen/native/logosets.py`
- `.scratch/deckgen/splice/` (merged deck + fetch/splice scripts)

### Open Questions
- Which delivery for the merged Overview, and which logo-wall decks (if any) to stage?
- Do the engine Overview and Dirk's hand-built MN Overview need to reconverge, or
  is the MN track now the canonical Overview and the engine scoped to product decks?

### Working Notes
- Curated library is durable in gitignored context + re-derivable via tracked
  `build-logo-library.py` (reads SharePoint pull + web-sourced + reference deck).
- SharePoint reads go through the CDP Edge on :9223 (scripts in `.scratch/deckgen/`);
  the "CUSTOMER LOGOS" folder is `20_Assets/BRISKEN logos and icons/CUSTOMER LOGOS`.
- `InsertFromFile` preserves the source slides' formatting (both decks are
  explicit-shape native builds, no theme reliance), so the graft is lossless.
- render_slides.py now writes to `.scratch/deckgen/renders/` (was polluting the
  compose dist dir and breaking compose cleanup — fixed).

### Reference Materials
- Dirk MN file: `.../Asset Testing/MN - Brisken - TreasuryCentral Solutions Overview 2026-07-27.pptx`
- Approved: `.../Asset Testing/Brisken - TreasuryCentral Solutions Overview 2026-07-21.pptx`

---

## How to Continue
`/resume brisken`, read the status file's two 2026-07-27 sections, then act on the
owner's answers to the two gated-write questions (upload flow: PDFs -> readiness
check -> upload -> re-list verify).

---

## Strategic Feedback

### What Worked Well This Session
- Reading Dirk's intent off the actual artifacts (his pptx, the render-diff of the
  two decks) instead of guessing — the "after slide 11" off-by-one and the
  old-vs-reviewed back-half only surfaced by looking.
- Engine-first with a tripwire'd, re-derivable asset library: the logo change is
  now a one-line spec edit per deck, not a manual re-layout.
- G4 visual review caught a real headline-over-logos collision before it shipped.

### Suggestions
- The engine Overview vs Dirk's hand-built MN Overview are diverging. Worth a
  quick owner alignment on which is canonical before more Overview work, to avoid
  maintaining two.

### System Health
- Autonomy: 3 human interventions this session (all direction/clarification: the
  scope AskUserQuestion, the splice instruction, checkpoint) — zero corrections of
  delivered work. Healthy.
- One self-inflicted slow-path (scratch render script polluted the engine's dist
  dir, broke compose cleanup) — diagnosed from the full error and fixed
  structurally. Both invasive-write gates and branch-isolation held.

---
