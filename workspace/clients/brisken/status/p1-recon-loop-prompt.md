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

### 1. The "Arriving" bug: ship the SPA half of PR 1

`docs/lovable-month-pool-prompt.md` is written and merged but NOT applied. This
is not polish. Verified against the deployed app with Playwright: the page does
NOT crash and throws no console errors (the parallel-field contract held), but
it renders a pooled row as status **"Arriving"** with a blank Month. The SPA
maps an unrecognised status onto its in-flight label, so six of Dirk's real
receipts are telling Criss they are arriving indefinitely. That is worse than
the held strip was, because "Arriving" is an affirmative, self-resolving claim
while "held" at least looked like it needed attention. `routing` and `claiming`
mislabel the same way; they are transient so the impact is seconds, not days.

**The primary fix is Lovable and the owner applies it** (the agent cannot inject
Lovable prompts). Section 1 of the prompt is the whole of it: add `pooled` to
the status map, label it "Waiting for its month", keep it out of the Held badge.

**What may need work OUTSIDE Lovable — pick up in this order:**

1. **Verify, do not assume.** After the prompt is applied, drive the live SPA
   and confirm a pooled row reads "Waiting for {Month}" and not "Arriving".
   Six pooled rows exist right now, so no TEST mail is needed. Use
   `%TEMP%/claude/recon-probe/` (chromium `channel="chrome"`, dismiss the
   feedback modal via "Got it"). A deploy that changes a payload is not
   verified until the SPA has been driven against it.
2. **If the SPA cannot cleanly extend its status map**, ship the label from the
   backend instead: add parallel per-row `status_label` (already-composed text,
   e.g. "Waiting for July 2026") and `status_kind`
   (`resting` | `held` | `working` | `done`) in `read_log` /
   `annotate_pool_state`, so the SPA renders text it does not have to know
   about. Small change; needs the contract row and a view-contract test.
3. **Close the contract gap that let this happen.** `docs/api-contract.md` pins
   list ELEMENT TYPES and says nothing about adding a new VALUE to an existing
   enum-ish field. `status` gained three values and the SPA silently mislabeled
   all three. Extend rule 1 ("enriching a field in place is the dangerous
   move") to cover enum growth, with the standing mitigation being option 2:
   when a status set grows, ship a parallel human-readable label so an
   un-updated consumer degrades to correct text rather than a confident wrong
   label.

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

## Owner-side, still open (hand the paths when asked, do not chase)

Unapplied Lovable prompts, all with their backends already live, under
`workspace/clients/brisken/automations/expense-reconciliation/docs/`:

- `lovable-month-pool-prompt.md` — NEW and the most urgent; without it pooled
  rows render as "Arriving".
- `lovable-month-report-prompt.md` — the one that changes what Criss can DO: it
  puts the two report-PDF buttons on screen.
- `lovable-re-ingest-prompt.md`, `lovable-issue-codes-prompt.md`,
  `lovable-ready-tile-prompt.md`, and `lovable-open-intake-prompt.md` (that last
  one only if the "Accepted senders" editor was ever built).

Card registry data entry: entities for cards 0113 / 6013 / 9693 / 8311 and the
missing 0340 card. That is backlog item 26 and the live MISSING ENTITY count,
not a defect in the resolution chain.

Live finding already surfaced, not a bug: the January statement run reconciles
0 of 80 charges, USD 20,228.68 unreconciled, 78 charges with no receipt at all.

**Do not re-ask the owner about:** the export target (there is none), Zoho (no
ties, deleted), mixed-entity export (one file, entity as a column), cash and
personal tenders (per-month assignments, not cards), or the January credit
notice (booked).

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
