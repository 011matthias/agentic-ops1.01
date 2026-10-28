# Lovable prompt: categories become Zoho accounts (Phase 1)

**APPLIED 2026-09-24** (published and driven; evidence and the two checks the
backend cannot reach are in `PROMPT-STATUS.md`). The GL engine is live since Fly `45d4c494` (2026-09-24 15:02
UTC): every month created from then on categorizes each line straight into one
of Dirk's curated Zoho accounts (194 postable leaves, revision `2026-09-24`)
instead of the eight buckets, and refuses on purpose when it cannot place one.
The published SPA knows none of this. On a month created on the new engine it
would show every category as blank (a leaf code is not one of the eight) and
offer the eight buckets, which the server accepts, so a pick there would put a
bucket on a month that posts by account. Publish before the next month is
created.

**Backend it reads (PR for this prompt, deployed before the paste):**
`category_vocabulary` (`"gl"` / `"buckets"`) on both month views, and
`gl_accounts` keyed by the same entity labels rows carry. Every name and code in
the check table was read off the live API on 2026-09-24.

````markdown
Some months now categorize into Zoho accounts instead of the eight categories. Teach the Expenses and Matching pages to show and pick accounts on those months, and to say why the tool left an account blank. Months made before this change must look and behave exactly as today. Do NOT add Supabase or any database; the app calls the FastAPI backend at `https://api.expenses.brisken.com` with the existing `Authorization: Bearer <token>`.

## 1. The data (already served; add the types to `src/lib/api.ts`)

Both month payloads, `GET /api/expense-batches/{id}` (Expenses page) and `GET /api/runs/{id}` (Matching page), now carry:

- `category_vocabulary`: `"gl"` or `"buckets"`. Treat a missing value as `"buckets"`.
- `gl_accounts`: an object keyed by company label, each value a list of `{ code: string, name: string, category: string }`. Example key: `"Corporate Services"`. `code` looks like `E100010-31`; `name` is that company's own Zoho wording, and the same code is worded differently per company (`E100010-31` is `"CorpServ | Travel Expense | Food"` for Corporate Services and `"Travel Expense | Food"` for Cloud Services), so always look the name up under the row's own company; `category` is the group heading, e.g. `"Travel Expense"`.
- `gl_revision`: a string such as `"2026-09-24"`.

A company that is NOT a key of `gl_accounts` has no account list. That is different from an empty list; treat both as "no list" on screen.

Look a row's company up with one helper, used everywhere, trimmed and case-insensitive against the keys (a direct `gl_accounts[entity]` misses on a spelling difference in case or spacing):

```ts
export function accountsFor(
  gl: Record<string, GlAccount[]> | undefined,
  company: string | null | undefined,
): GlAccount[] | undefined {
  const key = (company ?? "").trim().toLowerCase();
  if (!key || !gl) return undefined;
  return Object.entries(gl).find(([k]) => k.trim().toLowerCase() === key)?.[1];
}
```

`undefined` or an empty list both mean "no list".

## 2. Only when `category_vocabulary === "gl"`

Everything in this section applies only on a `"gl"` month. On a `"buckets"` month every picker keeps `category_options` and every label stays as it is today.

**Showing a category.** On a `"gl"` month a category value is an account code. Wherever the page shows a category (the row's category picker value, the per-line pickers, the Matching charge category, the candidate's category, the duplicate compare field, the variance chip's list), show the account's `name` from `gl_accounts[row company]`, with the code after it in small muted text: `CorpServ | Travel Expense | Food · E100010-31`. If the code is not in that company's list, show the code alone followed by the muted text from `gl.code.notInList`. Never show a raw code without trying the lookup first.

**Picking.** The four category pickers:
1. the Expenses row category `Select` (`ExpensesReviewGrid`, value `posting_category.category`),
2. the per-line pickers (`OpenLinePickers`),
3. the Add expense dialog's category `Select`,
4. the Matching charge category cell (`ChargeCategoryCell` in `RunWorkbench`) and the candidate rows it passes `categoryOptions` to.

On a `"gl"` month each offers `accountsFor(gl_accounts, company)` instead of `category_options`, where `company` is the row's `legal_entity_id` (in the Add expense dialog, the company currently chosen in that dialog). A company holds 62 to 68 accounts, so use a searchable combobox, not a plain `Select`: the existing `Popover` + `Command` components (`src/components/ui/command.tsx`), with a `CommandInput` (placeholder `gl.picker.search`) that matches the name or the code, a `CommandGroup` per `category` in the order they arrive, and `CommandEmpty` showing `gl.picker.noMatch`. Each item shows `name` with the code in muted text; the value sent is the `code`. The trigger shows the current account the way "Showing a category" above describes. Keep the existing undo item where it exists.

Send the code exactly where each picker sends the category name today; only the value changes:

| Picker | Call and body |
|---|---|
| Expenses row | the existing row mutation, `{ field: "category", value: "<code>" }` |
| Per-line | `postCategory(runId, { document_id, line_index, category: "<code>" })`, with NO `zoho_account` on a `"gl"` month |
| Add expense | `addExpense(runId, { ..., category: "<code>" })` |
| Matching charge | `setChargeCategory(runId, transactionId, "<code>")`, i.e. `PUT .../charges/{id}/category` with `{ category: "<code>" }` |

Clearing is unchanged (`""`). On a `"gl"` month, hide the Expenses row's separate Zoho account picker (the `Select` that sends `{ field: "zoho_account" }`): the account IS the category there, and a second account field would contradict it.

- No company on the row (empty `legal_entity_id`): the picker is disabled and shows `gl.picker.noCompany` as its placeholder.
- A company with no list: the picker is disabled and shows `gl.picker.noList`.
- Otherwise the placeholder is `gl.picker.placeholder`.

When a save reply carries `ignored` (the server did not recognise the value), show the existing error toast; do not treat it as saved.

## 3. Why an account was left blank (both kinds of month)

A row's `review` can now carry `reason_code: "category_refused"` with a second field `refusal`, one of: `entity_missing`, `org_not_curated`, `no_such_code_in_org`, `not_expense_relevant`, `account_unresolved`. `review.reason` holds the English sentence.

- Expenses page: in `reviewReason`, handle `category_refused` like `missing_fields` is handled: use the key `gl.refusal.${review.refusal}`; if that key has no translation, fall back to `review.reason`. Do not add a generic `expx.review.reason.category_refused` string.
- Matching page: when a charge row's `review.reason_code === "category_refused"`, show the same localized sentence in small muted text directly under that row's category picker.
- An unknown `refusal` value always falls back to `review.reason`, never to an empty line.

## 4. Strings (EN dictionary and the PT mirror in `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `gl.picker.placeholder` | Pick an account | Escolha uma conta |
| `gl.picker.noCompany` | Set the company first | Defina a empresa primeiro |
| `gl.picker.noList` | No account list for this company | Sem lista de contas para esta empresa |
| `gl.picker.search` | Search accounts | Buscar contas |
| `gl.picker.noMatch` | No account matches | Nenhuma conta encontrada |
| `gl.code.notInList` | not in this company's accounts | fora das contas desta empresa |
| `gl.refusal.entity_missing` | This expense has no company yet, so no account was picked. Set the company, then pick the account. | Esta despesa ainda não tem empresa, então nenhuma conta foi escolhida. Defina a empresa e depois escolha a conta. |
| `gl.refusal.org_not_curated` | No curated Zoho account list is set up for this company, so the tool did not guess an account. Pick one by hand. | Nenhuma lista de contas do Zoho está definida para esta empresa, então a ferramenta não tentou adivinhar uma conta. Escolha uma manualmente. |
| `gl.refusal.no_such_code_in_org` | The account remembered for this merchant does not exist in this company's Zoho chart. Pick one by hand. | A conta lembrada para este fornecedor não existe no plano de contas do Zoho desta empresa. Escolha uma manualmente. |
| `gl.refusal.not_expense_relevant` | The account remembered for this merchant is not one a card expense may post to in this company. Pick one by hand. | A conta lembrada para este fornecedor não é uma em que despesas de cartão possam ser lançadas nesta empresa. Escolha uma manualmente. |
| `gl.refusal.account_unresolved` | The tool could not tell which Zoho account this belongs to. Pick one by hand. | A ferramenta não conseguiu identificar a qual conta do Zoho isto pertence. Escolha uma manualmente. |

Account names come from Zoho and are never translated.

## 5. Do not change

- Anything on a `"buckets"` month: pickers, labels, filters, counts, exports.
- Settings (merchants, cards, entities), the Memory screen and the Cards page.
- The endpoints, request bodies and query keys; only the values sent from the four pickers change, and only on a `"gl"` month.

## 6. How to check it worked

1. Open July 2026 (`/months`, then July): the category pickers still list the eight categories and the values read as before.
2. On a month made after this change, a Corporate Services row booked to `E100010-31` reads `CorpServ | Travel Expense | Food · E100010-31`, a Cloud Services row with the same code reads `Travel Expense | Food · E100010-31`, and each picker lists only its own company's accounts, grouped under headings such as `Travel Expense` and `Marketing & Selling Expenses`.
3. A row with no company shows a disabled picker reading "Set the company first", and its review line reads "This expense has no company yet, so no account was picked. Set the company, then pick the account."
4. Switch the language to Portuguese: the same review line reads "Esta despesa ainda não tem empresa, então nenhuma conta foi escolhida. Defina a empresa e depois escolha a conta."
5. Pick an account on that row after setting its company: the row shows the account name, and a reload keeps it.
6. In a Corporate Services picker, typing `food` keeps `CorpServ | Travel Expense | Food` among the matches, and typing `E100010-31` leaves that one item. The row shows no separate Zoho account picker.
````

## Checking it landed (for us, after the owner publishes)

1. Lovable repo `main` and the live bundle both carry `category_vocabulary`,
   `gl_accounts`, `category_refused` and the `gl.refusal.` keys (bundle audit,
   not the repo alone: pasted is not published).
2. Cold drive of July on `expenses.brisken.com`: pickers list the eight, no
   `gl.` string renders.
3. A GL month: none exists live yet. Create a batch labelled exactly
   `TEST - GL drive` (no month name, so mail intake never routes to it and no
   month borrows from it) via `POST /api/expense-batches`. Add one synthetic
   receipt for Corporate Services and one with no company by DIRECT upload
   (`POST /api/expense-batches/{id}/receipts`), never by mail: a deleted
   batch's mail archives are re-pooled, direct uploads are not. Check rows 2
   to 6 of section 6 in EN and PT. Never Publish it (Publish writes durable
   memory). Purge in the same session with
   `POST /api/runs/{id}/delete` and body `{"confirm": "TEST - GL drive"}`,
   then prove it gone: `GET /api/runs/{id}` answers 404 and the months list
   no longer shows it. Uploading costs a little OpenAI credit, so it waits
   for the top-up too.
