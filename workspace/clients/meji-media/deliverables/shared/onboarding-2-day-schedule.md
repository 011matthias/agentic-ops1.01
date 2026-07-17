# Meji Media: 2-Day Onboarding Schedule for Matthias

**Prepared by:** Nicolas Neumann
**Date:** 2026-05-12
**Status:** Compressed program. Two days, full content coverage.

The curriculum is the same as the multi-week plan that lived in `handoff-package.md` + `first-two-weeks.md`. The compression comes from front-loading the reading (Day 1 morning), front-loading the live-system walkthrough (Day 1 afternoon), and running supervised execution (Day 2) before the introduction message lands.

End state by close of Day 2: Matthias has read everything, walked through every live system with Nicolas, drafted his intro to Gurmej, drafted the first weekly report template, and is ready for the Day 3 introduction message to go out under his own name.

---

## Day 1: Immersion (about 7 working hours)

### 1. Morning block: read everything (3 hours)

Read in this order. Don't skip ahead.

1. `context/meji-101.md`. The 1-page synthesis. Sets the mental model for the rest.
2. `context/business-context.md`. The brand, the venues, the pricing, the customer-visible facts. Read once carefully.
3. `deliverables/handoff-package.md`. End to end. This is the spine. Sections 1-7 are foundational. Sections 8-15 are operational reference; skim them now, return to them as needed.
4. `context/comms-profile.md`. Contacts, voice, sign-off, the validator gates.
5. `context/comms-log.md`. Skim from 2026-04-22 onward. Older entries are settled context.
6. `context/risk-register.md`. What can break, what's mitigated, what's still open.
7. The last 3 client-facing deliverables in `deliverables/`: `instantly-audit2.md`, `handoff-package.md` (already read), and whichever is third. The voice in these is the voice the client expects in your messages too.

**Teach-back at the end of the morning (15 minutes with Nicolas):**
- Name all three Meji contacts. For each: what they care about, what frustrates them, one example of their voice.
- Explain warm DB vs cold data and why bad cold data poisoned previous sends.
- Walk through what happens when an enquiry comes in (form to first email).
- Name the three Meji businesses (Meji Media, MejiAI, Banter Experiences).
- Name the three Christmas venues and their price ranges.
- Identify the three things you are most worried about not understanding yet. Metacognition matters more than coverage.

### 2. Lunch (30 minutes)

Off-screen. Reset.

### 3. Afternoon block: live-system walkthrough with Nicolas (3.5 hours)

Loom-recorded. Cover one system at a time. Matthias drives the screen share when possible; Nicolas narrates.

**System 1: Make.com production org (eu2) (60 minutes)**
- Tour the four scenarios (A0, A1, A2, A3) one by one in the UI
- Open A3, walk through the modules, show the `text:less` -> `date:less` fix that landed 2026-04-27
- Open Pipeline Config (DS 153173), walk through every field, point at `developer_bcc` and the deactivated-mailbox trap
- Open Email Templates (DS 153175), Venue Config (DS 154401), A0 Cursor (DS 153982)
- Show the live Google Sheet, point at columns K (stopped) and M (next_step_due)
- Show how to read executions with the MCP (`executions_list scenario_id=...`)

**System 2: Instantly (45 minutes)**
- Log in together with `gurmej@mejimedia.com` credentials. If they fail, that's the first real client ask Matthias has to make tomorrow.
- Tour the five visible campaigns (Vayne, MejiAI, Corporate Events, Christmas Bookers, Banter reactivation)
- Tour the sender pool, the 11 mailboxes across 4 domains (mejimedia.co, mejiai.com, mejievent.com, banterexp.com)
- Show where bounce data lives, where reply data lives, where warmup state shows
- Show the Diagnose API output for the two bounce-paused campaigns

**System 3: MySQL via UTIL scenario (30 minutes)**
- Run UTIL 8974201 in `recent` mode against `xmas_2020.enquiries`
- Show the row shape that A0 transforms into A1's webhook payload
- Show the `events` table and its `venue_id` mapping to the venue-config price tiers

**System 4: The docs portal (15 minutes)**
- Walk through `unpauseai.com/docs/meji-media/` end to end
- Read the volume forecast doc together
- Read the scaling report together
- Point at what's gated by the `meji2026` access code

**System 5: The Upwork threads (15 minutes)**
- Walk through Thread 1 (Automated Follow-Up System, team thread) chronologically
- Walk through Thread 2 (General outreach project, 1:1 Gurmej) chronologically
- Highlight the three chases from Gurmej on Thread 2 (2026-04-29, 2026-05-05, 2026-05-06) that the audit + transition message resolves

**System 6: The tooling Matthias inherits (15 minutes)**
- `tools/make-api.py`: when MCP returns 500, this is the fallback
- `tools/lint-comms-draft.py`: post-write hook on `context/drafts/*.md`
- `tools/validate-deliverable.py`: post-write hook on platform docs
- `tools/verify-infrastructure.py`: drift check; currently fails on Meji until YAML structure is fixed

### 4. End of Day 1 (30 minutes)

- Matthias writes a one-page "what I learned" doc. Free-form. Where Nicolas can see the gaps.
- Identify the top three questions for Day 2.

---

## Day 2: Supervised execution (about 6.5 working hours)

### 5. Morning block: deeper reading + draft work (3 hours)

**Read (90 minutes):**
- The three live spec docs: `specs/4-live/a1-enquiry-follow-up-sequence.md`, `a2-reply-detection-stop.md`, `a3-scheduled-follow-up-steps.md`. The Mermaid diagrams are the mental-model accelerator.
- `specs/4-live/a0-mysql-enquiry-poller.md`. Smaller scenario but important for understanding the ingest.
- The 2026-05-11 session log (`docs/sessions/2026-05-11.md`). The audit shipping context, the friction events, the open items.

**Draft work (90 minutes):**

Matthias drafts the following in `context/drafts/`. Each gets caught by `tools/lint-comms-draft.py` automatically. Nicolas reviews each before it's used.

- **Draft 1: Matthias's introduction message to Gurmej and Jess.** Goes on Thread 1. References Nicolas's transition message (already drafted, sent today on Day 2). Identifies Matthias by name, asks for the two access items (Make.com org membership, Sheet view), commits to a same-day reply when Gurmej confirms.
- **Draft 2: A standby reply for Thread 2.** When Gurmej responds to Nicolas's transition message, Matthias's first move is to acknowledge in Thread 2 and confirm the plan. Have this drafted now so the reply lands within hours, not days.
- **Draft 3: First weekly report.** Template form (the report goes out every Monday from here on). Pull the format from `context/weekly-report-template.md` and fill it with the current week's data. Empty week is fine; the format is what matters.

### 6. Lunch (30 minutes)

### 7. Afternoon block: co-pilot exercise + send (3 hours)

**Cold data evaluation framework (60 minutes):**
Matthias drafts the evaluation methodology for the cold data provider comparison (Apollo, Cognism, ZoomInfo, plus 2-3 UK B2B specialists). Nicolas reviews.

Inputs to evaluate against:
- Titles available (PA, EA, Office Manager, HR roles for corporate-event buyers)
- Filters that actually work for the target ICP
- Email verification quality (sample 100 emails, check bounce rate against Instantly)
- Cost per validated lead at the volume Meji needs
- Sample data approval workflow: how the sample lands with Gurmej

**Sample-data approval message template (30 minutes):**
Drafted reusable message Matthias will send every time a cold campaign is about to launch. Goes to Gurmej, attaches a sample of the actual contact list with titles, companies, locations.

**Mock client conversation (60 minutes):**
Nicolas plays Gurmej. Asks three hard questions:
1. "How long until the Christmas warm DB campaign is live?"
2. "What's the cost structure for this going forward?"
3. "If a campaign underperforms, what happens?"

Matthias answers in real time. Nicolas debriefs after each.

**Send the transition message (15 minutes):**
The message Nicolas drafted on 2026-05-12 goes out on Thread 2 of the Upwork conversation. From Nicolas's account, still. Matthias watches.

**Stage the response cascade (15 minutes):**
When Gurmej replies (likely within 24 hours), the sequence is:
1. Nicolas acknowledges briefly in Thread 2 confirming the transition is real
2. Matthias's intro lands in Thread 1 (his own message, his own account)
3. Matthias replies in Thread 2 with the plan recap and the first concrete action

### 8. End of Day 2 final teach-back (30 minutes)

Matthias presents back to Nicolas as if Nicolas were Gurmej:
- The plan committed to in the transition message
- The cold data evaluation methodology
- The sample-data approval gate
- The weekly report format

Nicolas pushes back on each. Matthias defends or revises. If he can answer all four without hesitation, he's ready for Day 3 solo work under supervision.

---

## What "ready" looks like at end of Day 2

- Matthias has read every load-bearing document for Meji
- He's walked through every live system with Nicolas, recorded
- He's drafted three messages, all caught and cleared by the validator
- He's been pushed on the hard questions and held the line
- The transition message has gone out; the silence on Thread 2 is broken
- He has a stage-managed plan for the next 48 hours of client responses

If any of those four are weak, Day 3 extends Day 2 rather than going live solo. The teach-back is the gate.

---

## What good looks like after Day 3 (first real client interaction)

- Gurmej replies to the transition message; Nicolas acks briefly; Matthias's intro lands in Thread 1
- Matthias gets the Make.com org invite and Sheet access
- Matthias replies in Thread 2 with the plan acknowledgement and a concrete first action (Instantly login test, sample request, calendar invite, whichever feels right)
- The weekly report cadence begins Monday morning, even if Week 1 is mostly "we've set up access, here's the campaign sequencing for the warm DB"

---

## Failure modes the schedule is designed against

- **Mimicry.** Matthias starts every message with Nicolas's openers. The validator catches the obvious AI tells; the voice profile catches the mimicry. The mock conversation on Day 2 afternoon forces him into his own voice.
- **Eager over-promising.** The mock-Gurmej exercise specifically tests the "how long until X is live?" question. The right answer is "I'll come back to you with a date by end of week" not "two weeks".
- **Skipping the live system walkthrough.** Reading specs without seeing the live system produces a fragile mental model. The afternoon Day 1 walkthrough is non-negotiable.
- **Treating it as a checklist.** The teach-backs (end of Day 1 morning, end of Day 1, end of Day 2) are where understanding gets tested. If the answers are mechanical, the schedule isn't working.

---

## What lives outside this schedule

The 30/60/90 day plan in `handoff-package.md` Section 10 still applies but needs updating for the new managed-service motion Gurmej asked for on 2026-05-12. Updated version lands in `deliverables/30-60-90-plan-v2.md` during Week 1 of Matthias running solo.

Pricing and commercial structure for the new managed motion is a separate conversation between Nicolas, Matthias, and Gurmej. Not part of this onboarding.
