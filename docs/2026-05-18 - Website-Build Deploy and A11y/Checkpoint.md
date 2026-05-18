# Checkpoint: Website-Build Deploy and A11y

**Date:** 2026-05-18
**Status:** SHIPPED. 3 bespoke demo sites live on Fly, real imagery, WCAG 2 AA verified, deliverable-rule regression closed. PRs #21 + #22 merged to main.

> Continues "Website-Build Capability Rebuild" (same day). That session scaffolded + built praxis-uslu as the proof page; this session finished the capability end-to-end and deployed it.

---

## Summary
Built coffee-boxx + pronto-pronto to the praxis-uslu bar, wired a real Pexels imagery pipeline across all three, deployed one Astro→nginx Fly app, and drove the quality gates to green — including a hard a11y debugging episode that exposed the Lighthouse CLI as unreliable in this Windows env (switched the gate to axe-core-via-CDP).

---

## What Was Done This Session
### Build
1. `Figure.astro` — auto photo-or-honest-slot (zero markup change on swap).
2. `scripts/fetch-imagery.mjs` — Pexels pipeline; 10 curated photos (no people, per-BRIEF), committed for hermetic Fly builds; attribution → `imagery.json`.
3. praxis-uslu rewired to real imagery; coffee-boxx + pronto-pronto built full (B4-safe `data.ts`, bespoke signature sections, CafeOrCoffeeShop / Restaurant JSON-LD).
4. `tools/validate-dist.py` + npm `postbuild` gate — closes the 2026-05-08 regression (Astro `dist/` was unscanned for em-dash/`&mdash;`/`--`).
5. `skil_web-build` skill written + registered; later hardened with the a11y-verification lesson.
6. Deploy infra: Dockerfile (nginx), `fly.toml` (local-web-ka/fra), `nginx.conf`, `.dockerignore`. Fly app created + deployed (multiple iterations).
7. `infrastructure.yaml` created (was absent).

### Quality gates (verified live)
- Performance 100, Best-Practices 96 (all 3).
- Accessibility **0 WCAG 2 A/AA + 2.1 violations** all 3 — via axe-core injected through CDP (authoritative).
- SEO: demos `index, follow` (owner directive); internal directory `noindex` via `BaseLayout indexable` prop.
- Deliverable-rule: zero violations across dist, structurally gated.

---

## Key Decisions Made
### Imagery via Pexels API (owner-chosen), committed to repo
- **Choice:** Owner supplied a Pexels key; pipeline downloads, images committed.
- **Rationale:** Hermetic Docker/Fly build (no key at deploy); re-runnable; meets the spec's "real imagery" definition-of-done.

### Allow indexing on demos (owner directive, against my recommendation)
- **Choice:** Demos `index, follow`; only the internal directory stays `noindex`.
- **Rationale:** Owner explicitly chose discoverability over the privacy posture I recommended. SEO category now passes.

### A11y gate = axe-core via CDP, not the Lighthouse CLI
- **Choice:** Authoritative a11y verification is axe-core run through `chrome-remote-interface`.
- **Rationale:** The Lighthouse CLI in this Windows env silently re-parsed a stale (18:25Z) JSON across deploys and disagreed with both `curl` and CDP `getComputedStyle`. axe-core is the same engine, run directly = trustworthy.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| app/src/components/Figure.astro | Created | Auto photo-or-slot image primitive |
| app/scripts/fetch-imagery.mjs | Created | Pexels imagery pipeline |
| app/src/pages/{coffee-boxx,pronto-pronto}.astro | Created | Two sites to the praxis bar |
| app/src/sites/{coffee-boxx,pronto-pronto}/data.ts | Created | B4-safe sourced content |
| app/src/sites/*/imagery.json + src/assets/* | Created | 10 committed curated photos + attribution |
| app/src/pages/praxis-uslu.astro | Modified | Real imagery; a11y (nav CTA, .tbc) |
| app/src/layouts/BaseLayout.astro | Modified | `indexable` prop (SEO posture) |
| app/src/styles/global.css | Modified | In-text link underline `!important` (a11y) |
| app/src/sites/{praxis-uslu,coffee-boxx}/theme.css | Modified | Deepened muted/accent for AA contrast |
| tools/validate-dist.py | Created | Deliverable-rule dist gate (npm postbuild) |
| .claude/skills/skil_web-build/SKILL.md | Created+Modified | Structural quality bar + a11y-verification lesson |
| workspace/projects/local-web/infrastructure.yaml | Created | Fly infra, sites, gates, status=live |

---

## Current Status
Live at **https://local-web-ka.fly.dev/** (`/praxis-uslu`, `/coffee-boxx`, `/pronto-pronto`). All objective gates green; merged to main (commits 71d8703, 9e21e23). local-web is an internal initiative — no comms log, no platform section, no orchestrator (ops/reconciliation N/A).

---

## Next Steps
1. **Owner:** visual reference-parity call on the live URL vs each BRIEF's award-tier anchors (subjective, not automatable; the only gate I cannot run).
2. Leave-behind QR cards still need the owner's real name + contact line (deferred, not fabricated) before any real pitch.
3. Optional: a per-business personalization pass before any site is actually sent (praxis approach copy is generic-but-factual; flagged in-page).
4. Decide design-from-references vs buy a premium theme base before scaling past 3 sites (changes per-site cost model + skill shape).

---

## Context for Next Session
### Files to Read First
- `workspace/projects/local-web/infrastructure.yaml` (canonical: Fly app, sites, gates)
- `.claude/skills/skil_web-build/SKILL.md` (the process + the a11y-verification lesson)
- `workspace/projects/local-web/REBUILD-SPEC.md` (the contract)
- `workspace/projects/local-web/app/src/pages/praxis-uslu.astro` (quality reference)

### Open Questions
- Reference-parity verdict (owner visual).
- Theme-base vs design-from-references at scale.

### Working Notes
- **Lighthouse CLI is unreliable here.** `npx lighthouse` stops re-running silently (re-parses stale JSON; chrome-launcher `destroyTmp` throws on Windows after results write). Use the axe-core-via-CDP harness pattern instead (forward-slash Chrome path — bash heredocs mangle backslashes; `chrome-remote-interface` + inject `axe-core/axe.min.js`; `CSS.getMatchedStylesForNode` for contrast root-cause).
- A11y root causes found (all fixed + re-verified 0 violations): (a) muted/accent tokens just under AA on light themes — deepened; (b) `.tbc` chip accent-on-tint — switched to ink-on-tint + accent border; (c) bare in-text links had `text-decoration:none` from component rules overriding base underline — forced `a:not([class])` underline `!important`; (d) pronto contact links `#e0612b` on dark surface = 4.43:1 — lightened to `#ef7a42` link-only.
- The header-CTA "color-contrast" Lighthouse flagged was a STALE false report — CDP proved it computed white-on-accent (5.35:1) all along. Hours lost trusting the stale CLI.
- Fly deploy: `flyctl` at `C:\Users\neuma_p1qrsic\.fly\bin\flyctl.exe` (not on bash PATH; call via PowerShell or full path). `flyctl deploy {app-abs-path} --config {fly.toml} --remote-only --now`. Pass absolute paths — relative path doubled (bash cwd was already app dir).

### Reference Materials
- Live: https://local-web-ka.fly.dev/
- Old prototypes (reference only): https://webvorschau-ka.vercel.app/{slug}
- PRs: #21 (build+deploy), #22 (infra+skill note)

---

## How to Continue
The capability is shipped and live. Next real work is owner-gated (parity verdict, QR card details, personalization before any pitch). For any new site: follow `skil_web-build` — and use axe-core-via-CDP for the a11y gate, never the Lighthouse CLI in this env.

---

## Strategic Feedback

### What Worked Well This Session
- "Do what you recommend" + answering the one escalation question crisply (SEO posture + "keep digging") kept a long autonomous session moving with a single well-placed intervention. Providing the Pexels key immediately when surfaced as a USER ACTION unblocked the whole imagery path without a stall.

### Suggestions
- When a quality gate depends on an external CLI, validate the CLI's freshness ONCE up front (does its output change when the input does?) before trusting it across iterations. A 30-second sanity check would have saved the bulk of this session's wasted loops.

### System Health
- **Tooling gap (now structural):** the a11y gate had no reliable runner in this env. Fixed by documenting axe-core-via-CDP in `skil_web-build` + `infrastructure.yaml`. Worth promoting to a reusable `tools/axe-check.cjs` so it is not re-authored per session (candidate `infrastructure-deferred` if it recurs).
- Autonomy score: 2 human interventions this session (escalation decision; wrap-up direction) — not elevated, but one `iteration-limit-breach` occurred (a11y, 3-gate exceeded) rooted in trusting a stale tool.
