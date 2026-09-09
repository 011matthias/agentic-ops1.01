# Meji Media: Handover Guide for Matthias

**Prepared by:** Nico Neumann
**Date:** 2026-05-07
**Status:** Live, operational, in transition. You're taking over.

This is the one document you read end-to-end before doing anything else. It covers the people, the system, the current state, the history that matters, what's overdue, and your first month. Everything is sourced from `infrastructure.yaml`, the comms log, and the Upwork threads (cross-checked against screenshots dated 2026-05-06).

There are two companion files in this folder:
- `intro-message-to-gurmej-jess.md`: the Upwork message I'll send to introduce you and ask Gurmej to add you to the Make.com org
- `first-two-weeks.md`: the action checklist version of Section 9 here, broken out for day-by-day tracking

---

## Table of Contents

1. [Read this first: where things actually stand right now](#1-read-this-first-where-things-actually-stand-right-now)
2. [What Meji Media is, and what we built](#2-what-meji-media-is-and-what-we-built)
3. [The people](#3-the-people)
4. [The two Upwork threads](#4-the-two-upwork-threads)
5. [The system, end to end](#5-the-system-end-to-end)
6. [Voice rules and the B1.5 live-system gate](#6-voice-rules-and-the-b15-live-system-gate)
7. [The history that matters](#7-the-history-that-matters)
8. [Open questions waiting on the client](#8-open-questions-waiting-on-the-client)
9. [Your first 48 hours and first two weeks](#9-your-first-48-hours-and-first-two-weeks)
10. [The next 30, 60, 90 days](#10-the-next-30-60-90-days)
11. [Access checklist](#11-access-checklist)
12. [Tools and patterns you inherit](#12-tools-and-patterns-you-inherit)
13. [What's configurable, and where](#13-whats-configurable-and-where)
14. [Things not to do](#14-things-not-to-do)
15. [When to pull me back in](#15-when-to-pull-me-back-in)

---

## 1. Read this first: where things actually stand right now

The most urgent thing on this client right now is a reply to Gurmej. He has chased me three times on the Instantly thread without getting an answer:

- 2026-04-29 14:24 BST: "Hi Nico did you take a look at this?"
- 2026-05-05 14:04 BST: "you did say you would get back to me about a week ago on this? I hope all is ok?"
- 2026-05-06 12:12 BST (yesterday): "Hi Nico" (content-free, third time of asking)

I'm sending the introduction message to him today (see `intro-message-to-gurmej-jess.md`) which closes that loop and hands him over to you. You picking up from that point is what makes the silence stop being a problem. Same-day reply when you accept the Make.com org invite is a strong way to open the relationship.

Beyond the Gurmej thread, here's what's true:

- The four Christmas/automation scenarios (A0, A1, A2, A3) are running clean. A3 has been healthy since the 2026-04-27 fix landed.
- Jess sent a single chase on 2026-05-05 11:40 BST asking about the Gmail send-limits research. The deliverability + scaling report that answers her question went live on 2026-04-27 (PR #102, force-deployed via `tools/vercel-force-deploy.sh`) at `unpauseai.com/docs/meji-media/scaling` (access code `meji2026`), but I never sent her the link. I'm sending it today as part of the introduction.
- The Instantly logins are in hand: `gurmej@mejimedia.com / <ASK-NICOLAS-OFFLINE>`. All 10-11 warmed Instantly domains are Meji-owned. Try them when you have access. If they don't work, ask Gurmej to verify or reset.
- One small loose end on the live system: the `developer_bcc` field in Pipeline Config (DS 153173) still points at a deactivated mailbox. A1 sends customer emails fine but emits status-2 warnings on every send. Cleanup is a B1.5-gated change you can take whenever you're ready.

That's the snapshot. The rest of this guide gives you what you need to act on it.

---

## 2. What Meji Media is, and what we built

Meji Media runs shared Christmas party nights at three UK venues: the ICC in Birmingham, the ICB in Wolverhampton, and the Empire Banqueting Hall in Leicester. Their customers are companies and groups of 5-50 guests browsing christmasofficeparty.co.uk, picking a venue, and submitting an enquiry form. The product is a themed party night that multiple groups attend together. **It is not private venue hire**, and treating it as private venue hire is the single fastest way to get a customer email rejected by Gurmej.

What we built for them is a four-scenario Make.com pipeline that takes those enquiries from the MySQL database where the website writes them, scores each one, sends an immediate acknowledgement email, runs scheduled follow-ups, and stops the moment someone replies. It went live on 2026-03-19 and has been the production lead-handling system for Meji's 2026 Christmas season since. Today it sits in a watching phase: the system runs itself, Jess edits the tracking sheet directly when she's already in conversation with a lead, and Gurmej watches ops usage.

Beyond the Christmas-side automation, Gurmej raised three growth asks during the 2026-04-22 call:

1. **Instantly outbound revival** across three segments: Christmas DB warm re-engagement, cold outreach revival, and hen/stag DB re-engagement
2. **Lead-scoring + monitoring dashboard** for the Instantly campaigns (similar to what we built for Christmas)
3. **Corporate side automation** (separate from Christmas, for Meji Media Ltd's non-events corporate work)

These are downstream of getting the Instantly login working. They're also where most of the next quarter's billable work sits.

---

## 3. The people

You'll be communicating with three people, all on Upwork. Read `context/comms-profile.md` once for the canonical profiles; the working summaries are below.

### Gurmej Pawar: owner, decision-maker

Decides scope, budget, plan changes, strategic direction. British, runs Meji Media (the parent) and the Christmas Office Party brand. Practical, no-fluff, has built businesses through events and outbound for years. Not technical, but understands ops well enough to ask the right questions about credit usage and deliverability. He'll push back on anything that sounds "too American" or "too pushy" -- that was the explicit framing he used when describing why he fired the previous outbound contractor. Wants every 1% improvement compounded.

When something is wrong, Gurmej surfaces it as a single direct line. The textbook example is his 2026-03-13 ops-overrun message: "Is it using that much use?" He doesn't ramble; he flags. When you see a one-line message from Gurmej, treat it as a high-signal ask. Reply same-day, own it, fix it.

What works with Gurmej: short messages, clear numbers, concrete options with a recommendation, "we did X because Y" framing. What doesn't: corporate AI-slop tone, hedging, generic lists, anything that reads as templated.

### Jess Harrar: operations, day-to-day

The voice the customer emails should feel like. She runs Meji's day-to-day comms with enquirers, edits the Google Sheet directly to mark leads as `stopped=TRUE` when she's already in conversation, and is the first to flag bugs. The 2026-04-24 "It looks like a lot of the enquiries are stuck on step 2" message is a perfect example -- quick, concrete, helpful. She'll say "Perfect, thanks Nico!" when something works, and she means it.

Jess approves customer-facing email template changes. Anything that touches what an enquirer reads goes through her first. She also ran the venue PDF source-of-truth audit on 2026-03-23/24 and will catch wrong tier names or wrong venue features faster than anyone.

What works with Jess: warm conversational tone, addressing her first when the issue is operational, thanking her when she pre-cleans data on her side. What doesn't: re-litigating settled decisions, dropping technical terms (scenario IDs, module numbers) into messages -- she doesn't need them and they make the message harder to skim.

### Anuj: their developer, agency-side

Owns the website and database (PHP/CodeIgniter/MySQL on `christmasofficeparty.co.uk`). Surfaces only when there's a technical integration ask: IP whitelisting, DB credential renewals, schema changes on the `enquiries` table. He created the read-only MySQL user we use (`make`) and shared credentials on 2026-03-09. He's CC'd on the team thread but doesn't read every message. When you need him, address him by name in the message ("Anuj, quick technical Q:") so he knows to engage.

What works with Anuj: direct technical asks, framed as "I need X to do Y, what's the cleanest way on your side?". What doesn't: assuming he's tracking the comms thread day-to-day. He isn't.

---

## 4. The two Upwork threads

Important and easy to miss: there are TWO active Upwork threads with Meji, and they serve different purposes. Both are visible in your Upwork inbox once Gurmej adds you.

**Thread 1: "Automated Follow-Up System Development for Event Enquiries"**, the team thread

Group thread with Gurmej, Jess, and (when relevant) Anuj. This is where all Christmas-side automation work happens: bug reports from Jess, ops questions from Gurmej, template changes, deliverability discussions, the venue PDFs, the deliverability + scaling report. Most messages so far have been here.

**Thread 2: "General outreach project"**, 1:1 Gurmej for the Instantly scope

Started by Gurmej as a separate project for the Instantly outbound work. This is where the Instantly logins were sent (2026-04-27 15:09 BST: `gurmej@mejimedia.com / <ASK-NICOLAS-OFFLINE>`) and where Gurmej has chased three times waiting for a response. Jess is NOT on this thread. The work that happens here is strategic outbound, not Christmas-side ops.

The reason this matters: when you reply to Gurmej about Instantly, reply in **Thread 2** (General outreach project), not Thread 1. They are different commercial conversations and conflating them in either direction would be confusing. The introduction message I'm sending today goes in Thread 1 because it covers the Christmas-side handover and the access asks; you'll then reply to Gurmej in Thread 2 to close the silence there.

---

## 5. The system, end to end

There are four production scenarios, all running on the **client's own Make.com org** in eu2 (zone `eu2.make.com`, org `5473701`, team `2826470`). The client owns the org; I'm a member. Once Gurmej adds you, you'll be a member too. Everything runs on the client's plan (Core 10k + 20k ops add-on = 30k ops/month; ~40% utilisation as of 2026-04-10).

There's also a leftover dev org in eu1 (`6475885` / `964106`) that contains earlier dev versions of A1/A2/A3 plus some UTIL scenarios. We don't use eu1 for anything live anymore. **Always work in eu2 for live operations. eu1 is for dev/UTIL only.**

The flow, in plain English:

A new enquiry hits the website form. The website writes a row to MySQL (`xmas_2020.enquiries`). Every 30 minutes, **A0** queries that table for new rows since the last cursor, transforms each one into flat JSON, and POSTs to A1's webhook. **A1** runs on each POST: scores the lead across 9 weighted factors, picks an A or B email template (A/B is currently off, so everyone gets A), writes a row to the Google Sheet, calls OpenAI for a personalised opening line, and routes -- hot leads get a team-notification email plus a warm acknowledgement; warm and standard leads get a standard acknowledgement. Every lead enters the follow-up queue with a priority-based cadence (hot 24/48h, warm 24/72h, standard 48/96h -- Jess extended these herself before 2026-04-22). Every 10 minutes, **A2** polls the Gmail inbox for replies and, if a reply matches an active lead in the sheet, marks that row `stopped=TRUE` so no more automated emails go out. Every hour, **A3** scans the sheet for rows that are due for their next step, and for each one, sends step 2 or step 3 from the Email Templates data store, again with an AI opening line.

Reference table for the production scenarios:

| Spec ID | Scenario name | ID | Trigger | Status | Make UI |
|---|---|---|---|---|---|
| A0 | MySQL Enquiry Poller | 8841775 | scheduled, 1800s (30 min) | active | https://eu2.make.com/5473701/scenarios/8841775 |
| A1 | Enquiry Follow-Up Sequence | 8804011 | webhook | active | https://eu2.make.com/5473701/scenarios/8804011 |
| A2 | Reply Detection & Stop | 8804012 | scheduled, 600s (10 min) | active | https://eu2.make.com/5473701/scenarios/8804012 |
| A3 | Scheduled Follow-Up Steps | 8804014 | scheduled, 3600s (60 min) | active | https://eu2.make.com/5473701/scenarios/8804014 |
| (UTIL) | UTIL -- MySQL Parameterized Query | 8974201 | tool (callable) | active, `ship: false` | https://eu2.make.com/5473701/scenarios/8974201 |

The UTIL scenario is yours for ad-hoc MySQL reads against the client's DB without writing one-off queries. Modes: `by_id`, `by_range`, `recent`, `events`, `count`. Don't delete it.

The data stores those scenarios read from:

| DS ID | Name | Records | Holds |
|---|---|---|---|
| 153173 | Pipeline Config | 1 | All 35 tunable knobs: scoring weights, cadence timing, AI config, A/B toggle, handoff threshold and email, `developer_bcc` (currently broken -- see §7) |
| 153175 | Email Templates | 10 | 5 template pairs x 2 A/B variants (A and B). Base keys per the spec: `initial_standard`, `initial_high`, `step_2`, `step_3`, plus a 5th (likely `cold_close` for A3 step 4+) |
| 154401 | MM -- Venue Config | 3 | One record per venue (Birmingham, Leicester, Wolverhampton). Theme name, venue title, features lists in HTML and plain text, tier names, phone, dates count |
| 153982 | A0 Cursor | 1 | Single field `last_id`: the highest MySQL row ID A0 has processed |

The production Google Sheet (the leads tracker Jess edits directly):

```
https://docs.google.com/spreadsheets/d/1Bmm-cbnvpdmJH7w3Y-PiZz7c3Z7JC4L6-6aMZw541BM/edit
```

Owner: `gurmej@mejimedia.com`. Worksheet name: `Leads`. Columns A through U. The columns A1 writes that A2 and A3 read: D (email), K (stopped TRUE/FALSE), L (current_step), M (next_step_due as a date-time), N (last_email_sent), Q (ab_variant). When you're debugging A3, K and M are the columns that matter.

Customer-facing Gmail inbox: `enquire@christmasofficeparty.co.uk` (connection `13923632`). Sheets connection: `12352178` (Gurmej's Google account). There's also a legacy `client.meji-media@unpauseai.com` connection still referenced in some places -- it was deactivated around 2026-04-21 and is part of the open mess (see §7).

The webhook A0 POSTs to (and that A1 listens on):

```
https://hook.eu2.make.com/cva0g9j0ru2p9690nrxji8791grkhhya
```

Webhook ID `3939562`. Don't change it without updating A0's `webhook_target` field at the same time.

If you want full module-level details for any scenario, the live specs are at `specs/4-live/`:
- `a0-mysql-enquiry-poller.md`
- `a1-enquiry-follow-up-sequence.md`
- `a2-reply-detection-stop.md`
- `a3-scheduled-follow-up-steps.md`

The Mermaid flow diagrams in those specs are the fastest way to build a mental model of any single scenario.

---

## 6. Voice rules and the B1.5 live-system gate

This section is what protects you from sending an email that gets flagged. The seven voice rules and the B1.5 gate all come from real corrections from Gurmej or Jess. The full source is `context/client-brief.md`; the working summaries are below.

### The seven voice rules

**1. Party night, not venue hire.** The product is a shared themed party night. Multiple groups attend together. Wrong: "We've got the ICB available for your group". Right: "We've got space at the Winter Masquerade night at the ICB". The features list in templates describes what the night includes (welcome drink, three-course meal, casino, DJ), not a venue spec sheet.

**2. Personal from Jess, not corporate.** Customer emails are signed "Jess" with "Meji Media" underneath. The voice is warm, conversational, slightly informal. Not "The Meji Media Team", not "Info Meji Media", and absolutely nothing that reads like a brochure. Gurmej's exact framing on 2026-03-29: emails should sound "more personal like its from Jess".

**3. Acknowledge the enquiry, don't announce the event.** Customers submitted a form about a specific event at a specific venue. They know what it is. The email acknowledges what they asked about. "Thanks for your enquiry about the Winter Masquerade night" is right. "We've got a Winter Masquerade night coming up" is wrong -- it sounds like cold outreach.

**4. Don't imply a confirmed booking.** Customers have enquired. They have not booked. Anything that assumes commitment ("you're joining our Winter Masquerade", "we've got you down for", "your booking with us") reads as misleading and breaks trust. Stay in enquiry-stage language until the customer replies.

**5. Use the customer's actual data, not generic examples.** When Gurmej shares a screenshot of a problem email, the response uses the exact data from that screenshot. Not "imagine a customer named Sarah with 10 guests". Use the real before/after.

**6. Topic of "Christmas party" applied uniformly.** All 10 templates use "Christmas party" as the topic, per Jess's 2026-03-24 instruction. If you ever revise templates, this stays.

**7. Use the venue PDFs as the source of truth.** Jess delivered three venue PDFs on 2026-03-24 (Birmingham, Leicester, Wolverhampton, all in the Upwork team thread). Those are the canonical source for theme name, tier names, features, and date counts. The website was being redesigned and isn't reliable. The Venue Config data store (DS 154401) reflects the PDFs as of the 2026-03-30 update.

### Comms style for messages to Gurmej and Jess

Flat structure, no numbered sections or bullet lists in messages, no em dashes, sign off as "Matthias", mid-thread continuity (no "Hi Gurmej," opener if you're continuing the same thread). Address Anuj by name when a message is for him. The full style profile is at `context/comms-profile.md`. The validator at `tools/lint-comms-draft.py` runs as a post-write hook on `context/drafts/*.md` and will flag em-dashes, audit-speak, weekday-vs-date mismatches, name-vs-source mismatches, and fabricated claims. Don't restate what was just said in the prior message -- the "no repeat pending items" feedback is real on this client.

### The B1.5 live-system gate

The single most important operational rule. Meji's scenarios are all `ship: true`, all running on the client's plan, all sending real emails to real customers. Any change to a live scenario or to a production data store record can break customer-facing behaviour.

How the gate works in practice:

Before any state-changing call to A0/A1/A2/A3 -- that means scenario activate/deactivate, blueprint edit, interval change, connection swap, OR an edit to a record in DS 153173 / 153175 / 154401 -- you write a one-line message to me (during transition) or to yourself in your plan/checkpoint (when this is fully yours): "About to {verb} {scenario} because {reason}." Then you present at least one alternative including "do nothing". Then you wait for explicit approval unless the most recent client message directly requested THIS specific change by name. After the change, you update `infrastructure.yaml` with the date and reason in the `note:` field for that scenario or DS.

What's gated:
- Activating, deactivating, or running a scheduled scenario
- Editing a scenario blueprint (any module change, interval change, filter change, connection swap)
- Editing any record in Pipeline Config, Email Templates, or Venue Config
- Enabling or disabling A/B testing
- Changing polling intervals on A0, A2, or A3
- Anything that touches what a customer reads in an automated email

What's autonomous:
- Read-only diagnostics: `executions_list`, `executions_get`, `executions_get-detail`, `data-store-records_list`, `scenarios_get`
- Status checks (not state changes)
- Running the UTIL scenario 8974201 for read-only DB queries (it's `ship: false` and only does SELECTs)
- Editing files in this repo that don't deploy to live infrastructure
- Drafting comms in `context/drafts/`

If you're not sure, treat it as gated. The cost of asking is one message; the cost of getting it wrong is a customer email going to the wrong place.

---

## 7. The history that matters

Three stories shape why the system looks the way it does. None of these will be obvious from reading the code.

### The A3 saga: verify behaviour, not config

On 2026-04-08, A3 was edited to add a `google-sheets:filterRows` module that would filter to only rows due for follow-up before doing per-row work. The intent was to drop ops burn from ~51 ops per run (which had caused a credit overrun on 2026-04-08) down to ~5 ops per idle run. The filter used column references `K` (stopped) and `M` (next_step_due) with a `text:less` operator on the `M < {{now}}` condition. Ops dropped from 51 to 1 immediately, and on 2026-04-10 I signed the change off as healthy based on that drop alone.

It wasn't healthy. The filter silently rejected every row because column M was being parsed by Sheets as a date-time serial number, not as a string, and `text:less` against an ISO RHS produced zero matches. From 2026-04-08 through 2026-04-27, no step-2 or step-3 emails went out. Two and a half weeks of follow-ups silently missed. Jess flagged it on 2026-04-24: "It looks like a lot of the enquiries are stuck on step 2."

The fix took two attempts. Fix A on 2026-04-27 was a guess: rename column refs from letters (`K`, `M`) to header names (`stopped`, `next_step_due`). It failed within ~2 minutes with `400 INVALID_ARGUMENT - Unable to parse range: 'Leads'!stopped2:stopped1000000` because Make's filterRows requires column LETTERS in the `a` field literally -- not header names, even with `includesHeaders: true`. Rolled back inside 2.5 minutes. Then I built a one-off diagnostic UTIL scenario in eu2 (scenario 9133798, deleted post-test), tested four single-condition variants, and found that `M < {{now}}` with `text:less` returned 27 bytes of nothing while `date:less` returned 30,323 bytes of rows. Real fix deployed: `text:less -> date:less`. Verified empirically: 151 ops, 10 rows drained, status 1.

The lesson is to **verify behaviour, not config**. An ops-count drop can mean the filter is working. It can also mean the filter is rejecting everything. The only way to tell those apart is to count actual emails sent or rows updated. When you suspect a silent failure on a live scheduled scenario, build a one-off diagnostic UTIL scenario in the same team, isolate the suspect operator, run responsively, compare bytes (or rows in a downstream sink). Cheaper than guessing.

### The dev/prod cutover and the two zones

The system was originally built in my own Make.com org (eu1, org `6475885`, team `964106`) using my personal Google account for Sheets and Gmail. On 2026-03-17 Gurmej added me as a member of the client's Make.com org (eu2, org `5473701`, team `2826470`). The four production scenarios were redeployed there with the client's connections: `gurmej@mejimedia.com` for Sheets, `enquire@christmasofficeparty.co.uk` for Gmail, the client's MySQL credentials. This is when the system went live.

The eu1 dev org is still around. It still has the older A1/A2/A3 scenarios (4596203, 4595921, 4596220) and the original Sheet (`14AcAeuYdDh46meaORZbBGQ0kfuXdTycZ-0kj-uiprZI`) and the original Email Templates and Pipeline Config data stores (98605, 98606). Don't touch any of it for live work. Those scenarios are stale, the connections point at my personal accounts, and the Sheet is in my Drive. The eu1 org is useful for one thing: dev/UTIL experimentation when you don't want to risk touching the client's environment. Everything else lives in eu2.

The MCP server `make-meji-media` is configured to point at the eu2 production org. When you call `scenarios_get` or `executions_list` via MCP, you're hitting eu2. There is no MCP for the eu1 dev org -- REST only.

### The deactivated mailbox trap

`client.meji-media@unpauseai.com` was a mailbox we used during the build phase for dev-side testing. It was on Google Workspace through the unpauseai.com domain, and it owned an early copy of the production Sheet that lived in that Drive. On the 2026-03-17 cutover, we swapped to the client's Drive (Sheet `1Bmm-cbnvpdmJH7w3Y-PiZz7c3Z7JC4L6-6aMZw541BM`, owned by `gurmej@mejimedia.com`). But we didn't fully decommission the legacy mailbox until ~2026-04-21, and a few stale references survived:

- **`developer_bcc` field in Pipeline Config DS 153173** still points at it. Every A1 send tries to BCC the deactivated address; Resume:onerror catches it; A1 emits status 2 (warning) instead of status 1 (green). Customer emails are unaffected.
- **S1 Production Cutover scenario (8883091)** in eu2 still references the legacy Drive. It's `ship: false`, not in active use.
- **UTIL -- Cell Writer (8842533) and UTIL -- EU2 Sheet Reader (8843278)** in eu2 still reference the deactivated Sheets connection (13838215) and Gmail connection (13838220). Both `ship: false`.
- **Sheet ID drift:** `infrastructure.yaml` had the old Sheet ID (`1nZcLJzj...`) until 2026-04-21, when I corrected it to the live Sheet (`1Bmm-...`). The legacy ID is preserved in YAML under `legacy_id` for traceability. If you ever see something pointing at the legacy ID, that's a stale reference.

Cleanup of `developer_bcc` is the one outstanding piece. It's a B1.5-gated change because it touches Pipeline Config. Bundle it with the next live A3/A1 change or take it as its own short session. Repointing to your address (or clearing the field entirely) ends the status-2 warnings on A1.

---

## 8. Open questions waiting on the client

Three things sit in the client's court. None are urgent on a clock, but each one gates downstream work.

**Volume forecast for next 6-12 months.** From the deliverability + scaling report. Gurmej said volume "ramps from May" on the 2026-04-22 call; Jess said it'll "skyrocket from June/July" the same day. Those framings don't quite line up; the report quotes them verbatim next to each other and asks them to reconcile. Whichever number lands determines whether Path A (monitor only), Path B (multi-mailbox), or Path C (dedicated infra) makes sense.

**Risk appetite for deliverability tradeoffs.** Are they willing to accept some risk of mailbox burn at higher volumes, or do they want the most conservative path? This shapes the recommendation when costings come back.

**Coupling between Christmas mailbox and Instantly.** Should `enquire@christmasofficeparty.co.uk` deliverability be planned independently of the Instantly outbound infrastructure (which uses ~10-11 separate warmed domains), or treated as one cross-system concern?

When you take this over, the move is to surface the questions one more time after you've introduced yourself, but don't push hard. Once the relationship is yours and you've got Instantly access working, the path costings become live work and the questions resolve themselves through the scoping process.

---

## 9. Your first 48 hours and first two weeks

Your action plan. The companion file `first-two-weeks.md` has the same content broken into per-day checkboxes if that's easier to track.

### First 48 hours

**1. Accept the Make.com org invite.** Once Gurmej confirms on the Upwork team thread (Thread 1) that he's added you to org `5473701` on `eu2.make.com`, accept the invite. Verify with one read-only call: `scenarios_list` should return A0 (8841775), A1 (8804011), A2 (8804012), A3 (8804014), and UTIL 8974201. If anything's missing, ping Gurmej one more time.

**2. Set up the MCP server entry locally.** In your `.mcp.json`, add:

```json
{
  "mcpServers": {
    "make-meji-media": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://eu2.make.com/mcp/u/<MATTHIAS_TOKEN>/sse"]
    }
  }
}
```

Generate `<MATTHIAS_TOKEN>` from your own Make profile (`Profile -> API & Tokens -> Add token`). The token is per-user; my token won't work for you. Restart your Claude Code session after adding.

**3. Smoke test with a read-only call.** From your Claude Code session: `executions_list scenario_id=8804014 limit=10` (A3). Should return recent executions, all status 1 since 2026-04-27. If you see anything else, surface it.

**4. Reply to Gurmej on Thread 2 (General outreach project).** Same-day. The introduction message I send today on Thread 1 closes the team-side loop, but Gurmej has chased three times on Thread 2 and that thread doesn't close until you reply there. Suggested shape: acknowledge the gap, explain the partner transfer, name a concrete first action (try the credentials, or schedule a brief intro call). Use Meji style: flat, no em dashes, sign as "Matthias", no greeting since the thread is in flight. Validator gate (`tools/lint-comms-draft.py`) catches the obvious mistakes if you draft in `context/drafts/` first.

**5. Get sheet view access.** Jess (or Gurmej) shares the production Sheet (`1Bmm-cbnvpdmJH7w3Y-PiZz7c3Z7JC4L6-6aMZw541BM`) with your Google account. Read-only is fine. Open it, scan a few recent rows, confirm you can see the K (stopped) and M (next_step_due) columns. Those are the two that matter when something looks off.

### Days 3-7: health pass and walkthrough

**6. Spot-check A3 and A1 over a fuller window.**

```
executions_list scenario_id=8804014 limit=20  # A3
executions_list scenario_id=8804011 limit=20  # A1
```

A3 should have ~24 executions per 24h on the hourly schedule, all status 1, ops counts varying with how many rows are due (1 op when nothing is due, ~15 ops per row when rows drain). A1 should have one execution per inbound enquiry from A0, status 2 (because of the `developer_bcc` issue -- expected, not a bug), ~13-14 ops per execution. If anything is consistently off-pattern, surface to me.

**7. Live walkthrough call with me.** 30-45 minutes, recorded as a Loom. Topics to raise: the A3 saga in person, the deactivated mailbox trap and where the legacy refs hide, the seven voice rules with concrete examples (we'll pull two recent customer emails and walk through what's right and wrong), the Instantly login situation, and any open questions from your first 48h. Save the Loom link to `walkthrough-loom.md` in this folder.

**8. Read three documents in this order, if you want to deepen context after the call:**
1. `context/client-brief.md`: the people and voice rules in full source form
2. `context/comms-log.md` from 2026-04-22 onward -- 75+ entries total, but only the recent ones are load-bearing
3. `docs/2026-05-02 - Meji Media A3 Fix and Deliverability Report/Checkpoint.md`: the full A3 saga retro

### Days 5-10: take over the relationship

**9. Try the Instantly credentials.** `gurmej@mejimedia.com / <ASK-NICOLAS-OFFLINE>`. If they work, start the audit (next section). If they don't, single-line ask to Gurmej: "Tried the ones you shared and they're not getting me through. Could you double-check or reset and resend? No rush, but it's the gating piece for the scope-out."

**10. First operational message under your name.** Likely triggered by Jess flagging something or Gurmej asking a question. Whatever the first one is, reply same-day. Match the Meji style. The validator gate is your safety net.

### Days 10-14: Instantly scope-out kick-off

**11. Once Instantly access works, do the audit.** When dashboard works:
- Inventory the 10-11 warmed domains (Meji-owned per Gurmej's 2026-04-27 confirmation, but verify in the dashboard)
- Pull current campaign list and last-30-day stats (open rate, reply rate, bounce rate per campaign)
- Check sender reputation on each domain (Google Postmaster, Microsoft SNDS if accessible)
- Note whether the previous contractor's setup is still active or paused

**12. Start the scope-out report.** The output is a report covering the three segments Gurmej raised on 2026-04-22: Christmas DB warm re-engagement, cold outreach revival, hen/stag DB re-engagement. Pricing structure is a follow-up conversation after the scope lands.

### What good looks like at end-of-week-two

- You've sent at least three messages from your account (introduction confirmation + two follow-ups or replies)
- A3 and A1 have continued running clean; you've spot-checked at least twice
- The Instantly login is either resolved (and the audit started) or has a clean ask back to Gurmej
- The introduction message has landed and Gurmej + Jess know you
- `developer_bcc` cleanup decision made (do it now / bundle with next change / leave for now -- whichever, just decide)

If any of these are stuck, surface to me. Two weeks in is not too late to hand back a piece if something feels off.

---

## 10. The next 30, 60, 90 days

Once the immediate handover is settled, the work shape is roughly this.

### Days 15-30: Instantly scope-out report goes live

The deliverable Gurmej is waiting on. Same shape as the deliverability + scaling report I deployed on 2026-04-27 (PR #102, live at `unpauseai.com/docs/meji-media/scaling`): a single gated HTML page on the docs portal, decision-support framing, surfaces the questions and tradeoffs without arbitrating. Three sections at minimum: (a) audit of the current Instantly setup (what's there, what's broken, what's stale), (b) the three segment scopes (Christmas DB, cold, hen/stag), (c) recommended sequencing and the pricing-structure question.

Bundle this into the same docs portal at `unpauseai.com/docs/meji-media/instantly` (gated by the existing `meji2026` access code, so Gurmej and Jess use the same mental model they already have).

### Days 30-60: first segment campaign live

After the scope lands and Gurmej picks a starting segment (most likely the Christmas DB warm re-engagement, since the data is clean and the audience is known-warm), the first campaign goes live. This is straight Instantly setup work: list import, sequence build, copy review with Gurmej, send schedule, monitoring dashboard hookup.

### Days 60-90: lead-scoring + monitoring dashboard for Instantly

Gurmej explicitly asked for a Christmas-style lead-scoring + monitoring view for the Instantly campaigns. The build pattern is similar to what we did for Christmas (Pipeline Config DS for tunable knobs, scenario for ingest from Instantly, Sheet for tracking, weekly summary email). Reuse where you can; the Instantly side has its own quirks (per-campaign open/reply/bounce, sender-domain rotation, reply routing) so it's not a copy-paste job.

After Day 90, the work shape is whatever Gurmej raises next. Likely candidates: hen/stag DB campaign launch, corporate side automation (separate from Christmas), pricing-structure conversation. Same operational rhythm: weekly health check, Jess-flag-resolution, ops monitoring, voice discipline, B1.5 gate on every live change.

---

## 11. Access checklist

What you need; what's automatic; what needs an explicit ask.

**Make.com production org membership.** Gurmej invites you to org `5473701` on `eu2.make.com`. Asked in the introduction message I'm sending today.

**MCP server config.** Local; you set it up after accepting the org invite. See §9 step 2.

**Upwork thread access.** Two threads (see §4). Path A: Gurmej adds you to both directly. Path B: you reply to both threads from a parallel Upwork account, with the introduction message giving them the heads-up. Either works; A is preferred because the thread history stays attached.

**GitHub.** You already have write access to `akkton/agentic-ops` (added 2026-04-18 for Brisken). Meji code lives in this monorepo, no per-client subtree, so no `/comd_client-handoff` step needed.

**Production Sheet view.** Jess shares it with your Google account once asked (in the introduction message).

**MySQL database direct access.** Optional. A0 reads from `xmas_2020.enquiries` via the `make` user (read-only) inside the Make.com Sheets connection. You inherit it via org membership without needing a personal copy. If you ever need to query the DB outside of Make, Anuj has phpMyAdmin at `christmasofficeparty.co.uk/phpmyadmin/` (host whitelisting required; Anuj has 3 EU2 IPs already whitelisted: `34.254.1.9`, `52.31.156.93`, `52.50.32.186`).

**Instantly dashboard.** Login `gurmej@mejimedia.com / <ASK-NICOLAS-OFFLINE>`. Try once you have time. If the credentials don't work, reset/verify ask to Gurmej (single line, see §9 step 9).

**Documentation portal.** `unpauseai.com/docs/meji-media/` with access code `meji2026`. Source files at `platform/public/docs/meji-media/` in this repo. You inherit access via repo access; no separate auth.

---

## 12. Tools and patterns you inherit

Most of these you'll know from Brisken; the Meji-specific ones are at the bottom.

**`skil_make-pack`**, load when working in any Meji scenario. Modules cover blueprint deployment (`BLUEPRINT-DEPLOYMENT.md`), MCP gotchas (`API-IMPOSSIBILITIES.md`), webhook investigation (`WEBHOOK-INVESTIGATION.md`), and migration patterns (`MIGRATION-PATTERNS.md`). Load one module at a time for the task at hand.

**`tools/make-api.py`**, REST wrapper that bypasses MCP 500 errors on blueprint params. Subcommands: `update`, `deploy`, `get`, `list`, `ds-upsert`, `scenario-run`. Use this when MCP `scenarios_update` returns a 500 on a full blueprint deploy.

**`tools/verify-infrastructure.py`**, drift check between `infrastructure.yaml` and live Make state. Currently errors on Meji because Meji's YAML is missing a top-level `orchestrator:` field (other clients have it). Worth fixing the YAML structure to make the tool work for this client too -- small system-dev item; flag it whenever you have spare cycles.

**`tools/validate-deliverable.py`**, runs as a post-write hook on `platform/public/docs/meji-media/*` and various deliverable folders. Checks paths, TODOs, voice (em-dash, audit-speak, hedging), umlauts, unverified-stat. You inherit the gate.

**`tools/lint-comms-draft.py`**, runs as a post-write hook on `context/drafts/*.md`. Checks em-dash, audit-speak, weekday-vs-date, name-vs-source, fabricated claims. Same idea: write a draft, the gate runs.

**The diagnostic-UTIL pattern** (the Meji-specific one) -- when something silently fails on a live scheduled scenario, build a one-off scenario in the same team, isolate the suspect operator with single-condition tests, run responsively, compare bytes or rows. Took ~10 minutes total for the 2026-04-27 A3 fix; proved the fix empirically; the diagnostic was deleted afterward. Reusable for any future filterRows or scheduling investigation.

**The B1.5 pre-flight phrasing**, "About to {verb} {scenario} because {reason}." Keep it one line. Then list at least one alternative including "do nothing". Then wait. Don't combine the change announcement with the change itself in the same message.

**The MCP write-back trick**, Make's `executions_get-detail` returns counts but not per-module output values. If you need to see what a module actually produced, add a temporary `datastore:AddRecord` after it and read the record back via `data-store-records_list`. Documented in `skil_make-pack/SKILL.md` "Known API Limitations".

---

## 13. What's configurable, and where

When Jess or Gurmej asks "can we change X?", this is the answer.

| What they want to change | Where it lives | How |
|---|---|---|
| Subject lines or body copy of customer emails | DS 153175 (Email Templates), records by key (e.g. `initial_standard_a`, `step_2_b`) | Edit the `subject` and `body_html` fields. B1.5 gated. |
| Lead-scoring weights | DS 153173 (Pipeline Config), `weight_*` fields (9 factors) | Edit the field values. Re-test with a known-score lead before declaring it ready. |
| Cadence (when step 2 / step 3 emails go out) | DS 153173, `cadence_{hot,warm,standard}_step{2,3}` (hours) | Edit the field values. Affects future enquiries from the moment of edit; doesn't retroactively reschedule existing rows. Currently hot 24/48, warm 24/72, std 48/96 (Jess extended these herself before 2026-04-22). |
| Hot-lead threshold | DS 153173, `handoff_threshold` | Numeric, default 50. Lower = more leads tagged hot. |
| Hot-lead notification recipient | DS 153173, `handoff_email` | Email address. |
| Whether handoff path is on at all | DS 153173, `handoff_enabled` | `true` / `false`. |
| A/B testing on or off | DS 153173, `ab_testing_enabled` | `true` enables ~50/50 variant assignment in A1 module 56. Currently `false`: Jess hasn't pushed to enable. |
| Venue features text in templates | DS 154401 (MM -- Venue Config), per-venue records | Edit `venue_features_html`, `venue_features_text`, `venue_tiers_html`, `venue_tiers_text`. Three records: birmingham, leicester, wolverhampton. Values come from the venue PDFs (2026-03-24 source-of-truth). |
| Theme name per venue | DS 154401, `theme_name` field | Birmingham/Leicester = "Winter Carnival", Wolverhampton = "Winter Masquerade". |
| Polling interval (A0, A2, A3) | Scenario-level scheduling config | A0 1800s, A2 600s, A3 3600s. B1.5 gated. Don't tighten without checking ops impact. |
| AI personalisation behaviour | DS 153173, `ai_*` fields | `ai_api_key`, `ai_model` (default `gpt-4o-mini`), `ai_system_prompt`, `ai_temperature` (0.7), `ai_max_tokens` (80), `ai_enabled`. When AI fails, A1's Resume handler keeps email sending without the personalised opening. |
| Sender identity | Gmail connection on the scenarios | Currently `enquire@christmasofficeparty.co.uk`. Changing this is a connection swap, B1.5 gated. |
| `developer_bcc` (currently broken; see §7) | DS 153173, `developer_bcc` field | Clear it or repoint to your address. B1.5 gated. |

Anything not in this table -- the scenario logic, the routing rules, the AI prompt structure -- requires a blueprint edit, which is also B1.5 gated and should go through the diagnostic-UTIL pattern if it's behaviour-changing.

---

## 14. Things not to do

Especially in the first month.

- **Don't change live scenarios in week one.** Read-only diagnostics only. The B1.5 gate exists for a reason; even a "tiny" tweak under your hand for the first time is the wrong vibe to set.
- **Don't propose template rewrites unless Jess asks.** The 2026-03-29 voice corrections from Gurmej are real and recent; let the system run as-is until you've seen what works.
- **Don't promise volume forecasting or path costings until the three deliverability-report questions have answers.** The whole point of the report's framing was decision-support, not arbitration. Until Gurmej and Jess answer, costings are guesses.
- **Don't delete the UTIL scenario 8974201.** It's read-only against the client's DB and useful when you need a quick query.
- **Don't engage Anuj unless there's a technical integration ask.** He's CC'd on the team thread but doesn't track day-to-day. When you do engage him, address him by name.
- **Don't conflate the two Upwork threads.** Christmas-side ops and ops/template/bug topics go on Thread 1; Instantly and outbound topics go on Thread 2. Mixing them confuses Gurmej (and Jess never sees Thread 2).
- **Don't change `developer_bcc` without B1.5 pre-flight.** It's tempting because the cleanup is "small", but it's still a Pipeline Config edit on a live scenario. One-line announce, alternative including "do nothing", wait for OK, then change. After the change: update `infrastructure.yaml` `note:` field.
- **Don't sign off as "Nico".** Sign as "Matthias". The relationship is yours now.

---

## 15. When to pull me back in

I'm handing this over fully, but if any of these come up, surface to me before acting:

- **A3 starts behaving silently again.** If executions are status 1 but follow-up emails aren't actually landing, that's the same false-verify pattern as 2026-04-08. Diagnostic-UTIL pattern, then call me before deploying.
- **Gurmej raises a strategic scope change.** Pricing structure, plan changes, switching to n8n, splitting Christmas from Instantly into separate engagements. These are decisions that affect the relationship shape; I want to be in the loop before you commit.
- **Anything escalates to a refund/dispute conversation.** Not expected, but if it happens, tell me immediately.
- **A regression of voice rules.** If Gurmej or Jess flags an email tone problem, that's worth a quick call. The 2026-03-29 corrections were specific and learnable; a regression would mean a template touched something it shouldn't have.
- **You're stuck on the Instantly login for more than 48h.** I should be able to help debug the credential situation if Gurmej's reset doesn't unstick it.

For everything else -- ops monitoring, Jess flagging a bug, Gurmej raising a follow-on scope, template edits, weekly health checks -- it's yours. Run with it.

Welcome to Meji. Gurmej and Jess are direct, fair, and easy to work with as long as the system holds and the comms stay honest. The hard work of the build is done. What's left is the relationship and the growth side.

-- Nico
