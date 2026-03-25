# Video Script -- Genius PR Proposal Site Walkthrough

**Type:** C (Proposal Site Navigation)
**Duration:** 3 min target, 4 min hard cap
**Visual:** Browser on proposal site, camera bubble bottom-right

---

## Beat 1 -- Context + Reframe [0:00-0:20]

> Hi there, Nico here. I put together a complete proposal site for your AI lead response system.

> The interesting thing about this project is that it looks like three separate workflows, but it is really one system with three entry points. Every reply from Instantly, every LinkedIn message from HeyReach, every Calendly booking, and every Fathom call -- they all converge on the same four destinations. Designing it as a unified system is what makes it reliable at scale.

> Let me walk you through it.

**[Click: Overview page]**

---

## Beat 2 -- Site Walkthrough [0:20-2:40]

### Overview Page [0:20-0:50]

> This is the overview. Three workflows, eleven integrations, AI classification, seven-day delivery.

> The three-zone diagram shows the flow: signals come in from your outbound tools on the left, Claude API classifies and routes in the middle, and everything flows out to HubSpot, Sheets, Notion, and Slack on the right.

**[Scroll to zones, point out each column]**

> The key design decision here is the shared output layer. Instead of three separate logging setups, all three workflows write to the same destinations with the same structure. That means consistent data, no duplicates, and one place to look when debugging.

### Solution Page [0:50-1:30]

**[Click: Solution in nav]**

> The solution page breaks down each workflow.

> Workflow 1, the AI Responder, is the priority. When a lead replies via Instantly or HeyReach, the webhook fires and Claude classifies the reply: HOT, WARM, COLD, or NOT INTERESTED.

> The critical part is the confidence threshold. If Claude is above 80% confident, the system auto-responds. If below 80%, it routes to manual review via Slack. That prevents embarrassing auto-replies on ambiguous messages.

**[Point to confidence threshold section]**

> For HOT leads, the auto-response includes two to three proposed meeting times and your Calendly booking link. No delay, no manual triage.

> Workflows 2 and 3 follow the same pattern: webhook in, classify or transform, write to HubSpot plus Sheets plus Slack. The Fathom workflow is especially interesting because Claude reads the full call transcript and generates structured notes with outcome classification and follow-up tasks.

### Workflow Page [1:30-1:50]

**[Click: Workflow in nav]**

> This is the architecture diagram. Three entry points on the left, the Claude intelligence layer in the middle, and the four shared outputs on the right.

> You can see the classification categories color-coded: HOT in red, WARM in orange, COLD in blue, NOT INTERESTED in gray. And the confidence bar showing the 80% threshold gate.

### Timeline + Onboarding [1:50-2:20]

**[Click: Timeline in nav]**

> Seven days, three phases. Days 1 through 3 for the AI Responder, which is your most urgent need. Days 4 and 5 for Calendly and Fathom. Days 6 and 7 for end-to-end testing with five real leads and hardening.

**[Click: Onboarding in nav]**

> The onboarding page is the day-1 kickoff checklist. Everything I need from you: API keys for each service, HubSpot Private App token, Slack channel access, classification rules for your industry. If this is filled out before we start, we hit the ground running on Day 1 with no setup delays.

### Investment [2:20-2:40]

**[Click: Investment in nav]**

> Fifteen hundred dollars fixed for all three workflows. The price reflects production-grade delivery: confidence gates, error handling, retry logic, contact deduplication, and documentation. The comparison section explains what the difference buys versus a lower-budget build.

---

## Beat 3 -- Close [2:40-3:00]

> So the proposal site, the workflow JSON, the architecture -- it is all there for you to review.

> The n8n workflow template is downloadable from the overview page. Import it into your Railway instance, plug in your API keys, and it runs. That is Workflow 1 working out of the box.

> If we work together, I would build all three as the unified system with the shared infrastructure, error handling, and the documentation. The onboarding page has everything needed to get started on Day 1.

> Thanks for your time. Happy to discuss any questions.

---

## Recording Checklist

- [ ] Proposal site loaded in browser, all pages verified
- [ ] Live demo pages load correctly (dark/light mode works)
- [ ] Clean desktop, no personal tabs visible
- [ ] Loom: screen + camera bubble (bottom-right)
- [ ] Beat outline on sticky notes (second monitor or phone)
- [ ] Timer visible for pacing
- [ ] Opening line and close memorized
- [ ] Wing everything in Beat 2 (you know the system)
