# Checkpoint: Upwork Independence Repo Move + u5 Delivery Kit

**Date:** 2026-07-25
**Status:** Repo-move absorbed, AEO enablers + posts routed to unpauseai-web, u5 delivery kit started

---

## Summary
The website left the monorepo for `akkton/unpauseai-web`, so the uwi content work retargeted there (AEO plumbing PR opened, pointers fixed); then advanced u5 by extracting the client-agnostic lead-gen pipeline playbook from the Meji reference build.

---

## What Was Done This Session

### Website repo move (correction absorbed)
1. Confirmed unpauseai.com now lives in `akkton/unpauseai-web` (011matthias has WRITE); our old `agentic-ops1/platform` blog merges never reached the live site. Stopped chasing Vercel access for matthias-5647 (dead end by design — merge != deploy, Nico runs `vercel --prod`).
2. Investigated the new repo before building: found its blog renderer has NO table branch, while all 3 posts in Nico's PR #1 depend on comparison tables (would render as pipe-text), plus no sitemap.ts and no llms.txt.

### unpauseai-web PR #2 (AEO plumbing)
3. Ported the #376 sprint enablers into unpauseai-web: blog table renderer + `src/app/sitemap.ts` (post enumeration) + robots `Sitemap:` line + `oneproposal` cspell word. Build-verified in a local clone (tsc/eslint/build/cspell green; build emits /sitemap.xml; 3 posts each prerender one `<table>`). Left for Nico to review + deploy.
4. Held back llms.txt + pricing.md (his positioning/pricing) and per-post author bylines — surfaced on the PR as his call rather than publishing his copy.

### uwi ledger + u5
5. Retargeted u2 status + editorial-backlog to unpauseai-web (#441, merged): repo-move banner, PRs #1/#2 tracked, publish-target + docs/publishing.md pointers.
6. Recorded the owner purchase approvals (domains + Instantly approved, mailboxes provider-open, Apollo held) and the Zoho/Apollo open questions in the checklist (#399, merged earlier); revised the referral recommendation to "not a channel" after the owner challenged the premise.
7. u5 delivery-kit spine (#442, merged): `workspace/templates/leadgen-delivery/` README + pipeline-playbook.md, genericized from Meji `deliverables/shared/`.

---

## Key Decisions Made

### Content work targets unpauseai-web, not the monorepo
- **Choice:** All website/content is now a branch + PR into `akkton/unpauseai-web`; going live is Nico's deploy step.
- **Rationale:** The site was split out 2026-07-25; the monorepo `platform/` path is dead for the live site.

### Referral is not a channel to run now
- **Choice:** No referral asks; keep it opportunistic; invest the effort in u2 content + u3 LinkedIn; Jochen is a separate u7 partnership conversation.
- **Rationale:** Owner challenged the premise — 4 of 5 ledger sources are paying clients; the model prices relationship capital at zero. Asking mid-delivery is a real withdrawal.

### u5 is the next build focus
- **Choice:** Advance the delivery kit (unblocks u7 + u1's campaign; all in our repo) over more u2 posts (which pile PRs on Nico) or u3 (sequenced after u5).
- **Rationale:** Highest-leverage ungated work with no external review dependency.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| unpauseai-web `src/app/(public)/blog/[slug]/page.tsx` | Modified (PR #2) | Add GFM table render branch |
| unpauseai-web `src/app/sitemap.ts` | Created (PR #2) | Sitemap w/ blog post enumeration |
| unpauseai-web `public/robots.txt`, `cspell.config.json` | Modified (PR #2) | Sitemap line; oneproposal word |
| `workspace/templates/leadgen-delivery/README.md` + `pipeline-playbook.md` | Created (#442) | u5 delivery-kit spine |
| `workspace/projects/upwork-independence/status/{u2,u5}-*.md` | Modified (#441,#442) | Retarget content; u5 stage-playbooks done |
| `workspace/projects/upwork-independence/context/{editorial-backlog,referral-ledger,cold-email-purchase-checklist}.md` | Modified (#441,#399) | Retarget; referral premise; approvals |
| `~/.claude/.../memory/reference_vercel_platform_team_scope.md` | Modified | Repo-move + auth-scope truth |

---

## Current Status
Platform: no `infrastructure.yaml` for upwork-independence (internal program, no orchestrator instance). Everything actionable this session shipped or is out for Nico. unpauseai-web PR #1 (posts) and PR #2 (plumbing) are green and await Nico's review + deploy; merge does not deploy there. u5 delivery kit has its spine on main; four slices remain. All purchases still gated on payment method + vault credentials (vault reads denied by the session classifier).

---

## Next Steps
1. u5 tier scope mapping — defines what the 650/1850/6300 tiers include; owner sign-off; unblocks u6's offer menu. Highest-leverage remaining u5 slice.
2. u5 script skeletons + Instantly API-client template + engagement-doc templates — need the gitignored Meji scripts from the MAIN checkout (not this worktree).
3. Nico: review + deploy unpauseai-web PR #1 + PR #2 (say so on the PR if publishing is wanted).
4. Owner: Zoho quote + provider cold-outreach terms (mailbox decision), Apollo free-tier export test, purchase execution, referral recommendation call, hours-estimate correction.

---

## Context for Next Session

### Files to Read First
- `workspace/projects/upwork-independence/status/uwi-general.md` + `status/u5-delivery-kit.md`
- `workspace/templates/leadgen-delivery/pipeline-playbook.md` (the u5 spine)
- memory `reference_vercel_platform_team_scope` (repo-move truth)

### Open Questions
- Tier scope mapping content (owner sign-off): what 0.20/0.55/1.00 concretely include across volume/channels/reporting.
- NeverBounce + Zoho prices unverifiable by fetch/browser (bot walls / JS injection).

### Working Notes
- Worktree gotcha: gitignored files (client `context/`, `.vercel/project.json`) are NOT in a worktree; read them from the MAIN checkout `C:\Users\neuma_p1qrsic\Repo\agentic-ops1`. The u5 script skeletons need Meji's gitignored scripts, so that work is a main-checkout task.
- unpauseai-web CI = tsc/eslint/build + spell + Playwright (3 checks); local clone in scratchpad was used to build-verify PR #2.
- Deploy dead-ended for real: the stored Vercel login is matthias-5647 (one team, matthias-neumanns-projects); the platform project 403s. This is by design (Nico owns production); do not retry tokens/seats.

### Reference Materials
- unpauseai-web PR #1 (posts), PR #2 (plumbing): github.com/akkton/unpauseai-web
- agentic-ops PRs this session: #399, #441, #442

---

## How to Continue
`/resume upwork-independence`, read the u5 spine, then draft the tier scope mapping (the u6-unblocking slice) OR switch to the MAIN checkout to extract the u5 script skeletons from Meji's gitignored scripts.

---

## Strategic Feedback

### What Worked Well This Session
- Investigating unpauseai-web's actual renderer before opening a PR (B7/E2) caught the table-rendering gap that would have shipped Nico's 3 posts as pipe-text; the fix rode the same PR.

### Suggestions
- When a decision has a "should we even" layer, pose that before the "how" — the referral offer question was asked as "what offer" when the ledger already showed the premise was the real question.

### System Health
- The MD060 table-style linter warnings fire on every status-file edit (the repo's compact `|---|` style); they are noise on every uwi edit. Worth either adopting the linter's expected style repo-wide or disabling MD060, so real diagnostics are not buried.
- Autonomy score: 2 human interventions this session (referral-premise challenge; the repo-move correction was external info, not a correction of my work).
