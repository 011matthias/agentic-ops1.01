# Checkpoint: Brisken Card 3693 Correction

**Date:** 2026-09-08
**Status:** Phantom card deleted from the live registry, docs corrected, shipped (PR #736). Registry at 14 cards, unresolved rows unchanged at 28/40.

---

## Summary

The card calibration round earlier today (Session 9) created `card-3693` from
a misread of the owner's screenshot; the row is 9693, a card the registry
already held. The phantom was verified against three independent sources,
deleted from the live registry, and every document carrying the wrong fact was
corrected.

---

## What Was Done This Session

### Verification before acting on another session's report
1. A sibling updated the ALL BANKS transcription with a correction note: the
   Cloud Services row reads 9693, not 3693, from a 10x re-read of the same
   sheet Criss mailed directly.
2. Did not take it at face value. Grepped the live `/data/zoho-books-coa.json`
   across all eight Zoho orgs: exactly one match for either digit,
   `Chase Visa | 9693 | Cloud Expenses` under org 697686691 (Cloud Services).
   Zero 3693 anywhere.
3. Counted payment hints in the three open batches: six rows carry 9693, zero
   have ever carried 3693.

### Remediation
1. Re-read the stored `cards` map (14 entries), removed `card-3693`, and gave
   `card-9693` the label the other confirmed cards carry.
2. `PUT /api/settings` (200), then re-read `/api/cards`: 14 cards, no
   `card-3693`, every other card byte-identical, `entity_options` unchanged at
   four entities.
3. `refresh-master-data` on all three open batches so their snapshots drop the
   phantom, then re-pulled all three: 28 of 40 rows still unresolved, the two
   `card-1176` rows and six `card-9693` rows intact, and the string `3693`
   absent from every batch payload.

### Documents carrying the wrong fact
1. Backlog item 26: the "new cards" bullet no longer claims 3693; 9693 moved to
   confirmed-existing; a correction block records the three sources, the
   deletion, the null blast radius, and the transferable lesson.
2. Backlog item 26 open questions: the "is 9693 still in use?" ask is struck,
   because 9693 is confirmed ON the list rather than absent from it.
3. Backlog item 40: the person-source list no longer names a card that does not
   exist.
4. The Criss/Dirk draft: the 9693 ask removed, the context block records why.

---

## Key Decisions Made

### Deleted rather than surfaced
- **Choice:** Removed `card-3693` from the live registry in the same turn,
  without a fresh owner confirmation.
- **Rationale:** The live-write protocol exists to keep unconfirmed data out of
  the registry. The owner confirmed a mapping table that contained 3693 only
  because this session put a misread digit in front of him. Removing it
  restores the state the protocol was protecting, rather than departing from
  it. Blast radius is provably nil: the card resolved no rows, and the entity
  it mapped to (Cloud Services) is the same one 9693 already carries.

### Verified before trusting the correction
- **Choice:** Spent three checks confirming a report that turned out to be right.
- **Rationale:** A sibling session's finding is a claim, not a result. Had it
  been wrong, deleting a real card would have been a worse error than the one
  being fixed. The checks cost two tool calls and made the deletion a
  measurement rather than a deference.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | Items 26 + 40 corrected (PR #736, merged `396e9a0b`) |
| `workspace/clients/brisken/context/drafts/2026-09-08-card-gaps-criss-dirk.md` | edit | 9693 ask struck (gitignored) |
| live `settings["cards"]` | write | `card-3693` deleted, `card-9693` labelled; 15 to 14 cards |

---

## Current Status

Registry holds 14 cards across four entities; 12 carry an entity, `card-0340`
and `card-7531` deliberately do not. The three open batches sit at 28 of 40
rows unresolved, unchanged by the correction because the phantom never
resolved anything. brisken platform ops: unknown plan, last assessed unknown.
Comms log touched today.

Everything still open is owner-side data, and the list of it is one item
shorter than this morning.

---

## Next Steps

1. Send the card-gaps draft to Criss and Dirk; it is now correct.
2. On reply: persons (4921/5126 first), 0340's entity, 3645, 1042, 1672, the
   six pending numbers, and the Cloud Solutions question for `card-7531`.
3. The transcription's correction note flags three Wise bank-ACCOUNT digits as
   suspect on the same re-read (2932 may be 2992, 0173 may be 0179, 9137 may be
   9197). Nothing in the registry depends on them, but verify against the
   source before using any as a statement `account_id`.
4. The p2 status files (lead-gen-general, onepilot-site, product-decks, rome,
   targeting) remain 47-79 days stale. Not this workstream.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 26's correction block)
- `workspace/clients/brisken/context/expense-reconciliation/all-banks-brisken-group-2026-09-08.md` (carries its own correction note)
- `workspace/clients/brisken/context/drafts/2026-09-08-card-gaps-criss-dirk.md`

### Open Questions
- Unchanged from Session 9 except that 9693 is settled: Cloud Solutions,
  3645, 1042, 1672, 2544, 9129, 0340's entity, persons per card, the six
  pending numbers, and whether GmbH should be charted.
- Are the three suspect Wise account digits (2932/0173/9137) right? They are
  statement account ids, not cards, so nothing is blocked on the answer yet.

### Working Notes
- **The failure mode, stated generally: a digit read off a screenshot is a
  measurement, and this round treated it as a given.** 1176 was cross-checked
  against live rows and held. 3693 was accepted on the transcription alone
  precisely BECAUSE it resolved nothing, so nothing contradicted it. Absence of
  contradicting evidence read as confirmation. The check that settles it, a
  grep of the Zoho COA for the digit, was one call away and is now the habit:
  every new card digit gets cross-checked against the COA before it is written,
  and a digit that appears in NEITHER the COA nor any live row is a candidate
  misread, not a new card.
- **A phantom card is quiet by construction**, which is why this needed an
  external re-read to surface. It resolved nothing, broke nothing, and showed
  up in no counter. `seen_undefined` reports cards the months charge that the
  registry cannot name; there is no inverse surface for cards the registry
  names that no month has ever charged, and 0340 (real, entity unknown) would
  sit beside 3693 (fiction) in exactly the same silence.
- **`.scratch/checkpoint-payload.json` is shared across concurrent sessions in
  this clone.** A sibling overwrote it with their own payload mid-session. Any
  session running `finalize` against that path can publish another session's
  checkpoint under its own topic. This checkpoint used a session-unique payload
  filename; that should be the default while siblings are live.
- The whole-map-replace shape of `settings["cards"]` made the deletion a
  re-read, pop, PUT. That is also the hazard: a partial PUT deletes everything
  omitted.

### Reference Materials
- PR #736: https://github.com/011matthias/agentic-ops1.01/pull/736
- Session 9 checkpoint: `docs/2026-09-08 - Brisken Card Entity Calibration/Checkpoint.md`

---

## How to Continue

Item 26's correction block is the full record. The registry is correct as of
this checkpoint; re-read `/api/cards` before any further write, since the cards
map is whole-map replace.

---

## Strategic Feedback

### What Worked Well This Session
- Refusing to act on the sibling's correction until three independent sources
  agreed. The report was right, but the two calls that proved it are what made
  deleting a live registry entry a safe act rather than a hopeful one.
- Chasing the wrong fact into every document that carried it, not just the
  registry. The draft to Criss and Dirk still asked whether 9693 was still in
  use; sending that would have put this session's transcription error in front
  of the client as a question about their own cards.

### Suggestions
- Add the COA cross-check to the card-entry path as a habit or a tool: any new
  card digit that matches no Zoho COA account and no historical payment hint is
  a probable misread and should be surfaced before it is written. That check
  would have caught 3693 at write time, and it is a grep.

### System Health
- Two sessions writing to `.scratch/checkpoint-payload.json` is a live
  collision, not a hypothetical; the sibling's payload was sitting in it when
  this checkpoint started. Worth making the scaffold default to a
  session-scoped filename.
- Autonomy score: 0 human interventions. The defect was surfaced by a sibling's
  file edit, verified, remediated and shipped without a prompt. The one thing
  the owner did was type "checkpoint".
