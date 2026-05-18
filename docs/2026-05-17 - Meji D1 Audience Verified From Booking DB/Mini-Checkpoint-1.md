# Mini-Checkpoint: Meji D1 Audience Verified From Booking DB

**Date:** 2026-05-17
**Status:** Q1 + Q2/Q3 RESOLVED BY DATA. The 983 Christmas Bookers are confirmed genuine, recent past customers. Round-2 voice draft unchanged and now data-backed. Only Banter origin remains a Gurmej question.
**Type:** mini

---

## Summary
User asked, before sending Gurmej unnecessary questions, what the database can actually tell us about the Banter and Christmas lists. Root cause of three sessions of premise-thrash found and fixed: every prior cross-ref hit only the ENQUIRY tables. Enumerated the `xmas_2020` schema (UTIL 8974201 + information_schema) and found the untouched CUSTOMER/ATTENDEE tables. Cross-referenced all 983 against them.

## What Was Done (all read-only, B5-safe)
- **Schema enumeration** — full table list + column types via `information_schema` over UTIL 8974201. Found `delegates` (31,776, has `email`), `full_data_parties` (2,380, has `leader_email`) — the real attendee/booking tables, never checked before.
- **Christmas attendee cross-ref** (`scripts/.xref_b0/.xref_b1.txt`, 2 batches): **967/983 (98.4%) are genuine past customers** — 548 both booked a party AND attended, 418 booked-party-only, 1 attended-only, 16 (1.6%) no trace. The 2026-05-16 "9.8% → scraped list" conclusion was a wrong-table artifact, formally REFUTED.
- **Recency** (`scripts/.rec_b0/.rec_b1.txt`): 549/967 resolved a year. 2025=177, 2024=190, 2023=93, 2022=71, 2021=18 → **84% booked/attended 2023+, 67% in 2024–25.** Recently active, not stale.
- **Q5-operational** (earlier this session): Christmas Bookers campaign `status=1` but dormant since ~2026-02-05, 982/983 already ran a 2-step sequence; no concurrent-send collision risk; segmentation 41/942 verified.
- Memory `project_meji_warm_rebuild_d1.md` updated with all three resolutions + schema-enumeration transferable principle.

## Current Status
- D1 round-2 voice draft (`context/drafts/d1-cadence-gurmej-voice-round2-2026-05-17.md`) unchanged — now fully data-backed; shared-history copy justified for ~98%.
- Gurmej-question status: **Q1 (real?) answered by data. Q2/Q3 (recency) answered by data. Banter origin = only genuine Gurmej question.**
- ≤16 no-trace Christmas contacts (1.6%) = internal soft-variant handling, not a client ask.
- Christmas A0–A3 pipeline untouched, live.
- Data: `context/d1-attendee-xref-result.json` (matches + year distribution), `context/d1-campaign-live-state.json`, `context/d1-segment-recheck.json`.

## Next Steps
1. Gurmej voice/re-pacing review of round-2 draft (user; do not send — external + B5).
2. Banter origin: still a real Gurmej question (no reachable data source). Christmas origin questions are now retired.
3. Pre-send hygiene before any send: verify all 983 + exclude 38 known bounces (B5-gated operator action).

## Friction
- `missed-tool` (cross-session): 3 sessions cross-reffed the enquiry tables and built a "broken premise" narrative; schema never enumerated until the user's scoping question forced it. Transferable principle now in memory: surprising low match → enumerate schema, question the table choice, before concluding the data is bad.
- B2 hard-limit hook misfired repeatedly on sequential successful read-only data-prep steps (no failure mode, no fixing). Noted, not escalated — not an iteration loop.

## Files to Read First
- memory/project_meji_warm_rebuild_d1.md (last 3 blocks: Q5/seg, Q1-by-data, recency)
- workspace/clients/meji-media/context/d1-attendee-xref-result.json
- workspace/clients/meji-media/context/drafts/d1-cadence-gurmej-voice-round2-2026-05-17.md
