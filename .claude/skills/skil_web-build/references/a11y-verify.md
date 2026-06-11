# Reference: a11y verification (axe-core via CDP)

The authoritative accessibility-gate method. `modules/SHIP.md` §3 links here. This is
the home for the method; do not restate it elsewhere.

**Use axe-core via CDP, not the Lighthouse CLI.** The Lighthouse CLI is unreliable in
the Windows dev env (silently re-parses stale JSON across deploys; disagrees with
`curl`/CDP — see incidents.md → 2026-05-18). The authoritative check is axe-core (the
same engine Lighthouse uses) run directly:

1. Launch headless Chrome with a **forward-slash** binary path (`C:/Program
   Files/...`) — backslashes get mangled through bash heredocs.
2. Connect via `chrome-remote-interface`.
3. Inject `axe-core/axe.min.js`.
4. Run `axe.run` with `wcag2a / 2aa / 21a / 21aa`.

For a contrast root-cause, `CSS.getMatchedStylesForNode` + `getComputedStyleForNode`
give ground truth in one shot. **Read the computed style; never theorize a fix from
axe's HTML snippet** — that is verification theater (it cost a 3-iteration breach on
2026-05-18; see incidents.md).

SEO `is-crawlable` failing is expected if a page is intentionally `noindex`; gate it
as "all non-noindex SEO audits pass", do not strip `noindex` to chase the number
unless the owner directs it.

Promoted (2026-06-11): the method is committed as `tools/axe-check.cjs`
(`node tools/axe-check.cjs <url> [...]`, exit 0 = zero violations) and runs
automatically inside `tools/local-web-deploy.py` after the live-origin check.
Re-authoring it per session, or skipping it because Chrome/node_modules are
missing, is a failed gate — the deploy tool exits 1 with the fix instruction.
