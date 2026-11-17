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
| Publish | not-started | Everygen has no posting scope | Choose a posting path per platform | Owner details pending | |

States: not-started · in-progress · blocked · done · live · paused

## Open decisions / gates

- Owner input pending: accounts (new or existing), niche and clip style,
  posting cadence, monetization goal.
- Rockstar's policy on posting and monetizing gameplay video: not checked yet;
  check before the first monetized upload.

## Pointers

- Project overview and verified facts: [README](../README.md)
- Context (gitignored): `workspace/projects/gta6-clipping/context/`
