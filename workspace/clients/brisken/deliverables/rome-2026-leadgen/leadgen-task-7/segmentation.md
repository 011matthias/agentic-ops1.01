# Tier 3 (booth/token-network): how 91 became 29

Source of truth: `workspace/clients/brisken/context/lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx`, read fresh 2026-07-11 (290 rows, the regenerated 2026-07-10 sheet). Segment definition from the Planner task pair: `fob_encoded` = true, "met via the Brisken Token, no specific note".

The sheet's `post_event_outreach` status column was dropped in the 2026-07-10 regeneration, so every prior-tier exclusion below is by explicit NAME against the prior rosters, not by any sheet status column. The `Tier` column was used only as a cross-check, never as the filter.

## The filter

91 rows carry `fob_encoded` = true. All 91 are booth-registered (`in_our_booth` = Yes); the token registration is the booth record.

| Removed | N | Matched against |
|---|---|---|
| `stop` = X | 15 | stop column (competitors, SIs, own team, test rows) |
| Tier-1 nineteen | 19 | Name list in the "Rome Tier 1 leads: LinkedIn + Sales Nav" task description. All 19 are fob_encoded; with the status column gone they would all have slipped back in on a column-based dedup |
| Tier-2 eighteen | 8 | `output/leadgen-task-5/tier2-roster.csv` (branch `leadgen/task-5`). Overlap: Georgiou, Vergel, Teisner-Kjaer, Jellonek, Brueckner, Mehlkopf, Opanasyk, Jones |
| Hottest-5 people | 8 | VW (Zucknick), JTI (Disdet, Cuello), Roche (Herrera La Grotta, Yesil), Adidas (Tse), LSEG (Bonizzoni, Favalli). Landro is in the hottest-5 but not fob_encoded |
| Sheet duplicate | 1 | "Hardik(Hrisha Papa) Katkoria", flagged `Tier` = DUPLICATE on the sheet; the primary Adidas row stays |

91 minus 51 = 40. Eleven more carry a personal angle and belong to other live motions:

| Routed out | N | Where they belong |
|---|---|---|
| Ashok Kumar (Accenture) | 1 | "Support the live Accenture (Ashok) MDH referral" (own Planner task; he already responded to the Rome outreach) |
| `personal outreach DN` partners | 10 | Richter (Eprox), Diet (INTENSUM), Szczecina (KPMG), Sharandakov (LeverX), Kiosses + Meyerhoff (Nagarro), Reinsfelder (SINVA), Stiebe (Target Networks), Ramos (Tradeweb), Koekkoek (Zanders). Their email runs via the partner/SAP personal-outreach pack (built 2026-07-10); a templated token note on top would double-contact them with a colder message than the one Dirk is already sending |

40 minus 11 = **29 connects**. The segment definition on both Planner siblings reads "no specific note", which is exactly the line between the 29 and the routed 11.

## Cross-check against the sheet's Tier column

The 29 land as `Tier` = GA (26) and `Tier` = T3 (3: Katkoria, Forst, Blauth). No H5, T1 or T2 row survived the name-dedup, which is the confirmation the name lists caught everything the wiped status column used to flag. GA-tagged contacts stay in: the GA tag defers the EMAIL sequence, while this task is the token-network LinkedIn connect that `rome-post-event-plan.md` track 1 wants for the whole fob network.

## Composition of the 29

17 SAP partners (Deloitte x3, EY x2, Worldpay x4, Nagarro x2, PAYMENTS.CC x2, KPMG, Mastercard, Global Payments, Zanders), 9 SAP employees, 3 SAP customers (2 Adidas, 1 Roche). The three customers sit on hottest-5 ACCOUNTS but are different people than the H5 threads; their notes stay generic so nothing cross-wires with Dirk's bespoke sends.

Two of the 29 were badge-scanned at the booth (Jakubowski, Matzinger). Three were personally engaged by Dirk at TAC Brussels 2024 (Karsch, Violante, Eysackers); their opener says "good to see you again" instead of "good to meet you". Nobody in the 29 is a no-show, so the softer did-not-attend opener branch is empty by construction: fob_encoded means the person registered at the booth in person.

## Expected-pool note

The continuation brief estimated ~45 after dedup. The gap to 29 is the 11 routed personal-note holders plus arithmetic slack in the estimate (the brief also expected ~68 fob survivors where the live sheet gives 69 before prior-tier dedup). The name-dedup itself matches the brief's numbers; the routing decision is this session's judgement call, argued above and flagged in `SUMMARY.md`.
