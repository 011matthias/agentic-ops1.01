# Checkpoint: VolaByg Proposal Reframe and Deploy

**Date:** 2026-06-10
**Status:** Proposal SENT to Ibrahim. Live site fixed and serving. Two PRs merged (#96, #97). Production deployed and verified.

---

## Summary
Fixed the reported 404 on `https://unpauseai.com/clients/volabyg-lead-automation/`, reframed the entire VolaByg (p026) proposal to the canonical `solution-context.md` (two-problem framing), shipped it to main, and deployed production. Proposal is now finished and sent to Ibrahim.

---

## What Was Done This Session

### Diagnosis (the 404)
1. Root cause was NOT uncommitted code. VolaByg has been on `main` since PR #92; the live site was serving a **stale Vercel build that predated that merge**. This repo deploys via manual `tools/vercel-force-deploy.sh`, and merges #92–#96 had never been force-deployed.
2. First (wrong) read was "never committed", inferred from the current dirty branch (`proposal/n8n-multi-client-ops`, 16 behind main) where the files are untracked. Corrected when an `origin/main` worktree showed the files as tracked (` M`), then confirmed via live `curl` (volabyg 404, older menovia 200, both on main = stale prod).

### Content reframe to canonical (PR #96)
3. Reframed landing pages + proposal markdown + cover-letter + video-script to `workspace/proposals/volabyg-lead-automation/solution-context.md`:
   - **Two distinct problems, one pipeline, one owner** (index H2), not "one root cause".
   - Spam leads with the **cold-tool reputation cause**; the strict-DNS `p=reject` finding becomes the audit's **"rejected or just filtered" question**, not an asserted fact. Added the "spam, not bounced" tell.
   - Count gap split into **transfer loss + invisible-alert loss**.
   - "no DKIM" softened to "none on common selectors" (absence not provable externally).
   - Last-updated stamps bumped to 2026-06-10.
4. Caught that the local `video-script.md` had **regressed to a "one root cause" draft**; discarded it and rebased on main's #93 version, then fixed its one remaining auth-as-fact line.

### Deploy + verify
5. Merged PR #96 (squash, all CI green). On explicit user order, force-deployed `main` to production from a clean `origin/main` worktree (guards against concurrent git-integration rebuild). Verified all 7 pages return 200 with reframed content live; original trailing-slash URL → 200.
6. Confirmed menovia + 26 other client pages now 404 in production is **intended** (PR #94 pruned 28 dead landing pages; production was just behind). Current main keeps only brisken (200) + volabyg. Homepage 200.

### Loom guide (PR #97)
7. Added a crafted **suggested opener and close** to `video-script.md` §1/§5 as "say it your way" lines (entry: cause-visible-from-outside + defers price; exit: one-owner + Phase 1 audit + soft call offer). Merged, CI green. Internal collateral, no deploy.

---

## Key Decisions Made

### Isolated worktree off origin/main for every commit
- **Choice:** Did all commits in throwaway worktrees based on `origin/main`, never on the dirty current branch.
- **Rationale:** `proposal/n8n-multi-client-ops` has 86 unrelated WIP entries and is 16 behind main; committing there would mix concerns and pollute the PR. The worktree keeps PRs clean and leaves the user's WIP untouched. Same reason the force-deploy ran from a clean main tree (`vercel-force-deploy` publishes the local tree, not main).

### Did not import the local video-script
- **Choice:** Rebased video-script on main's #93 version instead of committing the local draft.
- **Rationale:** The local draft used "one root cause" framing, which the canonical file explicitly supersedes. Committing it would have contradicted the same instruction it was meant to satisfy.

### Surfaced the production deploy as a gated decision
- **Choice:** Stopped before deploying and waited for an explicit order.
- **Rationale:** Production deploy is a B6 Band-3 gated-floor action; it also publishes all of main (wider blast radius than one proposal). User ordered "deploy now".

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| platform/public/clients/volabyg-lead-automation/{index,solution,workflow}.html | Modified (#96) | Two-problem reframe, audit-question phrasing, 2026-06-10 stamp |
| platform/public/clients/volabyg-lead-automation/volabyg-lead-automation-audit-checklist.md | Modified (#96) | Reject-vs-filter reframe, soften "no DKIM" |
| platform/src/content/proposals/volabyg-lead-automation.md | Modified (#96) | Two-problem reframe of the Next.js proposal body |
| workspace/proposals/volabyg-lead-automation/cover-letter.md | Modified (#96) | Two-problem framing, hook trimmed to <=225 chars |
| workspace/proposals/volabyg-lead-automation/video-script.md | Modified (#96, #97) | Canonical fix + suggested opener/close lines |
| workspace/proposals/volabyg-lead-automation/solution-context.md | Added (#96) | Canonical narrative source of truth |
| (production) unpauseai.com | Deployed | Force-deploy of main; volabyg live, 28 dead pages pruned |

---

## Current Status
- Live: `/clients/volabyg-lead-automation/` and all 7 sub-pages → 200 with reframed content. Audit checklist → 200. Brisken + homepage healthy.
- main HEAD: 8984d32 (PR #97). PRs #96 + #97 merged.
- Proposal **sent** to Ibrahim (per user). Frontmatter `sent:` still reads `null` — see Next Steps.
- No client folder exists for volabyg (prospect, not onboarded): no infrastructure.yaml / comms-log, so ops/comms-staleness checks N/A.

---

## Next Steps
1. **Resolve the gating decision (owner call, carried over from prior session today).** All 7 live volabyg pages carry a **client-side JS access gate** with the passcode `volabyg-2026` in plaintext page source (index.html:488). This conflicts with `rule_gated_access` (client-side gates banned; server-side only). It is NOT volabyg-specific: the live brisken `/clients/` site uses the same pattern, the server-side mechanism (`gated-sites.ts` + `proxy.ts`) is built only for `/docs/` active-client sites, and the rule's enforcement scope names `docs/**` + `src/**`, not `clients/**`. Three options: (a) make proposal sites public and remove the gate (matches the other ~27 `/clients/` proposals; the access code sent to Ibrahim becomes vestigial but the link still works); (b) move proposal gating to the sanctioned server-side model (bigger change: add `/clients/volabyg` to the proxy matcher + `VOLABYG_ACCESS_CODE` Vercel env var); (c) accept client-side gates for prospect proposals and update `rule_gated_access` to carve out `/clients/**` explicitly. The code was already sent to Ibrahim, so whatever is chosen, the link must keep resolving.
2. **Update proposal frontmatter `sent: null` → `sent: "2026-06-10"`** in `platform/src/content/proposals/volabyg-lead-automation.md` (+ keep `status: draft` or move to `sent`) so `/proposal-status` reflects reality. Needs a PR (clean worktree off main).
3. Clean up the user's stale local untracked volabyg files (old one-cause drafts) on the dirty branch before the next `git pull`/`checkout main`, or they will block checkout: `git clean -fd platform/public/clients/volabyg-lead-automation platform/src/content/proposals/volabyg-lead-automation.md workspace/proposals/volabyg-lead-automation`. main is authoritative.
4. When Ibrahim replies, log the thread (no comms-log exists for volabyg yet; create one if the prospect converts).

---

## Context for Next Session

### Files to Read First
- workspace/proposals/volabyg-lead-automation/solution-context.md (canonical narrative; landing-page copy must match this)
- platform/src/content/proposals/volabyg-lead-automation.md (frontmatter: id p026, value EUR 850 + 1,900 + 600/mo, access_code volabyg-2026)

### Open Questions
- None blocking. Awaiting Ibrahim's reply to the sent proposal.

### Working Notes
- Production deploy model: NOT auto-deploy on merge. Use `tools/vercel-force-deploy.sh` from a clean `origin/main` worktree (copy `platform/.vercel/project.json` in). vercel CLI authed as `akkton`, project `platform` (prj_xMUV…), org team_uBLr….
- To check whether something is live, query `origin/main` + live `curl`, not the local branch — the dirty `proposal/n8n-multi-client-ops` branch is 16 behind main and its volabyg files are untracked local drafts.
- Branch `proposal/volabyg-lead-automation` is the consumed #92 branch; use a fresh name for any new volabyg PR.

### Reference Materials
- PR #96: https://github.com/011matthias/agentic-ops1.01/pull/96 (reframe)
- PR #97: https://github.com/011matthias/agentic-ops1.01/pull/97 (Loom open/close)
- Live: https://unpauseai.com/clients/volabyg-lead-automation/ (access code: volabyg-2026)

---

## How to Continue
The proposal is sent and live; the immediate work is done. If picking up: ship the `sent: 2026-06-10` frontmatter update (Next Step 1), then wait on Ibrahim. If he engages, the Phase 1 audit (EUR 850, read-only) is the proposed entry point.

---

## Strategic Feedback

### What Worked Well This Session
- The canonical `solution-context.md` as a single source of truth made the reframe mechanical and catchable: it let me detect that the local video-script had regressed, instead of silently shipping a contradiction. Designating one "this file wins" doc per proposal narrative is worth repeating.

### Suggestions
- The dirty `proposal/n8n-multi-client-ops` branch (86 WIP entries, 16 behind main) is a standing hazard: it makes "is this committed/deployed?" ambiguous and forced every commit through a worktree. Worth landing or shelving that branch's WIP soon.

### System Health
- Production deploy is manual and easy to forget after a merge (5 merges had stacked up undeployed, which is what caused this 404). A post-merge reminder or a CI step that flags "main is ahead of the live production deployment" would prevent the next stale-deploy 404.
- `rule_gated_access` (client-side gates banned, server-side only) and the actual `/clients/**` prospect-proposal practice (client-side JS gates with plaintext codes, e.g. volabyg + brisken) have diverged. The rule's mechanism and enforcement target `/docs/**` active-client sites; `/clients/**` sits in an unenforced gap. Either the rule should explicitly carve out `/clients/**`, or the proposal sites should adopt the server-side model. Until decided, `validate-proposal.py`'s "Access gate present" check rewards the banned client-side pattern, masking it.
- Autonomy score: 3 human/hook interventions this session (all self/hook-caught before user impact): a slow-path initial misdiagnosis, a stop-hook B1 catch on a deferred commit, and a missed gate-inspection (asserted "public" without reading the page, corrected at checkpoint via the prior session log).
