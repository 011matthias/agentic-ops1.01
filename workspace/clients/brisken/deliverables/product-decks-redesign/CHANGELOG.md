# Product-deck NEW-generation rebuild; provenance and verification record

**Date:** 2026-07-23
**Decks:** the four product decks, rebuilt from scratch on the Dirk-approved
Overview foundation (`deckgen/native/`, DESIGN.md standard), one family with
a per-deck accent and layout signature:

| Deck | Slides | Accent / signature | Files |
|---|---|---|---|
| Market Data Hub | 13 | green `1B7A3D` / rail-left | `NEW - Brisken - Market Data Hub 2026-07-23.*` |
| Market Data Hub Commodities | 10 | rust `9C4A1E` / baseline | `NEW - Brisken - Market Data Hub Commodities 2026-07-23.*` |
| Smart Trading | 11 | indigo `3A4A9F` / bar-right | `NEW - Brisken - Smart Trading 2026-07-23.*` |
| Digital Co-Worker | 14 | plum `6D4098` / corner-dots | `NEW - Brisken - Digital Co-Worker 2026-07-23.*` |

Uploaded to SharePoint `2026_PPTX/Asset Testing` 2026-07-23 (per-deck, via
the hard-guarded `deckgen/upload.py`); each remote pptx re-downloaded and
content-compared slide-for-slide against the local build (ALL VERIFIED).
The specs that generate these decks: `deckgen/native/specs/*.yaml`.

## Copy sources (no invention)

- **Approved Overview build** (`native/specs/overview.yaml`, the byte-exact
  transcription of the Dirk-approved deck): each deck's app-mechanism slide
  (S12 MDH / S15 BST / S18 DCW), functional sources/destinations, the
  governance cards, the contact closer, the DCW use-case slides S21/S22/S23
  with Dirk's review edits baked in.
- **deckgen v2 specs** (Dirk-reviewed proposal substance): the short-version
  cards, problem-slide copy, and use-case bodies, translated into the
  BEFORE/AFTER pattern.
- **MESSAGING.md** terminology map incl. the 2026-07-21 Dirk-review
  additions; **CHANGELOG-substance-pass.md** (tc-overview-redesign) for the
  per-comment decisions.
- Success stories: ONLY the sourced deployments. MDH = Financial Services
  (REF s28 + Dirk's fill); DCW = Agriculture + Chemicals (REF s29/s30 +
  Dirk's fills); Smart Trading and Commodities ship WITHOUT a success slide
  because none is sourced.

## Verification record (gates G0-G6, DESIGN.md)

1. **Banned content + em-dash** (`validate-demo-material.py --client
   brisken`, 11 terms incl. the six new Dirk-decision terms): PASS on every
   pptx (slide XML incl. hidden) and PDF.
2. **Native structure gates**: fonts = named system fonts only (zero
   embedded parts), rIds valid, no hidden slides, engine pagination.
3. **Slop scan**: clean across all four decks.
4. **Adversarial source-trace**: 14 independent checkers (one per slide
   cluster). 6 REAL findings, all fixed in the specs:
   - The hierarchy footnote in MDH / Commodities / Smart Trading dropped
     the sentence subject, making the platform-level "in production across
     six industries" claim read as an app-level claim. Restored the V2
     wording: "OnePilot runs in production across ...".
   - Commodities used "tenor" before its gloss; the problem band now says
     "time horizon" and the glossed app slide is the term's first use.
   - Smart Trading's OTC use case claimed confirmation matching "whatever
     the format" (unsourced absolute); qualifier dropped.
   Adopted nits: "valuations" dropped from an MDH before-line (unsourced),
   Commodities handoff line no longer promises "the next page", the
   audit-trail freed line added to the Commodities app slide (Dirk S12
   emphasis), OMS/TMS glossed inline in Smart Trading. Consciously kept:
   the SAP Certified badge on each product deck's functional slide (Dirk's
   own certification mark, printed on his own product decks' diagrams).
5. **Render + visual inspection**: PowerPoint COM render, contact sheets
   read slide-by-slide, PLUS full-size review of every app slide. That
   full-size pass caught one real bug: the Commodities steps column
   rendered its fourth step behind the CONNECTS strip; copy tightened and
   re-verified. (A chars-per-line build guard for this class was tried and
   retired the same day; it could not separate approved copy from real
   overflow. The G4 full-size app-slide review is now mandatory in
   DESIGN.md.)
6. **Upload + re-download verify**: 8/8 files verified in the Asset
   Testing re-list (PDFs byte-exact); all four pptx re-downloaded and
   slide-text-identical to the local builds.

## Folder state observed at upload (2026-07-23)

The approved Overview pptx now sits in Asset Testing WITHOUT its "NEW - "
prefix (`Brisken - TreasuryCentral Solutions Overview 2026-07-21.pptx`),
its PDF still carries the prefix, the non-MN "2026-08 PROPOSAL" pairs are
gone, and the "MN - " copies remain. Naming reconciliation and any archive
of superseded variants stay the owner's call (content-approval-only
decision, 2026-07-23).
