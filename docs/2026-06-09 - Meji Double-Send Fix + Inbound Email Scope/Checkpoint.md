# Checkpoint: Meji Double-Send Fix + Inbound Email Scope

**Date:** 2026-06-09
**Status:** Double-send bug across all 3 live Instantly campaigns caught + fixed + campaigns resumed (behavioral verification pending the 07:00 UK send window via a background monitor). Inbound multi-inbox work scoped; client message drafted (held for send).

---

## Summary
Resumed Meji on the Monday "verify Piece 1 first sends" task and found all three loader-built Instantly campaigns (Piece 1 warm + Piece 2 A/B cold) were double-sending — Touch 1 and the follow-up landing ~20 min apart instead of days apart. Root-caused to a per-step `delay` placement error, paused all three, fixed the delays (live + in the loaders + audit), and resumed under your authorization. Then scoped the inbound-enquiry multi-inbox deliverability work Gurmej prioritised, enumerated the full Workspace mailbox roster (no spare mailbox exists), wrote the scope to context, and drafted the client message.

---

## What Was Done This Session

### Instantly double-send incident
1. **Caught it** during the Piece 1 send verification: pulled actual sent emails (not just config) and found 8 P1 + ~20 P2A + ~22 P2B leads each got Touch 1 + Touch 2 ~20 min apart on 2026-06-08.
2. **Root cause:** Instantly's per-step `delay` is the wait BEFORE THE NEXT email (gap follows the step), confirmed against the official API docs. Loaders set `delay=0` on step 0, firing the follow-up immediately. Same bug in all 3 loader-built campaigns.
3. **Paused** all 3 (P1 `00fc708d`, P2A `c3daf05c`, P2B `5d677062`) under explicit user authorization (B5). Extended the pause to P2 after surfacing it.
4. **Fixed delays** live (read-modify-write, copy preserved): P1 `[0,18,28]`→`[18,10,0]`, P2A `[0,3]`→`[3,0]`, P2B `[0,2]`→`[2,0]`.
5. **Recurrence-kill:** patched both loaders' sequence builders + added a cadence-delay assertion to the P1 audit (the 17/17 GO missed this because it checked copy/structure, not timing). Wrote reference memory `reference_instantly_sequence_delay_semantics.md`.
6. **Resumed** all 3 (status 1) on user go. Launched background monitor `bfqd489xt` to verify the first post-fix batch at the 07:00 UK window and auto-re-pause on any recurrence.

### Inbound enquiry email-address scope (Gurmej's priority)
7. Read live A1 + A3 blueprints: 5 customer-facing send modules, all on the single `enquire@christmasofficeparty.co.uk` connection (13923632); Make binds connection per-module so rotation needs a router per send point.
8. Grounded the need in `volume-forecast.md` (Sept peak 100-150/day from one mailbox = Gmail spam cliff).
9. **Enumerated the full 24-user Workspace directory** via the admin console (Super Admin `matthias@mejimedia.com`): `christmasofficeparty.co.uk` has ONLY `enquire@`. No spare role mailbox to reuse; a 2nd sender must be created (1 new seat).
10. Wrote the scope to `context/inbound-enquiry-multiinbox-scope.md` and drafted the client message (held for user to send on Upwork).

### Comms
11. Logged Gurmej's + Matthias's 2026-06-08 thread verbatim (comms-log Block 21): service-question answer, inbound-first priority, two-piece loop-close.

---

## Key Decisions Made

### Pause + fix + resume all 3 campaigns (not just Piece 1)
- **Choice:** treated the double-send as a 3-campaign bug; paused P2 alongside P1 even though only P1 was the verify target.
- **Rationale:** identical root cause, actively harming cold prospects; pausing is protective + reversible. Surfaced the P2 extension explicitly rather than silently.

### Fix the loaders + audit, not just the live campaigns
- **Choice:** patched both loader `sequence()` builders and added a delay assertion to the audit.
- **Rationale:** self-anneal Layer 1 — a rebuild would reintroduce the bug, and the audit that passed 17/17 couldn't detect the failure mode (verification theater). Now it can.

### Create one new mailbox, not reuse an existing one
- **Choice:** the inbound 2nd sender will be a new `christmasofficeparty.co.uk` mailbox (1 seat), after confirming via admin console that no spare exists.
- **Rationale:** the enquirer-facing domain has only `enquire@`; other-domain mailboxes are wrong-brand + are the cold-outreach reputations we isolate. Two mailboxes (≤75/day each) clears the cliff.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/context/analysis-scripts/meji_p1_instantly_load.py | Modified | Fixed sequence delays `[18,10,0]` + added cadence-delay audit check |
| workspace/clients/meji-media/context/analysis-scripts/meji_p2_instantly_load.py | Modified | Fixed `sequences()` delay placement + audit check |
| workspace/clients/meji-media/context/pilot-routing.md | Modified | INCIDENT banner (3 campaigns paused/fixed) |
| workspace/clients/meji-media/context/comms-log.md | Modified | Block 21 (2026-06-08 thread verbatim) + frontmatter |
| workspace/clients/meji-media/context/inbound-enquiry-multiinbox-scope.md | Created | Inbound multi-inbox + monitoring scope, cost, hours, enumeration finding |
| memory/reference_instantly_sequence_delay_semantics.md | Created | Instantly delay-field semantics (reusable across Route 2) |
| memory/MEMORY.md | Modified | Index pointer for the new reference memory |

Live Instantly state (not files): 3 campaigns paused → delays corrected → resumed (status 1).

---

## Current Status
- **Piece 1 warm `00fc708d`:** LIVE, delays fixed `[18,10,0]`, sender `gurmej@mejimedia.com`. 8 leads already double-sent (unrecoverable; they get Touch 3 ~18 June).
- **Piece 2 A `c3daf05c` / B `5d677062`:** LIVE, delays fixed `[3,0]` / `[2,0]`. ~42 cold leads completed their 2-touch double-send (nothing further to them).
- **Background monitor `bfqd489xt`:** running, waiting for the 07:00 UK window (~06:00 UTC) to verify the first post-fix batch and auto-re-pause on recurrence.
- **Inbound multi-inbox:** scoped, awaiting Gurmej green-light on 1 new Workspace seat. Client message drafted, held for send.
- Make A0-A3 inbound: read-only this session, untouched.

---

## Next Steps
1. **Read the monitor verdict** (`bfqd489xt` output, or re-run `/tmp/meji_send_monitor.py` logic) once the window opens — confirm no lead gets a same-day second email. If clean, the fix is behaviorally verified.
2. **Send the inbound scope message** to Gurmej (drafted; user sends on Upwork), then log verbatim to comms-log.
3. On Gurmej's seat green-light: create the new `christmasofficeparty.co.uk` mailbox, start warm-up (3-4 wk, binding for September), build the A1/A3 rotation + A2 coverage + monitoring (~13-14 hrs).
4. **Retainer pitch (step two):** still queued for after first warm sends + first weekly report land.

---

## Context for Next Session
### Files to Read First
- workspace/clients/meji-media/context/pilot-routing.md (INCIDENT banner + canonical routing)
- workspace/clients/meji-media/context/inbound-enquiry-multiinbox-scope.md (the active inbound piece)
- workspace/clients/meji-media/context/comms-log.md (Block 21 = latest thread)
- memory/reference_instantly_sequence_delay_semantics.md (the delay rule)

### Open Questions
- Does the post-fix batch send cleanly (no same-day double) at the 07:00 UK window? (monitor will answer)
- Are the mejixmas.com (Piece 3) mailboxes genuinely send-ready? (unchanged from prior; scrutinise before Piece 3)

### Working Notes
- **Instantly `delay` = wait before the NEXT email.** Gap lives on the earlier step; last step's delay unused. `delay=0` on step 0 = immediate double-send.
- **The admin login "blocked" call was a misread:** Google's "password changed 12 days ago" is an informational note, not a rejection — the sign-in had actually gone through. Temp password `LRyQbu9*…` (in `.env` + vault) was current, not stale. Don't repeat that misdiagnosis.
- **Workspace roster (24 users):** `christmasofficeparty.co.uk` = `enquire@` ONLY. Other users on mejimedia.com/.co, mejievent/mejixmas/mejiai.com, includesummit.com, banterexp.com, justbanter.co.uk.
- **B5 hook gap (recurring):** `instantly-invasive-gate.py` does not fire on script-wrapped `api.instantly.ai` calls (`uv run /tmp/x.py`) — no api.instantly.ai in the Bash command string. Protocol held via explicit user authorizations only. Same gap flagged 2026-06-08.
- Make Slack connection `13035840` exists → monitoring alerts can route there at no cost.

### Reference Materials
- Prior: docs/2026-06-08 - Meji Piece 1 Christmas Warm Live/Checkpoint.md
- Campaign IDs: P1 `00fc708d-c17c-4b4f-bafb-9248bdd1e8b9`, P2A `c3daf05c-1395-43fb-8154-cc4643290859`, P2B `5d677062-adc0-4492-a4e3-3ffe8507ba88`
- Official Instantly delay-field doc: developer.instantly.ai/api-reference/campaign/create-campaign

---

## How to Continue
Start by reading the monitor output (`bfqd489xt`) — if it reports ALL-CLEAN, the double-send fix is behaviorally verified and you can close that loop. The inbound scope message is ready to send; once Gurmej approves the seat, the mailbox + warm-up start (timeline-critical for September). The retainer pitch waits on the first weekly report.

---

## Strategic Feedback

### What Worked Well This Session
- Verifying behavior over config (pulling actual sent emails on the Monday check) is exactly what caught a bug that the build audit's 17/17 GO had declared clean. The "verify the real send, not the stored data" instinct paid for itself.
- Your "cant we just use an existing mailbox?" redirect was the right challenge and exposed that the scope skipped the enumerate-existing-infrastructure step. The autonomous Workspace enumeration that followed gave a definitive answer instead of a guess.

### Suggestions
- The inbound scope message is ready; sending it tomorrow keeps the September warm-up clock from slipping (the 3-4 wk warm-up is the binding constraint, and it can only start after the seat is approved).

### System Health
- **B5 hook gap is now a 2x-recurring `infrastructure-deferred`:** `instantly-invasive-gate.py` is blind to script-wrapped invasive calls. The actual pause/fix/resume of 3 live campaigns ran with zero hook coverage; only the explicit-authorization protocol held. Worth teaching the gate to flag inline scripts that contain `api.instantly.ai` or known invasive loaders.
- **The audit-vs-behavior gap that caused the double-send** is the same class as prior verification-theater entries: a GO verdict that checks structure but not the behavior that matters. The fix (cadence assertion) is local; the general lesson is that every "campaign live" audit needs a post-activation behavioral probe, not just a pre-activation config check.
- Autonomy score: 4 friction events (elevated) — 2 user-prompted (mailbox-reuse redirect, vault-password nudge), 2 self-detected (double-send catch, premature-limitation misread). Run /system-dev to close the B5-hook gap.
