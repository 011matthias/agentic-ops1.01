---
project: brisken
workstream: p1-expense-reconciliation
kind: loop-runbook
state: active
updated: 2026-09-07
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

**The 2026-09-06 owner program is COMPLETE (2026-09-07).** All four rounds
merged in order and deployed: R1 person-on-card + private-expense
suggestion (items 35/40/41, #686, v103), R2 auto-materialization (item 39,
#687, v104, flag `EXPENSE_RECON_AUTO_MATERIALIZE` ON since the watched
2026-09-07 flip, #695) with item 42's refusals split ahead of it (#683), R3 the trip
entity + declared batch type + travel-alias routing (#688, v105), R4
cross-batch settlement + the trip report (item 38's deep half, #685, v106:
the `receipt_claims` registry arbitrates one-receipt-one-charge across
batches, a month's pool spans overlapping trips, provenance ships as
`settled_by` both ways, and a trip's report sections per person). R4's
live drill on v106 proved the settlement end to end (a TEST trip receipt
settled a TEST month charge, a second month could not re-settle it, the
workbench rendered the settled row) and returned the live state to zero
TEST fixtures.

**What ranks next, in order:**

1. **Owner-side applies: DONE 2026-09-07.** All four Lovable prompts
   pasted, published and bundle-verified the same day (PR #698; the
   settings chunk round-trips `person` and `travel_alias`, so both
   erasure gates cleared). The travel alias is SET to `travel`
   (travel@expenses.brisken.com) and the full TEST- alias drill PASSED
   live: mailed a TEST- receipt to the alias via the MX, it rested as
   `pool_kind: travel` without minting a month (flag ON), the trip
   suggestion named the one TEST- trip, join-trip materialized the trip
   batch with the vision-read receipt (23.50 EUR taxi), batch delete
   pooled the mail back, fixtures removed to zero (0 trips, 3 months,
   pool 0). Person data entry is unblocked; the remaining owner-side
   item is DATA (see the collect list below).
   (The R2 flip is DONE: dismissals landed and
   `EXPENSE_RECON_AUTO_MATERIALIZE=1` went live 2026-09-07, #695.)
2. **The previously-ranked items resume:** 27 (wrong DAY in the right
   month), 23's remaining Zoho string layers (gated on the GL-codes
   call), 24, the overlay-route round.

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

Baselines: suite **1496 passed / 2 skipped** (post-#685, 2026-09-07),
calibrate exit 0, ruff (E9,F) clean on the diff. App root
`workspace/clients/brisken/automations/expense-reconciliation`. Live app is
**v106** (the R4 deploy, 2026-09-07); live state after the R4 drill
cleanup: zero month batches, zero trips.

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
printed month is confidently known.

**R2 status (2026-09-07): LIVE, flag ON.** Item 42 merged as PR #683, item 39
as PR #687; `EXPENSE_RECON_AUTO_MATERIALIZE=1` set on Fly 2026-09-07 with the
owner watching. The watched backfill minted July, August and September 2026
(`created_by: intake`, 0 failures), claimed all 24 pooled mails, and the
stranded sweep re-pooled 10 legacy archives: the owner triaged them same
session (5 TEST- drills dismissed; 5 real mails claimed into August by their
receipt-read dates — all were `receipt_month_source == "receipt"`). Pool is 0.
Arrival half stays known-senders-only; residuals live in backlog item 43.
Rollback order: flag OFF first, then delete the month (mail re-pools).

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

**Four unapplied Lovable prompts** (the R1/R2/R3/R4 rows in
`PROMPT-STATUS.md`), handed to the owner as pasteable text 2026-09-07.
Re-run `%TEMP%/claude/recon-probe/prompt_ledger.py` after any publish and
update `automations/expense-reconciliation/docs/PROMPT-STATUS.md`, reading
its two known-stale rows per the traps above.

Card registry: entities for 0113/6013/9693/8311 and the 0340 card itself were
entered 2026-09-06 (item 26, done via authorized operator-API write). Still
open, owner/Criss-side: a PERSON for every card (2838/0113/6013/9693/8311/
0340, plus 3645 and plastic-1672) — collect and enter any time (the entry
gate CLEARED 2026-09-07: the R1 prompt is verified in the published SPA, so
saves round-trip person values); entities for 0340/3645/1672; whether
Criss's recon ever covers the Consulting entity's cards (Wise 1160 / Chase
1176 — gates provisioning a third entity); the
GL-codes-vs-categories call (gates only the post-program item 23 layers
2-4). The travel alias is SET (`travel`, drill passed 2026-09-07), the
Hostinger dismissals and the R2 flip are DONE (2026-09-07, #695).

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
