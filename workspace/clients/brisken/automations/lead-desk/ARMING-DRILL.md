# Lead Desk, Arming Drill

The campaign engine is DORMANT: kill_switch=1, zero sends ever through the
Graph path. Before it is armed, this watched send-gate drill must pass in
an owner-present session. This file is the single spec of that drill; the
codified half is the `lead-desk-drill` CLI (`src/lead_desk/drill.py`),
which wraps the same engine plumbing the armed worker runs.

Roles and blast radius:

- Steps 1-4 and the step-6 prep are Matthias-solo. Only step 7 requires
  Dirk present.
- Every send in the drill goes to self (matthias -> matthias) or the
  chosen test address, never a prospect. The CLI's sending commands
  enforce this: they refuse any address in the contacts table and any
  target outside the step's sanctioned one. A refusal is a stop, not a
  prompt to re-type.

Where commands run: on the Fly machine, where the volume lives:
`flyctl ssh console -a brisken-lead-desk`, then `lead-desk-drill ...` /
`lead-desk-cloud-worker ...` (fly.toml sets `LEAD_DESK_DATA=/data`). The
in-app worker also ticks on its own every 15 minutes; "capture tick"
below means either its tick or a manual one.

Kill-switch mechanics (read once, before step 2): claims happen only with
the kill switch OFF and a campaign in status 'sending'. Steps 1, 3 and 4
run fully dormant. Steps 2 and 5 need a scoped, watched lift:

1. `lead-desk-drill status` - `sending_campaigns` must list EXACTLY the
   drill campaign; `guard_alerts` empty.
2. Kill 1 -> 0 (campaigns page toggle, POST /worker/kill).
3. Run the step's tick immediately.
4. Kill 0 -> 1.

Residual risk inside a lift window: the in-app loop may tick first and
fire the drill campaign's due send for real. By construction that mail
can only go to the test address.

## Prerequisites

- External test address chosen (a mailbox we control, outside
  brisken.com) and enrolled as the ONLY contact of a dedicated drill
  campaign: >= 2 email steps with the follow-up due immediately
  (day_offset 0), so the reply-halt in step 5 is observable in-session;
  small caps; `bcc_address` left at the Zoho dropbox default.
- The test address created manually as a Lead in Zoho CRM (step-6 prep),
  so the BCC dropbox has a Lead to file against.
- Invalid NDR address chosen: a nonexistent user at a real domain, e.g.
  `drill-nobody-20260813@<real-domain>`. Never @sap.com or @brisken.com;
  step 4 refuses the deny floor.
- Operator = matthias (the engine auto-sends only as matthias.silva@).

## Step 1, Dry run

- Purpose: prove the dormant engine is inert end to end: creds mint, both
  mailboxes are read, the kill switch is honored, nothing is leased,
  watermarks stay put.
- Command: `lead-desk-drill step1` (wraps one `lead-desk-cloud-worker
  --dry-run` tick and checks what it can machine-check).
- Pass criteria: kill_switch reported true; due_preview matches
  expectation (empty while dormant - the kill switch blocks even the
  peek); zero leases taken; watermarks unchanged.
- Rollback: none needed; a dry run mutates nothing. A FAIL on
  `watermarks_unchanged` can be the in-app loop's own tick landing
  mid-check; re-run.

## Step 2, Draft-to-self

- Purpose: run the FULL pipeline (claim -> render -> Graph) with every
  mail landing as a draft in the matthias mailbox and nothing acked.
- Command: the scoped lift above, with `lead-desk-drill step2` as the
  tick (wraps `lead-desk-cloud-worker --draft-to-self`). The drill
  campaign must be through both gates (Approve + Start sending) first.
- Pass criteria: one draft per due send in matthias Drafts with correct
  rendered copy (merge fields resolved, correct recipient); the attempt
  is NOT acked (stays leased, expires to stalled), so the step is
  repeatable via Retry on the campaign page. For a reply-step drill
  campaign: the staged draft must be RE:-threaded on the real anchor
  conversation (RE: subject, same conversationId) - this rehearses the
  Phase 3 createReply path end to end without sending.
- Rollback: kill back to 1 (part of the lift); delete the inspected
  self-drafts; Retry re-queues the stalled attempts.

## Step 3, Real self-send

- Purpose: first live send through the engine's Graph path (send_auto as
  matthias) plus the Sent Items evidence readback.
- Command: `lead-desk-drill step3 --to matthias.silva@brisken.com`
- Pass criteria: the CLI prints PASS with the imid found by the Sent
  Items readback; the timestamped drill mail is in the matthias inbox.
- Rollback: none needed (mail to self); delete the drill mail after.

## Step 4, NDR -> bounce -> auto-suppress

- Purpose: prove the bounce loop: engine send -> NDR arrives in the
  matthias inbox -> capture classifies the bounce keyed on the FAILED
  recipient -> the sink auto-suppresses that contact, halting every
  campaign.
- Command: `lead-desk-drill step4 --to <invalid-addr>`; wait <= 2 capture
  ticks (<= 30 min at the 15-minute interval); then
  `lead-desk-drill step4-verify --to <invalid-addr>`.
- Pass criteria: step4-verify prints PASS: a bounce event on the drill
  contact AND the contact auto-suppressed reason=bounced, within <= 2
  capture ticks.
- Rollback: none needed. The `drill-ndr-*` contact step4 registered is a
  persistent namespaced fixture (campaign 'drill', off the Rome board);
  it stays suppressed. Without it the bounce would park in the unmatched
  queue instead of rehearsing the suppress - that is why step4 creates it.

## Step 5, Reply-halt

- Purpose: prove the tick-order halt guarantee: capture runs BEFORE
  claim, so a reply that lands between ticks halts the follow-up
  server-side and the follow-up step never fires.
- Command: scoped lift; one watched tick (`lead-desk-cloud-worker`)
  sends the drill campaign's step-1 mail to the test address; kill back
  to 1. (If step 2 left that attempt leased or stalled: wait for the
  lease to expire, then Retry it on the campaign page first.) Reply from
  the test address. Wait one capture tick - the reply is ingested even
  while dormant. Scoped lift again; one watched tick; kill back to 1.
- Pass criteria: the reply event is on the test contact's timeline
  before any claim of the follow-up; the second watched tick claims 0
  for that enrollment (the follow-up step never claims); the board shows
  the contact as replied.
- Rollback: kill back to 1 after each lift; pause the drill campaign
  once the step passes.

## Step 6, Zoho BCC filing (THE still-unverified link)

- Purpose: verify that an engine send BCCed to the Zoho dropbox
  (s9hitl_pv69mu@mails4.zohocrm.com) actually files on the Lead in Zoho
  CRM. Nothing downstream confirms this automatically; it must be seen
  once in the CRM UI.
- Prep (solo, before step 5): the test address exists as a Zoho CRM
  Lead; the campaign page shows the dropbox as `bcc_address`.
- Command: none; the drill send from step 5 carried the BCC.
- Pass criteria: Zoho CRM UI -> the test Lead -> Emails related list
  shows the sent drill subject within ~15 min. Record evidence
  (screenshot + date) in the evidence log.
- Rollback: none.

## Step 7, Arm (Dirk present)

- Purpose: the only step that changes production posture: the kill
  switch goes 1 -> 0 and stays off; every campaign in status 'sending'
  becomes claimable.
- Command sequence:
  1. Scope-of-effects read aloud to Dirk: arming means the worker will
     claim and send from every 'sending' campaign at its caps, windows
     and throttles, as matthias.silva@, BCC to the Zoho dropbox; sent
     mail cannot be unsent.
  2. Explicit greenlight from Dirk.
  3. Readiness audit: evidence log shows steps 1-6 PASS;
     `lead-desk-drill status` shows `guard_alerts` empty, fresh
     heartbeat, fresh watermarks, and `sending_campaigns` = exactly the
     intended campaign(s).
  4. kill_switch 1 -> 0 via POST /worker/kill (campaigns page toggle).
- Pass criteria: worker status shows kill off (`lead-desk-drill status`
  or GET /api/worker/status); the next tick claims only from the
  intended campaign (tick report / heartbeat counters).
- Rollback: flip the kill switch back to 1 (instant, first line of
  defense); pause the campaign; the KILL file and stopping the machine
  remain the outer switches.

## Evidence log

| Date | Step | Result | Evidence |
|------|------|--------|----------|
