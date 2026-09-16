# Lovable prompt - publishing says what it saved to memory (item 88)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

Corrections made in a month (a vendor spelling, a paying account, a company, a
category) only teach the next month when someone presses "Save corrections to
memory", and nobody had pressed it: the tool had learned no company and no
field correction. The owner ruled that signing a month off saves its
corrections automatically. Publish is the sign-off, so the backend now saves
the month's corrections when a month is published. The page should say so.

## 1. The new field (`POST /api/runs/{id}/publish`)

The reply keeps `ok`, `run_id` and `published`, and gains `memory`:

- `{ "saved": true, "learned": { "merchant_categories": n, "merchant_entities": n, "field_corrections": n, ... } }`
- `{ "saved": false, "reason": "unchanged" }`: nothing new since the last save
- `{ "saved": false, "error": "..." }`: the save failed; the month IS published

## 2. The publish toast (`RunWorkbench.tsx`, the `publish` mutation)

In `publishRun` (`src/lib/api.ts`) type the reply as
`{ ok: boolean; memory?: { saved: boolean; reason?: string; error?: string; learned?: Record<string, number> } }`.

In the mutation's `onSuccess`, when publishing (`next === true`):

- `memory?.saved === true`: let `n` be `(learned.merchant_categories ?? 0) +
  (learned.merchant_entities ?? 0) + (learned.field_corrections ?? 0)`, the
  same three the Expenses page's own save toast adds. Show
  `t("toast.publishedSaved", { n })` when `n > 0`, else
  `t("toast.published")`.
- `memory?.reason === "unchanged"` or `memory` absent: `t("toast.published")`,
  as today.
- `memory?.error`: `toast.success(t("toast.published"))` and also
  `toast.warning(t("toast.publishedMemoryFailed"))`.

Unpublishing is unchanged.

## 3. The Expenses page's save button explains the automatic save

Change the tooltip of "Save corrections to memory"
(`expx.review.actions.commit.tip`) to the new text below. The button stays
where it is and does what it does.

## 4. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `toast.publishedSaved` | Month published; {n} corrections saved to memory for next month | Mês publicado; {n} correções salvas na memória para o próximo mês |
| `toast.publishedMemoryFailed` | Published, but the corrections could not be saved to memory. Use "Save corrections to memory" on the Expenses page. | Publicado, mas as correções não puderam ser salvas na memória. Use "Salvar correções na memória" na página de despesas. |
| `expx.review.actions.commit.tip` (changed) | Save these edits now so next month arrives pre-filled. Publishing the month saves them too. | Salve estas correções agora para o próximo mês vir preenchido. Publicar o mês também as salva. |

## 5. Do not change

The Publish / Unpublish buttons, their disabled rule (`sum.publish.blocked`),
"Commit learnings" and "Save corrections to memory" themselves, and every
other toast.

## 6. After publishing, check

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit):
   `toast.publishedSaved`, `toast.publishedMemoryFailed`.
2. Nothing to drive on a live month: publishing is Criss's sign-off, and no
   month has been published yet. Confirm by bundle only, and read the toast
   the first time a month is published.
