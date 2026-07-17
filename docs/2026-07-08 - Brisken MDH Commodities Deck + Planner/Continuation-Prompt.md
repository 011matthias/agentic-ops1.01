# Continuation Prompt — Brisken MDH Commodities Deck (SHORT rebuild)

Paste the block below into a fresh chat.

---

resume brisken

Finish the Brisken "Market Data Hub for Commodities" case-study deck. Read
`docs/2026-07-08 - Brisken MDH Commodities Deck + Planner/Checkpoint.md` first.

## The task
The previous draft was rebuilt as Dirk's full 46-slide walkthrough + a 5-slide
front section = 51 slides. The owner said that is **"waaaaaay too long."** Rebuild
it as a SHORT, standalone commodities case-study deck. It is a **separate asset**
from the generic MDH 12-page deck (`.../rome-2026/decks/brisken-market-data-hub.pptx`),
which you must NOT touch.

## Hard constraint (client directive, non-negotiable)
Never name **ADM**, never describe it as "this specific" account. The case study
is anonymized: technology and concepts only. Dirk's verbatim voice note is in
`workspace/clients/brisken/context/comms-log.md` (2026-07-08 INBOUND) and
`.scratch/transcript-WhatsApp Audio 2026-07-08 at 12.32.36.txt`.

## Recommended structure (~8-10 slides, confirm the exact cut with the owner)
1. **Cover** (reuse/adapt the source cover, or a clean title slide)
2. **Who we are** (institutional) — already built, reuse
3. **Partners and customers** — fill with the REAL, sourced logos/names below
4. **A worked example: commodity price curves** (concept) — already built, reuse
5. **Many sources, one governed process** — already built, reuse
6. **One curve, feeding risk and trading** (value) — already built, reuse
7. **1-3 KEY visual slides pulled from the 46p** to show the product concretely,
   e.g. the "Market Data Flow" architecture (source slides 2-5) and/or the
   "Market Data Governance Process Context" (source slide 46). Cherry-pick the
   strongest 1-3 visuals; do NOT re-include the full walkthrough.
8. **Close / next step**

The 5 front slides already built (steps 2-6) are verified good and on-brand; the
real change is dropping the 46-slide body and keeping only a few curated visuals.

## Partners slide content (real, already sourced from brisken.com "Trusted by teams at")
Customers: **Nestlé, Ford, Siemens, YETI, British American Tobacco**.
Technology partner: **SAP** (co-innovation; runs on SAP BTP + HANA).
Data providers (from the source deck): Bloomberg, LSEG/Refinitiv, ICE, CME.
Do not invent any others. If real logo images are wanted, source them properly
(Wikimedia, full-colour originals) per `feedback_use_original_logos`.

## Assets on disk
- `.scratch/mdh-source.pptx` — Dirk's 46-slide source (theme + the visual slides to cherry-pick)
- `.scratch/mdh-source-parse.txt` — text of all 46 slides (pick the visuals from here)
- `.scratch/deckgen/build-mdh-commodities.py` — the builder (has the 5 good front
  slides + the styling helpers). Edit this: keep the 5 front slides, replace the
  "insert into the 46p" logic with a short standalone deck; fill the partners slide.
- `.scratch/deckgen/brisken-mdh-commodities.pptx` / `.pdf` / `png-comm/` — the too-long draft

## Style tokens (match the source deck)
Maven Pro headings, blue `#0B57D0`, black on white, 16:9. No em-dashes (client-facing
deliverable). Build with python-pptx; render with PowerPoint COM (`SaveAs(pptx,32)` for
PDF, `Slide.Export "PNG"` for QA). Do NOT use Chrome/Edge headless while Edge is open.

## Pulling specific source slides into the short deck
python-pptx has no native cross-deck slide copy. Easiest reliable path: start from a
COPY of `mdh-source.pptx`, DELETE every slide except the cover + the 1-3 visuals you
want to keep, then insert the 5 built front slides in the right order (reorder via
`prs.slides._sldIdLst`). That reuses the theme and keeps the kept visuals pixel-intact.

## On sign-off
Show the owner the rendered PDF for review FIRST (open it with `Start-Process`, same
turn, per `feedback_open_files_directly`). After approval, move the final pptx to
`workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/` and the PDF
to `.../dirk-send-pack/` (pdf+pptx pairing). Nothing goes to Dirk or SharePoint without
an explicit per-action go.

## Do NOT
- Do not touch the generic 12-page MDH deck.
- Do not name ADM anywhere.
- Do not add the full walkthrough back.
- Do not send anything or write to SharePoint/Planner without an explicit go.
