# Direct LinkedIn profile URLs (resolved for the stragglers)

Web-search lookup across all 18, run 2026-07-11, to route around Sales Nav keyword search not surfacing everyone. Each URL below is matched on company **and** a treasury/finance/SAP role from the search result, not on name alone. From a direct profile you can open the person and use the Sales Nav view to Save to list.

**14 of 18 resolved. 4 have no public profile. 2 on-file URLs were wrong and are corrected.**

## Direct profile URLs (14)

| # | Name | Company | Profile URL |
|---|---|---|---|
| 4 | Uffe Teisner-Kjaer | Grundfos | https://www.linkedin.com/in/teisner-kj%C3%A6r-uffe-57aba22 |
| 5 | Jose Vergel | Holcim | https://www.linkedin.com/in/jose-vergel-a2b456 |
| 6 | Akash Gupta | Maersk | https://www.linkedin.com/in/akash-gupta-2647737 |
| 7 | Kamil Jellonek | Partners Group | https://www.linkedin.com/in/kamil-jellonek-a0920a1 |
| 8 | Roman Brueckner | SAP SE | https://www.linkedin.com/in/dr-roman-brueckner-7564a753 |
| 9 | Thomas Mehlkopf | SAP SE | https://www.linkedin.com/in/thomas-mehlkopf-5231477 |
| 11 | Sherief Hamid | SAP | https://www.linkedin.com/in/sherief-hamid |
| 13 | Johan Schelstraete | Equinor | https://www.linkedin.com/in/johan-schelstraete-8580152 |
| 14 | Leonid Opanasyk | DSV | https://www.linkedin.com/in/leonid-opanasyk-484b6b30 |
| 15 | Line Ehlers | DSV | https://www.linkedin.com/in/lineehlers |
| 16 | Ruth Wandhoefer | Leximar | https://www.linkedin.com/in/dr-ruth-wandh%C3%B6fer-523b22 |
| 17 | Eleanor Hill | Treasury Storyteller | https://www.linkedin.com/in/eleanor-hill-506b6817 |
| 18 | Hywel Jones | TAC Insights | https://www.linkedin.com/in/hywel-lewis-jones-7b622a109 |
| 1 | Christos Georgiou | BSTDB | https://www.linkedin.com/in/christos-georgiou-57917a14 |

## Two corrections to the on-file URLs

- **Thomas Mehlkopf (#9)**: the on-file `/in/thomas-mehlkopf` never resolved in search. The real profile carries a suffix, `/in/thomas-mehlkopf-5231477`.
- **Hywel Jones (#18)**: the on-file `/in/h-lewis-jones` is a mismatch. His actual slug is `/in/hywel-lewis-jones-7b622a109` (he posts as "Hywel Lewis Jones").

## One to eyeball before saving

- **Christos Georgiou (#1)**: the found profile is BSTDB's **IT/ICT Director**, not treasury. It is the right person Dirk met at the booth (name, company, and seniority all fit, and BSTDB's actual treasurer is someone else), but confirm visually since the title differs from what the sheet implied. Medium confidence.

## The 4 with no public profile

These are the ones Sales Nav search will also struggle with. Identity is real in every case; the profile is just not surfacing publicly.

| # | Name | Company | Status |
|---|---|---|---|
| 2 | Victoria Boclinca | BSTDB | No LinkedIn profile found at all |
| 3 | Sergey Timeshov | BSTDB | No LinkedIn profile found at all |
| 10 | Jeffrey Lasecki | SAP | Exists (SAP NA Treasury Lead, S/4HANA book author) but LinkedIn only returns a name-disambiguation directory, no single profile |
| 12 | Njal Fjotland | Equinor | Name corroborated at Equinor via SAP user-group pages, but no LinkedIn profile surfaces |

For these four, the Sales Nav search URLs in `runbook-salesnav-add.md` remain the only route. If they do not appear there either, skip them; do not save a guessed profile under Dirk's name. The three BSTDB people (Georgiou, Boclinca, Timeshov) are one account, so saving Georgiou covers the relationship even if the other two never resolve.

## Note

`tier2-roster.csv` now carries three new columns: `resolved_linkedin_url`, `resolve_confidence`, `resolve_note`. The `salesnav_search_url` column is unchanged, so both routes are in one file.
