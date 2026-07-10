# Mini-Checkpoint: P028 B2B Cold Outreach Proposal

**Date:** 2026-06-11
**Status:** Deliverables shipped + site live; awaiting Loom recording + Upwork submission
**Type:** mini

---

## Summary
Full proposal package (p028) for an anonymous Moldova-based Upwork posting (B2B cold outreach system from scratch: Sales Nav / PhantomBuster / Apollo / Instantly, 500 LinkedIn DMs in 2 weeks). Track 1 + a one-page site added mid-session on owner correction; cover letter reworked from 225-char hook to hook + 4 numbered points on owner request.

## What Was Done
- p028 proposal record, research block via agnt_proposal-research (PR #114). Key angle: LinkedIn weekly-cap honesty (~100 connects / 50-80 DMs per week) as the practical-experience differentiator.
- One-page proposal site (price / workflow / proof only, per owner anti-slop correction) — PR #115, deployed via vercel-force-deploy from detached worktree, verified 200: https://unpauseai.com/clients/b2b-cold-outreach-setup/ (no access code, deliberate).
- Cover letter rewritten as hook + 4 numbered points (PR #117); Upwork screening answers for 3 form questions (PR #118).
- Validator fixes: Track 1 no longer requires client dir; required-pages roster Track 2-only (p027 regression-checked). cspell: +PhantomBuster, +Chisinau.
- Pricing locked: $40/hr, est. 15-25h ($600-1,000), Matthias personal profile.

## Current Status
Everything on main (f1b6a48), site live and verified. User has cover letter + 3 screening answers ready to paste. Remaining: record Loom from video-script.md, submit, flip status draft -> sent.

## Next Steps
1. After user submits: set `sent: "2026-06-11"` + `status: sent` in platform/src/content/proposals/b2b-cold-outreach-setup.md; run /proposal-retro b2b-cold-outreach-setup.
2. Decide cover-letter default: owner expects "4 bulletpoints and stuff" but skill template + validator still encode the 2026-06-09 225-char hook directive. If numbered-points is the new standard, update PROPOSAL-TEMPLATES.md Template 0 + validator cap.
3. Fix p027 gated-access violation: `insurance-2026` is a plaintext client-side literal in platform/public/clients/insurance-agent-cold-email/index.html:477 (banned pattern, rule_gated_access).
4. Friction backlog (full checkpoint or /comd_system-dev): stale-prod-after-merge hit its 3rd recurrence (no Vercel git integration; only vercel-force-deploy.sh publishes) — infrastructure-deferred, candidate structural fix = CI deploy job or Vercel git integration. Also: comd_new-proposal doc drift ({VIDEO_LINK} placeholder fails the validator TBD check; template heading `--` gets hook-stripped to `;`), and .html file association opens Word not browser (use explicit msedge in Start-Process).

## Files to Read First
- workspace/proposals/b2b-cold-outreach-setup/cover-letter.md (final letter)
- workspace/proposals/b2b-cold-outreach-setup/upwork-screening-answers.md (submitted answers)
- workspace/proposals/b2b-cold-outreach-setup/video-script.md (Loom guide)
- platform/src/content/proposals/b2b-cold-outreach-setup.md (p028 record + research)
