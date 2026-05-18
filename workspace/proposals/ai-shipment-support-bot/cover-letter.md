Hi there,

Short Loom walkthrough plus the full build plan: https://unpauseai.com/clients/ai-shipment-support-bot/ (access code: ai-shipment-support-bot-2026)

I built the plan around the one thing that makes a shipment bot safe: it should never invent a tracking status. So the design splits cleanly. A small model handles the judgment (which order is this, what is the customer asking, how to phrase the German reply) and your ERP supplies every fact. The tracking number, link, and carrier are read from your existing interface and dropped into the reply word for word. The model never writes a tracking number. If the ERP has no answer, the bot does not guess, it hands the message to a person with full context.

That covers both request types you listed: "Where is my shipment?" and the correction and update follow-ups on tracking. Email comes in over All-Inkl by IMAP, Amazon Message Center over the Selling Partner API, and both get the same German handling. Communication stays exclusively German by design, not as a translate toggle.

One thing most applicants will skip: Amazon Message Center has its own rules (response window, link and contact restrictions, no promotional content). The Amazon path has a separate policy filter so a reply never puts the seller account at risk. That detail is on the site.

The site includes:
- A solution page with the full grounding architecture
- A workflow page with the visual pipeline and the three paths a message can take
- A timeline page (about 2 weeks for the core phase, then the full build)
- An investment page with the language, LLM, and model reasoning you asked for
- An FAQ on accuracy, the Amazon rules, and what corrections are actually safe to automate
- An importable n8n skeleton workflow you can download

On budget: the post did not state one, so I priced by scope. The core phase is 2,500 dollars fixed, both intents working on your real email tickets before anything else is built. The full build with the Amazon channel and corrections brings it to 4,000. I work fixed-price by phase, and I am open to hourly if that fits your procurement better. You mentioned wanting a reliable long-term partner for more AI automations, and the build ships with documentation, a runbook, and a handoff so that partnership is real and not a black box.

If we move forward, the first step is a quick look at what your ERP interface returns, since that decides which corrections can be automated safely. Happy to answer anything before then.

Cheers,
Matthias
UnpauseAI
