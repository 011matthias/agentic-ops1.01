# Checkpoint: VolaByg Proposal + Short-Hook Pipeline

**Date:** 2026-06-09
**Status:** Shipped + verified live; proposal not yet sent (awaiting Loom)

---

## Summary
Built and deployed the VolaByg (Ibrahim) Upwork proposal p026, a Track 2 lead-flow + email-deliverability audit pitch for a Danish construction SMB. Mid-session the owner changed the proposal pipeline twice (cover letter is now a <=225-char hook; the video deliverable is a content guide, not a verbatim script), both made permanent in the validator + command.

---

## What Was Done This Session

### Pipeline changes (permanent, owner-directed)
1. **Cover letter = <=225-char hook + `---` links block.** `validate-proposal.py` gained a format-detected `Cover letter hook <=225 chars` FAIL; legacy long-form letters keep their old line-count rules. `comd_new-proposal.md` Step 4b + Track table and `PROPOSAL-TEMPLATES.md` (new Template 0) updated.
2. **Video deliverable = content guide, not a SAY:/>> script.** Detected by the absence of SAY:/>> markers; `_check_video_guide` added (checks zero em dashes + sectioned structure); Step 4c rewritten. Legacy scripts still validate.

### VolaByg p026 deliverables
- 7-page gated site (`platform/public/clients/volabyg-lead-automation/`, access `volabyg-2026`) + downloadable audit checklist.
- 222-char hook cover letter (outcome-first, "Hi Ibrahim, Matthias here…", references a live UK client) + video content guide.
- Proof anchor = independently verified public DNS: `volabyg.dk` SPF `-all` + DMARC `p=reject` vs Instantly's cold-send infrastructure.

### Ship + deploy
- PR #92 (site + cover-letter pipeline change) and PR #93 (human cover-letter rewrite + video content-guide format), both CI-green, squash-merged to main via isolated worktrees off origin/main (kept the unrelated fix-branch WIP clean).
- `tools/vercel-force-deploy.sh` (user-authorized) deployed main; verified all 8 routes 200 + content + access gate + pricing.

### Prep
- Produced a plain-language client briefing for the owner (what Ibrahim wants, the two-problem diagnosis, the 3-phase fix, his 4 answers, objection prep).

---

## Key Decisions Made

### Cover letter is a <=225-char hook (and video is a content guide)
- **Choice:** Owner directives mid-session. Implemented as format-detected validator rules so the whole back-catalogue does not break.
- **Rationale:** Lean, human-voiced outbound; the hook does three jobs (understand / proof / short implementation) and points to the depth, which lives in the video + site.

### Proposer = Matthias; pricing = audit-first
- **Choice:** Video opens as Matthias; EUR 850 audit / 1,900 rebuild / 600 per month.
- **Rationale:** Owner picks. Audit-first lowers the barrier to a first yes and scopes the rebuild from real findings.

### Lead the proposal with the verified DNS finding
- **Choice:** Use the public `volabyg.dk` SPF/DMARC lookup as the credibility anchor, framed as "a 2-minute public check already shows…", not as presumption.
- **Rationale:** Strongest "this person already did the work" signal; differentiates from generic Upwork applicants.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| tools/validate-proposal.py | Modified | Format-detected hook char-cap + `_check_video_guide`; legacy formats still validate |
| .claude/commands/comd_new-proposal.md | Modified | Step 4b (hook) + Step 4c (content guide) + Track table |
| .claude/skills/skil_upwork-proposals/modules/PROPOSAL-TEMPLATES.md | Modified | Template 0 (short hook); old templates retired to thinking-aids |
| platform/src/content/proposals/volabyg-lead-automation.md | Created | Proposal markdown + research block |
| platform/public/clients/volabyg-lead-automation/*.html (7) + audit-checklist.md | Created | Gated proposal site + artifact |
| workspace/proposals/volabyg-lead-automation/cover-letter.md | Created/edited | 222-char hook (typo fixed) |
| workspace/proposals/volabyg-lead-automation/video-script.md | Created | Video content guide |
| platform/cspell.config.json | Modified | Allowlist VolaByg + Ibrahim |

---

## Current Status
Live: https://unpauseai.com/clients/volabyg-lead-automation (access `volabyg-2026`). Both PRs merged to main, production deploy verified. Proposal frontmatter `status: draft`, `sent: null`. Loom not yet recorded.

No `infrastructure.yaml` platform section for volabyg (prospect, not an active client) — ops status N/A. No comms-log — staleness N/A.

---

## Next Steps
1. Record the Loom from `workspace/proposals/volabyg-lead-automation/video-script.md` (content guide).
2. Decide the walkthrough reference: the hook ends "Short walkthrough…" but the links block now only has the site URL. Either paste the Loom link back into the links block, or repoint the hook to the site.
3. Send on Upwork (the 222-char hook); then flip the proposal frontmatter `status: draft -> sent`, set `sent:`.

---

## Context for Next Session

### Files to Read First
- workspace/proposals/volabyg-lead-automation/cover-letter.md
- workspace/proposals/volabyg-lead-automation/video-script.md
- platform/src/content/proposals/volabyg-lead-automation.md
- tools/validate-proposal.py (short-hook + video-guide format logic)

### Open Questions
- Walkthrough reference in the cover letter: keep a separate Loom, or let the site be the walkthrough? (owner's call)
- Exact Instantly sending domain (as `@volabyg.dk` or a separate cold domain) is unconfirmed; the audit determines which, and it changes the precise deliverability mechanism, not the recommendation.

### Working Notes
- DEPLOY: this repo does NOT auto-deploy main. Run `tools/vercel-force-deploy.sh` after every platform merge (CLAUDE.md). The earlier 404 was a 23h-stale production deployment, not a build failure or CDN cache.
- The branch-isolation pattern that worked: create a worktree off `origin/main`, copy only the intended files in, commit/push/PR there. Keeps unrelated WIP on the current branch untouched and the PR diff clean.
- Verified DNS (public, 2026-06-09): `volabyg.dk` SPF `v=spf1 include:spf.simply.com -all`, DMARC `p=reject`, MX `mx.simply.com`, no common DKIM selector.

### Reference Materials
- https://unpauseai.com/clients/volabyg-lead-automation (access `volabyg-2026`)
- PRs: #92, #93

---

## How to Continue
The proposal is live and done; the remaining work is human (record Loom, resolve the walkthrough reference, send on Upwork, flip status). The two pipeline changes are merged and enforced for all future proposals.

---

## Strategic Feedback

### What Worked Well This Session
- Picking the cover-letter angle via concrete previews (3 real drafts with char counts) converged fast after the first draft missed, instead of guessing again.
- Authorizing the deploy explicitly at the Band-3 floor kept the irreversible/outward step in your hands while everything reversible ran autonomously.

### Suggestions
- The platform deploy step is a recurring trip hazard: a merge to main looks "shipped" but isn't live until `vercel-force-deploy.sh`. Worth a tiny post-merge reminder (hook or checklist line) so it is surfaced for authorization immediately after every platform PR merges, not rediscovered via a 404.

### System Health
- Two friction patterns recurred: closing-offer deferrals (caught twice by stop-b1-gate) and the deploy missed-memory-recall. The deferral hook holds reliably; the deploy one is memory-only and fragile (consider the structural reminder above).
- Autonomy score: 3 human interventions this session (1 cover-letter quality redo, 1 video-format redirect, the deploy authorization which is correct gating not a miss) (elevated — a /system-dev pass could close the deploy-reminder gap).
- Gates: B1 fired (autonomous research/validate/diagnosis; AskUserQuestion only on genuine forks); B2 verified via validators + live 8-route fetch; B3 fired (diagnosed the 404 to the real cause via `vercel ls`); B6 auto-ran commit->push->PR->merge-on-green x2 and paused correctly at the deploy floor; 2 closing-offer deferrals caught by the stop hook.
