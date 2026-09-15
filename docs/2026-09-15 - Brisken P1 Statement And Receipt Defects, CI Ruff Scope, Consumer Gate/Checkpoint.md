# Checkpoint: Brisken P1 Statement And Receipt Defects, CI Ruff Scope, Consumer Gate

**Date:** 2026-09-15
**Status:** Items 51 and 52 closed on the backend and live on Fly v128; item 52's SPA half written and waiting on an owner paste. CI now lints the recon module. The deploy-consumer gate no longer closes on a command that observed nothing.

---

## Summary

Took the two live client-facing defects from the p1 backlog. Item 51 (a
statement parsing to zero rows reporting success) was a straightforward refusal
that turned out to be worse than recorded: the month did not merely stay
unchanged, it graduated to the reconciliation workbench holding zero charges.
Item 52 (Criss: "Recibo nao estar abrindo") turned out not to be a backend
defect at all; driving the live SPA refuted the recorded lead and found a dead
**View receipt** button, while a real flag defect sat underneath it. Then closed
the two system items the session brief flagged: CI's ruff scope, and a gate that
was closing on the presence of a browser command rather than on an observation.

---

## What Was Done This Session

### Item 51 — a statement that holds no charge is refused (PR #859)

1. Reproduced through the real route: `200 {"ok": true}`, job `done`,
   `statements[{"n_rows": 0, "n_new": 0}]` — and `summary.has_statement: True`,
   which the backlog had not recorded. `rematch_month` stamps that on commit, so
   an empty file turned an open month into a reconciliation with zero charges.
   On screen that is what a month whose statement reconciled looks like. That
   settled refuse-vs-advise, which the item had left open.
2. `execute_statement_attach` refuses before the fold. Nothing written: no
   charge, no `statements[]` entry, no `statement_anchors` entry, no graduation.
   The reason rides the job's existing `error` status, the channel the re-read
   already refuses on, so the SPA needs no new field.
3. Keyed on `n_rows`, never `n_new`. Zero NEW charges is the same file arriving
   twice, which the fold exists to absorb.
4. Closed the same shape on `reread_statements`, where it is worse: the re-read
   REPLACES the charge set, so a stored file that recorded rows and now reads
   none would take a live month's charges away silently. Exempt when the entry
   was already recorded `n_rows: 0`, so no legacy month is wedged.

### Item 52 — diagnosed to the SPA; the flag underneath it fixed (PR #860)

1. The recorded lead was that two flags disagreed on one row and the SPA gated
   its viewer on the wrong one. Both halves are false. The published bundle
   references **neither** flag: zero hits across the index and every chunk it
   loads.
2. Drove the live app. On `/expenses/{batchId}` every row's **View receipt**
   button is enabled, carries a React click handler, and does nothing. With
   `window.fetch`, `window.open`, `URL.createObjectURL` and anchor clicks all
   instrumented, a click produced no request, no dialog, no iframe, no tab, no
   error. 31 rows on August, 32 on September, so the read-only banner a
   statement month wears is not it either. The workbench is worse: its
   UNMATCHED RECEIPTS Document column is plain text with no handler at all.
3. Wrote `docs/lovable-view-receipt-prompt.md` and registered it in
   PROMPT-STATUS as not applied.
4. The defect underneath: the same field computed twice. `build_expense_view`
   resolved `receipt_image_available` against disk and was right;
   `_receipt_view`, which builds the RUN payload, resolved it from the SHAPE of
   the document id. Every mail- or drop-arrived receipt is `NNNN__name.pdf` and
   matches none of the id patterns, so the run payload said `false` for all 17
   unmatched receipts of live August while the endpoint served each of them 200.
   `service.receipt_image_file` is now the one resolver.

### System items from the session brief

5. **CI ruff scope (PR #862).** The recon module had never been in CI's lint
   scope, which is how twelve findings accumulated before PR #856 cleared them
   by hand. Added `src` and `tests` to the `hooks` job's ruff command. Timed
   after the parallel round closed so no in-flight branch reddens for findings
   its author did not introduce.
6. **Consumer gate (PR #863).** It closed on ANY browser call, `agent-browser
   open <url>` and `browser_navigate` included. Closing now requires a command
   that reads page state back, in the foreground, not reporting failure.

---

## Key Decisions Made

### Refuse the empty statement rather than advise on it
- **Choice:** hard refusal on the attach, on the job's `error` status.
- **Rationale:** the item left refuse-vs-advise open. The reproduction closed
  it: the month graduates, so "nothing happened" was never the outcome and an
  advisory on a month that already looks reconciled is not enough.

### Extend item 51's guard to the re-read, which the item did not ask for
- **Choice:** same guard on `reread_statements`, exempting an already-zero entry.
- **Rationale:** `reread_statements` already documents deny-by-default for a
  missing file and an unresolvable column map. A file that resolves and yields
  nothing is the same family and loses charges rather than adding none, so this
  is a gap in an existing guard, not a new feature. Recorded as a deliberate
  scope call in the register.

### One resolver for "can this receipt be opened", not two
- **Choice:** `receipt_image_file`, gated exactly as the image endpoint gates
  itself; `_receipt_view` takes `work_dir` and `expense_mode` as **required**
  keyword arguments.
- **Rationale:** an id-shape test cannot answer this question at all — what the
  endpoint serves depends on what is on disk, and the two drift the moment a
  new road into a month is added, which is exactly what the mail intake and the
  receipts drop were. Required arguments mean a future caller cannot silently
  report every receipt unopenable, which is the shape the defect had.

### Rewrite two tests rather than work around them
- **Choice:** `test_a_workbook_that_held_no_rows_is_annotated_with_nothing` and
  three gate tests pinned behaviour this session deliberately changed.
- **Rationale:** each used the loose behaviour as a vehicle for a property that
  still holds elsewhere (the empty anchor map survives for a PDF statement; a
  browser drive still closes the gate, just an observing one). Rewriting keeps
  the property and drops the dead scenario.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/web/service.py` | edit | `statement_read_nothing` + two refusals; `receipt_image_file` + the `_receipt_view` rewire |
| `automations/expense-reconciliation/tests/test_statement_zero_rows.py` | new | 7 tests, all through the routes |
| `automations/expense-reconciliation/tests/test_receipt_image_available.py` | new | 5 tests, four through the routes |
| `automations/expense-reconciliation/tests/test_statement_append.py` | edit | rewrote the test whose scenario the refusal makes unreachable |
| `automations/expense-reconciliation/docs/api-contract.md` | edit | two sections: the zero-row refusal, the disk-resolved flag |
| `automations/expense-reconciliation/docs/lovable-view-receipt-prompt.md` | new | the SPA half of item 52 |
| `automations/expense-reconciliation/docs/PROMPT-STATUS.md` | edit | registered it as not applied |
| `status/p1-improvement-backlog.md` | edit | item 51 closed, item 52 diagnosed, Shipped rows 44 and 45 |
| `status/p1-expense-reconciliation.md` | edit | two element rows |
| `.github/workflows/ci.yml` | edit | ruff over the recon module |
| `.claude/hooks/deploy-consumer-gate.py` | edit | observe-vs-navigate, foreground, non-failing |
| `tools/tests/test_deploy_consumer_gate.py` | edit | 3 rewritten, 13 added |
| `.claude/rules/rule_behaviors.md` | edit | consumer-drive sub-clause records the tightening |

---

## Current Status

Five PRs merged (#859, #860, #861, #862, #863), all CI-green. Fly **v128**
carries both backend fixes and both were verified against the deployed API, not
the merge: the August run payload read 0 of 17 receipts available before the
deploy and 17 of 17 after, with the endpoint serving all 17 throughout; and an
empty CSV attached to a throwaway `TEST-` month came back a job `error` with the
new message and left the month untouched (month deleted afterwards). Criss's
real months were only read.

brisken platform: unknown plan, `~?/?` ops/mo, last assessed `?` — the
`infrastructure.yaml` platform block is still unfilled, so `/ops-audit brisken`
would have nothing to compare against.

The comms log is 7 days stale.

Backlog items still open from the 48-54 band: 48 (US substantiation, round 2
unscheduled), 49 (the evidence record, its four standalone defects carved out as
65-68), 50 (SPA half), 52 (SPA half), 53 (coverage prompt unapplied), 54 (OCR
date misreads).

---

## Next Steps

1. Paste `docs/lovable-view-receipt-prompt.md` (owner). Until then Criss still
   cannot open a receipt, which is the thing she actually reported.
2. Paste `docs/lovable-failure-probe-prompt.md` — item 50 stays open without it.
3. Paste `docs/lovable-cost-centers-prompt.md`, sections 1 and 2 first. Both
   settings maps are whole-map replace; nobody types a cost center until a
   bundle grep proves the round-trip.
4. Item 54 (OCR date misreads silently prevent a match) is the strongest
   remaining code item in the band: it has two named live instances and closing
   the Crossmedia one closes July's entire EUR gap.
5. The July receipts (19 PDFs in the primary clone's
   `.scratch/recon-july/criss-receipts/`) and the dateless French bank receipt
   both need an owner go — they write into Criss's live July month.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`, items 48-54
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`

### Open Questions
- Does the **View receipt** button's handler exist and fail silently, or is the
  viewer component missing entirely? The React props show a composed handler
  (Radix tooltip plus the app's), so something is wired; what it does could not
  be read out of the minified bundle. Whoever applies the Lovable prompt will
  see the source and can answer it in one look.
- The workbench has no receipt-opening affordance at all. Is that deliberate
  (the reviewer is meant to work from the grid) or an unbuilt half? The prompt
  asks for both surfaces on the assumption it is the latter.

### Working Notes

**The SPA bundle moves under you.** Asset hashes changed twice inside ten
minutes (`index-BpHLd6SH` → `index-BLjtUgLv`, chunk-i18n 220,943 → 225,456
bytes). Fetch `index.html` and every asset it names in ONE pass; a second
request can 404 on a hash that was live a minute earlier.

**Three instrument slips, all caught, worth carrying:**
- The accessibility snapshot reports `[disabled]` on these buttons from the
  Tailwind `disabled:` class names in the class attribute. The DOM says
  `disabled === false`. Read `b.disabled`, not the a11y tree.
- `ruff check --show-settings | head -5` truncates `linter.rules.enabled` and
  makes it look as though only `E902` is active. The differential (inject a real
  `F401`, watch the command fail) is the only trustworthy check of lint scope.
- `fetch('/api/...')` from inside the SPA hits the Lovable host and 404s. The
  API base is `https://brisken-expense-recon.fly.dev`; the session token is
  `localStorage['erc-token']`.

**Refuted, do not re-run:** the read-only-banner theory for the dead button. A
statement month shows "Expenses are read-only", but the button is equally dead
on September, which has no statement.

**Live shape of the estate (read 2026-09-15):** 6 expense batches; only August
`074a7b8905d7` and July `50622baec444` carry statements; no month holds a
`statements[]` entry with `n_rows: 0`, which is what the re-read exemption was
measured against.

### Reference Materials
- Live API `https://brisken-expense-recon.fly.dev`, operator code in the local
  vault (`Brisken recon operator code matthias`)
- SPA `https://expenses.brisken.com` (Lovable, redirects from
  `brisken-reconcile-dash.lovable.app`)

---

## How to Continue

Cut a worktree off `origin/main`. Item 54 needs no owner input and has its
evidence already recorded. Everything else in the 48-54 band is owner-gated or
waiting on a paste. `regress_check.py` needs `C:/` paths for `--test` and
`--file`; heredocs die on Python triple-quoted blocks, so write scripts with the
Write tool and run the file.

---

## Strategic Feedback

### What Worked Well This Session

- **Reading the record before trusting the note.** Item 52's recorded lead was
  a week old and confidently wrong in both halves. Four cheap live reads (the
  bundle grep, the two payloads, the endpoint sweep) replaced it with the actual
  cause. The brief's own warning — an artifact is evidence about the moment it
  was taken — paid for itself inside twenty minutes.
- **Regressing every wiring point.** Six mutations across the session, each one
  green → red → green. Two of them reddened tests I would have assumed were
  load-bearing and one reddened four EXISTING tests, which is how the batch-side
  refactor got proven wired rather than asserted.
- **Positive controls on the negatives.** "Clicking the button fires no
  request" is a claim that a blind instrument produces for free. Logging an
  unrelated `/api/settings` call through the same patched `fetch` is what made
  the negative mean something.

### Suggestions

- The gate hardening shipped today fixes "a command that observed nothing". The
  sibling gap is still open: an observing drive closes the marker even when the
  assertion was on an unchanged field. The gate cannot read intent, but it could
  require the drive to come AFTER the deploy's own marker by more than a trivial
  interval, or carry the deployed label into `CONSUMER_CLEARED` so the confirm
  line names what was supposed to change. Cheap, and it keeps the advisory from
  reading as proof.

### System Health

- The primary clone `C:/Users/neuma_p1qrsic/Repo/agentic-ops1` was 57 commits
  behind at session start and is the checkout every hook in this session
  actually ran from. So today's gate hardening does not take effect until that
  clone is pulled — a gate merged into `main` and a gate running are two
  different things, which is the same class of gap the gate itself exists to
  close.
- **Autonomy score: 0 human interventions** — fully autonomous session.
