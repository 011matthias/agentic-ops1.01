# Checkpoint: Anthropic Skills Repo Integration

**Date:** 2026-05-19
**Status:** Complete — shipped to main (PRs #40, #41, #42)

---

## Summary
Plugged the `anthropics/skills` GitHub repo into Claude Code as a plugin marketplace, enabled the `document-skills` plugin (pdf/docx/pptx/xlsx) at project scope, repointed the PDF protocol rule at the now-real `pdf` skill, and vendored the `mcp-builder` skill as a single project skill.

---

## What Was Done This Session
### Marketplace + document-skills (PR #40)
1. Confirmed `anthropics/skills` is a real Claude Code plugin marketplace (`anthropic-agent-skills`, marketplace.json with 3 plugins: document-skills, example-skills, claude-api).
2. `claude` CLI is not exposed inside the VSCode extension env — replicated `claude plugin marketplace add` by hand: cloned repo to `~/.claude/plugins/marketplaces/anthropic-agent-skills`, registered in `known_marketplaces.json`, populated plugin cache, recorded in `installed_plugins.json`.
3. Enabled `document-skills@anthropic-agent-skills: true` in project `.claude/settings.json` (the only git-tracked change in #40).
4. Verified: all 3 plugin registry JSONs parse; 4 SKILL.md present (pdf/docx/pptx/xlsx). Claude Code later re-cached document-skills with a real version hash (`690f15cac7f7`) — confirms the standard mechanism took over.

### PDF protocol rule fix (PR #41)
5. `rule_deliverables.md` PDF protocol step 2 hardcoded `/mnt/skills/public/pdf/SKILL.md` (hosted-env-only path, broken on local Windows). Repointed it to "invoke the `pdf` skill", noting the `/mnt` path as the hosted equivalent.

### mcp-builder vendored (PR #42)
6. Plugin model has no per-skill toggle — `example-skills` is a 12-skill unit. User wanted only `mcp-builder`, so vendored it to `.claude/skills/skil_mcp-builder/` (SKILL.md + reference/ + scripts/ + LICENSE.txt + VENDOR.txt recording source commit `6a5bb06`).
7. Verified `skil_mcp-builder` resolves in the live in-session skill list (project skills load without restart).

---

## Key Decisions Made
### Plugin marketplace mechanism over vendoring (for document-skills)
- **Choice:** Used the native plugin marketplace path, same as existing `playground`/`productivity-suite`.
- **Rationale:** Auto-updates, distributes to the other dev via the enabled-plugin entry, no fork to maintain.

### Project scope (not user scope) for document-skills
- **Choice:** Enabled in committed `.claude/settings.json`.
- **Rationale:** PDF protocol is a project rule; the other developer should get the backing skill automatically.

### Vendor mcp-builder instead of enabling example-skills
- **Choice:** Single project skill under `skil_` convention.
- **Rationale:** Enabling the plugin would dump all 12 example skills into the picker; user asked for one. Tradeoff accepted: no marketplace auto-update; VENDOR.txt records source commit for manual re-pull.

### Did NOT enable claude-api plugin
- **Rationale:** Duplicates the `claude-api` skill already in the environment.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/settings.json` | Modified | +`document-skills@anthropic-agent-skills` in enabledPlugins (PR #40) |
| `.claude/rules/rule_deliverables.md` | Modified | PDF protocol step 2 → pdf skill, not broken /mnt path (PR #41) |
| `.claude/skills/skil_mcp-builder/**` | Created | Vendored mcp-builder skill (PR #42) |
| `~/.claude/plugins/known_marketplaces.json` | Modified | Registered `anthropic-agent-skills` (out-of-repo, user scope) |
| `~/.claude/plugins/installed_plugins.json` | Modified | Recorded document-skills install (out-of-repo) |
| `~/.claude/plugins/marketplaces/anthropic-agent-skills/` | Created | Cloned marketplace (out-of-repo) |
| `~/.claude/plugins/cache/anthropic-agent-skills/document-skills/` | Created | Plugin skill cache (out-of-repo) |

---

## Current Status
All three PRs squash-merged to `main`; working tree synced. `skil_mcp-builder` live this session. `pdf`/`docx`/`pptx`/`xlsx` available next session (plugins load at session start). No client touched — pure system-infra. No comms/ops/Make reconciliation in scope.

---

## Next Steps
1. (Optional, user-driven) If `example-skills` skills beyond mcp-builder are wanted (webapp-testing was the other low-overlap candidate), vendor them the same way — say "vendor {name}".
2. (Optional) `claude plugin marketplace update anthropic-agent-skills` or re-clone to pull upstream skill updates; re-copy vendored mcp-builder from the clone when refreshing (VENDOR.txt has the pin).
3. No blocking follow-ups.

---

## Context for Next Session
### Files to Read First
- `.claude/settings.json` (enabledPlugins)
- `.claude/skills/skil_mcp-builder/VENDOR.txt` (source pin for re-pull)
- `~/.claude/plugins/known_marketplaces.json` + `installed_plugins.json` (plugin wiring, out-of-repo)

### Open Questions
- None.

### Working Notes
- **Replicating `claude plugin marketplace add` by hand:** clone repo → `~/.claude/plugins/marketplaces/{marketplaceName}` (name from marketplace.json, NOT repo name); add to `known_marketplaces.json`; populate `~/.claude/plugins/cache/{mkt}/{plugin}/{version}/`; add to `installed_plugins.json` (scope/projectPath/installPath/gitCommitSha); enable in project `.claude/settings.json` enabledPlugins as `{plugin}@{marketplace}`. Claude Code reconciles/re-caches on next start (it bumped document-skills to version hash `690f15cac7f7` afterward).
- Plugin enablement takes effect at session start; project skills in `.claude/skills/` load mid-session immediately.
- No per-skill toggle in the plugin model — a plugin is the unit. Selective single-skill need = vendor as project skill.
- Windows/MSYS path gotcha: invoking Windows-native `node`/exe from the Bash tool with an MSYS `/c/Users/...` path resolves to `C:\c\Users\...` (ENOENT). Use `c:/Users/...` form or PowerShell for native-binary file args.
- `anthropics/skills` marketplace = `anthropic-agent-skills`; 17 skills across 3 plugins; HEAD `6a5bb06` this session.

### Reference Materials
- PRs: github.com/011matthias/agentic-ops1.01/pull/40, /41, /42
- Repo: github.com/anthropics/skills

---

## How to Continue
Nothing pending. To add more Anthropic skills: read VENDOR.txt for the source pin, copy the skill dir from `~/.claude/plugins/marketplaces/anthropic-agent-skills/skills/{name}` into `.claude/skills/skil_{name}/`, commit + PR + merge.

---

## Strategic Feedback

### What Worked Well This Session
- Tight directive sequencing: "plug in repo" → "overview" → "get mcp builder" each landed as a clear, bounded ask, letting each step ship cleanly without scope ambiguity.
- The AskUserQuestion on plugin selection + scope front-loaded the only real fork, so the rest ran autonomously.

### Suggestions
- A `tools/add-anthropic-skill.py {name}` script would turn the vendor flow (clone-check → copy → VENDOR.txt → branch/commit/PR) into one command and remove the manual MSYS-path and printf-quoting footguns hit this session. Worth building if more skills get pulled.

### System Health
- The `/mnt/skills` reference in `rule_deliverables.md` was a latent cross-platform breakage (hosted-env path baked into a local-Windows workspace) that sat unnoticed until this work surfaced it — there may be other `/mnt/`-assuming references; a grep sweep during a future `/system-dev` is warranted.
- Autonomy score: 3 friction events, 0 user corrections — the one B1 deferral was self-corrected by the `stop-b1-gate.py` structural hook (held as designed); 2 self-detected slow-paths (Windows shell mechanics). Not elevated.

---

## Friction Events This Session
| Type | Detected by | Gate | Fix | Detail |
|------|-------------|------|-----|--------|
| agent-deferred | agent (B1 stop-hook) | B1 | structural (held) | First response ended "Want me to make that edit?" for a bounded autonomous rule fix; `stop-b1-gate.py` caught it same-turn and the edit was done. Not a regression — the structural backstop functioned. |
| slow-path | agent | none | documented | Validated JSON via Windows `node` with an MSYS `/c/...` path → `C:\c\...` ENOENT; needed a PowerShell re-validation. Lesson: use `c:/` form or PowerShell for native-exe file args from Bash. |
| slow-path | agent | none | documented | `printf '%s' '...\n...'` in a commit message left literal `\n`; needed `git commit --amend`. Lesson: use repeated `-m` flags or a here-string for multi-line messages, never `\n` in printf '%s'. |
