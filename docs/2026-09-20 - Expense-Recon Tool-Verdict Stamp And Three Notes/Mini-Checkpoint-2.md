# Mini-Checkpoint: Expense-Recon Tool-Verdict Stamp And Three Notes

**Date:** 2026-09-20
**Status:** TRACEABILITY queue closed; three owner notes filed, none built
**Type:** mini

---

## Summary

Inherited backlog item 155 already built and pushed by a duplicate session of
the same continuation prompt, merged and deployed it, then built item 158 (the
`set_tool_decision` statement-id pin, opened as 157 and renumbered mid-review
when a sibling merged that number first). Filed three owner feedback notes that
belonged to nobody: #70 as item 159, and #71 and #72, which arrived while item
158 sat in CI, as items 160 and 161.

## What Was Done

- **Item 155 merged and deployed.** PR #1123, merge `a2276f06`, Fly **v190**
  (a duplicate session deployed the same commit again as v191 minutes later).
  Live was still v189 from Sep 18, so two days of sibling merges went out with
  it.
- **Verified item 155 the only way that actually works.** The live months show
  `operator_note` on 0 rows and always will: `intake_provenance` is frozen into
  the run snapshot at ingest (`service.py` ~5851) and read back from it
  (~7114), so a receipt already in a month can never gain a new provenance
  field. Proof instead came from running the SHIPPED function in-machine over
  `/data/inbound` on the deployed image: **32 notes from 88 readable bodies of
  94 stored `.eml`**, every known carrier verbatim. Cold Playwright drive of
  `/expenses/{September}`: route renders, no error strings, only the login as a
  non-GET.
- **Item 158 built, red-proven, merged.** PR #1129, merge `f2a77bc1`,
  `tests/test_tool_decision_statement_id_158.py` (3, route-level). Suite 2643 →
  **2646 passed / 2 skipped**; ruff clean. Test-only, no deploy.
- **Items 159, 160, 161 filed** (PRs #1129 and #1137, merge `211e1dee`), each
  with its live evidence rather than as a bare quote.

## What Did NOT Work (and why)

- **Probing the live months for `operator_note` to verify the deploy.** Returns
  0 on all three months on a correct deploy, because provenance is frozen at
  ingest. A correct deploy is indistinguishable from a failed one through that
  instrument, and the confident negative invites re-shipping work that already
  landed.
- **First in-machine scan of the archive.** Passed a `Path` to
  `extract_body_text`, which takes `bytes`; it reported "readable bodies: 0"
  with exit 0. The count-what-you-found line is what caught it.
- **The first conflict resolver.** Split on `\n`, leaving a trailing `\r` on
  every line (checkout is CRLF, `core.autocrlf=true`), then rejoined with
  `\r\n`, producing `\r\r\n` and lone CRs. `p1-expense-reconciliation.md`
  then conflicted as a WHOLE FILE on the next merge instead of at the two rows
  actually touched. Fixed by normalising on read and writing LF.
- **Claiming backlog number 157.** A sibling merged 157 and Shipped row 104 for
  note item M4 while this PR was in review, so the number had to move to 158
  after the PR was already open. Numbers are only safe once merged, not once
  chosen post-merge-from-main.

## Current Status

- Live: Fly **v192**, which carries M4 (`by_vendor` 97/97 rows have `profile`).
  Nothing merged is undeployed.
- Item 158 is test-only and needed no deploy.
- Items 159, 160, 161 are filed and **unbuilt**. None is diagnosed beyond the
  evidence in its entry.
- Two p2 status files are stale (`p2-product-decks` 59d, `p2-targeting` 60d).
  Not this session's workstream; left for the p2 owner.
- Platform ops status for brisken reads `unknown plan` in `infrastructure.yaml`.

## Next Steps

1. **Item 160** (note #71): settle whether July's Microsoft 718.20 row really
   has uncategorised receipt LINES while its row-level `posting_category` is
   set. The answer decides between a copy fix and a defect fix; do not rewrite
   the sentence first.
2. **Item 161** (note #72): ask the owner in one line whether "what is this" is
   about the section's purpose or the 85.3% / 65 mismatch, and drive April's
   page cold to see both figures together.
3. **Item 159** (note #70): reproduce "Add more receipts" on a CURRENT month —
   the run the note names (`af8936c6b05a`) is not among the seven the API lists.
4. Owner: paste `docs/lovable-operator-note-prompt.md` so item 155's note
   reaches Criss's screen. Until then the field is API-only.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 159, 160, 161)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  (the `statement_id` coverage note)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-operator-note-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

---

## Continuation prompt for the next session

```
/comd_resume brisken

Owner directive 2026-09-18 stands: the items in this prompt are to be built now; the covered-vs-quote licence question does not gate them. You are the TRACEABILITY session. Siblings may run at the same time on the same repo and the same Fly app: follow the parallel-safety rules in "How to work" exactly.

Read first: `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`, then backlog items 159, 160 and 161 in `workspace/clients/brisken/status/p1-improvement-backlog.md`, and the memories `project_brisken_expense_recon_usability_loop` (the 2026-09-20 paragraph first), `project_brisken_expense_recon_mail_intake`, `feedback_recon_no_live_writes_criss_acts`, `feedback_prompts_are_pasteable_text`, `feedback_continuation_prompt_carries_loop`, `rule_untrusted_inbound`.

## Where it stands

The TRACEABILITY queue is closed. Nothing of the previous session's is in flight; everything below is newly filed and unbuilt.

- **Item 155 SHIPPED and LIVE** (PR #1123, merge `a2276f06`, Fly **v190**; a duplicate session deployed the same commit as v191). `expenses[].operator_note` = the prose the sender typed ABOVE a forwarded invoice, recorded on provenance by `_provenance_entry` and lifted in `build_expense_view`; `body_render.operator_note` cuts at the LAST forward-header block. **The live months show it on 0 rows and always will**: `intake_provenance` is frozen into the run snapshot at ingest (`service.py` ~5851) and read back from it (~7114), so a receipt already in a month can never gain a new provenance field. Verified instead by running the shipped function in-machine over `/data/inbound` on the deployed image: 32 notes from 88 readable bodies of 94 stored `.eml`. SPA half `docs/lovable-operator-note-prompt.md` is written and **NOT pasted**, so the field is API-only until the owner pastes it.
- **Item 158 SHIPPED** (PR #1129, merge `f2a77bc1`; test-only, no deploy). `set_tool_decision`'s `statement_id` stamp, the one of item 152's five `decisions` writers no fixture reached, is pinned through the route that reaches it (the item-76 self-confirm rule, inside `rematch_month` on statement attach) in `tests/test_tool_decision_statement_id_158.py` (3, route-level). It asserts its premise separately first, because the gap survived T3 precisely by a stamp test passing over an empty table. The T3 docstring that claimed a fresh month already holds a tool verdict is corrected.
- **Live is Fly v192** (carries note item M4: `GET /api/memory` `by_vendor` 97/97 rows have `profile`). Nothing merged is undeployed.
- **Numbers taken:** items up to 161; next free backlog number is **162**, next free Shipped iteration is **106**. Re-check both after `git merge origin/main`, because siblings append too.

## Queue, in order

### 1. Backlog item 160 - a row with a settled category still says a category is missing (feedback note #71)

Owner, 2026-09-20T15:12:07Z, page `/expenses/50622baec444` (July): *"this should not be mentioned here i think..."*. The selector resolves it without asking: `#exp-row-0006__G173514057_5b606b64167e43cbb3a834880b5b0941.pdf > td:nth-of-type(6) > div > div:nth-of-type(1) > p` = July's **Microsoft Corporation 718.20**, `transaction_id` `49ace8baae6b6723`, `source_row` 27 of `July2026.xlsx`, column 6's first paragraph.

Read live 2026-09-20, that row carries BOTH `posting_category` `Software & Subscriptions` (source `llm; review`) AND `review` = `{"state": "pick", "reason": "One or more receipt lines still need a category before this can post.", "reason_code": "partial_uncategorized"}`. Column 6's first paragraph is where that reason renders.

**Settle the question before touching any copy.** Row-level and LINE-level categories are different things and the reason is about the lines. Either the message is correct and reads wrong beside a filled category field, or the line state is stale on this row. Those call for opposite fixes. Read that row's line items live first and say which it is; only then build. If it is a copy/placement fix it has an SPA half and needs a Lovable prompt; if it is a defect in how `partial_uncategorized` is decided it is backend and needs a red proof at the wiring point.

### 2. Backlog item 161 - two numbers on one page look like they contradict each other (feedback note #72)

Owner, 2026-09-20T15:15:00Z, page `/runs/0603bb0e6f38` (**April**), section **"Receipts to chase (65)"**: *"what is this"*.

April live: 94 charge rows, 34 receipts, `summary.n_charges_need_receipt` **65**, `summary.receipt_match_rate` **85.3** (`n_receipts_matched` 29 of 34), `n_receipts_need_charge` 5, `n_booked_no_receipt` 0. The rate is receipts-over-receipts; the section counts CHARGES with no receipt. 85.3% matched sitting above a list of 65 things to chase reads as a contradiction unless you already know which population each figure describes.

**Ask before building.** The owner may be asking what the section is FOR rather than why the figures disagree. Put the question to them in one line via `AskUserQuestion` with a recommendation, and drive April's page cold to see the two figures as they actually sit together. Both readings point at the same gap (the label does not say what it lists), so a one-line label change plus a hover explanation may answer either; do not assume that without the answer.

### 3. Backlog item 159 - "Add more receipts" opens the receipt view and adds nothing (feedback note #70)

Owner, 2026-09-18T10:19:09Z, page `/expenses/af8936c6b05a`, section "Add more receipts": *"add receipts function just opens receipt view in new tab but does not really add it"*.

Two facts already checked: the run it names (`af8936c6b05a`) is **not among the seven batches `GET /api/expense-batches` lists** (April, January, June, May, September, August, July), so that month is gone and a reproduction has to be built on a current one; and the complaint is about what a control DOES after the click, so a backend route that was never called leaves no trace and the API logs cannot settle it. A cold drive of the "Add more receipts" control on a live month is the instrument that can. Check first whether the button is wired to the upload route at all or only to a viewer link.

Append each item you ship to the backlog's Shipped table and move its entry, taking the next free number AFTER `git merge origin/main`. When the queue is empty, follow SESSION LOOP step 9.

## How to work

- Your worktree, cut fresh: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin` then `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-trace-<item> C:\Users\neuma_p1qrsic\Repo\agentic-ops1-trace origin/main`. **Check `git worktree list` for a sibling holding that directory before claiming it** (on 2026-09-20 two sessions ran the same prompt and raced on merge and deploy). One branch per queue item, reusing the directory after each merge. Never edit, commit or stash in the main checkout; never `git stash` anywhere. A hook refuses `cd X && ...`; use `git -C`, `uv run --directory`, absolute paths. The GitHub slug is `011matthias/agentic-ops1.01` (pass `--repo` to `gh`; `MSYS_NO_PATHCONV=1` for colon pathspecs, and then give `-C` a `C:/...` path).
- Siblings edit `web/service.py`, `web/app.py`, `web/intake_mail.py`, `tests/test_view_contract.py`, `docs/api-contract.md`, `docs/PROMPT-STATUS.md`, the backlog and the status file. Append at the END of the relevant block; never renumber, re-sort or reflow. Before the first push `git rebase origin/main` is fine; after any push only `git merge origin/main`, never rebase, never force-push. Re-run the module suite after every merge from main. **A backlog number is only yours once YOUR PR has merged**: on 2026-09-20 a sibling merged 157 while this session's PR sat in review, forcing a renumber to 158 with the PR already open.
- **Line endings.** `core.autocrlf=true`: the checkout is CRLF, git stores LF. A resolver that splits on `\n` leaves a trailing `\r` on every line; rejoining with `\r\n` produces `\r\r\n` and lone CRs, and the file then conflicts as a WHOLE FILE on the next merge. Normalise on read (`\r\n` -> `\n`, then `\r` -> `\n`) and write LF.
- Live reads only. API `https://brisken-expense-recon.fly.dev` (also `api.expenses.brisken.com`): `POST /api/login {"code": ...}` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never print it; read it inside a script). Months: July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`, April `0603bb0e6f38`; list `GET /api/expense-batches`. Feedback notes: `GET /feedback.jsonl` (72 as of 2026-09-20; the text key is `comment`, and `selector` + `pos` are what locate a note with no section). Never fetch `GET /runs/{id}/expense-report.pdf` live (it writes render outcomes); `reconciliation-report.pdf` is read-only. No writes to Criss's months; any production mutation beyond a deploy goes through `AskUserQuestion` as a decision with a recommendation, never "say the word". Windows Python cannot open `/c/...` paths: pass `C:\...`. In-machine read-only scans: base64 a script into `flyctl ssh console -a brisken-expense-recon --pty=false -C "sh -c 'echo <b64> | base64 -d > /tmp/x.py && python3 /tmp/x.py; rm -f /tmp/x.py'"`. **The mail archive is `/data/inbound`**, and `body_render.extract_body_text` takes **bytes**, not a Path; have the script print a count of what it found before you use its output, because a blind probe exits 0 and reports zero.
- **`flyctl` on this box** answers "no access token available" for every command while the token in `~/.fly/config.yml` is valid (api.fly.io accepts it). `flyctl auth login` is NOT needed: read `access_token` out of that file and export it as `FLY_API_TOKEN`.
- Build: route-level tests through the FastAPI app, at least one through the CALLER the fix changed; prove each wiring point red by hand (cp the source aside, one-line mutation via a script written with the Write tool, targeted tests, cp back, sha256 equal) because `tools/regress_check.py` prints "RED (no pytest summary line)" whether or not the suite failed; never restore with `git checkout --`. **Make the mutation script REFUSE to run unless the enclosing `def` at the target line is the one you mean** - the `decisions` stamp call is textually identical in five writers, and on 2026-09-18 a mutation aimed at `set_decision` landed in `set_tool_decision` and read as "does not bite". Suite: `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q -p no:cacheprovider` (about 6-7 minutes; 2646 passed / 2 skipped at `f2a77bc1`). Run it in the background and wait for the notification. Ruff: `uv run --no-project --with ruff --directory <module dir> ruff check src tests`. Python heredocs with triple quotes and heredocs carrying backslashes are blocked by hooks: write scripts with the Write tool.
- A test JPEG must exceed **4096 bytes** or `intake_mail.py` ~593 drops it as a signature logo and the mail silently takes the BODY-ONLY render path while the test passes; assert the `intake_provenance` key (the stored file NAME) to prove which path ran.
- Ship: commit on the item branch with explicit pathspecs, push, `gh pr create --repo 011matthias/agentic-ops1.01` (suite count before and after plus the red-proof lines in the body), wait for CI (`gh pr checks <n> --repo ...`; `test` is the module suite, about 10-12 min), `gh pr merge --squash --delete-branch` on green. The backlog move to Shipped and the status file update land in the same PR.
- Deploy (pre-authorized, one Fly app shared with siblings): after the merge, probe the live API for YOUR field first; a sibling's deploy may already carry your commit (`flyctl releases -a brisken-expense-recon`). **If your field is written at INGEST, the live months cannot show it and a probe there proves nothing** - run the function in-machine over the archive instead. If a deploy is needed: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add --detach C:\Users\neuma_p1qrsic\Repo\agentic-ops1-deploy-trace origin/main`, confirm your merge is in `git log -1` there, `MSYS_NO_PATHCONV=1 flyctl deploy "<module dir>" --config "<module dir>/fly.toml" -a brisken-expense-recon --remote-only`, then remove that worktree.
- Cold browser drives: headless Playwright with `channel="chrome"` (`uv run --no-project --with playwright --directory <scratchpad> python <script>`; `agent-browser` hung repeatedly on this host). Log in at the gate (the code read from `.env` inside the script), wait for localStorage `erc-token`, dismiss "Leave feedback anywhere" by clicking the "Got it" text, go to `/months`, click the month, land on `/expenses/{id}`; record every non-GET request and assert only the login. The deploy-consumer gate does not see a script drive: state the coverage explicitly in the closing text. When the SPA has no renderer for your field yet, the drive asserts no regression on the changed route and the API read shows the field - say that split in those words rather than claiming a renderer was verified.
- SPA work: `docs/lovable-<slug>-prompt.md` (background in one paragraph, the new fields with their exact JSON shape, the render rule, EN + PT-BR strings, a do-not-change list, checks; no Supabase, auth stays the bearer token), a Not-applied row in `docs/PROMPT-STATUS.md`, and the WHOLE prompt in the reply inside a FOUR-backtick fence. Label every fence: "Paste into Lovable:" or "Continuation prompt for Claude Code:". A file path is not the deliverable.
- Checkpoint branches: `docs/checkpoint-trace-<n>` in `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-trace` (trace-1 through trace-6 are used), cut off origin/main at checkpoint time; `checkpoint_scaffold.py --root <that worktree> pre` and `--root <that worktree> finalize` (`--root` goes BEFORE the subcommand). **`finalize` picks the Mini-Checkpoint-N filename itself and counts files already on disk, so write the prose only AFTER it names it** - writing at `pre`'s target bumps the counter and forces a rename. Run `uv run tools/repair-session-log.py docs/sessions/<date>.md --check` there before pushing AND again after any merge from main. Remove only the worktrees and branches YOU created; print `git worktree list` and `gh pr list --repo 011matthias/agentic-ops1.01 --state open --search trace` at every stop.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-18 `--status` read a sibling's 333k while this session sat at 452k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137); T3 (a new snapshot key, a parser change, three DB columns, 11 tests, 10 red proofs, deploy, live probe, cold drive) cost about 190k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries you created (leave siblings' entries alone).
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `--root <that worktree>`; write the checkpoint prose after `finalize` names the file; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
```
