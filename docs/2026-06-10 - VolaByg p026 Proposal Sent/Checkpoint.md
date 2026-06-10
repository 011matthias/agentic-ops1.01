# Checkpoint: VolaByg p026 Proposal Sent

**Date:** 2026-06-10
**Status:** Proposal SENT to Ibrahim. CRITICAL: sent landing-page link currently 404s (production not redeployed). Deploy + gating decision pending.

---

## Summary
Built the canonical problem-and-solution understanding for the VolaByg Loom video (sanity-checked the deliverability diagnosis and corrected the framing to two separate problems), then the proposal was sent. The sent landing-page link 404s because production was never redeployed after the volabyg pages merged to main; gating was reverted to "gate it" but the existing gate is a banned client-side one. Deploy and the gating fix are the open critical items.

---

## What Was Done This Session

### Video understanding / proposal content
1. Assembled the full problem-and-solution briefing for the Loom from the proposal markdown, cover letter, video content guide, checkpoint, and audit checklist.
2. Sanity-checked the email-authentication diagnosis. Corrected three over-claims:
   - From "Instantly mail is being rejected" to "reject-or-filter, the audit confirms which" (depends on whether Instantly sends as @volabyg.dk, via Simply.com SMTP, or from separate domains).
   - The cold-tool / warm-lead cause is the unconditional one and likely the bigger driver, because the reported symptom is "spam" not "bounced" (true reject-policy failures bounce, they do not land in spam).
   - Reframed from "two symptoms, one root cause" to two genuinely separate problems (deliverability vs data loss) sharing one pipeline and one owner. The two-problems reality is the argument for one A-to-Z owner.
3. Dropped the "bolted door" metaphor on request; rebuilt the briefing metaphor-free.
4. Created `workspace/proposals/volabyg-lead-automation/solution-context.md` as the canonical brief that drives landing-page narrative (untracked on the current branch).

### 404 diagnosis + gating
5. Diagnosed the live 404 correctly and fast (B3): isolated volabyg-specific vs whole-deploy by probing other `/clients/` sites (menovia 200, brisken 200, warme-wimmer migrated to /docs), confirmed files on origin/main, concluded stale production deploy (repo does not auto-deploy main).
6. Surfaced a gating fork (public vs gated). User chose public, then reverted to "gate it" because the application was already sent with code `volabyg-2026`.
7. Found the existing gate is client-side JavaScript (`if(code==='volabyg-2026')`) in all 7 pages, which `rule_gated_access` bans (code shipped in plaintext source).
8. Verified the sanctioned server-side path is feasible: `gated-sites.ts` model is path-agnostic (works for the `/clients/...` URL Ibrahim has), and the Vercel CLI is authed as `akkton` (can set the env var).
9. Created then tore down a `proposal/volabyg-public-site` worktree when the user reverted to gated.

---

## Key Decisions Made

### Gate the site (do not make public)
- **Choice:** Keep the gate; code `volabyg-2026` stays valid (already sent to Ibrahim).
- **Rationale:** Proposal already sent with that code and URL.

### Two separate problems, one owner (proposal framing)
- **Choice:** Present deliverability and the lead-count gap as distinct problems with distinct causes, unified only by pipeline + owner.
- **Rationale:** Honest and more persuasive; the two-skill-set split is the case for one A-to-Z owner. Avoids a claim that collapses under a follow-up question.

### Deliverability diagnosis stated as audit-confirmed, not asserted
- **Choice:** Lead with the verified strict-DNS finding (SPF -all, DMARC p=reject) as a credibility anchor, but phrase the rejection consequence as the reject-or-filter question the audit answers.
- **Rationale:** The reject outcome is conditional on Instantly's unobserved sending config; the cold-tool cause is the unconditional one.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/proposals/volabyg-lead-automation/solution-context.md | Created (untracked) | Canonical sanity-checked problem+solution brief driving landing-page narrative |

(No platform code changes were committed this session. The worktree branch was discarded.)

---

## Current Status
- Proposal p026 SENT to Ibrahim (code volabyg-2026).
- Live link https://unpauseai.com/clients/volabyg-lead-automation/ returns 404 (production last deployed before the volabyg pages; main does not auto-deploy).
- origin/main HEAD `7af3dc5` (#96) contains all 8 volabyg routes + the two-problem reframe.
- Gating: client-side JS gate present in the 7 HTML pages (rule_gated_access violation). Server-side migration not yet done.
- No `infrastructure.yaml` platform section for volabyg (prospect). Ops status N/A. No comms-log (prospect proposal). Comms staleness N/A.

---

## Next Steps
1. **URGENT, client-facing: deploy origin/main to production** so the sent link resolves. `tools/vercel-force-deploy.sh` from a clean origin/main worktree (per the cwd-tree gotcha). Band-3 floor, needs an explicit deploy order. The user owes a "correct" vs "fast" pick:
   - **correct:** add `gated-sites.ts` entry + two `proxy.ts` matcher lines for `/clients/volabyg-lead-automation`, set `VOLABYG_ACCESS_CODE=volabyg-2026` on Vercel, strip the client-side gate from the 7 pages, PR + merge, then deploy.
   - **fast:** deploy main as-is now (client-side gate, code works for Ibrahim), then migrate to server-side as a fast-follow.
2. After deploy, verify all 8 routes (200 + content) and the gate behavior (unlock with volabyg-2026 and with the master).
3. Decide whether `solution-context.md` edits should be applied to `index.html` / `solution.html` / the proposal markdown (the brief lists the implied edits) and committed, or left as the brief only.

---

## Context for Next Session

### Files to Read First
- workspace/proposals/volabyg-lead-automation/solution-context.md (canonical brief, untracked)
- platform/src/lib/gated-sites.ts (server-side gate model; add volabyg entry here)
- platform/src/proxy.ts (matcher literals; add the two /clients/volabyg lines)
- workspace/proposals/volabyg-lead-automation/video-script.md (Loom content guide)

### Open Questions
- "correct" vs "fast" gating path (then the deploy order).
- Apply the brief's implied edits to the live pages, or keep the pages as-is?

### Working Notes
- The 404 is pure deploy staleness, not code or gating: the files are on main and other `/clients/` sites serve fine; only volabyg 404s because the live prod build predates it.
- `solution-context.md` is untracked on branch `proposal/n8n-multi-client-ops` (the current branch, which is diverged and dirty with unrelated workspace deletions). It is NOT on main. If the brief or its edits should land, do it from a clean origin/main worktree.
- The client-side gate (lines ~28-48 CSS `.access-gate`, the `<div id="accessGate">` markup, and the `checkAccess()` + auto-grant IIFE) is identical across the 7 pages and removable by string match if migrating to server-side.
- Verified DNS (public, 2026-06-09, re-confirmed relevant): volabyg.dk SPF `v=spf1 include:spf.simply.com -all`, DMARC `p=reject`, MX `mx.simply.com`.

### Reference Materials
- Live (currently 404): https://unpauseai.com/clients/volabyg-lead-automation/ (code volabyg-2026)
- origin/main HEAD 7af3dc5 (#96)

---

## How to Continue
The single critical action is deploying production so Ibrahim's sent link works. Get the "correct" vs "fast" decision and the deploy order, run the deploy from a clean origin/main worktree, then verify the 8 routes and the gate. Everything else (server-side migration, applying the brief edits) follows from that.

---

## Strategic Feedback

### What Worked Well This Session
- The iterative sanity-check on the opener converged on a defensible diagnosis. Pushing back on "two symptoms, one cause" and on the asserted rejection caught two claims that would have failed under a technical prospect's follow-up.
- The 404 was diagnosed in one pass this time (isolate scope, check main, conclude staleness) instead of the 2026-06-09 guess-and-redeploy cycle.

### Suggestions
- Sending a proposal whose landing link is not yet live is the failure that bit here. Worth a pre-send check: before a proposal goes out, confirm the linked URL returns 200 (a one-line curl). The link being dead at send time is the worst-case version of the recurring stale-prod class.

### System Health
- The stale-prod-after-platform-merge class has now recurred at least three times (2026-05-19 x2, 2026-06-09, and this session) with the post-merge deploy reminder/hook proposed each time and never built. This session it caused a client-facing dead link. This is `infrastructure-deferred` and overdue for a structural fix (a PostToolUse or post-merge hook that flags "platform path merged to main is not live until vercel-force-deploy.sh runs", ideally with the pre-send URL check above).
- Autonomy score: 2 human interventions this session (the public-vs-gated direction change, and the pending deploy/gate decision which is correct Band-3 gating, not a miss). The client-side gate shipped by an earlier session is a separate latent rule violation surfaced now.
- Gates: B1 fired (autonomous diagnosis via curl/git/grep instead of asking); B3 fired correctly (full-picture 404 diagnosis); B6/Band-3 held (deploy not run autonomously, surfaced and awaiting order).
