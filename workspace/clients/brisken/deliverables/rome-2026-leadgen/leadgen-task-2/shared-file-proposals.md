# Changes to shared files: APPLIED 2026-07-09

Written first as unapplied proposals under the task-2 isolation rules. The owner then directed the
SharePoint replacement, which superseded the isolation constraint for these four items. All are applied.

## 1. `.scratch/deckgen/build-treasurycentral.js`: SAP BTP removed (APPLIED)

Dirk's directive, recorded on the open Planner task "Exclude BTP from all demos": "leave SAP BTP
(Business Technology Platform) out of all demo materials." Both prospect variants inherited BTP from the
shared slide code.

Line 189, slide 5 (architecture):

```diff
-  s.addText("runs on SAP BTP and HANA,\nchecks and logs every value", ...
+  s.addText("runs inside your SAP landscape,\nchecks and logs every value", ...
```

Line 265, slide 9 (who we are):

```diff
-    ["shield","Built into SAP","An SAP co-innovation partner. The cockpit runs on SAP's own cloud, BTP and HANA, so it sits inside your landscape, not beside it."],
+    ["shield","Built into SAP","An SAP co-innovation partner. The cockpit runs on SAP's own cloud, so it sits inside your landscape, not beside it."],
```

## 2. `.scratch/deckgen/build-treasurycentral.js`: Zalando migration claim softened (APPLIED)

```diff
-    proofExtra: "Your S/4HANA migration is the moment these feeds get decided; ...",
+    proofExtra: "An S/4HANA move is the moment these feeds get decided; ...",
```

"Your S/4HANA migration" asserted that Zalando has one in flight. No source in the repo says so; the only
public evidence is a consenso S/4Finance readiness check published 2018-09-20, which found the move
feasible and recommended greenfield. Whether it ever happened is unknown.

## 3. Both decks rebuilt and replaced, in the repo and in SharePoint (APPLIED)

`call-collateral/brisken-treasurycentral-{sanofi,zalando}.{pptx,pdf}` regenerated from the corrected
source. Sanofi had no clean build before this; its only change is the BTP removal.

The four files in SharePoint `2026_PPTX/Client Collateral` were overwritten at 18:25 UTC. Verified by
byte identity on the PDFs, which SharePoint does not rewrite:

| File | Now | Superseded BTP render |
|---|---|---|
| `Brisken - TreasuryCentral - Sanofi 2026.pdf` | 234,137 | 234,172 |
| `Brisken - TreasuryCentral - Zalando 2026.pdf` | 234,466 | 233,228 |

Both re-extract to 10 slides, 0 hits on "BTP", 0 em-dashes. The PPTXs re-list at 649,606 and 649,607;
SharePoint rewrites Office files on upload, so their size proves nothing either way.

The folder link Dirk was sent still resolves. Only the contents changed, and he has not been told.

## 4. `call-collateral/README.md`: two corrections (APPLIED)

Lokesh's title dropped from the table. Three of our sources disagree ("Treasury Consultant" in the booth
registration, "Senior Treasury Consultant" in the Tier-1 list, "SAP Consultant, Corporate Solutions" in
Dirk's forward) and none is verified. The Zalando tailoring row now describes the proof line as an
S/4HANA move stated conditionally, and the README carries a standing note that these decks contain no BTP.

## Not fixed, and still shipping BTP

The three module decks have their own build scripts and were out of scope here:
`brisken-market-data-hub.pdf` (2 hits), `brisken-digital-co-worker.pdf` (2), `brisken-mdh-commodities.pdf`
(1). `brisken-smart-trading.pdf` is clean. Market Data Hub and Digital Co-Worker are the likely Zalando
follow-up attachments, so this still blocks the back half of the task. They belong to the open "Exclude
BTP from all demos" task.
