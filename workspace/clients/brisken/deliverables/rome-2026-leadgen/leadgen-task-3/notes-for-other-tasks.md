# Notes for other tasks (from task 3)

Found while doing task 3. Not acted on, per the no-cross-task rule.

## For "Exclude BTP from all demos" (task id `mJrjdoY1yUKp0gNxDld7LWUAAL_e`)

**Status at 21:07 on 2026-07-09: mostly done, by a session running in parallel.** All four
deck build scripts now read zero BTP (`build-treasurycentral` at 20:23, the rest by 20:53),
both prospect decks were rebuilt and re-uploaded to SharePoint, and `decks/` plus
`dirk-send-pack/` were re-synced. The four attachable PDFs extract to zero BTP.

**What is left: `gen_onepagers.py`, still 5 references, untouched since 2026-07-08.** The
six rendered one-pagers in `sap-assets/` are all still dirty. Exact diffs, verified against
the helper's own conventions, are in `shared-file-proposals.md`.

**Owner correction 2026-07-09, and it unblocks the last piece:** nothing replaces BTP. It is
omitted because it does not sell a treasurer, and it can be named in conversation if a client
presses. An earlier version of these notes said the OnePilot one-pager needed a positioning
decision from Dirk before its BTP could come out. It does not. It is a mechanical edit, and
it has been removed from Dirk's task.

The historical detail below is kept because it records what was in Dirk's hands and when.

Task 3 verified the full inventory on 2026-07-09. Counts are `grep -ci btp` on sources and
`pypdf` extracted-text `\bBTP\b` matches on rendered PDFs. Exact per-file numbers, the two
canonical string edits, and the one-line `TRUST` chip fix are in
`shared-file-proposals.md`.

The shape of it:

- Four deck build scripts carry BTP at the same two slide positions (`build-treasurycentral`,
  `build-mdh`, `build-digital-coworker`, `build-mdh-commodities`). `build-smart-trading` is
  already clean. One edit pattern clears all four.
- One list entry in `gen_onepagers.py` line 125 puts an `SAP BTP` trust chip on **five**
  one-pagers at once. Removing that entry clears all five.
- **`brisken-onepilot-onepager.pdf` is different.** It has five BTP references and they are
  load-bearing: the eyebrow reads "The AI layer, on SAP BTP", and BTP is the architecture
  target plus two capability lines. Deleting the word leaves the page with no answer to
  "what does it run on". That one needs Dirk's decision on what replaces it, not a
  find-and-replace.
- Task 3 already proved the two deck edits and the chip removal render clean, on its own
  task-local copies. The rendered PDFs verify at zero BTP with HANA, the co-innovation
  partner claim, the SAP Store / ISO 27001 / SOC 1 chips and single-page layout intact.

**Time-sensitive:** the Sanofi and Zalando decks were uploaded to SharePoint and the link
emailed to Dirk at 16:27 on 2026-07-09, both containing BTP. The directive predates that
send by a day.

## For "Prepare Zalando TreasuryCentral demo collateral (Lokesh Doggala)" (task 2, `HsjUNuYE2EaRvqMz2XEp32UAN8ud`)

- The Zalando deck has the same two BTP references as the Sanofi one, from the same shared
  build script. Task 3 did not touch it. The fix is `shared-file-proposals.md` proposal 1,
  which repairs both prospects in one change: `node build-treasurycentral.js zalando`, then
  re-export.
- The Zalando `.pptx` and `.pdf` currently on SharePoint in `2026_PPTX/Client Collateral`
  both carry BTP and were sent to Dirk in the same 16:27 email.
- The one-pager companion that task 3 built is prospect-neutral. The same
  `build-onepager-btp-clean.py` produces it for the Zalando pack with no changes.
- The Zalando proof line leans on S/4HANA migration timing, which is correct for Zalando and
  actively wrong for Sanofi. Worth keeping the two decks' proof lines from converging.

## Rome event master sheet, changed 2026-07-09 on owner directive

CRM contacts are out of the Rome event sheet. The rule: the sheet holds people invited to
(or present at) the event; invited leads who did not attend may stay, provided
`attendee_type` and `no_show` classify them that way. Anyone never invited comes out.

Eight rows removed, 298 to 290. They are preserved with all 31 columns in
`event-admin/rome2026-removed-not-invited-2026-07-09.xlsx`, and a pre-edit backup sits
beside the sheet. A new Planner task, **"Build the CRM contacts master sheet"**
(`lBxskesYl06SYecMDyhzf2UAHVTt`), owns the follow-up.

Removed: 4 Shell contacts (`Event campaign inbound`), Isabelle Badoux (`Sales Nav research
add`), Adela Dolezalova + Maria Moeller (`Referral / loop-in`), Akash Gupta of Maersk
(`Email lead (not attending)`). Gupta was the non-obvious one: his `attendee_type` reads
"SAP customer" but he was never on the TAC roster.

Kept: 11 invited no-shows, all `TAC only` and all classified. All 91 `fob_encoded` booth
rows untouched, Ian Haegemans among them.

**This matters for task 2, and the mail thread resolves it.** Removing the Zalando "Adela
Dolezalova" row resolved a duplicate. An Adela Dolezalova was already in the sheet at row 253
as an **SAP analyst at Trillion Consulting** who attended the booth (`source: Both`,
`fob_encoded`).

Lokesh's reply, read from Dirk's mailbox 2026-07-09, addresses her as
`adela.dolezalova.external@zalando.de`. The `.external` in the address says she is a
contractor at Zalando, not an employee, which squares with the booth row: she is a Trillion
Consulting analyst working externally for Zalando. One person, two hats. The row 253 record
is the right one; the added row invented a Zalando SE employment that does not exist.

Lokesh's verbatim ask: "can you add my colleague @Adela Dolezalova and my lead @Maria Moeller
to the call so they can see it too?" Maria Moeller is `maria.moeller@zalando.de`, no
`.external`, so she is staff.

Neither of them has anything to do with the Sanofi call. Ian named nobody.

## The Sales Nav worklist mislabels customers, and it feeds task 1

`context/lead-generation/targeting/sales-nav-add-list-rome2026.md` has a `Track` column
reading `customer` for Accenture, Norsk Hydro, NYK and Sanofi. None of them are Brisken
clients. Accenture is a partner; the rest are leads.

The file was generated 2026-06-29 from the master sheet's `brisken_customer` field. Dirk's
"Customer flags wrong, 3rd time" correction landed 2026-07-08 and rebuilt that field on the
CRM `Account_Status`. The worklist was never regenerated, so it still carries the old error.

Anyone running LinkedIn outreach off that list could greet a prospect as an existing
customer. Regenerating it is a checklist item on the new CRM-sheet task.

The underlying rule, verified against the cache: of the 120 accounts whose `Account_Type` is
"Customer", 49 are leads and only 39 are active clients. `Account_Type` separates nothing.
Client means `Account_Status` of `Active - Cloud Subscription` or `Active - Consulting`.

## For whoever owns the Brisken comms log

The 2026-07-09 checkpoint's first next-step is still open: neither the Sanofi nor the
Zalando Tier 1 reply is logged in `workspace/clients/brisken/context/comms-log.md`. Ripgrep
finds no "Haegemans" anywhere in that file.

The consequence showed up immediately in task 3: the only first-party record of Ian
Haegemans, his title, his email and the Friday 16:00 commitment is the description field of
a Planner task. Everything else about him had to come from public web research. A booth
follow-up that converts to a call and never reaches the comms log is a lead whose history
lives in Microsoft Planner.

## For "Gather customer reviews on the SAP Store and Discovery Center listings" and the SAP profile tasks

Not investigated. Noting only that `sap-assets/` one-pagers are shared by the SAP listing
tasks and the demo packs, so a BTP edit there has blast radius into whatever is published on
the SAP Store. Coordinate before editing `gen_onepagers.py`.
