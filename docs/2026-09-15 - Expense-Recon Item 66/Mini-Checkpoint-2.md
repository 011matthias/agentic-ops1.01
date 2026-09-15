# Mini-Checkpoint: Expense-Recon Item 66

**Date:** 2026-09-15
**Status:** Shipped (PR #846, merge 75e46ba8, Fly v126) and driven live
**Type:** mini

---

## Summary

The last two paths that rewrote a whole period record from a stale copy, with
no lock and no re-read, now commit under `_BATCH_ADD_LOCK` against a fresh
one; and the two writes that destroyed stored bytes now archive what they
replace instead. Landing it took a merge override, because GitHub refused to
schedule an Actions suite for either of this session's PRs while sibling PRs
kept getting runs throughout.

## What Was Done

- **The lock.** `attach_emailed_receipt` and `ingest_receipts_folder_into_run`
  each read the period record, then worked for seconds to minutes (a vision
  call; vision over a folder plus the matcher), then rebuilt the entire record
  from the copy they had read. Both now use the `rematch_month` commit shape:
  take the lock, re-read fresh, refuse if the month was deleted, refuse a
  folder commit that would leave a concurrently-uploaded charge in no bucket,
  and carry receipts that arrived mid-flight into the pool as unmatched.
- **The event loop.** `post_manual_receipt` hands the locked span to
  `run_in_threadpool`. The item-18 AST guard named it the moment the lock went
  in, which is the caller-level proof the fix is wired, and it passes now.
- **The bytes.** A re-attach archives every file the charge already holds into
  `manual-receipts/superseded/` under a versioned name before writing, and the
  snapshot records the swap in `receipt_files` (stored only, absent from both
  view payloads, probed). A queued-upload replacement archives every file it
  would destroy, before writing anything, and never unlinks.
- **One correction to the item as written.** It names the same-NAME re-attach,
  but a re-attach under a DIFFERENT name left two files in the `{fs_tx}__*`
  glob that the image endpoint and `_attached_receipt_file` read with
  `sorted(...)[0]`, so the superseded version could be served. A charge now
  holds exactly one current file.
- **Docs.** `electronic-storage-system-description.md` asserted these defects
  as present in five places; rows 3 and 14 of the section-12 table now carry
  the sibling's strikethrough REMEDIATED convention, and the section intro
  states that convention instead of enumerating remediated rows, which item 65
  had already made false and every later sibling would again.

## Current Status

Live at Fly v126. Both live months render clean in the SPA (August workbench
driven cold from the login gate: 1410 text nodes, zero fallback strings, the
per-charge "Attach receipt" control present). The deployed attach handler was
proven to run end to end without mutating anything: an unsupported-type POST
to a live charge returned the code's own `Unsupported receipt file type .txt.`
at 400 while `/healthz` answered in 57 ms, and August's payload was
byte-identical before and after.

Suite 1550 -> 1557 on my base; 1693 passed / 2 skipped on the fully merged
tree. Four regress proofs, each green -> RED -> green.

**The CI anomaly is unresolved and is the one thing worth carrying forward.**
GitHub created no `github-actions` check suite for either PR #833 or #846
across six pushes, a close-and-reopen, a fresh branch, a fresh PR and a body
rewrite, while sibling `client/brisken/p1-item-*` PRs got runs minutes either
side. Actions was enabled, the workflow files on the branch were byte-identical
to main, the PR was open and non-draft with its head matching the pushed ref,
the queue was drained, and commit authorship matched a sibling's exactly. The
owner authorised the merge on the local evidence.

**It was not the clone or the credentials.** This checkpoint's own docs PR
(#854), pushed from the same machine with the same `gh` auth minutes later,
got all five checks immediately. Whatever suppressed the suite was specific to
the two item-66 code branches.

## Next Steps

1. Watch whether a future code PR touching the expense-recon module gets an
   Actions suite. The docs PR proves the clone and the auth are fine, so the
   next datum worth having is whether the suppression follows the paths in the
   diff or was a one-off on those two branches.
2. Items 60, 62, 68 and 69 remain open in the backlog.
3. `p2-lead-gen-general.md` (86d), `p2-product-decks.md`, `p2-rome.md` and
   `p2-targeting.md` (54-55d) are flagged stale by the SessionStart sweep.
   Untouched here; they belong to the p2 workstreams.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (Shipped row 43)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_web_unlocked_write_paths.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/electronic-storage-system-description.md` (section 12)
