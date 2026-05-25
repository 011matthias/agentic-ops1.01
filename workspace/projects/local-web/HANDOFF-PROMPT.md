# local-web — handoff prompt

Paste this into a fresh chat (claude.ai web, a different Claude Code workspace,
or any LLM with file access to this repo) to continue local-web work without
re-explaining state. Self-contained: works whether or not the target env has
this project's `/resume` slash command loaded.

Update the "Latest state" block whenever a new PR ships so this stays current —
or regenerate from the most recent `docs/{YYYY-MM-DD} - Local-Web …/Checkpoint.md`.

---

```
I'm continuing work on the "local-web" internal project of my agentic-ops repo
(C:\Users\neuma_p1qrsic\Repo\agentic-ops1).

Latest state — shipped + verified live 2026-05-20:
- 3 demo sites live on Fly: https://local-web-ka.fly.dev/{praxis-uslu,coffee-boxx,pronto-pronto}/
- PR #37: nginx HTML Cache-Control: no-cache (ends recurring stale-demo class)
- PR #43: budgeted WebGL depth-parallax hero on all 3 sites (skil_web-build §4b)
  - app/scripts/depth-map.py (Depth-Anything-V2-Small ONNX via uv) generates depth maps
  - DepthHero.astro: zero-dep WebGL1 shader; poster <Image> stays LCP + the entire
    no-JS / pre-init / reduced-motion / <=768px / no-WebGL / Save-Data fallback tree
  - canvas aria-hidden -> a11y tree unchanged; axe-core CDP 0 WCAG2AA on all 3
- PR #44: tools/depth-live.cjs (fresh-profile A/B parallax verifier) + skill §4b note

Read these to load full context:
1. docs/2026-05-20 - Local-Web 3D Depth Hero and HTML Cache/Checkpoint.md   (canonical)
2. docs/sessions/2026-05-20-context.yaml  (local-web: block)
3. workspace/projects/local-web/infrastructure.yaml
4. .claude/skills/skil_web-build/SKILL.md  (§4b is the WebGL hero standard)
5. workspace/projects/local-web/app/src/components/DepthHero.astro
6. tools/depth-live.cjs

Open next steps (owner-gated, not autonomous):
- Visual reference-parity verdict on the 3 live sites against the BRIEF anchors
- QR leave-behind cards need real name + contact per prospect (never fabricate)
- Per-business personalization pass before walking in to pitch
- Carried: design-from-references vs premium-theme-base before scaling past ~3 sites

After loading, post a short session header showing what you picked up (last shipped
state, next steps, open questions) and then wait for my task.
```

---

## If the target env IS this Claude Code workspace

Use the shorter form instead — the system has a purpose-built resume command:

```
/resume local-web

After loading, post a short session header showing what you picked up (last shipped
state, next steps, open questions) and then wait for my task.
```
