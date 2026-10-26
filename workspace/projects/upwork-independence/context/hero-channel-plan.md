# HERO x n8n channel plan (uwi u9)

Drafted 2026-10-26 on owner direction ("lets tackle the HERO point and plan
this out completely"), after the owner ruled out Make as a growth platform
(decision 8 in `../status/uwi-general.md`). Status roll-up:
`../status/u9-hero-n8n-channel.md`. Every external fact below was read live on
2026-10-26; the source follows it.

## Why this channel

The owner's ask is access to users of a business system we can integrate.
HERO, the German operating software for trade businesses, is the one ecosystem
where four facts line up:

1. **The n8n slot is empty.** No n8n node for HERO exists on npm:
   `n8n-nodes-hero`, `n8n-nodes-hero-software`, `n8n-nodes-herosoftware`,
   `@hero-software/n8n-nodes-hero` and `n8n-nodes-hero-handwerk` all return
   404, and a keyword search for `n8n-community-node-package hero` finds none.
   Make, by contrast, has a HERO app "supported and maintained by the official
   vendor HERO Software" (5 triggers, 11 actions, 1 search;
   make.com/en/integrations/hero-software). HERO already backs automation
   platforms; nobody serves its n8n users.
2. **HERO lists no implementers.** Its partner page shows 13 software and
   interface partners, no agency that builds automations for HERO customers,
   and no mention of n8n, Make or Zapier (hero-software.de/partner).
3. **HERO has partner doors that cost nothing to try**, all through
   kooperationen@hero-software.de: Schnittstellenpartner (integrations),
   Community-Experte (webinars in the HERO community), Vorteilswelt (offers to
   HERO customers) and Tippgeber (referrals)
   (hero-software.de/kooperationen/partnerschaften).
4. **We have production proof.** Wärme Wimmer runs its mail triage and its
   status and task workflows on n8n against the HERO GraphQL API (v9 in
   production), and the API's quirks are already proven (memory
   `reference_ww_hero_api_quirks`). WW's operating knowledge lives in the
   `akkton/agentic-ops` clone (memory `project_warme_wimmer_takeover`).

Size of the pool: HERO's own figure is "mehr als 10.000 Handwerker" in its
network; third-party sources range from 8,000+ (ki-syndikat.de) to 20,000+
users (starting-up.de). There is no verified customer count; treat it as a
pool in the thousands, all DACH trade businesses.

## What we sell

The program's standard shape: fixed setup plus monthly care, with care scoped
by class, not hours (the Brisken licence logic: the software doing the wrong
thing is covered; new function and changes forced by HERO's API are quoted
separately). Packages, each marked with whether WW proves it:

| Package | What it does | WW proof |
|---|---|---|
| Mail to HERO | Inbox triage onto the right project: logbook entry, task for the responsible person, attachments uploaded and linked | Yes, live (W2-04) |
| Status and tasks | Status moves on task, document and payment events; reminders after appointments; overdue tasks flag the project | Yes, live (W2-01 to W2-10) |
| Lead intake | Website form to HERO contact and project via the HERO Lead API | No; new build on a documented API |
| Sales follow-up | Stage-based customer mails, follow-ups, archiving | In test at WW (W2-14), not yet proof |
| Care | Error handler and watchdog as standard, fixes, monthly report | Pattern runs at WW |

Prices are owner decision D3. Anchors already decided elsewhere: local care
EUR200/mo (decision 7), the Brisken licence at EUR600/mo, the pricing-tiers
menu at 650 / 1,850 per month. Recommended shape: a fixed-price
"HERO-Automations-Check" as the entry, a fixed price per package, monthly care.

**Delivery model (fixed, not a decision):**
- The client owns its n8n: n8n Cloud in the client's name (Starter EUR20/mo or
  Pro EUR50/mo, billed annually; n8n.io/pricing) or self-hosted on the
  client's server. We never run one shared instance for several clients.
  Secondary sources read the n8n Sustainable Use License as excluding that
  (nordflux.de, community.n8n.io); confirm against the official license text
  before the first client. It also matches the repo rule of no shared
  services between clients.
- The client requests its own HERO API key from HERO support ("Trete dafür
  bitte mit unserem Support in Kontakt", hero-software.de/api-doku/graphql-guide).
  Whether API access costs extra or depends on the HERO plan is UNVERIFIED and
  is question 2 to HERO below.
- Every delivery is built from the template kit (phase 2) and improves it, so
  hours per client fall (the u5 principle).

## Phase 0: gates and first contact (week 1)

Owner decisions:
- **D1 identity of the node.** Recommendation: npm package
  `n8n-nodes-hero-software` (free on 2026-10-26; plain "hero" is ambiguous, an
  `n8n-nodes-influencer-hero` already exists), in its own public GitHub repo
  under the UnpauseAI identity, README linking unpauseai.com. Public is
  required anyway: n8n verification needs npm provenance from GitHub Actions.
- **D2 WW as a named reference.** Ask Raphael whether WW may be named in the
  case study, the n8n Experts application and the HERO pitch. Fallback:
  anonymised ("SHK-Meisterbetrieb in Bayern, 11 bis 50 Mitarbeiter").
- **D3 package prices** (see above).

First contact with HERO (owner sends; drafted on request): one email to
kooperationen@hero-software.de, leading with the WW production proof (named
only if D2 is yes), asking:
1. May a third party publish an n8n node for the HERO API, and under what
   terms (naming, logo, "official" wording)?
2. Which HERO plans include API access, and does a key cost extra?
3. Rate limits, webhooks (the docs list none), and whether v9 is the current
   endpoint (the public guide still shows v7).
4. A test account or developer key for building and testing the node.
5. Interest in listing us on the partner or Schnittstellen page, a
   Community-Experte webinar, and a Vorteilswelt offer.

**IP line:** the node is written fresh from HERO's public GraphQL schema. No WW
code, rules, IDs or data go into it; WW know-how (the quirks) does.

## Phase 1: build the node (weeks 1-4)

Agent-built, owner reviews. Effort ~15-20 agent-hours (ASSUMED, no prior node
build to measure against). Build starts in parallel with the HERO email;
**publishing waits** for HERO's answer to question 1, or, after two weeks of
silence, ships without HERO's logo and with a "not affiliated with HERO
Software" line.

Scope v1 mirrors HERO's own Make app plus what WW needed:
- Credential: API key (Bearer), base URL field.
- Triggers (polling; no webhooks documented): new project, project status
  changed, new contact, new document, new appointment.
- Actions: contact create / get / update / search; project create / get /
  search (archived projects through `project_match`, since `project_matches`
  drops them); logbook entry add; task create / update / complete; file
  upload and link to a project (separate upload endpoint, not GraphQL); raw
  GraphQL query as the escape hatch.
- Quirks handled inside the node: calendar times are Berlin wall-clock
  labelled `+00:00`; task titles reject `;`; HERO rejects mp4 uploads; back
  off on 429.

n8n verification requirements (docs.n8n.io, "submit community nodes"):
`n8n-node` scaffold, no runtime dependencies, lint passes, package name
`n8n-nodes-*`, keyword `n8n-community-node-package`, README, published to npm
by a GitHub Actions workflow with provenance (mandatory since 2026-05-01), UX
guidelines followed. Submit at creators.n8n.io/nodes. Verified nodes are
discoverable from the nodes panel inside n8n; unverified community nodes run
on self-hosted n8n only.

Testing: unit tests on request and response mapping; live writes only on a
HERO test account (question 4) or a 14-day HERO trial. Read-only checks
against WW's tenant with the owner's own key are allowed; writes there are
not (invasive-action gate).

## Phase 2: templates and proof (weeks 3-6)

- Three n8n templates generalised from WW patterns, submitted to n8n's
  template library through the Creator Hub: inbox to HERO logbook and task
  with AI triage; website form to HERO contact and project; status-change
  follow-up tasks with an overdue flag.
- A German case study (after D2): what changed at WW, measured numbers only
  (W2-04 execution counts, mails routed per month), never estimates.
- A landing page for the packages, the node and contact, on unpauseai.com
  (live site = `akkton/unpauseai-web`, published by its PR flow).

## Phase 3: distribution (weeks 5-12)

All inbound or partner-mediated, so the UWG §7 fence never applies.
- HERO: partner-page listing, a Community-Experte webinar ("Automatisierung im
  Handwerksbetrieb mit HERO und n8n"), a Vorteilswelt offer (the
  HERO-Automations-Check at a HERO-customer price), Tippgeber terms if HERO
  refers.
- n8n: verified node in the nodes panel, templates in the library, a release
  post in the n8n community forum, and an update to the n8n Experts waitlist
  entry (every HERO client on n8n counts toward its 3-customer bar).
- Referral: one intro ask to Raphael and Tobias after D2 (trade owners know
  each other through the Innung).
- LinkedIn posts on the owner's profile: node release, then the case study.

## Phase 4: sell and deliver (from the first enquiry)

First call, then the HERO-Automations-Check, then a package, then care. Hours
per client are recorded from client one; the kit gets fixed before the next
close if a delivery runs long.

## Measures and tripwires

- Weekly, read-only: npm weekly downloads of the package
  (`api.npmjs.org/downloads/point/last-week/<package>`; mirrors and bots
  inflate it, so read the trend, not the level), HERO reply status, enquiries
  by source.
- Milestones: node published by end of week 4; verification submitted the
  same week (n8n's review time is UNVERIFIED); first 3 qualified conversations
  by week 10; first paid HERO client by week 12.
- Week-12 tripwire: zero qualified conversations and no HERO listing or
  webinar means stop investing beyond maintenance. The node stays published as
  a passive asset; it costs nothing to keep.

## Risks

- **HERO's terms forbid a public node or API access costs extra.** Question 1
  and 2 answer this before anything is published. If forbidden, the templates
  use n8n's HTTP Request node and the offer runs as a service only.
- **HERO publishes its own n8n node** (it maintains the Make app). Offer in the
  first email to build it with them or hand it over; the implementer slot
  stays ours either way.
- **HERO OS Plus ships "Automationen mit HERO Copilot"** (heise.de, from
  EUR299/mo). That covers rules inside HERO. Our packages are cross-system:
  inbox, accounting, website forms, AI triage, alerting.
- **n8n declines verification.** The node still installs on self-hosted n8n;
  Cloud clients then get the templates built on HTTP Request.
- **WW declines naming.** The anonymised case still carries the measured
  numbers.
- **Capacity.** The agent builds; the owner's hours go to the HERO contact,
  review and sales calls, inside the program's 5-7 h/wk.
