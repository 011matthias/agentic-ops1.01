# Platform Roadmap

Last aligned: 2026-03-20

## Vision

Two distinct experiences:
1. **Public website** — Normal automation agency site. Showcases services, sells automations, handles proposals. Entry point for leads.
2. **Client portal** — The agentic automation platform. Where clients track live automations, get resources, communicate.

## Prospect Channels

- **Inbound:** Traffic → public site → interested → requests proposal → becomes client → portal activated
- **Outbound:** Hunt prospects (Upwork, direct outreach) → build their setup (proposal page, pitch) → sign → portal activated

## Phases

### Phase 0 — Unblock (Done)
- [x] Merge `platform/client-resources` branch (PR #21 merged 2026-03-20)
- [ ] Fix Autopilot Trigger.dev crash (PR #19 — CI build failure, deferred)

### Phase 1 — Live Portal Data (Current)
- [x] Wire modules system: first module registered (meji-enquiry-followup), push execution data via `/api/modules/{name}`
- [x] Portal automations page: last execution, run count, live status badge
- [x] DB: add module_executions table

### Phase 2 — Close the Funnel (Weeks 2-3)
- [ ] Portal first-login onboarding state
- [ ] Proposal pages: "Get Started" CTA → admin invite queue
- [ ] Outbound workflow: proposal page → send → sign → one-click invite from admin

### Phase 3 — Buy Flow + Auto-Deploy (Weeks 3-6)
- [ ] Pick 1 template to sell (lead inquiry follow-up)
- [ ] Stripe → Autopilot task → deploy template
- [ ] Portal auto-activate for buyer
- [ ] Buy page polish (real output, deliverables, pricing)

### Phase 4 — Agentic Story (Weeks 6-8, after Autopilot stable)
- [ ] Homepage "How it works" section
- [ ] About page: AI-assisted delivery model
- [ ] Portal "Autopilot activity" feed

## Notes

- Autopilot is internal until stable — not marketed yet
- Portal is where the differentiation lives, not the public site
- First module registered: meji-enquiry-followup (Make.com)
