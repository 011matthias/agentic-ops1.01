# Video Script - B2B Marketing Automation Infrastructure

## Target Duration: 4-5 minutes

---

### BEAT 1 - Hook (~30s)

>> Nav: Overview

SAY: Hi there, Nico here. Soren, I read through your posting for a B2B marketing automation expert and this is right in my wheelhouse.

SAY: I build marketing automation infrastructure on Make.com and n8n. Lead capture, enrichment, scoring, nurture sequences, the full pipeline. I've managed 50+ Make.com scenarios in production and built a B2B marketing pipeline that processed over 600,000 impressions across multiple channels.

SAY: I'm in Germany, one hour behind Tallinn, so we're practically on the same clock.

---

### BEAT 2 - The Proposal (~90s)

>> Nav: Solution
>> Scroll to Platform Split

SAY: Here's what I'd build. Two platforms working together. Make.com handles the integrations: Apollo API for enrichment, CRM sync, HeyReach webhooks, email sending. n8n handles the logic: scoring algorithms, conditional routing, sequence management, retry handling.

SAY: They talk to each other via webhooks. Make.com captures a lead, normalizes it, enriches it through Apollo, then passes it to n8n for scoring and routing. Two handoffs, both logged.

>> Scroll to Integration Map

SAY: I've mapped all 14 tools from your posting. Apollo, HeyReach, LinkedIn, your CRM, Google Ads, Ahrefs, SEMrush, Comet Browser. Some are ready to wire today. Others, like Comet Browser, need a discovery conversation first because there's no public API. I've outlined three integration paths depending on how your team actually uses it.

>> Nav: Workflow
>> Scroll to Worked Example: LinkedIn Lead via HeyReach

SAY: Let me walk through a concrete example. A prospect accepts a LinkedIn connection through one of your HeyReach campaigns. That fires a webhook with their name, email, and company. Make.com normalizes it, calls Apollo for enrichment, gets back company size, industry, seniority. Then it passes the enriched record to n8n.

>> Scroll to Scoring Model

SAY: n8n runs the scoring. Engagement signals, like a connection accept, plus firmographic signals, like VP title at a 300-person SaaS company. In this example, the lead scores 65 out of 100, landing in the Warm band. That automatically starts a 5-touch nurture sequence. If she replies to any email, the sequence stops and she gets reclassified as Hot with an instant Slack alert to your team.

SAY: All the scoring weights live in a Google Sheet. You can adjust them without touching the workflows.

---

### BEAT 3 - Scope and Gaps (~30s)

>> Nav: FAQ
>> Scroll to Gap Handling

SAY: Quick note on scope. The core of what you're looking for, the automation funnels, I cover fully. For the SEO and ad management side, I integrate the data those tools produce into the pipeline. Ahrefs ranking alerts, Google Ads conversion data feeding into the scoring model. But if you need someone running ad creative or keyword strategy day-to-day, that's a separate role.

SAY: Comet Browser, I haven't used directly, but the integration depends on whether it supports webhooks or data exports. The onboarding form asks about this so I can scope the right approach before we start.

---

### BEAT 4 - Investment (~30s)

>> Nav: Investment
>> Scroll to Pricing Structure

SAY: On pricing, my rate is above your posted range, and I want to address that directly. The retainer is the right comparison: $1,500 to $2,000 a month. At 10 to 15 hours per week, that's an effective rate of $25 to $33 an hour. And the output is automation that runs independently after it's built, not just hours of labor.

SAY: If you want to test the fit first, I'm open to a smaller project. One Apollo-to-CRM pipeline, about $500 to $700, delivered in a week.

---

### BEAT 5 - Close (~15s)

>> Nav: Onboarding

SAY: Soren, the proposal site has the full details: architecture, worked examples, timeline, pricing. There's also a short onboarding form you can fill out so our first conversation is already productive.

SAY: Thanks for watching. Talk soon.

---

## LOOM NOTES VERSION

- This is right in my wheelhouse: Make.com + n8n marketing automation
- 50+ Make.com scenarios, 600K+ impressions B2B pipeline, Germany/CET
- The proposal: Make.com for integrations, n8n for logic. 14 tools mapped.
- Concrete example: LinkedIn lead via HeyReach, Apollo enrichment, scoring math (65/100 = Warm), auto-nurture, reclassify on reply
- Scoring weights in Google Sheet, fully editable
- Scope: automation funnels fully covered. SEO/ads = data integration, not day-to-day management. Comet Browser = needs discovery.
- Pricing: $1,500-2,000/mo retainer, $25-33 effective rate. Test option: $500-700.
- Close: proposal site, onboarding form
