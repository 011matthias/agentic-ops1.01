# Checkpoint: Brisken Lead-Gen Q&A Cluster + Rome Pre-Event Send

**Date:** 2026-06-19
**Status:** p2 lead-gen engine advanced (AEO trust layer 3/8 clusters built, sweep runbook live); Rome pre-event send fully staged and gated only on Dirk's copy approval + the human-run merge.

---

## Summary
Resumed Brisken p2, resolved the who-drives-seat decision (human in-seat), built the three highest-leverage AEO Q&A cluster pages (MDH, Remittance, migration) plus the weekly-sweep runbook, then staged the Rome pre-event email send end to end: switched the mechanism to Dirk's Outlook (killing the Zoho DKIM blocker), built the 252-contact consent-clean send list + merge pack, drafted and logged the Dirk copy-approval email, and logged the session's hours.

---

## What Was Done This Session

### AEO Q&A cluster pages (the always-on trust layer)
1. `mdh-qa-cluster.html` (Cluster A, Market Data Hub, 8 queries) and `remittance-qa-cluster.html` (Cluster D, Remittance Advice Gate, 5 queries), committed f6f4b4e.
2. `migration-qa-cluster.html` (Cluster G, S/4HANA migration why-now + AI workforce, the broad fan-out catcher), committed c712fb7.
3. All three follow the `shadow-integration-report.html` template (theme toggle, FAQPage JSON-LD, comparison table, trust footer); the 71%/34% Shadow Integration stats folded in as attributed market research, never as a product metric; validate-html.py 0 hits.

### Engine cadence
4. `weekly-sweep-runbook.md`, made the radar's §7 weekly sweep executable (the one action that grows both the target list and the benchmark); wired a pointer into `targeting-radar.md`.
5. Resolved who-drives-seat = human in-seat (no agent-browser on Brisken's live LinkedIn); recorded in `sales-nav-targeting.md`.

### Rome pre-event send (the time-critical thread, E1 Fri 19)
6. Mechanism switched to **Dirk's Outlook (M365)**, not Zoho Campaigns. This made the `zcsend` DKIM / domain-auth work moot: a send from the real mailbox passes DMARC `p=reject` via SPF alignment (Outlook already in brisken.com SPF). The time-critical DNS action came off the board.
7. Built `rome2026-E1-send-list.csv` + `.xlsx`: 252 recipients from the 542 warm-reconnect rows (290 no-email dropped, consent-clean, 0 email-bearing opt-outs verified independently). Audience cut resolved = all 252.
8. Built `rome2026-mail-merge-pack.md`: E1/E2/E3 with the merge field placed, per-wave dates, Word mail-merge run steps, the M365 burst-pacing caution.
9. Drafted the Dirk copy-approval email (Register A); user sent it; logged verbatim to `comms-log.md`.
10. Logged the session's hours into `hours-tracker.xlsx` (2 rows, 3.00h / EUR 42.00).

---

## Key Decisions Made

### Send from Dirk's Outlook, not Zoho Campaigns
- **Choice:** Path (b), mail-merge from `dirk.neumann@brisken.com`.
- **Rationale:** Removes the DKIM/DNS lead-time blocker entirely (SPF alignment via M365 already satisfies DMARC p=reject). Fits the warm/authentic/low-volume posture. Cost: no native unsubscribe/tracking, and 252 from a personal mailbox needs pacing.

### Build the 3 highest-leverage AEO clusters, not all 8
- **Choice:** MDH (flagship), Remittance (strongest AI angle), migration (backs every campaign via the ECC-2027 why-now). Cluster C/F/B deferred.
- **Rationale:** Marginal value drops after the three load-bearing clusters; cover the spine first.

### Who-drives-seat = human in-seat
- **Choice:** A person runs the Sales Nav recipes; agent-browser is off the table for Brisken's live LinkedIn.
- **Rationale:** Account-risk on Dirk's company page (LinkedIn flags automation). Recipes rewritten to be human-runnable.

### Remittance trust footer stays company-level
- **Choice:** The Remittance page does NOT claim an SAP Store listing.
- **Rationale:** The 2026-06-17 audit found it is brisken.com only; it leans on the live ChatGPT customer proof instead (B4 accuracy).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `deliverables/mdh-qa-cluster.html` | Created | Cluster A Q&A page (committed f6f4b4e) |
| `deliverables/remittance-qa-cluster.html` | Created | Cluster D Q&A page (committed f6f4b4e) |
| `deliverables/migration-qa-cluster.html` | Created | Cluster G Q&A page (committed c712fb7) |
| `context/lead-generation/targeting/weekly-sweep-runbook.md` | Created | executable weekly sweep cadence |
| `context/lead-generation/targeting/sales-nav-targeting.md` | Modified | who-drives-seat resolved = human in-seat |
| `context/lead-generation/targeting/targeting-radar.md` | Modified | pointer to the sweep runbook |
| `context/lead-generation/outreach-assets/aeo-substrate.md` | Modified | build status: clusters A/D/G done |
| `context/lead-generation/dirk-go-live-sheet.md` | Modified | added the Q&A pages to staged-and-ready |
| `context/lead-generation/Rome-Event/rome2026-E1-send-list.csv/.xlsx` | Created | 252-contact consent-clean send list |
| `context/lead-generation/Rome-Event/rome2026-mail-merge-pack.md` | Created | E1/E2/E3 + Word merge run steps |
| `context/lead-generation/Rome-Event/conference-rome-2026-plan.md` | Modified | path-b decision, all-252, send list |
| `context/comms-log.md` | Modified | logged the sent Dirk copy-approval email |
| `workspace/hours-tracker.xlsx` | Modified | 2 lead-gen rows (+3.00h / EUR 42) |
| `.scratch/log-hours.py` | Created | ephemeral idempotent hours-writer (bg retry) |

---

## Current Status
p2 lead-gen: AEO trust layer has its 3 spine clusters live (ready-to-publish, Dirk-gated); the weekly sweep has a runbook. Rome pre-event send is fully staged: 252-list + copy + merge pack ready, deliverability confirmed (no DNS), gated only on Dirk's copy yes + the human-run merge (E1 Fri 19). Hours logged (LeadGen now 19 rows; Total recomputes to 43.25h / EUR 605.50 on next Excel open). Lead-gen orchestrator is manual (no Make/n8n platform section), so no infra reconciliation.

---

## Next Steps
1. **Rome E1 send:** on Dirk's copy approval, run the Word mail merge from his mailbox per `rome2026-mail-merge-pack.md`, E1 Fri / E2 Mon / E3 Tue, paced. (Human action.)
2. **Take `dirk-go-live-sheet.md` to Dirk:** sending identity, contact green-light, publish the research + Q&A pages, partner-cockpit access, the 2 product-shape decisions.
3. **Lead-gen autonomous build:** cluster-C (Bank Fee Portal), then F + B Q&A pages.
4. **Wave-1 lists:** the human runs the Sales Nav recipes in-seat (Colgate/Corteva A1 first).
5. **One-pager PDF:** needs a single-page layout (the doc-template render was 6 pages, removed); gated on the landing publish anyway.

---

## Context for Next Session

### Files to Read First
- `context/lead-generation/Rome-Event/conference-rome-2026-plan.md` (Rome state + send decision)
- `context/lead-generation/Rome-Event/rome2026-mail-merge-pack.md` (the staged send)
- `context/lead-generation/dirk-go-live-sheet.md` (the one Dirk conversation)
- `context/lead-generation/targeting/weekly-sweep-runbook.md` (the engine cadence)

### Open Questions
- Dirk's go on the E1/E2/E3 copy (gates the Friday send).
- Publish blended 71% or the sharper in-house-only sub-rate; TreasuryCentral/OnePilot hierarchy (both gate the Q&A + LinkedIn copy).

### Working Notes
- Deliverability for the Outlook path is solved: brisken.com SPF includes `spf.protection.outlook.com`, so a send from the real M365 mailbox passes DMARC p=reject via SPF alignment. No DNS change. (Zoho Campaigns would have needed the `zcsend` DKIM, which is why the path switch removed the blocker.)
- The 252 segment mix: 130 unspecified, 70 partner, 31 prospect, 20 sap_other, 1 customer. All-252 chosen; the `segment` column filters to 162 (drop partner+sap_other) if ever wanted.
- Hours-tracker is a known open-Excel collision zone. This session the openpyxl save failed SAFE (lock, no corruption, unlike 2026-06-18); a background retry loop landed the rows the moment Excel closed. Overview Total uses `=SUM(LeadGenLog[Hours])` (structured ref), auto-includes new rows.

### Reference Materials
- Commits: f6f4b4e (MDH+Remittance), c712fb7 (migration) on `client/brisken/lead-gen-onepilot`.
- Booking CTA (live): `bookings.brisken.com/#/tacrome2026`.

---

## How to Continue
Rome is the live clock: once Dirk approves the copy, the merge runs from his Outlook (pack has the steps). Everything else (cluster-C/F/B pages, Wave-1 lists) is autonomous Lane-1 work; the go-live sheet is the single Dirk conversation that switches the rest on.

---

## Strategic Feedback

### What Worked Well This Session
- Switching the send to Outlook collapsed the critical path: one decision removed a DNS action with hours of lead time. Re-checking DNS live (rather than asking "is DKIM set up?") and verifying the total ties to 40.25 before asserting were both autonomous-first wins.

### Suggestions
- The hours-tracker keeps costing round-trips because it is usually open in Excel during a session. A tiny `tools/hours-log.py` (the `.scratch` writer is most of it) that the agent calls, plus a habit of expecting the lock and going straight to the background-retry pattern, would remove the class. Suggested before in the register; this session it bit again (the projected-vs-actual number confusion came from the rows not landing while Excel stayed open).

### System Health
- The PDF one-pager path is a recurring soft spot: `md-to-pdf.py`'s doc template renders a one-pager as 6 pages, and it collides with an open Edge. A dedicated single-page brochure template (or reusing the landing's printable block) would make the one-pager a clean autonomous deliverable instead of a detour.
- Autonomy score: 3 human/guardrail interventions this session (2 stop-b1-gate catches on deferral phrasing, self-corrected; 1 user-flagged number-clarity confusion). The agent-deferred B1 phrasing reflex continues to recur and the hook continues to catch it every time.
