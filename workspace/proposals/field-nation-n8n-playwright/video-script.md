# Video Script -- Field Nation n8n + Playwright

## Target Duration: 2-3 minutes

---

### BEAT 1 -- Reframe and Authority (~30 seconds)

>> Their job posting on Upwork

SAY: Hi there, Nico here. I saw your posting for an n8n plus Playwright workflow to automate Field Nation work orders.

SAY: Email comes in, business rules evaluate it, browser automation accepts or requests the job.

>> Highlight "this is a test" and "ongoing job"

SAY: The real challenge isn't connecting the pieces. It's making the automation reliable.

SAY: Field Nation sessions expire. Work orders are first-come-first-served, so any delay means a missed job. And if they update their email format, a regex parser breaks overnight.

>> My Upwork profile

SAY: Quick context. I build n8n workflows full-time, self-hosted and cloud. Playwright automation with session management is something I work with regularly.

SAY: I put together a proposal site to walk through the full architecture.

---

### BEAT 2 -- Walkthrough (~90 seconds)

>> Open proposal site, Overview page with stat cards

SAY: Here's the proposal site. Four key numbers: 5 pipeline stages, under 60 seconds from email to action, 3-day delivery, $150 fixed.

>> Nav: Solution

SAY: The solution page breaks down each stage. First, n8n's IMAP trigger watches your inbox for Field Nation emails.

SAY: Then Claude API parses the email into structured data -- job title, pay rate, location, work type. I'm recommending Claude over regex because it handles format changes without breaking.

>> Scroll to "Decision Engine"

SAY: The decision engine runs your business rules. Minimum pay rate, maximum travel distance, preferred work types. All configurable -- you edit a Google Sheet, not the workflow itself.

SAY: The output is one of four decisions: accept, request with counter-offer, skip, or flag for manual review.

>> Scroll to "Browser Automation"

SAY: Playwright handles the Field Nation interaction. It logs in with stored credentials, navigates to the work order, and executes the decision.

SAY: Sessions are persisted between runs. If Field Nation logs you out, the script detects the login page and re-authenticates automatically.

>> Nav: Workflow

SAY: The workflow page has a downloadable n8n JSON you can import right now. It includes the email trigger, Claude API parser, and decision engine. The Playwright piece gets added after onboarding since it needs your credentials.

>> Scroll to "Error Handling"

SAY: Six failure scenarios mapped out. Session expired, work order already taken, email parse failure, site downtime, VPS crashes, MFA challenges. Each one has a specific detection method and response. Nothing fails silently.

---

### BEAT 3 -- Close (~20 seconds)

>> Nav: Investment

SAY: On pricing, I'm at $150 fixed instead of the posted $120. The difference covers session recovery, race condition handling, and documentation. Three-day delivery once I have your credentials and VPS access.

>> Nav: Onboarding

SAY: The onboarding page collects everything I need to start -- Field Nation login, VPS details, and your business rules. Fill that out and I can begin on Day 1. Looking forward to hearing from you.

---

## LOOM NOTES VERSION

- Open on their job posting. "The challenge isn't wiring n8n to Playwright. It's session management, race conditions, and email format resilience."
- My profile: n8n full-time, Playwright with session management.
- Overview page: stat cards (5 stages, <60s, 3 days, $150).
- Solution page:
  - Email trigger (IMAP) + Claude API parsing (format-change resilient).
  - Decision engine: configurable rules in a Google Sheet. Accept/request/skip/manual review.
  - Playwright: session persistence, auto re-auth, race condition detection.
- Workflow page: downloadable n8n JSON, import and test now. Error handling table -- 6 scenarios covered.
- Investment: $150 fixed, $30 above posted for production-grade error handling.
- Onboarding: collects FN credentials, VPS access, business rules. Fill out to start Day 1.
