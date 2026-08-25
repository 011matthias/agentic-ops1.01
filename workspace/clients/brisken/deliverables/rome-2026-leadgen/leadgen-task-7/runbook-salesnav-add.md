# Runbook: add Tier 3 to the "TA Cook Rome 26" Sales Nav list

**Seat:** Matthias's Sales Navigator seat (not Dirk's LinkedIn).
**List:** "TA Cook Rome 26", created by Dirk.
**Time:** about 25 minutes in five paced batches.
**Nothing here has been executed.** No lead has been added and no tab has been opened.

## Ground rules

- **Open each lead in Sales Navigator, not regular LinkedIn.** A Sales Nav people-search result carries the Save action directly.
- **Do not automate the seat.** Open a batch, save by hand, then the next batch. Six parallel search tabs already tripped the throttle once on this list; keep it to one batch at a time.
- **Duplicates are harmless.** Sales Nav marks anyone already in the list as saved.
- **Confirm identity before saving.** Match against the `job_title` column in `tier3-roster.csv`. Five contacts (Makoudi, Wise, George, Tesch, Blauth) have no verified public profile and two roster titles read TBD (Forst, Rekman); for those, match on company plus a treasury / SAP / payments-consistent role, and on a collision skip and note it rather than saving the wrong person.


## Batch 1 (6)

```
https://www.linkedin.com/sales/search/people?keywords=Hardik%20Katkoria%20Adidas
https://www.linkedin.com/sales/search/people?keywords=Christian%20Forst%20Adidas
https://www.linkedin.com/sales/search/people?keywords=Naeem%20Alam%20Deloitte
https://www.linkedin.com/sales/search/people?keywords=Bhavana%20Thorat%20Deloitte
https://www.linkedin.com/sales/search/people?keywords=Ikaros%20Matsoukas%20Deloitte%20UK
https://www.linkedin.com/sales/search/people?keywords=Magdalena%20Makoudi%20EY
```

## Batch 2 (6)

```
https://www.linkedin.com/sales/search/people?keywords=Robert%20Jakubowski%20EY%20Poland
https://www.linkedin.com/sales/search/people?keywords=Lukas%20Blauth%20Roche
https://www.linkedin.com/sales/search/people?keywords=Stiaan%20Scheepers%20Global%20Payments
https://www.linkedin.com/sales/search/people?keywords=Annika%20Lanz%20KPMG
https://www.linkedin.com/sales/search/people?keywords=Stephen%20Carlin%20Mastercard
https://www.linkedin.com/sales/search/people?keywords=Annemarie%20Boxberger%20Nagarro%20ES
```

## Batch 3 (6)

```
https://www.linkedin.com/sales/search/people?keywords=Milena%20Zang%20Nagarro%20ES
https://www.linkedin.com/sales/search/people?keywords=Steffen%20Karsch%20PAYMENTS.CC
https://www.linkedin.com/sales/search/people?keywords=Florian%20Matzinger%20PAYMENTS.CC
https://www.linkedin.com/sales/search/people?keywords=Tushar%20Gulhane%20SAP
https://www.linkedin.com/sales/search/people?keywords=Caroline%20Hacikyaner%20SAP
https://www.linkedin.com/sales/search/people?keywords=Markku%20Keskinen%20SAP
```

## Batch 4 (6)

```
https://www.linkedin.com/sales/search/people?keywords=Rosamaria%20Violante%20SAP
https://www.linkedin.com/sales/search/people?keywords=Robyn%20Wise%20SAP
https://www.linkedin.com/sales/search/people?keywords=Suma%20George%20SAP%20Australia
https://www.linkedin.com/sales/search/people?keywords=Jan%20Seda%20SAP%20CR
https://www.linkedin.com/sales/search/people?keywords=Natsuko%20Tsuji%20SAP%20Japan
https://www.linkedin.com/sales/search/people?keywords=Maximilian%20Tesch%20SAP
```

## Batch 5 (5)

```
https://www.linkedin.com/sales/search/people?keywords=Richard%20Gilbert%20Worldpay
https://www.linkedin.com/sales/search/people?keywords=Jack%20Green%20Worldpay
https://www.linkedin.com/sales/search/people?keywords=Antonia%20Rekman%20Worldpay
https://www.linkedin.com/sales/search/people?keywords=Olivier%20Tavares%20Worldpay
https://www.linkedin.com/sales/search/people?keywords=Eliane%20Eysackers%20Zanders
```

## Per lead

1. Open the search URL. The result page lands inside Sales Navigator.
2. Find the person, check the title against `tier3-roster.csv`.
3. Use the row's overflow menu, **Save to list**, pick **TA Cook Rome 26**.
4. Mark the `salesnav_add` column in `tier3-roster.csv` as `done`.

Do not send connection requests from Sales Navigator. Those go from Dirk's own account; see `runbook-linkedin-connect.md`.

## If you want the tabs opened for you

`.scratch/open_tabs.py` in the main repo opens URLs as Edge tabs over CDP on port 9222, where the Sales Nav session is already signed in. Feed it one batch at a time:

```powershell
uv run .scratch/open_tabs.py <six urls from one batch>
```

It only opens tabs. It does not search, scrape, save, or connect.

## Company-name note

Legal suffixes (AG, A/S, ASA, SE, GmbH, spol. s r.o., Co. Ltd.) are stripped from the search keywords and the queries are percent-encoded; suffixes hurt recall on Sales Nav. "F. Hoffmann-La Roche AG" searches as "Roche". The full legal names stay in `tier3-roster.csv`.
