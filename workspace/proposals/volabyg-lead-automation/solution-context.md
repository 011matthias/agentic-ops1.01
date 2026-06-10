# VolaByg (p026); Problem + Solution Context (canonical)

Source of truth for the landing-page narrative under
`platform/public/clients/volabyg-lead-automation/` and the proposal
markdown `platform/src/content/proposals/volabyg-lead-automation.md`.
Supersedes the earlier framing that treated the spam and the count gap
as one root cause and asserted authentication rejection as fact. When
landing-page copy conflicts with this file, this file wins.

Last updated: 2026-06-10

---

## Prospect

VolaByg (Volabyg Aps), Danish construction and renovation SMB (painting,
floor sanding, facade and tile work) serving private clients, businesses,
and housing associations. Contact: Ibrahim. Domain: volabyg.dk. Source:
Upwork. Proposer on the video and pages: Matthias. He asked for one owner
of the whole lead flow, "from A to Z", and asked directly for a pricing
structure.

## Current setup

Facebook (Meta) Lead Ads bring leads in, a Google Sheet holds them, and
Instantly sends a 3-step email sequence (day 0, day 2, day 4 to 5) back to
each lead.

## The two symptoms (two separate problems, not one)

1. A large share of the sequence emails land in spam. Deliverability.
2. The Facebook lead count does not match the replies and engagement he
   sees. Data loss.

These have different causes and need different fixes. The landing page
must keep them distinct. Do not claim a shared root cause. The shared
element is the pipeline and the owner, not the cause.

## Verified facts (public DNS, 2026-06-09)

- SPF: `v=spf1 include:spf.simply.com -all`
- DMARC: `p=reject`
- MX: `mx.simply.com`

Accurate reading: this is a strict, correctly configured policy. Only the
provider (Simply.com) is approved to send as volabyg.dk, and mail that
fails authentication is rejected. This is good security, and it leaves
zero margin for any third-party tool that is not authenticated exactly
right.

## Confidence flags (what the page must NOT assert)

- Do NOT state that Instantly mail "is being rejected". Whether the reject
  policy bites depends on how Instantly is wired, which has not been
  observed:
  - If Instantly sends through his Simply.com mailbox, authentication
    passes and nothing is rejected.
  - If Instantly sends from separate domains (its own recommended cold
    setup), volabyg.dk's policy is irrelevant to the sending.
  - Only if Instantly sends as volabyg.dk through its own infrastructure
    is the mail rejected.
  Phrase the auth point as something the audit confirms: "whether your
  mail is rejected or just filtered".
- Do NOT assert "no DKIM". A public lookup only checks common selectors;
  absence cannot be proven from outside.
- Note the tell: the reported symptom is "spam", not "bounced". Mail that
  truly fails a reject policy bounces; it does not land in spam. So the
  symptom leans toward accepted-but-filtered (the cold-tool cause) more
  than rejected (the auth cause). This is the reason to confirm before
  asserting.

## Problem 1; spam (deliverability), causes weighted by certainty

- Always applies (lead with this weight): Instantly is a cold-outreach
  tool (rotating mailboxes, warmup, aggressive sending). His leads are
  warm; they opted in on an ad. Warm mail sent through cold-outreach
  infrastructure gets filtered into spam on reputation alone, even when
  authentication passes.
- Depends on setup: if Instantly sends as volabyg.dk without aligned
  authentication, the strict reject policy discards that mail. Real and
  common, but conditional on his configuration.

## Problem 2; count gap (data loss), separate, two causes

- Real transfer loss: the handoff carrying each lead from Facebook into
  the Google Sheet quietly drops some. Likely culprits: an expired Meta
  Leads Access connection (the permission that lets the handoff pull new
  leads out of Facebook), a filter or dedup step skipping rows, or leads
  stuck in Meta's forms library that never sync across.
- Invisible-alert loss: some "missing" leads are not lost. His own
  internal lead alerts land in the same spam folder, so leads that did
  arrive were never surfaced to him.

Meta reports one number, the sheet shows fewer, and some that arrived were
never seen. The audit separates the two.

## Why two problems point to one owner (the positioning)

The two problems need two different skill sets. The usual hire is one or
the other: a deliverability specialist who will not work on the Facebook
automation, or an automation person who does not understand email
authentication. Each fixes their half and the other half stays broken.
One owner of the whole pipeline is the fix. Ibrahim's instinct to want one
A-to-Z owner is correct, and this is the page's central argument. Support
it with the live UK lead-gen client running the same stack (form to sheet
to authenticated sequenced email with reply detection).

## How we confirm it (audit, first action)

Read-only; nothing that is sending today is changed. Pull the DNS and the
handoff's run history, then reconcile three numbers over one window: what
Facebook reported, how many rows reached the sheet, how many entered the
sequence. Output: the real percentage being lost, split into
deliverability loss (rejected or filtered) versus transfer loss (dropped
before the sequence).

## Solution; three phases (= pricing)

- Phase 1, Audit, EUR 850. The read-only diagnosis above. Deliverable: a
  written findings report with real numbers from his data. Low-commitment
  way to see the findings before committing to a rebuild.
- Phase 2, Rebuild, EUR 1,900. Move warm leads onto an authenticated,
  transactional sending path instead of cold rotation; preserve the 3-step
  sequence; add reply detection that stops the sequence; a logged,
  verified handoff so no lead is silently dropped and the Facebook count
  and the delivered count agree.
- Phase 3, Ongoing management, EUR 600 per month. Deliverability
  monitoring, sequence iteration, one place to see lead counts end to end.

## Differentiators

- One owner, A to Z (his words), justified by the two-skill-set argument.
- Runs this exact stack in production for a live UK lead-gen client. Makes
  the diagnosis earned, not generic.
- EU and CET (same timezone as Denmark), GDPR by design. Facebook Lead Ads
  capture consumer personal data, so an EU owner lowers his compliance
  risk versus a non-EU contractor.

## Landing-page adjustments implied by this file

- index.html / solution.html: reframe from "one root cause" to two
  distinct problems sharing one pipeline and one owner. Lead the spam
  section with the cold-tool cause; present the strict-DNS finding as a
  verified observation with the auth consequence phrased as
  audit-confirmed, not asserted.
- Remove any copy stating mail "is failing authentication" or "is being
  rejected" as fact; rephrase as the reject-or-filter question the audit
  answers.
- Keep the count-gap section split into transfer loss and invisible-alert
  loss.
- Investment and timeline pages already match the three-phase structure;
  no change needed beyond consistency with the above.
