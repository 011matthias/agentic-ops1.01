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
usable for Brisken. Read this whole brief before touching anything, then
read `p1-improvement-backlog.md` beside it — that file, not this one, is the
list of what to do next.

## Start here (2026-08-24)

**The living-month plan is in flight (backlog item 29).** PR 1 (the mail
pool) has shipped and is deployed (#599 + #601, Fly v87): emailed receipts now file by the month printed on the
receipt and rest in a pool until that month exists, instead of landing in
whatever batch happened to be open. Read backlog item 29 before picking
anything else up; PR 2 (stable content-derived transaction ids, append-able
statements, the month staying open, incremental re-match) is the next round
and its prerequisite is the identity change, not the UI.

## Start here (2026-08-23)

The 2026-08-21 feedback wave is CLOSED. Every owner question that gated it
has been answered and every round has shipped and deployed. Two directives
landed on 2026-08-23 and reshaped what the tool produces:

1. **There is no target application any more.** The month's output is a
   document a person reads and an auditor accepts, not a file some system
   imports. Both report PDFs are live: `GET /runs/{id}/expense-report.pdf`
   (listing built from the export's own rows, then every receipt behind a
   caption naming the expense it proves) and
   `GET /runs/{id}/reconciliation-report.pdf` (exceptions FIRST, then every
   charge with its receipt and status, then the pages). The CSV and the XLSX
   survive as demoted sidecars.
2. **Anyone can email a receipt in.** The intake's `@brisken.com` sender
   allowlist is deleted (PR #587, Fly v83). The recipient rule and the spend
   guards are what hold the door now.

**Backlog 25 (the 2023 year on an April receipt) is CLOSED** — PR #590,
2026-08-24. It was eleven rows, not one. The stored readings already held
those years, so the model was wrong at the source, two ways: a card slip
printing YY-MM-DD read day-first, and a two-digit `26` resolved to a year
that is not 2026. The prompt was tightened and measured (6 of 11 fixed, none
of the 25 good readings made worse), and because five stay wrong the
load-bearing half is a deterministic guard: a date outside the batch's month
now reaches the reviewer as `check` / `date_outside_period` and the report
PDF names the expense numbers it distrusts. Nothing is auto-corrected, and a
date the reviewer typed is believed.

**Pick the top open item off the backlog.** Item 27 is the residue left
behind (the guard catches a wrong month, not a wrong day inside the right
month) and is deliberately parked until Criss reports a day error. Item 26 is
owner-side data entry. So the productive next moves are the untested material
and whatever Criss's next month surfaces.

**Do not re-ask the owner about:** the export target (there is none), Zoho
(no ties, deleted), mixed-entity export (one file, entity as a column),
cash/personal tenders (per-month assignments, not cards), or the January
credit notice (booked, my call).

**Owner-side, still open** (hand the paths when asked, do not chase):
- Lovable prompts unapplied, all backends live:
  `docs/lovable-month-report-prompt.md` (the only one that changes what
  Criss can DO — it puts the PDF buttons on screen),
  `docs/lovable-re-ingest-prompt.md`, `docs/lovable-issue-codes-prompt.md`,
  `docs/lovable-ready-tile-prompt.md`,
  `docs/lovable-open-intake-prompt.md` (only if the "Accepted senders"
  editor was ever built), plus the older wave prompts listed further down.
  All under
  `workspace/clients/brisken/automations/expense-reconciliation/docs/`
  in the `agentic-ops1-recon` worktree.
- Card registry data entry: entities on cards 0113/6013/9693/8311 and the
  missing 0340 card — that is backlog item 26 and the live MISSING ENTITY
  count, not a defect in the resolution chain.

**Live findings worth the owner's attention, already surfaced:** the January
statement run reconciles 0 of 80 charges, USD 20,228.68 unreconciled, 78
charges with no receipt at all. That is the data, not a bug.

Suite baseline: **1206 passed / 2 skipped**; `calibrate --config
examples/run.example.json` green. Fly app at **v83**.

## Reading the app without anyone's help

Never ask the owner to check a screen or read a value. The operator code is
in the local vault (`Brisken recon operator code matthias`) and the probe
helpers read it from there, so it never enters the transcript:

- `%TEMP%/claude/recon-probe/api.py` - `api.get("/api/...")` logs in and
  returns parsed JSON.
- `%TEMP%/claude/recon-probe/dom_probe.py` - Playwright against the live
  SPA. Bundled chromium is absent on this machine; launch with
  `p.chromium.launch(channel="chrome")`.
- Endpoint tests need a REAL batch or run id; `/api/operator/state` lists
  them (`operator_runs`, `processing`).

## How the wave got here (2026-08-21, the 8-PR program)

The operator walked the whole tool on 2026-08-21 and left 14 in-app notes
(the first full wave since feedback capture went global). The full design
lives in the approved plan `~/.claude/plans/looks-like-there-is-keen-aurora.md`
and in backlog items 10-17; the user picked CARDS-FIRST sequencing. Three
rounds are SHIPPED:

- **Cards R1 (PR #555):** `settings["cards"]` registry (multi-digit card
  identity: the statement marker "2838" and the plastic last-4 "1672" are
  the SAME card), `GET /api/cards`, read-time composition over the legacy
  `card_entities`/`card_accounts` maps + `/data` presets (no write
  migration), one resolver in `src/expense_recon/cards.py`.
- **Cards R2 (PR #556):** Zoho demoted to an optional card attribute.
  Per-card Zoho-OPTIONAL setup advisories (`setting: "cards"`); journal
  credit + expense Paid-Through resolve via the CONSERVATIVE
  `cards.resolve_account_map` (bare-digit keys match labels; label-shaped
  keys exact-only; ANY ambiguity keeps the visible placeholder — two
  adversarial-review rounds executed wrong-money scenarios and every one
  is pinned as a test); `merchants_inert` on GET /api/settings.

- **Cards R3 (PR #559, the headline):** entity-less batches — the
  legal-entity ask at creation is GONE; entity resolves per receipt via
  ONE chain (override -> hint assignment -> card registry with ambiguity
  refused -> stamped value -> `needs_entity` review state) shared by
  grid, export, AND statement graduation (the attach bakes chain
  entities into the matcher pool — pre-fix an assigned entity-less
  batch reconciled 0 silently). Rows carry `card`/`entity_source`/
  `payment_hint`; `card_review` strip server-grouped; `POST
  /api/expense-batches/{id}/cards` (exact hint assignments, `learn:
  true` persists tokens: single-digit-run rule, multi-run hints learn
  as exact aliases, generic tenders NEVER learned — compound + DE
  vocabulary covered); `POST .../refresh-master-data` (audited,
  preserves assignment targets, reports row impact). Export ruling
  pinned: `(entity - assign)` placeholder, never block, re-export folds
  later assignments in. 3-lens adversarial review executed; restore +
  attach final-write now under the batch lock. Review residue logged in
  the backlog item-10 tail.

- **Intake quick-wins (PR #561, 2026-08-21):** delivered-files in mail
  meta (+ legacy derive from parts/), Month column truth (batch_label
  for every routed row, held says held, deleted months say so instead
  of per-expense misattribution), delete-month behind a typed confirm
  phrase (cascade under the batch lock, jobs purged, inbound metas
  stamped batch_deleted — archives NEVER deleted, custody holds;
  response: next_open_batch + learned_memory kept). 3-lens adversarial
  review pre-commit; the async-handler event-loop freeze it caught is
  fixed here, the pre-existing twin is backlog item 18. Lovable half:
  `docs/lovable-intake-quickwins-prompt.md`.

- **Body-only mail (PR #563, 2026-08-21):** GET /api/inbound/{archive}/
  body (sanitized text, never the raw archive), POST .../render-ingest
  (body->PDF through the NORMAL pipeline — vision + quarantine judge it
  like any scanned receipt; byte-deterministic render so retries dedupe,
  transient `rendering` status makes render/dismiss/replay mutually
  exclusive, container ships a full-Latin font for German bodies),
  POST .../dismiss (terminal junk path; held strip can reach zero).
  Replay now rescues stranded body-only mail; interrupted renders
  reconcile to retryable. Lovable half:
  `docs/lovable-body-only-prompt.md`. Leftover design call = backlog
  item 19 (re-ingest for attachment mail after a month delete).

- **Memory validate/adjust (PR #565, 2026-08-21):** PUT/DELETE
  /api/memory/categories (count-preserving; absent zoho_account key
  preserves the learned account), validated_at/by migration
  (race-tolerant on the live store) + bulk validate + ?unvalidated=1,
  reset confirm gate (bare POST = side-effect-free preview). Review
  fixes pinned: value changes CLEAR validation stamps — machine
  re-teaches never wear an old sign-off. NOTE: the SPA Reset button is
  a safe no-op until `docs/lovable-memory-edit-prompt.md` is applied.

- **Language + receipt visibility (PR #567, 2026-08-21):** structured
  missing list, books_as `{account: null, unassigned: true}` sentinel
  (export CSV literal unchanged — grid==export amounts hold),
  reason_label dropped, honest `receipt_image_available` (+ attached
  manual/folder receipts keep availability via the endpoint's glob —
  review carry, pinned) + `source_file` per row. Issue-code prose piece
  parked as backlog item 20. Lovable half:
  `docs/lovable-language-receipt-prompt.md` — item 1 APPLY FIRST (the
  deployed split depiction shows a blank account label on uncategorized
  parts until applied).

**Remaining rounds, in order (design in the plan file; each ships like
steps 5-8 below, with an adversarial review pass before commit):**

1. **Cards R4 (pending owner answers in the backlog):** mixed-entity
   export (per-entity CoaGate), persisted cards migration, intake
   dropdown unification. Backlog item 18 (async endpoints on the batch
   lock, pre-existing freeze class) rides with whichever code round
   comes first.

**Waiting on the OWNER (hand these when asked, do not re-send):** Lovable
prompts `docs/lovable-cards-prompt.md` (Settings > Cards editor),
`docs/lovable-zoho-decoupling-prompt.md` (merchants relabel + inert hint
+ dropdown fixes), `docs/lovable-cards-r3-prompt.md` (optional entity
at creation, row card/entity chips, card-review strip, assign + refresh
actions), `docs/lovable-intake-quickwins-prompt.md` (Files + Month
columns, guarded delete-month dialog, job-poll 404 edge) and
`docs/lovable-body-only-prompt.md` (held-mail actions: view body /
render as PDF / dismiss, `rendering` + `dismissed` statuses) and
`docs/lovable-memory-edit-prompt.md` (Memory page edit/delete/validate +
the REQUIRED reset-confirm flow — the old Reset button is a safe no-op
until applied) and `docs/lovable-language-receipt-prompt.md` (i18n keys,
books_as mapping — its item 1 is APPLY FIRST, missing-image tile, No
receipt state, source_file) — all backends live. After the owner
publishes, DOM-probe the SPA (Lovable merge != live).

**BLOCKER CLEARED (2026-08-22).** The batch page no longer crashes on a
parse issue. The owner published the Lovable fix; the served bundle
(`chunk-expenses._batchId`) renders `file`/`line`/`message` with a
`typeof item === "string"` fallback, and a DOM probe of batch
`ae61e122a505` (which really does carry one object-shaped parse issue)
shows 36 table rows plus the quarantine note, no error boundary, zero
console errors. The recurrence-kill shipped the same day:
`tests/test_view_contract.py` + `docs/api-contract.md` pin the element type
of every list field on BOTH view payloads (backlog item 21, Shipped row
13). Backlog item 18 shipped in the same session (PR #572, deployed Fly
v74): the set-aside-restore and cards endpoints no longer block the event
loop on the batch writer lock, and a static AST guard fails CI on the next
`async def` route that does. A separate hosting bug the same day is
already fixed and live: Lovable's host 404s chunk files whose names begin
with `_` (route-derived `_batchId`/`_runId`/`_intakeId`) plus `new-*`, so
`vite.config.ts` now pins `chunkFileNames: "assets/chunk-[name]-[hash].js"`
— never remove that override, and if pages 404 again, sweep the published
bundle's asset list before suspecting the backend.

**Round 8 was the last wave item, and the owner answered it on 2026-08-22
(one export file with the entity as a column; cash/personal tenders stay
per-month assignments; per-entity Zoho accounts moot). It shipped as PR
#580.** Two rounds shipped before that answer arrived, both found in the live
app rather than in the plan:

- **Count semantics (PR #575, backlog item 22, deployed).** An operator note
  at 13:34 UTC: "it sayz 35 categorized but when you click on open it says
  only 5 categorized". Same batch, same key, two meanings — the list counted
  expenses carrying a category (35 of 36, true), the batch page counted rows
  whose review state was `ready`, so the 30 Cards-R3 rows awaiting an entity
  read as uncategorized and NEEDS CATEGORY claimed 31 when 1 needed a
  category. `service.categorized_counts` is now the single rule behind every
  payload, readiness has its own `n_ready`, and `service.batch_list_summary`
  derives the list screen from the same live overlay the batch page renders
  (the stored summary is frozen at ingest, so an edit never moved it).
  DOM-verified after deploy: the tiles read CATEGORIZED 35 / NEEDS CATEGORY 1.
  The SPA needed no change; optional READY tile in
  `docs/lovable-ready-tile-prompt.md`.
- **Issue codes (PR #576, backlog item 20, deployed).** Upload rejections now
  carry `{code, file, suffix, limit}` in a PARALLEL `issue_details` /
  `upload_issue_details` at all three emission sites; `issues` keeps its
  English prose and its `string[]` type. Pinned in `test_view_contract.py`.
  SPA half `docs/lovable-issue-codes-prompt.md` is optional.

**Then the owner answered everything (2026-08-22 evening / 08-23), and the
wave closed.** Four more rounds shipped and deployed:

- **Zoho layer 1 (PR #579).** "Zoho does not matter anymore, the app should
  have no connection or ties to zoho anymore." The Books API client, the
  journal poster, `zoho-post`, the `coa_source: "api"` live pull and the
  `seed-zoho` importer are deleted (~1,600 lines + 65 tests);
  `tests/test_no_zoho_connection.py` fails on any Zoho host, `ZOHO_*` read,
  or re-added subcommand. Hosted behavior unchanged. Three layers remain,
  scoped in backlog item 23: the `zoho_account` FIELD names (SPA-coordinated),
  the chart gate (keep the mechanism, needs a non-Books chart source), and
  the export artifact — **that one is blocked on one answer: which system the
  CSV gets imported into now.**
- **Cards R4 export half (PR #580).** Owner answers: one file with the entity
  as a column (already true after R3, now pinned); cash/personal tenders stay
  per-month assignments, no code; per-entity Zoho account moot. The find:
  `CoaGate` assumed one entity per run, so every entity-less batch exported
  with NO chart validation. `MultiEntityCoaGate` gates each row against its
  own entity's chart. Left in item 10: persisted cards migration, intake
  dropdown unification.
- **Item 19 re-ingest (PR #582).** `POST /api/inbound/{archive}/re-ingest`
  recovers ONE stranded archive into the open month; only mail stamped
  `batch_deleted` qualifies, no bulk version. SPA half:
  `docs/lovable-re-ingest-prompt.md`.

**Owner-side, still open:** four Lovable prompts unapplied (ready tile, issue
codes, re-ingest, plus the older ones), the card registry needs entities on
0113/6013/9693/8311 and the missing 0340 card (that is what the live
MISSING ENTITY 30 is), and Dirk's rendered credit notice in the January
set-aside strip needs one restore click — my call was to book it.

Suite baseline at that point was 1168 / 2 skipped (now 1190; see the top
of this file); Advisories are SNAPSHOTTED
into each run's summary — existing runs keep old wording by design.

## Where the loop stood (2026-08-19, after round 6)

Round 6 (PR #543, owner-directed): **multi-category vendors + split
depiction.** The merchant book accepts `multi_category: true` (name
still canonicalized, category no longer auto-stamped — flagged vendors
are judged per receipt); every grid row carries `category_variance`
(the "Mixed categories" chip + vendor drill-down data) and `books_as` +
`is_split` (the exact per-account fan-out the export writes, shared
code path, so grid and export cannot disagree). Item 6 rode along: the
extraction prompt now forbids reading the card-terminal bank as the
vendor (cache fingerprint bumped — hosted readings re-read once).
Lovable half handed: `automations/expense-reconciliation/docs/
lovable-variance-books-as-prompt.md`. Owner rulings behind it
(2026-08-19): splits ARE the truth, never collapsed, depict them; and
category variance is surfaced for human judgment, not suppressed.

## Where the loop stood (2026-08-18, after round 5)

Round 5 was a discovery pass over the genuinely untested material, and it
found **no money defects**: set 6 (13 never-tested receipts) summed exact
against every spot-checked source total, and a May fresh-read pair taken
5 days apart kept all 20 rows' amounts/currencies/dates identical with
the quarantine holding 7/7 both times. All residual drift is text-field
(vendor names, tax labels, references) — recorded as backlog items 6/7.
**The proactive loop is paused as of this round:** the next code round
fires on evidence (Criss's real usage, the item-4 watch, or a defect in
her next month), not on a schedule. Set 6 now has a run config +
extraction cache at `.scratch/criss-recon-set6/`.

## Where the loop stood (2026-08-16, after round 4)

Round 4 (PR #538): **set-aside strip + restore.** The batch API now
exposes what the quarantine set aside (`view.set_aside` +
`summary.n_set_aside`, reason as a machine code for PT wording) and
`POST /api/expense-batches/{id}/set-aside/restore` re-adds a file the
tool got wrong, reusing the stored reading (no second AI read). Mid-month
exclusions survive later adds now; the May run derives its strip from the
old warnings. The visible strip in Criss's screen is the OWNER's Lovable
half: prompt at `automations/expense-reconciliation/docs/
lovable-set-aside-prompt.md`, not yet applied. Verify the strip on her
screen once published (Lovable merge != live; DOM probe).

From round 3 and earlier, live on the deployed app (`brisken-expense-recon`):

1. **Non-receipt quarantine (PR #516, Fly v58).** Statement pages and
   report-summary sheets among the uploads are set aside with a visible
   warning instead of becoming phantom expenses. Verified on Criss's real
   May folder: 7 of 7 statement PDFs set aside, 20 of 20 receipts kept.
2. **No more literal "null" accounts (PR #518, Fly v58).**
3. **Same photo, same answer (PR #536).** Once a photo has been read, the
   raw reading is stored keyed on the photo's content hash and reused;
   re-runs are byte-identical by construction and cost nothing. Verified:
   smoke10 run twice, the two CSVs diff-clean, second run made zero
   extraction calls. Hosted app caches at `/data/extraction-cache.sqlite`
   (env `EXPENSE_RECON_EXTRACTION_CACHE`); local runs via
   `llm.extraction_cache_path` in the run config.
4. **CLI runs use the merchant name book (PR #536).** A run config can
   carry `expense.merchants` (inline) or `expense.merchants_path` (bare
   map or a full settings dump), and the exported CSV shows the canonical
   merchant name over the raw OCR spelling. Offline checks now judge the
   same pipeline Criss gets.

**The single source of truth for what to do next is the backlog file
beside this one: `p1-improvement-backlog.md`. As of round 4 no open item
is a code task: item 2 needs an owner/Criss conversation, item 3 is
deliberately unscheduled, item 4 is a watch (re-check the category
columns on your first diff; quiet through three identical runs), item 5
is cosmetic. The productive next moves are running the UNTESTED material
(set 1 May with the strip in place, set 6 different vendors) and
verifying cross-month vendor stability — new defects found there get
appended to the backlog and become the next round. Every new improvement
idea you have during the session gets APPENDED to that backlog file,
never left in chat or scattered into checkpoint notes.**

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
| 1 | `.scratch\criss-recon-may\` | Criss's real May month: 27 files in `receipts\` (20 receipts + 7 Chase statement PDFs), `May2026.xlsx`, `run.local.json`, `run.llm.json` (added 2026-08-13, NO cache — every run is a fresh read). Outputs kept: `expenses-QUARANTINE-20260813.csv` and `expenses.csv` (2026-08-18 fresh read) — the round-5 drift-evidence pair: money identical, text wobbled (backlog items 6/7) |
| 2 | `.scratch\criss-recon-runs\7d2fea33d39a\` | 37 receipts, largest set, `run.local.json` |
| 3 | `.scratch\criss-recon-runs\05d3db59b225\` | 10 receipts + `run.llm.json` (**start here**; config now carries `extraction_cache_path`, and `extraction-cache.sqlite` beside it holds the 10 pinned readings — delete it to force fresh readings). Outputs kept: `expenses-BASELINE.csv` (July 28 code), `expenses-NEW.csv`/`expenses-NEW2.csv` (2026-08-13 pre-fix drift/null evidence), `expenses-QUARANTINE-RUN3.csv` (2026-08-13 post-quarantine), `expenses-R4-PRECACHE.csv` (2026-08-15 pre-cache: the BRL→EUR + tax-drift evidence), `expenses-R5-CACHED1.csv` + `expenses-R6-CACHED2.csv` (2026-08-15 post-cache, byte-identical pair) |
| 4 | `.scratch\test-receipts-ER-00215\` | 37 loose receipt PNGs, no config (same images as set 2) |
| 5 | `.scratch\test-receipts-ER-00215-smoke10\` | 10 PNGs, no config (same images as set 3) |
| 6 | `workspace\clients\brisken\context\expense-reconciliation\receipts\` | 13 real receipts, different vendor mix: Uber email-forwards, MBTA ticket, DB tickets, ZE scans. Run config + live-merchants snapshot + pinned extraction cache + `expenses.csv` (round 5, sums source-verified) at `.scratch\criss-recon-set6\` |

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
modules fail to import. Current suite baseline: **1206 passed, 2 skipped**.

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
- **Extraction drift is CLOSED for re-runs (PR #536).** Pre-fix it was
  worse than "text only": the 2026-08-15 baseline (R4) drifted vs
  2026-08-13 on 8 of 9 rows, including a BRL→EUR currency flip and a
  50.50→50.00 tax drift. With the cache, identical content is answered
  from the store; only NEW photos get a fresh (and still drift-prone
  single) reading, which the merchant name book then canonicalizes.
- **Categorize calls are NOT cached** (backlog item 4, watch): with
  pinned inputs the post-fix back-to-back pair was byte-identical, but
  the same PagBank receipt was filed three ways on three days pre-fix.
  Check the category columns in your first diff.
- **The CLI loads the merchant registry from the run config now**
  (`expense.merchants` / `expense.merchants_path`, PR #536). The smoke10
  config does NOT yet carry one — for a prod-parity run, pull
  `settings["merchants"]` from the live `/api/settings` into a local JSON
  and point `merchants_path` at it.
- **A receipt can legitimately split into two CSV rows** (one per Zoho
  account, same Reference#, sums exact). Whether Criss wants that is
  backlog item 2 — an owner conversation, not code.
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

## Definition of done (scorecard as of 2026-08-15)

The tool is usable when a month of her real receipts produces a CSV she
can post with judgment-level edits only:

- Same receipts run twice → same money: **done, verified**
- No phantom rows from non-receipts: **done, verified on May**
- Honest "(uncategorized)"/"(illegible)" instead of guesses: **done**
- Amounts, currencies, dates match the receipt: **holding, keep checking**
- Same receipts run twice → same VENDOR, so learning compounds: **done for
  re-runs (byte-identical pair verified 2026-08-15); cross-month new
  photos are the registry's job — keep checking on set 1/6 material**
- Criss can SEE what was set aside and why, in her own screen: **backend
  done (round 4: strip data + restore endpoint, verified by test); the
  visible strip waits on the owner applying the Lovable prompt — confirm
  on her screen once published**

## Standing constraints

- Verify behavior, not config. Name the test you ran.
- Never invent a data value; unverified reads TBD.
- No client messages to Criss or Dirk without an explicit ask.
- Never touch her live runs on the Fly volume; pull material down and work
  locally.
