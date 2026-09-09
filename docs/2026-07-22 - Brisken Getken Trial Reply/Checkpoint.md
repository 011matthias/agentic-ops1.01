# Checkpoint: Brisken Getken Trial Reply

**Date:** 2026-07-22
**Status:** Reply sent; suppression list owed to getken by Thursday 2026-07-24

---

## Summary

Assessed Cristian Funze's (getken.ai) answer on the Brisken cold-email trial, then sent the reply from `matthias.silva@brisken.com` via Graph: launch approved conditional on his two fixes, our suppression-list dedup, and TreasuryCentral-lead naming, with the TreasuryCentral Solutions Overview deck attached.

---

## What Was Done This Session

### Assessment
1. Evaluated Cristian's reply: qualifier root cause (audience definition gates before the ERP disqualifier runs; Pfizer/AbbVie survived by model luck) and tenure diagnosis (subject pulled 17.7y company tenure, body pulled 5.4y role tenure, no cross-field check) both judged sound; his infra account matches our records (Brisken's 53 domains really are unprovisioned).
2. Recalibrated conditions after the owner's "this is free" push-back: dropped preview-verification, success-bar number, shared-infra and geography gates; kept two, because the 834-contact pool is Brisken's future prospect universe regardless of who pays for sending.

### Outbound (sent)
3. Reply sent 2026-07-22 14:36 UTC in-thread ("RE: Cristian Out of Office" — thread carries his auto-OOO subject) to cristian@getken.ai, cc valentina@ken.so. Content: launch yes once qualifier + tenure fixes land; hard precondition 1 = suppression list from us by Thursday, pool dedup confirmed before first send; point 2 = naming stated as settled (TreasuryCentral lead product, OnePilot the platform layer behind), live links brisken.com + onepilot.brisken.com, deck attached as the framing reference.
4. Attachment byte-verified: `Brisken - TreasuryCentral Solutions Overview 2026-07-21.pptx` (469,208 B, `listItemUniqueId` = the user's sourcedoc GUID `7624408f-c1f8-440a-a540-48ac207b030c`, pulled app-only from `2026_PPTX/Asset Testing`).
5. Pre-send readiness script asserted recipients, threading, attachment size, content markers, em-dash zero; send confirmed by Sent Items readback (`attach=True`).

---

## Key Decisions Made

### Launch answer is conditional-yes, two gates only
- **Choice:** Keep suppression dedup (hard) + naming alignment; drop the other five candidate conditions.
- **Rationale:** Free trial removes financial exposure but not relationship exposure: one first-touch per contact at Pfizer/FMC/AstraZeneca-class treasury teams, and overlap with Zoho customers / active Rome threads would burn live relationships.

### Naming stated as settled, not pending approval
- **Choice:** Owner direction: TreasuryCentral lead, OnePilot behind; no approval mention in the mail.
- **Rationale:** Hierarchy already decided (brand flip 2026-06-18; Dirk's V3 handoff). My draft's "Dirk's call, may have moved" hedge was corrected — see friction.

### Reply-all, thread preserved
- **Choice:** `createReplyAll` keeping valentina@ken.so in CC rather than a fresh mail.
- **Rationale:** Standard thread behavior; the mangled OOO subject is the thread's identity, changing it would fork the conversation.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p2-outreach.md` | Modified | Getken trial element added; cold-email prose nuanced (vendor trial vs retired in-house channel); `updated:` bumped |
| `docs/sessions/2026-07-22-getken.md` | Created | Session-log shard (sibling sessions live; nightly sweep folds it) |
| `docs/sessions/2026-07-22-context.yaml` | Modified | `getken_trial` block merged under brisken |
| `docs/INDEX.md` | Modified | Row added under brisken |
| `docs/friction-register.md` | Modified | 1 row (missed-memory-recall) |

No repo commits: ledger reaches main via a docs/... PR only (G1), and the shared tree holds live sibling sessions. Scratch scripts (Graph stage A–D) stayed in the session scratchpad.

---

## Current Status

Email delivered and verified in Sent Items. Ball split: Cristian owes the qualifier + tenure fixes and the dedup confirmation; we owe the suppression list by Thursday 2026-07-24. Trial success bar = meetings booked (deliberately no number; free trial).

---

## Next Steps

1. **Build the suppression list** (Zoho `Account_Status` customers + Rome master-sheet active contacts + ANON opt-outs) — blocked on one owner decision: plain emails vs hashed emails (the list discloses Brisken's customer/prospect names to an external vendor; hashed lets him dedup without reading them).
2. Send the list to Cristian by Thursday 2026-07-24 (Register-A message, short).
3. When his re-run preview arrives, spot-check: AstraZeneca + BMS present, no same-industry flip-flops, per-segment mix (his own admission: top-of-ranked previews skew senior).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p2-outreach.md` (getken element row)
- `docs/sessions/2026-07-22-context.yaml` (`getken_trial` block)

### Open Questions
- Suppression list shape: plain vs hashed? (owner)
- Does Dirk know the trial leads with a free-teardown ask and RAPSODY as the delivery vehicle? (Cristian answered Dirk's question in-thread; assumed yes.)

### Working Notes
- The getken thread lives ONLY in `matthias.silva@brisken.com` (one inbound from cristian@getken.ai since 07-01); subject is "Re: Cristian Out of Office" — filter on sender domain, not subject.
- Graph mechanics that worked: app-only token → all-folders message scan with `$filter` on receivedDateTime + local sender match; drive `root/search(q=...)` then GUID-check `sharepointIds.listItemUniqueId` against the sourcedoc parameter; `createReplyAll` → PATCH body (prepend above quoted history) → POST attachment (<3 MB simple fileAttachment) → send → Sent Items readback.
- First send attempt aborted on my own readiness check scanning the QUOTED history for banned phrases (false positive); re-check against the new-content segment only, then send. Scope readiness string-checks to the content you authored.
- Trial facts from Cristian: 834-person pool, 345 (~41%) ops titles; 9 warmed inboxes on alphapartnersco.com / apexbridgeco.com / apexpartnersco.com, 10/day each; Brisken-branded domains connectable under paid engagement; one test arm asks for a call instead of the teardown.

### Reference Materials
- Deck source: SharePoint MARKETING `2026_PPTX/Asset Testing`, sourcedoc `{7624408F-C1F8-440A-A540-48AC207B030C}`
- Live naming evidence: https://www.brisken.com, https://onepilot.brisken.com

---

## How to Continue

`/comd_resume brisken`, read the getken_trial block, get the owner's plain-vs-hashed call, build the suppression list from Zoho + Rome sheet + ANON set, send it (Register A), tick the precondition with Cristian.

---

## Strategic Feedback

### What Worked Well This Session
- The owner's "this is free so we don't have much to lose" push-back was a high-value recalibration: it collapsed seven conditions to the two that actually protect Brisken assets, and the reply got sharper for it.

### Suggestions
- The Thursday suppression-list promise is now an external commitment with a date. Answering the plain-vs-hashed question early (one word) keeps it comfortably deliverable.

### System Health
- Autonomy score: 1 human intervention this session.
- The Graph send path (find thread → verify file by GUID → readiness-checked reply-all with attachment) is now a proven 4-stage pattern living only in scratchpad scripts; third occurrence this week of scripted pre-send readiness + Sent Items readback (Nestle mails, Lead Desk drill, this). Candidate for a `tools/` helper (`graph-send.py`) — if it recurs once more, that is `infrastructure-deferred`.
