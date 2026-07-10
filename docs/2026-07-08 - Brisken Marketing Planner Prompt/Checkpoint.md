# Checkpoint: Brisken Marketing Planner Prompt

**Date:** 2026-07-08
**Status:** Deliverable handed off (distributable prompt) — no live write performed

---

## Summary
Dirk wants the main marketing tasks written into the Brisken "MARKETING PLAN" in Microsoft Planner. The ask resolved to producing a reusable prompt the owner can hand to each marketing chat so every chat derives its own task names from its current work and writes them into the shared plan correctly. No task was written to the live tenant this session.

---

## What Was Done This Session
### Investigation (read-only, live tenant via CDP :9222)
1. Confirmed the Edge CDP session on `localhost:9222` is live and signed into the Brisken tenant (`aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74`) as Matthias.Silva.
2. Enumerated open tabs: active `brisken.sharepoint.com/sites/MARKETING` session + a Planner tab open at `planner.cloud.microsoft/webui/mytasks/assignedtome/view/grid` (**My Tasks**, not the MARKETING PLAN board).
3. Searched the repo for "our to-do list" (session docs + grep) — could not uniquely pin a canonical task-list file; the checkpoints carry my session-note framing of open items, not a shared owner/Dirk list.

### Deliverable
4. Wrote a copy-paste prompt for the owner to distribute to marketing chats. First version took a fixed task list (placeholder). Revised per owner request so **each chat derives its own task names** from the work it is actually doing, phrased client-readable, then writes them into the plan.

---

## Key Decisions Made
### Do not fabricate task names into a client-visible plan
- **Choice:** Refused to reconstruct-and-write tasks from my own session notes. Held for the actual list, then pivoted to the distributable prompt.
- **Rationale:** The MARKETING PLAN is shared with the Brisken MARKETING group; wrong or invented task text is high-blast-radius and client-visible (B4 + anchor-on-source + no-invasive-action-without-ask).

### Prompt design: self-derivation over fixed list
- **Choice:** Each chat reviews its own current work, extracts ~3-7 main tasks, names them client-readable (plain, outcome-first, no em-dashes, no internal shorthand/acronyms), dedups against existing plan tasks, writes, and reads back.
- **Rationale:** Owner is fanning the work across multiple marketing chats; each chat knows its own workstream better than a central list would.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| (none in repo) | — | Deliverable was an in-conversation prompt; read-only tenant inspection only. `inspect_marketing.py` lived in scratchpad and its run was cancelled on the pivot. |

---

## Current Status
No write to the live tenant. The distributable prompt is ready in-conversation (full text in Working Notes below). Two fill-ins remain before it is sent: the **bucket name** (default "To do") and, optionally, the **exact MARKETING PLAN board URL** to hardcode so no chat can land on the wrong plan.

Platform/ops usage not re-assessed this session (no Make/n8n/Trigger scenarios touched).

---

## Next Steps
1. Owner: open the MARKETING PLAN board once and copy its URL → hardcode into the prompt so chats can't write into "My Tasks" or a legacy plan by mistake.
2. Owner: set the bucket name in the prompt (default "To do"), then distribute to the marketing chats.
3. Alternative fast path: hand me the actual task lines + bucket and I write them into the plan directly (I am already attached to the session).

---

## Context for Next Session
### Files to Read First
- `docs/sessions/2026-07-08.md` (this day's sessions 1-5)
- memory `reference_user_edge_cdp_9222.md` (CDP attach recipe)
- memory `feedback_no_invasive_action_without_ask.md` (why the write was gated)

### Open Questions
- What is the canonical "our to-do list" the owner/Dirk share? Not found as a repo file; may be a OneNote / the SharePoint MARKETING PLAN file / a shared doc.
- Exact MARKETING PLAN plan ID / board URL (not captured; prompt currently navigates by name).
- Target bucket name inside MARKETING PLAN.

### Working Notes
**Mechanism for writing to Planner (verified environment, corrected after parallel Session 5):** Playwright `connect_over_cdp("http://localhost:9222")` HANGS here — ~100+ targets open. Use RAW single-target CDP: GET `http://localhost:9222/json/list`, pick the page whose url contains `planner.cloud.microsoft`, drive that one `webSocketDebuggerUrl` over a websocket (Runtime.evaluate + Input.dispatch*). Working driver already in repo: `.scratch/cdp.py` (JSON steps on stdin: click/type/enter/sleep/eval + optional `--goto`). Tenant UI is mixed EN/DE ("Add task" = "Aufgabe hinzufügen"). The first "MARKETING PLAN" hit is a DELETED legacy plan; the live one already carries a "Lead Generation" bucket + ~5 tasks (Session 5). Graph API POST /planner/tasks is cleaner but needs a bearer token page cookies don't carry.

**Final distributed prompt (self-derivation version, raw-CDP attach):**
```
TASK: Add YOUR current marketing work as tasks in Microsoft Planner. Each chat defines its
own task names from what it is actually working on. This writes to Brisken's LIVE M365
tenant, so add only real tasks and change nothing else.

ENVIRONMENT (already set up — do not re-auth, do not open a login flow):
- Microsoft Edge is running with remote debugging on port 9222, signed into the Brisken
  M365 tenant as Matthias.Silva (tenant id aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74).
- ATTACH WITH RAW SINGLE-TARGET CDP, NOT Playwright. chromium.connect_over_cdp() HANGS here
  because ~100+ targets are open. Instead: GET http://localhost:9222/json/list , find the
  page whose url contains "planner.cloud.microsoft", and drive that ONE target's
  webSocketDebuggerUrl directly over a websocket (CDP Runtime.evaluate + Input.dispatch*).
- A ready-made driver already exists in this repo: .scratch/cdp.py . It takes a JSON array
  of steps on stdin — {"click":"aria-or-text"} | {"type":"text"} | {"enter":1} |
  {"sleep":ms} | {"eval":"js"} — run in one persistent connection, plus an optional
  --goto URL. Reuse it, e.g.:
    echo '[{"click":"Aufgabe hinzufügen"},{"type":"My task title"},{"enter":1}]' | \
      uv run .scratch/cdp.py --goto "https://planner.cloud.microsoft/webui/..."
- Do NOT use agent-browser --auto-connect — that's an isolated context and won't be signed in.

DESTINATION:
- Plan: "MARKETING PLAN" (shared with the MARKETING group).
- WARNING: the first hit for "MARKETING PLAN" is a DELETED legacy plan. Confirm you are on
  the LIVE plan before writing (read the plan title AND check it already contains a
  "Lead Generation" bucket). Do NOT write into the legacy plan or into "My Tasks".
- The live plan already has a "Lead Generation" bucket with ~5 tasks. Dedup against what is
  there and add to the right bucket.
- Bucket / column: [FILL IN — e.g. "To do" or "Lead Generation"]

DEFINE YOUR TASK NAMES (do this first, from your own work):
1. Review what you are currently working on for the marketing workstream: your current
   session, latest checkpoint / next-steps, open deliverables and specs. Anchor on real,
   in-flight or upcoming work — do not invent tasks you are not actually doing, and skip
   anything already finished.
2. Pull out the MAIN tasks only — the handful of deliverables you are accountable for
   (aim for roughly 3 to 7), not every sub-step.
3. Write each as a short, client-readable title. The Brisken MARKETING team will see these,
   so: plain language, outcome-oriented, no internal shorthand or acronyms they wouldn't
   know, no em-dashes (no —, no --), no filler words (robust, leverage, streamline, etc.).
   Example shape: "Send Rome booth follow-up outreach", not "p2 tier-3 send after Dirk go".
4. Echo the list of titles you derived before you write anything.

HOW TO WRITE CORRECTLY:
1. Open the "MARKETING PLAN" plan and select the target bucket.
2. Read the existing tasks first. Skip any task already there or clearly equivalent (avoid
   duplicates, including near-duplicates another chat may have added).
3. For each remaining title: click "Add task" ("Aufgabe hinzufügen" in the German UI), type
   the exact title, press Enter. One task per title.
4. Do not set assignees, due dates, or descriptions unless you deliberately want one. Do not
   touch, reassign, complete, or delete any existing task. Do not send anything.

VERIFY before reporting done:
- Re-read the plan's task list and confirm every title you intended is present exactly once.
- Report: plan name + URL, bucket, the titles you derived and added, how many you skipped as
  duplicates, and which workstream/source you drew them from.

If you can't find the "MARKETING PLAN" plan or the browser isn't signed in, STOP and say so.
Do not create a new plan or write into a different one.
```

### Reference Materials
- Planner (My Tasks tab): `https://planner.cloud.microsoft/webui/mytasks/assignedtome/view/grid?tid=aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74`
- Marketing site: `https://brisken.sharepoint.com/sites/MARKETING`

---

## How to Continue
If the owner returns the bucket + plan URL (or the actual task lines), either finalize the prompt or write the tasks into MARKETING PLAN directly via the CDP session, then read back to verify.

---

## Strategic Feedback

### What Worked Well This Session
- Owner's mid-task clarification ("Dirk wants tasks into Planner directly, I have it open") sharpened an ambiguous SharePoint ask fast, avoiding a wrong-artifact build.

### Suggestions
- If "our to-do list" is a recurring shared artifact, naming its home once (a doc path, OneNote section, or the SharePoint file) would let future chats anchor without asking.

### System Health
- Autonomy score: 1 human intervention this session (the SharePoint→Planner redirect).
- No rule/skill gap surfaced. The invasive-action gate and B4 held: the session correctly produced a gated hand-off instead of writing unverified task text into a client-visible plan.
