# Checkpoint: Meji D1 Past-Attendee Correction and Gurmej-Voice Cadence

**Date:** 2026-05-17
**Status:** D1 copy redrafted in Gurmej's voice (round 2); send still gated on Q1 + verification

---

## Summary

Started by drafting the full D1 recognition cadence on the locked low-familiarity premise, then the user surfaced screenshots of the live Christmas Bookers campaign proving the 983 are PAST Moonlight & Mistletoe attendees, not strangers. Corrected the premise (third correction on this deliverable), pulled the full live sequence as primary evidence, resolved Q4/Q5/Q6 with the user, and redrafted the cadence in Gurmej's own voice (round 2, supersedes round 1).

---

## What Was Done This Session

### Copy build
1. Drafted full Touch 1-4 D1 cadence, Seg A + Seg B, on the low-familiarity premise (`d1-recognition-cadence-copy-round1-2026-05-17.md`).
2. After premise correction, redrafted as 8 emails in Gurmej's existing voice (`d1-cadence-gurmej-voice-round2-2026-05-17.md`); round 1 banner-flagged DO-NOT-SEND.
3. Drafted the copy-ownership question to Gurmej (`ask-gurmej-copy-ownership-2026-05-17.md`).

### Premise correction (the core event)
4. User screenshots → pulled full live Christmas Bookers sequence read-only (`scripts/meji_d1_pull_existing_sequence.py` → `context/d1-existing-sequence.json`). All 4 Step-1 variants + Step-2 address recipients as past M&M guests/clients.
5. Reconciled the contradiction with the old "scraped list" finding: the prior test cross-reffed the enquiry DB; enquiry ≠ attendee, so it never disproved attendance. Single-shot unverified import is a deliverability fact only.
6. Updated design doc, project memory, MEMORY.md index; resolved Q4 (Christmas reactivation, early/spaced), Q5 (build around his voice), Q6 (anchor via the event).

---

## Key Decisions Made

### Audience definition corrected to past M&M attendees
- **Choice:** The 983 are warm-but-lapsed past Moonlight & Mistletoe attendees, not cold/low-familiarity.
- **Rationale:** The operator's own live outbound copy is the authoritative audience definition and explicitly asserts attendance ("had a blast at the last Christmas party", "since we worked together").

### Build the cadence in Gurmej's existing voice (Q5)
- **Choice:** Re-pace his live copy into the locked cadence rather than write fresh copy.
- **Rationale:** User directive; his voice is already captured and is what the audience has seen.

### Two deliberate deviations from his live copy, flagged for review
- **Choice:** Pull the ask out of Touches 1-2; drop the year-round/Adidas-Polestar cross-sell pivot, keep Christmas focus.
- **Rationale:** Cadence needs no-ask recognition early; D1's objective is Christmas reactivation, not the year-round cross-sell his live copy pushes.

### Q1 reclassified from draft-blocker to send-blocker
- **Choice:** Proceed with the draft; Q1 (pure attendees vs mixed list) now gates SEND only.
- **Rationale:** His voice assumes shared history regardless of author, so the draft is unblocked; the mixed-list risk is a pre-send hygiene caveat.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/context/drafts/d1-recognition-cadence-copy-round1-2026-05-17.md | Created, then DO-NOT-SEND banner | Round-1 cadence (premise-invalidated) |
| workspace/clients/meji-media/context/drafts/d1-cadence-gurmej-voice-round2-2026-05-17.md | Created | Round-2 cadence in Gurmej's voice (current) |
| workspace/clients/meji-media/context/drafts/ask-gurmej-copy-ownership-2026-05-17.md | Created | Copy-ownership question (answered = Q5) |
| scripts/meji_d1_pull_existing_sequence.py | Created | Read-only pull of live sequence copy |
| workspace/clients/meji-media/context/d1-existing-sequence.json | Created | Primary evidence: live sequence dump |
| workspace/clients/meji-media/context/d1-recognition-cadence-design.md | Modified | Premise rewrite + open questions + Q4/Q5/Q6 resolutions |
| memory/project_meji_warm_rebuild_d1.md | Modified | Premise correction + resolutions appended |
| memory/MEMORY.md | Modified | Index line corrected |

---

## Current Status

D1 cadence redrafted in Gurmej's voice and persisted, awaiting his voice/re-pacing review. Nothing sent (external-comms + B5 gates intact). Comms log last contact 2026-05-15 (~2 days, current). No `platform` section in meji-media infrastructure.yaml.

---

## Next Steps

1. Gurmej review of round-2 (`d1-cadence-gurmej-voice-round2-2026-05-17.md`): the two flagged deviations (ask pulled from T1-2; year-round pivot dropped) plus phrasing fidelity.
2. Resolve Q1 (are all 983 genuine attendees or a mixed list) — Gurmej fork; governs whether a softer no-shared-history variant is needed before send.
3. Resolve Q5-operational: is the live campaign actively sending to the 983 right now (double-send / September-timing risk) — read-only Instantly check when this becomes the active thread.
4. Pre-send hygiene (verify all 983, sentiment-triage the 41) — B5-gated operator work.
5. Run platform feasibility assessment for meji-media (no `platform` section in infrastructure.yaml).

---

## Context for Next Session

### Files to Read First
- workspace/clients/meji-media/context/d1-recognition-cadence-design.md (premise + open-questions block, 2026-05-17)
- workspace/clients/meji-media/context/drafts/d1-cadence-gurmej-voice-round2-2026-05-17.md (current draft)
- workspace/clients/meji-media/context/d1-existing-sequence.json (Gurmej's live voice, primary evidence)
- memory/project_meji_warm_rebuild_d1.md (full correction history)

### Open Questions
- Q1: Are the 983 pure past M&M attendees or a mixed/prospect-padded list? (Gurmej; gates send, not draft)
- Q5-op: Is the live Christmas Bookers campaign actively sending right now? (read-only checkable)
- Q2/Q3: Source system of record; recency/which year(s). (data-first, then Gurmej; non-blocking)
- Q7: Address verification on the unverified single-shot import. (B5 operator)

### Working Notes
- The premise has now been corrected three times on this one deliverable: cold (data) → low-familiarity (2026-05-16 user) → past-attendee (2026-05-17 user, primary evidence). Root cause of the thrash: the live campaign copy, the authoritative audience definition, was never pulled until the user forced it via screenshots. Do not re-investigate the provenance ambiguity; it is documented and is genuinely a Gurmej question.
- Reconciliation that resolves the apparent contradiction: enquiry DB ≠ attendee list. M&M guests come via ticketing/group-booking/guest-list, not the Christmas enquiry funnel, so the old "86% unmatched" never disproved attendance.
- Cadence STRUCTURE (4 touches, Seg A 41 / Seg B 942, ask none→clear, Jun→Aug) survived all three premise corrections; only the voice/framing changed.
- Placeholder-leak suppression that works: `<!-- output-allow:placeholder-leak:N ... -->` on the line BEFORE the span (line 2), and never put literal mustache braces in the comment text (the validator's own regex matches them).

### Reference Materials
- scripts/meji_d1_pull_existing_sequence.py (re-runnable read-only sequence pull)
- Prior checkpoints: docs/2026-05-16 - Meji D1 Christmas Bookers Premise Broken/

---

## How to Continue

Pick up on Gurmej's review of the round-2 draft. If he approves the two flagged deviations, the voice/structure is settled and the remaining path is Q1 confirmation + pre-send hygiene before any send. Do not send anything; external-comms and B5 gates remain.

---

## Strategic Feedback

### What Worked Well This Session
- The user surfacing the live campaign screenshots was the single highest-leverage input of the whole D1 thread; it resolved in one step a premise that three sessions of metadata forensics had circled around.
- Answering open questions interactively two at a time (Q4/Q6, then Q5) kept the rebuild moving without a large client round-trip.

### Suggestions
- For any "what is this audience" question, ask for or pull the existing outbound copy first. It is faster and more authoritative than provenance forensics, and it is read-only.

### System Health
- `missed-tool` gap: there is no gate that forces reading existing campaign copy before an audience-definition call. This caused a three-session premise thrash. Operationalization candidate: a workflow step or `tools/` helper that dumps live sequence copy before any audience-definition or cadence-design task. Recommend `/system-dev` to close this.
- Autonomy score: 3 interventions this session (1 user-detected premise correction, 2 agent/hook-caught). Borderline; the premise-thrash root cause is structural and worth a /system-dev pass.
