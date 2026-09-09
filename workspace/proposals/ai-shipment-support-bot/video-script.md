### Opening

SAY: Hi there, Matthias here.

SAY: You asked for an AI bot that answers shipment questions for your German shop, so this is exactly how I'd build it, where it can go wrong, and where I'd push back before writing code.

>> Open the proposal site at unpauseai.com/clients/ai-shipment-support-bot

---

### Beat 1, Reframe

SAY: The way I read this, the real risk isn't building a bot that replies. It's building one that replies confidently with the wrong tracking number. A support bot that talks about shipments is only useful if it is never wrong about a shipment.

SAY: So the whole design turns on one split. The model handles judgment, which order is this and what is the customer asking. Your ERP, the system that already holds the tracking data, supplies every fact. The model never writes a tracking number, it only writes the German sentence around it.

---

### Authority

SAY: That judgment-versus-facts split is the pattern I use in production for systems where a wrong answer has a real cost. Document extraction with confidence scoring, email and marketplace automation with a safe human handoff. Every build ships with documentation, a runbook, and a handoff, so you are not dependent on me to keep it running.

SAY: It matters here because the win on this project is not a clever bot, it is a bot your customers can trust on day one.

---

### Beat 2, Structure

>> Click Solution in top nav

SAY: Here is the pipeline. Step one, ingest. Email arrives over All-Inkl by IMAP, the standard way mail clients pull email. Amazon Message Center arrives over Amazon's Selling Partner API. Both get flattened into one internal message so the rest of the flow does not care which channel it was.

SAY: Step two, understand. One small LLM call, a language model call, pulls the order reference and an intent label from a fixed set: shipment status, tracking correction, or out of scope. It returns a confidence score with every field.

SAY: Step three, ground. Plain code calls your ERP with the order reference and gets the tracking link, number, carrier, and status back. No model in this step at all.

SAY: Step four, compose. A German template carries the structure and the formal Sie tone. The facts from step three are inserted word for word. Step five, the gate. High confidence and a clean match sends automatically. Anything uncertain becomes a drafted German reply in a human queue. Nothing wrong goes out on its own.

>> Click Workflow in top nav

SAY: This page draws the same flow with the three paths a message can take: auto-resolved, drafted for a human, or escalated straight to a person.

---

### Beat 3, Edge cases and tradeoffs

>> Click FAQ in top nav

SAY: Three things I'd flag before any code.

SAY: First, Amazon Message Center is not just another inbox. Buyer-seller messaging has rules, a response window, restrictions on links and contact details, no promotional content. Send the wrong thing and it is the seller account at risk, not just one customer. So the Amazon path gets its own policy filter, and more cases there default to human review.

SAY: Second, corrections are only as automatable as your ERP allows. Reading tracking is easy. Writing a change back, like a delivery address before dispatch, is only safe if your interface exposes a controlled path for it. Where it does not, the bot acknowledges in German and hands off. Confirming that is the first onboarding step.

SAY: Third, this processes personal data, so GDPR, the EU data protection rules, shapes it. Data minimisation, a configurable retention window on the audit log, and a model setting so message content is not used for training. I build the controls, I am not pretending to be your data protection officer.

---

### Beat 4, What ships when

>> Click Timeline in top nav

SAY: The build is split on purpose. The core phase, about two weeks, gets both intents answering correct German over your email channel, grounded in the ERP, with handoff working. You judge real reply quality on real tickets before paying for the rest.

SAY: The full build, a couple more weeks, adds the Amazon channel under its policy rules, the correction write-back where your ERP allows it, and an audit view your team can read.

---

### Beat 5, Close

SAY: Pricing is on the site. Core phase is twenty-five hundred dollars fixed, the full build brings it to four thousand, and there is an optional retainer for the longer partnership you mentioned. The n8n skeleton is downloadable from the site right now if you want to see the structure.

SAY: If it is a fit, the first step is a quick look at what your ERP interface returns, because that decides what we can safely automate. Everything else is on the site. Cheers.

---

## LOOM NOTES VERSION

- Open on the proposal URL on screen.
- Reframe: real risk is a confident wrong tracking number. Judgment vs facts split.
- Authority: production pattern for high-cost-of-error systems. Docs, runbook, handoff every build.
- Solution page: ingest (IMAP + Amazon SP-API into one shape), understand (small model + confidence), ground (ERP, no model), compose (German template, facts verbatim), gate (auto vs human draft).
- Workflow page: three paths, auto-resolved, drafted, escalated.
- FAQ page, three flags: Amazon policy filter, corrections limited by ERP write access, GDPR controls (minimisation, retention, no-training).
- Timeline page: core phase ~2 weeks, full build a couple more.
- Close: $2,500 core, $4,000 full, optional retainer. n8n skeleton downloadable. First step is the ERP interface check.
- Walk pages in order via top nav: Solution, Workflow, FAQ, Timeline.
