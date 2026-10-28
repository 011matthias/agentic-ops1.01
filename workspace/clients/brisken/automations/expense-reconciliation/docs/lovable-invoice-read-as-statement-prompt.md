# Lovable prompt: an invoice kept after being read as a statement page (item 105)

**Background.** The receipt reader sometimes calls a real invoice a bank or
card statement page, and those files used to be set aside. Since item 105 the
backend keeps such a file as an expense when it prints a vendor, a total, an
invoice number and its own line items, and the row asks for a look until the
reviewer confirms its category. The row already renders: its review reason
arrives as English prose from the backend, because the SPA has no copy for the
new reason code yet. This prompt adds that copy in English and Portuguese.
Nothing else changes.

## Paste this into Lovable

In `src/lib/i18n.tsx`, add one review-reason key in both languages, next to
the other `expx.review.reason.*` keys:

- English:
  `"expx.review.reason.invoice_read_as_statement": "This looked like a bank or card statement page, but it prints its own invoice number and line items, so it was kept as an expense. Check it is one purchase, then confirm its category."`
- Portuguese:
  `"expx.review.reason.invoice_read_as_statement": "Parecia uma página de extrato bancário ou de cartão, mas tem número de fatura e itens próprios, então foi mantida como despesa. Confira se é uma única compra e confirme a categoria."`

The expenses grid already resolves `review.reason_code` through
`reasonKey()` / `reviewReason()` in `ExpensesReviewGrid.tsx`, so no component
change is needed: with the key present, the row shows this copy instead of the
backend prose. The existing "Confirm category" control (note #62, driven by
`expenses[].category_confirmable`) is what clears the check; it is already
offered on these rows.

**Do not change:** the review-reason lookup, the Confirm category control,
any API call, auth (bearer token), or any other i18n key.

## Verify after publish

Bundle audit: `chunk-i18n` carries `expx.review.reason.invoice_read_as_statement`
in both languages. No live row has this reason today (the July invoices sit in
the set-aside strip and are not re-sorted), so the render is verified on the
next invoice the reader calls a statement page.
