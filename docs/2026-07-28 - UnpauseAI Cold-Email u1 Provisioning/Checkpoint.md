# Checkpoint: UnpauseAI Cold-Email u1 Provisioning

**Date:** 2026-07-28
**Status:** Purchase blocked on owner-provisioned UnpauseAI accounts; all decisions closed, warm-up-parallel build prepped

---

## Summary
Went to execute the u1 cold-email purchase runbook; enumeration found the vault holds only Meji **client** accounts, not UnpauseAI rails, so no spend could fire without a client-boundary violation. Closed the three open purchase decisions, wrote the owner-provisioning path, and prepped the account-agnostic build (filter spec + sequences).

---

## What Was Done This Session
### Enumeration (the finding that gated everything)
1. RDAP re-checked all 5 domain candidates: still available.
2. Confirmed Porkbun's API now supports registration (`POST /domain/create`), but only from a verified, funded account.
3. Read the vault: `porkbun`=`gurmejsp`, `apollo`=`gurmej@mejimedia.com`, `workspace-super-admin`=`matthias@mejimedia.com` (Meji tenant), Instantly=client's only. All client property; no UnpauseAI-owned rails. Did NOT touch any client account.
4. DNS: unpauseai.com's own mail runs on Zoho (`mx.zoho.eu`), a second reason to keep cold senders off Zoho.

### Decisions closed (research, no account needed)
1. Mailbox provider: Google Workspace, separate tenant. Zoho ruled out (its usage policy bans cold outreach + it hosts the clean root's mail; blast-radius).
2. Verification: MillionVerifier (~$37/10k vs NeverBounce ~$80/10k).
3. Apollo free tier ruled out (late-2025 gutted it to a 25-record export cap); needs a paid Basic seat.

### Deliverables (PR #468)
1. Rewrote `cold-email-purchase-checklist.md`: decisions closed, account-ownership finding, owner-provisioning steps (§12), GWS-exact DNS runbook (§7).
2. New `u1-list-and-sequences.md`: exact Apollo filter (UK+US, owner/MD, 5-50, Make/n8n/Zapier/GHL, DE excluded) + 4-touch cold-email sequence v1 drafts (delay-on-earlier-step cadence).
3. Updated `u1-cold-email-infra.md` element states.

---

## Key Decisions Made
### Do not build UnpauseAI's engine on client accounts
- **Choice:** Every u1 line buys on an UnpauseAI-owned account the owner provisions; no client account is used.
- **Rationale:** Co-mingles billing on the client's cards, puts UnpauseAI's cold-sending reputation on the client's infrastructure (deliverability risk to Meji), and defeats the independence program. Owner confirmed this path.

### Cold senders separate from the clean root
- **Choice:** Google Workspace in a new tenant, not Zoho.
- **Rationale:** Zoho bans cold outreach and already hosts unpauseai.com's real mail; a suspension must not touch the clean root.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/projects/upwork-independence/context/cold-email-purchase-checklist.md | rewrite | Decisions closed, owner-provisioning steps, GWS-exact DNS |
| workspace/projects/upwork-independence/context/u1-list-and-sequences.md | new | Apollo filter spec + sequence drafts |
| workspace/projects/upwork-independence/status/u1-cold-email-infra.md | update | Element states + real blocker |

---

## Current Status
u1 is prepped to the account boundary. PR #468 open (CI pending at checkpoint). Nothing purchased; no send (B5 unchanged). The warm-up clock cannot start until the owner provisions the UnpauseAI-owned accounts (card + signup + phone/2FA are theirs to do); everything downstream is agent-executable.

---

## Next Steps
1. **Owner:** provision the UnpauseAI-owned accounts per checklist §12 (Porkbun funded, new GWS tenant, Instantly Growth, Apollo Basic, MillionVerifier). Fastest clock-start = items 1-3.
2. Once `porkbun-unpauseai` + `gws-unpauseai` + `instantly-unpauseai` exist: I register the 3 domains, add them to the tenant, create 6 mailboxes, run DNS (§7), connect to Instantly, enable warm-up same day; set day-21/28 markers.
3. During warm-up: build the Apollo list per the filter spec, MX pre-filter, MillionVerifier, load sequences; refine copy vs u5/u2; swap the Step-3 bracket for a verified case.
4. First real send stays B5-gated (separate scope-of-effects + readiness audit).

---

## Context for Next Session
### Files to Read First
- workspace/projects/upwork-independence/status/u1-cold-email-infra.md
- workspace/projects/upwork-independence/context/cold-email-purchase-checklist.md (§12 = owner steps)
- workspace/projects/upwork-independence/context/u1-list-and-sequences.md

### Open Questions
- Apollo Basic is billed annually (~$588 up front) for a small pool; check the monthly-billed rate first, or accept the annual seat as the shared enrichment engine for u3 too.
- GWS tenant primary domain: use one sending domain (e.g. tryunpauseai.com) as primary, other two as secondary.

### Working Notes
- Vault naming: store new UnpauseAI creds with a `-unpauseai` suffix so they never get confused with client accounts again (root cause of this session's stop).
- Porkbun API registration draws from prepaid balance, not a per-call card charge; fund >= ~$34 before the register call.
- Did not run the Porkbun `/ping` (would touch the client account); credential validity for the UnpauseAI account gets verified once it exists.

### Reference Materials
- PR #468: https://github.com/011matthias/agentic-ops1.01/pull/468
- Zoho cold-email ban: https://www.zoho.com/mail/help/usage-policy.html
- Verifier pricing: https://puzzleinbox.com/blog/millionverifier-pricing-guide/

---

## How to Continue
`/resume upwork-independence`, then read the three u1 files. If the owner has provisioned accounts, execute checklist §8 (day-1 sequence). Otherwise the work is warm-up-parallel refinement only.

---

## Strategic Feedback

### What Worked Well This Session
- The Layer-3 intent review fired correctly: the task's premise (vault creds = purchase rails) was tested against reality before any spend, catching a client-boundary violation at enumeration time rather than mid-purchase (B7 + B5 both held).

### Suggestions
- Add a vault-hygiene convention (owner-scope suffix like `-unpauseai` vs `-{client}`) so account ownership is legible at read time; would have surfaced today's stop in one `vault.py list`.

### System Health
- **Autonomy: 1 human decision** (the account-provisioning direction fork — a genuine owner call on money + boundary, not an automatable deferral). No gates skipped. B1/B5/B7 fired correctly.
- Recurring `missed-tool`: opened with `find`/`grep -r` over the repo root (120s timeout, redone with Glob/Grep). Same pattern as 2026-07-22 brisken; the CLAUDE.md guidance is in-context but keeps losing to habit. Worth a /system-dev look at a PreToolUse Bash nudge on repo-root `find`/`grep -r`.
