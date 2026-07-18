# Deployment Spec — Meji Media "ROI Plan" doc-site page

Spec of the last deployment made to unpauseai.com.

| Field | Value |
|---|---|
| ID | p-meji-roi-plan |
| Type | Client-facing static doc-site page (Family B, active-client) |
| Surface | https://unpauseai.com/docs/meji-media/roi-plan (gated) |
| Access code | Live value is the Vercel env var `MEJI_ACCESS_CODE` (gates the whole `/docs/meji-media/` prefix). The code recorded in client comms, `meji2026`, is stale: rotated at the Vercel env level (comms-log flags a 500 on `/api/gate-unlock` for it). |
| PR / commit | #265 · `49a95b6` |
| Author | 011matthias (co-author: Fable 5) |
| Deployed | 17 July 2026 |
| Status | Merged to `main`; force-deploy / live render not verified in-session |

## Summary

One new client-facing strategy page under the existing gated Meji Media doc-site.
It answers a single question for the client (Gurmej): where the return on the
engagement comes from. Success is framed as repeat corporate accounts, not one-off
bookings: the stated goal of 5 to 10 big corporate clients booking more than once a
year, at roughly £20k+ per repeat account. The page maps three revenue routes, the
named-account layer, and the background work protecting deliverability.

## Access

Server-side gate only (per the platform gated-access standard). The page inherits
the existing `meji` gate:

- Registry: `platform/src/lib/gated-sites.ts` (id `meji`, cookie `meji-auth`,
  prefix `/docs/meji-media/`).
- Edge matcher: `platform/src/proxy.ts` (`/docs/meji-media` + `/docs/meji-media/:path*`).
- No new gate wiring was needed; the prefix already covers `roi-plan.html`.
- Code: `meji2026` (same code communicated to Gurmej for all gated pages).
  Caveat: comms-log 2026 entry noted a 500 from `POST /api/gate-unlock` on a
  `meji2026` test, flagged as a possible Vercel env-var rotation; if the code is
  refused at the login, the env value was rotated since.

## Scope of change (10 files, +557 / -1)

| File | Change |
|---|---|
| `platform/public/docs/meji-media/roi-plan.html` | New page (547 lines) — the deliverable |
| `platform/public/docs/meji-media/.deliverable-config.yaml` | Added `roi-plan.html` to the covered-files list; keeps copy-clipboard and Ctrl+K search suppressed per the site convention |
| `index.html`, `guide.html`, `system-overview.html`, `scaling.html`, `volume-forecast.html`, `lead-scoring.html`, `ab-testing.html`, `build-plan.html` | +1 line each: "ROI Plan" nav link added for roster consistency across the 8 existing pages |

## Page structure

Five sections, with a fixed sidebar and IntersectionObserver active-section
highlighting.

1. **The Goal** — 5 to 10 repeat corporate accounts (Polestar rebooking as the
   model); £2k to £15k per event, £20k+ per year for a multi-event client;
   September into Christmas as the window to judge the engagement on.
2. **Three Routes** —
   - Warm re-engagement (tag: *Live, converting*): the proven converter, single
     mailbox today; a second warm sender proposed before the season.
   - September corporate (tag: *In build for September*): the volume route for the
     £2k to £15k contracts, timed to a 1 September start; approved copy locked,
     UK-wide list in build.
   - Referral partners (tag: *Ready to turn on*): the untapped multiplier via event
     agencies sitting on corporate rosters.
3. **The Named-Account Layer** — the 12 client-named accounts plus 14 sourced
   lookalikes, the £20k+/yr repeat-buying targets worked by name across all three
   routes; the 12 run through HubSpot.
4. **What Protects the Pipeline** — four background controls: sender monitoring
   (Live), list verification (Live), inbound headroom (Warming), domain
   anti-spoofing (In progress).
5. **The Read Ahead** — timeline: Now/July (warm converting, foundations laid) →
   September to October (corporate buying window) → Christmas season (fullest read,
   measured in pounds against the repeat-account goal).

Hero stats: `8` live opportunities to date; `£20k+` per repeat account a year;
`September` as the read on the whole engagement.

## Data provenance (B4)

Every figure traces to a live source or the client's own stated numbers:
the £2k to £15k / £20k+ figures and the 5 to 10 account goal are Gurmej's verbatim
words (comms-log north-star, Block 27/28); the route status tags and the protection
layer trace to live Instantly pulls and the pilot state.

## Standards compliance

- Design system reused verbatim: theme boot script (no flash), dark/light toggle,
  print stylesheet, mobile sidebar; no CSS fork.
- Gated-access: server-side model only, no client-side password.
- Voice: narrative prose, zero em-dashes.
- QoL carve-out: copy-clipboard and Ctrl+K deliberately suppressed to match the 7
  prior narrative pages, documented via the `deliverable-allow` marker and
  `.deliverable-config.yaml` (native Ctrl+F suffices; no shell/code blocks on the
  page).
- Validation (per commit): `validate-html` + `validate-deliverable` clean, 0 hits
  across all 9 pages.

## Deployment note

Merged to `main`. A merge does not by itself guarantee the platform is live (Vercel
git-integration lag); the page is confirmed live only after `tools/vercel-force-deploy.sh`
has run and a fetch of the no-slash URL returns the new build behind the gate. Not
verified in the session that produced this spec.
