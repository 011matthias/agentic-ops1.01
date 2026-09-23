# Checkpoint: Recon Attribution Grounding And The Live Write Recovery

**Date:** 2026-09-23
**Status:** the learning-loop wave's first item is live and verified; the two weakest matching areas are measured and handed over, nothing built

---

## Summary

Four of the owner's ten 2026-09-23 feedback notes are one subject, the tool's
learning loop, and the first of them shipped as item 163: a memory save is now
computed as a plan, previewed, journalled with every touched row's pre-image,
and undoable. The session then measured the two areas the owner named as
working least well, card and category attribution, found that the card is the
single root cause of three empty columns, and handed over a continuation
prompt grounded in today's numbers rather than the backlog's older snapshots.

---

## What Was Done This Session

### Item 163, the learning loop's first half

1. Grouped notes #76, #78, #80 and #81 into one backlog section and measured
   the loop before building it: 153 rows over 62 vendors, 88 of the 113 rows
   on a repeat vendor still carrying a model guess or nothing, and exactly one
   row in the estate reading `learned`. That measurement is what ranked #81
   first: the recall side had been fixed twice while the teach side depended
   on a button whose effects nobody could see or take back.
2. Built `learning/commits.py`, whose `RecordingStore` accepts the five
   `record_*` calls the learners make and keeps them as planned writes instead
   of writing. Because the learners only ever call and never read back, the
   dry run is exact rather than approximate, so the preview cannot describe a
   different save from the one that happens.
3. Shipped `GET /api/runs/{id}/memory-plan`, `GET /api/memory/commits`,
   `POST /api/memory/commits/{id}/undo`, the `memory_journal` table, and
   `read_row` / `restore_row` on the learning store. PR #1202, merge
   `dedd7260`, deployed at Fly commit `dedd726002e4`.
4. Ten route-level tests, seven wires proven red by regressing the source, and
   the SPA half published by the owner, then verified in English and Portuguese
   from a cold browser (PR #1208).

### The attribution measurement

5. Read all three live months read-only through five parallel readers, each
   checked by a skeptic. Card sources across 154 receipts: hint 77, settled
   charge 21, hand pick 11, registry 2, learned 0, **none 43**. Every
   entity-less and person-less row is a card-less row, in every month.
6. Of the 43 card-less receipts, 25 print no payment method at all and 18
   print something the registry cannot resolve. The vendors that fail are the
   multi-card ones, and bill-to is empty on 154 of 154 rows, so no company
   signal survives a missing card.
7. Categorization: 94 of 154 receipts rest on the model, 33 carry a reviewer
   override with 21 of those on a repeat vendor, 138 of 174 receiptless
   charges are a guess off the bank descriptor, and memory holds 108 rules of
   which 102 are the Zoho seed and none are validated.
8. Recorded items 169 and 170 with the four points where the card chain
   refuses evidence it already holds, and the raw-vendor memory key that stops
   a correction reaching a merchant's other spellings. PR #1214, merge
   `0e2a6130`.
9. Delivered the continuation prompt in the reply and appended it to the
   mini-checkpoint (PR #1215, merge `f3ecd6bc`).

### Recovery and guards

10. Undid my own live write to Criss's September month using the feature built
    an hour earlier: `rows_restored: 8`, all eight rules back to
    `decision_count: 1`, journal entry 1 stamped reverted.
11. Two pattern rules from this session's own failures: `warn-padded-commit-sha`
    and `warn-spa-write-button-click`, both tested positive and negative.

---

## Key Decisions Made

### Measure before building anything for items 169 and 170

- **Choice:** neither item gets code until a committed replay instrument
  exists that judges card, entity, person and category per row.
- **Rationale:** nothing anywhere judges those four today. `labels.csv` in all
  eight bundles carries pair labels only, and the item-115 category replay was
  a scratch script that never reached the repo, so its numbers cannot be
  reproduced. Every generalization this project shipped without a measurement
  came back: item 117's one-word aliases, item 133's merchant floor, item
  156's Zoho taxonomy.

### The undo, rather than leaving the accidental write in place

- **Choice:** put the decision to the owner with a recommendation, then undo.
- **Rationale:** the damage was near-nil (all eight rules already existed with
  identical values; only `decision_count` and timestamps moved) but the
  journal entry would have sat in the record as a save Criss did not make. The
  reversal also became the first real exercise of the feature on live data.

### The alias gap is reported, not written

- **Choice:** measure what filling the four AI merchants' alias lists would
  move and prepare the diff; do not send it.
- **Rationale:** it is a live settings mutation, and the owner's standing
  instruction on that registry is "not yet, and dont re ask". The entries
  already exist; only the alias strings are missing, which is a smaller ask
  than the one he declined, but it is still his.

---

## What Did NOT Work (and why)

- **Clicking "Save corrections to memory" to verify the new build:** the old
  build saves immediately, so the click fired a real
  `POST /api/runs/51a22ad72864/commit-memory` against Criss's live September
  month. The rule this establishes: prove the published bundle carries the new
  build before driving any control whose OLD behaviour is a write.
- **A padded commit SHA in the Fly build argument:** I passed
  `dedd7260...00000000`, an invention, which would have made `/healthz` report
  a commit that exists nowhere and defeat the item-120 build stamp. Caught
  before it landed; the deploy was stopped and redone with the real
  `dedd726002e4eec37428744aed142571e7731e81`.
- **A Portuguese verification drive that silently stayed in English:** it
  reported English strings as Portuguese. Fixed by setting the language the
  way the app stores it and proving the switch with a control string before
  believing any assertion.
- **Case-sensitive needles on the Memory page:** reported the Categories and
  Aliases sections missing while the page rendered "LEARNED CATEGORIES", the
  same trap as the 2026-09-18 "Guess"/"GUESS" incident.
- **Asserting the month list on the page sign-in lands on:** sign-in lands on
  the new-batch screen; the months list is its own route `/months`. An
  instrument fault that read exactly like a broken deploy.
- **`regress_check.py` with an MSYS-style `/c/Users/...` path:** the baseline
  reads RED with "no pytest summary line" and exits before mutating anything.
  Windows `C:\...` paths work.
- **A five-reader, five-skeptic workflow on Fable:** the readers finished;
  four skeptics and the synthesizer died on the model usage limit, so the run
  returned a null brief while its summary still listed five readers OK.
  Resuming the same script on Opus replayed the readers from cache.
- **Editing a client status file on the docs branch:** the branch-isolation
  gate stopped it at the first Edit. Recovery cost a patch archive, a fresh
  client worktree and a three-way apply, because `origin/main` had moved five
  commits and the straight apply failed on context.
- **A checkpoint folder name containing a colon:** illegal on Windows,
  `ENOTDIR`.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/learning/commits.py` | added | RecordingStore, planned writes, apply_plan, registry_diff |
| `src/expense_recon/learning/store.py` | edited | `read_row` / `restore_row` plus the table-key validator |
| `src/expense_recon/web/service.py` | edited | `store_factory` seam, `plan_month_memory`, pre-image, `undo_memory_commit` |
| `src/expense_recon/web/store.py` | edited | `memory_journal` table and its six accessors |
| `src/expense_recon/web/app.py` | edited | three memory routes; the commit route returns `journal_id` |
| `tests/test_memory_journal_item_163.py` | added | 10 route-level tests |
| `docs/api-contract.md` | edited | the plan / journal / undo section and three error codes |
| `docs/lovable-memory-journal-prompt.md` | added | SPA half, now Applied |
| `docs/PROMPT-STATUS.md` | edited | the prompt row moved to Applied with drive evidence |
| `status/p1-improvement-backlog.md` | edited | the learning-loop section, then the attribution measurement with items 169 and 170 |
| `status/p1-expense-reconciliation.md` | edited | attribution element row; item-163 row corrected to shipped, deployed and applied |
| `.claude/patterns/warn-padded-commit-sha.md` | added | a SHA with eight trailing zeros is padded, not real |
| `.claude/patterns/warn-spa-write-button-click.md` | added | gate a Save/Commit/Refresh click on bundle-first proof |

---

## Current Status

Item 163 is live and verified in both languages. The two weakest matching
areas are measured and recorded as items 169 and 170, both gated on an
instrument that has to be written first. Nothing from this session is
in flight; five PRs merged (#1202, #1204, #1208, #1214, #1215) and both
worktrees are removed.

Brisken ops status: `infrastructure.yaml` carries no platform plan or
assessment date for this client, so the pre-flight reads "unknown plan".
Worth a feasibility line the next time the file is touched.

---

## Next Steps

1. Build the committed replay instrument for card, entity, person and
   category, proved with a fabricated rule the way item 115 was.
2. Item 169, the card chain's four refused-evidence points, each measured
   before it is changed.
3. Item 170, keying learned rules on the registry canonical rather than the
   raw vendor string.
4. Items 164, 165 and 166, and the unitemized notes #73, #74, #75, #77, #82.
5. `p2-product-decks.md` (62 days) and `p2-targeting.md` (63 days) have been
   flagged stale in four consecutive checkpoints. A p1 session cannot write p2
   state without inventing it, so the honest resolutions are a p2 session or a
   deletion, not another next-step line.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md`, the section
  "Attribution and categorization, measured before the next round (2026-09-23)"
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py:6488-6603`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/categorize.py:297-522`
- `docs/2026-09-23 - Attribution Measured Card Entity Person And Category/Mini-Checkpoint-1.md`,
  whose second half is the continuation prompt

### Open Questions

- May an unvalidated Zoho-seeded rule beat a line read? Unruled since item 115;
  all 102 seeded rules remain validated 0.
- Cards 9693 and 1176 have never had a statement loaded (item 108), which is
  why September's OpenAI receipts cannot attribute at all. Coverage, not code.
- The alias lists on the four AI merchants: the entries exist, the aliases are
  empty, and filling them is a live settings write and therefore the owner's.
- No month has ever been published by Criss, so the learning loop has still
  never run on real data.
- The brisken comms-log has not been touched since 2026-09-08.

### Working Notes

The five reader reports from the grounding workflow are extracted under the
session scratchpad as `wf/read_*.md` and `wf/verify_category-chain.md`; they
carry every file:line pointer behind the prompt's claims. The skeptic that
survived the model limit refuted exactly two facts, and both were the ones
taken from the backlog rather than from the live API: July's line-source mix
had moved since 2026-09-17, and the registry had grown from 28 merchants to
33. That is the pattern worth carrying forward: in this repo, a backlog number
older than a week is a prior, not a reading.

### Reference Materials

- PRs #1202, #1204, #1208, #1214, #1215
- Fly commit `dedd726002e4eec37428744aed142571e7731e81`

---

## How to Continue

Paste the continuation prompt from the mini-checkpoint into a fresh session.
It opens with `/comd_resume brisken` and carries the live picture, both
chains with code pointers, the ruled-out list and the session loop.

---

## Strategic Feedback

### What Worked Well This Session

- **The feature fixed the incident it was built for, within the hour.** The
  accidental live write was undone by the undo route shipped the same session,
  and the journal entry that proves it is the only entry on the live Memory
  page. That is a stronger demonstration than any test.
- **Adversarial verification earned its cost on the first run.** Of 20-odd
  reader facts, the skeptic refuted exactly two, and both were stale backlog
  citations that would have shipped into the handover prompt as current state.
- **Measuring before ranking changed the order of work.** The one-`learned`-row
  measurement is what put note #81 ahead of the three notes that sound more
  substantial, and the same discipline is now the gate on items 169 and 170.

### Suggestions

- **The bundle-first rule wants a real gate, not a warning.** The pattern rule
  added today fires on the Playwright source text, which catches the shape I
  used but not a click driven through the MCP browser tools. The durable
  version is a helper in `tools/` that fetches the published bundle, asserts a
  caller-named marker, and refuses to return a page object otherwise, so the
  proof is a precondition of driving rather than a habit.

### System Health

- Autonomy: 1 human intervention, and it was solicited (the undo decision, put
  through `AskUserQuestion` with a recommendation after the read-only half of
  the work was already done). Everything else was new instruction, not
  correction.
- The friction register is at 323 KB with nothing yet archivable, because no
  resolved row has aged past the shortest sanctioned window. It will need the
  30-day split within a week or two at the current rate.
- Four of this session's five hook candidates were heredoc-size blocks on git
  commit messages, a legitimate use the gate cannot distinguish from a Python
  payload. It costs a turn each time and is worth a carve-out for `git commit
  -F -`.
