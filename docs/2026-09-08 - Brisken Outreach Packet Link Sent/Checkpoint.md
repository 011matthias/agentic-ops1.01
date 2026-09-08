# Checkpoint: Brisken Outreach Packet Link Sent

**Date:** 2026-09-08
**Status:** The September campaign packet is in Dirk's hands; every remaining gate is his answer, not our build.

---

## Summary

A question about recent mail to Dirk turned into closing the one thing blocking the September campaign: the review-packet link mail had been staged and unsent since 2026-09-07, and the thread it answers had been open since 2026-07-25. It went out verified at 16:20:56Z after a cold drive of the link and a six-point readiness check.

---

## What Was Done This Session

### Answered from the mailbox, not the log

1. Summarized the last outbound mails to Dirk section-wise, reading Sent Items over Graph rather than trusting `comms-log.md`. The two most recent composed mails (both 2026-09-07 11:31Z) are the travel-alias announce and the company-card list ask; everything after them in Sent Items is the intake tool's automated "Receipt received:" acks, which is worth knowing before anyone reads that folder as correspondence.
2. On the follow-up about the campaign, established that nothing about outreach had reached Dirk since July: the last real sends were "Post Event Outreach" (2026-07-25) and "Rome GA follow-up: copy for your review" (2026-07-26). The September mail was staged, not sent.

### Sent the packet link (the actual unblock)

3. Cold-drove `https://brisken-lead-desk.fly.dev/review/september-2026` with no cookie first, because that is the leg that broke on 2026-09-07: 303 to `/login?next=%2Freview%2Fseptember-2026`, login form renders the hidden `next` field.
4. Sent as a Graph `createReply` on Dirk's 2026-07-25T13:00:06Z message so the thread is preserved and the recipient is inherited rather than typed. Readiness check before firing, all PASS: Dirk only, no cc, no BCC, 0 attachments, subject threads, still a draft. Verified after: Sent Items 2026-09-08T16:20:56Z, `isDraft=false`, 0 copies left in Drafts.
5. Recorded the send verbatim in `comms-log.md`, deleted the staged draft per W1 §2, updated the two status rows that still claimed "nothing sent". PR #731 merged on green CI.

### Corrected a wrong instruction from the last checkpoint

6. The 2026-09-07 next-step said `p2-outreach.md` "looks superseded by `p2-outreach-engine.md`; verify and delete". It is not superseded: `p2-outreach.md` is the AEO / LinkedIn borrowed-trust motion, `p2-outreach-engine.md` is the Lead Desk sender. Set its state to `dormant` with the reason inline instead of deleting a live workstream.

---

## Key Decisions Made

### The send was a decision to put to the owner, not an offer to leave hanging

- **Choice:** After the B1 gate blocked an open-offer closing, split the work: take the read-only half (cold-drive the link) immediately, then put the send itself as an `AskUserQuestion` with a recommendation and the full text in the preview.
- **Rationale:** Mail into a client's inbox is invasive and needs a per-action yes. But "say the word and I'll send it" hands back the judgment the owner was relying on. A decision with a stated recommendation is the shape that respects both constraints.

### Reply into the thread, not a fresh mail

- **Choice:** `createReply` on Dirk's own 2026-07-25 message rather than composing a new mail to him.
- **Rationale:** The recipient is inherited from the message rather than typed, which removes the class of error the readiness check exists to catch; and his three-directions reply is the question this mail answers, so the thread carries its own context.

### Dormant is a state, not a stale file

- **Choice:** Correct `p2-outreach.md` to `state: dormant` instead of deleting it or leaving it flagged.
- **Rationale:** All six elements are built and waiting on one human gate (Dirk's publish decision). That is dormancy, not rot; deleting it would have destroyed a real workstream's record on a prior session's mistaken read.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/context/comms-log.md` | edit | Send record + verbatim text (gitignored) |
| `workspace/clients/brisken/context/drafts/outreach-engine-plan-to-dirk.md` | delete | Sent; W1 §2 (verbatim lives in the comms log) |
| `workspace/clients/brisken/status/p2-outreach-engine.md` | edit | Link-mail row SENT; next action = read his answers (PR #731) |
| `workspace/clients/brisken/status/p2-outreach.md` | edit | State corrected to dormant with the reason inline |

---

## Current Status

The packet is seeded and reachable and now actually pointed at: 4 decisions (release mode, wave-1 week, the SAP hold, the dropped six) plus 3 wave sequences with editable copy, waves sized warm 21 ×2 / cold close-out 23 ×1 / ecosystem 18 ×1, 83 mails maximum. It has no answers yet, which is expected within hours of the mail.

The sender stays dormant: `kill_switch=1`, two send attempts in the engine's entire history, both self-tests. Nothing in this session touched a send path.

brisken platform: unknown plan, ~?/? ops/mo, last assessed unknown (`infrastructure.yaml` still carries no platform section for the fastapi orchestrator).

Status-file sweep flagged five more stale files this session, all untouched workstreams: `p2-lead-gen-general.md` (79d), `p2-onepilot-site.md` (48d), `p2-product-decks.md` (47d), `p2-rome.md` (48d), `p2-targeting.md` (48d).

---

## Next Steps

1. Read Dirk's answers off `/review/september-2026` when they land. The four decisions gate wave shape; the three sequence verdicts gate copy.
2. Build the waves from his approved wording, then run the arming session (steps 6-7) before anything can send.
3. Decide the `owner@maintainiq.com` pending access request, unapproved on a client lead system since 2026-08-03.
4. Sweep the five stale p2 status files above; most are probably dormant-not-rotten like `p2-outreach.md` turned out to be, so the fix is a state correction each, not a rewrite.
5. Assess brisken's platform/ops section in `infrastructure.yaml`, which reports unknown plan and unknown usage.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/status/p2-outreach-engine.md`
- `workspace/clients/brisken/context/lead-generation/review-packet-september-2026.json`
- `workspace/clients/brisken/context/comms-log.md` (tail: the 2026-09-08 send)

### Open Questions

- Does Dirk want the Outlook-drafts variant (staged in his Drafts, he clicks send) or the per-wave release variant (~1.5d build)? Decision one on the page.
- Release mode, wave-1 week, the SAP hold and the dropped six are all his to answer; every wave build waits on them.

### Working Notes

- **Sent Items is mostly automation now.** Between 2026-08-21 and today, 36 of the 44 mails to Dirk are `Receipt received:` acks from the intake tool. Any future "what did we send Dirk" question needs that filter or the answer is noise.
- **The `$top` cap bites on this mailbox.** A Graph scan since 2026-07-20 with `$top=80` truncates before reaching late July precisely because of those acks. Page it or narrow the window; do not read a short result as an absence.
- **The comms log was accurate this time,** but it was checked against Graph rather than trusted, and that is what surfaced the acks. Keep doing it in that order.

### Reference Materials

- `https://brisken-lead-desk.fly.dev/review/september-2026` (gated; cold drive returns 303 + `?next=`)
- PR #731, PRs #700 / #702 (packet + deep-link sign-in)

---

## How to Continue

Check whether `/review/september-2026` has answers. If it does, read the four decisions and three wave verdicts off the page and start the wave build from his wording. If it does not, the thread is his to answer and nothing on our side is blocked; pick up the stale-status sweep or the platform assessment instead.

---

## Strategic Feedback

### What Worked Well This Session

- Verifying against the mailbox before answering a "what did we send" question. It cost two tool calls and caught that the automated acks dominate Sent Items, which changes how that folder reads.
- The split-then-decide move after the B1 block: read-only half taken immediately, invasive half put as a real decision with the text in the preview. The owner answered in one turn with no back-and-forth.

### Suggestions

- The prior checkpoint shipped a next-step ("verify and delete `p2-outreach.md`") that would have destroyed a live workstream if executed literally. Next-steps that propose a deletion should carry the evidence for supersession, not the impression of it; a one-line "superseded by X because both cover Y" would have made the error visible when it was written.

### System Health

- Three of this session's four friction rows are same-day recurrences of guard-caught patterns (B1 deferral, cd-guard, heredoc). The guards are holding and costing one call each, which is the design working; the B1 one is the expensive one because it costs a whole turn.
- Autonomy: 2 human interventions (one scope clarification, one mandatory send approval).
