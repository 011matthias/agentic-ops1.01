# Checkpoint: Expense-Recon xlsx Sign Defect and Statement Re-read

**Date:** 2026-09-11
**Status:** Shipped (PR #805, Fly v114) and both live months repaired; a ten-item void list is queued for a fresh session, starting with items 1 and 2.

---

## Summary

Criss reported that the August month "sees the receipt but never links it to the charge". Root cause: the Excel statement parser kept Chase's printed sign (purchases negative) while the CSV parser had canonicalized it since 3.15, so every charge reached the matcher as -15.00 against a 15.00 receipt. Fixed the parser, mapped Chase's `Type` column, made an entity-less receipt unscoped in the matcher, added a statement re-read route, and ran it on July and August live: August 0 -> 14 reconciled + 7 review, July 0 -> 24 + 15.

---

## What Was Done This Session

### Diagnosis (read-only, before any code)
1. Pulled both workbench views off the live API: July `50622baec444` 112 charges / 50 receipts / 0 reconciled, August `074a7b8905d7` 111 / 31 / 0, every row `pending` with zero candidates, exact same-day same-amount pairs present (LOVABLE 15.00 on 08-31, OBSIDIAN 96.00, ZOHOCORP 576.00, PRESSMASTER 135.00).
2. Pulled `August2026.xlsx` and `July2026.xlsx` off the Fly volume (`flyctl ssh sftp get`, `MSYS_NO_PATHCONV=1`): Chase multi-card export, `Type` = Sale/Payment, 110 of 111 amounts negative, `refunds` empty on the stored run.
3. Confirmed in code: `statement_xlsx.py` had neither the Type-column path nor the majority inference that `statement_csv.py` carries; `guess_column_map` never mapped `type`; `match_month` dropped any receipt whose entity differed from the charge's (23 of 31 August receipts and 46 of 50 July receipts carry entity `""`).
4. Offline A/B on the real files with the live receipt list: 0 matches as stored; sign fixed alone unlocks only the 8 named-entity receipts; sign + unscoped empty entity unlocks the rest, with the invoice+receipt pairs landing as ambiguous.

### Fix (PR #805, merged on green CI, deployed v114 from a detached origin/main worktree)
5. `ingest/statement_xlsx.py`: both 3.15 paths, mirrored from the CSV sibling; `is_credit` follows the canonical sign.
6. `inspect.guess_column_map`: `type` on `^type$` / `^transaction type$` only (an `Account Type` column would abs() every credit).
7. `matching/deterministic.py`: empty entity on either side is unscoped; a receipt naming another entity still never pairs (existing test untouched).
8. `POST /api/expense-batches/{id}/statements/reread` + `service.reread_statements`: rebuilds the charges from every `statements[]` file in upload order and REPLACES the set inside `rematch_month` (new kwargs `replace_statements`, `rekey_decisions`); decisions carried over by sheet row via `statement_anchors`; refuses with nothing written on a missing file, an unresolvable map, a stranded decision, or an upload that landed mid-read. `store.rekey_decisions` added.
9. `fly.toml` in the module re-synced to `flyctl config show` (always-on both services, `recon_data_v2`, 1024 MB); it still said scale-to-zero, `recon_data`, 512 MB and would have undone the 2026-09-10 recovery on deploy.
10. Tests: suite 1511 -> 1523; `test_statement_reread.py` (route-level: attach a Chase workbook and match, repair a month stored with printed signs, late receipt still reconciles after the repair, missing file refuses, no statement is 400); three `tools/regress_check.py` proofs (Type path, majority inference, entity rule) RED under mutation, green restored.
11. `docs/api-contract.md` section for the re-read; status file and backlog (items 55, 56; Shipped row 31) updated in the same PR.

### Live repair + verification
12. Distinguishing probe after deploy: the new route answers 400 "no statement to re-read" on January (old code would 404). Platform config verified intact after the deploy (mount, always-on, 1024 MB, release v114).
13. Re-read on August (job done 14:24:46Z) and July (done 14:26:15Z). Ids changed on every row, one negative amount left per month (the card payment, now in refunds), `statements[]` kept the original upload record, no doubling.
14. Consumer drive on both SPA workbenches (agent-browser, session `recon-fix`, operator login): August tiles MATCH RATE 12.6% / RECONCILED 14 / REVIEW 7 / UNMATCHED TX 89 / UNMATCHED RECEIPTS 7; July 21.4% / 24 / 15 / 72 / 9; rows show real candidates with Confirm/Reject (ZOHOCORP 576.00 <-> "ZOHO Corporation 99% 576.00 USD", HOSTINGER 172.61 <-> "Hostinger 99%"); zero fallback strings.

### Brainstorm (owner ask, after the fix)
15. Ten functionality voids grounded in today's data, ranked (see Working Notes). Owner picked items 1 and 2 first, then redirected: work the whole list in a fresh chat.

---

## Key Decisions Made

### Repair by re-read, not re-upload
- **Choice:** a new operator route that re-parses the stored statement files and replaces the month's charge set.
- **Rationale:** `transaction_id` derives from the canonical amount, so a re-upload of the same file after the parser fix folds 111 corrected rows in beside the 111 wrong ones. The re-read is the only path that does not double the month, and it carries reviewer decisions over by sheet row.

### Empty entity is unscoped, not a mismatch
- **Choice:** `match_month` skips the entity check when either side is `""`.
- **Rationale:** mailed and dropped receipts carry no entity until a card hint or the reviewer names one; the strict inequality made every one of them unpairable, which contradicts the owner's stated flow (injected receipts reconcile against the month's statement). The classic `reconcile()` path stamps the config entity on every receipt, so nothing changes there.

### The two live months were rewritten without a separate ask
- **Choice:** ran the re-read on July and August as part of "it needs an immediate fix".
- **Rationale:** the fix is inert for Criss without it; the operation rebuilds charges from files that stay on disk, deletes nothing, changes no receipt, and both months carried zero reviewer decisions (verified before running). Reported plainly with the before/after counts.

### Item 56 left unbuilt
- **Choice:** invoice+receipt pairs stay ambiguous; Criss picks one.
- **Rationale:** collapsing a duplicate group to one candidate in the matcher pool changes what the matcher sees and needs an owner ruling on unresolved groups; the pairs are visible with candidates, which unblocks her today.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/statement_xlsx.py` | edit | sign canonicalization (Type path + majority inference) |
| `.../src/expense_recon/inspect.py` | edit | `type` column heuristic |
| `.../src/expense_recon/matching/deterministic.py` | edit | empty entity unscoped |
| `.../src/expense_recon/web/service.py` | edit | `reread_statements`; `rematch_month` gains `replace_statements` + `rekey_decisions` |
| `.../src/expense_recon/web/store.py` | edit | `rekey_decisions` |
| `.../src/expense_recon/web/app.py` | edit | re-read route + background job |
| `.../tests/test_statement_reread.py` | new | route-level tests for the parser fix and the re-read |
| `.../tests/test_statement_xlsx.py`, `test_inspect.py`, `test_deterministic_matching.py` | edit | parser / guess / matcher tests |
| `.../docs/api-contract.md` | edit | re-read endpoint contract |
| `.../fly.toml` | edit | mirrors the live platform config |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | 2026-09-11 paragraph, elements row, fly.toml correction |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | items 55, 56; Shipped row 31 |
| memory `project_brisken_expense_recon_usability_loop.md`, `project_brisken_expense_recon_fly_hosting.md`, `MEMORY.md` | edit | outcome + the fly.toml correction |

All repo edits merged in PR #805 (`a7cb072d`).

---

## Current Status

brisken platform: unknown plan, ~?/? ops/mo. Last assessed: ? (no `platform` section for the FastAPI app; Fly is the host).

Backend live at v114 with the parser fix, the entity rule, and the re-read route. July and August 2026 repaired and rendering in the SPA. Criss's remaining work on those months is deciding the review rows and the ambiguous invoice+receipt pairs. The sibling `client/brisken/p1-cost-centers` branch (worktree `agentic-ops1-cc`) touches `service.py`, `app.py`, `store.py` in other regions; expect a small merge when it lands. The July receipt PDFs found on 2026-09-11 still wait for the owner's ingest go.

---

## Next Steps

1. Fresh session: work the ten-void list (Working Notes), items 1 and 2 first: readiness refuses a month whose match rate is zero with exact pairs in the pool, and every re-match sends the dev one line with the counts. Append the list as backlog items 57-64 before building.
2. Item 3 needs an owner ruling before code: how charges on cards missing from the registry should post (blank entity vs the upload's entity).
3. Item 56 needs an owner ruling: may an unresolved duplicate group be collapsed to one candidate automatically.
4. Four p2 status files are stale (82d / 50d / 51d / 51d); a p2 session should update or delete them.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 55, 56, Shipped row 31)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("Re-reading a month's statements")
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`reread_statements`, `rematch_month`, `rematch_after_change`)
- memory `project_brisken_expense_recon_usability_loop.md` (2026-09-11 paragraph)

### Open Questions
- Item 3: post charges on unknown cards to a blank entity, or keep inheriting the upload's account entity? (77 of August's 111 charges are on cards 3645 / 3876, both absent from the registry, all stamped Corporate Services today.)
- Item 56: auto-collapse unresolved duplicate groups in the matcher pool, or only after the reviewer confirms?
- Which route for the 19 July receipt PDFs: direct ingest or forward the mail to expenses.brisken.com?

### Working Notes

**The ten voids (ranked; 6 = backlog item 56, 7 relates to the re-read).**

1. `ready_to_post` was `true` on August with 0 of 111 matched and 31 receipts in the pool. Readiness checks undecided rows and unmapped accounts only. Rule to add: zero match rate with N exact same-day same-amount pairs present means sign / entity / currency is broken; refuse readiness and say which.
2. No notification on living-month re-matches. `tools/brisken-recon-notify.py` pings on new runs only; attaches, re-reads and mail-driven re-matches report nothing. One line per re-match ("August: 0 of 111, pool 31") to the dev.
3. A multi-card workbook stamps every charge with the upload's entity. `account_id` card-2838 -> all 111 rows Corporate Services, while `coverage[]` shows 3645 (40 charges) and 3876 (37) as "not in your card list", entity blank. Per-row entity from the parsed card column via the registry; unknown cards blank.
4. A charge with waiting candidates renders "No receipt found". LOVABLE 25.00 on Aug 5: bucket `unmatched`, candidates [0027 ambiguous, 0028 exact]; SPA prints "No receipt found" while both receipts show elsewhere as "Awaiting decision". Bucket or label is wrong.
5. Receipts routed by receipt date never meet a charge posted in the neighbouring statement period. August's workbook starts 07-31, July's 06-30; a receipt dated the 31st goes to that calendar month's batch and never sees the next statement. Trips borrow across batches (R4); adjacent company months do not.
6. Invoice + receipt for one purchase -> ambiguous (item 56). 23 of August's 31 receipts sit in such pairs; duplicate resolution is display-only.
7. A repaired parser cannot repair the months it already parsed except through the curl-only re-read. A parser fingerprint per `statements[]` entry (as the extraction cache does for vision) would let the app flag or re-read stale months itself.
8. Receipts that will never appear on a card statement (bank transfer, cash, PayPal; the Lovable invoice reads "Pay with a bank transfer") stay unmatched forever. A "settled outside the card" disposition.
9. Same-currency candidates use the 20% probable band meant for FX pairs: ADOBE 16.23 offered a Lovable 15.00 receipt, ANTHROPIC 104.95 an Obsidian 96.00 one (offline run). Same currency + different amount + different vendor should not be a candidate.
10. Two small ones: `statements[]` does not record the column map / card currency an upload used, so a re-read re-guesses; and an unrecognized `Type` label is treated as a purchase and abs'd (a German "Lastschrift" export would flip credits), so unknown labels should keep the printed sign.

**Traps met today.** Playwright MCP wants Edge CDP on :9222 and was not running; agent-browser (`--session <name>`, `agent-browser close --all` if a session hangs) is the drive that works. `gh pr create` needs the slug `011matthias/agentic-ops1.01` or no `--repo` at all. `uv run python -c` in the module lacks fastapi (it is the `web` extra); pytest via `uv run --directory <module> pytest` resolves it. The 2026-09-10 memory said no `fly.toml` exists in the repo; a stale tracked one did, and a source deploy from the module ships it. The re-read on the hosted run pays the LLM judgments again because the judgment cache keys on transaction ids (cents, not a defect worth fixing alone).

**Measured, for reuse.** Offline on the real August file through the fixed parser: 5 exact + 4 FX judgment + 23 charges with candidates, 7 receipts unmatched; live after the re-read (hosted LLM judgment resolved several pairs): 14 reconciled + 7 review, 7 receipts unmatched.

### Reference Materials
- PR #805 https://github.com/011matthias/agentic-ops1.01/pull/805
- Live API `https://brisken-expense-recon.fly.dev` (operator code in vault "Expense Recon App"); SPA `https://expenses.brisken.com`
- Re-read: `POST /api/expense-batches/{id}/statements/reread` -> `{job_id}`; poll `GET /jobs/{job_id}`

---

## How to Continue

`/resume brisken`, read the backlog items 55-56 and the void list above, cut `client/brisken/p1-recon-voids` off `origin/main` in a worktree, append items 57-64 to the backlog, then build items 1 and 2 (readiness rule + re-match notification) with route-level tests and a `regress_check.py` proof each, PR, CI-green merge, `flyctl deploy .` from the module directory of a detached origin/main worktree, drive the SPA.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the live records first (both workbench views, then the actual workbook off the volume) put the cause in the parser within minutes and kept the fix away from the receipt-hunting the previous checkpoint was doing for the same symptom.
- The offline A/B on the real August file with the live receipt list separated the three blockers (sign, Type guess, entity scope) and sized each before any code.
- `regress_check.py` on all three fixes plus a route-level test file meant the suite was seen to fail for each change, not just pass.

### Suggestions
- Build void 1 next: a readiness gate that cannot say "ready" on a zero-match month would have made the 2026-09-10 upload visibly broken the same day. It is the structural version of this session's diagnosis.

### System Health
- Autonomy: 1 human intervention (the owner's pick on the void list, then a redirect to a fresh chat). Gates: B1:1 (stop hook on the brainstorm closing) B2:4 (three regress proofs + two SPA drives) B3:1 skipped:0.
- One memory was wrong (no `fly.toml` in the repo) in a way that could have regressed the platform config on deploy; corrected in the memory and in the file. Memories that assert absence deserve a `git ls-files` check before being acted on.
