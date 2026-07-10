# Checkpoint: Brisken OnePilot Deck Restructure

**Date:** 2026-07-08
**Status:** Complete — decks restructured, deployed to Dirk's drafts + SharePoint, hours logged

---

## Summary
Rebuilt Brisken's three OnePilot product decks (Market Data Hub, Digital Co-Worker, Smart Trading) into one dark-cockpit visual system, swapped the new versions onto Dirk's three Rome hottest-lead drafts in place of the rejected 2024 renders, confirmed the drafts sync to his Exchange server, and saved all three decks to the Brisken SharePoint presentations folder with verified shareable links.

---

## What Was Done This Session

### Decks
1. Extracted the source content from the old 2024 decks (`context/Products/Brisken - MDH Overview Presentation 240816.pptx`, `Digital Co-Worker.pptx`).
2. Built restructured **MDH** (12 slides) and **Digital Co-Worker** (10 slides) decks in `.scratch/deckgen/` (pptxgenjs), matching the already-approved Smart Trading treatment (same cover/about/problem/agnostic/architecture/pipeline/governance/onepilot/close spine, cyan `#3BE3E0`, plain-language rewrite, zero em-dashes).
3. Rendered all three pptx to PDF + per-slide PNG via **PowerPoint COM** (no LibreOffice on this box); QA'd every slide visually, fixed two stat-row wrap glitches (`360°`, `24/7`) and the DCW footer count.

### Dirk's live drafts (Outlook COM)
4. Swapped attachments on the three Rome drafts, matched by **recipient** (not subject/body, since Dirk had edited the wording): JTI → `brisken-market-data-hub.pdf`, Adidas → `brisken-digital-co-worker.pdf`, VW/Michael → `brisken-smart-trading.pdf` (new attachment, per owner approval).
5. Proved wording untouched: MD5 of Body + HTMLBody + Subject identical before/after on all three (attachment-only change).
6. Confirmed server sync: safe upload (Outbox empty → nothing sent), connection moved to Online (700); drafts now visible on Dirk's OWA/phone, attachments embedded ByValue.

### SharePoint
7. Located the target folder via authenticated REST + Search (it is under `20_Assets`, not the library root): `/sites/MARKETING/Shared Documents/20_Assets/BRISKEN PRESENTATIONS/OnePilot - Cloud Solutions Presentations`.
8. Uploaded the three pptx via the REST `Files/add` API from the user's authenticated Edge (CDP :9222, Playwright connect_over_cdp), named `Brisken - Smart Trading 2026.pptx`, `Brisken - Market Data Hub 2026.pptx`, `Brisken - Digital Co-Worker 2026.pptx`.
9. Verified functionally: downloaded each back, opened with python-pptx, correct slide counts (12/12/10) and covers. (MD5 won't match source — SharePoint injects doc-property bytes on upload.)
10. Generated + verified a folder deep-link and three direct file links for Dirk.

### Housekeeping
11. Deleted the three rejected 2024 renders; refreshed the send-pack README + its PDF; logged **2.5h** to the July Lead Generation tab (deck restructure 07-07 1.0h; SharePoint 07-08 1.5h); wrote 2 memories.

---

## Key Decisions Made

### Attachment-only draft swap, matched by recipient
- **Choice:** Change only the attachment on each draft; match drafts by To address; hash the body before/after.
- **Rationale:** Dirk had manually edited the draft bodies. Attachment-only + recipient-match + hash-proof guarantees his wording is never touched.

### SharePoint via REST from the user's live browser, not the SPA UI
- **Choice:** Drive the user's authenticated Edge over CDP :9222 with Playwright and call the SharePoint REST API directly.
- **Rationale:** The BRISKEN library is not synced locally (OneDrive Business unconfigured), no credentials available, and the SPA upload UI is fragile. REST `Files/add` + `$value` download is reliable and verifiable. See `reference_user_edge_cdp_9222`.

### PPTX only, not the matching PDFs, into Dirk's live library
- **Choice:** Uploaded the three `.pptx` only (the explicit ask); did not add PDFs.
- **Rationale:** Adding unrequested files to a client's official library is an invasive write; kept scope to what was asked.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../rome-2026/decks/brisken-{market-data-hub,digital-co-worker,smart-trading}.pptx` | Created (untracked) | editable restructured deck sources |
| `.../rome-2026/dirk-send-pack/brisken-{market-data-hub,digital-co-worker,smart-trading}.pdf` | Created (untracked) | client-facing renders |
| `.../dirk-send-pack/brisken-{market-data-hub-overview,ai-digital-coworker,trade-automation-overview}.pdf` | Deleted | rejected 2024 renders superseded |
| `.../dirk-send-pack/README.md` + `rome-hottest-leads-send-pack.pdf` | Modified | reflect the restructured decks |
| `.scratch/deckgen/build-{mdh,digital-coworker}.js` | Created (gitignored) | deck build scripts |
| `workspace/hours-tracker/hours-tracker-2026-07-july.xlsx` | Modified | +2 Lead Generation rows (2.5h) |
| `memory/project_brisken_product_decks_restructured.md` | Created | deck-set canonical record |
| `memory/reference_user_edge_cdp_9222.md` | Created | reusable browser-CDP capability |
| Dirk's Outlook (3 drafts) · SharePoint (3 pptx) | Live-system writes | the actual deliverables |

---

## Current Status
All three restructured decks are live in three places: on Dirk's Rome drafts (JTI/Adidas/VW, server-synced, drafts-only, nothing sent), in the repo (`rome-2026/decks/` pptx + `dirk-send-pack/` pdf, untracked), and in Brisken SharePoint (`OnePilot - Cloud Solutions Presentations`, functionally verified). July Lead Generation tab: 13.0h / EUR 182.00 total (my 2.5h + the parallel session's 10.5h), Excel-verified, no overlaps.

No orchestrator/scenario state touched. brisken p2 lead-gen is manual-first; sends stay 1:1 from dirk.neumann@brisken.com.

---

## Next Steps
1. **(Optional) Add the matching PDFs to SharePoint** — the folder convention pairs `.pdf` + `.pptx`; only pptx uploaded per the ask. One run if Matthias wants the three PDFs added.
2. **Rome Tier-1 send** still gates on Dirk's JTI volume figure + his approval; drafts (with the new decks) are ready in his Outlook.
3. Booth-network Tier-3 outreach (parallel session) awaits Dirk approval to load ~17 drafts.
4. Downstream lead-gen threads: SAP PartnerFinder + Discovery Center reposition, 1Proposal synopsis, gated interim proposal page, Rome Tiers 2-4.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/deliverables/lead-generation/rome-2026/dirk-send-pack/README.md` — the send-pack v2 map (which deck goes to which lead)
- `.scratch/deckgen/build-smart-trading.js` — the deck design system (template for any future Brisken deck)
- `memory/project_brisken_product_decks_restructured.md` + `memory/reference_user_edge_cdp_9222.md`

### Open Questions
- Does Matthias want the three matching PDFs in SharePoint too? (folder pairs pdf+pptx; only pptx uploaded)
- Rome Tier-1: still waiting on Dirk's JTI volume figure before those drafts send.

### Working Notes
- Deck sources live in gitignored `.scratch/deckgen/`; if scratch is cleaned, the build scripts vanish (memory has the pointer). Editable pptx are committed-adjacent in `rome-2026/decks/` (untracked).
- SharePoint: MD5 of an uploaded Office file never matches the source (doc-property injection); verify by re-opening (slide count), not by hash.
- The user's Edge runs with `--remote-debugging-port=9222` and is logged into brisken M365 as Matthias.Silva — drive it via Playwright `connect_over_cdp` + `contexts[0]` for any authenticated web task (agent-browser `--auto-connect` is isolated and won't reuse the session).
- Concurrency: two parallel sessions wrote the shared July hours xlsx today; my deck row initially double-booked an hour with the other session's row, caught + fixed (shrank mine to 19:00-20:00). The log tool places rows but does not reject cross-row time overlaps.

### Reference Materials
- SharePoint folder: `https://brisken.sharepoint.com/sites/MARKETING/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2FMARKETING%2FShared%20Documents%2F20_Assets%2FBRISKEN%20PRESENTATIONS%2FOnePilot%20-%20Cloud%20Solutions%20Presentations`

---

## How to Continue
The deck work is closed. Pick up the open Brisken lead-gen threads (Rome Tier-1 send once Dirk supplies the JTI volume figure, booth-network approval, SAP surfaces) or, if asked, add the three matching PDFs to the SharePoint folder with the same REST-over-CDP path.

---

## Strategic Feedback

### What Worked Well This Session
- The "restructure like Smart Trading" instruction gave a concrete design anchor, so the two new decks matched a known-good target with no ambiguity.
- Granting the CDP-attached browser + explicit per-action SharePoint go unblocked a task with no local sync and no credentials.

### Suggestions
- If future decks are common, promote the `.scratch/deckgen/` build scripts into a tracked `tools/` deck-builder so they survive a scratch clean.

### System Health
- `log-brisken-hours.py` places rows but does not check for **time overlaps** against existing rows; with parallel sessions writing the same monthly xlsx, that let a 20:00-21:00 hour double-book (caught + fixed manually). Structural fix candidate: reject/warn on an overlapping (date, start-end) window on `--add`.
- Autonomy score: 1 human-visible intervention (concurrency overlap, self-detected + fixed). Otherwise autonomous across a long multi-part session (decks → drafts → SharePoint → hours).
