---
project: upwork-independence
workstream: u1-cold-email-infra
group: uwi
spec:
state: active
updated: 2026-07-22
general_ref: status/uwi-general.md
---

# uwi / u1 — Cold-email sending infrastructure

Stand up UnpauseAI-owned sending infrastructure for the volume-engine channel
(0.378 of acquisition effort, UK/US only per UWG §7). UnpauseAI owns the full
knowledge/safety layer (cold-email skill, Mimecast MX pre-filter + Instantly
delay-semantics memories, B5 invasive gate) and ZERO sending infrastructure:
every working account (Instantly, Apollo, domains, mailboxes, NeverBounce) is
Meji/Brisken client property, off-limits. Purchases are GATED (owner decision
2026-07-22): this workstream delivers a ready-to-purchase checklist so a later
"go" starts the 3-4 week warm-up clock same-day.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Ready-to-purchase checklist | not-started | The current deliverable: registrar choice, 2-3 domain candidates, mailbox plan, ESP/list/verify tiers with EUR/mo, DNS-auth runbook, day-1-after-go sequence | Write `../context/cold-email-purchase-checklist.md` | — | this file |
| Sending domains (2-3) | blocked | Nothing registered; unpauseai.com never cold-sends | — | purchase gate | checklist |
| Mailboxes + warm-up | blocked | 3-4 wk warm-up is the calendar gate on all downstream | — | purchase gate + domains | checklist |
| Instantly workspace | blocked | Own ESP account; credential -> vault + `../context/.env` | — | purchase gate | checklist |
| Apollo account | blocked | Own list-building; meji filter-spec pattern reusable once credential exists | — | purchase gate | checklist |
| NeverBounce account | blocked | Verification; necessary-but-insufficient (MX pre-filter beside it) | — | purchase gate | checklist |
| First campaign build | not-started | UK/US-only list sourcing (UWG §7 structural), B5 gate + readiness audit inherited | — | warm-up complete + u5 kit | `rule_instantly_invasive` |

## Open decisions / gates

- PURCHASE GATE: every account needs its own explicit owner approval.
- Registrar + mailbox provider choice lands in the checklist (recommendation
  with EUR/mo, owner picks).

## Pointers

- Deliverability knowledge: memories `reference_cold_email_gateway_bounces`
  (Mimecast MX pre-filter), `reference_instantly_sequence_delay_semantics`
  (gap on the EARLIER step), warm-up 3-4 wk (`project_brisken_outreach_domains`).
- Delivery pipeline shape: `u5-delivery-kit.md` (meji p1-p3 extraction).
- Model economics: leadgen-portfolio scorer, cold pool 50, EUR40/mo fixed infra
  assumption.
