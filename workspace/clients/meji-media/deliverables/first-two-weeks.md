# Meji Media -- First Two Weeks

A concrete walk-through of the first fortnight as the new owner. Read `handoff-package.md` first; this is the action checklist.

The order matters in the first three items (access has to land before anything else can happen). The rest are flexible; sequence them based on which signals come back from the client thread.

---

## Days 1-3: Get operational

### 1. Confirm Make.com org access

Once Gurmej confirms on the Upwork thread that he's added you to org `5473701` on `eu2.make.com`, accept the invite from your Make.com profile. Verify access with a single read-only call:

```
scenarios_list (filter: org 5473701, team 2826470)
```

You should see the four production scenarios: A0 (8841775), A1 (8804011), A2 (8804012), A3 (8804014), plus the UTIL scenario 8974201. If anything is missing or the org doesn't show, ping Gurmej one more time before doing anything else.

### 2. Set up the MCP server entry

In your local `.mcp.json`, add the entry from `handoff-package.md` Section 9. Generate your own personal Make.com API token (don't reuse Nicolas's). Once added, restart your Claude Code session and confirm the MCP appears under `make-meji-media`.

Quick smoke test, no state change:

```
executions_list scenario_id=8804014 limit=10
```

This should return recent A3 executions. All status 1 since the 2026-04-27 fix.

### 3. Get sheet view access

Jess (or Gurmej) shares the production Sheet (`1Bmm-cbnvpdmJH7w3Y-PiZz7c3Z7JC4L6-6aMZw541BM`) with your Google account. Read-only is fine. Open it, scan a few recent rows, and confirm you can see the K (stopped) and M (next_step_due) columns -- those are the two that matter when something looks off.

---

## Days 3-7: Do a health pass and a 1:1 with Nicolas

### 4. Spot-check A3 and A1 executions

Within 48 hours of having access, run two read-only checks to build your own confidence in the system:

```
executions_list scenario_id=8804014 limit=20  # A3
executions_list scenario_id=8804011 limit=20  # A1
```

Look for: A3 should have ~24 executions per 24h on the hourly schedule, all status 1, ops counts varying with how many rows are due (1 op when nothing is due, ~15 ops per row when rows drain). A1 should have one execution per inbound enquiry from A0, status 2 (because of the `developer_bcc` issue -- this is expected, not a bug, see `handoff-package.md` Section 7), ~13-14 ops per execution.

If anything is consistently off-pattern, pull Nicolas in before deciding what to do. Otherwise, you're good.

### 5. Live walkthrough call with Nicolas

30-45 minute Loom-recorded call. The doc covers what; the call is for why. Topics worth raising:

- The A3 saga in person -- "what would I have done differently" walkthrough
- The deactivated mailbox trap and where the legacy refs hide
- The Voice rules with concrete examples (pull two recent customer email screenshots and walk through what's right and wrong)
- The Instantly login situation -- what Nicolas tried, what's broken
- The four queued drafts and the per-draft decision

Save the Loom link to `walkthrough-loom.md` in this folder so you can re-watch it later or hand it off to anyone else who picks up the client.

### 6. Read three documents in this order

If you only have an hour to deepen context after the call, read in this order:

1. `context/client-brief.md` -- the People + Voice rules in full source form
2. `context/comms-log.md` -- skim from 2026-04-22 onward; that's where the recent context lives. The full log is 75 entries from 2026-02-27 forward; you don't need to read it all.
3. `docs/2026-05-02 - Meji Media A3 Fix and Deliverability Report/Checkpoint.md` -- the full A3 saga retro and current state

Everything older than 2026-04-08 is mostly settled context (build phase, go-live, template fixes). Useful background but not load-bearing for the next two weeks.

---

## Days 5-10: Decide on the four drafts and start the relationship under your name

### 7. Decide what to do with the four queued drafts

Section 10 of `handoff-package.md` walks through each. Recommended path repeated here for convenience:

- **Draft 1 (deliverability report notification)** -- Nicolas sends as-is, today
- **Draft 2 (A3 fix confirmation)** -- Nicolas sends as-is, today
- **Draft 3 (Gurmej Instantly logins)** -- skip; the credentials were already shared on 2026-04-22
- **Draft 4 (apology for missed 2026-04-22 message)** -- skip; rolled into the introduction message instead

Once Drafts 1 and 2 land and the introduction message goes out, you take over the thread. The next inbound message comes to you, not Nicolas.

### 8. First message under your name

Likely triggers:

- Gurmej confirms the Make.com org add (your "thanks, I'm in" reply)
- Jess shares sheet access (your "got it, thanks" reply)
- One of them asks a follow-up on the deliverability report
- Jess flags an operational issue with A1 or A3

Whatever the first one is, take it as your introduction-by-action. Match the Meji draft style: flat, no em dashes, sign off as "Matthias", no "Hi Gurmej" opener since the thread is in flight. The validator (`tools/lint-comms-draft.py`) runs on `context/drafts/*.md` if you want a safety net before sending.

---

## Days 10-14: Resolve the Instantly login and start the scope

### 9. Try the Instantly credentials Nicolas already received

Nicolas got the credentials from Gurmej on 2026-04-22 17:36 (the message Nicolas missed at the time). Try those first. If they work, great -- the audit can start.

If they don't work (Nicolas reported they "appear wrong" on his side), the most likely causes are: (a) transcription typo when copied out of the Upwork thread, (b) credentials expired, (c) 2FA blocking. A clean message to Gurmej:

> Hi Gurmej, on the Instantly logins from the 22nd: tried the ones you shared and they're not getting me through. Could you double-check or reset and resend? No rush, but it's the gating piece for the scope-out.
>
> Matthias

### 10. Once you're in Instantly, do the audit

When dashboard access works:

- Inventory the existing 10-11 warmed domains (Meji-owned vs inherited from previous contractor -- ask Gurmej if not obvious from the dashboard)
- Pull current campaign list and last-30-day stats (open rate, reply rate, bounce rate per campaign)
- Check sender reputation on each domain (Google Postmaster, Microsoft SNDS if accessible)
- Note whether the previous contractor's setup is still active or paused

The output is a scope-out report that gives Gurmej a path forward across the three segments he raised on 2026-04-22: Christmas DB warm re-engagement, cold outreach revival, and hen/stag DB re-engagement. Pricing structure is a follow-up conversation after the scope lands.

### 11. The deliverability report questions

If by day 14 Gurmej or Jess hasn't engaged with the three open questions in the report (volume forecast, risk appetite, Instantly coupling), a one-line nudge in the thread is appropriate. Not before -- they're entitled to read at their own pace, and the report itself said "no urgency on the path decision today." Around day 14 it's reasonable to surface that the path costings are still gated on those answers.

---

## What good looks like at end-of-week-two

- You've sent at least three messages from your account (introduction confirmation + two follow-ups or replies)
- A3 and A1 have continued running clean; you've spot-checked at least twice
- The Instantly login is either resolved (and the audit started) or has a clean ask back to Gurmej
- The four queued drafts are dispositioned -- sent, replaced, or skipped, with the comms-log updated
- `developer_bcc` cleanup decision made (do it now / bundle with next change / leave alone for now -- whichever, just decide)
- `MEMORY.md` and `CLAUDE.md` reflect Meji as your client

If any of these are stuck, surface to Nicolas. Two weeks in is not too late to hand back a piece if something feels off.

---

## What NOT to do in the first two weeks

- Don't change live scenarios. Read-only diagnostics only. The B1.5 gate exists for a reason; even a "tiny" tweak under your hand for the first time is the wrong vibe to set.
- Don't propose template rewrites unless Jess asks. The 2026-03-29 voice corrections from Gurmej are real and recent; let the system run as-is until you've seen what works.
- Don't promise volume forecasting or path costings until the three deliverability-report questions have answers. The whole point of the report's framing was decision-support, not arbitration.
- Don't delete the UTIL scenario 8974201. It's read-only against the client's DB and useful when you need a quick query.
- Don't engage Anuj unless there's a technical integration ask. He's CC'd on the thread but doesn't track day-to-day. When you do engage him, address him by name in the message so he knows it's for him.
