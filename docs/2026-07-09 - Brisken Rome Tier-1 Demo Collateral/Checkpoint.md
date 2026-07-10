# Checkpoint: Brisken Rome Tier-1 Demo Collateral

**Date:** 2026-07-09
**Status:** Complete — 2 decks built, uploaded to SharePoint, link emailed to Dirk (verified sent)

---

## Summary
Handled the first two Tier-1 Rome booth-follow-up replies (Sanofi / Ian Haegemans, Zalando / Lokesh Doggala): created 2 assigned Planner tasks, built 2 tailored TreasuryCentral demo decks in the dark-cockpit system, uploaded them to a new SharePoint "Client Collateral" folder, and emailed Dirk the link.

---

## What Was Done This Session
### Planner
1. Read Dirk's inbox (classic Outlook COM); found the Sanofi + Zalando replies and Dirk's 3 forwards carrying the task instructions ("prepare the collateral for this").
2. Created 2 tasks in MARKETING PLAN / Lead Generation, auto-assigned to Matthias, per `TASK-NAMING-STANDARD.md` §4 (standalone grammar). Verified via Graph (description + 4-item checklists persisted).

### Demo collateral
3. Built 2 tailored TreasuryCentral demo decks (10 slides each) via new `.scratch/deckgen/build-treasurycentral.js` (reuses `build-mdh.js` primitives, so the dark-cockpit visual system is identical). Content sourced from the module decks + the TreasuryCentral homepage + Dirk's own outreach wording; no invented claims.
4. Rendered PPTX to PDF + PNG (PowerPoint COM); QA'd both montages.
5. Placed editable PPTX + send-ready PDF + README in `deliverables/lead-generation/rome-2026/call-collateral/`.
6. Corrected the close footer to match the product-deck standard (`brisken.com · Houston, TX`).

### SharePoint + email
7. Created SharePoint `.../2026_PPTX/Client Collateral` and uploaded all 4 files (house-style names); verified via re-list.
8. Built `.scratch/cdp-sp-collateral.py` (list / mkdir / upload / nav to any SP path; folder-capable, unlike `cdp-sp-io.py`).
9. Verified the folder link resolves (nav check), drafted the email, sent from Matthias to Dirk on approval, verified in Sent Items.

---

## Key Decisions Made
### Collateral = tailored TreasuryCentral overview, one per prospect
- **Choice:** a 10-slide TreasuryCentral cockpit deck per prospect, tailored on cover / problem / proof / close, with the shared product story in the middle.
- **Rationale:** "keep the same visual standard as the other assets" + the task checklist ("tailor TreasuryCentral demo flow"); the module decks are the base, TreasuryCentral is the umbrella.

### New "Client Collateral" folder inside 2026_PPTX
- **Choice:** created inside `2026_PPTX` (where the product decks live), sibling to the existing `Archive` folder.
- **Rationale:** user said "inside the folder where the other assets are"; the assets are in `2026_PPTX`.

### Evonik / RWZ proof slide kept, flagged for Dirk
- **Choice:** kept Dirk's own VW-note framing naming Evonik + RWZ as customers; surfaced it for his review rather than deciding for him.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.scratch/deckgen/build-treasurycentral.js` | Created | parameterized deck builder (`sanofi`\|`zalando`) |
| `.scratch/cdp-sp-collateral.py` | Created | folder-capable SharePoint I/O (list/mkdir/upload/nav) |
| `workspace/.../rome-2026/call-collateral/*.pptx,*.pdf,README.md` | Created | client-collateral deliverables + sourcing map |
| SharePoint `2026_PPTX/Client Collateral/*` (4 files) | Created (remote) | uploaded collateral |
| 2 Planner tasks (MARKETING PLAN / Lead Generation) | Created (remote) | Sanofi + Zalando collateral prep |

---

## Current Status
Both decks built, on SharePoint, and the link is emailed to Dirk (verified in Sent Items 16:27). Planner tasks live and assigned. The p1 expense-reconciliation build is a separate track, unaffected (still gated on §38 stack pick + Anthropic API access).

---

## Next Steps
1. Log the Sanofi + Zalando Tier-1 replies + call commitments to `comms-log.md` (Sanofi: next-week Fri ~16:00 confirmed, Dirk sends invite; Zalando: Dirk books end of next week, add Adela + Maria).
2. Dirk to review the Evonik / RWZ proof slide before presenting.
3. As more Tier-1 leads reply, reuse the same path: `call-collateral/` + the `Client Collateral` SP folder.
4. Optional: add a SAP one-pager companion to each pack (task checklist item).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/TASK-NAMING-STANDARD.md`
- `workspace/.../rome-2026/call-collateral/README.md` (sourcing map)
- `.scratch/deckgen/build-treasurycentral.js`

### Open Questions
- Evonik / RWZ naming on the proof slide: Dirk's sign-off.
- Cover "Prepared for {Company}" personalization kept as default.

### Working Notes
- **Sanofi:** Ian Haegemans, Treasury Process & Analytics Expert, GPO Team, Brussels; ian.haegemans@sanofi.com. "Friday is perfect" → next-week Fri ~16:00, Dirk sends the invite.
- **Zalando:** Lokesh Doggala, SAP Consultant, Corporate Solutions; lokesh.doggala@zalando.de; add Adela Dolezalova (external) + Maria Moeller (his lead). Dirk books end of next week or later.
- **SharePoint tooling:** `cdp-sp-collateral.py` MUST run with `MSYS_NO_PATHCONV=1` (Git Bash mangles leading-slash `/sites/...` args). mkdir uses `web/folders/addUsingPath`; list/upload use `GetFolderByServerRelativeUrl` (encodeURIComponent). Fresh-tab CDP pattern, same as `cdp-sp-io.py`.
- **Deck build:** `node build-treasurycentral.js <sanofi|zalando>`; render via `pdf-export.py` / `render-one.py` (PowerPoint COM).

### Reference Materials
- SP folder: `MARKETING/Shared Documents/20_Assets/BRISKEN PRESENTATIONS/OnePilot - Cloud Solutions Presentations/2026_PPTX/Client Collateral`

---

## How to Continue
Collateral is delivered. The next Tier-1 replies follow the same path (Planner task → tailored deck via the build script → call-collateral/ → SP Client Collateral → email Dirk). Log the two replies to comms-log if not already done.

---

## Strategic Feedback

### What Worked Well This Session
- One parameterized build script for both prospects kept the decks byte-for-byte identical in visual system while tailoring the four prospect-specific slides. Reusing the `build-mdh.js` primitives meant "same visual standard" was structurally guaranteed, not eyeballed.

### Suggestions
- The SharePoint leading-slash path-mangling burned ~5 calls and tripped the 3-iteration cap. A one-line wrapper (or the tool defaulting `MSYS_NO_PATHCONV=1`) kills this class permanently.

### System Health
- Third+ SharePoint/CDP tooling-recall friction of the day: memory-only fixes are not holding same-day. The standing recurrence-kill is a `PreToolUse` advisory (flag `connect_over_cdp`/`9222` script bodies and leading-slash SP shell args), already noted for `/system-dev`.
- Autonomy score: 3 friction events, all self- or hook-caught; no substantive user correction.
