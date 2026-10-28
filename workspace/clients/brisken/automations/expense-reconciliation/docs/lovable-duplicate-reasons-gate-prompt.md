# Lovable prompt: the duplicate panel shows the four reasons it now hides (item 223, front 4)

> **NOT YET APPLIED.** SPA only: one set in `CompareCopies.tsx`, plus one
> i18n entry if `lovable-copies-kind-prompt.md` has not added it yet. The
> backend already sends every one of these `basis` values.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/CompareCopies.tsx` (one set) and, only if missing, `src/lib/i18n.tsx` (one key, EN and PT). No new field and no new request.

## Why

Every duplicate group says why the tool decided it (`duplicate_groups[].basis`), rendered by `duplicateReason()` in `CompareCopies.tsx` through `wb.dups.basis.<basis>`. That function uses the key ONLY when the basis is in the `BASIS_KEYS` set; any other basis reads the fallback "Decided by the tool". `BASIS_KEYS` still lists only the first seven reasons (`hash`, `reference`, `printed_reference`, `vendor_date`, `distinct_reference`, `receipt_card`, `statement`), so the labels added for the newer reasons are in `i18n.tsx` but never shown:

- `reference_digits`: "Same number, written differently"
- `misread_digit`: "Same slip, one digit read differently"
- `body_twin`: "The email repeats the attached invoice"
- `intake_twin`: "Invoice and receipt from one email" (an invoice and its payment receipt that arrived in one email; every such pair from now on)

Counted on the live months on 2026-09-27: July holds 6 `reference_digits` groups and 1 `misread_digit`, August 1 `body_twin`, September 4 `body_twin`. All 12 read "Decided by the tool" today.

## 1. `CompareCopies.tsx`: four more reasons pass the gate

Add `"reference_digits"`, `"misread_digit"`, `"body_twin"` and `"intake_twin"` to the `BASIS_KEYS` set. Nothing else in the file changes; the reviewer lines ("Set aside by a reviewer" / "Kept apart by a reviewer") still win first.

## 2. `i18n.tsx`: only if a key is missing

Search `i18n.tsx` for `wb.dups.basis.intake_twin`. If it is not there, add it next to the other `wb.dups.basis.*` keys:

| Key | EN | PT |
|---|---|---|
| `wb.dups.basis.intake_twin` | Invoice and receipt from one email | Fatura e recibo do mesmo e-mail |

The other three keys exist in both languages already; do not change their wording. Every name you add to `BASIS_KEYS` must have its key in both languages, or the panel would print the raw key.

## Checking it landed

Read only; open the duplicate panels, do not click "Not a copy".

1. July 2026 Matching (`/runs/50622baec444`), Duplicates panel: a group of two slips read two ways shows "Same number, written differently" (one shows "Same slip, one digit read differently"), not "Decided by the tool".
2. September 2026 Matching (`/runs/51a22ad72864`): a group holding a `…rendered-body.pdf` shows "The email repeats the attached invoice".
3. No live month holds an `intake_twin` group yet (they start with mail arriving after 2026-09-27); the published bundle carries `intake_twin` inside the `BASIS_KEYS` set and `wb.dups.basis.intake_twin` in EN and PT.
````
