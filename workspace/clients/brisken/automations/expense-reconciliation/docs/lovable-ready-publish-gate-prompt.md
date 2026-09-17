# Lovable prompt: Ready to post means complete; Publish is gated (items 99 + 100)

Paste this into the `brisken-expense-review` Lovable project.

The app calls the FastAPI backend at `https://api.expenses.brisken.com`. **Do NOT add Supabase or any database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

July 2026 shows a green "Ready to post" pill and an enabled Publish while 24
charges have no receipt and 11 receipts have no charge. The pill reads
`summary.ready_to_post`, which only means "nothing left to decide". The
backend now says whether the month is COMPLETE, says what blocks it, refuses
to publish an incomplete month unless the request overrides, and records who
published. Nothing else about the page changes.

## 1. New fields (`GET /api/runs/{id}`)

On `summary` (all optional for an older backend):

- `month_complete` (boolean): the month may read Ready to post and be published.
- `n_charges_need_receipt` (integer): charges with no receipt and nothing that closes them.
- `n_receipts_need_charge` (integer): receipts with no charge that are not set aside.
- `n_charges_category_guessed` (integer): charges needing no receipt whose category is still the tool's guess.
- `ready_to_post` and `n_undecided` keep their meaning: nothing left to decide.

Top level of the run payload:

- `published` (boolean), `published_at` (ISO string or null), `published_by` (string or null), `published_override` (boolean).

In `src/lib/api.ts`: add the four summary keys as optional to `RunSummary`, and
the four `published*` keys as optional to `RunDetail`.

## 2. Publish call (`src/lib/api.ts`, `publishRun`)

Change to `publishRun(runId: string, publish: boolean, opts?: { override?: boolean })`.
Send `body: { override: true }` only when `publish && opts?.override`; send no
body otherwise. Extend the reply type with optional `published_at`,
`published_by`, `published_override`, and for unpublish
`memory?: { unlearned?: boolean; kept?: boolean; saved_at?: string; trigger?: string }`.

A refusal is HTTP 400 `{ error, code, readiness? }` with `code` one of
`month_not_complete`, `no_statement`, `not_a_month`. `apiFetch` already throws
`ApiError` with `data`; read `code` from `e.data`.

## 3. The pill (`StatusLine` in `src/components/RunWorkbench.tsx`)

`const complete = typeof summary.month_complete === "boolean" ? summary.month_complete : summary.ready_to_post;`

- `complete`: green pill `sum.readyToPost`, as today.
- broken month: as today.
- otherwise amber pill: `sum.notComplete`, then ` · ` and each non-zero
  blocker in this order: `n_undecided` (existing `sum.blocked.count` /
  `.plural` text), `n_charges_need_receipt` (`sum.needReceipt.one` / `.many`),
  `n_receipts_need_charge` (`sum.needCharge.one` / `.many`),
  `n_charges_category_guessed` (`sum.guessed.one` / `.many`). Treat a missing
  count as 0.
- When `summary.ready_to_post === true` and not `complete`, add a muted
  caption after the pill: `sum.nothingToDecide`.

## 4. Publish button (`src/components/SummaryBar.tsx` + the `publish` mutation in `RunWorkbench.tsx`)

- Pass `complete` (the rule above) into `SummaryBar` and key the button on it,
  not on `ready_to_post`. Leave the other buttons as they are.
- Published state: `const isPublished = typeof data.published === "boolean" ? data.published : <today's operator-state lookup>;`
- Published: "Unpublish" as today.
- Not published and `complete`: click publishes with no body, as today.
- Not published and not `complete`: the button stays enabled with tooltip
  `sum.publish.override.tip` and opens an `AlertDialog`
  (`@/components/ui/alert-dialog`): title `pub.override.title`, body
  `pub.override.body`, then the same blocker list as the pill (one per line),
  buttons `pub.override.cancel` and `pub.override.confirm`. Confirm calls
  `publishRun(runId, true, { override: true })`.
- `onError`: when `e.data?.code` is `month_not_complete`, `no_statement` or
  `not_a_month`, toast `pub.refused.<code>`; otherwise `e.message` as today.
- On success invalidate the run query as well as `operator-state`, so the
  pill and the published line refresh.
- Unpublish success: when `res.memory?.kept === true`, toast
  `toast.unpublishedKept`; otherwise today's `toast.unpublished`.

When `published` is true, show one muted line beside the button:
`pub.by` with `{by}` = `published_by` and `{date}` = `published_at` formatted
like the page's other dates, plus ` · ` and `pub.withOpenItems` when
`published_override` is true. Hide the line when `published_by` is absent.

## 5. Guide (`src/lib/i18n.tsx`, `guide.finish.p1`, used by `GuideScreen.tsx`)

Replace both texts with the strings in section 7.

## 6. Retire /classic (`src/routes/classic.tsx`)

Replace the route with a redirect: `beforeLoad: () => { throw redirect({ to: "/months" }); }`
(`redirect` from `@tanstack/react-router`), no component. The backend already
refuses to publish a classic run.

## 7. Strings (EN, then PT)

| Key | EN | PT |
|---|---|---|
| `sum.notComplete` | Not complete | Incompleto |
| `sum.nothingToDecide` | Nothing left to decide | Nada mais a decidir |
| `sum.needReceipt.one` | {n} charge still needs a receipt | {n} lançamento ainda sem recibo |
| `sum.needReceipt.many` | {n} charges still need a receipt | {n} lançamentos ainda sem recibo |
| `sum.needCharge.one` | {n} receipt has no charge | {n} recibo sem lançamento |
| `sum.needCharge.many` | {n} receipts have no charge | {n} recibos sem lançamento |
| `sum.guessed.one` | {n} category is still the tool's guess | {n} categoria ainda é só sugestão da ferramenta |
| `sum.guessed.many` | {n} categories are still the tool's guess | {n} categorias ainda são só sugestão da ferramenta |
| `sum.publish.override.tip` | Open items remain; publishing asks you to confirm | Há pendências; publicar pede confirmação |
| `pub.override.title` | Publish an incomplete month? | Publicar um mês incompleto? |
| `pub.override.body` | This month still has open items. Publishing signs it off, saves its corrections to memory and records that it was published with open items. | Este mês ainda tem pendências. Publicar encerra o mês, grava as correções na memória e registra que foi publicado com pendências. |
| `pub.override.cancel` | Cancel | Cancelar |
| `pub.override.confirm` | Publish anyway | Publicar mesmo assim |
| `pub.by` | Published by {by} on {date} | Publicado por {by} em {date} |
| `pub.withOpenItems` | with open items | com pendências |
| `pub.refused.month_not_complete` | This month is not complete, so it was not published. | Este mês não está completo, então não foi publicado. |
| `pub.refused.no_statement` | This month has no statement yet, so it was not published. | Este mês ainda não tem extrato, então não foi publicado. |
| `pub.refused.not_a_month` | Only a month can be published. | Só um mês pode ser publicado. |
| `toast.unpublishedKept` | Unpublished. What this month taught memory stays; remove it on the Memory page. | Despublicado. O que este mês ensinou à memória continua lá; remova na página Memória. |
| `guide.finish.p1` | When every charge has its receipt or is marked already booked, every receipt has its charge or is set aside, and nothing is left to decide, the bar turns to Ready to post. Publish signs the month off. | Quando todo lançamento tiver seu recibo ou estiver marcado como já lançado, todo recibo tiver seu lançamento ou estiver separado, e nada mais houver a decidir, a barra muda para Pronto para lançar. Publicar encerra o mês. |

## 8. Do not change

Downloads, Confirm all matched, Commit learnings, the decision calls, the
month-health banner, and every existing count's meaning.

## 9. Verify after publish

Read `GET /api/runs/50622baec444` (July) and `GET /api/runs/074a7b8905d7`
(August) first; if `summary.month_complete` is absent the backend is not
deployed yet.

1. Bundle (`uv run tools/lovable-bundle-audit.py`) hits `month_complete`,
   `n_charges_need_receipt`, `n_receipts_need_charge`,
   `n_charges_category_guessed`, `published_override`, `sum.needReceipt.many`,
   `pub.override.confirm`, `pub.refused.month_not_complete`.
2. July, Matching: amber "Not complete · 24 charges still need a receipt · 11
   receipts have no charge" with the caption "Nothing left to decide".
3. August, Matching: amber "Not complete · 8 rows to decide · 100 charges
   still need a receipt · 10 receipts have no charge · 1 category is still
   the tool's guess".
4. On either month, Publish opens the confirm dialog listing the same
   blockers. Press Cancel; do not publish a real month.
5. `/classic` lands on `/months`.
6. PT: "Incompleto", "lançamentos ainda sem recibo", "Publicar mesmo assim".
7. Network: no POST other than `/api/login` during the drive.
