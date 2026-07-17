# Meji Media: Transition State and Next Deliverables

**Prepared:** 2026-05-14
**Status:** Gurmej greenlit transition 2026-05-14 19:33 BST. Nicolas's reply with platform mechanics and access question queued in `context/drafts/nicolas-response-to-greenlight.md`. Awaiting Gurmej's setup of new Upwork project.

This document marks the clean demarcation between Nicolas's prior work and Matthias's forward responsibility, anchors every next deliverable to Gurmej's exact words from his 2026-05-12 reply, and presents the 11-year volume forecast both as the strategic anchor for our timing and as a silver-platter deliverable to Gurmej.

---

## 1. Where Nicolas left off

State of everything Meji-related as of 2026-05-14, before the access channel rolls to Matthias.

### Live infrastructure (operational, Nicolas's build)

- **Make.com production org** (eu2, org 5473701, team 2826470). Four scenarios running clean: A0 (8841775), A1 (8804011), A2 (8804012), A3 (8804014). UTIL 8974201 (read-only MySQL helper, `ship: false`).
- **Christmas-side automation pipeline.** Website form to A0 to A1 to A2 to A3. Customer enquiries acknowledged within seconds, follow-ups scheduled, replies detected, sequences stopped on reply.
- **Production Google Sheet** (`1Bmm-cbnvpdmJH7w3Y-PiZz7c3Z7JC4L6-6aMZw541BM`). Owned by `gurmej@mejimedia.com`. Jess edits directly when in conversation with a lead.
- **Three Make.com data stores:** Pipeline Config (DS 153173), Email Templates (DS 153175), Venue Config (DS 154401). Plus A0 Cursor (DS 153982).
- **Customer Gmail inbox:** `enquire@christmasofficeparty.co.uk`, connected via Make.com Gmail connection.
- **MySQL read-only access** via Anuj's `make` user (created 2026-03-09). Inherited through Make.com Sheets connection.

### Client-facing deliverables shipped (Nicolas's hand)

- **Christmas-side automation handover docs** at `unpauseai.com/docs/meji-media/` (gated by access code `meji2026`). Sections: overview, system, scaling, volume forecast, lead scoring, A/B testing, guide.
- **Deliverability and scaling report** (2026-04-27, PR #102). Three paths (A monitor-only, B multi-mailbox, C dedicated infra). Open questions back to Gurmej and Jess.
- **Volume forecast doc** (11 years of enquiry data, 2015 to 2025). Detailed in Section 3 as the strategic anchor and the silver-platter deliverable.
- **Instantly audit** (2026-05-11). Two PDFs: human-voiced 3-page summary + 12-page structured inventory.

### Open conversation state

- **Gurmej greenlit the transition** 2026-05-14 19:33 BST via Upwork Thread 2 ("Ok let's do it"). Nicolas-side confidence assurance about Matthias delivered at 16:50 BST same day.
- **Nicolas's next reply queued** with the platform mechanics (new Upwork project + agency invite) and the access question (fresh credentials for Matthias vs inherit Nicolas's).
- **Three pre-existing open questions** still in Gurmej's court from the scaling report: volume forecast acknowledgement, risk appetite at higher volumes, Christmas-Instantly infrastructure coupling. The volume-forecast delivery in Section 3 is designed to close question 1 cleanly.

### Known operational debt (Nicolas-side, inherited by Matthias)

- **`developer_bcc` field** in Pipeline Config still points at a deactivated mailbox (cosmetic warning, customer emails unaffected). B1.5-gated cleanup, bundle with next live change.
- **`/contact` 404 on the website**, plus stale menu items (Burton, Derby), plus a 0121 phone typo on the T&Cs page, plus a stale Family Christmas date. All low-priority, batch into one Anuj message when there's a natural moment.
- **MejiAI and Corporate Events Instantly campaigns paused** on bounce protection. No reactivation until cold-data evaluation produces clean lists.

---

## 2. Where Matthias starts

Operational responsibilities effective the moment Gurmej sets up the new Upwork project and the agency accepts with Matthias as the lead.

### Owned by Matthias from day one

- **All client communication.** Thread replies, ops responses, weekly reports. Nicolas's last outbound is the greenlight reply currently queued.
- **Christmas-side automation operations.** Weekly health check on the four scenarios, ops utilisation monitoring, Jess-flagged bug response, voice-discipline gate on any template edit, B1.5 pre-flight on any live-system change.
- **The new managed motion.** Every deliverable in Section 4 below.
- **Sample-data approval workflow.** Every cold campaign goes through Gurmej's review before send.

### Nicolas's role from here

- **Background support** during the transition window (first 30 days).
- **Escalation contact** for strategic scope changes, refund or dispute conversations, voice-rule regressions, A3 silent-failure suspicion. Specific triggers documented in `handoff-package.md` Section 15.
- **No direct client comms** unless the situation requires it and Matthias asks.

---

## 3. The 11-year volume forecast (strategic anchor and silver-platter deliverable)

Same artifact, two purposes:
- **Internally:** the foundation for every campaign timing decision in the new managed motion (Section 4)
- **To Gurmej:** a relationship-strengthening deliverable that wasn't asked for, presented on a silver platter

Live at `unpauseai.com/docs/meji-media/volume-forecast` (gated by `meji2026`). Source: four MySQL tables across `xmas_2020.enquiries`, `all_enquiries`, `full_data_enquiries`, and a backup snapshot. Covers 2015 to 2025 with a verified 2020 to 2022 gap (COVID-era data not recoverable from available tables).

### What the data says

- **Annual totals are roughly stable year over year.** Neither Gurmej's "+10% per year" nor Jess's "skyrockets June/July" matches the pattern. Annual volume is closer to flat than growing.
- **The ramp is real, but it lands August through October**, not June and July. Every year, every dataset.
- **Typical September day:** 20 to 25 enquiries, sustained for several weeks.
- **Single-day record:** 42 enquiries on 2025-09-03. Runner-up days are also September: 15th, 16th, 22nd 2025; 25 September 2024; 18 September 2019.
- **Cliff exposure changes during September peak.** At 100 to 150 outbound emails per day from the single mailbox during peak, the deliverability cliffs documented in the scaling report shift materially against a flat-year average.

### Why it matters operationally

The Q4 buying window the transition message commits to is August through October specifically, not "Q4 generically." Christmas warm DB must be live by mid-July (pre-peak warm-up). Cold campaigns ramp before August or pause during September. Weekly reports during August to October are the highest-stakes ones. Every timing decision in Section 4 traces back to this same data.

### How we deliver it to Gurmej

1. **Cover-note draft** added to `context/drafts/` before Matthias's intro lands. One short paragraph in plain text with the three-line headline and the link to the live doc. Three lines: 11 years of his own enquiry data analysed; the ramp lands August through October (not June to July, not +10 percent per year); single-day record was 42 on 2025-09-03 with typical September day 20 to 25 sustained.
2. **Verbal walkthrough** during Matthias's intro call. 5 minutes max. Screen share, seasonal chart, implication for the Q4 campaigns.
3. **Operational integration** baked into Deliverable 1 (Christmas warm DB launches mid-July to land pre-peak). The launch timing is the demonstration that the prognosis is being acted on.

### Why this lands as a relationship win

- Data from Meji's own systems that Gurmej probably hasn't seen presented this way
- Directly relevant to the planning conversation he just opened (campaign timing, Q4 readiness)
- Corrects both his and Jess's intuitions in a way that respects both ("the ramp Jess saw is real, just timed slightly differently")
- Positions Matthias as data-fluent on day one, not just operationally competent
- Free analysis already done, presented as a gift rather than a billable line item

The point of the silver platter: Gurmej feels like the agency is already thinking ahead of him, not just executing what he asked for.

---

## 4. The deliverables, anchored to Gurmej's words

Every deliverable below maps directly to a sentence Gurmej wrote in his 2026-05-12 reply. His exact framing is quoted; the deliverable is what we build to satisfy it.

### Deliverable 1: Christmas warm DB campaign

> "Rebuild the Christmas outreach around our warm database"

**What we build:**
- Pull the warm database (past Christmas customers + past enquirers who didn't convert)
- Clean it: validate emails, remove bounces from prior sends, deduplicate
- Segment by engagement history (booked previously, enquired previously, opened recent sends, dormant)
- Build a 3-touch sequence (initial, +5 day follow-up, +10 day final)
- Deliverability test on a 50 to 100 contact warm-up sample
- Launch at conservative volume, ramp over 2 weeks
- **Live by mid-July to give 4 to 6 weeks of engagement before the August inbound peak** (per Section 3).

### Deliverable 2: Banter warm DB campaign

> "Rebuild the Banter outreach around our warm database"

**What we build:**
- Same shape as Deliverable 1, applied to Banter's past customers
- Lower volume, calmer cadence (Banter is the quieter brand)
- Same 3-touch sequence with reply detection
- Persona-separated sender (Jessica Harrar mailboxes on `banterexp.com`, not the Gurmej mailboxes)

### Deliverable 3: Cold-data provider evaluation report

> "Analyse how we source better cold data for corporate event outreach, so we are targeting the right people and not wasting sends (apollo or elsewhere?)"

**What we build** (per `context/cold-data-evaluation-framework.md`):
- One-week head-to-head evaluation across Apollo, Cognism, ZoomInfo, plus 2 to 3 UK B2B specialists (Lusha, LeadIQ, plus one more)
- 150-contact sample pull from each, same ICP brief (UK corporate-events buyers, 50 to 500 employee companies, PA/EA/Office Manager/HR titles)
- Scored on six criteria: title precision, company filter precision, email verification quality, location precision, cost per validated lead, filter UX
- Comparison report to Gurmej with sample files attached and a recommendation

### Deliverable 4: Christmas cold data per venue city

> "Build clean cold data for Christmas in the cities where we are organising parties, making sure it is properly filtered and viable before anything goes live"

**What we build:**
- Three separate cold lists: Birmingham, Leicester, Wolverhampton
- Each filtered to a 25-mile radius around the venue
- Titles: PA, EA, Office Manager, HR (per Deliverable 3 ICP)
- Company size: 50 to 500 employees
- Industry exclusions: universities, NHS, public sector, registered charities, single-person LLPs
- Email verification quality threshold: bounce rate below 2% on a 50-contact test send

### Deliverable 5: Sample-data approval workflow (recurring, non-negotiable)

> "Before any cold campaign goes live, I'd like to see a small sample of the data first so we can check job titles, companies, locations and relevance."

**How it operates:**
- Every cold list gets a 100 to 200 contact sample sent to Gurmej before any campaign launches
- Sample includes titles, companies, locations, and a sense of relevance per contact
- Gurmej flags issues (wrong vertical, wrong size, wrong location, mixed signal, role mailboxes, domain concentration)
- Pass = approved for full pull, fail marginally = refine filters and re-sample, fail materially = move to next-ranked provider
- Pattern: sample format gets approved once for each campaign type; subsequent samples pattern-match against the approved structure for speed

### Deliverable 6: Per-campaign follow-up sequences

> "I also think each campaign needs a proper follow-up sequence, not just one email"

**Default structure across all campaigns:**
- Three touches over 10 to 14 days
- Reply detection: sequence stops the moment a recipient replies
- Bounce handling: contacts removed from sequence on bounce, list quality monitored
- Subject-line variants for testing where the warm-up data supports it
- No single-touch campaigns. Ever.

### Deliverable 7: Monday morning weekly report (ongoing cadence)

> "a clear weekly update showing: emails sent, bounce rate, replies, positive replies, opportunities / calls booked, any issues or changes needed"

**Format** (template at `context/weekly-report-template.md`):
- Total emails sent
- Bounce rate
- Replies
- Positive replies
- Opportunities or calls booked
- Anything flagged for Gurmej's decision

Same layout every Monday morning, 30-second read, sent to Gurmej before 10am UK time. Skip weeks only with a heads-up the prior week.

---

## 5. Sequencing and timing

Dates are working assumptions, not commitments, until Matthias confirms after access lands. The deliverable outcomes in Section 4 take precedence over the calendar.

### Trigger: Gurmej sets up new Upwork project + invites agency

Estimate: within 1 to 5 days of his greenlight (2026-05-14). Until this lands, nothing operational can move.

### Week 1: Channel established (target 2026-05-19 to 2026-05-25)

- Matthias intro message on the new Upwork project thread, with the volume forecast cover note attached (Section 3 delivery)
- Access landing: Make.com org, Sheet view, Instantly login per Gurmej's chosen path
- First weekly report Monday 2026-05-26 (Deliverable 7 cadence starts)
- Cold-data evaluation kickoff (Deliverable 3 work begins)
- Internal: Christmas warm DB rebuild plan drafted (Deliverable 1 design phase)

### Week 2 to 3: Foundation (target 2026-05-26 to 2026-06-08)

- Cold-data provider comparison report to Gurmej (Deliverable 3 ships)
- Christmas warm DB rebuild plan to Gurmej as a one-pager (Deliverable 1 plan ships)
- Banter warm DB rebuild plan (Deliverable 2 plan ships)
- Weekly report week 2 with real activity

### Week 4 to 6: Christmas warm DB build (target 2026-06-09 to 2026-06-29)

- Cleaned warm list ready with engagement-history segmentation
- 3-touch sequence drafted, Gurmej-reviewed, deliverability-tested
- Christmas warm DB campaign live mid-July (Deliverable 1 ships)
- First samples for Christmas cold campaigns pulled (Deliverable 4 sample phase)

### Week 7 to 10: Cold and Banter expansion (target 2026-06-30 to 2026-07-27)

- Banter warm DB campaign live (Deliverable 2 ships)
- Christmas cold campaigns live per venue city after Gurmej approves each sample (Deliverable 4 ships)
- Per-campaign follow-up sequences active across all campaigns (Deliverable 6 default behaviour)
- Sustained weekly reports (Deliverable 7 cadence)

### August to October: peak operating regime

This is the moment the volume forecast prognosis becomes operational. Inbound enquiry peak runs in parallel with managed outbound. Cold campaigns throttle during September to preserve sender reputation. Weekly reports are the highest-leverage operational artifact. Don't be surprised by the shape of the numbers.

### November onward

Season retrospective. Numbers compared to the forecast, voice corrections from the year, what to change for 2027.

---

## 6. Risk callouts

1. **Q4 timing slip.** If the Christmas warm DB rebuild misses mid-July, the launch lands during peak when the team's attention is split. Day 30 milestone (cleaned list + segmentation + sequence drafted) is the early signal.

2. **September deliverability collision.** Cold campaign volume that's fine in May can be material in September. The 100 to 150 daily outbound from the customer mailbox during peak doesn't leave much headroom on shared infrastructure. Fresh eyes on the cliffs against the volume-forecast peak numbers.

3. **Voice regression on the new motion.** Christmas-side voice rules are learned; new Instantly outbound has its own voice profile that doesn't exist yet. Matthias develops it through Gurmej's sample-approval iterations. Plan for 2 to 3 sample rounds before the voice stabilises.

---

## 7. Matthias's intro call talking points

Three things worth Gurmej hearing in voice rather than text:

- **The 11-year volume forecast finding** as Matthias's first analytical framing. He reads it back to Gurmej in his own words. Positions him as data-fluent and aligned with the same evidence base. This is the silver-platter moment in voice form.
- **The August-October peak operational regime concept.** Build the shared mental model now, not in September.
- **Confirm Matthias's read on the three open questions** from the scaling report. Volume answer is now data-grounded. Risk appetite and Christmas-Instantly coupling remain Gurmej's calls.

After the intro call: revisit this deliverables doc with Matthias's adjustments, then it becomes the canonical plan.

---

Source files this document references:
- `deliverables/handoff-package.md` (Nicolas's full curriculum)
- `deliverables/instantly-audit2.md` (2026-05-11 audit)
- `deliverables/onboarding-2-day-schedule.md` (Matthias's training plan)
- `context/cold-data-evaluation-framework.md` (provider comparison methodology)
- `context/weekly-report-template.md` (Monday morning format)
- `context/risk-register.md` (full risk inventory)
- `platform/public/docs/meji-media/volume-forecast.html` (the 11-year analysis)
- `platform/public/docs/meji-media/scaling.html` (deliverability and scaling report)
