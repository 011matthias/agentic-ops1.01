# Checkpoint: Air to Sea Shuttles Reply

**Date:** 2026-11-16
**Status:** Reply sent; waiting for Harold Riley to pick a call time

---

## Summary
Harold Riley answered the 10-30 enquiry and asked for a call and a contact number. He wants Google Business Profile, SEO, AI-search visibility and site conversion work first, with booking, quoting and follow-up automation after that, on a limited budget. We drafted the reply and Matthias sent it after removing the mention of Nicolas.

---

## What Was Done This Session
### Comms
1. Read the prospect's comms log and the 10-30 checkpoint, then drafted a send-ready reply. It proposes Wed 18 or Thu 19 Nov, 11 AM-1 PM Houston time, and gives Matthias's +49 number with WhatsApp suggested. It links his two lists: groups of six or more are told to call for a quote, so site conversion and quoting meet at the same point. It commits Matthias to reviewing the GBP and the site before the call. No prices. `lint-comms-draft.py`: 0 hits.
2. Logged Harold's inbound mail verbatim, with his priorities and budget wording, plus the sent reply. The reply is marked as reconstructed because the sent copy was never seen (see below).
3. Decision via AskUserQuestion: Matthias takes the first call alone, and Nicolas is offered for a follow-up or an in-person meeting if Harold asks.

---

## Key Decisions Made
### First call without Nicolas
- **Choice:** Matthias alone, although Harold asked for "you and Nicolas".
- **Rationale:** The owner's call. He removed the Nicolas line before sending. The fallback for the call is recorded in the comms log.

### Budget handled in Register A
- **Choice:** No number and no concession. The reply says the call is about "which one or two things are worth doing first for the budget you have in mind".
- **Rationale:** No price has been stated yet. Pricing belongs in the conversation (first-letter rule).

---

## What Did NOT Work (and why)
- **Reading the sent reply for a verbatim log:** iCloud Sent ("Sent Messages", 125 items) has nothing addressed to air2seashuttles. Gmail IMAP returned `AUTHENTICATIONFAILED Invalid credentials` with `~/.gmail.env`. The screenshot UI is Zoho Mail, and nothing here reads it.
- **Checking call slots against the owner's calendar:** lecture times live only in the KIT calendar (CalDAV). No tool reads it, and the one Stundenplan PDF found is in iCloud Trash. The proposed slots are unchecked.
- **Heredoc carrying a Python IMAP script:** the heredoc-size-gate blocked it because `\\Sent` would collapse in transit. Rewrote the script with the Write tool. The gate worked as intended.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/air-to-sea-shuttles/context/comms-log.md (main clone, gitignored) | Edited | Inbound 11-16 verbatim, outbound reply (reconstructed), Nicolas decision |
| docs/2026-11-16 - Air to Sea Shuttles Reply/Checkpoint.md | Created | This checkpoint |

---

## Current Status
- Reply sent 2026-11-16. The sending address is still unknown (Zoho Mail, not reachable from here).
- Waiting for Harold to choose Wednesday or Thursday.
- Ops status: air-to-sea-shuttles has no infrastructure.yaml. That is expected for a prospect with no orchestrator.

---

## Next Steps
1. When Harold picks a time, send the calendar invite to him only, then log his reply verbatim.
2. Before the call, review his Google Business Profile and air2seashuttles.com for the one or two highest-return fixes: AI-search visibility, conversion to "inquiries and confirmed reservations", and the phone-only group quote. Also bring up the $55/$45 fare mismatch in person.
3. Prepare a prioritized, budget-sized option for the call. This prospect fits Route 1 (local site + AEO) first and automation second.

---

## Context for Next Session
### Files to Read First
- workspace/clients/air-to-sea-shuttles/context/comms-log.md

### Open Questions
- Which address the 10-30 and 11-16 mails went out from (Zoho Mail).
- Does the owner want `~/.gmail.env` fixed? Its app password is rejected.

### Working Notes
- Time math: Houston CST is UTC-6 and Germany CET is UTC+1, so the gap is 7 h (both sides are off DST in mid-November).
- Harold's stated priorities map onto UWI Route 1 (local site + AEO). Automation (booking, quoting, follow-up) is his second interest "as the business grows".

### Reference Materials
- https://air2seashuttles.com

---

## How to Continue
`/comd_resume air-to-sea-shuttles`. Wait for Harold's reply, and draft nothing further unless Matthias asks.

---

## Strategic Feedback

### What Worked Well This Session
- The 10-30 suggestion held: the first draft was send-ready, with the swaps listed under it. The phone number came from the prospect-letter memory instead of a placeholder.

### Suggestions
- Build a read-only calendar reader (iCloud CalDAV, KIT feed) in `tools/` so proposed meeting slots can be checked against lectures. Every call-scheduling draft currently ships with unchecked times.

### System Health
- stop-b1-gate blocked one closing that left the Nicolas question as a statement. Rephrasing it as an AskUserQuestion decision resolved it in one turn.
- Autonomy: 1 human intervention (the Nicolas decision).
