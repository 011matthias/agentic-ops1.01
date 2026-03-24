# Deliverable Standards

**HTML deliverables.** Self-contained HTML files (infographic, dashboard, doc site, tool) MUST include:
1. Dark/light mode toggle (pill button, `[data-theme]` CSS, localStorage persistence)
2. Copy-to-clipboard on code/command blocks (hover-reveal, brief feedback)
3. Keyboard search (Ctrl/Cmd+K, visible hint)
4. Filter/search state persistence (localStorage)

**HTML structural validation.** Before deploying any self-contained HTML, run `uv run tools/validate-html.py {files}`. Fix all failures before deploy. For multi-page sets, run in directory mode to check cross-page consistency. This is a B2 gate extension — failing validation = do not deploy.

**Static HTML paths (Vercel).** Always use absolute paths between static HTML files. Vercel cleanUrls + trailingSlash:false breaks relative paths on nested routes.

**Client-facing content accuracy.** Every number, field name, and config value must trace to a queried source. Unverified = "TBD". See B4 gate in rule_behaviors.md.

**Brand accuracy.** For platform work, read `workspace/projects/platform/context/brand.md` at session start. Never assume brand name spelling or contact info.
