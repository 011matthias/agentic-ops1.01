# Mini-Checkpoint: Meji Warm Rebuild D1 Enrichment

**Date:** 2026-05-16
**Status:** D1 enrichment design fully locked; heavy data run deferred for session-pressure only (no open questions)
**Type:** mini

---

## Summary
Queried both warm campaigns via the new Instantly V2 API (read-only), corrected the warm-DB sizing (983 leads, not ~1,900), fixed the "lead-list/audience export" wording in the playbook + plan, documented the D7 report API shape, and started D1 enrichment (schema + UTIL method recovered, segment design locked at 3-segment v1).

## What Was Done
- **Analytics:** Christmas Bookers `1f40cb36-c62c-4569-95bd-692709512c9c` → `leads_count` **983** (1,923 = emails sent). Banter `c83adc69-298f-4be5-94b7-41bf60f4248e` → **4,362** (8,588 = emails sent). Both read-only.
- **D7 shape documented** in `weekly-report-template.md`: windowed `/campaigns/analytics` field map, `[]`-on-empty-window gotcha, lifetime-vs-windowed caveat, `reply_count_automatic` exclusion, no-bounce-field-in-`/daily`.
- **Wording corrected** in `seven-deliverables-playbook.md` + `christmas-warm-rebuild-plan.md`: warm DB = campaign-attached leads via API (read [A] autonomous, mutations [M]+B5). Stale "no API" premise retired.
- **Enrichment started:** join key = `email`; `full_data_enquiries` 22-col schema recovered; UTIL 8974201 `by_id`+positional-UNION method proven; `enquiry_status` ∈ {NULL,cold,new,in_contact,dead} — no booked value.
- **Decisions locked:** paginate `/leads/list` for records (not count); v1 = 3 recency segments (booked tier deferred). Written into the plan.

## Current Status
Three asks delivered. Enrichment design is complete and unblocked. The heavy run (paginate 983 → batch cross-ref via UTIL 8974201 → assign 3 segments → demote no-match to cold) was deferred only because two large UTIL dumps pushed the session to high context pressure — not for any open question.

## Next Steps
1. Fresh session + `/resume meji-media`: run the D1 enrichment data run per the locked design in the plan's "Enrichment schema" + step 2.
2. After segments: draft the 3-segment sequence copy for Gurmej's voice review (first of 2-3 rounds).

## Files to Read First
- `workspace/clients/meji-media/context/christmas-warm-rebuild-plan.md` (Enrichment schema section + step 2 = full locked spec)
- `workspace/clients/meji-media/context/weekly-report-template.md` (D7 API shape)
- memory `project_meji_warm_rebuild_d1.md`
