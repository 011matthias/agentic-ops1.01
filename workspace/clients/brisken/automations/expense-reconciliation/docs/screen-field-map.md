# A wrong value is on screen. Which function produced it?

For a stand-in who has the repository, has a screenshot from Criss, and has
never opened `web/service.py`. That file is **15,408 lines**, and the
function that built the cell in question is somewhere in it.

This is a map, not a refactor. Backlog item 120 says explicitly: no
refactor under the licence. Nothing here proposes moving code.

**Verified against commit `603b4d1d` on 2026-09-20.**

## Read this before using any line number below

Line numbers in this file are stale the week after they are written.
`service.py` grew from 11,729 to 15,408 lines between 2026-09-17 and
2026-09-20, and every offset moved with it. Backlog item 120's own
evidence block cites `build_view` at line 952; it is at 3219.

**So search by name, never by number.** The numbers below are dated
landmarks for orientation only:

```bash
grep -n "^def build_view" src/expense_recon/web/service.py
```

Every function named here is top-level in `src/expense_recon/web/service.py`
unless another file is given.

## Step 1: which screen is it, and which builder owns it

Almost every value Criss sees comes from one of two builders, and which one
depends on the run's stored mode plus whether a statement has been attached.
The dispatch is in `web/app.py` at `GET /api/runs/{run_id}`:

```
run_mode(run) == MODE_EXPENSE_GENERATION and not has_statement(run)
    -> build_expense_view      the receipt spine (an expense batch)
otherwise
    -> build_view              the transaction spine (a month with a statement)
```

This dispatch is the single most common reason a reader looks in the wrong
place. A batch **with** a statement attached graduates to `build_view`, so
the same screen name can be served by either function depending on the
month's state. Check the run first.

| The screen | Builder | Landmark (2026-09-20) |
|---|---|---|
| A month with a statement loaded | `build_view` | :3219, 1162 lines |
| An expense batch, no statement yet | `build_expense_view` | :7208, 834 lines |
| The month's report PDF | `build_expense_report` | :8298, 678 lines |
| Card review (which card paid) | `build_card_review` | :6707, 179 lines |
| What the tool has learned | `build_memory_view` | :5227, 125 lines |
| Cost-centre totals | `build_cost_center_totals` | :8978, 140 lines |
| Coverage panel | `month_coverage` | :11234, 132 lines |

## Step 2: which field, inside that builder

These are the top-level keys each builder returns, read off the code. Find
the key whose name matches the part of the screen that is wrong.

**`build_view`** returns:
`rows`, `summary`, `coverage`, `card_evidence`, `receipt_chase`,
`duplicate_groups`, `duplicate_charges`, `duplicate_receipts`,
`unmatched_transactions`, `unmatched_receipts`, `assignable_receipts`,
`copies_set_aside`, `statements`, `parse_errors`, `parse_issues`,
`category_options`, `vendor`, `currency`, `total`, `amount_diff`,
`date_diff_days`, `published`, `published_at`, `published_by`,
`published_override`, `held_by`, `last_rematch`, `rematch_pending`,
`folder_ingest`, `llm_enabled`, `has_coa`, `adjudication_available`,
`writeback_available`, `run_id`, `label`, `created_at`, `updated_at`.

**`build_expense_view`** returns:
`expenses`, `summary`, `coverage`, `card_review`, `set_aside`, `trip`,
`statements`, `duplicate_groups`, `expense_ingest`, `period_suggestion`,
`batch_type`, `mode`, `has_statement`, `legal_entity_id`,
`account_options`, `entity_options`, `cost_center_options`,
`category_options`, `parse_errors`, `parse_issues`, `last_rematch`,
`rematch_pending`, `llm_enabled`, `has_coa`, `run_id`, `label`,
`created_at`, `updated_at`.

### The two that carry most of the grid

**Search inside one function, not across the file.** A plain `grep` for
these anchors returns five hits, because the summary shape is built in
several places and only one of them is `build_view`'s. Scope the search to
the function first; this awk prints only hits between `def build_view(` and
the next top-level `def`:

```bash
# Run from the module root. Literal matching (index), not regex, so a
# pattern full of quotes and brackets needs no escaping.
scoped() {  # usage: scoped <function> <pattern>
  awk -v fn="def $1(" -v pat="$2" \
    'index($0,fn)==1 {f=1} f && /^def / && index($0,fn)!=1 {f=0} \
     f && index($0,pat) {print NR": "$0}' \
    src/expense_recon/web/service.py
}
```

One caution about reading its output, because it bit the writing of this
page. When the helper finds nothing it prints nothing, and so does a
BROKEN helper. Before trusting an empty result, run it once against
something you know is there (`scoped build_view '"transaction_id": tx_id'`
should print line 3717); if that prints, the empty answer is real.

**A wrong value in one grid ROW** (a date, a vendor, an amount, the match
status, which card it thinks paid): the row dict is assembled in one
`rows.append({...})` inside `build_view`. Its keys are `transaction_id`,
`date`, `vendor`, `amount`, `currency`, `account_id`, `legal_entity_id`,
`coverage_key`, `initial_bucket`, `effective_bucket`, `status`,
`chosen_document_id`, `candidates`, `has_learned`, and `cards_differ`
(present only when the held receipt's card and the charge's card
disagree).

```bash
scoped build_view '"transaction_id": tx_id'    # one hit: :3717 on 2026-09-20
```

**A wrong COUNT in the header** (`n_reconciled`, `n_review`, `match_rate`,
`n_unmatched_tx`, `n_settled_outside`, `n_copies_set_aside`): one
`summary = {...}` literal near the end of `build_view`.

```bash
scoped build_view '"n_transactions": n_tx'     # one hit: :4129 on 2026-09-20
```

Two counts are routinely reported as bugs and are not. `match_rate` is
charge-based and under-reads a month with many receiptless charges;
`receipt_match_rate` is the receipt-based figure the SPA leads with. And
`n_receipts` deliberately does not move when a receipt is settled outside
the card: it still answers "how many receipts are in the month", and
`n_settled_outside` is the separate question.

## Step 3: which layer is actually wrong

A value on screen has passed through several hands, and the builder is only
the last one. Deciding which layer is wrong, before reading any of them,
saves the most time:

| If the value is | The layer that owns it | Where |
|---|---|---|
| Wrong on the ORIGINAL document too | extraction, the LLM read the receipt wrong | `llm/`, and the extraction cache |
| Right on the document, wrong in the grid | ingest, the parser or column map | `ingest/` |
| Right per row, wrong about WHICH receipt pairs with which charge | matching | `matching/deterministic.py`, then `matching/judgment.py` |
| Right in the pairing, wrong category or account | categorization and the merchant registry | `categorize.py`, the registry, the company rules |
| Right everywhere but stale on screen | the view builder, or the SPA | this file's Step 1, then the SPA repo |
| Right in the API reply, wrong on screen | not this repository | `011matthias/brisken-expense-review` |

**That last row is worth checking first.** The screen is a separate Lovable
app. Fetch the API reply and read the field yourself before opening
`service.py` at all; if the JSON is right, nothing in this repository is
wrong. `docs/operating.md` has the authenticated `curl`.

## Step 4: confirm you are in the right function before editing

`service.py` has 286 functions and several near-duplicate names
(`build_view` / `build_expense_view` / `build_card_review`). Before
changing anything, prove the function you found is the one that produced
the value: change it to something obviously wrong, refetch the API, and
watch the wrong value appear. Then undo.

A function that does not change the value when broken is not the function
that produced it. This costs one minute and is the difference between
fixing the field and fixing a field that looks like it.

## What this map does not cover

Only the read path, and only the two main builders in depth. The write
path (what happens when Criss decides something) is not mapped here:
`apply_decisions`, `commit_to_memory`, `rematch_month` and
`move_expense_to_month` are the entry points, and `docs/api-contract.md`
documents the endpoints that reach them.

Related: `docs/api-contract.md` (every endpoint), `docs/operating.md` (how
to read live state), `BLUEPRINT.md` (why the pipeline is shaped this way).
