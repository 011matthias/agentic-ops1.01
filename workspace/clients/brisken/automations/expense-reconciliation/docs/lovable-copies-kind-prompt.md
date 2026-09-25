# Lovable prompt: three new duplicate reasons (front 4, 2026-09-25)

Paste the block below into Lovable. Copy only; no layout, logic or API change.

````
Background: the duplicate panel shows, for every duplicate group, why the tool
decided it (`duplicate_groups[].basis`, rendered through the i18n keys
`wb.dups.basis.<basis>`, falling back to `wb.dups.basis.unknown` "Decided by
the tool"). The backend now decides three more kinds of copy, so three new
`basis` values arrive and today render as the fallback:

- `reference_digits`: the two documents print the same number inside
  different words ("169518087198" and "Operação #169518087198").
- `misread_digit`: the same slip read twice, with one digit read differently
  (271025 and 271825), same shop, same day, same amount.
- `body_twin`: the saved text of an email repeats the invoice attached to it.

Change: add these six i18n entries next to the existing `wb.dups.basis.*`
keys in src/lib/i18n.tsx, English and Portuguese:

EN
  "wb.dups.basis.reference_digits": "Same number, written differently",
  "wb.dups.basis.misread_digit": "Same slip, one digit read differently",
  "wb.dups.basis.body_twin": "The email repeats the attached invoice",

PT
  "wb.dups.basis.reference_digits": "Mesmo número, escrito de outra forma",
  "wb.dups.basis.misread_digit": "Mesmo cupom, um dígito lido diferente",
  "wb.dups.basis.body_twin": "O e-mail repete a fatura anexada",

Do not change: any other key, the fallback key, the duplicate panel's layout,
the "Not a copy" / "Same document" controls, which member is shown as kept,
any API call, the bearer-token auth. No Supabase.
````

Verify after publish: the published bundle carries the three keys in EN and
PT (`uv run tools/lovable-bundle-audit.py`), and September's duplicate panel
shows "The email repeats the attached invoice" on the four mail-body groups
(Zoho 50.00, Lovable 60.00, Anthropic 100.00, Lovable 50.00) instead of
"Decided by the tool". Read-only drive; no control is clicked.
