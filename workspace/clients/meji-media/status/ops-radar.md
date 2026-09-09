---
project: meji-media
workstream: ops-radar
group: ""
spec: ""
state: active
updated: 2026-09-08
---

# Meji Media / Opportunity Radar

The repeatable method for finding leaks, gaps, and ROI opportunities from live
state with slight weekly effort. This file is the durable, value-free anchor:
it names where every part of the method lives so a fresh session (or machine)
can rediscover it without prior context. The method's content and all client
data live in the gitignored `context/`.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Lens catalog + scoring rubric | live | sec J of `context/weekly-review-blueprint.md` (J1 lenses, J2 rubric, J3 cadence) | recalibrate rubric at first deep sweep | - | 12 lenses capped, one-in-one-out |
| Candidate ledger | live | `context/opportunity-radar.md`, seeded 2026-07-20; RAD-29 added 2026-08-25 | prune rejected/promoted rows at next sweep | - | states: candidate / promoted / rejected / watch |
| Engine `--radar` mode | live | `context/analysis-scripts/` weekly-review engine, radar flag off the cron path | fold into `--scheduled` after 2 clean weeks | - | deterministic feeds; verified on live data 2026-07-20 |
| Weekly light pass | dormant | never ran; the 08-31 restart date passed without a run | restart when the weekly-report work resumes (pending Gurmej's September go) | - | always-on lenses + one rotating deep lens |
| Deep-sweep workflow | dormant | one run only (`weekly-reviews/2026-07-20-deep-sweep.md`); the 08-01, 08-15 and 09-01 editions did not run | next deep sweep after the September launch; the pre-gate function was served instead by the 09-03 launch-readiness audit (Live state below) | - | client-parameterized; adversarial verify stage mandatory |

## Invocation

- Weekly: `/comd_radar meji-media light`
- Biweekly: `/comd_radar meji-media deep` (next: the 09-01 pre-gate edition)

Monday auto-review (the scheduled task) is separate and DID keep running
unattended through August; `weekly-reviews/` holds 07-26, 08-10, 08-16 and 08-23,
and the daily reply-SLA flags ran to 08-21. The radar cadences that lapsed are the
judgment passes that ride on top of that output, not the automated pull itself.

## Live state at 2026-09-03

Make: the 20k -> 40k tier move EXECUTED 2026-08-28 (verified read-only via
`organizations_get 5473701`: `operations: 40000`; the upgrade granted the new
allowance immediately and RE-ANCHORED the billing cycle 28 Aug -> 28 Sep).
Auto-purchase remains OPEN (`autoPurchasingActivated: false`); it is the second
half of what Gurmej approved in Block 31 and the promised confirmation message
to him is held until it is on.

Instantly inventory, re-verified 2026-09-03 with a status-x-contacted cross-tab.
CORRECTION to the 08-27 table: Instantly `status=1` ("in sequence") INCLUDES
never-emailed leads, so the old In-seq column double-counted Fresh (Big
Companies read as "267 in-seq + 258 fresh" when 258 of the 267 ARE the fresh
ones). "Emailed" below derives from `timestamp_last_contact`. `status=-1`
semantics are UNVERIFIED (the old table's "Bounced" label was an assumption);
the column is reported raw.

| Campaign | Total | Never emailed | Emailed | Frozen mid-seq (emailed) | Status -1 |
|---|---|---|---|---|---|
| P1 Warm Re-engagement | 907 | 1 | 906 | 0 | 31 |
| P2A Decision-Makers | 589 | 0 | 589 | 0 | 33 |
| P2B Organisers | 434 | 3 | 431 | 17 | 30 |
| P3 Christmas Cold | 569 | 0 | 569 | 0 | 5 |
| Christmas Bookers | 983 | 1 | 982 | 2 | 39 |
| Big Companies UK | 880 | 258 | 622 | 9 | 19 |

P1/P2A/P3 are spent. The open item is `Big Companies UK` (245913f7, status -2,
created 2025-11-12, pre-dates our engagement, in no routing doc): 258 never
contacted and 9 frozen mid-sequence, on the SAME three mejievent mailboxes the
September corporate wave launches from. Decision put to Gurmej 09-03
(finish / retire / fold the 258 into the new push).

September launch prep (2026-09-03): launch line-up message + 4-page campaign
status PDF (`deliverables/meji-campaign-status-2026-09-03.{md,pdf}`) finalized
after a 2-round adversarial verify (22 findings fixed) and handed to the owner
for send. Owner APPROVED the full launch path 2026-09-04 (12 hrs / ~$440 domain work
announced in the message with its price, not asked) with one change: the
domain setup and the DMARC step also WAIT for Gurmej's reply; nothing
executes before it.
mejievent DMARC still `p=none` (live 8.8.8.8 pull 09-03); first tighten step is
part of the launch chain. `placement-seeds.csv` still empty; seed inboxes asked
of Gurmej in the message. Corporate rebuild = three NEW sequences from the
approved 07-29 emails. PLAN PIVOT (owner, 09-04): A and B are UPGRADED IN
PLACE (sequence swap + fresh list + resume, history kept), NOT retired; only
Version C is a new campaign. Message finalized 09-06, PENDING owner send.
Jess ask-3 (workload proposal, no prices) drafted 09-06 off the LIVE A1
blueprint (8804011): venue map is hardcoded ids 130-150 with FALLBACK
'birmingham', so any post-April event gets Birmingham venue details; the two
fixes are head-of-flow enquiry_type filter + live venue read from the event
record. Pricing (ask 4) only after Meji accepts the scope.

Ask 3 SENT and ANSWERED: Jess replied 2026-09-07 17:29 CEST in the Upwork room
("Thanks Matthias, let me know if you need anything from me in the meantime"),
which clears the ask-4 gate. Ask 4 (pricing) drafted 09-07 for Gurmej in the
same room, grounded in a second live read of A0 (8841775) + A1 (8804011):

- A0 runs `SELECT * FROM enquiries WHERE id > cursor ORDER BY id ASC LIMIT 50`
  on MySQL connection 13875518 and POSTs a fixed JSON body to A1's webhook.
  So the venue fix does NOT need a new DB read in A1: joining the event/venue
  in A0's existing query and adding one payload field lets A1 module 80 read
  the venue straight from the webhook. Module 80 keeps its `venue_key` output
  name, so module 81, sheet column 20 and module 90 stay untouched, and A3
  (which renders venue from the sheet) inherits the fix.
- Same reason the family exclusion is cheapest as a WHERE clause in A0 rather
  than a Make filter at A1's head: the row is never fetched, so there is no
  cursor stall (cursor advances to the last office row; an all-family batch
  returns nothing and costs no extra op, since A0's query runs on its 30-min
  schedule regardless). This SUPERSEDES the 09-06 "head-of-flow filter"
  placement, which was chosen before A0's query was read.
- Head-of-A1 filtering would also block module 6 (gateway:WebhookRespond), so
  the website form would stop getting the `{"status":"ok"}` body. Filtering in
  A0 avoids that question entirely.
- Net effect on Make usage: no operations added, and the family exclusion
  removes a few. Relevant to the Block 31 credit-cliff conversation.

Quote: 8-10 hrs total (~3 exclusion, ~5-6 venue read incl. regression across
event ids 130-150), $295-$370 at $36.85/hr; piece 1 alone ~3 hrs / ~$110.
UNSENT, with the owner. OPEN: whether ask 1 (launch line-up to Gurmej) has
actually gone out; no Gurmej reply in the mailbox since 2026-08-28.

## Gurmej reply 2026-09-07 19:14 + live verification 2026-09-08

Ask 1 WAS sent (launch message 09-05 12:01, campaign-status PDF 09-05 14:52).
Gurmej replied 09-07 19:14 with three items: how will Christmas suppression work
(booked + opt-outs), can send volume be increased on their mailboxes and is there
a charge, and corporate gets until end of September before he keeps or scraps it.
He did NOT answer either of the two things the launch message said it needed
before anything sends (the Big Companies UK finish/retire/fold word, and the
3-5 test inbox addresses), so the launch is still blocked on him.

Live Instantly pull 2026-09-08 (read-only; `User-Agent` header is REQUIRED, the
urllib default gets a Cloudflare 403 code 1010, same class as the Resend issue):

| Christmas campaign | Leads | Sent | Replies | Interested | Not interested | Bounced |
|---|---|---|---|---|---|---|
| Warm Re-engagement (00fc708d) | 907 | 2452 | 103 | 14 | 21 | 32 |
| Bookers (1f40cb36) | 983 | 1923 | 26 | 16 | 27 | 39 |
| Cold 3 Cities (f9e61441) | 569 | 1122 | 10 | 3 | 4 | 5 |
| **Total** | **2459** | **5497** | **139** | **33** | **52** | **76** |

- `unsubscribed_count` is 0 on all three, consistent with the deliberate
  no-unsubscribe-header style. The account block list holds exactly ONE address
  (snitha_bains@yahoo.co.uk). So the only opt-out record that exists is the 52
  manual "not interested" tags plus whatever sits unread in the reply threads.
  Re-mailing the 2,459 without rebuilding a stop-list WOULD re-contact people
  who asked to stop.
- `status=-1` NOW VERIFIED as bounced (31/39/5 against bounced 32/39/5). This
  closes the "semantics unverified" caveat carried since 09-03.
- Sender capacity, all warm (`warmup_status=1`, score 100) and NOT used by the
  corporate push: gurmej@mejimedia.com 90/day, gurmej@mejixmas.com 45,
  gurmej.p@mejixmas.com 45, bookings@christmasofficeparty.co.uk 30. That is
  210/day available without touching the three mejievent mailboxes.
- The three `mejimedia.co` mailboxes the Bookers campaign sends from are in
  warmup ERROR (`warmup_status=-1`, one at score 0). That campaign cannot send
  again as configured. Matches the "3 dead .co mailboxes" note in pilot-routing.

Live MySQL read (UTIL 8974201, `recent` 20): the `enquiries` table carries
`enquiry_status` (values seen: `new`, `in_contact`, null on brand-new rows),
`dead` (0/1), `reference`, `assigned_to` (Steve / Lauren / Jess), `last_contact`
and `next_contact`, all actively maintained by their team. So "who booked" is
suppressible by a LIVE READ of their own system, the same mechanism as the Jess
venue fix, rather than by a manual list. OPEN: which `enquiry_status` value means
booked, and whether `reference` fills on booking. Jess can answer in one line.
Side benefit: `enquiry_status=in_contact` + `assigned_to` also keeps anyone
mid-conversation with Lauren out of a bulk send.

Timing point worth putting to Gurmej: he judges corporate at end of September,
but the second domain's mailboxes only come into service early October after
warm-up. The $440 spend contributes nothing to the judgment he is making, so
holding it until after his end-of-month call costs him nothing.

## Ask 4 sent bare; Gurmej pushback 2026-09-08 19:16

Sequence: Jess 09-07 17:29 ack -> Matthias 09-07 17:56 sent the hours WITHOUT the
scope ("The hour scope of this task would be around 8-10 hours of work") -> Jess
09-07 18:04 "@Gurmej Pawar are you okay with this?" -> Gurmej 09-08 19:16 "Hi
it's 8-10 hours to stop the family christmas enquiries getting and auto
response?"

Read: Gurmej was never in the 09-01 Jess thread where the Birmingham-fallback
fault was explained, so he is pricing a one-line toggle. This is a conviction
probe, so Register B per rule_human_communication §1: restate the scope, hold the
number, no pre-emptive discount. The fix is scope, not price.

Load-bearing facts for the reply, all verified:
- Split is ~3 h family exclusion + ~5-6 h venue read. The 8-10 was only ever the
  combined figure.
- Blast radius stated HONESTLY: every event id currently in the system maps
  correctly EXCEPT 151 (13 Dec). The cost is forward: every date added from now
  lands on the `"birmingham"` fallback, and a whole next-season calendar would go
  out as Birmingham until the list is hand-edited. Silent failure, no flag.
- What the enquirer actually receives on a fallback: Birmingham's
  `##venue_name##`, `##venue_title##`, `##venue_features##`, `##venue_tiers##`
  and `##venue_phone##` (module 81 loads the Birmingham record from data store
  154401; templates substitute all five).
- 21 hardcoded event ids in module 80 (9 birmingham + 6 wolverhampton + 6
  leicester), which is the regression surface behind the 5-6 h.
- Peak-season load, verified live 09-08: the 20 most recent `enquiries` rows
  (15956-15976) span 1788864422 to 1788887721, i.e. 20 enquiries in 6.5 hours
  this morning, worked by Lauren / Jess / Steve.
- Jess's own words 09-01 endorse the root fix: "It'll mean less updates needed
  for next year too."
