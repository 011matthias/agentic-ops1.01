Video Script -- Agentic AI SaaS Workflows
Duration: 3-4 minutes
Format: Screen + camera bubble (Loom)
Site: unpauseai.com/clients/agentic-ai-saas-workflows/ (access code: agentic-2026)


BEAT 1: The real problem [0:00-0:30]

SAY: "Hi there, Nico here. I build agentic AI workflows with n8n and Make.com. What caught my attention about your project is that you don't just need automations. You need AI agents that make real decisions: classifying tickets, deciding what to escalate, generating responses with the right context. That's a different kind of system than a basic webhook-to-CRM setup."

>> Browser on the Overview page. Scroll past the hero ("Agentic AI Support & Escalation System").


BEAT 2: Three-tier walkthrough [0:30-1:30]

SAY: "So here's how I'd structure it. Three tiers of AI agents, all sharing the same classification engine."

>> Scroll to "How It Works" heading. Point to the 3-zone diagram (Triggers In / AI Classification / Actions Out).

SAY: "Tier 0 handles the known issues. A ticket comes in, Claude classifies it with structured JSON, and if confidence is above 85%, the system auto-resolves it. Customer gets a response in under 30 seconds. No human needed."

>> Scroll to "What We Build" heading. Point to the "Tier 0: Auto-Resolver" card.

SAY: "Tier 1 is for the trickier ones. The AI enriches the ticket with CRM history and knowledge base context, then pushes a structured summary to Slack. Your support team sees the ticket, the classification, and a suggested response. One click to send."

>> Point to "Tier 1: Agent-Assisted" card.

SAY: "Tier 2 catches bugs and infrastructure issues. The agent generates a structured bug report with repro steps, affected systems, and severity. Routes it directly to engineering."

>> Point to "Tier 2: Engineering Escalation" card.


BEAT 3: Classify a ticket live [1:30-2:30]

SAY: "Let me show you what the classification actually looks like."

>> Click "Workflow" in the top nav. Page loads the Architecture & Demo page.

SAY: "This is a live demo running on the proposal site. I'll paste in a sample support ticket."

>> Scroll to "Live Demo: Support Ticket Classifier" heading. Click the textarea (pre-populated with password reset ticket).

SAY: "Hit classify, and it calls the Claude API in real time."

>> Click "Classify Ticket" button. Wait for the result card to appear.

SAY: "It comes back with category, priority, escalation tier, confidence score, and a suggested response. This one is classified as technical, P1 priority, Tier 1 for agent-assisted review because the confidence is in that middle range. The AI isn't sure enough to auto-resolve it, so it routes to a human with full context."

>> Point to each result field as you mention it.

SAY: "You can also download the n8n workflow that powers this. Import it into your instance and it runs."

>> Scroll to "Download Starter Workflow" heading. Point to the download button.


BEAT 4: How this proposal was built [2:30-3:00]

SAY: "One more thing worth seeing."

>> Click "Overview" in the top nav to go back. Scroll to "Proof of Work" heading.

SAY: "This proposal site itself was built by an agentic AI pipeline. Claude Code orchestrates sub-agents for each page, MCP connects to Make.com and n8n servers for live data, and a Python validator checks 47 quality rules before deployment. It's the same multi-agent pattern I'd build for your support system. Different use case, same architecture."

>> Point to the first portfolio card ("Proposal Pipeline (This System)").


BEAT 5: Getting started [3:00-3:15]

SAY: "The onboarding page has a form with everything I'd need to get started. If this direction makes sense, I can have the first agent running in Week 1."

>> Click "Onboarding" in the top nav. Brief scroll past the form fields.

SAY: "Thanks for watching."


========================================
LOOM NOTES (paste into Loom notes panel)
========================================

Open on Overview page (unpauseai.com/clients/agentic-ai-saas-workflows/)

Your project needs AI agents that decide, not just automate. That's a different system.

Scroll to "How It Works" -- 3 zones: Triggers, AI Classification, Actions
Scroll to "What We Build" -- 3 tiers:
  Tier 0: auto-resolve, >85% confidence, <30s response
  Tier 1: agent-assisted, CRM + KB enrichment, Slack summary
  Tier 2: engineering escalation, structured bug reports

Click "Workflow" nav -- go to live demo
Scroll to "Live Demo: Support Ticket Classifier"
Click "Classify Ticket" -- real Claude API call
Result: category, priority, tier, confidence, suggested response
Scroll to "Download Starter Workflow" -- importable n8n JSON

Click "Overview" nav -- scroll to "Proof of Work"
This proposal = same agentic pipeline (Claude Code, MCP, sub-agents, validator)

Click "Onboarding" nav -- form to kick off project
First agent running in Week 1
