---
project: upwork-independence
workstream: uwi-general
group: uwi
spec:
state: active
updated: 2026-07-22
---

# Upwork Independence (group general reference)

Shared context for the owned-acquisition program. Workstream state lives in the
u1-u7 files beside this one; this file holds pointers, the decisions taken, and
the weekly hours ledger. It is a roll-up, not a copy.

## Shared context (belongs to the program, not one workstream)

| Topic | Canonical source | Note |
|---|---|---|
| Strategy verdicts | `docs/optimize/upwork-independence-{gtm-v2,gtm-v2-confirm,leadgen-portfolio,pricing-tiers}/SUMMARY.md` | Dead ends + sensitivities machine-readable via `optimize_overview.py --prior-art upwork-independence` |
| Decision assets | `../gtm-plan.json`, `../acquisition-portfolio.json`, `../pricing-tiers.json` | Locked optimize assets; byte-stable outside runs |
| Two-routes framing | memory `project_upwork_independence_two_routes` | Route 1 local SMB / Route 2 B2B lead-gen; UWG §7 fence |
| ICP | `../context/icp.md` | Shared prerequisite for u1 (list filters), u2 (buyer-intent queries), u3 (recipes) |
| Accounts roster | `../infrastructure.yaml` | absent -> live as purchased |

## Decisions taken (owner, 2026-07-22)

1. **Purchases: plan-only.** u1 stops at a ready-to-purchase checklist; every
   purchase needs its own explicit approval.
2. **Capacity: ~14 h/wk from day one** (the model's acquisition budget). Owner
   decides which client load gives way; the ledger below measures actuals.
3. **Referral: ledger + offer definition only.** No outbound drafts until a
   separate go.
4. **Warm retainer conversion is OFF the table (owner, 2026-07-28).** The
   2026-07-25 research's Tier-1 step 1 (convert Brisken/Jochen/Meji hourly to
   retainers) is falsified by owner input: Brisken and Jochen are special
   agreements, not convertible; Meji is hour-capped by the client's own
   reluctance (USD 40/hr, will not grow). The EUR 5k/mo target must come from
   NEW clients via the u1-u7 channels, with the productized audit (research
   loop A) as the fixed-price front door. A u8 warm-conversion workstream was
   created and deleted same-week on this correction.

## Cross-model reconciliation (do not re-litigate)

The operative acquisition plan is the **leadgen-portfolio mix** (cold-email
0.378 volume engine, LinkedIn 0.289, referral 0.154, AEO 0.178, demo-first
0.0/fill-only). gtm-v2-confirm's +35.62 kEUR referral keep is an artifact of
the GTM model's missing referral-supply constraint (its own SUMMARY says so);
u4's ledger probe is the validation, not a channel pivot. Demo-first tension
(GTM kept 24% local, portfolio dropped it): local is cheap to deliver,
expensive to win — run as spare-capacity fill / AEO proof only.

## Workstreams

- `u1-cold-email-infra.md` — sending infra checklist (purchases GATED)
- `u2-aeo-content.md` — sprint-zero platform fixes + corpus + probe loop
- `u3-linkedin-outbound.md` — identity, recipes, cadences (seat GATED)
- `u4-referral-partnership.md` — partner ledger + offer (drafts GATED)
- `u5-delivery-kit.md` — meji pipeline -> `workspace/templates/leadgen-delivery/`
- `u6-offer-surface.md` — pricing/service pages from `pricing-tiers.json`
- `u7-subcontracting.md` — starts when u5 exists (kit = contractor runbook)
- `u8-bfsg-wedge.md` — BFSG audit -> remediation -> monitoring (owner-selected
  first compliance wedge 2026-07-28; offer spec at owner review)

## Weekly acquisition-hours ledger (target ~14 h/wk)

| Week (Mon) | u1 | u2 | u3 | u4 | u5 | u6 | u7 | Total | Note |
|---|---|---|---|---|---|---|---|---|---|
| 2026-07-20 | ~1 | ~2.5 | — | ~1 | — | — | — | ~4.5 | scaffold 07-22 + week-1 batch 07-22 (u1 checklist, u2 backlog + 3 posts, u4 ledger); agent-session ESTIMATES, owner corrects |
