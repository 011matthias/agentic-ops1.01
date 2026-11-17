# GTA6 Clipping

Side project, started 2026-11-17: short GTA6 gameplay clips for TikTok,
YouTube Shorts and Instagram Reels. Goals, cadence, accounts and
monetization are not defined yet; the owner is sending details.

Element-by-element state: [status/p1-clip-pipeline.md](status/p1-clip-pipeline.md).

## Facts checked 2026-11-17

**GTA6 launches 19 Nov 2026 on PS5 and Xbox Series X|S; no PC version
announced** ([TechRadar](https://www.techradar.com/gaming/grand-theft-auto-6-release-date-confirmed-but-its-been-delayed-heres-why),
Take-Two statements). Every clip starts as a console recording.

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
