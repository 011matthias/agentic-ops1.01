# Brisken expense reconciliation

Matches a month of card-statement charges against the receipts for them,
so the person closing the month works through exceptions instead of
through everything. Criss closes the month; the tool's job is to have an
opinion about every line before she looks at it, and to say which lines
it is unsure about.

**Verified against commit `603b4d1d` on 2026-09-20.** Everything
below was read off the code or the live app that day. Where this file used
to describe intentions, it now describes only what runs; anything you want
to know about why it is shaped this way is in the documents at the bottom.

## What it is, and what it is not

It is a **single-tenant working tool**: one company, one operator role, one
machine. It runs as a FastAPI JSON API on Fly.io in Frankfurt, with a
separate Lovable-built SPA as the screen Criss uses.

It is **not** the multi-tenant SaaS in
[`the v2 functional spec`](../../specs/1-spec/p1-expense-reconciliation-functional-spec.md).
Dirk descoped that on 2026-05-27 ("We just need a working tool. Anneal
quality through real-data use, not architecture up front"), and the build
has followed the tool since. The spec is kept as the original design, not
as a description of this program; `SPEC-GAP-REGISTER.md` maps one to the
other line by line. Multi-tenancy, RBAC, Firebase/Cloud SQL and mobile
receipt capture are out of scope by that decision, not missing by oversight.

## Where it runs

| | |
|---|---|
| API | `https://brisken-expense-recon.fly.dev` (Fly app `brisken-expense-recon`, region `fra`) |
| The screen Criss uses | `https://expenses.brisken.com` (Lovable SPA, repo `011matthias/brisken-expense-review`) |
| Receipts mailbox | `expenses.brisken.com` MX, port 25, served by this same app |
| Data | Fly volume `recon_data_v2` mounted at `/data`: run database, stored receipts, mail archive |

One machine serves all three. `docs/operating.md` is the page for running
it; `docs/if-it-is-down.md` is the page for when it will not run.

## Run it locally

```bash
cd workspace/clients/brisken/automations/expense-reconciliation
uv sync --extra web           # web extra: without it the API and its tests are skipped
uv run expense-recon-web      # http://127.0.0.1:8000, loopback only
```

Loopback only, so nothing leaves the machine. Interactive API docs are at
`/docs` when run this way. Without `OPENAI_API_KEY` in the environment the
LLM paths fall back to keyword rules rather than failing; set it to
exercise categorization, FX judgment and receipt extraction.

The same pipeline has a command line, which is how a month can be run
without the web app at all:

```bash
uv run expense-recon --config run.json            # reconcile, writes the xlsx
uv run expense-recon --config run.json --dry-run  # counts to stdout, no file
uv run expense-recon doctor   --config run.json   # pre-flight config check
uv run expense-recon calibrate --config run.json  # matcher metrics; non-zero exit on a broken invariant
uv run expense-recon history  --config run.json   # and `diff`, over past runs
uv run expense-recon backup   --dry-run           # and `--check` / `--go` (see docs/backup-and-restore.md)
uv run expense-recon-inspect statement.csv        # suggest a column_map for an unknown statement
```

`examples/run.example.json` is a working config to copy.

## Run the tests

```bash
uv run --extra web --with 'pytest>=8.0' pytest -q
```

**`--extra web` is not optional.** The web tests open with
`pytest.importorskip("fastapi")`, so without the extra they do not fail,
they SKIP, and the run still reports success. A green run that silently
skipped the API is the most likely way to believe a change is safe when it
is not.

CI runs the suite on every PR (`.github/workflows/expense-recon-tests.yml`);
it is the check that gates auto-merge.

There is a second gate beyond pass/fail: `expense-recon calibrate` runs the
matcher over a known-good month and exits non-zero if the reconciliation
invariant breaks or a receipt is double-bound, so it catches a matcher
regression that leaves every unit test green.

## How a month moves through it

1. Receipts arrive continuously, by mail to the intake address or by upload.
2. At month end a card statement is loaded, which is the reconcile step.
3. Ingest, categorize, deterministic match, then LLM judgment for the FX and
   ambiguous cases the deterministic pass could not settle.
4. Criss reviews: every charge has a proposed answer, and the ones the tool
   is unsure of are the ones it asks about.
5. The month is published, which is the record that it was reviewed and by
   whom.

The reconciliation guarantee holds throughout: nothing is silently dropped,
and FX entries always land in review rather than being auto-resolved.

## Where the rest is written down

This file is the orientation. It deliberately does not restate what these
cover, because two descriptions of one thing drift apart:

| Document | What it answers |
|---|---|
| `docs/operating.md` | Deploy, roll back, read live state, audit a publish, where the labels and the notifier live |
| `docs/if-it-is-down.md` | It is down: which half, the three failure shapes, how to recover |
| `docs/backup-and-restore.md` | What is backed up, and how to restore it |
| `docs/screen-field-map.md` | A wrong value is on screen: which function produced it |
| `docs/api-contract.md` | Every endpoint, request and response |
| `BLUEPRINT.md` | Why the design is shaped this way |
| `ANNEALING.md` | Known rough edges, and which ones were resolved |
| `SPEC-GAP-REGISTER.md` | The v2 spec against what was actually built |
| `../../status/p1-expense-reconciliation.md` | Where the work stands now |
| `../../status/p1-improvement-backlog.md` | The open backlog, numbered |
