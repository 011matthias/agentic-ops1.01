# Mini-Checkpoint: GTA6 Clip Engine First Video

**Date:** 2026-11-19
**Status:** p1.1 to p1.6 built; first F1 video in `engine/data/ready/m5-f1/`, shown to the owner, not posted
**Type:** mini

---

## Summary
The engine now goes from viewer clips to a finished, checked 1080x1920 video. First video: ohnePixel's jet crash through the city (21.7 s), sent to the owner for feedback.

## What Was Done
- PR #1769 (p1.3): `clipengine analyze` (faster-whisper large-v3 int8_float16 on the GPU, F1 cut at sentence boundaries, review packages in `data/review/{moment}/`) and `clipengine judge` (refuses a keep with spoiler, cutscene, adult reject, wrong hook count, or a title without the streamer). Migration 3 (`transcripts`, `moments`); GPU wheels in an optional `gpu` extra.
- Live: 21 sections analyzed in 3 min 19 s (120 s audio in 4 to 8 s, peak VRAM 2.5 of 6 GB). Verdicts: keep 5 (ohnePixel jet crash) and 15 (caseoh_ scooter chase); reject 1 (strip club), 3, 4, 10, 12 (story cutscenes / mission), 8 (radio song); 13 open.
- PR #1770 (p1.4 to p1.6): `clipengine render` (EDL, `config/layouts.yaml` facecam profile for ohnePixel, ASS captions with highlighted word, hook, name tag, two-pass loudnorm, checks incl. captions vs the render heard again by Whisper). Only a pass reaches `data/ready/`.
- First video `m5-f1`: 1080x1920 60 fps, 21.7 s, -13.9 LUFS, captions 0.02 s off; opened locally and sent to the owner.
- Memory: `reference_local_machine.md` gained the IPv6-reset and NVENC-driver facts.

## What Did NOT Work (and why)
- **faster-whisper's own audio decoder:** PyAV's `av.open()` no longer takes `metadata_errors`; audio is decoded with ffmpeg instead.
- **Newest nvidia-cublas-cu12 (12.9.3.13):** no Windows wheel; pinned `<12.9.3`.
- **First sentence-start rule (sentence start up to 0.5 s after the core):** cut off the sentence the top clip began in; now the sentence containing the core start, or the next one if it ended before.
- **h264_nvenc:** ffmpeg 8.1 needs NVENC API 13.1 (driver 610+), the laptop has 560.94 (API 12.2); x264 fallback.
- **ASS `WrapStyle: 2`:** the hook ran off both edges; `WrapStyle: 0`.
- **Ending the cut on the WASTED screen (72.0 s):** the game mutes on death, 4.9 s of silence failed the check; out at 68.3 s.
- **`uv run --directory` with a relative DB path:** created an empty `clipengine.sqlite` in the worktree (deleted); use absolute paths.

## Current Status
Queue of this task is done. Nothing posted anywhere. No ops status: internal project without an orchestrator.

## Next Steps
1. Owner feedback on `m5-f1` (layout, captions, hook, length), then adjust the style sets.
2. Render moment 15 (caseoh_) after calibrating his facecam profile; judge the 13 open packages.
3. 22.11.: `suggest --since 72h`; then p1.7 (schedule, `claude -p` judgment, cleanup) and the YouTube curve.

## Files to Read First
- `workspace/projects/gta6-clipping/engine/README.md`
- `workspace/projects/gta6-clipping/status/p1-clip-pipeline.md`
- `workspace/projects/gta6-clipping/engine/src/clipengine/produce.py`
