# Mini-Checkpoint: Recon Card Filter And Footnote

**Date:** 2026-09-24
**Status:** Item 187 pasted, applied and driven; footnote defect fixed and live (Fly `24034c4c`)
**Type:** mini

---

## Summary

The owner pasted the card-status and private-reimburse prompts between sessions,
so `/cards` and the reimburse-edit control are live. Driving `/cards` surfaced a
defect I had shipped in its footnote; that is fixed and verified. The owner then
asked for a card filter on the months list itself, which went out as a prompt,
was pasted, and is now driven green on every check.

## What Was Done

- **Read the live surface instead of trusting the backlog.** The bundle already
  carried `cards/status`, `never_loaded`, `reimburse.edit` and "Receipts by
  email", so both prompts I had listed as outstanding were in fact live. Cold
  Chrome confirmed `/cards` in the nav and the 1176 drill-down.
- **Footnote defect, found and fixed** (PR #1279, merge `24034c4c`, deployed and
  driven). The page renders the payload's `note` verbatim, and that string ended
  "a card with no charge and no statement anywhere reads never_loaded", so a
  payload identifier was on Criss's screen. Prose now, with
  `test_the_note_names_no_payload_field` checking it against the payload's own
  keys rather than a hard-coded list. Suite 3239 passed, 2 skipped.
- **Item 187, the months card filter** (prompt in #1279, scope correction #1282,
  applied record #1287). No backend work: `GET /api/cards/status` already
  carries the strip and the per-month join key.
- **Scope correction, self-caught after a gate fired.** The first draft of that
  prompt swapped the month row's figures to the selected card's, which is past
  the "but just that" the owner set, and then handed them the choice instead of
  making it. Replaced with one caption line and one string.

## What Did NOT Work (and why)

- **Asserting from the backlog that the two prompts were unpasted.** Both were
  live. The backlog is written by whoever last touched it and lags the app; the
  published bundle is the cheap instrument and settled it in one fetch.
- **Swapping the months table's columns per selected card.** Beyond the scope
  the owner set, and unnecessary: "50 receipts" on the August row is a TRUE
  statement about August. One caption removes the ambiguity at no cost, and the
  card's own figures already exist one click away on `/cards`.
- **Regex chip-matching built with `new RegExp('^'+lab+'(\\\\s|...)')` through
  the PowerShell tool.** PowerShell passes backslashes through unchanged, so the
  over-escaped source reached JS as `\\s` and matched a literal backslash. Every
  chip read "not found". `String.startsWith` has no escaping surface and worked
  first try.
- **Chaining `gh pr checks --watch` and `gh pr merge` in one Bash call.** The
  no-auto-commit gate cannot see a CI verdict produced inside the same
  invocation, so it asked on all five merges this session even though every PR
  was green. Separate calls would have been silent.

## Current Status

Fly `brisken-expense-recon` serves `24034c4c`. Live and driven: `/cards` (nav,
strip, drill-down, prose footnote), `/months` card filter (six selections plus
the empty case, columns unchanged in every state), the reimburse-edit control,
and "Receipts by email" on the months list.

Brisken ops: platform unknown plan, last assessed unknown. Comms log 16 days
stale.

## Next Steps

1. Dirk: statements for cards 9693, 0113, 6013 and 8311. The Cards page now
   states the gap itself, behind "Show 4 cards with nothing loaded".
2. Criss or owner: card 3645's `zoho_account` (item 172), and the two August
   rows where her card pick contradicts the confirmed statement charge
   (`0008__Invoice-HMVWDWIL-0029.pdf`, `0027__Invoice-HMVWDWIL-0028.pdf`).
3. Settle the commercial framing for NEW surfaces under the October licence.
   Items 185 and 187 both shipped on an owner directive rather than a quote.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 108, 185, 187)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-months-card-filter-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`build_card_status`)
