# Lovable prompt 3 of 3: the Email intake page, two deltas

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Prompt 3 of 3. It changes ONE cell renderer on the Email intake page and adds
one small strip. Independent of the other two.

**This supersedes `lovable-month-pool-prompt.md` sections 0 and 12. Do not
paste that file again** — sections 1 through 11 of it are already live in
your app, and re-running them would fight the change below.

---

## What the page already does (measured 2026-08-24)

`/inbound` works. It renders:

- the header "Email intake" and "Every email the tool received and what came
  of it."
- badges "Waiting: 6" and "Held: 1"
- the button "Retry held and add waiting mail"
- a table: Received | From | Subject | Files | Status | Month | Actions
- a per-row Actions menu (icon-only "...") offering **View body**, **Add to
  month as PDF**, **Dismiss**, correctly varied by row state
- Month cells reading "August 2026 (waiting)", "July 2026 (waiting)",
  "March 2026"
- Status cells reading "Waiting for its month", "Text-only email, needs
  manual handling", "Dismissed", plus a "Held" badge

All of that stays. Two deltas follow.

## Delta 1: render the Status cell from the backend, not from a local map

### Why

`entries[].status` is an enum that keeps growing. It gained `pooled`,
`routing` and `claiming` on 2026-08-24. Your local map had no case for them
and fell through to the in-flight label, so six of Dirk's *resting* receipts
read **"Arriving"** with a blank Month and would have kept saying so
indefinitely. Nothing crashed; the page was confidently wrong, which is worse
than an error, because "Arriving" is a claim that resolves itself.

That specific case is fixed in your app now: `pooled` maps to "Waiting for
its month". The problem is the shape, not that one value. The next status the
backend adds will mislabel exactly the same way.

### The change

Every row now carries two parallel fields the backend composes:

- `status_kind` - how to TREAT the row: `resting` | `held` | `working` |
  `done` | `unknown`
- `status_label` - what to SAY, already written out: "Waiting for August
  2026", "Needs one click to read", "Added", "Dismissed", "July 2026 is
  already reconciled"

**Render `status_label` as the Status cell text.** Drive colour and treatment
from `status_kind`:

| `status_kind` | Treatment |
| --- | --- |
| `resting` | neutral / informational (blue or grey). Fine, waiting on a schedule |
| `held` | amber or red, exactly as the Held treatment is today. Needs a human |
| `working` | muted, with a spinner. Resolves in seconds; never actionable |
| `done` | quiet / success. Nothing owed |
| `unknown` | neutral, and show `status_label` verbatim. The backend is newer than this build |

Then **delete the local status-to-label map.** If you keep any mapping at
all (to localize into PT, which is legitimate), key it on `status_kind` and
fall through to `status_label` for anything you have no string for. **Never
map an unrecognised `status` onto a label you already have** - that is the
entire bug.

### What visibly changes

- "Waiting for its month" becomes "Waiting for August 2026". The month is
  named in the Status cell instead of only in the Month column.
- "Text-only email, needs manual handling" becomes "Needs one click to
  read", which says what to do rather than what is wrong.
- A pooled row whose month is already CLOSED comes back as
  `status_kind: "held"` with "July 2026 is already reconciled". A local map
  cannot know that; it is a task, not a wait, and today it renders as a
  healthy wait.

### What must NOT change

- The Month column keeps rendering `pool_month` + `pool_month_state` exactly
  as it does now ("August 2026 (waiting)"). It is correct. The Status cell
  naming the month too is deliberate redundancy, not a duplicate to remove.
- The Held and Waiting badges keep reading `n_held` and `n_pooled`. Do not
  derive them from `status_kind`.
- The Actions menu, its items, and which rows get which item: unchanged.

## Delta 2: "did anything bounce?"

The payload gains two top-level fields beside `n_held` / `n_pooled`:

- `n_refused` - mail TURNED AWAY in the last 7 days
- `refusals` - the newest rows, each `{at, stage, reason, from, to, peer}`

Until now a refused message left no trace anywhere: no archive, no log row,
no counter. When somebody said "I sent that receipt", there was no way to
tell whether it had been turned away. `stage` is `rcpt` (the recipient was
refused, usually a stranger probing the listener) or `data` (we accepted the
envelope and then a guard stopped the message: disk floor, in-flight ceiling,
daily submission limit, storage failure).

- `n_refused === 0`: show nothing at all. That is the normal state and it is
  the answer to the question.
- Otherwise: a quiet count near the Held / Waiting badges, expanding to a
  small table of the rows: time, from, to, reason.
- Give `stage: "data"` rows more weight than `rcpt` ones. A refused RCPT is
  usually spam. A DATA refusal is a real submission we accepted and then
  turned away, which is exactly the mail somebody will later swear they sent.

**These are NOT entries.** They have no archive, so there is nothing to
dismiss, replay or open. Do not put them in the mail table and do not give
them an Actions menu.

## Do not

- Do not re-apply `lovable-month-pool-prompt.md`. Sections 1-11 are live.
- Do not touch the Actions menu, the Month column, the badges' data sources,
  or the "Retry held and add waiting mail" button.
- Do not touch any other screen.
- No em-dashes in UI copy.

## Verify after publish

The six waiting rows read "Waiting for August 2026" / "Waiting for July
2026" in the Status cell, in a neutral tone, with the Month column unchanged
beside them. The Held badge still says 0. No refusals strip appears while
`n_refused` is 0.
