# Video Script -- Warme Wimmer Make.com Migration

## Target Duration: 3-4 minutes

---

### BEAT 1 -- Reframe and Authority (~40 seconds)

>> Their job posting

SAY: Hi there, Nico here. I saw your posting for a Make.com specialist to take over from your current provider.

>> Highlight "migrate, stabilize, and maintain"

SAY: The real challenge here isn't the building. It's inheriting someone else's scenarios without breaking anything that your team depends on today.

---

### (continued)

>> My Upwork profile

SAY: Quick context on why I'm a good fit for this specifically. I'm based in Karlsruhe, so same timezone, same business hours. German and English are both native for me.

>> Scroll to Energy Sector portfolio piece

SAY: I've also done work in the German energy sector, so the industry context isn't new to me. And Make.com is my daily driver for automation work.

---

### BEAT 2 -- Walkthrough (~2 minutes)

>> Open proposal site, hero + stat cards

SAY: I put together a full proposal site walking through how I'd handle the migration. Let me run through it quickly.

>> Sidebar: "Your Systems"

SAY: Your stack has three layers. Hero handles field operations, LexOffice handles accounting, and then Mailgun, OpenAI, and S3 support the communications and file storage side. Make.com is the glue between all of them, and that's what makes the migration sensitive.

---

### (Solution page -- ~60 seconds)

>> Nav: Solution

SAY: The migration follows four phases. Let me walk through each one.

>> Sidebar: "Scenario Audit"

SAY: Phase one is a full audit. Before I touch anything, I'd export every blueprint from your current account, map out which scenarios depend on which, and document all the API connections. The output is a scenario inventory and a dependency map.

>> Scroll to download button

SAY: I actually built a structured audit checklist you can download here. It covers all five phases of the migration. It's yours to keep regardless of whether we work together.

>> Sidebar: "Phased Migration"

SAY: Phase two is the actual move. I'd migrate scenarios in dependency order, not all at once. Independent scenarios go first, then anything that depends on them. And the webhook URL cutover gets coordinated with your sysadmin as a scheduled window so you don't drop events.

>> Sidebar: "Parallel Validation"

SAY: Phase three is a parallel run. Where it's safe to do so, I'd keep the old scenarios active alongside the new ones for a few days. This catches data format differences and timing issues that only show up in production.

---

### (Timeline page -- ~30 seconds)

>> Nav: Timeline

SAY: The full migration takes about four weeks.

>> Scroll through weeks

SAY: Week one is the audit. Weeks two and three are the phased migration. Week four is stabilization -- that's the parallel run and error monitoring setup.

>> Sidebar: "Week 5+"

SAY: After that, it shifts to ongoing maintenance. Change requests, new builds, whatever your team needs. The hours flex down to match the actual workload.

---

### (Investment page -- ~15 seconds)

>> Nav: Investment

SAY: On pricing -- I'm proposing $30/hr, which is above your posted range. The short version is: I'm local, I already know Hero and LexOffice, and migration work needs more care than a fresh build. The comparison table below breaks down how that stacks up.

---

### BEAT 3 -- Close (~15 seconds)

>> Nav: Onboarding

SAY: The onboarding page has a checklist of everything I'd need to start the audit. If this looks like a good fit, I can start this week. Happy to talk through any of it first.

---

## LOOM NOTES VERSION

- Open on their job posting. "Migration != building from scratch. It's inheriting logic without breaking live systems."
- My profile: Karlsruhe (same timezone), German native, energy sector portfolio piece, Make.com daily.
- Overview page: 5 systems, 4 phases. Show the three-zone grid (Hero, LexOffice, Mailgun/OpenAI/S3).
- Solution page -- 4 phases:
  - Audit: export blueprints, map dependencies, document connections. Download checklist artifact.
  - Migration: dependency order, not big-bang. Webhook cutover coordinated with sysadmin.
  - Parallel run: old + new side by side to catch production-only issues.
- Timeline page: 4 weeks. Week 1 audit, weeks 2-3 migrate, week 4 stabilize, week 5+ maintain.
- Investment: $30/hr, above range. Local, knows their systems, migration risk premium. Comparison table.
- Close: onboarding page has day-1 checklist. Ready to start this week.
