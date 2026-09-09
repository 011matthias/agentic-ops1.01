---
project: upwork-independence
workstream: u8-bfsg-wedge
group: uwi
spec:
state: active
updated: 2026-07-28
general_ref: status/uwi-general.md
---

# uwi / u8 — BFSG compliance wedge (audit -> remediation -> monitoring)

Owner-selected first wedge (2026-07-28) from the compliance-deadline
ideation (`project_compliance_deadline_wedges` memory): automated
accessibility audit as the paid front door (research loop A with a legal
engine attached), fixed-price remediation, EUR 200/mo monitoring annuity.
Demand live now: Abmahnwelle since late 2025, automated adversarial
scanning expected Q3 2026. Full offer definition:
`../context/bfsg-offer-spec.md` (DRAFT, at owner review).

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Offer spec v1 | done | Drafted 2026-07-28: 3-stage offer, price anchors (ASSUMPTION-tagged), pipeline plan, channels, legal fence, validation plan | Owner review | owner | `../context/bfsg-offer-spec.md` |
| Audit pipeline v1 | not-started | Crawl (Scrapling/Playwright) + axe-core + Lighthouse + Abmahn-classic custom checks + agentic triage + HTML/PDF report | Build after offer approval; fixture-test on 5 real shops | offer approval | spec §pipeline |
| Report template (DE) | not-started | German findings report, severity + exposure class + effort per finding; deliverable-rule compliant | With pipeline v1 | — | rule_deliverables |
| Legal template review | blocked | Lawyer pass on report template + Erklärung template + postal letter; one-time cost TBD | Owner purchase decision | owner + cash | spec §legal-fence |
| First 3 paid audits | not-started | Validation gate: sell at anchor price via warmest channel before any scaling | Pipeline + owner channel go | pipeline, drafts gate | spec §validation |
| Agency white-label pitch | blocked | Wholesale per-audit or rev-share to DACH web agencies | After first paid audits prove the report | validation | spec §channels |
| Postal probe (~EUR 100) | blocked | Personalized one-finding letters; repurposes the research's Tier-3 postal test | After validation + owner go | drafts gate + cash | spec §channels |

## Open decisions / gates

- Offer approval = the gate for all build work (owner, spec doc).
- DRAFTS GATE: no outbound (postal, agency pitches) without explicit go.
- Overlay-non-compliance claim stays out of all copy until sourced (B4).
- No Rechtsberatung, ever: technical conformance only.

## Pointers

- Offer: `../context/bfsg-offer-spec.md` (canonical).
- Ideation + verified demand sources: memory `project_compliance_deadline_wedges`.
- Care-price anchor EUR 200/mo: gtm-v2 interior optimum
  (`docs/optimize/upwork-independence-gtm-v2/SUMMARY.md`).
- Front-door ranking rationale: memory `project_monetization_loops_research`
  (loop A, 7.11).
