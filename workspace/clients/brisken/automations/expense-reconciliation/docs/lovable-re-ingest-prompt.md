# Lovable prompt - re-ingest mail stranded by a deleted month

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Backend is live. Without this, the recovery path exists but nobody can reach
it from the app.

## The situation

A mail delivered receipts, they were ingested into a month, and that month was
later deleted. The archive keeps the delivered files (archives are never
deleted, custody holds), but the expenses went with the month and Replay does
not touch this mail: replay is for mail that never landed, and this one did.

The Email-intake log already marks these rows: `batch_deleted: true`. They are
the only rows where the new action applies.

## 1. New per-mail action: "Re-ingest into the open month"

`POST /api/inbound/{archive}/re-ingest` (no body).

Show the action on a log row when **both** are true:

- `batch_deleted` is `true`, and
- the row delivered at least one file (`files` is non-empty).

Place it beside the existing per-mail actions (view body / render as PDF /
dismiss). It is a real ingest: expect it to take a few seconds, disable the
button while it runs, and refresh the log and the month afterwards.

Success (`200`):

```json
{ "ok": true, "status": "ingested", "archive": "20260821T121712-ab12cd34",
  "batch_id": "370e7731b502", "job_id": "…", "documents": ["0003__tren.jpg"] }
```

On success the row stops saying "month deleted" and shows the new month, so
re-fetching the log is enough; no local patching needed.

## 2. The refusals, and what to say

All refusals return `409` with `{"error": "..."}`. Show the message; none of
them is a bug.

| When | Message from the API | What the reader should understand |
|---|---|---|
| The mail's month still exists | "this mail still belongs to a live month; re-ingest exists for mail stranded by a deleted month" | Nothing to recover. This is also what a second click gets, because the first one already moved the mail. |
| No month is open | "no open month to ingest into" | Start a month first, then retry. |
| The mail had no attachment | "this mail delivered no attachment to re-ingest; a body-only mail is recovered with render-ingest" | Use the existing "Render as PDF" action instead. |
| Mid-flight or dismissed | "cannot re-ingest mail in state '…'" | Something else is acting on this mail. |

`404` means the archive id is unknown.

## 3. Do not add a bulk version

One archive at a time, on purpose. A "re-ingest everything stranded" button
would drain months of old receipts into whatever month happens to be open. The
backend has no bulk endpoint and should not get one.

## 4. Status vocabulary

A mail being re-ingested carries the transient status `re_ingesting`. Treat it
like the existing `rendering`: show it as busy, and do not offer the per-mail
actions while it is set.
