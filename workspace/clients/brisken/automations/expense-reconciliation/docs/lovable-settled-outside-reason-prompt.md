# Lovable prompt: the row settled outside the card system, in Portuguese (item 144)

> **NOT APPLIED** (see PROMPT-STATUS.md). Backend shipped 2026-09-17 (PR #1074,
> live on Fly): a row whose `settled_outside` carries a `how` leaves the
> `needs_person` box, reads `can_mark_private: false`, and carries
> `review.reason_code: "needs_entity_settled_outside"`. The row already renders;
> its reason arrives as English prose because the SPA has no copy for the new
> code. No backend or API change.

````markdown
In `src/lib/i18n.tsx`, add one review-reason key in both languages, next to the other `expx.review.reason.*` keys:

- English:
  `"expx.review.reason.needs_entity_settled_outside": "This expense was settled outside the card system, so no card will name the company it belongs to. Set the legal entity on the row; the export shows a placeholder until then."`
- Portuguese:
  `"expx.review.reason.needs_entity_settled_outside": "Esta despesa foi paga fora do sistema de cartões, então nenhum cartão vai indicar a empresa à qual ela pertence. Defina a entidade legal na linha; a exportação mostra um espaço reservado até lá."`

The expenses grid already resolves `review.reason_code` through `reasonKey()` / `reviewReason()` in `ExpensesReviewGrid.tsx`, so no component change is needed: with the key present, the row shows this copy instead of the backend prose.

**Do not change:** the review-reason lookup, the card picker, the "Paid with a private card" option (the backend already withholds it on these rows through `can_mark_private: false`), the boxes and their counts, any API call, auth (bearer token), or any other i18n key.
````

## Why this row needs its own sentence

The generic entity reason opens with "Assign this expense's paying card". On a
row settled by bank transfer there is no card to assign and never will be, so
the first thing the screen told Criss to do was the one thing she could not.
Item 144 gave the case its own reason on the backend; this is the half that
makes it readable in the language she works in.

## Checking it landed

1. Bundle: `expx.review.reason.needs_entity_settled_outside` in the i18n chunk in
   both languages, and the PT sentence "paga fora do sistema de cartões".
2. July Expenses (`/expenses/50622baec444`), the RODRIGO TANURE TRICARICO
   CONSULTORIA row of 2026-07-31 (BRL 27,203.34): in EN it reads the English
   sentence above, and in PT the Portuguese one, instead of the backend prose.
   Its card picker offers the nine company cards and no private option, and the
   row carries no person question. All of that is already live and must not move.
3. Every other row's reason is unchanged. `summary.n_needs_person` on July stays
   at its current value (13 as of 2026-09-17); this prompt renders copy and
   changes no count.
4. Network: no PUT, POST, PATCH or DELETE during the drive except
   `POST /api/login`.
