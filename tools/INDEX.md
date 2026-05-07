# Tools Manifest

One-line index of `tools/` scripts. Auto-loaded at session start to reduce `missed-tool` friction (5+ register entries where a tool existed but wasn't found).

| Tool | When to use |
|------|-------------|
| `validate-output.py FILE` | Universal text validator (em-dashes, brand misspellings, AI-tells, fabrication risk). Auto-fires via post-write-gate hook on any file in deliverable or comms scope. |
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
