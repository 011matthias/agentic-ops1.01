# Mini-Checkpoint: Brisken OnePilot Hero + Card Polish

**Date:** 2026-06-21
**Status:** Shipped to Fly prototype; brisken.com deploy planned (not started)
**Type:** mini

---

## Summary
Polished the Brisken OnePilot/TreasuryCentral prototype: the three TreasuryCentral
capability cards are now click-to-expand (reusing the page's `.qa-toggle` disclosure,
no new JS), and the hero was enlarged in length and width. Deployed live to the Fly
prototype and behavior-verified. Then strategized the next move: putting the prototype
on `brisken.com` (a subdomain on our host, Wix untouched, DNS edited at GoDaddy).

## What Was Done
- Made the 3 TreasuryCentral panel cards (One view of the money / FX and market data /
  Control built in) expandable, each revealing 2 sentences of governed-treasury detail.
  Reused the existing `.qa-toggle` + `.qa-chev` + generic toggle JS; markup = `.card-exp`
  wrapper with `qa-q`/`qa-toggle` head, `.card-teaser`, and `.qa-a.card-more` reveal
  (ids `tc-money`, `tc-fx`, `tc-control`). Added a `.card-exp` CSS block AFTER the
  centered-layout block so source order wins; `.grid-exp { align-items:start }` +
  `align-self:start` so an expanded card grows alone.
- Enlarged the hero: `.hero > .wrap` 1120 -> 1240px; `.hero-grid` padding 34/26 -> 62/56,
  gap 16 -> 26; `h1` clamp(30,3.9vw,46) -> clamp(40,5.4vw,70); `.hero-split` gap 32 -> 56;
  hero-art max-width 410 -> 540; hero `.big-stat` 60 -> 76px. Added a `@media(max-width:760)`
  tighten so mobile stays sane (padding 40/30, stat 54px).
- validate-html clean (0 hits); zero em-dashes / banned words in new content.
- Synced (`sync-site.py`, 3 files) + `flyctl deploy` to `brisken-onepilot-proto`.
- Behavior-verified on the LIVE gated site via Playwright (passed the name gate as
  "Matthias"): TC node opens, 3 cards present, all collapsed by default, clicking card 1
  sets `aria-expanded=true` and un-hides its reveal with the exact copy. Hero render
  confirmed via Chrome headless.
- DNS recon for brisken.com (public lookups): NS = `pdns01/02.domaincontrol.com` (GoDaddy
  is DNS authority); apex A `185.230.63.107` + `www` CNAME `td-ccm-neg-87-45.wixdns.net`
  (Wix hosts apex/www via the "Pointing" method, GoDaddy keeps the nameservers).

## Current Status
- Live: https://brisken-onepilot-proto.fly.dev/ (name-gated; enter any name). Both changes
  are deployed and verified.
- Source edits in `brisken-onepilot-website-prototype.html` are UNCOMMITTED. Repo HEAD is
  on `system/project-status-convention` (a concurrent session moved it off the Brisken
  branch). Deploy ships from the working tree, so live is correct regardless; the git
  commit is held pending the user's branch-routing decision.
- brisken.com deploy: strategized, not started. Recommended path = subdomain
  (`onepilot.brisken.com` / `treasury.brisken.com`) -> our host (stay on Fly via
  `flyctl certs add`, OR move to a static host if the name-gate is dropped). One CNAME +
  Fly's cert-validation records added at GoDaddy; Wix apex/www left alone.

## Next Steps
1. Decide branch routing, then commit the hero+cards edits (file:
   `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html`).
2. Start the brisken.com deploy (see the deploy prompt handed to the user this session):
   confirm subdomain label + keep-gate-or-public + who edits GoDaddy DNS; run
   `flyctl certs add <sub>.brisken.com`; hand Brisken the exact GoDaddy DNS records.

## Files to Read First
- workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html (the prototype)
- workspace/clients/brisken/onepilot-site/app.py + sync-site.py (Fly name-gate host)
- memory: project_brisken_onepilot_site_hosting.md, project_brisken_onepilot_positioning_decisions.md
