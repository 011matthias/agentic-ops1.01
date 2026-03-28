# B2B Lead Capture Pipeline -- Blueprint Walkthrough

This document accompanies the `b2b-lead-pipeline-blueprint.json` file. Import the JSON into any Make.com account to see the scenario structure. This walkthrough explains what each module does and what you'd need to configure.

---

## Overview

5 modules in a linear flow: Webhook receives a lead, Router branches to the enrichment path, Apollo enriches the contact, JSON parser extracts the response, and an HTTP module pushes the enriched record to your CRM.

This is a starter blueprint, not the production scenario. The production version adds error handling, deduplication, logging, and the webhook to n8n for scoring. Those get built during Phase 1.

---

## Module 1: Custom Webhook

**Type:** `gateway:CustomWebHook`

**What it does:** Listens for incoming HTTP POST requests. This is the entry point for every lead.

**Expected fields:**
- `email` (required) -- the lead's email address
- `name` -- full name
- `company` -- company name
- `source` -- which channel sent this lead (e.g., "heyreach", "web_form", "apollo")

**To configure:** After importing, Make.com generates a unique webhook URL. Copy this URL and point your form handler, HeyReach webhook settings, or any other lead source at it. Each source sends a POST request with the fields above as JSON.

**To test:** Use curl or Postman to send a test payload:
```
POST {your-webhook-url}
Content-Type: application/json

{
  "email": "test@example.com",
  "name": "Test User",
  "company": "Test Corp",
  "source": "manual_test"
}
```

---

## Module 2: Router

**Type:** `builtin:BasicRouter`

**What it does:** Splits the flow into branches. Currently one branch (the enrichment path).

**Where to add branches:** In the production version, you'd add:
- A branch for already-enriched leads (skip Apollo, go straight to CRM)
- A branch for leads with missing or invalid email (route to a review queue)
- An error handler branch for API failures

**Configuration:** No configuration needed for default behavior. The single branch passes all data through.

---

## Module 3: HTTP -- Apollo Enrichment

**Type:** `http:ActionSendData`

**What it does:** Sends the lead's email to Apollo's `/v1/people/match` endpoint and gets back the full person record with company data, title, seniority, and industry.

**To configure:**
- Replace `{{parameters.apolloApiKey}}` with your actual Apollo API key
- The API key goes in the `x-api-key` header

**What comes back:** A JSON response containing:
- `person.title` -- job title
- `person.seniority` -- level (vp, director, manager, etc.)
- `person.organization.name` -- company name
- `person.organization.estimated_num_employees` -- company size
- `person.organization.industry` -- industry classification

**If it fails:**
- **404:** Apollo doesn't have this person. In the production version, an error handler flags the lead as `enrichment_status: "partial"` and routes it to manual review.
- **429:** Rate limit hit. Add a retry module with exponential backoff.
- **401:** Invalid API key. Check your key in Apollo's settings.

---

## Module 4: JSON Parser

**Type:** `json:ParseJSON`

**What it does:** Parses the raw response body from the Apollo HTTP call into structured fields that Module 5 can reference. Without this module, the Apollo response is a raw string.

**Configuration:** None needed. It reads the output of Module 3 automatically.

---

## Module 5: HTTP -- CRM Push

**Type:** `http:ActionSendData`

**What it does:** Creates a new contact in your CRM with the enriched data. The default configuration targets HubSpot's `/crm/v3/objects/contacts` endpoint.

**To configure:**
- Replace `{{parameters.hubspotToken}}` with your CRM access token
- If you use a different CRM (Pipedrive, Salesforce, etc.), change the URL and field mapping

**Field mapping (HubSpot):**
- `email` -- from the original webhook payload
- `firstname` -- from the original webhook payload
- `company` -- from Apollo enrichment
- `jobtitle` -- from Apollo enrichment
- `lead_source` -- from the original webhook payload
- `lead_score` -- set to "0" (scoring happens in n8n, not Make.com)

**If you use Pipedrive:** Change the URL to `https://api.pipedrive.com/v1/persons` and adjust field names to Pipedrive's schema (name, email, org_id, etc.).

---

## What's Intentionally Missing

This blueprint demonstrates the capture-and-enrich pattern. The production scenario adds:

1. **Deduplication** -- a CRM search module before the push to check if the email already exists. If it does, update the existing record instead of creating a duplicate.

2. **Error handling** -- error handler routes on each HTTP module. API failures get logged to a Google Sheets "errors" tab and trigger a Slack notification.

3. **Rate limit management** -- a queue module before the Apollo call that throttles requests based on your plan's API limits.

4. **Google Sheets logging** -- a module at the end that appends a row with timestamp, lead email, source, enrichment status, and action taken.

5. **Webhook to n8n** -- after CRM write, a webhook fires the enriched record to n8n for scoring and routing. The score result comes back via a return webhook.

These additions get built during Phase 1 of the engagement, configured specifically for your tools and thresholds.

---

## How to Import

1. In Make.com, go to **Scenarios**
2. Click the three-dot menu in the top right
3. Select **Import Blueprint**
4. Upload `b2b-lead-pipeline-blueprint.json`
5. The scenario appears with all 5 modules connected
6. Connect your Apollo API key and CRM token in the HTTP modules
7. Run once with test data to verify the flow

The scenario structure and routing logic are ready to go. Only the credentials need your input.
