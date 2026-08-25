# Direct LinkedIn profile URLs (resolved and verified)

Web-search lookup across all 29, run 2026-07-11: one search agent per contact (19 completed in the workflow pass; the remaining 10 were finished by hand in the same session after the agent pool hit the usage limit). Every URL below is matched on company AND a treasury / SAP / payments-consistent role, not on name alone. A wrong URL becomes a connection request under Dirk's name, so unverifiable contacts return nothing rather than a guess.

**24 of 29 carry a direct profile URL (19 high confidence, 5 eyeball-first). 5 have no verifiable public profile. 1 on-file URL is suspect.**

## High confidence (19)

| # | Name | Company | Profile URL |
|---|---|---|---|
| 1 | Hardik Katkoria | Adidas | https://www.linkedin.com/in/hardik-katkoria-88636633 |
| 2 | Christian Forst | adidas AG | https://www.linkedin.com/in/christian-forst-1153a2198 |
| 4 | Naeem Alam | Deloitte | https://www.linkedin.com/in/naeem-alam-14a61443 |
| 5 | Bhavana Thorat | Deloitte GmbH | https://www.linkedin.com/in/cabhavana-thorat |
| 6 | Ikaros Matsoukas | Deloitte UK | https://www.linkedin.com/in/ikarosm |
| 9 | Stiaan Scheepers | Global Payments | https://www.linkedin.com/in/stiaanscheepers |
| 10 | Annika Lanz | KPMG | https://www.linkedin.com/in/annika-lanz-9b172521a |
| 11 | Stephen Carlin | Mastercard | https://www.linkedin.com/in/stephenmcarlin |
| 15 | Steffen Karsch | PAYMENTS.CC | https://www.linkedin.com/in/steffen-karsch-95531836 |
| 16 | Caroline Hacikyaner | SAP | https://www.linkedin.com/in/caroline-hacikyaner-cpa-35bb292 |
| 19 | Rosamaria Violante | SAP | https://www.linkedin.com/in/rosamaria-violante-70410191 |
| 20 | Tushar Gulhane | SAP | https://www.linkedin.com/in/tushargulhane |
| 22 | Jan Seda | SAP CR | https://www.linkedin.com/in/jan-seda |
| 23 | Natsuko Tsuji | SAP Japan | https://www.linkedin.com/in/natsukotsuji |
| 25 | Antonia Rekman | Worldpay | https://www.linkedin.com/in/antonia-rekman-07672122 |
| 26 | Jack Green | Worldpay | https://www.linkedin.com/in/jack-green-02b52371 |
| 27 | Olivier Tavares | Worldpay | https://www.linkedin.com/in/olivier-tavares |
| 28 | Richard Gilbert | Worldpay | https://www.linkedin.com/in/richardgilbert |
| 29 | Eliane Eysackers | Zanders | https://www.linkedin.com/in/eliane-eysackers-687a544 |

Christian Forst and Caroline Hacikyaner had no URL on the master sheet and are new finds (Forst independently confirmed as Senior Manager Group Treasury at adidas via Treasury Today; Hacikyaner via SAP working-capital strategy references). The rest verify the on-file URLs.

## Eyeball before sending (5, medium confidence)

| # | Name | Company | Profile URL | Why eyeball |
|---|---|---|---|---|
| 7 | Robert Jakubowski | EY Poland | https://www.linkedin.com/in/robert-jakubowski-66168b62 | EY SAP Treasury competency leader confirmed on ey.com, but the profile page is login-walled; ey.com says Manager where the sheet says Senior Manager |
| 12 | Annemarie Boxberger | Nagarro ES | https://www.linkedin.com/in/annemarie-boxberger-a4a01420a | Only Annemarie Boxberger on LinkedIn in Germany, but headline reads Convista, not Nagarro; likely a job change since Rome |
| 13 | Milena Zang | Nagarro ES | https://www.linkedin.com/in/milena-zang-41887b21b | Nagarro marketing confirmed via posts; one snippet suggests a recent move to Merz Lifecare |
| 14 | Florian Matzinger | PAYMENTS.CC | https://www.linkedin.com/in/florian-matzinger-762a0591 | PAYMENTS.CC team page confirms the role; the profile's own affiliation was not directly readable |
| 17 | Markku Keskinen | SAP | https://www.linkedin.com/in/markku-keskinen-784aa32 | Slug tied to an SAP Treasury Nordics event mention; affiliation not directly readable |

## Job-change flags picked up in passing

Katkoria may have moved to ALDI SUED after Rome (RocketReach shows a newer role); Boxberger and Zang likewise may have left Nagarro. The booth meeting still happened, so the notes stay valid, but the roster `job_title` column may be stale for these three.

## The 5 with no verifiable public profile

| # | Name | Company | Status |
|---|---|---|---|
| 3 | Magdalena Makoudi | EY | Name returns zero public hits; the on-file URL (`magdalena-makoudi-913a8b3`) could not be corroborated. Verify visually in Sales Nav before any invite |
| 8 | Lukas Blauth | Roche | **On-file URL suspect.** The slug `lukas-blauth-92368a418` never appears in search, and the only public Lukas Blauth profile is a Potsdam PhD candidate. Do not use the on-file URL blind; go via Sales Nav and confirm the Roche affiliation |
| 18 | Robyn Wise | SAP | No public profile surfaced. Sales Nav search only |
| 21 | Suma George | SAP Australia | 40+ same-name profiles, none confirmable at SAP Australia. Do not guess |
| 24 | Maximilian Tesch | SAP SE | No public profile surfaced. Sales Nav search only |

For these five, the Sales Nav search URLs in `runbook-salesnav-add.md` are the route. If they do not surface there either, skip them; do not connect on a guessed profile.

## Note

`tier3-roster.csv` carries the results in the `resolved_linkedin_url` / `resolve_confidence` / `resolve_note` columns; the `salesnav_search_url` column is unchanged, so both routes sit in one file. Row numbers above are the roster `seq` values.
