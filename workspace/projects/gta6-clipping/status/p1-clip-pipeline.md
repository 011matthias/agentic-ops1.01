---
project: gta6-clipping
workstream: p1-clip-pipeline
group: 
spec: 
state: active
updated: 2026-11-17
---

# gta6-clipping / p1-clip-pipeline

From console recording to a posted clip on TikTok, YouTube Shorts and
Instagram Reels.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Everygen MCP | blocked | Registered as `everygen`, not signed in | Owner: Everygen plan, then `/mcp` → everygen → Authenticate | Paid plan + OAuth sign-in (owner only) | [README](../README.md) |
| Capture | not-started | GTA6 out 19 Nov 2026, PS5 / Xbox only | Pick console and recording path (built-in capture or capture card) | Owner details pending | [README](../README.md) |
| Edit (cut, captions, voiceover) | not-started | Everygen covers upload, captions, voiceover; cutting itself is untested | One test clip end to end once the MCP is signed in | Everygen MCP | |
| Publish | not-started | Everygen has no posting scope; aggregator APIs have the platform audits, own TikTok app needs one | Choose aggregator vs own apps | Owner details pending | [README](../README.md) |

States: not-started · in-progress · blocked · done · live · paused

## Open decisions / gates

- Owner input pending: accounts (new or existing), niche and clip style,
  posting cadence, monetization goal.
- Source material: own console recordings, streamer footage under a clipping
  deal, or AI generation. Rockstar's policy text ("occasional,
  non-commercial", no spoilers) sits badly with high-volume monetized
  clipping; decide before building.

## Pointers

- Project overview and verified facts: [README](../README.md)
- Context (gitignored): `workspace/projects/gta6-clipping/context/`
