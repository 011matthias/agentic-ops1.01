# Sanofi call collateral (task 3)

For Ian Haegemans, Sanofi. Call next-week Friday about 16:00. Dirk presents.
Built 2026-07-09.

Every file here is verified free of SAP BTP references, per Dirk's standing directive
("Exclude BTP from all demos"). The verification is a `pypdf` text extract asserting zero
`\bBTP\b` matches in the rendered PDF, not a visual scan of the source.

| File | What it is | BTP refs | Provenance |
|---|---|---|---|
| `brisken-treasurycentral-sanofi.pdf` | 10-slide demo deck, send-ready | 0, verified | rebuilt by task 3 from `build-treasurycentral.js` with the two BTP strings removed |
| `brisken-treasurycentral-sanofi.pptx` | editable source of the above | 0, verified | same |
| `brisken-treasurycentral-onepager.pdf` | one-page leave-behind | 0, verified | rebuilt by task 3 from the shared one-pager HTML with the `SAP BTP` trust chip removed |
| `brisken-smart-trading.pdf` | product deck, optional annex | 0, already clean | unmodified copy of `dirk-send-pack/brisken-smart-trading.pdf` |

## Deliberately excluded

The Market Data Hub, MDH Commodities and Digital Co-Worker decks each still carry BTP (2, 1
and 2 references). Attaching them would break the directive that this pack exists to honour.
They are the property of the "Exclude BTP from all demos" task; see
`../shared-file-proposals.md` for the exact edits that would clear them.

If Ian's questions run toward market data specifically, Market Data Hub is the deck that
should follow the call. It needs the BTP fix first.

## The Sanofi tailoring

Only four things differ from the Zalando build: cover, problem headline, proof line, close
emphasis. The middle of the deck is the shared product story, which is intentional; the
visual system is byte-identical to the product decks because both come from the same
`build-mdh.js` primitives.

The Sanofi problem headline is "A global treasury runs one process. The data behind it lives
in a dozen places." The proof line is "Standardise the process once, governed and
analytics-ready, and run it the same way across the whole group." Both were written before
we researched Sanofi's Treasury Core Model, and both survive that research intact. See
`../call-prep-brief.md`.

## Two open items on the deck itself

1. **Slide 8 names Evonik and RWZ.** Dirk has not signed this off for external use. Flagged
   for his review in the 2026-07-09 checkpoint, still open.
2. **Slide 10 reads "When we talk, we will show TreasuryCentral live on your SAP data."**
   That sentence was written for a pre-call email, where "when we talk" pointed at this
   call. Presented during the call it promises what is already happening, and it implies a
   live run on Sanofi's own data. `../demo-flow.md` gives a verbal close to use instead.

## Rebuilding

```bash
# deck (writes into this folder)
NODE_PATH=.../.scratch/deckgen/node_modules \
  node ../build/build-treasurycentral-sanofi.js sanofi
uv run --script ../build/export-pdf.py

# one-pager (strips the chip, renders, self-verifies single-page + BTP-free)
uv run --script ../build/build-onepager-btp-clean.py
```

Chrome headless renders the one-pager rather than Edge, because Edge is normally open on
this machine as the PDF viewer and its headless mode fails silently in that state.
