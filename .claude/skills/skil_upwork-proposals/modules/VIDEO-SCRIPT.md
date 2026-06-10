# Video Walkthrough Blueprint

The proposal video is a Loom **content guide**, not a verbatim script. You
speak from bullet points in your own words. A word-for-word `SAY:` script
makes you sound like you are reading; an outline you talk from sounds like a
person. (Owner directive 2026-06-09; this blueprint replaces the older
verbatim 5-beat script.)

## Why video dominates

Text is claims. Video is evidence. A 2 to 3 minute walkthrough proves clarity
of thought, communication, and real understanding of THEIR problem in a way no
written proposal matches.

## The arc: build a diagnosis that lands on an easy question

The whole video is one movement: collapse their several symptoms into ONE root
cause or insight, make it concrete on screen, build the evidence beat by beat,
and close on an easy question they can answer in a single line.

Three principles carry the arc:

1. **Reframe to one cause.** Open by collapsing the noise to a single root.
   "Two symptoms, but they are usually one cause, not two separate problems."
   This is the move that proves you understand it better than they described it.
2. **Likely-cause honesty.** Whenever you have not logged into their system,
   frame findings as the *likely* cause and say what you reasoned from (public
   DNS, the job post, the visible stack). Reasoning from the outside, named as
   such, builds trust; overclaiming certainty you do not have breaks it.
3. **Close on a question, not a pitch.** End on a one-line question they can
   answer off the top of their head. It lowers the barrier to reply and hands
   you the number or detail you need to scope. "Roughly how many leads a month
   are you seeing versus expecting?" beats "let's hop on a call."

## The beat skeleton (timestamp it, target ~2 minutes)

Write the guide as `##` sections, one per beat, each a few bullets of what that
beat must LAND plus a rough time budget (`## 0:35 ...`). Two variants share the
same spine; pick by whether you are diagnosing a broken thing or scoping a new
build.

### Variant A: Diagnosis (something is broken or underperforming)

1. **0:00 Open: name it, reframe to one cause.** State the symptoms, collapse
   them to a single root cause, reassure it is fixable, and say you can already
   see the likely culprit.
2. **0:15 Walk the pipeline.** Trace their actual flow out loud on screen
   (source, the handoff, the destination). Point at where a lead, record, or
   dollar can leak.
3. **0:35 The cause points, named and glossed.** Name each likely cause. Gloss
   any spoken abbreviation once, inline ("SPF, DKIM and DMARC, the three DNS
   records that prove a domain is allowed to send mail"). Tie each cause back
   to the symptom they actually feel.
4. **1:20 Why they connect, and how you would confirm.** Show the causes share
   a fix, then state the concrete first thing you would check (pull the DNS,
   the run history, the logs) and that it yields the real number.
5. **1:40 Close: the fix in one line, then the easy question.** Compress the
   fix to one sentence, name one comparable thing you have shipped, and end on
   a one-line question that quantifies their pain.

### Variant B: Build (they want something new built)

Same spine, retargeted:

1. Open: reframe the request to the real underlying need.
2. Walk the proposed pipeline or a concrete artifact / demo on screen.
3. Name the hard parts and how you handle each (the edge cases, the unreliable
   bits), glossed.
4. How you would confirm scope before building.
5. Close on an easy scoping question ("what is the one workflow eating the most
   time right now?").

## Terms-to-gloss block (required)

End every guide with a short `## Terms to gloss if you say them on camera`
list: each spoken abbreviation or jargon term paired with a 3 to 8 word plain
gloss. It is a silent teleprompter aid so any term lands in the ear the first
time you say it. Universal terms (AI, API, URL, CRM, and the rest of the
common set) need no gloss. See `rule_human_communication.md` section 7.

## Recording rules

- Screen plus camera bubble. Start on the work; no "hey, my name is" intro
  beyond one line.
- 2 to 3 minutes. Talk to the screen while pointing at the form, the inbox,
  the DNS block, or the workflow.
- Speak linearly; each beat builds on the last.
- Close on the question, never "hire me".
- The opening is about THEIR problem. Never say why the job interests you
  ("I thought it was a great opportunity") in the first beat; your interest
  is implied by the video existing.
- Pause silently instead of saying "uhm". Loom transcribes every filler word
  and prospects read the transcript panel as much as they watch.
- Narrate demos at the principle level (intake, parallel provisioning, gate,
  notify), never node-by-node field lists. Per-node narration is the spoken
  form of slop and is what pushes a video past 3:30.
- Claim only what the screen shows. If the demo is one workflow, do not
  assert it proves a system-level property (isolation, scale); show the
  property or scope the claim down.
- Record the close as ONE take, one ending. No stitched closes, no "maybe we
  can get together". (Source: 2026-06-10 review of three recorded Looms;
  video 2 ended with three endings glued together.)

## Pre-send checklist (per video)

1. Generate the Loom transcript and chapters; a video without a transcript
   cannot be skimmed by the prospect's team.
2. Skim the transcript for filler runs, retake seams ("Would you?",
   orphaned half-sentences), and word slips; re-record the broken beat.
3. Confirm the Loom account display name matches the name you say on camera.
4. Title the Loom after their problem, not ours.

## Format and validation

- File: `workspace/proposals/{slug}/video-script.md`, `##` sections, no `SAY:`
  lines, no `>>` stage directions, no LOOM NOTES block.
- Zero em dashes.
- `tools/validate-proposal.py` detects the guide by the ABSENCE of `SAY:`/`>>`
  markers and checks zero em dashes, a sectioned structure, and the
  terms-to-gloss block. Legacy verbatim scripts still validate under the old
  rules.

## Reference exemplars

- `workspace/proposals/volabyg-lead-automation/video-script.md` is the
  canonical Variant A likely-cause walkthrough.
- `workspace/proposals/n8n-multi-client-ops/video-script.md` adapts the spine
  to an operator application (no single "broken thing" to diagnose).

Adapt the spine, not the specifics.
