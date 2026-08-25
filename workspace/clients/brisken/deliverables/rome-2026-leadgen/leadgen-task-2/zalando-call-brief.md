# Zalando TreasuryCentral call: brief for Dirk

Prepared 2026-07-09 for Planner task "Prepare Zalando TreasuryCentral demo collateral (Lokesh Doggala)".
Every fact below carries its source. Anything we do not know is listed as an open question rather than filled in.

## The one thing to get right

**There is no recorded booth conversation with Lokesh.** He tapped the Brisken token at Booth #2 on
2026-06-24 at 15:31 UTC and does not appear anywhere in `booth-meeting-notes.md`. He replied to the
generic network follow-up (subject "Following up from the SAP conference in Rome", sent 2026-07-08),
not to a bespoke note. So the call cannot open with "picking up where we left off"; there is nowhere
to pick up from. Treat it as a warm inbound from a stranger who liked the TreasuryCentral one-liner.

That is why the demo flow (`zalando-demo-flow.md`) puts discovery before the product story instead of
after it.

## Who is on the call

| Person | What we actually know | Source |
|---|---|---|
| Lokesh Doggala | `lokesh.doggala@zalando.de`, +49 151 5427 7398, `linkedin.com/in/lokesh-r-a899a247`. Tapped the booth token 2026-06-24 15:31 UTC. Title is contested, see below. | `context/.../brisken-token-registrations.csv`; Planner task description |
| Adela Dolezalova | `adela.dolezalova.external@zalando.de`. Registered at the booth under company **Trillion**, not Zalando, five minutes after Lokesh. An external consultant on the Zalando account. | Same CSV, `company` column |
| Maria Moeller | `maria.moeller@zalando.de`. Dirk's forward calls her "lead". No booth registration, no CRM record, no prior contact anywhere in our files. | Planner task description; absence from the CSV and `zoho-crm.json` |

Maria is the person we know least about and the one Dirk's own note flags as the lead. She did not
come through the booth, which means Lokesh brought her in. Working assumption, to test on the call:
Lokesh is the practitioner and internal champion, Maria owns the decision, Adela is the implementation
partner who will ask the integration questions.

**The title conflict.** Three of our own sources disagree:

- Booth self-registration: "Treasury Consultant"
- Our Tier-1 send list: "Senior Treasury Consultant"
- Dirk's forward on 2026-07-09: "SAP Consultant, Corporate Solutions"

The last is most likely his current email signature and therefore the one to trust, but nobody has
verified it. The deck cover avoids the problem by naming him without a title. Do not read a title back
to him on the call.

## Zalando is not a new name to us

The Zoho CRM already carries an account **ZALANDO**, status `Lead - Cloud Subscription`, owner
**Dirk Neumann**, country Germany, last touched 2026-02-20. There is also a prior contact,
**Tinatin Biganashvili** (`tinatin.biganashvili@zalando.de`), lead source "Trade Show / Conference",
owner Yashmica Roy, last activity 2025-06-30. (Source: `context/zoho-crm.json`.)

Per the account-status convention, `Lead - *` means this is an open lead and not a customer, so nothing
on the call should imply an existing relationship. Worth knowing before the call in case Lokesh mentions
a colleague who spoke to us in 2025.

## What Zalando's SAP finance estate looked like, publicly

The one substantive public data point: consenso Consulting ran an **SAP S/4Finance Readiness Check at
Zalando**, published 2018-09-20. In scope were "general ledger, accounts receivable, accounts payable,
asset accounting, controlling, ERP reporting, consolidation, **banking, treasury, cash and liquidity
management**". Their cash management then ran on "a modified SAP solution, strongly tailored to
Zalando's requirements", and the study concluded that "the added value of a green field approach became
clear: existing, suboptimal solutions are no longer pursued".
(Source: <https://www.consenso.de/en/sap-s-4finance-readiness-check-at-zalando.html>)

**This is eight years old.** Do not assert on the call that Zalando runs a customized cash management
build or that a migration is in flight. What it earns us is a good question rather than a claim: a
heavily tailored in-house cash management layer is exactly the manual middle TreasuryCentral replaces,
and a greenfield S/4 move is exactly the moment those feeds get re-decided. Ask; do not tell.

The deck has been adjusted accordingly: the proof slide now reads "An S/4HANA move is the moment these
feeds get decided" instead of "Your S/4HANA migration ...". See `shared-file-proposals.md`.

## Open questions, in the order they should get answered

1. Which ERP are they on today, ECC or S/4HANA, and is a move in flight or done?
2. Is cash and liquidity management still a custom build, or standard SAP?
3. What does Maria Moeller own, and is she the budget?
4. What did Lokesh actually want when he replied? His reply text is not in our files; Dirk has it in
   his mailbox and it should be read before the call.
5. Is Adela's firm (Trillion) an incumbent SI on the account, and does that make them a channel or a
   blocker?

Questions 4 and 5 are cheap to answer before the call and change how it opens.

## What is unverified

- Lokesh's current job title (three conflicting internal sources).
- Maria Moeller's role and seniority (Dirk's word "lead" is the only evidence).
- Zalando's ERP state in 2026. The 2018 readiness check is the newest source found.
- Zalando's treasury pain. Nothing was recorded at the booth.
