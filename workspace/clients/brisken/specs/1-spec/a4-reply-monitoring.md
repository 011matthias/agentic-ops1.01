---
id: a4
name: Reply Monitoring and Escalation
type: automation
stage: spec
orchestrator: n8n
version: 0.1.0
created: 2026-03-30
updated: 2026-03-30
trigger: scheduled
systems:
  - gmail
  - n8n
last_changes: "Initial spec based on Dirk's requirement: second responses must be submitted to human review"
next_steps:
  - Confirm which inbox to monitor for replies
  - Define escalation channel (email, Slack, or both)
  - Confirm who handles reply review
  - Wire to A3 lead log for thread context
---

> **CONFIRMED** (2026-03-30)
> Dirk explicitly stated: "Monitor responses -- any second responses must be submitted to human review."

# A4 -- Reply Monitoring and Escalation

## Overview

Monitors the outbound email inbox for replies from leads who received an automated first response (from A3). When a lead replies, the workflow:
1. Detects the reply and matches it to the original lead
2. Stops any pending follow-up sequence for that lead
3. Routes the reply to mandatory human review (no auto-response to second messages)

This is a hard requirement from Dirk: **all second responses must go through human review**, regardless of lead quality score.

## Trigger

Scheduled -- polls inbox every 5 minutes (300 seconds). More frequent than A2 because reply timeliness matters.

## Flow

```
[Every 5 minutes]
  -> n8n: Gmail node -- search for new reply emails
  -> Match reply to original lead (by email address or thread ID)
  -> Stop pending follow-up sequence (if any scheduled in A3)
  -> Log reply in destination (Sheets / CRM)
  -> Notify reviewer: "Lead [name] replied -- human review required"
       -> Include: original lead data, first response sent, reply content
  -> Mark email as processed
```

## Reply Detection Logic

| Method | Pros | Cons |
|--------|------|------|
| Gmail thread ID matching | Exact thread context | Requires storing thread IDs from A3 sends |
| Email address matching | Simple, works across tools | May match unrelated emails from same address |
| Subject line matching | Good for RE: patterns | Fragile if subject is changed |

**Recommended:** Gmail thread ID matching (store the sent email's thread ID in the lead log when A3 sends).

## Escalation

Every detected reply triggers mandatory human review:

1. **Notification** to reviewer via email or Slack:
   - Lead name, company, source
   - Original inquiry summary
   - First response that was sent
   - Reply content
   - Link to lead in destination system (Sheets/CRM)

2. **No auto-response.** The reviewer handles the conversation from this point.

3. **SLA tracking** (optional, Phase 2): track time between reply received and human response.

## Requirements

- Gmail connection in n8n (same inbox as outbound sends from A3)
- Thread ID storage in lead destination (A3 must save sent email thread ID)
- Reviewer notification channel configured
- Reviewer identified (Dirk? Matthias? Sales team?)

## Edge Cases

- Lead replies to a different email address: won't be caught unless we monitor multiple inboxes
- Lead replies after follow-up sequence completed: still route to human review
- Out-of-office / auto-replies: filter by known auto-reply patterns, don't escalate
- Bounce notifications: log as "undeliverable", stop sequence, don't escalate as reply

## Outstanding

- [ ] Which inbox to monitor for replies?
- [ ] Escalation channel: email, Slack, or both?
- [ ] Who handles reply review? (name/role)
- [ ] Should out-of-office replies be filtered or escalated?
- [ ] SLA tracking desired? (time to human response)
