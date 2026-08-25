# Runbook: add Tier 2 to the "TA Cook Rome 26" Sales Nav list

**Seat:** Matthias's Sales Navigator seat (not Dirk's LinkedIn).
**List:** "TA Cook Rome 26", created by Dirk.
**Time:** about 15 minutes in three paced batches.
**Nothing here has been executed.** No lead has been added and no tab has been opened.

## Ground rules

- **Open each lead in Sales Navigator, not regular LinkedIn.** A `linkedin.com/in/...` profile forces a detour to reach "Save to list". A Sales Nav people-search result carries the Save action directly.
- **Do not automate the seat.** The owner ruled out driving Brisken's Sales Nav aggressively; a burst of scripted searches is the exact pattern LinkedIn bans for. Open a batch, save by hand, then the next batch.
- **Duplicates are harmless.** Sales Nav marks anyone already in the list as saved. Four of the eighteen (Jellonek, Brueckner, Mehlkopf, Jones) were on the earlier `sales-nav-add-list-rome2026.md` roster and may already be in.
- **Confirm identity before saving.** Fourteen of these have no LinkedIn URL on the master sheet. Match against the `job_title` column in `tier2-roster.csv`. On a name collision, skip and note it rather than saving the wrong person.

## Batch 1 (six)

```
https://www.linkedin.com/sales/search/people?keywords=Christos%20Georgiou%20BSTDB
https://www.linkedin.com/sales/search/people?keywords=Victoria%20Boclinca%20Black%20Sea%20Trade%20and%20Development%20Bank
https://www.linkedin.com/sales/search/people?keywords=Sergey%20Timeshov%20BSTDB
https://www.linkedin.com/sales/search/people?keywords=Uffe%20Teisner-Kjaer%20Grundfos
https://www.linkedin.com/sales/search/people?keywords=Jose%20Vergel%20Holcim
https://www.linkedin.com/sales/search/people?keywords=Akash%20Gupta%20Maersk
```

## Batch 2 (six)

```
https://www.linkedin.com/sales/search/people?keywords=Kamil%20Jellonek%20Partners%20Group
https://www.linkedin.com/sales/search/people?keywords=Roman%20Brueckner%20SAP
https://www.linkedin.com/sales/search/people?keywords=Thomas%20Mehlkopf%20SAP
https://www.linkedin.com/sales/search/people?keywords=Jeffrey%20Lasecki%20SAP
https://www.linkedin.com/sales/search/people?keywords=Sherief%20Hamid%20SAP
https://www.linkedin.com/sales/search/people?keywords=Njal%20Fjotland%20Equinor
```

## Batch 3 (six)

```
https://www.linkedin.com/sales/search/people?keywords=Johan%20Schelstraete%20Equinor
https://www.linkedin.com/sales/search/people?keywords=Leonid%20Opanasyk%20DSV
https://www.linkedin.com/sales/search/people?keywords=Line%20Ehlers%20DSV
https://www.linkedin.com/sales/search/people?keywords=Ruth%20Wandhoefer%20Leximar
https://www.linkedin.com/sales/search/people?keywords=Eleanor%20Hill%20Treasury%20Storyteller
https://www.linkedin.com/sales/search/people?keywords=Hywel%20Jones%20TAC%20Insights
```

## Per lead

1. Open the search URL. The result page lands inside Sales Navigator.
2. Find the person, check the title against `tier2-roster.csv`.
3. Use the row's overflow menu, **Save to list**, pick **TA Cook Rome 26**.
4. Mark the `salesnav_add` column in `tier2-roster.csv` as `done`.

Do not send connection requests from Sales Navigator. Those go from Dirk's own account; see `runbook-linkedin-connect.md`.

## If you want the tabs opened for you

`.scratch/open_tabs.py` in the main repo opens URLs as Edge tabs over CDP on port 9222, where the Sales Nav session is already signed in. Feed it one batch at a time:

```powershell
uv run .scratch/open_tabs.py <six urls from one batch>
```

It only opens tabs. It does not search, scrape, save, or connect.

## Company-name note

Legal suffixes (`A/S`, `ASA`, `AG`, `SE`, `GmbH`) are stripped from the search keywords above. They hurt recall on Sales Nav, and the slash in `DSV A/S` breaks the query string unless it is percent-encoded. The full legal name stays in `tier2-roster.csv`.
