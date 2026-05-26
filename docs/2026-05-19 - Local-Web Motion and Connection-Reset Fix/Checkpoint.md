# Checkpoint: Local-Web Motion and Connection-Reset Fix

**Date:** 2026-05-19
**Status:** Shipped — all PRs merged to main, live on Fly, gates green. One open client-side verification (user cache / reduced-motion).

---

## Summary
Fixed the total `ERR_CONNECTION_RESET` outage on all three local-web demo sites (nginx absolute-redirect leak behind the Fly TLS edge, then the cached-301 poisoning follow-up), codified the 3D/motion imagery decision into `skil_web-build`, and implemented the 4b default motion tier (Ken Burns, scroll-reveal, card hover-lift) across all three sites — shipped despite an environment that was reverting agent file edits.

---

## What Was Done This Session

### 1. ERR_CONNECTION_RESET outage (sites down) — fixed
1. Root cause: `/<slug>` (no slash) → nginx canonical 301 built as **absolute** `http://local-web-ka.fly.dev:8080/...` because nginx behind Fly's TLS edge only sees `http` on `:8080`. Browser followed to a dead endpoint → reset. Server-side `curl` returned 200, hiding it.
2. Fix 1 (PR #24): `absolute_redirect off; port_in_redirect off; server_name_in_redirect off;` → relative redirects.
3. User reported still broken → diagnosed **cached-301 poisoning** (browsers cache `301 Moved Permanently` persistently; server fix can't evict a client cache).
4. Fix 2 (PR #26): `try_files $uri $uri/index.html $uri.html $uri/ =404;` → no-slash URL serves the index **directly, 200, no 301 ever**; homepage nav switched to trailing-slash form (different cache key) so already-poisoned browsers self-heal via the working homepage.
5. Skill hardened (PRs #25, #27): nginx relative-redirect + no-301 mandate + "a cached-redirect bug is invisible to curl — never declare fixed on a server-side 200."

### 2. 3D/motion capability decision — codified
- User asked "can websites be 3D" → clarified intent = animated/3D-feel **imagery**, not interactive Three.js scenes. Picked **Option 2: budgeted WebGL hero**.
- `skil_web-build` section **4b** added (PR #32): default CSS motion tier on every site + at-most-one budgeted WebGL hero with mandatory guardrails (lazy-init, poster fallback, `prefers-reduced-motion`, mobile-static, post-add gate re-run). Perf 100 / 0 WCAG2AA stays absolute. Full multi-element Three.js out of scope.

### 3. Motion 4b default tier — implemented on all 3 sites (PR #36)
- **Shared layer (DRY):** `global.css` motion block (Ken Burns `@keyframes kb-drift`, `.reveal-on [data-reveal]` reveal states, card hover-lift); `kenburns` prop on the `Figure` primitive; reduced-motion + no-JS-safe IntersectionObserver in `BaseLayout` with a 2.5s failsafe (content can never stay hidden).
- Applied `kenburns` + `data-reveal` across praxis-uslu, coffee-boxx, pronto-pronto.
- Captured the full change-set as idempotent `tools/apply-local-web-motion.py` (working tree was reverting agent edits — see Working Notes).
- Added reusable `tools/axe-check.cjs` (axe-core via CDP — the skill's infrastructure-deferred candidate).
- Gates: build + dist gate green; **axe-core CDP = 0 WCAG2 A/AA violations on all 3 live pages**; live HTML/CSS bundle verified to contain all motion rules.

---

## Key Decisions Made

### Eliminate the redirect entirely vs. just make it relative
- **Choice:** Serve the directory index directly at the no-slash URL (no 301 at all) + trailing-slash nav.
- **Rationale:** A relative 301 fixes new visitors but a persistently-cached bad 301 cannot be evicted server-side. Emitting no redirect removes the poisoning vector permanently; the slash-form nav is a fresh cache key that rescues already-poisoned browsers.

### Durable-commit workaround for the reverting working tree
- **Choice:** Stopped hand-editing after edits reverted twice (escalation gate); wrote the entire change-set as one idempotent script, applied + `git commit` atomically in a single shell call, and `git restore --source=HEAD` before every build/deploy.
- **Rationale:** An external editor/harness file-sync was rolling the working tree back to HEAD between tool calls. The git object store is the only durable surface; re-applying by hand into a reverting tree is an iteration loop.

### Respect the 3D-scope clarification over the literal multiple-choice answer
- **Choice:** User selected "Full Three.js" then said "like the pictures or animations" — treated the clarification as the real intent (animated imagery), flagged the mismatch, and codified the budgeted tier the user re-confirmed.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/projects/local-web/app/nginx.conf` | Modified | Relative redirects + serve no-slash index directly (no 301) |
| `workspace/projects/local-web/app/src/styles/global.css` | Modified | Motion layer: Ken Burns, reveal states, card hover-lift |
| `workspace/projects/local-web/app/src/components/Figure.astro` | Modified | `kenburns` prop on the shared image primitive |
| `workspace/projects/local-web/app/src/layouts/BaseLayout.astro` | Modified | Reduced-motion/no-JS-safe reveal observer + 2.5s failsafe |
| `workspace/projects/local-web/app/src/pages/{praxis-uslu,coffee-boxx,pronto-pronto}.astro` | Modified | `kenburns` + `data-reveal` applied |
| `workspace/projects/local-web/app/src/pages/index.astro` | Modified | Trailing-slash nav (cache-key rescue) |
| `.claude/skills/skil_web-build/SKILL.md` | Modified | nginx no-301 gate + cached-redirect verification note + 4b motion standard |
| `tools/apply-local-web-motion.py` | Created | Idempotent re-applicable motion change-set (revert workaround) |
| `tools/axe-check.cjs` | Created | Reusable axe-core CDP WCAG2 A/AA checker |

PRs merged to main: **#24, #25, #26, #27, #32, #36**.

---

## Current Status
All three sites live at https://local-web-ka.fly.dev/{praxis-uslu,coffee-boxx,pronto-pronto}/ — HTTP 200, motion deployed (verified in live CSS bundle + HTML via cache-less curl), 0 WCAG2 A/AA violations (axe-core CDP). The connection-reset outage is resolved server-side. User reports "nothing changed" — verification proves it IS deployed, so the cause is client-side: stale browser HTML cache (most likely, given this user's repeated cache issues this session — HTML has no `Cache-Control`) or Windows `prefers-reduced-motion` (motion intentionally disabled, by design). Awaiting the user's InPrivate-window check to confirm.

Internal project — no `infrastructure.yaml` platform section, orchestrator n/a; no ops/comms staleness applicable.

---

## Next Steps
1. **User runs the InPrivate-window check** on https://local-web-ka.fly.dev/praxis-uslu/ — confirms whether "nothing changed" is stale cache (expected) vs. reduced-motion vs. a real defect.
2. If still flat in InPrivate: capture screenshots from headless Chrome (tools/axe-check.cjs has the CRI+Chrome plumbing) to prove rendered state and isolate definitively.
3. Consider adding a short `Cache-Control` (e.g. `max-age=60, must-revalidate`) for `text/html` in `nginx.conf` so HTML cache staleness stops recurring for this user (recurring friction — fingerprinted assets are fine, the HTML doc is the problem).
4. Owner-gated (carried from prior local-web checkpoint, unchanged): visual reference-parity verdict; QR-card real name+contact; per-business personalization pass.

---

## Context for Next Session

### Files to Read First
- `docs/2026-05-19 - Local-Web Motion and Connection-Reset Fix/Checkpoint.md` (this file)
- `.claude/skills/skil_web-build/SKILL.md` (sections 4b + 6 — the new standards)
- `tools/apply-local-web-motion.py` (the durable change-set if a re-apply is ever needed)
- `workspace/projects/local-web/app/nginx.conf` (the redirect fix)

### Open Questions
- Is "nothing changed" stale cache, OS reduced-motion, or something else? (gated on user InPrivate check)
- Should `text/html` get an explicit short `Cache-Control` to stop the recurring browser-cache class for this user?

### Working Notes
- **Working-tree revert (unresolved environment issue):** Every Edit/Write to local-web source reverted to HEAD between tool calls. Confirmed it is NOT a project hook — all PostToolUse hooks (`em-dash-strip-gate`, `post-write-gate`) are non-mutating and out-of-scope for `.astro/.css`; no git hooks; reflog showed no HEAD reset during editing; `git status` kept going clean to HEAD. Harness emitted "modified, either by the user or by a linter" showing original content → external editor/harness file-sync writing a stale buffer back. **Workaround that works:** edit via `tools/apply-local-web-motion.py`, `git add && git commit` in one shell call, `git restore --source=HEAD --worktree` immediately before each build/deploy. The git commit is the durable source of truth; the working tree is not trustworthy in this environment.
- **Shell `cd` breaks hooks:** `cd` into `app/src` made relative hook paths (`.claude/hooks/...`) resolve against the subdir → PreToolUse hooks errored and blocked an Edit. Recovery: `Set-Location` repo root via PowerShell. Rule going forward: never `cd` into subdirs; use `npm --prefix`, absolute paths, `git -C`.
- Lighthouse CLI deliberately not run (unreliable in this Windows env per skill); a11y proven authoritatively via axe-core CDP instead. Perf not numerically re-measured — change is CSS + ~1KB bundled JS with no render-blocking additions; not fabricating a number.
- Motion is calm-by-design (26s Ken Burns drift, 0.7s reveals) per the skill's award-tier anti-flashy art direction — sets user expectation.

### Reference Materials
- Live: https://local-web-ka.fly.dev/{praxis-uslu,coffee-boxx,pronto-pronto}/
- PRs: #24 #25 #26 #27 #32 #36 (github.com/011matthias/agentic-ops1.01)
- Deploy: `flyctl deploy <app-abs> --config <fly.toml> --remote-only --now` (fly account matneumann07@gmail.com)

---

## How to Continue
The build is done and verified server-side. Pick up at the user's InPrivate-check result. If it renders there, the issue was cache — recommend the `Cache-Control` hardening (Next Step 3) to end the recurring class. If a real defect, use `tools/axe-check.cjs`'s headless-Chrome plumbing to screenshot the actual rendered state. Any further local-web source edit MUST use the durable-commit pattern (apply-script → atomic commit → restore-before-build) until the working-tree reverter is identified.

---

## Strategic Feedback

### What Worked Well This Session
- The user's terse "it still wont work" / "nothing changed" forced real behavioral verification (cache-less curl + axe-CDP) instead of trusting a server 200 — directly exposed the verification-theater pattern and the cached-redirect class.
- Escalating to a durable-commit workaround after two reverts (instead of a third hand re-apply) is exactly the iteration-limit gate working.

### Suggestions
- When an environment reverts agent writes, default immediately to the apply-script + atomic-commit pattern rather than diagnosing first — the diagnosis cost ~15 tool calls and critical context pressure. A short checklist entry "if files revert: script+commit+restore, don't re-edit" would save the spiral.

### System Health
- `skil_web-build` is now well-hardened (nginx, cached-redirect, 4b motion) and gained a real reusable a11y tool (`tools/axe-check.cjs`) — the infrastructure-deferred candidate is closed.
- Recurring HTML browser-cache pain for this user on local-web is a structural gap: the stack ships no `Cache-Control` for the HTML doc. Worth a one-line nginx fix to stop it returning every session.
- Autonomy score: 3 human interventions this session (1 genuine agent friction — verification-theater on the first reset fix; 2 client-environment perceptions requiring explanation, not agent defects). Not elevated past threshold.
