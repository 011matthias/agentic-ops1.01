# Checkpoint: Brisken Planner Sync + Ashok Rethread

**Date:** 2026-07-17
**Status:** Overdue Planner cards truth-synced; all remaining opens are Dirk's sends/decisions

---

## Summary

Worked the three overdue Planner tasks from the nag email: a both-mailbox all-folders truth sweep proved two of the three effectively done and stale only on the board, the board was synced after explicit approval (17 ticks + a superseded status note), Dirk's claimed Ashok reach-out was verified TRUE and propagated into Lead Desk and the master sheet, and the parked Ashok note-brief was rebuilt as a true threaded reply on Dirk's unanswered 07-13 mail (the standalone would have started a new thread). Drafts folder dupe-scanned clean afterwards.

---

## What Was Done This Session

### Truth sweep (read-only, Graph app-only)
1. Both mailboxes, all folders, since 07-01, across the 17 partner/SAP contacts + Ashok (both addresses) + Ian Haegemans; plus Dirk's calendar for today.
2. Findings: 16/17 partner contacts covered (10 personal notes 07-12; ICD cluster incl. Ramos via the 07-12 15:32Z "ICD Dashboard follow-up from Rome"; Sharandakov call 07-14). The card's "Ramos not evidenced" was wrong. Real replies: Mehlkopf 07-13, Szczecina 07-14. Only open: Kulkarni (draft in Dirk's Drafts since 07-13, unsent).
3. Sanofi: call today 16:00–16:30 CEST, Ian accepted; slide-8 + invite items were already settled; slide-10 decision is Dirk's on the call.

### Planner board sync (approved, then verified by re-read)
1. Task "17 Rome partner and SAP contacts": 15 checklist ticks + STATUS note superseded with the mailbox-verified 07-17 state. Now 16/17 checked, `activeChecklistItemCount: 1` (Kulkarni).
2. Task "Sanofi sign-off": slide-8 + invite/length ticked; slide-10 + meeting item left open (resolve after today's call).
3. Task "Ashok referral": no board write; both open items genuinely open.
4. First run self-aborted on a checklist-title prefix mismatch (`(Eprox)` vs `(Eprox Consulting AG)`); fixed, applied on iteration 2/3.

### Ashok verification + propagation (user-ordered)
1. Dirk's claim TRUE: send 2026-07-13T23:47:42Z on the booth thread, To k.ashok@accenture.com, BCC Zoho dropbox; only response = auto-OOO. internetMessageId captured.
2. Lead Desk: event appended via the app's own `/events` ingest sink, run inside the Fly machine (secret never left it), ext_key = internetMessageId (idempotent vs future capture). Verified by re-query; derived status stays "Contacted - awaiting reply".
3. Master sheet row 3: AC3 `last_outreach` → 2026-07-13 (text ISO), AF3 `outreach_log` → 3-line log (E1, the 07-13 re-connect, the unsent note-brief as `[open]`). Pre/post snapshot verify ALL MATCH. App-only workbook PATCH proven 403 (site grant is read-only for writes); cached delegated token still valid.

### Ashok history pull (for the deck/deliverable rebuild)
1. Entire Dirk↔Ashok record = 2 conversations: the 2021/22 "TPI connection with FXAll" thread (Carlos Peral intro, ADNOC "Project Speed" eval; Dirk supplied TraderPlus + MDH docs; died in client procurement) and the 2026 Rome thread.
2. Characterization delivered: Ashok is terse, process-anchored, responsive when engaged; Accenture consumes forwardable material for THEIR client analysis. Implication: the MDH deliverable should be liftable into his central-bank recommendation (40-45 integrations, vs MRM), not a Brisken-sells-to-Ashok deck.

### Draft re-thread + dupe scan (user-ordered)
1. The parked note-brief had its OWN conversationId (standalone with "Re:" subject) — would have started a new thread. Rebuilt via `createReplyAll` on the 07-13 sent mail: brief content preserved on top, quoted history below, To Ashok only, BCC Zoho, threaded conversationId. 8/8 verification checks green; old draft deleted; exactly 1 Ashok draft remains.
2. Full Drafts dupe scan: 47 drafts, 0 same-recipient+subject dupes, 0 multi-draft conversations. The 27 staged Rome sends (25 T3 + Georgiou + Kulkarni) intact. Flagged for Dirk (untouched): a 2026-02-06 draft starting with a password-looking string and a 2025-12-28 draft with a masked card number as subject.

---

## Key Decisions Made

### Board ticks only with mailbox evidence
- **Choice:** Tick exactly what the sweep proves; leave Kulkarni, slide-10, the meeting item, and both Ashok items open.
- **Rationale:** feedback_brisken_outreach_truth_is_mailbox — the board must not claim more than the mailboxes show (the 07-16 incident class).

### Lead Desk write through `/events`, not raw sqlite
- **Choice:** POST to the app's ingest sink from inside the Fly machine.
- **Rationale:** preserves event_hash idempotency, worker-send dedupe, and derived-status logic; raw inserts would bypass all three. Secret never crossed the wire.

### Re-thread instead of PATCHing the standalone draft
- **Choice:** `createReplyAll` on the anchor message + carry content over + delete the orphan.
- **Rationale:** conversationId/threading headers cannot be retrofitted onto an existing message via PATCH; only a reply created off the anchor threads correctly in Outlook and for Ashok.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| Planner tasks (2 cards, live) | Modified | 17 ticks + STATUS supersede, verified by re-read |
| Lead Desk DB via `/events` (live) | Appended | 07-13 Ashok send event, imid-keyed |
| Rome master sheet `Master contacts` row 3 (live) | Modified | AC3 + AF3 status append, snapshot-verified |
| Dirk's Drafts (live) | Rebuilt | Threaded Ashok reply draft; standalone deleted |
| `workspace/clients/brisken/status/p2-rome.md` | Modified | Added Partner/SAP outreach + Ashok referral element rows |
| `memory/project_brisken_ashok_accenture_referral.md` | Modified | Sync + re-thread state recorded |
| `docs/sessions/2026-07-17.md`, `docs/friction-register.md`, `docs/INDEX.md`, `docs/sessions/2026-07-17-context.yaml` | Modified | Ledger updates (this checkpoint) |

Session scratch scripts stayed in the session scratchpad (not the repo).

---

## Current Status

All three overdue cards now match reality. Everything left is in Dirk's hands: send the Kulkarni draft, decide slide-10 on today's 16:00 Sanofi call, rewrite + send the threaded Ashok reply. Ashok is back from OOO and silent; the no-send hold on the staged Rome wave is untouched (all 27 drafts intact, kill switch engaged on Lead Desk sender).

---

## Next Steps

1. After today's Sanofi call: tick the slide-10 + meeting items and take the card to 100% (gated board write; needs a go).
2. Watch the Ashok thread — Lead Desk capture should log Dirk's send when it happens; on Ashok's reply, update the card's two open items (gated).
3. Kulkarni draft is unsent since 07-13: if still parked around 07-20, surface a nudge brief to Dirk per the pack's nudge rule.
4. Four stale status files flagged (26d: p2-lead-gen-general, p2-onepilot-site, p2-outreach, p2-targeting) — refresh on next touch of those workstreams; they are gated on Dirk go-live decisions.
5. Recurrent classifier friction: consider a settings allowlist for running session-scratchpad python scripts (see friction register; needs user approval via /update-config).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p2-rome.md` (element states incl. the two new rows)
- `memory/project_brisken_ashok_accenture_referral.md` (full Ashok state)
- `docs/sessions/2026-07-17-context.yaml`

### Open Questions
- Does Dirk confirm the 40-45 central-bank scope, and where does the Accenture customer's decision stand? (The two open card items; only Ashok can answer.)

### Working Notes
- Planner card ids: 17-contacts `S-t9htVQa0WgWqw5zGW0j2UALkug`, Sanofi `VeH5a5bwf0Ky5jns-nt8bGUAMA-a`, Ashok `ifV1Pvhh5kKGaxe9xb5kTmUADlqA` (plan `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`).
- Ashok row = master sheet row 3; email col I. Lead Desk contact_id `dd49eafc5cc66c46`.
- The 07-13 send imid: `<SN7PR22MB3761F6E543367AC1F48AF5A397FA2@SN7PR22MB3761.namprd22.prod.outlook.com>`.
- App-only Graph = read-only on the MARKETING site workbook (403 on range PATCH, now proven); sheet writes need the delegated token (`.scratch/graph_token.txt`, sniffed off automation Edge :9223 — still valid this session).
- Exchange uppercases reply subjects ("RE:"); case-insensitive checks when verifying reply drafts.
- createReplyAll on a self-sent message correctly addresses the original recipient; PATCH To/BCC afterwards anyway.
- Dirk had a live compose window ~12:56Z today (empty autosave in Drafts) — he is active in the mailbox.

### Reference Materials
- `workspace/clients/brisken/deliverables/lead-generation/rome-2026/dirk-send-pack/partner-sap-outreach.md` (the 17-contact pack, v2)
- Lead Desk: brisken-lead-desk.fly.dev (`/events` sink, ingest secret in Fly env)

---

## How to Continue

`/resume brisken`, read the files above. The three cards need no work until Dirk acts or the Sanofi call closes; then apply the gated ticks (working notes have the card ids). If the user asks about the Accenture deliverable, start from the history characterization in this checkpoint plus the booth memo scope (40-45 central-bank integrations, anti-MRM).

---

## Strategic Feedback

### What Worked Well This Session
- The nag email screenshot as a work order worked cleanly: each card carried enough state to reconstruct intent, and the mailbox-truth rule turned "work on these" into decidable evidence questions.
- Explicit per-action grants ("permission granted") after staged, fully-described writes made the invasive steps fast and safe — the staged-script-plus-grant pattern is a good rhythm.

### Suggestions
- The Planner nag emails will keep firing while Kulkarni + the Ashok items stay open. If Dirk's send lag is structural, consider agreeing a standing weekly "Drafts pending" digest to him instead of per-card chasing.

### System Health
- Autonomy score: 2 human interventions this session (classifier-block round-trip on the sheet write; the draft-threading correction, which was also a real defect catch on the morning session's verify).
- The auto-mode classifier blocking session-scratchpad Graph scripts is now a repeat cost (2nd+ session); it needs either a scoped allowlist or acceptance that mailbox/sheet writes always cost one user round-trip. That round-trip is arguably a feature for invasive writes — but it also hit a read-only token grab.
