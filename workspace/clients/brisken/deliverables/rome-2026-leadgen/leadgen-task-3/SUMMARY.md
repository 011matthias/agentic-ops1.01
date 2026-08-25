# Task 3 summary

**Task:** Prepare Sanofi TreasuryCentral demo collateral (Ian Haegemans)
**Planner id:** `hLqRXF37_U6aV08Qd4U6zmUAMo0F`, MARKETING PLAN / Lead Generation, 3rd open
card from the top of the Board view
**Branch:** `leadgen/task-3` (worktree at `agentic-ops1-leadgen-task-3`)
**Date:** 2026-07-09

## The finding that shaped the task

The Sanofi deck already existed. A session earlier the same day built it, uploaded it to
SharePoint, and emailed Dirk the link at 16:27.

That deck names **SAP BTP** on slides 5 and 9. Dirk's Planner task *"Exclude BTP from all
demos"* was opened 2026-07-08 20:55, a day before the deck was built. The directive reads:
"leave SAP BTP (Business Technology Platform) out of all demo materials." The collateral now
sitting in Dirk's inbox contradicts it, and the same defect is in the Zalando deck beside it.

So task 3 is not "build a deck". It is: repair the deck, supply the parts of the checklist
nobody had done, and hand Dirk a correction he can send.

## What was created

Everything is under `output/leadgen-task-3/`. Nothing outside it was modified.

| File | What it is |
|---|---|
| `collateral-pack/brisken-treasurycentral-sanofi.pptx` / `.pdf` | the 10-slide deck, rebuilt with zero BTP references |
| `collateral-pack/brisken-treasurycentral-onepager.pdf` | the leave-behind, rebuilt with the `SAP BTP` trust chip removed. This was an open next-step from the prior checkpoint, never delivered |
| `collateral-pack/brisken-smart-trading.pdf` | optional annex, verified already BTP-free |
| `collateral-pack/README.md` | pack manifest, provenance, the two open items on the deck |
| `call-prep-brief.md` | sourced research on Ian and Sanofi treasury, with a confidence column and an explicit not-found list |
| `demo-flow.md` | run of show for the Friday call, discovery questions, objections, a do-not-say list |
| `deliver-to-dirk.md` | exact SharePoint steps plus a paste-ready note to Dirk |
| `shared-file-proposals.md` | the BTP edits to shared build scripts, proposed not applied |
| `notes-for-other-tasks.md` | what tasks 2 and 18 need to know |
| `build/` | the three scripts that regenerate the pack |

## Checklist status

| Planner checklist item | State |
|---|---|
| Confirm scope of collateral + Friday 16:00 slot with Dirk | **Needs Dirk.** Four open questions collected in `deliver-to-dirk.md` step 3 |
| Tailor TreasuryCentral demo flow to Sanofi treasury / GPO context | **Done.** `demo-flow.md`. The deck was tailored; the flow did not exist |
| Assemble deck + one-pager pack from dirk-send-pack + product decks | **Done.** `collateral-pack/`, BTP-clean, with the MDH and Digital Co-Worker decks deliberately excluded and the reason recorded |
| Deliver collateral to Dirk before the call | **Done.** The 16:27 email linked the SharePoint folder rather than attaching files, so the in-place fix repaired what the link serves. SharePoint `TimeLastModified` 18:25:24Z, 38s after the rebuild; both PDFs verify at zero BTP. The one-pager was not uploaded |

## What the research changed

Sanofi went live on SAP S/4HANA Treasury in **September 2020** and has run a Treasury Core
Model since 2017 that redesigned 40+ treasury processes onto it. The migration-timing angle,
which is correct for Zalando, would have told Ian we had not looked.

Better, and sourced: Sanofi's own public posting for his seat says it exists to monitor
"process efficiencies, deviations, and process adherence" via KPI dashboards. And Ian posted
publicly, three months ago, that Sanofi treasury is "building out a data foundation to become
AI-ready". The pitch writes itself from there: the process is already standard, the data
feeding it is not, and an adherence KPI built on hand-assembled inputs measures the
assembling. Full sourcing and confidence levels in `call-prep-brief.md`.

The deck's Sanofi proof line was written before any of this and lands on it anyway. It stays.

## Requires a manual step

Both the delivery and the deck's BTP fix closed on 2026-07-09 while this task was running.

1. **Delivery: done.** The 16:27 email linked the SharePoint folder rather than attaching
   files, so repairing the files in place repaired the link. A parallel session rebuilt and
   re-uploaded both decks; SharePoint reports `TimeLastModified` 18:25:24Z and both PDFs
   verify at zero BTP. The Zalando deck is fixed too.
2. **The one-pager was never uploaded.** `collateral-pack/brisken-treasurycentral-onepager.pdf`
   is BTP-clean and sits only in this task directory. The shared `sap-assets/` copy still
   carries the trust chip.
3. **The remaining BTP sources are still dirty**, and belong to the "Exclude BTP from all
   demos" task: `build-mdh.js` (2 refs), `build-digital-coworker.js` (2),
   `build-mdh-commodities.js` (1), `gen_onepagers.py` (5). Task 3 stood down rather than
   race the session actively editing that file set.
4. **Dirk's five decisions** are Planner task `VeH5a5bwf0Ky5jns-nt8bGUAMA-a`, assigned to him.

## Open questions for Dirk

1. Slide 8 names **Evonik and RWZ** as OnePilot customers. Still unsigned-off, flagged in the
   prior checkpoint and unresolved.
2. Slide 10 promises to "show TreasuryCentral live on your SAP data". Is there a live
   environment for Friday, or is this deck-only? `demo-flow.md` supplies a verbal close that
   does not depend on the answer.
3. Call length. The run of show assumes 45 minutes.
4. Is anyone joining from Sanofi besides Ian.
5. The `brisken-onepilot-onepager.pdf` builds its whole eyebrow on "The AI layer, on SAP BTP".
   Removing BTP there is a positioning decision, not an edit.

## Verification performed

- Rendered the deck to PDF and extracted its text: **0** `\bBTP\b` matches, HANA retained,
  "Sanofi" and "Haegemans" present, zero Zalando leakage, 10 slides.
- Rendered the one-pager: **0** BTP, still single-page, and the Co-Innovation Partner, SAP
  Store, ISO 27001 and SOC 1 chips all survive.
- Enumerated BTP across every pack candidate and every build source before choosing what to
  include, rather than assuming the product decks were clean. Three of five were not.
- Resolved the task id against the live Planner board twice: `orderHint` ordering from Graph,
  then a screenshot of the rendered board to confirm positions 1, 2 and the tail matched.
- Confirmed no file outside `output/leadgen-task-3/` was created or modified.

## Where I could be wrong

The claim that the 16:27 email carried the BTP deck rests on the prior session's checkpoint
saying it was sent and verified in Sent Items, plus the BTP references I measured in the
local files it says were uploaded. I did not open Dirk's mailbox or the SharePoint folder to
confirm the bytes on the far end match the bytes here.

**Corrected 2026-07-09.** An earlier version of this summary said Ian's title was not
independently confirmed and that only Dirk's forward sourced him. Both were wrong. He typed
his own title into the Brisken booth token registration on 2026-06-24 (`fob_encoded: true`),
and his master-sheet row, Sanofi's Zoho account and four earlier Sanofi trade-show contacts
were all on disk the whole time.

The error was mechanical and worth naming: I searched with ripgrep, which honours
`.gitignore`, over a repo where the client's entire `context/` tree is gitignored. Six files
matched. A plain `grep` found twenty-three. The tool's default quietly became the boundary of
what I believed existed, and I wrote that belief into a client-facing brief as fact.

What the records changed: Sanofi is a Dirk-owned CRM **lead** (`Lead - Cloud Subscription`),
not a client, and `Account_Type` cannot be used to tell the difference (of 120 accounts
reading `Customer`, 49 are leads and 39 are active clients). Isabelle Badoux is a genuine
Dirk-owned CRM contact, not a thin Sales Nav name, though still nothing connects her to this
call.

Still standing: his LinkedIn preview says Antwerp while Dirk's forward says Brussels, where
the in-house bank is registered. Not worth raising.
