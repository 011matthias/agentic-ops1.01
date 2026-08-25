# The Zalando pack, and the steps to get it to Dirk

## What is in the pack

| File | What it is | Status |
|---|---|---|
| `deck/brisken-treasurycentral-zalando.pdf` | The 10-slide TreasuryCentral deck, tailored to Zalando, send-ready | Built and verified 2026-07-09 |
| `deck/brisken-treasurycentral-zalando.pptx` | Editable source for the same deck | Built 2026-07-09 |
| `deck/build/build-treasurycentral-zalando.js` | The build script that produced both, so the deck can be regenerated | Forked from `.scratch/deckgen/build-treasurycentral.js` |
| `zalando-call-brief.md` | Who is on the call, what we know, what we do not | This session |
| `zalando-demo-flow.md` | The 40-minute run of show | This session |

The deck in `deck/` was the first BTP-free build, made while the shared copy in
`workspace/clients/brisken/deliverables/lead-generation/rome-2026/call-collateral/` still named SAP BTP on
two slides. On 2026-07-09 the owner directed the fix: the shared source was corrected, both prospects were
rebuilt, and the repo and SharePoint copies were replaced. The deck here and the shared copy now carry the
same content; they differ only by render, since each PDF was produced in a separate PowerPoint pass. See
`shared-file-proposals.md`.

## What is deliberately not in the pack

**The Rome one-pager.** `brisken-rome-2026-onepager.pdf` is event collateral: it says "Booth #2" and
points at `bookings.brisken.com/#/tacrome2026`, a booking link for a conference that has already
happened. Sending it to Zalando three weeks after Rome reads as a mailmerge. The 10-slide deck is the
leave-behind.

**A second one-pager, newly written.** The deck already carries the problem, the three engines, the
architecture, the governance and the proof, on ten pages. A one-pager restating them would add a file
without adding an argument.

**The product decks, for now.** The intent was to attach one engine deck after discovery picks the
angle. Three of the four cannot go out as they stand:

| Deck | BTP mentions | Attachable today |
|---|---|---|
| `brisken-smart-trading.pdf` | 0 | Yes |
| `brisken-mdh-commodities.pdf` | 1 | No |
| `brisken-market-data-hub.pdf` | 2 | No |
| `brisken-digital-co-worker.pdf` | 2 | No |

(Counts from extracting the text of each PDF in `dirk-send-pack/` on 2026-07-09.) Market Data Hub and
Digital Co-Worker are the two most likely follow-up attachments for Zalando, and both currently breach
the directive. Fixing them belongs to the open Planner task "Exclude BTP from all demos" and is logged
in `notes-for-other-tasks.md`. Until then, the TreasuryCentral deck goes alone.

## The manual steps

Nothing here needs a portal. Four steps, all in Dirk's mailbox and calendar, none of which we should
touch on his behalf.

**1. Read Lokesh's reply before anything else.** It is in Dirk's mailbox and not in our files. It is
the only record of what he actually asked for, and it decides whether the demo flow's discovery block
can be shortened. Everything below assumes it says nothing more specific than "interested, let's talk".

**2. Book the call.** Dirk sends the invite; his forward says "I will book end of next week or later",
so the slot is his to pick. Attendees, all three from his forward:

```
lokesh.doggala@zalando.de
adela.dolezalova.external@zalando.de
maria.moeller@zalando.de
```

Suggested invite subject and body, 40 minutes:

> **Subject:** Brisken and Zalando: TreasuryCentral on live SAP data
>
> Lokesh, Maria, Adela,
>
> Thanks for picking this up after Rome. I have kept this to forty minutes: a short conversation about
> how treasury data reaches SAP at Zalando today, then a live look at TreasuryCentral on the part that
> matters most to you.
>
> If there is someone else who owns the feeds, they are welcome to join.
>
> Dirk

**3. Attach the deck to the invite, or send it the morning of the call.**
`deck/brisken-treasurycentral-zalando.pdf`. Sending it ahead of time is the better move here: Maria has
not met us, and the deck does the introducing.

**4. After the call, update the CRM.** The `ZALANDO` account already exists in Zoho, status
`Lead - Cloud Subscription`, owned by Dirk. Lokesh, Adela and Maria are not on it yet. The open Planner
task "Upload the Rome contacts to the CRM once all three tiers are contacted" covers the bulk load;
this account is worth doing by hand first, because it is the only Rome lead with a booked call and a
named decision maker.

## The note to Dirk: already sent, not ours

Superseded. On 2026-07-09 at 16:27 UTC Matthias sent Dirk "TreasuryCentral decks for Sanofi and
Zalando", pointing him at a new Client Collateral folder in SharePoint rather than attaching anything.
The draft that used to live here was never sent and has been deleted; the message that did go out is
transcribed verbatim in `context/comms-log.md`.

**What was delivered carries the BTP defect.** The SharePoint
`Brisken - TreasuryCentral - Zalando 2026.pdf` is 233,228 bytes, byte-identical to the `call-collateral/`
render that names SAP BTP on slides 5 and 9. The clean rebuild in `deck/` (245,502 bytes, 0 BTP hits)
was never uploaded. Sanofi has the same problem and no clean rebuild at all. Replacing the two
SharePoint files writes into Brisken's live tenant and waits on an explicit go.
