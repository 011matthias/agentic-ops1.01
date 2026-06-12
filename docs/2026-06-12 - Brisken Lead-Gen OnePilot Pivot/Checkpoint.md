# Checkpoint: Brisken Lead-Gen OnePilot Pivot

**Date:** 2026-06-12
**Status:** p2 lead-gen reframed + isolated on its own branch; pre-terms (awaiting Dirk's verbatim offer + terms call)

---

## Summary
Reframed the Brisken p2 lead-gen engagement from SAP-treasury consulting to selling the **OnePilot product suite**, rebuilt the strategy deck around a **per-product campaign model** (one shared engine, a campaign per product), ran a grounded sourceability test, filled in the commission term sheet, and recovered the whole session's work onto an isolated `client/brisken/lead-gen-onepilot` branch after a parallel finance session had stashed it.

---

## What Was Done This Session
### Strategy pivot (deck + spec + boundaries)
1. Deep-scanned Brisken's products (6 client `.pptx` decks) → distilled to `context/lead-generation/brisken-product-catalog.md`. Brisken's core is **OnePilot** (no-code financial-data orchestration on SAP BTP: Framework + 7 apps + AI Digital Workforce), plus a 2026 **OnePilot for FSI** banking push.
2. Interpreted "Dirk does not want new treasury clients" = stop selling the capacity-bound **consulting** (SAP Treasury Consulting / RAPSODY / Treasury Assessment); sell the **OnePilot products** instead. Same SAP-treasury account base; offer/CTA shifts from a Treasury Assessment to a product demo.
3. Owner redirected from a single Market-Data-Hub wedge to **a campaign per product**. Rebuilt the deck: "one engine, a campaign per product" + a campaign library + a per-campaign **targeting layout** (who / how we find them / why) + **sample outreach** (MDH + Remittance emails) + the `account`→`company` disambiguation.

### Sourceability test (grounded)
4. Ran each of the 8 campaigns against the real sourcing stack (TheirStack/Enlyft technographics + Apollo technology & job-posting filters). Verdicts recorded in the catalog: **6 viable standalone, 1 cross-sell layer (AI Digital Workforce), 1 parked (ESG)**. Wave 1 = Market Data Hub + Remittance Advice Gate + Bank Fee Portal.
5. Factual fix: the deck's ESG/CSRD "deadline" claim was stale — the **Feb-2026 CSRD Omnibus cut scope ~80%** and pushed non-EU reports to 2029. Corrected the ESG card.

### Commission economics
6. Filled the commission term sheet (spec §2): propose 10-15% of first-year subscription value, signed-contract trigger, 30-day pay, **12-month attribution window**, cap ≥ EUR 25k.
7. Dirk clarified retention is **lead-flow** retention (low lead volume), with a **>90% close rate** on the leads they get. This **flips the deal toward commission-weighted** (nearly every accepted lead becomes a close → a commission). Updated §2 accordingly. (Caveat captured: their 90% is warm/inbound; cold leads close lower.)

### Git recovery (isolation)
8. A parallel finance (p1 expense-recon) session had stashed this session's p2 WIP (`stash@{0}`) to clean its branch. Restored it onto a fresh **`client/brisken/lead-gen-onepilot`** branch off `main`, verified all content, committed (`43e9f0b`), dropped the stash.

---

## Key Decisions Made
### Sell OnePilot products, not treasury consulting
- **Choice:** p2 generates leads for OnePilot subscriptions + AI Digital Workforce; consulting is out of scope.
- **Rationale:** Owner directive; the products are scalable SaaS, the account base (SAP treasury/finance shops) is unchanged.

### One engine, a campaign per product (no single wedge)
- **Choice:** Shared sourcing-to-booking engine; each product plugs in its own ICP, signal, angle, and product-demo CTA.
- **Rationale:** Owner redirect. Each product is a different pain for a different buyer; breadth = more leads.

### Commission-weighted, not base-weighted
- **Choice:** Fight for a strong commission % + long attribution; the $300 base is secondary.
- **Rationale:** Dirk's >90% close rate means nearly every qualified lead converts, so the commission (not the per-lead fee) is the economics.

### Isolate p1 and p2 on separate branches
- **Choice:** p1 finance on `main`; p2 lead-gen on `client/brisken/lead-gen-*`.
- **Rationale:** Owner directive ("keep them isolated"); the tangle this session came from editing p2 files on a p1 branch.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html` | Modified (committed `43e9f0b`) | Per-product OnePilot deck: targeting layout, sample outreach, ESG/CSRD fix, account→company |
| `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.pdf` | Regenerated (untracked artifact) | PDF render matching the HTML (13 pp) |
| `workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md` | Modified (committed) | Products pivot, per-product campaign library, commission term sheet, sourceability test |
| `workspace/clients/brisken/PROJECT-BOUNDARIES.md` | Modified (committed) | p2 description + swap-history entry (products + per-product + branch isolation) |
| `workspace/clients/brisken/context/lead-generation/brisken-product-catalog.md` | Created (on disk; `context/` gitignored) | Distilled 6 product decks + per-product campaign library + sourceability verdicts |
| `workspace/clients/brisken/context/lead-generation/evidence-pack-2026-06-11.md` | Modified (on disk) | Reframe note: the 24-account list survives the product pivot |

---

## Current Status
- **Branch:** `client/brisken/lead-gen-onepilot` (p2 work committed at `43e9f0b`). `main` holds p1 finance untouched.
- **Deck + PDF:** consistent, per-product, validator-clean, zero em-dashes.
- **No platform ops:** p2 orchestrator is `none` (manual-first); no Make/n8n usage, no ops audit needed.
- **No comms-log:** brisken has no `comms-log.md`; p2 is pre-terms, nothing to log.
- **Leftover shared WIP** (uncommitted, deliberately not forced onto either project's branch): `docs/friction-register.md`, a few untracked `docs/` checkpoint folders, `deloitte-jobsuche.jpeg`.

---

## Next Steps
1. **Owner / Dirk:** capture Dirk's verbatim offer (gates Phase 0); settle commission at the terms call using spec §2 (lean commission-weighted given the 90% close).
2. **Owner:** confirm campaign rollout order (proposed wave 1: MDH + Remittance Advice Gate + Bank Fee Portal) and demo owner per product.
3. On terms confirm: provision own seats (Apollo / Sales Nav) + sending infra, start domain warm-up, launch wave-1 campaigns.
4. Keep all p2 work on `client/brisken/lead-gen-*` branches; never edit p2 files on a p1/finance branch again.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/PROJECT-BOUNDARIES.md` (binding; read before touching anything — p1/p2 isolation + swap history)
- `workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md` (the plan: products pivot, campaign library, term sheet)
- `workspace/clients/brisken/context/lead-generation/brisken-product-catalog.md` (product catalog + per-product campaigns + sourceability verdicts)
- `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html` (the Dirk-facing deck)

### Open Questions
- Dirk's verbatim offer (commission %, basis, attribution) — uncaptured; gates all spend.
- Campaign rollout order + demo owner per product — owner's call.
- Whose identity/domain fronts the outreach (sending identity, spec §2 item 4).

### Working Notes
- **>90% close rate** is the load-bearing fact: it makes the commission the prize and volume the only dial. Their 90% is on warm/inbound leads; cold-sourced leads will close lower (don't promise 90% on cold). The BANT gate exists to approach their fit bar.
- **Sourceability:** ESG parked (EU cold-email ban + CSRD deadline deflated by the Feb-2026 Omnibus). AI Digital Workforce = cross-sell layer (signal too vague for a clean cold list). Credit Data Hub = tiny universe (~68 SAP Credit Management installs, Enlyft). Bank Fee Portal = firmographic proxy (no "many banks" field exists).
- **Demo automation: dead.** Brisken is lead-starved, not demo-flooded; they hand-run every demo and close it. (My earlier "demo capacity is the bottleneck" risk was wrong — see Friction.)
- **`context/` is gitignored** — the catalog + evidence pack live on disk only; they survived the stash/reset turmoil because git never touched them.

### Reference Materials
- 6 product decks: `workspace/clients/brisken/context/Products/*.pptx`
- `context/lead-generation/negotiation-benchmarks-2026-06-12.md` (commission/lead-pricing anchors)
- `context/lead-generation/evidence-pack-2026-06-11.md` (24 verified US companies)

---

## How to Continue
`git checkout client/brisken/lead-gen-onepilot`. The deck, spec, and boundaries are the latest; the catalog/evidence-pack are on disk (gitignored). Everything downstream is gated on Dirk's terms call (verbatim offer + commission). When terms confirm, provision own infra and launch wave 1. Do NOT do p2 work on `main` or a finance branch.

---

## Strategic Feedback

### What Worked Well This Session
- The owner's tight, iterative redirects (products-not-consulting → campaign-per-product → "lay out who/why" → "run it") kept the deck converging fast without over-building any one version.
- Grounding the sourceability verdicts with real WebSearch (CSRD Omnibus, SAP Credit Management technographic, Apollo filters) caught a stale ESG claim before it reached Dirk.

### Suggestions
- When a session starts cross-project work (p2 lead-gen while p1 finance is live), establish the dedicated branch BEFORE the first edit. The tangle + recovery this session was avoidable with a 5-second `git checkout -b` up front.

### System Health
- **Recurring pattern (2nd day running): asserting facts about the client's business without their numbers.** 2026-06-11 it was the EU-travel-card claim from sample data; this session it was "demo capacity is the bottleneck" / "low volume is a limitation" — both inverted by the owner (no EU card; >90% close + lead-starved). B4 covers client-facing data claims; it does NOT yet cover INTERNAL strategic assertions about the client's operations. Candidate: extend the B4 discipline (or a memory) to "flag operational/business-state claims about the client as hypotheses until their data confirms."
- **Branch-scope gap:** nothing warns when editing files for project X on a branch named for project Y. A structural guard (PreToolUse on Edit/Write: if path is `clients/{c}/...` for a different project than the current `client/{c}/...` branch, warn) would have prevented the stash/recovery cycle.
- Autonomy score: 3 human interventions this session.
