# Checkpoint: Brisken Calvin Clip (Lead-Gen Task 6)

**Date:** 2026-07-09
**Status:** Task complete on the Planner board and delivered to the client. One
client-visible defect found AFTER delivery (BTP on the end card); the corrected
render is built locally and the SharePoint replacement is HELD pending an explicit go.

---

## Summary

Resolved Planner Task 6 ("Produce the Calvin / Remittance forwardable clip brief"),
wrote the brief, then built the clip itself as the Path-B illustration, uploaded both
cuts to Brisken SharePoint, sent Dirk the link, and marked the task complete. The
checkpoint friction audit then caught that the shipped end card names SAP Business
Technology Platform, against Dirk's open "Exclude BTP from all demos" directive.

---

## What Was Done This Session

### Brief (commit `ccfb5df`)
1. Resolved Task 6 by Planner order-hint, not by guessing: 6th open task in the
   Lead Generation bucket, id `3NUFAgixXEK-PdZhHsz_zGUAIhyK`.
2. Wrote `calvin-clip-brief.md`: nine shots, 90 seconds, on-screen text, end card,
   an accuracy ledger tracing every claim to a source, four questions for Dirk.
3. Wrote `production-runbook.md` (Path A live capture, Path B fallback, masking
   checklist, export matrix, hosting, five-item pre-send gate).

### Clip (commit `bfbdaaa`)
4. Built `clip/clip.html` as a deterministic timeline exposing `__seek(t)`, driven
   frame by frame through headless Chrome, piped into a static ffmpeg from
   `imageio-ffmpeg` (no system ffmpeg on this machine).
5. Rendered two cuts, both exactly 90.00s, no audio, captions burned in:
   16:9 1920x1080 (2.4 MB) and 1:1 1080x1080 (2.0 MB).
6. Created SharePoint `2026_VIDEO` beside `2026_PPTX`, uploaded both cuts plus a
   README, verified by comparing server byte-length against local.

### Delivery (commits `1d2eb36`, `16a316c`, `f8827b6`)
7. Drafted, shortened (twice, on user correction), and **sent** the email to Dirk
   from `Matthias.Silva@brisken.com`, verified in Sent Items.
8. Marked the Planner task complete (`percentComplete=100`), verified by re-reading
   the task and re-listing the bucket to prove only that one task moved.

### Post-delivery correction (uncommitted at checkpoint time)
9. Friction audit found the BTP violation. Removed the line from `clip.html`, updated
   the brief's end-card spec and accuracy ledger, re-rendered both cuts.

---

## Key Decisions Made

### The clip is not a remittance demo
- **Choice:** Kept the funding-request-to-bank-transfer flow, and recorded that
  Remittance Advice Gate would need its own separate 45-second cut.
- **Rationale:** The Planner title and the p2 spec both say "Calvin / Remittance",
  but slide 8 of the Digital Co-Worker deck shows a funding request. Remittance
  Advice Gate is a different application with a different customer proof. The spec
  buckets them together because they share a story, which justifies leading the
  Remittance campaign with this clip and does not justify calling it one.

### The approval gate is the centre of the clip
- **Choice:** Longest single hold in the 90 seconds goes to the human clicking Approve.
- **Rationale:** The person who decides is whoever the treasurer forwards it to, and
  their objection is control, not capability. Brisken's own deck carries the line as
  a footnote; the clip promotes it to the central beat.

### "Calvin" survives, "digital co-worker" does not
- **Choice:** The clip says "Calvin is an agent on OnePilot" and never says co-worker.
- **Rationale:** The Messaging Spine and the TreasuryCentral restyle blueprint both
  retire the label, but Calvin is printed inside slide 8's chat box and cannot be
  renamed by a marketing decision. `OnePilot Agents` is the category; `Calvin` is one
  agent. No deck re-cut needed.

### Three claims barred from the end card, then a fourth
- **Choice:** No SAP Store listing, no named customer, no ISO/SOC line. After the
  audit, no SAP BTP either.
- **Rationale:** Only MDH and Trade Automation are Store-listed (2026-06-17 audit);
  the chemicals proof is anonymized and only the logos were cleared; the catalog
  records ISO/SOC as a posture Brisken states about itself. BTP is Dirk's directive.

### Path B shipped, labelled
- **Choice:** Built the animated illustration rather than waiting for demo-tenant time.
- **Rationale:** Every frame carries an "ILLUSTRATION" chip and the end card names it.
  A recording of the product beats an animation of it for the skeptical second viewer,
  so this is a placeholder that gets replaced, not the asset.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `output/leadgen-task-6/calvin-clip-brief.md` | Created, then amended | The spec; amended to bar BTP from the end card |
| `output/leadgen-task-6/production-runbook.md` | Created | Manual steps: record, mask, edit, export, host, gate |
| `output/leadgen-task-6/clip/clip.html` | Created, then amended | Deterministic clip source; BTP line removed |
| `output/leadgen-task-6/clip/render.py` | Created | Headless-Chrome frame capture into ffmpeg |
| `output/leadgen-task-6/video/*.mp4` | Created, then re-rendered | The two cuts |
| `output/leadgen-task-6/video/README.txt` | Created | Ships beside the files on SharePoint |
| `output/leadgen-task-6/email-to-dirk.{md,html}` | Created | The sent message, HTML carries the live anchor |
| `output/leadgen-task-6/shared-file-proposals.md` | Created | 5 shared-file edits staged, not applied |
| `output/leadgen-task-6/notes-for-other-tasks.md` | Created | 6 findings belonging to other board tasks |
| `.scratch/planner_list_leadgen.py` | Created | List bucket tasks in board order |
| `.scratch/planner_task_details.py` | Created | Dump a task's description + checklist |
| `.scratch/grabtoken2.py` | Created | Graph token from OUR OWN tab, not the user's |
| `.scratch/sp-upload-video.py` | Created | Folder create + upload + byte-length verify |
| `.scratch/planner_complete_task6.py` | Created | Guarded single-task completion |
| SharePoint `.../2026_VIDEO/` | Created | Both cuts + README, live in Brisken's tenant |
| Planner task `3NUFAgix…` | Completed | percentComplete 0 -> 100 |

---

## Current Status

Task 6 is closed on the board and Dirk holds the SharePoint link. The clip he can
open right now still carries "running on SAP Business Technology Platform" on its end
card. The corrected 16:9 cut is rendered locally; the 1:1 was still rendering at
checkpoint time. Nothing has been re-uploaded.

Branch `leadgen/task-6`, PR #207 open and unmerged (isolation rule: never commit to
main while parallel task sessions run).

No orchestrator platform for brisken p2 (manual-first, 1:1 from Dirk's Outlook), so no
ops status line and no Make.com reconciliation applies.

---

## Next Steps

1. **Decide on the SharePoint replacement.** The corrected cuts overwrite two files
   in `2026_VIDEO` that only this session created. It is an invasive tenant write, so
   it is held. Dirk has the link either way, so the window matters.
2. **Decide whether Dirk gets a note.** The email did not mention BTP, so a silent
   replacement is defensible. A one-line follow-up is the honest option.
3. **Build `tools/validate-demo-material.py`.** Proposed by session 10 this same day
   for the identical defect; not built; recurred within hours in a different asset.
   Scan rendered demo text against a banned-terms list sourced from client directives.
4. Apply the five shared-file edits in `output/leadgen-task-6/shared-file-proposals.md`
   (p2 spec next_steps, brief relocation, catalog naming note, booth playbook, and the
   comms-log entry for the sent email).
5. Re-cut the clip from a live demo recording (runbook Path A) when demo-tenant time
   exists. That replaces the illustration.
6. Answer the two open questions the email deliberately does not ask: ISO 27001 /
   SOC 1 certificate scope, and whether the chemicals customer clears a named reference.

---

## Context for Next Session

### Files to Read First
- `output/leadgen-task-6/SUMMARY.md` (on branch `leadgen/task-6`)
- `output/leadgen-task-6/calvin-clip-brief.md` sections 6 and 7 (the claim bars, the naming call)
- `output/leadgen-task-6/shared-file-proposals.md`
- `docs/sessions/2026-07-09-context.yaml` (carries the parallel sessions' BTP findings)

### Open Questions
- Replace the two MP4s on SharePoint now, and does Dirk get told?
- ISO 27001 / SOC 1: is there a certificate, and what is in scope?
- Does the chemicals customer clear a named reference for this flow?
- May the clip retire "digital co-worker" while the Adidas deck still carries it?

### Working Notes

**The BTP miss, in full.** Dirk's directive (Planner, open, created 2026-07-08):
"leave SAP BTP out of all demo materials. Review the existing decks and demos and
remove BTP content." The Digital Co-Worker deck names BTP on slide 7; I sourced the
end card's trust line straight from it, ran a claim gate against SAP Store / named
customer / ISO, and never checked the directive. The task title was printed in my own
board listing at the start of this session. Today's `2026-07-09-context.yaml` already
recorded "BTP also in 3 of 4 module decks (… Digital Co-Worker 2 …)". I did not read
it, because I never ran `/comd_resume` and never loaded the session context. The fix
now on disk uses the deck's own alternative phrasing: "running inside your SAP
landscape" (slide: "sits inside your landscape, not beside it"), which keeps the trust
signal without the banned name.

**Verification theater, in full.** Building the clip, three messages were clipped out
of the chat panel. I checked with `getBoundingClientRect` and the check reported zero
clipped elements, because `overflow:hidden` clips relative to the element's own box
and I was translating that same box: the geometry API reports where an element *would*
be, not whether it was painted. I stated "Nothing clipped in either ratio" on the
strength of that. The pixels disagreed. The check that actually worked crops the
element's rect out of a real screenshot and counts ink pixels. Two related bugs came
from measuring layout before the user's chat bubble had text typed into it, which put
every scroll offset a line short and walked the cursor off the Approve button.
**Transferable principle: a rendering claim must be verified in pixels. Geometry APIs
describe intent, not output.**

**Outlook hazard.** This machine's COM profile carries BOTH `Matthias.Silva@brisken.com`
and `dirk.neumann@brisken.com`, and defaults to Dirk's. Sending without pinning
`SendUsingAccount` would have sent from Dirk to Dirk. Also: `SendUsingAccount.SmtpAddress`
reads back empty before `.Send()`, so it is not a usable pre-send assertion; verify
against the item in Sent Items afterwards.

**SharePoint auth.** `rtFa` is scoped to the apex `.sharepoint.com`, not
`brisken.sharepoint.com`, and there is a decoy `rtFa` on `.live.com`. Filter cookies by
apex-suffix. Page-context `fetch` + base64 through `Runtime.evaluate` is not viable for
MB-scale files; cookies + `requests` is. `HasUniqueRoleAssignments=false` on the new
folder proved Dirk inherits access before the link went out.

**Planner.** Order hints sort ascending and match the Board top-to-bottom, so open-task
position is derivable without a screenshot. The board grew 37 -> 39 tasks *during* this
session and two tasks were completed by other sessions, so position-based task IDs are
unstable across parallel runs. Complete by task id, never by position.

### Reference Materials
- SharePoint: `.../20_Assets/BRISKEN PRESENTATIONS/OnePilot - Cloud Solutions Presentations/2026_VIDEO/`
- Planner: MARKETING PLAN `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`, bucket Lead Generation `gyfptEwAwUiJLXfd6aMrYWUABZRr`
- PR: https://github.com/011matthias/agentic-ops1.01/pull/207
- `workspace/clients/brisken/context/Products/Digital Co-Worker.pptx` slide 8 (the flow), slide 7 (BTP)

---

## How to Continue

Read `SUMMARY.md` on `leadgen/task-6`. The single live decision is whether to overwrite
the two MP4s in SharePoint `2026_VIDEO` with the BTP-free renders, and whether Dirk gets
a note. Everything else on this task is either shipped or staged in
`shared-file-proposals.md`.

---

## Strategic Feedback

### What Worked Well This Session
- The explicit per-action greenlights ("greenlight to send", "mark this complete") made
  the three invasive writes clean: each got a readiness check before firing rather than
  a permission round-trip mid-flight.
- The two corrections on the email ("shorter", "embed the link") were terse and
  specific, which is why they cost one turn each instead of a discussion.

### Suggestions
- The parallel-task prompt says "gather context first: check the repo" but does not say
  "run `/comd_resume`". Both BTP defects today came from a session not reading the
  day's own context YAML. Adding `/comd_resume {client}` as step 0 of the task prompt
  would have caught this before the asset was built, not after it was delivered.

### System Health
- **The same defect shipped twice in one day.** Session 10 found BTP in the Zalando and
  Sanofi decks, proposed `tools/validate-demo-material.py`, and did not build it.
  Hours later this session shipped BTP on a video end card to the same tenant. The
  write-time hooks enforce banned *language* (em-dashes, corporate thesaurus) but
  nothing enforces banned *content* whose source of truth is a client directive living
  in Planner. That gap is now the highest-value structural fix on the board, and it is
  `infrastructure-deferred` on its second occurrence.
- Autonomy score: 5 friction events, 2 of them user-detected interventions.
