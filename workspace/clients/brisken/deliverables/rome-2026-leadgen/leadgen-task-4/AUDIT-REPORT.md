# Rome 2026 master contact sheet: correctness audit

Six independent auditors swept the sheet across identity, contactability,
designation, tiering, flag consistency and cross-source reconciliation. Every
non-trivial finding then went to a separate agent whose only instruction was to
refute it, defaulting to refuted when uncertain.

**28 findings survived. 12 were refuted and dropped.** The refuted ones are
listed at the bottom, because the reasons they died are as useful as the
findings that lived.

Sources reconciled: the master workbook, TA Cook's official post-event export,
the Brisken Token (NFC fob) registrations, the badge scans, the warm-customer
list, the past-conference cross-reference, and Dirk's own hand-edited copy.

---

## The structural discovery

**90 of the 298 rows have no name because TA Cook withheld it.** Every row with
a blank name has `sponsor_opt_in = No`, and in TA Cook's export the 90
non-opted-in attendees are exactly the 90 with blank First/Last Name. The
correlation is perfect in both directions.

These are not a merge bug and not enrichable. They are attendees who declined to
share their details with sponsors. They carry a company and an attendee type and
nothing else. They can never be contacted as individuals, only counted as
account-level presence.

Nothing in the old sheet said so. The corrected sheet labels them `ANON` with
`contactability = tac_optout_anon`, `email_owner = none`, `linkedin_owner = none`.

A related check came back clean: **zero people appear in both the token
registrations and the TA Cook opt-out set**, so no booth registration is being
used to route around someone's opt-out. Voluntarily tapping the fob is an
independent lawful basis, and it never collides with a withheld consent here.

---

## Confirmed findings, by what they would have cost

### Someone already received a wrong message

| Finding | Detail |
|---|---|
| `lowercase-name-already-sent` | `asako teruki` was stored all-lowercase and is one of the 19 sent from Dirk's Outlook on 2026-07-08. A real recipient at NYK read "Hi asako". Now `Asako Teruki`, salutation `Asako`. Not undoable; worth knowing. |

### Would have sent the wrong message to the wrong person

| Finding | Detail |
|---|---|
| `email-person-mismatch-boclinca` | Victoria Boclinca's row carries `rtsompani@bstdb.org`. That local-part is a different BSTDB person. The two other BSTDB rows match their owners correctly, so the defect is hers alone, and it came in from TA Cook's export unchanged. A `{First}` merge would have delivered "Hi Victoria" to R. Tsompani. Held with `send_hold = verify_email`. |
| `organiser-not-excluded` / `hywel-organizer-in-tier2` | Hywel Jones is the TA Cook **event organiser**. He tapped the fob, has no stop flag, and carries a note, so the old predicates put him inside both the booth-network consent blast and the Tier-2 warm sends. The touch doc excludes him in prose; the sheet never encoded it. Now `ORGANISER`, routed to his own thread. Note that `stop = X` would be the wrong fix: Dirk wants to talk to him about the Brisken Token for the next conference. |
| `residual-slb-email-swap` | The known Dan Morrison / Edilbert Galera mix-up was only half repaired. Galera's `alt_email` still held Morrison's address, Morrison's `alt_email` was a copy of his own, and Morrison's booth timestamp was actually Galera's. Both men are in the already-sent 19. Corrected against the token registrations. |
| `named-customers-not-yes` | The booth-network draft calls Snersrud, Lundemo Larsen, Haegemans and teruki "active customers" and gives them a different email template. The CRM-enriched sheet says all four are `No (Lead - ...)`. **The master is right and the draft is wrong.** This is the same mislabel class Dirk has now flagged three times. Fix the draft, not the sheet. |
| `yes-domain-contamination` | Four `icdportal.com` rows were marked `brisken_customer = Yes` by domain inference. Dirk's own edited copy says `No (SQL)`. Corrected to his value. The two Equinor rows are authoritatively `Yes` and were left alone. |

### Would have sent a warm 1:1 to someone who should not get one

| Finding | Detail |
|---|---|
| `tier2-routing-artifacts-as-warm-sends` | The "has a `dirk_notes` value" predicate treats bookkeeping as intent. Six rows would have received a warm personal email off the back of notes reading `cc: with colleague above?`, `see comment in "if we know them"`, `Visionary Mail`, and `Cc on the Shell/Rome thread ... not the responder`. The scheme now distinguishes a personal note from a routing artifact. |
| `ga-intent-missed-promotes-to-tier2` | Dirk wrote his hold decision in prose twice rather than as the bare token: Fabio Mora's note ends `=> GA`, Bruno Forret's ends `General awareness (GA) is always good`. An exact `== 'GA'` match missed both and promoted them to warm. Both now `GA`, both held for his confirmation. |

### Would have corrupted the tier logic

| Finding | Detail |
|---|---|
| `tier3-40-anonymized-noncontactable` | Under the owner's model, Tier 3 is 65 rows, of which only 25 are contactable. The other 40 are the anonymized opt-outs. Any "Tier 3 outreach" plan sized on 65 was sized on people who cannot be contacted. |
| `dup-person-hardik-katkoria` | Hardik Katkoria (Adidas, a priority account) became two `fob_encoded` rows because the merge's name key differs on his middle name. One row carries a gmail nickname address. Both would have counted in the booth-network send. Now one canonical row, one `DUPLICATE`. |
| `dup-person-adela-dolezalova` | Two rows, conflicting treatment: one `stop = X` at Trillion Consulting, one a live Zalando referral with no email. Cross-linked and held. |
| `test-row-in-live-booth-set` | An `Example` fixture row sits in the live sheet with `fob_encoded = true`, inflating the booth-network count. Now `TEST`. |
| `tac-provenance-overclaim` | Three rows claim TA Cook attendance but do not exist in TA Cook's export. Christian Forst is booth-only. Corrected. |
| `noshow-count-drift-and-branch` | The plan doc says 15 no-shows; the sheet has 18. The drift is fully explained by three prospect rows added afterwards. Doc is stale, sheet is right. |

### Would have made us look sloppy

| Finding | Detail |
|---|---|
| `blank-title-on-contactable-leads` | 13 contactable rows had no `job_title`, two of them already emailed. All non-blank now, `TBD` where genuinely unknown. |
| `acronym-and-casing-mangle` | TA Cook title-cases everything, which mangles acronyms: `Gm Treasury`, `It App/sys Specialist`, `Partnerships Manager Uk&i`, `Chief Revenue Officer Apac`. Repaired. |
| `cross-source-seniority-contradiction` | For five people the booth self-entry is materially more senior and more specific than TA Cook's registration value. Erik Snersrud is `Global Head of Payments`, not `Manager Cash Management`. Pavitra Jogessar is `VP - Risk Governance and Transformation`, not `VP`. The self-entry wins, since they typed it themselves. |
| `reversed-name-kiosses` | Stored as `first_name = Kiosses`, `last_name = Christos`. He is Christos Kiosses. |
| `middle-name-in-first-field` | Eight rows would salute on a middle or compound name. Isolated into `salutation_first` so the raw fields stay intact. |
| `free-mail-as-primary` | Eight rows use a personal address as the primary corporate contact. Two are live leads and are held with `needs_corporate_email`; one of them is a Roche **H5** recipient on a hotmail address. |
| `named-unreachable-no-channel` | Four named people (Domenic at JTI, Isabelle Badoux, Adela Dolezalova, Maria Moeller) have no email, phone or LinkedIn. They were being counted as leads. Now `UNREACHABLE`. |
| `engagement-no-post-event` | Five rows show live positive engagement (a booked meeting, "call after the summer") with no post-event outreach recorded. These are open commitments, not data defects. |
| `non-title-values-in-job-title-field` | Relationship descriptors and department words sitting in `job_title`. |
| `own-team-rows` | Brisken and UnpauseAI staff are in the list. All correctly stopped. Now explicitly `OWN_TEAM`. |

---

## What was refuted, and why it matters

Twelve findings died under adversarial review. Four are worth recording, because
each would have caused real damage if applied.

| Refuted finding | Why it was wrong |
|---|---|
| `deferred-vs-personal-not-derivable` and `hot-personal-double-send` | Both proposed pulling people out of Tier 2. Doing so would have dropped warm contacts whose `dirk_notes` explicitly ask for a personal follow-up ("I will send the pptx"). The correct repair was the opposite: let a personal note **outrank** the deferral. |
| `lseg-wrongly-deferred` | The claim was real but the row citations were wrong, because 27 cells contain embedded newlines and a line-based grep miscounts. Any fix keyed on line number would have edited the wrong people. Every fix in the rebuild is keyed on email. |
| `suspected-dup-hitachi-mikiko` | Proposed merging an anonymous Hitachi opt-out row into Mikiko Oizumi's booth row. That is precisely the re-identification the opt-out forbids. |
| `sap-customer-stopped` | Four `SAP customer` rows carry `stop = X`. They are Dirk's own edits, present in his hand-edited copy. Not a mistrigger. |

One proposed repair was **fabricated** and rejected before it reached the sheet:
an email address `isabelle.badoux@sanofi.com` that appears in no source file.
Isabelle Badoux stays `UNREACHABLE` with `send_hold = needs_enrichment`. A
neighbouring value that looked equally invented, `christian.forst@adidas-group.com`,
turned out to be real: he tapped the fob twice, once with gmail and once with his
corporate address. Both were checked against the sources before either was
trusted.
