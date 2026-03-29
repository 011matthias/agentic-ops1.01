### BEAT 1: The Insight

>> Job posting on screen briefly, then face/screen share

SAY: Elephant. Hi there, Nico here.

SAY: I read through your posting carefully, and what stood out to me is the scaling problem hiding inside your stack. You've got seven systems that all work individually. GoHighLevel handles the CRM. Retell AI handles the voice calls. n8n ties everything together. The individual tools aren't the hard part.

SAY: The hard part is what happens between them. When a GHL pipeline stage changes, that fires a webhook to n8n. n8n calls the Retell API with dynamic variables pulled from the contact record. Retell runs the call and sends back three webhook events. n8n has to filter for the right one, update the GHL contact, and trigger the SMS follow-up via Twilio. That entire chain has to work correctly for every client, and when something breaks, you need to trace it across three different systems.

SAY: That orchestration layer is n8n. And n8n is what I build every day.

SAY: Now, I want to be honest. I haven't configured GHL or Retell AI directly. But the integration patterns, the webhooks, the API calls, the event filtering, the data mapping, those are the same patterns I work with in production n8n workflows across multiple client accounts. The gap is the UI, not the architecture. And your SOP-driven onboarding model is exactly how I learn new platforms.

---

### BEAT 2: The Proposal

>> Show proposal site briefly (overview page), then back to talking

SAY: Let me walk you through how I'd actually handle this.

SAY: The biggest time sink in your operation right now is client onboarding. Cloning a GHL snapshot takes minutes. But the reconfiguration after the clone takes 3 to 4 hours, because webhook URLs, integration credentials, and custom field mappings don't carry over. Every new client needs those set up from scratch. That's where errors happen, and that's where the real cost is.

SAY: My approach is to build structured n8n workflow templates with parameterized webhook paths and credential bindings. Instead of remembering a sequence of manual steps for each client, you fill in a checklist of values and the template handles the wiring. Each setup gets faster as the templates improve.

SAY: For ongoing maintenance, your posting mentions 2 to 3 change requests per client per week. That's mostly prompt refinements when a Retell agent mishandles an edge case, workflow updates when a client changes their pipeline, and debugging when a webhook stops firing or an OAuth token expires. I handle these async with a written update per change: what was modified, why, and what to watch for. You get a changelog, not a status meeting.

SAY: The key thing is that n8n gives you execution-level visibility into every step. When something breaks, the execution log shows exactly which node failed and what data it received. I can diagnose issues from the log without asking you to reproduce anything or check anything on your end.

>> Show solution page briefly (webhook architecture table visible)

SAY: I've put together a proposal site with the full architecture breakdown. There's a webhook reference table showing all five webhooks in the system, a table showing what carries over from a GHL snapshot clone and what doesn't, and a downloadable n8n workflow template you can import right now to see the pipeline structure. The link and access code are in my cover letter.

---

### BEAT 3: Investment and Close

SAY: On pricing. I've scoped the setup at $450 per client environment. That covers the full sequence: snapshot clone, post-snapshot reconfiguration, Retell agent setup, n8n workflow creation, end-to-end testing, and documentation. Slightly above your posted rate because the scope includes structured documentation and template work that reduces cost on every subsequent setup.

SAY: For ongoing maintenance, a retainer of $350 to $500 per month per active client, depending on how many clients you're running. That covers the 2 to 3 change requests per week, proactive monitoring, and debugging. The retainer scales with your active client count. If a client churns, that cost drops. Your automation cost tracks your revenue.

SAY: Here's what I'd suggest as a starting point. One test setup in Week 1. I get your SOPs, your Loom walkthroughs, and access to GHL, n8n, and Retell. I set up one client environment end-to-end. You evaluate the output. If it meets your bar, we move to live clients. If it doesn't, you have a fully documented environment as a usable artifact, not a sunk cost.

SAY: I'm based in Germany, CET timezone, which fits your European preference. Async by default, structured updates, no surprises. Happy to start with that test setup so you can see the work before committing to anything ongoing. Thanks for watching.

---

### LOOM NOTES

- Open with "Elephant" (keyword from posting)
- Lead with integration layer insight, not the experience gap
- The bottleneck: GHL webhook -> n8n -> Retell API -> callback -> n8n -> GHL update + Twilio SMS. Seven systems, one orchestration layer.
- Honest about GHL/Retell gap: UI familiarity, not architecture. SOPs close that.
- Setup problem: snapshot clone is fast, reconfiguration is 3-4 hrs (webhooks, credentials, field mappings don't carry over)
- Solution: parameterized n8n templates, structured error handling, execution-level logging
- Maintenance: 2-3 requests/week per client. Async, written updates per change, changelog not meetings.
- Reference the site: webhook table, carries-over table, downloadable n8n template. Don't walk through it.
- Pricing: $450/setup (above posted $415, justified by documentation + template work). $350-500/mo retainer per active client.
- Close: Week 1 test setup, evaluate before committing. Germany/CET, async.
