---
project: brisken
workstream: p1-expense-reconciliation
kind: loop-runbook
state: active
updated: 2026-08-24
---

# Brisken expense tool: improvement loop, next round (paste into a fresh chat)

Load the Brisken expense-reconciliation project (p1). We are continuing the
test-and-fix loop on the receipt-first pipeline until the tool is genuinely
usable for Brisken. Read this whole brief before touching anything, then read
`p1-improvement-backlog.md` beside it — that file, not this one, is the list of
what to do next.

## Where things stand (2026-08-24, end of session)

**PR 1 of the living-month plan is SHIPPED and DEPLOYED** (#599 engine, #601
count fix, #602 status; Fly **v87**). Emailed receipts now file by the month
PRINTED on the receipt instead of landing in whichever batch happened to be
open, and mail whose month has no batch RESTS in a pool (status `pooled`) until
that month is created or renamed into, at which point it is claimed
automatically. Deleting a month returns its mail to the pool. Full design and
the PR 2 / PR 3 specs are backlog item 29; the approved plan file is
`C:\Users\neuma_p1qrsic\.claude\plans\fizzy-seeking-lagoon.md`.

Baselines: suite **1237 passed / 2 skipped**, calibrate green, ruff (E9,F)
clean. Worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-recon`, app root
`workspace/clients/brisken/automations/expense-reconciliation`.

**Live state that matters:** 19 inbound archives, 10 ingested, 6 **pooled**, 3
dismissed (test drills, cleaned). `n_held` is 0 for the first time. The 6
pooled are real receipts waiting for months that do not exist:

| Month | Mail |
|---|---|
| 2026-08 | Monetico/CIC card ticket, two OpenAI purchases, OpenAI credits |
| 2026-07 | Hostinger subscription, AWS billing statement |

They join automatically the moment a batch labelled "August 2026" / "July 2026"
exists. `create_expense_batch` refuses an empty batch, so opening a month needs
at least one uploaded receipt — do NOT seed a fabricated one into a live month.

## The three directions, in the order they were ranked

### 1. Ship the SPA half of PR 1 (owner action, blocking)

`docs/lovable-month-pool-prompt.md` is written and merged but NOT applied. This
is not polish: the live SPA renders a pooled row as status **"Arriving"** with a
blank Month (verified against the deployed app, no crash, no console errors —
the parallel-field contract held). So six of Dirk's real receipts currently tell
Criss they are "arriving" indefinitely, which is worse than the held strip was,
because held at least looked like it needed attention. The agent cannot inject
Lovable prompts; the owner does that manually.

### 2. Intake trust (backlog item 30) — recommended next build

Small, and this session proved it is where receipts are actually being lost.
Three parts, all in item 30: outside senders (Dirk's iCloud address) get no ack
at all; a refused RCPT leaves no trace anywhere; and forwarded vendor receipts
are body-only by default, so they all sit held until someone clicks render.
Doing this before PR 2 means the living month gets built on a mailbox people can
trust rather than one nobody can audit.

### 3. PR 2 — the living month (backlog item 29)

The larger prize and already owner-approved. Stable content-derived transaction
ids (the prerequisite — ids are positional today and operator decisions key on
them, so any appended or partial statement upload renumbers decisions onto the
wrong charge), append-capable statement uploads, `has_statement` no longer
closing the month, and incremental re-match preserving operator decisions and
persisted LLM judgments. Nothing is on fire here.

## House loop (unchanged)

Regression tests proven RED first by temporarily regressing the real source,
then un-regressing. Full suite `--all-extras` + `calibrate --config
examples/run.example.json` per PR. Adversarial review over the whole diff before
committing — it has found real defects every single round, including this one.
Ship per B6 (commit → push → `gh pr create` → merge on green CI; never push main
directly). Ledger files (`docs/INDEX.md`, friction register, `docs/sessions/`)
NEVER on a client branch — separate docs PRs. Deploy is pre-authorized after a
green merge: check `/api/operator/state` for in-flight jobs first, deploy from a
clean `origin/main` worktree, then verify `/healthz` plus a real API read.

**Verify the consumer, not just the API.** The v86 deploy was declared verified
on API reads alone; the SPA check that found the "Arriving" fallback only
happened later. A deploy touching a payload is not verified until the SPA has
been driven against it.

## Standing constraints

Never message Criss or Dirk without an explicit ask. Never invent data values
(B4). No stash; use worktrees. Batches and fixtures created live must be
`TEST -` namespaced and removed afterwards (re-list until zero remain). SPA view
contract: parallel fields only, never retype list fields
(`docs/api-contract.md`, `tests/test_view_contract.py`).

**Graph mailbox allowlist is `dirk.neumann@brisken.com` and
`matthias.silva@brisken.com` ONLY** — Criss's mailbox is off-limits, which means
anything she forwarded is invisible from the sending side.

Operator code for the SPA/API is in the local vault entry "Brisken recon
operator code matthias" (never print it). OpenAI key is vault "OpenAI Brisken"
and bills Dirk — smallest possible test sets. Probe helpers live in
`%TEMP%/claude/recon-probe/` (`api.py` for authed calls; launch chromium with
`channel="chrome"` and dismiss the feedback modal via the "Got it" button).

**Windows gotchas:** the cd-guard hook blocks `cd X && ...` — use `( cd X && ... )`,
`git -C`, `uv run --directory`, or absolute paths. Bash heredocs carrying large
Python payloads fail (escapes collapse, "unexpected EOF"); use the Write tool
for anything file-sized. And **commit early on the feature branch** — a
`git checkout -- <path>` on uncommitted work destroyed a whole file this session
and cost a full rebuild.
