# Checkpoint: Meji Two-Piece Pilot State Lock and Piece 1 Cadence

**Date:** 2026-05-24
**Status:** Piece 1 copy drafted, awaiting send to Gurmej; Piece 2 ICP fully locked, ready to source; separate-domain approved, execution gated on user.

---

## Summary

Worked Pieces 1 (warm Christmas follow-up) and 2 (corporate cold list) across three Gurmej message exchanges. Locked Piece 1 strategy (Branch C: Christmas-primary with year-round secondary), Piece 2 ICP (UK-wide corporate + 3-city Christmas, role split at 50), and the separate-domain decision (not subdomain). Drafted the Piece 1 3-touch cadence using Gurmej's own Instantly vocabulary. DNS recon surfaced that `mejimedia.co` (the existing campaign's configured sending mailboxes) does not resolve, flagged as a Piece 1 pre-send dependency.

---

## What Was Done This Session

### Client messages drafted, iterated, sent

1. Piece 1 strategy verification (Branch A year-round-until-peak vs Branch B Christmas-forward). Sent. Gurmej answered Branch C (hybrid: Christmas-primary, year-round secondary).
2. Piece 2 geographic question (regional Midlands recommendation vs UK-wide). Gurmej answered UK-wide for corporate, 3 cities for Christmas.
3. Separate-domain proposal (course-correcting from the subdomain Gurmej had earlier approved). Gurmej approved.
4. Piece 1 3-touch cadence drafted in Gurmej's vocabulary; supersedes the round-2 4-touch draft from 2026-05-17.

### State files locked / updated

- `context/piece1-warm-followup-status-2026-05-22.md` — created + updated to UNBLOCKED (Branch C).
- `context/piece2-cold-list-scope-locked-2026-05-22.md` — created + updated (geo closed).
- `context/cold-sending-domain-setup-plan-2026-05-22.md` — created (full runbook); Decision 1 marked LOCKED.

### DNS recon

- `mejimedia.com`: Google Workspace; mature DMARC (`p=quarantine`); already runs Brevo + MailerLite for marketing.
- `mejimedia.co`: NXDOMAIN (confirmed two resolvers). The Christmas Bookers campaign's sending mailboxes live here. Flagged Piece 1 pre-send dependency.

---

## Key Decisions Made

### Piece 1 strategy: Branch C (hybrid)

- **Choice:** Christmas-primary with year-round corporate-events as a supporting mention in every touch.
- **Rationale:** Gurmej 2026-05-24 — "trying to get them back for Christmas but letting them know we do other corporate events." Original Nov-2025 year-round opener was a Nov-launched fallback because Christmas was already gone that year, not the long-term strategy.

### Piece 2 geography

- **Choice:** UK-wide for corporate; 3 venue cities (Wolverhampton/Leicester/Birmingham) for Christmas.
- **Rationale:** Gurmej 2026-05-24 — "The cold database would be UK wide." Overrode my regional-Midlands recommendation. Christmas remains venue-bound by definition.

### Separate domain over subdomain

- **Choice:** Separate domain (e.g. `meji-events.com`) for cold sending, not a subdomain of `mejimedia.com`.
- **Rationale:** Reputation isolation. Subdomain reputation bleeds into root; `mejimedia.com` runs client comms + Brevo/MailerLite marketing + Google Workspace and can't absorb cold-prospecting risk. Gurmej approved.

### 3 touches, single segment

- **Choice:** Touch 1 (early June reconnect) + Touch 2 (late June timing pressure) + Touch 3 (mid-late July direct ask). One sequence, no Seg A/B reply-status split.
- **Rationale:** Matches Gurmej's "Steps 2 and 3" framing exactly (opener + 2 follow-ups). 41/942 split dropped for v1 simplicity; can re-introduce later if value justifies.

### Voice and vocabulary lifted from Gurmej's live copy

- **Choice:** Every touch built from phrases Gurmej already uses in his Christmas Bookers sequence ("I sure did," "we handle events all year round," "I'd be happy to align," "If yes, happy to give you a ring," p.s. "google meji media," "Sent from my iPhone").
- **Rationale:** User direction 2026-05-24. The new copy is in Gurmej's voice because it IS his vocabulary, not paraphrased.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `context/drafts/reply-to-gurmej-warm-opener-consolidation-2026-05-22.md` | Created, rewritten, marked sent | Piece 1 strategy verification (Branch A/B); sent 2026-05-22 |
| `context/drafts/reply-to-gurmej-cold-list-geography-2026-05-22.md` | Created | Piece 2 geographic question with recommendation |
| `context/drafts/reply-to-gurmej-separate-domain-2026-05-22.md` | Created | Separate-domain proposal (course-correct from subdomain) |
| `context/drafts/d1-cadence-3touch-christmas-primary-2026-05-24.md` | Created, rewritten | Piece 1 3-touch follow-up cadence in Gurmej's vocabulary; supersedes round-2 draft |
| `context/piece1-warm-followup-status-2026-05-22.md` | Created, updated 2026-05-24 | Piece 1 tracking; BLOCKED to UNBLOCKED Branch C |
| `context/piece2-cold-list-scope-locked-2026-05-22.md` | Created, updated 2026-05-24 | Piece 2 ICP scope lock; geographic question closed |
| `context/cold-sending-domain-setup-plan-2026-05-22.md` | Created, edited 2026-05-24 | Cold sending domain runbook; Decision 1 LOCKED |
| `memory/feedback_anchor_on_clients_words.md` | Created | New feedback memory: anchor on client's actual words; do not paraphrase, speculate, or re-ask what they've defined |

---

## Current Status

- **Piece 1:** Copy drafted (`context/drafts/d1-cadence-3touch-christmas-primary-2026-05-24.md`). Awaiting user to send to Gurmej for copy review. One open question for him (phrasing + Touch 1 subject). Pre-send dependency: resolve the `mejimedia.co` mailbox question.
- **Piece 2:** ICP fully locked. Ready to translate into Apollo filter spec and pull a 100-200 sample. Apollo access + NeverBounce subscription needed (small pass-throughs to Gurmej).
- **Subdomain:** Decision locked. Execution needs user-side action: domain name choice, provider account (recommend Mailforge / Zapmail), domain registration, DNS records, 3 mailboxes, warm-up start. Long-lead: warm-up takes ~3-4 weeks.
- **Commercial frame:** 8 hrs / $266 fixed for both Pieces 1+2; separate ~3-5 hrs for subdomain setup, also separately approved. Retainer renegotiation deferred to post-delivery.

---

## Next Steps

1. **User sends the Piece 1 cadence draft to Gurmej** for copy review (the one open question is in the doc).
2. Begin Piece 2: translate ICP into Apollo filter spec; pull sample of 100-200; deliver to Gurmej for green-light.
3. User picks subdomain provider + domain name; register and start warm-up (long-lead, start ASAP).
4. Pre-send for Piece 1: verify what the warm campaign actually sends from (the `mejimedia.co` flag).
5. Apply Gurmej feedback on cadence copy; build fresh Instantly campaign; schedule Touch 1 for early June.

---

## Context for Next Session

### Files to Read First

- `context/piece1-warm-followup-status-2026-05-22.md` (Piece 1 current state, Branch C confirmed)
- `context/piece2-cold-list-scope-locked-2026-05-22.md` (Piece 2 ICP locked)
- `context/cold-sending-domain-setup-plan-2026-05-22.md` (cold-sending runbook, Decision 1 locked)
- `context/drafts/d1-cadence-3touch-christmas-primary-2026-05-24.md` (the Piece 1 deliverable, drafted not sent)
- `memory/feedback_anchor_on_clients_words.md` (new this session — anchor on client's actual words)
- `memory/feedback_negotiation_posture.md` (durable lesson from the earlier Gurmej pushback)
- `memory/feedback_client_comms_tone.md` (tone register)
- `memory/project_meji_warm_rebuild_d1.md` (Piece 1 background, audience verification)

### Open Questions

- Gurmej feedback on Piece 1 cadence copy (phrasing + Touch 1 subject).
- What does the warm Christmas Bookers campaign actually send from? `mejimedia.co` returns NXDOMAIN.
- Subdomain provider choice (Mailforge / Zapmail vs Google Workspace).
- Cold sending domain name (e.g. `meji-events.com`).

### Working Notes

- The four Step 1 variants (A/B/C/D) in the existing warm campaign all pitch year-round corporate events with M&M as the hook. Branch C inverts: Christmas leads, year-round becomes a supporting mention.
- The Christmas Bookers campaign is exhausted (982/983 contacted, dormant since ~Feb 2026). Implementation = fresh campaign, NOT reactivation (which would re-send old Step 1 to all 983).
- 38 known bounces excluded before send (945 sendable from 983).
- DMARC on `mejimedia.com` is `p=quarantine`; a subdomain inherits org policy unless given its own `_dmarc` record. One reason separate domain is cleaner for cold.
- DNS recon showed Meji already used the separate-domain pattern: `mejimedia.co` was their cold sending domain, now lapsed.
- 41/942 reply-status segment split dropped for v1; can be reintroduced once base sequence proves out.

### Reference Materials

- Live Christmas Bookers sequence (Gurmej's actual voice): `context/d1-existing-sequence.json`
- D1 audience xref data: `context/d1-attendee-xref-result.json` (98.4% match to past attendees)
- D1 segment recheck: `context/d1-segment-recheck.json` (41/942 reply-status split)

---

## How to Continue

Resume the Meji client work. The immediate live action is sending the Piece 1 cadence draft to Gurmej (file exists, no further edits needed unless user has feedback). After that, work proceeds along three parallel tracks: Piece 1 (waiting on Gurmej review → build campaign), Piece 2 (Apollo source → sample → review → full list), subdomain (user-side execution → start warm-up). The cross-cutting `mejimedia.co` flag must be resolved before Piece 1 sends.

---

## Strategic Feedback

### What Worked Well This Session

- Structured state-locking via context files (piece1, piece2, cold-sending plan) made multi-track progress legible and survives compaction. Reusable pattern for multi-piece engagements.
- DNS recon as an autonomous diagnostic step surfaced the `mejimedia.co` issue before it became a runtime surprise. Small, fast, high-value autonomous check.
- Re-using Gurmej's own copy as the vocabulary source for the cadence draft (after user redirected to it) produced a draft genuinely in his voice rather than a paraphrase. General principle: when a deliverable needs to be in a client's voice, mine their existing output for verbatim phrasing first.

### Suggestions

- For future multi-piece engagements, set up state-lock files for each piece earlier in the work. The piece1/piece2/cold-sending lock-files made the state legible only after several Gurmej rounds; could have been established sooner.
- Default to one review question per deliverable, only for items the client hasn't already settled. User had to explicitly correct "no overload in questions." Trim aggressively.

### System Health

- Autonomy score: 4 human interventions this session (elevated — but all four cluster on the same theme: speculating/paraphrasing/over-asking beyond the client's stated words. Captured in new memory `feedback_anchor_on_clients_words.md` so the pattern is preventable next session).
- Recurring noise: B1 stop-hook fires meta-text false positives on quoted-client-message patterns in drafts. Known F2 deferred item from earlier system-anneal. Not blocking but adds friction noise during comms-heavy work.
