# Pipeline playbook

The operation, stage by stage. Warm and cold campaigns run the same path; they
differ only in the first two stages and in whether the sample-approval gate
fires. That sameness is the point: it makes the operation predictable week to
week and runnable by someone who did not build it.

```
Source  ->  Clean + verify  ->  Segment  ->  Build sequence  ->  Sample-approve (cold only)
        ->  Controlled ramp  ->  Reply + bounce detection  ->  Weekly report
```

## Stage 1 — Source the list

**Warm.** Extract the full known audience from the client's existing records
(past customers, past enquirers), not a partial or stale slice. The warm list
is the client's own data; no purchase, no provider.

**Cold.** Never trust one provider on faith; the classic cold failure is list
quality, not the sending system. Run a structured provider bake-off:

- Give every provider (Apollo + a small set of alternatives) the **identical
  target brief**: the exact job titles that buy, the company-size band, the
  geography, and the exclusions (the wrong-fit categories that sink a run:
  usually one-person firms, public sector, universities, charities, unless the
  ICP says otherwise).
- Pull a **real sample** from each (~150 contacts), not a sales demo.
- Score each sample on: match rate against the brief, verification cleanliness
  (test with a small send), and cost per genuinely usable contact.
- The client picks the source from samples they can inspect, not from provider
  promises.

Geography is fenced here: UK/US only for cold (UWG §7). Mis-located records are
dropped at this stage, not later.

## Stage 2 — Clean and verify

The bounce-rate stage, and the single biggest lever on deliverability.

- Deduplicate; drop addresses that have hard-bounced before.
- **MX pre-filter before paid verification:** drop gateway-filtered domains
  (Mimecast and similar) and no-MX domains first, because a verifier reports
  those as valid and they still fail. Shrinks the paid-verification volume too.
  (See `reference_cold_email_gateway_bounces`.)
- Run every surviving address through email verification (NeverBounce or
  equivalent). Nothing enters a sequence unverified.

## Stage 3 — Segment

Group by engagement recency and strength (booked before, enquired before,
recently opened/replied, long-dormant) so timing and copy fit where each person
is, rather than one message to everyone. Cold lists segment by the brief axes
(city/venue, title band) instead of engagement history.

## Stage 4 — Build the sequence

Every campaign is a multi-touch sequence, never a single send. The reference
shape is three touches over roughly ten days:

- **Touch 1:** the initial email.
- **Touch 2:** ~5 days later, non-repliers only.
- **Touch 3:** ~10 days after touch 1, non-repliers only.

Two safeguards run underneath, always on:

- **Reply-stop.** The instant someone replies, their sequence halts; no next
  email. Keeps the conversation human from the reply onward.
- **Bounce-drop.** A bouncing address leaves the active sequence immediately and
  is counted so a rising bounce rate surfaces in the weekly report early.

Sequencing mechanics on Instantly: the per-step delay is the gap BEFORE the
next email, so it belongs on the EARLIER step; a delay of 0 double-sends. Verify
this in the readiness audit before any send (see
`reference_instantly_sequence_delay_semantics`).

## Stage 5 — Sample-approve (cold only)

The gate that makes the bad-data failure unrepeatable. Fires on every cold
campaign, every time, no exception for speed:

1. The client receives a sample of ~100-200 real contacts from the actual list.
2. The sample shows title, company, and location per contact, so relevance is
   judgeable directly.
3. The client flags anything wrong.
4. Clean sample -> the campaign proceeds. Flagged issues -> the list is reworked
   and re-sampled; a badly-failing provider is swapped, not patched.
5. Nothing sends until the client says yes.

Warm campaigns skip this gate (the audience is the client's own known list) but
still get a small warm-up batch (stage 6).

## Stage 6 — Controlled ramp

Volume rises gradually, never all at once; sudden spikes are exactly what spam
filters react to.

- Warm: send a warm-up batch first (50-100 contacts) to confirm deliverability
  is clean, then scale over ~2 weeks. If the warm-up lands well, ramp; if
  anything looks off, hold and fix before volume.
- Cold: ramp new domains/mailboxes through their warm-up window (3-4 weeks on a
  freshly-provisioned stack) before real volume.
- Spread load across several mailboxes so no single sending address takes a
  spike. This is also the lever for any seasonal peak (below).

## Stage 7 — Reply and bounce detection

Runs continuously, not as a step. Replies stop sequences; bounces drop contacts
and feed the bounce-rate line. This is the layer that turns the weekly report
into an early-warning instrument rather than a post-mortem.

## Stage 8 — Weekly report

One short email, same format every week, a 30-second read. Numbers come from the
sending platform's own reporting, never estimates:

> emails sent, bounce rate, replies, positive replies, opportunities/calls
> booked, and any issues or changes needed.

Compile by hand from week one so it is reliable immediately; automate the
compilation once the rhythm is steady. The format stays identical either way.
Bounce rate and reply rate are the early signals: if either moves the wrong
way, slow the send before it becomes an incident, not after.

## Seasonal-peak discipline (when the client's data shows one)

Many client businesses have a hard inbound peak (Meji's was September). Where
the client's own history shows one, it drives the calendar, not the reverse:

- Get warm campaigns live BEFORE the peak so the audience has 4-6 weeks of
  engagement before inbound competes for attention.
- Ramp cold before the peak, or hold cold during it; heavy new cold volume on
  top of a peak strains deliverability exactly when the client's own inbox
  needs headroom.
- Watch the early signal harder through the peak weeks.

Pull the client's real history to find the peak; never assume one.

## Who decides what

The split that keeps the operation moving without over-asking:

- **Client's calls:** cold-data provider (from samples), final approval on
  every cold list, sign-off on sequence copy before it sends, the commercial
  structure.
- **Our calls:** list cleaning and segmentation, the technical sequence build,
  deliverability pacing and mailbox rotation, the day-to-day operation, what
  goes in the weekly report.
- **Shared:** launch timing per campaign, and anything where the data changes
  the plan.

Bring the client a decision only when it is genuinely theirs. The weekly report
is the heartbeat; between reports, the operation runs without asking.

## Failure modes and their built-in responses

| When this happens | The response (already in the pipeline) |
|---|---|
| A contact bounces | Removed from the sequence automatically; counted in the weekly bounce rate |
| Someone replies mid-sequence | Their sequence stops on the spot; the thread becomes human |
| A cold sample fails the client's check | It does not send; the list is reworked or the provider swapped first |
| Bounce rate starts climbing | Surfaces in the Monday report before it is an incident; the send slows while the cause is found |
| A seasonal peak collides with active cold sends | Cold volume paces down for the peak weeks so warm + the client inbox keep headroom |

The thread through all of it: problems surface in the weekly report early and
visibly, and the four invariant safeguards stop the specific failures that sank
prior cold runs from recurring.
