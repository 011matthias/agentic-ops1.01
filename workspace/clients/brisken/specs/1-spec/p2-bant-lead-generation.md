---
id: p2
name: BANT Lead Generation (OnePilot products)
type: service-engagement
stage: spec
orchestrator: none            # manual-first; automation candidates listed in Phase 4
version: 0.3.0
created: 2026-06-11
updated: 2026-06-12
trigger: manual
systems:
  - linkedin-sales-navigator   # own seat, to be provisioned (NOT Meji's)
  - apollo                     # own seat, to be provisioned (NOT Gurmej's login-share)
  - instantly                  # dedicated Brisken workspace, to be provisioned
  - neverbounce
  - google-sheets              # lead tracker v1
last_changes: "Direction change 2026-06-12 (two steps): (1) Brisken does not want new treasury-CONSULTING clients; p2 sells the OnePilot PRODUCT suite + AI Digital Workforce. (2) Architecture is one shared engine running a SEPARATE CAMPAIGN PER PRODUCT (own ICP, signal, angle, product-demo CTA), not a single wedge. 8 core campaigns (7 apps + Digital Workforce) + OnePilot for FSI as a parallel banking track. Full product catalog + campaign library in context/lead-generation/brisken-product-catalog.md; Dirk-facing deck (HTML+PDF) reframed."
next_steps:
  - "Owner: set or confirm campaign rollout order (proposed wave 1: Market Data Hub, Remittance Advice Gate, Bank Fee Portal)"
  - "Owner: confirm demo owner per product (who at Brisken takes which product's call)"
  - "Owner: capture Dirk's verbatim offer message into context/lead-generation/terms (gates Phase 0 close)"
  - "Terms call with Dirk: settle the 6 term-sheet items in §2 (commission basis now first-year subscription value)"
  - "On terms confirm: provision own sourcing seats + sending infra, start warm-up, launch wave 1 campaigns"
---

# p2: BANT Lead Generation for Brisken

## 1. The offer + direction (2026-06-12 reframe)

**Direction change (owner, 2026-06-12): Brisken does not want new
clients for the treasury CONSULTING business** (SAP Treasury Consulting
Services, RAPSODY fixed-price packages, Treasury Assessment). Those are
capacity-bound expert-hours. p2 now generates leads for the **OnePilot
product suite (SaaS subscriptions)** and the **AI Digital Workforce**,
not for consulting engagements. The target account base is unchanged
(SAP treasury/finance shops have exactly the data-integration pain
OnePilot kills); what changes is the OFFER and the CTA: from a Treasury
Assessment / consulting conversation to a per-product OnePilot demo.

**Architecture (owner, 2026-06-12, second step):** no single opening
wedge. One shared engine (sourcing, sending, qualification, booking,
reporting) runs a **separate campaign per product**, each with its own
ICP, public buying signal, message angle, and product-demo CTA. Eight
core campaigns (the 7 apps + the AI Digital Workforce) plus OnePilot
for FSI as a parallel banking track. The campaign library (per-product
ICP/signal/angle design) lives in
`context/lead-generation/brisken-product-catalog.md`.

Dirk offered, relayed by owner 2026-06-11: **$300 per BANT-qualified
lead plus a commission on closed deals** for Brisken's B2-enterprise
business. Exact wording, commission %, basis, and payment mechanics:
**TBD**; the offer arrived outside logged channels; verbatim capture is
the first Phase 0 item. For a product sale the commission basis is
first-year subscription value (SaaS norm; see negotiation-benchmarks).
Nothing in this spec overrides what Dirk actually said.

What Brisken sells (full catalog distilled to
`context/lead-generation/brisken-product-catalog.md` from 6 client
decks, 2026-06-12): the **OnePilot platform** (no-code orchestration
Framework on SAP BTP) with seven apps (Market Data Hub, Trade
Automation, Cash Flow & Exposure Hub, Credit Data Hub, Bank Fee Portal,
ESG Data Hub, Remittance Advice Gate), the **AI Digital Workforce**
(ChatGPT-powered co-workers), plus the now-out-of-scope consulting (SAP
Treasury Consulting, RAPSODY, Treasury Assessment). 2026 expansion:
**OnePilot for FSI** (banking orchestration across SAP and non-SAP
cores) is a separate, larger ICP needing its own research. HQ: Houston,
TX. Existing inbound channels: SAP ecosystem listings (per the
2026-03/04 discovery for the paused nurturing project).

## 2. Phase 0: terms (gates all spend and all outbound)

Term sheet to settle with Dirk. The verbatim offer is still uncaptured
(item 0); proposed positions anchored on
`negotiation-benchmarks-2026-06-12.md`.

0. **Capture Dirk's verbatim offer first.** It arrived outside logged
   channels; nothing below overrides what he actually said.

1. **BANT event = billable lead.** A held product demo (not a generic
   discovery call) with an ICP-fit contact; Dirk accepts/rejects each
   within 48h with a one-line reason; accepted = $300. No-show
   protection: a missed meeting counts only if rescheduled and held
   within 2 weeks.

2. **Commission (the economic core; the $300 only covers cost).**
   OnePilot is a SaaS subscription sold on a 6-18 month cycle with
   Brisken's sales in the loop, so these five sub-terms matter more
   than the per-lead fee:
   - **Rate:** 10-15% of first-year subscription value (ACV). Anchor:
     SAP's own program pays a basic referrer 10% of first-year cloud
     revenue; enterprise-SaaS norms are 10% warm / 15-20% qualified
     opportunity.
   - **Basis:** first-year subscription value (not lifetime, not flat).
   - **Trigger:** signed customer contract; paid within 30 days of
     Brisken receiving the customer's first payment.
   - **Attribution window:** any opportunity we sourced that signs
     within 12 months is ours. Non-negotiable given the long cycle; a
     short window makes the commission worthless.
   - **Cap/clawback:** uncapped or cap >= EUR 25k (SAP's basic-referrer
     cap); pro-rata clawback only if the customer churns inside year 1.

   **Two-lever fallback:** commission-weighted (accept $300/lead if the
   commission is rich and defined as above) OR base-weighted (if Dirk
   wants a token commission, the per-lead fee rises to $700-1,200 per
   held BANT meeting; the enterprise-BANT market is $400-1,700).

   **Lead flow + close rate (Dirk, 2026-06-12, clarified):** NOT product
   churn. Dirk means lead volume is low (they generate few leads), and
   their close rate on the leads they do get is >90%. This flips the
   economics TOWARD the commission, not away: at ~90% close, nearly
   every accepted BANT lead becomes a closed deal and pays the
   commission, so the commission is the prize, not air. Posture: lean
   COMMISSION-WEIGHTED (strong %, long 12-month attribution window); the
   $300 base is fine, do not trade the commission down for it. The only
   variable that matters is qualified-lead VOLUME, which makes the
   campaign breadth more valuable (more campaigns = more leads = more
   closes). Caveat: their 90% is on their current warm/inbound/self-
   selected lead mix; our cold-sourced leads will close at a lower
   fraction, so do not promise 90% on cold. The BANT gate exists to get
   our leads as close to their fit bar as possible; even at half that
   close rate, with OnePilot ACV the commission dominates.

3. **Geography**: US-first (their HQ market; B2B cold email lawful
   under CAN-SPAM). DACH/EU excluded from cold email (UWG §7, GDPR);
   LinkedIn only there. The ESG Data Hub campaign is therefore
   LinkedIn-led (see Phase 1 sourceability test).
4. **Sending identity**: dedicated lookalike domains, never
   brisken.com itself; signed by Dirk or a Brisken sales identity.
   Anchor: Dirk's 2026-04-10 call position that lead contact "needs
   to be personal" and sales@/marketing@/info@ style senders are out.
5. **Infra cost ownership**: domains, mailboxes, Instantly workspace,
   verification, own Apollo/Sales Nav seats. Estimate (ours, not
   quoted to client yet): $250-500/month. Given performance pricing,
   propose Brisken carries it.
6. **Exclusivity scope**: we keep the right to run lead-gen for
   non-competitors.
7. **Demo capacity (raise on the call).** Every lead is a product demo;
   confirm who at Brisken runs demos per product and their weekly
   capacity. Thin capacity caps useful volume and argues for running
   2-3 campaigns live, not eight.

## 3. Phase 1: ICP + evidence pack (in progress, zero spend)

Approved 2026-06-11: build BEFORE the terms call so the conversation
anchors on concrete accounts, not concept.

**Campaign library (2026-06-12):** the eight core campaigns and their
starting ICP / signal / angle design are tabled in
`context/lead-generation/brisken-product-catalog.md`. The account
profile, personas, and intent triggers below are the parameters for
the treasury-DATA campaigns (Market Data Hub, Trade Automation, Cash
Flow & Exposure Hub), which share the evidence-pack account list; each
other campaign sources its own list against its own signal before it
goes live. OnePilot for FSI (banking) is a parallel track with its own
ICP and research.

**Sourceability test (2026-06-12; full verdicts in the catalog):**
Remittance Advice Gate is GREEN (abundant cash-application/AR job
signal + AI angle + Brisken proof) and joins MDH + Bank Fee Portal in
wave 1. Bank Fee Portal and Credit Data Hub are YELLOW (firmographic
proxy / a tiny ~68-company SAP Credit Management universe). ESG Data
Hub is PARKED: EU-channel-constrained and its CSRD deadline deflated
when the Feb-2026 Omnibus cut scope ~80% and pushed non-EU reports to
2029. AI Digital Workforce runs as a cross-sell layer, not a
standalone list. Net: six viable standalone campaigns, one cross-sell
layer, one parked.

**Account profile (hypothesis, for Dirk to correct):** US companies
running SAP (ECC or S/4HANA) with an in-house treasury function,
roughly $500M+ revenue; OR any company in an announced S/4HANA
migration regardless of size band; the migration window is when
treasury modules get re-evaluated.

**Personas (multi-thread 3-5 per account):** Treasurer; VP/Director
of Treasury; Cash Manager; Head of Treasury Operations; Director of
Finance Transformation; SAP finance program / IT leads owning the
finance stack.

**Intent triggers (highest-signal, swept weekly):**

- Job postings naming SAP Treasury / TRM / S/4HANA Treasury
- S/4HANA migration announcements
- New CFO / Treasurer hires
- AFP / EuroFinance / SAP Sapphire / ASUG treasury-session presenters

**Universe size (sourced 2026-06-11, full table + caveats in
`context/lead-generation/evidence-pack-2026-06-11.md`):** the named
SAP TRM install base is small; Enlyft 628 global / ~182 US
(indicative), TheirStack 297 global / ~55 US (job-signal floor),
and skews mega-cap. The practical universe is two rings: (1) existing
TRM/Cash-Management users (OnePilot upsell + optimization), and
(2) the S/4HANA migration cohort (~27,000 customers end-2024 per
SAP's 2024 Integrated Report, ECC deadline 2027/2030), where every
migrator re-evaluates treasury. Confirms the precision play:
per-account depth, not volume. Evidence pack carries 24 verified US
accounts with direct signals; the 7 with live SAP-Treasury job
postings are the first-outreach cohort.

**Gate:** sample account list → Dirk validates fit before any contact
sourcing (same sample-approval pattern proven on the Meji Piece-2
build).

## 4. Phase 2: channels (approved: both tracks, LinkedIn first)

- **Track A: LinkedIn (starts within days of terms confirm).** Sales
  Navigator on our own seat, persona-targeted connection + 2
  follow-ups. Open decision (Phase 0 item 4): whose profile fronts it.
- **Track B: cold email (live ~2-3 weeks after terms confirm).**
  2-3 lookalike domains, 4-6 mailboxes, SPF/DKIM/DMARC, dedicated
  Instantly workspace, warm-up, NeverBounce-verified sends. CTA: a
  demo of that campaign's product (low-friction, maps directly onto
  BANT qualification).

**Hard isolation constraint:** no tool, seat, domain, or workspace
shared with any other client. Verified 2026-06-11 that all current
Apollo access is Gurmej's (Meji's) login-shared seat; off-limits
here. Own seats are a provisioning item.

## 5. Phase 3: qualification + handoff (approved: book-meetings-only)

Reply → short qualifying email exchange against the agreed BANT
checklist → booked meeting in Dirk's calendar → logged → $300 invoice
event on Dirk's acceptance. We do NOT run qualification calls
ourselves at start (revisit if acceptance rate disappoints).

Tracking: one Google Sheet (account, contact, signal, channel, stage,
BANT fields, Dirk verdict, invoice status). Weekly delivery note to
Dirk: count, pipeline, flags. The paused a0-a6 nurturing designs are
candidates for reply/no-show flows later; separate resumption
decision per PROJECT-BOUNDARIES.md, not part of p2.

## 6. Phase 4: scale candidates (not in initial scope)

- Automate the weekly intent-trigger sweeps
- CRM beyond the sheet
- DACH/EU expansion (LinkedIn-only mechanics)
- Productize as Route 2 case study #2

## 7. Economics (assumptions, to validate; not promises)

- Cost: $250-500/month infra estimate + our time.
- Volume: single-digit BANT meetings/month in months 1-2 is the
  honest expectation for a precision enterprise universe; conversion
  rates are TBD until live. At $300 each that roughly covers infra.
- The commission on Brisken-scale consulting deals is the prize,
  which is why §2 item 2 is the most important term.

## 8. Timeline

| When | What |
| --- | --- |
| Now → terms call | Verbatim offer capture, evidence pack, term sheet |
| Week 1 post-terms | Seats + domains provisioned, warm-up starts, LinkedIn outreach begins |
| Week 3-4 | Cold email live |
| Week 4-8 | First BANT meetings (realistic, not promised) |
