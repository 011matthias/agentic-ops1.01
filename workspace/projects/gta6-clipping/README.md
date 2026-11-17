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

## Layout

- `status/` workstream status, kept current
- `context/` gitignored: account logins, tokens, raw exports
