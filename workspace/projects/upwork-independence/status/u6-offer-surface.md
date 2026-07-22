---
project: upwork-independence
workstream: u6-offer-surface
group: uwi
spec:
state: not-started
updated: 2026-07-22
general_ref: status/uwi-general.md
---

# uwi / u6 — Offer surface (pricing + service pages)

Public rendering of the good/better/best menu (650/1850/6300 EUR/mo).
`../pricing-tiers.json` is canonical; surfaces derive from it and never
duplicate numbers. Current state: `(public)/pricing` carries the OLD
automation-project offer; `catalog.ts` is one-off-purchase shaped (does not
fit monthly retainers); no lead-gen service page exists. Weeks 3-6.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Pricing page tiers | not-started | Replace/extend old project pricing with the retainer menu, fed from pricing-tiers.json | Design decision: extend /pricing vs dedicated page | u5 tier scope mapping | `platform/src/app/(public)/pricing/page.tsx` |
| Lead-gen service page | not-started | The Route-2 offer page; UK/US cold-email scope stated | After tier mapping | u5 | — |
| Machine-readable pricing | not-started | /pricing.md or .txt twin (2026-06-07 AEO audit WARN still open; pricing-tiers gives it real content) | Ship with u2 sprint zero | — | ai-visibility baseline report |
| Retainer content module | not-started | catalog.ts schema is selfServicePrice/premiumPrice one-off shaped; retainers need their own module | With pricing page work | — | `platform/src/content/catalog.ts` |

## Open decisions / gates

- Extend `/pricing` vs dedicated service page (owner preference at build time).
- Tier scope mapping (u5) must exist first — the menu cannot be published
  without defining what each tier includes.

## Pointers

- Canonical values: `../pricing-tiers.json` (guard-validated).
- Platform standards: `rule_platform_standards` (§2 language, §7 data accuracy —
  every claim traces to shipped work).
- Incentive coupling warning: premium price + mid tier move TOGETHER
  (pricing-tiers SUMMARY finding 3); never edit one tier's public number alone.
