# Mini-Checkpoint: Brisken SAP Surfaces + Planner Lead-Gen Bucket

**Date:** 2026-07-08
**Status:** PartnerFinder copy walked into the live editor field by field (paste-ready + hero image produced); 5 marketing tasks written to the live MARKETING PLAN "Lead Generation" bucket. Remaining SAP / OnePilot items Dirk-gated.
**Type:** mini

---

## Summary
Continued the P2 SAP-surfaces repositioning: reconciled `sap-surfaces-repositioning.md` to the REAL PartnerFinder editor (caps and tab structure confirmed via live screenshots the user shared), produced an on-brand hero image for the At-a-Glance media slot, added the review-seeding ask, and rewrote the Resources-tab cards. Separately, created a "Lead Generation" bucket in Brisken's live MARKETING PLAN (Microsoft Planner) and added this chat's 5 marketing tasks, driven over raw CDP on the user's signed-in Edge.

## What Was Done
- **SAP PartnerFinder (paste-ready, live-editor-accurate):** Heading (~130 cap), Description (400-cap, 387-char fit), Services tab (1500-cap, 1322-char A/B fit, TraderPlus retired to BST), Resources tab (4 card rewrites + card-04 rename + 4 proposed cards 05-08), and the field-map table rewritten to the real editor. Deliverable intro and live-note reconciled: PartnerFinder is now a screen-read, mission 3904 stays schema-based (not yet opened).
- **Hero image:** `deliverables/lead-generation/sap-assets/partnerfinder-hero.webp` (2560x1440, ~155 KB WebP, under SAP's 500 KB cap) — dark-cockpit 3-tier spine (TreasuryCentral / OnePilot / your SAP data + trust marks). Editable render source in `.scratch/brisken-sap-assets/partnerfinder-hero.html`.
- **Review-seeding ask:** section 5 of the deliverable — Dirk-voice, Register A, paste-ready for his warm customers.
- **Microsoft Planner:** created the "Lead Generation" bucket in the live MARKETING PLAN (planId `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`, tenant `aa3bd2bf-...`) and added 5 tasks: Update SAP PartnerFinder profile / Refresh SAP Discovery Center listing / Update SAP resource brochures / Gather SAP customer reviews / Reply to the mbi GmbH enquiry. First hit was the DELETED legacy plan (`e0Xx...`); caught via screenshot before writing. Raw single-target CDP driver at `.scratch/cdp.py` (Playwright `connect_over_cdp` hangs on this browser's 111 targets).

## Current Status
SAP-surfaces deliverable is paste-ready and matches the live editor. brisken.com form healthy (prior session). 5 Planner tasks live in the shared MARKETING PLAN. Deliverable edits + the WebP are uncommitted on the shared branch on purpose (parallel chat active in the same tree). No client message sent, no invasive brisken.com/CRM/Instantly action.

## Next Steps
1. Dirk pastes PartnerFinder (Heading / Description / image / Services / Resources) and publishes; opens mission 3904 to paste section 2 and confirm scope; sends the review-seeding ask to 2-3 warm customers.
2. Gated: #4 interim proposal slot (needs Dirk's file + brisken.com-vs-OnePilot-Fly site decision); #6 mbi GmbH reply (on Dirk's go); PartnerFinder Locations tab (needs a screen-read); BST + cards 05-08 datasheets (on Dirk's word, then the PDF protocol).

## Files to Read First
- `workspace/clients/brisken/deliverables/lead-generation/sap-surfaces-repositioning.md`
- `workspace/clients/brisken/deliverables/lead-generation/sap-assets/partnerfinder-hero.webp`
- `docs/2026-07-08 - Brisken P2 SAP Surfaces + Leads Export + Form Fix/Checkpoint.md` (prior full checkpoint this workstream)
