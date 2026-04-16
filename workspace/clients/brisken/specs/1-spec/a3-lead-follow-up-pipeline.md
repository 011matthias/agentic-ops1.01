---
id: a3
name: Lead Follow-Up Pipeline
type: automation
stage: spec
orchestrator: TBD
version: 0.4.0
created: 2026-03-20
updated: 2026-04-16
trigger: webhook
systems:
  - TBD-platform
  - zoho-crm
  - outlook
  - openai
last_changes: "v0.4.0 (2026-04-16, post scope-site review): HITL default reversed -- ALL first responses go through HITL by default; auto-send is an opt-in per tier later. Conversation-history lookup added to Stage 1. Contact enrichment extended to include internal CRM lookup. Classification framed as per-channel, configurable, learning. Activity logging added as requirement. Platform narrowed -- not n8n, custom multi-tenant SaaS direction."
next_steps:
  - Platform call with Dirk (scope + sequencing, custom vs Firebase)
  - Confirm scoring tier thresholds (keep current demo scale)
  - Define email templates or brief for AI drafting
  - Confirm outbound SMTP credentials (Dirk's @brisken.com)
  - Resolve mini-CRM direction (built-in vs federated) with Dirk
---

> **CONFIRMED** (2026-03-30, updated 2026-04-15)
> Dirk provided detailed process requirements (2026-03-30). Scoring/classification model refined per 2026-04-10 call + WhatsApp feedback: 4-tier classification, HITL correction, CRM abstraction, platform expansion.

# A3 -- Lead Follow-Up Pipeline

## Overview

Unified entry point for all leads arriving from A0 (LinkedIn), A1 (website), and A2 (SAP channels). Receives the normalised lead payload, scores and classifies the lead (4-tier: SPAM/Low/Medium/High), enriches contact data, logs events to CRM abstraction layer, drafts a personalised first response via AI, and routes through tier-based human review before sending.

## Trigger

Webhook endpoint -- receives POST from A0, A1, or A2 with the standard lead payload.

## Flow

```
Webhook receives standard lead payload
  -> 1. Validate required fields + conversation-history lookup
       (sender known? prior contact / customer / partner? recent threads?)
  -> 2. Deduplicate: check if lead email already logged (within 24h window)
  -> 3. Score + Classify (4-tier model, see below)
       -> SPAM: log and discard (no reply; auto-response suggested where appropriate)
       -> Low/Medium/High: continue pipeline
  -> 4. Log lead via CRM abstraction layer (CREATE_LEAD event)
  -> 5. Contact Enrichment: internal CRM lookup + external company + LinkedIn
  -> 6. AI Draft Response: generate personalised first response
       -> Response richness scales with tier (High = detailed, Low = templated)
  -> 7. HITL Gate (first response): ALL tiers route through HITL by default
       -> Dashboard queue with draft + enrichment + conversation history
       -> Reviewer approves, edits, or rejects
       -> Auto-send is opt-in per tier / score band (Phase 2 feature)
  -> 8. Send first response email via SMTP (Dirk's @brisken.com)
  -> 9. Log every event (send, draft, approval, rejection) via activity log
        + CRM abstraction (LOG_EMAIL event)
```

## Scoring and Classification (updated 2026-04-10)

### Design Principles

1. **Spam is part of scoring, not a separate pre-filter.** Every lead with a valid email gets scored. Spam = negative score, not a gate before scoring.
2. **ALL non-spam leads get a response.** Tier determines response richness, not whether a response is sent.
3. **Scoring must be configurable via data store** (not hardcoded). Weights and thresholds stored in a config table that can be updated without code changes.
4. **Per-channel classification** (2026-04-13 Dirk). Each channel has its own criteria set -- signals, weights, and thresholds are adjustable per channel rather than shared. A SAP-Store-originated lead is classified by different rules than a LinkedIn-originated one.
5. **Learning classification** (2026-04-13 Dirk). Classification rules evolve over time from human corrections -- approved / edited / rejected drafts and reviewer-flagged mis-tier events. Phase 1: log every human decision against the lead. Phase 2+: feed those back into weight adjustment. The reviewer corrections are the training signal; no ML-from-scratch.
6. **Channel context feeds into scoring** via flat bonuses (Phase 1 default -- simpler). Multipliers remain available as a config option per tenant.

### Weight Table

| Signal | Weight | Notes |
|--------|--------|-------|
| Company email domain | +3 | `@brisken.com` vs `@gmail.com` |
| Company name provided | +2 | Company field is non-empty |
| Message/comment provided (100+ chars) | +2 | Detailed inquiry shows intent |
| Job title provided | +1 | Role context |
| Phone number provided | +1 | Direct contact signal |
| Spam indicators detected | -10 | Generic pitch, suspicious patterns, known spam domains |
| Free email domain only | 0 | Baseline (not penalised, just no bonus) |

### Channel Bonuses

| Channel | Bonus | Rationale |
|---------|-------|-----------|
| SAP Store | +5 | Product inquiry = high commercial intent |
| SAP Discovery Center | +1 | Use case exploration = moderate intent |
| Website (landing page) | +0 | Baseline |
| Website (contact form) | +0 | Baseline |
| LinkedIn (specific campaign) | +1 | Targeted outreach response |
| LinkedIn (generic message) | +0 | Baseline |

> **Design decision for Dirk:** Channel bonuses (flat additive, shown above) vs channel multipliers (SAP Store 1.3x, Discovery 1.1x). Multipliers scale with base score; bonuses are fixed. Current interactive demo on scope page uses the flat bonus model. See scoring demo at solution page for live calculator.

### Tier Thresholds

| Tier | Score Range | Action | Response Richness |
|------|-------------|--------|-------------------|
| **SPAM** | Below 0 | Log and discard | None |
| **Low** | 0 -- 4 | Auto-send, no notification | Templated acknowledgement |
| **Medium** | 5 -- 9 | Auto-send + notification to reviewer | Personalised with context |
| **High** | 10+ | Hold for human review | Full personalised draft with enrichment data |

> **Design decision for Dirk:** Current scale (above) matches the live interactive demo. Alternative: larger ranges (SPAM < 0, Low 0-19, Med 20-39, High 40+) with proportionally larger weights. The demo would need rescaling. Recommend keeping current scale unless Dirk wants finer granularity.

### Example Scoring Walkthrough

**SAP Store lead, company email, detailed message:**
```
company_email: +3, company_name: +2, message(150 chars): +2, phone: +1
Base: 8
Channel bonus (SAP Store): +5
Total: 13 -> HIGH
Action: hold for human review, full personalised draft
```

**LinkedIn generic, free email, no message:**
```
free_email: +0, no company: +0, no message: +0
Base: 0
Channel bonus (LinkedIn generic): +0
Total: 0 -> LOW
Action: auto-send templated acknowledgement
```

### Scoring Config Schema (data store)

```json
{
  "tenant_id": "brisken",
  "weights": {
    "company_email": 3,
    "company_name": 2,
    "message_detailed": 2,
    "job_title": 1,
    "phone": 1,
    "spam_indicators": -10
  },
  "channel_bonuses": {
    "sap_store": 5,
    "sap_discovery": 1,
    "website_landing": 0,
    "website_contact": 0,
    "linkedin_campaign": 1,
    "linkedin_generic": 0
  },
  "thresholds": {
    "spam_below": 0,
    "low_max": 4,
    "medium_max": 9
  }
}
```

## HITL Review Gates (updated 2026-04-10)

### First Response Gate (Step 7)

> **Design update (2026-04-16, post scope-site review):** HITL is the default for all tiers. Auto-send is an opt-in the tenant admin can switch on later per tier or per score band, once trust in drafting quality is established. This reverses the earlier tier-based auto-send default.

**Phase 1 behaviour -- all tiers go through HITL:**

| Tier | Action | Notification |
|------|--------|-------------|
| High | Queue for review + full enrichment context | Dashboard + email to reviewer |
| Medium | Queue for review (lighter context) | Dashboard |
| Low | Queue for review (templated draft, quick-approve) | Dashboard |

**Phase 2 opt-in auto-send (configurable per tenant):**

| Tier | When auto-send enabled |
|------|-----|
| High | Always queue (safety) |
| Medium | Auto-send + notification |
| Low | Auto-send (no notification) |

**Review workflow:** Reviewer sees draft in unified dashboard with original message, enrichment data, conversation history, and AI draft. Can approve, edit, or reject. Approval triggers send; rejection flags the lead for manual handling. Every action (approve, edit, reject, time-to-decision) is logged and becomes training signal for the learning classifier.

### Follow-Up and Reply Gate (MANDATORY)

> **Critical correction (2026-04-10):** ALL second responses (replies from leads) trigger mandatory human review, regardless of tier. This is not score-dependent. The tool accompanies the entire process start to finish, not just the first touch.

| Event | Action | Applies to |
|-------|--------|-----------|
| Lead replies to any email | Stop follow-up sequence, route to human review | ALL tiers |
| Follow-up due (no reply) | AI drafts follow-up, Dirk approves in dashboard | ALL tiers |
| Dead lead (no engagement) | Continue nudging within reputation limits, Dirk approves each | ALL tiers |

Follow-up cadence and dead-lead policy are configurable per tenant.

## Contact Enrichment (Step 5)

Before drafting a response, gather background info on the contact. Two lookup paths run in parallel:

**Internal (built-in CRM / contact store):**
- Does this sender exist in the contact store? Classification (prior customer, partner, spammer, unknown)
- Last conversation summary and status
- Company record: open contracts, opportunities, notes

**External:**
- Company website lookup (from email domain)
- LinkedIn profile search (if name + company available)
- Optional third-party enrichment API (Clearbit, Apollo) -- Phase 2

Implementation: Code node with HTTP requests. Start with internal lookup + domain lookup; expand to LinkedIn and third-party later. Enrichment results attach to the lead record and feed the AI draft prompt.

## AI Response Drafting (Step 6)

Use OpenAI to draft a personalised first response. Response richness scales with tier:

**High tier -- full personalised draft:**
1. Acknowledge the inquiry by name and reference their specific interest
2. Reference the exact product/use case from channel context
3. Provide relevant additional information and document links
4. Ask a targeted clarifying question
5. Include enrichment context (company background, role)

**Medium tier -- personalised with context:**
1. Acknowledge the inquiry
2. Reference their interest area (may be less specific)
3. Provide general information
4. Ask an open clarifying question

**Low tier -- templated acknowledgement:**
1. Thank them for reaching out
2. Brief overview of relevant offerings
3. Invite them to share more about their needs

**AI prompt inputs:**
- Lead source, channel, and channel context (product, use case, campaign)
- Lead's message/inquiry text
- Enrichment data (company background)
- Tier (determines response depth)
- Response templates/guidelines from Brisken

**Output:** Draft email ready for review or auto-send.

## Email Architecture (confirmed 2026-04-10)

- **Outbound:** SMTP using Dirk's personal @brisken.com email credentials
- **No inbox access:** automation does NOT read Dirk's inbox
- **Reply capture:** Outlook auto-forward rule to a dedicated mailbox the system monitors (see A4)
- **Thread preservation:** In-Reply-To + References headers (RFC 5322). Always reply in-thread, even follow-ups without response, to maintain email chain
- **Follow-ups:** always individually crafted (never mass/template), aggressive for dead leads within reputation limits

## CRM Abstraction Layer

Zoho CRM is the first connector but the system defines standard events. Zoho = async event log, not operational DB. See `reference/crm-abstraction-layer.md` for full event definitions.

Events emitted by A3:
- `CREATE_LEAD` -- on first ingest (after dedup)
- `UPDATE_STATUS` -- on tier assignment, on send, on reply, on dead
- `LOG_EMAIL` -- on every email sent or received (with thread_id)
- `ADD_NOTE` -- on enrichment results, on reviewer comments

## Standard Lead Payload (input)

```json
{
  "source": "linkedin | website | sap",
  "source_detail": "campaign-name | landing-page-url | discovery-center | store",
  "channel_context": {
    "sap_channel": "discovery-center | store | null",
    "campaign_id": "string | null",
    "form_id": "string | null",
    "page_url": "string | null",
    "use_case": "string | null",
    "product": "string | null"
  },
  "first_name": "",
  "last_name": "",
  "email": "",
  "company": "",
  "job_title": "",
  "phone": "",
  "message": "",
  "submitted_at": ""
}
```

## Destination

Zoho CRM as async event log via CRM abstraction layer. Dirk works in the unified dashboard + Outlook, not in the CRM directly.

## Requirements

- Platform decision resolved (determines implementation)
- Outbound SMTP credentials (Dirk's @brisken.com)
- Email templates or guidelines for AI drafting
- OpenAI API key (for response drafting)
- Scoring config initial values confirmed by Dirk
- Zoho CRM API credentials (for async event logging)
- Activity log store (every HITL decision, every send, every reply captured -- feeds learning classifier and audit trail)
- GDPR-compliant data handling (retention, right-to-delete, data residency)

## Outstanding

- [x] ~~Platform: not n8n~~ (confirmed 2026-04-13 by Dirk)
- [ ] Platform: custom multi-tenant SaaS vs Firebase -- resolve on next call
- [x] ~~Destination system~~ -- Zoho CRM as async event log (confirmed 2026-04-10)
- [x] ~~Lead scoring model~~ -- 4-tier with numeric weights (defined 2026-04-15)
- [x] ~~HITL default~~ -- all tiers through HITL Phase 1, auto-send opt-in later (confirmed 2026-04-13)
- [x] ~~Second-response HITL~~ -- confirmed 2026-04-13
- [ ] Outbound SMTP credentials (@brisken.com)
- [ ] Email templates or brief for first response style
- [ ] Confirm scoring tier thresholds with Dirk (keep current demo scale unless pushed back)
- [ ] Mini-CRM direction: built-in contact store vs federated with external CRM (Dirk deciding)
- [ ] Enrichment API choice (start with domain lookup? Use Clearbit/Apollo?)
- [ ] Document attachments: which documents for which products/use cases?
- [ ] Zoho CRM API credentials and field mapping
- [ ] GDPR: data retention policy, right-to-delete process, residency region
