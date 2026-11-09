# Checkpoint: WW Out Of The Public Repo

**Date:** 2026-11-09 (work done 2026-11-05)
**Status:** Public tree clean; 13 remote branches and history remain (owner-pending)

---

## Summary

WW material left the public `agentic-ops1.01` for the private `UnpauseAI/ClientSense` repo, moved verbatim and verified before removal; every remaining mention in the public tree is now the bare abbreviation "WW", with no client name, staff name, address or record id.

---

## What Was Done This Session

### Client TOM checklist
1. Checked the TOM annex of WW's data-processing agreement against this laptop; on owner order removed 11 open WLAN profiles. The other gaps and the owner's choices live in local memory `project_ww_takeover`, not here (this repo is public).

### Moved to ClientSense (private)
1. ClientSense #1/#2: 68 files plus 3 patches of never-merged branches, each blob-hash-checked against agentic-ops1@731b97f5.
2. ClientSense #3: 17 WW sessions from 9 day logs and 16 WW friction rows, cut verbatim; every moved Focus/Built/Outcome line and row was checked present on origin/main and absent from the scrub branch before commit.

### Public repo
1. #1736: 50 WW files and the references to them (gated-site registry entry, proxy matcher, vercel rewrites, cspell, INDEX rows). #1737: 18 WW checkpoints.
2. #1738 (ledger): the moved sessions and rows deleted (three WW-only day logs whole), 32 docs files swapped name forms for "WW", staff names for a role, one staff address and the Hero record and type ids dropped; the INDEX section pointer removed.
3. #1739 (rules, tests, `platform/`, UWI, Meji status): same swap; the WW-automations guard in `test_scrub_test_data.py` and its every-PR CI slot deleted (the import it guarded is cancelled); the legacy gate-secret fallback named after the client dropped from `platform/`; the input-classifier scope word is now `ww`.
4. Two pattern rules from this session's slips (see friction).

---

## Key Decisions Made

### The public-tree standard
- **Choice:** no client name form, staff name, address or record id anywhere in the public tree; the bare abbreviation "WW" stays.
- **Rationale:** GitHub code search and casual reading hit the default branch; "WW" is opaque once the name is gone and keeps 300+ ledger lines readable.

### Checkpoint section
- **Choice:** this checkpoint is filed under `system`, not under the client.
- **Rationale:** a client-section checkpoint here would republish what was just moved; WW checkpoints and session logs now live in ClientSense.

### The WW import into this repo is cancelled
- **Choice:** the layout-plan preparation for importing WW (W1-20 guard, items 13-20) is moot; the guard went, the generic scrub tool stays.
- **Rationale:** the owner directive of 2026-11-05 moves WW out, so the guard protected a path that will never exist.

---

## What Did NOT Work (and why)

- **Deleting the 13 `docs/checkpoint-*-ww-*` remote branches:** the auto-mode classifier denied `git push origin --delete` as Git Destructive twice, the second time right after the owner's explicit "tu es"; not routed around through the GitHub API.
- **`git commit -q -F - @'...'@` in PowerShell:** the here-string arrived as an argument and was read as a pathspec ("did not match any file(s) known to git"), no commit happened and the chained push sent a branch with no new commit. Now `block-ps-commit-herestring-as-arg`.
- **`MSYS_NO_PATHCONV=1 git -C /c/Users/... show rev:path > file`:** git.exe failed "cannot change to" and the redirect left 66 empty copies, caught only by the blob-hash check. Now `block-msys-noconv-git-c-posix-path`.
- **`preflight-hooks.py --full` on this machine:** 15 failures, all in `test_cd_guard`, `test_recon_uptime_workflow` and `test_vercel_as`, because `shutil.which("bash")` resolves to the WSL launcher in WindowsApps; CI on Linux ran the same suite green.
- **First transcript count (185 files):** matched rule text that quotes the client slug; a differential probe on client-only terms gave 64.
- **`pii_scan` as proof the moved set was clean:** reported 0 flagged on a control that also returned 0, so it proved nothing; manual counts were used instead.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| ClientSense #1, #2, #3 | added | WW files, branch patches, sessions, friction rows |
| agentic-ops1 #1736, #1737 | deleted | WW files and checkpoints out of HEAD |
| agentic-ops1 #1738 | edited / deleted | ledger scrub (42 files) |
| agentic-ops1 #1739 | edited | rules, tests, platform/, UWI, Meji status (33 files) |
| `.claude/patterns/block-ps-commit-herestring-as-arg.md` | new | PowerShell here-string commit message |
| `.claude/patterns/block-msys-noconv-git-c-posix-path.md` | new | MSYS `git -C /c/...` empty-copy trap |
| memory `project_ww_takeover.md` (renamed), 10 linking memories, `reference_repo_tooling_gotchas.md` | edited | local state |

---

## Current Status

`origin/main` returns 0 hits for the name forms, staff names and ids across all text files (control: 54 Meji hits in the register); a removed day log fetches 404 without login, a kept one 200; #1739 CI green including the full hook suite. Still public: the 13 WW remote branches (10 fully merged into main, 3 saved as patches in ClientSense) and git history. Ops status: system, no infrastructure.yaml.

---

## Next Steps

1. Owner: run the branch delete (the full one-liner is in memory `project_ww_takeover` and the 2026-11-05 reply).
2. Then remove the 8 local worktrees that hold those branches (`git worktree list`, the `*-ckpt-ww*` and `*-ww-*` paths).
3. Owner decision, outside WW: `workspace/clients/meji-media/status/ops-radar.md` quotes a Meji gate code in plain text in this public repo; rotate or redact.
4. History purge only on a separate owner order (filter-repo plus force push is Band 3).

---

## Context for Next Session

### Files to Read First
- memory `project_ww_takeover.md` (status, contract constraints, open owner actions)

### Open Questions
- Is the Meji gate code in `ops-radar.md` still live?

### Working Notes
- The swap standard is mechanical: name forms to `WW`, slugs to `ww`, staff to a role. Rerun the name-form grep over origin/main before any future WW-adjacent commit; the pattern lives in memory `project_ww_takeover`, not here.

### Reference Materials
- https://github.com/UnpauseAI/ClientSense (private)

---

## How to Continue

Nothing further runs in this repo for WW. WW work resumes from ClientSense plus the akkton clone, per the takeover memory.

---

## Strategic Feedback

### What Worked Well This Session
- Moving verbatim and proving the move (hash, line presence and absence) before deleting anything public, so "nothing lost" was a measured claim.

### Suggestions
- Make the tests that shell out to `bash` resolve Git Bash explicitly (one helper in `hooklib`), so `preflight --full` is trustworthy on Windows instead of failing 15 tests for an unrelated reason.

### System Health
- `block-stop-merge-left-pending` caught two turn-ends on a pending suite/CI, both handed to a background Monitor; the block holds, the Monitor reflex does not.
- Autonomy: 2 human interventions (ClientSense repo created and invite sent; branch deletion left to the owner).
