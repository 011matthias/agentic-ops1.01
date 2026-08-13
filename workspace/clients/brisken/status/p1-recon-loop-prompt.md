---
project: brisken
workstream: p1-expense-reconciliation
kind: loop-runbook
state: active
updated: 2026-08-13
---

# Brisken expense tool: improvement loop, next round (paste into a fresh chat)

Load the Brisken expense-reconciliation project (p1). We are continuing the
test-and-fix loop on the receipt-first pipeline until the tool is genuinely
usable for Brisken. Read this whole brief before touching anything.

## Where the loop stands (2026-08-13, after round 1+2)

Two fixes are live on Fly release v58 (app `brisken-expense-recon`):

1. **Non-receipt quarantine (PR #516).** The tool now recognizes when an
   upload is not a receipt (a bank-statement page, an expense-report summary
   sheet) and sets it aside with a visible warning instead of inventing an
   expense from it. Verified on Criss's real May folder: 7 of 7 statement
   PDFs set aside, 20 of 20 real receipts kept.
2. **No more literal "null" accounts (PR #518).** When the AI answers "no
   category" as the word "null", the export now shows the honest
   "(uncategorized - assign)" placeholder instead.

**The single source of truth for what to do next is the backlog file
beside this one: `p1-improvement-backlog.md`. Pick the top OPEN item
(currently: "Same photo, same answer" — the extraction cache — with "test
runs should use the merchant name book" as its small companion). Every new
improvement idea you have during the session gets APPENDED to that backlog
file, never left in chat or scattered into checkpoint notes.**

## What the tool is, and the one mode that matters

`workspace/clients/brisken/automations/expense-reconciliation` — FastAPI
engine on Fly (`brisken-expense-recon`, scale-to-zero, machine
`48ee133c363758`, region fra). The review UI is a separate Lovable SPA at
`brisken-reconcile-dash.lovable.app`; the backend is API-only.

**Brisken only does receipt-first reconciliation** (`mode:
"expense_generation"`): a folder of receipt photos/PDFs goes in, the AI
reads each one, a Zoho Expenses CSV comes out. The statement-plus-report
reconciliation path exists in the code but is NOT their workflow; do not
spend effort there and do not use it to judge quality.

Criss (she/her) runs this monthly. Her real process is in memory
`project_brisken_expense_recon_chris_process`; the loop state is in memory
`project_brisken_expense_recon_usability_loop`.

## Test material (all local, machine-bound paths)

Root: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\`

| Set | Path | Contents |
|---|---|---|
| 1 | `.scratch\criss-recon-may\` | Criss's real May month: 27 files in `receipts\` (20 receipts + 7 Chase statement PDFs), `May2026.xlsx`, `run.local.json`, `run.llm.json` (added 2026-08-13), `expenses.csv` from the verified quarantine run |
| 2 | `.scratch\criss-recon-runs\7d2fea33d39a\` | 37 receipts, largest set, `run.local.json` |
| 3 | `.scratch\criss-recon-runs\05d3db59b225\` | 10 receipts + `run.llm.json` (**start here**). Outputs kept: `expenses-BASELINE.csv` (July 28 code), `expenses-NEW.csv` + `expenses-NEW2.csv` (2026-08-13 pre-fix, the drift/null evidence), `expenses-QUARANTINE-RUN3.csv` (post-fix, verified) |
| 4 | `.scratch\test-receipts-ER-00215\` | 37 loose receipt PNGs, no config (same images as set 2) |
| 5 | `.scratch\test-receipts-ER-00215-smoke10\` | 10 PNGs, no config (same images as set 3) |
| 6 | `workspace\clients\brisken\context\expense-reconciliation\receipts\` | 13 real receipts, different vendor mix: Uber email-forwards, MBTA ticket, ZE scans |

Genuinely distinct material: set 1 (May), set 2 (ER-00215), set 6
(different vendors). Sets 3/4/5 are draws from the same 37 images.

## How to run one (this exact recipe works)

The main checkout is shared with other live sessions and usually behind
`origin/main`. Work from the dedicated worktree, refreshed first:

```powershell
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1-recon fetch origin
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1-recon checkout --detach origin/main
```

(If `agentic-ops1-recon` does not exist: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add --detach C:\Users\neuma_p1qrsic\Repo\agentic-ops1-recon origin/main`.)

The key is in the local vault, entry `OpenAI Brisken`:

```python
json.loads((pathlib.Path.home()/'.passwords.json').read_text())['OpenAI Brisken']['api_key']
```

Export it as `OPENAI_API_KEY` (never print it), then:

```powershell
uv run --directory <worktree>\workspace\clients\brisken\automations\expense-reconciliation --all-extras expense-recon --config <abs path>\run.llm.json
```

`--all-extras` matters: without it `rapidfuzz` is missing and 9 test
modules fail to import. Full suite baseline: **1043 passed, 2 skipped**.

### Traps that will waste your time

1. **A run overwrites its own output.** `output.path` is ignored in
   `expense_generation` mode; it writes `expenses.csv` into the config's
   directory. Copy the previous output aside before every run.
2. **`legal_entity_id` must be exactly `Corporate Services` or `Cloud
   Services`** — anything else silently yields `has_coa: false`. The local
   configs are already correct.
3. **Quarantine warnings are EXPECTED output now.** Set 1 prints 7
   "looks like a bank/card statement page… excluded" lines and set 3
   prints 1 "expense-report summary page" line. That is the shipped fix
   working, not a failure.
4. **Cost:** the vault key is Dirk's, so runs bill him. A 10-receipt pass
   on `gpt-4o-mini` is cents; repeated 37-receipt sets are not. Default to
   set 3.

## What is already known (do not re-derive)

- **receipt_01 is RESOLVED.** The "1,837.51 USD vs 8,796.35 BRL flip" was
  never a money bug: the image is page 7 of a Zoho expense report, a
  summary page that carries BOTH totals. It is now quarantined.
- **Money fields are stable run-to-run on the same code** (verified twice
  on set 3). The live defect class is TEXT drift: vendor spellings (MEGA
  CENTER / CENTRO / CENTRE from one image), reference numbers, tax labels,
  line-item descriptions — all at temperature 0.
- **The CLI never loads the merchant registry.** `_run_expense_generation`
  calls `generate_expenses(cfg, dir)` bare (`registry=None`,
  `expense_memory=None`); only the web path consults the registry. Backlog
  item 2 closes this.
- **A receipt can legitimately split into two CSV rows** (one per Zoho
  account, same Reference#, sums exact). Whether Criss wants that is
  backlog item 4 — an owner conversation, not code.
- **Learned memory** (`/data/learning.sqlite`, 103 seeded rows) self-heals
  as Criss corrects. Do NOT loosen its exact-match lookup to fuzzy; that
  cross-wires merchants.

## The loop

Each iteration:

1. **Run** a set (start with set 3) and save the output under a distinct
   name.
2. **Diff** against the prior saved outputs, field by field. Money fields
   and text fields fail differently; only text is currently broken.
3. **Pick the top OPEN backlog item** (`p1-improvement-backlog.md`). The
   ranking rule: wrong money beats wrong text, things that stop the tool
   from learning beat cosmetics, monthly pain beats one-offs.
4. **Diagnose against the real code** in the refreshed worktree, never
   against memory of it.
5. **Fix on a `client/brisken/...` branch.** Write a regression test and
   prove it fails without the fix. Full suite with `--all-extras`.
6. **Ship:** commit, push, PR, merge on green CI. Fly deploys are
   pre-authorized after a green merge (`feedback_fly_deploy_preauthorized`);
   deploy from a clean origin/main worktree and verify the live origin
   (healthz 200, `/api/expense-batches` returns 401 not 404).
7. **Re-run the same set** and confirm the defect is gone in the OUTPUT,
   not just in tests.
8. **Bookkeeping in the same session:** move shipped items to the
   backlog's "Shipped" table, append any new ideas to "Open", bump the
   status file row, update memory `project_brisken_expense_recon_usability_loop`.

Stop and ask only for: a design decision that changes behavior Criss
depends on, anything touching her live runs or published data, or a real
send.

## Definition of done (scorecard as of 2026-08-13)

The tool is usable when a month of her real receipts produces a CSV she
can post with judgment-level edits only:

- Same receipts run twice → same money: **done, verified**
- No phantom rows from non-receipts: **done, verified on May**
- Honest "(uncategorized)"/"(illegible)" instead of guesses: **done**
- Amounts, currencies, dates match the receipt: **holding, keep checking**
- Same receipts run twice → same VENDOR, so learning compounds: **open —
  this is the current target**

## Standing constraints

- Verify behavior, not config. Name the test you ran.
- Never invent a data value; unverified reads TBD.
- No client messages to Criss or Dirk without an explicit ask.
- Never touch her live runs on the Fly volume; pull material down and work
  locally.
