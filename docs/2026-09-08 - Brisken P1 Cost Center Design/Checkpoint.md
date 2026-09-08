# Checkpoint: Brisken P1 Cost Center Design

**Date:** 2026-09-08
**Status:** Item 47 design ANSWERED and recorded; nothing built (the build is a separate order)

---

## Summary

A design-only round on backlog item 47: Dirk wants expenses attributed to
projects and purposes. Four decisions were put to the owner with
recommendations and all four came back; the answered design, its
API-contract implications and a drafted Lovable half now live inside item 47
itself. One answer went against the recommendation, and that is what makes
the empty-registry case load-bearing.

---

## What Was Done This Session

### Grounding (read-only, no backend touched)

1. Read item 47, the same-day drop/create-UI checkpoint, and
   `docs/api-contract.md`, then the code the design has to sit on:
   the settings registries (`cards` / `merchants` / `entities` and their
   edge normalizers), the review-state precedence chain in `service.py`,
   the `books_as` line-item fan-out, `build_expense_report_pdf`'s
   `sections` parameter, and the `learning/store.py` schema.
2. Enumerated all 57 API routes. Nothing aggregates across batches today,
   which is the finding that decided D4: a cross-month view is genuinely
   new surface, not a re-skin of an existing one.

### The decision round (item 47)

1. Four questions put with recommendations. Three taken as recommended;
   D1 answered differently ("Dirk creates and defines the cost centers
   manually" rather than the recommended grow-while-reviewing hybrid).
2. Design recorded INSIDE item 47 per the brief: no separate design doc.
   Includes the parallel-field contract table, the new
   `GET /api/cost-centers/totals` route, and a six-part Lovable draft.
3. One row added to `p1-expense-reconciliation.md`'s element table.

---

## Key Decisions Made

### The cost-center list is owner-authored only (D1, against recommendation)

- **Choice:** `settings["cost_centers"]`, whole-map replace, edited only in
  Settings. The tool never invents a cost center and never learns a new
  NAME; learning only re-uses names Dirk defined.
- **Rationale:** owner's call. The consequence it creates is the thing to
  build first: an empty registry must resolve nothing AND flag nothing, or
  the day the field ships every row in every month reads
  `needs_cost_center`. That is the merchant registry's own contract, and
  item 26 (open since 2026-08-23) is standing evidence that an owner-side
  data-entry prerequisite can sit for weeks.

### Person does not resolve the cost center (D2)

- **Choice:** override > trip > learned merchant > card `default_cost_center`
  > unresolved. Person only ranks the picker; category never participates.
- **Rationale:** person is precisely the signal that cannot separate two of
  Dirk's own four examples, since Nicolas is on both sides of "Brazil" and
  "Lidar". A person-first chain would fill one in wrong and confidently,
  which is the `pooled` rows reading "Arriving" all over again. Learned
  sitting above the static default keeps the 2026-08-07 merchant reversal
  consistent.

### The roll-up is not a project total (scope boundary, agent-raised)

- **Choice:** both surfaces carry a stated limit: card and receipt spend
  only, never contractor invoices or salaries.
- **Rationale:** "what did Lidar cost" answered from this tool is partial by
  construction, and a partial number presented as a total is worse than no
  number (B4). Raised before the surface question because it constrains what
  the surface may claim.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| status/p1-improvement-backlog.md | edit | item 47 block replaced with the answered design + contract + Lovable draft (#726) |
| status/p1-expense-reconciliation.md | edit | one element row for cost centers (#726) |

---

## Current Status

Item 47 is designed and unbuilt. PR #726 merged green (six checks) as
`3531bcc5`; the design is verified present on `main`. No backend code, no
deploy, no writes to the live app this session, per the session's hard
limits.

brisken platform: unknown plan, ~?/? ops/mo, last assessed unknown (no
`platform` section in `infrastructure.yaml` for the fastapi orchestrator).

Three sibling sessions ran concurrently on this repo; `main` moved five
commits mid-session (items 48 and 26/40 landed in the same two status
files). The rebase was clean and the sibling item-48 block was proven
byte-identical afterwards.

---

## Next Steps

1. **Item 47 build, when ordered.** Order: registry + resolution chain +
   review state (inert while the registry is empty) → month-report
   `sections` partition → learned merchant→cost-center table →
   `GET /api/cost-centers/totals`. Cross-month last: it is the only piece
   that needs data the earlier pieces produce.
2. **Dirk defines the initial cost-center list.** Owner-side prerequisite
   created by D1. Nothing resolves until it exists, and by design nothing
   complains either.
3. Existing queue is unchanged: the drop DELTA prompt is still with the
   owner (bundle re-audit plus a browser drive for the chrome halves once
   pasted), then items 27 / 23-strings / 24.
4. A `platform` feasibility assessment for brisken's fastapi orchestrator
   is still absent from `infrastructure.yaml`.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` — item 47 is
  now self-contained: decisions, contract, Lovable draft, build order
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  — rules 1 through 5; the design leans on 1 (parallel fields) and 5
  (a hand-mapped enum ships with a label)

### Open Questions

- No real shared-cost example was on the table when D3 (v1 refuses splits)
  was decided. If one turns up, the v2 shape is per line item via the
  `books_as` fan-out, not operator percentages.
- Whether `kind` (project / function / trip) should ever influence
  resolution. v1 says no, display-only.

### Working Notes

- `build_expense_report_pdf` already takes `sections`: contiguous listing
  slices with their own caption, per-currency sums and continuous numbering,
  built for the per-person trip report (item 38). Partitioning by cost
  center is that same call with a different key, which is why D4 step 1 is
  nearly free.
- `normalize_cards_setting` has a plain string-field loop
  (`label`, `label_pt`, `entity`, `person`, `zoho_account`); adding
  `default_cost_center` is one entry in it.
- `merchant_entity` (`vendor_norm` → `legal_entity_id`, `decision_count`)
  is the structural twin for the learned merchant→cost-center table.
- The Lovable half was deliberately NOT written into
  `docs/lovable-*.md`: PROMPT-STATUS audits that folder as pasteable, and
  every field it names is unbuilt. Promote it in the build round.
- Em-dash baseline for the two status files was measured, not assumed:
  134 hits on `origin/main`, 152 after. These are internal status files,
  outside the client-facing ban, and the additions match the file's own
  house style.

### Reference Materials

- PR #726 (merged `3531bcc5`)
- `docs/2026-09-08 - Brisken P1 Drop Cap And Create-UI Retirement/Checkpoint.md`
  — where items 47 and 48 were seeded

---

## How to Continue

Item 47 needs an explicit build order before any code. When it comes, read
item 47's block end to end first: it carries the build order, and the
inert-while-empty rule is the first thing to implement, not a detail to add
later.

---

## Strategic Feedback

### What Worked Well This Session

- Grounding the four questions in code before asking them changed two of the
  answers' framing. Enumerating all 57 routes turned "which surface" from a
  preference question into a cost question, and reading
  `build_expense_report_pdf` is what made the two-step D4 recommendation
  credible rather than a guess.
- Raising the card-spend-is-not-project-cost boundary before the surface
  question rather than as a footnote after it. It constrains what the view
  may claim, so it had to come first.

### Suggestions

- The heredoc failure recurred again today (fifth register row on this exact
  pattern, second one today). The documented fix has never held across
  sessions; the size gate is what actually holds, and it holds cheaply.
  Worth accepting that the gate IS the fix and stopping the "documented"
  rows, or lowering the reflex by defaulting to the Write tool for any
  multi-line payload without first estimating its length.

### System Health

- Three sibling sessions on one repo, `main` moving five commits mid-session,
  two of them in the same two files this session edited: the worktree
  discipline plus a pre-push rebase absorbed all of it with zero conflicts
  and zero lost sibling work. That is the branch-isolation rule earning its
  keep rather than being ceremony.
- Autonomy: 1 human intervention (the four-question decision round, which
  was the session's assigned deliverable rather than a deferral). Fully
  autonomous otherwise.
