# Checkpoint: Local-Web 3D Depth Hero and HTML Cache

**Date:** 2026-05-20
**Status:** Shipped — PRs #37, #39, #43, #44 merged; nginx + WebGL build live on Fly; live render + A/B parallax verified via fresh-profile headless; structural gates green.

---

## Summary
Closed the prior-session "nothing changed" open thread autonomously (proved fresh-client render via zero-cache headless probe → confirmed stale local browser HTML was the cause), shipped the recurring-friction structural fix (`Cache-Control: no-cache` on HTML), then built and live-shipped the 4b *budgeted WebGL depth-parallax hero* on all 3 sites — the actual 3D the user pointed out had never been implemented (only the CSS motion tier had).

---

## What Was Done This Session

### 1. Closed "nothing changed" without asking the user (B1)
1. Built `tools/local-web-shot.cjs` — fresh zero-cache headless profile + motion-marker probe.
2. Ran against live `praxis-uslu`: `kb-drift` Ken Burns animation computed live, 12 reveal elements, 11→0 hidden after scroll → `motionLive: true`. Stale-local-cache hypothesis confirmed by behavior, not assumed.

### 2. HTML `no-cache` (PR #37) — structural close of recurring stale-demo class
1. Root cause: nginx served the HTML shell with no `Cache-Control` → browsers heuristic-cached → redeploys invisible until hard refresh. Recurring across sessions for this user.
2. One-line server-level `add_header Cache-Control "no-cache" always;` — inherited only by `location /` (HTML, robots, sitemap); `/_astro/` + image blocks define their own `add_header` so fingerprinted assets keep `public, immutable` (nginx no-inheritance rule).
3. Shipped + deployed + **verified live**: HTML `cache-control: no-cache`, HTTP 200 + 0 redirects (no-301 fix intact), security headers still present (no inheritance regression); assets still immutable.

### 3. infra.yaml drift sync (PR #39)
Status line was stale at "2026-05-18 / PR #21"; resynced to reflect #24–#37 (and after #43/#44).

### 4. Budgeted WebGL depth-parallax hero on all 3 sites (PR #43) — the 3D
The skill's §4b budgeted WebGL hero was codified last session but never built; only the default CSS motion tier had shipped. This implements the real depth-parallax 3D:
1. `app/scripts/depth-map.py` — Depth-Anything-V2-Small ONNX via `uv` (PEP 723 inline deps); CPU inference on 3 hero photos. Hermetic: model cached, depth PNGs committed (mirrors the Pexels imagery pipeline). Worked first try in this Windows env.
2. `DepthHero.astro` — transparent enhancement of `<Figure>`. Poster is the unchanged optimized `<Image>` (still LCP, still the only thing in the no-JS / pre-init / reduced-motion / ≤768px / no-WebGL / Save-Data tree). Zero-dependency hand-rolled WebGL1 shader: object-fit cover math + edge inset zoom + clamp; pointer + sinus idle drift, lerped; lazy `requestIdleCallback` + IntersectionObserver init; RAF pauses off-screen; reduced-motion change tears down to poster. `canvas aria-hidden` → accessible tree unchanged.
3. Wired into all 3 hero `<Figure>` → `<DepthHero>` (gallery/signature Figures untouched).
4. Depth-quality verdict (visual on the generated maps): praxis-uslu strong, coffee-boxx clear, pronto-pronto subtle-by-design (shallow macro depth, suits calm art direction).
5. Gates: build + dist deliverable gate (em-dash etc.) green; **axe-core CDP 0 WCAG2 A/AA on all 3** local-preview; DOM-state probe (poster present, canvas active, `is-on`) PASS on all 3. Live-verified via `tools/depth-live.cjs` (fresh-profile, A/B pointer): praxis foreground plants visibly displace much more than background = real depth, coffee shows clear pour-vs-machine parallax, pronto gentle-by-design.

### 5. Self-anneal: ship the verify tool + skill+infra notes (PR #44)
1. `tools/depth-live.cjs` — reusable fresh-profile A/B pointer-parallax verifier for the 4b WebGL hero (full-page `captureBeyondViewport`; reliable in this env).
2. `skil_web-build` §4b — points at `depth-live.cjs` as the verify tool; records the hard lesson: trust composited screenshots, never `readPixels` a non-`preserveDrawingBuffer` context (undefined post-composite, false-fails).
3. `infrastructure.yaml` status synced to include #43 + the new verify tool.
4. Removed the bespoke `tools/depth-probe.cjs` (its CDP-`clip`-after-`scrollIntoView` reads the wrong region; `depth-live.cjs` supersedes it).

---

## Key Decisions Made

### Pick depth-map parallax over `<model-viewer>` GLTF for the budgeted WebGL slot
- **Choice:** Depth-map displacement on the real hero photo.
- **Rationale:** Skill says depth-map is the typical choice. A rotating 3D pizza / coffee cup is exactly the vertical-cliché the skill's anti-generic gate forbids. Depth-map preserves the photographic art direction.

### `no-cache` for HTML, not `max-age=60, must-revalidate`
- **Choice:** `Cache-Control: no-cache` on HTML.
- **Rationale:** This user has hit stale HTML *across multiple sessions* — definitive end of the class wins over micro-perf. `no-cache` still allows storage + cheap 304 conditional GETs (nginx does this automatically via ETag/Last-Modified). Fingerprinted assets keep immutable via their own location blocks (nginx no-inheritance rule).

### Ship #43 on local-preview structural gates + DOM probe, do the visual verification *live* with the proven tool
- **Choice:** Push/PR/merge/deploy with axe+dist+DOM-probe PASS; final visual A/B done on the deployed site with `local-web-shot.cjs`-class tooling.
- **Rationale:** Local probe iteration was burning cycles on a CDP-`clip` coordinate bug (my probe, not the product). The fall-back tool was already proven this session. Risk bounded by an immediate poster-only revert plan if live broke. Avoided a 4th probe iteration; live render verified cleanly.

### Self-anneal as committed tool (Layer 1), not memory
- **Choice:** `tools/depth-live.cjs` + skill pointer.
- **Rationale:** Per rule_behaviors Layer 1, tools beat memory. Verifying the 4b hero will recur on every future depth-hero deploy — a tool that fires deterministically is structurally better than a remembered procedure.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/projects/local-web/app/nginx.conf` | Modified | HTML `Cache-Control: no-cache` (PR #37) |
| `workspace/projects/local-web/app/scripts/depth-map.py` | Created | Depth-Anything-V2-Small ONNX depth-map pipeline (PR #43) |
| `workspace/projects/local-web/app/src/components/DepthHero.astro` | Created | Budgeted WebGL depth-parallax hero w/ poster fallback (PR #43) |
| `workspace/projects/local-web/app/src/pages/{praxis-uslu,coffee-boxx,pronto-pronto}.astro` | Modified | Hero `<Figure>` → `<DepthHero>` (PR #43) |
| `workspace/projects/local-web/app/src/assets/{3}/hero-depth.png` | Created | Committed depth maps (hermetic Fly build) (PR #43) |
| `tools/local-web-shot.cjs` | Created | Fresh-profile headless render + motion probe (PR #37) |
| `tools/depth-live.cjs` | Created | Reusable 4b WebGL hero live A/B verify tool (PR #44) |
| `.claude/skills/skil_web-build/SKILL.md` | Modified | §4b: implemented note + verify tool pointer + readPixels lesson (PR #44) |
| `workspace/projects/local-web/infrastructure.yaml` | Modified | Status drift sync (PR #39, then again in PR #44 to include #43 + verify tool) |

PRs merged to main: **#37, #39, #43, #44**.

---

## Current Status
All 3 sites live at https://local-web-ka.fly.dev/{praxis-uslu,coffee-boxx,pronto-pronto}/ — HTTP 200, HTML `no-cache`, assets `public, immutable`, depthhero markup + depth assets emitted, 0 WCAG2 A/AA violations (axe-core CDP), real depth-parallax effect confirmed via fresh-profile A/B headless on the live URLs. The recurring stale-HTML class for this user is structurally closed. The "3D wasn't implemented" gap is closed: the budgeted WebGL hero (skill §4b) is now actually shipped, not just codified.

Internal project — no `infrastructure.yaml` platform section, orchestrator n/a; no ops/comms staleness applicable.

---

## Next Steps
1. **Owner visual call** on the 3 live sites — does the 3D hero hit the BRIEF anchor parity / award-tier bar in the user's judgement? (Subjective gate the skill explicitly hands to the owner.) If yes → these are ready to pitch.
2. **QR leave-behind cards** — still need the owner's real name + contact line per prospect (carried; never fabricate).
3. **Per-business personalization pass** before walking in to pitch (carried).
4. **Decision still open** (carried from 2026-05-18): design-from-references vs. buy a premium theme base before scaling past ~3 sites.

---

## Context for Next Session

### Files to Read First
- `docs/2026-05-20 - Local-Web 3D Depth Hero and HTML Cache/Checkpoint.md` (this file)
- `.claude/skills/skil_web-build/SKILL.md` (§4b — now includes the implemented-stack note + verify tool pointer + readPixels lesson)
- `workspace/projects/local-web/app/src/components/DepthHero.astro` (the WebGL component — guardrails are non-negotiable)
- `tools/depth-live.cjs` (the live verifier; run before declaring a 4b deploy done)
- `workspace/projects/local-web/app/nginx.conf` (the no-cache + no-301 + relative-redirect block)

### Open Questions
- Does the live 3D hold the owner's award-tier bar visually (subjective parity gate)? Gated on the owner call.
- Is the `pronto-pronto` macro depth too subtle? Could re-shoot the hero with more depth separation if the answer is yes; current judgement is "subtle suits the calm art direction" but the owner's eye is the verdict.

### Working Notes
- **Reverter dormant this session.** Last session warned about the working-tree reverter; this session every edit committed cleanly (nginx.conf, infra.yaml, DepthHero.astro, 3 page swaps, skill, infra). The "apparent revert" of infra.yaml mid-session traced to my own `gh pr merge -q` (invalid flag, error masked by `2>&1 | tail -1`) — PR #39 stayed unmerged on its branch, main legitimately didn't have the change. Re-merged correctly. **B3 attribution worked**: my own command, not the env.
- **Verification-method discipline (Layer 2).** My first `depth-probe.cjs` used `readPixels` on a WebGL context created with `alpha:false` but no `preserveDrawingBuffer` → post-composite reads are undefined and produced false fails for coffee/pronto. Then I went to CDP-`clip` screenshots with viewport coordinates after `scrollIntoView` → blank captures because clip semantics relative to the page were wrong. Both were verification-tool bugs, not product bugs (pronto rendered the pizza correctly in the first full-viewport shot). The transferable principle (now in the skill): **for WebGL canvases, trust composited screenshots; never `readPixels` without `preserveDrawingBuffer`**. The full-page `captureBeyondViewport` pattern from `local-web-shot.cjs` works reliably here.
- **Depth pipeline is fast and reliable.** Depth-Anything-V2-Small ONNX via `uv` on Windows CPU: model download once (HF cache), inference ~few seconds for 3 images, model_quantized variants available if size becomes an issue. PNGs are 88–136KB at source res; Astro `getImage` → webp brings them to 6–11KB (grayscale compresses superbly).
- **Perf number deliberately not fabricated.** Skill says Lighthouse CLI is unreliable in this Windows env. The behavioral argument for unchanged Perf-100 is strong (poster `<Image>` is eager/priority and unchanged = LCP unchanged; WebGL fully deferred via idle+IO; depth 6–11KB lazy; photo webp ~48–113KB lazy post-LCP; ~3KB extra deferred JS; zero new deps; nothing render-blocking added). Honest B4: report "perf unaffected by construction; no numeric measurement (Lighthouse CLI unreliable here)" rather than a made-up score.

### Reference Materials
- Live: https://local-web-ka.fly.dev/{praxis-uslu,coffee-boxx,pronto-pronto}/
- PRs: #37 #39 #43 #44 (github.com/011matthias/agentic-ops1.01)
- Skill: `.claude/skills/skil_web-build/SKILL.md` §4b
- Deploy: `flyctl deploy <app-abs> --config <fly.toml> --remote-only --now` (fly account matneumann07@gmail.com)
- Depth model: `onnx-community/depth-anything-v2-small` on HuggingFace

---

## How to Continue
The 4b WebGL hero is shipped, live-verified, and structurally guarded. Owner-gated next steps are subjective (visual parity verdict) or human-data (QR card name/contact). For any future local-web source edit, the durable-commit pattern from the 2026-05-19 checkpoint is still the safe default *if* the reverter shows signs of being active again (this session it was dormant). For any future 4b WebGL deploy: run `node tools/depth-live.cjs <out> <url>...` for the A/B parallax visual after deploying.

---

## Strategic Feedback

### What Worked Well This Session
- The user's terse correction "the 3D designs were not implemented at all into the 3 websites" was exactly right and immediately actionable. It forced the gap-vs-codified distinction into focus and avoided me defending the prior session's narrower scope.
- B1/B3 application closed the prior-session "nothing changed" thread without asking the user to do an InPrivate check — headless probe instead.
- Atomic branch + commit + push + PR + merge + Fly-deploy chain held through 4 PRs in one session without ship-gate hesitation (except where the skill's WebGL gate legitimately mandated a pre-publish quality check).

### Suggestions
- **Wrap `gh pr merge` in a tool that re-checks state.** The `gh pr merge -q` foot-gun this session (invalid flag, masked by tail-pipe) cost a B3 catch. A `tools/gh-merge.sh <num>` that runs the merge, then `gh pr view <num> --json state` and asserts `MERGED`, would make the next failure self-evident without relying on me catching the masked error. Tool > vigilance.
- **For 4b WebGL builds, run `depth-live.cjs` *before* push, not just after.** I left the visual gate for live this session because my local probe was flaky. Now that `depth-live.cjs` is the codified working pattern, run it against `localhost:4321` BEFORE the merge → live-deploy → re-run. Stops a broken WebGL build from reaching production even momentarily.

### System Health
- Autonomy score: **3** human interventions this session (one direction-change from the user about the 3D gap; two of my own self-detected verification-theater/slow-path events). Not elevated, but borderline.
- `skil_web-build` 4b is now end-to-end concrete: depth-map pipeline + DepthHero component + verify tool + nginx hardening — the entire ladder is structural. The "implemented but undocumented" gap that produced this session's correction is now closed at the skill level.
- The `gh pr merge` masked-error class is recurring (saw it in the 2026-05-19 session as "verification-theater on merge state"). Operationalizing the wrapper tool above would close it for good.
