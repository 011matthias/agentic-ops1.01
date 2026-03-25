# Video Script -- Genius PR Proposal Site Walkthrough

**Type:** C (Proposal Site Navigation)
**Duration:** 3 min target, 4 min hard cap
**Visual:** Browser on proposal site, camera bubble bottom-right

---

## Beat 1 -- Authority Hook + Reframe [0:00-0:30]

> Hi there, Nico here. I specialize in n8n webhook pipelines with AI classification -- it is what I build daily with the Claude API.

> I put together a complete proposal site for your AI response system, including a working n8n workflow you can import right now and a live demo where you can test the classification yourself.

> The interesting thing about this project is that it looks like three separate workflows, but it is really one system with three entry points. Every reply -- email, LinkedIn, call recording -- converges on the same four destinations. Designing it as a unified system is what makes it reliable at scale.

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

### Workflow Page [1:30-2:10]

**[Click: Workflow in nav]**

> This is the workflow page. At the top you can see the live demo.

**[Scroll to demo section, click into the textarea]**

> I am going to paste in a sample reply and let Claude classify it in real time.

**[Paste a sample text like "Hi, we are interested. Can we set up a call this week?", click Classify Reply]**

> And there it is -- classified as HOT with 92% confidence. The suggested response includes meeting time proposals and the Calendly link. This is the actual Claude API running live, not a simulation.

**[Scroll down to architecture diagram]**

> Below the demo is the architecture diagram. Three entry points on the left, Claude intelligence in the middle, four shared outputs on the right. The confidence bar shows the 80% threshold -- anything below that routes to manual review via Slack.

**[Scroll to download section]**

> And here is the download. The full n8n workflow JSON with color-coded zone sticky notes. Import it into your Railway instance, plug in your API keys, and it runs.

### Timeline + Onboarding [2:10-2:40]

**[Click: Timeline in nav]**

> Seven days, three phases. Days 1 through 3 for the AI Responder, which is your most urgent need. Days 4 and 5 for Calendly and Fathom. Days 6 and 7 for end-to-end testing with five real leads and hardening.

**[Click: Onboarding in nav]**

> The onboarding page is a live form -- fill it out and we can start on Day 1 with no delays. It covers which integrations you have access to, API key readiness, your Calendly link, Slack channel, and any custom classification rules. Takes about five minutes.

### Investment [2:20-2:40]

**[Click: Investment in nav]**

> Fifteen hundred dollars fixed for all three workflows. The price reflects production-grade delivery: confidence gates, error handling, retry logic, contact deduplication, and documentation. The comparison section explains what the difference buys versus a lower-budget build.

---

## Beat 3 -- Close + Requirements [2:40-3:10]

> So that is the full proposal. On your specific requirements: the workflow you just saw IS the webhook example with Claude API and HubSpot integration -- that is requirement one and two answered in one artifact. Seven-day delivery is realistic if credentials are ready on day one. The onboarding page has the full checklist so we can hit the ground running.

> If we work together, I would build all three workflows as the unified system with shared error handling, retry logic, and contact deduplication. The onboarding page has everything needed to get started.

> Thanks for watching.

---

## Recording Checklist

- [ ] Proposal site loaded in browser, all pages verified
- [ ] Live demo tested (paste sample text, verify classification returns)
- [ ] Download link works (JSON file downloads)
- [ ] Clean desktop, no personal tabs visible
- [ ] Loom: screen + camera bubble (bottom-right)
- [ ] Beat outline on sticky notes (second monitor or phone)
- [ ] Timer visible for pacing
- [ ] Opening line and close memorized
- [ ] Wing everything in Beat 2 (you know the system)
