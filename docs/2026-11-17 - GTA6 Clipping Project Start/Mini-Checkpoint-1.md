# Mini-Checkpoint: GTA6 Clipping Project Start

**Date:** 2026-11-17
**Status:** Plan done (p1 spec on main), Twitch access verified, build of p1.1 not started
**Type:** mini

---

## Summary

New internal side project `workspace/projects/gta6-clipping/`: clip other creators' GTA6 streams and videos into vertical shorts for TikTok, YouTube Shorts and Instagram, monetized later through platform payouts. The master plan p1 (seven stages, views-first, no API LLM costs) is merged; the Twitch developer app works and the owner's language and streamer-selection decisions are recorded.

## What Was Done

- Project scaffold, README with verified platform and policy facts, status file, `.gitignore` for `context/` (PRs #1750 to #1753).
- Master plan `specs/1-spec/p1-clip-engine.md` (#1754), revised to views-first + no API costs (#1755) and owner decisions (#1756).
- Owner-facing page published: https://claude.ai/artifact/9R8xvYEy9gM4ZUzteZi2Eg (private; source is a scratchpad file, not in the repo).
- Everygen MCP registered as `everygen` in the primary clone's `.mcp.local.json` (scope gta6-clipping); not signed in, and only useful for voiceover now.
- Twitch developer app: owner put Client-ID and Secret in the primary clone's `workspace/projects/gta6-clipping/context/.env`; app token minted; GTA VI game_id `1867279146`; Get Clips returns view_count, duration, vod_offset, video_id on real clips.
- yt-dlp 2026.10.26 (via `uvx`) returns a 100-point `heatmap` (YouTube most-replayed) without downloading; `claude` 2.1.212 is on PATH for `claude -p` runs.

## What Did NOT Work (and why)

- **Paid clipping campaigns as the business model:** owner declined; platform payouts are the model.
- **Claude API for moment scoring:** owner rejected API spend; judgment moves to Claude Code on the subscription.
- **Fetching Rockstar's video policy page directly:** WebFetch timed out twice and a curl with a browser user agent was refused by the auto-mode classifier; policy wording is cited from search results only.
- **Owner pasted Twitch browser cookies** instead of app credentials: not used, not stored; owner told to sign out and change the password.

## Current Status

Plan complete; nothing of the engine is built. Owner decisions: clips in English; Claude Code picks the start streamers from launch day (GTA6 releases 19 Nov 2026, PS5/Xbox) by English clip views, owner signs off. Pre-launch data is thin (497 GTA VI clips, ~20k views in 7 days, some trailer-loop accounts). No `infrastructure.yaml` beyond type/notes; no comms log (internal project).

## Next Steps

1. Build p1.1 (uv project `engine/`, SQLite schema, streamer register, Twitch/YouTube watch, discovery) in a fresh session.
2. From 19 Nov: rank English GTA VI streamers by clip views, propose 5 to 10 to the owner.
3. p1.2/p1.3 prototype on one real stream: interval selection, section download, faster-whisper on the 6 GB GPU, first review package answered in session.

## Files to Read First

- `workspace/projects/gta6-clipping/specs/1-spec/p1-clip-engine.md`
- `workspace/projects/gta6-clipping/status/p1-clip-pipeline.md`
- `workspace/projects/gta6-clipping/README.md`
