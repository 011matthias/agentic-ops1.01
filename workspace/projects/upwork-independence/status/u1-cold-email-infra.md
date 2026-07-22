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
| Ready-to-purchase checklist | done | Written 2026-07-22, prices live-fetched same day: Porkbun $11.08/.com/yr, GWS Starter EUR 6.80/mbx/mo, Instantly Growth $47/mo, Apollo Free/$49+, NeverBounce TBD (bot-walled). 5 domain candidates RDAP-verified available. Model-feedback flag: real fixed stack ~2x the scorer's EUR 40/mo assumption | Owner approval line-by-line (checklist §10) | purchase gate | `../context/cold-email-purchase-checklist.md` |
| Sending domains (2-3) | approved | Owner APPROVED 2026-07-22 ($33.24/yr, 3 domains); not yet registered — needs payment method + registrar credential (vault reads denied this session) | Register on an owner-run purchase session | execution access | checklist §10 |
| Mailboxes + warm-up | approved, provider open | Owner APPROVED 6 mailboxes but asked whether Zoho undercuts Google Workspace; Zoho price UNVERIFIED (JS-injected, 2 fetch + 3 browser attempts failed). Zoho bills annually per its own page vs GWS monthly-flex | Quote Zoho + check provider cold-outreach terms, then buy | provider decision | checklist §11 |
| Instantly workspace | approved | Owner APPROVED Growth ($47/mo); not yet purchased | Buy on the purchase session | execution access | checklist §10 |
| Apollo account | not approved | Owner asked how the free tier works without a subscription: $0 plan, 900 credits, no card; but bulk EXPORT limits on free are UNVERIFIED and export is the capability we need | Test export on a real free account before relying on it | owner | checklist §11 |
| NeverBounce account | blocked | Verification; necessary-but-insufficient (MX pre-filter beside it) | — | purchase gate | checklist |
| First campaign build | not-started | UK/US-only list sourcing (UWG §7 structural), B5 gate + readiness audit inherited | — | warm-up complete + u5 kit | `rule_instantly_invasive` |

## Open decisions / gates

- PURCHASE GATE: every account needs its own explicit owner approval.
- Registrar + mailbox recommendation landed in the checklist (Porkbun +
  Google Workspace monthly-flex); owner picks per line at purchase time.
- Sender display names: owner decision at purchase, tied to the u2
  author/entity decision.

## Pointers

- Deliverability knowledge: memories `reference_cold_email_gateway_bounces`
  (Mimecast MX pre-filter), `reference_instantly_sequence_delay_semantics`
  (gap on the EARLIER step), warm-up 3-4 wk (`project_brisken_outreach_domains`).
- Delivery pipeline shape: `u5-delivery-kit.md` (meji p1-p3 extraction).
- Model economics: leadgen-portfolio scorer, cold pool 50, EUR40/mo fixed infra
  assumption.
