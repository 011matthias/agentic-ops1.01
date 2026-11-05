# Checkpoint: VossMoos Call Prep and Debrief

**Date:** 2026-11-05
**Status:** Call held 2026-11-04 16:30 CET; André (VossMoos UG) decides by Friday 2026-11-06, start Monday 2026-11-09

---

## Summary
Prepared the owner for the Upwork call on "Outbound Product Manager: Roadmap, Outreach Systems & AI Agents", then transcribed the recording locally and summarized it. The role turned out to be productizing a single-customer AI outbound system into a multi-tenant product, owned through a dated roadmap.

---

## What Was Done This Session
### Call prep
1. Answered the owner's prep questions: KPIs, the posting's problem and funnel, "roadmap", "PM agents", and talk tracks for each "You are" bullet, grounded in memory files (Mimecast 10/11, Instantly delay semantics, Meji 3 campaigns, Brisken 53-domain farm, Sales Nav pacing, send-by-ID 19/19, recon KPI 21 to 82).
2. Built `.scratch/call-prep-vossmoos.html`: 7 sections, every point a collapsible `<details>` with a one-line summary, expand/collapse all, 8 call questions, rate $45 with floor $36.
3. Web search for VossMoos UG found no public footprint, so the prep said to ask André to show the product.

### Debrief
1. Located the recording (`Desktop\Downloads\WhatsApp Audio 2026-11-04 at 16.50.30.mp4`), transcribed it on CPU with faster-whisper large-v3-turbo (1114 s audio in 554 s), never uploaded.
2. Delivered the call summary: who they are, what the role is, what was not discussed, two facts to correct, recommended KPIs.

---

## Key Decisions Made
### Local transcription
- **Choice:** faster-whisper on CPU, audio decoded by an ffmpeg subprocess.
- **Rationale:** a private call recording does not go to a cloud API, and the Brisken OpenAI/Gemini keys belong to the client.

---

## What Did NOT Work (and why)
- **faster-whisper `model.transcribe(path)`:** the PyAV release uv resolved rejects `av.open(..., metadata_errors="ignore")` (TypeError in `faster_whisper/audio.py decode_audio`). Fixed by decoding to float32 PCM with ffmpeg and passing the numpy array.
- **Looking for the recording in `%USERPROFILE%\Downloads`:** the Downloads known folder is redirected to `C:\Users\neuma_p1qrsic\Desktop\Downloads` (registry User Shell Folders `{374DE290-123F-4565-9164-39C4925E467B}`); the old folder holds nothing recent.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.scratch/call-prep-vossmoos.html` | created (gitignored) | collapsible call-prep page |
| `.scratch/vossmoos-call-2026-11-04-transcript.txt` | created (gitignored) | timestamped transcript, copied from the session scratchpad |
| memory `reference_downloads_folder_redirected.md` | created | real Downloads path |
| memory `project_vossmoos_outbound_pm_lead.md` | created | the lead, its decision date, open terms |

---

## Current Status
- **What André said:** VossMoos built an AI outbound system for one enterprise customer that replaces about 10 BDRs. Agents enrich from conferences, LinkedIn and customer data, and a human approves each message. There are 3 to 4 tenants now, more coming.
- **What he wants:** a "visionary" PM to turn it into a named product with a roadmap, dated milestones and general vs tenant-specific prioritization, and to answer stakeholders who ask daily what ships. Their PM agent (Jira + Slack ticket admin) does not set direction. The team is 3 to 4 engineers/analysts.
- **Not discussed:** rate and weekly hours. The owner said they are available from next week.
- **Ops status:** platform has no infrastructure.yaml; no comms-log (Upwork thread).

---

## Next Steps
1. Before Friday 2026-11-06: decide the rate (recommendation $45/hr, floor $36; client average $12.13/hr over 874 h) and the weekly hours that fit KIT.
2. Optional, only on the owner's request: an Upwork message with a one-paragraph two-month roadmap sketch on the KPIs (approval rate without edits, time saved per message, replies/meetings per tenant, days to onboard a tenant).
3. On an offer: contract via Upwork only, then a first-week plan (tenant inventory, KPI baseline, roadmap v0 with dated milestones).
4. Carried over: remove worktree `agentic-ops1-case-study` once the PDF is attached; codify the no-video variant in `skil_upwork-proposals/PROPOSAL-TEMPLATES.md`.

---

## Context for Next Session
### Files to Read First
- `.scratch/vossmoos-call-2026-11-04-transcript.txt`
- `.scratch/call-prep-vossmoos.html`

### Open Questions
- At 01:05 the owner summarized back "you work in the legal branch". André's opening is not in the recording, which starts mid-sentence. Unclear whether it is a transcription artifact.

### Working Notes
- Facts to correct in anything written: in the call the owner said the KPI went from "about 22%" to "about 85%"; the documented figures are 21 to 82 of 100. NeverBounce was described as an MX/gateway check; it verifies that the mailbox exists and misses gateway blocks, which is why the MX pre-filter exists (reference_cold_email_gateway_bounces).
- André on the three-warmth-variant conference follow-up: "we have the same, kind of the same." That was the strongest match in the call.

### Reference Materials
- Source audio: `C:\Users\neuma_p1qrsic\Desktop\Downloads\WhatsApp Audio 2026-11-04 at 16.50.30.mp4`
- Prior checkpoint: Upwork No-Video Proposals (case study PR #1725/#1727)

---

## How to Continue
`/comd_resume platform`, read the transcript, wait for André's Friday message, then help with terms or the first-week plan.

---

## Strategic Feedback

### What Worked Well This Session
- Grounding every talk track in a memory file meant nothing invented reached the call. The one drift (22/85, NeverBounce) came from speaking off the page, so the prep page should put the exact figures on the first line of each point.

### Suggestions
- Put a "say exactly this number" line at the top of each experience point in future call-prep pages. The two misstatements were numbers and a mechanism that were in the page but behind an expand.

### System Health
- One pattern-rule false positive ("next item handback" warn on a KPI answer with no handback). Low cost, noted rather than logged.
- Autonomy: 1 human intervention (mid-turn format directive: compact plus expandable).
