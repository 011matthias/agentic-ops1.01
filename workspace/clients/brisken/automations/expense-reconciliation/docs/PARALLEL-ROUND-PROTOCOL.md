# Parallel round protocol: one backlog item per session, many sessions at once

Written 2026-09-15, when the owner opened ten backlog items to run as ten
simultaneous Claude sessions (items 61-68, 16, 17), beside a live sibling on
item 47. Every one of them edits `service.py` and the same handful of shared
files, and every one ends in a merge, a Fly deploy and a checkpoint. Without a
single protocol they collide on merge, deploy over each other, mangle the
session log, and leave branches and worktrees behind. This file is that
protocol; each session's prompt points here instead of restating it.

## 1. Scope

- One backlog item per session, by number. The item's text in
  `workspace/clients/brisken/status/p1-improvement-backlog.md` is the spec;
  the live months are the evidence.
- Stay inside your item. If your fix needs a helper another item also needs,
  add a local one; widening a sibling's is a merge conflict in waiting.
- Read first, in this order: this file; your item; `docs/api-contract.md`;
  memory `project_brisken_expense_recon_usability_loop.md` (2026-09-11 and
  later paragraphs); `docs/2026-09-15 - Expense-Recon Void List Round 3/Mini-Checkpoint-2.md`.

## 2. Setup: your own worktree, nothing in the shared tree

```
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-item-{N} C:\Users\neuma_p1qrsic\Repo\agentic-ops1-item{N} origin/main
```

Work only inside `agentic-ops1-item{N}`. The main checkout is shared by live
siblings: never edit, commit or stash there. A hook refuses `cd X && ...`;
use `git -C`, `uv run --directory`, and absolute paths.

## 3. Read the live records before diagnosing

- API `https://brisken-expense-recon.fly.dev`: `POST /api/login {"code": ...}`
  returns a bearer token. The code is the local vault entry "Expense Recon
  App": `uv run C:\Users\neuma_p1qrsic\vault.py get "Expense Recon App"`.
- Live months: August 2026 `074a7b8905d7`, July 2026 `50622baec444`. Read
  both payloads (`GET /api/runs/{id}`, `GET /api/expense-batches/{id}`) and
  say what they actually show against what your item claims. The 2026-09-14
  entity item predicted 77 rows moving and 0 moved; the 2026-09-15
  receipt-taken item no longer reproduced at all. Report that kind of gap,
  then build the fix on a constructed fixture.
- A gap that does not reproduce is not the same as a claim that is false.
  For a matching-class item, grep the human labels first (`notes.csv` /
  `labels.csv` in the main clone's gitignored
  `context/expense-reconciliation/expense-reports/csv/by-month/*_live_*`)
  and read the printed document the item names. If every named instance is
  refuted AND the proposed rule, measured on both live payloads, surfaces
  only pairs the labels call wrong, do not build: close the item with the
  evidence and the condition that would reopen it. Item 54 (2026-09-15) was
  both: its two "OCR date misreads" were read correctly, and its rule
  flagged only recurring same-amount subscriptions.
- Reads are autonomous. A synthetic receipt dropped into a live month is
  deleted in the same session, no exceptions. Any production mutation beyond
  a deploy (a refresh, a reset, a TEST batch, a manual match on Criss's data)
  needs a per-action yes: put it through `AskUserQuestion` as a decision with
  a recommendation and its consequence, never as "say the word".

## 4. Build

- Parallel-field contract (`docs/api-contract.md` rule 1): add fields, never
  retype; absent, not null. Pin every new list field in
  `tests/test_view_contract.py` and document it in `docs/api-contract.md` in
  the same PR. Existing counts keep their one question.
- Tests are route-level, through the FastAPI app, and at least one runs
  through the CALLER the fix changed, not only the helper it added.
- One `tools/regress_check.py` proof per fix, run from the repo root:
  `uv run tools/regress_check.py --test "<suite cmd>" --file <src> --replace "<wired>" --with "<disabled>"`.
  The mutation must change behaviour; `x = None or f()` reported TEST BITES
  on 2026-09-14 while proving nothing. Single-line mutations only; a
  multi-line literal matches zero times.
- Module suite:
  `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q`
  (1550 tests at round-3 close). **CI does not run this suite** (`ci.yml` runs
  hooks, platform, spell, Playwright, lead-desk). A green PR proves nothing
  about the module; your local run, its count before and after, and the
  regress line are the evidence. Put all three in the PR body.
- `.jpg` fixture names carry JPEG bytes through vision; `.pdf` names with
  JPEG bytes skip vision and fall back to a filename vendor (2026-09-14
  duplicate-collapse fixtures).
- Ruff in CI covers `tools .claude/hooks tools/tests` only. `uvx ruff check`
  on the module is courtesy; the 6 pre-existing errors in `cli.py` and
  `coa_gate.py` are not yours.

## 5. Shared files: append, never reflow

`web/service.py`, `web/app.py`, `tests/test_view_contract.py`,
`docs/api-contract.md`, `docs/PROMPT-STATUS.md`,
`status/p1-improvement-backlog.md`, `status/p1-expense-reconciliation.md`.
Add new functions, sections and rows at the END of the relevant block, table
or list. Do not renumber, re-sort, reformat, or move existing lines. Ten
textual merges stay clean only if nobody touches the lines between them.

## 6. Ship

- Band 1 / Band 2 as always: commit on the item branch, push, `gh pr create`,
  merge when CI is green. The backlog (your item moved to Shipped with the PR
  number, Shipped row appended at the top of the table) and the status file
  land in the SAME PR.
- Before the FIRST push: `git rebase origin/main` is free. After any push:
  `git merge origin/main`, never rebase, never force-push (Band 3). Re-run
  the module suite after every merge from main; a sibling has probably
  landed in `service.py` since you branched.
- `gh pr merge --squash --delete-branch`. `gh pr checks` can return the
  previous run's results before the new run registers; re-check after a push.
- If a merge conflict lands in a shared file, keep both sides (they are
  appends) and re-run the suite. Do not drop a sibling's lines.

## 7. Deploy: one Fly app, many mergers

Fly deploys are pre-authorized (memory `feedback_fly_deploy_preauthorized`).
Only `origin/main` is ever deployed, so a sibling's deploy after your merge
carries your commit too.

1. After the merge, probe the authenticated API on a live month for YOUR new
   field. Present: already live, skip the deploy and say which release
   carried it (`flyctl releases -a brisken-expense-recon`). Absent: deploy.
2. Deploy from a fresh detached worktree, never from the item branch:
   `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add --detach C:\Users\neuma_p1qrsic\Repo\agentic-ops1-deploy-item{N} origin/main`,
   confirm your merge commit is in `git log -1`, confirm `fly.toml` matches
   `flyctl config show -a brisken-expense-recon` (always-on both services,
   `recon_data_v2`, 1024 MB), then `flyctl deploy .` from the module
   directory. If `flyctl releases` shows a release still in progress, wait
   for it and re-probe step 1 before deploying.
3. Remove the deploy worktree when the drive in §8 is done.

## 8. Verify: drive the SPA, with your own browser session

- `agent-browser --session recon-item{N}` (distinct per session; the default
  session is machine-shared and a sibling will navigate your tab). Playwright
  MCP needs Edge CDP :9222 and is usually not running.
- Drive `https://expenses.brisken.com` on the route that displays the changed
  field, on a live month. Assert the new value renders and no fallback
  ("--", "Unknown", "No receipt found", a blank cell) took its place.
- When the SPA has no renderer for your field yet (its Lovable prompt is
  pending), the drive asserts the changed route still renders with no
  regression, and the authenticated API read shows the field on the live
  month. State that split in those words. Do not claim the renderer was
  verified.
- `uv run tools/lovable-bundle-audit.py` runs AFTER the owner publishes, not
  before; a pre-paste "NOT APPLIED" is the correct reading, not a failure.

## 9. Lovable prompt

- `docs/lovable-{slug}-prompt.md` in this module, shaped like
  `docs/lovable-receipt-taken-prompt.md`: background in one paragraph, the
  new fields with their exact JSON shape, the render rule, i18n keys EN + PT,
  a do-not-change list. No Supabase, auth stays the bearer token.
- Add a Pending row to `docs/PROMPT-STATUS.md`.
- The final reply hands the WHOLE prompt as pasteable text (memory
  `feedback_prompts_are_pasteable_text`); a file path is not the deliverable.
- If the item has no SPA surface, say so in one line and skip. Do not invent
  a prompt.

## 10. Checkpoint, then leave nothing behind

- `/checkpoint --mini`, topic `Expense-Recon Item {N}`. The ledger edits
  (`docs/INDEX.md`, `docs/sessions/2026-09-15.md`, the register) go on
  `docs/checkpoint-item-{N}`, cut FRESH off `origin/main` at checkpoint time
  in its own worktree
  (`C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-item{N}`), PR, merge on
  green, `--delete-branch`. Run `finalize` with `--root` = that worktree.
  Never commit a ledger file on the client branch.
- Ten checkpoints on one day will contend for the session log. Before
  pushing: `uv run tools/repair-session-log.py docs/sessions/2026-09-15.md --check`
  from the docs worktree; repair if it reports. If the PR conflicts, merge
  `origin/main`, keep both sides, run the check again.
- Cleanup, in this order, only for worktrees and branches YOU created
  (siblings are live in the others):

```
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree remove C:\Users\neuma_p1qrsic\Repo\agentic-ops1-item{N}
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree remove C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-item{N}
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree remove C:\Users\neuma_p1qrsic\Repo\agentic-ops1-deploy-item{N}
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 branch -D client/brisken/p1-item-{N} docs/checkpoint-item-{N}
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch --prune
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree prune
```

  Then print, verbatim, the output of these three and stop only when all
  three are clean:

```
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree list            (no item{N} row)
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 branch -a | grep -i "item-{N}"   (empty)
gh pr list --state open --search "item {N}"                              (empty)
```

## 11. The final reply, in this order

1. Shipped: PR number, merge SHA, Fly release, suite count before and after,
   the regress line(s) with the test that went red.
2. Live: what the two months actually showed before the fix, which route was
   driven, what rendered.
3. The Lovable prompt in full, or the one line saying the item has none.
4. Cleanup proof: the three outputs from §10.
5. Anything left open, named as open.
