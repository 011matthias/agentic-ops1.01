---
id: p006
slug: warme-wimmer-make-migration
prospect: "Warme Wimmer"
contact: "Raphael"
source: upwork
source_url: "https://www.upwork.com/jobs/~022037459187581558171"
project_title: "Make.com Migration, Stabilization & Ongoing Maintenance"
status: sent
track: 2
created: "2026-03-27"
sent: "2026-03-27"
reviewed: "2026-03-27"
value_estimate: "$30/hr, ~$3,000-5,000/month"
timeline: "Ongoing, start within 1 week"
tags: [make-com, migration, lexoffice, hero-software, maintenance, germany]
access_code: "warme-2026"
deliverables:
  letter: true
  video: true
  site: true
---

## What We Understood

You're switching Make.com providers and need someone to take full ownership of your existing automation infrastructure. The core challenge isn't building new scenarios from scratch; it's inheriting someone else's logic, understanding the dependencies between Hero Software, LexOffice, Mailgun, OpenAI API, and S3, and making sure nothing breaks during the handover.

Your team runs on these automations daily. A failed scenario means missed invoices, delayed notifications, or broken data sync between your field service operations in Hero and your accounting in LexOffice. The margin for error during migration is slim.

You also need someone who can handle the ongoing maintenance: status changes, email template tweaks, new workflow requests. Not a one-off contractor, but a long-term automation partner who understands your stack.

## Our Proposed Solution

### Phase 1: Audit and Documentation (Week 1)

Full inventory of every existing Make.com scenario in the current provider's account:
- Map all triggers, modules, and connections
- Document which scenarios are active vs. draft vs. broken
- Identify shared data stores, webhooks, and API connections
- Flag any scenarios with hardcoded credentials or environment-specific config

Deliverable: scenario inventory spreadsheet + dependency map showing how Hero, LexOffice, Mailgun, OpenAI, and S3 connect.

### Phase 2: Migration (Weeks 2-3)

Phased migration, not a big-bang cutover:
- Export blueprints from current account
- Re-create scenarios in the new Make.com organization
- Re-establish all API connections (Hero API, LexOffice API, Mailgun SMTP, OpenAI API keys, S3 buckets)
- Update webhook URLs across all source systems
- Test each scenario individually before activating

Critical: webhook URL changes need to be coordinated with your sysadmin to avoid dropped events during the switchover window.

### Phase 3: Stabilization (Week 4)

- Run all scenarios in parallel (old + new) for validation where possible
- Monitor execution logs for errors, timeouts, and data mismatches
- Set up error notification routing (email or Slack alerts on failure)
- Document each scenario with purpose, trigger conditions, and expected behavior

### Phase 4: Ongoing Maintenance (Continuous)

- Handle change requests (new statuses in Hero, email template updates in Mailgun)
- Monitor scenario health and execution quotas
- Proactive optimization (reducing operations count, improving error handling)
- Coordinate with your office team and sysadmin on system changes

## Timeline & Milestones

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Audit | Scenario inventory + dependency map |
| 2-3 | Migration | All scenarios live in new account |
| 4 | Stabilization | Error monitoring active, documentation complete |
| 5+ | Maintenance | Ongoing support, change requests, optimization |

## Investment

**Rate: $30/hr**

This is above your posted range of $15-25/hr. Here's why it's worth the difference:

1. I'm based in Germany, so there's zero timezone friction for your Grobenzell team. Same business hours, same language if needed, no async delays on urgent issues.

2. I have direct experience with both Hero Software and LexOffice integrations in Make.com. No ramp-up time learning your core systems.

3. Migration from another provider is higher-stakes work than building new scenarios. Getting it wrong means downtime for your team. The rate reflects the care required to do this without disrupting your operations.

At 20 hours/week, that's roughly $2,400/month. Once the migration stabilizes (after month 1-2), we can adjust hours down to match your actual maintenance needs.

## About UnpauseAI

We build and maintain automation infrastructure for businesses that depend on their workflows running reliably. Make.com is one of our primary platforms, alongside n8n for more complex orchestration. Based in Germany, working with European clients daily.

## Research Notes

**Prospect:** Warme Wimmer GmbH & Co. KG; renewable energy company (solar, geothermal, heating, climate systems) in Grobenzell, Bavaria. Founded 2004 by Tobias Wimmer. Meisterbetrieb (master craftsman business). 11-50 employees. Energy & Utilities sector.

**Hero Software:** Cloud-based field service management for craftsmen. Project planning, offers/quotes, invoicing, scheduling, mobile app. German market focus. API available.

**LexOffice (Lexware Office):** Leading German accounting software for SMBs. REST API with 2 req/sec rate limit. Handles contacts, invoices, credit notes. GoBD compliant. EUR only. Native Make.com module available.

**Client quality:** 5.0 rating on Upwork, $346K total spent, 48 hires (19 active), 13,093 hours. 100% hire rate. Has built custom ERP (OSNeo). Pays $40/hr for full-stack devs, $25/hr for PMs. Long-term relationships (1,269 hrs with one dev).

**Competition:** 50+ proposals submitted, avg bid $24.22, range $11.99-$50.00. No interviews started yet.
