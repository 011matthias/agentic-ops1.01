---
project: upwork-independence
workstream: uwi-general
group: uwi
spec:
state: active
updated: 2026-09-05
---

# Upwork Independence (group general reference)

Shared context for the owned-acquisition program. Workstream state lives in the
u2-u7 files beside this one; this file holds pointers, the decisions taken, and
the weekly hours ledger. It is a roll-up, not a copy.

## Shared context (belongs to the program, not one workstream)

| Topic | Canonical source | Note |
|---|---|---|
| Strategy verdicts | `docs/optimize/upwork-independence-{gtm-v2,gtm-v2-confirm,leadgen-portfolio,pricing-tiers,portfolio-no-cold}/SUMMARY.md` | Dead ends + sensitivities machine-readable via `optimize_overview.py --prior-art upwork-independence` |
| Decision assets | `../gtm-plan.json`, `../acquisition-portfolio.json`, `../pricing-tiers.json` | Locked optimize assets; byte-stable outside runs |
| Two-routes framing | memory `project_upwork_independence_two_routes` | Route 1 local SMB / Route 2 B2B lead-gen; UWG §7 fence |
| ICP | `../context/icp.md` | Shared prerequisite for u2 (buyer-intent queries), u3 (recipes) |
| Accounts roster | `../infrastructure.yaml` | absent -> live as purchased |

## Decisions taken (owner, 2026-07-22)

1. **Purchases: plan-only.** u1 stops at a ready-to-purchase checklist; every
   purchase needs its own explicit approval.
2. **Capacity: ~14 h/wk from day one** (the model's acquisition budget). Owner
   decides which client load gives way; the ledger below measures actuals.
3. **Referral: ledger + offer definition only.** No outbound drafts until a
   separate go.

## Cross-model reconciliation (do not re-litigate)

The operative acquisition plan is the **portfolio-no-cold mix** (run
2026-09-05, after the owner retired cold email: LinkedIn 0.3683, demo-first
0.2992, AEO 0.1778, referral 0.1547, cold-email 0.0 pinned). The retirement
is an owner order, priced by the model at ~1,149 kEUR vs the prior
leadgen-portfolio winner; re-adding the channel is the owner's call, never a
run's. gtm-v2-confirm's +35.62 kEUR referral keep is an artifact of the GTM
model's missing referral-supply constraint (its own SUMMARY says so); u4's
ledger probe is the validation, not a channel pivot. Demo-first is no longer
fill-only: with cold email gone it takes the freed hours (its ~144 EUR/h
marginal beats the 33 EUR/h reinvestment), reversing the leadgen-portfolio
drop verdict under the new constraint regime.

## Workstreams

u1 (cold-email infra plan: status file, purchase checklist, list + sequences)
deleted 2026-09-05 on owner order; git history holds the last version.

- `u2-aeo-content.md` — sprint-zero platform fixes + corpus + probe loop
- `u3-linkedin-outbound.md` — identity, recipes, cadences (seat GATED)
- `u4-referral-partnership.md` — partner ledger + offer (drafts GATED)
- `u5-delivery-kit.md` — meji pipeline -> `workspace/templates/leadgen-delivery/`
- `u6-offer-surface.md` — pricing/service pages from `pricing-tiers.json`
- `u7-subcontracting.md` — starts when u5 exists (kit = contractor runbook)

## Weekly acquisition-hours ledger (target ~14 h/wk)

| Week (Mon) | u1 | u2 | u3 | u4 | u5 | u6 | u7 | Total | Note |
|---|---|---|---|---|---|---|---|---|---|
| 2026-07-20 | ~1 | ~2.5 | — | ~1 | — | — | — | ~4.5 | scaffold 07-22 + week-1 batch 07-22 (u1 checklist, u2 backlog + 3 posts, u4 ledger); agent-session ESTIMATES, owner corrects |
