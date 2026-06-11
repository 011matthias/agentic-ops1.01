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

**Ship via `uv run tools/local-web-deploy.py`** — the full gauntlet in one command:

1. `npm run build` (the deliverable-rule postbuild gate fires here)
2. `audit-local-web-aesthetics.py --strict` — hard-fail classes block the deploy
3. `flyctl deploy`
4. live-origin parity: fetch each `fly.dev` URL (cache-busted), assert the live
   HTML carries *this exact build's* content-hashed `/_astro/` asset refs
5. `axe-check.cjs` on each live URL — zero WCAG 2 A/AA violations (DoD 11)
6. `verify-rendered.cjs` on each live URL — hero actually paints (pixel variance),
   brand fonts loaded, motion markers live (DoD 14's behavior half)
7. advisory second opinion: `npx impeccable@2.3.2 detect dist/ --fast --json`
   (their 41 deterministic detectors; network/availability failures WARN loudly
   but do not block — OUR gates 1-6 are the authoritative ones)

It cannot return green without the production URL serving the bytes you just built
AND behaving correctly. **A skipped or unrunnable gate is a FAILED gate** — if
Chrome, node modules, or flyctl are missing, the tool exits 1 with the install
command; it never warns-and-continues past a hard gate (no graceful degradation;
source: CLI-Anything HARNESS.md doctrine, adopted 2026-06-11).

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

## 3b. TEST.md — plan-then-evidence (DoD item 23)

<!-- rule:web-ship-test-md -->
One markdown file per site, `app/src/sites/{slug}/TEST.md`, written in two passes:

- **At build start (plan pass):** list the gates this site will be verified
  against — the deliverable-rule scan, aesthetics audit, Lighthouse budgets, axe,
  live-origin parity, rendered-behavior probes — each with one line stating WHAT
  output property will be checked ("Verified: live HTML carries this build's
  hashed asset refs"). Writing the inventory before any check runs is the point:
  it records intent independent of what later happens to pass.
- **At ship (evidence pass):** append the verbatim tool output (the
  `local-web-deploy.py` gate summary, the axe PASS lines, Lighthouse scores)
  under a `## Results — YYYY-MM-DD` heading. One artifact then records both
  intent and evidence; B2's "name the specific test performed" gets a durable
  home instead of a claim in chat.

A gate listed in the plan with no evidence block under Results is an OPEN gate —
the site is not shipped. (Source: CLI-Anything HARNESS.md Phases 4+6, adopted
2026-06-11.)

## 4. Handoff readiness

Each site owns its route, theme tokens, content, JSON-LD — designed to split cleanly
into the client's own repo at handoff. No shared business data between sites.

## 5. Ship authorization

Per `rule_no_auto_commit` (B6): these edits stop at the staging boundary. No
auto-deploy, no auto-PR, no auto-merge. `tools/local-web-deploy.py` is a deploy
command — it requires an explicit owner ship order in the current conversation.
local-web prototype edits are carved out of the commit gate, but a live deploy is not.
