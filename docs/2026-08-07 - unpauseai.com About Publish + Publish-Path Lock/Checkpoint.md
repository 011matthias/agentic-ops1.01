# Checkpoint: unpauseai.com About Publish + Publish-Path Lock

**Date:** 2026-08-07
**Status:** Bio change LIVE on unpauseai.com/about (string-verified); publish path cemented into memory + CLAUDE.md; akkton GitHub Actions still dead (Nico fix pending)

---

## Summary
Published the one-paragraph Matthias-bio change to unpauseai.com/about and verified it live by content, then locked the real publish mechanism into the always-loaded memory + CLAUDE.md. GitHub Actions has been dead on akkton since 2026-08-04, so the normal auto-publish did not fire; the site went live via a manual replicate of `publish.yml` (the user ran the final owner-authored promote, because the agent's classifier hard-blocks author-as-akkton).

---

## What Was Done This Session

### Diagnosis (turned a "needs Nico" escalation into a drivable path)
1. Read `ci.yml` + `publish.yml` from a local clone (they were in a sibling session's scratchpad). This is what unlocked everything: CI triggers on `pull_request:[main]` (so the missing suite on PR #19 = Actions genuinely dead, not a config exclusion), and Publish works by making main's tip **akkton-authored** (no Vercel token; only `GITHUB_TOKEN`). Vercel Hobby builds only owner-authored commits.
2. Confirmed via API: akkton `id=188410956` type User; PR #19 `mergeable_state=clean`; main + live `/api/version` both `2e89530`; Actions' last run 2026-08-04.

### Publish (manual replicate of publish.yml)
3. Merged PR #19 (main -> `11806a37`, collaborator-authored, which Vercel refuses to build).
4. Built the owner-authored promote commit (parent `11806a37`, identical tree, author+committer `188410956+akkton@users.noreply.github.com`). **The agent's auto-mode classifier hard-blocked `gh api .../git/commits` (author-as-akkton) twice.** The user ran the promote (main -> `076cf44`); Vercel built it.
5. Verified LIVE by content, not by deploy status: `/api/version` == `076cf44`, `/about` serves "Nicolas and I started the company together" and the new "I build and run the systems we ship" opening, old opening gone, HTTP 200.

### Publish-path cementing (the "point every reference here" ask)
6. Rewrote memory `reference_vercel_platform_team_scope` as the authoritative procedure (mechanism, normal path, break-glass manual promote with the PowerShell + classifier gotchas, `/api/version`+grep verification); updated MEMORY.md index; scope-noted `reference_vercel_force_deploy_uses_cwd_tree` to legacy-platform-only; corrected CLAUDE.md Platform section (PR #499, merged, confirmed on origin/main).

---

## Key Decisions Made

### Manual owner-authored promote is the sanctioned publish path when Actions is down
- **Choice:** Replicate `publish.yml` by hand (merge, then an akkton-authored promote commit at main's tip).
- **Rationale:** It IS the repo's own mechanism (Nico's workflow does exactly this on every merge); Vercel Hobby only builds owner-authored commits and a Deploy Hook does not bypass that.

### Did not bypass the classifier for author-as-akkton or governing-file edits
- **Choice:** Left the owner-authored promote and the `rule_behaviors.md` scope-note for the user; did not self-add a permission rule or route through another tool.
- **Rationale:** Those guardrails (impersonation-shaped commits; agent editing its own governing rules) are the kind a human should clear, even with verbal authorization. The user ran the promote and committed CLAUDE.md; both landed.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| memory/reference_vercel_platform_team_scope.md | rewrite | Authoritative publish procedure (proven 2026-08-07) |
| memory/MEMORY.md | edit | Index line -> new path |
| memory/reference_vercel_force_deploy_uses_cwd_tree.md | edit | Scope-note: legacy platform project only |
| CLAUDE.md | edit (PR #499, merged) | Platform section -> akkton/unpauseai-web publish path |

---

## Current Status
unpauseai.com/about is live with the new bio. The publish path is authoritative in memory + CLAUDE.md. akkton GitHub Actions is still dead (no runs since 2026-08-04); until Nico restores it, every publish needs the manual owner-authored promote (user-run, PowerShell). `rule_behaviors.md` "Platform-merge-is-not-live" sub-clause was NOT edited (classifier-blocked; superseded by the memory + CLAUDE.md anyway). Platform has no infrastructure.yaml (no ops line).

---

## Next Steps
1. **Nico (durable fix):** restore GitHub Actions on akkton/unpauseai-web (Settings -> Billing -> Actions minutes / spending limit; confirm Actions enabled). Then `publish.yml` auto-promotes on every merge and no manual step is needed.
2. Optional: land the `rule_behaviors.md` scope-note (a one-line human edit; agent is classifier-blocked from editing rule files).
3. Next website change: follow `reference_vercel_platform_team_scope` (normal path if Actions is back; else the break-glass promote, user-run, PowerShell).

---

## Context for Next Session

### Files to Read First
- memory `reference_vercel_platform_team_scope` (the whole procedure)

### Open Questions
- Is akkton's Actions outage minutes-exhaustion or a disabled toggle? (admin-only to see; assumed billing.)

### Working Notes
- Owner promote recipe: parent = merge commit `M`, tree = `M`'s tree, author+committer `188410956+akkton@users.noreply.github.com`, via `POST git/commits` then `PATCH git/refs/heads/main`. The classifier blocks the AGENT; hand the USER the PowerShell form.
- Classifier cluster that blocked authorized work this session: author-as-akkton (x2), `.claude/rules/` edit (x1), governing-file commit of CLAUDE.md (x1 — user committed it, then the PR merge was NOT blocked). A PR *create* and *merge* of a user-authored governing-file change go through; only the agent's own edit/commit of it is blocked.
- api.github.com was intermittently unreachable for ~30 min mid-session (TCP timeouts); WebFetch to unpauseai.com stayed fine. A background retry loop initially had a bug (empty timeout output misclassified as success); fixed by requiring non-empty.

### Reference Materials
- PR #19 (unpauseai-web, merged + promoted), PR #499 (agentic-ops CLAUDE.md, merged)
- https://unpauseai.com/api/version (live-commit oracle)

---

## How to Continue
`/resume` is not needed for the website; the memory `reference_vercel_platform_team_scope` is self-contained. For the next publish, follow it end to end and verify with `/api/version` + a content grep.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the actual `publish.yml`/`ci.yml` (from a local clone, no network) converted a "this needs Nico/admin" escalation into a mostly agent-drivable path. Enumerating the real capability surface (B7) is what broke the logjam; the user's "no you unblock it" is what forced me to do it.

### Suggestions
- Two memory-only fixes keep failing by recall and both recurred today: (a) user-facing command blocks in bash when the user is on PowerShell (feedback_user_commands_powershell_syntax, 2026-07-25 regression), and (b) treating a classifier denial as a hard wall / escalating before exhausting (2026-07-22 regression). Both are candidates for a structural nudge: a write-time check that flags a fenced ```bash user-command block, and a decision-rule that a classifier denial on user-authorized work means "hand the user a runnable command" not "escalate as a wall".

### System Health
- **Autonomy: elevated (~6 human interventions)** — several were classifier-forced (the user had to hand-run the promote and hand-commit CLAUDE.md because the agent was blocked), not deferrals. Run /system-dev if the classifier-forced-manual pattern recurs.
- External: akkton GitHub Actions outage is a billing/admin issue outside this repo; the manual promote is the standing workaround until Nico clears it.
