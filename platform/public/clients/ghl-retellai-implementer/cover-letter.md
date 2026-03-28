Elephant.

https://unpauseai.com/clients/ghl-retellai-implementer/
(access code: ghl-retellai-2026)
Loom walkthrough: (attached below)

I put together a proposal site that breaks down how I'd fit into your stack. The site covers:
- How n8n orchestrates the data flow between GHL, Retell AI, Supabase, and Twilio
- The post-snapshot reconfiguration problem (webhook URLs, credentials, integrations that don't carry over)
- A downloadable n8n workflow template for the GHL-to-Retell call pipeline
- Onboarding checklist for what I'd need to do a test setup on one client

Here's why I think this works despite not having direct GHL or Retell AI experience yet: the hard part of your stack isn't configuring individual tools. It's the integration layer between them. When a GHL pipeline stage changes, that fires a webhook to n8n. n8n calls the Retell API with dynamic variables (client name, services, availability). Retell sends back three webhook events per call, and you need an IF node filtering for call_analyzed before updating the GHL contact and triggering the SMS sequence. That orchestration layer is n8n, and that's where I live.

I run production n8n workflows across multiple client accounts with Supabase, Airtable, and webhook integrations. I also maintain 50+ Make.com scenarios with structured error handling and monitoring. Your SOP-driven onboarding model is exactly how I learn new platforms, and I build with AI dev tools daily (Cursor, Claude Code), which maps directly to your workflow.

I'm based in Germany (CET), which fits your European timezone preference. English and German are both native. Async communication is how I work by default. I execute cleanly and flag blockers early.

Happy to do a test setup on one client environment so you can see how I work before committing to anything ongoing.

Cheers,
Nico
UnpauseAI
