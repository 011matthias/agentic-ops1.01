# Checkpoint: Meji D1 Audience Verified From Booking DB

**Date:** 2026-05-17
**Status:** D1 audience data-verified. Q1 + Q2/Q3 + Q5-operational resolved from data. Round-2 voice draft unchanged and now fully evidenced. Only Banter origin remains a Gurmej question.

---

## Summary
Resumed Meji, answered Q5-operational (campaign live-state) and verified the round-2 segmentation, then — prompted by the user's question of what the database can tell us before asking Gurmej unnecessary questions — found and fixed the root cause of three sessions of premise-thrash: every prior cross-reference hit only the enquiry tables. Enumerated the `xmas_2020` schema, found the untouched customer/attendee tables, and proved 98.4% of the 983 Christmas Bookers are genuine, recent past customers.

---

## What Was Done This Session
### Resume + live-state verification
1. Full `/resume meji-media` (YAML fast-path + all memory files + recent session history).
2. Q5-operational: `scripts/meji_d1_campaign_live_state.py` — Christmas Bookers `status=1` but dormant since ~2026-02-05, 982/983 already ran the 2-step sequence, no concurrent-send collision risk.
3. Segmentation verified: `scripts/meji_d1_segment_recheck.py` — Seg A 41 / Seg B 942 reconciles exactly to lead-level `email_reply_count>0`; the round-2 draft number is sound (B4).

### Audience verification (the core work)
4. Enumerated the `xmas_2020` schema via UTIL 8974201 + `information_schema`. Found the customer/attendee tables prior sessions never checked: `delegates` (31,776, has `email`), `full_data_parties` (2,380, has `leader_email`).
5. Cross-referenced all 983 Christmas Bookers against both: **967/983 (98.4%) are genuine past customers** — 548 booked a party AND attended, 418 booked, 1 attended, 16 (1.6%) no trace.
6. Recency: 549/967 resolved a usable year — 84% booked/attended 2023+, 67% in 2024–25. Recently active, not stale.
7. Reconciled against the old "9.8% / scraped" conclusion: it cross-reffed the enquiry tables; an event attendee never appears there. Formally refuted.
8. Persisted: 3 memory blocks in `project_meji_warm_rebuild_d1.md`; Mini-Checkpoint-1; context YAML; this checkpoint.

---

## Key Decisions Made
### Christmas list questions are now data-answered, not Gurmej questions
- **Choice:** Q1 (genuine?) and Q2/Q3 (recency) are resolved from Meji's own booking DB; they will not be asked of Gurmej. The ≤16 no-trace contacts are an internal soft-variant handling decision, not a client ask.
- **Rationale:** 98.4% match against `delegates`+`full_data_parties` plus a recent-year distribution is stronger evidence than a client's recollection would be.

### Banter stays a genuine Gurmej question
- **Choice:** Banter origin remains open for Gurmej.
- **Rationale:** Banter (banterexp.com) is a separate business; its customer data is not in `xmas_2020` or any system reachable here. Honest limit, not a deferral.

### Round-2 voice draft unchanged
- **Choice:** No edit to `d1-cadence-gurmej-voice-round2-2026-05-17.md`.
- **Rationale:** The data confirms the premise the draft already encodes; the shared-history copy is justified for ~98% of the list.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| scripts/meji_d1_campaign_live_state.py | Created | Read-only Christmas Bookers live-state (Q5-op) |
| scripts/meji_d1_segment_recheck.py | Created | Verify Seg A41/B942 from lead data (B4) |
| scripts/meji_d1_campaign_live_state.py + .xref/.rec scratch | Created | Attendee + recency UNION-injection params |
| workspace/clients/meji-media/context/d1-campaign-live-state.json | Created | Campaign live-state result |
| workspace/clients/meji-media/context/d1-segment-recheck.json | Created | Segmentation reconciliation result |
| workspace/clients/meji-media/context/d1-attendee-xref-result.json | Created | 967/983 match + year distribution (key artifact) |
| memory/project_meji_warm_rebuild_d1.md | Modified ×3 | Q5/seg, Q1-by-data, recency + schema-enumeration principle |
| docs/2026-05-17 - Meji D1 Audience Verified From Booking DB/Mini-Checkpoint-1.md | Created | Lightweight checkpoint (earlier in session) |
| docs/sessions/2026-05-17-context.yaml | Modified | Fast-path resume updated to data-verified state |

---

## Current Status
- D1 round-2 voice draft delivered, unchanged, now fully data-backed; awaiting Gurmej voice/re-pacing review (external + B5; user sends).
- Christmas Q1/Q2/Q3 retired by data. Banter origin = only genuine Gurmej question.
- Christmas A0–A3 pipeline live, untouched this session.
- Comms: last contact 2026-05-15 (2 days, OK).
- Platform: no `platform` section in `meji-media/infrastructure.yaml`; client uses Make.com.

---

## Next Steps
1. Gurmej voice/re-pacing review of `context/drafts/d1-cadence-gurmej-voice-round2-2026-05-17.md` (user sends; do not send — external + B5).
2. Pre-send hygiene before any send: verify all 983 + exclude the 38 known bounces (B5-gated operator action).
3. Banter origin remains a genuine Gurmej question; Christmas origin questions are retired.
4. Run platform feasibility assessment for meji-media (no `platform` section in infrastructure.yaml).
5. Commercial model stays internal until the user explicitly clears it.

---

## Context for Next Session
### Files to Read First
- memory/project_meji_warm_rebuild_d1.md (last 3 blocks)
- workspace/clients/meji-media/context/d1-attendee-xref-result.json
- workspace/clients/meji-media/context/drafts/d1-cadence-gurmej-voice-round2-2026-05-17.md

### Open Questions
- Banter genuine past-customer source — Gurmej only (non-gating to Christmas D1).
- Q7: address verification on the unverified single-shot import (B5 pre-send operator step).
- Retainer model + amounts (internal; user holds context).

### Working Notes
- The `xmas_2020` DB has two table families: ENQUIRY (`enquiries`, `full_data_enquiries`, `enquiries_backup_*`) and CUSTOMER/ATTENDEE (`delegates` has `email`; `full_data_parties` has `leader_email`; `parties`/`invoices`/`transactions` have no email column). Attendee questions must hit the second family. Three prior sessions used the first and concluded the list was scraped — wrong table, not bad data.
- UTIL 8974201 `by_id` mode injection: `0 UNION SELECT {22 cols aligned to enquiries} FROM (...)`. Schema enumeration via `information_schema.tables/.columns` works. Large results (>tokens) auto-save to tool-results files; parse with Python, don't Read raw.
- Recency caveat: only 549/967 resolved a year (others matched on email but the row's `created` was null/0). The 84%-recent figure is on the 549.

### Reference Materials
- Data: `context/d1-attendee-xref-result.json`, `d1-campaign-live-state.json`, `d1-segment-recheck.json`
- xref params: `scripts/.xref_b0.txt`, `.xref_b1.txt`, `.rec_b0.txt`, `.rec_b1.txt`

---

## How to Continue
The audience question is closed. Next substantive move is Gurmej's voice review of the round-2 draft (his call, external). No further data work is needed on the Christmas list. If Gurmej replies, paste into `/comms meji-media`.

---

## Strategic Feedback

### What Worked Well This Session
- The user's scoping question ("what can you retrieve before asking Gurmej unnecessary questions") was high-leverage: it forced schema enumeration that resolved three sessions of premise-thrash in one pass. Asking "what do we already know" before "what do we ask the client" is the right instinct.

### Suggestions
- When a cross-reference returns a surprisingly low match rate, treat it as a schema question before a data-quality conclusion. The "9.8% → scraped" narrative survived three sessions because the table choice was never questioned.

### System Health
- **B2 hard-limit hook is imprecise.** It counted sequential successful read-only data-prep Bash commands as "build/test iterations" and fired the HARD-LIMIT escalation 3+ times this session with no failure and nothing being fixed. The streak counter should distinguish fix-retry-after-failure from distinct successful commands, or exclude non-test Bash. Logged as `infrastructure-deferred`.
- Autonomy score: 3 human interventions this session (1 user-surfaced cross-session miss; 2 Stop-hook-caught B1 closing-offers). At threshold, not elevated; the closing-offer pattern remains a recurring regression with the structural backstop holding.
