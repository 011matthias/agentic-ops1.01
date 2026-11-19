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
uv run --extra dev pytest -q              tests (offline, against a fake Twitch/YouTube)
```

- **Fetch (p1.2):** viewer clips are laid on their VOD, overlapping clips merge into one
  interval weighted by summed views, intervals touching Twitch `muted_segments` are skipped, and
  only the strongest N are downloaded with 5 s pad (`--download-sections`, max 120 s centred
  on the most-viewed clip). A VOD still being recorded is skipped. Streamers without public
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
