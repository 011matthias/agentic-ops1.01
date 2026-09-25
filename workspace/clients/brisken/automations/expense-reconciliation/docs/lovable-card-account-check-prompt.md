# Lovable prompt: each card's paid-through account, checked (backlog item 172)

Paste into Lovable. The backend is live once the item-172 PR deploys; the
field below exists on `GET /api/settings`. One screen changes: Settings >
Cards (`src/components/CardsCard.tsx`, the "Zoho account" input at the
card row).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com`
(`API_BASE` in `src/lib/api.ts`). Change ONLY what is described here.

## What changes

Every card on Settings > Cards names the Zoho account it is paid through.
The backend now checks that name against the company's Zoho chart and says
when it is wrong. Show that check beside the account field. Nothing is
saved or changed automatically.

## 1. API type

In `src/lib/api.ts`, each entry of `cards_effective[]` on the settings reply
gains:

```ts
account_check?: {
  status: "ok" | "not_in_chart" | "wrong_type" | "inactive" | "no_account" | "no_chart";
  detail: string;          // English sentence from the backend, may be ""
  closest: string;         // the card account it most likely meant, "" if none
  account_id: string;
  company_org: string;
  chart_modified: string;  // ISO timestamp of the chart file
  chart_verified: boolean;
};
```

It is read-only: never send it back in a save.

## 2. On the card row

In `CardsCard.tsx`, find the card's `cards_effective` entry by `key` and,
directly under the "Zoho account" input:

- `status === "ok"`: a small green check icon inside the input's right
  edge, tooltip "Found in the company's Zoho chart as a card account." / "Encontrada no plano de contas Zoho da empresa como conta de cartão."
- `status === "no_chart"` or the field is absent: show nothing.
- Any other status: an amber line under the input (`text-amber-700`, dark
  mode `text-amber-400`, small text), with an alert icon:
  - `not_in_chart`: "This account is not in the company's Zoho chart." /
    "Esta conta não está no plano de contas Zoho da empresa."
  - `wrong_type`: "This is not a card account in Zoho." / "Esta não é uma
    conta de cartão no Zoho."
  - `inactive`: "This account is inactive in Zoho." / "Esta conta está
    inativa no Zoho."
  - `no_account`: "No Zoho account named yet." / "Nenhuma conta Zoho
    informada."
  - When `closest` is not empty, add on the same line: "Did you mean
    {closest}?" / "Você quis dizer {closest}?", with `{closest}` as a
    button styled as a link. Clicking it puts `closest` into the input
    (the same `update(i, { zoho_account })` call typing would make). It
    does NOT save; the user saves with the page's existing Save button.
  - When `chart_verified` is false, a second muted line: "The chart on file
    is from {date}; if this account was added in Zoho since, the chart may
    be what is out of date." / "O plano de contas salvo é de {date}; se a
    conta foi criada no Zoho depois disso, pode ser o plano que está
    desatualizado." `{date}` = `chart_modified` formatted as a date.
  - The backend's `detail` goes in the alert icon's tooltip, as-is.
- Once the user edits the input, hide the line for that row until the next
  settings load: the check describes the SAVED value.

## 3. Card list header

Above the card list, when at least one card has a status other than `ok`,
`no_chart` or absent, show one amber sentence: "N card(s) name an account
Zoho does not have as a card account." / "N cartão(ões) informam uma conta
que o Zoho não tem como conta de cartão."

## Do not

- Do not save anything on load or on the "Did you mean" click.
- Do not change how cards are saved or which fields a save sends.
````

## Checks after publishing (for the agent, not for Lovable)

1. Bundle: `account_check`, `chart_verified` and the PT string "Você quis
   dizer" present.
2. Cold drive Settings > Cards read-only: card 3645 shows the amber line
   with "Did you mean CHASE VISA - 2838 - TRAVEL?"; every other card's line
   matches `GET /api/settings` `cards_effective[].account_check.status`.
   Do not click Save.
