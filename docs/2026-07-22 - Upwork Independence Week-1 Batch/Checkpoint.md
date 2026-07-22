# Checkpoint: Upwork Independence Week-1 Batch

**Date:** 2026-07-22
**Status:** Week-1 batch shipped (u1 checklist, u2 backlog + first posts, u4 ledger); all 5 PRs merged CI-green

---

## Summary

Executed the week-1 batch of the uwi program in an isolated worktree: u4 referral ledger (pool-15 falsified to 3-4 honest warm sources), u1 ready-to-purchase checklist (live-priced, ~2x the model's fixed-cost assumption), u2 editorial backlog (33 pieces) plus the first 3 corpus posts with the author/entity decision taken and applied.

---

## What Was Done This Session

### u4 — referral partnership
1. `context/referral-ledger.md` (#384): 7 first-degree names collapsing to 5 independent sources (Brisken/Dirk, Jochen, Meji/Gurmej+Jess, Wimmer/Irina+Tobias, Coolify/Dzmitry), 5 second-degree SI-ecosystem rows via Dirk, 0 subcontractors. Honest warm supply: 3-4 sources vs model pool-15 (~3x over reality) — the gtm-v2-confirm supply gap is confirmed at enumeration time.
2. Offer definition recommendation: no upfront commission for the client network; defined post-conversion thank-you; Jochen routed to partnership/subcontract (u7); commission reserved for arm's-length future partners. Owner call pending.

### u1 — cold-email infra
1. `context/cold-email-purchase-checklist.md` (#385): Porkbun $11.08/.com/yr, 5 RDAP-verified available domains (getunpauseai.com taken), GWS Starter EUR 6.80/mailbox/mo (2/domain plan), Instantly Growth $47/mo, Apollo Free (900 credits) -> $49+ annual-billed, NeverBounce TBD (403 + press-and-hold bot wall; ZeroBounce walled too). DNS-auth runbook + day-1-after-go sequence.
2. All prices live-fetched 2026-07-22 (WebFetch subagent + agent-browser for the JS-rendered Apollo page); B4 honored (TBD over invention).

### u2 — AEO content
1. `context/editorial-backlog.md` (#386): 33 pieces from icp.md demand taxonomy, buyer problem language, ranked intent x pool with T4/DACH up-weighted (content is the DE-legal channel).
2. First 3 P1 posts (#387): make-contractor-left-takeover, cold-email-no-replies-diagnostic, spf-dkim-dmarc-cold-email-minimum. validate-platform-content 0 findings; cspell clean after one CI-red fix cycle.
3. Author/entity decision surfaced and answered: per-post `author` frontmatter (hardcode = fallback for old posts), new posts credited "Matthias Neumann", publisher stays Organization UnpauseAI. Applied in `blog.ts` + `[slug]/page.tsx`.

### Program bookkeeping
1. Status files u1/u2/u4 brought current (incl. sprint-zero = merged #376, not force-deployed).
2. uwi-general hours ledger (#388): ~4.5h week-1 batch, marked as agent-session estimates.

---

## Key Decisions Made

### Blog authorship (owner, 2026-07-22)
- **Choice:** Per-post author frontmatter; the three new posts credit Matthias Neumann; Nicolas hardcode remains only as fallback for pre-existing posts.
- **Rationale:** Named-person authorship helps AI citation (E-E-A-T); the author entity should match who fronts the content program; per-post field keeps both developers able to author.

### Referral offer shape (recommendation, owner call pending)
- **Choice (proposed):** No upfront commission; post-conversion thank-you; Jochen = partnership track.
- **Rationale:** Rows are paying clients; commission reads transactional in the Mittelstand register and its admin cost exceeds yield at 3-4 sources.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| workspace/projects/upwork-independence/context/referral-ledger.md | Created | u4 ledger + offer recommendation (#384) |
| workspace/projects/upwork-independence/context/cold-email-purchase-checklist.md | Created | u1 ready-to-purchase checklist (#385) |
| workspace/projects/upwork-independence/context/editorial-backlog.md | Created | u2 33-piece backlog (#386) |
| platform/src/content/blog/{make-contractor-left-takeover,cold-email-no-replies-diagnostic,spf-dkim-dmarc-cold-email-minimum}.md | Created | First 3 corpus posts (#387) |
| platform/src/content/blog.ts + platform/src/app/(public)/blog/[slug]/page.tsx | Modified | Per-post author field, JSON-LD reads it (#387) |
| platform/cspell.config.json | Modified | + domainkey (DNS literal) (#387) |
| workspace/projects/upwork-independence/status/{u1,u2,u4}-*.md | Modified | Element states current (#384-#386) |
| workspace/projects/upwork-independence/status/uwi-general.md | Modified | Week-1 hours row (#388) |

---

## Current Status

All five PRs (#384-#388) merged on green CI and verified on origin/main. Blog posts and #376 AEO fixes are merged but NOT live (Vercel force-deploy pending owner order). Purchases, referral asks, and the tier menu remain gated per the standing 2026-07-22 owner decisions.

---

## Next Steps

1. Owner: force-deploy order (takes #376 + #387 live), purchase approvals (checklist §10), offer-recommendation call.
2. u2: continue P1 backlog (#4 Zapier/Make/n8n comparison, #5 warm-up duration, #6 lead-drop handoffs); schedule the monthly ai_visibility_probe run (needs PERPLEXITY_API_KEY).
3. u5: delivery-kit extraction (meji pipeline -> workspace/templates/leadgen-delivery/) — unblocks u7.
4. Feed the two model-feedback flags (referral supply 3-4 vs pool-15; infra cost ~2x EUR 40/mo) into the next scorer re-pin conversation once live data exists.

---

## Context for Next Session

### Files to Read First
- workspace/projects/upwork-independence/status/uwi-general.md
- workspace/projects/upwork-independence/context/editorial-backlog.md (working order for u2)
- workspace/projects/upwork-independence/context/cold-email-purchase-checklist.md (if a purchase go arrives)

### Open Questions
- Owner calls pending: force-deploy, purchases, offer recommendation, hours-estimate correction.
- NeverBounce pricing unverifiable by fetch/browser (bot walls) — quote on purchase day.

### Working Notes
- The brief's referenced kickoff checkpoint folder (`docs/2026-07-22 - Upwork Independence Execution Kickoff/`) is not on origin/main; the kickoff state lives in session 12 of the daily log + the merged status files. Its INDEX row currently dead-links pending a sibling session's docs PR.
- Playwright MCP needs the user's Edge on :9222 (was down); agent-browser CLI is the working fallback for JS-rendered pages.
- Apollo page shows only annual-billed rates; monthly-billed rate not displayed.

### Reference Materials
- PRs: #384 (u4), #385 (u1), #386 (u2 backlog), #387 (posts + author), #388 (hours)

---

## How to Continue

`/resume upwork-independence`, read uwi-general + the backlog, pick the next P1 pieces (u2) or start u5 extraction; act on whichever owner orders have arrived.

---

## Strategic Feedback

### What Worked Well This Session
- The standing-gates block in the brief (no purchases, no drafts, no menu, no force-deploy) let the whole batch run without a single mid-task permission question; the one genuine decision (author) was batched to the end and answered in seconds.

### Suggestions
- The referral supply gap is now measured, not suspected: consider re-weighting expectations for the referral channel before investing the u4 ask-drafting hours, rather than after.

### System Health
- validate-platform-content and cspell run as separate gates with separate dictionaries; the posts PR went CI-red on words the content validator had already passed. Folding a cspell pass into the content preflight (or validate-platform-content) would make "validator clean" mean "CI green" for content PRs.
- Autonomy score: 2 human interventions this session (both hook/self-detected friction, zero user corrections).
