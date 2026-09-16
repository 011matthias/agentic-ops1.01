# Lovable prompt: duplicates are decided, and decided groups leave the to-do area (item 74)

Backlog item 74 (notes #37, #41, #45, #46). Owner rulings: two charges to one
vendor are two charges, so charge-side duplicates are gone; the tool decides
every receipt group and never asks; resolved items leave the to-do area
(Criss, note #46: "Ações resolvidas deveriam ser retiradas da área que constam
para ser removidas").

**Written against item 79's page structure as published** (month views live
2026-09-16, SPA `main` at `9df1a1e`): the Matching view's `DuplicatesPanel`
and view 1's fold of copies. Everything item 79 built stands. Backend shipped
first (item 74 PR, Fly deploy); every field below is live.

Paste everything between the two rules into the `brisken-expense-review`
Lovable project.

---

Paste into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend as a JSON API
at `api.expenses.brisken.com`. **Do NOT add Supabase or any database.** Auth
stays the existing `Authorization: Bearer <token>`. No backend change: every
field below already ships. Query keys stay `["expense-batch", id]` and
`["run", id]`.

## Why

The duplicates panel at the bottom of a month's Matching view asks the
reviewer "Real duplicate / Not a duplicate" about groups the tool has already
decided, and it lists two real charges to one vendor as "Duplicate charges".
The backend now decides every receipt group itself, says on what evidence, and
no longer raises charge groups at all. The panel becomes a collapsed record of
the copies the tool set aside, with an undo.

## 1. The fields (`GET /api/runs/{id}` and `GET /api/expense-batches/{id}`)

Every `duplicate_groups[]` element:

```json
{
  "group_id": "da109dc56459efa7",
  "kind": "receipt",
  "members": ["0008__Invoice-HMVWDWIL-0029.pdf", "0009__Receipt-2247-1655-6392.pdf"],
  "resolution": null,
  "state": "decided",
  "decided_by": "tool",
  "verdict": "copy",
  "basis": "printed_reference"
}
```

- `state`: `"open"` or `"decided"`, always present.
- `decided_by`: `"tool"` or `"reviewer"`; `verdict`: `"copy"` or
  `"distinct"`. Both present when `state` is `"decided"`, both ABSENT when it
  is `"open"`. Never null.
- `basis`: the evidence the TOOL decided on, one of `"hash"`, `"reference"`,
  `"printed_reference"`, `"vendor_date"` (these say copy) or
  `"distinct_reference"`, `"receipt_card"`, `"statement"` (these say two
  purchases). A reviewer's ruling does not change it. Absent only on an open
  group.
- `resolution` keeps its meaning. A reviewer's ruling outranks the tool:
  `"confirmed"` reads `verdict: "copy"`, `"ignore"` reads `verdict:
  "distinct"`, both with `decided_by: "reviewer"`.
- `kind` is always `"receipt"` now. `duplicate_charges` is always `[]`.
- `summary.n_duplicate_groups_open` (integer, both payloads): groups nobody has
  decided. Expected 0.

## 2. The panel (`DuplicatesPanel` in `RunWorkbench.tsx`, Matching view)

Today the panel shows the title "Possible duplicates" and the sentence
"Advisory only. Resolving a group records your call; it never moves a row
between buckets or changes the reconciliation total." (false since a ruling
re-matches the month), treats every receipt group as decided
(`isDecided = !!g.resolution || g.kind === "receipt"`), folds those behind
"{n} decided", and gives every card both "Real duplicate" and "Not a
duplicate". Change it as follows.

- **Keep the index pairing exactly as it is** (`chargeIdx` / `receiptIdx` and
  the fallback to member ids). Do NOT filter or reorder `duplicate_groups` or
  `duplicate_receipts`: the pairing is by index within a kind, and a filtered
  array puts one group's receipts under another. Partition the paired entries
  (`detailed`) at render time into three lists:
  - OPEN: `state === "open"`. When `state` is absent (an older payload), keep
    today's rule: open unless `resolution` is set or `kind === "receipt"`.
  - COPIES: `state === "decided"` and `verdict === "copy"`.
  - KEPT APART: `state === "decided"` and `verdict === "distinct"`.
- **Nothing to show:** when all three lists are empty, render nothing (as
  today when there are no groups).
- **OPEN** groups render exactly as today: the title `wb.dups.title`, the
  member table, both buttons "Real duplicate" / "Not a duplicate", same
  handlers. None are expected; this keeps the page honest if one ever appears.
  Delete the `wb.dups.body` sentence everywhere.
- **No OPEN group:** no title and no intro sentence. The panel is only the
  record below.
- **The record.** Replace the "{n} decided" fold line (`wb.decided.fold.one` /
  `wb.decided.fold.many`) with `wb.dups.setAside.title`, `{n}` = COPIES count,
  and when KEPT APART is not empty append ` · ` and `wb.dups.keptApart.count`
  with its count. Keep the panel's own Show/Hide toggle, its styling and its
  collapsed default. When COPIES is empty but KEPT APART is not, the line
  reads just the `wb.dups.keptApart.count` part.
- **Inside the record**, COPIES first, then KEPT APART, each in array order.
  One card per group, muted as decided cards are today, member table as today
  (date, vendor, reference, total). In the card header, replace the kind label
  and the resolution pill with the reason, one line of muted text:
  - `decided_by === "reviewer"`: `wb.dups.byReviewer.copy` (verdict copy) or
    `wb.dups.byReviewer.distinct` (verdict distinct);
  - otherwise `wb.dups.basis.{basis}`, falling back to `wb.dups.basis.unknown`
    for any value not in section 4. Never print the raw key.
- **ONE button per decided card**, small, `variant="outline"`, right-aligned
  where the two buttons sit today, same `onResolve` and `busy`:
  - COPIES: `wb.dups.notCopy`, calls `onResolve(group_id, "ignore")`;
  - KEPT APART: `wb.dups.sameDocument`, calls `onResolve(group_id, "confirmed")`.
  Never send a null or empty resolution; the backend accepts only
  `"confirmed"` and `"ignore"`.
- Keep the `kind === "charge"` code path and the `DuplicateCharge` type
  defensively; the backend sends no charge group and `duplicate_charges` is
  `[]`, so "Duplicate charges" never renders.

**View 1, receipts without a charge.** The fold of copies
(`receiptCopiesAll`, `wb.decided.foldCopies.*`) stays exactly as it is. Only
the button on a copy row (`r.duplicate?.group_id`, today `wb.dups.notDup`)
changes its label to `wb.dups.notCopy`; same call with `resolution: "ignore"`.
A group the tool calls two purchases carries no row marker, so its receipts
are ordinary open receipts there.

## 3. The Expenses view (`ExpensesReviewGrid.tsx`)

The duplicate-copies bar (`n_duplicate_copies`), the row badges and "Delete
the extra" stay as they are. Only copies carry markers now, so the bar counts
copies the tool or a reviewer set aside. Change only string VALUES in section
4: the bar (`expx.dup.count_one`, `expx.dup.count`), the row link
(`expx.dup.notDuplicate`) and its toast (`expx.dup.toast.ignored`). No code
change here.

## 4. i18n (EN and PT in the same edit, `src/lib/i18n.tsx`)

`t()` has no plural logic: pick `.one` at the call site when the count is 1.

| Key | EN | PT |
|---|---|---|
| `wb.dups.setAside.title` | Copies set aside ({n}) | Cópias separadas ({n}) |
| `wb.dups.keptApart.count` | {n} kept apart | {n} mantidos separados |
| `wb.dups.notCopy` | Not a copy | Não é cópia |
| `wb.dups.sameDocument` | Same document | Mesmo documento |
| `wb.dups.byReviewer.copy` | Set aside by a reviewer | Separada por um revisor |
| `wb.dups.byReviewer.distinct` | Kept apart by a reviewer | Mantidos separados por um revisor |
| `wb.dups.basis.hash` | Identical file | Arquivo idêntico |
| `wb.dups.basis.reference` | Same document number | Mesmo número de documento |
| `wb.dups.basis.printed_reference` | One prints the other's number | Um traz o número do outro |
| `wb.dups.basis.vendor_date` | Same vendor, date and amount | Mesmo fornecedor, data e valor |
| `wb.dups.basis.distinct_reference` | Different document numbers | Números de documento diferentes |
| `wb.dups.basis.receipt_card` | Paid with different cards | Pagos com cartões diferentes |
| `wb.dups.basis.statement` | The statement shows two charges | O extrato mostra dois lançamentos |
| `wb.dups.basis.unknown` | Decided by the tool | Decidido pela ferramenta |
| `expx.dup.count_one` | 1 copy set aside | 1 cópia separada |
| `expx.dup.count` | {n} copies set aside | {n} cópias separadas |
| `expx.dup.notDuplicate` | Not a copy | Não é cópia |
| `expx.dup.toast.ignored` | Kept as a separate purchase | Mantida como compra separada |

`wb.dups.body` is no longer rendered; leave the key or delete it, either is
fine.

## 5. Do not change

The resolve route, its payload keys and its reply handling; the index pairing
of `duplicate_groups` with `duplicate_receipts`; row markers (`duplicate`) and
`n_duplicate_copies`; item 79's cards, views, folds and switch; `RowView`,
`RowStatusBadge` and the Status cell; the Expenses view beyond the four string
values in section 3. No em-dashes in any new string.

## 6. Render defensively

`state`, `decided_by`, `verdict`, `basis` may be absent on an older payload:
an absent `state` falls back to today's rule (section 2, OPEN), and such a
group renders as today. An unknown
`basis` renders `wb.dups.basis.unknown`. `n_duplicate_groups_open` absent
means 0.

---

## Verify after publish

Re-read `GET /api/runs/{id}` for July `50622baec444` and August
`074a7b8905d7` minutes before driving and substitute live numbers.

**Bundle** (`tools/lovable-bundle-audit.py`, every chunk crawled; controls
must hit before any absence is believed): `n_duplicate_groups_open` and
`decided_by` in `chunk-runs._runId-*`; `wb.dups.setAside.title`,
`wb.dups.basis.printed_reference` and `wb.dups.notCopy` in the i18n chunk and
in `chunk-runs._runId-*`. Decisive signatures: `n_duplicate_groups_open`,
`wb.dups.setAside.title`.

**Browser drive**, 1440x900, named session, read-only (open the fold, hover;
never click Not a copy or Same document on Criss's months), EN then PT:

1. July `/runs/50622baec444`, Matching view, bottom: no "Possible duplicates"
   heading, no "Advisory only" sentence, no "Duplicate charges", no "Real
   duplicate" button, no "decided" fold line. One fold line
   "Copies set aside (5)" (reads "Copies set aside (4) · 1 kept apart" once the
   Google ruling is reset). Opened: Aposto Karlsruhe 80.00 EUR and Google LLC
   71.64 USD read "Set aside by a reviewer"; Lovable Labs 200.00 USD, the two
   Hostinger bodies and the Redis invoice read "Same document number"; each
   card has exactly one button, "Not a copy".
2. August `/runs/074a7b8905d7`: "Copies set aside (11)"; the two Lovable 15.00
   and 25.00 pairs read "One prints the other's number"; the OpenAI 80.12 and
   Obsidian 96.00 bodies read "Same vendor, date and amount"; the other seven
   "Same document number". No OPENAI 86.06 charge group anywhere.
3. View 1 on both months: the fold of copies still reads "{n} copies set
   aside" and its undo reads "Not a copy".
4. PT pass on August: "Cópias separadas (11)", "Um traz o número do outro",
   "Não é cópia".
5. Network during the drive: no POST other than `/api/login`.
