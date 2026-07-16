# Checkpoint: Brisken Videos SharePoint Move + Calvin Workspace Tweak

**Date:** 2026-07-11
**Status:** Shipped to Dirk's tenant (all files byte-verified). Source commit local-only, blocked on the repo-visibility decision.

---

## Summary

Consolidated all AI-generated Brisken videos into Dirk's own SharePoint folder
(`20_Assets/BRISKEN VIDEOS/2026_NEW AI GENERATED VIDEOS`), caught and removed a
"Built on SAP BTP" chip from the MDH film before it reached him, implemented his
workspace-building tweak on the Calvin clip (re-rendered, pixel-verified,
re-uploaded), and delivered the narrator-integration prompt for the video-gen
repo. Push of the source changes was denied: the GitHub repo is PUBLIC.

---

## What Was Done This Session

### SharePoint consolidation (owner-directed "move the videos there")
1. Discovered Dirk's pre-existing folder via read-only CDP BFS of the MARKETING
   library: `BRISKEN VIDEOS` with subfolder `2026_NEW AI GENERATED VIDEOS`
   (held only a "FILE FROM 2018 EXPLAINER VIDEO" subfolder).
2. Server-side MOVED the two Calvin clips + README there from our `2026_VIDEO`
   (version history preserved; README renamed `calvin-clip-README.txt`;
   byte-verified). Recycled the emptied `2026_VIDEO` folder (restorable).
3. Uploaded the MDH demo film both cuts as
   `mdh-demo-film-16x9-1080p.mp4` (10,609,543 B) and
   `mdh-demo-film-1x1-1080.mp4` (7,879,787 B), byte-verified.

### MDH film BTP removal (B4 catch before upload)
4. Pre-upload scan found the outro trust chip "Built on SAP BTP" in
   `specs/brisken-mdh.spec.yaml` + `composition/src/brisken/brand.ts`
   (video-gen repo) — the same defect class that shipped twice on 07-09.
   Removed the chip (4 chips remain), re-rendered 16:9 + 1:1 (58.00s,
   h264/yuv420p/30fps), pixel-verified the outro frames before upload.

### Calvin clip workspace tweak (Dirk's feedback via owner, mid-turn add)
5. Grounding pass: no "workspace" language exists in any Brisken deck or the
   comms log; Dirk's own words from the owner's message are the anchor.
6. Implemented as three copy touches in `clip.html`: manual beat sub
   "A workspace assembled by hand.", cash beat sub "Calvin builds the
   workspace around the request.", end card "Calvin built the workspace.
   You stayed in control. Every step was logged." Plus one timing fix:
   caption-sub fade was hardcoded to the approval beat (48.6-49.6); now
   relative to its own card.
7. Preview-pass pixel check (both ratios), full re-render (90.00s both),
   final-mp4 frame checks at t=12/42/86s, then overwrote the SharePoint
   copies (byte-verified; prior cut kept in version history).
8. Updated `calvin-clip-brief.md` (shot table + end card) and
   `video/README.txt` (revision note) to match; committed `801172a` on
   `leadgen/task-6`.

### Narrator prompt for video-gen
9. Delivered a paste-ready prompt (in chat) to promote narration to a
   default-on pipeline stage, grounded in the repo's existing machinery
   (tts_kokoro.py, music_bed.py, asr_faster_whisper.py, -14 LUFS mix,
   quality/qc.mjs), with spec surface (`narration:`/`narrator:`,
   `narration: none` opt-out), fit-to-hold timing, ASR-diff verification,
   and brisken-mdh as the proving case (script stops for owner review;
   no-BTP constraint restated).

### Public-repo finding
10. `gh pr create` push was denied by the harness classifier; verified with
    `gh repo view`: **011matthias/agentic-ops1.01 is PUBLIC**. PR #207
    already published the earlier Calvin cut + brief + email-to-Dirk there.
    Logged to comms-log + friction register; owner decision needed.

---

## Key Decisions Made

### Destination = `2026_NEW AI GENERATED VIDEOS`, not `BRISKEN VIDEOS` root
- **Choice:** Put all our videos in that subfolder.
- **Rationale:** Dirk created it and its name describes exactly our output;
  the root holds his historical video projects in their own subfolders.

### Recycle the emptied `2026_VIDEO` folder
- **Choice:** Recycle (not keep, not hard-delete) after the verified move.
- **Rationale:** We created it 07-09; leaving an empty duplicate invites
  future mis-uploads. Recycle bin keeps it restorable. Known cost: the
  folder link emailed to Dirk 07-09 now dead-ends.

### Remove ONLY the BTP chip from the MDH outro
- **Choice:** Keep "SAP Co-Innovation Partner", "On the SAP Store",
  "ISO 27001", "SOC 1 Type II"; drop "Built on SAP BTP".
- **Rationale:** BTP is Dirk's standing exclude-directive. The other chips
  trace to the SAP-surfaces spine; ISO/SOC scope is an open question owned
  by the Calvin-clip thread, and MDH (unlike DCW) IS Store-listed, so the
  Store chip is true here. Minimal change per directive, no over-edit.

### Workspace tweak = three copy touches, no visual redesign
- **Choice:** Name the already-animated workspace assembly in captions and
  the end card rather than re-staging the clip.
- **Rationale:** Stage B already shows the workspace building itself (chat +
  S/4HANA panel filling in); the copy just never said it. Dirk's words
  ("workspace building aspect of calvin") map directly onto captions;
  smallest change that delivers the emphasis, keeps the 90s timing intact.

### Stop at the public-repo boundary
- **Choice:** Leave commit `801172a` unpushed; surface instead of retrying.
- **Rationale:** The classifier's premise checked out (repo is public;
  content is confidential client material). Pushing more client content to
  a public repo is an outward-facing action the owner must decide.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| SharePoint `BRISKEN VIDEOS/2026_NEW AI GENERATED VIDEOS/` | 5 files in (2 moved, 1 moved+renamed, 2 uploaded), then 3 overwritten | All AI-generated videos in Dirk's folder |
| SharePoint `.../OnePilot - Cloud Solutions Presentations/2026_VIDEO/` | Recycled | Emptied by the move; we created it 07-09 |
| `video-gen/specs/brisken-mdh.spec.yaml` | Modified (UNCOMMITTED) | BTP chip removed from outro trust list |
| `video-gen/composition/src/brisken/brand.ts` | Modified (UNCOMMITTED) | Same removal in the brand-kit default |
| `video-gen/out/brisken-mdh/{16x9,1x1}.mp4` | Re-rendered (gitignored) | BTP-free cuts, outro pixel-verified |
| worktree `output/leadgen-task-6/clip/clip.html` | Modified, commit `801172a` (LOCAL) | Workspace captions + relative sub timing |
| worktree `output/leadgen-task-6/calvin-clip-brief.md` | Modified, same commit | Shot table + end card match the render |
| worktree `output/leadgen-task-6/video/README.txt` | Modified, same commit | Revision note |
| worktree `output/leadgen-task-6/video/*.mp4` | Re-rendered, same commit | The shipped cuts |
| `workspace/clients/brisken/context/comms-log.md` | Appended | Internal ops note: move, BTP fix, tweak, public-repo finding |
| memory `project_brisken_mdh_demo_film.md` | Updated | New canonical video folder; BTP chip gone; uncommitted video-gen edits |
| `.scratch/cdp_sp_{video_folders,move_check,move_videos,upload_mdh,upload_calvin_rev}.py` | Created (gitignored) | Discovery (read-only), move+recycle, two upload+verify scripts |
| `docs/friction-register.md` | Appended | Public-repo gap entry |

---

## Current Status

Dirk's folder holds exactly: `calvin-clip-16x9-1080p.mp4` (2,452,121 B),
`calvin-clip-1x1-1080.mp4` (2,077,236 B), `calvin-clip-README.txt`,
`mdh-demo-film-16x9-1080p.mp4`, `mdh-demo-film-1x1-1080.mp4` — all
byte-verified after write, Calvin cuts carrying the workspace emphasis,
MDH film BTP-free. Two source surfaces are pending: commit `801172a`
(leadgen/task-6, unpushed — repo is public) and the video-gen working tree
(BTP edits uncommitted — direct-to-main repo needs an owner order).

No orchestrator platform for brisken p2 (manual-first), so no ops status
line applies.

---

## Next Steps

1. **OWNER DECISION: repo visibility.** `011matthias/agentic-ops1.01` is
   PUBLIC and already carries Brisken deliverables via PR #207. Flip it
   private (`gh repo edit 011matthias/agentic-ops1.01 --visibility private`)
   or name the public destination as intended; then push `801172a` + PR.
2. **OWNER ORDER: commit video-gen** BTP edits (direct-to-main repo):
   `specs/brisken-mdh.spec.yaml` + `composition/src/brisken/brand.ts`.
3. Hand the narrator prompt (in chat, also summarized in this checkpoint) to
   a video-gen session; its step 7 stops for script approval on brisken-mdh.
4. Optional, needs explicit ask: one-line note to Dirk that the videos now
   live in his `2026_NEW AI GENERATED VIDEOS` folder (his 07-09 link is dead).
5. Structural follow-up: a destination-visibility check before client-content
   pushes (see friction entry) — candidate extension to no-auto-commit-gate.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/comms-log.md` (2026-07-11 internal note — the full move/verify record)
- `C:/Users/neuma_p1qrsic/Repo/agentic-ops1-leadgen-task-6/output/leadgen-task-6/calvin-clip-brief.md` (updated spec)
- memory `project_brisken_mdh_demo_film.md` (canonical video-folder pointer)

### Open Questions
- Repo visibility: private, or approved-public? (Blocks the push.)
- Does Dirk get the one-line "videos moved" note? (Old link dead-ends.)
- Narrator on the Calvin clip specifically: brief argues a synthetic voice on
  an AI-product clip undercuts trust (real Brisken voice preferred) — Dirk's
  call once the narrator pipeline exists.

### Working Notes
- **Dirk's folder (canonical for our videos):** `/sites/MARKETING/Shared
  Documents/20_Assets/BRISKEN VIDEOS/2026_NEW AI GENERATED VIDEOS`.
- **SharePoint move mechanics:** `GetFileByServerRelativePath(...)/moveto(
  newurl='...',flags=0)` does a server-side move keeping version history;
  flags=0 fails on collision instead of overwriting. Folder `recycle()` is
  restorable, `deleteObject()` is not. Cookie auth per the 07-09 recipe
  (FedAuth on host, rtFa on apex, decoy rtFa on .live.com).
- **ffmpeg on this machine:** not on Git Bash PATH; resolve
  `$LOCALAPPDATA/Microsoft/WinGet/Packages/Gyan.FFmpeg.../bin/ffmpeg.exe`.
- **Caption-sub timing bug (fixed):** `capSub` opacity was hardcoded to the
  approval card's window; any new sub on another card would never have faded
  in. Now `ease(seg(t, cardA+1.2, cardA+2.2))` relative to the active card.
- **video-gen pipeline split:** crew pipeline already narrates (Kokoro VO,
  ducked bed, ASR QC, golden refs); `render-brisken.mjs` is a separate
  silent path — the narrator prompt directs unifying them.
- **Failed approach:** SharePoint search API (`fileextension:mp4`) returns 0
  for the tenant's videos (mp4 not indexed); folder BFS via REST works.

### Reference Materials
- Dirk's folder: https://brisken.sharepoint.com/sites/MARKETING/Shared%20Documents/20_Assets/BRISKEN%20VIDEOS/2026_NEW%20AI%20GENERATED%20VIDEOS
- Prior Calvin checkpoint: `docs/2026-07-09 - Brisken Calvin Clip (Lead-Gen Task 6)/Checkpoint.md`
- video-gen repo: `C:/Users/neuma_p1qrsic/Repo/video-gen` (BLUEPRINT.md §5 TTS, §6 phases)

---

## How to Continue

Resolve the repo-visibility decision first (Next Step 1) — it unblocks the
push. The tenant side is done and verified; nothing in Dirk's folder waits on
us. For the narrator work, paste the prompt from this session's final message
into a video-gen session and review the brisken-mdh narration script it
produces before any audio renders.

---

## Strategic Feedback

### What Worked Well This Session
- The mid-turn task addition ("dirk also had some tweaks") folded in without a
  restart: the render pipeline was already open, so the tweak rode the same
  verify-upload loop as the move.
- Accumulated recipes paid off: the 07-09 CDP-cookie upload script and the
  ffmpeg/Edge gotcha memories turned tenant writes and pixel verification
  into minutes, not investigation cycles.

### Suggestions
- Decide the repo-visibility question once, at the org level: every Brisken
  branch push re-raises it, and PR #207 shows the exposure is already live,
  not hypothetical.

### System Health
- The harness classifier was the ONLY gate that caught client content heading
  to a public repo; our own B6 hook validates ship mechanics (branch, CI) but
  never destination visibility vs content sensitivity. That is the
  highest-value structural gap surfaced this session.
- Autonomy score: 0 human interventions this session (1 agent-detected
  friction event, structural fix pending).
