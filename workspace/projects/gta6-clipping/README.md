# GTA6 Clipping

Side project, started 2026-11-17: short clips of OTHER creators' GTA6
streams and videos for TikTok, YouTube Shorts and Instagram Reels (owner
decision 2026-11-17; we do not clip our own play). Cadence and accounts are
not defined yet.

Element-by-element state: [status/p1-clip-pipeline.md](status/p1-clip-pipeline.md).
Master plan (workflow, phases, data model): [specs/1-spec/p1-clip-engine.md](specs/1-spec/p1-clip-engine.md).

## Business model: platform monetization (owner decision 2026-11-17)

Revenue comes from the platforms' own payout programs on views. Figures
are third-party estimates unless the link is the platform's own; checked
2026-11-17.

- **YouTube Shorts:** creators share 45% of the Shorts pool. Entry is 1,000
  subscribers plus 10 million Shorts views in 90 days (or 4,000 watch
  hours). From 1 Feb 2027 Shorts revenue needs 10 million qualified views in
  the preceding 90 days; reports differ on grandfathering
  ([Tubefilter](https://www.tubefilter.com/2026/08/10/youtube-partner-program-ad-eligibility-requirements-shorts/)).
  Gaming Shorts earn about $0.02 to $0.10 per 1,000 views, so $20 to $100
  per million ([vidIQ](https://vidiq.com/blog/post/youtube-shorts-monetization/)).
- **TikTok Creator Rewards:** about $0.40 to $1.00 per 1,000 qualified
  views, Germany about $0.62. Needs 10,000 followers, a personal account
  and videos over one minute
  ([ttcalculator](https://ttcalculator.net/learn/tiktok-pay-germany-earnings/)).
- **Instagram:** no general per-view payout found for Germany; the Reels
  bonus is invite-only (third-party guides).
- **Reused content:** YouTube monetizes clips of other people's content
  only with significant added value (commentary, editing, narrative),
  judged for the whole channel and even with the creator's permission
  ([YouTube help](https://support.google.com/youtube/answer/1311392)).
  TikTok's originality scoring pays reposts little or nothing. Raw clips at
  volume therefore earn close to nothing on the two platforms that pay; the
  format has to add value.
- **Copyright:** clipping without the creator's permission draws takedowns,
  and three YouTube copyright strikes in 90 days end a channel.

Considered and declined by the owner on 2026-11-17: paid clipping
campaigns (median $1.00 per 1,000 views across 710 campaigns,
[Content Rewards](https://contentrewards.com/articles/how-much-do-clippers-make)).

**Sources of footage:** Twitch's API lists a game's clips sorted by view
count, so viewers' own clips mark the strongest moments; there is no
official clip download endpoint
([Twitch docs](https://dev.twitch.tv/docs/api/clips/)).

## Facts checked 2026-11-17

**GTA6 launches 19 Nov 2026 on PS5 and Xbox Series X|S; no PC version
announced** ([TechRadar](https://www.techradar.com/gaming/grand-theft-auto-6-release-date-confirmed-but-its-been-delayed-heres-why),
Take-Two statements).

**Everygen MCP** (`https://everygen.ai/api/mcp`, formerly Viewmax):

- Auth is OAuth 2.1 with dynamic client registration at `www.viewmax.io`,
  so Claude Code signs in through `/mcp` with no API key. Unauthenticated
  calls answer 401.
- Scopes offered: `media:upload`, `image:generate`, `video:generate`,
  `voice:change`, `voiceover:generate`, `audio:generate`, `generation:read`.
  **There is no publish scope: Everygen cannot post to TikTok, YouTube or
  Instagram.** Posting needs a separate path.
- No free plan. Per everygen.ai: Starter $24/month (200 credits), Pro $49
  (500), Creator $139 (1,000); annual billing is cheaper. Credits do not
  roll over. Credit cost per operation is not published.
- Registered as server `everygen` in the gitignored `.mcp.local.json`
  (primary clone), scoped `gta6-clipping`: it renders in the primary clone
  and in any `client/gta6-clipping/...` worktree.

**Posting limits** (checked 2026-11-17, mostly vendor docs; re-check
before building):

- YouTube: `videos.insert` costs 1 unit from a separate Video Uploads
  bucket, 100 calls a day, and Google's reference now says uploads from
  unverified projects are not forced private
  ([docs](https://developers.google.com/youtube/v3/docs/videos/insert)).
- TikTok: an unaudited Content Posting API client posts private only, for
  at most 5 users per 24 h; public posting needs TikTok's audit. About 15
  posts per creator account per day, per third-party guides quoting
  TikTok ([TikTok docs](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post)).
- Instagram: Business account required. Meta's publishing guide says 100
  API posts per 24 h, its `content_publishing_limit` reference still says
  50; read the endpoint live per account
  ([Meta docs](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit)).
- Posting aggregators (Upload-Post, Ayrshare, Late/Zernio, Blotato) carry
  the platform audits already; their prices are unverified.

**Policy limits:**

- Rockstar's posting policy (January 2025 version, quoted from search
  results; the page timed out on a direct fetch) covers "occasional,
  non-commercial" fan use, puts spoilers off-limits and removes isolated
  cutscene videos
  ([Rockstar](https://support.rockstargames.com/articles/7bNaeoMFTV0iUDGhStTXvz)).
- YouTube "inauthentic content" (since 15 July 2025) demonetizes whole
  channels of template-made, minimally varied videos
  ([Social Media Today](https://www.socialmediatoday.com/news/youtube-clarifies-monetization-update-inauthentic-repeated-content/752892/)).
  Its pre-launch gaming update keeps graphic violence in the first 7
  seconds ineligible for ads
  ([Dexerto](https://www.dexerto.com/gta/youtube-updates-gaming-violence-monetization-rules-ahead-of-gta-6-launch-3405945/)).
- Meta (July 2025): accounts that repeatedly repost others' content lose
  reach and monetization
  ([TechCrunch](https://techcrunch.com/2025/07/14/following-youtube-meta-announces-crackdown-on-unoriginal-facebook-content)).

## Layout

- `status/` workstream status, kept current
- `context/` gitignored: account logins, tokens, raw exports
