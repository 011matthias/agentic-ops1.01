---
project: gta6-clipping
workstream: p1-clip-pipeline
group: 
spec: p1
state: active
updated: 2026-11-19
---

# gta6-clipping / p1-clip-pipeline

Turn other creators' GTA6 streams and videos into clips on TikTok, YouTube
Shorts and Instagram Reels, earning through the platforms' view payouts.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Format | done | Owner 2026-11-17: streamer clips and VODs, analyzed, auto-assembled and edited (subtitles, hooks, effects); single moments and compilations over a minute | Build per master plan | none | [Master plan](../specs/2-build/p1-clip-engine.md) |
| p1.1 Watch (engine) | done | Built 2026-11-17: register, SQLite, Twitch VODs + viewer clips, YouTube feed, `suggest` / `approve` / `reject`; 38 offline tests; live match against the Twitch pages for LIRIK and KaiCenat; merged PR #1758. Register is still empty | none | none | [engine/README](../engine/README.md) |
| Start streamers | done | 10 approved 2026-11-19 from the launch-day `suggest --since 24h` (English clip views): ohnePixel, xQc, Lacy, jasontheween, IShowSpeed, KaiCenat, TheBurntPeanut, LIRIK, caseoh_, stableronaldo. One-hit and flagged names left out (Zoil, Clix, Dinah, king_wolfe_, Zerkaa). First watch over 1 day: 8 have a VOD; caseoh_ and IShowSpeed keep no public VOD, so their moments come from the clip itself | 22 Nov: `suggest --since 72h`, swap streamers who stopped playing GTA | none | [Spec stage 1](../specs/2-build/p1-clip-engine.md) |
| Source + highlights (p1.2) | done (Twitch) | `clipengine fetch` built 2026-11-19: overlapping viewer clips merge into intervals weighted by summed views, muted stretches excluded, VODs still recording skipped, strongest N downloaded as sections (yt-dlp, 1080p60, 5 s pad, max 120 s); streamers without VODs get their top clips. First live run: 21 sections from 5 finished VODs plus caseoh_ / IShowSpeed clips, every file the requested length by ffprobe. `vod_offset` is the clip END (audio match of 5 clips, within ~1 s). IPv6 reset ~40 % of requests, so yt-dlp runs over IPv4 | YouTube curve after the first video | none | [Spec stage 2](../specs/2-build/p1-clip-engine.md) |
| Analyze + judge (p1.3) | done | `clipengine analyze` / `judge` built 2026-11-19: local Whisper large-v3 on the GPU (120 s audio in 4 to 8 s, 2.5 of 6 GB VRAM), F1 cut at sentence boundaries, review packages. First 21 moments: 2 kept (ohnePixel jet crash, caseoh_ scooter chase), 6 rejected (strip club, 4 story cutscenes, a radio song), 13 open | Render the first F1 video | none | [Spec stage 3](../specs/2-build/p1-clip-engine.md) |
| Edit + render + checks (p1.4 to p1.6) | done | `clipengine render` built 2026-11-19: cut list, facecam over gameplay from `config/layouts.yaml` (ohnePixel calibrated), word-highlighted captions, hook, name tag, -14 LUFS, checks. First video `data/ready/m5-f1/` (ohnePixel jet crash) shown to the owner, not posted. Owner feedback 2026-11-19: layout, captions, hook style good; length ~1 min (now 55.7 s, cut target 55 s with whole sentences); the shown hook names GTA6 ("ohnePixel playing GTA6 for the first time", enforced by judge). NVENC needs NVIDIA driver 610+ (laptop: 560.94); owner approved the update to 621.24, x264 fallback until then | Verify NVENC after the driver install; caseoh_ layout + video; check the gameplay band for menus | none | [Spec stages 4 to 6](../specs/2-build/p1-clip-engine.md) |
| Channels | in-progress | YouTube channel cl1pmaxxers created 2026-11-17, nothing posted. Engine read access works: Google Cloud project + Desktop OAuth client, owner consent (youtube.readonly, yt-analytics.readonly), channel and Analytics queries answer (Analytics 403 before the channel existed, 200 after). OAuth app still in test mode (token expires after 7 days; Branding incomplete). Channel art (PR #1761) uploaded by the owner 2026-11-19 on YouTube and TikTok, profile with CL1P. TikTok: owner has an old account (last post 2025-04-07, other content); reuse depends on its Kontostatus (third-party guides: Business accounts excluded from Creator Rewards) | Owner: give a takedown contact email for `[KONTAKT-E-MAIL]`, send the TikTok Kontostatus screenshot. Before p2 runs on a schedule: finish Branding, publish the OAuth app, consent again | Owner | IDs and tokens in gitignored `context/accounts.md` |
| Publish (p2) | not-started | Aggregator APIs carry the platform audits. Owner 2026-11-17: clip any streamer, drop one on complaint, so p2 needs a claim/complaint watch that sets `permission: no` and takes that streamer's videos down | Pick aggregator; connect accounts | p1 first video | [README](../README.md) |
| Learning loop (p2) | not-started | Plan agreed 2026-11-17: each video's recipe from the cut list (format, length, hook, teaser, category, streamer, style set, post time); metrics at 24 h / 3 d / 7 d; retention curve laid over the cut list to find drop points, weekly rules into a playbook p1.4 follows; winning variants get more of the next videos with a fixed test share; per platform, minimum views before a rule changes, metric fixed in advance. YouTube retention curve via Analytics API (third-party docs, verify on the first video); TikTok watch time via API reportedly only for Creator/Business accounts, fallback TikTok Studio in the browser | Spec as p2 once posting starts | Posting | |
| Monetization gates | not-started | YouTube 1,000 subs + 10M Shorts views / 90 days; TikTok 10,000 followers; Instagram no per-view payout in DE | Track progress per account once live | Accounts | [README](../README.md) |
| Everygen MCP | blocked | Registered, not signed in; voiceover useful if the format adds narration | Sign in once the format needs voiceover | Paid plan + owner OAuth | [README](../README.md) |

States: not-started · in-progress · blocked · done · live · paused

## Open decisions / gates

- Decided 2026-11-17: clip other creators; earn through platform payouts,
  not clipping campaigns.
- Decided 2026-11-17: no API LLM costs (judgment by Claude Code on the
  subscription); where detectable, only the most-viewed intervals count
  (Twitch viewer clips, YouTube heatmap via yt-dlp).
- Decided 2026-11-17: clips in English; Claude Code picks the start
  streamers from launch (19 Nov) by English clip views, owner signs off.
- Twitch developer app: in primary clone `context/.env`, app token verified
  2026-11-17; Twitch game_id for GTA VI is 1867279146. The engine reads it
  from any worktree via the primary checkout; secrets are never copied.
- Decided 2026-11-17 (build): YouTube uploads via the public channel feed,
  not the Data API (no key exists, none needed until p1.2's yt-dlp).
- Third-party services (owner question 2026-11-17): only posting clearly
  needs one (TikTok audit); transcription, music and voiceover only if the
  local path or the format calls for it; AI clipping tools declined (template
  look, cost per input minute, duplicate our free views signal).
- Decided 2026-11-17: clip any streamer without asking first and drop one on
  complaint or claim; owner accepts the strike risk (three YouTube copyright
  strikes in 90 days end a channel).
- Decided 2026-11-17: owner creates the YouTube channel and TikTok account
  now; nothing is posted until p1 delivers approved videos.
- Autonomy gates (agreed 2026-11-17): production runs alone with per-video
  approval once p1.2 to p1.7 stand and three hand-started runs pass without
  intervention; posting after approval comes with p2; posting without
  approval only after 30 consecutive videos approved unchanged and no
  copyright claim.

## Pointers

- Master plan: [specs/2-build/p1-clip-engine.md](../specs/2-build/p1-clip-engine.md)
- Engine: [engine/README.md](../engine/README.md)
- Project overview and verified facts: [README](../README.md)
- Context (gitignored): `workspace/projects/gta6-clipping/context/`
