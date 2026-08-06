# BFSG accessibility audit + remediation + monitoring

Status: spec-drafted (promoted to workstream u8, 2026-07-28)
Added: 2026-07-28
Demand verified: 2026-07-28

## One-liner

Automated Barrierefreiheits-Audit (fixed price) for German B2C shops and
service sites, feeding fixed-price remediation and a EUR 200/mo compliance
monitoring retainer; sold direct and white-label through web agencies.

## Demand

BFSG in force since 2025-06-28. Abmahnwelle running since late 2025, first
Bußgelder Q1 2026; EUR 3,500-20,000 per Abmahnung, Bußgeld up to EUR 100k.
Automated violation-scanning by Abmahn-Kanzleien expected from Q3 2026:
every non-compliant shop is about to get found. Most-cited violations are
automatable basics (alt-texts, contrast, keyboard forms, fehlende
Barrierefreiheitserklärung).

## Supply / competition

Not zero: several German agencies content-market BFSG services (xictron,
quellcoder, cis-internetservice, web-accessibility-checker on page 1).
Agencies quote EUR 5-15k for remediation at day rates. Cheap end: overlay
widgets (accessiBe class); their claimed non-compliance is NOT yet sourced,
keep out of copy until verified.

## Automation edge

Crawl (Scrapling/Playwright) + axe-core + Lighthouse + custom Abmahn-classic
checks + agentic triage + templated German report; ~1-2h human QA per audit.
Scan engine doubles as the monitoring engine. Re-audit gives a verifiable
"0 critical findings" claim the day-rate shops don't offer.

## Offer shape

Audit EUR 490-790 -> remediation EUR 2,500-6,000 by shop size -> monitoring
EUR 200/mo (GTM-v2 interior care-price optimum). All ASSUMPTION until 3 sales.

## Channel

White-label to small DACH web agencies (their portfolios are full of
non-compliant shops); personalized postal letters with ONE real finding from
the recipient's own site; AEO content cluster ("BFSG Abmahnung was tun").

## First euro

Pipeline v1 -> fixture-run on 5 real shops -> sell 3 audits via warmest
channel. Weeks, not months; demand is live this quarter.

## Risks / open questions

Technical conformance only, never Rechtsberatung (RDG); report + Erklärung
templates need a one-time lawyer pass (cost TBD). Price anchors unvalidated.
Content channel is contested.

## Detail

Full spec: `../upwork-independence/context/bfsg-offer-spec.md` (canonical).
Workstream: `../upwork-independence/status/u8-bfsg-wedge.md`.
