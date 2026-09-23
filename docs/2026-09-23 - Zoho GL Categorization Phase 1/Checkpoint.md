# Checkpoint: Zoho GL Categorization Phase 1

**Date:** 2026-09-23
**Status:** Foundation shipped (PRs #1232, #1234 merged). The engine still classifies into the eight buckets; nothing calls the new taxonomy yet.

---

## Summary

Shipped the two pieces of the direct-to-Zoho-GL change that are safe to land
before anything behavioural: a snapshot read that tolerates a missing category,
and Dirk's curated 199-leaf chart compiled into a committed asset the runtime
can actually reach. Both regress-checked. Tier 2 was deferred on evidence, and
one of the brief's four named hazards turned out not to exist.

---

## What Was Done This Session

### Shipped
1. **PR #1232** — `categorization_from_dict` read `d["category"]` and
   `d["zoho_account"]` with bare subscripts; a snapshot written by the new
   engine would `KeyError` and the month would not open. Both now `.get`.
2. **PR #1234** — `tools/compile-brisken-gl-taxonomy.py` plus the generated
   `zoho/_curated_leaves_data.py` (412 codes, 199 postable across three
   entities) and its reader `zoho/curated_leaves.py`.
3. Architecture doc `docs/zoho-gl-categorization-architecture.md`.
4. Reconciled item 170's closure banner so the next session is not stopped by a
   flat "anything about expense CATEGORY definition" on the ruled-out list.

### Established by fan-out
5. Understand workflow, 7 readers + a completeness critic (8/8, 0 errors).
6. Design judge panel, 3 approaches + 3 lens judges + synthesis (7/7, 0 errors).

---

## Key Decisions Made

### The stop-work applies to the buckets, not to the chart
- **Choice:** Proceed. The owner's 2026-09-23 direction ("no working on expense
  category definition anymore") closed work on the eight-bucket VOCABULARY.
- **Rationale:** Dirk hand-marked his own chart that afternoon and revised it at
  18:56, six minutes before the closure merged, and notes #83-85 ask for the
  replacement. Two sessions ran in parallel and neither saw the other.

### Tier 1 lives in the per-entity learning store
- **Choice:** `learning/store.merchant_category`, not the settings registry.
- **Rationale:** Owner call. It is already keyed `(legal_entity_id, vendor_norm)`
  and already carries `zoho_account`; the settings registry is entity-blind.

### Tier 2 deferred, and refusing rather than absent
- **Choice:** Build Tiers 1 and 3; travel and dining that no vendor rule
  resolves raises `account_unresolved`.
- **Rationale:** Owner call, on three findings. It reverses the written decision
  at `cost_centers.py:44`. The trip feature has never carried production data
  (live `GET /api/trips` empty, all 7 batches `company-month`, cost-centre
  registry empty, each proven against a control). And a purpose selects a FAMILY
  of three leaves (Transportation / Accommodation / Food), not one leaf.

### The asset is generated Python, and its source is the sheet
- **Choice:** `src/expense_recon/zoho/_curated_leaves_data.py`, compiled from
  Dirk's workbook, cross-checked against the chart pull but never sourced from it.
- **Rationale:** The Dockerfile copies only `pyproject.toml`, `uv.lock` and
  `src`, so a JSON asset would be the first non-.py file under `src/` and absent
  on Fly. And the pull is silently truncated for Cloud Services.

---

## What Did NOT Work (and why)

- **Keying the taxonomy on the account NAME:** Corporate Services calls its
  general food leaf `CorpServ | Travel Expense | Food` where the other two orgs
  say `Travel Expense | Food`, on the same code `E100010-31`. A name-keyed
  mapping silently skips that entity.
- **Inferring the account hierarchy from the code prefix:** `Business Travel
  Expenses - CRM` is `E600010-20` while its children are `E600010-10-20-*`,
  nested under the Conferences parent, identically in all three sheets. The
  branch had to be built from parent NAMES instead.
- **Sourcing the asset from `zoho-books-coa.json`:** truncated for Cloud
  Services at a 200-row page boundary; 19 accounts Dirk marked Y are absent,
  including `COGS - DEV Infrastructure`, which is the account Anthropic posts to
  under Cloud Services and the design's own flagship Tier 1 example.
- **Asserting every postable leaf has a parent:** eight do not (`R&D`, `Bank
  Fees and Charges`, `Interest Expense`, `Tax Paid`, two OpeEx headers and two
  more). Dirk's convention is that outside COGS a parent is postable, so a root
  account is its own category.
- **Running `regress_check.py` from the repo root:** the test path is relative
  to the module, so the baseline read RED with "file or directory not found".
  Re-run from the module root with an absolute script path.
- **A heredoc carrying a Python triple-quoted block:** blocked by
  `heredoc-size-gate`, which is exactly what the previous session's checkpoint
  warned about. The Write tool is the path.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../src/expense_recon/web/serialize.py` | Edit | Tolerant read of `category` / `zoho_account` |
| `.../tests/test_serialize_retired_category.py` | Create | 6 caller-level tests, bite-proven |
| `tools/compile-brisken-gl-taxonomy.py` | Create | Workbook to committed asset, refuses on contradiction |
| `.../src/expense_recon/zoho/_curated_leaves_data.py` | Create | Generated: 412 codes, 199 postable |
| `.../src/expense_recon/zoho/curated_leaves.py` | Create | Reader; code-keyed, numeric-id-only |
| `.../tests/test_curated_leaves.py` | Create | 19 tests, bite-proven |
| `.../docs/zoho-gl-categorization-architecture.md` | Create | The design and the findings behind it |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edit | Item 170 banner reconciled |
| `tools/INDEX.md` | Edit | Compiler row |

---

## Current Status

`origin/main` at `94586b73`. Module suite **3102 passed, 2 skipped**. Nothing
uncommitted; both PRs merged with all CI checks green.

Nothing is deployed. The tolerant read is a safety net for writes that do not
exist yet, so it goes live with the engine change rather than ahead of it.

brisken platform: unknown plan, ~?/? ops/mo, last assessed unknown.

---

## Next Steps

1. **Accept-and-drop on the four 400-ing write paths** (`app.py` 3397, 3865,
   5124, 5307) plus `normalize_merchants_setting`, per the `RETIRED_ENTITY_KEYS`
   precedent. The SPA sends the settings map back wholesale, so one stored
   retired value 400s the entire save including the cards and entities tabs.
2. **Serve both vocabularies**, adding a new key beside `categories` and
   `category_options` rather than repurposing them.
3. **The precedence chain** (`zoho/posting_resolution.py`), with the leaf and
   scope checks lifted from `coa_gate.classify_account` into
   `resolve_account_id` in the SAME change that deletes `category_accounts.py`.
4. **File the new findings** as backlog items: the truncated chart pull; the
   Publish-fires-registry-write with a category-only conflict check; unvalidated
   `paid_through_account_id`.
5. Two status files stale and untouched: `p2-product-decks.md` (62d),
   `p2-targeting.md` (63d).

---

## Context for Next Session

### Files to Read First
- `.../automations/expense-reconciliation/docs/zoho-gl-categorization-architecture.md`
- `.../src/expense_recon/zoho/curated_leaves.py`
- `tools/compile-brisken-gl-taxonomy.py` (its docstring carries the why)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 179, 180, 181

### Open Questions
- Do the six `SPOT-CHECK` accounts stand as marked? (Dirk's)
- Card 3645's `zoho_account` holds another card's label; the real account has to
  come from Dirk (item 172).
- Should `Categorization` carry the invariant "falsy category if and only if
  REFUSED"? The synthesis argues it replaces the 17-gate rewrite, because
  `posting_common`'s live gate already reads `not cat.category`.

### Working Notes
- The sibling session itemized notes #83/#84/#85 as items **179, 180, 181**.
  Do not re-file them. Items up to 181 are taken.
- Phase 1 **unblocks item 166**, which is explicitly gated on "the 52-row Zoho
  account to category table nobody has ruled on". This work dissolves that table
  rather than ruling on it.
- 126 of 236 test modules carry at least one of the eight literal strings, not
  the 63 first estimated.
- Compile command, with the counts that must be asserted:
  `--expected-counts 697686691=67,808232536=64,822741658=68`.
- `uv run ruff` is not on PATH in the worktree; `uvx ruff check` works.

### Reference Materials
- Source sheet: `C:\Users\neuma_p1qrsic\Desktop\Downloads\CoA BRISKEN BCS BTS CorpServ 260923.xlsx`
- Derived workbook + deriving script: `workspace/clients/brisken/context/expense-reconciliation/`
- PRs: #1232, #1234

---

## How to Continue

Read the architecture doc, then take next step 1. The order in that doc is
deliberate: every step before the engine conversion exists so the conversion
cannot break something silently.

---

## Strategic Feedback

### What Worked Well This Session
- Verifying the workbook myself rather than only through a subagent. The
  tab-to-org probe, the Y/N counts and the truncated-pull discovery all came
  from four short scripts, and the truncation would have shipped a mapping whose
  flagship example refuses at runtime. The critic separately noted no reader had
  opened the xlsx at all.
- Reading the six commits I was behind before writing code. The stop-work
  direction was in them, and starting without it would have meant building
  against a live owner directive.

### Suggestions
- The compile step asserts Dirk's counts but nothing yet asserts the asset is
  fresh relative to the sheet. `--check` compares the asset to a recompile of
  whatever workbook it is handed, so pointing it at a stale sheet passes. A
  recorded `SOURCE_SHA256` mismatch warning at load would close that.

### System Health
- `bg_watch` state is per working tree, not per session: a sibling's watch for
  "CI on PR #1226" nagged this session on every tool call for over an hour with
  an ETA it could not act on. `session_state.py` had the same shape and was
  fixed on 2026-09-17 by going per-session. Same fix applies.
- Autonomy: 2 human interventions (the scope-conflict confirmation, and the
  two-part design decision).
