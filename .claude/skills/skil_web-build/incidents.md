# Incidents & decision log

The institutional memory behind the rules. Modules cite these by date ("see
incidents.md → 2026-05-18 nginx/301") so the normative text stays terse. Load this
when debugging a regression or asking *why* a rule exists. Newest first.

## 2026-06-03 — five-site aesthetic upgrade + Lists A/B operationalized

All five live sites (praxis-uslu, helmle-physio, meinzer-maler, pronto-pronto,
beauty-lounge) were upgraded against two owner-supplied standards: **List A**
(strategic / "why it's right for THIS job") and **List B** (visual craft / "looks
expensive at a glance"). North-star locked: not "would a designer admire this" but
**"would THIS owner pay, and would their customer act."** Both lists now live in
`modules/CONCEIVE.md` §0; Definition-of-Done items 16-22 make them checkable;
`tools/audit-local-web-aesthetics.py` mechanically pre-screens them.

Findings worth keeping:

1. **The set read as one template (List A1 failure).** Five sites were really three
   hero structures: praxis+helmle were near-identical (headline-left / facts-card-right)
   and pronto+meinzer both full-bleed-photo + overlaid-headline. Fix: five *distinct*
   hero structures — editorial split, stacked-cinematic, full-bleed overlay, panel +
   real-work photo, tri-band hover. This became the per-SET diversity gate (item 18).
2. **Imagery is the weakest layer, and Pexels' top hit is usually wrong.** Four traps
   hit in one pass: wrong-service (acupuncture needles for a Krankengymnastik practice),
   wrong-place (Reykjavík metal siding for a German Maler), garish off-palette
   background (candy-pink behind a crème-palette beauty shot), and smiley-model stock.
   Every fetched image must be *looked at* and re-queried until it is real-work /
   real-place, warm, on-palette. Faces out of frame beat headset-smilers. One CSS
   grade filter applied identically across a site's photos is the cheap way to make
   them read as one set (List B4).
3. **The honesty sentinel was leaking as a visual defect.** `[BITTE PRÜFEN]` chips
   rendered on live demos read as broken fields to an owner. Fix: `data.ts` keeps
   `CHECK`; the page renders a quiet "auf Anfrage" or omits the row (item 20, detail in
   `modules/DATA.md`). Honesty preserved, pitch-readiness restored.
4. **Logo/palette fights are real.** helmle's teal mark beside a clay CTA looked
   incoherent; resolved by promoting a logo-derived petrol-teal to the single accent
   (item 19). meinzer's copper "Werkstatt-warm" intent was under-deployed and read
   grey-corporate; fixed by landing copper on a panel + rule + marks rather than
   retuning the hex.

Mobile-vs-desktop contrast trap (re-confirmed): a copper mark at `text-lg` (18px) is
just under the bold large-text threshold, so axe-on-desktop passed while Lighthouse
mobile flagged it; bumping to `text-xl` (>=21.6px) put it back over the 3:1 large-text
line. Always read the MOBILE Lighthouse a11y, not just desktop axe.

## 2026-06-03 — Component convention + skill restructure

The skill was a single ~400-line `SKILL.md`: incident narratives interleaved with
normative rules, `§8` Definition-of-Done duplicating `§1–§6`, and fragile numbering
(`§3a`, `§4b`). Restructured to the `trigger-pack` hub-and-spoke shape: lean spine +
`modules/` (CONCEIVE/DATA/BUILD/SHIP) + `references/` + `components/` + this
`incidents.md`. Sustainability invariants: one home per rule, a single gate, growth
routes to a sub-file instead of bloating the spine. The 2026-05-26 checkpoint had
already flagged the split as due. Same change established `components/nav-bar.md` as
the first per-element standard, gated through Definition-of-Done item 15.

## 2026-06-01 — "live" declared off a localhost screenshot

A logo change was screenshotted on localhost, declared "live-verified", and never
deployed. Fix: built `tools/local-web-deploy.py` (builds + `flyctl deploy` +
fetches each `fly.dev` URL cache-busted and asserts the live origin serves *this
exact build* via content-hashed `/_astro/` asset refs). A localhost `astro preview`
proves build OUTPUT, never the deployed ORIGIN. Source of Definition-of-Done item 14
and the `feedback_live_means_deployed_origin` memory. Same day: owner directive made
the comparative-judgment gate match-then-exceed (anchor is a floor, not a ceiling).

## 2026-05-26 — Kowalski + frontend-design taste anchors integrated

Quantified motion craft (`references/motion-craft.md`), typography bans, the
comparative-judgment gate, and the background-depth rule landed (then `§3a`). The
"award-tier bar" became operationally citable, not per-session goodwill. The
`frontend-design` plugin co-load instruction was added at the top of the skill. This
session's PRs (#57/#58) auto-shipped unverified, which triggered `rule_no_auto_commit`
(B6) — the reason ship now stops at the staging boundary.

## 2026-05-19 — default motion tier + depth hero shipped

CSS-driven default motion tier (Ken Burns, scroll-reveal, card hover-lift) live on all
3 sites. Depth-map parallax hero implemented (`DepthHero.astro`, zero-dep WebGL1
shader, committed depth maps). Full contract + the `tools/depth-live.cjs` verify
method now in `references/depth-hero.md`.

## 2026-05-18 — nginx ERR_CONNECTION_RESET + the a11y/Lighthouse breach

Two regressions in one build cycle:

1. **nginx 301 leak.** Trailing-slash 301 leaked `http://host:8080/...` behind the Fly
   TLS edge; every `/<slug>` page died with `ERR_CONNECTION_RESET` in-browser while
   server-side curl still 200'd. Fix: `absolute_redirect off; port_in_redirect off;
   server_name_in_redirect off;` + `try_files … =404` (emit no redirect at all,
   because cached 301s are unfixable client-side). Full detail in
   `references/deploy-internals.md`.
2. **Stale-Lighthouse 3-iteration breach.** Trusted the Lighthouse CLI across ~4
   deploy cycles while it silently re-parsed a stale JSON; an a11y fix was theorized
   from axe HTML snippets instead of computed style (verification theater). Fix:
   axe-core-via-CDP is the authoritative method, read computed style not snippets
   (`references/a11y-verify.md`).

## 2026-05-08 — em-dash regression in dist/

Em-dashes shipped because `dist/` was unscanned. Fix: `npm run build` `postbuild` runs
`tools/validate-dist.py ./dist`, failing on U+2014 / `&mdash;` / `&#8212;` /
typographic `--` in visible HTML. Fix at SOURCE, never rely on the minifier. Source of
Definition-of-Done item 3.

## Open questions (carry forward)

- **Design-from-references vs buy a premium theme base:** still designing from
  references directly. Revisit before scaling past ~3 sites — it changes the per-site
  cost model and this skill's shape. (Open since the 2026-05-18 checkpoint.)
- Leave-behind QR cards need the owner's real name + contact line — never fabricated.
