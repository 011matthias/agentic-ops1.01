---
project: gta6-clipping
workstream: p1-clip-pipeline
group: 
spec: 
state: active
updated: 2026-11-17
---

# gta6-clipping / p1-clip-pipeline

Clip other creators' GTA6 streams and videos under paid clipping campaigns,
post to TikTok, YouTube Shorts and Instagram Reels, submit for per-view payout.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Campaign intake | not-started | One GTA6 campaign open 17 Nov (song promo, wants own footage); no streamer-funded GTA6 campaign confirmed | Watch Content Rewards and streamer Discords from launch day 19 Nov | Owner: Content Rewards account | [README](../README.md) |
| Source + highlights | not-started | Twitch API ranks a game's clips by views; no official download endpoint | Prototype on one campaign creator's stream | No campaign picked | [README](../README.md) |
| Edit | not-started | Plan: local ffmpeg + Whisper, facecam over gameplay in 9:16, captions, hook; each clip re-cut, never duplicated | Prototype after source | Source | |
| Publish | not-started | Aggregator APIs carry the platform audits | Pick aggregator; connect accounts and link them in Content Rewards | Owner accounts | [README](../README.md) |
| Submit + track | not-started | Submission is manual (paste post link), some campaigns within 30 min of posting | Browser automation or one tap by owner | No submission API | [README](../README.md) |
| Everygen MCP | blocked | Registered, not signed in; only voiceover still useful | Sign in only if voiceover is wanted | Paid plan + owner OAuth | [README](../README.md) |

States: not-started · in-progress · blocked · done · live · paused

## Open decisions / gates

- Decided 2026-11-17: clip other creators, only under an active campaign or
  written permission.
- Owner input pending: Content Rewards account, which platforms, how many
  accounts, which streamers to target.

## Pointers

- Project overview and verified facts: [README](../README.md)
- Context (gitignored): `workspace/projects/gta6-clipping/context/`
