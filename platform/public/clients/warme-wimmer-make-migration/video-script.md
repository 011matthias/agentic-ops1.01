# Video Script -- Warme Wimmer Make.com Migration

## Target Duration: 3-4 minutes

---

### BEAT 1 -- Reframe and Authority (~40 seconds)

>> Screen: their Upwork job posting, scrolled to the job title and summary

SAY: Hi there, Nico here. I saw your posting for a Make.com specialist to take over from your current provider.

>> Highlight the line "migrate, stabilize, and maintain" in their posting

SAY: The real challenge here isn't the building. It's inheriting someone else's scenarios without breaking anything that your team depends on today.

---

### (continued)

>> Switch to my Upwork profile page, visible: Karlsruhe Germany, languages, availability

SAY: Quick context on why I'm a good fit for this specifically. I'm based in Karlsruhe, so same timezone, same business hours. German and English are both native for me.

>> Scroll down to the "Energy Sector Technology Trends" portfolio piece

SAY: I've also done work in the German energy sector, so the industry context isn't new to me. And Make.com is my daily driver for automation work.

---

### BEAT 2 -- Walkthrough (~2 minutes)

>> Open the proposal site: unpauseai.com/clients/warme-wimmer-make-migration/. Show the hero section with the four stat cards (5 Systems, 4 Phases, DE, 1 wk)

SAY: I put together a full proposal site walking through how I'd handle the migration. Let me run through it quickly.

>> Click sidebar item "2 - Your Systems" on the overview page. Show the three-zone grid (Field Operations, Accounting, Supporting Services)

SAY: Your stack has three layers. Hero handles field operations, LexOffice handles accounting, and then Mailgun, OpenAI, and S3 support the communications and file storage side. Make.com is the glue between all of them, and that's what makes the migration sensitive.

---

### (Solution page -- ~60 seconds)

>> Click "Solution" in the top nav bar. Solution page loads showing the hero section

SAY: The migration follows four phases. Let me walk through each one.

>> Click sidebar item "1 - Scenario Audit" on the solution page

SAY: Phase one is a full audit. Before I touch anything, I'd export every blueprint from your current account, map out which scenarios depend on which, and document all the API connections. The output is a scenario inventory and a dependency map.

>> Scroll down to the migration audit checklist download button

SAY: I actually built a structured audit checklist you can download here. It covers all five phases of the migration. It's yours to keep regardless of whether we work together.

>> Click sidebar item "2 - Phased Migration"

SAY: Phase two is the actual move. I'd migrate scenarios in dependency order, not all at once. Independent scenarios go first, then anything that depends on them. And the webhook URL cutover gets coordinated with your sysadmin as a scheduled window so you don't drop events.

>> Click sidebar item "3 - Parallel Validation"

SAY: Phase three is a parallel run. Where it's safe to do so, I'd keep the old scenarios active alongside the new ones for a few days. This catches data format differences and timing issues that only show up in production.

---

### (Timeline page -- ~30 seconds)

>> Click "Timeline" in the top nav bar. Timeline page loads

SAY: The full migration takes about four weeks.

>> Scroll through the week-by-week breakdown. Pause briefly on "Week 1: Audit"

SAY: Week one is the audit. Weeks two and three are the phased migration. Week four is stabilization -- that's the parallel run and error monitoring setup.

>> Scroll to sidebar item "5 - Week 5+: Maintain"

SAY: After that, it shifts to ongoing maintenance. Change requests, new builds, whatever your team needs. The hours flex down to match the actual workload.

---

### (Investment page -- ~15 seconds)

>> Click "Investment" in the top nav bar. Show the $30/hr hero and the "Why Above Range" section

SAY: On pricing -- I'm proposing $30/hr, which is above your posted range. The short version is: I'm local, I already know Hero and LexOffice, and migration work needs more care than a fresh build. The comparison table below breaks down how that stacks up.

---

### BEAT 3 -- Close (~15 seconds)

>> Click "Onboarding" in the top nav bar. Briefly show the form fields

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
