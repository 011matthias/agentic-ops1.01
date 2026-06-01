# Tools Manifest

One-line index of `tools/` scripts. Auto-loaded at session start to reduce `missed-tool` friction (5+ register entries where a tool existed but wasn't found).

| Tool | When to use |
|------|-------------|
| `validate-output.py FILE` | Universal text validator (em-dashes, brand misspellings, AI-tells, fabrication risk, `unsourced-claim`: client-facing problem-claims with no source attribution within ±2 lines — B4/register #7). Auto-fires via post-write-gate hook on any file in deliverable or comms scope. |
| `validate-deliverable.py FILE.html` | HTML deliverable QoL features check (dark mode, copy-clipboard, Ctrl/Cmd+K, state persistence) per rule_deliverables.md. Auto-fires on HTML writes. |
| `validate-html.py FILE.html` | HTML structural validation (unclosed tags, duplicate IDs, missing head, relative paths). B2 gate extension before deploy. Use `--dir` for cross-page consistency. |
| `lint-comms-draft.py FILE.md` | Anti-AI lint for comms drafts and comms-log entries. Auto-fires on writes to `/context/drafts/`, `/proposals/`, or `comms-log.md`. |
| `voice-check.py FILE.md` | Bilingual (DE/EN) anti-slop checker for client deliverables. Run before publishing markdown. |
| `friction-watch.py` | Push-based `/comd_system-dev` trigger. Surfaces concentration, memory-sprawl, staleness, recurrence patterns from friction register. Hook-friendly with `--quiet --format json`. |
| `validate-proposal.py` | Proposal frontmatter/structure validation. Use before `/comd_publish-proposal`. |
| `strip-em-dash.py FILE [...]` | Mechanical em-dash → semicolon replacement in prose (skips fenced code). Use after voice-check flags em-dashes. |
| `make-api.py` | Make.com API helper — list/get/update scenarios, blueprints. Use for autonomous Make diagnostics. |
| `notion-restructure-v18.py` | Notion page restructuring helper (Wärme Wimmer doc site). Client-specific. |
| `build-warme-wimmer-doc-site.py` | Wärme Wimmer doc site generator. Client-specific. |
| `rename-chat.py "{scope}--{task}"` | Auto-rename current chat per rule_session-start.md. Called by `/comd_resume` and other session-start commands. |
| `vercel-force-deploy.sh [--domain X]` | Force a production Vercel deploy and guard against concurrent git-integration rebuilds superseding it. Run after a platform merge per the Deploy verification gate (rule_behaviors.md step 6). Parses the deploy URL from CLI output, settles, confirms the intended deployment is live via `vercel ls --prod`, and `vercel promote`s it back if a concurrent rebuild won the race. |
| `wire-hooks.py [--check\|--ensure\|--write]` | Cross-device enforcement-layer recurrence kill. Tracked carrier of the canonical 9-hook block; writes it into gitignored `.claude/settings.local.json`. `--ensure` runs at SessionStart (auto-heals any device every session); `--check` warns loud + exits 1 if the block is down; `--write` repairs on demand. Preserves all other settings keys (permissions, enabledPlugins). |
| `validate-dist.py DIR [...]` | Em-dash + `--` typographic-substitute scan for framework-built sites (Astro `dist/`). Closes the 2026-05-08 regression where built deliverables escaped the validate-html.py path. Wire as npm postbuild for any framework build. |
| `apply-local-web-motion.py` | Apply motion-config patches idempotently to local-web Astro sites (skil_web-build §4b). Edit→commit→restore pattern dodges the working-tree-revert issue. |
| `morning_briefing.py` | Daily morning todo briefing across active clients + projects, delivered by email via Resend (set User-Agent — see project_morning_briefing memory). Driver for the scheduled trig_015ZoMm18Evyj3PGfUPe7tC3 routine. |
| `heic-to-png.py FILE [...]` | Convert HEIC photos (iPhone screenshots) to PNG for use in client deliverables/proposals. Handles batch convert. |
| `svg-to-png.py FILE [...]` | Rasterize SVG to PNG (for PDF embeds, screenshots). |
| `md-to-pdf.py FILE.md [--out X.pdf]` | Markdown → PDF for client deliverables. Use after the PDF protocol's markdown-draft review gate (rule_deliverables.md). |
| `gh-merge.sh PR_NUM` | Wraps `gh pr merge --squash --delete-branch` with a `state == MERGED` assertion via `gh pr view`. Closes the 2026-05-20 #107 silent-merge-failure class (invalid `-q` flag swallowed by `2>&1 \| tail -1`). Use for any PR merge from an agent. |
| `safe-edit.py FILE old_string new_string` | Edit wrapper with EBUSY retry-with-backoff for the Windows+IDE-open file-lock class (register #81). Falls back to a clear `LIMITATION: file locked` message after 5 retries (500ms apart). |
| `spec-staleness.py [--days N]` | Surface in-flight specs (stage 2-build / 3-test) with `updated:` older than N days. Default 30. Use to identify dormant client work without mutating spec data. Run periodically or from `/comd_system-dev`. |
| `validate-spec.py FILE.md` | Spec frontmatter + stage/folder validator. Auto-fires via post-write-gate on any write under `workspace/clients/*/specs/`. Catches missing required keys, stage/folder mismatches, and surfaces `needs_fixes: true`. Per-file companion to the on-demand skil_spec-cleanup audit. |
| `handoff-readiness.py {client}` | Score a client's handoff readiness: specs in 4-live, infrastructure.yaml status, comms-log currency, automations present. Use before proposing a client handoff or marking dormant. |
| `openclaw-sandbox-init.py {slug}` | Scaffold an isolated prototype sandbox for an openclaw idea OUTSIDE this repo (default `~/Repo/openclaw-sandbox/{slug}/`). Refuses if target is inside `agentic-ops1` to prevent capture by a client `git subtree push`. Writes Dockerfile (non-root, read-only fs, cap_drop:ALL, no host mounts beyond `./scratch`), docker-compose with narrow defaults, `.env.example` (scoped-keys-only guidance), `.gitignore`, and a README pre-flight checklist (no-training tier confirmation, no client-data copy, TOS/GDPR/TCPA stance per idea). |

## Output validators — JSON contract

`validate-output.py`, `validate-deliverable.py`, `validate-html.py`, `lint-comms-draft.py` all support `--format json` and emit:

```json
{
  "total": N,
  "hits": [{"line": N, "category": "...", "severity": "HIGH|MEDIUM|LOW", "message": "...", "snippet": "..."}],
  "by_category": {"category": N, ...},
  "by_severity": {"HIGH": N, ...}
}
```

Severity HIGH = ship-blocker, MEDIUM = strong warning, LOW = nudge. The post-write-gate hook surfaces HIGH first.

## Suppression markers

- **validate-output.py**: `<!-- output-allow:CATEGORY[,CAT2][:N_LINES] reason text -->` on the line before a hit (or `:N` to suppress next N lines).
- **validate-deliverable.py**: `<!-- deliverable-allow: CATEGORY[, CAT2] | reason: ... -->` anywhere in the file (suppresses globally for that category).
- **validate-html.py**: no suppression — structural failures should be fixed, not muted.

## Adding a new tool

1. Use `# /// script\n# requires-python = ">=3.11"\n# ///` PEP 723 header for inline deps.
2. Run via `uv run tools/{name}.py`.
3. If callable from a hook, support `--format json` and exit 0 even on hits (the hook reads JSON, not exit code).
4. Add a one-liner to this INDEX.

## External tools (installed via package manager, not vendored)

Tools that live on the system PATH rather than in this repo. Install once per machine.

| Tool | Install | When to use |
|------|---------|-------------|
| `skill-seekers` | `pip install skill-seekers` (or `pipx install skill-seekers`) | Turn a docs site / GitHub repo / PDF into a structured SKILL.md. Use when converting external documentation into a vendored skill in `.claude/skills/`. Source: [yusufkaraaslan/Skill_Seekers](https://github.com/yusufkaraaslan/Skill_Seekers). |
| `agnix` | `npm install -g agnix` (or `cargo install agnix-cli`) | Lint SKILL.md / CLAUDE.md / hook configs for syntax and trigger issues across Claude Code, Codex, Cursor, etc. 420 rules. Run as a pre-commit gate after editing skills or rules to catch silent-ignore patterns. Source: [agent-sh/agnix](https://github.com/agent-sh/agnix). |
