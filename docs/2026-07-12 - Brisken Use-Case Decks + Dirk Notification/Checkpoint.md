# Checkpoint: Brisken Use-Case Decks + Dirk Notification

**Date:** 2026-07-12
**Status:** COMPLETE — 3 use-case decks built, QA'd, shipped to SharePoint; TreasuryCentral decks audited + patched; notification email sent to Dirk and logged.

---

## Summary
Built three OnePilot use-case scenario decks (Intercompany Funding Request, Remittance Advice, Market Data Monitor) from the product catalog, ran a fresh-eyes audit across all deck assets, fixed a pre-existing s04 logo-over-text overlap on the Sanofi/Zalando prospect decks, saved everything into SharePoint Client Collateral WIP, and sent Dirk a notification email with real hyperlinks.

---

## What Was Done This Session
### Use-case decks (new)
1. New generator `.scratch/deckgen/build-usecases.js` — 3 decks x 9 slides, dark-cockpit system (verbatim primitives from `build-treasurycentral.js`). Content grounded in `brisken-product-catalog.md` (Calvin demo, Remittance Advice Gate, MDH monitor/scheduler). Scenario slides carry an amber ILLUSTRATIVE SCENARIO tag; product-fact stat bars only; no Evonik/RWZ/BTP; ICE dropped from the use-case provider strips.
2. Two subagent QA rounds (fresh eyes) + fix cycle: page-number format, footer spacing, stat-row balance, logo strips, close-slide wordmark legibility, 2 widow lines.

### TreasuryCentral audit + patch
3. Fresh-eyes audit of all 35 TC slides. My earlier patches (TBD/GCG removals, glow shift) all confirmed clean. One pre-existing HIGH surfaced: prospect decks slide 4 (WHAT RUNS IN IT) had the Market Data Hub provider logo strip overlapping the 3rd body line.
4. Fixed via `patch-tc-s04.py` (trim card body to 2 lines so the strip clears) on live san/zal, and at source in `build-treasurycentral.js`.

### Ship + notify
5. Uploaded 3 use-case decks (pptx+pdf) + re-fixed san/zal to `2026_PPTX/Client Collateral WIP`; refreshed the root `2026_PPTX` use-case copies. Verified by re-list.
6. Fetched durable SharePoint links; sent notification email Matthias -> Dirk from Matthias's Outlook (verified in Sent Items 2026-07-12 12:36), logged verbatim to comms-log.

---

## Key Decisions Made
### Use-case deck location
- **Choice:** Placed the 3 decks in BOTH root `2026_PPTX` (from the first "next to the product assets" ask) and `Client Collateral WIP` (the later "with the TC assets" ask); Dirk's email points at Client Collateral WIP.
- **Rationale:** "also save with the TC assets" read as additive; keeping both is non-destructive; cdp-sp-io.py has no delete mode. Flagged the duplication to the owner for a one-word consolidation.

### Fix the s04 overlap despite being pre-existing
- **Choice:** Fixed the Sanofi/Zalando s04 overlap even though it predates my edits.
- **Rationale:** A logo-over-text overlap on decks Dirk may send to prospects is exactly what the audit was for; surgical python-pptx patch preserves Dirk's XML transplants; also fixed at source.

### Email is a notification, not an essay
- **Choice:** Rewrote the Dirk email from prose to lead-line + bullets + real hyperlinks after the owner correction.
- **Rationale:** `feedback_dirk_email_notification_style.md` (owner directive 2026-07-11). Missed on first draft (friction, logged).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.scratch/deckgen/build-usecases.js` | Created | Generator for the 3 use-case decks (gitignored) |
| `.scratch/deckgen/build-treasurycentral.js` | Modified | s04 body trim + Evonik removal + glow-down (source hygiene) |
| `.scratch/deckgen/build-tc-generic.js` | Modified | Removed TBD chips + GCG text chip + glow-down at source |
| `.scratch/deckgen/patch-tc.py`, `patch-tc-s04.py` | Created | In-place python-pptx fixes for live TC decks |
| `.scratch/cdp-sp-io.py` | Modified | `SP_FOLDER` env var for subfolder uploads |
| `.scratch/deckgen/_sp_download.py` | Modified | Added `Target.activateTarget` (fixes "Failed to fetch") |
| `workspace/clients/brisken/.../call-collateral/*` | Modified | Committed mirror: 3 use-case + refreshed sanofi/zalando (pptx+pdf) |
| `workspace/clients/brisken/context/comms-log.md` | Modified | Sent Dirk email logged verbatim |
| `workspace/clients/brisken/context/decks/sharepoint-2026-07-10/*` | Modified | Deck mirror refreshed |
| `memory/project_brisken_product_decks_restructured.md` | Modified | Session state (audit, s04 fix, locations, email) |
| `memory/reference_user_edge_cdp_9222.md` | Modified | `Target.activateTarget` requirement note |

External (not repo): SharePoint `2026_PPTX` + `2026_PPTX/Client Collateral WIP` — 6 use-case files + refreshed san/zal.

---

## Current Status
All three use-case decks are live in SharePoint (root product folder + Client Collateral WIP), the Sanofi/Zalando prospect decks have the s04 overlap fixed, and Dirk has been notified by email (sent + verified + logged). Nothing pending from this thread; Dirk reviews at his own pace.

Brisken orchestrator = fastapi (expense-recon p1 + lead-gen p2, both live); no Make/n8n ops-limit surface, so no ops audit needed.

---

## Next Steps
1. If a single home is wanted for the use-case decks, drop the root `2026_PPTX` copies (they duplicate Client Collateral WIP) — needs a recycle path (cdp-sp-io.py has no delete mode yet).
2. Standing lead-gen (from prior checkpoint): T3 email wave, staged-draft watch, Tradeweb nudge ~Jul 15, optional Rome one-pager restyle.
3. If Dirk supplies real data-volume / time-saved numbers, slot them into the generic TreasuryCentral stat slots (still open from 2026-07-11).

---

## Context for Next Session
### Files to Read First
- `memory/project_brisken_product_decks_restructured.md` (full deck state, generators, locations, banned-terms rules)
- `memory/feedback_dirk_email_notification_style.md` (Matthias->Dirk email format — apply BEFORE drafting)
- `workspace/clients/brisken/context/comms-log.md` (latest thread)
- `.scratch/deckgen/build-usecases.js` + `build-treasurycentral.js` (the surviving generators)

### Open Questions
- Use-case decks: keep in both root `2026_PPTX` + Client Collateral WIP, or consolidate to one? (flagged to owner)
- ICE logo renders clipped at chip size on the prospect decks' s04 strip; left as-is (Dirk's content). Drop it there too for consistency, or leave?

### Working Notes
- `_sp_download.py` failed twice with "TypeError: Failed to fetch" until `Target.activateTarget` was added after `createTarget` — a fresh CDP tab must be activated or its page-context `fetch` dies (throttled background). `cdp-sp-io.py` always had activate; the downloader did not. Now noted in `reference_user_edge_cdp_9222`.
- PDFs have `null` LinkingUri in SharePoint (only Office docs get one); the email links the pptx per deck + the folder link for the PDFs.
- python-pptx text edits: set `runs[0].text` and blank the rest of the paragraph's runs to avoid split-run artifacts (used in all patch scripts).
- SharePoint rewrites pptx bytes on upload; verify by re-listing SIZE, not hash (PDF size is a fingerprint).

### Reference Materials
- SharePoint folder: `.../2026_PPTX/Client Collateral WIP`
- `brisken-product-catalog.md` (source for all deck content)

---

## How to Continue
Deck work is closed pending Dirk's review. If he asks for edits: edit the SharePoint pptx directly OR adjust the generator + re-patch + re-upload via `cdp-sp-io.py` (set `SP_FOLDER` for the subfolder). For any new Matthias->Dirk email, load `feedback_dirk_email_notification_style` and run `agnt_comms-critic` on the draft before presenting.

---

## Strategic Feedback

### What Worked Well This Session
- The subagent fresh-eyes audit caught a real pre-existing HIGH defect (s04 overlap) that the build-and-verify loop had missed — independent QA earned its keep.
- Fixing generators at source alongside the live-file patches prevents the defects from regenerating (self-annealing).

### Suggestions
- The `agnt_comms-critic` gate should run automatically on any Matthias->Dirk draft; running it this session would have caught the essay-format email before the owner did.

### System Health
- `missed-memory-recall` remains the dominant friction class (this is the ~6th brisken instance in 3 days). The pattern: correct memory exists on disk, recall misses it at decision time. Structural kill candidates keep being logged (edge_cdp.py helper, comms-critic auto-gate) but not built — trending toward `infrastructure-deferred`.
- Autonomy score: 2 human interventions this session.
