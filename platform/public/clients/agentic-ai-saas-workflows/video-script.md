# Video Script -- Agentic AI SaaS Workflows

## Target Duration: 3-4 minutes

---

### BEAT 1 -- Opener (~30 seconds)

>> Overview page, hero section

SAY: Hi there, Nico here. I build agentic AI workflows with n8n and Make.com. What caught my attention about your project is that you don't just need automations. You need AI agents that make real decisions: classifying tickets, deciding what to escalate, generating responses with the right context. That's a different kind of system than a basic webhook-to-CRM setup.

---

### BEAT 2 -- Three-tier walkthrough (~60 seconds)

>> Scroll to "How It Works"

SAY: So here's how I'd structure it. Three tiers of AI agents, all sharing the same classification engine.

>> "What We Build" -- Tier 0 card

SAY: Tier 0 handles the known issues. A ticket comes in, Claude classifies it with structured JSON, and if confidence is above 85%, the system auto-resolves it. Customer gets a response in under 30 seconds. No human needed.

>> Tier 1 card

SAY: Tier 1 is for the trickier ones. The AI enriches the ticket with CRM history and knowledge base context, then pushes a structured summary to Slack. Your support team sees the ticket, the classification, and a suggested response. One click to send.

>> Tier 2 card

SAY: Tier 2 catches bugs and infrastructure issues. The agent generates a structured bug report with repro steps, affected systems, and severity. Routes it directly to engineering.

---

### BEAT 3 -- Live demo (~60 seconds)

>> Nav: Workflow

SAY: Let me show you what the classification actually looks like. This is a live demo running on the proposal site.

>> Scroll to demo, click textarea

SAY: I'll paste in a sample support ticket. Hit classify, and it calls the Claude API in real time.

>> Click "Classify Ticket", wait

SAY: It comes back with category, priority, escalation tier, confidence score, and a suggested response. This one is classified as technical, P1 priority, Tier 1 for agent-assisted review because the confidence is in that middle range. The AI isn't sure enough to auto-resolve it, so it routes to a human with full context.

>> Scroll to download button

SAY: You can also download the n8n workflow that powers this. Import it into your instance and it runs.

---

### BEAT 4 -- Meta (~30 seconds)

>> Nav: Overview, scroll to "Proof of Work"

SAY: One more thing worth seeing. This proposal site itself was built by an agentic AI pipeline. Claude Code orchestrates sub-agents for each page, MCP connects to Make.com and n8n servers for live data, and a Python validator checks 47 quality rules before deployment. It's the same multi-agent pattern I'd build for your support system. Different use case, same architecture.

---

### BEAT 5 -- Close (~15 seconds)

>> Nav: Onboarding

SAY: The onboarding page has a form with everything I'd need to get started. If this direction makes sense, I can have the first agent running in Week 1.

---

## LOOM NOTES VERSION

- Overview page. "Your project needs AI agents that decide, not just automate."
- "How It Works" -- 3 zones: Triggers, AI Classification, Actions.
- "What We Build" -- 3 tiers:
  - Tier 0: auto-resolve, >85% confidence, <30s.
  - Tier 1: agent-assisted, CRM + KB enrichment, Slack summary.
  - Tier 2: engineering escalation, structured bug reports.
- Nav: Workflow. Scroll to live demo. Click "Classify Ticket" -- real Claude API call.
  - Result: category, priority, tier, confidence, suggested response.
  - Download: n8n JSON, importable.
- Nav: Overview. "Proof of Work" -- this proposal = same agentic pipeline.
- Nav: Onboarding. Form to kick off. First agent Week 1.
