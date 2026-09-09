# Video Script -- AI Marketing Make.com Expert

---

### BEAT 1: Why This Is Systems Engineering

>> Their job posting

SAY: Hi there, Nico here. I saw your posting for a Make.com expert to build your autonomous marketing system.

SAY: The thing that stood out is that this isn't standard Make.com work. You're building an 8-agent architecture with Claude as the reasoning layer, and that puts this in systems engineering territory.

>> Scroll to "not a simple automation project" in the posting

SAY: You said it yourself: "not a simple automation project." And the level of detail in your posting confirms that.

SAY: Most job descriptions I see are two paragraphs. Yours has a full system architecture, a guardrail spec, and a screening question to filter out people who didn't read it.

---

### Background and Relevant Experience

>> My Upwork profile

SAY: Quick background. I run UnpauseAI. My daily work is building and maintaining Make.com scenarios with API integrations, error handling, and structured data flows.

SAY: I currently maintain 10+ production scenarios for a single client across MySQL, Google Sheets, and email systems.

>> Scroll down on Upwork profile

SAY: More directly relevant: I use Claude API in my own automation tooling. So the structured prompt, JSON response, parse, validate, error handle pipeline isn't something I'd be learning on your project. It's something I already debug regularly.

---

### BEAT 2: Site Walkthrough

>> Open proposal site index page

SAY: I put together a proposal site walking through how I'd approach this build. Let me run through the key parts.

>> Sidebar: System Architecture

SAY: Your system has three layers. Data ingestion from the ad platforms, AI reasoning through Claude, and action execution across ClickUp, Slack, Mailchimp, and WordPress. Make.com orchestrates all of it. Each layer has different failure modes, and that's what makes the error handling design critical.

---

### (Solution page)

>> Nav: Solution

SAY: The solution page covers the four hard problems I see in this project.

>> Sidebar: Claude API JSON Parsing

SAY: First, JSON parsing. Claude sometimes wraps responses in markdown fences, returns free-form text, or invents keys. Your posting calls this out specifically.

SAY: My approach is a multi-layer parser inside the scenario: strip fences, attempt parse, validate against the expected schema, and route failures to an error handler. Not in the prompt. In the scenario logic.

>> Sidebar: Structural Guardrail System

SAY: Second, guardrails. You're right that these need to be Make.com conditional modules, not prompt instructions. A prompt is a suggestion. A filter module is deterministic.

SAY: If the budget change exceeds 20%, the action doesn't fire. No reasoning involved. I've mapped out all 8 guardrails from your posting with where they sit in the scenario flow.

>> Sidebar: Multi-Client Architecture

SAY: Third, multi-client scaling. The iterator-based architecture with per-client config from Google Sheets is the right pattern.

SAY: The tricky parts are rate limiting across multiple ad platform APIs and error isolation so one client's failure doesn't cascade.

---

### (Brief page)

>> Open brief.html in browser

SAY: I also put together a project brief page. This is my read of your architecture based on what's in the posting. The 8 agents, the 3-phase autonomy model, the guardrail spec, and the KB schema.

SAY: I've flagged the things I'd want to clarify in Week 1 once I have access to your full system design doc.

---

### (Timeline page)

>> Nav: Timeline

SAY: The timeline follows your 16-week structure. Phase 1 is weeks 1 through 8, scenarios 1 through 10. Analysis and task assignment only. Phase 2 adds controlled execution with approval gates.

>> Sidebar: Phase 1: Analysis Layer (Weeks 1-8)

SAY: Each week has a clear deliverable. Week 1 is environment setup and the first data ingestion scenario. By week 4, we have the Claude API integration running with the JSON parser. Guardrails come in weeks 7 and 8. Every scenario gets tested before connecting to the next.

---

### BEAT 3: Pricing and Next Steps

>> Nav: Investment

SAY: On pricing. My rate is $35.63 per hour. For Phase 1, I estimate 120 to 160 hours, roughly $4,300 to $5,700.

>> Sidebar: Fixed-Price Alternative

SAY: I'm also offering a per-scenario fixed price as an alternative. Around $500 per scenario for Phase 1, each with a test gate before payment. That puts the delivery risk on me and aligns with your "one scenario at a time" requirement. Your call on which structure works better for you.

>> Nav: Onboarding

SAY: The onboarding page has the full checklist of what I'd need to start. Access to the system design doc, the KB template, Make.com org access, and API credentials. If this looks like a fit, I can start Week 1 as soon as those are in place.

---

## LOOM NOTES VERSION

- Open on job posting. "Not a simple automation project." 8-agent architecture, Claude API, structural guardrails. Systems engineering, not Make.com consulting.
- Profile: UnpauseAI. 10+ production Make.com scenarios. Claude API in own tooling. JSON parsing is daily work, not new territory.
- Overview page: three layers (data ingestion, AI reasoning, action execution). Architecture zone cards.
- Solution page, 4 hard problems:
  - JSON parsing: strip fences, parse, validate schema, error route. In scenario logic, not prompt.
  - Guardrails: 8 conditional modules. Prompt = suggestion. Filter = deterministic. Budget ceiling, keyword lock, delete protection, phase controls.
  - Multi-client: iterator + per-client config from Sheets. Rate limiting. Error isolation.
  - Phased autonomy: Phase 1 read-only, Phase 2 controlled execution, future Phase 3 autonomous.
- Brief page: our read of the architecture. 8 agents, 3 phases, guardrail spec, KB schema. Open questions for Week 1.
- Timeline: 16 weeks. Phase 1 weeks 1-8 (scenarios 1-10, analysis only). Phase 2 weeks 9-16 (controlled execution). Each week has a deliverable and test gate.
- Investment: $35.63/hr, Phase 1 estimate 120-160 hrs. Fixed-price alternative: ~$500/scenario. Test gate before payment.
- Onboarding: checklist. System design doc, KB template, Make.com access, API creds. Can start immediately.
