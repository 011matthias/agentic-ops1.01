# Checkpoint: Cost Centers Step 2, Criss's July Receipts, Item 50 Closed

**Date:** 2026-09-11
**Status:** Item 47 step 2 of 6 shipped and pushed; steps 3-6 open. July receipt recovery is at the ingest decision.

---

## Summary

Backlog item 47 step 2 is built: the three things that can carry a cost center
(card, merchant registry entry, trip) and the resolution of that chain onto
every expense row, with the override riding the existing field-override path.
Alongside it, Criss's mailbox came unblocked and turned out to hold the July
receipts the last three sessions were hunting, and backlog item 50 turned out
to be half closed already.

---

## What Was Done This Session

### Cost centers, item 47 step 2 of 6 (two commits, pushed)

1. **The three carriers.** `cards[].default_cost_center` through all five card
   code points (normalize, dataclass, `card_to_dict`, and both halves of the
   config snapshot, so it reaches an existing batch via refresh-master-data
   exactly as `person` does); `merchants[].cost_center` on the registry entry
   and on `MerchantMatch`; and a real `cost_center` column on trips with the
   idempotent `ALTER` the deployed volume needs.
2. **The resolution.** `resolve_batch_row_cost_centers` runs the chain over the
   same card pass `person` uses. Every row carries `cost_center`,
   `cost_center_source`, `cost_center_source_label`, `needs_cost_center`;
   `n_needs_cost_center` sits beside `n_needs_person`, `cost_center_options`
   beside `entity_options`. `needs_cost_center` fires last of all, after
   `needs_person`, and is unreachable while the registry is empty.
3. **The override.** `cost_center` joins `EXPENSE_HEADER_FIELDS`, so it lands
   in `edited_fields` like any other field edit and the export needs no second
   mechanism.
4. **29 tests** across `test_cost_center_carriers.py` and
   `test_cost_center_resolution.py`, all through the settings PUT, the trips
   routes, or `GET /api/expense-batches/{id}`. Suite 1535 to 1564, ruff clean
   on every touched file. Six wiring points regress-checked, each
   green to red to green.
5. **Re-pinned in the same round** (rule 4): `test_view_contract.py` and
   `docs/api-contract.md`.

### July receipts, and where the search actually ends

6. Re-probed Criss's mailbox with the same differential script: **dirk OK 2691,
   matthias OK 451, criss OK 32606**. The Exchange Application Access Policy
   propagated; the controls answering in the same run is what makes the OK
   trustworthy.
7. Swept her 81 folders over 2026-06-25 to 2026-08-15: 976 messages in the
   window, 179 from chase-list vendors, 34 with attachments. Cross-referenced
   against the 97 uncovered July charges: **20 charges with a receipt-shaped
   mail**, behind 9 distinct mails.
8. Downloaded them: **19 receipt and invoice PDFs** (Anthropic x8, Lovable x6,
   Supabase x2, Microsoft x1, plus a screenshot) into
   `.scratch/recon-july/criss-receipts/`.

### Hosting

9. Item 50's hosting half closed: memory raised to 1024 MB on owner order,
   verified after (1024 MB, `min_machines_running: 1` on both ports,
   `/healthz` 200).
10. All six stranded local commits pushed. The 2026-09-10 permission-classifier
    refusals were transient; every push this session went through first try.

---

## Key Decisions Made

### The step-2d "interpretation" needed no owner call
- **Choice:** built a real `cost_center` column on trips.
- **Rationale:** the prior session flagged that item 47 never says how a trip
  carries a cost center and asked for an owner ruling before relying on an
  interpretation. It does say, in its own API-contract section: "trip object
  gains `cost_center`; `POST` / `PUT /api/trips` accept it." Reading the whole
  spec answered the question the interpretation was invented for.

### The empty-registry contract gets exactly one home
- **Choice:** the service guards only the expensive merchant sweep; the
  contract itself lives solely in `CostCenterRegistry.resolve`.
- **Rationale:** the first draft implemented the guard in both places, which
  meant a mutation of either left the tests green and neither was load-bearing.
  One home is what makes the regress-check bite.

### A name is validated at the override, never at the carriers
- **Choice:** the row override 400s on an undefined cost center and stores the
  registry's own spelling; card, merchant and trip store whatever is typed.
- **Rationale:** those four screens are edited independently, so validating at
  the carriers would make edit ORDER matter. Naming a card's project before the
  project exists would fail for a reason invisible from that screen. An unknown
  name simply fails to resolve, which leaves the row unassigned instead of
  stamping an invention.

### Both registries are read live, not from the batch snapshot
- **Choice:** cost-center and merchant registries are read from settings on
  every view build.
- **Rationale:** the whole first phase of this feature is an empty registry. The
  day the owner defines the first cost center, existing months have to start
  resolving without a refresh pass. The card default is the deliberate
  exception: it rides the card snapshot like `person`.

### Receipt matching stops at the script and hands off to the app
- **Choice:** did not hand-match the 19 PDFs to charges; recorded the limit and
  stopped before the ingest.
- **Rationale:** see Working Notes. The script is the wrong instrument.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/cards.py` | edit | `default_cost_center` through all five card code points |
| `src/expense_recon/merchant_registry.py` | edit | `cost_center` on the entry and on `MerchantMatch` |
| `src/expense_recon/web/store.py` | edit | trips `cost_center` column + idempotent migration |
| `src/expense_recon/web/service.py` | edit | `resolve_batch_row_cost_centers`, row fields, review state, summary counter, options, `EXPENSE_HEADER_FIELDS` |
| `src/expense_recon/web/app.py` | edit | trip PUT merge, trip dict for the view, override registry validation |
| `tests/test_cost_center_carriers.py` | new | 16 tests, the three carriers through their real surfaces |
| `tests/test_cost_center_resolution.py` | new | 13 tests, the chain through the batch API |
| `tests/test_view_contract.py` | edit | pin `cost_center_options[]`; fixture now defines a cost center |
| `docs/api-contract.md` | edit | the cost-center section |
| `status/p1-expense-reconciliation.md` | edit | step 2, the July finding, Criss unblocked |
| `status/p1-improvement-backlog.md` | edit | item 50 hosting half closed |

---

## Current Status

`client/brisken/p1-cost-centers` at `1e9fea1d`, **pushed**, four commits ahead
of main, no PR opened yet. Suite 1564 passed / 2 skipped. Working tree clean.

brisken platform: unknown plan, last assessed unknown; `infrastructure.yaml`
carries no `platform` section for this client.

`brisken-expense-recon` on Fly: 1024 MB, one machine in fra,
`min_machines_running: 1` on 8080 and 2525, autostop unset, `/healthz` 200.

Four brisken status files are stale (p2-lead-gen-general 82d, p2-product-decks
50d, p2-rome 51d, p2-targeting 51d). All p2; untouched this session.

---

## Next Steps

1. **Item 47 step 3:** month report grouped by cost center. Reuse the
   `sections` partition item 38 built for per-person trip reports in
   `build_expense_report_pdf`; partitioning on cost center is the same call
   with a different key. Unassigned rows get their own final section, named as
   unassigned, never hidden.
2. **Item 47 step 5:** `GET /api/cost-centers/totals?from=&to=` for the
   cross-month roll-up. Both surfaces carry the stated limit: card and receipt
   spend only, never a total project cost.
3. **Item 47 step 6:** the Lovable half, promoted out of item 47 into its own
   prompt doc now that the backend emits the fields.
4. **The July ingest** needs its explicit go (owner has chosen
   verify-then-ingest). See Open Questions.
5. Open a PR for `client/brisken/p1-cost-centers` once step 3 lands, or now if
   the branch should not sit.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 47 (the
  spec; items 48-54 are the other open work)
- `.../automations/expense-reconciliation/src/expense_recon/cost_centers.py`
- `.../src/expense_recon/web/service.py`, `resolve_batch_row_cost_centers` and
  `build_expense_view`
- `.../docs/api-contract.md`, the cost-centers section

### Open Questions
- **The July ingest.** 19 PDFs are downloaded and the owner has chosen
  verify-then-ingest, but the write lands in Criss's live July month
  `50622baec444` and needs its own explicit go. The open sub-question is
  WHICH route: push the files through the app's normal ingest so its OCR does
  the matching, or forward the source mail to `expenses.brisken.com` so the
  real intake path is exercised end to end.
- **Criss's "Failed to fetch" is unexplained again.** The cold-start theory was
  the leading one and it loses its mechanism now that the machine is confirmed
  always-on (and was already, before this session). The probe that records
  machine state at failure time is the open half of item 50.
- Whether the four stale p2 status files should be refreshed or retired.

### Working Notes

**The verification limit, stated because the headline number is misleading.**
Reading amounts out of the 19 PDFs confirms only **two** charges on a
discriminating amount: Supabase 92.70 and Anthropic 52.26, both 2026-07-29.
Everything else carries round figures (25.00 / 50.00 / 100.00) that several
different July charges share, so the amount narrows the vendor and cannot say
which charge a given receipt covers. Four PDFs yield no extractable text at all
(three Anthropic `WWT1PNYP` invoices and the Microsoft `G170925639`), so the
text probe is structurally blind on them. The conclusion is not "20 charges
recovered", it is **the script is the wrong instrument**: the app's own OCR and
matching engine exist to answer exactly this, and running the files through the
real ingest is both the better match and the exercise of the real path.

**A false positive caught on the way.** The substring `chase` matches inside
"Purchase Order", which paired the JPM Chase annual membership fee with an
Archer-Daniels-Midland purchase-order mail. Removed from the vendor key map;
the first pass reported 21 strong candidates, the honest count is 20.

**Two near-misses of the same class, both self-caught, both worth carrying.**
(a) The `cost_center_options[]` contract pin passed against an EMPTY list: the
path was pinned, the element kind never observed, so the "object" assertion was
decorative. Fixed by having the contract fixture define a cost center. Any
future pin added to that file with an empty example has the same hole. (b) The
empty-registry guard was written in two places, which would have made a
mutation of either leave the suite green. Both are the instrument-validity
shape: the test ran, and proved nothing.

**Item 50's premise was stale and the file was not the record.** The item
quotes a `fly.toml` saying `auto_stop_machines = true` /
`min_machines_running = 0`. The live machine config said otherwise:
`min_machines_running: 1` already set on both services, autostop unset. Reading
the machine rather than the file is what narrowed an owner decision from two
questions to one, and it invalidated the leading theory for Criss's error at
the same time.

### Reference Materials
- Scratch, all gitignored, in the PRIMARY clone `.scratch/recon-july/`:
  `policy_probe.py` (the differential mailbox probe, Dirk is the control),
  `criss_july_sweep.py`, `criss_match.py`, `criss_fetch.py`,
  `criss_verify.py`; outputs `criss-july.json`,
  `criss-receipt-manifest.json`, `criss-receipts/`
- App `https://api.expenses.brisken.com`; July batch `50622baec444`
- Worktrees: work `agentic-ops1-cc` on `client/brisken/p1-cost-centers`;
  ledger `agentic-ops1-docs-0911` on `docs/checkpoint-2026-09-11-brisken-cc`

---

## How to Continue

The build is at a clean seam: steps 1 and 2 committed and pushed, suite green,
no caller pointing at anything unbuilt. The resume prompt below is the
artifact, not a description of one. Paste it whole into a fresh chat; it
carries its own continuation protocol and re-emits it, so the chain does not
lose the instruction at the next handoff.

```
Resume Brisken p1 (expense reconciliation), cost centers, backlog item 47.
Continue at STEP 3 of 6. Steps 1 and 2 are committed, pushed, green, and
nothing is half-wired.

WORKTREE: C:/Users/neuma_p1qrsic/Repo/agentic-ops1-cc
BRANCH:   client/brisken/p1-cost-centers  (HEAD 1e9fea1d, PUSHED, no PR yet)
Work there, not in the primary clone: sibling Claude sessions share it.

=== HOW TO RUN THIS SESSION (carry this forward) ===
When context pressure gets too high, do the following in this exact order:
  1. PAUSE operation at a clean seam. Never stop mid-wiring.
  2. CHECKPOINT (invoke /comd_checkpoint, never hand-roll it).
  3. GENERATE a copy-pasteable prompt that resumes from the exact spot you
     paused at, and INCLUDE THIS FIVE-LINE PROTOCOL VERBATIM inside that
     prompt so the next session does the same.
No leaving voids: if something is half-built, either finish it or revert it
before you pause, and say in the prompt which you did and why.
"Clean seam" means the suite is green and no caller is left pointing at a
function that does not exist yet.
=== END PROTOCOL ===

Read first, in this order:
  1. workspace/clients/brisken/status/p1-improvement-backlog.md, item 47.
     That is the SPEC. Build to it; do not re-decide it. Items 48-54 are the
     other open defects.
  2. .../automations/expense-reconciliation/docs/api-contract.md, the
     cost-centers section (added this round; it is the contract steps 3-6
     must not break).
  3. .../src/expense_recon/cost_centers.py and, in web/service.py,
     `resolve_batch_row_cost_centers` + its call site in build_expense_view.

DONE (steps 1-2): the owner-authored registry with the empty-registry
contract; the chain override > trip > merchant > card; the three carriers
(card `default_cost_center`, merchant `cost_center`, a real `cost_center`
column on trips + its migration); per-row resolution emitting cost_center /
cost_center_source / cost_center_source_label / needs_cost_center;
`n_needs_cost_center`; `cost_center_options`; the override in
EXPENSE_HEADER_FIELDS validated against the registry. 53 tests across
test_cost_centers.py, test_cost_centers_api.py, test_cost_center_carriers.py,
test_cost_center_resolution.py. Suite 1564, ruff clean via
`uvx ruff check --config <repo>/ruff.toml`.

Three contracts that must not regress:
  - An empty registry resolves nothing AND FLAGS NOTHING. It has exactly ONE
    home, `CostCenterRegistry.resolve`; do not re-add a second guard in the
    service or the mutation test stops biting. This is the only test here
    that fails silently.
  - A name is validated ONLY at the row override. Card, merchant and trip
    store it as typed, because those screens are edited independently and
    edit ORDER must not matter.
  - `resolve()` takes no person or category argument and a test asserts the
    signature.

STEP 3, the month report grouped by cost center:
  build_expense_report_pdf already takes `sections` -- contiguous slices of
  the listing with their own caption, per-currency sums and continuous
  numbering, built for the per-person trip report in item 38. Partitioning on
  cost center is the same call with a different key. Unassigned rows get
  their own FINAL section, named as unassigned, never hidden. Carry the
  stated limit in the caption: this tool sees card and receipt spend only,
  never contractor invoices or salaries, so a cost-center figure is not a
  total project cost.

Then step 5: GET /api/cost-centers/totals?from=&to= (per cost center, per
currency, row count, explicit unassigned bucket) -- the only genuinely new
surface, since nothing aggregates across batches. Then step 6, the Lovable
half, promoted out of item 47 into its own prompt doc now that the backend
emits the fields.

Method, non-negotiable per rule_behaviors B2: every increment needs a test
that runs THROUGH the caller, and you must watch it go red. Use
  uv run --directory C:/Users/neuma_p1qrsic/Repo/agentic-ops1-cc tools/regress_check.py \
    --test "uv run --directory <recon dir> pytest <file> -q" \
    --file <src> --replace "<wired call>" --with "<disabled>"
Steps 1 and 2 proved BOTH the helpers and the wiring this way, at six points.

Two traps this round hit, so watch for them:
  - A contract pin can pass against an EMPTY example: the path gets pinned
    and the element kind never observed. When you add a row to
    test_view_contract.py, make the fixture FILL it.
  - A contract implemented in two places makes neither load-bearing, and the
    mutation test goes green while proving nothing.

ALSO OPEN, not cost centers:
  - The July receipts are FOUND. Criss's mailbox is readable now (the
    Exchange policy propagated; dirk+matthias are live controls in the same
    probe). 19 receipt PDFs for 20 of the 97 uncovered July charges are in
    the PRIMARY clone's .scratch/recon-july/criss-receipts/, manifest
    criss-receipt-manifest.json. Only 2 are confirmed on a discriminating
    amount (Supabase 92.70, Anthropic 52.26); the rest sit on round figures
    several charges share, and 4 PDFs give up no text. Do NOT hand-match
    them: the app's own OCR is the right instrument. The owner chose
    verify-then-ingest; the ingest writes into Criss's LIVE July month
    50622baec444 and still needs an explicit per-action go, including which
    route (direct ingest vs forwarding the mail to expenses.brisken.com).
  - Criss's "Failed to fetch" is unexplained again: the cold-start theory
    died when the machine turned out to be pinned always-on already. The
    open half of item 50 is a probe that records machine state at failure.
  - Four p2 status files are stale (p2-lead-gen-general 82d, p2-rome,
    p2-targeting, p2-product-decks ~50d). Refresh or retire.

Do not: click Join in Zoho Expense (provisions an empty org, recovers
nothing), or POST test data to 074a7b8905d7 / 50622baec444 / a5f97a85b1d0 /
86929f2a909a / 51a22ad72864 -- those are Criss's real months. Test batches:
create with allow_empty, delete with POST /api/runs/{id}/delete and
{"confirm": "<run id>"} (DELETE /api/expense-batches/{id} is a 405).

Method warning, now twice-proven: an API error string, and a config FILE,
each name a symptom rather than the record. Read the record. 6018 "your
account is disabled" meant "Expense was never set up"; a 403 on a mailbox
meant an Exchange group; and item 50's quoted fly.toml said the app could
stop while the live machine config said min_machines_running was already 1.
```

---

## Strategic Feedback

### What Worked Well This Session
- Reading the whole spec before accepting a handoff's framing. The prior
  session flagged step 2d as needing an owner ruling; item 47's own
  API-contract section answered it outright. One read replaced a round trip.
- Checking item 50's live machine config instead of the `fly.toml` the item
  quoted. It cut the owner decision in half and killed a leading theory for an
  unrelated defect in the same call.
- Mutating the contract at its single home rather than accepting the first
  green regress-check. Noticing the guard existed twice is what made the
  empty-registry test actually bite.

### Suggestions
- The contract-pin hole is worth a structural fix, not just this note.
  `_assert_contract` in `test_view_contract.py` could fail a pin whose observed
  element-kind set is EMPTY, which is exactly the "path pinned, kind never
  observed" case. That would have caught this round's decorative pin
  automatically and will catch the next one. Cheap, and it lives in the file
  whose entire purpose is preventing shape drift.

### System Health
- **Autonomy: 2 human interventions**, both solicited decisions rather than
  corrections (the Fly memory tier, and how to route the recovered receipts).
  No course correction was needed this session.
- `git push` worked first try on every attempt, including the six commits the
  last session left stranded. The 2026-09-10 permission-classifier refusals
  were transient, and `rule_no_auto_commit` Band 1 does run as written.
- Four tool calls went to guards firing on shapes the register has carried
  since August (two heredoc forms, one `cd X && ...`) plus one MSYS path-form
  slip and one guessed route. Every guard fired before damage; the cost is
  small and recurrent rather than dangerous.
