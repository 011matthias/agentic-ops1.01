# Checkpoint: Shipment Bot Proposal, Repo Hygiene, Meji Prod Fix

**Date:** 2026-05-19
**Status:** All three workstreams complete and verified. Proposal submitted, repo hygiene merged, Meji prod 404 fixed and live-verified.

---

## Summary
Built and shipped Track 2 Upwork proposal p024 (German AI shipment-support bot), then a full-repo untracked-file hygiene pass (delete scratch + gitignore + archive + commit at-risk infra), an Upwork profile intro-video script, and diagnosed/fixed a production 404 on the Meji doc site caused by a stale Vercel production alias.

---

## What Was Done This Session

### Proposal p024 — ai-shipment-support-bot (Track 2)
1. Parsed anonymous Upwork job (German shop AI bot: WISMO + tracking corrections, All-Inkl email + Amazon Message Center, ERP-grounded, German-only, long-term partner).
2. 4 design decisions via AskUserQuestion: descriptive prospect label, $2,500–$4,000 phased, Track 2, n8n+Python+small-LLM. Proposer = Matthias (identity-memory confirm).
3. Worked around missing skill modules (PROPOSAL-CONFIG/AGENT-CONSTRAINTS/PROFILE-CONTEXT don't exist) by using the proposal corpus + `validate-proposal.py` as ground truth.
4. Built 8 HTML pages (index, solution, workflow, timeline, investment, faq, onboarding, gdpr), n8n skeleton artifact, cover letter (Template 3), video script.
5. Validators 38/0/0/0, validate-html 0 hits. Deployed (PR #14), live-verified, then Loom link added (PR #18), status flipped draft→sent (PR #20, submitted 2026-05-18 → recorded).

### Repo Hygiene (full-repo untracked audit)
1. Classified 57 untracked items repo-wide; reframed "cleanup" as mostly privacy + rescuing at-risk infra, not tidiness.
2. Deleted 11 ephemeral scratch files from `scripts/` (incl. 2 PII-bearing JSON intermediates), added `.gitignore` patterns (`scripts/.*`, `/test.pdf`, `.claude/chat-title`).
3. Archived 11 one-off `meji_*.py` scripts to gitignored `workspace/clients/meji-media/context/analysis-scripts/`.
4. Committed at-risk untracked infra/tooling/deliverables (PR #17, 59 files).

### Intro Video Script
1. Upwork profile intro-video script for Matthias: reliable-AI-automation positioning, multilingual led, ~75–95s, anonymized client use cases (no names, per user).
2. Saved to `workspace/projects/platform/upwork-agency/intro-video-script.md` (uncommitted, iterating).

### Meji Prod 404 Fix
1. Diagnosed `/docs/meji-media/build-plan` + `/volume-forecast` 404 (same commit as working `system-overview`) → stale production alias (1-day-old build predating the pages).
2. Force-deployed current main (`e35768f`) via `vercel-force-deploy.sh`, new prod `platform-3snvisd60`.
3. Verified: build-plan + volume-forecast now 200 (gate page), system-overview unchanged, proposal page no regression.

---

## Key Decisions Made

### Proposal: validator-as-ground-truth
- **Choice:** When `comd_new-proposal` referenced non-existent skill modules, used the existing proposal corpus + `validate-proposal.py` as the structural source of truth instead of blocking.
- **Rationale:** Validator encodes all enforced rules; corpus shows the live pattern. Zero rework loops resulted.

### Hygiene: archive client scripts to gitignored context/
- **Choice:** One-off `meji_*.py` → `workspace/clients/meji-media/context/analysis-scripts/` (gitignored).
- **Rationale:** Keeps reproducibility record local; client-query scripts must not reach the shared repo (existing policy: `workspace/clients/*/context/` is gitignored).

### Meji fix: force-deploy main, not investigate further
- **Choice:** After confirming files in main but absent from 1-day-stale prod, ran the sanctioned `vercel-force-deploy.sh`.
- **Rationale:** Trunk IS the intended production state; Vercel git-integration auto-deploy had lagged. Force-deploy is the documented remedy for the stale-prod/CDN failure mode.

### Rules: user reverted self-annealing additions
- **Choice:** Added rule 5 (pronounceability) + rule 6 (beat transitions) to `rule_deliverables.md`; user reverted both (and the shortened video script).
- **Rationale (theirs, inferred):** Rule 6 was requested ("make a concept"); rule 5 was my self-annealing suggestion. Reversion stands — do not re-apply.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| platform/src/content/proposals/ai-shipment-support-bot.md | Created | p024 frontmatter + research; status sent |
| platform/public/clients/ai-shipment-support-bot/*.html (8) | Created | Track 2 site |
| platform/public/clients/ai-shipment-support-bot/*-n8n-skeleton.json | Created | Downloadable artifact |
| workspace/proposals/ai-shipment-support-bot/cover-letter.md | Created | Template 3 + Loom link |
| workspace/proposals/ai-shipment-support-bot/upwork-message.md | Created | Short front-door message + German line |
| workspace/proposals/ai-shipment-support-bot/video-script.md | Created (user reverted edits) | Loom script |
| .gitignore | Modified | scratch/PII patterns |
| workspace/projects/platform/upwork-agency/intro-video-script.md | Created (uncommitted) | Upwork profile intro video |
| ~70 untracked infra/tooling/deliverable files | Committed (PR #17) | rescued at-risk files |
| Vercel production deployment | Redeployed | platform-3snvisd60 (Meji 404 fix) |

---

## Current Status
- **p024:** submitted on Upwork 2026-05-18, status `sent`, in main. Complete.
- **Repo hygiene:** PR #17 merged. 1 intentional untracked item remains (`upwork-message.md` was later committed in #18; intro-video-script.md still uncommitted, iterating).
- **Meji doc site:** live and gated correctly. https://unpauseai.com/docs/meji-media/ , build-plan/volume-forecast restored. Code `meji2026` (env `MEJI_ACCESS_CODE`).
- **HEAD:** `e35768f` (main moved significantly during session — other-dev merges up to PR #42).

---

## Next Steps
1. Finalize/commit `intro-video-script.md` when the user stops iterating.
2. `/system-dev` pass: (a) fix `comd_new-proposal` referencing non-existent modules + `/proposal-retro`; (b) investigate Vercel git-integration auto-deploy lag (root of the Meji 404, likely affects other recently-merged pages until force-deployed).
3. `/proposal-status` to confirm p024 shows `sent` in the pipeline dashboard.
4. Brisken: a `2026-05-20-dirk-call-talking-notes.md` draft is open in context/drafts — call prep pending (not touched this session).

---

## Context for Next Session
### Files to Read First
- docs/sessions/2026-05-19-context.yaml
- platform/src/content/proposals/ai-shipment-support-bot.md
- workspace/projects/platform/upwork-agency/intro-video-script.md (uncommitted)
- platform/src/lib/gated-sites.ts (Meji/Wimmer gate model)

### Open Questions
- Is Vercel git-integration production auto-deploy reliably firing on main merges, or does every platform change now need a manual `vercel-force-deploy.sh`? (Meji 404 implies the latter.)
- Should `comd_new-proposal` be rewritten to match the actual `skil_upwork-proposals` modules, or should the missing modules be created?

### Working Notes
- `validate-proposal.py` is structural-only ground truth (frontmatter form: `deliverables: {letter,video,site,artifact}` booleans; cover letter needs access code + video link in first 3 body lines, "The site includes:" block, optionality close; video script needs `BEAT 1/2/3`, `SAY:`/`>>`, LOOM NOTES, abbreviation glosses for non-common ALL-CAPS tokens within 120 chars).
- Meji 404 root cause: production alias pointed at a build predating the pages. `vercel-force-deploy.sh` self-verifies and busts CDN. Pattern will recur until auto-deploy lag is fixed.
- `cd` in the Bash tool persists and breaks relative hook paths (`.claude/hooks/*`) for ALL later Bash calls. Recover via PowerShell `Set-Location` to repo root (shells share cwd). Never `cd`; use absolute paths or `(subshell)`.
- Skill modules referenced by `comd_new-proposal` (PROPOSAL-CONFIG.md, AGENT-CONSTRAINTS.md, PROFILE-CONTEXT.md) and `/proposal-retro` do not exist. Use corpus + validator instead.

### Reference Materials
- Proposal: https://unpauseai.com/clients/ai-shipment-support-bot/ (code `ai-shipment-support-bot-2026`)
- Loom: https://www.loom.com/share/2c6cd58f7180477487efd370b8ec4f4d
- Meji docs: https://unpauseai.com/docs/meji-media/ (code `meji2026`)
- PRs: #14 (proposal), #17 (hygiene), #18 (Loom), #20 (sent)

---

## How to Continue
p024 is closed (submitted). The live follow-ups are the `/system-dev` items (proposal command drift + Vercel auto-deploy reliability) and finalizing the intro video script once the user stops iterating. Brisken Dirk call prep is the next client-facing thing if that surfaces.

---

## Strategic Feedback

### What Worked Well This Session
- Tight AskUserQuestion batching on the proposal (4 decisions in one round) and the intro video (4 in one round) kept identity/claims decisions with the user without stalling the build.
- B3 was applied well on the Meji 404: read full headers, compared a working sibling, traced to own-attributable infra (stale prod) rather than blaming the gate or git first.

### Suggestions
- The recurring theme is "structural PASS ≠ behaviorally correct" for spoken deliverables. The durable fix isn't more rules (user reverted them) but a one-line habit: read `SAY:` lines aloud before declaring a video script done. Consider keeping that as a personal check rather than a rule.
- When a command references infrastructure that doesn't exist (`comd_new-proposal`), that's silent drift that costs every run — worth a `/system-dev` cleanup rather than repeated per-session workarounds.

### System Health
- Autonomy score: 6 human interventions this session (elevated — run /system-dev to close gaps).
- Two infrastructure-deferred items recurred and were only documented: (1) `comd_new-proposal` stale module/command references, (2) Vercel auto-deploy lag forcing manual force-deploys. Both are now in Next Steps for `/system-dev`.
