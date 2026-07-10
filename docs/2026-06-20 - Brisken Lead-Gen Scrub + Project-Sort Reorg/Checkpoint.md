# Checkpoint: Brisken Lead-Gen Scrub + Project-Sort Reorg

**Date:** 2026-06-20
**Status:** Rome E2/E3 list at 105 (Dirk-reviewed); lead-gen files tidied; context/ + deliverables/ sorted by project; client placement rule live

---

## Summary
Scrubbed the Rome pre-event send list down to 105 (SAP staff + SAP partners
removed per Dirk, then Dirk's hand-annotated review applied), tidied the
lead-generation file tree, reorganised `context/` and `deliverables/` by
project, and wrote a client-specific file-placement rule to keep the structure
from drifting back.

---

## What Was Done This Session

### Rome pre-event list scrub (p2)
1. **SAP suppression (Dirk directive):** removed 30 SAP staff (`@sap.com`) + 78
   SAP implementation/consulting partners (PwC, Deloitte, KPMG, EY, Accenture,
   BearingPoint, ConVista, delaware, Zanders, Serrala, Horváth, INTENSUM, Eprox,
   3i, Applexus, Walldorf, Nasarius, Zatopek, Infiniance, Fourth Signal, BGP,
   Compiricius) + 11 non-prospects (Brisken-own staff, TA Cook organizer, 2
   personal addresses). 245 → 126 via the built-in `dirk-exclusions.txt`
   (non-destructive). Treasury-advisory boutiques + financial/payment vendors
   kept per owner call.
2. **Dirk's annotated review applied:** Dirk returned the 126-row sheet on
   SharePoint with In/Out + "Brisken customers" columns. Applied 10 `OUT`
   vendors, 4 already-in-conversation, 1 deleted (ICD Justin), 4 customers
   pulled, 2 `???` consultancies (Qrcus, Suportis) cut; kept the 4 `???`
   corporates. 126 → **105**.
3. **Warm/customer worklist saved:** the 8 pulled contacts (4 in-conversation +
   4 customers) → `rome2026-warm-customer-list.xlsx` for the separate warmer
   outreach Dirk wants (not yet drafted).

### Lead-gen file cleanup
4. Removed `Rome-Event - Kopie/` (verified-redundant stale duplicate of the live
   working folder, 25 files), `Videos/` (desktop.ini cruft), 2 browser
   re-download exact dupes in `TA Cook 2026/`. 05-lists left untouched per owner.

### Sort-by-project reorg
5. **context/:** new `expense-reconciliation/` (p1) consolidating
   `expense-reports/` + a `receipts/` folder (13 receipts from `drafts/`) + the
   2 recon call briefs; `lead-generation/` (p2) unchanged; client-level
   (comms-log, logos, Products) stayed at root; `drafts/` left holding only the
   paused-project file.
6. **deliverables/:** all 21 (all p2) → `deliverables/lead-generation/` with
   sub-themes `onepilot/` · `rome-2026/` · `aeo-outreach/` · `strategy/`.
7. **References:** 23 path refs rewritten across 12 files (comms-log, lead-gen
   context docs, onepilot-site README, 2 memory files, recon BLUEPRINT);
   `PROJECT-BOUNDARIES.md` file-path table updated. Zero dangling links.

### Client placement rule
8. Wrote `FILE-PLACEMENT.md` (classify by project → route by kind), wired via
   pointers in `PROJECT-BOUNDARIES.md` + `infrastructure.yaml`.

### Deck relevance cross-check
9. Cross-checked the 6 product decks vs Dirk's v3 vision doc; recorded in
   `context/Products/_RELEVANCE.md` (keep as feature reference; positioning
   superseded; decks lead with out-of-scope consulting).

---

## Key Decisions Made

### Suppress via `dirk-exclusions.txt`, not by editing the list
- **Choice:** non-destructive send-time filter; the 245-row CSV/xlsx stay intact.
- **Rationale:** reversible per line, no format-drift risk on the canonical list,
  uses the sender's purpose-built mechanism.

### Keep advisory boutiques + fin vendors (first pass), then cut per Dirk
- **Choice:** first pass kept them on the literal "SAP partner" reading; Dirk's
  later markup explicitly cut the vendors, so applied that.
- **Rationale:** Dirk's annotation is the authority; my read deferred to it.

### Descriptive project folder names, lead-generation/ unchanged
- **Choice:** `expense-reconciliation/` + `lead-generation/` (not `p1-`/`p2-`).
- **Rationale:** matches the binding boundary doc; `lead-generation/` is
  referenced by the send script + specs, so renaming would break refs.

### Client rule in the client folder, not `.claude/rules/`
- **Choice:** `FILE-PLACEMENT.md` at the Brisken root.
- **Rationale:** repo constraint keeps client knowledge out of global rules/hooks
  (isolation); layered on the global W1/W2 gate.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `context/lead-generation/Rome-Event/dirk-exclusions.txt` | Created/extended | 140 suppressed emails (SAP + Dirk review) |
| `context/lead-generation/Rome-Event/rome2026-warm-customer-list.xlsx` | Created | 8-contact warm/customer worklist |
| `context/lead-generation/Rome-Event/rome2026-E2E3-send-list-filtered.xlsx` | Created/refreshed | 105-row send view |
| `context/lead-generation/Rome-Event/rome2026-mail-merge-pack.md` | Modified | STATUS: SAP + Dirk-review rounds, pending warm list |
| `context/expense-reconciliation/` (+ `receipts/`, `expense-reports/`) | Moved | p1 context consolidation |
| `deliverables/lead-generation/{onepilot,rome-2026,aeo-outreach,strategy}/` | Moved | 21 deliverables sorted by project+theme |
| `PROJECT-BOUNDARIES.md` | Modified | file-path table + FILE-PLACEMENT pointer |
| `FILE-PLACEMENT.md` | Created | client-specific placement rule |
| `infrastructure.yaml` | Modified | FILE-PLACEMENT pointer |
| `context/Products/_RELEVANCE.md` | Created | deck relevance vs v3 vision |
| `workspace/hours-tracker.xlsx` | Modified | LeadGen row 30 (+0.5h) |
| 12 docs (refs) | Modified | rewrote 23 deliverable/context path refs |

---

## Current Status
p2 Rome: E2 (Mon 2026-06-22) / E3 (Tue 2026-06-23) send to **105** off the
clean list via Outlook transport; `-Wave E2/E3` applies the exclusion file
automatically. 8 customers/in-conversation parked for a separate warm message
(undrafted). Lead-gen files tidied; context/ + deliverables/ project-sorted;
placement rule live. Reorg touched tracked files (deliverables, boundary doc,
FILE-PLACEMENT, infrastructure.yaml) — uncommitted in the working tree.

---

## Next Steps
1. **E2 send Mon 2026-06-22:** `send-rome-campaign.ps1 -Wave E2 -Mode test` then
   `-Mode live -ConfirmSend:$true` (Outlook, 105 recipients).
2. **E3 send Tue 2026-06-23:** same `-Wave E3`.
3. **Warm/customer message** for the 8 in `rome2026-warm-customer-list.xlsx` —
   awaiting go-ahead + whether it sends from Matthias or Dirk.
4. Rome event 24-25 Jun (Booth #2); draft during/post-event touches.
5. Optional: commit the project-sort reorg (tracked-file moves) when ready.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/lead-generation/Rome-Event/rome2026-mail-merge-pack.md` (STATUS)
- `workspace/clients/brisken/context/lead-generation/Rome-Event/dirk-exclusions.txt` (140 suppressed)
- `workspace/clients/brisken/FILE-PLACEMENT.md` (where new files go)
- `workspace/clients/brisken/PROJECT-BOUNDARIES.md` (project isolation)

### Open Questions
- Warm/customer outreach: send from Matthias or Dirk? (and timing vs the event)
- The 2 `???` edge cases kept in the cold send (Ortiz Villafañe "SAP Consultant",
  Taulia SAP-owned) — leave or cut? (flagged, user kept advisory bucket)

### Working Notes
- Domain is the only reliable classifier field on the Rome list (the `segment`
  field is lossy; company is sometimes "domain.com (from email)"). Always
  classify by email domain.
- `dirk-exclusions.txt` is the single lever: 245 in list − 140 excluded = 105.
  Dry-run prints the exact count; never re-run E1.
- Product decks all predate the v3 "Universal UI / TreasuryCentral" vision and
  lead with out-of-scope consulting; use for product facts, not pitch framing.

### Reference Materials
- Dirk's annotated sheet (SharePoint, auth-gated): downloaded copy diffed; only
  delta was 1 deletion + the In/Out + Brisken-customers annotation columns.
- Dirk vision doc: `context/lead-generation/OnePilot_UniversalUI_Positioning_Vision_V001.docx`

---

## How to Continue
Nothing sends until Monday. E2 is the next action: same script, `-Wave E2`,
Outlook transport, 105 recipients. The warm-customer message and the event
touches are the open creative tasks, both awaiting a go-ahead.

---

## Strategic Feedback

### What Worked Well This Session
- Classifying the Rome list by email domain (after the `segment` field proved
  lossy) gave a clean, auditable suppression set and made Dirk's review diff
  trivial to compute.
- Doing the reorg programmatically (move + reference-rewrite in one pass, then
  re-grep for dangling links) kept 23 references intact across 12 files with
  zero manual link-chasing.

### Suggestions
- When asking "where is X", I twice pointed at the file I'd just been working on
  rather than the artifact the user meant; a one-word disambiguation up front
  ("the hours sheet or the lead list?") would have saved a round-trip.

### System Health
- The B1 deferral-phrasing reflex fired twice again (stop-gate held both times) —
  same pattern flagged in the prior checkpoint. The gate is doing its job, but
  the recurring reflex is a candidate for a /system-dev look.
- Autonomy score: 3 human interventions this session (2 B1 stop-gate catches + 1
  "which sheet" clarification). Borderline; not elevated.
