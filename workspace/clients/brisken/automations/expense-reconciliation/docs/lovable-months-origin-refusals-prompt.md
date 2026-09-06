# Lovable prompt: months origin badge + refusals split line

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Standalone and small: two additive renders, no behavior change anywhere else.
Every field below is parallel — an unchanged screen keeps working without it.

---

## What changed underneath

Mailed receipts can now create their month batch on their own: a receipt
mailed in for July materializes "July 2026" if no such month exists, instead
of waiting in the pool. Months therefore now have an ORIGIN, and the operator
needs to see which months made themselves.

Separately, the intake's refused-mail counter was drowned by spam relay
probes (55 of 55 window rows in the last audit were `*@flyio.net` probes), so
the backend now splits it. The old number keeps its meaning.

## 1. `/months`: origin badge on auto-created months

`GET /api/expense-batches` rows now carry `created_by`:

- `"intake"` — mail created this month itself
- `null` — an operator created it (every batch from before this change)

On the months list, render a small neutral badge on rows with
`created_by === "intake"`: **"From email"** (PT: "Por e-mail"), next to the
month name, styled like the existing Statement badge but muted. No badge for
`null`. The batch page's payload carries the same value at
`summary.created_by` if you want the badge on the month header too.

Do not filter or sort by it; it is a provenance marker, not a state.

## 2. Intake page: the refusals strip gets one honest line

`GET /api/inbound/log` now carries, beside the existing `n_refused`
(unchanged meaning: everything turned away in the last 7 days):

- `n_refused_ours` — real submissions we accepted the envelope for and then
  turned away (day budget, disk floor, storage failure). This is the number
  that means "someone's receipt bounced".
- `n_probes` — spam relay probes (mail never addressed to us). Permanent
  background noise, not a delivery problem.
- each `refusals[]` row gains `probe` (boolean) and `kind_label` (ready
  prose: "Relay probe, not our mail" / "A real submission, turned away" /
  "Refused at the envelope").

Change the strip's headline from the single count to the split, for example:
**"2 turned away · 53 relay probes"** — driving the alarm color (if any) from
`n_refused_ours` only, never from `n_probes`. In the expanded row list,
render `kind_label` as the row's kind text and visually mute rows with
`probe: true`. If the two new counters are absent (older backend), fall back
to the current single-number render.

## 3. Nothing else to do

The intake log rows for auto-created months already read correctly with no
SPA change: their `status_label` says "Filed into July 2026" (the SPA renders
`status_label` verbatim since the 2026-08-25 prompt). Acks to senders are
backend-only.
