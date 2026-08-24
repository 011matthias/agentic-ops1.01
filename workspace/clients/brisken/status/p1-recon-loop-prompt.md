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

### 2. Verify the SPA once the owner applies the prompts

The backend halves are all live; the SPA is the remaining half of three
rounds. **Verify, do not assume**: drive the live SPA and confirm what it
renders. Six pooled rows exist right now, so no TEST mail is needed. Use
`%TEMP%/claude/recon-probe/` (`api.py` for authed calls; chromium
`channel="chrome"`, dismiss the feedback modal via "Got it").

What to check after each prompt lands:

- A pooled row reads **"Waiting for August 2026"** and not "Arriving". The
  backend already composes that text (`status_label`); section 0 of the
  month-pool prompt is what makes the SPA render it.
- The Settings screen has a "People we recognise" editor writing
  `intake.known_senders`.
- The two report-PDF buttons are on screen.

A deploy that changes a payload is not verified until the SPA has been driven
against it. The "Arriving" bug was found exactly that way, and so was the
dismissed-row mislabel this round (#609), which an API read alone did not
show.

### 3. Whatever the next feedback wave surfaces

The 2026-08-21 wave is fully worked through. Items 16, 17, 3, 4, 5, 8 in the
backlog are small and unranked; none of them is urgent.

## Owner-side, still open (hand the paths when asked, do not chase)

Unapplied Lovable prompts, all with their backends already live, under
`workspace/clients/brisken/automations/expense-reconciliation/docs/`:

- `lovable-month-pool-prompt.md` — **most urgent**; section 0 (render from
  `status_kind` / `status_label`) is the fix for the live "Arriving"
  mislabel, and section 12 adds the refusals strip.
- `lovable-known-senders-prompt.md` — NEW; the Settings editor for
  `intake.known_senders`.
- `lovable-month-report-prompt.md` — the one that changes what Criss can DO:
  it puts the two report-PDF buttons on screen.
- `lovable-re-ingest-prompt.md`, `lovable-issue-codes-prompt.md`,
  `lovable-ready-tile-prompt.md`, and `lovable-open-intake-prompt.md` (that
  last one only if the "Accepted senders" editor was ever built).

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
