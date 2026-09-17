# Lovable prompt: an email that added nothing (item 106)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend as a JSON API. **Do NOT add Supabase or any
database.** Auth stays the existing `Authorization: Bearer <token>`.

---

## Background

On the Email intake page (`/inbound`, `InboundLogScreen.tsx`) a forwarded
email whose files all created no expense used to read "Added" in green. Four
real forwards did: two Amazon Web Services "billing statement available"
emails, an AT&T bill notice and a card summary. The tool read each as a
statement or summary page and set it aside, so nothing reached the month.
The backend now labels these rows honestly (the Status cell already renders
`status_label`, so the text is fixed without this prompt). This prompt makes
the row stand out and shows, per file, why it created no expense.

## New fields on `GET /api/inbound/log`

- `n_no_expense` (number, top level): how many emails finished with no
  expense.
- `entries[].not_added` (array, ABSENT when empty): one object per file that
  created no expense, also present on an email that did add something:

```json
{"file": "rendered-body.pdf", "why": "set_aside", "reason": "statement"}
{"file": "hotel.jpg", "why": "already_on_file"}
{"file": "scan.pdf", "why": "too_large"}
```

  `why` is `set_aside` (then `reason` is `statement`, `report_summary` or
  `other`), `already_on_file`, or an upload problem (`unsupported_type`,
  `empty_or_unreadable`, `too_large`, `upload_cap`). `file` equal to
  `rendered-body.pdf` means the email text itself.

An email "added nothing" when `status` is `ingested` or `replayed`,
`documents` is an empty array, and `batch_deleted` is not true.

## Render rules

1. **Status badge.** For an email that added nothing, draw the badge with the
   amber `held` colour classes instead of the green `done` ones. Keep the
   backend's `status_label` text. Do not change `status_kind` handling for any
   other row.
2. **Header badge.** Beside "Held: N", when `n_no_expense > 0`, show a badge
   `mail.noExpense.badge` with the count, same amber style.
3. **Expanded row.** The expand panel of an email that added nothing
   currently says `mail.expenses.none`. Replace that line, when `not_added` is
   present, with one line per entry:
   - `set_aside`: `mail.notAdded.setAside` with the file name and the reason
     text (`mail.notAdded.reason.statement` / `.report_summary` / `.other`),
     plus a link "Open the month" to `/expenses/{batch_id}` (the set-aside
     list is on that page).
   - `already_on_file`: `mail.notAdded.alreadyOnFile`.
   - anything else: `mail.notAdded.unreadable`.
   Show the file name as "the email text" (`mail.notAdded.emailText`) when it
   is `rendered-body.pdf`.
   On an email that DID add expenses, list the `not_added` lines under its
   expenses with the same keys.

## i18n (EN / PT)

| Key | EN | PT |
|---|---|---|
| `mail.noExpense.badge` | Nothing added: {n} | Nada adicionado: {n} |
| `mail.notAdded.setAside` | {file}: read as {reason}, set aside | {file}: lido como {reason}, separado |
| `mail.notAdded.reason.statement` | a bank or card statement page | uma página de extrato bancário ou de cartão |
| `mail.notAdded.reason.report_summary` | a summary page | uma página de resumo |
| `mail.notAdded.reason.other` | not a receipt | não é um recibo |
| `mail.notAdded.alreadyOnFile` | {file}: already on file, not added again | {file}: já estava no sistema, não foi adicionado de novo |
| `mail.notAdded.unreadable` | {file}: could not be read | {file}: não foi possível ler |
| `mail.notAdded.emailText` | the email text | o texto do email |
| `mail.notAdded.openMonth` | Open the month | Abrir o mês |

## Do not change

- The Status cell text source (`status_label`), the Month cell, the row
  Actions menu, "Retry held and add waiting mail", the refusals strip.
- How `held`, `resting`, `working` and `unknown` rows look.
- Any API call. This prompt only reads fields.
