# Uplifted Consulting - Automation Workflows

Specifications for Uplifted Consulting automations. This document is the source of truth.

---

## A1: Positive Reply Notifier

**Status:** In Progress
**Trigger:** Webhook from Smartlead (EMAIL_REPLY)
**Systems:** Smartlead, OpenRouter, Slack

### Problem

Manual monitoring of email replies to identify interested prospects.

### Solution

Auto-classify replies using AI and notify Slack for positive responses.

### Flow

1. Receive webhook from Smartlead (email reply)
2. Extract reply text and lead context
3. Send to OpenRouter for classification (Positive/Not Positive)
4. If Positive: send rich notification to Slack
5. Log result to dashboard

### Acceptance Criteria

- [ ] Webhook receives and parses Smartlead payload
- [ ] AI correctly classifies positive vs not positive
- [ ] Slack notification includes: lead info, reply preview, AI reasoning, confidence, inbox link
- [ ] Dashboard shows all processed replies with classification
