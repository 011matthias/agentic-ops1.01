# Product decks: SharePoint is the source of truth

Four product decks: Market Data Hub, Market Data Hub for Commodities, Smart
Trading, Digital Co-Worker. One dark-cockpit visual system, problem-first
(slide 2 is THE PROBLEM, "Who we are" at the end).

**Dirk owns these decks and edits them directly in SharePoint.** The `.pptx`
files in `2026_PPTX` are canonical. The copies here, and the PDFs in
`../dirk-send-pack/`, are mirrors pulled down from SharePoint. They are not
generated.

| Deck | SharePoint name | Slides | Pages in PDF |
|---|---|---|---|
| Market Data Hub | `Brisken - Market Data Hub 2026-07.*` | 13 | 12 |
| Digital Co-Worker | `Brisken - Digital Co-Worker 2026-07.*` | 11 | 11 |
| Smart Trading | `Brisken - Smart Trading 2026.*` | 11 | 10 |
| MDH for Commodities | `Brisken - Market Data Hub Commodities 2026.*` | 9 | 9 |

The `2026-07` suffix is not a version scheme. It is the name Dirk gave his
edited copies of our 2026-07-07 uploads. After the 2026-07-09 deduplication
there is exactly one `.pptx` and one `.pdf` per deck, so the suffix
disambiguates nothing; whatever sits in `2026_PPTX` is current.

## Do not regenerate these

`.scratch/deckgen/build-mdh.js` and its three siblings produced the first
version of these decks and were retired on 2026-07-09. Re-running them
overwrites Dirk's edits, and his edits are not cosmetic:

- **Smart Trading:** slide 10, `PARTNERS AND CUSTOMERS`, is hidden.
- **Market Data Hub:** slide 12, `Brisken`, is hidden.

Hidden slides do not export to PDF, which is why two of the decks carry one
fewer page than they have slides. A regeneration silently un-hides both and
puts them back in front of a client. That is why the page counts above are
recorded here: they are the check.

To update a deck, edit the `.pptx` in SharePoint (or ask Dirk to), then pull
it back down here and re-export the PDF. Never push a generated deck over one
of his.

`build-treasurycentral.js` is the exception and stays live. It generates the
per-prospect call collateral in `../call-collateral/`, which Dirk presents but
does not edit, and it carries the shared visual primitives if a new deck is
ever needed.

## No SAP BTP

Dirk's directive, on the Planner task "Exclude BTP from all demos". Check with:

```
uv run tools/validate-demo-material.py --client brisken --dir decks dirk-send-pack call-collateral
```

Do not hand-grep for "BTP". It appears spelled out too: the MDH Commodities
credentials chip read "built on SAP Business Technology Platform" until
2026-07-09, and four separate hand-audits that day missed it. The validator reads
PDF page text and `ppt/slides/slideN.xml`, so it catches hidden slides and terms
split across text runs, and it knows both spellings.

One deliberate exception, his call and not ours:
`BRISKEN MDH WALKTHROUGH DEMO SLIDES 250710.*` (46 slides) names BTP on a
Technical Architecture diagram, in the label "BTP, Azure, AWS, Google Cloud".
That is a deployment target, not a positioning claim, and removing it would
make the diagram wrong.
