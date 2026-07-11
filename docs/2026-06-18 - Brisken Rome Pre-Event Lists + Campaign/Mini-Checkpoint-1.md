# Mini-Checkpoint: Brisken Rome Pre-Event Lists + Campaign

**Date:** 2026-06-18
**Status:** Track 1 complete (deliverable ready for Rachel via Dirk); Track 2 staged, Dirk-gated
**Type:** mini

---

## Summary
Built the SAP T&WCM Rome 2026 pre-event package: a reusable extractor that
produced a ranked, curated 40-company EU invite list (one finance decision-maker
each) for sponsor contact Rachel, plus a staged pre-event email sequence and a
brand-matched landing page with a printable TreasuryCentral/OnePilot one-pager.
Nothing sent or published.

## What Was Done
- **Extractor** `Rome-Event/build-invite-list.py` (PEP723, openpyxl): 6 source
  adapters → normalized EU schema, Europe filter, public-sector/charity drop,
  treasury/finance title scoring, dedupe-by-company, warmth+prominence ranking,
  em-dash sanitizer. Reusable for refreshes + Dirk's seed-list merge.
- **Track 1 deliverable:** `rome-2026-invite-list-rachel-top40.xlsx/csv` (curated
  40, warm-first) + `...-FULL.xlsx/csv` (1,091-company EU backing pool). Copies in
  `Rome-Event/` and `05-lists/Rome Treasury Conference 2026/`. `rachel-note-DRAFT.md`.
- **Track 2 staged:** `Rome-Event/pre-event-email-sequence-DRAFT.md` (3-touch
  T-5/T-3/T-1) + `deliverables/brisken-rome-2026-landing.html` (HTML validator
  clean, 0 em-dashes, working theme toggle, printable one-pager = the brochure
  Dirk asked to upload).
- Read the two event `.eml`; captured event facts + Dirk's messaging spine into
  the runbook; logged Dirk's sponsor-profile email + the build to comms-log.

## Current Status
- **Warm-set reality:** AFP=1 EU treasury contact, WebSummit=0 (VC/founders).
  The real warm core is SAP-FAM EU insurers + Landi Renzo + Barclays/News UK
  treasury specialists; the rest are recognizable EU large-cap CFOs ranked by a
  curated prominence lift (lists carry no prominence signal).
- Event is 23-25 June (Booth 2, Cardo Roma) — 6 days out; sequence is a sprint.
- Track 2 is Dirk-gated (send-authorization, consent posture, publish decision).
  Did NOT commit (client work; Track 2 gated). Did NOT auto-generate the
  one-pager PDF (PDF protocol = format question + draft gate first).

## Next Steps
1. Hand Rachel the `rachel-top40.xlsx` + `rachel-note-DRAFT.md` via Dirk's thread.
   Merge Dirk's seed list at the top of the ranking when it arrives (re-run the
   extractor with the seed as a tier-0 adapter).
2. Align with Dirk on Track 2: send-authorization + audience/consent posture for
   the sequence; publish/deploy the landing page (points to www.brisken.com);
   whether to expand other decks into standalone web pages (catalog warns: do NOT
   re-skin OnePilot-as-platform assets until Dirk confirms the TreasuryCentral
   hierarchy).
3. If publishing: deploy landing page to Fly (same pattern as the OnePilot
   prototype) — gated. Generate the one-pager PDF via the PDF protocol for the
   app Brochures upload Dirk requested.

## Files to Read First
- `workspace/clients/brisken/context/lead-generation/Rome-Event/conference-rome-2026-plan.md` (runbook + event facts + messaging spine)
- `workspace/clients/brisken/context/lead-generation/Rome-Event/build-invite-list.py` (the extractor)
- `workspace/clients/brisken/context/lead-generation/evidence/brisken-product-catalog.md` (sourced product content)
- `workspace/clients/brisken/context/comms-log.md` (2026-06-17/18 entries)
