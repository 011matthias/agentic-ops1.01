# Planner board: proposed renames and rescopes

**Not applied.** Renaming other tasks breaks this session's isolation rule ("do
not modify other Planner tasks"), and a write to the MARKETING PLAN board is an
invasive action on a board Dirk reads. This file is the exact text to apply on a go.

Plan `MARKETING PLAN` (`xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`), bucket `Lead Generation`
(`gyfptEwAwUiJLXfd6aMrYWUABZRr`).

## The problem the board has

Two naming errors are baked into six task titles.

**"Tier 1 hottest-5" is a contradiction.** The hottest five accounts are the
bespoke pack Dirk sends himself. Tier 1 is the 19 we sent from his Outlook. They
are disjoint sets, verified: no address appears in both. Calling H5 a subdivision
of Tier 1 implies containment that does not exist.

**"Tier 3 booth/token-network" names two disjoint groups.** The booth/token
network is the 91 people who tapped the fob. Tier 3 is the 33 cold contactable
attendees. Their intersection is empty: every token-tapper is already H5, T1, T2,
GA, stopped, the organiser, a duplicate or the test row. A LinkedIn motion on
"the ~90 booth contacts" would re-invite everyone in H5, T1 and T2.

## Proposed renames

| Task id | Current title | Proposed title |
|---|---|---|
| `OiY1cuBlZEOPf8tBj8pXh2UANEWv` | Rome Tier 1 hottest-5: LinkedIn + Sales Nav | **Rome H5 hottest-five: LinkedIn + Sales Nav** |
| `n4xGTfqJSUqAJLM057LKOmUAEMP1` | Rome Tier 1 hottest-5: email outreach | **Rome H5 hottest-five: email outreach (Dirk sends)** |
| `a7c6yU3_DEOjqnG08LBR22UAL5yv` | Rome Tier 3 booth/token-network: LinkedIn + Sales Nav | **Rome T3 cold leads: LinkedIn + Sales Nav** |
| `NmYYXMHlfE6UDj1aS8PcOmUANkgn` | Rome Tier 3 booth/token-network: email outreach | **Rome T3 cold leads: email outreach** |
| `j_otEGN-pkePGKbDKza0IGUAPCMY` | Rome Tier 1 leads: LinkedIn + Sales Nav | **Rome T1 booth follow-up: LinkedIn + Sales Nav** |
| `E3KqsA7guEKQW5vAk7MQKWUAK5ue` | Rome Tier 2 warm-engaged: LinkedIn + Sales Nav | *(keep)* |
| `44fzQjQ6QkiTyooKxI0u-2UAOwdg` | Rome Tier 2 warm-engaged: email outreach | *(keep)* |
| `WIfpjLJxAEyz2lfDGBCepGUAJScw` | Rome booth/token-network: GDPR consent email | *(keep; it is the only task that should say "booth/token-network")* |

## Proposed descriptions

Each cohort's size below is computed from the rebuilt sheet, and every count is
reproducible with `build-master-v2.py`.

**Rome H5 hottest-five: LinkedIn + Sales Nav** (11 people)
> The 11 addresses in Dirk's bespoke send pack (`dirk-send-pack/README.md`, the
> To: and Cc: lines of the six notes): Zucknick and Landrø at VW, Disdet and
> Cuello at JTI, Herrera La Grotta and Yesil at Roche, Tse at Adidas, Bonizzoni,
> Favalli, Hetesi and Jaszczak at LSEG. Connect from Dirk's own LinkedIn.
> Add all 11 to the "TA Cook Rome 26" Sales Nav list on Matthias's seat.
> The current checklist names 9; the two LSEG cc's are missing.
> Not the same people as T1. The sets are disjoint.

**Rome T3 cold leads: LinkedIn + Sales Nav** (33 people, 29 attended, 4 no-show)
> `Tier = T3` in the rebuilt master. Cold: reachable, attended or invited,
> no personal note from Dirk, did not tap the Brisken Token.
> **None of the 33 has a LinkedIn URL on file.** Every one needs a Sales Nav
> lookup before a connect. Per the standing rule, open the Sales Nav search tab
> and let the user click Save; never automate connects.
> This task is NOT the booth/token network. That group is the GDPR consent task.

**Rome T3 cold leads: email outreach** (33 people)
> Two variants, selected by `t3_branch`: `attended` (29) gets "thanks for coming
> by our booth"; `no_show` (4) gets "we had hoped to catch you". Copy for both is
> in `post-event-sequences.md`. The 4 Shell no-shows fold into Bill Askew's live
> 27 July thread rather than a generic note.

**Rome booth/token-network: GDPR consent email** (74 people)
> `booth_network_send = TRUE`: the 91 fob-encoded token-tappers, minus the stop
> list, minus the event organiser, minus the duplicate registration, minus the
> test row, minus anyone with no email. Membership is a column now, not a
> derivation. Independent of tier: an H5, T1 or T2 person can also be here.

**Rome T1 booth follow-up: LinkedIn + Sales Nav** (19 people)
> The 19 emailed from Dirk's Outlook on 2026-07-08. One correction to the
> existing description: `asako teruki` is **Asako Teruki**, and her LinkedIn slug
> is `asako-tateno-teruki-794531129`, so her surname may be Tateno-Teruki.
> Confirm before the connect note.

## Also stale

`workspace/clients/brisken/TASK-NAMING-STANDARD.md` §2 and §3 still encode the old
model where H5 is a subdivision of Tier 1. Rewriting it is a shared-file change;
it belongs in the same pass as the board renames so the standard and the board
stop disagreeing.
