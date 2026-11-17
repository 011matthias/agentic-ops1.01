---
project: gta6-clipping
workstream: p1-clip-pipeline
group: 
spec: 
state: active
updated: 2026-11-17
---

# gta6-clipping / p1-clip-pipeline

Turn other creators' GTA6 streams and videos into clips on TikTok, YouTube
Shorts and Instagram Reels, earning through the platforms' view payouts.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Format | blocked | Raw clips of others earn close to nothing on YouTube and TikTok; payout needs added value and, on TikTok, videos over a minute | Owner picks the format | Owner decision | [README](../README.md) |
| Source + highlights | not-started | Twitch API ranks a game's clips by views; no official download endpoint | Prototype on one streamer's stream | Format | [README](../README.md) |
| Edit | not-started | Plan: local ffmpeg + Whisper, 9:16 facecam over gameplay, captions, hook; commentary layer depends on format | Prototype after source | Format | |
| Publish | not-started | Aggregator APIs carry the platform audits | Pick aggregator; connect accounts | Owner accounts | [README](../README.md) |
| Monetization gates | not-started | YouTube 1,000 subs + 10M Shorts views / 90 days; TikTok 10,000 followers; Instagram no per-view payout in DE | Track progress per account once live | Accounts | [README](../README.md) |
| Everygen MCP | blocked | Registered, not signed in; voiceover useful if the format adds narration | Sign in once the format needs voiceover | Paid plan + owner OAuth | [README](../README.md) |

States: not-started · in-progress · blocked · done · live · paused

## Open decisions / gates

- Decided 2026-11-17: clip other creators; earn through platform payouts,
  not clipping campaigns.
- Open: format (raw clips vs commentary/compilation over a minute),
  permission from the clipped streamers, accounts and platforms.

## Pointers

- Project overview and verified facts: [README](../README.md)
- Context (gitignored): `workspace/projects/gta6-clipping/context/`
