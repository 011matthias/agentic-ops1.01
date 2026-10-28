# Mini-Checkpoint: Expense-Recon Operator Note Above The Forward

**Date:** 2026-09-20
**Status:** Item 155 shipped, deployed (Fly v191) and verified. Queue closed; item 2 handed to a peer session.
**Type:** mini

---

## Summary

Backlog item 155 (note item T4): the filing instruction Dirk types ABOVE a
forwarded invoice now reaches the expense row as `expenses[].operator_note`,
display only. The boundary rule was derived by running the shipped function
over the live mail archive rather than guessed, and that measurement changed
two of the item's own assumptions.

## What Was Done

- `body_render.operator_note`: cuts a body at the **LAST** forward-header block
  in its first 30 lines and returns the prose above it, minus header lines,
  separator rules, forward markers and mail-client noise. Capped at 40 lines /
  2000 chars; the longest live note is 211.
- `intake_mail._archive_operator_note` wired into `_provenance_entry`, so every
  file a mail delivered carries the note; `build_expense_view` lifts it to
  `expenses[].operator_note` the way `untrusted_instructions` is lifted.
- Measured with the shipped function over `/data/inbound`, in-machine and
  read-only: **92 archives, 86 readable bodies, 71 with a forward boundary, 30
  with a note.** Six times the five the item named, because the item only
  judged the 30 attachment-bearing mails.
- Two findings the item did not anticipate. A forward can be **nested** (Criss
  forwards Dirk's forward; his "BTA / Marketing/Sales" sits *between* the two
  header blocks), which is why the cut is at the last block and not the first;
  8 of the 30. And **13 of the 30 notes arrive on body-only mail**, which is
  why those are recorded too: the item's caution against double-recording
  guards against a second copy of the *invoice*, and the rule cannot produce
  one, since it keeps only what sits above the forward.
- Display only (`rule_untrusted_inbound`), asserted as a differential rather
  than promised: two identical receipts, one mail naming an entity, a cost
  center, a category and a card, land on identical `legal_entity_id`,
  `entity_source`, `person`, `posting_category`, `card_source`, `cost_center`
  and `private`.
- `tests/test_operator_note_155.py` (11); the T4 pin in
  `tests/test_intake_mail.py` rewritten, because it asserted the drop that is
  no longer true; a contract pin in `tests/test_view_contract.py`. Suite
  2603 -> 2615 passed / 2 skipped. Three wiring points proven RED by hand,
  each anchor checked to sit in the function it names first.
- PR #1123 (merge `a2276f06`), follow-up PR #1126 (merge `3a1d5925`), Fly v191.
  SPA half `docs/lovable-operator-note-prompt.md` written, NOT pasted.

## What Did NOT Work (and why)

- **A 68-byte JPEG fixture for the mail-attachment tests:** `intake_mail.py`
  ~593 skips images under 4096 bytes as signature logos, so every test meant to
  exercise the ATTACHMENT path silently ran the body-only render path and
  passed. Caught only because the two-attachment test reported one provenance
  entry keyed `0000__rendered-body.pdf`. Fixed by giving the fixture real size
  and asserting the provenance key, which names which path ran.
- **Cutting at the FIRST forward boundary:** returns nothing for the 8 nested
  forwards, which are exactly the ones carrying Dirk's instruction inside
  Criss's forward.
- **flyctl with its own stored credential:** v0.4.71 answers "no access token
  available" for every command while that same token is accepted by
  api.fly.io (read-only probe: HTTP 200, viewer matneumann07@gmail.com). It is
  flyctl's config read that is broken, not the credential. Nobody needs to
  re-run `flyctl auth login`; exporting the token as `FLY_API_TOKEN` works.
- **Reading the live months to verify the deploy:** `operator_note` is absent
  on all 85 mail-delivered rows and always will be for them, because
  `intake_provenance` is written into the run snapshot at INGEST and read back
  from it. A confident "0 notes live" would have read as a broken deploy.
  Verified instead by running the deployed function in-machine (94 archives,
  88 readable bodies, 32 notes) with two named differential cases.

## Current Status

Item 155 is live on v191 and behaves as designed: the field appears on mail
arriving from v191 on, not on receipts already in a month. The SPA shows
nothing until the owner pastes the Lovable prompt. brisken platform: unknown
plan, last assessed unknown; comms-log 12 days stale.

**Two TRACEABILITY sessions ran the same continuation prompt today.** The peer
(`agentic-ops1-71`) raced this session on the merge, deployed the same commit
as **v190** a minute before this session's **v191**, and now owns queue item 2
(pin `set_tool_decision`'s `statement_id`) as backlog item **157**. It holds
`agentic-ops1-trace` on `client/brisken/p1-trace-toolstamp`.

## Next Steps

1. Owner: paste `docs/lovable-operator-note-prompt.md` into Lovable. Until
   then `operator_note` is API-only.
2. File feedback note **#70** (2026-09-18T10:19Z, `/expenses/af8936c6b05a`,
   "add receipts function just opens receipt view in new tab but does not
   really add it"). It is unfiled two days on; the backlog's highest note
   reference is #65. Handed to `agentic-ops1-71`, unconfirmed.
3. Decide whether the 32 notes already in the archive should reach existing
   rows. That needs a re-ingest per archive, which is a live write on Criss's
   months, so it is Criss's call and was not done.
4. Peer session owns item 157; do not duplicate it.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  (section "The note the sender typed above the forward")
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-operator-note-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/body_render.py`
  (the `operator_note` block at the end)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 155, Shipped row 103)
