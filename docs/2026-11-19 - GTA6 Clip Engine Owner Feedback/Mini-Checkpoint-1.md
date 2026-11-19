# Mini-Checkpoint: GTA6 Clip Engine Owner Feedback

**Date:** 2026-11-19
**Status:** owner feedback on the first video applied (PR #1772); NVIDIA driver 621.24 installed, NVENC works
**Type:** mini

---

## Summary
The owner reviewed `m5-f1`. Layout, captions and hook style were good, and four changes followed: about 1 minute long, a hook that leads with GTA6, the main object (the jet) always completely visible, and the GPU driver update. All four are done and the video was re-sent.

## What Was Done
- **Length ~1 min:** `cut_f1` fills toward 55 s with whole sentences (build-up first), max 60 s; `analyze --length` overrides.
- **Hook leads with GTA6:** `judge` refuses a keep whose first hook does not name GTA. The video uses the owner's wording, "ohnePixel playing GTA6 for the first time".
- **Main object completely visible:** gameplay is no longer cropped to 0.84; the whole gameplay region is scaled to full width over a blurred zoom of itself, the duplicate facecam in the gameplay is blurred, and captions sit on the blurred strip. `config/layouts.yaml` ohnepixel gameplay = full frame.
- **Driver:** NVIDIA 621.24 (WHQL notebook DCH, found via NVIDIA's GFE lookup by device id 2520, Authenticode valid) installed silently after one UAC click; `h264_nvenc` opens.
- **Video:** `m5-f1` re-cut to 12.6–68.3 s (starts when the pause map closes, luma 44→106 at 12.5 s) = 55.7 s, -13.9 LUFS, captions 0.03 s, rendered over NVENC; a 720p preview was sent (the original is 71.8 MB, above the 30 MB send limit).
- PR #1772 merged (61 tests; regress_check: length growth, GTA rule and fit layout each bite). Memory `reference_local_machine.md`: IPv6 resets, and the driver history.

## What Did NOT Work (and why)
- **Sending the 1080p original (71.8 MB):** SendUserFile caps at 30 MB; send a 720p preview (~14 MB).
- **Gameplay cropped to the band's 0.84 aspect:** cut the jet's wings off; owner rule: the main object must be completely visible.
- **Whole-frame black check for a dark gameplay band:** the bright facecam band hid an open pause map at the start; found only by looking.

## Current Status
`data/ready/m5-f1/m5-f1.mp4` is the current approved-direction version; nothing posted. Moment 15 (caseoh_) is kept but needs a GTA6-first hook and a facecam profile.

## Next Steps
1. Owner's verdict on the new `m5-f1` fit layout.
2. caseoh_: calibrate facecam in `config/layouts.yaml`, re-judge moment 15 with a GTA6 hook, render.
3. Check the gameplay band for menus and dark stretches (pause map case); judge the 13 open packages.
4. 22.11.: `suggest --since 72h`; then p1.7 (schedule, `claude -p` judgment, cleanup) and the YouTube curve.

## Files to Read First
- `workspace/projects/gta6-clipping/engine/src/clipengine/render.py` (`filter_graph`)
- `workspace/projects/gta6-clipping/engine/config/layouts.yaml`
- `workspace/projects/gta6-clipping/status/p1-clip-pipeline.md`
