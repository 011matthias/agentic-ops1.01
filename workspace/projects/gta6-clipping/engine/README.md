# clipengine

The GTA6 clip engine (master plan: [p1-clip-engine.md](../specs/2-build/p1-clip-engine.md)).
Built so far: p1.1, register, SQLite state, Twitch and YouTube watch, streamer suggestions;
p1.2, interval planning from viewer clips and section downloads.

Run from this folder (`uv` installs everything on first use):

```text
uv run clipengine suggest --since 48h     top streamers by English GTA VI clip views, report in data/reports/
uv run clipengine approve LOGIN           owner said yes: append to config/streamers.yaml
uv run clipengine reject LOGIN            owner said no: never suggested again
uv run clipengine watch                   new VODs, YouTube uploads and viewer clips, last 7 days
uv run clipengine list                    what the database holds per streamer
uv run clipengine fetch --dry-run         plan the most-viewed stretches of finished VODs
uv run clipengine fetch --top 3           ... and download only those (yt-dlp, source quality)
uv run --extra gpu clipengine analyze     transcripts, F1 cuts, review packages in data/review/
uv run clipengine judge ID --file F.json  store Claude Code's verdict on package ID
uv run --extra gpu clipengine render ID   cut list, 1080x1920 render, checks; a pass lands in data/ready/
uv run --extra dev pytest -q              tests (offline, against a fake Twitch/YouTube)
```

- **Render (p1.4 to p1.6):** the cut list (`edl.json`) is the only render input. Facecam
  (1080x640) over gameplay (1080x1280), both cropped by the streamer's profile in
  `config/layouts.yaml`; ASS captions from the word times (2 to 4 words, spoken word
  highlighted, fillers dropped), the hook boxed on top for ~3 s, `twitch.tv/{name}`
  throughout; two-pass loudnorm to -14 LUFS; style sets rotate per moment.
- **Gameplay window (`follow.py`):** owner 2026-11-19, the gameplay fills the whole band
  and the main object stays completely visible. A 912x1080 window (the band's aspect)
  follows the main object: 4 fps samples, YOLOX-m on the CPU (about 0.25 s a frame),
  hysteresis against other objects, a box the centre line runs through is mirrored about
  it (the chase camera keeps the vehicle centred, boxes miss a wing), a smoothed path fed
  to the crop per frame by `sendcmd`. The model is one download, not in git:
  `data/models/yolox_m.onnx` from the YOLOX release `0.1.1rc0` (sha256 `21ff6cfd...`).
- **Encoder:** ffmpeg 8.1 needs NVENC API 13.1 (NVIDIA driver 610+); since driver 621.24
  (2026-11-19) `h264_nvenc` opens. Without it the renderer falls back to x264 on the CPU.
- **Checks:** 1080x1920, F1 length and cut-list length, -14 +-1 LUFS, no silence over 2 s,
  no black or frozen stretch, captions within 0.2 s of the render heard again by Whisper,
  no bars in the gameplay band, the main object inside the window in every sample (an
  object wider than the window keeps the band filled and is only recorded, owner
  2026-11-19), and no stretch of 0.75 s or more in the band (caption line left out) that
  is black, paused (map, menu, title or load screen) or a menu over the blurred game
  (weapon wheel). Thresholds and their calibration are in `produce.py` above
  `band_stretches`. A menu that is part of the moment passes with
  `render ID --accept-band REASON`; the reason lands in `check.json`.
  Failures stay in `data/renders/{id}/` with `check.json`.

- **Analyze (p1.3):** faster-whisper large-v3 (int8_float16, CUDA) transcribes each fetched
  section with word times; the F1 cut (15 to 60 s) starts at the sentence the top clip begins
  in and ends at the sentence end after it. Measured 2026-11-19 on the RTX 3060 Laptop:
  120 s of audio in 4 to 8 s (up to 32 s on music), model load 14 s, peak VRAM 2.5 of 6 GB.
  The `gpu` extra carries the Windows cuBLAS / cuDNN wheels; audio is decoded with ffmpeg
  because faster-whisper's PyAV decoder breaks on the current `av`. Hugging Face is reached
  over IPv4 (same IPv6 resets as yt-dlp).
- **Judge:** `review.json` with `verdict` (keep / reject), `spoiler`, `cutscene`, `adult`
  (none / defuse / reject), `category`, 2 to 3 `hooks`, `title`, optional `in_s` / `out_s`.
  A keep is refused with a spoiler, a cutscene, an adult reject, or a title that does not
  name the streamer (the channel description promises that).

- **Fetch (p1.2):** viewer clips are laid on their VOD, overlapping clips merge into one
  interval weighted by summed views, intervals touching Twitch `muted_segments` are skipped, and
  only the strongest N are downloaded with 5 s pad (`--download-sections`, max 120 s centred
  on the most-viewed clip). A VOD still being recorded is planned up to 30 min behind live
  and never marked fetched, so the next run picks up what was recorded since (launch streams
  run for days); ffmpeg reads its live playlist from segment 0 (`-live_start_index 0`), from
  the live edge it hung. A download hung past 600 s fails its section. Streamers without public
  VODs: clips made within 90 s of each other are one moment, its most-viewed clip is
  downloaded. Files land in `data/{streamer}/{vod}/sections/` and `data/{streamer}/clips/`;
  no download under 50 GB free (`CLIPENGINE_MIN_FREE_GB`).
- **`vod_offset` is the clip's END**, not its start as Twitch's API reference says. Measured
  2026-11-19 by matching three clips' audio against their VODs (6.4 / 17.6 / 33.7 s long, two
  VODs): the clip starts at `vod_offset - duration`, within about 1 s.

- **Register:** `config/streamers.yaml` (tracked). Suggestions never enter it on their own.
- **State:** `engine/data/clipengine.sqlite` of the PRIMARY checkout, whichever worktree runs
  the engine, so every session sees the same history. The folder ignores itself (`.gitignore`
  with `*`). Schema in `src/clipengine/db.py` as numbered migrations; later phases add tables.
- **Secrets:** `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` from
  `../context/.env`; in a git worktree the primary checkout's copy is used.
- **Overrides** for dry runs: `CLIPENGINE_DATA_DIR`, `CLIPENGINE_REGISTER`, `CLIPENGINE_ENV_FILE`.
- **YouTube** uploads come from the channel's public feed (no API key, no quota, latest 15
  uploads); duration and the most-replayed curve come from yt-dlp in p1.2.
- **Twitch** clips are re-read over the whole window on every watch, because views keep growing
  and `vod_offset` is filled in late. Clips of every game are stored; later stages filter on
  the GTA VI category (`config.GTA6_GAME_ID`).
