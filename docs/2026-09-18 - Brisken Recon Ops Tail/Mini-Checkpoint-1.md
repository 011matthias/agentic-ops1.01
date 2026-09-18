# Mini-Checkpoint: Brisken Recon Ops Tail

**Date:** 2026-09-18
**Status:** Five ops-tail items shipped (123, 125, 127, 128, 129 backend + prompt); Fly v187 live and verified
**Type:** mini

---

## Summary

One of four parallel p1 sessions, fenced to the operations tail. Five builder subagents in `agentic-ops1-ops-*` worktrees produced five PRs (#1098 item 123, #1099 item 127, #1100 item 128, #1101 item 125, #1103 item 129); all merged, Fly v187 deployed from a detached origin/main worktree and verified live. Note #70 in `/feedback.jsonl` is the owner's (not Criss's) and is outside this fence.

## What Was Done

- **Item 127 (PR #1099).** `tools/recon_accuracy_check.py`: `ci` replays two committed SYNTHETIC labelled bundles (`tests/fixtures/accuracy/`, invented data; E1, E2, E3 clean + review zone, E4, no_charge near a charge, one charge with two identical receipts, refunds) through the pinned scorer and GATES on exact equality against `expected.json`; new `accuracy` job in `expense-recon-tests.yml`, already green in CI. `real` scores the six gitignored months against `tools/recon-accuracy-baseline.json` (train 56.8 / holdout 19.2 / all 76.0, 0 wrong) and `.claude/hooks/recon-accuracy-deploy-gate.py` asks with the table before any recon `flyctl deploy` on a drop. Decision: a gate, not a report; the scorer is deterministic so the only mover is a matcher change, which then has to be written down by re-recording `expected.json`. Red-proven four ways (widened FX knob, mislabelled pair, missing labels.csv, hook seam).
- **Item 128 (PR #1100).** `tests/test_reader_parity.py` (same statement as CSV and XLSX, field by field; sign inference is the path September's defect lived on), closed-literal pins for `row_type`, `reason_code`, `month_health.state`, `rematch_log.trigger` via `ast` scanners (the code emits 12 triggers where `api-contract.md` listed 10: `duplicates`, `month_move`), `tests/test_extraction_prompt_pin.py`, `tests/test_smtp_listener_e2e.py` through the real aiosmtpd Controller over `smtplib`. Skipped as not cheap: reader-version stamp per statement; committing the A/B runner + prompt ledger (client readings).
- **Item 123 (PR #1098).** `tools/recon_uptime_probe.py` (healthz status + disk floor, port-25 banner, SPA shell, one retry) on `expense-recon-uptime.yml` every 10 minutes: one `recon-uptime` issue + one Resend mail to `BRIEFING_TO` per outage, comment while down, close + one mail on recovery. First `workflow_dispatch` (run 35354794530, dry_run) from the GitHub runner: all three OK, port 25 included, so the runner is a valid vantage point and the cron is live.
- **Item 125 (PR #1101).** Rechecked live first: `454 TLS not available`. Now `web/smtp_tls.py` (self-signed pair on the volume via the image's `openssl`, TLS 1.2+, renewed 30 days before expiry, CA pair via env later) and the Controller's `tls_context` (opportunistic, never required); `transport_tls` on every arrival's archive meta, log row and receipt provenance. Live on v187: EHLO advertises `starttls`, `220 Ready to start TLS`, TLS 1.3 handshake completed (845-byte DER cert served).
- **Item 129 (PR #1103).** `last_rematch` + `rematch_pending` on both month payloads (pure reads of the snapshot's `rematch_log` / pending mark, `rematch_visibility(snapshot)`). Live on v187, August: `last_rematch` = `{at 2026-09-17T11:35:23Z, trigger expense_edit, n_transactions 114, n_matched 9, n_review 1, ...}`, equal to the run payload's `summary.n_reconciled` 9; `rematch_pending: null`. Lovable prompt `docs/lovable-rematch-visible-prompt.md` (EN + PT-BR, 12 trigger labels, one fragment on the shared month header after "Last updated") with a Not-applied row in `docs/PROMPT-STATUS.md`. Notes #53 and #54 answered yes and now visibly.
- **Deploy + verification.** `flyctl deploy` from `agentic-ops1-ops-deploy` (detached origin/main at 1f241789) → `flyctl releases` reads v187. Cold headless-Chrome drive (fresh context, operator login, `/runs/074a7b8905d7`): page renders "August 2026 · 114 charges · Last updated: Sep 17, 2026, 03:39 PM", both statements, card tabs; no "Failed"/"Error"/"undefined"/"NaN"; the only non-GET request is `/api/login`. "Last matched" is absent by design until the prompt is pasted.

## What Did NOT Work (and why)

- **Builder 125's first red proof (removing `tls_context=`):** stayed green because its tests built their own Controller and bypassed `start_intake_smtp`; a caller-level test was added and went red (feature set collapsed to exactly today's live EHLO).
- **`resolve_append.py` renumbering Shipped rows by a whole-table duplicate scan:** main's table already carries two legacy rows numbered 37, so the dedupe renumbered a 2026-08 row to max+1 and moved it to the top; replaced by `fix_shipped.py` (rebuild = origin/main's rows verbatim + this PR's row at max+1, plus dropping a merge-duplicated item heading).
- **`git merge origin/main | tail && push && gh pr create` in one chain:** the pipe masked the conflict exit, so PR #1100 opened on a conflicted tree; resolved by hand (theirs first, then ours).
- **Merging several Shipped-table PRs while all are open:** every merge turns the others DIRTY (`gh pr merge`: "has merge conflicts"); each remaining PR needed merge main + table rebuild + a fresh ~5 min CI run, strictly serial (about 35 minutes for four).
- **`flyctl logs --no-tail` for the STARTTLS startup line:** the window did not include it; the live EHLO/STARTTLS probe was the proof instead.

## Current Status

brisken platform: unknown plan (no `platform` section in `infrastructure.yaml`). Fly v187 live: items 125 and 129 backend serving; 123's cron running from GitHub; 127's CI job green on its first PR; 128's guards in the suite (2547 collected). Backlog headings 123/125/127/128/129 suffixed, Shipped rows 92 to 96, status rows added. Worktrees `agentic-ops1-ops-{123,125,127,128,129,deploy,ckpt}` are this session's; remote branches deleted on merge.

## Next Steps

1. Owner: paste `docs/lovable-rematch-visible-prompt.md`; check the August header reads "Last matched Sep 17 (an expense was edited): 9 of 114 charges paired, 1 to review".
2. Item 125 second live leg: the next real mail's receipt carries `submitted_by.transport_tls: true` on `GET /api/expense-batches/{id}`; a false there names a sender still delivering in the clear.
3. Owner note #70 (2026-09-18 10:19Z, run `af8936c6b05a`, operator matthias): "add receipts function just opens receipt view in new tab but does not really add it". Untriaged, outside this fence.
4. Owner decisions: a Brisken mailbox as uptime-alert recipient (needs a Graph secret in repo secrets; Resend free tier reaches only `BRIEFING_TO`); a CA certificate for the MX via DNS-01 on the registrar API.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 123, 125, 127, 128, 129 (Shipped paragraphs) and Shipped rows 92 to 96
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-rematch-visible-prompt.md`, `docs/PROMPT-STATUS.md` Not-applied table
- `tools/recon_accuracy_check.py`, `tools/recon-accuracy-baseline.json`, `.claude/hooks/recon-accuracy-deploy-gate.py`
- `tools/recon_uptime_probe.py`, `.github/workflows/expense-recon-uptime.yml`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/smtp_tls.py`

## Open Questions (outside this fence, not fixed here)

- Matcher: two identical charges on nearby days against one receipt resolve greedily to the first charge in statement order instead of deferring (found building the 127 fixture; that row is labelled `excluded`).
- `tests/test_intake_mail.py::test_renaming_a_batch_into_a_month_claims_its_pool` reads the grid before the claimed receipt's async ingest lands under full-suite load (seen once, passes alone and in its module).
- `OWNERSHIP-HANDOFF.md`'s Fly table still says scale-to-zero and volume `recon_data`; the module README's "Expected: 98 passed" line is stale.
- Builder 125 reported its two source files gaining item-125 wiring mid-session from "another actor"; the subagents share this session's scratchpad and the most likely author is its own earlier patch script. The committed wiring is coherent and tested; noted in case a sibling session also holds an uncommitted copy.
- Residues named in the backlog: 127's per-month verdict tally on the operator state; 128's reader-version stamp; 129's per-file "matched with X" line and which rows moved (events carry counts, no row ids).

---

## Prompts handed over 2026-09-18

### Paste into Lovable: the month says when it was last matched (item 129)

The file `docs/lovable-rematch-visible-prompt.md` (module docs) is the canonical copy; its fenced block is the prompt.

### Paste into a fresh Claude Code chat: ops tail, second pass

````
/comd_resume brisken

You are one of FOUR parallel sessions on the Brisken expense-reconciliation tool (p1). The other three are already running and have their own frame. Your entire job is the operations tail nobody else is touching.

## SCOPE FENCE — read this before anything else

**YOURS, and nothing else:** backlog items **123, 125, 127, 128** and the UI prompt for **129**.

**NOT YOURS. Do not open, edit, test, deploy, or write docs about these, even if you spot a defect in them:**
- The **M-series** (branch `client/brisken/p1-memory-m1`) — another session owns memory work end to end.
- The **T-series** (branch `client/brisken/p1-trace-t2`) — another session owns trace work end to end.
- **match-description** (branch `client/brisken/p1-match-description`) — another session owns the matcher's descriptions.
- **Items 130, 131 and 132** — all three sit inside those frames.
- The **matcher itself** (`src/expense_recon/matching/**`). Item 127 is about RUNNING the accuracy scorer in CI, never about changing how matching works. If your work would edit a file under `matching/`, you have left your lane: stop and say so.

If you find something broken outside your fence, write ONE line in your checkpoint's Open Questions naming it. Do not fix it. A second session fixing the same file is the one failure mode this split exists to prevent.

**Already shipped, do not rebuild:** items 98, 104, 144, 146, 147, 148, and the prompt halves for 109 and 130. Read the backlog heading before starting any item; a `SHIPPED` marker means it is done.

## Where it stands (2026-09-18 evening)

All five fenced items are SHIPPED and live. PR #1098 (123, uptime monitor; first dispatch run 35354794530 from the GitHub runner all OK, port 25 reachable), #1099 (127, accuracy scorer in CI as an exact-equality gate on synthetic bundles + a real-months deploy hook; CI job green), #1100 (128, four guards), #1101 (125, STARTTLS; live EHLO advertises starttls and a TLS 1.3 handshake completes), #1103 (129 backend: `last_rematch` + `rematch_pending` on both month payloads; August live shows expense_edit, 9 of 114). Fly **v187** carries 125 and 129 (read back with `flyctl releases`). The 129 Lovable prompt `docs/lovable-rematch-visible-prompt.md` is written with a Not-applied row in `docs/PROMPT-STATUS.md`, waiting on the owner's paste. Checkpoint: `docs/2026-09-18 - Brisken Recon Ops Tail/Mini-Checkpoint-1.md`.

## Your queue, in order

1. **Read `GET /feedback.jsonl` first** (70 lines on 2026-09-18 evening; #70 is the OWNER's note on run `af8936c6b05a`: "add receipts function just opens receipt view in new tab but does not really add it", untriaged and outside the fence unless the owner assigns it). A new note from Criss outranks everything below.
2. **Item 129 paste check.** When `docs/PROMPT-STATUS.md` or the bundle shows `mh.rematch.last` live, drive the August header cold in EN and PT-BR and move the row to Applied; until then nothing to do.
3. **Item 125 second leg.** Read the newest mail-sourced receipt on `GET /api/expense-batches/{id}` (August `074a7b8905d7` or the owner's new month) and report `submitted_by.transport_tls`; a `false` names a sender still delivering in the clear. Read-only.
4. **Item 123 watch.** `gh run list -w expense-recon-uptime.yml --limit 5`: the cron must be firing every 10 minutes with green runs and no `recon-uptime` issue open. If a run is red for a probe error (exit 2), fix the probe; a DOWN is the app, not you.
5. Nothing else is in the fence. Residues are recorded in the backlog under each item and are the owner's call: 127's per-month verdict tally, 128's reader-version stamp, 129's per-file "matched with X" line, 125's CA certificate, 123's Brisken-mailbox recipient.

Before each item: `gh pr list -R 011matthias/agentic-ops1.01 --state open`, `git worktree list`, and grep recently modified transcripts in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/*.jsonl` for the item number. A number another session is holding is not yours, even if it is in your list.

## Staying out of the other three sessions' way

All four of you share ONE clone, so these are not style preferences:

- **Your worktrees are prefixed `agentic-ops1-ops-`** (e.g. `agentic-ops1-ops-127`). Your branches are `client/brisken/p1-ops-<item>-<slug>` and `docs/ops-<topic>`. Never create a branch or worktree outside those namespaces, and **never remove a worktree you did not create** — `git worktree list` is full of other sessions' live work. The ops-{123,125,127,128,129,deploy,ckpt} worktrees from the first pass are merged and may be removed with `git worktree remove`.
- **Never `git stash`.** The stash is shared across every worktree in the clone; a sibling will pop yours. Commit on a branch instead.
- **Never `git add -A`.** Stage explicit paths only.
- **Use a session-unique checkpoint payload**: `.scratch/checkpoint-payload-ops.json`, never the bare `.scratch/checkpoint-payload.json`.
- **Ledger files go through a `docs/ops-...` PR only** (`docs/INDEX.md`, `docs/friction-register.md`, `docs/sessions/*.md`). Never commit one on a feature branch.
- **The Shipped table in `p1-improvement-backlog.md` is the #1 collision point.** Main's table already carries two legacy rows numbered 37, so never dedupe the whole table. After merging origin/main, rebuild the table as origin/main's rows verbatim plus your row numbered max+1 on top, and drop a merge-duplicated `### N.` heading (the copy without the SHIPPED suffix). Expect every merged sibling PR to turn yours DIRTY: merge main again, rebuild, push, wait for CI.
- **For `api-contract.md` and `PROMPT-STATUS.md`, keep main's sections first and append yours.** If your section makes an earlier sentence false, fix that sentence in place.
- **Deploys are serialized whether you like it or not.** Always read the version back with `flyctl releases` and never infer it from your own deploy.

## How to work

- **The API host is `https://brisken-expense-recon.fly.dev`.** `expenses.brisken.com` serves only the SPA; the SPA calls `api.expenses.brisken.com`. **Python's default urllib User-Agent is refused by Cloudflare** (`403 error code: 1010`); send a browser UA on every request. `MSYS_NO_PATHCONV=1` for every `/api/...` arg in Git Bash. Windows Python cannot open `/c/...` paths: pass `C:\...`. The operator code is vault entry "Expense Recon App", field `operator_code` (`python C:\Users\neuma_p1qrsic\vault.py get "Expense Recon App"`); never print it or a token.
- **No writes to Criss's live months, ever.** Read-only API calls only. Never probe publish. `GET /runs/{id}/expense-report.pdf` WRITES render outcomes: never fetch it live.
- **Parallel builder subagents work well**: one worktree per item, a `general-purpose` Agent per worktree in the background with a self-contained brief (hard rules, measurement, docs, commit on the branch, do NOT push), `uv run tools/bg_watch.py watch` per builder. Tell every builder: report anything in the brief that turned out to be WRONG (it returned corrections from all five builders today). Builders share your scratchpad directory: name their scratch files by item.
- **Never chain a mutating git command through a pipe** (`git merge ... | tail && git push`): the pipe hides the conflict exit and the push runs anyway. Use `if git merge ...; then ...; else ...; fi`.
- **`tools/regress_check.py` is unusable.** Prove every wiring point BY HAND: `cp` the source aside, disable it with a single-line change, run the targeted pytest, read the FAILED lines, `cp` back, confirm byte-identical. A red proof that does not go through the real caller does not bite (builder 125's first proof).
- **The negative-case fixture is where defects come from.** Name the specific absent row class in every brief.
- **Patch CRLF sources in BYTE mode.** Python heredocs with triple quotes are blocked by a hook: write scripts with the Write tool. A bare persistent `cd` is blocked: use `( cd X && ... )` or `git -C`. Never `git checkout --` to restore a backup; use `cp`.
- **Full module suite in the FOREGROUND before any PR:** `uv run --extra dev --extra web pytest -q -p no:cacheprovider` from the module root (~5 min, ~2547 tests). Deploy with `flyctl deploy . -a brisken-expense-recon --remote-only` from a clean detached origin/main worktree (pre-authorized).
- **After a deploy:** a live API probe of the changed field, then a cold consumer drive (headless Playwright `channel="chrome"`: fresh context, goto, set localStorage `brisken.lang`, fill the first input with the operator code, Enter, goto the route, read `body` inner text, record non-GET requests, which must be none besides login). Dismiss the feedback widget first (`[data-fb-widget] [role=dialog]`, its "Got it" button via JS `click()`). Say plainly what the drive covered.
- In the same PR, update the backlog item's heading and its Shipped row, plus `status/p1-expense-reconciliation.md`.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine and with four sessions live it will usually be someone else's; trust its `context=` ONLY when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl`. Keep a small script for it in your scratchpad. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check costs about 45k; a builder-run item costs you 30-60k because the builder burns its own window; a matcher-scale item with before/after measurement costs about 225k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries you registered.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/ops-...` worktree off origin/main and `--root <that worktree>` BEFORE the `finalize` subcommand (it is a global flag); use `.scratch/checkpoint-payload-ops.json`; write the checkpoint prose after `finalize` or rename your file to the number it prints; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; the SCOPE FENCE section verbatim; where it stands (what shipped with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with exact code pointers and live evidence; the "Staying out of the other three sessions' way" and "How to work" sections; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session (labelled as such), and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````
