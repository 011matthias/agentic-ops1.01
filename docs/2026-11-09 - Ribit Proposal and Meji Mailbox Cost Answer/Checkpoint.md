# Checkpoint: Ribit Proposal and Meji Mailbox Cost Answer

**Date:** 2026-11-09
**Status:** Ribit proposal shipped (PRs #1734, #1735), waiting on the owner to submit. Gurmej reply drafted in chat, not sent.

---

## Summary

Wrote a no-video Upwork proposal for Ribit (automotive AI, cold email to dealer principals, $200 per held appointment plus a $600 advance) with a new one-page dealer launch plan PDF. Then answered Gurmej's question on how many Meji sending mailboxes to keep: keep the three mejievent.com senders plus his own address, drop 12. The answer comes from a live, read-only Instantly inventory.

---

## What Was Done This Session

### Ribit proposal (platform / Upwork)
1. `dealer-launch-plan.html` with six sections (what you pay for, who we write to, list source including CASL, sending setup, 30-day timeline, weekly report), rendered with headless Chrome to `dealer-launch-plan-2026-11-05.pdf`. One page; content bottom at 821 of 842 pt, checked with pymupdf.
2. `cover-letter.md`: a 225-char opening, answers to the posting's five asks in order, and a sources note. Second attachment: the existing `outbound-case-study.pdf`.
3. Price set by the owner: $200 per held appointment plus a $600 advance, chosen over $250 with no advance and $150 with the same advance. Merged in #1734 and #1735.

### Meji: mailbox cost question (Gurmej, 2026-11-08 16:37 CET)
1. Live read-only Instantly inventory (`/accounts` and `/campaigns`, paged) found 16 accounts, all Google, all status 1, across seven domains:
   - mejimedia.com: 1, Gurmej's own address
   - mejievent.com: 3, the corporate senders
   - mejixmas.com: 2
   - mejimedia.co: 3, domain is NXDOMAIN, warmup -1
   - mejiai.com: 3
   - banterexp.com: 3
   - christmasofficeparty.co.uk: 1, `bookings@`, never used in a campaign
2. The plan is Hypergrowth (`pid_hg_v2`). Growth costs $47 a month and still warms every mailbox, but holds only 1,000 contacts; the workspace held 10,544 leads on 10-27.
3. Comms-log entry added with his message verbatim, the inventory, and the note "answer drafted in chat, NOT sent". `last_contact` set to 2026-11-08.
4. `status/ops-radar.md` set to `paused`, since Gurmej's 2026-10-30 message asks to stop all work after that week.

---

## Key Decisions Made

### Ribit pricing
- **Choice:** $200 per qualified appointment held, plus a $600 advance that covers the first three appointments and the warm-up weeks.
- **Rationale:** the advance pays for the 2 to 3 weeks of warm-up that per-appointment pricing otherwise leaves unpaid; the owner picked it through AskUserQuestion.

### Gurmej reply scope
- **Choice:** say which mailboxes to keep and which to drop; leave out where to cancel them and any offer to do the cleanup.
- **Rationale:** who bills the nine 2025-era mailboxes (his own Workspace or a reseller) can't be read through the API. He stopped the engagement on 10-30, so offering the export work would read as pitching paid work.

---

## What Did NOT Work (and why)

- **Python `urllib` against the Instantly API with its default User-Agent:** HTTP 403 from Cloudflare on a valid key. An explicit `User-Agent` header fixes it (added to `reference_instantly_api_semantics.md`).
- **Inline `curl .../workspaces/current` with the key pulled through `cut -d=`:** `instantly-invasive-gate` read `cut -d=` as curl's implicit-POST `-d` flag and asked for permission on a read-only GET.
- **Stop-event pattern rule to catch paste-ready text handed over as a file path:** not viable. The stop arm strips fenced and backticked code before it matches, so it can't tell a message with the fence from one without it. The rule was created, tested (false match on the quiet case) and deleted.
- **First render of the launch plan:** overflowed, and the `.page` `overflow:hidden` clipped the weekly report and the footer. Fixed by tightening the copy, not by shrinking type.
- **Heredoc with a Python triple-quoted block:** blocked by `heredoc-size-gate` (already on the Meji WHAT NOT TO RETRY list). Used Edit instead.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/proposals/ribit-dealer-cold-email/dealer-launch-plan.html` + `-2026-11-05.pdf` | created (#1734) | Attachment 1 |
| `workspace/proposals/ribit-dealer-cold-email/cover-letter.md` | created (#1734), price note (#1735) | Letter + sources |
| `workspace/clients/meji-media/context/comms-log.md` | edited (gitignored) | 2026-11-08 inbound entry, `last_contact` |
| `workspace/clients/meji-media/status/ops-radar.md` | edited | state `paused` per the 10-30 stop |
| memory `feedback_prompts_are_pasteable_text.md`, `MEMORY.md` | edited | Rule extended to cover letters and client replies |
| memory `reference_instantly_api_semantics.md` | edited | User-Agent 403 gotcha |

---

## Current Status

- **Ribit:** the letter text has been handed over. Attachments are on main and in the `agentic-ops1-ribit` worktree. Not yet submitted on Upwork, as far as this session knows.
- **Meji:** the reply to Gurmej is in chat and unsent. Nothing changed in Instantly. The November corporate campaign `da3b2966` is paused with 172 leads waiting for touch 2, runs on the three mejievent.com senders the reply says to keep, and has not been mentioned to Gurmej. Engagement stopped by the client on 2026-10-30.
- **Meji ops status:** no `platform` section in `infrastructure.yaml`.

---

## Next Steps

1. Owner: paste the Gurmej reply into the Upwork thread (it is in this session's last reply) and decide whether to mention the paused November wave.
2. Owner: submit the Ribit proposal with `dealer-launch-plan-2026-11-05.pdf` and `outbound-case-study.pdf`. Then `git worktree remove ../agentic-ops1-ribit`.
3. Narrow `instantly-invasive-gate.py`'s `-d`/`--data` arm to the curl segment of a pipeline, with a `cut -d=` negative case in `tools/tests/test_instantly_invasive_gate.py` (sys/ branch).
4. Compact `MEMORY.md`: 194 lines against the 200-line read limit, target under 140.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/comms-log.md` (2026-11-08 entry)
- `workspace/proposals/ribit-dealer-cold-email/cover-letter.md`

### Open Questions
- Do the nine October-2025 Meji mailboxes (mejievent, mejiai, banterexp, mejimedia.co) bill through Gurmej's Google Workspace or through a mailbox reseller?
- If Gurmej drops to the Growth plan, who exports and clears the 10,544 stored leads, given the engagement is stopped?

### Working Notes
- Inventory script: `meji_accounts.py` in this session's scratchpad (pages `/accounts` and `/campaigns`, maps `email_list` to campaigns). Read-only; needs an explicit User-Agent.
- Instantly pricing, read 2026-11-09: Growth $47/mo ($37.6 annual) for 1,000 contacts and 5,000 emails/mo, unlimited accounts and warmup; Hypergrowth $107/mo ($85.58 annual) for 25,000 contacts and 125,000 emails/mo.

### Reference Materials
- https://instantly.ai/pricing
- CRTC Compliance and Enforcement Decision 2016-428 (CASL conspicuous publication)

---

## How to Continue

`/comd_resume meji-media` if Gurmej replies. For Ribit, nothing is pending on our side until the client responds.

---

## Strategic Feedback

### What Worked Well This Session
- The Gurmej answer was built from a live inventory, not from memory. The NXDOMAIN check on mejimedia.co turned "maybe drop" into "can't send at all", and that is the line that makes three of the twelve cuts obvious to him.

### Suggestions
- The paste-ready-text miss has now happened twice in eleven days (air-to-sea 10-30, Ribit 11-09). A pattern rule can't see it, so the structural fix belongs in `stop-b1-gate.py` itself, which reads the raw text before stripping: flag a closing message that names a `cover-letter`, `video-script` or `drafts/` path and contains no fenced block.

### System Health
- `instantly-invasive-gate` false-fired on a read-only GET (`cut -d=` read as curl `-d`). The highest-blast-radius gate stays trustworthy only while its asks stay rare.
- Autonomy: 3 human interventions (Ribit price decision, the permission prompt from the gate's false positive, "hand me the cover letter").
