# UnpauseAI: Project Status

Snapshot of where UnpauseAI stands. Update on material changes (new initiatives, client wins, agency milestones, platform releases). Not a log; this is a current-state document.

**Last updated:** 2026-05-11

---

## Brand & Identity

| Field | Value |
|-------|-------|
| Name | UnpauseAI (one word) |
| Tagline | Built to stay done. |
| Domain | unpauseai.com |
| Founder | Nicolas Neumann |
| Partner | Matthias Neumann |
| HQ | Karlsruhe, Germany |
| Timezone | CET |
| Languages | English (fluent), German (native) |
| Positioning | EU-based automation consultancy. Production-grade workflow automation for regulated industries and scaling operations. GDPR-aware by design. |
| Brand assets | `workspace/projects/platform/upwork-agency/assets/` (banner, avatar, horizontal logo, SVG + PNG) |

## Service Pillars

1. **Lead and inquiry automation** (instant response, AI-personalized follow-up, multi-factor lead scoring, reply detection)
2. **CRM and ERP integration** (bidirectional sync, automated invoicing, deal-stage workflows, customer deduplication)
3. **Sales campaign operations** (aggregated dashboards, AI reply scoring, weekly trend reports)
4. **Custom workflow automation** (database polling, enrichment pipelines, scheduled reports, webhook routing)
5. **Migration and platform consolidation** (Make.com to n8n, zero-downtime cutovers)
6. **Healthcare and regulated-industry automation** (GDPR-compliant patient journey, consent tracking, audit trails)

## Technology Stack

| Platform | Use |
|----------|-----|
| Make.com | Visual workflow automation, fast iteration, client-facing scenarios |
| n8n | Self-hosted data pipelines, larger-scale CRM/ERP integrations |
| Trigger.dev | Code-first AI workflows, custom logic, durable execution |
| Claude API | AI integration (classification, sentiment, follow-up personalization) |
| FastAPI | Legacy automations, custom backends |
| Next.js + Vercel | Platform site (unpauseai.com) |

Common integrations: HubSpot, Fortnox, Upsales, TeamLeader, Smartlead, Instantly, Google Workspace, Slack, Airtable, MySQL, Postgres, OpenAI, Apify, Stripe, Notion.

## Pricing & Engagement

- Typical project scope: EUR 2,500 to 5,500
- Average delivery: 3 to 7 weeks
- Engagement model: detailed scoped proposal up front, fixed-fee delivery
- Handoff: documentation, monitoring, credentials transferred. No retainer trap.

---

## Upwork Agency

| Field | Status |
|-------|--------|
| Created | 2026-05-11 |
| Owner email | nicolas.neumann@unpauseai.com |
| Tier | Agency Plus ($20/month) |
| Primary specialty | AI Services > AI Apps & Integrations (recommended; pending category registration) |
| Profile copy | `workspace/projects/platform/upwork-agency/profile-copy.md` |
| Service descriptions | `workspace/projects/platform/upwork-agency/service-descriptions.md` |
| Service slots used | 5 of 10 (Data Analysis & Testing, ERP/CRM, Database Mgmt, DevOps & Solution Arch, Infosec & Compliance) |
| Service slots remaining | 5 (priority queue: AI Apps & Integrations, Marketing Automation, Scripts & Utilities, Sales Operations, Other Web Dev) |
| Matthias membership | Blocked: invite returned "User has active assignments or offers" when set to Exclusive. Fix: invite as Non-Exclusive. Pending. |
| Reviews | None yet (new agency). Reputation halo from Nicolas's solo profile does NOT carry over to agency contracts. |

## Why the agency exists

Primary driver: handoff of Meji Media from Nicolas's solo profile to Matthias. Upwork does not permit direct contract transfer between freelancers, so the close-and-rehire path requires Matthias to land on a credible agency profile (not a fresh solo profile with zero history). Secondary driver: foundation for future joint work.

---

## Active Clients

`workspace/clients/` contains 9 client folders. Operational state varies.

| Client | Status |
|--------|--------|
| meji-media | **Active.** Solo contract on Nicolas's profile. Two Upwork threads. Recent deliverables: Instantly audit (2026-05-11), volume forecast doc, deliverability + scaling report. Handoff to Matthias via agency pending Gurmej/Jess buy-in. |
| brisken | Status: read directly from spec folder |
| herbox-netherlands | Status: read directly from spec folder |
| herbox-sweden | Status: read directly from spec folder |
| hideit-equorperated | Status: read directly from spec folder |
| kunde-inc | Status: read directly from spec folder |
| peakora | Status: read directly from spec folder |
| ulf-incorporated | Status: read directly from spec folder |
| uplifted-consulting | Status: read directly from spec folder |

Run `/comd_status-check` for live status across all clients. This doc only tracks the operationally hot ones.

---

## Platform Site (unpauseai.com)

Stack: Next.js 15 + Tailwind + TypeScript, deployed to Vercel (Root Directory: `platform/`).

| Surface | State |
|---------|-------|
| Public site | Live. Home, About, Services, Work, Proposals, Contact, Assessment. |
| Proposals | 26 proposal markdown files in `platform/src/content/proposals/`. Statically generated. |
| Client portal | M2 in progress. Auth works, module execution tracking schema in place, architecture map admin page live. |
| First module registered | meji-enquiry-followup (Make.com) |
| Roadmap | See `workspace/projects/platform/context/roadmap.md`. Currently between M1 (Foundation Verified) and M2 (First Real Client Live). |

---

## Recent Material Changes

- **2026-05-11** Upwork agency created. Profile assets, copy, and 5 service descriptions drafted in `workspace/projects/platform/upwork-agency/`. `svg-to-png.py` tool added.
- **2026-05-11** Meji Instantly audit shipped (2 PDFs + cover note). PDF generation protocol installed as permanent rule.
- **2026-05-08** Client directive: zero em-dashes in HTML deliverables (universal, includes `&mdash;` and `--`). Applied retroactively. Enforced by `validate-output.py`.
- **2026-05-08** Meji docs site sidebar emoji removal.
- Volume forecast doc added to Meji docs site.

---

## Open Initiatives

| Initiative | Owner | Status |
|-----------|-------|--------|
| Meji handoff to Matthias | Nicolas + Matthias | Blocked on agency setup completion + Gurmej/Jess buy-in. Sequence: add Matthias non-exclusive → warm-introduce to client → close current contract → reopen under agency with Matthias assigned. |
| Off-platform agreement with Matthias | Nicolas | Drafting. Covers revenue split, payment cadence, scope of his role, IP, exit conditions. |
| Remaining 5 Upwork service descriptions | Nicolas (with drafting help) | Priority order in `service-descriptions.md`. AI Apps & Integrations should be primary. |
| Upwork agency logo + banner upload | Nicolas | Assets ready in `workspace/projects/platform/upwork-agency/assets/`. Manual upload via Upwork settings. |
| Portfolio extraction for Upwork profile | Pending | Need to mine existing client deliverables for case studies. Compensates for zero agency reviews. |
| Platform M2: first paying client live | Nicolas | Wire Meji Make.com scenario to `/api/modules/meji-enquiry-followup`. Create Meji client account. Pending Meji handoff resolution. |

---

## How to Use This Doc

- **Loading context at session start:** read this file plus `roadmap.md` plus the relevant client's `context/` folder.
- **When information here goes stale:** update in place. Don't append; replace. This is a snapshot, not a log.
- **Session logs go elsewhere:** `docs/sessions/{date}.md`.
- **Checkpoints go elsewhere:** `docs/checkpoints/`.
- **Friction events go elsewhere:** the friction register.
