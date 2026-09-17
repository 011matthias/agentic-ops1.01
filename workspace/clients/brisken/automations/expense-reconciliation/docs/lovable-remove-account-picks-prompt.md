# Lovable prompt: remove "Account picks" from Settings > Legal entities (note #61)

> **NOT YET APPLIED.** SPA only. The backend half is live first and makes the
> order safe either way: `PUT /api/settings` accepts an entity that still
> carries `account_picks` and drops it, and `GET /api/settings` never returns
> it (`docs/api-contract.md`, "`account_picks` is gone from `entities`").

Owner, note #61 on this field: "maybe make these dropdown so user does not
have to know the exact numbers by heart". Told what it does (it shortens the
list of accounts a company's expense rows offer; empty means the full chart),
he ruled on 2026-09-17 to remove it: every row always offers the company's
full chart. None of the five live entities carries a value, so nothing on
any expense row changes.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One change, on the Settings page, Legal entities tab. No new field, no new request, no new text.

## Remove the "Account picks" field

The backend no longer uses an entity's `account_picks`: every expense row offers the company's full chart of accounts. Take the field out of the Legal entities editor completely.

1. In an entity's open row, delete the whole "Account picks" block: its label (`set.entities.col.accountPicks`), its text input (placeholder `6010 Meals, 6020 Travel`), the "Comma-separated" line under that input (`set.entities.listHelp`), and the help line under it (`set.entities.help.accountPicks`).
2. Remove `account_picks` from the editor's row state everywhere it appears: the empty new row, the mapping that loads each entity from `GET /api/settings` (today `(account_picks ?? []).join(", ")`), the check that decides whether a row has anything set, and the save payload.
3. The Legal entities save keeps sending `{"entities": {...the whole map...}}` exactly as today, with each entry carrying only `org_id`, `chart_path`, `default_paid_through` and `scope_groups`.
4. Delete `set.entities.col.accountPicks` and `set.entities.help.accountPicks` from both languages (EN "Account picks" / "The accounts the expense list offers for this company's rows. Leave empty to offer the company's chart of accounts."; PT-BR "Contas preferidas" / "As contas que a lista de despesas oferece para as linhas desta empresa. Deixe vazio para oferecer o plano de contas da empresa.").

## Do not change

- Every other field in the entity row: Zoho org id, Chart of accounts path, Default paid through with its help line, Scope groups with its "Comma-separated" line. `set.entities.listHelp` stays in the dictionary; Scope groups still uses it.
- The row summary, drag-to-reorder, add and remove, and the save button and its toast.
- The account dropdown on expense rows. It reads `account_options` from the batch payload, which the backend already fills from the company's chart.

## Checking it landed

Do not save anything: open rows and read them only.

1. `/settings`, Legal entities tab, open Corporate Services: the fields read Zoho org id, Chart of accounts path, Default paid through (with its help line), Scope groups (with "Comma-separated" under it), and nothing after Scope groups. No "Account picks" label, no `6010 Meals, 6020 Travel` placeholder, no "The accounts the expense list offers..." line.
2. Switch to Portuguese and open the same row: no "Contas preferidas", and "Separado por vírgula" still sits under "Grupos de escopo".
3. Bundle: `account_picks` absent from `chunk-settings`; `set.entities.col.accountPicks` and `set.entities.help.accountPicks` absent from `chunk-i18n`; `set.entities.listHelp` and `set.entities.col.scopeGroups` still present.
````
