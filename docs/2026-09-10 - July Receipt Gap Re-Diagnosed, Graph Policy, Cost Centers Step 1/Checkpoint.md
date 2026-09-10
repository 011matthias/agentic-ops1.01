# Checkpoint: July Receipt Gap Re-Diagnosed, Graph Policy, Cost Centers Step 1

**Date:** 2026-09-10
**Status:** July diagnosis corrected twice and settled; Criss's mailbox unblocked at Exchange but not yet propagated; cost centers step 1 of 6 shipped

---

## Summary

The 2026-09-09 verdict on July's missing receipts was wrong in both halves, and
correcting it changed what to do: the receipts are not locked behind Zoho access,
they were never filed anywhere, and Dirk has been mailing them into the intake
daily since 09-07. Criss's mailbox was opened at the Exchange layer (not, as the
reflex said, by widening a Graph scope), her statement-attach failure was
diagnosed to infrastructure rather than to the statement code, five defects were
added to the backlog, and the cost-center build began.

---

## What Was Done This Session

### The July gap, re-diagnosed twice

1. **`6018 "your account is disabled"` does not mean a disabled account.** The
   token resolves to `dirk.neumann@brisken.com`, admin, active. Dumping the full
   `/organizations` payload splits the eight cleanly: the two readable orgs carry
   `user_status: 1`, `is_quick_setup_completed: true`, plans Zoho One and FREE;
   all six "locked" orgs carry plan TRIAL, `is_quick_setup_completed: false`, and
   **no `user_status` field at all**. GmbH is FREE and works, so it was never
   about a paid plan. Zoho Expense was simply never set up in those six.
   Confirmed by the owner: Expense serves a "Join your existing organizations"
   screen listing exactly those six.
2. **The "sent to Criss, unreachable" group was reasoning from the wrong
   question.** Where the receipt *email arrives* is not where the receipt *is
   filed*. `GET /api/inbound/log?detail=1` showed 16 forwards from Dirk between
   09-07 and 09-10T06:43, each self-filing by receipt month, covering the exact
   vendors called unreachable.
3. **Consequence:** for July there is nothing to unlock. Books holds the charges
   from the card feed with no attachment on 108 of 111 rows; Expense is live only
   in Cloud Services, where the 8 already came from. Coverage restated FX-aware
   with vendor agreement: **21 of 111 covered, 89 not**, split 44 recoverable
   from a vendor billing portal (USD 3,398 + EUR 900) against 45 paper slips
   (USD 932).

### Criss's mailbox: opened at Exchange, not at Graph

The instinct ("expand the Graph scope") would have achieved nothing. The token
already carries tenant-wide `Mail.Read`; the refusal was
`403 [RAOP] Blocked by tenant configured AppOnly AccessPolicy settings`. The
Application Access Policy that `rule_brisken_graph_first` described as absent had
since been created and was enforcing. Owner signed in as an Exchange admin and
ran the script; real scope group is **`sg-marketing-ops-mailboxes`** (not the
runbook's remembered name, which is why the script reads `ScopeName` off the live
policy). Members 2 to 3, `Granted`, control mailbox still `Denied`.

### Criss's statement failure

Her "Error" mail carried no text, three inline images. The real one: **Attach
bank statement**, `August2026.xlsx`, card `2838`, red **"Failed to fetch"**.
Ruled out by probe: the endpoint (two statements attached in 0.1s each), CORS
(clean on 200/401/404 and the column-map 400 from the SPA's own origin), and the
failed deploys (v111/v112 at 10:42Z, 42 minutes after her 10:00:43Z error).

### Cost centers (item 47), step 1 of 6

`settings["cost_centers"]` registry, normalizer, resolution chain, settings
wiring, 24 tests. Both mutations proven to bite.

---

## Key Decisions Made

### Do not click Join in Zoho Expense

- **Choice:** leave the six orgs unjoined.
- **Rationale:** joining provisions an EMPTY Expense org. It recovers nothing for
  July and moves against the 2026-08-22 directive that the app have no ties to
  Zoho.

### Widen the mailbox allowlist to Criss, and say why in the rule

- **Choice:** `rule_brisken_graph_first` now allowlists three mailboxes, with the
  evidence for the third written into the rule.
- **Rationale:** the two controls must move together. Allowed in code but not in
  the policy group is a 403; in the group but not in code is our own refusal.

### Delete the drafted email rather than leave it staged

- **Choice:** the "re-enable your login" draft was written, critiqued, then
  deleted the same session.
- **Rationale:** its central ask had become false. A staged draft resting on a
  dead premise is worse than none (W1 §4: no SUPERSEDED banners).

### Build the empty-registry contract before anything else

- **Choice:** cost centers step 1 is the registry and its empty case, nothing
  else.
- **Rationale:** an empty registry must resolve nothing AND flag nothing. Without
  it, the day the field ships every row in every month reads
  `needs_cost_center`, and a review state at 100% is noise. It is also the only
  test here that regresses silently.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/rules/rule_brisken_graph_first.md` | edit | Third mailbox; the policy is live; scope is not the lever |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit x4 | The corrected diagnosis, route split, Exchange finding |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | Items 50-54; item 47 marked BUILD ORDERED |
| `.../automations/expense-reconciliation/src/expense_recon/cost_centers.py` | add | Registry + resolution chain |
| `.../expense-reconciliation/tests/test_cost_centers{,_api}.py` | add | 24 tests, registry and through-the-API |
| `.../expense_recon/web/{app,store}.py` | edit | Settings default, PUT validation, GET options |
| `.../context/zoho-receipts-july-2026/README-july-receipt-gap.md` | edit | Corrected attribution (gitignored) |
| `.../context/graph-access-policy-runbook.md` | rewrite | Policy is live; how to add a mailbox; four dead routes (gitignored) |
| `.../context/drafts/zoho-expense-access-july-to-dirk.md` | created, then deleted | Premise became false |

Six commits, **all local** — every `git push` this session was refused by the
permission classifier.

---

## Current Status

brisken platform: unknown plan, ~?/? ops/mo, last assessed unrecorded.
comms-log 2 days old.

Branches, all unpushed:
- `client/brisken/p1-july-gap-attribution` — 5 commits (diagnosis, rule, backlog)
- `client/brisken/p1-cost-centers` — the above plus step 1, in worktree
  `C:/Users/neuma_p1qrsic/Repo/agentic-ops1-cc`

Suite 1511 to **1535 passed, 2 skipped**. Ruff clean.

Criss's mailbox: `Test-ApplicationAccessPolicy` says Granted, but the enforcement
layer still 403s. The poller ran 18 rounds over 45 minutes with Dirk healthy as a
control in every round, then timed out. Propagation is simply slower than the
runbook's ~30 minutes.

---

## Next Steps

1. **Re-probe Criss's mailbox** (`python .scratch/recon-july/policy_probe.py`).
   On OK, run the July sweep against her mailbox; the allowlist already carries
   her.
2. **Cost centers steps 2-6** (see the handoff prompt): card
   `default_cost_center` + merchant `cost_center`, row resolution in
   `build_expense_view`, `cost_center` into `EXPENSE_HEADER_FIELDS`, month report
   grouping, `GET /api/cost-centers/totals`, Lovable half.
3. **Owner decision on item 50:** `min_machines_running = 1` and more than 512MB.
   The mail-availability half is the real risk, not the upload.
4. Push the six commits once the classifier allows it, then PR.
5. Refresh four stale p2 status files (49-81 days): `p2-lead-gen-general`,
   `p2-product-decks`, `p2-rome`, `p2-targeting`.
6. Rotate whatever `tok.txt` holds; it is still on two branches, one pushed.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 47, 50-54)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/cost_centers.py`
- `workspace/clients/brisken/context/graph-access-policy-runbook.md`

### Open Questions
- How long does this tenant's Application Access Policy actually take to
  propagate? 45 minutes was not enough.
- Item 50: was the machine stopped at 10:00:43Z? Unprovable now; the next
  occurrence needs a probe that records machine state at failure.
- Item 52: does the SPA gate its receipt viewer on `has_receipt_image`? One row
  reports `receipt_image_available: true` and `has_receipt_image: false` at once
  while the file serves 200.

### Working Notes

**The method failure worth carrying forward.** Three wrong or nearly-wrong claims
this session, one root cause: reading an error string or an absence instead of
the record behind it. `6018` read as "a user was disabled" (it was "Expense was
never set up"). "No receipt mail in the two mailboxes we may read" read as
"unreachable" (the sender was forwarding them into our own intake daily). And a
receipt-image 404 nearly read as a defect when it was my own wrong URL. The
instrument-validity sub-clause covers the third shape and did not fire on the
first two, because both felt like reads rather than probes.

**A near-miss worth naming.** The CORS probe was written to POST a statement to
`074a7b8905d7`, Criss's real August month. Caught by re-reading before running,
not by any gate. A mappable file would have attached itself to her live month.

**Two stray TEST batches reached the live months list** for about ten minutes
during the statement repro, because `DELETE /api/expense-batches/{id}` is a 405;
the real route is `POST /api/runs/{id}/delete` and it requires
`{"confirm": "<run id or label>"}`.

**Statement-attach quirk found by the drill:** a well-formed xlsx whose columns
do not read as charges attaches with `200 {"ok": true}` and records
`n_rows: 0`. That is backlog item 51.

**Zoho Expense probe ergonomics:** `/users/me` with no org returns `6024`
("belongs to multiple organizations"); pass a readable org id to identify the
token.

### Reference Materials
- Scripts (all `.scratch/recon-july/`, gitignored): `ze_orgs_probe.py`,
  `policy_probe.py`, `wait_for_criss.py`, `repro2.py`, `cors_probe.py`,
  `routes.py`, `add-criss-to-graph-policy.ps1`
- App `https://api.expenses.brisken.com`; batches July `50622baec444`, August
  `074a7b8905d7`, June `a5f97a85b1d0`, May `86929f2a909a`, Sept `51a22ad72864`
- Graph app `79d33e4a-23a0-4e16-bee2-68396b8ee562`, policy group
  `sg-marketing-ops-mailboxes`

---

## How to Continue

The cost-center build is at a clean seam: step 1 committed, suite green, nothing
half-wired. Everything else is either waiting on propagation (Criss's mailbox) or
on an owner decision (item 50).

The resume prompt below is the artifact, not a summary of one. Paste it whole
into a fresh chat. It carries its own continuation protocol and re-emits it, so
the chain does not lose the instruction at the next handoff.

```
Resume Brisken p1 (expense reconciliation), cost centers, backlog item 47.
Continue at STEP 2 of 6. Step 1 is committed, green, and nothing is half-wired.

WORKTREE: C:/Users/neuma_p1qrsic/Repo/agentic-ops1-cc
BRANCH:   client/brisken/p1-cost-centers  (HEAD e299f50a, UNPUSHED)
Work there, not in the primary clone: five sibling Claude sessions share it.

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
     That is the SPEC. Build to it; do not re-decide it. Items 50-54 are the
     other open defects from 2026-09-10.
  2. .../automations/expense-reconciliation/src/expense_recon/cost_centers.py
     (what step 1 built)
  3. docs/2026-09-10 - July Receipt Gap Re-Diagnosed, Graph Policy, Cost
     Centers Step 1/Checkpoint.md, Working Notes

DONE (step 1): settings["cost_centers"] = {name: {kind, note, active}} with
whole-map replace at the settings edge; CostCenterRegistry with the chain
override > trip > merchant > card; SETTINGS_DEFAULTS key; PUT validation in
app.py; derived read-only cost_center_options on GET /api/settings. 24 tests in
tests/test_cost_centers.py + tests/test_cost_centers_api.py. Suite 1511 -> 1535,
ruff clean via `uvx ruff check --config <repo>/ruff.toml`.

The contract that must not regress: an empty registry resolves nothing AND FLAGS
NOTHING. Without it every row in every month reads needs_cost_center on day one.
It is the only test here that fails silently. resolve() deliberately takes no
person or category argument and a test asserts the signature.

STEP 2, in this order:
  a. cards.py normalize_cards_setting + the Card dataclass + card_to_dict:
     add `default_cost_center` (a string; validate it is a defined cost-center
     name only at RESOLUTION time, not at the settings edge, because cards and
     cost centers are edited independently and edit order must not matter).
  b. merchant_registry.py normalize_merchants_setting: add `cost_center`,
     same reasoning.
  c. service.build_expense_view (~line 4863; the per-row loop is ~5008, the row
     dict output ~5095): resolve per row and emit the parallel fields from
     CostCenterResolution.as_fields() -- cost_center, cost_center_source,
     cost_center_source_label, needs_cost_center. Follow how `person` /
     `person_source` are threaded through `card_res`; that is the pattern.
  d. Trip resolution: trips (TripRow) carry no cost-center column. The reading
     I chose but did NOT implement is that a trip batch resolves to a
     same-named cost center of kind "trip", which needs no schema change.
     FLAG THIS TO THE OWNER as an interpretation before relying on it; the
     design says "trip" is a resolver but never says how a trip carries one.
  e. cost_center into EXPENSE_HEADER_FIELDS (app.py ~3188, the
     PUT /api/runs/{id}/expenses/{doc} allowlist) so the override rides the
     existing field-override mechanism with no second path. Validate against
     the registry; blank clears.

Then steps 3-6: month report grouped by cost center (reuse the `sections`
partition item 38 built for per-person trip reports, in build_expense_report_pdf),
GET /api/cost-centers/totals for the cross-month roll-up, and the Lovable half
(Settings editor + row picker). Carry the stated limit on both surfaces: this
tool sees card and receipt spend only, never contractor invoices or salaries, so
a cost-center figure is not a total project cost.

Method, non-negotiable per rule_behaviors B2: every increment needs a test that
runs THROUGH the caller, and you must watch it go red. Use
  uv run --directory C:/Users/neuma_p1qrsic/Repo/agentic-ops1-cc tools/regress_check.py \
    --test "uv run --directory <recon dir> pytest <file> -q" \
    --file <src> --replace "<wired call>" --with "<disabled>"
Step 1 proved BOTH the helper and the wiring this way. Do the same.

ALSO OPEN, not cost centers:
  - Criss's mailbox: Test-ApplicationAccessPolicy says Granted but enforcement
    still 403 after 45 min. Re-probe with
    `python .scratch/recon-july/policy_probe.py`. On OK, sweep her mailbox for
    July receipts; the allowlist in rule_brisken_graph_first already carries her.
    Dirk is the control in that probe -- if he ever fails, it is not propagation.
  - Six commits sit local across client/brisken/p1-july-gap-attribution,
    client/brisken/p1-cost-centers and docs/checkpoint-2026-09-10-brisken-july-cc.
    EVERY git push on 2026-09-10 was refused by the permission classifier. Retry
    once; if still refused, say so plainly rather than working around it.
  - Backlog item 50 needs an OWNER DECISION, not a build: min_machines_running=1
    and >512MB on brisken-expense-recon. The real risk is not Criss's upload, it
    is that the app is the MX target for expenses.brisken.com and is currently
    allowed to stop.

Do not: click Join in Zoho Expense (provisions an empty org, recovers nothing),
or POST test data to 074a7b8905d7 / 50622baec444 / a5f97a85b1d0 / 86929f2a909a /
51a22ad72864 -- those are Criss's real months. Test batches: create with
allow_empty, delete with POST /api/runs/{id}/delete and {"confirm": "<run id>"}
(DELETE /api/expense-batches/{id} is a 405).

Method warning from 2026-09-10, because it cost two wrong diagnoses in one
session: an API error string names a symptom, not a cause. Read the RECORD
behind it. 6018 "your account is disabled" meant "Expense was never set up",
and a 403 on a mailbox meant an Exchange group, not a missing Graph scope.
```

---

## Strategic Feedback

### What Worked Well This Session
- Every negative that closed a search was re-tested against a control in the same
  run: the Zoho org probe kept Cloud Services answering, the mailbox probe kept
  Dirk answering, the CORS probe checked all four response codes. That is what
  turned "Criss is blocked" into "Criss is blocked and Dirk is not, so it is the
  policy", which is the finding the fix depended on.
- `regress_check.py` on both the helper AND the wiring. Disabling the PUT branch
  reddened the API suite; without that second run the tests would have proven
  only that the registry works, not that anything calls it.

### Suggestions
- The instrument-validity sub-clause fires on probes. Both misses this session
  were *records*: an error string and an empty result set. Worth widening its
  trigger from "any negative that closes a search" to include **any diagnosis
  taken from an error message rather than from the object the message is about**.
  A 403 or a 6018 names a symptom; the record behind it names the cause.

### System Health
- **Autonomy: 2 human interventions**, both corrections that materially changed
  the outcome ("why criss's mailbox, we need zoho access" and "nobody told you to
  log in to all the vendors"). Both were cases where I had answered a question
  the user had not asked.
- `git push` was refused by the permission classifier on every attempt, so six
  commits sit local across two branches. If that is deliberate, the ship chain in
  `rule_no_auto_commit` Band 1 cannot run at all and the rule should say so.
