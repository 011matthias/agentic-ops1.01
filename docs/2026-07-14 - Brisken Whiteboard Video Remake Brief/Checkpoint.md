# Checkpoint: Brisken Whiteboard Video Remake Brief

**Date:** 2026-07-14
**Status:** Brief delivered to video-gen; remake build not started

---

## Summary

Located the Brisken MDH whiteboard explainer on SharePoint via Graph (one video, two versions, ~11 copies), exported both versions plus Dirk's own remake materials, and wrote a fully sourced content-reference brief into the video-gen repo so the remake updates the stale 2018 language, not just the visuals.

---

## What Was Done This Session

### Find + export (Graph, autonomous)
1. Searched SharePoint driveItems via the cached delegated Graph token (still valid ~6.6h; no re-sniff needed) and resolved all whiteboard-video hits to real folder paths.
2. Identified the two distinct versions: the 8.4 MB 2018-era original (`20_Assets/BRISKEN VIDEOS/2026_BRISKEN PRODUCT VIDEOS/190630_... - the original.mp4`) and the 4.6 MB June-2025 English re-render (`250625_YT Videos all/`); the rest are byte-identical event-folder copies.
3. Downloaded both (byte sizes verified against SharePoint metadata) and exported them to `video-gen/cache/ingest/whiteboard/` with an `ingest.meta.json` provenance sidecar; confirmed gitignore coverage via `git check-ignore`.
4. Pulled Dirk's own remake folder (`FILE FROM 2018 EXPLAINER VIDEO/`): script docx, VEO/Flow scene prompts, YouTube transcript, five keyframe PNGs.

### Content reference brief (the deliverable)
5. Extracted the 2018 narration verbatim from the script docx; found Dirk's remake plan keeps that stale narration word-for-word.
6. Mined current language from the canonical 2026-07 MDH deck mirror, the owner-approved `brisken-mdh.spec.yaml` film narration, and the verified brand kit `composition/src/brisken/brand.ts`.
7. Wrote `video-gen/specs/brisken-whiteboard-remake.brief.md`: stale-object inventory (17 rows, each sourced), banned-terms block (BTP in any spelling, Evonik/RWZ, the four PII-rejected screens, em-dashes, thesaurus voice), lift-verbatim current copy block, asset map, two explicit TBDs.

---

## Key Decisions Made

### Graph-first, token reuse
- **Choice:** Reused the cached delegated token in `.scratch/graph_token.txt` for search, download, and folder listing; no CDP re-sniff, no desktop path.
- **Rationale:** rule_brisken_graph_first; token had ~6.6h validity with `Files.ReadWrite.All`.

### Ingest home = `cache/ingest/whiteboard/`
- **Choice:** Videos land under video-gen's gitignored `cache/`, not a tracked dir.
- **Rationale:** video-gen BLUEPRINT "big files stay out of git; raw ingested recordings gitignored."

### Brief grounded in deck truth, 2018 text demoted to "base only"
- **Choice:** Source-of-truth ranking: 2026-07 SharePoint deck > approved film spec > brand.ts > 2018 script. The remake updates words, not just pictures.
- **Rationale:** The 2018 narration contains dead objects (Thomson Reuters, SAP Cloud Platform, sapappcenter.com, BRISKEN.IO) and Dirk's own remake prompts carry them forward unchanged.

### No commit on video-gen
- **Choice:** Brief left untracked in the working tree.
- **Rationale:** video-gen is on `main`; commit-on-main is B6 gated floor. Surfaced once, not asked repeatedly.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `video-gen/specs/brisken-whiteboard-remake.brief.md` | Created | The content reference brief (deliverable; untracked on main) |
| `video-gen/cache/ingest/whiteboard/*.mp4` (x2) | Created | Both source videos, byte-verified (gitignored) |
| `video-gen/cache/ingest/whiteboard/ingest.meta.json` | Created | SharePoint provenance sidecar |
| `agentic-ops1/.scratch/whiteboard-videos/*` | Created | Working copies: 2 mp4s, script docx, flow-prompt md, transcript md, 5 keyframe PNGs (gitignored scratch) |

---

## Current Status

Brief is in place and self-contained; video-gen can build the remake from it without re-deriving anything. Nothing committed anywhere (agentic-ops1 touched only gitignored scratch; video-gen commit is gated). Brisken platform ops line: n/a (no Make/n8n platform section relevant; Lead Desk ops tracked in its own checkpoint).

---

## Next Steps

1. In video-gen: author the remake spec (`brisken-whiteboard.spec.yaml` or extend the existing MDH pipeline) off the brief; Dirk's five keyframes + the seven cleared MDH frames + brand.ts are all on hand.
2. Resolve the two TBDs with Dirk when convenient: SAP Store URL on the end card (or keep the text chip), music bed vs voice-only.
3. Commit the brief on video-gen when the owner orders it (B6 floor).

---

## Context for Next Session

### Files to Read First
- `video-gen/specs/brisken-whiteboard-remake.brief.md` (the deliverable; everything else hangs off it)
- `video-gen/specs/brisken-mdh.spec.yaml` (approved narration + product-truth/PII precedent)
- `video-gen/composition/src/brisken/brand.ts` (verified brand kit + banned-terms note)

### Open Questions
- Does Dirk want the remake to keep the white whiteboard aesthetic (his flow prompts) or move to the dark-cockpit deck system? The brief supports either; visuals were deliberately left his call.
- SAP Store end-card URL and music bed (the brief's two TBDs).

### Working Notes
- The delegated Graph token expires ~6.6h after this session; next session re-sniff via `.scratch/grab_graph_token.py` (needs the CDP Edge planner tab) or use the app-only cred where in scope.
- SharePoint search hit ~11 copies of the same original mp4 across event folders; the two canonical homes are recorded in `ingest.meta.json`. Sizes reported by search for some copies (3.4 KB "mp4s") are stubs/thumbnails, not real files.
- MDH deck mirror slide 12 (PARTNERS AND CUSTOMERS) is a hidden slide; do not treat as public-facing copy.
- `validate-demo-material.py --client brisken` is the banned-terms checker if remake copy ever lands in agentic-ops1 paths.

### Reference Materials
- SharePoint remake folder: `MARKETING/Shared Documents/20_Assets/BRISKEN VIDEOS/2026_NEW AI GENERATED VIDEOS/FILE FROM 2018 EXPLAINER VIDEO/`
- Decks README (BTP/Evonik/RWZ directives): `workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/README.md`

---

## How to Continue

Open video-gen, read the brief, and build the remake spec against it. The narration should be assembled from the brief's "current canonical copy block" + the approved film narration lines; visuals per Dirk's keyframes unless he redirects. No agentic-ops1 state is pending.

---

## Strategic Feedback

### What Worked Well This Session
- The prior session's Graph token + the existing `sp_probe.py` pattern made the whole find-export loop autonomous; zero user asks from "find" to shipped brief.

### Suggestions
- When handing Dirk the remake, lead with the one-line finding that his own remake prompts carry the 2018 narration verbatim (Thomson Reuters, SCP, sapappcenter.com); that is the part he cannot see from the visuals.

### System Health
- Autonomy score: 0 human interventions this session (1 friction event, hook-caught and self-corrected).
- The closing-offer deferral class keeps recurring (3 sessions today) but the stop-b1-gate hook now reliably converts it to same-turn self-correction; the structural fix is holding at the last line of defense. Watch whether write-time discipline improves or the hook stays the only catch.
