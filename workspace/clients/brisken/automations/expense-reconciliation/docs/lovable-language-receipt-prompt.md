# Lovable prompt - language consistency + honest receipt column

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Context: backend follows the contract "stable codes, SPA localizes". Apply
item 1 FIRST - the deployed split depiction shows a blank account label on
uncategorized parts until it lands.

## 1. books_as parts (APPLY FIRST - visible gap on the live app)

`books_as` rows changed shape:

```json
{ "account": "Travel & Transport", "unassigned": false, "amount": "42.50" }
{ "account": null, "unassigned": true, "amount": "9.99" }
```

Render `unassigned: true` parts as EN "(uncategorized - assign)" / PT
"(sem categoria - atribuir)" in a muted/amber style. Never render a null
account raw.

## 2. Missing i18n keys for review reasons

The review object has always carried `reason_code`; two codes currently
fall through to the English `reason` prose. Add keys:

- `uncertain_match`: EN "This match isn't certain - confirm which receipt
  belongs here." / PT "Esta correspondência não é certa - confirme qual
  recibo pertence aqui."
- `receiptless_suggested`: EN "No receipt attached; category suggested
  from the charge - confirm it." / PT "Sem recibo anexado; categoria
  sugerida a partir da cobrança - confirme."

Also fix the existing `vendor_guess` PT wording: it must say the category
was guessed from the MERCHANT NAME (PT "nome do comerciante"), not from
the file name. Remove the orphan i18n key `col.state` (nothing renders it).

## 3. missing_fields composes from data

Rows with `reason_code: "missing_fields"` now also carry
`"missing": ["date", "amount", "currency"]` (subset). Compose the
sentence from your own localized field names (EN date/amount/currency,
PT data/valor/moeda) instead of showing the English prose. Keep the
prose as fallback for any other code without a key.

## 4. Honest receipt column + source identity

- `receipt_image_available` is now truthful: a manually typed expense
  with no document is `false`. Render EN "No receipt" / PT "Sem recibo"
  (muted text, no View button) - distinct from a failed preview.
- Rows gain `source_file` (the upload/mail filename the row came from;
  `""` for typed-in rows). Show it as a muted secondary line or tooltip
  on the receipt cell.
- Summary already carries `n_missing_receipt_image` + `has_image_info`:
  when `has_image_info` is true, add a 5th tile EN "Missing receipt
  image" / PT "Sem imagem do recibo" with that count.

## 5. Set-aside strip

`reason_label` was removed from set-aside entries (you were already
instructed to key wording on the machine `reason` code - no change if
that instruction was followed; delete any leftover reason_label usage).

## 6. Extracted data vs tool labels

Fields that come FROM the receipt (raw vendor text, the tax label
sub-line such as "Taxa de entrega") stay in the receipt's own language by
design. Give the tax_label sub-line the same "from receipt" visual
treatment raw vendor text has, and make it editable like vendor/date/
total (it is already an accepted PUT field).
