# AI voice receptionist

Status: idea
Added: 2026-07-28
Demand verified: no
First target: stadtmobil

## One-liner

A German-speaking AI agent answers the phone: handles bookings, FAQs, and
routing, escalates the rest to a human with full context. Sold to
phone-heavy organizations that miss, queue, or pay per-minute for calls.

## Demand (why they must buy)

Staff shortage plus phone-heavy operations; every unanswered ring is a lost
booking or job. The demo is visceral and closes the argument: call the bot
live in the meeting.

## First target: stadtmobil

Carsharing organization with a member hotline (bookings, access problems,
damage reports). Attractive as first target because the structure is
federated regional organizations under one brand (ASSUMPTION, verify): one
working install at the local org becomes a reference for every sibling org.

Open questions before any pitch (B7, enumerate first):
- Which regional org, and who owns the hotline decision?
- Hotline volume, hours, and what share of calls is routine?
- Is call handling in-house or outsourced under contract?
- Booking-system integration surface: is there an API at all?

## Supply / competition (honest)

Human answering services at per-minute/agent rates; AI voice vendors are
mostly English-first. German voice quality and latency is the technical bar,
and the moat if cleared well.

## Automation edge

Marginal cost per call near zero against per-minute human answering; 24/7
coverage without shift cost.

## Offer shape

Paid pilot on the after-hours or overflow line (fixed price, low risk for
them), then full install 2-4k EUR (ASSUMPTION) + 300-800 EUR/mo scaled by
call volume (ASSUMPTION).

## Channel (UWG-clean)

Direct local approach to the first target (local, cooperative, approachable);
then reference-sell across sibling orgs and adjacent phone-heavy niches
(clinics, Handwerk, salons). No cold email needed at any step.

## First euro

Demo bot built on stadtmobil's public FAQ and booking flows, live call in
the meeting, paid after-hours pilot. Realistic: 3-6 weeks (voice needs more
build time than the other ideas on this board).

## Risks / open questions

- German STT/TTS latency and quality under real phone-line conditions.
- GDPR and call-recording consent; announcement requirements.
- Hotline may be contractually outsourced; decision cycle unknown.
- Member acceptance: a badly handled emergency call (lockout at night) is
  reputational damage; escalation design is load-bearing, not a feature.
