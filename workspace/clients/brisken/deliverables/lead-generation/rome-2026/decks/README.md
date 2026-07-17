# Product decks: SharePoint is the source of truth

**Exceptions in this folder (not SharePoint mirrors):**

Three storyline proposals sit beside the SharePoint mirrors as a matched
demonstration set, so Dirk can flip through all three and decide whether to
adopt the standard. They answer his feedback that the decks "all run the same
storyline." The shared bookends stay (hero, THE SHORT VERSION intro at slide 2,
the WHY IT IS SAFE governance grid, the dual close), but each deck's **body is
now a genuinely different structure** so the set reads as three different talks.
Redundant slides are hidden (`show="0"`), never deleted; Dirk's partner slides
stay hidden.

- `brisken-market-data-hub-storyline-proposal.pptx` (14 slides, 12 visible;
  `WHY IT FITS` and `PARTNERS AND CUSTOMERS` hidden). **Screen-led product
  tour ("show the machine").** After the short version and a qualified
  ABAP / Datafeed-RFC problem (71% job-ads stat, strikeable footnote), a
  5-node WHAT IT IS ribbon hands to SIX real product screens, one per pipeline
  stage: connect a provider once, the data lands SAP-ready, a bad rate caught,
  the four-eyes change request, mapped to your SAP, audited to the target, each
  cyan-framed with three callouts. Then the MDH-specific safe grid and the dual
  close. The generic marketing middle (the fits-together diagram, the
  how-it-works overview, the three text step-pairs, the 3-card what-it-is, the
  runs-on chips) was cut.
- `brisken-digital-co-worker-storyline-proposal.pptx` (13 slides, all visible).
  **Story-led (one request's journey).** A single funding request is followed
  end to end across four beat slides carried by three motifs: a journey rail
  (Request > Reads > Checks > Books > Replies), an accumulating chat thread, and
  a filling audit ledger. Then the widen (the same pattern across the team),
  the production-proof cases, safe, runs-on, who-we-are, dual close. The card
  slides (what it is, how you use it, the payoff chart, the architecture
  diagram) were cut or merged.
- `brisken-smart-trading-storyline-proposal.pptx` (12 slides, 11 visible;
  `PARTNERS AND CUSTOMERS` hidden). **Clock-led (a stopwatch trilogy).** The
  manual clock (10-15 min per trade, Association of Corporate Treasurers, with
  an amber stopwatch) then the automated clock (under a minute, cyan stopwatch)
  then the two clocks side by side (~12 min vs <1 min). Then venues, the
  architecture diagram, safe, runs-on, who-we-are, dual close. The redundant
  third trade-walk (the old HOW IT WORKS) was cut.

All three carry the dual close on one slide (demo headline plus one subordinate
line "Or start with the Quick Assessment.", plain text, no hyperlink). This is
the recommended-pending-flag-9 element: Dirk decides whether the product decks
carry the second assessment path. The word "free" appears nowhere.

MDH now shows SIX real product screens (was one). All six are screening-verified
clean; each is a per-shot approval (flag 4). Some are real product captures with
their own whitespace or a status icon; Dirk approves or swaps any of them.

- `storyline-proposal-note-2026-07-14.md` is the sign-off note for Dirk:
  the four per-deck spines plus his nine open decisions (MDH screenshot
  approval sheet lives at `.scratch/mdh-shots/contact-sheet.html`).

Once Dirk decides per deck: adopt into SharePoint (then re-pull the mirror
and delete the proposal) or reject (delete the proposal). The MDH Commodities
rebuild is still only mapped in the note and waits on his answers (flags 2
and 6).

Four product decks: Market Data Hub, Market Data Hub for Commodities, Smart
Trading, Digital Co-Worker. One dark-cockpit visual system, problem-first
(slide 2 is THE PROBLEM, "Who we are" at the end).

**Dirk owns these decks and edits them directly in SharePoint.** The `.pptx`
files in `2026_PPTX/Brisken Product Assets/` are canonical. The copies here,
and the PDFs in `../dirk-send-pack/`, are mirrors pulled down from SharePoint.
They are not generated.

The `2026_PPTX` library was reorganized 2026-07-16 (root emptied into
subfolders, version history intact):

```text
2026_PPTX/
├── Brisken Product Assets/      product decks + Use Case decks + TC generic
├── Client Deliverables/         Sanofi/, Zalando/ per-prospect decks
├── Demo & Walkthrough/          MDH walkthrough demo slides
├── Asset & Deliverable Prep/    genuinely unfinished WIP
├── Asset Testing/               empty staging area
├── RAW MATERIAL/                Evonik 2024 source files
└── Archive/                     superseded copies (duplicate losers)
```

| Deck | SharePoint name | Slides | Pages in PDF |
|---|---|---|---|
| Market Data Hub | `Brisken - Market Data Hub 2026-07.*` | 13 | 12 |
| Digital Co-Worker | `Brisken - Digital Co-Worker 2026-07.*` | 11 | 11 |
| Smart Trading | `Brisken - Smart Trading 2026.*` | 11 | 10 |
| MDH for Commodities | `Brisken - Market Data Hub Commodities 2026.*` | 9 | 9 |

The `2026-07` suffix is not a version scheme. It is the name Dirk gave his
edited copies of our 2026-07-07 uploads. After the 2026-07-09 deduplication
there is exactly one `.pptx` and one `.pdf` per deck, so the suffix
disambiguates nothing; whatever sits in `Brisken Product Assets` is current.

## Do not regenerate these

`build-mdh.js`, `build-smart-trading.js`, `build-digital-coworker.js` and
`build-mdh-commodities.js` produced the first version of these decks and were
**deleted on 2026-07-09**. There is no generator for a product deck any more,
by design. Regenerating would overwrite Dirk's edits, and his edits are not
cosmetic:

- **Smart Trading:** slide 10, `PARTNERS AND CUSTOMERS`, is hidden.
- **Market Data Hub:** slide 12, `Brisken`, is hidden.

Hidden slides do not export to PDF, which is why two of the decks carry one
fewer page than they have slides. A regeneration silently un-hides both and
puts them back in front of a client. That is why the page counts above are
recorded here: they are the check.

To update a deck, edit the `.pptx` in SharePoint (or ask Dirk to), then pull
it back down here and re-export the PDF. Never push a generated deck over one
of his.

`build-treasurycentral.js` is the exception and survives. It generates the
per-prospect call collateral in `../call-collateral/`, which Dirk presents but
does not edit, and it carries the shared visual primitives (copied verbatim
from the deleted builders) if a new deck is ever needed.

## No SAP BTP, no Evonik, no RWZ

BTP: Dirk's directive, on the Planner task "Exclude BTP from all demos".
Evonik/RWZ: Dirk's email 2026-07-10 ("We cannot mention EVONIK in the pptx");
his own fix anonymizes to "Customer Team" in prose and a "German Chemical
Group" text chip in place of the logo. Purge shipped to SharePoint 2026-07-11.
Check with:

```
uv run tools/validate-demo-material.py --client brisken --dir decks dirk-send-pack call-collateral
```

Do not hand-grep for "BTP". It appears spelled out too: the MDH Commodities
credentials chip read "built on SAP Business Technology Platform" until
2026-07-09, and four separate hand-audits that day missed it. The validator reads
PDF page text and `ppt/slides/slideN.xml`, so it catches hidden slides and terms
split across text runs, and it knows both spellings.

One deliberate exception, his call and not ours:
`BRISKEN MDH WALKTHROUGH DEMO SLIDES 250710.*` (46 slides, in
`2026_PPTX/Demo & Walkthrough/`) names BTP on a Technical Architecture
diagram, in the label "BTP, Azure, AWS, Google Cloud".
That is a deployment target, not a positioning claim, and removing it would
make the diagram wrong.
