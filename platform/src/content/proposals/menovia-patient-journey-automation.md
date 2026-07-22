---
id: p001
slug: menovia-patient-journey-automation
prospect: Menovia
contact: ""
source: upwork
source_url: "https://www.upwork.com/jobs/~022036084367276304860"
project_title: "Patient Journey Automation"
status: draft
created: "2026-03-23"
sent: null
value_estimate: "3500-5500"
timeline: "4-7 weeks"
tags: [n8n, healthcare, crm, gdpr, automation, mollie]
phases:
  - name: "Core Patient Journey"
    weeks: "1-4"
    price: "EUR 3,500"
    items: ["CRM + intake workflow", "Booking + payment flow", "Email/SMS sequences", "End-to-end testing"]
  - name: "Compliance & Handover"
    weeks: "5-7"
    price: "EUR 2,000"
    items: ["GDPR audit + consent flows", "Intercom + Dutch content", "Documentation + training"]
---

## What We Understood

Menovia is building a digital menopause clinic and needs the operational backbone to support the full patient journey, from first enquiry through to ongoing monitoring and aftercare. The medical expertise is in place. What is missing is the automation infrastructure that connects your tools, handles communication, processes payments, and keeps everything GDPR-compliant.

You have already done the hard part: documenting your workflows in detail across 15+ chapters, selecting your preferred toolstack (Zoho CRM, n8n, Mollie, Brevo, MessageBird, Cal.com), and defining your three packages (Basic, Plus, Complete). You do not need a consultant to tell you what to build. You need an implementation partner who can take your documented workflows and turn them into a working, tested, and maintainable system.

Three things stand out from your brief:

- **GDPR is non-negotiable.** You are processing personal data of Dutch patients. Every tool must host data in the EU, every data collection point needs consent tracking, and medical data must stay exclusively in the EHR. This is not something to bolt on at the end. It needs to be built into every workflow from day one.
- **The system must run without you.** After handover, your team needs to operate and adjust the system independently. That means documentation, training, and a system that is transparent, not a black box.
- **Speed matters.** You want to launch in Q2 2026. The toolstack is largely decided, the processes are documented, and the content drafts exist. What you need is focused execution.

## Our Proposed Solution

We design around your patient's experience, not your tool list. Here is how the system works end to end:

- **Patient Intake Flow**: A screening form (Typeform or Tally) triggers an n8n workflow that creates a contact in Zoho CRM, sends a confirmation email via Brevo, and prompts the patient to book their introductory call. Every step logs back to the CRM.

- **Booking and Payment**: Cal.com handles appointment scheduling with automatic Google Meet link generation. When the patient books, n8n triggers a Mollie payment link for the deposit. Payment confirmation updates the CRM, notifies the physician, and triggers the next communication sequence. All three packages (Basic, Plus, Complete) are supported with the correct payment amounts and subscription handling.

- **Communication Sequences**: Automated email (Brevo) and SMS (MessageBird) flows handle every touchpoint: appointment reminders at 24h, 6h, and 1h before each consultation, blood kit dispatch notifications with track-and-trace, lab receipt confirmations, treatment plan invitations, monitoring appointment scheduling, and aftercare check-ins at month 1, 3, 6, and 12. All content in Dutch, using your drafts as the starting point.

- **CRM as Central Hub**: Zoho CRM serves as the single source of truth for patient status. Every touchpoint (form submission, booking, payment, email, SMS, Intercom chat) logs back to the patient record. Your team gets a dashboard showing the full patient pipeline: who is in intake, who is in testing, who is in active treatment, and who is in aftercare.

- **Intercom Integration**: Your existing Intercom instance gets connected to the CRM and n8n. Website visitors who start a chat are automatically matched to their CRM record. FAQ responses, screening chat flows, and support routing are configured. The EU workspace is set up to ensure data stays in Europe.

- **GDPR by Design**: Consent tracking is built into every data collection point. We verify EU data hosting for every tool in your stack. Data Processing Agreements are documented. Opt-in and opt-out flows work correctly in every email and SMS. A data retention policy is defined and, where possible, automated. Medical data never enters the CRM, it stays exclusively in your NEN 7510-certified EHR.

## Your Starter Template

We built a sample Patient Intake Workflow for you. It is yours to keep, regardless of whether we work together.

The template is a working n8n workflow that demonstrates the core of your intake automation:

- **Webhook trigger** receives a form submission (name, email, phone, package selection, consent checkbox)
- **Data validation** checks required fields and consent status
- **GDPR consent logging** records the consent timestamp and source before any data is stored
- **CRM contact creation** adds the patient to Zoho CRM with the correct pipeline stage
- **Confirmation email** sends a personalised welcome message via Brevo
- **Appointment reminder** schedules follow-up notifications

This is one workflow out of the 8-10 that make up the full system. We can walk you through it on a 20-minute call, no commitment, so you can see exactly how the automation works and ask questions about the broader implementation.

**GDPR Compliance Matrix for Your Toolstack:**

| Tool | EU Data Hosting | DPA Available | Consent Required | Status |
|------|----------------|---------------|-----------------|--------|
| Zoho CRM | Yes (EU data centre) | Yes | Yes (patient personal data) | Ready |
| n8n Cloud | Yes (EU option) | Yes | N/A (processor) | Ready |
| Mollie | Yes (Netherlands) | Yes | N/A (payment processor) | Ready |
| Brevo | Yes (EU servers) | Yes | Yes (marketing emails) | Ready |
| MessageBird | Yes (Netherlands) | Yes | Yes (SMS communications) | Ready |
| Cal.com | Yes (EU option) | Yes | Yes (booking data) | Ready |
| Intercom | Yes (EU workspace) | Yes | Yes (chat + support data) | Requires EU workspace setup |
| Typeform | Yes (EU option) | Yes | Yes (form submissions) | Ready |

All tools in your proposed stack support EU data hosting and provide Data Processing Agreements. No US-only services. This is a strong foundation for GDPR compliance.

## Timeline & Milestones

**Phase 1: Core Patient Journey (Weeks 1-4)**

- **Week 1:** Zoho CRM configuration (patient profiles, deal pipeline, package fields, physician dashboard), n8n instance setup, first intake workflow deployed and tested
- **Week 2:** Cal.com booking integration with Mollie payment flow, email sequences in Brevo (confirmations, reminders), SMS setup in MessageBird
- **Week 3:** Full communication sequence build-out (blood kit emails, treatment plan invitations, monitoring appointment flows, aftercare sequence), CRM dashboard refinement
- **Week 4:** End-to-end testing of the complete patient journey from intake through to aftercare, edge case handling, team walkthrough

**Phase 2: Compliance, Content and Handover (Weeks 5-7)**

- **Week 5:** GDPR compliance audit across all tools, consent flow verification, data retention policy configuration, DPA documentation
- **Week 6:** Intercom EU workspace setup with CRM integration and FAQ bot, Dutch content finalised in all email and SMS templates, EHR integration assessment and recommendations
- **Week 7:** Full technical documentation (system overview, workflow descriptions, user guide), team training session, handover package, post-launch support begins

Phase 1 delivers a fully working automation system. Phase 2 hardens it for compliance, finalises the content, and ensures your team can operate it independently. We recommend completing both, but Phase 1 is self-contained if you prefer to start there.

## Investment

**Phase 1: Core Patient Journey; EUR 3,500**
- Zoho CRM fully configured (patient profiles, pipeline, dashboards)
- 8-10 n8n workflows covering the full patient journey
- Mollie payment integration (deposits, package payments, subscriptions)
- Brevo email and MessageBird SMS automation
- Cal.com booking with automatic video link generation
- End-to-end testing of the complete patient flow

**Phase 2: Compliance, Content and Handover; EUR 2,000**
- GDPR compliance audit with consent flows and data retention
- Intercom EU workspace with CRM integration and FAQ bot
- All Dutch email and SMS content finalised in the platform
- EHR integration assessment and recommendations
- Full technical documentation and team training session
- 2 weeks of post-launch support included

**Total: EUR 5,500**

This is a fixed price per phase. Tool subscription costs (Zoho, n8n, Mollie, Brevo, Cal.com, MessageBird) are separate and paid directly by Menovia. We can advise on the most cost-effective plans for each.

For context: comparable digital infrastructure projects at Dutch agencies typically run EUR 12,000-18,000. We keep costs lower because automation infrastructure is all we do. No overhead, no account managers, no discovery workshops that bill by the hour. You bring the documented workflows, we build the system.

## About UnpauseAI

We build automation infrastructure for businesses that need their operations to run without manual intervention. Our systems are in production today, processing thousands of automated operations monthly across CRM, email, payments, and scheduling integrations. We work exclusively with n8n and Make.com, which means every workflow we build benefits from deep platform expertise, not surface-level familiarity. Based in Europe, GDPR-aware by default.
