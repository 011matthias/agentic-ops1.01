# Checkpoint: Brisken Rome GA Post-Event Wave

**Date:** 2026-07-27
**Status:** GA wave sent (19), verified, sheet reconciled; SAP 15 + 4 in-thread held for Dirk

---

## Summary
Built and sent the Rome/TA Cook GA ("general-awareness") post-event wave: 19 emails from Dirk via Graph after the cohort turned out to be ecosystem (SAP staff, consultancies, payment firms), not buyers. A pre-send audit caught 21 unrelated drafts in Dirk's folder, which became a new send-by-ID safety rule.

---

## What Was Done This Session

### GA wave (the arc)
1. Identified GA = the `tier='GA'` cohort (40 rows), un-held 2026-07-17 for its own wave. Pulled the roster from the master sheet; surfaced that all 40 are flagged "general awareness, not a warm lead" and are SAP staff (15) + consultancies (11) + payment firms (10) + corporates (4), not a buyer audience.
2. Asked the two real forks (wave shape; SAP handling). Owner chose a low-touch no-ask note and "write Dirk to decide the SAP names"; staged + (user sent) that ask email.
3. Dirk (07-24): consultancy go on a market-data angle, SAP he reviews. Recut the note to a Market Data Hub version. Dirk (07-27): "use the plainer version"; owner confirmed plainer for all, SAP out.
4. Readiness dedup dropped 4 already-in-thread contacts (Eliane/Zanders, Florian+Steffen/Payments.cc, Fabio/Ferrero). Staged 19 plainer-note drafts in Dirk's Outlook (booth/event opener, same-firm wording varied, Zoho BCC).
5. Pre-send audit → **sent 19/19** by message ID, verified out of Drafts and into Sent Items. Reconciled the 19 master-sheet rows (status AA, last_outreach AC), 0-drift verified.

### System
6. Wrote `rule_brisken_graph_send_by_id.md` (owner directive) — send only by ID, deny-by-default guards, content+recipient situational-correctness check, verify behavior.

---

## Key Decisions Made

### GA wave is low-touch, plainer note, SAP excluded
- **Choice:** Plainer TreasuryCentral no-ask note to 19 non-SAP ecosystem contacts; SAP 15 held for Dirk; 4 in-thread held for a personal line.
- **Rationale:** Dirk's competitive caution ("better not over communicate" with SAP) + the cohort being partners/vendors, not buyers. The T3 buyer pitch would have been wrong here.

### Targeted sheet reconcile, not the reconcile tool
- **Choice:** Updated exactly the known-sent 19 directly rather than running `brisken-outreach-reconcile.py`.
- **Rationale:** The tool pulls sends from the aggregate `/messages` scan, which false-negatives just-sent Sent-Items outbound (documented T3 near-miss). I had verified knowledge of the 19; a targeted upgrades-only PATCH is correct and safe.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/rules/rule_brisken_graph_send_by_id.md` | create | New hard rule: Graph sends only by ID + guards |
| `context/lead-generation/rome-ga-wave.md` | create | Both GA sequences + segmentation (canonical wave doc) |
| `context/comms-log.md` | append | Dirk 07-24 + 07-27 replies, GA send, reconcile |
| `status/p2-rome.md` | edit | GA cohort wave = done; post-event + sheet rows |
| `.scratch/ga_*.py` | create | Dirk-ask draft, loader, pre-send audit, sender, verify, sheet reconcile (gitignored) |

---

## Current Status
GA wave complete: 19 sent + verified, sheet reconciled. SAP 15 and 4 in-thread contacts held for Dirk. Brisken ops status: platform plan unknown (no `platform` block change this session; lead-gen is the active p2 workstream). `rome-ga-wave.md` doc has a pending sync (it was open/locked during the session); comms-log is authoritative.

---

## Next Steps
1. **Dirk's court:** he sends nothing more on GA until he reviews the SAP 15 himself; the 4 in-thread contacts deserve a personal line from him (not the wave note).
2. Commit `rule_brisken_graph_send_by_id.md` to main via a small **system PR** (not this deckgen client branch; siblings share the tree).
3. Sync `context/lead-generation/rome-ga-wave.md` with the final decision + sent status once the file is closed (comms-log already holds it).
4. GA non-responder follow-up later; T3 touch-2 to non-responders ~2026-08-02 then stop.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/lead-generation/rome-ga-wave.md`
- `workspace/clients/brisken/status/p2-rome.md`
- `.claude/rules/rule_brisken_graph_send_by_id.md`

### Open Questions
- How does Dirk want the 15 SAP staff handled (LinkedIn-only / partner note / later)?
- Personal-line handling for the 4 in-thread contacts.

### Working Notes
- Send infra pattern (reusable): stage drafts in Dirk's Outlook via app-only Graph → pre-send audit (positive allowlist, assert exact count, refuse SAP/held) → send by ID with `--go` → verify Drafts→Sent. Scripts in `.scratch/ga_*.py`.
- Master workbook coords: site `brisken.sharepoint.com,65b8d36f-...,e9089a15-...`, path `30_Events/TA Cook/TA Cook 2026/TAC Rome2026-post-event-master-contacts_260627_DN-Edits.xlsx`, sheet `Master contacts`; `email outreach_status`=AA(26), `last_outreach`=AC(28), join `email`=I(8). App-only Sites.ReadWrite.All PATCH works (200).
- Readback lags after PATCH; trust the whole-sheet diff, not the immediate cell read.
- Stiaan Scheepers: sent to readable `stiaan.scheepers@globalpayments.com`; sheet primary is the cryptic `ss50866@` alias (reconcile maps back).

### Reference Materials
- `feedback_brisken_outreach_truth_is_mailbox` (mailbox-truth + workbook write), `rule_brisken_graph_first`, `project_brisken_rome_master_contact_sheet`.

---

## How to Continue
GA execution is done from our side; the ball is with Dirk on SAP + the 4 in-thread. If picking up: read `rome-ga-wave.md`, confirm Dirk's SAP decision, and reuse the `.scratch/ga_*.py` send pattern for any follow-up wave (send-by-ID rule now applies).

---

## Strategic Feedback

### What Worked Well This Session
- Questioning the cohort before building: surfacing that GA was SAP/partners/vendors, not buyers, changed the whole deliverable and avoided a reputationally bad blast. The pre-send audit then caught 21 unrelated drafts in Dirk's folder, a real save.

### Suggestions
- Turn the send-by-ID guard into a structural preflight hook (refuse a Graph `/send` loop lacking a count-assert + recipient-allowlist), so the new rule is enforced by code, not recall.

### System Health
- **Autonomy:** high on execution; the human turns were required owner approvals (invasive sends, client-copy choices), not corrections of my work. One B1 deferral (offered vs. staged the Dirk-ask email) was caught by `stop-b1-gate` and self-corrected same turn. No corrective user interventions.
