---
project: brisken
workstream: p1-expense-reconciliation
kind: loop-runbook
state: active
updated: 2026-09-06
---

# Brisken expense tool: improvement loop, next round (paste into a fresh chat)

Load the Brisken expense-reconciliation project (p1). We are continuing the
test-and-fix loop on the receipt-first pipeline until the tool is genuinely
usable for Brisken. Read this whole brief before touching anything, then read
`p1-improvement-backlog.md` beside it — that file, not this one, is the list of
what to do next.

## Where things stand (2026-08-26)

**Backlog item 29 is COMPLETE.** The whole chain is shipped and deployed
(Fly **v98**): stable transaction identity (2a), `rematch_month` + the
judgment cache (2b-1), the extraction baseline (2b-1b), the month staying
open (2b-2a), the fold (2b-2b-1), the `statements[]` surface (2b-2b-2,
PR #636), and the coverage surface (PR 3, PR #644).

A statement is now an input stream, not a closing event. `POST
.../statement` appends by identity and is repeatable per card; each upload is
recorded in `statements[]` on both review payloads; the sheet writeback is
anchored PER UPLOAD (`statement_anchors`), because one charge occupies a row
in every file that prints it and a field on the charge could only name one of
them. Two hazards are answered by surfacing, never deduping: an `advisory`
fires when one card is typed against two account ids, or when an upload lands
100% new over a period the same account already covers. `rematch_month`
refuses any commit that would drop a charge the month gained meanwhile.

**PR 3 shipped 2026-08-26 (#644).** `coverage[]` on both review payloads
answers which cards a month has loaded, from which uploads, over what span,
and how far each has got, carrying the run summary's own four bucket counts
and unreconciled money PER CARD. Registry cards with nothing loaded get a row
on purpose. `charge_states` is now the one place a charge's effective bucket
is decided, so the grid and the workbench cannot report a month at two
different stages of done. The reconciliation document gained a coverage table
and per-card sections, grouped on the new `rows[].coverage_key`.

Verified live on the January month: three card rows (2838 / 3645 / 0340)
summing 40+31+9 = 80 charges and 18,092.08 + 1,277.53 + 859.07 =
USD 20,228.68, matching the summary exactly; the downloaded PDF carries the
table and three sections; the SPA renders both month views with no errors.

**The SPA half is outstanding.** `docs/lovable-coverage-prompt.md` carries the
statements panel, the per-statement `?file=` download selector AND the
coverage panel; until the owner pastes it, a month holding two workbooks still
offers one download button and the per-card split exists only in the API and
the PDF. That is the one open thread from this round.

**What is next is no longer a decision: the 2026-09-06 owner program leads.**
On 2026-09-06 the owner directed four product changes, captured with their
rulings as backlog items 38 (company months vs TRIPS, declared at entry,
both reconcile), 39 (mail materializes the month itself — supersedes the
2026-08-24 "pre-creating months intrudes" ruling below), 40 (person
attribution through the CARD: registry entries gain a person, the existing
card chain resolves it, sender identity stays provenance only), and 41 (a
payment method that resolves to no registered card is SUGGESTED as a
private expense with `reimburse_to` a person — the one bounded exception to
40's card-only rule). Round order is in item 38: person-on-card + the
private-expense suggestion first (one round), auto-materialization second,
the trip entity third, cross-batch reconciliation + trip report last. The
previously-ranked items (27, 23's Zoho string sweep, 24, the overlay-route
round) queue behind the program unless one of them rides along cheaply.

**Execution model (2026-09-06): the four rounds run as four parallel chats,
one worktree + branch + PR each** (`client/brisken/r1-person-private-expense`,
`r2-auto-materialize`, `r3-trips`, `r4-cross-batch-settlement`). MERGE ORDER
IS R1 → R2 → R3 → R4: rebase onto latest origin/main immediately before
merge and rerun the suite if main moved; the later-merging round owns
conflict resolution on the shared surfaces (service.py, app.py,
api-contract.md, test_view_contract.py). Wait-points: R3's roster-mismatch
commit and its merge wait for R1; R4's trip-spanning half (R4b) starts only
after R3 merges (its settlement-registry half R4a builds immediately).
Deploys serialize on merge order, each from a fresh detached origin/main
worktree. Ride-alongs are assigned: item 35's canonical grouping is R1's
first commit; item 42 (refusals split) is a standalone micro-PR at the head
of the R2 chat.

**Backlog item 30 is fully shipped and deployed** (PRs #607, #608, #609),
along with the out-of-Lovable half of the "Arriving" bug:

- **Known senders.** Settings `intake.known_senders` lists outside addresses
  that count as ours. `graph_notify.send_mail` takes an explicit per-call
  `allow_external` and asserts the structural recipient guard BEFORE
  consulting it. The production list now carries Dirk's
  `dirk_.neumann@icloud.com` (verified 2026-09-06; acks work).
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

Baselines: suite **1400 passed / 2 skipped** (PR #657, 2026-08-29), calibrate
exit 0, ruff (E9,F) clean on the diff. App root
`workspace/clients/brisken/automations/expense-reconciliation`. Live app is
the #657 release (v101+; nothing has shipped in September).

**Worktrees were consolidated on 2026-08-25.** There is no longer an
`agentic-ops1-recon` worktree: the repo is the primary clone
`C:\Users\neuma_p1qrsic\Repo\agentic-ops1` (on `main`, clean) plus
`agentic-ops1-deploy` (detached at origin/main, deploys only). Cut a fresh
worktree for the round rather than expecting an old one to exist.

**Live state (2026-09-06 audit):** ZERO month batches exist (all six deleted
after the demo test), **23 pooled** (12 Aug / 5 Jul / 6 Sep) plus **7 stranded
`batch_deleted` archives**, `n_held` 0. Three of the pooled are still the SAME
Hostinger invoice (H_46243348, pre-dedupe arrivals); two must be dismissed
before any month materializes or their intake rows will read as processed.
`n_refused` 55 in the 7-day window, ALL `*@flyio.net` relay probes; item 42
splits the counter. `intake.known_senders` now lists Dirk's iCloud (acks
work). Card registry after the 2026-09-06 round-0 data entry: 6 cards, five
with entities (0113 Corporate Services; 6013/9693/8311 Cloud Services; 2838
legacy), 0340 created with entity blank; persons not yet enterable (item 40
builds the field first).

Pooled mail joins automatically the moment its month batch exists.
`create_expense_batch` refuses an empty batch, so opening a month needs at
least one uploaded receipt — do NOT seed a fabricated one into a live month.

**Owner ruling 2026-08-24: pre-creating months INTRUDES — SUPERSEDED
2026-09-06 by backlog item 39.** The owner now directs the opposite: mailed
receipts become expenses on their own, auto-creating the month batch when the
printed month is confidently known. Until item 39's round DEPLOYS, the
2026-08-24 behavior is still what runs live (the pool waits); do not hand-create
months in the interim.

**R2 status (2026-09-06): built, not yet live.** Item 42 merged as PR #683;
item 39 is PR #687 (this branch) — flag `EXPENSE_RECON_AUTO_MATERIALIZE`
default OFF, arrival half known-senders-only, stranded sweep only under
`materialize: true` and last, residuals in backlog item 43. Live behavior is
unchanged until the staged flip (Hostinger dismissals gate it).

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

Nothing remains in item 29. Every part of the plan file shipped, and the
sign-contradiction interaction 2a pinned is answered the way 2a implied: two
uploads that disagree really are two rows, and 2b-2b-2's `advisory` says so
out loud rather than deduping a contradiction into whichever file arrived
first.

**The one deliberate leftover:** the four expense-edit overlay routes are
still closed, each pinned by a test. Not because re-applying an edit is
dangerous (2b-1b refuted that; the overlay is idempotent by construction) but
because opening a reviewer-facing edit surface is only worth doing once the
edits it takes are reversible and honestly attributed. 2b-1b restored the
baseline that makes that possible, so reopening them is now a real round with
the re-match wiring that has to follow an edit.

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

Card registry: entities for 0113/6013/9693/8311 and the 0340 card itself were
entered 2026-09-06 (item 26, done via authorized operator-API write). Still
open, owner/Criss-side: a PERSON for every card (2838/0113/6013/9693/8311/
0340, plus 3645 and plastic-1672) — collect now, enterable only after item
40's round deploys the field AND its Lovable prompt is verified in the
published SPA (the settings cards map is whole-map replace; a stale SPA save
would silently erase person values); entities for 0340/3645/1672; whether
Criss's recon ever covers the Consulting entity's cards (Wise 1160 / Chase
1176 — gates provisioning a third entity); the travel alias local-part
(gates R3's deploy); the GL-codes-vs-categories call (gates only the
post-program item 23 layers 2-4). Two dismissals of the duplicate Hostinger
pool copies gate the R2 flip.

Curation, operator-side, nothing to build: the 103 learned category rows are
all unvalidated (the item-13 surface exists, unused); the merchant registry
carries the MEGA CENTER/CENTRE and Fenix/Ki-Massa dup pairs and the
construction-materials-as-Travel mislabel (Merchants editor edits).

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
