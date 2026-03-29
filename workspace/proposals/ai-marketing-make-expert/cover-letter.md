# Cover Letter

## Upwork Plain Text (copy-paste ready)

10+. Hi there, Nico here.
https://unpauseai.com/clients/ai-marketing-make-expert/ (access code: aimarketing-2026)
Video walkthrough: [LOOM_LINK]

That number is how many Make.com scenarios I've built with Claude or OpenAI API calls baked in, including JSON response parsing, error routing, and retry logic.

What caught my attention about this posting is that you've already done the hard thinking. A 1,300-paragraph system design doc with week-by-week technical notes tells me you know exactly what you want built. That changes the dynamic completely. I'm not here to architect your system for you. I'm here to implement it reliably, one scenario at a time, with test gates between each.

The three things I want to call out from your posting:

1) Claude API JSON parsing. I've dealt with this exact problem. Claude wraps responses in markdown fences, returns conversational text when you need structured data, and occasionally invents keys that aren't in your schema. The fix is a multi-layer parser: strip fences, attempt parse, validate schema, and route to an error handler on failure. Not in the prompt. In the scenario logic.

2) Guardrails as Make.com conditionals, not prompt instructions. This is the right call. Prompts are suggestions. A Make.com filter module between Claude's output and the write operation is deterministic. Budget ceiling at 20%, keyword locks, delete protection. If the filter doesn't pass, the action doesn't fire. No reasoning involved.

3) One scenario at a time, testing before connecting. This is exactly how I work. Each scenario gets built, tested with real data from the KB, and documented (env vars, webhook URLs, blueprint export) before I touch the next one.

What I've built that's relevant:

I maintain 10+ production Make.com scenarios for a single client, orchestrating MySQL, Google Sheets, email, and webhook integrations across multiple systems. That project taught me what breaks at scale: rate limits, silent JSON failures, error handlers that don't actually catch errors, and scenarios that work in testing but fail with real data volumes.

I also use Claude API in my own automation tooling, so the structured prompt + JSON response + error handling pipeline isn't theoretical for me. It's something I debug regularly.

On pricing:

My hourly rate is $35.63/hr. For Phase 1 (10 scenarios, weeks 1-8), I estimate 120-160 hours, which comes out to roughly $4,300-5,700.

If you'd prefer to cap risk, I can also do this per-scenario: ~$500/scenario for Phase 1, ~$600/scenario for Phase 2. Each scenario has a test gate before payment. That way you're only paying for scenarios that actually pass their acceptance criteria.

The proposal site includes:
- Technical deep-dive on JSON parsing, guardrails, and multi-client architecture
- Week-by-week build plan mapped to your scenario sequence
- Both pricing models with comparison table
- FAQ covering rate limits, phase transitions, and guardrail configuration
- Onboarding checklist for what I'd need to start Week 1
- Project brief showing how I've read and understood your architecture

Cheers,
Nico
UnpauseAI
