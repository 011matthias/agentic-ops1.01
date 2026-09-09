# Meji Outreach: Technical Approach

**Prepared for:** Gurmej Pawar
**From:** Matthias, UnpauseAI
**Date:** 15 May 2026
**Companion doc:** "Meji Outreach: Scope and How We'll Work Together" (the what)

This is the how. It walks through the mechanics so you can see exactly how each piece is built and where the safeguards sit. Written to be followed without a technical background; where a term needs explaining, it is explained inline.

## The shape of the system

Every campaign, warm or cold, runs through the same path:

Source the list  ->  Clean and verify  ->  Segment  ->  Build the sequence  ->  Sample and approve (cold only)  ->  Send in a controlled ramp  ->  Detect replies and bounces  ->  Weekly report

The difference between warm and cold is only the first two steps. The sequence build, the sending discipline, the reply and bounce handling, and the reporting are identical. That consistency is deliberate: it is what makes the operation predictable week to week.

## 1. Warm database rebuild

The warm database is people who already know you: past customers and past enquirers. The build:

**Extract.** Pull the full warm audience from the existing records, not a partial or stale slice.

**Clean.** Remove duplicates, drop addresses that have hard-bounced before, and run every remaining address through email verification (a check that confirms an inbox actually exists before we send to it). This is the single biggest lever on bounce rate, and it happens before anything goes out.

**Segment.** Group people by how recently and how strongly they have engaged: booked before, enquired before, opened or replied to recent sends, long-dormant. Each group gets timing and copy that fits where they are, rather than one message to everyone.

**Sequence and test.** Build the follow-up sequence (next section), then send to a small warm-up batch first (50 to 100 contacts) to confirm deliverability is clean before scaling. If the warm-up batch lands well, we ramp; if anything looks off, we hold and fix before volume goes out.

**Scale.** Increase send volume gradually over about two weeks rather than all at once. Sudden spikes are one of the things spam filters react to; a measured ramp avoids that.

Christmas runs this first because it has to be live by mid-July. Banter follows on the same machinery, at lower volume.

## 2. The follow-up sequence

Every campaign uses a three-touch sequence, not a single email:

- **Touch 1:** the initial email.
- **Touch 2:** a follow-up about five days later, only to people who have not replied.
- **Touch 3:** a final follow-up about ten days after the first, again only to non-repliers.

Two automatic safeguards run underneath it:

**Reply detection.** The moment someone replies, their sequence stops. They do not get the next scheduled email. This prevents the "I already answered, why are you emailing me again" problem and keeps the conversation human from the point of reply onward.

**Bounce handling.** If an address bounces, that contact is removed from the active sequence immediately and does not receive further sends. Bounces are also tracked so a rising bounce rate surfaces in the weekly report before it becomes a deliverability problem.

## 3. Cold-data sourcing for corporate events

The previous cold campaigns failed on list quality, not on the system. The fix is a structured provider evaluation rather than trusting one source on faith.

**Same brief to every provider.** Apollo and a small set of alternatives each get the identical target brief: the right job titles (PA, EA, Office Manager, HR roles), the right company size (mid-sized UK companies), the right exclusions (no universities, public sector, charities, or one-person firms, since those were exactly the wrong-fit contacts that sank the last cold run).

**Pull a real sample from each.** Roughly 150 contacts per provider, not a sales demo.

**Score on what matters.** Each sample is scored on how many contacts actually match the brief, how clean the email verification is (tested with a small send), and cost per genuinely usable contact.

**You pick from samples.** You see the comparison and the actual sample lists, and you choose the source. The decision is made on contacts you can inspect, not on provider promises.

## 4. Per-city Christmas cold lists

For each party city (Birmingham, Leicester, Wolverhampton), the cold list is built and filtered specifically:

- **Titles:** the people who actually book corporate parties (PA, EA, Office Manager, HR), not generic job titles.
- **Company size:** mid-sized firms with the budget and the need.
- **Location:** within sensible commuting range of that city's venue, so the offer is relevant to the recipient.
- **Exclusions:** the same wrong-fit categories stripped out before the list is finished.

Each city list is checked for viability and then comes to you as a sample before it is used.

## 5. The sample-approval gate, operationally

This is the safeguard, so here is exactly how it works in practice:

1. Before any cold campaign, you receive a sample of roughly 100 to 200 real contacts from the actual list.
2. The sample shows job title, company, and location for each contact, so you can judge relevance directly.
3. You flag anything wrong (wrong roles, wrong company type, wrong area, anything that does not fit).
4. If the sample is clean, the campaign proceeds. If you flag issues, the list is reworked and re-sampled. If a provider's sample fails badly, we move to the next-best provider rather than patching a bad source.
5. Nothing sends until you have given the sample a yes.

This gate exists specifically so the bad-data failure cannot repeat. It runs on every cold campaign, every time, with no exceptions for speed.

## 6. The weekly update

Every Monday morning you get one short email. The numbers in it come straight from the sending platform's own reporting, not from estimates:

- Emails sent, bounce rate, replies, positive replies, opportunities or calls booked, and any issues or changes needed.

For now this is compiled by hand each Monday so it is reliable from week one. Once the rhythm is steady, the goal is to automate the compilation so the same report generates itself and the manual step disappears. The format stays identical either way, so it remains a 30-second read.

## 7. Protecting deliverability through September

Your eleven-year enquiry history shows a hard September peak: 20 to 25 enquiries a day sustained for weeks, with a single-day record of 42. During that window, the customer-acknowledgement inbox is already working hard, so the outbound side has to be paced carefully or deliverability suffers across the board.

The approach:

- **Spread the load.** Send across several of the existing mailboxes rather than leaning on one, so no single sending address takes a volume spike that trips spam filters.
- **Pace the cold side.** Cold campaigns ramp before August or hold during September, rather than adding heavy new volume on top of the peak.
- **Watch the early signal.** Bounce rate and reply rate in the weekly update are the early warning. If either moves the wrong way going into the peak, we slow down before it becomes a problem, not after.

## What happens when things go wrong

- **A contact bounces:** removed from the sequence automatically, counted in the weekly bounce rate.
- **Someone replies mid-sequence:** their sequence stops on the spot; the conversation becomes human from there.
- **A cold list sample fails your check:** it does not send. The list is reworked or the provider is swapped before anything goes out.
- **Bounce rate starts climbing:** it shows in the Monday update before it becomes a deliverability incident, and the send slows while the cause is found.
- **The September peak collides with active cold sends:** cold volume is paced down for the peak weeks so the warm side and the customer inbox keep their headroom.

The thread through all of it: problems surface in the weekly update early and visibly, and the safeguards (verification before send, sample approval, reply and bounce handling, paced ramps) are designed to stop the specific failures that happened before from happening again.
