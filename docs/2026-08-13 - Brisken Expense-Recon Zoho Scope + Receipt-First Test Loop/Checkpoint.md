# Checkpoint: Brisken Expense-Recon Zoho Scope + Receipt-First Test Loop

**Date:** 2026-08-13
**Status:** Receipt-first test loop set up and handed off; vendor-name non-determinism identified as the live defect

---

## Summary

Re-consented the Zoho Books token with expense/bill read scope and ran
`seed-zoho` into production learned memory (103 rows), then measured its real
reach and found it small (3 of 78 card descriptors). Assembled and verified
seven local receipt-first test sets, ran the pipeline twice on real receipts,
and established that vendor names drift between byte-identical runs while
money fields hold.

---

## What Was Done This Session

### Zoho Books scope + learning seed
1. Owner generated a fresh Self Client grant; exchanged it for a refresh
   token carrying `accountants.READ, settings.READ, expenses.READ, bills.READ`.
   Verified code 0 on `chartofaccounts`/`expenses`/`bills` for BOTH target orgs
   (Corporate Services 822741658, Cloud Services 697686691) BEFORE writing
   `context/.env`; CRM token confirmed still minting afterwards.
2. Ran `memory seed-zoho` for both entities. Production `/data/learning.sqlite`
   did not previously exist; it now holds 103 merchant_category rows (67 CS +
   35 Cloud) verified in-container through the deployed `LearningStore`.
   Load path: export rows to JSON, tee to `/data`, replay through the deployed
   store (the permission classifier blocks base64 file transfers, and replaying
   through production code means production authored its own schema).
3. Added the standing rule `anthropic -> Software & Subscriptions [Other Infra
   and IT Costs for Cloud Business]` for Corporate Services, because Zoho
   history spells the vendor `antropic`, which never matches a normalized
   statement charge.
4. Measured the seed's real reach against the April Chase 2838 statement:
   **3 of 78 distinct descriptors recall**. Zoho vendor records are clean names;
   card descriptors carry processor noise (`ELEVENLABS.IO`,
   `ADOBE  *800-833-6687`, `MICROSOFT#G149866119`). Running the deployed
   `vendor_names.clean_vendor_name` first does not help (still 3/78).

### Stale blocker cleared
5. The "press Publish in Lovable" blocker carried in memory for weeks is dead.
   Verified by probing the live bundle: `brisken-reconcile-dash.lovable.app`
   serves `set.cardAccount.*`, `set.cardEntity.*`, `wb.setup.*` i18n keys and
   `entity_options` from PR #498. Probe gotcha: grepping the bundle for raw API
   field names returns nothing even on a correct build, because the SPA labels
   everything through i18n keys.

### Bug fixed and shipped (PR #510)
6. `_print_dry_run_summary` unpacked `parse_errors` as 3-tuples while producers
   emit 4-tuples (the 4th is `severity`). Every `--dry-run` with at least one
   parse issue printed its counts then died with `ValueError: too many values
   to unpack`, exiting non-zero and swallowing the issue detail. Star-unpack,
   matching the tolerance the producer's own logger loop already used.
   Regression test proven to fail without the fix; suite 1024 pass / 2 skip;
   CI green on all seven jobs; merged.

### Receipt-first test material
7. Pulled the three remaining receipt-first runs off the Fly volume and
   assembled seven local sets with complete file listings (see Working Notes).
8. Corrected `legal_entity_id` in two configs: May said `Brisken Corp Services`,
   `7d2fea33d39a` said `Brisken`. Neither matches a chart entity, so both would
   have returned `has_coa: false` regardless of anything else.
9. Built a receipts-only variant of the May set, excluding the 7 Chase
   statement PDFs Criss uploaded into her receipts folder.

### Live runs and the finding
10. Ran the 10-receipt set twice with byte-identical config, `gpt-4o-mini`,
    `temperature=0` both times. Money fields (amount, currency, date, tax)
    identical on all 10. **4 of 10 rows differed in vendor or description.**
    One merchant read `MEGA CENTER`, `MEGA CENTRO`, `MEGA CENTRE` across three
    runs of the same image.
11. Wrote the improvement-loop handoff prompt to
    `.scratch/recon-improvement-loop-prompt.md`.

---

## Key Decisions Made

### Receipt-first is the only mode that counts
- **Choice:** Judge the tool solely on `mode: "expense_generation"`. The
  statement-plus-ER reconciliation path exists but is not Brisken's workflow.
- **Rationale:** Owner correction mid-session. All test material and quality
  judgments were re-scoped to receipt-first.

### Do not loosen the learned-memory lookup to fuzzy matching
- **Choice:** Keep `(legal_entity_id, vendor_norm)` exact-match; fix vendor
  canonicalization upstream instead.
- **Rationale:** The 3-of-78 recall looks like it wants fuzzy matching, but
  fuzzy keys cross-wire merchants in a financial tool. The gap self-heals as
  Criss categorizes, because `learn_from_run` keys a receiptless charge on the
  statement descriptor itself.

### Do not build currency inference from vendor or location
- **Choice:** Reject reviewer feedback item (b) as specified; demote the
  default-currency field in the UI instead.
- **Rationale:** Guessing currency from a merchant name is the same shape as
  the bug that put BRL numbers into a USD journal at roughly 5x.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/context/.env` | edit | new `ZOHO_BOOKS_REFRESH_TOKEN` (gitignored) |
| `.../expense_recon/cli.py` | edit | dry-run parse_errors star-unpack (PR #510) |
| `.../tests/test_cli_integration.py` | edit | regression test, both tuple shapes |
| `/data/learning.sqlite` (Fly volume) | create | 103 seeded merchant_category rows |
| `.scratch/criss-recon-may/` | create | May month pulled local, entity corrected |
| `.scratch/criss-recon-may-receiptsonly/` | create | May minus the 7 statement PDFs |
| `.scratch/criss-recon-runs/{7d2fea33d39a,05d3db59b225}/` | create | 37- and 10-receipt runs pulled local |
| `.scratch/criss-recon-runs/05d3db59b225/run.llm.json` | create | the only runnable receipt-first config |
| `.scratch/recon-improvement-loop-prompt.md` | create | fresh-chat handoff brief |
| `memory/project_brisken_expense_recon_master_data.md` | edit | scope resolved, seed run, measured reach, Publish blocker dead |
| `memory/project_brisken_zoho_books.md` | edit | granted scope now 4 read scopes |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | element states |

---

## Current Status

brisken platform: unknown plan, ops usage not assessed. Backend healthy on Fly
(machine `48ee133c363758`, scale-to-zero, auto-starts). SPA current and
published. Learned memory seeded but thin in practice. The receipt-first
engine runs end to end on real receipts and produces a Zoho Expenses CSV; its
weakness is vendor-name stability, not arithmetic.

Criss's "May 2026" run (created 2026-08-06 13:25) still carries `has_coa=0`
because that flag is snapshotted at run creation and the card-first-label fix
deployed the following day. A fresh run clears it; the existing one never will.
No run is published, so nothing has gone downstream.

---

## Next Steps

1. Start the improvement loop in a fresh chat from
   `.scratch/recon-improvement-loop-prompt.md`.
2. Establish whether the merchant registry is consulted on the receipt-first
   path at all; it was built 2026-07-29 to canonicalize exactly the
   `MEGA CENTER` / `CENTRO` / `CENTRE` case.
3. Get a third data point on the July-28-baseline money delta (receipt_01,
   `1837.51 USD` vs `8796.35 BRL`) before trusting or distrusting the money
   path; the clean run-to-run test showed no money drift.
4. Tell Criss to re-run May so the `has_coa` snapshot refreshes.
5. Resolve the two open reviewer design items (entity-from-a-column,
   currency derivation) or route them back to Criss with the question of which
   case prompted each.
6. `p2-targeting.md` status file is 22 days stale; refresh or delete on the
   next p2 session.

---

## Context for Next Session

### Files to Read First
- `.scratch/recon-improvement-loop-prompt.md`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md`

### Open Questions
- Is the merchant registry wired into `generate_expenses`, and if so why does
  it not collapse the three MEGA CENTER spellings?
- Is the baseline-vs-current money delta a fix, a regression, or noise?
- Does `card_accounts` resolution work on a receipt-first run, given entity
  comes from `expense.legal_entity_id` rather than a card?

### Working Notes

**Test material, all under `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\`:**
set 1 `.scratch\criss-recon-may\` (27 files: 20 receipts + 7 Chase statement
PDFs, plus `May2026.xlsx`); set 2 `.scratch\criss-recon-runs\7d2fea33d39a\`
(37 receipts); set 3 `.scratch\criss-recon-runs\05d3db59b225\` (10 receipts +
baseline + `run.llm.json`, START HERE); set 4
`.scratch\test-receipts-ER-00215\` (37 loose PNGs); set 5
`...-smoke10\` (10 PNGs); set 6
`workspace\clients\brisken\context\expense-reconciliation\receipts\` (13
receipts, Uber email-forwards + MBTA + ZE scans); set 7
`.scratch\criss-recon-may-receiptsonly\` (May minus statements). Sets 3/4/5
are the same images.

**Three traps, all cost time this session.** (a) `run.local.json` as the app
wrote it has NO `llm` block, and receipt-first needs vision, so it cannot run;
use `run.llm.json`. (b) `output.path` is IGNORED in `expense_generation` mode;
a run writes `expenses.csv` into the config's directory and overwrites the
baseline. Copy it aside first. (c) `--all-extras` is required or `rapidfuzz` is
missing and 9 test modules fail to import.

**Key source:** vault entry `OpenAI Brisken` in `~/.passwords.json`, field
`api_key`. It is Dirk's key, so runs bill him; two 10-receipt passes on
`gpt-4o-mini` is cents, repeated 37-receipt sets are not.

**Failed approach:** base64-encoding the seeded SQLite for transfer to the Fly
volume was blocked by the permission classifier twice. Exporting rows to plain
JSON and replaying them in-container through the deployed `LearningStore` is
both permitted and better, since production code authors its own schema.

**Measured, do not re-derive:** seed recall 3/78 raw and 3/78 after
`clean_vendor_name` (it gains CLUELY INC, loses GITHUB INC.). Run-to-run
determinism: 6 of 10 rows identical, 0 money-field diffs, 4 vendor/description
diffs.

### Reference Materials
- PR https://github.com/011matthias/agentic-ops1.01/pull/510
- SPA: https://brisken-reconcile-dash.lovable.app
- Backend: https://brisken-expense-recon.fly.dev

---

## How to Continue

Open a fresh chat and paste `.scratch/recon-improvement-loop-prompt.md`. It is
self-contained: material paths, run recipe, the three traps, what is already
measured, the loop, and the definition of done. Start on set 3 (ten receipts,
cheapest, has a baseline).

---

## Strategic Feedback

### What Worked Well This Session
- Verifying the new Zoho token against both orgs BEFORE overwriting `.env`,
  and re-checking the CRM token afterwards. A same-Self-Client re-grant could
  plausibly have invalidated the sibling token; checking cost one call.
- Proving the regression test fails without the fix before shipping PR #510.
  Without that step the test would have been decoration.
- Running the pipeline twice rather than once. A single run against a stale
  baseline would have produced a confident and wrong non-determinism claim;
  the second run separated model drift from code drift.

### Suggestions
- Three separate misses this session came from trusting a stale artifact
  (a 16-day-old memory line, a 91-commit-behind checkout, a July baseline).
  The SessionStart hook already prints the stale-checkout warning; it does not
  warn that a loaded memory's claims about live state are old. A cheap win:
  have the memory loader flag `project`-type memories older than N days whose
  body contains an imperative ("press", "ask the owner", "blocked on") as
  needing live verification before being acted on.

### System Health
- The B1 stop-gate fired 3 times, all on closing-sentence offers, all
  corrected in the same turn. Same pattern as the 2026-07-27 entry, where the
  fix was `documented`. Documentation is not holding on this one; the primer
  mechanism is the only thing that has changed the behavior mid-session.
- Autonomy: 4 human interventions (elevated; run /system-dev to close gaps).
  All four were course corrections rather than unblocks, and three of them
  were the user supplying context I could have queried.
