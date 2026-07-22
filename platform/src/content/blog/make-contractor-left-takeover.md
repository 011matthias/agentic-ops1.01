---
title: "Your Make.com Contractor Left: Taking Over an Automation You Didn't Build"
slug: make-contractor-left-takeover
date: "2026-07-22"
category: Process
excerpt: "The takeover order that keeps inherited automations alive: secure access, freeze changes, map what exists, watch it run, then stabilize before you touch a single module."
---

When the person who built your Make.com scenarios leaves, the automations keep running on borrowed time. The takeover order that works: secure access first, freeze all changes, map what actually exists, watch it run for a full cycle, and only then stabilize and extend. Skipping straight to "let's improve it" is how inherited automations die.

We do takeover work on Make.com, n8n, and Zapier stacks; this is the sequence we follow on every one.

## The first 48 hours: access, then freeze

Two things matter immediately, and neither is technical brilliance.

**Get the account under your control.** If the scenarios live in the contractor's personal Make.com account, they can vanish when that account closes or the card behind it expires. Move scenarios into an organization account you own, or at minimum get owner access transferred. Then rotate every credential the contractor could still use: API keys, connection logins, webhook URLs they might have copied.

**Freeze changes.** No edits, no "quick fixes," no renaming. A running automation you don't understand is an asset; a half-edited one is an outage. The freeze holds until the map (next section) exists.

## Map what actually exists

Make.com hides more surface area than the scenario list suggests. Inventory all of it:

- **Scenarios**: for each one, note the trigger (webhook, schedule, watch module), the systems it touches, and when it last ran successfully.
- **Connections**: which accounts they authenticate as. Personal Gmail connections in business automations are a common and nasty surprise.
- **Data stores**: Make's internal databases. These often hold state the scenarios depend on, and they don't show up unless you look.
- **Webhooks**: what external systems point at them. A webhook URL is an unlisted door into your automation.
- **Off-platform pieces**: Google Sheets acting as databases, Apps Script glue, external APIs with their own billing.

You don't need to understand the logic yet. You need to know the blast radius of every moving part.

## Watch it run before you change it

Make.com's execution history is the closest thing you have to documentation. Let the stack run for at least one full business cycle and read what it did: which scenarios fire daily versus monthly, which ones error and self-recover, which incomplete executions pile up quietly. A scenario that has been failing for three weeks tells you either it matters and nobody noticed, or it never mattered at all. Both are load-bearing facts.

## Triage: what to fix in what order

| Symptom | Risk | First move |
|---|---|---|
| Scenario errors on every run | Data is being lost right now | Fix before anything else |
| Scenario is off and nobody knows why | Hidden dependency or a deliberate kill | Investigate before re-enabling; never just switch it on |
| Connections authenticate as the leaver | Total stoppage when the account closes | Migrate to owned accounts now |
| Webhooks point at test or personal endpoints | Data leaving silently | Re-point and rotate URLs |
| No documentation anywhere | Every future change is slow and risky | Write the map as you triage; do not schedule "documentation later" |

## Stabilize, then extend

Once the map exists and the erroring scenarios are fixed, set a baseline: every scenario either runs clean or is deliberately off, and failures notify a human (Make's error handling plus an email or Slack alert covers this). Document each scenario as you touch it, not in a separate documentation project that never happens.

Only after that baseline holds do new features make sense. Building on an unstable inherited stack multiplies the mess; the feature you add today becomes the thing the next person can't untangle.

## When to bring in help

If the stack touches revenue (lead routing, invoicing, order flow) and nobody on your team can read a Make.com scenario, the takeover is worth professional hands. What to look for in whoever does it: they should start by asking for read access and execution history, not by proposing a rebuild. Rebuilds are sometimes right, but anyone who reaches that conclusion before mapping what exists is guessing at your expense.
