# Checkpoint: Brisken MDH Commodities Case-Study Deck + Planner Tasks

**Date:** 2026-07-08
**Status:** In progress. Commodities deck drafted but TOO LONG (needs a drastic cut, next chat). Planner tasks added + verified. WhatsApp directive logged.

---

## Summary
Picked up the Brisken Market Data Hub follow-up. Transcribed Dirk's WhatsApp voice note (the commodity price-curve case study, hard "never name ADM" constraint), built a first draft of a SEPARATE commodities case-study deck, and added this session's lead-gen tasks to the shared MARKETING PLAN in Microsoft Planner. Deck draft came out far too long; the corrected direction and everything needed to finish it are in `Continuation-Prompt.md`.

---

## What was done

### 1. Dirk's WhatsApp voice note (transcribed + logged)
- Source: `iCloudDrive/UnpauseAI/Brisken_/WhatsApp Audio 2026-07-08 at 12.32.36.mp4` (407s, EN).
- Transcribed **locally** with faster-whisper (`.scratch/transcribe.py`, no audio left the machine); full transcript at `.scratch/transcript-WhatsApp Audio 2026-07-08 at 12.32.36.txt`.
- Logged verbatim to `workspace/clients/brisken/context/comms-log.md` (2026-07-08 INBOUND entry).
- **Content:** the real MDH use case (client = ADM, commodity price-curve management). **HARD CONSTRAINT (repeated by Dirk): never name ADM, never "this specific" account.** Share only the technology and concepts, anonymized.
- **Ask:** build a commodities asset = his SharePoint deck "Market Data Hub for Commodities" + the anonymized story + 1-2 institutional/partners slides.

### 2. Separate commodities deck (DRAFT, too long)
- Owner decision this session: this is a **SEPARATE asset** from the generic MDH 12-page deck (`.../rome-2026/decks/brisken-market-data-hub.pptx`). Do not touch the 12p.
- Pulled Dirk's source deck read-only from SharePoint via CDP:9222 (`.scratch/fetch-mdh-source.py` -> `.scratch/mdh-source.pptx`, 46 slides, "BRISKEN MDH WALKTHROUGH DEMO SLIDES 250710.pptx"; parse in `.scratch/mdh-source-parse.txt`).
- Built `.scratch/deckgen/build-mdh-commodities.py` -> `.scratch/deckgen/brisken-mdh-commodities.pptx` (+ `.pdf`, front PNGs in `png-comm/`): the 46-slide walkthrough with **5 new front slides inserted after the cover** (Who we are; Partners placeholder; 3 anonymized case-study slides). Rendered via PowerPoint COM.
- **Owner verdict: "waaaaaay too long."** The 51-slide result is wrong. The 5 front slides are good and reusable; the fix is to NOT append the whole 46-slide walkthrough. See continuation prompt for the short-deck plan.

### 3. Partners data (sourced from brisken.com)
- Owner asked to read partners from brisken.com. "Trusted by teams at" logos: **Nestlé, Ford, Siemens, YETI, British American Tobacco**. Technology partner: **SAP** (co-innovation). Data providers already in the source deck: Bloomberg, LSEG/Refinitiv, ICE, CME.
- These are public customer logos, distinct from the anonymized case-study client. Safe to use on the partners slide.

### 4. Microsoft Planner (MARKETING PLAN, live M365)
- Added 3 tasks to the **Lead Generation** bucket (shared plan, id `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`): "Build the Market Data Hub product deck with a customer case study", "Send Rome top-lead follow-up emails", "Send Rome booth network follow-up outreach".
- Dropped a 4th (SAP partner profile) as a dup of another chat's dedicated bucket. Briefly created + then **deleted** one exact MDH-deck duplicate (my error, fixed). Verified each present once; touched no other chat's tasks.
- Method: raw CDP over :9222 to a dedicated tab (Playwright connect_over_cdp hangs on the heavy Office tabs; use single-target raw CDP instead). Board add = "Add task card in {bucket} column" -> real Input.insertText -> Enter. Grid view virtualizes rows (misleading for verification); verify via the board column reader. Task menu delete item is labeled just "Delete" (gate on task-menu signature so you never hit the bucket's Delete).

---

## Current Status
- Commodities deck: draft exists, too long, needs the short cut (next chat).
- Partners data: in hand (real, sourced).
- Planner: done + verified.
- Transcript: logged.
- Nothing sent to Dirk. Rome Tier-1 still gates on his JTI volume figure.

---

## Next Steps (all in `Continuation-Prompt.md`)
1. Rebuild the commodities deck SHORT (~8-10 slides): the 5 front slides + a few curated visual slides from the 46p + a close. Fill the partners slide with the real brisken.com logos.
2. On owner sign-off, move final pptx to `deliverables/lead-generation/rome-2026/decks/` and PDF to `dirk-send-pack/`.

---

## Working Notes
- Anonymization is a hard client constraint: never ADM, never "this specific". Concept-level only.
- Style tokens (match source deck): Maven Pro headings, blue `#0B57D0`, black on white, 16:9. Standard PPTX layouts present (Blank = idx 6).
- Render pptx via PowerPoint COM (`SaveAs(pdf,32)`, `Slide.Export PNG`); Chrome/Edge headless is NOT usable while Edge is open.
- CDP:9222 = user's signed-in Edge (Matthias.Silva@brisken.com). Playwright connect_over_cdp hangs on the 100+ heavy targets; use raw single-target CDP (`websockets`). Close only tabs you opened.
- Session was long (deck fetch + Planner + build). High pressure.
