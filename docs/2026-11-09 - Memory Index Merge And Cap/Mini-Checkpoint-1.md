# Mini-Checkpoint: Memory Index Merge And Cap

**Date:** 2026-11-09
**Status:** Done (index merged, cap warning merged as PR #1744)
**Type:** mini

---

## Summary

MEMORY.md had reached 195 lines (the harness reads 200), one line per memory file. 101 memories were folded into 28 collection files with their content verbatim, and the index dropped to 103 lines. `memory_audit.py --cap-check` now warns at SessionStart from 150 lines.

## What Was Done

- Backup of the whole memory folder to `.scratch/memory-backup-2026-11-09/` (194 files, sha256 identical).
- Merge rule: a memory referenced from a live repo path (rules, agents, hooks, patterns, tools, status files, source) keeps its file name; it either stays alone or becomes the collection host. 19 hosts plus 9 new files (`project_private_disputes`, `project_private_finance_admin`, `project_meji`, `project_harness`, `project_brisken_onepilot_marketing`, `reference_local_machine`, `feedback_prospect_letters_and_pdfs`, `feedback_talking_to_owner`, `feedback_verification_traps`).
- Each former memory is one `##` section: old index title, `Former memory \`stem\`` line (type, modified, originSessionId), old index note, description, body verbatim. Hosts got a top note carrying their former description; sections appended, nothing above rewritten.
- `[[old_stem]]` and `old_stem.md` links in 65 memory files repointed; 12 more files had dash-style `[[name-slug]]` links (from the `name:` field) repointed to real stems; two links to memories that never existed were made plain text.
- Verified: 101/101 deleted files have body + description + metadata inside their target; 0 dead index links, 0 files without index line, 0 dangling memory links in memory or rules; `memory_audit.py` reports 101 files = 101 entries.
- PR #1744 (merged `efa69cf1`): `memory_audit.py` `index_line_count` / `cap_warning` / `--cap-check`, wired in `wire-hooks.py` SessionStart; tests run the wired args against fixture stores; `regress_check` green to red to green for both the wiring and the threshold; `preflight-hooks.py --full` 2181 passed.

## What Did NOT Work (and why)

- **First `--apply` of the merge script:** aborted on `project_brisken_expense_recon_master_data.md` because the file has CRLF line endings and the frontmatter regex expected `\n`. Aborted before any write (hash check confirmed); fixed by normalizing line endings on read.
- **Read-based Retire as a shrink lever:** not used. The audit's Retire bucket is "0 reads in 53 days", not "done or wrong"; merging alone reached the target, so no memory was dropped and no owner question was needed.

## Current Status

Memory store: 101 files, MEMORY.md 103 lines / 13.8 KB (was 195 lines / 21 KB). Cap warning on `main`; it reaches a checkout's `settings.json` when that checkout pulls and `wire-hooks.py` self-heals at the next SessionStart. The primary clone is behind `origin/main` and shared with a live sibling session, so it was not pulled here.

## Next Steps

1. When saving a memory: add a section to the fitting collection file first; a new index line only for a new topic.
2. Delete `.scratch/memory-backup-2026-11-09/` once the merged store has been used for a while without a missing-fact report.

## Files to Read First

- `C:\Users\neuma_p1qrsic\.claude\projects\c--Users-neuma-p1qrsic-Repo-agentic-ops1\memory\MEMORY.md`
- `tools/memory_audit.py` (INDEX CAP section of the docstring)
