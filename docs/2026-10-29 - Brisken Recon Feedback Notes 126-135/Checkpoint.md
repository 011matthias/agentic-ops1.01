# Checkpoint: Brisken Recon Feedback Notes 126-135

**Date:** 2026-10-29
**Status:** Notes #126-#135 itemized as backlog 258-262; backend live on Fly `dec3e207`; two Lovable prompts published and cold-driven, one written and unpasted

---

## Summary

Ten unread feedback notes became backlog items 258-262. Every bounded half shipped and was verified live: chase-list actions, Retry rendering body-only mail, the open-count mismatch, mail links, and removing set-aside files. Statement removal and mailed-statement recognition were deliberately left for a fresh session.

---

## What Was Done This Session

### Backend (expense-reconciliation module)
1. Item 258: `assignable_receipts[]` gained `date` + `reference` (the hand-match picker printed "-" for every date). PR #1673.
2. Item 259: `replay_held(render_body_only=25)` renders held body-only mail on the operator's Retry press; `rendered` is a parallel reply field. PR #1673.
3. Item 260: `rows[].closed_without_receipt` (the month gate's own verdict) after the first fix, `summary.n_charges_open_no_receipt_due`, read 0 live. PRs #1673 + #1678.
4. Item 261 (part): `links[]` on `GET /api/inbound/{archive}/body`, display only; a body with no visible text (zero-width characters included) holds as `held_no_valid_files` at arrival, and Retry moves a stored one there. PRs #1699 + #1701.
5. Item 262 (part): `POST /api/expense-batches/{id}/set-aside/dismiss` `{file, undo?}` flags the entry (bytes kept); a dismissed file refuses restore (`set_aside_dismissed`). PR #1699.
6. Test hardening: `test_renaming_a_batch_into_a_month_claims_its_pool` waits for the claimed expense, not the pool count (a CI race on the slower runner).

### Screen (Lovable)
1. `lovable-chase-actions-prompt.md` published by the owner; sections 1-3 verified by bundle audit + cold read-only drive (August: tile 42 open = panel 42, 42 Match buttons, picker order equals the ranking rule). Section 4 (top bar) did not land.
2. `lovable-topbar-actions-prompt.md` written as the follow-up, published, verified: 7 buttons + "..." in `MonthHeader`'s sticky bar, 700px wraps cleanly, banner sentence EN + PT, the Matching bar unchanged.
3. `lovable-setaside-links-prompt.md` written, NOT pasted.

### Live operation (owner yes)
1. One Retry press: 8 rendered, 7 landed. Charm Taphouse became an October expense (USD 107.19); the Google x3, Toast "Welcome", Toast "Thank you for your business" (a marketing note, no amount) and GitHub mails were set aside (October 6 -> 11, September 4 -> 5). "Nico - Receipts" has no text and no links and stays held.

---

## Key Decisions Made

### Links in mail are shown, never followed
- **Choice:** list a body's links for the operator; the tool fetches nothing.
- **Rationale:** rule_untrusted_inbound forbids a mail deciding a URL to fetch; an allowlist needs an owner ruling. Display answers note #129's "need to know if links can be processed" with no ruling.

### "Delete a document" means a reversible flag
- **Choice:** set-aside removal flags `dismissed`, keeps entry and bytes, `undo` reverses.
- **Rationale:** the storage description promises nothing accepted is destroyed. Statement removal also orphans Criss's decisions, so it waits for a dry-run design.

### Retry renders body-only mail on the operator's click only
- **Choice:** cap of 25 per press; arrival still never renders a stranger's mail.
- **Rationale:** the press is the same authorization as the per-mail render button; the cap bounds spend on Dirk's key.

---

## What Did NOT Work (and why)

- **`n_charges_open_no_receipt_due` as the #132 fix:** read 0 on live August. The real gap row (ANNUAL MEMBERSHIP FEE) is gray-filled, so it is already closed, while its `reason_code` reads `not_a_purchase`; the synthetic test had a non-gray fee row. Replaced by `rows[].closed_without_receipt`.
- **"page header row" in the chase prompt's section 4:** Lovable left the buttons in the body; the page's real top bar is `MonthHeader`'s sticky nav. The follow-up named the component.
- **Claiming item 257 from a stale read:** a sibling took 257 while CI ran; the PR conflicted and the section was renumbered to 258-262.
- **A test fixture with an "Unsubscribe" link label:** that is readable text, so the "no readable body" tests failed until the fixture matched the live mail (0 characters).
- **`python -I` with `PYTHONIOENCODING`:** `-I` ignores it; `sys.stdout.reconfigure(encoding="utf-8")` is the fix.
- **Probing the Matching tab on October:** October has no statement, so `/runs/{id}` shows Expenses; re-probed on August.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/web/service.py` | edit | picker fields, `closed_without_receipt`, `dismiss_set_aside_file`, `dismissed` in the view |
| `.../web/intake_mail.py` | edit | Retry render budget, `_has_readable_body`, `links[]` on the body view |
| `.../web/body_render.py` | edit | `extract_body_links`, `has_visible_text` |
| `.../web/month_readiness.py` | edit | `n_charges_open_no_receipt_due` |
| `.../web/app.py` | edit | replay cap, `set-aside/dismiss` route |
| `.../tests/test_chase_hand_match_item_258.py`, `test_open_without_receipt_due_item_260.py` | new | items 258 + 260 |
| `.../tests/test_intake_mail.py`, `test_document_type_quarantine.py` | edit | items 259, 261, 262; CI race fix |
| `.../docs/lovable-{chase-actions,topbar-actions,setaside-links}-prompt.md` | new | SPA halves |
| `.../docs/PROMPT-STATUS.md`, `api-contract.md` | edit | ledger + contract rows |
| `tools/lovable-bundle-audit.py` | edit | NEW keys for the chase round |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | edit | items 258-262, roll-up |

---

## Current Status

Live on Fly `dec3e207` (`/healthz` verified by deploy.py). Ops status: platform unknown plan (no `platform` section in brisken's `infrastructure.yaml`). The feedback store holds notes past #135; a sibling handled #136-#139 as items 263-265 today.

---

## Next Steps

1. Diff `lovable-setaside-links-prompt.md` against the sibling's published `lovable-feedback-1029-prompt.md` (both touch #126/#130) and cut the overlap before the owner pastes it.
2. Check whether the sibling's "drop the asked-for button" prompt (PR #1687) removed the chase row's "Mark the receipt as asked for" that item 258 added; reconcile the two intents with the owner.
3. Item 262, statements: design a dry run that lists the decisions a statement removal would orphan, then the removal.
4. Item 261, the 1176 statement read as "not an expense document": read its stored reading first; any reader change goes in the schema only and is A/B'd old x2 vs new x2.
5. "Nico - Receipts" moves to no-valid-files on the next Retry press; its receipts were probably images below the signature-size floor. Ask the owner whether to read the archive in-machine.
6. `status/p1-recon-loop-prompt.md` is 44 days stale: rewrite it from this checkpoint or delete it.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (top two paragraphs)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 258-265
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Not applied table)

### Open Questions
- Should "Mark the receipt as asked for" exist on the chase rows, given the sibling removed an "asked for" button today?
- Statement removal: what happens to a reviewer's confirmed decision on a charge only the removed statement printed?

### Working Notes
- Instrument checks that held: the bundle audit's five control fields; the differential link probe (the Toast mail shows 5 links, so Nico's 0 is real).
- Live month ids: August `074a7b8905d7`, September `51a22ad72864`, October `4ac14cb8b9e8`.
- Drive scripts (cold login, read-only): scratchpad `drive_chase.py`, `drive_topbar2.py`, `drive_matching_bar.py`.

### Reference Materials
- PRs #1673, #1678, #1682, #1685, #1690, #1694, #1699, #1701

---

## How to Continue

`/resume brisken`, then take Next Steps 1-2 before any new feedback note: both are overlaps with a sibling's published work that the owner may have to rule on.

---

## Strategic Feedback

### What Worked Well This Session
- Validating each instrument before believing a negative: the bundle-audit controls, the August re-probe of the Matching tab, and the Toast mail as the positive control for `links[]`.
- Driving the published screen after every paste caught the section-4 miss the owner would otherwise have found.

### Suggestions
- Run a new count or predicate over the live row that motivated it BEFORE the first deploy. Item 260 cost a second PR, CI cycle and deploy because the synthetic fee row was not gray-filled.

### System Health
- Three sessions worked the same feedback store on the same day; item numbers raced, and two Lovable prompts overlap on #126/#130. A claim-before-build marker on the backlog, per item, would prevent both.
- Autonomy: 3 human interventions (two Lovable publishes, one yes for the live Retry press).
