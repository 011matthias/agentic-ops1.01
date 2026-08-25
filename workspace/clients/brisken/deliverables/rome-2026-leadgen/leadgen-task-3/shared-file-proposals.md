# Shared-file change proposals (task 3, not applied)

Task 3 runs under parallel-execution isolation, so nothing below was edited.
Each item is a proposal for whoever owns the shared file.

Trigger: Planner task **"Exclude BTP from all demos"** (id `mJrjdoY1yUKp0gNxDld7LWUAAL_e`,
open, 0%). Dirk's directive, verbatim from the task description:

> Dirk's directive: leave SAP BTP (Business Technology Platform) out of all demo
> materials. Review the existing decks and demos and remove BTP content.

The Sanofi collateral is demo material, so the directive binds it. Rather than ship
a deck that contradicts a live directive, task 3 built BTP-clean copies inside
`output/leadgen-task-3/collateral-pack/`. The shared originals are untouched and
still carry BTP.

## Verified BTP inventory

Counts are `grep -ci btp` for sources and `pypdf` extracted-text `\bBTP\b` matches
for rendered PDFs, run 2026-07-09.

### Build sources (`.scratch/`, gitignored, shared across tasks 2 and 3)

| File | BTP refs | Nature |
|---|---|---|
| `deckgen/build-treasurycentral.js` | 2 | architecture line (slide 5), "Built into SAP" card (slide 9) |
| `deckgen/build-mdh.js` | 2 | same two positions |
| `deckgen/build-digital-coworker.js` | 2 | same two positions |
| `deckgen/build-mdh-commodities.js` | 1 | architecture line |
| `deckgen/build-smart-trading.js` | 0 | already clean |
| `brisken-sap-assets/gen_onepagers.py` | 5 | `TRUST` chip row (line 125) plus four OnePilot product entries (lines 219, 225, 229, 231) |

The `TRUST` chip on line 125 is shared by all six one-pagers, so removing that one
list entry cleans five of them at once. The OnePilot one-pager is different: BTP is
load-bearing in its eyebrow, its architecture target, and two capability lines, so it
needs a content decision, not a deletion.

### Rendered artifacts

| File | BTP refs |
|---|---|
| `rome-2026/call-collateral/brisken-treasurycentral-sanofi.pdf` + `.pptx` | 2 |
| `rome-2026/call-collateral/brisken-treasurycentral-zalando.pdf` + `.pptx` | 2 |
| `rome-2026/dirk-send-pack/brisken-digital-co-worker.pdf` | 2 |
| `rome-2026/dirk-send-pack/brisken-market-data-hub.pdf` | 2 |
| `rome-2026/dirk-send-pack/brisken-mdh-commodities.pdf` | 1 |
| `rome-2026/dirk-send-pack/brisken-smart-trading.pdf` | 0 |
| `sap-assets/brisken-onepilot-onepager.pdf` | 5 |
| `sap-assets/brisken-{bank-fee-portal,market-data-hub,remittance-advice-gate,smart-trading,treasurycentral}-onepager.pdf` | 1 each |

## Proposal 1: APPLIED UPSTREAM 2026-07-09, by another session

Superseded while this document was being written. A parallel session edited
`build-treasurycentral.js` at 20:23, rebuilt both prospect decks at 20:24 and refreshed the
`call-collateral/README.md` at 20:26. Verified independently: the shared
`brisken-treasurycentral-sanofi.pdf` and `brisken-treasurycentral-zalando.pdf` now both
extract **zero** `\bBTP\b` matches. The Zalando defect is closed too.

Their wording differs from the proposal below. They cut "BTP and HANA" down to "SAP's own
cloud" and, on the architecture slide, to "runs inside your SAP landscape". This document's
version kept "SAP HANA". Both are BTP-free; theirs is the one that shipped.

The proposal text is kept below only because proposals 2 and 3 reference the same edit
pattern.

### The edit, as applied

Two string edits. Task 3 applied exactly these in its task-local copy
(`output/leadgen-task-3/build/build-treasurycentral-sanofi.js`) and verified the
rendered PDF drops to zero BTP matches while keeping HANA, the co-innovation-partner
claim, and the inside-not-beside framing.

Line 189:

```diff
-  s.addText("runs on SAP BTP and HANA,\nchecks and logs every value", ...
+  s.addText("runs on SAP HANA,\nchecks and logs every value", ...
```

Line 265:

```diff
-    ["shield","Built into SAP","An SAP co-innovation partner. The cockpit runs on SAP's own cloud, BTP and HANA, so it sits inside your landscape, not beside it."],
+    ["shield","Built into SAP","An SAP co-innovation partner. The cockpit runs on SAP HANA, so it sits inside your landscape, not beside it."],
```

The second edit also drops "SAP's own cloud", which described BTP specifically and
reads as dangling once BTP is gone.

Both prospects share this file, so applying it fixes the Zalando deck in the same
change. Rebuild with `node build-treasurycentral.js sanofi` and `... zalando`, then
re-export the PDFs.

## Proposal 2: `.scratch/brisken-sap-assets/gen_onepagers.py`

Line 125, remove one list entry:

```diff
-TRUST = ["<b>SAP</b> Co-Innovation Partner","SAP Store","SAP BTP","<b>ISO 27001</b>","<b>SOC 1 Type II</b>","live with customers today"]
+TRUST = ["<b>SAP</b> Co-Innovation Partner","SAP Store","<b>ISO 27001</b>","<b>SOC 1 Type II</b>","live with customers today"]
```

Task 3 verified this on its task-local one-pager: single page preserved, BTP gone,
and the Co-Innovation Partner, SAP Store, ISO 27001 and SOC 1 chips all still render.

### The OnePilot entry: no decision needed after all

An earlier version of this document said lines 219, 225, 229 and 231 needed Dirk's call on
what replaces BTP. Owner correction 2026-07-09: **nothing replaces it.** BTP is omitted
because it does not sell a treasurer, and it can be named in conversation if a client
presses. So this is a mechanical edit, not a positioning question.

The `target(big, sub)` helper takes a destination descriptor, never a platform name. Every
other one-pager passes "SAP and non-SAP", "SAP S/4HANA", "Inside SAP", "On your SAP data".
The OnePilot entry is the only one that puts a platform there.

```diff
-   name_html="One<span class='ac'>Pilot</span>", eyebrow="The AI layer &middot; on SAP BTP",
+   name_html="One<span class='ac'>Pilot</span>", eyebrow="The AI layer",
...
-     target("SAP BTP","bi-directional, SAP and non-SAP")),
+     target("Inside SAP","bi-directional, SAP and non-SAP")),
...
-     "Codeless framework: build your own apps and automation on SAP BTP without a line of code.",
+     "Codeless framework: build your own apps and automation without a line of code.",
...
-   caps=["on SAP BTP","SAP + non-SAP","four-eye + SoD","manage by exception"]),
+   caps=["inside SAP","SAP + non-SAP","four-eye + SoD","manage by exception"]),
```

"Inside SAP" is already in use on the Remittance Advice Gate one-pager, so it forks no new
vocabulary. The caps list stays at four entries, which the layout expects.

Together with the `TRUST` chip removal above, this takes `gen_onepagers.py` from 5 BTP
references to zero, and the six rendered one-pagers to zero. Regenerate and assert
`re.findall(r"\bBTP\b", text, re.I) == []` on each, plus the single-page check the script
already performs.

## Proposal 3: rebuild the artifacts

After proposals 1 and 2, re-render and re-verify:

- `deckgen/pdf-export.py` for the pptx set
- `brisken-sap-assets/gen_onepagers.py` for the one-pagers
- confirm with the same check task 3 used:
  `pypdf` extract, assert `re.findall(r"\bBTP\b", text, re.I) == []`

`build-mdh.js`, `build-digital-coworker.js` and `build-mdh-commodities.js` carry BTP
at the same two slide positions and take the same edit. Task 3 did not touch them:
they belong to the "Exclude BTP from all demos" task, and the Sanofi pack does not
attach them.
