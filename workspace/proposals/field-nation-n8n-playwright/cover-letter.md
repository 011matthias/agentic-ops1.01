# Cover Letter -- Field Nation n8n + Playwright

## Upwork Plain Text (copy-paste ready)

Hi there,

https://unpauseai.com/clients/field-nation-n8n-playwright/
(access code: fieldnation-2026)
Loom walkthrough: [will record before sending]

I put together a proposal site that breaks down exactly how I'd build this. The site includes:
- 5-stage pipeline architecture (email trigger, Claude API parsing, decision engine, Playwright automation, logging)
- downloadable n8n workflow you can import and test right now
- error handling breakdown covering session expiry, race conditions, and MFA detection
- onboarding form to collect your Field Nation credentials, VPS access, and business rules

The hard part here isn't wiring n8n to Playwright. That's a few nodes. The hard part is what happens when Field Nation logs you out mid-run, when a work order gets taken between your email notification and the accept click, or when they update their email template and your parser breaks. Those are the scenarios I've designed around.

I also looked into Field Nation's developer API (developer.fieldnation.com). Their REST endpoints cover the buyer side -- posting and managing work orders. Provider-side actions like accepting and requesting aren't exposed through the API, which confirms browser automation is the right approach here.

I build n8n workflows full-time, both self-hosted and cloud. Playwright automation with session persistence and structured error handling is a setup I work with directly.

I'm proposing $150 instead of $120. The difference covers production-grade session recovery and a documented workflow you can maintain yourself. Fixed price, 3-day delivery.

I saw this is a test with ongoing work potential. The system I'm building is modular -- adding new business rules is a spreadsheet edit, not a code change. If the test goes well, extending to new marketplaces or adding reporting takes the same architecture.

Nico
UnpauseAI
