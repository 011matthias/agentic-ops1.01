# Notes for other Lead Generation tasks

Found while working task 2. Not acted on.

## "Exclude BTP from all demos"

Dirk's directive is unimplemented across the current demo material. Measured by extracting the text of
each rendered PDF on 2026-07-09:

| File | BTP mentions |
|---|---|
| `dirk-send-pack/brisken-market-data-hub.pdf` | 2 |
| `dirk-send-pack/brisken-digital-co-worker.pdf` | 2 |
| `dirk-send-pack/brisken-mdh-commodities.pdf` | 1 |
| `dirk-send-pack/brisken-smart-trading.pdf` | 0 |
| `call-collateral/brisken-treasurycentral-zalando.pdf` | 0, fixed 2026-07-09 (was 2) |
| `call-collateral/brisken-treasurycentral-sanofi.pdf` | 0, fixed 2026-07-09 (was 2) |

The TreasuryCentral pair is done: two string edits in `.scratch/deckgen/build-treasurycentral.js`, both
prospects rebuilt, and the repo plus the four SharePoint files replaced. Details in
`shared-file-proposals.md`.

The three module decks have their own build scripts (`build-mdh.js`, `build-mdh-commodities.js`,
`build-digital-coworker.js`) and need the same treatment before any of them is attached to an email again.
Market Data Hub and Digital Co-Worker are the ones most likely to be attached as Zalando follow-up
material, so this still blocks the back half of task 2.

Note the directive says demo materials. `brisken-rome-2026-onepager.md` also lists "on SAP BTP" under
Credentials. Whether a credentials line on a one-pager counts as demo material is Dirk's call, not ours.

## "Prepare Sanofi TreasuryCentral demo collateral (Ian Haegemans)"

The Sanofi deck and PPTX already exist in
`workspace/clients/brisken/deliverables/lead-generation/rome-2026/call-collateral/`, untracked, built
2026-07-09 around 15:47 local, alongside the Zalando pair. Whoever picks up that task should audit what
is there before rebuilding. It carries the same two BTP strings.

Unlike Zalando, Sanofi has a confirmed slot (next week Friday, around 16:00, per the task description),
so the collateral has a real deadline.

## "Upload the Rome contacts to the CRM once all three tiers are contacted"

Zalando is worth pulling forward. The `ZALANDO` account already exists in Zoho (status
`Lead - Cloud Subscription`, owner Dirk Neumann, last activity 2026-02-20) and none of the three call
attendees are on it. It is the only Rome lead with a call being booked and a named decision maker, and
the CRM will not show that.

There is also a stale Zalando contact on file: Tinatin Biganashvili, lead source "Trade Show /
Conference", owner Yashmica Roy, last activity 2025-06-30.

## "Rome Tier 1 leads: LinkedIn + Sales Nav"

That task lists Lokesh Doggala's LinkedIn as `linkedin.com/in/lokesh-r-a899a247`, which matches the
booth registration exactly. He is now a live opportunity with a call pending, so a generic Tier-1
connection note would land oddly. Suggest handling him outside the batch.
