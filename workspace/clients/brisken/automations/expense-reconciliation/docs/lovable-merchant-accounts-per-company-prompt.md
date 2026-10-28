# Lovable prompt: a merchant's account per company (backlog items 180 and 181)

Paste the block below into Lovable. It adds one section to each entry in
Settings > Merchants (an account picker per company) and one panel at the top
of that tab (the merchants that still need an account). The backend half is
live; nothing else on the site changes.

---

## Background

Brisken books one vendor to a different Zoho expense account in each company.
Anthropic, for example, is an IT cost in Corporate Services and an
infrastructure cost of sale in Cloud Services. A merchant used to hold one
account for every company, so the AI vendors held none and the tool asked the
model, which often refused because several accounts fit.

Each merchant can now hold one account per company. On months that use the
Zoho accounts, a receipt or card charge from that merchant books to its
company's account directly, with no model call.

## 1. The data

`GET /api/settings` carries four things this screen uses. All are already on
the response.

**`merchants[name].accounts`** (optional, absent when unset): the stored
choice, company label to account CODE.

```json
"Anthropic": {
  "aliases": [], "category": "Software & Subscriptions", "zoho_account": null,
  "accounts": {"Corporate Services": "E100020-10", "Cloud Services": "E700030-19"}
}
```

**`account_companies`**: the companies to show a picker for, one row each,
in display order. Use `label` as the picker's heading AND as the key you
save under. (The app knows two spellings of each company; `labels` lists
them. Never show both.)

```json
"account_companies": [
  {"label": "Cloud Services", "org_id": "697686691",
   "labels": ["Brisken Cloud Services, LLC", "Cloud Services"]},
  {"label": "Corporate Services", "org_id": "822741658", "labels": ["..."]}
]
```

**`gl_accounts[label]`**: that company's accounts, `[{code, name, category}]`.
`name` is the company's own wording; `category` is the group heading.

**`merchant_accounts[name]`**: for each stored code, what it is in that
company: `[{company, label, org_id, code, name, postable, reason}]`.
`postable: false` means the tool will refuse to book there; `reason` says why.

**`needs_account`**: merchants booked to a company, on a Zoho-account month,
with no account set for that company:
`[{merchant, company, org_id, n_rows, months: ["July 2026", ...]}]`.
Empty when there is nothing to do.

## 2. Settings > Merchants: an "Account per company" section on each entry

Below the existing fields of each merchant entry, add a section headed
**Account per company** / **Conta por empresa**, with one row per entry of
`account_companies`:

- Left: the company `label`.
- Right: a searchable picker of `gl_accounts[label]`, grouped by `category`,
  each option shown as `name · code`. First option: **Not set** / **Não
  definida**.
- Selected value: `merchants[name].accounts[label]`, when present.
- Under the picker, when `merchant_accounts[name]` has a row for this company
  with `postable: false`, show a small warning chip: **Cannot book here** /
  **Não é possível lançar aqui**, with the tooltip taken from the reason:

| `reason` | EN | PT-BR |
|---|---|---|
| `not_expense_relevant` | Dirk marked this account as not for card expenses in this company. | Dirk marcou esta conta como não destinada a despesas de cartão nesta empresa. |
| `no_such_code_in_org` | This company has no such account. | Esta empresa não tem essa conta. |
| `org_not_curated` | This company has no Zoho accounts set up yet. | Esta empresa ainda não tem contas Zoho configuradas. |
| anything else | This account cannot be used here. | Esta conta não pode ser usada aqui. |

Hint line under the section heading, muted:
EN: "Used on months that use the Zoho accounts. A receipt or card charge from
this merchant books to its company's account without asking the AI."
PT-BR: "Usado nos meses que usam as contas Zoho. Um recibo ou lançamento de
cartão deste fornecedor é lançado na conta da sua empresa sem consultar a IA."

### Saving

- Send `accounts` as an object of `{label: code}` holding only the companies
  that have a value. Send the CODE, never the name.
- To clear every company, send `"accounts": {}`. Omitting the key keeps what
  is stored, so a save that does not carry it changes nothing.
- Keep sending every other key of the entry exactly as received, including
  keys this screen does not edit.
- The save reply's `ignored` array may contain
  `merchants.<name>.accounts.<company>` when a value was not an account code.
  Show a toast naming the merchant and company:
  EN "The account for {merchant} in {company} was not saved: pick it from
  the list." PT-BR "A conta de {merchant} em {company} não foi salva:
  escolha-a na lista."

## 3. A "Merchants that need an account" panel

At the top of the Merchants tab, only when `needs_account` is not empty, show
a bordered panel headed **Merchants that need an account** / **Fornecedores
que precisam de uma conta**, with one line per entry:

`{merchant} · {company} · {n_rows} rows · {months joined with ", "}`
(PT-BR: `{n_rows} linhas`; singular `1 row` / `1 linha`).

Clicking a line scrolls to that merchant's entry and opens its picker for
that company. Sub-line, muted: EN "These merchants were booked to a company
that has no account set for them, so the AI chose or the row was refused."
PT-BR "Estes fornecedores foram lançados numa empresa sem conta definida para
eles, por isso a IA escolheu ou a linha foi recusada."

## 4. Check before publishing

- A merchant with no `accounts` shows every picker on **Not set**, and saving
  an unrelated field of it sends no `accounts` key (or the same map back).
- Picking an account for one company and saving sends only that company's
  code; reloading shows it selected with the account's name.
- `needs_account` empty: no panel at all.
- Both languages.
