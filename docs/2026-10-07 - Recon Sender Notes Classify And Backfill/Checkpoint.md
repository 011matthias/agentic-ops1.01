# Checkpoint: Recon Sender Notes Classify And Backfill

**Date:** 2026-10-07
**Status:** LIVE — items 250, 252, 253, 254 shipped; SPA prompts pending paste

---

## Summary

Built sender-note classification for the expense recon (item 250): notes from trusted senders now decide company, account, and split. Then applied it to all six months with noted receipts (items 252-254), with two correctness fixes discovered in dry runs before any rows were written.

---

## What Was Done This Session

### Item 250 — Sender notes classify receipts (new mail, going forward)
1. `sender_note.py`: pure module — `read_companies`, `account_hint`, `strip_signature`, `stamp_sender_notes`, `names_account`, `CORPSERV_UNSPLIT_CODES`; company vocabulary for BCS/BTS/CorpServ; three `COMPANY_ORGS` org-id mappings.
2. `trusted_sender_notes(provenance, cfg)` in `intake_mail.py`: deny-by-default trust filter — tenant + `known_senders`, no `untrusted_instructions`, not just a signature (strips lines matching intake aliases' full names).
3. `ClassificationSource.NOTE` added to `types.py` with `ORIGIN_PERSON` and three new `Receipt` fields (`sender_note`, `sender_note_entity`, `sender_note_split`).
4. `_note_accounts()` in `categorize.py`: NOTE tier above merchant list on GL months; LLM fallback via `classify_by_note`; `names_account` guard blocks account picks whose words aren't in the note.
5. `resolve_batch_row_cards` entity order in `service.py`: override > `sender_note_entity` > card > batch/learned > none; `entity_source = "sender_note"`.
6. Three owner rulings (do not re-litigate): (a) company — "note always wins" over the card (Criss's equal override pick still wins on read); (b) split — "own account, never split", books whole in Corporate Services on an N/A-allocation account; (c) account — "decide when clear" (model >= 0.85, source NOTE, origin person, never learned).
7. 35 tests in `test_sender_note_250.py`; Lovable prompt handed: `docs/lovable-sender-note-classify-prompt.md`.
8. Shipped: PR #1589, Fly `27ab0ec4`; recorded live in PR #1591.

### Items 252-254 — Backfill existing months; two correctness fixes from dry runs
9. `sender_note_backfill.py` (684 lines): route `POST /api/runs/{id}/sender-notes/apply {confirm, dry_run}`; `archives_by_document` re-reads notes from mail archives for pre-item-155 receipts; `plan_backfill` applies trust filter, stamps, re-categorizes; `commit_plan` writes under batch lock with REMATCH_PENDING on company moves.
10. **Item 253 — pair by card, book by note** (found in first dry run: 5 pairs would have been lost): `pairing_entity(receipt)` returns None when company == `sender_note_entity`, so the note-moved receipt keeps its card's charge in `pair_in_scope` and `_second_chance_shortlist`. PR #1606, Fly `ca8a2cea`.
11. **Item 254 — account clear only when note names it** (found in second dry run: 6 wrong accounts — "Nicolas/Lydar" → travel, Railway hosting → conference train): `names_account(note, account)` strips company names from the note, requires one meaningful non-generic word in common; the LLM alone had filed three Railway rows under travel. PR #1608, Fly `4887af16`.
12. Applied live after dry runs confirmed 0 pairs lost, 17 account decisions all named in the note. Six months (May-October 2026): 71 receipts stamped (24 notes re-read from archive), 19 companies moved, 17 accounts set, 40 notes restored to display, 0 pairs lost, 1 gained.
13. `docs/lovable-sender-notes-trigger-prompt.md` handed for the `mh.rematch.trigger.sender_notes` i18n key.
14. Cold browser drive of September confirmed rows render with "Note from the sender" label; no raw key text (`sender_note` literal visible until SPA prompt pasted — expected).

### Gate-compliance note
- `warn-send-output-truncated` false-positived on any command containing the word "sender" (e.g. `sender_note_backfill`). Not a real email send; the pattern fires on the string alone.
- `heredoc-size-gate` fired correctly twice blocking triple-quote heredocs in Bash. Both discarded as gate-working-correctly.

---

## Key Decisions Made

### Company override
- **Choice:** Note always wins over the card. Criss's own reviewer-pick equal to the note still wins on read (override table entry beats NOTE).
- **Rationale:** The note is the sender's deliberate statement of which entity the cost belongs to; the card tells you only who paid.

### Split receipts
- **Choice:** "Own account, never split" — a note saying "split" books the whole amount in Corporate Services on the never-allocated account for that cost type (`CORPSERV_UNSPLIT_CODES`).
- **Rationale:** Corporate Services is the entity that holds costs not yet allocated; an explicit split note means "this belongs to the whole group."

### Account clarity
- **Choice:** "Decide when clear" — model >= 0.85 + `names_account` guard (note's own words must name the account).
- **Rationale:** The LLM alone had 6 false positives in dry runs (railway hosting → conference travel). `names_account` ensures the note actually contains the cost type's vocabulary.

### Pairing
- **Choice:** "Pair by card, book by note" — entity used for pairing is the card's company, not the note's.
- **Rationale:** A company-moved receipt still belongs to the same card charge; breaking the pair by pairing on the note entity would lose 5 confirmed pairs.

---

## What Did NOT Work (and why)

- **Large Python patches via Bash heredoc:** Shell tokenizer fails when the script body contains triple-quoted strings (`"""..."""`); the heredoc-size gate also blocked several attempts. Fixed with the Write tool.
- **`regress_check.py --file` with a repo-relative path:** `--file` resolves against `--cwd` (the module dir); the file was never found. Fixed by passing a module-relative path.
- **`gh pr create` with inline `--body` quoting a multi-line body:** Hung >120 s on Windows. Fixed with `--body-file`.
- **`warn-send-output-truncated` false positive:** The pattern fires on any command output containing "sender"; `sender_note_backfill` output was flagged as a send truncation warning every run. Not a real email event.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/sender_note.py` | Created | Company vocab, trust filter, stamp, names_account |
| `src/expense_recon/matching/types.py` | Modified | `NOTE` source enum, 3 new Receipt fields |
| `src/expense_recon/matching/deterministic.py` | Modified | `pairing_entity()` — pair by card |
| `src/expense_recon/matching/judgment.py` | Modified | `_second_chance_shortlist` uses `pairing_entity` |
| `src/expense_recon/web/serialize.py` | Modified | Serialize/deserialize sender_note fields |
| `src/expense_recon/categorize.py` | Modified | `_note_accounts()`, `names_account` guard, NOTE_DECIDES_AT |
| `src/expense_recon/llm/client.py` | Modified | `classify_by_note` protocol + implementation |
| `src/expense_recon/web/intake_mail.py` | Modified | `trusted_sender_notes()` |
| `src/expense_recon/web/service.py` | Modified | entity_source order, `stamp_sender_notes` calls |
| `src/expense_recon/cli.py` | Modified | `generate_expenses` sender_notes param |
| `src/expense_recon/output/report_xlsx.py` | Modified | NOTE excluded from review sheet |
| `src/expense_recon/web/sender_note_backfill.py` | Created | Backfill route, archive re-read, plan/commit |
| `tests/test_sender_note_250.py` | Created | 35 tests for item 250 |
| `tests/test_note_pairs_by_card_253.py` | Created | 4 tests for item 253 |
| `tests/test_sender_note_backfill_252.py` | Modified | Renamed test + `entity_source == "sender_note"` assertion |
| `tests/test_operator_note_155.py` | Modified | `from_addr` param; renamed test to use stranger |
| `docs/api-contract.md` | Modified | Sender notes classify section |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Modified | Items 250, 252, 253, 254 LIVE |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Modified | Session summary entry added |
| `docs/lovable-sender-note-classify-prompt.md` | Created | SPA prompt for item 250 badge/label changes |
| `docs/lovable-sender-notes-trigger-prompt.md` | Created | SPA prompt for `mh.rematch.trigger.sender_notes` i18n |

PRs (all merged): #1589 (item 250), #1591 (record 250 live), #1604 (item 252 backfill route), #1606 (item 253 pair by card), #1608 (item 254 names_account), #1609 (record 252-254 live). Fly: `27ab0ec4` (250), `ca8a2cea` (253), `4887af16` (254).

---

## Current Status

All four items LIVE on Fly `4887af16`. Brisken p1 ops: `unknown plan, ~?/? ops/mo`.

Two Lovable prompts handed, not yet pasted:
- `docs/lovable-sender-note-classify-prompt.md` — replaces "Nothing was decided from it" hint; adds `sender_note` entity sub-label; adds `note` category badge (same tone as "learned").
- `docs/lovable-sender-notes-trigger-prompt.md` — adds `mh.rematch.trigger.sender_notes` EN/PT i18n key. Until pasted, the `sender_note` raw key is visible in the SPA instead of the label, and the "senders' notes applied" trigger toast is missing.

---

## Next Steps

1. **Owner:** paste `docs/lovable-sender-note-classify-prompt.md` into Lovable; verify `expx.operator_note.hint`, `expx.review.badge.note`, `expx.entity.source.sender_note` render correctly.
2. **Owner:** paste `docs/lovable-sender-notes-trigger-prompt.md` into Lovable; verify `mh.rematch.trigger.sender_notes` toast fires after a note backfill.
3. Brisken comms-log is 9 days stale — log any conversations from the past week before the next session.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/sender_note.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/sender_note_backfill.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`
- `docs/lovable-sender-note-classify-prompt.md`
- `docs/lovable-sender-notes-trigger-prompt.md`

### Open Questions
- Is the `warn-send-output-truncated` pattern already in `.claude/patterns/` and fixable there, or is it a separate hook?

### Working Notes
- `sender_note` raw key visible in SPA until prompts are pasted — this is expected, not a bug.
- Criss's equal override pick beats the note on read (e.g. Typora and Uber show "override" not "note") — correct behavior; the override was set before the note and matches the note's company.
- Archive re-read path (`archives_by_document`) works for pre-item-155 receipts; 24 of 71 used it.
- `names_account` strips company names (BCS/BTS/Corporate Services) from the note before matching; "IT" must appear as `\bI[Tt]\b` to count.
- Dry-run row list approach (read each row before any write) caught both item 253 and 254 before production impact. This is the right gate for any future backfill.

### Reference Materials
- Fly app: `brisken-expense-recon`, version `4887af16`
- Backfill route: `POST https://api.expenses.brisken.com/api/runs/{run_id}/sender-notes/apply`
- September batch: `51a22ad72864`

---

## How to Continue

```
/resume brisken
```

Paste the two Lovable prompts, then verify the SPA renders correctly on September (`51a22ad72864`): "Note from the sender" label (not `expx.operator_note.hint`), badge on NOTE-decided categories, `sender_note` entity sub-label on company-moved rows.

---

## Strategic Feedback

### What Worked Well This Session
- **Dry-run-row-list discipline:** Reading the planned changes row by row before any write caught two correctness failures (items 253 and 254) that would have silently written wrong data. Both were real issues (5 lost pairs; 6 wrong accounts). This is now the canonical approach for backfill operations.
- **Three-ruling approach before building:** Asking the owner to rule on company, split, and account separately (with the card-belongs-to-one-company plain-language explanation for company) gave clean, un-re-litigated decisions that held through all four items.

### Suggestions
- The `warn-send-output-truncated` pattern should be narrowed to match the actual truncation message shape (e.g. a specific sentinel string from the send path) rather than the word "sender" in any output. Every `sender_note_backfill` run generates a false positive, adding approval noise to every dry run.

### System Health
- **Autonomy Score:** ~4 human interventions (AskUserQuestion for company ruling, AskUserQuestion for account ruling, AskUserQuestion for pairing ruling after dry runs, "change existing rows / hand me the lovable prompt" directive). Elevated — the first three are genuine owner decisions; the fourth was a clear directive. Not a structural gap.
- The `heredoc-size-gate` fired correctly twice; the Write tool is the right path for multi-line Python with triple quotes.
