---
id: p2
name: BANT Lead Generation (SAP Treasury)
type: service-engagement
stage: spec
orchestrator: none            # manual-first; automation candidates listed in Phase 4
version: 0.1.0
created: 2026-06-11
updated: 2026-06-11
trigger: manual
systems:
  - linkedin-sales-navigator   # own seat, to be provisioned (NOT Meji's)
  - apollo                     # own seat, to be provisioned (NOT Gurmej's login-share)
  - instantly                  # dedicated Brisken workspace, to be provisioned
  - neverbounce
  - google-sheets              # lead tracker v1
last_changes: "Initial spec from 2026-06-11 owner directive + approved plan (evidence pack first, book-meetings-only qualification, LinkedIn-first channel mix)."
next_steps:
  - "Owner: capture Dirk's verbatim offer message into context/lead-generation/terms (gates Phase 0 close)"
  - "Finish evidence pack (universe sizing + sample account list, public data); research running 2026-06-11"
  - "Terms call with Dirk: settle the 6 term-sheet items in §2"
  - "On terms confirm: provision own sourcing seats + sending infra, start warm-up, begin LinkedIn outreach"
---

# p2: BANT Lead Generation for Brisken

## 1. The offer (as relayed; verbatim capture pending)

Dirk offered, relayed by owner 2026-06-11: **$300 per BANT-qualified lead
plus a commission on closed deals** for Brisken's B2-enterprise business.
Exact wording, commission %, basis, and payment mechanics: **TBD**; the
offer arrived outside logged channels; verbatim capture is the first
Phase 0 item. Nothing in this spec overrides what Dirk actually said.

What Brisken sells (verified brisken.com, 2026-06-11): SAP Cash
Management & Treasury consulting + the OnePilot application suite
(Market Data Hub, Trade Automation, Cash Flow & Exposure Hub, Credit
Data Hub, Bank Fee Portal, ESG Data Hub, Remittance Advice Gate),
RAPSODY 4-week implementation packages, Treasury Assessment service.
HQ: The Woodlands, TX. Existing lead channels are inbound only (SAP
Discovery Center + SAP Store listings, per the 2026-03/04 discovery
for the paused nurturing project).

## 2. Phase 0: terms (gates all spend and all outbound)

Term sheet to settle with Dirk, six items:

1. **BANT event definition.** Proposed: a held discovery meeting with
   an ICP-fit contact; Dirk accepts/rejects each lead within 48h with
   a stated reason; accepted = $300 billable.
2. **Commission**: %, basis (first contract vs first-year revenue),
   payment trigger. The commission is the economic core of the deal;
   the $300 roughly covers operating costs at realistic early volume.
3. **Geography**: US-first (their HQ market; B2B cold email lawful
   under CAN-SPAM). DACH excluded from cold email (UWG §7); LinkedIn
   only there, if Dirk wants DACH at all.
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

## 3. Phase 1: ICP + evidence pack (in progress, zero spend)

Approved 2026-06-11: build BEFORE the terms call so the conversation
anchors on concrete accounts, not concept.

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
  Instantly workspace, warm-up, NeverBounce-verified sends. CTA:
  Brisken's Treasury Assessment (low-friction, maps directly onto
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
