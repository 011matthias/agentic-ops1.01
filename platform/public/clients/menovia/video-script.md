# Menovia Workflow Walkthrough - Video Script

**Format:** Loom screen recording (screen + camera bubble)
**Duration:** ~2-3 minutes
**Screen:** n8n workflow canvas (unpauseai.app.n8n.cloud)
**Embed location:** unpauseai.com/clients/menovia/workflow

---

## [0:00-0:15] Intro

**Screen:** Menovia proposal overview page (unpauseai.com/clients/menovia)

> Hi, this is Nicolas from UnpauseAI. I want to walk you through the patient intake automation we built for Menovia. This is a working workflow -- not a mockup -- and you can test it yourself right now.

---

## [0:15-0:35] The Problem

**Screen:** Still on overview page, scroll to the patient journey section

> Right now, when a new patient fills in a form on your website, someone has to manually enter that into the CRM, send a confirmation email, schedule reminders, and track consent. That is 10 minutes of manual work per patient, every time. When you are handling dozens of patients a week, that does not scale.

---

## [0:35-1:05] Workflow Overview

**Screen:** Switch to n8n canvas. Zoom out to show the full workflow with sticky notes visible.

> Here is the automation. You can see three sections: Input on the left, Data Processing in the middle, and Output on the right. The header sticky note at the top tells you exactly what this workflow does.

> The flow is left to right. A patient submits their form, we validate the data, log their GDPR consent with a timestamp, create a CRM contact in Zoho, send them a confirmation email in Dutch, and schedule a booking reminder. All of this happens in under two seconds, automatically.

---

## [1:05-2:05] Key Nodes

**Screen:** Click into each node as you describe it

> Let me show you the key nodes.

> **[Click Webhook node]** This is the entry point. Any form on your website can POST data here. Name, email, phone, package selection, and GDPR consent.

> **[Click IF node]** The validation check. If the name is empty, the email is missing, or GDPR consent is not given, the workflow stops and returns a clear error message in Dutch. No incomplete records get into your CRM.

> **[Click GDPR Consent node]** This is important. Before anything else happens, we log the consent timestamp, the source, and the version of the consent text. This is your GDPR audit trail.

> **[Click CRM node]** The contact is created in Zoho CRM on the EU endpoint. First name, last name, email, phone, package selection, and the consent details all go into the right fields. Lead status is set to New.

> **[Click Email node]** A personalised confirmation email goes out immediately in Dutch. It confirms what package they selected and tells them to expect a booking invitation.

> **[Click Reminder node]** Finally, we schedule a follow-up. If the patient has not booked within 24 hours, they get a gentle reminder. No one falls through the cracks.

---

## [2:05-2:25] Live Demo

**Screen:** Open a terminal or the workflow page, show the cURL command

> Let me show you this is real. I will send a test request right now.

> **[Run the cURL command, show the enriched JSON response]**

> You can see the response includes a full preview of the patient journey, the GDPR audit log, the CRM fields that would be created, and a data quality check. This is not just a pass-through -- it is showing you exactly what the production system does.

---

## [2:25-2:45] CTA

**Screen:** Switch to the workflow page on the proposal site

> You can download this template from the workflow page and import it directly into your own n8n instance. Replace the placeholder credentials with your Zoho and Brevo accounts, and it is ready to handle real patients.

> If you have any questions, the FAQ page covers the most common ones, or just send me a message. Thanks for watching.

---

## Recording Notes

- Keep the camera bubble in the bottom-right corner
- Use the dark theme in n8n for better contrast on recording
- Zoom into nodes when explaining them, zoom back out for transitions
- Speak at a natural pace, not rushed
- Test the cURL command before recording to make sure the webhook responds
- Total target: under 3 minutes
