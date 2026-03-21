# Platform Roadmap

Last aligned: 2026-03-21

## Vision

Two distinct experiences:
1. **Public website** — Automation agency site. Showcases services, sells automations, handles proposals.
2. **Client portal** — The agentic automation platform. Clients track live automations, get resources, communicate.

## Milestones

Each milestone is tied to a user-visible outcome, not a technical task.

### M1 — Foundation Verified (Current)
**Outcome:** Admin can log in and see everything working. Architecture map gives permanent transparency.

- [x] Auth works (admin via Google, client via magic link)
- [x] Module execution tracking (schema + API + portal UI)
- [x] Architecture map admin page (`/admin/architecture`)
- [ ] Verify end-to-end: admin logs in, sees dashboard, visits portal, sees execution data

### M2 — First Real Client Live
**Outcome:** First paying client using the portal with real, live automation data.

- [ ] Wire Make.com scenario to POST execution data to `/api/modules/meji-enquiry-followup`
- [ ] Create Meji Media client account (invite Gurmej/Jess via admin)
- [ ] Seed their project + resources via admin UI
- [ ] Client logs in, sees their project with live data + docs

### M3 — Funnel + Onboarding
**Outcome:** New prospects can find you, request service, and get onboarded.

- [ ] Proposal pages: "Get Started" CTA -> admin invite queue
- [ ] Portal first-login onboarding state
- [ ] Outbound workflow: proposal -> send -> sign -> one-click invite

### M4 — Self-Service + Payments
**Outcome:** Someone can buy an automation and start using it without manual admin work.

- [ ] Stripe -> auto-deploy template -> portal auto-activate
- [ ] Buy page polish (real output, deliverables, pricing)

### M5 — Agentic Story
**Outcome:** The unique selling point is visible on the public site.

- [ ] Homepage "How it works" section
- [ ] About page: AI-assisted delivery model
- [ ] Portal "Autopilot activity" feed

## Notes

- Autopilot is internal until stable — not marketed yet
- Portal is where the differentiation lives, not the public site
- First module registered: meji-enquiry-followup (Make.com)
- Architecture map at `/admin/architecture` is the single source of truth for platform state
