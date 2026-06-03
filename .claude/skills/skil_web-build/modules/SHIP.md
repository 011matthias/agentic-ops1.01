# Module: SHIP

Load at **Build Procedure step 4**. Detail behind Definition-of-Done items 3, 9, 10,
11, 13, 14 in `SKILL.md`. Build success is not aesthetic success and a green build is
not a live site — this module is the gauntlet between "looks done" and "is done".

Companion references:
- `references/deploy-internals.md` — nginx redirect config + the cached-301 trap
- `references/a11y-verify.md` — the axe-core-via-CDP method (NOT the Lighthouse CLI)

## 1. Deliverable-rule gate (structural)

`npm run build` runs `postbuild` -> `tools/validate-dist.py ./dist`: fails on em-dash
U+2014, `&mdash;`/`&#8212;`, or typographic `--` in visible HTML. A failing build must
not deploy. Fix at SOURCE, never rely on the minifier. (See incidents.md → 2026-05-08.)

## 2. Deploy via the one canonical path

**Ship via `uv run tools/local-web-deploy.py`** — it builds, runs `flyctl deploy`,
then fetches each `fly.dev` URL (cache-busted) and asserts the live origin serves
*this exact build* by matching content-hashed `/_astro/` asset refs. It cannot return
green without the production URL serving the bytes you just built.

A localhost `astro preview` proves the build OUTPUT, never the deployed ORIGIN;
"live" is a fact about `fly.dev`, full stop. (See incidents.md → 2026-06-01.) Raw
`flyctl deploy {app-abs-path} --config {fly.toml} --remote-only` still works for
one-offs, but then you owe the live-origin check by hand.

nginx config is locked and load-bearing — `absolute_redirect off; port_in_redirect
off; server_name_in_redirect off;` plus the `try_files $uri $uri/index.html $uri.html
$uri/ =404;` chain. No 301s, ever; a cached 301 is unfixable client-side. The full
explanation and the ERR_CONNECTION_RESET regression are in
`references/deploy-internals.md`.

## 3. The real quality gate (non-negotiable, on the deployed Fly URL)

- **Lighthouse mobile ≥95** Performance, Best Practices, SEO on the DEPLOYED URL.
  SEO `is-crawlable` failing is expected if a page is intentionally `noindex`; gate
  as "all non-noindex SEO audits pass", do not strip noindex to chase the number
  unless the owner directs it.
- **Accessibility:** axe-core via CDP returns zero WCAG 2 A/AA violations. The
  Lighthouse CLI a11y output is NOT authoritative in this env — use the method in
  `references/a11y-verify.md`.
- **Reference-parity gate:** does the build sit credibly next to its BRIEF anchor
  sites? Screenshot-compare; the match-then-exceed articulation lives in
  `modules/CONCEIVE.md` §5.
- WCAG AA contrast, keyboard nav, semantic HTML.

Only after these pass is the site "done".

## 4. Handoff readiness

Each site owns its route, theme tokens, content, JSON-LD — designed to split cleanly
into the client's own repo at handoff. No shared business data between sites.

## 5. Ship authorization

Per `rule_no_auto_commit` (B6): these edits stop at the staging boundary. No
auto-deploy, no auto-PR, no auto-merge. `tools/local-web-deploy.py` is a deploy
command — it requires an explicit owner ship order in the current conversation.
local-web prototype edits are carved out of the commit gate, but a live deploy is not.
