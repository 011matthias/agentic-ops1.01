# Lead Desk, Campaign Runbook

Zero to an approved, sending-ready campaign in under an hour, entirely in
the tool. Every step below is a page or form the app already serves; no
scripts, no sheet edits, no mailbox work. Nothing in steps 1-6 can send a
single mail: sending needs BOTH typed gates (step 6 and step 7) plus the
global kill switch off, and the worker claims only inside the campaign's
send window and caps.

Time budget: ~42 minutes of work across steps 1-6, plus the step-7 press.

## 1. Create the campaign (~2 min)

Campaigns page, "New campaign" card (`POST /campaigns`): campaign id
(slug; lowercased, spaces become dashes), name, daily cap (default 40).
The row is created with the house defaults: from matthias.silva@,
CC dirk.neumann@, BCC the Zoho CRM dropbox, send window 08:30-17:30
Europe/Berlin weekdays, throttle 12s + 4s jitter, status `draft`, and the
seed warmness rules. You land on `/campaigns/{id}`, where everything else
happens.

## 2. Templates (~15 min)

Card "4. Templates" (`POST /templates`): template key (e.g. `cold-e1`),
channel, subject (email only), body. Saving always creates a NEW version;
an approved campaign keeps sending its pinned version until re-approved.
Merge vars are a whitelist over contact columns: first_name, last_name,
company, job_title, email, country, persona, signal, tier, written as
`{{first_name}}`.

Preview against a real contact before approving: the approval card
renders every step for the first real contact per degree, and
`GET /templates/{key}/preview?contact_id={id}` returns the rendered
subject/body plus any missing vars for one specific contact. Write copy
for every template key the sequences in step 3 will reference; the
approval blocks on a missing or unrenderable template.

## 3. Sequences per degree (~5 min)

Card "3. Sequences per degree" (`POST /campaigns/{id}/sequences`), one
form per degree (cold, cold_touched, warm). Steps, one per line:

    channel template_key day_offset [reply]

`day_offset` counts from the previous step's ACTUAL completion; step 1
counts from approval. The `reply` token sends the step in-thread on the
prior step's mail (wire subject RE: the prior subject). Default posture:
step 1 fresh, every later email step carries `reply`; step 1 itself can
never be a reply (the form refuses it).

Send mode per degree: `auto-matthias` (auto-send as matthias.silva@, CC
Dirk) or `draft-dirk` (staged as ready drafts in Dirk's mailbox; his
click is the send gate; the warm degree defaults to it). LinkedIn steps
never auto-execute; they become manual board tasks. Editing a sequence on
an approved campaign revokes the approval; the "Edit live" delta under
each degree appends or edits FUTURE steps without demoting.

## 4. List upload + degree rules + reclassify (~10 min)

Card "1. Upload contacts" (`POST /campaigns/{id}/upload`, CSV or XLSX).
Headers match case-insensitively with aliases (email, first_name,
last_name, company, job_title, linkedin_url, phone, country, ...); an
optional `degree` column assigns warmness manually. An existing contact
is ADOPTED with its full history, never duplicated. Uploads are inert
until approval.

Card "2. Warmness rules": first match wins. Edit the JSON
(`POST /campaigns/{id}/rules`), then "Re-run rules on unapproved rows"
(`POST /campaigns/{id}/reclassify`). Per-row overrides live in the
enrolled table: the degree dropdown (`POST /enrollments/{eid}/degree`)
and Remove for not-yet-approved rows.

Suppression needs NO per-campaign work: it is global and pre-loaded. The
`suppression_entries` ledger (2,454 entries at the 2026-08 mailbox-truth
import; per-address and per-@domain rows) plus the per-contact suppressed
flags are checked again at claim time and at wave enumeration, on top of
the hard-denied recipient domains.

## 5. Schedule (~5 min)

Card "Schedule & pacing" (`POST /campaigns/{id}/schedule`): start no
earlier than (YYYY-MM-DD, blank clears) holds the first touch until that
date; new contacts per day (blank/0 = off) ramps step-1 sends so a large
wave spreads over days. The daily cap was set at creation; the
cross-campaign per-mailbox cap lives on the Campaigns page
(`POST /settings/mailbox-cap`).

Then READ the projected send schedule table on the same card: a
day-by-day estimate of when the sends land (it ignores replies, bounces,
and the mailbox cap). If the shape is wrong, fix pacing now; it is the
cheapest moment to do so.

## 6. Approve: gate 1 (~5 min)

Card "6. Approval". Clear every blocking issue (no contacts, missing
degree, missing sequence, unrenderable template), read the rendered copy
per degree and the scope text, then type the campaign id and press
Approve (`POST /campaigns/{id}/approve`). Approval FREEZES the template
version pins, each contact's exact recipient address, and the enrolled
list hash. The claim path refuses anything that drifts from this frozen
scope. Still nothing sends: the campaign sits in `approved`.

## 7. Start sending: gate 2

Card "7. Sending gate": type the campaign id again and press Start
sending (`POST /campaigns/{id}/start-sending`). The worker claims ONLY
from a `sending` campaign, only when the global kill switch is off, only
on/after the start date, inside the send window, under the caps. Pause /
Resume live on the same card; the kill switch on the Campaigns page stops
everything at once.

## What stays human, by design

- Per campaign: the Approve press and the Start sending press, each with
  a typed confirm. No automation performs either.
- Per wave: Dirk's own yes for mail in his name. `draft-dirk` steps stage
  ready drafts in his mailbox and only HIS click sends; the staged-wave
  card is visibility only, nothing on the page releases it.
- Per attempt: triage of parked/stalled sends on the campaign page:
  Retry (re-queue), Send fresh (drop an unrecoverable reply-thread
  anchor), Mark sent (assert the mail did go out).
- LinkedIn steps: sent by hand, marked done on the board.

## Telemetry checklist (is the tool managing this campaign?)

- Engine card on the campaign page: worker tick age + last-tick counters,
  attempts by status, sends today vs the daily cap, new contacts vs the
  ramp, capture-grounded inbound since approval, the staged-wave line,
  and any send-guard alert.
- `/unmatched`: captured mail that matched no contact, waiting on a human
  link or dismiss.
- Board freshness strip: capture heartbeat, per-mailbox watermarks, and
  the deep truth-scan age, with the same thresholds the Engine card uses.
