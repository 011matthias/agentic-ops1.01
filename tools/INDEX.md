# Tools Manifest

One-line index of `tools/` scripts. Auto-loaded at session start to reduce `missed-tool` friction (5+ register entries where a tool existed but wasn't found).

| Tool | When to use |
|------|-------------|
| `validate-output.py FILE` | Universal text validator (em-dashes, brand misspellings, AI-tells, fabrication risk, `unsourced-claim`: client-facing problem-claims with no source attribution within ±2 lines — B4/register #7). Auto-fires via post-write-gate hook on any file in deliverable or comms scope. |
| `validate-deliverable.py FILE.html` | HTML deliverable QoL features check (dark mode, copy-clipboard, Ctrl/Cmd+K, state persistence) per rule_deliverables.md. Auto-fires on HTML writes. |
| `validate-html.py FILE.html` | HTML structural validation (unclosed tags, duplicate IDs, missing head, relative paths). B2 gate extension before deploy. Use `--dir` for cross-page consistency. |
| `lint-comms-draft.py FILE.md` | Anti-AI lint for comms drafts and comms-log entries. Auto-fires on writes to `/context/drafts/`, `/proposals/`, or `comms-log.md`. |
| `voice-check.py FILE.md` | Bilingual (DE/EN) anti-slop checker for client deliverables. Run before publishing markdown. |
| `friction-watch.py` | Push-based `/comd_system-dev` trigger. Surfaces concentration, memory-sprawl, staleness, recurrence, and synthesis-cadence (ledger >21d stale / reviews never written) patterns from the friction register. Unresolved counting is prefix-match (`No (caught by hook)` counts as unresolved, reported in a separate hook-contained sub-bucket that stale excludes and concentration keeps). Hook-friendly with `--quiet --format json`. |
| `weekly_synthesis.py [--scheduled\|--local] [--preflight\|--print-registration]` | Deterministic no-LLM weekly sensor (the paused weekly-review's signal half): friction-watch signals + corrected backlog + cadence staleness + sensor-lag census, emailed via `send_email.py`. `--scheduled` reads register/ledger/reviews from origin/main BLOBS (never the working tree) and exits 1 on send failure; writes NO file (W1). `--print-registration` emits the version-controlled Register-ScheduledTask command targeting the pinned `agentic-ops1-cadence` worktree. |
| `eval-agents.py {run\|grade\|compare\|list}` | Behavioral eval harness for the fixture-backed agents (intent-reviewer, comms-critic, proposal-research BLOCKED). `run` = paid generation via headless `claude -p` from a neutral cwd (repo context NOT auto-loaded; answer keys stripped from fixtures); transcripts in gitignored `.scratch/evals/{run-id}/`. `grade` = free deterministic regex graders; `compare A B` = before/after regression diff for rule/prompt PRs (base rev via `--repo` + a second worktree). LOCAL-ONLY by design: the agents read machine-local memory files CI lacks. Sonnet default; `--n 3` for suspected flakes. |
| `anneal-metrics.py [--format json\|--append\|--date D]` | Convergence + toolkit-drift metrics for the `/comd_system-dev` anneal cycle (Phase 1.5 / 6.5). Reuses `friction-watch.py`'s parser; computes asset counts, recurrence/memory-fix %, documented-vs-actual drift (CLAUDE.md advertised counts vs reality), and git change-set size since the prior cycle. `--append` writes a row to `docs/anneal-ledger.md`. Advisory (exit 0). |
| `session_state.py [--status\|--list-candidates\|--clear-candidates\|--reset]` | Session-scoped instrumentation store (tempdir JSON). Shared by `session-pressure-meter.py` + the gate hooks: holds pressure counters (tool calls, distinct files) and auto-captured friction CANDIDATES. `/comd_checkpoint` drains candidates via `--list-candidates` → classify (promote/discard) → `--clear-candidates`. Detection is automated; promotion to the register is a judgment call. Self-manages session boundary via payload `session_id`. |
| `validate-proposal.py` | Proposal frontmatter/structure validation. Use before `/comd_publish-proposal`. |
| `strip-em-dash.py FILE [...]` | Mechanical em-dash → semicolon replacement in prose (skips fenced code). Use after voice-check flags em-dashes. |
| `make-api.py` | Make.com API helper — list/get/update scenarios, blueprints. Use for autonomous Make diagnostics. |
| `notion-restructure-v18.py` | Notion page restructuring helper (Wärme Wimmer doc site). Client-specific. |
| `build-warme-wimmer-doc-site.py` | Wärme Wimmer doc site generator. Client-specific. |
| `rename-chat.py "{scope}--{task}"` | Auto-rename current chat per rule_session-start.md. Called by `/comd_resume` and other session-start commands. |
| `vercel-force-deploy.sh [--domain X]` | Force a production Vercel deploy and guard against concurrent git-integration rebuilds superseding it. Run after a platform merge per the Deploy verification gate (rule_behaviors.md step 6). Parses the deploy URL from CLI output, settles, confirms the intended deployment is live via `vercel ls --prod`, and `vercel promote`s it back if a concurrent rebuild won the race. |
| `wire-hooks.py [--check\|--ensure\|--write]` | Cross-device enforcement-layer recurrence kill. Tracked carrier of the canonical enforcement-hook block; writes it into gitignored `.claude/settings.local.json`. `--ensure` runs at SessionStart (auto-heals any device every session); `--check` warns loud + exits 1 if the block is down; `--write` repairs on demand. Preserves all other settings keys (permissions, enabledPlugins). |
| `validate-dist.py DIR [...]` | Em-dash + `--` typographic-substitute scan for framework-built sites (Astro `dist/`). Closes the 2026-05-08 regression where built deliverables escaped the validate-html.py path. Wire as npm postbuild for any framework build. |
| `apply-local-web-motion.py` | Apply motion-config patches idempotently to local-web Astro sites (skil_web-build §4b). Edit→commit→restore pattern dodges the working-tree-revert issue. |
| `local-web-deploy.py [--no-deploy\|--skip-build\|--only SLUG]` | Canonical "ship local-web" path, full gauntlet: build → aesthetics audit `--strict` → `flyctl deploy` → live-origin parity (content-hash match on `/_astro/` refs) → `axe-check.cjs` → `verify-rendered.cjs` → advisory `npx impeccable detect`. Cannot pass without the production URL serving AND correctly rendering the bytes you built. A missing dependency is a failed gate (exit 1 + fix), never a skip. |
| `assert-live-origin.py URL [--expect STR\|--expect-absent STR\|--match-assets FILE\|--status N]` | Stack-agnostic deploy-origin parity check (the generalization of `local-web-deploy.py`'s `/_astro/` gate to any Fly/Vercel/Railway origin). Cache-busted fetch asserts the production URL serves the expected build: `--expect` substrings present, `--expect-absent` (old build) gone, `--match-assets` hashed refs all live. The structural kill for the "verified on localhost while the origin served the old build" class (2026-06-17 brisken-expense-recon). Exit 0 verified, 1 mismatch. |
| `axe-check.cjs URL [...]` | Authoritative WCAG 2 A/AA gate (axe-core via headless-Chrome CDP; the Lighthouse CLI a11y output is NOT trusted in this env). Runs inside `local-web-deploy.py`; run standalone for any deployed page. Exit 0 = zero violations. |
| `verify-rendered.cjs [--toggle [SEL]] URL [...]` | Rendered-BEHAVIOR probes: hero paint variance (catches unpainted canvas / blank reveal-gated sections), brand-font-loaded check, optional theme-toggle brightness-delta probe (the 0/31-dead-toggles class only a behavior probe catches). Runs inside `local-web-deploy.py`; use `--toggle` on gated client pages. |
| `local-web-shot.cjs URL OUT-PREFIX` | Fresh-client rendered-state proof: zero-cache screenshots (top + post-scroll) + motion-marker assertions (Ken Burns live, scroll reveals fired). Settles "nothing changed" reports. |
| `depth-live.cjs URL` | Depth-hero live verify: headless-Chrome probe that the WebGL hero initialises (`.depthhero.is-on`, canvas painted) + A/B pointer screenshots for the parallax eyeball check. |
| `morning_briefing.py` | Daily morning todo briefing across active clients + projects, delivered by email via Resend (set User-Agent — see project_morning_briefing memory). Driver for the scheduled trig_015ZoMm18Evyj3PGfUPe7tC3 routine. |
| `heic-to-png.py FILE [...]` | Convert HEIC photos (iPhone screenshots) to PNG for use in client deliverables/proposals. Handles batch convert. |
| `svg-to-png.py FILE [...]` | Rasterize SVG to PNG (for PDF embeds, screenshots). |
| `md-to-pdf.py FILE.md [--out X.pdf]` | Markdown → PDF for client deliverables. Use after the PDF protocol's markdown-draft review gate (rule_deliverables.md). |
| `gh-merge.sh PR_NUM` | Wraps `gh pr merge --squash --delete-branch` with a `state == MERGED` assertion via `gh pr view`. Closes the 2026-05-20 #107 silent-merge-failure class (invalid `-q` flag swallowed by `2>&1 \| tail -1`). Use for any PR merge from an agent. |
| `safe-edit.py FILE old_string new_string` | Edit wrapper with EBUSY retry-with-backoff for the Windows+IDE-open file-lock class (register #81). Falls back to a clear `LIMITATION: file locked` message after 5 retries (500ms apart). |
| `spec-staleness.py [--days N]` | Surface in-flight specs (stage 2-build / 3-test) with `updated:` older than N days. Default 30. Use to identify dormant client work without mutating spec data. Run periodically or from `/comd_system-dev`. |
| `validate-spec.py FILE.md` | Spec frontmatter + stage/folder validator. Auto-fires via post-write-gate on any write under `workspace/clients/*/specs/`. Catches missing required keys, stage/folder mismatches, and surfaces `needs_fixes: true`. Per-file companion to the on-demand skil_spec-cleanup audit. |
| `handoff-readiness.py {client}` | Score a client's handoff readiness: specs in 4-live, infrastructure.yaml status, comms-log currency, automations present. Use before proposing a client handoff or marking dormant. |
| `project_status.py --client X [--check\|--scaffold SLUG]` | Per-project status-of-elements files under `workspace/clients/{X}/status/`. `--check` lists each workstream's status file with state + staleness (active/blocked/live not touched within `--days`, default 21) and flags malformed frontmatter (exit 1 stale/bad, 3 no folder). `--scaffold SLUG [--group G --spec ID --general-ref P]` writes a template file (refuses overwrite). `--sweep-stale [--once-per-day]` scans ALL clients and advises on stale/malformed files, exit 0 always (fail-open) — wired into SessionStart (`wire-hooks.py`) so rot surfaces without anyone running `--check`. Backs `rule_project_status.md` / `skil_project-status`; loaded by `/comd_resume`, updated at `/comd_checkpoint`. |
| `openclaw-sandbox-init.py {slug}` | Scaffold an isolated prototype sandbox for an openclaw idea OUTSIDE this repo (default `~/Repo/openclaw-sandbox/{slug}/`). Refuses if target is inside `agentic-ops1` to prevent capture by a client `git subtree push`. Writes Dockerfile (non-root, read-only fs, cap_drop:ALL, no host mounts beyond `./scratch`), docker-compose with narrow defaults, `.env.example` (scoped-keys-only guidance), `.gitignore`, and a README pre-flight checklist (no-training tier confirmation, no client-data copy, TOS/GDPR/TCPA stance per idea). |
| `check-index.py` | Assert every `tools/*.py`, `*.sh`, `*.cjs`, `*.mjs` has a row in this manifest. CI gate + pre-commit hook; closes the recurring missing-tool friction (register #74, #133). |
| `audit-client-pages.py` | Client-page structure auditor; enforces rule_client_page_structure.md §2-§6. Run before any client-page deploy. |
| `normalize-client-pages.py` | Client-page structure corrector; injects the theme toggle, print stylesheet, and last-updated footer per rule_client_page_structure.md. Idempotent. |
| `validate-platform-content.py` | Platform (unpauseai.com) content standards validator: em-dashes, brand typos, banned words, dead `/paths`, proposal heading drift. Run before a platform deploy. |
| `validate-pilot-routing.py` | Validate client-facing drafts against a client's pilot-routing.md table (piece cross-wire check). Auto-fires via post-write-gate. |
| `audit-local-web-aesthetics.py [--only SLUG\|--strict\|--persist\|--trend]` | Advisory visual-craft pre-ship pass for local-web sites: List-B tells, design-thresholds floors/ceilings, motion-envelope scan, saturation bands (OKLCH cream band, saturated font tier), reveal-safety, JSON-LD presence. Findings cite `rule:web-*` IDs. `--strict` (used by `local-web-deploy.py`) exits 1 on hard fails; `--persist` snapshots per-site scores to `.critique/`; `--trend` prints the score history. |
| `check-skill-map.py [PATH ...]` | Skill routing-table validator: dead backtick pointers in any `.claude/skills/*/` markdown, modules/references/components unreachable from SKILL.md, duplicated `rule:` ID anchors (one home per rule). Auto-fires via post-write-gate on skill writes; run bare for the full tree. |
| `web-build-signals.py` | Deterministic session-entry state probe for local-web: git-dirty site dirs, dev-server port, per-site BRIEF/TEST/dist presence, latest critique scores. Run at web-build session start; lead with pointed next steps instead of scope questions. |
| `build-hours-tracker.py` | Build a blank hours tracker at `workspace/hours-tracker.xlsx`. |
| `sync-hours.py` | Sync `workspace/hours-tracker.xlsx` with git commit activity. |
| `send_email.py` | Reusable plain-text email sender (Resend HTTP API, stdlib only). Shared by `morning_briefing.py` and the scheduled agents. |
| `prompt-queue-ui.py [--port N\|--no-open]` | Serve the miniature prompt-queue UI (default `http://127.0.0.1:7077`) over `.claude/queue/pending.md`: add/edit/reorder/delete/clear pending prompts + read-only `done.md` tail. File stays source of truth (hash-guarded writes). Companion to the skil_prompt-queue drain skill. |

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
