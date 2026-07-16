# Checkpoint: Brisken Presenter Pass and Sanofi Rollout

**Date:** 2026-07-16
**Status:** Shipped — three storyline proposals refined in repo; Sanofi TreasuryCentral restructured and live on SharePoint; sorting prompt banked

---

## Summary
Ran the presenter-flow pass (slide-2 growth + train-of-thought audit + the 9-point deck-fix-pass) over the three storyline proposals, then applied the same structure to the Sanofi TreasuryCentral deck and shipped it to SharePoint 2026_PPTX (root + Client Collateral WIP) ahead of Friday's call. Banked Dirk's assessment-docs publishing thread as memory and wrote the 2026_PPTX folder-sorting prompt for a new chat.

---

## What Was Done This Session

### Presenter pass on the three storyline proposals (repo deliverables, NOT SharePoint)
1. THE SHORT VERSION grew to four rows (added "Who it is for") on all three; closing line now names each deck's spine (MDH "one pipeline, six real screens", DCW "one request, followed end to end", ST "the same trade on our clock").
2. Train-of-thought bridges: MDH ribbon closes on "Each of the next six pages is a real screen of this pipeline, in order." + stage tags on all six screen eyebrows (INGEST ×2 / VALIDATE / GOVERN / DISTRIBUTE / AUDIT); safe-grid "Audited to the target" card became a callback. DCW problem slide closes on "So watch one request." ST venue list now appears once, architecture page calls back to it and hands into the control grid; "6 steps" stat corrected to 5.
3. Fix-pass catches: DCW AI chip removed from runs-on (4 chips, ST-matched grid), DCW footers 10-12 relabeled, live em-dash removed from ST slide 6, MDH "Refinitiv"→"LSEG".
4. Close slides on all three: official on-dark white logo (keyed from `context/brisken-logo-on-navy.jpg`) replacing the illegible navy wordmark; "Built to stay done." (UnpauseAI's own tagline — cross-brand leakage) replaced with per-deck promise stamps: MDH "One governed feed.", DCW "Busywork, done.", ST "The trade books itself."
5. Verification: 2 rounds of fresh-eyes multi-agent QA (3 agents over all 39 renders; all real findings fixed), COM counts intact (14/2 hidden, 13/0, 12/1), validator PASS, own em-dash/"free" XML sweep CLEAN.

### Sanofi TreasuryCentral rollout (SharePoint, owner-directed)
1. Confirmed live state first: 2026_PPTX root file (603,251 B @ 16:26) was a sibling session's upload minutes earlier; downloaded fresh, hash-matched the sibling's verify copy, built on that.
2. Inserted THE SHORT VERSION as slide 2 (10 → 11 slides; footers renumbered 02-10/11; rId20/sldId 266; cloned from the MDH slide, TC copy).
3. Fix-pass repairs: problem slide no longer resolves itself (new pain close "None of those steps is hard. Together they run a global process on hand-carried data."), architecture trust line de-enumerated → hands into the safe grid, AI chip removed from runs-on (4 chips re-centered), "Segregation of duty"→"duties", proof slide got its own headline ("Customer treasuries run on it today.") + SAP row reworded (was verbatim-duplicating slide 10's card), close = white logo + "Every decision, one cockpit."
4. PRESERVED verbatim: the slide-10 demo-ask wording the sibling session shipped today (Dirk-gated, no live demo).
5. Verified: fresh-eyes QA agent (slide 2 / chips / footers / banned content / close all CLEAN; its 3 real findings fixed), validator PASS, PDF 11 pages, race-check passed at upload, live file re-downloaded and COM-confirmed (11 slides, SHORT VERSION at 2). Repo mirrors in call-collateral/ refreshed from live bytes.

### Docs, memory, prompt
1. Sign-off note gained "Presenter pass 2026-07-16" section + close-slide change + three per-shot screenshot observations for Dirk's flag-4 review (USD→USD rates, clipped mapping shot, impossible audit-log dates).
2. Dirk's "ASSESSMENT DOCS BRISKEN - LEGACY & Updates" mail thread banked as the assessment-doc publishing place: comms-log INBOUND entry (verbatim) + memory `reference_brisken_assessment_docs_thread`; MEMORY.md compacted 19.6→13.6KB.
3. 2026_PPTX folder-sorting prompt written to `context/sharepoint-2026pptx-sort-prompt.md` (incl. owner-required "Asset & Deliverable Prep" folder), based on a live folder inventory.

---

## Key Decisions Made

### "Built to stay done." removed from all Brisken decks
- **Choice:** Replace the close headline on all four decks with per-deck promise stamps.
- **Rationale:** QA identified it as UnpauseAI's canonical marketing tagline — cross-brand leakage into client-branded decks (it had leaked in via the fix-pass prompt's own example). Owner directed "implement it on the 3"; carried into Sanofi.

### Sanofi build based on live SharePoint state, not repo mirror
- **Choice:** Fresh CDP download + hash check against the sibling session's verify copy; race-check (size+mtime) baked into the upload script.
- **Rationale:** A sibling session had uploaded a newer Sanofi version 20 minutes before this task; repo mirror was stale. SharePoint = truth.

### Stage tags instead of color progression on the MDH tour
- **Choice:** Eyebrows carry "· INGEST/VALIDATE/…" tying each screen to the ribbon; no per-stage color system.
- **Rationale:** The fix-pass color-progression item is for paired step overviews; a 5-color ramp would fight the two-accent dark-cockpit palette. Tags give the same traceability for one text edit per slide.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/deliverables/.../decks/brisken-{market-data-hub,digital-co-worker,smart-trading}-storyline-proposal.pptx` | Modified | Presenter pass + fix-pass + close-slide fixes |
| `.../decks/storyline-proposal-note-2026-07-14.md` | Modified | Presenter-pass section, close change, flag-4 screenshot observations |
| `workspace/clients/brisken/deliverables/.../call-collateral/brisken-treasurycentral-sanofi.{pptx,pdf}` | Modified | Mirrors refreshed from the live restructured deck |
| SharePoint `2026_PPTX/Brisken - TreasuryCentral - Sanofi 2026.{pptx,pdf}` (root + Client Collateral WIP) | Overwritten | Restructured 11-slide deck live (SP versioning keeps priors) |
| `workspace/clients/brisken/context/comms-log.md` | Appended | Dirk's assessment-docs thread, verbatim |
| `workspace/clients/brisken/context/sharepoint-2026pptx-sort-prompt.md` | Created | New-chat prompt for the 2026_PPTX reorganization |
| `~/.claude/.../memory/reference_brisken_assessment_docs_thread.md` + `MEMORY.md` | Created/Compacted | Publishing-thread memory; index compacted under size limit |
| `.scratch/deckbuild/*` (fixpass_edits.py, sanofi_build*.py, sp_*.py, renders, unpacks) | Created (ephemeral) | Build/QA/upload tooling |

All repo changes remain uncommitted on `client/brisken/lead-desk-cockpit` (working tree is shared with sibling sessions' changes; a commit would sweep in their work).

---

## Current Status
Three storyline proposals sit in the repo, presenter-ready, awaiting Dirk's flags (1/3/4/8/9; Commodities 2/6). The Sanofi deck on SharePoint is the restructured 11-slide version, verified live, with Friday 2026-07-17 16:00 (Ian Haegemans) as its first outing. Nothing else in SharePoint touched. The sorting prompt is ready to paste into a new chat.

---

## Next Steps
1. Tell Dirk the Sanofi deck is now 11 slides (summary slide shifted everything after slide 1 by one) before Friday's call.
2. Run the 2026_PPTX sorting prompt in a new chat (`context/sharepoint-2026pptx-sort-prompt.md`).
3. Await Dirk's flag answers; on approval adopt the three proposals into SharePoint (re-pull mirrors, delete proposals), then roll the standard into the collateral generators (`.scratch/deckgen/build-*.js`) so regenerated decks inherit it.
4. Structural fix candidate: add em-dash + "free" patterns to `tools/fixtures/demo-banned-terms.json` so the validator catches typography, not just content terms (this session found a live em-dash the previous "PASS" missed).
5. Zalando deck still carries the pre-softening close on SharePoint; rebuild before Dirk books that call (generator already defaults neutral).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/README.md`
- `.../decks/storyline-proposal-note-2026-07-14.md`
- `workspace/clients/brisken/context/sharepoint-2026pptx-sort-prompt.md`

### Open Questions
- Dirk's flags 1/3/4/8/9 (+ 2/6 Commodities); his read on the new close stamps (flag-9 adjacent).
- Should the hero slides also move to the white on-dark logo? (Top-left on flat dark reads acceptably; only closes were swapped.)

### Working Notes
- Build loop unchanged (unpack → XML → clean.py → pack.py --original → COM verify → PNG render → fresh-eyes QA → validator). pptxenv venv; rIds first-free-above-max; footers NN/N hand-set.
- SHORT VERSION slides share identical shape ids (2,3,4,10-13,20-23,30-33,40-43) across all family decks; 4-row geometry: cards h=700000 pitch 820000 at y=2590800/3410800/4230800/5050800; bridge y=5871480 h=350520. Clone-and-retext is the fastest path to add one to any family deck.
- White on-dark logo asset: `.scratch/deckbuild/brisken-logo-white.png` (keyed from `context/brisken-logo-on-navy.jpg`, 791x173). Close-slide pic geometry: x=5316443, cx=1546921, cy=338328.
- Chip-grid constants (5→4 fix): card x = 566420/3394392/6222365/9050337, w=2573972; label x = card+143510, w=2286952; icon x = card+976090.
- Scoped-block replacement, not global string, for x-coords (x="566928" is the family left margin, appears ~7×/slide).
- SharePoint access: CDP Edge :9222 + SP REST (`.scratch/deckbuild/sp_{list_now,dl_sanofi,upload_sanofi}.py`; first fetch after tab-create fails — retry after ~6s). Graph app has no MARKETING-site grant; CDP is the documented fallback. SP re-stamps pptx on ingest (+~800 B), so verify by re-download + COM, not byte-compare.
- validate-demo-material.py scans ONLY the 4 content terms (BTP ×2 spellings, Evonik, RWZ) — NOT em-dashes or "free"; pair it with the manual XML sweep until the fixture grows.
- Sanofi deck package: pptxgenjs-made, media named image-{slide}-{n}.png, per-slide notesSlides, sldSz 12191695 (305 EMU narrower than the product decks — copied geometry fits).

### Reference Materials
- Approved restructure plan: `C:\Users\neuma_p1qrsic\.claude\plans\refactored-dazzling-hopper.md`
- Fix-pass checklist: `workspace/clients/brisken/context/deck-fix-pass-prompt.md`
- Live folder inventory (2026-07-16 ~16:40): 2026_PPTX root 20 files; subfolders Client Collateral WIP (12), RAW MATERIAL (2), Archive (1)

---

## How to Continue
Use this prompt in a fresh session:

> Continue the Brisken deck work (checkpoint: docs/2026-07-16 - Brisken Presenter Pass and Sanofi Rollout/Checkpoint.md). The three storyline proposals (repo) and the Sanofi TreasuryCentral deck (SharePoint 2026_PPTX, 11 slides, live) all carry the presenter-flow standard. Pending: Dirk's flag answers gate SharePoint adoption of the three proposals + the Commodities rebuild; the Zalando deck needs the softened close + this structure; the 2026_PPTX folder sort runs from context/sharepoint-2026pptx-sort-prompt.md in its own chat. Build mechanics + geometry constants are in the checkpoint's Working Notes.

---

## Strategic Feedback

### What Worked Well This Session
- The narration audit (write one presenter sentence per slide, then fix where it jumps) found every real flow defect the freeform "look at the slides" pass missed — worth making the default for any deck work.
- Hash-checking the live SharePoint file against the sibling session's verify copy before building prevented a stale-base rebuild; the race-check abort in the upload script makes parallel-session deck work safe.

### Suggestions
- Sibling sessions and this one now coordinate through `.scratch` artifacts by accident (backup dirs, verify copies). A tiny convention — one `.scratch/sp-state.json` with {file, size, mtime, session, action} appended on every SP touch — would make the race-checks deterministic instead of forensic.

### System Health
- Autonomy score: 0 human interventions this session — fully autonomous (two mid-turn scope additions by the owner were direction, not correction; 1 agent-detected friction, self-fixed).
- The validator's "PASS" was quietly narrower than the checkpoint language claimed ("no em-dashes" was never checked). When a gate's coverage and its reputation diverge, every PASS builds false confidence — the demo-banned-terms.json fixture addition (Next Steps #4) is the cheap structural close.
