# Task 6 summary: Produce the Calvin / Remittance forwardable clip brief

**Planner task:** "Produce the Calvin / Remittance forwardable clip brief"
(id `3NUFAgixXEK-PdZhHsz_zGUAIhyK`, MARKETING PLAN, Lead Generation bucket, 6th open
task from the top of the Board). **Branch:** `leadgen/task-6`. **Date:** 2026-07-09.

The task existed because the p2 spec named three Lane-1 forwardables and only two had
build evidence. This closes the third: the brief is written, and the clip itself is
built, encoded, and on SharePoint as the Path-B illustration. Path A, a screen
recording of the live demo, still needs Brisken's demo tenant and replaces this file
when it exists.

## Created

| File | What it is |
|---|---|
| `calvin-clip-brief.md` | The spec. Nine-shot, 90-second brief with on-screen text, the end card, an accuracy ledger tracing every claim to a source, and four questions for Dirk. |
| `production-runbook.md` | The manual-execution file. Pre-record checklist, masking checklist, recording and edit steps, export matrix, hosting, and the five-item gate before it is sent to anyone. |
| `clip/clip.html` + `clip/render.py` | The clip source. A deterministic timeline (`__seek(t)`) driven frame by frame through headless Chrome and piped into ffmpeg. Re-renders both cuts from scratch. |
| `video/calvin-clip-16x9-1080p.mp4` | The master. 90.00s, 1920x1080, H.264, 2.4 MB, no audio track. |
| `video/calvin-clip-1x1-1080.mp4` | The LinkedIn feed cut. 90.00s, 1080x1080, 2.0 MB, captions re-placed rather than centre-cropped. |
| `video/README.txt` | Ships beside the files on SharePoint: what the clip is, what it deliberately does not claim. |
| `email-to-dirk.md` | Draft, not sent. |
| `shared-file-proposals.md` | Four edits to shared files, written out rather than applied. |
| `notes-for-other-tasks.md` | Six findings that belong to other Board tasks. |

## Delivered to SharePoint

Both cuts and the README are in a new folder beside the PPTX assets, uploaded and
verified by comparing server byte-length against local, not by trusting a 200:

`.../20_Assets/BRISKEN PRESENTATIONS/OnePilot - Cloud Solutions Presentations/2026_VIDEO/`

Nothing else on SharePoint was touched; the folder is new and overwrote nothing.
Nothing outside `output/leadgen-task-6/` was created, modified, moved, or deleted in
the repo. No Planner task was completed or edited.

## What the brief decides, and why it took reading rather than writing

**The clip is not a remittance demo.** The Planner title and the p2 spec both say
"Calvin / Remittance", but Brisken's own slide 8 shows a funding request becoming a
bank transfer. Remittance Advice Gate is a different application, proven at a
different customer. The spec buckets them together because they share a story, which
is a good reason to lead the Remittance campaign with this clip and a bad reason to
call it a remittance demo. If that campaign ever runs at volume it earns its own
45-second cut.

**The middle of the clip is the approval gate, not the automation.** The viewer who
decides is the one the treasurer forwards it to, and that person's objection is
control, not capability. A clip that shows only speed confirms the fear it needs to
answer.

**"Digital co-worker" is dead, "Calvin" is not.** Brisken's Messaging Spine and the
TreasuryCentral restyle blueprint both retire the label. But Calvin is printed inside
the chat box on slide 8 and cannot be renamed by a marketing decision. The two are not
competing: `OnePilot Agents` is the category, `Calvin` is one agent. The clip says
"Calvin is an agent on OnePilot" and the deprecated label never appears.

**Three claims are barred from the end card.** No "listed on the SAP Store" (the
2026-06-17 audit found only Market Data Hub and Trade Automation are listed, and this
line is correct on the MDH teardown, so it will get copied across without thinking).
No named customer (the chemicals proof is anonymized; logos were cleared, the
logo-to-use-case mapping was not). No ISO 27001 or SOC 1 line until Dirk confirms the
certificate scope, because the catalog records it as a posture Brisken states about
itself.

## What shipped, and what is still manual

The clip that exists is **Path B**, the labelled schematic, animated from slide 8 in
the deck's own dark-cockpit palette. Every frame carries an "ILLUSTRATION" chip and
the end card names it as one. It was never meant to be the final asset.

Still manual:

1. **Re-cut it from the live demo (Path A).** Needs a Brisken person who can drive the
   real Calvin flow, about 40 minutes of recording, and the four-eye approval prompt
   switched on in the demo tenant. A recording of the product beats an animation of it
   for the skeptical second viewer, who reads an animation as marketing.
2. **Host it first-party.** `resources.brisken.com` is live (200) and already serves
   the SAP brochure PDFs from an isolated Vercel project. Upload, wrap in a minimal
   landing page so the end-card URL has a destination, and give each outreach tier a
   tracked link. The forward count is the only metric that says whether it worked.
3. **Apply the four shared-file edits** in `shared-file-proposals.md`.

`email-to-dirk.md` is a draft and was not sent. The carrier emails and Sales Navigator
messages that would deliver the clip to prospects were not drafted at all. That is the
comms-draft class and it waits for an explicit ask plus Dirk's
sending-identity gate.

## Open questions

1. Can a Brisken person screen-record the live Calvin demo? Path A is worth waiting a
   week for.
2. Is there an ISO 27001 / SOC 1 Type II certificate, and what is in scope? Decides
   whether the end card carries a third trust line.
3. Does the chemicals customer clear a named reference for this flow? A yes makes the
   end card materially stronger.
4. May the clip retire "digital co-worker" while the deck that went to Adidas on
   2026-07-07 still carries it? Re-cutting that deck is Dirk's call, not a side effect
   of this brief.
