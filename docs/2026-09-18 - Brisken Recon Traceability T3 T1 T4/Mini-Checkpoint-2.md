# Mini-Checkpoint: Brisken Recon Traceability T3 T1 T4

**Date:** 2026-09-18
**Status:** T3 shipped + deployed (Fly v188); T1 merged, deploy pending; T4 merged-or-in-CI, nothing to deploy
**Type:** mini

---

## Summary

The TRACEABILITY session of three parallel sessions on the owner's 2026-09-18
note. T3 gave every charge a record of which statement upload printed it and
where, and put that upload's id on every stored decision, history line and
receipt claim. T1 audited receipt identity across every surface and found one
gap. T4 scanned the live mail archive, closed three "do not build" questions
with counts, and turned up a finding the note had not anticipated.

## What Was Done

- **T3 (backlog 152, PR #1107, merge `b1fe1d28`, Fly v188).** New snapshot key
  `statement_origins` records every charge each upload printed, so `rows[]` and
  `expenses[]` carry `statement_file`, `statement_id`, and `source_row` (a
  workbook line) or `source_page` (a PDF one), plus `transaction_id` on
  `expenses[]` read from the EFFECTIVE settlement. The Chase PDF parser now
  records the page (`_extract_pages` + `page_starts`), which was the call the
  brief left open: recorded rather than declared unrecorded, because live
  August actually holds a PDF statement whose three charges had no place at
  all. `decisions` / `decision_history` / `receipt_claims` each gained a
  `statement_id` column, resolved inside the store from the snapshot (memoized
  per run, dropped on every snapshot write) rather than threaded through
  seventeen writers. Item 72 marked closed by item 103.
- **T1 (backlog 153, PR #1109, merge `16de8a1b`).** Audited every receipt
  surface on live July, August and September: all six object surfaces already
  carry `document_id` at 100%, and the three string surfaces carry it AS the
  string. One gap: `set_aside[]` named the same value `file`.
  `set_aside[].document_id` now rides beside it, read from the entry's stored
  receipt so a legacy parse-issue entry correctly gets no key.
- **T4 (backlog 154, PR #1111).** 91 stored `.eml` scanned in-machine:
  0 nested `message/rfc822`, 0 HEIC, 30 mails with both a PDF and a real body
  whose numbers are mostly the PDF's. Two characterisation pins shipped; three
  builds declined with the count behind each. Item 154 filed for the finding.

## What Did NOT Work (and why)

- **Probing the mail archive at `/data/mail`:** the path does not exist, so the
  scan reported "0 mails with a PDF attachment and a real body" with every
  command exiting 0. The archive is `<data_root>/inbound`. Caught only because
  the 0 contradicted a known count from the prior session; the rerun prints the
  `.eml` count first so the instrument proves itself before its output is used.
- **The first red proof of `set_decision`'s stamp:** the anchor text
  (`... self.conn.commit()` + `return cur.rowcount > 0`) ends
  `set_tool_decision`, not `set_decision`, so the mutation left the suite green
  and read as "this wiring point does not bite". Re-anchoring on
  `set_decision`'s own tail made it red at 3 tests.
- **A test asserting the matcher's own verdict carries the statement id:**
  chasing the above showed a fresh attach writes ZERO rows to `decisions` and
  there are no `decided_by='tool'` rows in that fixture at all, so the test
  asserted a premise the month never reaches. Dropped rather than kept;
  `set_tool_decision`'s stamp is wired and exercised by no fixture here, stated
  in the PR rather than implied.
- **`tools/regress_check.py` for any of the twelve wiring proofs:** it prints
  `RED (no pytest summary line)` whether or not the suite failed, so every
  proof this session was run by hand (cp aside, one-line mutation, targeted
  tests, cp back, sha256 equal).

## Current Status

- Live API carries T3 on both months: July 112 of 112 charges and August 111 of
  114 now name their upload and sheet row through the anchors fallback; the
  three August charges that do not are exactly the PDF-sourced ones. 31 of
  July's 54 and 9 of August's 25 expenses carry a charge side. `statement_id`
  and `source_page` stay absent until each month's next re-read, which this
  session did not trigger (no live writes; Criss acts).
- Cold headless drive of `expenses.brisken.com` → `/months` → `/expenses/{id}`
  rendered 11,743 chars, no fallback string, ONE non-GET request (the login).
  The SPA has no renderer for any field shipped today, so that drive asserts no
  regression on the changed route, not a rendered new value.
- brisken platform ops: unknown plan, `~?/?` ops/mo, last assessed `?`.
- brisken comms-log is 10 days stale.

## Next Steps

1. Deploy T1 (`16de8a1b`) and T4 to Fly; probe `set_aside[].document_id` live on
   July or September (both months have set-aside entries) and re-drive cold.
2. Backlog item 154: carry the operator's prose above a forward onto provenance
   as a DISPLAY-ONLY note. Never routing: mail text is untrusted inbound.
3. Both live months gain `statement_id` + the PDF `source_page` only at their
   next re-read, which is Criss's action, not ours.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  (the two new sections: charge origin, and receipt identity per surface)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 152, 153, 154
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/statement_origin.py`

---

## Continuation prompt for the next session

/comd_resume brisken

Owner directive 2026-09-18 stands: the items in this prompt are to be built now; the covered-vs-quote licence question does not gate them. You are the TRACEABILITY session. Sibling sessions (MEMORY on the M-notes, MATCHING on the X-notes) run at the same time on the same repo and the same Fly app: follow the parallel-safety rules in "How to work" exactly.

Read first: `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`, then in that module `docs/api-contract.md` (the two 2026-09-18 sections at the end: "A charge names the statement line it was printed on" and "A receipt is the same receipt on every surface"), backlog items 155, 152, 153, 154 in `workspace/clients/brisken/status/p1-improvement-backlog.md`, and the memories `project_brisken_expense_recon_usability_loop` (the 2026-09-18 TRACEABILITY paragraph first), `project_brisken_expense_recon_mail_intake`, `feedback_recon_no_live_writes_criss_acts`, `feedback_continuation_prompt_carries_loop`, `rule_untrusted_inbound`.

## Where it stands

- **T3 SHIPPED and DEPLOYED** (backlog 152, PR #1107, merge `b1fe1d28`, **Fly v188**). Snapshot key `statement_origins` = `{file: {transaction_id: {"row": n} | {"page": n} | {}}}`, written by both callers that write `statement_anchors` (`service.py` attach + re-read commit), kept apart from the anchors because the anchors' emptiness is load-bearing for the writeback. `rows[]` and `expenses[]` carry `statement_file`, `statement_id`, `source_row` (workbook) or `source_page` (PDF); `expenses[]` also carries `transaction_id` from the EFFECTIVE settlement (`charge_state_map`), so a reject takes all five off. `Transaction.source_page` + `ingest/statement_pdf.py` `_extract_pages` / `_page_starts` / `parse_statement_text(page_starts=)`. `statement_id` columns on `decisions` / `decision_history` / `receipt_claims`, resolved inside `store.py` (`_charge_origins` memo, dropped in `update_run_snapshot`; `_history_statement_id` for the append-only table). Reader is `web/statement_origin.py`, shared so `store.py` never imports `service.py`. Item 72's heading marks it closed by item 103.
  - **Live after v188:** July 112 of 112 charges and August 111 of 114 carry `statement_file` + `source_row` through the ANCHORS FALLBACK (both months predate `statement_origins`). The 3 August charges that do not are exactly the PDF-sourced ones from `20260804-statements-1176-.pdf`. 31 of July's 54 and 9 of August's 25 expenses carry a charge side. `statement_id` and `source_page` are ABSENT on both months and arrive only at each month's next re-read, which is Criss's action; this session triggered no live writes.
- **T1 SHIPPED, NOT YET DEPLOYED** (backlog 153, PR #1109, merge `16de8a1b`). `set_aside[].document_id` beside `file`, read from the entry's STORED RECEIPT (`_set_aside_document_id`), absent on a legacy `_derive_legacy_set_aside` entry whose `file` is a parse-issue name. The audit is in the contract: all six object surfaces already carried the id at 100% across July/August/September, and `duplicate_groups[].members[]`, `card_review.unresolved_hints[].documents[]` and `expense_ingest.documents[]` carry it AS the string. Both PDF builders' evidence items carry it already (item 68).
- **T4 EVIDENCE SHIPPED, BUILD DECLINED** (backlog 155, PR #1111). Two characterisation pins in `tests/test_intake_mail.py`. Archive scan, in-machine read-only over `/data/inbound`: 91 `.eml`, 0 nested `message/rfc822`, 0 HEIC, 30 mails with both a PDF and a real body whose numbers are mostly the PDF's (9 of 10, 11 of 12, 14 of 28). Not built, each with its count: a nested-`.eml` unpacker (`msg.walk()` already descends, now pinned), HEIC conversion, rendering a body beside an attachment. Reopen condition for the last one: a body carrying an AMOUNT the attachment does not.
- **Numbering, because three sessions append:** the MEMORY sibling took backlog 154 (note M2) and Shipped rows 100 + 101 mid-branch, and their conflict resolution relabelled this session's T1 and T3 STATUS rows as "item 154"; that is repaired in PR #1111. Take a number only after `git merge origin/main`.

## Queue, in order

1. **Deploy T1 + T4 and verify.** `16de8a1b` is merged and not on Fly. After deploying, probe `set_aside[].document_id` live on **July `50622baec444`** or **September `51a22ad72864`** (both hold set-aside entries; August holds none), and re-drive cold. Expect the key present on entries with a stored receipt.
2. **Backlog item 155 — carry the operator's prose onto provenance.** Above the forward Dirk types the filing instruction, and it exists nowhere in the PDF. Verbatim from the live archive: "This is ZOHO BOOKS for CorpServ So it is split between BCS and BTS Booked to It subscriptions in CorpServ." (Zoho 50102456463), "CorpServ only Dev IT costs" (Lovable #2247-1655-6392), "BTS only" (Google Workspace 5668402379), "BTS" (Brave #2244-2487), "Reviewed the account..." (Afi #2568-2661). The intake READS it (`_archive_body_text` fingerprints it) and drops it: `_provenance_entry` (`web/intake_mail.py` ~1259) records sender, `received_at`, `archive`, `transport_tls` and the untrusted flags, no body text. Build: carry the text ABOVE the quoted forward onto the provenance of the files that mail delivered, and show it on the expense row as a note from the sender. **DISPLAY ONLY, never routing** — mail text is untrusted inbound, so it cannot choose an entity, category, cost center or recipient; the reviewer reads it and decides. The real work is the boundary rule (a plain-text forward marker, an Outlook `From:` block, a `<blockquote>`); getting it wrong in the safe direction means showing too much, never too little. This one HAS an SPA surface, so it needs a Lovable prompt.
3. **Only if the queue is otherwise empty:** `set_tool_decision`'s `statement_id` stamp is wired and exercised by no fixture (a fresh attach writes zero `decisions` rows and the fixture has no `decided_by='tool'` row). Find the path that writes one (item 76 self-confirm) and pin it, or record that no fixture reaches it.

Append each to the backlog as its own item when you first push, taking the next free number AFTER `git merge origin/main`; keep "(note item T4)" or the equivalent in the heading so cross-references survive renumbering. When the queue is empty, follow SESSION LOOP step 9.

## How to work

- Your worktree, cut fresh: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin` then `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-trace-<item> C:\Users\neuma_p1qrsic\Repo\agentic-ops1-trace origin/main`. One branch per queue item, reusing the `agentic-ops1-trace` directory after each merge (remove the worktree, cut again off origin/main after a fetch). Never edit, commit or stash in the main checkout; never `git stash` anywhere. A hook refuses `cd X && ...`; use `git -C`, `uv run --directory`, absolute paths. The GitHub slug is `011matthias/agentic-ops1.01` (pass `--repo` to `gh`; `MSYS_NO_PATHCONV=1` for colon pathspecs, and then give `-C` a `C:/...` path).
- Siblings edit `web/service.py`, `web/app.py`, `tests/test_view_contract.py`, `docs/api-contract.md`, `docs/PROMPT-STATUS.md`, the backlog and the status file all day. Append at the END of the relevant block; never renumber, re-sort or reflow. Before the first push `git rebase origin/main` is fine; after any push only `git merge origin/main`, never rebase, never force-push. Re-run the module suite after every merge from main. On a conflict in a shared file keep both sides (the files are CRLF: a resolver regex needs `\r?\n`) — and check whether a sibling's own resolution mangled YOUR rows, which happened on 2026-09-18.
- Live reads only. API `https://brisken-expense-recon.fly.dev` (also `api.expenses.brisken.com`): `POST /api/login {"code": ...}` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never print it; read it inside a script). Months: July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`; list `GET /api/expense-batches` (key `batch_id`). Never fetch `GET /runs/{id}/expense-report.pdf` live (it writes render outcomes); `reconciliation-report.pdf` is read-only. No writes to Criss's months; any production mutation beyond a deploy goes through `AskUserQuestion` as a decision with a recommendation, never "say the word". Windows Python cannot open `/c/...` paths: pass `C:\...`. In-machine read-only scans: base64 a script into `flyctl ssh console -a brisken-expense-recon --pty=false -C "sh -c 'echo <b64> | base64 -d > /tmp/x.py && python3 /tmp/x.py; rm -f /tmp/x.py'"` (the image has pypdf). **The mail archive is `/data/inbound`, NOT `/data/mail`** — a scan of the wrong path exits 0 and reports zero findings, so print a count of what the instrument found before using its output. Read-only DB copy when needed: in-machine `sqlite3.backup`, then `MSYS_NO_PATHCONV=1 flyctl ssh sftp get -a brisken-expense-recon /tmp/<f> 'C:\...\scratchpad\<f>'`; delete both copies when done.
- Build: route-level tests through the FastAPI app, at least one through the CALLER the fix changed; prove each wiring point red by hand (cp the source aside, one-line mutation via a script written with the Write tool, targeted tests, cp back, sha256 equal) because `tools/regress_check.py` prints "RED (no pytest summary line)" whether or not the suite failed; never restore with `git checkout --`. **Check the anchor really sits in the function you think**: on 2026-09-18 a mutation aimed at `set_decision` landed in `set_tool_decision` and read as "this point does not bite". Suite: `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q -p no:cacheprovider` (about 6 minutes alone, longer with siblings running theirs; 2593 passed / 2 skipped on the T4 branch). Run it in the background and wait for the notification. Ruff on the module: `uv run --no-project --with ruff --directory <module dir> ruff check src tests`. Python heredocs with triple quotes and heredocs carrying backslashes are blocked by hooks: write scripts with the Write tool. Document every new field in `docs/api-contract.md` and pin every new list field in `tests/test_view_contract.py` (both contract dicts and both MUST_COVER sets) in the same PR; a new SCALAR gets its own pin test instead, since those dicts pin list element types only.
- Ship: commit on the item branch with explicit pathspecs, push, `gh pr create --repo 011matthias/agentic-ops1.01` (suite count before and after plus the red-proof lines in the body), wait for CI (`gh pr checks <n> --repo ...`; `test` is the module suite), `gh pr merge --squash --delete-branch` on green. The backlog move to Shipped and the status file update land in the same PR.
- Deploy (pre-authorized, one Fly app shared with the siblings): after the merge, probe the live API for YOUR field first; a sibling's deploy may already carry your commit (`flyctl releases -a brisken-expense-recon`; v188 carries T3). If absent and no release is in progress: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add --detach C:\Users\neuma_p1qrsic\Repo\agentic-ops1-deploy-trace origin/main`, confirm your merge is in `git log -1` there, `MSYS_NO_PATHCONV=1 flyctl deploy "<module dir>" --config "<module dir>/fly.toml" -a brisken-expense-recon --remote-only`, then remove that worktree. Then a live API probe of the changed field and a cold browser read-back.
- Cold browser drives: headless Playwright with `channel="chrome"` (`uv run --no-project --with playwright python <script>`; `agent-browser` hung twice on this host). Log in at the gate (the code read from `.env` inside the script), wait for localStorage `erc-token`, dismiss "Leave feedback anywhere" by clicking the "Got it" text, go to `/months`, click the month, land on `/expenses/{id}`; record every non-GET request and assert only the login. The deploy-consumer gate does not see a script drive: state the coverage explicitly in the closing text, and when the SPA has no renderer for your field say in those words that the drive asserts no regression on the changed route and the API read shows the field.
- SPA work: write `docs/lovable-<slug>-prompt.md` (background, exact JSON shapes, render rule, EN + PT-BR strings, do-not-change list, checks), add a Not-applied row to `docs/PROMPT-STATUS.md`, and hand the whole prompt in the reply inside a FOUR-backtick fence under the label **"Paste into Lovable:"**. Label every fence: "Paste into Lovable:" or "Continuation prompt for Claude Code:". The SPA needed no change for T3, T1 or T4; item 155 DOES have a surface, so it needs one.
- Checkpoint branches: `docs/checkpoint-trace-<n>` in `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-trace` (trace-1 and trace-2 are used), cut off origin/main at checkpoint time; `checkpoint_scaffold.py --root <that worktree> pre` and `--root <that worktree> finalize` (the `--root` goes BEFORE the subcommand), and note that `finalize` picks the Mini-Checkpoint-N number itself, so write the prose file only after it tells you the name. Run `uv run tools/repair-session-log.py docs/sessions/<date>.md --check` there before pushing (three sessions write the same log today). Remove only the worktrees and branches YOU created; print `git worktree list` and `gh pr list --repo 011matthias/agentic-ops1.01 --state open --search trace` at every stop.

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
