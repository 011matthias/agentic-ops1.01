---
project: brisken
workstream: p1-expense-reconciliation
kind: loop-runbook
state: active
updated: 2026-08-25
---

# Brisken expense tool: improvement loop, next round (paste into a fresh chat)

Load the Brisken expense-reconciliation project (p1). We are continuing the
test-and-fix loop on the receipt-first pipeline until the tool is genuinely
usable for Brisken. Read this whole brief before touching anything, then read
`p1-improvement-backlog.md` beside it — that file, not this one, is the list of
what to do next.

## Where things stand (2026-08-25, end of session)

**Backlog item 30 is fully shipped and deployed** (PRs #607, #608, #609; Fly
**v90**), along with the out-of-Lovable half of the "Arriving" bug:

- **Known senders.** Settings `intake.known_senders` lists outside addresses
  that count as ours. `graph_notify.send_mail` takes an explicit per-call
  `allow_external` and asserts the structural recipient guard BEFORE
  consulting it. **The production list is EMPTY** — Dirk's
  `dirk_.neumann@icloud.com` still gets no ack until an operator lists it.
- **Body-only mail from a known sender renders on arrival**, reusing the
  operator render path unchanged. Strangers still hold and still alert.
- **Every refusal is written down** (`inbound/refusals.jsonl`, DATA-stage
  guards included), surfaced as `n_refused` (7-day window) + `refusals[]`.
- **Every log row carries `status_kind` + `status_label`**, and an
  unrecognised status degrades to the raw value instead of borrowing a label.
  api-contract **rule 5** now covers enum growth; `test_every_status_has_a_label`
  fails the suite on a new status until someone decides what it SAYS.

Baselines: suite **1257 passed / 2 skipped**, calibrate green, ruff (E9,F)
clean on the diff. Worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-recon`,
app root `workspace/clients/brisken/automations/expense-reconciliation`.

**Live state:** 21 inbound archives, 6 **pooled**, `n_held` 0, `n_refused` 1
(a deliberate relay-refusal drill on 2026-08-24; it ages out of the window).
The 6 pooled are real receipts waiting for months that do not exist, and they
now say so on screen:

| Month | Mail |
| --- | --- |
| 2026-08 | Monetico/CIC card ticket, two OpenAI purchases, OpenAI credits |
| 2026-07 | Hostinger subscription, AWS billing statement |

They join automatically the moment a batch labelled "August 2026" /
"July 2026" exists. `create_expense_batch` refuses an empty batch, so opening a
month needs at least one uploaded receipt — do NOT seed a fabricated one into
a live month.

## The directions, in the order they now rank

### 1. PR 2 of the living month (backlog item 29) — the top remaining build

Already owner-approved; the approved plan file is
`C:\Users\neuma_p1qrsic\.claude\plans\fizzy-seeking-lagoon.md`.

Stable content-derived transaction ids are the prerequisite: ids are
positional today (`f"{account_id}:{row_index}"` in `ingest/statement_csv.py`)
and operator decisions key on them, so any appended or partial statement
upload renumbers every decision onto the wrong charge. Then: append-capable
statement uploads (per card, several times a month, content-id dedupe),
`has_statement` no longer closing the month, and incremental re-match
preserving operator decisions and persisting LLM FX/ambiguous judgments by
(transaction_id, document_id) so a re-match never re-spends on a pair it
already judged.

Nothing is on fire here, which is exactly why it is now the top item.

### 2. The published SPA: what is live

**`automations/expense-reconciliation/docs/PROMPT-STATUS.md` is the ledger.**
One row per Lovable prompt, applied or not, with the evidence. Audited
2026-08-25 by driving the app. Re-run
`%TEMP%/claude/recon-probe/prompt_ledger.py` and update that file whenever
the owner publishes; a prompt sitting in `docs/` says nothing about whether
it was ever pasted, and guessing from the repo is what made coordination bad
enough for the owner to call it out.

Headline from that audit: **`/months` renders only the create form.** Zero
tables, zero rows; the page fetches `GET /api/expense-batches`, gets six
batches, and discards them. There is no way into an existing month except
the intake page's Month links. That is backlog item 32 and
`docs/lovable-months-list-prompt.md`, and it blocks testing harder than
anything else open.

Sixteen prompts ARE applied, including both report-PDF buttons, body-only
handling, cards R3, set-aside, memory editing and the feedback widget. Three
remain, all rewritten 2026-08-25 to open with a measured inventory of what
the app already has, so Lovable adds the delta instead of rebuilding working
screens.

**Two audit traps, both of which produced a wrong answer first.** A loose
regex matched a Cards help line and reported the known-senders editor as
present; and per-row intake actions are an icon-only
`button[aria-label="Actions"]` menu, so enumerating button TEXT reports no
actions on any row. Match exact strings, and open the menu.

### 3. Whatever the next feedback wave surfaces

The 2026-08-21 wave is fully worked through. Items 16, 17, 3, 4, 5, 8 in the
backlog are small and unranked; none of them is urgent.

## Owner-side, still open (hand the paths when asked, do not chase)

Unapplied Lovable prompts, all with their backends already live, under
`workspace/clients/brisken/automations/expense-reconciliation/docs/`:

Ledger with evidence: `automations/expense-reconciliation/docs/PROMPT-STATUS.md`.
Unapplied, in the order they matter:

- `lovable-months-list-prompt.md` — **THE blocker.** No way into an existing
  month; `/months` is the create form only. Backlog item 32.
- `lovable-known-senders-prompt.md` — Settings > Email intake: deletes the
  dead "Accepted senders" editor (backlog item 31), rewords three stale help
  lines, adds the `known_senders` field.
- `lovable-inbound-status-refusals-prompt.md` — the status label + the
  refusals strip. Supersedes month-pool §0/§12, which were REMOVED from that
  file so it cannot be double-pasted.
- `lovable-issue-codes-prompt.md`, `lovable-re-ingest-prompt.md` — status
  unverifiable; no live batch or archive exercises them.

Everything else in `docs/` is APPLIED; nothing to hand over.

Card registry data entry: entities for cards 0113 / 6013 / 9693 / 8311 and
the missing 0340 card. That is backlog item 26 and the live MISSING ENTITY
count, not a defect in the resolution chain.

Live finding already surfaced, not a bug: the January statement run
reconciles 0 of 80 charges, USD 20,228.68 unreconciled, 78 charges with no
receipt at all.

**Do not re-ask the owner about:** the export target (there is none), Zoho (no
ties, deleted), mixed-entity export (one file, entity as a column), cash and
personal tenders (per-month assignments, not cards), or the January credit
notice (booked).

## House loop (unchanged)

Regression tests proven RED first by temporarily regressing the real source,
then un-regressing. Full suite `--all-extras` + `calibrate --config
examples/run.example.json` per PR. Adversarial review over the whole diff
before committing — it has found real defects every single round, including
both of this one's (a stranded `rendering` status, a sub-second window
cutoff). Ship per B6 (commit → push → `gh pr create` → merge on green CI;
never push main directly). Ledger files (`docs/INDEX.md`, friction register,
`docs/sessions/`) NEVER on a client branch — separate docs PRs. Deploy is
pre-authorized after a green merge: check `/api/operator/state` for in-flight
jobs first, deploy from a clean `origin/main` worktree, then verify
`/healthz` plus a real API read — AND drive the SPA if the payload changed.

**A RED-proof harness must snapshot the WORKING TREE, not restore from git.**
A `git checkout -- <path>` restore between regression cases silently destroys
uncommitted edits to the same files; that cost two rebuilds on 2026-08-25
before the harness was changed to snapshot the file contents in memory. Commit
early on the feature branch regardless.

## Standing constraints

Never message Criss or Dirk without an explicit ask. Never invent data values
(B4). No stash; use worktrees. Batches and fixtures created live must be
`TEST -` namespaced and removed afterwards (re-list until zero remain). SPA
view contract: parallel fields only, never retype list fields
(`docs/api-contract.md`, `tests/test_view_contract.py`), and per **rule 5** a
grown enum ships a parallel human-readable label.

**Graph mailbox allowlist is `dirk.neumann@brisken.com` and
`matthias.silva@brisken.com` ONLY** — Criss's mailbox is off-limits, which
means anything she forwarded is invisible from the sending side.

Operator code for the SPA/API is in the local vault entry "Brisken recon
operator code matthias" (never print it). OpenAI key is vault "OpenAI Brisken"
and bills Dirk — smallest possible test sets. Probe helpers live in
`%TEMP%/claude/recon-probe/` (`api.py`, `smtp_probe.py` for an envelope-only
liveness/refusal drill, `drill_autorender.py` + `dismiss_drill.py` for a
full TEST- namespaced body-only drill).

**Windows gotchas:** the cd-guard hook blocks `cd X && ...` — use
`( cd X && ... )`, `git -C`, `uv run --directory`, or absolute paths. Bash
heredocs carrying large Python payloads fail (escapes collapse, "unexpected
EOF"); use the Write tool for anything file-sized.
