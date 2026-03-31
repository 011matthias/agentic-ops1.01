---
id: a1
name: Website Form Ingest
type: automation
stage: spec
orchestrator: n8n
version: 0.2.0
created: 2026-03-20
updated: 2026-03-30
trigger: webhook
systems:
  - website-forms
  - n8n
last_changes: "Confirmed by Dirk (2026-03-30). Multiple form types: articles, landing pages, contact form. Switched to n8n."
next_steps:
  - Confirm form tool (WordPress, Tally, Typeform, custom?)
  - Generate n8n webhook URL
  - Client configures form(s) to POST to webhook
  - Test with sample submission
---

> **CONFIRMED** (2026-03-30)
> Dirk confirmed website/landing page contact forms as an active lead channel.
> Multiple form types exist across articles, landing pages, and the main contact form.

# A1 -- Website Form Ingest

## Overview

Receives form submissions from the Brisken website via an HTTP webhook, normalises them into the standard lead schema, and forwards to the A3 follow-up pipeline.

Dirk confirmed (2026-03-30): "Web Site / Landing Page Contact Forms -- we have various articles in landing pages or also a contact form in the website. When someone is interested, they fill it out."

## Trigger

n8n Webhook node -- instant trigger on form POST.

## Flow

```
Website visitor submits contact/enquiry form
  -> Form tool POSTs JSON to n8n webhook URL
  -> n8n: parse and validate payload
  -> Transform: map form fields to standard lead schema
  -> HTTP POST to A3 webhook (unified lead pipeline)
```

## Standard Lead Schema (output)

```json
{
  "source": "website",
  "source_detail": "",
  "first_name": "",
  "last_name": "",
  "email": "",
  "company": "",
  "job_title": "",
  "phone": "",
  "message": "",
  "form_id": "",
  "page_url": "",
  "submitted_at": ""
}
```

`source_detail` distinguishes between article forms, landing page forms, and the main contact form.

## Requirements

- n8n Webhook node URL (generated after workflow is created)
- Client must configure form tool to POST to this URL on submission
- Form tool TBD: WordPress, Tally, Typeform, Gravity Forms, custom HTML, or other

## Edge Cases

- Spam/bot submissions: basic validation (email format, required fields present)
- Missing optional fields: set to empty string, not null
- Multiple form types: use `form_id` or `page_url` to distinguish source

## Outstanding

- [ ] Confirm form tool being used
- [ ] How many different forms exist across articles/landing pages/contact page?
- [ ] Can client add a webhook/integration to each form?
- [ ] Sample form payload (for field mapping)
