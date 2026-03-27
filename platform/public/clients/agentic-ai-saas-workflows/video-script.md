# Video Script -- Agentic AI SaaS Workflows

Duration: 3-4 minutes
Format: Screen + camera bubble (Loom)

---

## BEAT 1: The real problem [0:00-0:30]

SAY: "Hi there, Nico here. I build agentic AI workflows with n8n and Make.com. What caught my attention about your project is that you don't just need automations. You need AI agents that make real decisions: classifying tickets, deciding what to escalate, generating responses with the right context. That's a different kind of system than a basic webhook-to-CRM setup."

>> Browser open on the proposal overview page (index.html). Scroll slowly past the hero section.

---

## BEAT 2: Three-tier walkthrough [0:30-1:30]

SAY: "So here's how I'd structure it. Three tiers of AI agents, all sharing the same classification engine."

>> Scroll to "How It Works" section on index.html. Point to the 3-zone diagram.

SAY: "Tier 0 handles the known issues. A ticket comes in, Claude classifies it with structured JSON, and if confidence is above 85%, the system auto-resolves it. Customer gets a response in under 30 seconds. No human needed."

>> Scroll to "What We Build" section. Point to the Tier 0 card.

SAY: "Tier 1 is for the trickier ones. The AI enriches the ticket with CRM history and knowledge base context, then pushes a structured summary to Slack. Your support team sees the ticket, the classification, and a suggested response. One click to send."

>> Point to Tier 1 card.

SAY: "Tier 2 catches bugs and infrastructure issues. The agent generates a structured bug report with repro steps, affected systems, and severity. Routes it directly to engineering."

>> Point to Tier 2 card.

---

## BEAT 3: Classify a ticket live [1:30-2:30]

SAY: "Let me show you what the classification actually looks like."

>> Navigate to workflow page. Scroll to the live demo section.

SAY: "This is a live demo running on the proposal site. I'll paste in a sample support ticket."

>> Click the textarea, show the pre-populated ticket about password reset.

SAY: "Hit classify, and it calls the Claude API in real time."

>> Click "Classify Ticket" button. Wait for result.

SAY: "It comes back with category, priority, escalation tier, confidence score, and a suggested response. This one is classified as technical, P1 priority, Tier 1 for agent-assisted review because the confidence is in that middle range. The AI isn't sure enough to auto-resolve it, so it routes to a human with full context."

>> Point to each result field as you mention it.

SAY: "You can also download the n8n workflow that powers this. Import it into your instance and it runs."

>> Scroll to the download section. Point to the download button.

---

## BEAT 4: How this proposal was built [2:30-3:00]

SAY: "One more thing worth seeing."

>> Scroll to "Proof of Work" section on the overview page.

SAY: "This proposal site itself was built by an agentic AI pipeline. Claude Code orchestrates sub-agents for each page, MCP connects to Make.com and n8n servers for live data, and a Python validator checks 47 quality rules before deployment. It's the same multi-agent pattern I'd build for your support system. Different use case, same architecture."

>> Point to the first portfolio card (Agentic Proposal Pipeline).

---

## BEAT 5: Getting started [3:00-3:15]

SAY: "The onboarding page has a form with everything I'd need to get started. If this direction makes sense, I can have the first agent running in Week 1."

>> Navigate to onboarding page. Brief scroll.

SAY: "Thanks for watching."

---

## LOOM NOTES VERSION

- Open on overview page
- "Build agentic AI workflows. Your project needs AI agents that decide, not just automate."
- 3 tiers: auto-resolve (>85% confidence), agent-assisted (Slack summary), engineering escalation (bug reports)
- DEMO: workflow page, paste ticket, classify live, show result fields
- Download: n8n JSON, importable
- META: this proposal = same agentic pipeline architecture (Claude Code, MCP, sub-agents, validator)
- CLOSE: onboarding form, first agent Week 1
