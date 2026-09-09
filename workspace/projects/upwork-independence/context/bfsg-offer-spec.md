# BFSG Compliance Wedge — Offer Spec (internal draft v1)

Status: DRAFT for owner review, 2026-07-28. Nothing here is client-facing.
Demand facts verified by web search 2026-07-28 (sources in
`project_compliance_deadline_wedges` memory); every price below is
ASSUMPTION until sold 3 times.

## Why this exists

BFSG (Barrierefreiheitsstärkungsgesetz) in force since 2025-06-28 for B2C
e-commerce and consumer-facing services. Abmahnwelle running since late 2025,
first Bußgelder Q1 2026, EUR 3,500-20,000 per Abmahnung, Bußgeld up to
EUR 100k; automated violation-scanning by Abmahn-Kanzleien expected from
Q3 2026. The most-cited violations are automatable basics: missing alt-texts,
contrast, keyboard-dead forms, missing/deficient Barrierefreiheitserklärung.
Buyers do not need convincing they have a problem; the law and the
Abmahn-Kanzleien do the demand generation.

## The offer (three stages, each feeds the next)

**Stage 1 — Barrierefreiheits-Audit (paid front door).**
Automated multi-page WCAG 2.1 AA / EN 301 549 scan + human-verified findings,
delivered as a German report: prioritized violation list, per-finding legal
exposure class (Abmahn-classic vs. edge), Barrierefreiheitserklärung status,
fix-effort estimate. Turnaround 5 working days.
Price anchor: EUR 490-790 fixed (ASSUMPTION; maps to the pricing-tiers entry
tier EUR 650). Impulse-buyable against a EUR 3.5-20k Abmahnung risk.

**Stage 2 — Remediation (fixed-price project).**
Fix the findings: alt-texts, contrast tokens, keyboard/focus order, form
labels, ARIA landmarks, templated Barrierefreiheitserklärung (with explicit
"legal wording reviewed by your counsel" carve-out). Ends with a re-audit:
"measured: 0 critical findings" — the measured-result positioning the
monetization research says to sell. Price anchor: EUR 2,500-6,000 by shop
size (ASSUMPTION; agencies quote EUR 5-15k, verified 2026-07-28 — automation
is the margin).

**Stage 3 — Compliance monitoring (retainer, the annuity).**
Monthly automated re-scan of all pages + new-content checks + regression
report + Erklärung currency check. EUR 200/mo (NOT arbitrary: the GTM-v2
optimize run found EUR 200 as the interior care-price optimum, both
neighbours worse). This is the recurring layer; audits and remediation are
its acquisition funnel.

## Audit pipeline (build plan, reuses owned assets)

1. Crawl: existing scraping stack (Scrapling/Playwright), sitemap-first.
2. Scan: axe-core via Playwright per page + Lighthouse a11y + custom checks
   for the Abmahn-classics (Erklärung present/complete, keyboard traps,
   form labeling, contrast).
3. Agentic triage: LLM classifies severity/effort per finding, drafts the
   German report from a fixed template; human QA pass before send.
4. Report: self-contained HTML per rule_deliverables (toggle, print CSS) +
   PDF export.
Marginal cost per audit after build: ~1-2h human time. That is the
superiority-by-automation: agencies hand-audit at day rates; this scales.
The scan engine doubles as the Stage-3 monitoring engine unchanged.
Quality gate: the optimize harness can hill-climb report accuracy against
hand-labeled fixture pages later (quality gate, not revenue engine, per the
research finding).

## Channels (UWG §7-clean, in order of speed)

1. **White-label to small DACH web agencies** (Shopware/WooCommerce/Shopify
   builders): their portfolios are full of non-compliant shops, they lack
   a11y expertise, and 73% of agencies already buy white-label delivery.
   Wholesale per-audit price or rev-share. Reachable via LinkedIn + warm.
   This sells N audits per partner instead of 1 per sale.
2. **Postal probe** (repurposes the research's EUR ~100 Tier-3 postal test):
   personalized letters to shop owners containing ONE real finding from
   their own site. Postal is legal in DE where cold email is not, and the
   payload is a personalized audit teaser, not a generic demo. Register A
   tone: helpful specialist, not Abmahn-fearmongering.
3. **AEO/content (u2 synergy):** "BFSG Abmahnung erhalten, was tun" cluster.
   Today's SERP is agency content marketing — proof the funnel converts, and
   proof this channel is contested (see Competition).
4. Referral ledger sources (u4), once the drafts gate opens.

## Competition (honest)

Supply is NOT zero: multiple German agencies content-market BFSG services
(xictron, quellcoder, cis-internetservice, web-accessibility-checker — all on
page 1 today). The edge is therefore: (a) price via automated pipeline,
(b) measured/verifiable results (re-audit proof, zero-criticals claim),
(c) selling white-label TO the agencies rather than against all of them.
Overlay widgets (accessiBe class) are the cheap end; their claimed
non-compliance is NOT yet verified (B4) — do not use in marketing copy until
sourced.

## Legal fence (hard)

This is a TECHNICAL conformance service, never Rechtsberatung
(Rechtsdienstleistungsgesetz). The report assesses WCAG/EN 301 549
conformance; Abmahnung response and Erklärung legal wording route to the
client's counsel. One-time cost item: lawyer review of the report template +
Erklärung template + the postal letter (TBD EUR, owner purchase decision).

## Validation plan (before scaling anything)

1. Build pipeline v1; run on 5 real DACH shops (fixtures, not outreach).
2. Sell 3 audits at the anchor price via the warmest channel available;
   adjust price on evidence.
3. Only then: postal batch + agency white-label pitch.
Stall trigger: if 0 of first 10 pitches buy at EUR 490+, the price or the
channel is wrong — stop and re-read evidence, do not discount silently.

## Open gates (owner)

- Offer approval (this document).
- Lawyer-review purchase (template pack, one-time, TBD).
- Any outbound (postal batch, agency pitches) — drafts gate stands.
- Where the audit sits on unpauseai.com (u6 dependency, after approval).
