# UnpauseAI ICP (Ideal Customer Profile)

Shared prerequisite for three uwi workstreams: u1 cold-email list filters, u3
LinkedIn recipes, u2 editorial buyer-intent queries. Derived 2026-07-22 from
three evidence layers (5-agent extraction, run wf_7981a3ef-8ed):

1. **Won engagements** (strongest): meji-media, brisken p1+p2, jochen/One
   Assessment, warme-wimmer.
2. **The 34-proposal Upwork corpus** (`platform/src/content/proposals/`) —
   what buyers actually asked for, with posted budgets.
3. **The optimize-model segments** (pricing-tiers + leadgen-portfolio
   scorers) — ASSUMPTION-tagged planning numbers, flagged as such.

Provenance discipline: OBSERVED = traced to a won engagement or a real
posting. ASSUMED = a model parameter awaiting validation. Never quote an
ASSUMED number to a prospect.

## The core persona (Route 2: B2B lead-gen retainer client)

The three B2B channels (cold email, LinkedIn, referral) target ONE persona
reached three ways (model finding, corroborated by the corpus):

| Trait | Value | Provenance |
|---|---|---|
| Decision-maker | Owner / MD / founder, bought DIRECT, no procurement layer | OBSERVED: every won deal (Gurmej owner, Dirk MD, Tobias/Irina founder+PM, Ibrahim owner-level) |
| Company size | SMB / Mittelstand, ~5-50 people; solo founders at the micro end | OBSERVED: won deals 11-50 or owner-run; corpus skews solo founders + small agencies |
| Trigger state | A BROKEN or manual existing process, not greenfield ambition: fired the prior contractor, outbound producing zero (Brisken: ~150 mailboxes, ~2M cold emails, 0 leads), leads silently dropping in a handoff, multi-day manual back-office ritual | OBSERVED: all won work is rescue/take-over; none is greenfield |
| What they buy | "One owner, end to end, ongoing" - takeover + rebuild + recurring operation, never a one-off artifact | OBSERVED: volabyg ask verbatim; wimmer migration->maintenance; meji rescue->retainer |
| Industry | No single vertical. Won set spans events marketing, SAP treasury, HVAC/renewables, construction. The COMMON factor is an owner running revenue-relevant process on low-code + spreadsheets | OBSERVED |
| Stack markers (list filters) | Make.com / n8n / Zapier present or wanted; Google Sheets as the data plane; Instantly/Apollo for outbound-minded buyers; GHL in agency-land | OBSERVED: n8n or Make in ~10/12 and 9/12 of corpus batches; Sheets in 6/9 |
| Geography | UK + US for cold email (UWG §7 bans DE cold). DE/DACH reachable ONLY via LinkedIn, referral, content, demo-first — where German language + CET is decisive: both German-language proposals in batch 1 were the only sent/won ones | OBSERVED constraint + OBSERVED signal |
| Budget reality | Won pricing is modest: $30/hr (wimmer, ~$2,400/mo), $1,000-1,500/mo retainer (meji), EUR14/hr engagement tabs (Brisken family). Upwork posted budgets anchor at hobby level ($10-600) and every proposal absorbed a large gap via fixed-price + de-risked entry (free phase 0, EUR850 audit-first, $120 phase 1) | OBSERVED |
| Expansion motion | Land-and-expand inside one account is the strongest revenue path: Brisken spawned three separately-billed workstreams; meji runs the hourly->retainer->fixed ladder | OBSERVED |

## Segment bands (tier mapping — ASSUMED, validate against real quotes)

From the pricing-tiers scorer; the tier MENU is unreleased pending u5's
scope-to-deliverables mapping:

| Segment | Size (pool) | Tier | Price | Who this plausibly is |
|---|---|---|---|---|
| Micro | 150 prospects | good EUR650/mo thin | solo founders / one-person operators (7/12 of one corpus batch) who anchor low but convert on de-risked entry |
| Core | 95 prospects | better EUR1850/mo | the won-deal persona above; meji's real $1-1.5k/mo and wimmer's ~$2.4k/mo bracket this price point (OBSERVED corroboration) |
| Scale | 30 prospects | best EUR6300/mo full | funded/scaling orgs (the corpus's agency-intermediary + enterprise outliers). LEAST validated: no won deal at this level; the corpus's closest analog is the EUR1,800-2,200/mo agency retainer ask |

## Route 1 persona (local SMB care — fill only, never outbound hours)

Owner-run local service business (Handwerk first: pool 60/yr ASSUMED),
Karlsruhe-region, buys a EUR1,200 build + EUR200/mo care annuity. Reached via
demo-first/AEO proof, never cold email (UWG §7). The 5 live prototype sites
are the pitch asset. OBSERVED corroboration: warme-wimmer IS this persona at
larger scale (Meisterbetrieb, renewables), won with German language + niche
stack familiarity.

## What buyers ask for (demand taxonomy → u2 queries + offer copy)

Ranked by corpus frequency:

1. **Cold outreach / lead-gen pipelines** (~17/33 asks): list building,
   enrichment (Apollo), verification (NeverBounce), sequences (Instantly),
   reply handling, speed-to-lead. Validates the Route-2 pivot: demand showed
   up unprompted across geographies.
2. **AI-in-the-loop ops automation**: support triage with confidence gating,
   classification + personalization layers on Claude/OpenAI, human-approval
   gates before irreversible actions.
3. **Back-office integration rescue**: CRM<->accounting sync, migration
   takeovers, audit + stabilization of inherited automations.
4. **Compliance-shaped builds**: GDPR-aware flows, DE-language support,
   policy-constrained sends (Amazon SP-API, healthcare). GDPR-as-lived-
   experience won healthcare/wellness asks in the corpus.

## Discriminators we win with (use in copy, sequences, content)

- **EU/CET/GDPR by design** — cited as an edge in nearly every proposal,
  including for US buyers (timezone overlap); decisive for DE deals.
- **Rescue posture**: "we take over the broken thing and own it end to end",
  not "we build you a new thing".
- **Fixed scope, de-risked entry**: audit-first or thin phase 1 absorbs the
  budget-anchor gap.
- **Client-owned infrastructure** (no vendor lock-in) — explicit selling
  point in 4+ corpus proposals.
- **Recurring by default**: every engagement shape converts to retainer/care.

## Anti-ICP (do not spend acquisition hours on)

- Hobby-anchored buyers with no expansion path (sub-$500 one-off postings
  UNLESS the de-risked entry leads to a care/retainer ladder).
- Greenfield speculative platforms (the corpus's unsent drafts cluster here).
- Pure staff-augmentation hourly seats (no ownership, no expansion).
- Any DE-target cold-email ask (UWG §7 — legally fenced, guard-enforced).

## Channel filter derivation (operational)

- **u1 Apollo/cold**: UK+US; owner/founder/MD titles; 5-50 employees;
  technographic markers Make/n8n/Zapier/GHL/Instantly where available;
  exclude DE. MX pre-filter (Mimecast = drop) before verification.
- **u3 Sales Nav**: same persona, DE INCLUDED (LinkedIn is DE-legal);
  three-axis radar recipe shape from the Brisken targeting method;
  "changed jobs in 90 days" as the native trigger filter.
- **u2 buyer-intent queries**: derive from the demand taxonomy, phrased as
  the persona's problem language ("leads dropping between Facebook and
  sheet", "Make.com contractor left", "cold email getting no replies",
  "reconciliation takes days") — not our solution language.

## Open validation questions (feed results back to the scorers via re-pin)

1. Does the core persona bear EUR1,850/mo? (meji + wimmer bracket it:
   plausible; not yet proven at the tiered menu's framing.)
2. Does the scale segment exist for us at EUR6,300/mo? (No won evidence;
   highest-risk tier assumption.)
3. Are the channel pools real? (cold 50 / LinkedIn 30 / referral 15 / content
   25 — all ASSUMED; u4's ledger is the referral test.)
4. Proposal-send drop-off: 11/12 of one corpus batch died at status:draft,
   never sent. The bottleneck was OUR send cadence, not prospect rejection —
   worth remembering when reading "Upwork didn't work" as evidence.
