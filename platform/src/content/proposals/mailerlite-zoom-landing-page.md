---
id: p011
slug: mailerlite-zoom-landing-page
prospect: "TBD"
contact: "TBD"
source: upwork
source_url: "https://www.upwork.com/jobs/~022037573108618918227"
project_title: "MailerLite Zoom Signup Landing Page with Stripe & GDPR Compliance"
status: draft
track: 2
created: "2026-03-27"
sent: null
value_estimate: "$200 fixed"
timeline: "4 days"
tags: [mailerlite, stripe, zoom, gdpr, email-automation, landing-page]
access_code: "mailerlite-2026"
deliverables:
  letter: true
  video: true
  site: true
research:
  prospect_company: "TBD (new Upwork member, no company name in posting)"
  prospect_industry: "Education / Group coaching (Zoom sessions)"
  prospect_location: "United States"
  prospect_contact: "TBD"
  prospect_systems:
    - "MailerLite"
    - "Stripe"
    - "Zoom"
  prospect_pain_points:
    - "Needs domain authentication on MailerLite but unsure how to set it up"
    - "Wants a reusable landing page template for recurring group Zoom sessions"
    - "Needs GDPR-compliant signup with required terms checkbox, link, and popup"
    - "Requires Stripe integration for paid signups"
    - "Wants automated email delivering Zoom link after signup"
  job_language_echoes:
    - "clean, reusable landing page template"
    - "user signs up, agrees to terms, receives the Zoom link by email"
    - "required terms checkbox (link and pop-up)"
    - "GDPR compliance"
    - "Stripe integration to sign up"
  location_advantage: "EU-based, strong on GDPR compliance requirements"
  relevant_proof_points:
    - "Built GDPR compliance scanner automation for meditation app prospect"
    - "Email automation workflows for multiple clients (MailerLite, Make.com, n8n)"
    - "Stripe payment integration experience across client projects"
  budget_gap: "Client budget $150, bidding $200 -- justified by Stripe + GDPR + reusable template combination"
  profile_cherry_picks:
    - "GDPR compliance expertise (meditation app GDPR scanner proposal)"
    - "Email marketing automation (Meji Media email workflows)"
    - "Fast turnaround on platform configuration work"
---

## What We Understood

You need a complete signup flow for recurring group Zoom sessions: a clean MailerLite landing page where users sign up, agree to your terms (with a required checkbox, link to full terms, and a popup), pay through Stripe, and automatically receive the Zoom link by email. You also need domain authentication set up on MailerLite so your emails land in inboxes, not spam folders. The landing page template needs to be reusable so you can duplicate it for different Zoom sessions without rebuilding from scratch.

## Our Proposed Solution

Everything stays inside MailerLite's native toolset, which keeps it simple and maintainable:

1. **Domain Authentication** -- DKIM, SPF, and DMARC records configured at your domain registrar, verified in MailerLite
2. **Reusable Landing Page Template** -- Drag-and-drop page with your branding, saved as a reusable template. Duplicating it for a new Zoom session takes 5 minutes: swap the title, date, and Zoom link
3. **Signup Form with GDPR Consent** -- Required terms checkbox with link to your terms page and popup display. GDPR consent fields capture IP, timestamp, and subscription source automatically
4. **Stripe Payment Block** -- Native MailerLite-Stripe integration. Product created in Stripe, payment block added to the landing page. No third-party connectors needed
5. **Automated Email with Zoom Link** -- MailerLite automation triggered on form submission: sends a branded confirmation email containing the Zoom link immediately after signup

## Timeline & Milestones

- **Day 1:** Domain authentication (DNS records) + MailerLite account review
- **Day 2-3:** Landing page template + signup form + Stripe payment block + GDPR consent setup + terms popup
- **Day 4:** Email automation workflow + end-to-end testing + template duplication walkthrough + handoff

## Investment

$200 fixed price. Includes domain authentication, reusable landing page template, Stripe integration, GDPR-compliant signup form with terms popup, automated Zoom link email, Loom walkthrough showing how to duplicate the template for future sessions, and 7 days of post-delivery support for questions.

The $50 above your listed budget covers the Stripe integration and GDPR consent setup properly, which together add about 2 hours of careful configuration. This setup pays for itself after your second Zoom session since you will never need to rebuild from scratch.

## About UnpauseAI

We build email automation and marketing workflows for small businesses and agencies. MailerLite domain authentication, Stripe payment flows, and GDPR-compliant signup forms are configurations we handle regularly.
