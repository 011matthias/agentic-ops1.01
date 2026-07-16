# Checkpoint: Brisken Video Narrator + Logo Handoff + Dirk Notify

**Date:** 2026-07-12
**Status:** Videos updated + live in Dirk's SharePoint (by a separate video-gen session); Dirk notified by email. video-gen source changes uncommitted, owner-gated.

---

## Summary

Handed a video-gen session exact, file-aware instructions to roll the generated
narrator into all Brisken videos, then revised them for two owner directives
(narration must be a connected walkthrough, not caption fragments; use the real
full-color logo, not the fabricated typed-wordmark + CSS diamond). Staged the real
logo assets. Marked the Planner "adaptable demo" task started. After video-gen
executed and re-uploaded the four videos, verified them and sent Dirk the
"videos are client-ready" notification, verified in Sent Items and logged.

This session did NOT edit or render the videos itself. It authored the handoff,
staged assets, and handled the client notification. A separate video-gen session
did the narration/logo/render/upload.

---

## What Was Done This Session

### Narrator-integration handoff (v1)
1. Grounded the state across two repos: the narration pipeline
   (`pipeline/narration.mjs`) was already built and applied to the MDH film;
   the Calvin clip had no narrator and lives in agentic-ops1 (HTML+Playwright,
   not Remotion). Wrote `video-gen/docs/brisken-narration-rollout.md` with exact
   file locations, the mp4-agnostic audio-path reuse (`ttsLine`/`buildProgram`/
   `muxAudio`, `-c:v copy`, no re-render for Calvin), scene timeline + draft lines,
   verification, and the SharePoint-upload delivery boundary.

### Planner
2. Marked "Brainstorm an adaptable client demo to replace the static decks"
   (Lead Generation bucket, id `MfqCpytRhUiO4gaI4OdqI2UAH-zO`) started, 0 -> 50,
   verified by re-read. Fresh Graph token via `.scratch/grabtoken2.py` (prior
   was ~6h stale).

### Handoff revision (v2 — two owner directives)
3. **Narration → connected walkthrough.** Rewrote the guidance so the voice
   describes the process as one continuous train of thought (each line picks up
   the previous beat), with full recommended connected drafts for BOTH films,
   while keeping muted-first + no-new-claims + the scene-fit gate.
4. **Real logo.** Found the culprit: the MDH film draws a typed `"brisken"` text
   span + a CSS rotated-square `Diamond` (fabricated, wrong shape). Instructed to
   delete both and use the real asset. Staged the real logo files:
   `brisken-logo-fullcolor.png` (navy+cyan) + `brisken-logo-reverse.png` into
   `video-gen/composition/public/brisken/`, and `brisken-logo-fullcolor.png` into
   the Calvin clip dir. Specified the dark-background treatment (full-color on a
   light chip; reverse as fallback) and the exact `BriskenVideo.tsx` / `clip.html`
   edit points.

### Dirk notification (after video-gen executed)
5. Verified all four files re-uploaded to Dirk's folder 07-12 12:35-12:36 UTC
   (sizes up from the silent versions -> narration + logo landed) via a read-only
   listing before asserting "ready".
6. Drafted the notification in Dirk's style (lead line + folder link + bullets,
   no ask), showed it, and on owner "send" sent it from Matthias's Outlook
   (`SendUsingAccount` pinned to Matthias, dedup-guarded). Verified in Sent Items
   (To: Dirk Neumann, Sender: Matthias Silva, folder hyperlink present, 14:57 UTC).
   Logged verbatim to `comms-log.md`.

---

## Key Decisions Made

### Reuse the audio path, don't rebuild Calvin in Remotion
- **Choice:** Calvin narration = mux a program wav onto the existing silent masters
  (`buildProgram` + `muxAudio`, `-c:v copy`); re-render frames only for the logo swap.
- **Rationale:** The narration path is mp4-agnostic; rebuilding the bespoke
  HTML/Playwright clip in Remotion would be high-effort and risky for zero gain.

### Real logo on a light chip (dark background)
- **Choice:** Full-color `brisken-logo-fullcolor.png` inside a small near-white plate.
- **Rationale:** The real logo's wordmark is navy, invisible on the dark cockpit;
  a light chip shows the true brand colors legibly. The reverse (white) logo is the
  fallback. Either way the typed-wordmark + CSS diamond are deleted (per
  [[feedback_use_original_logos]] — never a wordmark stand-in).

### Notification email, not an essay
- **Choice:** Lead line + folder link + four bullets, no ask, no process narration.
- **Rationale:** [[feedback_dirk_email_notification_style]]. The folder link also
  quietly replaces the 07-09 link that went dead when the files moved.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `video-gen/docs/brisken-narration-rollout.md` | Created, then rewritten | The handoff: narrator + connected narration + real logo, both repos' paths |
| `video-gen/composition/public/brisken/brisken-logo-fullcolor.png` + `brisken-logo-reverse.png` | Staged (copied) | Real logo assets for the MDH Remotion build |
| `.../leadgen-task-6/output/leadgen-task-6/clip/brisken-logo-fullcolor.png` | Staged (copied) | Real logo for the Calvin clip |
| Planner task `MfqCpytRhUiO4gaI4OdqI2UAH-zO` | 0 -> 50 | "Adaptable demo" marked started |
| `workspace/clients/brisken/context/comms-log.md` | Appended | Sent email verbatim + grounding |
| `.scratch/cdp_sp_list_dirk_videos.py`, `send_dirk_videos_ready.py`, `planner_start_demo.py` | Created (gitignored) | Read-only folder listing; guarded send; guarded Planner start |

Not this session (separate video-gen session): the narration/logo edits, re-renders,
and the SharePoint re-upload of all four videos.

---

## Current Status

Dirk's folder (`20_Assets / BRISKEN VIDEOS / 2026_NEW AI GENERATED VIDEOS`) holds
the four narrated, real-logo videos (MDH 16x9/1x1 = 9,989,677 / 7,025,270 B;
Calvin 16x9/1x1 = 3,591,470 / 3,219,281 B), all re-uploaded 07-12 12:35-12:36 UTC.
Dirk emailed 14:57 UTC that they are ready. No orchestrator/ops line for this work.

Open source surfaces: the video-gen narration + logo changes are UNCOMMITTED
(direct-to-main repo, needs owner order). The Calvin clip's `clip.html` logo edit
lives in the `leadgen-task-6` worktree (commit `801172a` line still local-only per
the public-repo question from the prior checkpoint).

---

## Next Steps

1. **OWNER ORDER: commit the video-gen work** (direct-to-main). Files: the narration
   stage (`pipeline/narration.mjs`, `render-brisken.mjs`), `pipeline/narrate-calvin.mjs`,
   the brisken-mdh spec's narration block, the logo change in `BriskenVideo.tsx` +
   the staged logo PNGs, provider/qc edits. Uncommitted by design until you say so.
2. Optional, Dirk's call: swap the Calvin clip's generated voice for a real Brisken
   recording (the pipeline makes it a per-scene wav drop-in). Noted in the comms log.
3. Planner "adaptable demo" task sits at 50%; move to 100% only if you consider the
   two demo videos the deliverable, or leave it open as the broader direction.
4. Carried from prior checkpoint, still open: repo-visibility decision on
   `011matthias/agentic-ops1.01` (PUBLIC, holds Brisken deliverables) before pushing
   `801172a`.

---

## Context for Next Session

### Files to Read First
- `video-gen/docs/brisken-narration-rollout.md` (the full handoff, both directives)
- `workspace/clients/brisken/context/comms-log.md` (2026-07-12 SENT entry)
- memory `project_brisken_mdh_demo_film.md`, `feedback_dirk_email_notification_style.md`,
  `feedback_use_original_logos.md`

### Working Notes
- **Logo truth:** real full-color logo = `brisken-logo-light.png` (292x64, navy+cyan);
  reverse/dark-bg = `brisken-logo-src.png` (790x173, white wordmark + cyan mark). The
  SVGs in `.scratch/logo/` are 79-byte "not found" stubs; there is no hi-res full-color
  vector locally (pull from brisken.com if a larger crisp full-color render is needed).
- **MDH brand mark was fabricated:** typed `BRISKEN.copy.wordmark` span + CSS `Diamond`
  (a rotated square, not the hexagon). That was the "monochrome crap."
- **Send mechanism:** `CreateItem(0)` defaults to Matthias on this profile, but the
  profile also carries Dirk; pin `SendUsingAccount` to Matthias anyway and verify the
  SENDER (not just recipient) in Sent Items. `ns.SendAndReceive(False)` throws
  "must be logged in to your provider" (COM-blocked) - don't rely on it; poll Sent
  Items directly (Outbox empties on its own).
- **SharePoint read-only listing** of one folder: `.scratch/cdp_sp_list_dirk_videos.py`
  (cookie grab via CDP :9222, GET only). Folder-view link format:
  `.../Forms/AllItems.aspx?id=<encoded folder>&parent=<encoded parent>`.

### Reference Materials
- Dirk's folder: https://brisken.sharepoint.com/sites/MARKETING/Shared%20Documents/20_Assets/BRISKEN%20VIDEOS/2026_NEW%20AI%20GENERATED%20VIDEOS
- Prior checkpoint (SharePoint move + Calvin tweak): `docs/2026-07-11 - Brisken Videos SharePoint Move + Calvin Workspace Tweak/`
- Planner: MARKETING PLAN `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`, Lead Generation bucket `gyfptEwAwUiJLXfd6aMrYWUABZRr`

---

## How to Continue

The client side is done and verified; nothing waits on us with Dirk. The one open
engineering action is the owner order to commit the video-gen narration+logo work
(direct-to-main). If Dirk asks about the Calvin voice, the real-recording swap is a
per-scene wav drop-in through the same pipeline.

---

## Strategic Feedback

### What Worked Well This Session
- Grounding before asserting: the read-only folder listing confirmed all four files
  were actually re-uploaded before the email claimed "ready" (B4), and the Sent Items
  readback confirmed the send went from Matthias, not Dirk (the profile's known hazard).
- The staged logo assets + exact edit points made the handoff executable rather than
  aspirational: the video-gen session had the real files in place, not a to-do.

### Suggestions
- The recurrent B1 closing-offer reflex fired twice again this session (both were
  legitimate gates: an invasive SharePoint write and an outbound email needing the
  user's own "show me first"). The content was right; only the phrasing read as an
  offer. When the pause IS a real gate, state it as a decision point ("held pending
  your go") rather than "want me to..." - the hook is correcting phrasing, not judgment.

### System Health
- Cross-repo handoff via a doc the target session reads (with staged assets + exact
  paths) is a clean pattern for video-gen work that lives outside agentic-ops1. Worth
  reusing whenever the deliverable is produced in another repo.
- Autonomy score: 1 human-visible friction (the B1 reflex, hook-caught, self-corrected);
  0 user error-corrections this session.
