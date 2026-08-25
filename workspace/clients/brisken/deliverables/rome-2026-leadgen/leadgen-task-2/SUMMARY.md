# Task 2 summary

**Planner task:** "Prepare Zalando TreasuryCentral demo collateral (Lokesh Doggala)"
(id `HsjUNuYE2EaRvqMz2XEp32UAN8ud`, MARKETING PLAN / Lead Generation, second open task in board order).
**Branch:** `leadgen/task-2`. **Worktree:** `../agentic-ops1-leadgen-task-2`.
**Date:** 2026-07-09.

## What I found before starting

A Zalando TreasuryCentral deck already existed, untracked, in
`workspace/clients/brisken/deliverables/lead-generation/rome-2026/call-collateral/`, built 2026-07-09 at
15:47 local, roughly fifteen minutes after the Planner task was created. Same for Sanofi. I did not
create either and did not overwrite them.

The existing deck is good: ten slides, tailored, sourced. Two problems with it:

1. It names **SAP BTP** on slides 5 and 9. An open task on the same Planner board records Dirk's
   directive to "leave SAP BTP out of all demo materials."
2. Slide 8 asserts "**Your** S/4HANA migration is the moment these feeds get decided." Nothing in the
   repo says Zalando has a migration in flight.

So the deck work was not redone; it was corrected, and the rest of the task (which was untouched) was
built.

## What I created

| File | What it is |
|---|---|
| `deck/brisken-treasurycentral-zalando.pdf` | The deck, BTP removed, migration claim softened. 10 slides, send-ready |
| `deck/brisken-treasurycentral-zalando.pptx` | Editable source |
| `deck/build/build-treasurycentral-zalando.js` | Forked build script carrying the three edits |
| `zalando-call-brief.md` | Who is on the call, what we know and do not, the five open questions |
| `zalando-demo-flow.md` | 40-minute discovery-led run of show, branched on what they say |
| `collateral-pack-and-delivery.md` | Pack manifest, what is deliberately excluded, the four manual steps, an unsent note to Dirk |
| `shared-file-proposals.md` | Four changes to files outside this task directory, with exact diffs. Not applied |
| `notes-for-other-tasks.md` | Findings belonging to four other Planner tasks |

Nothing outside `output/leadgen-task-2/` was created, modified, moved or deleted. No Planner task was
completed, commented on or edited.

## The three findings that matter

**Lokesh never had a booth conversation.** He tapped the Brisken token at 15:31 UTC on 2026-06-24 and
appears nowhere in `booth-meeting-notes.md`. He replied to the generic network email of 2026-07-08, not
to a bespoke note. A call that opens with "picking up where we left off" would be opening on a fiction.
The demo flow is built around that.

**Maria Moeller is an unknown, and Dirk called her the lead.** No booth registration, no CRM record, no
prior contact anywhere in our files. Lokesh brought her in. She is the person the second half of the
call is aimed at, and we know nothing about her.

**Three of the four attachable product decks breach the BTP directive** (Market Data Hub 2 mentions,
Digital Co-Worker 2, MDH Commodities 1; Smart Trading is clean). The two most likely Zalando follow-up
attachments are among them. The TreasuryCentral deck goes alone until that is fixed.

## Verification performed

- Rendered `deck/brisken-treasurycentral-zalando.pptx` to PDF through PowerPoint, extracted the text of
  all 10 slides: **0 occurrences of "BTP"** (the shared copy has 2), 0 em-dashes, and all three edited
  strings present in the output.
- Counted BTP mentions in every PDF in `dirk-send-pack/` by text extraction, not by reading the source.
- Zalando CRM status read from `context/zoho-crm.json`: account `ZALANDO`, status
  `Lead - Cloud Subscription`, owner Dirk Neumann. Confirmed it is a lead and not a customer, per the
  `Account_Status` convention.
- Lokesh's absence from `booth-meeting-notes.md` confirmed by case-insensitive search for "doggala"
  across `workspace/clients/brisken/`.

## What happened after this task was marked done

The Planner task was completed on 2026-07-09 at 15:59 UTC (checklist items "Deliver collateral to Dirk"
and "Confirm booking + attendees" left unticked, because neither had happened).

Separately, at 16:27 UTC, Matthias sent Dirk "TreasuryCentral decks for Sanofi and Zalando", pointing at
a new Client Collateral folder in SharePoint. That message is not the draft written here; the draft was
never sent and has been deleted. The sent text is transcribed verbatim in `context/comms-log.md`.

**The delivered decks were the BTP versions, and have since been replaced.** The SharePoint Zalando PDF
was 233,228 bytes, byte-identical to the `call-collateral/` render carrying 2 BTP hits; Sanofi (234,172)
had the same defect. On the owner's direction both were rebuilt BTP-free from the corrected source and
the four SharePoint files were overwritten at 18:25 UTC. Verified byte-exact: Sanofi PDF now 234,137,
Zalando 234,466, both 10 slides with 0 BTP hits. Details in `shared-file-proposals.md`.

## Still requires a manual step

1. **Read Lokesh's reply.** It sits in Dirk's mailbox and nowhere in our files. It is the only record of
   what he asked for.
2. **Book the call.** Dirk's forward says he will book it end of next week or later. Paste-ready invite
   subject, body and the three attendee addresses are in `collateral-pack-and-delivery.md`. No calendar
   invite or Outlook draft was created: that is a state change in a live mailbox and needs an explicit go.
3. **Decide whether Dirk is told the decks were corrected.** The folder link he was sent still resolves
   and the contents are now right. He has not been told.
4. **Fix the three module decks** still carrying BTP, under the open "Exclude BTP from all demos" task.
   Two of them are the likely Zalando follow-up attachments.

## Open questions

- Lokesh's actual job title. Three of our own sources give three different answers, and the deck avoids
  the problem by omitting it.
- What Maria Moeller owns.
- Whether Zalando is on ECC or S/4HANA in 2026. The newest source found is a consenso readiness check
  published 2018-09-20, which put treasury, cash and liquidity management in scope, described their cash
  management as "a modified SAP solution, strongly tailored to Zalando's requirements", and recommended
  greenfield. Eight years stale; usable as a question, not as a claim.
- Whether Adela Dolezalova's firm (Trillion, per her booth registration, not Zalando) is an incumbent
  systems integrator on the account.
