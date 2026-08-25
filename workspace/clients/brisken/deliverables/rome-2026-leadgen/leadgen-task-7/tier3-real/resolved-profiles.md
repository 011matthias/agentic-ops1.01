# Real Tier 3: resolved LinkedIn profiles

Per-contact web-search lookup, run 2026-07-13, one agent per contact, verified on company AND a treasury / finance / SAP / IT-finance role. A wrong URL becomes a connection request under Dirk's name, so unverifiable contacts return nothing rather than a guess.

**12 of 25 resolved (11 high, 1 medium). 13 have no verifiable public profile and are Sales Nav only.**

## Resolved (12)

| # | Name | Company | Conf | Profile URL |
|---|---|---|---|---|
| 1 | Hardik harshad Katkoria | Adidas | high | https://www.linkedin.com/in/hardik-katkoria-88636633 |
| 2 | Ana Matos | Adidas | high | https://www.linkedin.com/in/anamariacorreiadematos/ |
| 3 | Christian Forst | adidas AG | high | https://de.linkedin.com/in/christian-forst-1153a2198 |
| 4 | Alessia Belluomo | Aeroporti Di Roma | high | https://it.linkedin.com/in/alessia-belluomo-1b8ba424 |
| 5 | Tomáš Rybáček | Allwyn | high | https://www.linkedin.com/in/rybacek/ |
| 6 | Line Ehlers | DSV A/S | high | https://www.linkedin.com/in/lineehlers/ |
| 7 | Kenneth Bogert | F. Hoffmann-la Roche, Ag | high | https://ch.linkedin.com/in/kenneth-bogert-53a4a216 |
| 8 | Juan Carlos Alonso | Moeve | high | https://es.linkedin.com/in/juan-carlos-alonso-de-los-santos-5301036a |
| 9 | Thorsten Stegner | Robert Bosch GmbH | high | https://www.linkedin.com/in/thorsten-stegner-783945247/ |
| 10 | Bandar Mohammad Alghannam | Saudi Aramco Digital Finance Department | medium | https://sa.linkedin.com/in/bandar-alghannam-cma-mba-65219b22 |
| 11 | Maurice Schrijnemakers | Vodafone | high | https://www.linkedin.com/in/mauriceschrijnemakers/ |
| 12 | Tomáš Krčka | ČEZ, a.s. | high | https://www.linkedin.com/in/tkrcka/ |

## No verifiable public profile (13, Sales Nav only)

| # | Name | Company | Why |
|---|---|---|---|
| 13 | Miguel Carvalho | Adidas AG | No LinkedIn profile could be verified against both Adidas AG and a plausible treasury/finance/SAP role. Miguel Carvalho is a very common Portuguese na |
| 14 | Sergey Timeshov | BSTDB | Multiple searches for "Sergey Timeshov" (and spelling variants) with BSTDB, treasury, and Principal Officer returned no LinkedIn profile for this pers |
| 15 | Lukas Blauth | F. Hoffmann-La Roche AG | Could not verify. The on-file LinkedIn URL returns HTTP 999 (auth-walled), and web searches for "Lukas Blauth" at F. Hoffmann-La Roche in a Solution A |
| 16 | Sultan Alqahtani | Mobily | The person is confirmed real (TheOrg lists Sultan Mohsen Alqahtani as General Manager Treasury at Mobily, Riyadh, exactly matching name/company/title) |
| 17 | Mohammad Bin Rayes | Mobily | No LinkedIn profile could be verified for Mohammad Bin Rayes, Director Treasury at Mobily. Search hits under the Bin Rayes / Mohammad Rayes name resol |
| 18 | Anders Fosse Johannessen | Norsk Hydro ASA | No LinkedIn /in profile could be found for Anders Fosse Johannessen tied to Norsk Hydro. Searches surfaced only unrelated namesakes (an Anette Fosse J |
| 19 | Maren Kobberød Risvik | Norsk Hydro ASA | A "Maren Risvik" profile (no.linkedin.com/in/maren-risvik-0449ba17a) exists in Norway, but no snippet or fetched page confirms Norsk Hydro or a treasu |
| 20 | Anna Maria Tyszko | Pandora | Could not confidently verify a LinkedIn profile for Anna Maria Tyszko at Pandora. One plausible Polish candidate exists (pl.linkedin.com/in/anna-tyszk |
| 21 | Nedhal Al Abdulaal | Saudi Aramco | No LinkedIn profile for Nedhal Al Abdulaal at Saudi Aramco could be found. Searches surfaced only different people (Nedhal Al-Sultan at TASNEE, and un |
| 22 | Ahmed Hashim | Saudi Aramco | Multiple "Ahmed Hashim"/"Ahmed Al-Hashim" people exist at Saudi Aramco. A RocketReach entry shows an "Ahmed al-Hashim" as a Business System Analyst at |
| 23 | Arwa Malak | Saudi Aramco | No LinkedIn profile for "Arwa Malak" at Saudi Aramco could be found or verified. Searches returned only unrelated Arwa profiles and a different person |
| 24 | Guido Goeltzer | Vodafone Group Services GmbH | Confirmed a real Guido Goeltzer at Vodafone in a cash-flow/treasury role (TreasuryCast "Dialling Up Cash Flow at Vodafone" podcast, matching his Cash  |
| 25 | Doris Altschachl | Wiener Städtische Versicherung AG | No LinkedIn profile for Doris Altschachl at Wiener Staedtische Versicherung AG could be found. Searches returned only unrelated Altschachl profiles (P |

The Saudi Aramco (4), Mobily (2) and Norsk Hydro (2) clusters are the bulk of the unresolved; those regions/companies have low public LinkedIn visibility and web search cannot confirm them on both company and role. Several are confirmed to exist (Alqahtani via TheOrg as GM Treasury, Bin Rayes as Director Treasury) but have no findable public profile. Do not connect on a guessed URL; use the Sales Nav search and confirm visually, and skip if they do not surface.

The columns `resolved_linkedin_url` / `resolve_confidence` / `resolve_note` carry this per row in `roster.csv`; the `salesnav_search_url` column is the fallback route for all 25.
