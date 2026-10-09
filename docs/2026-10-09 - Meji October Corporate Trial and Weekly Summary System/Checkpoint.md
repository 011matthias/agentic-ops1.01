# Checkpoint: Meji October Corporate Trial and Weekly Summary System

**Date:** 2026-10-09
**Status:** Corporate October trial live (134, 0 of 3 positive replies, verdict 31 Oct); Christmas lists sending with two live bookings; weekly client summary PDF template built but not yet sendable

---

## Summary
Finished the dormant Christmas release, built and launched Gurmej's US-in-London corporate trial from an Apollo pull (987 sourced, cut to 134 on London headcount + industry), survived and recovered from a campaign-reuse incident, and built the standing two-page weekly client summary format. One formatting fix stands between the first summary PDF and sending it.

---

## What Was Done This Session
### Christmas lists
1. Dormant wave (`26a0d9eb`) released at 36 (Sydni Berry pulled: open 9 Sept pricing question our classifier had filed as `4-UNCLEAR`); both Christmas page figures corrected and verified live (uweb PR #51, #52; `com_review` page).
2. Housekeeping: block list 25 → 32 (7 explicit stop/left-company requests); two finished Christmas campaigns (`1f40cb36`, `00fc708d`) paused.

### Corporate October trial
3. Apollo pull for Gurmej's US-in-London ICP: 987 verified contacts at 881 companies, free-search sized first. Discovered his filters don't implement his own thesis: London headcount (counted per company; median 8) and Apollo's real industry label (vs. the keyword-tag filter that let through PE/hedge funds/law firms) cut 987 → 73 strict matches, then +72 at 10-19 staff = **134** after Mimecast and overlap removal.
4. Campaign A (`c3daf05c`, Piece 2) wiped of 589 June-July leads (snapshot kept), renamed "US-in-London Oct (A)", loaded with the 134, Gurmej's own 3-touch copy, Mon-Fri only, activated 2026-10-06 16:56 UTC.
5. Gurmej (10-06): go confirmed; success line = **3 genuine positive replies by 31 Oct**; weekly summaries agreed, billed inside campaign management at 6 h/week total.
6. Touch 1 sent 7-8 Oct: 2 bounced, 3 human replies, 0 positive so far.

### Weekly client summary (new deliverable)
7. Format chosen with the owner: short, 2 pages (results / maintenance). Facts pulled live (B4), markdown draft approved, then a reusable Jinja template + Chrome-based PDF generator built in the client's gitignored `context/` tree. First PDF renders at the right page count but trips its own overflow guard on page 1 (content sits a few mm into the reserved footer margin) — not yet sent.

### Housekeeping this checkpoint
8. `status/enquiry-automation.md`: corporate row split into the live October-trial row and a paused-B row with an explicit "never resume as-is" warning (same cause as item 10 below).
9. `status/ops-radar.md`: 28-day stale flag resolved with a pointer note (the September narrative is superseded; current state lives in the status file + comms-log); date bumped.

---

## Key Decisions Made
### October trial audience: strict match over raw pull
- **Choice:** Run the 134 that actually match Gurmej's stated thesis (US HQ + real London team + software/fintech), not the 987 his filters nominally returned.
- **Rationale:** 75% of his own filtered list had under-20 London staff and included PE firms, hedge funds, and law firms his brief explicitly excluded. Apollo's funding-stage and "last funded" filters are unusable (proven: a nonsense value returns the same count as a real one), so this was the only honest proxy left.

### Campaign reuse: wipe before rebuild, never PATCH in place
- **Choice:** Clear campaign A's old leads entirely before loading the new audience, rather than editing the sequence in place.
- **Rationale:** Forced by the incident below — PATCHing a completed campaign's sequence silently re-arms it.

### Weekly summary: internal tooling never appears in the client deliverable
- **Choice:** The stuck `MejiReplySLA` task, the review engine's stale campaign list, and this session's own incidents stay internal; the summary only reports on Gurmej's account.
- **Rationale:** Standard separation between what we fix and what the client needs to see.

---

## What Did NOT Work (and why)
- **Reusing campaign A by PATCHing its sequence from 2 steps to 3:** Instantly re-armed the COMPLETED campaign (status 3 → 1) and re-opened all 533 finished leads inside it; 3 retired June contacts received touch 3 at 16:33 UTC before the pause landed, minutes later. My post-PATCH check verified only the fields I'd changed (sequence, schedule, gap), not the side effects (campaign status, lead statuses). Fixed by wiping the campaign's leads before any rebuild. Saved to memory (`reference_instantly_api_semantics` item 4): never reuse a campaign holding a previous run's leads.
- **Reading `/leads/list` immediately after a bulk Instantly write:** the list lags the write by 1-2 minutes in both directions (a delete read back as 6 → 3 → 0 over successive polls; an insert read back as 37 → 91 → 114 → 132). An `all(...)` check run against an empty intermediate read passed vacuously once. Guarded with a poll-and-wait loop since.
- **Declaring "nothing was loaded" after the owner interrupted a tool call mid-run:** the load had already completed before the interruption landed; I reported from the harness's rejection message instead of reading the target state back. Caught on the next readiness check (the leads were already present). New memory: `feedback_interrupted_tool_may_have_run`.
- **Apollo `organization_funding_stage` / `organization_total_funding_range` as funding filters:** both silently ignored — return the exact unfiltered control count. `organization_latest_funding_stage_cd` looked honoured (count dropped) but a differential with the deliberate junk value `series_zzz` returned the same dropped count, proving it isn't matching on value either. None of these are usable; confirmed by a three-way differential before reporting it as a limitation rather than a result.
- **Apollo `q_organization_keyword_tags` as an industry filter:** it's a keyword match against anything on the company's page, not a classifier. Let through private equity, hedge funds, asset managers, law firms, and consumer brands under "financial services". Switched to `organizations/enrich`'s real industry field.
- **PDF page count alone as the layout check:** the template's fixed-height pages clip overflowing content instead of adding a page, so a correct page count (2) hid a section running off the bottom of page 1. The generator now also scans for a `LAYOUT-OVERFLOW` marker the template prints when a page's content exceeds its box.
- **Jinja `s.items` in the summary template:** resolves to the dict's built-in `.items()` method before the `"items"` key, which isn't iterable the way the template expected. Needed bracket access (`s["items"]`) everywhere that key is read.
- **Shell `python -c "..."` with backtick-quoted names in multi-line log text:** command substitution silently blanked three fenced names in one comms-log entry. Repaired by writing the edit through a file instead of inline shell.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/context/comms-log.md` | appended (multiple entries) | Canonical record of the dormant release, the Apollo build, the campaign-A incident and relaunch, housekeeping, weekly-summary agreement |
| `workspace/clients/meji-media/context/p2/uslondon-2026-10-04-october-list-145.csv`, `...-london-headcount.json`, `...-org-industry.json`, `campaignA-leads-before-wipe-2026-10-06.json` | created | Apollo pipeline outputs and the pre-wipe snapshot of campaign A's old leads |
| `workspace/clients/meji-media/context/weekly-summaries/2026-10-09.json`, `template/summary.html.j2` | created | Weekly summary data + the standing two-page template |
| `workspace/clients/meji-media/context/analysis-scripts/meji_weekly_summary_pdf.py`, `meji_uslondon_*.py` | created | PDF generator (with overflow/em-dash/page-count guards); Apollo sourcing + enrichment scripts |
| `workspace/clients/meji-media/status/enquiry-automation.md` | edited | Corporate row split into live-A / paused-B with the reuse warning; `updated:` bumped |
| `workspace/clients/meji-media/status/ops-radar.md` | edited | Stale-flag resolved with a pointer note; `updated:` bumped |
| `C:\Users\neuma_p1qrsic\.claude\projects\...\memory\reference_instantly_api_semantics.md` | edited | Items 4-6: campaign re-arm on PATCH, list-read lag, DELETE content-type quirk |
| `C:\Users\neuma_p1qrsic\.claude\projects\...\memory\feedback_interrupted_tool_may_have_run.md` | created | Read state back after an interrupted mutating call, don't report from the harness message |
| uweb PR #51, #52 (merged) | shipped | Corrected Christmas page figures, verified live |
| ops PR #1561, #1615 (merged) | shipped | Status-file update; this checkpoint's own ledger |

---

## Current Status
**Christmas warm (`62fc56ff`):** 774 leads, touch 1 done, touch 2 under way, 3 bounced total. Two live booking enquiries: Indy Sagoo (table of 10, Leicester, Sat 12 Dec, standard price, wants a call) and Ella Richardson/Enterprise Mobility (5 or 12 Dec, Jess has confirmed both dates). One already-booked customer (Mark James Hair) received a follow-up it shouldn't have — needs a `parties`-table re-check.

**Christmas dormant (`26a0d9eb`):** 36 leads, touch 2 under way, 1 bounced.

**Corporate (`c3daf05c`, now "US-in-London Oct (A)"):** 134 leads, touch 1 sent (7-8 Oct), 2 bounced, 3 human replies (0 positive). Touch 2 from Mon 12 Oct, touch 3 ~22 Oct, verdict 31 Oct against 3 positive replies. Campaign B (`5d677062`) stays paused with 20 July leads genuinely mid-sequence — **never edit its sequence while those leads are live**, same failure mode as the 10-06 incident, just on leads that are supposed to still be active.

**Weekly summary:** first PDF built, 2 pages, zero em-dashes, but page 1 trips the new overflow guard. Not sent to the owner or Gurmej yet.

**Make:** 13,168 / 40,000 operations, resets 28 Oct, auto top-up still off.

**Infrastructure drift found this checkpoint, unresolved:** `infrastructure.yaml`'s `instances:` block (org 6475885, zone eu1.make.com, scenario ids 4596203/4595921/4596220/4604238) does not match the live, MCP-connected org (5473701, eu2.make.com, scenario ids 8841775/8804011/8804012/8804014/8974201) that every session this week has actually operated on. Confirmed live via `scenarios_list` this checkpoint. Not touched — too large and risky to rewrite under this session's pressure; flagged as the top next-session item since it's the canonical reference the "Start building gate" and "Modify scenario gate" rules both depend on.

**Ops status:** no `platform:` section in `infrastructure.yaml` for Make — status line unavailable via the normal checkpoint check; folds into the drift item above.

**Project status:** `enquiry-automation.md` now live/current. `ops-radar.md` de-staled with a pointer, candidate ledger still needs an actual prune pass (not done this session).

---

## Next Steps
1. **Infrastructure.yaml drift (new, highest-leverage):** reconcile the `instances:` block against the live org 5473701/eu2.make.com scenario set from this checkpoint's `scenarios_list` pull, in its own focused session — not folded into other work.
2. Tighten the weekly-summary template's spacing until page 1 clears the overflow guard; rasterise both pages and look before handing the PDF to the owner for approval; then send to Gurmej.
3. Before Mon 12 Oct 06:17 (the weekly review cron): update the review engine's campaign list to match current reality (Sept waves live, A relaunched, Bookers/Warm Re-engagement/B paused); investigate `MejiReplySLA`'s stuck run (last result `0x80070420`, "instance already running").
4. Monday, then weekly until the Christmas sequences finish: re-check the `parties` table against remaining warm/dormant leads and remove anyone newly booked (the Mark James Hair miss).
5. Owner yes needed: add 3 more stop requests to the block list (Eden Farm, Dovecote, PostHog).
6. Watch corporate replies daily from touch 2 (12 Oct); track against the 3-positive bar.
7. A3 operations fix: Gurmej approved 2 Oct, but the RAD-29 read-only blueprint verification (never run) is the actual unblocker before touching the live scenario.
8. Decide campaign B (`5d677062`): retire, or rebuild fresh the way A was — never patch it in place while its 20 leads are mid-sequence.
9. Prune the `opportunity-radar.md` candidate ledger (overdue, noted but not actioned this session).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/meji-media/context/comms-log.md` (top entries, 2026-10-02 through 10-09)
- `workspace/clients/meji-media/status/enquiry-automation.md`
- `workspace/clients/meji-media/context/weekly-summaries/2026-10-09.json` + `template/summary.html.j2` + `context/analysis-scripts/meji_weekly_summary_pdf.py`
- `workspace/clients/meji-media/infrastructure.yaml` (for the drift fix — cross-reference against a fresh `scenarios_list` call, don't trust the file as-is)

### Open Questions
- Does the owner want their own name on the weekly summary instead of "UnpauseAI"?
- Should auto top-up in Make be turned on now, ahead of the 28 Oct reset?
- Campaign B: retire or rebuild?
- Was the `infrastructure.yaml` org drift a deliberate historical artifact (an old/retired Make workspace) or an update that was simply missed for months? Worth asking the owner if the history isn't recoverable from git blame.

### Working Notes
Apollo API limitation findings (funding filters unusable, keyword tags ≠ industry) are now proven and documented in this session's comms-log and the Apollo scripts' own docstrings — don't re-derive them. The campaign-reuse failure mode (PATCH re-arms a completed campaign) is now in `reference_instantly_api_semantics`; treat "never reuse a campaign holding old leads" as a hard rule for any future Instantly campaign edit, not just this one.

### Reference Materials
- `workspace/clients/meji-media/context/pilot-routing.md` (Piece 2 note, 2026-10-06 entry)
- Memory: `reference_instantly_api_semantics`, `feedback_interrupted_tool_may_have_run`, `project_meji_weekly_review_system`, `reference_cold_email_gateway_bounces`

---

## How to Continue
`/resume meji-media` picks this up from the context YAML. Start with the infrastructure.yaml drift (next step 1) if a focused block of time is available, since every other Meji action this week implicitly depended on trusting the wrong file and got lucky by going through MCP/live API calls instead. Otherwise, finish the weekly-summary spacing fix (next step 2) — it's the smallest remaining task and unblocks the first client-facing send of the new format.

---

## Strategic Feedback

### What Worked Well This Session
- The B5 readiness-audit pattern (enumerate every precondition, print pass/fail, refuse on any red) caught the campaign-A incident's blast radius within minutes rather than after a full send cycle, and the same pattern cleanly recovered the relaunch (20/20, then 11/11 on the second pass).
- Differential-probing (a known value vs. a deliberate junk value) killed two false positives this session — the Apollo funding filter looking like it worked, and an earlier Instantly filter claim — before either reached the client.

### Suggestions
- `infrastructure.yaml` for Make clients needs an automated drift check (a cheap `scenarios_list` diff against the tracked org/scenario ids) run periodically, not just at ad-hoc discovery like this session's. The file silently diverged from live reality for what looks like months.

### System Health
- Autonomy: roughly a dozen explicit owner decision points this session (AskUserQuestion answers plus corrections), all on genuinely invasive live-account actions (campaign builds, loads, activations, block-list writes) under `rule_instantly_invasive` — elevated in count but each one was a real B5 gate doing its job on a high-stakes live client account, not agent indecision on a reversible step.
- Gates: B1 fired 3 times this session (closing-text deferral patterns), all caught and rewritten before the turn ended. B5 (Instantly invasive-action) fired on every mutating Instantly call across the session — working as designed. Two real friction events this session are promotable to the register rather than discarded as "gate working correctly": the campaign-reuse incident (verification checked the edit, not its side effects) and the interrupted-tool-call report (declared state from the harness message instead of reading it back). Both now have structural fixes (a memory each; the campaign one additionally changes future practice to "always wipe before reuse").
