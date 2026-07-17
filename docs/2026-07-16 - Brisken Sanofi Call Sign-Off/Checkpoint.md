# Checkpoint: Brisken Sanofi Call Sign-Off

**Date:** 2026-07-16
**Status:** Closed — deck corrected + deployed live; one gated board-write parked

---

## Summary
Triaged the Brisken MARKETING Planner board (read via the Graph app), then closed the Sanofi call sign-off: confirmed no live TreasuryCentral demo exists, got Dirk's decision by email to soften slide 10, rebuilt + validated the Sanofi deck, and deployed the softened version live to SharePoint (verified by re-download).

---

## What Was Done This Session

### Planner triage (Graph app, read-only)
1. Read MARKETING PLAN (292 tasks) via app-only Graph token; surfaced the Lead Generation bucket (25 open) ranked by hard dates and leverage.
2. Named the four this-week items (Sanofi sign-off due 07-16, Ashok/Accenture due 07-16, 17-partner outreach overdue, Shell brief for 27-Jul) plus the p2 go-live conversation that unblocks four tasks.

### Sanofi demo assessment
3. Established: a Sanofi-tailored TreasuryCentral **deck** exists, but no live demo runs on Sanofi's SAP data. Slide 10 promised "we will show TreasuryCentral live on your SAP data" — a commitment nothing could back.
4. Staged the deck build source to default to a neutral close, with the live-demo line as an explicit `closeLead` opt-in.

### Comms with Dirk
5. Drafted + comms-critic-cleared + SENT (Graph Mail.Send, 202, Sent-Items verified) the slide-10 question to Dirk.
6. Dirk replied: "Yes, do not promise that - right now I have no demo at all...." DECISION 2 settled.

### Deck correction + live deploy
7. Rebuilt the Sanofi deck (neutral close), validated (`validate-demo-material.py` PASS; slide-10 text confirmed in pptx+pdf).
8. Updated the repo deliverable copy.
9. Overwrote the live SharePoint deck in `Client Collateral WIP` (versioned + local backup), verified by re-download.
10. Per owner direction ("throw it in 2026_PPTX"), also uploaded the corrected pptx+pdf to the `2026_PPTX` root folder; verified live.

---

## Key Decisions Made

### Slide 10: soften, do not promise a live demo
- **Choice:** Remove the "live on your SAP data" promise; neutral close is now the deck default.
- **Rationale:** Dirk confirmed there is no demo at all. Said on the call, the old line over-promised a live run on Sanofi's data.

### Where the corrected deck lives
- **Choice:** Deployed to both `2026_PPTX/Client Collateral WIP` (existing home, overwritten) and `2026_PPTX` root (owner's explicit ask); kept OUT of the Treasury Assessment folder and info.brisken.com/free-assessment.
- **Rationale:** Owner directive "throw it in 2026_PPTX thats it"; the two excluded locations are the assessment product, not this TreasuryCentral demo.

### Send + SharePoint writes gated on explicit go
- **Choice:** Paused for owner yes before the email send and before each SharePoint write.
- **Rationale:** rule_brisken_graph_first + feedback_no_invasive_action_without_ask — live-tenant sends and SharePoint writes are invasive.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.scratch/deckgen/build-treasurycentral.js` | Modified (gitignored) | Slide-10 default now neutral; `closeLead` opt-in for the live-demo variant |
| `workspace/clients/brisken/deliverables/lead-generation/rome-2026/call-collateral/brisken-treasurycentral-sanofi.pptx` | Modified (tracked) | Rebuilt with softened close |
| `.../brisken-treasurycentral-sanofi.pdf` | Modified (tracked) | Rebuilt PDF (send-ready) |
| `workspace/clients/brisken/context/comms-log.md` | Modified (gitignored) | Logged outbound email, Dirk's reply, deploy resolution; `last_contact` → 2026-07-16 |
| SharePoint `2026_PPTX/Client Collateral WIP/Brisken - TreasuryCentral - Sanofi 2026.{pptx,pdf}` | Overwritten (external) | Softened deck, versioned + backed up |
| SharePoint `2026_PPTX/Brisken - TreasuryCentral - Sanofi 2026.{pptx,pdf}` | Created (external) | Owner-requested home for the deck |

---

## Current Status
Sanofi is squared for Friday's 16:00 call with Ian Haegemans. The deck Dirk opens closes on the softened line, verified live on SharePoint in both target folders. The only remaining Sanofi item is a Planner board-write (tick the slide-10 checklist), gated on an explicit go. Repo deck change sits uncommitted in the working tree on the unrelated `client/brisken/lead-desk-cockpit` branch.

Platform (expense-reconciliation): custom SaaS build, no ops tier / workflow-engine op count — no ops status line applies.

---

## Next Steps
1. **On owner go:** tick the Planner "Sign off before Sanofi call" slide-10 checklist item (task `VeH5a5bwf0Ky5jns-nt8bGUAMA-a`) — a write to Brisken's shared board.
2. **Shell prep brief (27 July call):** build the internal brief on where Brisken fits Shell's SAP treasury landscape (IHB, Bank Hub, TRM) — Planner task `yPwpN8uYPEeHgMw5T3uwm2UACPnW`, 0%, fully autonomous, nothing blocking. Also add William Askew's Jul 1/2/7 replies to the master sheet.
3. **Ashok/Accenture MDH referral (due 07-16):** confirm the 40–45 central-bank scope + customer decision status (needs Dirk/Ashok input).
4. **Decide** whether the repo deck change should be committed on its own branch vs left in the working tree.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/comms-log.md` (tail — Sanofi thread + deploy resolution)
- `.scratch/deckgen/build-treasurycentral.js` (slide-10 `closeLead` logic; live-variant swap for future calls)
- `workspace/clients/brisken/deliverables/lead-generation/rome-2026/call-collateral/README.md` (per-prospect deck tailoring)

### Open Questions
- Planner slide-10 checkbox: tick now or leave until after the call? (gated board write)
- Zalando deck carries the same "live on your SAP data" close (still the pre-softening wording on SharePoint); soften it too before Dirk books that call? The build source already defaults neutral, so a rebuild would fix it.

### Working Notes
- **SharePoint folder reality:** `2026_PPTX/Client Collateral` is EMPTY; the real collateral set (TreasuryCentral generic/Sanofi/Zalando + 4 use cases) lives in `2026_PPTX/Client Collateral WIP`. Dirk's 07-09 email link (and the one I reused in my 07-16 email) points to the empty folder. Owner chose to also drop the deck in `2026_PPTX` root rather than fix the WIP-vs-non-WIP split.
- **Graph app-only path is solid:** Planner read, Mail.Send, and (via CDP against the user's Edge) SharePoint read/write all worked this session. SharePoint writes still need the user's Edge on :9222 (no app-only Sites.Selected grant for MARKETING).
- **Deck toolchain:** `node .scratch/deckgen/build-treasurycentral.js sanofi` → `uv run .scratch/deckgen/pdf-export.py brisken-treasurycentral-sanofi` (PowerPoint COM) → validate → copy to deliverables → CDP upload.
- Pre-overwrite SharePoint backups: `.scratch/deckgen/sp-backup-2026-07-16/`.

### Reference Materials
- Planner MARKETING PLAN id `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`, Lead Generation bucket `gyfptEwAwUiJLXfd6aMrYWUABZRr`
- Sanofi Planner task `VeH5a5bwf0Ky5jns-nt8bGUAMA-a` (due 07-16, call Fri 07-17 16:00, Ian Haegemans)

---

## How to Continue
Sanofi deck is done and live. Next natural pickup is the **Shell prep brief** (autonomous, dated 27 July) or, on an owner go, ticking the Sanofi slide-10 Planner item. If Dirk books the Zalando call, soften that deck's slide 10 the same way (rebuild — source already defaults neutral).

---

## Strategic Feedback

### What Worked Well This Session
- Tight directive loop: short owner replies ("send it", "go ahead", "throw it in 2026_PPTX") kept the invasive-action gates fast without over-explaining.
- Behavior verification held throughout: every send and SharePoint write was confirmed by reading the live state back (Sent-Items readback, re-download + slide-10 text check), not by trusting a 202/200.

### Suggestions
- The empty `Client Collateral` vs `Client Collateral WIP` split is a live confusion source — Dirk's own email links point at the empty folder. Worth a one-time cleanup (promote WIP → final, or delete the empty folder) so links stop misfiring.

### System Health
- Autonomy score: 2 human interventions this session (one B1 closing-offer reflex caught by the stop-b1-gate; one unverified SharePoint link in the outbound email that caused a fix-it detour). Not elevated.
- The stop-b1-gate hook fired 3× — twice correctly flagging offer-phrasing on *legitimate* invasive-action pauses (SharePoint write, second Dirk email), once on a true deferral. The hook holds; the generation reflex to offer-instead-of-act remains the most-logged class in the register.
