# Checkpoint: Brisken Recon Item 104 Decision History

**Date:** 2026-09-18
**Status:** Item 104's history half shipped (PR #1081, Fly v180) and recorded (#1082); credential half declined by the owner

---

## Summary

Item 104 was the highest-ranked unshipped item in the voids audit, and the
session's two most valuable acts were both corrections to what it claimed:
its "four write points" were twelve, and my own first cut carried a data-loss
bug that an adversarial reviewer found and I had not. Every verdict in the
tool now leaves an append-only line saying who changed what, from what, when
and why.

---

## What Was Done This Session

### Item 104, the decision-history half
1. New pure `web/decision_history.py`: what a line is, whether a write moved
   anything, how it reads in English, what putting it back would mean. An
   append-only `decision_history` table beside the decisions.
2. `GET /api/runs/{id}/history` (newest first, `limit` / `before_id` /
   `row_key`, and `n_entries` follows the filter) plus
   `POST .../history/{entry_id}/undo`.
3. `who` is the label inside the SIGNED SESSION TOKEN, never `_operator()`,
   which reads the server's environment. That is the confusion the item is
   named for: Criss's feedback notes read `operator` while the developer's
   read `matthias`.

### The enumeration that changed the scope
1. The item's text said "the four write points". Enumerating every
   `set_decision` / `set_disposition` / `set_category_override` /
   `set_duplicate_resolution` call in `src/` and classifying each found
   **twelve** reviewer-driven sites.
2. Three of them would have shipped silent: accepting the tool's category
   guess (note #62), the expense-field category edit, and attaching a mailed
   receipt by hand (which records a confirmed decision). Closed in a second
   commit, wired at the ROUTE so `service.py` stayed untouched.
3. Deliberately not recorded, and stated in the contract: `set_tool_decision`
   (the matcher's own re-match writes) and header-field corrections (vendor,
   date, total), a data edit rather than one of the five verdicts.

### The adversarial review, which found the bug I could not
1. Fifteen findings against the committed SHA. The one that mattered:
   `_category_value` collapsed "no override at all" and "an override with an
   account but no category" into the same `None`, so the undo guard compared
   a moved row as equal to a stale line, **allowed the undo, and destroyed a
   later account pick** — precisely the harm `history_superseded` exists to
   prevent. The same collapse meant an account-only pick recorded no line, so
   the ledger could not even show what was lost.
2. Also real: `isinstance(err, str)` is always true because `Refusal` IS a
   `str`, so the 409 arm was dead and R4 conflicts answered 400 against both
   docs; a first disposition advertised an undo that could never work;
   `delete_run` orphaned every history row; `n_entries` showed the month's
   total in the per-row fold; the reader-facing summary said "category
   category".
3. **Three of my tests did not bite.** `confirm-ready` asserted `0 == 0`
   (its fixture confirmed nothing); the gate test's 401 comes from middleware
   that answers before routing, so it passed with both routes deleted; and my
   own first attempt at the summary test used a needle that could not match.

---

## Key Decisions Made

### Record the change, withhold the undo, where undoing would leave the month inconsistent
- **Choice:** A duplicate ruling gets a history line but no one-click undo.
- **Rationale:** The ruling decides what the matcher's pool holds, so the
  resolve route re-matches the month after writing it (item 56). An undo that
  wrote the old ruling back without that re-match leaves a month whose ruling
  says one thing and whose pairs reflect the other. It is reversed by making
  the opposite ruling, which re-matches properly.

### Refuse an undo rather than silently overwrite
- **Choice:** `history_superseded` unless the row still holds exactly what
  that line left there.
- **Rationale:** A line says "A became B"; writing A back over a row that has
  moved to C throws the later work away without telling anyone. The reader
  who clicked undo on Tuesday's line would have reverted Thursday's work.

### Write the review's findings as tests BEFORE fixing them
- **Choice:** Seven tests added red, then fixed, then watched go green.
- **Rationale:** A fix whose test has never been seen to fail has been
  asserted, not verified. Four were red on the reviewed tree, which is the
  only evidence the fixes are wired to anything.

---

## What Did NOT Work (and why)

- **Driving `brisken-expense-recon.fly.dev` as the browser consumer:** the
  Fly app serves the API and answers the root with
  `{"error":"authentication required"}`; there is no login form on it. The
  SPA is a separate Lovable deployment at `expenses.brisken.com`, which is
  what has to be driven. Two calls lost assuming the deployed app was the
  screen.
- **`input[type=password], input[type=text]` as the sign-in selector:** the
  SPA's field is `input#code`. The generic locator timed out at 30 s.
- **Letting the deploy-consumer-gate's "[CONSUMER DRIVEN] ... closed"
  advisory stand as evidence:** it printed that for the Playwright run that
  had just died with a `TimeoutError` having asserted nothing. The gate reads
  the command's SHAPE, not its exit status, so a failed drive closes it. The
  2026-09-15 tightening (foreground, state-reading verb, "not reporting
  failure") has that hole.
- **A standalone Python probe for the finding-1 repro:** the receipts path
  needs the test harness's LLM stub (`receipts.source 'folder' needs an
  `llm:` block`), so it was written as a pytest test instead, which was the
  better artifact anyway.
- **Polling `gh pr checks` and the suite file by hand:** ~15 calls and an
  `iteration-3x` gate fire. Background waiters were already registered and
  would have notified.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../src/expense_recon/web/decision_history.py` | create | The pure half: line shape, change detection, English rendering, undo eligibility |
| `.../src/expense_recon/web/store.py` | edit | `decision_history` table + append / list / count / get / mark-undone; `delete_run` clears it |
| `.../src/expense_recon/web/app.py` | edit | Twelve write sites, two routes, the helpers, the review's fixes |
| `.../tests/test_decision_history_item_104.py` | create | 36 tests, route-level, two named operator codes |
| `.../docs/api-contract.md` | edit | The item 104 section |
| `.../docs/lovable-decision-history-prompt.md` | create | The SPA fold + Undo button, EN + PT, NOT pasted |
| `status/p1-improvement-backlog.md` | edit | Heading, Shipped paragraph, Shipped row 86 |
| `status/p1-expense-reconciliation.md` | edit | Element row |

---

## Current Status

Live on Fly v180. Both routes answer on July, August and September; an
unknown month still 404s, so an empty read is a fact rather than a missing
route; the `row_key` filter and its count follow each other; the undo route
is registered. Every live month reads `entries: []`, the honest answer for a
period nothing recorded. The SPA was driven cold at `expenses.brisken.com`:
July's matching page and expenses grid render (57 table rows), no fallback
strings, no console errors, which is what proves the nine changed route
handlers did not break Criss's screens.

Module suite 2476 passed / 2 skipped, exit 0; CI green on all seven checks,
including the module suite in a clean environment. PRs #1081 and #1082
merged; all three worktrees removed.

brisken platform line from `pre`: unknown plan, `~?/?` ops/mo, last assessed
`?`. Comms-log 10 days stale.

---

## Next Steps

1. Any new `/feedback.jsonl` note past #69, Criss's first. None as of today.
2. **Item 127** is the strongest of what remains: the matcher's accuracy
   scorer runs by hand and nothing runs it before a deploy. Note that CI DOES
   now run the module suite (`expense-recon-tests.yml`), which the
   parallel-round protocol doc still says it does not — worth correcting
   there while building 127.
3. Items 123, 125, 128 (operations, in scope under the reversal).
4. Item 126 is an owner action: Criss closes one month unaided, timed.
5. Items 108, 118, 129 and item 121's remaining half wait on owner data or a
   UI paste.
6. Watch for item 132's drift advisory on July's next re-match.
7. The deploy-consumer-gate closes on a FAILED browser command; tightening it
   to require a zero exit is a small, high-value fix.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  (the item 104 section carries the twelve-site table and the undo refusals)

### Open Questions
- Does the owner want the SPA History fold built now?
  `docs/lovable-decision-history-prompt.md` is written and NOT pasted; until
  it is, nothing on screen shows the ledger.
- The machine's own re-match writes are not recorded. The triggers exist in
  the vocabulary; wiring them means threading a `who` through the matcher.

### Working Notes
- **Owner ruling 2026-09-18: item 104's credential half (Criss's named code,
  deleting the shared code, rotating the signing secret, session expiry) is
  left entirely for now. Do not re-ask.** Lines written from a shared-code
  session read `operator`, which is the truth about a shared code.
- The SPA is `expenses.brisken.com`, NOT the Fly domain. Sign-in field is
  `input#code`; the operator code is vault entry "Brisken recon operator code
  matthias".
- These module sources are CRLF. Patch with `read_bytes` / `write_bytes`; a
  literal `\n` anchor matches zero times and text mode flattens the file.
- The append path was not exercised on the live instance, because that needs
  a write to one of Criss's months. What the live 200 DOES prove is that the
  table was created on the live volume: a missing table raises `no such
  table` and 500s.

### Reference Materials
- PRs #1081 (the build) and #1082 (the record); Fly v180
- `%TEMP%\claude\recon-probe\api.py` for authenticated GETs
- `%TEMP%\claude\...\scratchpad\drive_spa_104.py` for the cold SPA drive

---

## How to Continue

Read `/feedback.jsonl` first; a new note from Criss outranks everything. If
nothing new has landed, item 127 is the strongest remaining item and needs no
scope question under the owner's build-it-all reversal.

---

## Strategic Feedback

### What Worked Well This Session
- Enumerating the write sites instead of trusting the item's own count. The
  item said four; there were twelve, and three of the three I found last
  would have shipped a ledger with invisible holes, which is worse than no
  ledger because it gets trusted.
- Committing before dispatching the adversarial review, per the previous
  session's suggestion. The reviewer read a fixed SHA, never re-verified
  hashes, and its one HIGH finding was a real data-loss bug.
- Writing the review's findings as failing tests before fixing them. Four
  went red then green; that is the difference between a fix and a claim.

### Suggestions
- The deploy-consumer-gate should require the browser command to EXIT ZERO
  before it prints "[CONSUMER DRIVEN] ... closed". Today it closed on a
  Playwright run that had died with a `TimeoutError` having asserted nothing,
  and its own advisory then reads back as evidence. This is the second
  recorded instance of the gate closing on something that proves nothing
  (2026-09-17 was the first), so the 2026-09-15 tightening has a hole that is
  one `returncode` check wide.

### System Health
- **Autonomy: 1 human intervention** (the owner's ruling on item 104's
  credential half, which was correctly a decision rather than something to
  take).
- Sibling contention was free this round: three merges of `origin/main`, zero
  conflicts, because the item's code lives in its own new module and its
  ledger edits went through a docs worktree.
