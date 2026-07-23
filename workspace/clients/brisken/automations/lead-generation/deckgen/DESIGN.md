# Brisken deck design standard (NEW-generation native family)

The codified foundation behind the Dirk-approved
`NEW - Brisken - TreasuryCentral Solutions Overview 2026-07-21.pptx`.
Every future Brisken deck wave (product decks, Sanofi/Zalando prospect
decks, use-case decks) inherits this file by reference; the engine that
enforces it is `native/` (see README "Native pipeline"). MESSAGING.md stays
the terminology authority; this file is the structure, design, and process
authority. Supersedes the 2026-07-15 `context/deck-fix-pass-prompt.md`
(dark-cockpit fix-pass; its surviving rules are folded into §2).

## 1. Tokens and palettes

Base tokens (shared by every deck; source of truth `native/tokens.py`):

- Colors: INK `0F1417`, PAPER `FFFFFF`, NEUTRAL `F4F6F7`, MUTED `5B666B`,
  FAINT `8A9599`, LINE `E2E7E9`, ONINK `ECEFF0`, ONINK_SUB `9AA6AB`,
  NEUTRAL_DK `1B2327`.
- Fonts: Century Gothic (display) / Segoe UI (body) / Segoe UI Semibold.
  Named system fonts, NOT embedded (the approved deck ships zero
  `ppt/fonts/` parts; the native render gate enforces exactly these three).
- Canvas: 13.333 x 7.5 in, margin 0.62, 12-col feel via the shared card
  arithmetic. Footer hairline at 6.92 + "TreasuryCentral, powered by
  OnePilot" signature + `NN` page number.
- ONE focal bright element per slide. Everything else stays in the neutral
  ramp.

Per-deck identity = one `Palette` (accent + bright + layout signature).
One family, per-deck accent:

| Deck | accent | bright | signature |
|---|---|---|---|
| overview | `0E7C86` teal | `17B0BE` | none (parity with the approved deck) |
| market-data-hub | `1B7A3D` green | `27AE60` | rail-left |
| mdh-commodities | `9C4A1E` rust | `C2661B` | baseline |
| smart-trading | `3A4A9F` indigo | `5468D4` | bar-right |
| digital-co-worker | `6D4098` plum | `9463D6` | corner-dots |

The hues echo the per-deck identities Dirk saw in the 2026-07-21
distinct-aesthetics pass (MDH green terminal, Commodities rust, Trading
indigo), now inside the single approved system. The Digital Co-Worker moved
from "soft teal" to plum because the Overview owns teal in this family.
Adding deck #5 = one Palette entry + one spec; no new layout code.

## 2. Slide grammar and content contracts

Slide types live in `native/grammar.py`; specs (`native/specs/*.yaml`)
carry only content. Canonical product-deck order:

cover → the short version (4 cards) → the problem → where-it-sits
(hierarchy, this deck's app focal) → app mechanism → functional overview →
use cases (1 slide each) → governance → success proof (only where sourced)
→ contact closer.

Full-bleed dark dividers only in decks >20 slides (the Overview); at
product-deck scale section identity comes from the kicker line.

Content contracts (each type):

- **cover** — deck name + "Powered by OnePilot" eyebrow; no claims.
- **the short version** — four cards: what it is / what it replaces / what
  you get / who it is for. One line each.
- **problem** — the BEFORE world in three bands (sources / the manual
  middle / your systems). NEVER names the product (don't resolve the
  tension early). The middle band is the villain (ink, bright rule).
  Optional stat line only with the source named in-sentence.
- **hierarchy (where-it-sits)** — TreasuryCentral "one workspace on
  OnePilot" → OnePilot band with the four app cards incl. "+ your own
  apps" → SAP "your book of records, grounded". Product decks highlight
  their own app card.
- **app mechanism** — answers, in order: the problem it removes → what it
  does step by step (numbered) → what you no longer do by hand, plus a
  grounded CONNECTS-TO ink strip (real venues, formats, SAP targets, so
  "any" is backed by instances).
- **functional overview** — sources → [product, on SAP's own cloud,
  governed] → destinations, one protocol strip, governance micro-panel.
- **use case** — concrete BEFORE (manual today, real actor and setting) /
  AFTER (numbered steps, max 6) / named human checkpoint chip. Jargon
  glossed inline on first use.
- **governance** — the four plain-language controls (audit trail,
  four-eyes/SoD + HITL, anomaly alerts, manage by exception) + "AI
  grounded in SAP, with a human in the loop" + ISO 27001 / SOC 1 Type II.
  Mandatory in every deck.
- **success proof** — only stories with a sourced deployment (REF s28-30 +
  Dirk's own before/after fills). A deck with no sourced story ships
  WITHOUT this slide; nothing is invented.
- **contact** — dark closer; make the headline a thematic callback to the
  problem slide's language where one offers itself.

Substance rules (from the approved deck's substance pass):

1. Every jargon term is glossed inline in plain language on first use
   (remittance advice, in-house bank, exposure, CAMT.086, security master,
   SAP module names, ...).
2. Every claim traces to a named source: Dirk's reference deck (REF sN),
   a deckgen spec, MESSAGING.md, or a logged Dirk decision. No invented
   numbers; statistics only with the source named in-sentence (the
   ACT / LSEG pattern). Delete a claim rather than guess.
3. `[NEEDS INPUT]` chips are visible placeholders and never ship
   unflagged; a deck may ship with them only when the report to Dirk
   names them.
4. Storyline: problem before credentials; the problem slide never resolves
   itself; no claim restated near-verbatim on adjacent slides (make the
   second instance an explicit callback); vary card vocabulary; don't mix
   a capability into a channel/system list as if a peer; keep icon/accent
   treatment uniform on parallel trust grids (phase-coloring only for real
   sequences).
5. Internal-demo content keeps its label ("Shown here as a working demo,
   not a customer deployment"). Illustrative scenarios keep their tag.
6. Zero em-dashes (deliverable standard; compose fails the build).
7. Footer pagination is engine-owned: cover / dividers / contact carry no
   number; body pages run sequentially (the hand-numbering drift class is
   dead in this family).

## 3. Verification gates (per deck, in order)

Failures loop back to the SPEC or the engine, never to the artifact.

- **G0 source lint** — spec text scanned against MESSAGING.md swaps and
  the fixture terms before building.
- **G1 banned content + em-dash** — `uv run tools/validate-demo-material.py
  --client brisken` over the composed pptx (slide XML incl. hidden) and,
  post-render, the deck folder incl. the PDF. Fixture:
  `tools/fixtures/demo-banned-terms.json` (BTP both spellings, Evonik,
  RWZ, em-dash, your live SAP data, SAP OneExposure, AI Digital Workforce,
  ChatGPT, central repository, cockpit).
- **G2 slop scan** — anti-slop pass over the extracted deck text
  (corporate thesaurus, meta-phrases, performed humanness).
- **G3 adversarial source-trace** — independent checkers, one per slide
  cluster, each re-reading the sources and flagging any untraceable claim.
  Findings are fixed in the spec and the affected clusters re-checked.
- **G4 render + visual inspection** — PowerPoint COM render
  (`native/render.py`: PDF + per-slide PNGs + rId / hidden-slide / native
  font gates), then contact sheets (`native/montage.py`) read
  slide-by-slide: overflow, collisions, footer sequence, badge identity,
  accent consistency. Budget 2-3 iterations; the Overview loop caught 8+
  real layout bugs this way. MANDATORY extra: review each APP slide at
  full size (not only the contact sheet) and check the three card bottoms
  against the CONNECTS strip — an over-long column renders BEHIND the
  strip and is invisible at contact-sheet scale (caught once, 2026-07-23;
  a chars-per-line build guard was tried and retired the same day because
  it could not separate approved copy from real overflow).
- **G5 upload** — `deckgen/upload.py <deck>` (CDP :9223), per-deck, never
  `--all`. Asset Testing is the only expressible destination.
- **G6 re-download verify** — pull the uploaded pair back and
  byte/content-compare against the local build.

## 4. Rollout rules

- All uploads land in `2026_PPTX/Asset Testing` only. Promotion into
  `Brisken Product Assets` follows the swap runbook (README) after Dirk's
  explicit per-deck approval; superseded-variant cleanup is Dirk's call.
- Naming: `NEW - Brisken - <Deck> <YYYY-MM-DD>.pptx/.pdf` — sorts as one
  NEW block beside the approved Overview and can never collide with
  Dirk's live files or the older `... 2026-08 PROPOSAL` pairs.
- Dirk notifications follow the bullet-notification style (lead line =
  what + where with clickable links, <~120 words, one soft ask). Every
  send is a per-send gated action needing an explicit owner yes.
- Dirk's feedback comes as comments/edits on the live SharePoint file; it
  is pulled off the live file, folded into the SPEC (so it survives
  regeneration), and the deck regenerates clean through G0-G6.
