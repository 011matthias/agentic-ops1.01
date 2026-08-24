# Lovable prompt: the month pool on the inbound page

> **APPLIED 2026-08-25. DO NOT PASTE THIS FILE.**
>
> Sections 1 through 11 are live on the published SPA (verified: the
> "Waiting" badge, the Month column reading "August 2026 (waiting)", Dismiss
> on pooled rows, "Retry held and add waiting mail"). Re-running them would
> fight the change that supersedes them.
>
> The two sections that were NOT applied moved out, rewritten to account for
> everything already live: **`lovable-inbound-status-refusals-prompt.md`**.
> Paste that one instead.
>
> This file is kept as the record of what the round asked for.

Backend is already deployed. Every field named here is NEW and PARALLEL:
nothing the page already renders changed type or meaning, so the page keeps
working if you ship only part of this.

---

## The change in one paragraph

Emailed receipts used to file into whichever expense month happened to be
open, which is how August receipts landed in the April month. They now file
by the month printed ON the receipt. When that month has no expense batch
yet, the mail does not fail and is not "held": it waits in a **pool**, and
it is added automatically the moment someone creates or renames a batch to
that month. Nothing is lost and nobody has to click anything.

The inbound page has to show that waiting state honestly, because "waiting"
is now a normal, healthy outcome rather than a problem.

## 1. The `pooled` status

`entries[].status` can now be `"pooled"`. Treat it as its own state, NOT as
a held state and NOT as an error:

- Colour it neutral or informational (blue/grey), never red or amber.
- It must not be counted in the Held badge. The backend already keeps it out
  of `n_held`.
- Label it **Waiting for its month** rather than the raw word "pooled".

Two other transient statuses can appear briefly: `routing` and `claiming`.
Render them as "Working..." with a spinner if you show them at all. They
resolve within seconds; they never need an action.

## 2. Month column

Rows now carry `pool_month` (a `"YYYY-MM"` string) whenever the backend has
read the receipt's month. Use it as follows:

- **Row already in a batch** (has `batch_label`): keep showing `batch_label`
  exactly as today. Optionally show `pool_month` as a muted subtitle.
- **Row with `status === "pooled"`**: show the month in human form
  ("July 2026") plus a short waiting note driven by `pool_month_state`:

| `pool_month_state` | Show |
|---|---|
| `"no_batch"` | `July 2026 (waiting)` |
| `"open"` | `July 2026 (being added)` |
| `"closed"` | `July 2026 (already reconciled)` |

`"open"` is transient and usually resolves on the next refresh. `"closed"`
means the month already has a bank statement attached, so it is not taking
new receipts; that is the one case where a human may want to intervene.

Format the month yourself from `"YYYY-MM"`; do not ask the backend for a
display string. If `pool_month` is missing, fall back to what the row shows
today.

## 3. Two more per-row fields

- `receipt_month_source` explains how the month was decided. Show it as a
  tooltip or muted caption on the month cell:
  - `"receipt"`: "read from the receipt" (no caption needed, this is normal)
  - `"arrival"`: "no date could be read; filed under the month it arrived"
  - `"implausible-receipt"`: "the printed date looked wrong; filed under the
    month it arrived"
- `mixed_months` is `true` (or absent) when one email carried receipts from
  more than one month. The whole email files under the earliest of them.
  Show a small badge: "spans two months". This is the operator's cue that a
  receipt may need moving by hand after it lands.

## 4. A Pool badge beside Held

The payload gains a top-level `n_pooled` alongside `n_held`. Add a second
badge next to the Held badge:

- Held: red/amber, as today. Means something needs a human.
- Pool: neutral. Means mail is waiting for its month, which is fine.

Label it **Waiting** with the count. When `n_pooled` is 0, hide it, the same
way Held behaves.

## 5. Pooled rows get Dismiss

The Dismiss action was available on held rows only. It must now also appear
on rows with `status === "pooled"`. Junk that carries an attachment now rests
in the pool, and without Dismiss it would sit there forever.

Same endpoint, same confirm, same result: `POST /api/inbound/{archive}/dismiss`.

## 6. The replay button does more now

The button currently labelled around "Retry held emails" now does two things
in one press: it re-routes held mail, and it adds any pooled mail whose month
is open. Update the copy to say so, for example **"Retry held and add waiting
mail"**.

The response gains counts. Report them plainly in the toast:

```
{ replayed, pooled, claimed, still_held, still_pooled, failed }
```

Something like: "3 added, 2 still waiting for their month, 1 held". Do not
report `pooled` as a failure; it means mail was correctly parked.

## 7. Batch creation: the month advisory

`POST /api/expense-batches` now returns `month` (a `"YYYY-MM"` string, or
`null`) and, when `month` is null, an `advisory` string.

`null` means the batch's label does not name a month, so emailed receipts can
never join it. The default label is a full date, which is a timestamp and not
a month, so this fires on every batch created without an explicit label.

After a successful create, if `month` is null, show the returned `advisory`
text as an informational banner on the new batch, with a **Rename** action
that opens the existing rename dialog. Do not block anything; the batch is
perfectly usable for uploaded receipts. The advisory is only about mail.

Suggest a label in the rename field in the form "July 2026". Accepted forms
are "April 2026", "abril 2026", "2026 Apr" and "2026-04". A label carrying a
full date is rejected as a month on purpose.

## 8. Rename now reports its month

`POST /api/runs/{id}/rename` returns `month` too. When it comes back non-null,
any mail waiting for that month is being added right now, on a background
thread. Show a toast: "July 2026. Any waiting receipts for this month are
being added." Then refresh the inbound log after a couple of seconds so the
rows flip from waiting to added.

## 9. Deleting a month

`POST /api/runs/{id}/delete` gains `pooled_back` beside the existing
`inbound_marked`.

Mail that belonged to the deleted month goes BACK to the pool; re-creating
that month picks it up again automatically. Say that in the confirmation
toast when `pooled_back > 0`: "4 emailed receipts are waiting again for
July 2026. Re-create that month and they are added automatically."

`inbound_marked` keeps its old meaning (older mail that predates month
stamping, which still needs the manual re-ingest action) and is normally 0.
Do not present the two as the same number.

## 10. Body-only render no longer refuses

`POST /api/inbound/{archive}/render-ingest` used to return 409 when no month
was open. It now always renders, and returns either `status: "ingested"` (as
today) or `status: "pooled"` with a `pool_month`. Handle the pooled outcome as
a success: "Rendered. Waiting for July 2026."

## 11. The confirmation email wording changed

For context only, no UI work. The automatic reply to a sender now names where
the receipt went: either the batch it joined, or the month it is waiting for
plus the fact that it joins automatically. If any help text in the SPA
describes that email, it should match.

## Contract rules for this round

- Every field above is additive. Render defensively: check the field exists
  and has the type you expect before using it, and fall back to today's
  rendering when it does not.
- No existing list field changed element type, so no existing renderer needs
  touching.
- Do not retype or repurpose `n_held`, `inbound_marked`, or `status` values
  you already handle.
- Body-only mail from a recognised sender no longer reaches
  `held_body_only`: it is read on arrival. The Held strip now holds only
  mail from senders we do not recognise, plus mail that genuinely failed, so
  any copy telling the operator to click "Read email body" on every
  forwarded receipt is out of date.
