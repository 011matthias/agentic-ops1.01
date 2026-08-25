# Rome 2026 master sheet: lead classification scheme

Every one of the 298 rows carries exactly one `Tier`. The partition is
asserted in `build-master-v2.py`; the build fails if it ever stops holding.

## The four lead classes

Grounded on how each group was actually contacted, not on a company name match.

| Class | Definition (the rule the script applies) | n |
|---|---|---|
| **H5** | Appears as a `To:` or `Cc:` address in Dirk's bespoke send pack (`dirk-send-pack/README.md`). Dirk sends these himself. | 11 |
| **T1** | `post_event_outreach == "Booth follow-up sent 2026-07-08"`. The 19 we sent from Dirk's Outlook. | 19 |
| **T2** | Carries a real personal note from Dirk in `dirk_notes`, and is reachable. Warm. | 25 |
| **T3** | Reachable, no personal note. Cold. Split by `t3_branch` into `attended` (29) and `no_show` (4). | 33 |

H5 and T1 are disjoint by construction, and the script asserts it.

**H5 is a roster, not a company rule.** Matching on company name instead would
pull in 13 people who were never in Dirk's pack: Ana Matos, both Katkorias,
Christian Forst, Miguel Carvalho (all adidas), Lukas Blauth, Kenneth Bogert
(Roche), five anonymized rows, and Domenic (JTI). Those people are real leads,
but they are T3, not H5. The `priority_account` column tags them
(`hot5_adidas`, `hot5_roche`, ...) so the account stays visible without
promoting the person into a send they were never part of.

## The non-lead classes

A row that is not a lead gets an explicit label rather than being forced into a tier.

| Class | Meaning | n |
|---|---|---|
| `ANON` | TA Cook withheld the PII (`sponsor_opt_in = No`). Company and attendee type only. Never contactable as an individual. | 89 |
| `STOP` | Competitor, systems integrator, or otherwise never-contact. | 69 |
| `GA` | Dirk marked the row general-awareness. Hold. | 40 |
| `DEFERRED` | SAP partner / employee / analyst with no personal note, under Dirk's "leave partners for later" rule. | 1 |
| `UNREACHABLE` | Named, but no email, phone or LinkedIn on file. | 4 |
| `OWN_TEAM` | Brisken and UnpauseAI staff. | 4 |
| `ORGANISER` | Hywel Jones, TA Cook. Own relationship thread, never the treasury sequence. | 1 |
| `DUPLICATE` | Same person as another row (`duplicate_of` names the canonical). | 1 |
| `TEST` | Leftover fixture row. | 1 |

## Precedence

Ordered. First match wins, so every row lands once.

```
1  TEST          brisken_customer == 'test row', or an example@ex.com address
2  OWN_TEAM      brisken.com / unpauseai.com domain, or company is Brisken
3  DUPLICATE     email is in the duplicate-suppress map
4  ORGANISER     attendee_type == 'TAC'
5  ANON          first_name and last_name both blank
6  H5            email is in the send-pack roster
7  T1            post_event_outreach starts with 'Booth follow-up sent'
8  STOP          stop == 'X'
9  GA            dirk_notes is 'GA', ends '=> GA', or says 'General awareness (GA)'
10 T2            personal note from Dirk AND reachable
11 DEFERRED      SAP partner/employee/analyst, account is not LSEG
12 UNREACHABLE   no channel of any kind
13 T3            everything else
```

Two orderings in that chain are load-bearing and were both wrong in the old
ad-hoc predicates:

**A personal note outranks the SAP deferral (10 before 11).** Dirk's own Tier-2
roster names people at Eprox, Nagarro, SAP and Zanders, all typed `SAP partner`
or `SAP employee`. Deferring on `attendee_type` alone silently dropped four
people he had explicitly written notes for. Putting `DEFERRED` first collapses
T2 from 25 to 8 and leaves `DEFERRED` at 56; putting the note first yields
T2 = 25 and `DEFERRED` = 1. That one remaining row is Ashok Kumar (Accenture),
independently confirmed as the only un-stopped SAP partner with a real email and
no protective note.

**`OWN_TEAM` outranks `ANON` (2 before 5).** 90 rows have both names blank. One
of them is Brisken's own company row, listed by TA Cook with PII withheld. It is
correctly suppressed either way, but `OWN_TEAM` is the truthful label, so `ANON`
is 89.

## `lead_type` is orthogonal to `Tier`

A person can be warm and still not be a treasury prospect. Dirk wrote
"personal outreach DN" on 13 partner and SI rows (Deloitte, KPMG, PwC, Nagarro,
Zanders) and on 4 SAP staff. They have earned the warm personal touch. None of
them should ever receive the treasury pitch.

| | prospect | partner_si | sap_internal |
|---|---|---|---|
| H5 | 7 | 4 (LSEG) | 0 |
| T1 | 19 | 0 | 0 |
| T2 | 8 | 13 | 4 |
| T3 | 33 | 0 | 0 |

The four `partner_si` rows in H5 are the LSEG contacts, which Dirk pulled into
the priority group as a named exception to the partner deferral.

## Supporting columns

| Column | Purpose |
|---|---|
| `Tier_reason` | One line stating why this row got this class. Auditable. |
| `t3_branch` | `attended` or `no_show`. Selects the T3 email variant. |
| `priority_account` | `hot5_vw` / `hot5_jti` / `hot5_roche` / `hot5_adidas` / `hot5_lseg`. Account overlay, not a tier. |
| `canonical_account` | Collapses 15 spelling variants (Adidas / Adidas AG / adidas AG, DSV / DSV A/S, Shell / Shell International, and so on). |
| `contactability` | Lawful basis: `tac_optout_anon`, `direct_booth`, `tac_optin`, `referral`, `salesnav_prospect`, `personal_relationship`, `unverified`. |
| `seniority` | Band from the corrected title. `unknown` if and only if the title is `TBD`. Asserted. |
| `salutation_first` | The value a `{First}` merge should use. Isolated from `first_name` so the raw field stays audit-clean. |
| `booth_network_send` | Membership of the GDPR consent blast. `TRUE` for 74 rows: the 91 token-tappers minus the stop list, the organiser, the duplicate, the test row, and anyone with no email. |
| `email_owner` | Which motion owns this person's email. Set to `none` whenever `send_hold` is set. |
| `linkedin_owner` | `dirk` for H5/T1/T2/organiser, `matthias` for T3, `none` if there is no LinkedIn URL. |
| `send_hold` | `verify_email`, `needs_corporate_email`, `needs_enrichment`, `owner_decision`. Any value blocks the row from every send. 10 rows are held. |
| `is_customer` | `TRUE` only where `brisken_customer == 'Yes'`. Exactly 2 rows, both at Equinor. The 4 Tradeweb/ICD rows were a false `Yes` from domain inference and are corrected to `No (SQL)`. |
| `duplicate_of` | Email of the canonical row. |

## Reproducing

```
uv run output/leadgen-task-4/build-master-v2.py
```

Builds from the pinned pre-drift snapshot, writes
`rome2026-post-event-master-contacts-v2.xlsx` and `lead-classification.csv`, and
prints a drift report comparing the snapshot against the live workbook. The live
workbook is only ever read, never written. Re-runnable and idempotent. The
partition assertions and the dead-lookup-key assertions run on every build.
