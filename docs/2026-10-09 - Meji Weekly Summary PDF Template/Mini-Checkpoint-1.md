# Mini-Checkpoint: Meji Weekly Summary PDF Template

**Date:** 2026-10-09
**Status:** Corporate October trial LIVE (134); weekly client summary template built, first PDF one spacing fix from sendable
**Type:** mini

---

## Summary
Ran Meji from 2026-10-02 to 10-09: dormant Christmas wave released (36), Gurmej's US-in-London corporate trial sourced from Apollo, cut to 134 and launched in a cleared and renamed campaign A, and a standing two-page PDF format for the weekly client summary built. The summary's page 1 trips its own overflow guard by a few mm, so it is not yet sendable.

## What Was Done
- Dormant wave `26a0d9eb` released with 36 (Sydni Berry pulled: open 09-09 pricing question filed `4-UNCLEAR`); both Christmas page figures corrected (uweb #51, #52). Status file updated (#1561).
- Apollo pull for Gurmej's ICP: 987 verified at 881 companies; London headcount counted per company (median 8; only 222 at 20+); Apollo industry label replaced keyword tags (73 strict tech/fintech at 20+, 72 more at 10-19); 12 Mimecast domains and 1 July contact removed; 132 + 2 replacement contacts = **134**.
- Campaign A `c3daf05c` (Piece 2) wiped of 589 Jun-Jul leads (snapshot kept), renamed "US-in-London Oct (A)", Gurmej's three touches, Mon-Fri, activated 10-06 16:56 UTC. Touch 1 sent 7-8 Oct, 2 bounced.
- Gurmej (10-06): go, success line = **3 genuine positive replies by 31 Oct**, Ella answered, **weekly summaries agreed at 6 h/week total**.
- Housekeeping: block list 25 -> 32; Bookers `1f40cb36` + Warm Re-engagement `00fc708d` paused.
- Weekly summary: format chosen (short, 2 pages), facts pulled live, markdown approved, Jinja template + Chrome generator built in gitignored `context/`, first PDF rendered.

## What Did NOT Work (and why)
- **Reusing campaign A by PATCHing its sequence (2 -> 3 steps):** Instantly re-armed the COMPLETED campaign (status 3 -> 1) and re-opened 533 finished leads; 3 retired June contacts got touch 3 at 16:33 UTC before the pause. Fixed by wiping A's leads first. Memory `reference_instantly_api_semantics` item 4.
- **Immediate read-back after bulk Instantly writes:** `/leads/list` lags 1-2 min both ways (deletes 6 -> 3 -> 0; inserts 37 -> 132). An `all()` check over an empty read passed vacuously once; guarded since.
- **Apollo funding-stage filters:** `organization_funding_stage` and `organization_total_funding_range` silently ignored (return the control count); `organization_latest_funding_stage_cd` returns 3 for the junk value `series_zzz` too. Not filterable via API.
- **Apollo `q_organization_keyword_tags` as an industry filter:** it is a keyword match; let through PE, hedge funds, asset managers, law firms, consumer brands. Use `organizations/enrich` industry.
- **PDF page count as the layout check:** pages clip overflow instead of adding a page, so a count of 2 hid a section cut off at the footer. Template now prints LAYOUT-OVERFLOW, generator rejects it.
- **Jinja `s.items`:** resolves to `dict.items`; use `s['items']`.
- **Shell `python -c "..."` with backticks in the text:** command substitution blanked three names in a comms-log entry (repaired from a file).
- **Saying "nothing was loaded" after the owner stopped a tool call:** the load had already run; memory `feedback_interrupted_tool_may_have_run`.

## Current Status
Christmas warm `62fc56ff`: 774, touch 1 done, touch 2 under way, 3 bounced, two live booking enquiries (Indy Sagoo, table of 10 Leicester Sat 12 Dec; Ella Richardson, Enterprise Mobility, 5 or 12 Dec, Jess on both). Dormant: 36, touch 2 under way; one already-booked customer (Mark James Hair) received a follow-up. Corporate A: 134, touch 1 done, **0 of 3** positive (Partly + Decagon "keep on file", PostHog remove), touch 2 from Mon 12 Oct. Campaign B `5d677062` paused with 20 July leads mid-sequence: never resume as is. Make 13,168 / 40,000, reset 28 Oct, auto top-up off. Summary PDF at `context/weekly-summaries/Meji-weekly-summary-2026-10-09.pdf` renders 2 pages but page 1 overflows the safety margin. Ops: no `platform` section in infrastructure.yaml. Status files: enquiry-automation.md corporate row stale since 10-02; ops-radar.md STALE (28d). 37 friction candidates undrained (mini).

## Next Steps
1. Tighten the template's base spacing (section gap, item padding, cell padding) until page 1 passes the overflow guard; rasterise both pages with pypdfium2 and look; give the owner the PDF path for approval before it is sent; then delete `2026-10-09-draft.md` (superseded by the JSON).
2. Before Mon 12 Oct 06:17: update the weekly review engine's campaign list (Sept waves live, A relaunched, Bookers / Warm Re-engagement / B paused); investigate `MejiReplySLA` (last result 0x80070420, instance already running).
3. Monday: re-check the `parties` table against remaining Christmas warm + dormant leads (UTIL 8974201 parties mode) and remove booked ones; weekly until the Christmas sequences end.
4. Block list (owner yes, B5): phil.etherington@eden-farm.co.uk, sarah.reay@dovecotestmo.com, joe@posthog.com.
5. Corporate: watch replies daily from touch 2; count positives against 3.
6. A3: RAD-29 read-only blueprint check, then the change (Gurmej approved 10-02).
7. Update status/enquiry-automation.md (corporate row) and resolve stale ops-radar.md; run a full checkpoint to drain the 37 candidates.

## Files to Read First
- `workspace/clients/meji-media/context/comms-log.md` (entries 2026-10-02 to 10-07 at the top)
- `workspace/clients/meji-media/context/weekly-summaries/2026-10-09.json`, `.../template/summary.html.j2`, `context/analysis-scripts/meji_weekly_summary_pdf.py`
- `workspace/clients/meji-media/context/pilot-routing.md` (Piece 2 note, 2026-10-06)
- memory `project_meji_weekly_review_system`, `reference_instantly_api_semantics`, `feedback_interrupted_tool_may_have_run`
