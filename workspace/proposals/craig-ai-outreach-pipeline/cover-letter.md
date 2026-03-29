# Cover Letter -- AI Outreach Pipeline

## Upwork Plain Text (copy-paste ready)

Hi Craig, I built a full proposal site for your outreach pipeline:
https://unpauseai.com/clients/craig-ai-outreach-pipeline/ (access code: craig-aop)

I also recorded a walkthrough:
[LOOM LINK HERE]

The site includes:
- full solution breakdown covering all 4 components (CRM lead pull, Claude research engine, message generation, delivery + dashboard)
- a live demo where you paste a company URL and see Claude research the prospect and draft a personalized message
- timeline with day-by-day breakdown (2-3 weeks)
- investment ($3,500 phased across 2 milestones) and onboarding checklist

The core idea: rather than template-blasting, Claude researches each prospect's website and business before writing anything. The output reads like you spent 10 minutes looking at their site, because Claude actually did.

On your specific requirements:

1) CRM pipeline to pull leads: webhook trigger from your CRM (HubSpot, GoHighLevel, or whatever you use). New lead enters a pipeline stage, webhook fires, research starts automatically.

2) Research and personalized messaging: Claude API scrapes the prospect's site, analyzes their industry, services, and pain points, then drafts an outreach message referencing specific details from their business. Not a template with merge fields.

3) Email/LinkedIn integration: email sends via Instantly, Smartlead, or SMTP. LinkedIn messages are queued for manual send or Dripify automation (see note below).

4) Dashboard to review and track: approval queue where you see the draft alongside the research summary. One-click approve. Activity log tracks every touchpoint per lead.

One honest note: LinkedIn does not have a reliable API for direct message sending. Two options: Dripify Pro ($59/month) has webhook support we can integrate, or we queue LinkedIn messages as tasks for you to send manually. Most people start with option 2 and add Dripify later if the volume justifies it.

The system runs on n8n (open source, self-hosted). No per-execution costs, no vendor lock-in. You own the workflows and can export them anytime.

If this direction makes sense, the onboarding page on the site has everything needed to start Day 1. Happy to jump on a call to walk through your CRM setup first if that is more useful.

Best,
Nico
