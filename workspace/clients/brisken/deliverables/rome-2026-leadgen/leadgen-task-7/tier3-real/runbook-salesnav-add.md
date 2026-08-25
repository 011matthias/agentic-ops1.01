# Runbook: add real Tier 3 to the "TA Cook Rome 26" Sales Nav list

**Seat:** Matthias's Sales Navigator seat.
**List:** "TA Cook Rome 26".
**Nothing here has been executed.**

## Ground rules

- Open each lead in Sales Navigator (the Save action is on the result row).
- One batch at a time; six parallel search tabs tripped the throttle once before.
- Duplicates are harmless (marked as saved).
- 13 of the 25 have no verified public profile; match on company + a treasury / finance / SAP / IT-finance role, and skip on a collision rather than saving the wrong person. Saudi Aramco (4), Mobily (2) and Norsk Hydro (2) are the hardest; they may not surface in Sales Nav either, in which case skip.

## Batch 1 (6)

```
https://www.linkedin.com/sales/search/people?keywords=Hardik%20Katkoria%20Adidas
https://www.linkedin.com/sales/search/people?keywords=Ana%20Matos%20Adidas
https://www.linkedin.com/sales/search/people?keywords=Christian%20Forst%20Adidas
https://www.linkedin.com/sales/search/people?keywords=Alessia%20Belluomo%20Aeroporti%20Di%20Roma
https://www.linkedin.com/sales/search/people?keywords=Tom%C3%A1%C5%A1%20Ryb%C3%A1%C4%8Dek%20Allwyn
https://www.linkedin.com/sales/search/people?keywords=Line%20Ehlers%20DSV
```

## Batch 2 (6)

```
https://www.linkedin.com/sales/search/people?keywords=Kenneth%20Bogert%20Roche
https://www.linkedin.com/sales/search/people?keywords=Juan%20Alonso%20Moeve
https://www.linkedin.com/sales/search/people?keywords=Thorsten%20Stegner%20Robert%20Bosch
https://www.linkedin.com/sales/search/people?keywords=Bandar%20Alghannam%20Saudi%20Aramco
https://www.linkedin.com/sales/search/people?keywords=Maurice%20Schrijnemakers%20Vodafone
https://www.linkedin.com/sales/search/people?keywords=Tom%C3%A1%C5%A1%20Kr%C4%8Dka%20%C4%8CEZ
```

## Batch 3 (6)

```
https://www.linkedin.com/sales/search/people?keywords=Miguel%20Carvalho%20Adidas
https://www.linkedin.com/sales/search/people?keywords=Sergey%20Timeshov%20BSTDB
https://www.linkedin.com/sales/search/people?keywords=Lukas%20Blauth%20Roche
https://www.linkedin.com/sales/search/people?keywords=Sultan%20Alqahtani%20Mobily
https://www.linkedin.com/sales/search/people?keywords=Mohammad%20Bin%20Rayes%20Mobily
https://www.linkedin.com/sales/search/people?keywords=Anders%20Johannessen%20Norsk%20Hydro
```

## Batch 4 (6)

```
https://www.linkedin.com/sales/search/people?keywords=Maren%20Risvik%20Norsk%20Hydro
https://www.linkedin.com/sales/search/people?keywords=Anna%20Tyszko%20Pandora
https://www.linkedin.com/sales/search/people?keywords=Nedhal%20Al%20Abdulaal%20Saudi%20Aramco
https://www.linkedin.com/sales/search/people?keywords=Ahmed%20Hashim%20Saudi%20Aramco
https://www.linkedin.com/sales/search/people?keywords=Arwa%20Malak%20Saudi%20Aramco
https://www.linkedin.com/sales/search/people?keywords=Guido%20Goeltzer%20Vodafone
```

## Batch 5 (1)

```
https://www.linkedin.com/sales/search/people?keywords=Doris%20Altschachl%20Wiener%20Staedtische
```

## Per lead

1. Open the search URL (lands inside Sales Navigator).
2. Check the title against `roster.csv`.
3. Overflow menu, **Save to list**, **TA Cook Rome 26**.
4. Mark `salesnav_add` = `done` in `roster.csv`.

`.scratch/open_tabs.py` opens a batch of tabs over CDP if wanted; it only opens tabs. Legal suffixes (AG, A/S, ASA, GmbH, a.s.) are stripped from the search keywords and percent-encoded; the full legal names stay in `roster.csv`.
