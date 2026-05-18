# Gated Access Standard (server-side only)

**Hard constraint.** Every gated client page on the platform uses the
server-side gate model. Client-side / in-page JavaScript password gates are
banned: they ship the passcode in page source as plaintext, which is the
exact exposure this standard exists to remove. Reason: owner directive
2026-05-18 ("From now on access codes should only be server side model for
security reasons"). Applies retroactively, not just to new pages.

## The only sanctioned mechanism

- **Registry:** `platform/src/lib/gated-sites.ts` — `GATED_SITES` array.
- **Enforcement:** `platform/src/proxy.ts` — HMAC grant-cookie check at the
  edge before any gated HTML is served.
- **Unlock:** `platform/src/app/api/gate-unlock/route.ts` — validates the
  site code OR the master password, sets the grant cookie.
- **Login UI:** `platform/src/app/gate-login/page.tsx` — server-rendered,
  proxy rewrites to it (URL bar keeps the doc path).

Access codes and the master password live in **Vercel env vars** and are
never committed to git and never sent to the browser:

- Per-site code: the site's `accessCodeEnv` (e.g. `WIMMER_ACCESS_CODE`,
  `MEJI_ACCESS_CODE`).
- Master password: `MASTER_ACCESS_CODE` — unlocks **every** gated site.
- Grant-cookie HMAC secret: `GATE_AUTH_SECRET` (falls back to
  `WIMMER_AUTH_SECRET`).

## Adding a new gated client site (the only allowed path)

Two touches, both required:

1. Add a `GATED_SITES` entry in `lib/gated-sites.ts` (id, pathRoot,
   pathPrefix, cookie, accessCodeEnv, label).
2. Add the site's two literal lines to the `config.matcher` array in
   `proxy.ts` (`/docs/<site>` and `/docs/<site>/:path*`). The matcher must
   be a static literal — it cannot be derived from the registry.

Then set the site's access-code env var on Vercel. The master password is
enforced automatically by the shared unlock route — **never** write
per-site code-checking or a per-site master bypass. If a new gated page
does not get the master for free, the mechanism was bypassed: stop and use
the shared path instead.

## Prohibited

- `var SOMECODE = '...'` or any password/credential in HTML, client JS, or
  committed source.
- A second gate implementation. Reuse `gated-sites.ts`; do not fork it.
- Skipping the env var and hardcoding a code "temporarily".

**Enforcement.** Build-time: a client-side password literal in
`platform/public/docs/**` or `platform/src/**` is a `gated-access-violation`
friction event. The accuracy/verification gates in `rule_behaviors.md`
(B2: test behavior) apply — verify a new gate by hitting the live unlock
endpoint with both the site code and the master, not just by reading config.
