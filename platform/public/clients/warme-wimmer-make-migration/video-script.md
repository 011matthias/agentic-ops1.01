# Video Script -- Warme Wimmer Make.com Migration

## Target Duration: 3-4 minutes

---

### BEAT 1 -- Reframe (~45 seconds)

SAY: Hi there, Nico here. I saw your posting for a Make.com specialist to take over from your current provider, and I wanted to walk you through how I'd handle this.

SAY: The real challenge here isn't building new automations. It's inheriting someone else's work without breaking anything. Your team depends on these scenarios running every day -- Hero syncing with LexOffice, emails going out through Mailgun, files landing in S3. If something fails during the handover, that's missed invoices or lost data.

>> Show the proposal site overview page (index.html) with the system map

SAY: So the way I'd approach this is methodical. Audit first, then migrate in phases, then stabilize before taking over maintenance.

---

### BEAT 2 -- Structure (~90 seconds)

SAY: Let me show you the migration plan I've put together.

>> Scroll to "Migration Approach" section on solution page

SAY: Phase one is a full audit. I'd export every blueprint from your current provider's account, map out all the connections between Hero, LexOffice, Mailgun, OpenAI, and S3, and document what each scenario does. Before I change anything, I need to understand the full picture.

>> Scroll to "Your System Landscape" section

SAY: This matters because Make.com scenarios don't live in isolation. A webhook URL change in one scenario can break a downstream trigger in another. And API connections -- especially LexOffice with its 2 requests per second rate limit -- need careful handling during re-authentication.

SAY: Phase two is the actual migration. I'd move scenarios in groups, not all at once. Each group gets re-created in your new Make.com account, connections re-established, webhook URLs updated in coordination with your sysadmin, and tested individually before going live.

>> Scroll to timeline page showing the 4-phase breakdown

SAY: Phase three is a parallel run period. Where possible, I'd keep the old scenarios active alongside the new ones for a few days. This catches timing issues and data format differences that only surface in production.

---

### BEAT 3 -- Edge Cases (~45 seconds)

SAY: The main risk points in a migration like this are:

SAY: First, webhook URLs. Every scenario that uses a webhook trigger gets a new URL in the new account. If we don't update every source system at the same time, events get dropped. I'd coordinate this with your sysadmin as a scheduled cutover window.

SAY: Second, API re-authentication. Hero and LexOffice connections need fresh API keys or OAuth tokens in the new account. I'd set these up and test them before migrating any scenario that depends on them.

SAY: Third, data stores. If your current scenarios use Make.com data stores for caching or deduplication, those need to be exported and re-imported. Missing this means scenarios lose their memory of what's already been processed.

---

### BEAT 4 -- Extension (~30 seconds)

>> Scroll to "Ongoing Ownership" card on overview page

SAY: Once the migration is stable, I'd set up error monitoring so you get alerts when something fails instead of finding out days later. From there, I handle the ongoing work -- new statuses in Hero, email template changes, whatever comes up. The goal is that your team doesn't need to think about the automations at all.

---

### BEAT 5 -- Close (~15 seconds)

SAY: The full proposal is on the site with a detailed timeline, investment breakdown, and onboarding checklist. If this looks like a good fit, I'm ready to start with the audit this week. Happy to talk through any of it first.

---

## LOOM NOTES VERSION

- Migration != building from scratch. It's inheriting logic without breaking live systems.
- Phase 1: Full audit. Export blueprints, map dependencies (Hero, LexOffice, Mailgun, OpenAI, S3). Understand before changing.
- Phase 2: Phased migration. Move in groups, not big-bang. Re-establish connections, update webhooks, test individually.
- Phase 3: Parallel run. Old + new side by side to catch production-only issues.
- Risk 1: Webhook URL changes. Need coordinated cutover window with sysadmin.
- Risk 2: API re-auth. Fresh tokens for Hero + LexOffice before migrating dependent scenarios.
- Risk 3: Data stores. Export + re-import to preserve processing memory.
- After stabilization: error monitoring, ongoing maintenance, change requests.
- Full proposal site with timeline, pricing, onboarding checklist.
- Ready to start audit this week.
