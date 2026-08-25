# Notes for other Lead Generation tasks

Surfaced while auditing the master sheet. Not acted on, per the no-cross-task rule.

## For "Rome Tier 1 leads: LinkedIn + Sales Nav" (task 1)

The task description holds 10 LinkedIn URLs and says 9 need a Sales Nav lookup.
The corrected sheet has `linkedin_owner = dirk` and a `linkedin_url` for each of
the 19, so the split is now readable straight off the `lead-classification.csv`.

`asako teruki` in that task's roster is `Asako Teruki`. Her surname may be
`Tateno-Teruki`; her LinkedIn slug is `asako-tateno-teruki-794531129`. Worth
resolving before a connect note.

## For "Rome Tier 2 warm-engaged: LinkedIn + Sales Nav" (task 5)

T2 is 25 people, not the "~20" the task description says. 17 of the 25 are
partners or SAP staff (Deloitte, KPMG, PwC, Nagarro, Zanders, LeverX, INTENSUM,
SINVA, Target Networks, Eprox, Tradeweb, and 4 SAP employees), carrying Dirk's
"personal outreach DN" note. They are legitimately warm, and they are not
treasury prospects. Filter on `lead_type = prospect` to get the 8 real ones.

Six rows that the old predicate would have handed you as warm are routing
artifacts, not outreach intent: notes reading `cc: with colleague above?`,
`see comment in "if we know them"`, `Visionary Mail`, and `Cc on the Shell/Rome
thread ... not the responder`. They are `T3` or held now.

## For "Rome Tier 3 booth/token-network" tasks (tasks 4 and 23)

The two names conflate two disjoint groups, and the task descriptions inherit the
confusion. Concretely:

- The **booth/token network** is the 91 `fob_encoded` token-tappers. After
  removing the stop list, the organiser, the duplicate and the test row, 74 have
  an email. That is the GDPR consent blast, tracked by `booth_network_send`.
- **T3** is 33 cold contactable people, of whom 29 attended and 4 did not. It is
  disjoint from the booth group: every token-tapper is already H5, T1, T2, GA,
  stopped, or the organiser.

A "Tier 3 LinkedIn motion on the ~90 booth contacts" as literally written would
double-invite the entire T1, T2 and H5 cohorts. Use `Tier` and
`booth_network_send`, not the fob column.

Also: `linkedin_url` is present for 61 rows overall but **zero** of the 33 T3
people. Every T3 LinkedIn connect needs a lookup first.

## For "Rome Tier 1 hottest-5: LinkedIn + Sales Nav" (task 22)

H5 is 11 people, being the To: and Cc: addresses of the six notes in
`dirk-send-pack/README.md`. The task's checklist names 9. The two missing are the
LSEG cc's, Silvester Hetesi and Wiktor Jaszczak.

Dogan Yesil (Roche cc) is on a personal hotmail address and is held pending
Dirk's decision.

## For "Upload the Rome contacts to the CRM once all three tiers are contacted" (task 20)

Do not upload the 89 `ANON` rows as contacts. TA Cook withheld their PII because
they declined to share it with sponsors. They have a company and an attendee type
and nothing else. They belong in account-level reporting, if anywhere.

Do not upload the `TEST`, `OWN_TEAM` or `DUPLICATE` rows either.

Per the CRM rule, customer status comes from the Zoho `Account_Status` field, not
from a shared email domain. Four `icdportal.com` rows in this sheet were marked
`brisken_customer = Yes` by domain inference and have been corrected to Dirk's own
`No (SQL)`. After that correction, `is_customer = TRUE` holds for exactly **2
rows, both at Equinor** (Njal Fjotland, Johan Schelstraete). Read `is_customer`
from the rebuilt sheet, never from the old one.

## For "Support the live Accenture (Ashok) MDH referral" (task 7)

Ashok Kumar is the single row in `DEFERRED`. He is the only un-stopped SAP partner
with a real email and no protective note, he tapped the fob, and his
`if_we_know_them` says "Met at TAC Brussels 2024 (Dirk personally engaged)". His
classification should probably move once that referral is live.
