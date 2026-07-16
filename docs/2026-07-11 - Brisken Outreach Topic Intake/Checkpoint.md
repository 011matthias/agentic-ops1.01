# Checkpoint: Brisken Outreach Topic Intake

**Date:** 2026-07-11
**Status:** Fill-in roster live in Dirk's Planner task Notes; ball in Dirk's court

---

## Summary
Dirk replied on the partner/SAP outreach Planner task that these 17 need a
personal touch (he knows them all) and asked where he can hand over the topic /
subject points per person. Matthias promised, in the task chat, to "drop the
names right here in the task" for Dirk to add a line or two under each. Executed
that by prepending a fill-in roster block to the task Notes via Graph.

---

## What Was Done This Session

### Answered Dirk's "where do I give you the topics"
1. Read the built pack (`dirk-send-pack/partner-sap-outreach.md`) + the 07-11
   Partner SAP Outreach checkpoint to reconstruct state: pack shipped, 13 drafts
   already in Dirk's Outlook, 3 contacts held (live threads).
2. Drafted a Register-A chat reply for Matthias (call vs written, "I'll turn
   what you give me into a note in your voice"). Matthias sent the written
   option to Dirk.

### Dropped the fill-in roster into the task (the promised deliverable)
3. Inspected the live Planner tab over raw page-level CDP (:9222): board view
   open, task detail not open, `conversationThreadId: null` on the task — the
   "Aufgabenchat" is the newer Loop-backed chat with **no Graph write path**, so
   the reliable surface is the task Notes.
4. Found the task via Graph: id `S-t9htVQa0WgWqw5zGW0j2UALkug`, read its existing
   Notes (roster rules written by the task-4 session) + checklist (17 contacts).
5. Prepended a "YOUR ANGLES GO HERE" block: 13 names each on its own line for a
   hook, an inline ICD-Dashboard prompt on Lasecki + Hamid, and a "nothing to
   add here" line for the 3 held contacts (Sharandakov, Staniford + Ramos;
   Jochen already done). Existing Notes preserved verbatim below via exact
   in-memory round-trip.
6. Set `previewType: description` so the board card now previews the block —
   how Dirk notices it in the task he was chatting in.

---

## Key Decisions Made

### Task Notes, not the chat
- **Choice:** wrote the roster into the task Notes field, not the Aufgabenchat.
- **Rationale:** the chat has `conversationThreadId: null` (Loop/Teams-backed,
  no stable Graph API) and is a linear thread where "add a line under each" does
  not work. Notes is the only surface that supports the fill-in structure
  Matthias promised, and it is a clean, reversible Graph write.

### Prepend + preserve, not overwrite
- **Choice:** prepend the block, keep the existing roster-rules Notes intact,
  round-trip the existing description string in-memory rather than retyping it.
- **Rationale:** the existing Notes carry the task-4 roster logic; overwriting
  would lose it, and retyping risked degrading the pre-existing mojibake
  (`Teisner-Kj�r`) further. In-memory round-trip changes only the prepended block.

### 13 in the fill-in, 3 held off
- **Choice:** list only the 13 we are drafting; mark Sharandakov + the Tradeweb
  pair as "already moving, nothing to add."
- **Rationale:** Sharandakov replied 07-06 (call being set); Tradeweb pair are
  awaiting reply on Dirk's 07-01 technical thread. Inviting angles for them
  risks reopening live threads with a fresh opener.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| Planner task `S-t9htVQa0Wg...` Notes (external state) | Modified | Prepended fill-in roster; `previewType` set to `description` |
| .scratch/planner_cdp.py | Created | Raw page-level CDP inspect of the Planner tab (read-only) |
| .scratch/find_outreach_task.py | Created | Graph: locate task id + dump current Notes/checklist |
| .scratch/post_outreach_fillin.py | Created | Graph PATCH of the Notes (dry-run default, `--go` to write, readback) |
| .scratch/planner_inspect.py | Created | Abandoned connect_over_cdp attempt (hung); kept as scratch |

(All `.scratch/` files are gitignored/ephemeral. No repo commits this session.)

---

## Current Status
Fill-in roster is live in the task Notes (Graph readback HTTP 200: block at top,
all 13 names present, original Notes intact, `previewType: description`). Dirk's
chat reply already told him the names would be in the task; now they are. Nothing
is blocked on our side.

Platform: Brisken has no op-count model (custom SaaS / FastAPI build) — no ops
line applicable.

---

## Next Steps
1. **Dirk's court:** add a line/hook under each name in the task Notes; supply
   the ICD-Dashboard state line for Lasecki + Hamid.
2. **Then ours:** fold Dirk's angles into the 13 drafts already in his Outlook
   (edit the loaded drafts, or regenerate via `.scratch/load_partner_drafts.py`);
   re-verify sync (server round-trip, not local readback).
3. Watch the task Notes for Dirk's edits (Graph re-read of the description).
4. Carry-overs from earlier today unchanged: 19 staged Rome drafts await Dirk's
   send; ~Jul 15 Tradeweb in-thread nudge if quiet; T3 email wave; repo-visibility
   owner decision (011matthias/agentic-ops1.01 public); proto migration to a
   brisken.com home.

---

## Context for Next Session

### Files to Read First
- workspace/clients/brisken/deliverables/lead-generation/rome-2026/dirk-send-pack/partner-sap-outreach.md
- docs/2026-07-11 - Brisken Partner SAP Outreach/Checkpoint.md (the pack build)
- .scratch/post_outreach_fillin.py (how the Notes were written; re-read shows the block)

### Open Questions
- Will Dirk fill the Notes, or come back wanting a call instead? If a call, the
  roster block doubles as the capture template.
- Lasecki/Hamid ICD state line still unresolved (also gating those two drafts).

### Working Notes
- **Planner writes:** Graph token in `.scratch/graph_token.txt` (from
  `grabtoken.py`, CDP :9222 Edge planner tab) has `Tasks.ReadWrite` +
  `Group.ReadWrite.All`. Task details PATCH needs `If-Match` etag (fetch fresh
  same-run to avoid 412). Notes = the `description` field on `/planner/tasks/{id}/details`.
- **CDP gotcha (new):** Playwright `connect_over_cdp` to the user's Edge hung
  180s at context enumeration (many tabs open). Raw page-level CDP websocket
  (the `grabtoken.py` pattern: `Runtime.evaluate` against the page target's
  `webSocketDebuggerUrl`) is the reliable path for read/eval on a known single
  tab. Memory `reference_user_edge_cdp_9222` updated with this caveat.
- **Task chat is unreachable via Graph:** `conversationThreadId: null`; the
  Aufgabenchat is Loop-backed. Outbound task-chat replies are Matthias's to
  type in the live UI.

### Reference Materials
- Planner task: id `S-t9htVQa0WgWqw5zGW0j2UALkug`, plan `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`
- Board tab: https://planner.cloud.microsoft/webui/plan/xSrT0YMHTkCaTkhtTAFZJ2UAC-aA/view/board

---

## How to Continue
`/comd_resume brisken`, then Graph re-read the task Notes
(`.scratch/find_outreach_task.py`) to see whether Dirk has filled any hooks; for
each filled name, weave his angle into the matching draft in his Outlook and
re-verify server sync.

---

## Strategic Feedback

### What Worked Well This Session
- The prior checkpoint + the built pack carried full state; reconstructing "what
  is already sent / held / drafted" took one read, no re-derivation. The task
  Notes themselves (written by task-4) also paid off again as cross-session memory.
- Dry-run-then-`--go` on the Graph write (scopes + etag + preview + preserve
  check first) made the invasive client-system write safe and one-shot.

### Suggestions
- The `.scratch/planner_*.py` family has grown to ~15 one-off Graph/CDP scripts.
  A single small `tools/planner.py` (token load, task lookup, details read/patch
  with etag handling) would retire most of them and remove the "which script did
  the read" ambiguity. Candidate for /comd_system-dev.

### System Health
- Autonomy score: 0 human interventions — the one user turn ("execute, you have
  greenlight") was the required authorization for an invasive write into the
  client's live Planner, the invasive-action gate working as designed, not a
  correction.
- Two agent/hook-detected events, both self-handled: a `connect_over_cdp`
  slow-path and a B1 deferral phrasing caught by the stop-hook. No new structural
  gap beyond the standing sibling-session guard (unbuilt, tracked).
