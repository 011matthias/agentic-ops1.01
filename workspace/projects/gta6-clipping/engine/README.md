# clipengine

The GTA6 clip engine (master plan: [p1-clip-engine.md](../specs/2-build/p1-clip-engine.md)).
Built so far: p1.1, register, SQLite state, Twitch and YouTube watch, streamer suggestions.

Run from this folder (`uv` installs everything on first use):

```text
uv run clipengine suggest --since 48h     top streamers by English GTA VI clip views, report in data/reports/
uv run clipengine approve LOGIN           owner said yes: append to config/streamers.yaml
uv run clipengine reject LOGIN            owner said no: never suggested again
uv run clipengine watch                   new VODs, YouTube uploads and viewer clips, last 7 days
uv run clipengine list                    what the database holds per streamer
uv run --extra dev pytest -q              tests (offline, against a fake Twitch/YouTube)
```

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
