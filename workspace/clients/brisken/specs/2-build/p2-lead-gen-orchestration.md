---
id: p2.ops1
name: Lead-Gen Orchestration (operating model)
type: operations-runbook
stage: build
orchestrator: none            # manual-first; n8n automation candidates in §7
version: 0.1.1
created: 2026-06-12
updated: 2026-06-16
trigger: manual
systems:
  - linkedin-sales-navigator   # own seat, to provision at go-live (the ONLY direct-outreach channel)
  - apollo                     # own seat; sourcing / enrichment only (no email send)
  - google-sheets              # lead tracker (single source of truth)
  # RETIRED 2026-06-12 - cold-email stack (instantly, neverbounce, lookalike domains, mailboxes, warm-up):
  # Brisken's own ~150-mailbox / ~2M-email campaign returned 0 leads. Channel dropped, not deferred.
last_changes: "2026-06-12 (later, hardening): COLD EMAIL RETIRED (Brisken's own ~150-mailbox/~2M-email campaign = 0 leads). Engine respine: spine is now the trigger-detection radar (context/lead-generation/targeting-radar.md) with a 3-axis ICP (SAP fit x data-vendor-USER disposition x live trigger); the only direct-outreach channel is precision LinkedIn; SAP co-sell + active vendor referral moved off the critical path. See section 0. Earlier 2026-06-12: added section 9 (force multipliers) + section 10 (go-forward, campaign 1 = MDH). Sections 2-3 and 7 below predate the respine; section 0 supersedes their cold-email parts."
next_steps:
  - "Dirk gate 1: which of the 6 data-vendor relationships are active (co-marketing/referral vs technical only). Unlocks Way 2."
  - "Dirk gate 2: sending identity (whose name and domain front the outreach)."
  - "Dirk gate 3: green-light to contact + ~$99/mo Sales Navigator seat."
  - "Open for Dirk: is SAP co-sell (account-exec referral) active? Distinct from being SAP-listed; the bigger prize."
  - "On go-live: provision seat, Dirk-validate the MDH target list, start LinkedIn (Way 1) while Dirk opens vendor conversations (Way 2)."
---

# p2.ops1: Lead-Gen Orchestration

The plan + ICP live in `specs/1-spec/p2-bant-lead-generation.md`; the
per-product campaign library + sourceability verdicts live in
`context/lead-generation/brisken-product-catalog.md`. This doc locks
HOW the engine runs and what it takes to reach the first BANT lead.

## 0. Strategy hardening (owner, 2026-06-12) — supersedes the cold-email parts below

Diagnosis: Brisken has a discovery problem, not a closing problem. They
close >90% of the leads they actually get; the binding constraint is
qualified-lead VOLUME. So the metric is **warm, triggered at-bats per
month into the >90%-close motion**, and the job is to manufacture
warmth, not volume.

- **Cold email is retired.** Brisken's own ~150-mailbox, ~2M-email
  campaign returned 0 leads. A system that touches the SAP money core
  does not earn a meeting cold. Track B (section 2/3/timeline below),
  Instantly, lookalike domains, and warm-up are dropped, not deferred.
- **Spine = the trigger-detection radar** (`context/lead-generation/targeting-radar.md`).
  A 3-axis ICP: SAP fit x **data-vendor-user disposition** (proven pain,
  the sharpener) x live trigger. The radar ranks the universe and feeds
  every other move.
- **Three lanes, concurrent.** Lane 1 autonomous now (radar + forwardable
  assets + AEO substrate + Dirk enabler pack, zero spend, no contact).
  Lane 2 go-live on one compressed Dirk decision (precision LinkedIn via
  the reachable persona; one Sales Nav seat). Lane 3 Brisken-driven and
  off the critical path (SAP co-sell business case, vendor co-marketing).
- **Reweighting.** SAP co-sell and active vendor referral are the prize
  but slow and Brisken-owned; the dependable near-term levers are
  Store-listing AEO, the SAP-partner trust badge reused everywhere, and
  the reverse-sourced vendor signal (needs no vendor permission).
- **Concentration.** Point all lanes at the SAME triggered cohort so each
  account meets Brisken on two-plus trusted surfaces before the 1:1.
- **Products narrow 8->3:** Market Data Hub + Trade Automation + OnePilot
  platform; the other apps are subfunctions/proof (Remittance/Calvin =
  the best forwardable asset, not a standalone campaign).
- **WhatsApp evaluated and excluded as an acquisition channel (agent
  assessment 2026-06-16, owner to confirm).** Raised as a possible new
  outreach angle, eventually openclaw-automated. Rejected for this
  motion on three grounds: (1) it is a colder, more intrusive channel
  than the cold email already proven dead here (0 leads on ~2M sends),
  so it adds volume where the diagnosis calls for warmth; (2) US
  enterprise treasury does not transact on WhatsApp and the ICP's
  personal mobile numbers are not ethically or reliably sourceable;
  (3) openclaw-automated WhatsApp Web outreach violates WhatsApp ToS
  (number-ban risk) plus UWG §7 for any EU tail. Narrow legitimate uses
  (post-consent demo logistics, inbound "WhatsApp us" surfaces, non-US
  WhatsApp-native ICPs such as OnePilot for FSI, or the DE Route-2 local
  motion) are not the wave-1 enterprise-SAP motion. The automation
  instinct redirects to the §7 weekly trigger-detection radar sweep,
  which is ToS-clean and compounds.

Sections 1 and 9-11 hold as written. Sections 2-3 (the engine table's
email rows) and 7 (Instantly automation) are superseded by this section
where they assume a cold-email channel.

## 1. Reframe (owner, 2026-06-12): delivery before compensation

Build the engine and generate first BANT leads as proof of quality;
settle commission afterward. The plan-spec §2 term sheet is deferred,
not dropped, and stays the reference for the eventual money
conversation. No pricing work is in scope here.

## 2. The split that shapes the whole plan

Generating real leads means contacting Brisken's real prospects under
a Brisken-associated identity. That needs Dirk's OPERATIONAL consent
(his brand, his market, his reputation, GDPR/CAN-SPAM), which is a
smaller and faster gate than negotiating money. So the work splits:

| Build now (no spend, no contact, no Dirk) | Go-live gated (one Dirk yes + modest infra) |
|---|---|
| This operating model | Sending identity / lookalike domains (Dirk's brand) |
| Per-campaign ICP / signal / angle (catalog) | Own Apollo + Sales Navigator seats (spend) |
| Campaign-1 target list (the 24 already exist) | Instantly workspace + mailboxes + warm-up (spend + ~2-3 wk) |
| Persona map per account (public LinkedIn) | The actual connection requests / sends (Dirk consent) |
| LinkedIn + email sequences (draft templates) | Demo owner + calendar slot (Dirk) |
| BANT checklist + tracker + reporting format | |

We build the left column to "ready to press send," then take it to
Dirk for the right column. The ask he hears is "approve go-live and
give us the identity," not a price negotiation.

## 3. The engine (one shared pipeline; every campaign plugs in)

Manual-first by design: the universe is small and precision (named SAP
TRM install base in the low hundreds; see evidence pack). First leads
come from high-touch, hand-built outreach, not an automated blast.
Automation is the scale layer once a campaign proves it books (§7).

| # | Stage | Tool | Manual / auto (v1) |
|---|---|---|---|
| 0 | Provision (one-time) | seats, domains, Instantly, NeverBounce, Sheet | manual setup |
| 1 | Source per-campaign list | Apollo + TheirStack/Enlyft technographic + job-post filters | manual |
| 2 | Map 3-5 personas/account | Sales Navigator | manual |
| 3 | Verify emails | NeverBounce | manual (batch) |
| 4 | Outreach, LinkedIn-first | Sales Nav (connect + 2 follow-ups); Instantly (email, after warm-up) | manual send v1 |
| 5 | Reply + BANT qualify | email exchange vs the §4 checklist | manual |
| 6 | Book + log | demo owner's calendar + tracker | manual |
| 7 | Report + tune | weekly note to Dirk; per-campaign rates | manual |

LinkedIn leads because it has no warm-up lag; email goes live ~2-3
weeks behind once domains warm. One campaign runs live at a time until
it books a demo, then a second is layered in.

## 4. Definition of done: what counts as a BANT lead

The billable unit (plan-spec §2.1) is a **held product demo with an
ICP-fit contact** that clears the bar below. The demo is the
deliverable; BANT is the gate to book it.

- **Need** (lead signal): the specific pain the campaign's product
  removes is present (e.g. MDH: manual market-data uploads into SAP).
- **Authority**: contact owns or directly steers the treasury/finance
  system decision (Treasurer, Cash Manager, SAP-finance program lead,
  or one hop from them).
- **Timeline**: a live evaluation window (active S/4HANA migration, a
  current data-integration pain, a recent relevant hire).
- **Budget**: a real subscription budget or the authority to allocate
  one; softest of the four at the demo-booking stage, firmed on the
  demo itself.

A demo that clears Need + Authority + Timeline books; Budget is
confirmed live. This is the bar to get our cold-sourced leads close to
Brisken's own fit standard (their >90% close is on warmer leads; ours
will be lower, so the gate matters).

## 5. Wave-1 execution

Start with the one tightest, already-proven campaign, prove it books,
then parallelize. Do not open three cold campaigns at once.

1. **Campaign 1 = Market Data Hub.** The proven 24-account list exists
   (evidence pack), it is the flagship product, and its signal (SAP
   Treasury / TRM job posts) is the cleanest to source. Fastest path
   to a first booked demo.
2. **Then Remittance Advice Gate** (strongest AI angle + abundant
   cash-application job signal + Brisken's ChatGPT customer proof).
3. **Then Bank Fee Portal** (hard-dollar ROI; firmographic-proxy
   sourcing).

ESG parked; AI Digital Workforce runs as a cross-sell layer on the
above lists (catalog sourceability test).

### 5.1 Go/no-go gates (the motion has a defined stop)

Numbered checkpoints so an unproductive campaign gets re-cut or stopped,
not ground indefinitely. They also protect the Brisken relationship: a
defined exit is what lets us say "we'll know by week 8" instead of
open-ended spend. Measured from first send on the live campaign.

- **G1 (week 4) — signal check.** If the targeting + trust groundwork
  has produced zero qualified replies, re-cut the list and the message
  before going wider. Do not add volume to a list that is not replying.
- **G2 (week 8) — booking check.** If nothing has booked a held demo,
  pause new outreach and diagnose which of {list, message, product-fit}
  is the miss; decide with Dirk whether to continue, re-cut, or stop.
- **G3 (week 12) — pipeline check.** If held demos are not converting
  toward real pipeline, stop and reassess the motion rather than keep
  spending Dirk's demo time and ours. No sunk-cost grind.

These gates are internal discipline first; the client-facing deck states
them as the built-in checkpoints so Dirk knows the spend is bounded.

## 6. Tracker schema (Google Sheet, single source of truth)

One row per contact: `account | campaign | contact | title | persona |
signal (the public trigger) | channel | stage (sourced → sent →
replied → qualifying → booked → held → accepted) | BANT: N/A/T/B flags
| demo date | demo owner | Dirk verdict | notes`. Weekly delivery note
to Dirk derives from this: count by stage, pipeline, flags.

## 7. Automation roadmap (after a campaign proves it books)

Manual-first to first leads. Once a campaign reliably books, the
n8n candidates are: the weekly intent-trigger sweep (job-post / hire /
migration signals), Instantly send orchestration via API, and
Sheet sync. Not before proof; automating an unproven motion wastes the
build (plan-spec Phase 4).

## 8. Open go-live decisions (not for me to assume)

1. **Infra ownership.** Going operational needs ~$250-500/mo (seats,
   domains, Instantly, verification). Two paths: we front it as an
   investment in landing Brisken (Route-2 reference client #2), or
   Dirk provisions. Recommendation: front the LinkedIn-only motion
   first (Sales Nav seat ~$99/mo is the only hard cost to a first
   booked demo); defer the email stack's larger cost until LinkedIn
   shows the campaign books.
2. **Sending identity** (Dirk-gated, plan-spec §2.4): whose
   profile/domain fronts the outreach. Needed before any send.
3. **Demo owner per product** (Dirk): who runs the MDH demo and their
   weekly capacity. Caps useful live volume.
4. **Live concurrency**: one campaign at a time to first proof
   (recommended), revisit after the first booking.

## 9. Force multipliers (raise hit-rate beyond cold volume)

Brisken is lead-starved but asset-rich. The largest gains come from
weaponizing latent assets, not grinding more cold volume.

**A. Sharper intent signals (engine fires these; extend section 3 stage 1).**
Beyond SAP-Treasury job posts:
- **ECC-2027 / S4HANA migration cohort = the spine signal** across
  every campaign. Every migrator re-evaluates the treasury stack, and
  the deadline supplies the urgency the copy otherwise lacks.
- **Competitor-TMS displacement**: Kyriba / FIS Quantum / ION-Reval /
  GTreasury users, especially at contract renewal.
- **10-K / earnings-call language** (FX exposure, hedge accounting,
  bank-fee programs, "treasury transformation") = self-declared pain.
- **M&A / multi-entity announcements** to Cash Flow & Exposure Hub.
- **Finance/treasury layoffs or freezes** to AI Digital Workforce.
- **New CFO/Treasurer hires** (90-day re-evaluation window); AFP /
  EuroFinance / SAP Sapphire treasury rosters.

**B. Lower-friction CTAs (per campaign; softer than "book a demo").**
- Bank Fee Portal: a free bank-fee leakage mini-audit (hard-dollar,
  loss-aversion hook).
- Remittance / Digital Workforce: a 90-second "Calvin" co-worker video
  (the email-to-bank-transfer flow from their own deck; forwardable
  inside the buying committee).
- MDH: a one-page "your market-data flow into SAP, mapped" teardown.
- Any campaign: an ABM 1-pager citing the account's specific public
  signal; ISO 27001 / SOC 1 as the trust closer for risk-averse
  treasury.

**C. Warm-channel multipliers (CONFIRMED live 2026-06-12; exploit, not build).**
- **SAP Store (audited live 2026-06-17).** The buyable transactional
  SAP Store (store.sap.com DCP) carries only TWO Brisken listings:
  Market Data Hub and Trade Automation. The MDH per-vendor variants
  (OANDA / Central Banks / Commodities / Financial Services) exist as
  sap.com partner MARKETING pages, not as buyable store listings.
  Remittance Advice Gate and Bank Fee Portal did NOT surface on any SAP
  channel (store or indexed partner pages); they are on brisken.com
  only. (The sap.com partner pages were index-only this audit because
  Akamai blocked live fetch, so confirm against the partner cockpit
  once Dirk's access is available.) The SAP Store AI advisor already
  surfaces OnePilot for the brand query. Levers: (1) use the
  SAP-listed page as the cold-outreach CTA + trust asset; (2) AEO the
  listings so the advisor surfaces them for problem/category queries,
  capturing in-marketplace demand where every visitor is an SAP
  customer. Open: is SAP co-sell (account-exec referral) active? That
  is distinct from being listed and is the bigger prize. Dirk item.
- **AFP marketplace (live).** Brisken is a listed AFP vendor with
  product-launch posts. AFP is the largest US treasury association
  (matches US-first). Lever: listing as credibility + speaking /
  content / member reach at AFP 2026.
- **Data-vendor partnerships** (Bloomberg, Refinitiv/LSEG, 360T, CME,
  Deutsche Boerse, OANDA). Two plays. (1) Reverse-source (autonomous,
  no permission): "uses [vendor] + runs SAP" via job-post signals
  (Bloomberg/BLPAPI/Terminal, Refinitiv/Eikon/Workspace, 360T, FXall,
  FXGO, CME); the signal is the personalization. Bloomberg/Refinitiv/
  OANDA/central-banks -> MDH; 360T/FXall/FXGO/CME -> Trade Automation.
  (2) Partner-referral + co-marketing (needs Dirk + a live vendor
  relationship): Bloomberg Enterprise App Portal (325k+ Terminal
  users) and LSEG partner program + Workspace SDK are real listing /
  referral channels; the vendor sells the data, OnePilot makes it
  usable in SAP, so the referral is complementary and
  consumption-positive. Confirm per vendor which relationship is
  active. The per-vendor "MDH for OANDA / for Central Banks" SAP-listed
  variants are ready-made co-marketing units.
- **Customer proofs** (FSI / agricultural / chemicals): reference
  selling + lookalike sourcing seeds.

**D. Compounding mechanics.** The weekly signal sweep becomes a
proprietary intent database that improves the longer it runs;
multi-thread 3-5 personas per account; feed only high-fit leads into
Dirk's >90% close (quality is the economics, not a slogan).

## 10. Go-forward (campaign 1: Market Data Hub)

Owner greenlit running both data-vendor plays 2026-06-12.

**Now (autonomous, zero-spend, no contact):**

- Base list: the 24 verified SAP-treasury accounts in
  `context/lead-generation/evidence-pack-2026-06-11.md`; first cohort
  is the 7 JOB-signal accounts (Corteva, Toyota, J&J, Ford, Colgate,
  Amtrak, Penn Turnpike).
- Rank for MDH by the data-vendor signal ("uses Bloomberg / Refinitiv /
  360T / OANDA / CME + SAP"), sourced from public job-posts and web.
  The signal doubles as the message hook. Full per-account vendor
  tagging is go-live sourcing work (seat-efficient); the method is set.

**Gated on Dirk (operational, not money):**

1. Which of the six data-vendor relationships are active (co-marketing
   / referral vs technical only). Unlocks Way 2.
2. Sending identity (whose name and domain front the outreach).
3. Green-light to contact + ~$99/mo Sales Navigator seat.

**Go-live:** provision the seat, Dirk-validate the MDH target list,
start LinkedIn outreach (Way 1) while Dirk opens the vendor
conversations (Way 2); track in one sheet; a booked product demo is
the BANT lead.

### Campaign-1 message variants (draft; sender TBD, Dirk gate 2)

Bloomberg variant:

> Subject: Bloomberg data into SAP by hand?
> Hi [name], saw [Company] runs SAP treasury and works with Bloomberg
> market data. Usually that means someone is keying rates and prices
> into SAP by hand, or babysitting a custom script that keeps breaking.
> Brisken's Market Data Hub does that part automatically, no code, and
> it is listed on the SAP Store. A short demo shows it on your setup.
> Worth 15 minutes?
> [sender]

Refinitiv / LSEG variant:

> Subject: Refinitiv feed into SAP without the manual step?
> Hi [name], [Company] runs SAP treasury and pulls market data from
> Refinitiv. Getting that feed into SAP cleanly is usually manual work
> or fragile middleware. Brisken's Market Data Hub governs it end to
> end, no code, and it is SAP-listed. Open to a short demo on your
> setup?
> [sender]

## 11. Partner-channel track (beyond cold outreach): SAP + data vendors only

Owner scope (2026-06-12): organize around Brisken's CLOUD-platform
positioning (the SAP ecosystem + its data integrations), not the
treasury vertical. Two partner families only: **SAP** (was point 1) and
the **data vendors** (was point 3). Dropped as off-focus, treasury-
vertical: SAP-treasury SIs, treasury associations/events, banks.

Rule: anything Brisken already runs is an ASSET we use, never a task in
this plan. Each net-new move below carries "confirm with Dirk it is not
already running, then do it."

**A. SAP partner channel.**

- Already running (asset, not a task): OnePilot is live on the SAP
  Store, but only as two buyable listings (Market Data Hub + Trade
  Automation) per the 2026-06-17 audit; the MDH variants are sap.com
  marketing pages and Remittance / Bank Fee are not on any SAP channel
  (brisken.com only). The advisor surfaces OnePilot on the brand query.
- Net-new:
  1. **SAP co-sell / PartnerEdge "Sell"**: account-exec referrals + RFP
     bundling. Fits the 2025 cloud + embedded-AI direction; the bigger
     prize. Confirm if active.
  2. **SAP Store advisor AEO**: tune the existing listings so the
     advisor surfaces them for problem/category queries ("market data
     into SAP", "bank-fee automation"), not just "brisken". Captures
     in-marketplace demand where every visitor is an SAP customer.
  3. **ASUG** content / speaking, if not already active.

**B. Data-vendor partner channel** (the co-marketing / referral half;
reverse-sourcing stays in the cold engine, section 9C).

- Already running (asset, not a task): the integrations themselves (MDH
  governs Bloomberg / Refinitiv / 360T / OANDA / CME) and the
  per-vendor SAP-listed variants.
- Net-new:
  1. **Vendor app-portal listings**: Bloomberg Enterprise App Portal
     (325k+ Terminal users), LSEG partner program + Workspace SDK.
     Inbound visibility into the vendor's own customer base.
  2. **Vendor referral**: complementary and consumption-positive
     (OnePilot makes their feed usable in SAP), so their account /
     support teams can hand off "get our feed into your SAP".
  3. **Co-marketing**: joint "govern your [vendor] feed into SAP, no
     code" content, using the per-vendor SAP-listed variant as the unit.
- Gate: Dirk confirms which vendor relationships are active (gate 1).
