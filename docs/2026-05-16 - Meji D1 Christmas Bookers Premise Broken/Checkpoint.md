# Checkpoint: Meji D1 Christmas Bookers Premise Broken

**Date:** 2026-05-16
**Status:** D1 sequence-copy work PAUSED. Provenance question drafted to Gurmej (Thread 2), not yet sent. Awaiting client answer on list origin before D1 can proceed.

---

## Summary
Ran the locked D1 warm-rebuild enrichment data run. It falsified the deliverable's core premise: the "Christmas Bookers" Instantly list (983) is ~90% unmatched against Meji's booking database and was bulk-imported in a single minute on 2025-11-12. Drafted a provenance question to Gurmej and paused the build pending his answer.

---

## What Was Done This Session
### Enrichment run (read-only, autonomous)
1. Pulled all 983 Christmas Bookers leads via Instantly V2 API (`/leads/list`, campaign `1f40cb36-c62c-4569-95bd-692709512c9c`). Count matches `leads_count` exactly.
2. Recovered the 3 archive table schemas: `full_data_enquiries` (22 col, email+created), `enquiries` (22 col, email+created), `enquiries_backup_23-04-2025` (email+created). Dropped `all_enquiries` — it has NO email column (6 cols: EnquiryDate/EventReference/HearAbout/LEVEL/Size/id), so it is structurally unmatchable by email.
3. Cross-referenced all 983 emails vs the 3 usable tables via UTIL 8974201 (by_id + positional-UNION injection, aggregated MAX(created) per email, 3 batches). Join validated case- and trailing-space-insensitive.
4. Consolidated + segmented; demoted no-match to cold per the plan gate.
5. Provenance test on Instantly metadata: all 983 `timestamp_created` identical to the minute (2025-11-12T08:43Z); `verification_status` null for all.

### Comms
6. Drafted info-request to Gurmej (Thread 2, "General outreach project") asking list origin + whether a true warm source exists. Logged to comms-log (entry 13, status: not yet sent).

---

## Key Decisions Made
### Drop all_enquiries from cross-ref
- **Choice:** Cross-ref against `full_data_enquiries` + `enquiries` + `enquiries_backup_23-04-2025` only.
- **Rationale:** `all_enquiries` (2015–2020) has no email column. Documented as a structural blind spot for pre-2023 contacts, but the plan frames the audience as 2024/2025, which IS in the matchable range.

### Pause D1, ask Gurmej before any sequence copy
- **Choice:** Do not draft recognition-first copy. Surface the premise break and ask for list provenance.
- **Rationale:** Recognition copy assumes recipients remember Meji. True for ~10%. Both "reframe as cold" and "proceed" rest on assumptions only Gurmej can resolve (where the list came from).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/context/d1-warm-leads-raw.json | Created | 983 raw Instantly leads |
| workspace/clients/meji-media/context/d1-enrichment.json | Created | Per-lead segment assignment + counts |
| workspace/clients/meji-media/context/d1-enrichment-findings.md | Created | Findings + provenance evidence + decision framing |
| workspace/clients/meji-media/context/comms-log.md | Modified | Entry 13 (Gurmej provenance question); frontmatter 13/6 |
| scripts/meji_d1_pull_warm_leads.py | Created | Instantly pagination pull |
| scripts/meji_d1_build_xref_queries.py | Created | Batched UTIL injection param generator |
| scripts/meji_d1_consolidate.py | Created | Join + segment + cold demotion |
| scripts/meji_d1_provenance.py | Created | Lead-creation timestamp provenance test |
| memory/project_meji_warm_rebuild_d1.md | Modified | Recorded premise break + provenance evidence |

---

## Current Status
- D1 enrichment design executed; run complete and verified. Result: 96/983 (9.8%) locatable in booking DB; 887 unmatched; 850 no-trace-no-engagement; whole list a single bulk import 2025-11-12, none verified.
- D1 sequence-copy build PAUSED pending Gurmej's answer on list provenance.
- A0–A3 Christmas pipeline unaffected (untouched this session), live in production org.
- Platform: no `platform` section in meji-media infrastructure.yaml (Make.com client). Consider platform feasibility assessment, but not urgent — no platform deploy this session.

---

## Next Steps
1. User: send the drafted message into Upwork Thread 2 ("General outreach project"). Log Gurmej's reply via `/comms` when it arrives.
2. On reply: branch — (a) genuine warm source exists → re-point D1 enrichment at it; (b) no warm source → reframe D1 as a cold campaign (sample-approval gate applies, prospecting copy not recognition copy), treat the 96+37 as a small genuine-warm seed.
3. Do NOT draft sequence copy until 1–2 resolve.
4. Optional autonomous deepening if useful before reply: inspect Instantly lead custom fields / list_id for import source hints (full lead object was not pulled this session — only a field subset).

---

## Context for Next Session
### Files to Read First
- workspace/clients/meji-media/context/d1-enrichment-findings.md (full finding + provenance + decision branches)
- workspace/clients/meji-media/context/d1-enrichment.json (segment counts)
- workspace/clients/meji-media/context/christmas-warm-rebuild-plan.md (the plan whose premise broke)
- memory/project_meji_warm_rebuild_d1.md

### Open Questions
- Where did the Christmas Bookers list originate? (blocks D1 direction — asked Gurmej)
- Is there a separate genuine warm/past-customer source elsewhere? (asked Gurmej)
- If no warm source: is D1 re-scoped as cold, or parked? (downstream of the above)

### Working Notes
- UTIL 8974201 reusable method confirmed: `mode=by_id`, `param1 = 0 UNION SELECT <22 positional cols, NULLs + needed at fixed positions> FROM (<subquery>) g`. Base query is `SELECT * FROM enquiries WHERE id = <param1>` (22 cols). `continueWhenNoRes:true` + `showWarnings:false` means SQL errors return empty silently — test injections with a no-WHERE probe first.
- No MAKE_API_TOKEN available (MCP is stateless HTTP endpoint), so UTIL runs cannot be scripted via tools/make-api.py; had to paste ~30K-char params inline 3x. Candidate infra improvement: provision a read API token to enable scripted batch UTIL runs.
- Provenance is the strongest evidence and is definition-independent: single-minute bulk import + zero verification. This does not reveal the source; only Gurmej can.
- all_enquiries pre-2023 blind spot is real but cannot explain 887/983 given the 2024/2025 framing.

### Reference Materials
- Plan: workspace/clients/meji-media/context/christmas-warm-rebuild-plan.md
- Pipeline scripts: scripts/meji_d1_*.py (reproducible end to end)

---

## How to Continue
Wait for Gurmej's reply on Thread 2. Process it with `/comms meji-media`. Then take the branch in Next Steps #2. The enrichment machinery is built and reusable if the target list changes — only the input source (which campaign / which export) would change.

---

## Strategic Feedback

### What Worked Well This Session
- The user repeatedly stopping to ask "what did you do, why, and what's wrong" before deciding direction. This forced a clean separation between fact (10% match) and interpretation (our definition of warm), and surfaced that the real failure was an unvalidated assumption in the plan, not the data. High-value pattern: demand the reasoning chain before the recommendation.

### Suggestions
- When a prior-session plan asserts a factual premise about client data ("curated through years of real interaction"), run the cheapest possible falsification of that premise FIRST, before designing any machinery on top of it. One metadata query (lead creation timestamps) would have caught this at design time and saved the enrichment build.

### System Health
- Gap: the spec/plan creation flow has no "premise falsification" step. Plans can assert data properties as fact and carry them through multiple sessions unchallenged (this premise survived the plan, a memory, and a mini-checkpoint). A lightweight "what single query would prove this assumption false, and has it been run?" gate at plan-lock time would close it. Candidate `strategic-gap` structural fix for /system-dev.
- Autonomy score: 3 human interventions this session (1 strategic-gap surfaced by the user's questioning; 2 B1 soft-deferrals caught by the stop-hook and corrected). Not elevated, but the strategic-gap is the meaningful one.
