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

## Where things stand (2026-08-25, end of day)

**The living month is built.** Backlog item 29's whole PR-2 chain is shipped
and deployed (Fly **v97**): stable transaction identity (2a), `rematch_month`
+ the judgment cache (2b-1), the extraction baseline (2b-1b), the month
staying open (2b-2a), the fold (2b-2b-1), and the `statements[]` surface
(2b-2b-2, PR #636).

A statement is now an input stream, not a closing event. `POST
.../statement` appends by identity and is repeatable per card; each upload is
recorded in `statements[]` on both review payloads; the sheet writeback is
anchored PER UPLOAD (`statement_anchors`), because one charge occupies a row
in every file that prints it and a field on the charge could only name one of
them. Two hazards are answered by surfacing, never deduping: an `advisory`
fires when one card is typed against two account ids, or when an upload lands
100% new over a period the same account already covers. `rematch_month`
refuses any commit that would drop a charge the month gained meanwhile.

**Next is PR 3, the coverage surface** - per-card coverage in the batch view
(which cards have statements, over what periods, matched/unmatched per card),
the month page's statement panel, and per-card sections in the reconciliation
report. The backend half of the selector already exists
(`GET /runs/{id}/statement-categorized.xlsx?file=`), but the SPA renders
neither `statements[]` nor the selector, so from the UI a month with two xlsx
statements can still only download the current one.

**Backlog item 30 is fully shipped and deployed** (PRs #607, #608, #609),
along with the out-of-Lovable half of the "Arriving" bug:

- **Known senders.** Settings `intake.known_senders` lists outside addresses
  that count as ours. `graph_notify.send_mail` takes an explicit per-call
  `allow_external` and asserts the structural recipient guard BEFORE
  consulting it. **The production list is EMPTY** - Dirk's
  `dirk_.neumann@icloud.com` still gets no ack until an operator lists it.
- **Body-only mail from a known sender renders on arrival**, reusing the
  operator render path unchanged. Strangers still hold and still alert.
- **Every refusal is written down** (`inbound/refusals.jsonl`, DATA-stage
  guards included), surfaced as `n_refused` (7-day window) + `refusals[]`.
- **Every log row carries `status_kind` + `status_label`**, and an
  unrecognised status degrades to the raw value instead of borrowing a label.
  api-contract **rule 5** now covers enum growth; `test_every_status_has_a_label`
  fails the suite on a new status until someone decides what it SAYS.

**Backlog item 29 PR 2a (stable transaction identity) and PR 2b-1
(`rematch_month` + the judgment cache) are shipped**; see direction 1 below.

**Arrival-time duplicate detection is shipped** (backlog item 33): a mail
whose content the tool already holds is parked as `duplicate` before it
reaches a month, and points at the mail that has it.

Baselines: suite **1352 passed / 2 skipped**, calibrate exit 0, ruff (E9,F)
clean on the diff. App root
`workspace/clients/brisken/automations/expense-reconciliation`.

**Worktrees were consolidated on 2026-08-25.** There is no longer an
`agentic-ops1-recon` worktree: the repo is the primary clone
`C:\Users\neuma_p1qrsic\Repo\agentic-ops1` (on `main`, clean) plus
`agentic-ops1-deploy` (detached at origin/main, deploys only). Cut a fresh
worktree for the round rather than expecting an old one to exist.

**Live state (2026-08-25):** 10 **pooled**, `n_held` 0, `n_duplicates` 0.
Three of the pooled ten are the SAME Hostinger invoice (H_46243348),
forwarded three times minutes before the dedupe deployed; they will
become three expenses when July 2026 opens unless two are dismissed.
`intake.known_senders` is still EMPTY, so Dirk's
`dirk_.neumann@icloud.com` body-only forwards hold and go unacked.

**Earlier state:** 21 inbound archives, 6 **pooled**, `n_refused` 1
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

**Owner ruling 2026-08-24: pre-creating months INTRUDES.** The open question
from the previous checkpoint is closed. We do not open August or July on
Criss's behalf, and we do not ask her to. The pool is the correct resting
place and the receipts wait there until she opens the month herself in the
course of her own work. This retires the "create the two months" step that
sat at position 2 of the previous next-steps list.

## The directions, in the order they now rank

### 1. PR 2b of the living month (backlog item 29) — the top remaining build

Already owner-approved; the approved plan file is
`C:\Users\neuma_p1qrsic\.claude\plans\fizzy-seeking-lagoon.md`.

**PR 2a is done.** Transaction ids are content-derived and stable under
append, insert and reorder; `assign_content_ids` in `ingest/_common.py` is
the one definition, called at the end of every statement parse. Read its
docstrings before touching identity — the stamp is a post-pass for a
reason (sign canonicalization) and the `-{n}` occurrence separator is not
a `:` for a reason (the sheet writeback reads a trailing `:N` as a row).

**PR 2b-1 is also done.** `service.rematch_month` is the one function that
reconciles what a month currently holds; the attach path is its first caller
and every incremental path in 2b-2 calls it rather than growing a second
copy. `web/judgment_cache.py` means a re-match only pays for pairs it has
not judged before.

What remains (PR 2b-2): append-capable statement uploads (per card, several
times a month, content-id dedupe), `has_statement` no longer closing the
month, and wiring the incremental re-match to receipt arrivals.

Start 2b-2 by triaging the `has_statement` guard, NOT by lifting it. It
refuses at nine call sites in three classes: three that must open (receipts,
statement, set-aside restore), two that should open only because a re-match
now follows (cards, refresh-master-data), and four expense-edit overlay
routes that must stay closed or get a real decision, because the attach
bakes edits into the snapshot receipts and reopening the overlay over a
baked pool risks double-application. The plan reads as if it were one
switch. It is not.

One interaction PR 2a pinned deliberately and 2b has to handle: a file
whose SIGN inference differs between a partial and a full upload yields
different ids for the same printed row, because the two uploads genuinely
disagree about whether the money went out or came back. Surfacing two rows
beats silently deduping a contradiction. Decide in 2b whether that wants a
visible warning.

Nothing is on fire here, which is exactly why it is now the top item.

### 2. The published SPA: what is live

**`automations/expense-reconciliation/docs/PROMPT-STATUS.md` is the ledger.**
One row per Lovable prompt, applied or not, with the evidence. Audited
2026-08-24 by driving the app. Re-run
`%TEMP%/claude/recon-probe/prompt_ledger.py` and update that file whenever
the owner publishes; a prompt sitting in `docs/` says nothing about whether
it was ever pasted, and guessing from the repo is what made coordination bad
enough for the owner to call it out.

**Every prompt is applied as of 2026-08-25, verified by driving the app.**
The three that were outstanding all landed: `/months` renders a real list
(1 table, 6 rows, 6 `/expenses/{id}` links, real month labels), the stale
"Accepted senders" editor is gone and "People we recognise" replaced it, and
Status cells render the backend `status_label` with the refusals strip beside
them. Backlog items 31 and 32 are CLOSED.

That last one matters for anything you ship next: because the SPA renders
`status_label` from the backend, a NEW intake status shows correct prose
with no SPA change. The `duplicate` status shipped the same day proved it.

**Two audit traps that made applied prompts read as missing**, on top of the
two the 2026-08-24 audit hit. `prompt_ledger.py` scores `[x]` on a FOUND
needle, so the row "STALE editor must be GONE" passes as `[ ]` — an inverted
check inside a checklist of positive ones. And its refusals needle is
`"refus"` while the shipped copy says **"turned away"**, so a live feature
reported as absent. Take needles from what the app SAYS, not from the prompt
draft. Both are recorded in `docs/PROMPT-STATUS.md`.

**Two audit traps, both of which produced a wrong answer first.** A loose
regex matched a Cards help line and reported the known-senders editor as
present; and per-row intake actions are an icon-only
`button[aria-label="Actions"]` menu, so enumerating button TEXT reports no
actions on any row. Match exact strings, and open the menu.

### 3. Whatever the next feedback wave surfaces

The 2026-08-21 wave is fully worked through. Items 16, 17, 3, 4, 5, 8 in the
backlog are small and unranked; none of them is urgent.

## Owner-side, still open (hand the paths when asked, do not chase)

**No unapplied Lovable prompts.** All of `docs/` is applied; re-run
`%TEMP%/claude/recon-probe/prompt_ledger.py` after any publish and update
`automations/expense-reconciliation/docs/PROMPT-STATUS.md`, reading its two
known-stale rows per the traps above.

`intake.known_senders` is still EMPTY on production. Until an operator lists
`dirk_.neumann@icloud.com`, every body-only forward from Dirk's personal
address holds and he gets no ack — that address is outside the tenant, and
`is_known_sender` recognises `@brisken.com` plus the list, nothing else. The
Settings editor for it now exists ("People we recognise"), so this is a UI
edit, no deploy. A session sandboxed against state-changing calls to the live
app cannot do it; hand it over.

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
uncommitted edits to the same files; that cost two rebuilds on 2026-08-24
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
