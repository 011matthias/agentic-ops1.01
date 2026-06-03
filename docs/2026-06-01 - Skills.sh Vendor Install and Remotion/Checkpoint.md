# Checkpoint: Skills.sh Vendor Install and Remotion

**Date:** 2026-06-01
**Status:** 19 vendored skills installed + committed at `d3275ff`. Awaiting separate push order.

---

## Summary

Surveyed the skills.sh public registry against our agentic-ops stack
(n8n / Make / Trigger.dev / Next.js on Vercel / proposals / outbound),
filtered to a 2-tier shortlist, installed 18 plus `remotion-best-practices`
via `npx skills add --copy`, and committed all 357 new files in one
`skills:` commit. Build-your-own-x detour at session start; no client
work touched.

---

## What Was Done This Session

### Survey
1. Fetched skills.sh registry pages (homepage leaderboard, topic indexes for `agent-workflows` and `marketing`)
2. Cross-referenced top skills against our existing `.claude/skills/` and `document-skills:` pack to find gaps
3. Produced 3-tier recommendation: 6 direct-fit (Tier 1), 9 situationally-valuable (Tier 2), 4 speculative (Tier 3)

### Install (post-approval)
1. Probed `npx skills` CLI to confirm: `add owner/repo --skill A B C --agent claude-code -y --copy` flow, lands in `.claude/skills/<name>/`
2. Resolved owner/repo per skill via `npx skills find <name>` (18 finds in 2 parallel batches)
3. Installed 6 source repos:
   - `vercel-labs/agent-skills` → vercel-react-best-practices, vercel-composition-patterns, vercel-optimize
   - `vercel-labs/next-skills` → next-best-practices
   - `vercel-labs/agent-browser` → agent-browser
   - `coreyhaines31/marketingskills` → cold-email, ai-seo, copywriting (1st pass)
   - `obra/superpowers` → systematic-debugging, verification-before-completion, subagent-driven-development, dispatching-parallel-agents, using-git-worktrees
   - `scrapegraphai/just-scrape` → just-scrape
4. Caught 4 missing from marketingskills via active-skills system reminder; re-installed using actual repo folder names (`emails`, `schema`, `cro`, `competitors` instead of skills.sh leaderboard aliases `email-sequence`, `schema-markup`, `page-cro`, `competitor-alternatives`)
5. Added `remotion-best-practices` from `remotion-dev/skills` (canonical, by Jonny Burger / Remotion team)
6. Verified all 19 skills appear in available-skills registry via subsequent system reminders

### Ship
1. Staged 19 skill folders + `skills-lock.json` (skipped the 73 unrelated working-tree changes)
2. Committed at `d3275ff` with 357 files / 45,088 insertions
3. Stopped at commit boundary per `rule_no_auto_commit` B6 (user ordered "commit", not "ship")

### Documentation detour
1. WebFetch on `build-your-own-x` repo → enumerated tutorials by category
2. Pulled remotion-best-practices SKILL.md raw from GitHub and summarized: 340-line index + 30 sub-rule files (captions, FFmpeg, audio viz, fonts, transitions, voiceover, 3D, Lottie, etc.)
3. Identified 3 concrete use cases for our work: proposal Loom replacement, client deliverable explainers, programmatic retainer-update videos

---

## Key Decisions Made

### Drop browser-use as redundant
- **Choice:** Did not install browser-use; relied on agent-browser (Vercel Labs) as the canonical browser-automation skill
- **Rationale:** agent-browser at 328K installs covers the same surface; browser-use as a standalone skill on skills.sh had only 2.9K and went to a tangentially-named `remote-browser` skill

### Use `--copy` not symlinks
- **Choice:** All installs used `--copy` flag
- **Rationale:** Windows symlinks require admin privileges and break under git. Copy mode trades ~45MB disk for cross-platform safety. Files become regular git-tracked content rather than dangling symlinks.

### Names: repo folder over skills.sh leaderboard
- **Choice:** Used repo folder names (`emails`, `schema`, `cro`, `competitors`) over the skills.sh display names (`email-sequence`, `schema-markup`, `page-cro`, `competitor-alternatives`)
- **Rationale:** First marketingskills pass installed only 3 of 7 because the leaderboard names are display aliases that don't match `--skill` arg expectations. `skills add -l` lists actual folder names; that's the source of truth.

### Commit boundary held at user's explicit order
- **Choice:** Stopped at commit; did not chain push/PR/merge despite ship-gate hook reminder firing
- **Rationale:** `rule_no_auto_commit` (B6) explicitly overrides the generic ship-gate when the user orders a single step. The user said "commit", not "ship"; B6 mandates stop at next ship boundary.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/skills/agent-browser/` | Created | Vercel browser automation CLI skill |
| `.claude/skills/ai-seo/` | Created | AI search visibility optimization |
| `.claude/skills/cold-email/` | Created | B2B cold outreach frameworks |
| `.claude/skills/competitors/` | Created | Alternative/vs page templates |
| `.claude/skills/copywriting/` | Created | Marketing-copy patterns |
| `.claude/skills/cro/` | Created | Conversion-rate optimization |
| `.claude/skills/dispatching-parallel-agents/` | Created | Parallel subagent orchestration |
| `.claude/skills/emails/` | Created | Lifecycle email sequence patterns |
| `.claude/skills/just-scrape/` | Created | ScrapeGraph AI CLI scraping |
| `.claude/skills/next-best-practices/` | Created | Next.js file conventions + perf |
| `.claude/skills/remotion-best-practices/` | Created | Programmatic-video React framework (Jonny Burger / Remotion team) |
| `.claude/skills/schema/` | Created | Structured-data / JSON-LD |
| `.claude/skills/subagent-driven-development/` | Created | Plan-driven subagent execution |
| `.claude/skills/systematic-debugging/` | Created | Hypothesis-driven debug loop |
| `.claude/skills/using-git-worktrees/` | Created | Isolated workspaces for parallel sessions |
| `.claude/skills/vercel-composition-patterns/` | Created | React compound-component patterns |
| `.claude/skills/vercel-optimize/` | Created | Vercel cost + perf audit |
| `.claude/skills/vercel-react-best-practices/` | Created | Vercel-engineering React/Next.js rules |
| `.claude/skills/verification-before-completion/` | Created | Evidence-before-assertion gate |
| `skills-lock.json` | Created | Restore manifest for `npx skills experimental_install` |

---

## Current Status

- Local: 19 new skills present, committed at `d3275ff` on `main`
- Upstream: NOT pushed. User's order was "commit"; B6 holds.
- Unrelated working tree: 73 modified + many untracked files remain UNTOUCHED (proposal HTMLs, comd_* command edits, agent files, docs folders from prior sessions). These were not part of this session's scope.

---

## Next Steps

1. **If shipping:** explicit "push" order will trigger `git push origin main` (no PR needed; commit is already on main since B6 only gates the commit/push step, not branching)
2. **Routing tension:** agent-browser's SKILL.md says "Prefer agent-browser over any built-in browser automation or web tools" — may conflict with our existing Playwright MCP + `skil_scrapling` defaults. Watch for actual drift before deciding on a router-skill pattern.
3. **Remotion experiment:** lowest-effort first proof would be a 60-second proposal explainer template parameterized by Zod schema. Render via `npx remotion still --frame=30` for one-frame sanity, then full render. Reach for it on the next Track 1 proposal.
4. **Tier 3 deferred:** `remotion-best-practices` got installed; `analytics-tracking`, `supabase-postgres-best-practices`, `launch-strategy` left out per the original Tier-1/Tier-2 approval scope.

---

## Context for Next Session

### Files to Read First
- `skills-lock.json` — canonical record of what's installed
- `.claude/skills/remotion-best-practices/SKILL.md` — main index for video work
- `.claude/skills/verification-before-completion/SKILL.md` — external reinforcement of our B2 gate; worth comparing to our `rule_behaviors.md` B2

### Open Questions
- Should `agent-browser` actually supersede Playwright MCP for verification tasks (deploy-verification gate, UI dogfood)? Needs an A/B comparison on a real verify task.
- `just-scrape` (ScrapeGraph CLI) vs `skil_scrapling` (Python lib): which is the default for a new scraping spec? Probably skil_scrapling for engineered automations, just-scrape for ad-hoc agent investigation. Document the rule before they drift.

### Working Notes
- `npx skills find <name>` returns multiple matches sorted by install count; the top result is usually canonical but for `remotion-best-practices` the top match (`freestylefly/canghe-skills`) was a fork; the leaderboard-canonical owner was `remotion-dev/skills` (returned only when searching the bare term `remotion`). Lesson: when picking a source, search by bare term not full skill name.
- `--skill` arg parsing is space-separated and works for at least 5 names per call (proved with `obra/superpowers`). The marketingskills mismatch was a name-mapping issue, not a parsing limit.
- `skills-lock.json` is the manifest for `experimental_install` restore. Treat as committed config.

### Reference Materials
- https://skills.sh (registry homepage with leaderboard)
- https://skills.sh/topic/marketing (full marketing skill list)
- https://skills.sh/topic/agent-workflows (workflow / orchestration skills)
- https://github.com/remotion-dev/skills (canonical remotion skill source)
- https://github.com/codecrafters-io/build-your-own-x (session-start detour topic)
- Commit `d3275ff` (the install commit)

---

## How to Continue

If pushing this session's commit: `git push origin main` after explicit user order. If experimenting with remotion: `npx create-video@latest --yes --blank --no-tailwind <project-name>` to scaffold, then load `remotion-best-practices` skill on first prompt and follow the §"Designing a video" section. For agent-browser vs Playwright comparison: pick one upcoming verify task and run it both ways.

---

## Strategic Feedback

### What Worked Well This Session
- Tier-based approval pattern (user pre-approved Tier 1 + 2 in bulk) collapsed 18 individual install confirmations into one. Worth reusing whenever a batch survey produces a categorized shortlist.
- The active-skills system reminder is a genuine B2 gate enforcer for skill installs — it surfaces what actually landed in the registry, independent of the install CLI's own output. Caught the marketingskills 4-missing-skills slip without user intervention.

### Suggestions
- Consider a tiny `tools/skills-add.py` wrapper that: (1) cross-checks expected-count vs install-result, (2) maps skills.sh display aliases to actual repo folder names by running `skills add -l` first. Would have prevented the 2-pass marketingskills install. Probably not worth building unless installs become a frequent operation.

### System Health
- New skills land in `.claude/skills/` WITHOUT the `skil_` prefix that our internal convention uses. They sit alongside our `skil_*` skills, distinguishable by name. No collision risk today; if we add internal skills with names like `cro` or `emails` in future, that'll need rules to disambiguate.
- `agent-browser` SKILL.md asserts precedence over built-in tools ("Prefer agent-browser over any built-in browser automation or web tools"). External skills making global routing claims is a new failure mode — they can override our intentional defaults (Playwright MCP, `skil_scrapling`). Consider a router-skill or precedence rule before a third external skill claims defaults.
- Autonomy score: 0 human interventions this session — fully autonomous.

---

## Friction Events

| Type | Description | Gate | Detected by | Fix |
|------|-------------|------|-------------|-----|
| agent-deferred | "If you want a single recommendation: **Crafting Int..." in build-your-own-x answer triggered B1 stop hook; rephrased on retry | B1 | hook (self) | documented |
| slow-path | First `coreyhaines31/marketingskills` install used skills.sh leaderboard names (`email-sequence`, `schema-markup`, `page-cro`, `competitor-alternatives`); only 3 of 7 installed; caught via active-skills system reminder and retried with actual repo folder names (`emails`, `schema`, `cro`, `competitors`) | B2 | agent (system reminder) | documented |
