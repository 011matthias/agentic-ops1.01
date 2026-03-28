### BEAT 1: The Integration Layer

>> Their Upwork job posting on screen

SAY: Hi there, Nico here. I saw your posting for a GHL and Retell AI technical implementer.

SAY: I want to be upfront: I haven't worked with GoHighLevel or Retell AI directly. But here's what caught my attention about your stack.

SAY: The bottleneck in scaling client setups isn't configuring individual tools. It's the integration layer between them. When a GHL pipeline stage changes, that fires a webhook to n8n. n8n calls the Retell API with dynamic variables. Retell sends back three webhook events per call. n8n filters for call_analyzed, updates the GHL contact, and triggers the SMS follow-up via Twilio.

SAY: That orchestration layer is n8n. And that's where I'm strongest.

---

### Authority

>> Show Upwork profile

SAY: Quick context. I'm based in Germany, CET timezone, which fits your European preference. English and German are both native.
SAY: I build and maintain production n8n workflows across multiple client accounts with Supabase, Airtable, and webhook integrations. I also manage 50+ Make.com scenarios with structured error handling and monitoring.

---

### BEAT 2: Site Walkthrough

>> Nav: Overview

SAY: I put together a proposal site to walk through how I'd fit into your stack. Let me run through the key parts.

>> Sidebar: Your Stack, As I Understand It

SAY: On the overview page, I've mapped your seven systems into four zones. GoHighLevel handles CRM and pipelines. Retell AI and ElevenLabs handle the voice agents. n8n is the automation backbone connecting everything. And Supabase, Airtable, and Twilio fill in the data and messaging layers.

---

### (Solution page)

>> Nav: Solution

SAY: The solution page walks through the full architecture: the data flow from GHL to Retell and back, a webhook reference table, client onboarding, and what ongoing maintenance looks like week to week.

>> Sidebar: The Data Flow

SAY: The data flow section traces the full loop. GHL pipeline event fires a webhook to n8n. n8n validates and routes by stage. For qualified leads, it calls the Retell API with client-specific dynamic variables like the client name, available services, and appointment slots.

SAY: After the call, Retell sends three webhook events back to n8n. The key one is call_analyzed, which has the transcript and outcome. An IF node filters for that event, then n8n updates the GHL contact record and triggers follow-up actions.

>> Sidebar: Client Onboarding Flow

SAY: The onboarding section covers the snapshot-to-live process. Cloning the master GHL snapshot is the easy part. The manual work is what comes after: webhook URLs don't carry over, integrations need re-auth, and credential mappings need updating. That's 3-4 hours per client right now.

SAY: I've mapped out each reconfiguration step and where n8n templates can reduce that time.

>> Sidebar: n8n Workflow Template

SAY: There's also a downloadable n8n workflow you can import right now. It includes the GHL webhook trigger, the pipeline stage filter, the Retell API call with dynamic variables, the callback webhook receiver, the call_analyzed filter, and the GHL contact update. Sticky notes explain each zone.

---

### (Timeline and Investment)

>> Nav: Timeline

SAY: The timeline has three phases.

>> Sidebar: Phase 1: Test Setup

SAY: Phase 1 is a test setup in Week 1. I get your SOPs, your Loom walkthroughs, and access to your tools. I set up one client environment end-to-end so you can evaluate my work before committing to anything ongoing.

>> Nav: Investment

SAY: On pricing, I'm matching the posted $415 per client setup. The monthly retainer covers ongoing maintenance, 2-3 change requests per week per client, monitoring, and debugging. Post-go-live support is included, not time-limited.

>> Sidebar: Comparison

SAY: There's a comparison table showing the per-setup plus retainer model against hiring full-time or billing hourly. The short version: you only pay for active clients, and if a client churns, the retainer adjusts.

---

### BEAT 3: Close

>> Nav: Onboarding

SAY: The onboarding page collects everything I'd need for the test setup. Platform access, SOPs, your master snapshot details, and the first client to set up.

SAY: Your posting says you want someone reliable, self-sufficient, and who executes cleanly and flags blockers early. That's how I work. Async by default, structured updates, no surprises.

SAY: Happy to start with the test setup so you can see the output before committing. Thanks for watching.

---

### LOOM NOTES VERSION

- Open job posting. "The bottleneck isn't individual tools. It's the integration layer between GHL, Retell, and n8n."
- Upfront: no direct GHL/Retell experience, but the orchestration layer (n8n) is my primary platform.
- Profile: Germany/CET, native English/German. Production n8n, 50+ Make.com scenarios.
- Overview page: 4 zones mapping their 7 systems. GHL (CRM/pipelines), Retell+ElevenLabs (voice), n8n (backbone), Supabase+Airtable+Twilio (data/messaging).
- Solution page, 5 sections:
  - Data flow: GHL webhook to n8n, Retell API call with dynamic vars, 3 callback events, IF filter for call_analyzed, GHL update.
  - Webhook architecture: table of all 5 webhooks (source, destination, payload, constraints). Retell 10s timeout / 3 retries.
  - Client onboarding: snapshot clone is fast, post-snapshot reconfiguration is the pain (webhook URLs, credentials, integrations). 3-4 hrs/client. Carries-over table.
  - Ongoing maintenance: 4 sub-sections (prompt refinements, workflow updates, GHL adjustments, debugging). Typical week callout.
  - Downloadable n8n workflow template: full pipeline with sticky notes.
- Timeline: Phase 1 (Week 1 test setup), Phase 2 (first live clients), Phase 3 (ongoing ops).
- Investment: $415/setup, monthly retainer per active client. Comparison table. Post-go-live support included.
- Onboarding: collects platform access, SOPs, snapshot details, first client info.
- Close: "Execute cleanly, flag blockers early." Test setup before committing.
