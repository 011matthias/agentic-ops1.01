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

### 2. The published SPA: what is live (audited 2026-08-25)

The owner published after this round. Audited against the deployed API by
driving the app; **do not re-derive this, and do not trust a text scan** (see
the trap below).

The intake page is **`/inbound`**, not `/intakes`. Routes on the published
build: `/`, `/months`, `/inbound`, `/memory`, `/compare`, `/guide`,
`/settings`, `/expenses/new`.

LIVE, verified:

- `lovable-month-report-prompt.md` — "Download expense report (PDF)" and
  "Download CSV (data export)" on the batch page, reconciliation PDF on the
  workbench. This was the one that changes what Criss can DO.
- `lovable-body-only-prompt.md` — held rows offer **View body / Add to month
  as PDF / Dismiss**.
- `lovable-month-pool-prompt.md` sections 1, 2, 4, 5, 6 — "Waiting: 6" badge,
  Month column reading "August 2026 (waiting)", Dismiss on pooled rows,
  "Retry held and add waiting mail".
- `lovable-intake-quickwins`, `lovable-ready-tile`, `lovable-cards-r3`.

**The "Arriving" bug is gone.** The SPA fixed it with its own status map
(section 1) rather than with `status_label` (section 0); the rendering is
correct either way. A pooled row reads "Waiting for its month" with the
month in the column beside it.

NOT applied:

- month-pool **section 0** (`status_kind` / `status_label`) — not urgent, the
  SPA's own strings are right today. It is the durability fix: the next
  status value added mislabels again without it.
- month-pool **section 12** (refusals strip) — `n_refused` is live and
  unrendered.
- `lovable-known-senders-prompt.md` — no "People we recognise" editor.
- `lovable-open-intake-prompt.md` — **the stale "Accepted senders" editor is
  still on the Settings screen and the backend has ignored `intake.senders`
  since #587, so anything typed there is silently discarded.**
- `lovable-re-ingest-prompt.md`, `lovable-issue-codes-prompt.md` —
  UNVERIFIED, both need a state the live app does not currently have (a
  stranded attachment archive; a batch carrying a parse issue).

Stale Settings copy, unrelated to any prompt: "People who can email receipts
straight into the open month" and "the sender gets a short reply when their
receipts land in the open month". Both predate the month pool.

**The audit trap, worth remembering.** Enumerating `button` innerText reports
NO actions on an intake row: the per-row control is an icon-only ellipsis
`button[aria-label="Actions"]` opening a Radix menu, and its text is empty.
The first pass of this audit concluded body-only handling was missing
because of exactly that. Click the Actions button and read `[role=menuitem]`.
Probe: `%TEMP%/claude/recon-probe/held_menu.py`.

### 3. Whatever the next feedback wave surfaces

The 2026-08-21 wave is fully worked through. Items 16, 17, 3, 4, 5, 8 in the
backlog are small and unranked; none of them is urgent.

## Owner-side, still open (hand the paths when asked, do not chase)

Unapplied Lovable prompts, all with their backends already live, under
`workspace/clients/brisken/automations/expense-reconciliation/docs/`:

- `lovable-open-intake-prompt.md` — **most urgent, and it is a trap rather
  than a gap**: the "Accepted senders" editor IS on the live Settings
  screen and the backend ignores what it writes. Someone authorising a
  sender there during testing gets a false result.
- `lovable-known-senders-prompt.md` — the Settings editor for
  `intake.known_senders`; replaces the editor above with one that works.
- `lovable-month-pool-prompt.md` sections 0 and 12 only (1-11 are live).
- `lovable-re-ingest-prompt.md`, `lovable-issue-codes-prompt.md` — status
  unverified, see section 2.
- `lovable-month-report-prompt.md` and `lovable-ready-tile-prompt.md` are
  APPLIED; nothing to hand over.

**One settings decision waiting:** listing `dirk_.neumann@icloud.com` in
`intake.known_senders` starts sending confirmations to his private mailbox
and makes his forwarded receipts render on arrival. One PUT, and it is the
owner's call rather than something an agent does silently. Send the WHOLE
`intake` object: the merge is shallow at the top level, so a partial PUT
drops the aliases with it.

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
