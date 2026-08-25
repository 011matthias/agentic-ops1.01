# Deliver the Sanofi collateral to Dirk

## DELIVERED 2026-07-09. This file is now a record, not a plan.

No re-send was needed. The 16:27 email linked the SharePoint `Client Collateral` folder
rather than attaching the deck, so fixing the files in place fixed what Dirk's link serves.

A parallel session repaired `build-treasurycentral.js` at 20:23 local, rebuilt both prospect
decks at 20:24, and re-uploaded them. Verified read-only against the SharePoint REST API:
the four files carry `TimeLastModified` of `2026-07-09T18:25:24Z` and later, 38 seconds
after the local rebuild. Both rendered PDFs extract zero `\bBTP\b` matches. The Zalando deck
is fixed too.

Residual: the folder holds four files and no one-pager. The BTP-clean
`brisken-treasurycentral-onepager.pdf` in `collateral-pack/` has not been uploaded. The
shared `sap-assets/` copy still carries the `SAP BTP` trust chip.

What Dirk still owes is now Planner task **"Sign off the open items before the Sanofi call"**
(`VeH5a5bwf0Ky5jns-nt8bGUAMA-a`), assigned to him.

The steps below record how the delivery was specified, and remain the procedure if the
one-pager is added later.

## What changed since the 16:27 email

The 2026-07-09 checkpoint records that the Sanofi and Zalando decks were uploaded to the
SharePoint `Client Collateral` folder and the link was emailed to Dirk, verified in Sent
Items at 16:27. That deck contains SAP BTP on slides 5 and 9.

Dirk's Planner task **"Exclude BTP from all demos"** was created 2026-07-08 20:55, the day
before. So the collateral currently in his hands contradicts a directive that was already
open when it was built. Nobody caught it because the two tasks were worked separately.

This delivery replaces that deck and adds the one-pager companion, which the checkpoint had
left as an open next step.

## Step 1: replace the files on SharePoint

Target folder, unchanged from the prior upload:

```
MARKETING/Shared Documents/20_Assets/BRISKEN PRESENTATIONS/
  OnePilot - Cloud Solutions Presentations/2026_PPTX/Client Collateral
```

Upload these three, overwriting the two same-named files already there:

| Local file | Action on SharePoint |
|---|---|
| `collateral-pack/brisken-treasurycentral-sanofi.pdf` | overwrite |
| `collateral-pack/brisken-treasurycentral-sanofi.pptx` | overwrite |
| `collateral-pack/brisken-treasurycentral-onepager.pdf` | new file |

The existing tool does this: `.scratch/cdp-sp-collateral.py` (list / mkdir / upload / nav),
driven through the CDP-attached Edge on port 9222 that is already signed in as
Matthias.Silva.

It must be invoked with `MSYS_NO_PATHCONV=1`, because Git Bash rewrites the leading-slash
`/sites/...` argument into a Windows path and the upload fails with a confusing error. That
cost about five calls in the prior session.

```bash
MSYS_NO_PATHCONV=1 uv run --script .scratch/cdp-sp-collateral.py upload \
  "/sites/MARKETING/Shared Documents/20_Assets/BRISKEN PRESENTATIONS/OnePilot - Cloud Solutions Presentations/2026_PPTX/Client Collateral" \
  output/leadgen-task-3/collateral-pack/brisken-treasurycentral-sanofi.pdf
```

Verify by re-listing the folder and checking the modified timestamps, not by trusting the
upload's exit code.

**The Zalando deck in that same folder still contains BTP.** It is task 2's file and task
18's directive. It is not touched here. Flagged in `notes-for-other-tasks.md`.

## Step 2: the note to Dirk

Send from Matthias to Dirk, same thread as the 16:27 email if possible so the link context
carries. Paste-ready, no edits needed except the folder link.

> **Subject:** Sanofi collateral: rebuilt without BTP, one-pager added
>
> Dirk,
>
> The Sanofi deck I sent this afternoon still had SAP BTP on two slides, which cuts against
> your directive to keep BTP out of the demo material. I have rebuilt it without BTP and
> added the TreasuryCentral one-pager as the leave-behind. Both are in the Client Collateral
> folder now, replacing the earlier deck.
>
> Two things I would rather you decided than have me assume. Slide 8 names Evonik and RWZ as
> OnePilot customers, and that is your call before it goes in front of Sanofi. Slide 10 says
> we will show TreasuryCentral live on their own SAP data, which reads well in an email
> before the call but promises a live run once you are in the room. I have suggested a
> verbal close instead, in the notes.
>
> I also put together a run of show and a short prep brief on Ian and Sanofi's treasury
> setup. Five minutes on it before Friday would pay for itself: they finished their S/4HANA
> treasury migration back in 2020, so the migration angle we use with Zalando would land
> badly here.
>
> Matthias

## Step 3: what Dirk still owes an answer on

Carry these into the Planner task comment rather than letting them sit in mail.

1. Evonik and RWZ named on the proof slide: sign off, or replace the slide.
2. Is there a live TreasuryCentral environment to demo, or is Friday deck-only?
3. Call length, so the run of show can be cut to fit.
4. Anyone else joining from Sanofi.

## Not done, deliberately

- No file uploaded to SharePoint.
- No mail sent, and no Outlook draft created. Creating a draft in Dirk's mailbox by COM is
  still a write into a live mailbox.
- The Planner task is not marked complete and its checklist is untouched, per the task-3
  isolation rules.
