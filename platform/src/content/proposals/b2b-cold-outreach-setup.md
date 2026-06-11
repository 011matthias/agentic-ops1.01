---
id: p028
slug: b2b-cold-outreach-setup
prospect: Anonymous B2B operator (Moldova)
contact: TBD
source: upwork
source_url: ""
project_title: "B2B Cold Outreach System Setup: LinkedIn + Email from Scratch"
status: draft
track: 1
created: "2026-06-11"
sent: null
value_estimate: "$600-1,000 ($40/hr, est. 15-25h)"
timeline: "2-4 weeks"
tags: [cold-outreach, lead-generation, linkedin, sales-navigator, phantombuster, apollo, instantly, icp]
access_code: ""
deliverables:
  letter: true
  video: true
  site: false
research:
  prospect_company: "Anonymous (posting discloses no company name; MDA is the ISO code for Moldova)"
  prospect_industry: "B2B, sector undisclosed; likely founder/operator stage given $2.4K total Upwork spend across 17 hires"
  prospect_location: "Chisinau, Moldova"
  prospect_contact: "TBD (not named in posting)"
  prospect_systems:
    - "LinkedIn Sales Navigator"
    - "PhantomBuster"
    - "Apollo.io"
    - "Instantly.ai"
    - "email outreach tools (unspecified beyond Instantly)"
  prospect_pain_points:
    - "No cold outreach system exists yet; needs full setup from scratch including account configuration, ICP definition, list sourcing, and workflow prep"
    - "Wants 500 targeted LinkedIn DMs in two weeks, which collides with LinkedIn's practical per-account weekly caps; achievable as stated only for first-degree connections, otherwise needs a connect-then-message ramp"
    - "Needs a clean, validated email list built in parallel for future outreach; a distinct deliverable from the DM campaign"
    - "Wants a structured and scalable process, not a one-off task"
  job_language_echoes:
    - "set up my cold outreach system from scratch"
    - "account setup, ICP list building, lead sourcing, and outreach workflow preparation"
    - "500 targeted people through LinkedIn DMs within two weeks"
    - "clean lead list with validated email addresses for future outreach"
    - "how you would use these tools together and how each tool contributes to the workflow"
    - "structured and scalable process"
    - "practical experience, understands B2B outreach"
  location_advantage: ""
  relevant_proof_points:
    - "Live Instantly.ai operation in production for a client: 3 active campaigns, multi-domain sending, sequence-step delays calibrated against the Instantly API spec"
    - "Domain and mailbox provisioning from scratch for a client: domain registration, Google Workspace secondary domain, SPF/DKIM/DMARC, Instantly connection with warm-up"
    - "Apollo.io ICP filter specification: multi-set people-search filters (role, company size, geography, exclusions), sample-validated 200 contacts before the full pull"
    - "Email verification pipeline with NeverBounce: deliverable/catch-all/invalid tiering for bounce-rate control on live campaigns"
    - "Found and fixed a sequence-delay bug across 3 live campaigns by reading the Instantly API spec directly"
  budget_gap: "Client's average Upwork spend is about $140/hire ($2.4K across 17 hires), but the posting is marked Expert and says higher rates are acceptable. Quoted $40/hr at an estimated 15-25 hours ($600-1,000 total); addressed in the Investment section."
  profile_cherry_picks:
    - "Live client cold-outreach operation is the strongest proof against the anti-AI-response filter: it answers the experience ask with a running system, not credentials"
    - "Apollo ICP filter methodology answers the explicit 'how do the tools work together' question at operator depth"
    - "From-scratch domain/mailbox/warm-up runbook maps literally onto the 'account setup' deliverable in the posting"
    - "Naming LinkedIn's real weekly caps converts the riskiest requirement (500 DMs in 2 weeks) into the clearest practical-experience signal"
---

## What We Understood

You want a cold outreach system set up from scratch: account setup, ICP list building, lead sourcing, and outreach workflow preparation, using LinkedIn Sales Navigator, PhantomBuster, Apollo, and Instantly. The first goal is around 500 targeted people reached through LinkedIn DMs within two weeks, with a clean, validated email list built in parallel for future outreach.

That is one pipeline with two outputs: messages going out on LinkedIn now, and an email asset you can run campaigns on later. I run exactly this stack for a client today, so the plan below comes from a live system, not a tutorial.

## Our Proposed Solution

Each tool has one job, and the order matters:

**Sales Navigator** is where the ICP gets precise. We define the target (role, company size, geography, exclusions) as saved searches, so the list is reproducible instead of a one-off export.

**PhantomBuster** runs the LinkedIn side: exporting the Sales Navigator results, then sending connection requests and DMs on a schedule that stays inside LinkedIn's tolerances. This is the part where practical experience matters most. The working numbers: roughly 100 connection requests and 50 to 80 automated DMs per week per account are sustainable on a healthy, warmed account. So 500 DMs in two weeks is realistic as stated if the targets are already first-degree connections (about 35 a day). For cold prospects, the honest plan is a phased ramp: connection requests go out first, DMs follow each acceptance, and the 500 mark lands over three to four weeks instead of two. Pushing past those caps is how accounts get restricted, which costs far more than the extra two weeks.

**Apollo** enriches the same people with verified work emails and firmographic data, and extends sourcing beyond LinkedIn where the ICP allows it.

**Email verification** (NeverBounce or similar) tiers every address into deliverable, catch-all, or invalid before anything is saved. That is what makes the lead list "clean" rather than just long.

**Instantly** is the future-outreach infrastructure: sending domains separate from your main domain, SPF/DKIM/DMARC authentication, mailbox warm-up started on day one so the email channel is ready the moment you want to use it.

## How It Works

1. Define the ICP together and lock it as Sales Navigator saved searches
2. Configure PhantomBuster: account connection, safe rate limits, export and DM phantoms
3. Pull and enrich the list through Apollo, verify every email, dedupe and tier the output
4. Launch the LinkedIn sequence: connection ramp plus DMs, monitored daily against account health
5. Stand up Instantly: domains, authentication, mailboxes, warm-up, so future email outreach starts warm

## Timeline & Milestones

| Phase | When | What happens |
|-------|------|--------------|
| Setup | Week 1 | Accounts configured, ICP locked, first list pulled and verified, Instantly warm-up started |
| Launch | Week 2 | LinkedIn outreach running at safe volume; DM target hit in full if targets are first-degree |
| Ramp | Weeks 3-4 | Connection-based DM volume completes the 500; validated email list delivered; handover |

## Investment

$40 per hour, estimated 15 to 25 hours for the full setup, so $600 to $1,000 total. Hourly means you pay for actual time, and the estimate is the cap I work against, not a floor. The estimate covers everything above: accounts, ICP, list building, verification, the LinkedIn campaign launch, and the Instantly foundation. Tool subscriptions (Sales Navigator, PhantomBuster, Apollo, Instantly, verification credits) are billed to your own accounts, which also means you own everything when we are done.

## About UnpauseAI

I work within UnpauseAI, an EU-based automation consultancy. Cold outbound is a named capability, not a side skill: we run a live multi-domain Instantly operation for a client today, with ICP-filtered Apollo sourcing, verified lists, and sequence calibration done against the Instantly API directly. English and German fluent.

## Research Notes

Anonymous posting from Chisinau, Moldova. The PS line filters out AI-generated applications, so the letter and video lead with operator judgment: the LinkedIn weekly-cap reality is the differentiator most bidders will not name. Hourly posting at Expert level; client's per-hire average is low, so the quote stays in the $600-1,000 band. Proof points describe live client work without identifiers.
