# Video Script -- AI Sales Chatbot Proposal Site Walkthrough

**Type:** C (Proposal Site Navigation)
**Duration:** 3 min target, 4 min hard cap
**Visual:** Browser on proposal site, camera bubble bottom-right

---

## Beat 1 -- Authority Hook + Reframe [0:00-0:30]

> Hi there, Nico here. I build AI-powered automation systems, primarily with n8n, Claude API, and Make.com.

> I put together a complete proposal site for your AI sales chatbot project. Rather than just describing what I would build, I mapped out the full architecture so you can see exactly how it works.

> The key thing about this project: most proposals you are getting will configure GHL's built-in Conversations AI. That is an FAQ bot -- it handles trained Q&A and appointment booking, but it cannot run a real sales conversation. It freezes on objections. What you actually need is an external AI brain that follows a sales flow, handles pushback, and sounds like your brand. That is what this proposal covers.

> Let me walk you through it.

**[Click: Overview page]**

---

## Beat 2 -- Site Walkthrough [0:30-2:40]

### Overview Page [0:30-0:50]

> This is the overview. Eight components, four-zone architecture, three to four week delivery.

> The four-zone diagram shows the flow: leads come in from GHL on the left, the external AI brain handles conversation intelligence in the middle, voice and multimedia on the third layer, and everything routes back to GHL for tracking and follow-ups on the right.

**[Scroll to zones, point out each column]**

> The core design decision is keeping the AI engine external. GHL is excellent for CRM, messaging, and pipelines. But the conversation intelligence -- the part that actually closes -- lives outside GHL where we have full control over the prompts, the sales playbook, and the conversation memory.

### Solution Page [0:50-1:30]

**[Click: Solution in nav]**

> The solution page maps to your eight requirements one-to-one.

> AI sales conversations: this is the external engine with a sales playbook, objection library, and conversation state machine. When a prospect says "I cannot afford it right now," the AI does not freeze -- it runs the objection handling flow from the playbook. "That makes sense. Most of our clients felt the same way before seeing the ROI breakdown. Would it help to see how others in your situation approached it?"

**[Scroll through sections]**

> Voice capabilities: ElevenLabs clones your brand voice and generates voice notes. Twilio delivers them. The AI decides when a voice note would be more effective than text -- for example, after two unanswered text messages, switch to a voice note.

> The snapshot system is section seven. GHL's snapshot captures the CRM config -- pipelines, tags, custom fields, workflows. But you also need to provision the external stack for each new client: AI engine config, voice persona, Twilio number, n8n webhook URLs. We build a provisioning script that handles both sides.

### Timeline Page [1:30-2:00]

**[Click: Timeline in nav]**

> Five phases across three to four weeks. Week one is foundation -- GHL setup, webhook infrastructure, n8n orchestration layer. Weeks one to two are the AI brain -- conversation engine, sales playbook, objection handling. Weeks two to three add voice and multimedia. Week three handles follow-ups and tracking. Week three to four is snapshot creation, testing, documentation, and handoff.

> Each phase delivers working functionality. By end of week two, you have a working AI conversation engine responding to real messages.

### Investment Page [2:00-2:20]

**[Click: Investment in nav]**

> Three thousand five hundred dollars across two milestones. This is eight major components across a three to four week build. The breakdown shows what is included in each milestone, what the monthly running costs look like, and what each new client clone costs to provision.

**[Scroll to included/excluded sections]**

> I also list what is NOT included so there are no surprises. Ongoing maintenance, additional niche adaptations beyond the first, and third-party subscription costs are separate.

### Onboarding [2:20-2:40]

**[Click: Onboarding in nav]**

> The onboarding page is a live form. Fill it out and we can start with no delays. It covers your GHL account details, current CRM structure, credit repair offer details, brand voice samples, and which integrations you already have in place. Takes about five minutes.

---

## Beat 3 -- Close + Requirements [2:40-3:10]

> So that is the full proposal. Eight components, external AI brain architecture, snapshot-ready for cloning across your clients.

> The thing that makes this different from a template bot: the AI actually follows your sales flow. It handles objections. It remembers what a prospect said two messages ago. And when a prospect buys, it stops selling and starts onboarding. That is what separates a chatbot from a sales agent.

> If this direction makes sense, the onboarding page has everything needed to get started. Happy to jump on a call first if you want to walk through your GHL setup together.

> Thanks for watching.

---

## Recording Checklist

- [ ] Proposal site loaded in browser, all pages verified
- [ ] Architecture diagrams render correctly
- [ ] Clean desktop, no personal tabs visible
- [ ] Loom: screen + camera bubble (bottom-right)
- [ ] Beat outline on sticky notes (second monitor or phone)
- [ ] Timer visible for pacing
- [ ] Opening line and close memorized
- [ ] Wing everything in Beat 2 (you know the system)
