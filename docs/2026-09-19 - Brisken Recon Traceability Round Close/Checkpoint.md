# Checkpoint: Brisken Recon Traceability Round Close

**Date:** 2026-09-19
**Status:** Queue closed. T3, T1 and T4 shipped, merged and live; two follow-on items open (backlog 155, and a pin for `set_tool_decision`).

---

## Summary

The TRACEABILITY session of three parallel sessions on the owner's 2026-09-18
note. All three queue items shipped: a charge now carries a record of which
statement upload printed it and where, a receipt is named the same way on
every surface, and the mail archive was scanned to settle what the intake
should and should not be taught to read.

---

## What Was Done This Session

### T3 — the receipt-to-line link survives as a record (backlog 152)

1. New snapshot key `statement_origins` (`{file: {transaction_id: {"row": n} |
   {"page": n} | {}}}`), written by both callers that write
   `statement_anchors` and kept apart from them because the anchors' emptiness
   is load-bearing for the writeback.
2. `rows[]` and `expenses[]` carry `statement_file`, `statement_id`, and
   `source_row` (a workbook line) or `source_page` (a PDF one); `expenses[]`
   also carries `transaction_id`, read from the EFFECTIVE settlement.
3. The Chase PDF parser records the page: `_extract_pages` keeps the text
   layer apart per page and hands `parse_statement_text` a line-to-page index.
4. `statement_id` columns on `decisions`, `decision_history` and
   `receipt_claims`, resolved inside `store.py` from the snapshot rather than
   threaded through seventeen writers.
5. Item 72's heading marks it closed by item 103.

### T1 — a receipt is the same receipt on every surface (backlog 153)

1. Audited every receipt-bearing surface on three live months. All six object
   surfaces already carried `document_id` at 100%; the three string surfaces
   carry it AS the string.
2. One gap: `set_aside[]` named the same value `file`. Added
   `set_aside[].document_id` beside it, read from the entry's stored receipt.

### T4 — the whole message is walked (backlog 155)

1. Scanned 91 stored `.eml` in-machine, read-only.
2. Shipped two characterisation pins; declined three builds with the count
   behind each.
3. Filed backlog item 155 for the finding the note had not anticipated.

### Round close

1. Mini-checkpoint PR #1113 mid-round; this full checkpoint at the close.
2. Continuation prompt written for the next session covering item 155 and the
   `set_tool_decision` pin.

---

## Key Decisions Made

### Record the PDF page rather than declare it unrecorded

- **Choice:** built `Transaction.source_page` and the parser change, instead of
  taking the brief's offered alternative of stating that no page is recorded.
- **Rationale:** live August actually holds a PDF statement
  (`20260804-statements-1176-.pdf`, 3 charges). The writeback anchors are
  deliberately empty for a PDF, so those three charges could name neither a row
  nor an upload. "Not recorded" would have been a true sentence about a real
  gap that was cheap to close.

### Resolve the statement id inside the store, not at the call sites

- **Choice:** `store.py` resolves `(run_id, transaction_id) -> statement_id`
  from the snapshot behind a per-run memo, dropped whenever the store rewrites
  a snapshot.
- **Rationale:** the value is a pure function of its two keys, so seventeen
  callers could only get it wrong, and `decision_history` is append-only, which
  means the value has to be right at INSERT.

### Close T4's build question, then file what the judging turned up

- **Choice:** declined the nested-`.eml` unpacker, HEIC conversion and
  body-beside-attachment rendering; filed item 155 rather than building it.
- **Rationale:** each decline has a count behind it (0 nested rfc822, 0 HEIC,
  body numbers 9-of-10 to 14-of-28 duplicated from the PDF). The operator-prose
  finding is a new function needing a boundary rule and an untrusted-inbound
  constraint; half-building it at 452k context would have been worse than
  recording it with the evidence.

### Do not touch the two stale p2 status files

- **Choice:** left `p2-product-decks.md` (58d) and `p2-targeting.md` (59d) flagged.
- **Rationale:** different workstream, different session's scope. Updating
  another session's status file is the collision this round already paid for
  twice.

---

## What Did NOT Work (and why)

- **Scanning the mail archive at `/data/mail`:** the path does not exist, so the
  scan reported "0 mails with a PDF attachment and a real body" with every
  command exiting 0. The archive is `<data_root>/inbound`. Caught only because
  the 0 contradicted a count from the prior session; the rerun prints the
  `.eml` count first so the instrument proves itself before its output is used.
- **The first red proof of `set_decision`'s stamp:** the anchor text
  (`self.conn.commit()` + `return cur.rowcount > 0`) ends `set_tool_decision`,
  not `set_decision`, so the mutation left the suite green and read as "this
  wiring point does not bite". Re-anchoring on `set_decision`'s own tail made
  it red at 3 tests.
- **A test asserting the matcher's own verdict carries the statement id:**
  chasing the above showed a fresh attach writes ZERO rows to `decisions` and
  the fixture holds no `decided_by='tool'` row at all, so the test asserted a
  premise the month never reaches. Dropped rather than kept; this is now
  backlog queue item 2.
- **`tools/regress_check.py` for any of the twelve wiring proofs:** it prints
  `RED (no pytest summary line)` whether or not the suite failed, so every
  proof was hand-rolled (cp aside, one-line mutation, targeted tests, cp back,
  sha256 equal).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `web/statement_origin.py` | created | the `statement_origins` key + reader, shared by `service.py` and `store.py` |
| `web/service.py` | edited | record `_origins` at both commit sites; origin fields on `rows[]` and `expenses[]`; `set_aside[].document_id` |
| `web/store.py` | edited | three `statement_id` columns, the per-run origin memo, the stamp at five writers |
| `matching/types.py`, `web/serialize.py` | edited | `Transaction.source_page` both ways |
| `ingest/statement_pdf.py` | edited | `_extract_pages` / `_page_starts` / `page_starts=` |
| `tests/test_charge_origin_t3.py` | created | 11 route-level tests for the charge origin |
| `tests/test_document_type_quarantine.py` | edited | 2 tests for the set-aside document id |
| `tests/test_intake_mail.py` | edited | 2 characterisation pins for the mail walk |
| `tests/test_view_contract.py` | edited | 3 scalar pins |
| `tests/test_web_pdf_upload.py` | edited | stub moved from `_extract_text` to `_extract_pages` |
| `docs/api-contract.md` | edited | two new sections |
| `status/p1-improvement-backlog.md`, `status/p1-expense-reconciliation.md` | edited | items 152, 153, 155; Shipped rows 98, 99, 102 |

---

## Current Status

Everything this session produced is merged and, where it needed deploying,
live. T3 is on Fly v188 and T1 rode a sibling's v189; T4 changed no runtime
behaviour. Live July carries `statement_file` + `source_row` on 112 of 112
charges and August on 111 of 114 (the three exceptions are the PDF-sourced
ones), both through the anchors fallback, because both months predate
`statement_origins`. `statement_id` and `source_page` stay absent on both
until Criss re-reads them, which this session deliberately did not trigger.

brisken platform: unknown plan, `~?/?` ops/mo, last assessed `?`.
brisken comms-log is 11 days stale (last touched 2026-09-08).

---

## Next Steps

1. **Backlog item 155** — carry the operator's prose above a forward onto
   provenance as a display-only note, with a Lovable prompt. The boundary rule
   (where the operator's text ends and the quoted forward begins) is the work.
2. **Pin `set_tool_decision`'s `statement_id` stamp**, or record in the
   contract that no fixture reaches it.
3. Run `/ops-audit brisken`: the platform block has no plan, no ops figure and
   no assessment date.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  (the two 2026-09-18 sections at the end)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 155
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/intake_mail.py`
  (`_provenance_entry` ~1259, `_archive_body_text` ~1283, `inbound_root` ~822)

### Open Questions
- Where the "text above the quoted forward" boundary lies: the archive holds a
  plain-text `Begin forwarded message:` marker, an Outlook `From:/Date:/To:/Subject:`
  block, and HTML `<blockquote>`. Derive from the 30 real mails.
- Whether a body-only mail, which already becomes a rendered receipt, should
  also record its text as a note. Decide explicitly.
- Covered-vs-quote licence question, still open with the owner and explicitly
  not gating this work.
- brisken comms-log is 11 days stale; any client conversations since
  2026-09-08 are unlogged.

### Working Notes
- The five live operator notes, verbatim, are in backlog item 155 and in the
  continuation prompt. They are the test corpus for the boundary rule.
- The mail archive is `/data/inbound`. A scan of a wrong path exits 0 and
  reports zero findings.
- 30 of 91 mails carry both a PDF and a real body; 5 of those 30 carry an
  operator note. 48 are body-only (a different path), 19 have 2+ PDFs.
- `expenses[]` already carries `submitted_by` and `untrusted_instructions`
  from provenance, which is where a note field belongs.
- `docs/lovable-untrusted-flag-prompt.md` (item 93) is the nearest precedent
  for the Lovable prompt: same row, same untrusted-text framing.

### Reference Materials
- PRs #1107 (T3), #1109 (T1), #1111 (T4), #1113 (mini-checkpoint)
- Fly releases: v188 carries T3, v189 carries T1
- `docs/2026-09-18 - Brisken Recon Traceability T3 T1 T4/Mini-Checkpoint-2.md`
  (carries the mid-round continuation prompt)

---

## How to Continue

Paste the continuation prompt appended below into a fresh session. It opens
with `/comd_resume brisken`, carries the two open items with their code
pointers and live evidence, and embeds the SESSION LOOP verbatim.

---

## Strategic Feedback

### What Worked Well This Session

- **Reading the live months before building each item.** T3's design changed
  because August turned out to hold a PDF statement; T1's scope shrank from
  "fix the surfaces" to "fix one naming" because five of six surfaces were
  already correct. Both would have been wrong builds on assumption.
- **Hand red-proofs over `regress_check.py`.** Twelve mutations, two of which
  found real problems: one mis-anchored (proving the proof itself needs
  checking) and one exposing a test built on a false premise. A green suite
  would have shipped both.
- **Declining three builds with a count behind each.** T4's value was mostly in
  what it did not build, and the counts are what make that reviewable rather
  than a judgment call nobody can re-check.

### Suggestions

- **Fix or retire `tools/regress_check.py`.** It has printed `RED` regardless of
  outcome for at least two sessions, and every session now hand-rolls around
  it. Parsing the pytest exit code is a small change; a tool that reports
  success unconditionally is worse than no tool, because its output reads as
  evidence. Logged as `infrastructure-deferred`.

### System Health

- **Autonomy: 1 human intervention** (the user had to ask where the checkpoint,
  Lovable prompt and continuation prompt were, after T4's build finished). The
  SESSION LOOP's steps 5-7 were due at that point and I treated "queue not yet
  fully merged" as "loop tail not yet due".
- Three sessions writing one ledger cost two extra merge-resolve cycles and a
  duplicated session-log number. `repair-session-log.py` caught the log half; a
  cheap lint for duplicate backlog item numbers and duplicate Shipped iteration
  numbers would catch the other half.

---

## Continuation prompt for the next session

/comd_resume brisken

Owner directive 2026-09-18 stands: the items in this prompt are to be built now; the covered-vs-quote licence question does not gate them. You are the TRACEABILITY session. Sibling sessions (MEMORY on the M-notes, MATCHING on the X-notes) may run at the same time on the same repo and the same Fly app: follow the parallel-safety rules in "How to work" exactly.

Read first: `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`, then in that module `docs/api-contract.md` (the two 2026-09-18 sections near the end: "A charge names the statement line it was printed on" and "A receipt is the same receipt on every surface"), backlog item 155 in `workspace/clients/brisken/status/p1-improvement-backlog.md`, and the memories `project_brisken_expense_recon_usability_loop` (the 2026-09-18 TRACEABILITY paragraph first), `project_brisken_expense_recon_mail_intake`, `feedback_recon_no_live_writes_criss_acts`, `feedback_prompts_are_pasteable_text`, `feedback_continuation_prompt_carries_loop`, `rule_untrusted_inbound`.

## Where it stands

The previous TRACEABILITY session closed its whole queue. Nothing is in flight; both items below are new work it uncovered.

- **T3 charge origin SHIPPED and LIVE** (backlog 152, PR #1107, merge `b1fe1d28`, Fly **v188**). Snapshot key `statement_origins` = `{file: {transaction_id: {"row": n} | {"page": n} | {}}}`, written by both callers that write `statement_anchors`. `rows[]` and `expenses[]` carry `statement_file`, `statement_id`, `source_row` (workbook) or `source_page` (PDF); `expenses[]` also carries `transaction_id` from the EFFECTIVE settlement. `Transaction.source_page` + `ingest/statement_pdf.py` `_extract_pages` / `_page_starts`. `statement_id` columns on `decisions` / `decision_history` / `receipt_claims`, resolved inside `store.py` (`_charge_origins` memo dropped in `update_run_snapshot`; `_history_statement_id` for the append-only table). Shared reader: `web/statement_origin.py`, in its own module so `store.py` never imports `service.py`. Live: July 112 of 112 and August 111 of 114 charges carry `statement_file` + `source_row` via the anchors fallback; the 3 August charges that do not are the PDF-sourced ones. `statement_id` and `source_page` stay ABSENT on both months until Criss re-reads them.
- **T1 receipt identity SHIPPED and LIVE** (backlog 153, PR #1109, merge `16de8a1b`, Fly **v189**). `set_aside[].document_id` beside `file`, read from the entry's STORED RECEIPT, absent on a legacy `_derive_legacy_set_aside` entry. Verified live: July 5 of 5, September 3 of 3; the three restored July entries match an expense id.
- **T4 evidence SHIPPED, build declined** (backlog 155, PR #1111, merge `f721e094`). Archive scan, in-machine read-only over `/data/inbound`: 91 `.eml`, 0 nested `message/rfc822`, 0 HEIC, 30 mails with both a PDF and a real body whose numbers are mostly the PDF's. Not built with the count behind each: a nested-`.eml` unpacker (`msg.walk()` already descends, now pinned in `tests/test_intake_mail.py`), HEIC conversion, rendering a body beside an attachment. Reopen condition for the last: a body carrying an AMOUNT the attachment does not.
- Checkpoints: mini PR #1113 (merge `deed9d7d`) mid-round, full checkpoint at the round close. No worktrees, branches or bg-watches left over.

## Queue, in order

### 1. Backlog item 155 — the operator's note above a forward reaches the row

**The finding, with live evidence.** Above the forwarded vendor mail Dirk types the FILING INSTRUCTION, and it exists nowhere in the attached PDF. Verbatim from the live archive, 2026-09-18:

- "This is ZOHO BOOKS for CorpServ So it is split between BCS and BTS Booked to It subscriptions in CorpServ." (Zoho invoice 50102456463)
- "CorpServ only Dev IT costs" (Lovable #2247-1655-6392)
- "BTS only" (Google Workspace 5668402379)
- "BTS" (Brave #2244-2487)
- "Reviewed the account..." (Afi Technologies #2568-2661)

5 of the 30 attachment-bearing mails carry one. That is the entity, the cost split and the category, from the person who knows, and Criss cannot see any of it.

**What happens today.** The intake READS that text and drops it. `_archive_body_text` (`web/intake_mail.py` ~1283, delegating to `body_render.extract_body_text`) is called for fingerprinting (`content_fingerprints` ~1230) and for the body-only render path, but `_provenance_entry` (~1259) records only the person fields, `received_at`, `archive`, `transport_tls` and `untrusted_instructions` — no body text. Provenance reaches the receipts through `provenance_by_digest` (~2426) / `provenance: dict[str, dict]` (~2492) and surfaces on `expenses[]` beside `submitted_by` and `untrusted_instructions`, which is exactly where the note belongs. Pinned as it behaves today by `test_the_operator_note_above_a_forward_is_read_but_reaches_no_receipt`.

**Build.** Carry the operator's own prose — the text ABOVE the quoted forward — onto the provenance of the files that mail delivered, and render it on the expense row as a note from the sender.

- **DISPLAY ONLY. It must never route.** Mail text is untrusted inbound (`rule_untrusted_inbound`): it cannot choose an entity, a category, a cost center, a card or a recipient, and no LLM call may be given it as instruction. The reviewer reads it and decides. Say this in the contract section and in the Lovable prompt.
- **The real work is the boundary rule**: where the operator's text ends and the quoted forward begins. Three shapes in the live archive: a plain-text forward marker (`Begin forwarded message:`), an Outlook header block (`From: ... Date: ... To: ... Subject:`), and an HTML `<blockquote>`. Derive the rule from the 30 real mails, not from a guess — re-run the scan (see "How to work" for the in-machine recipe; the archive is `/data/inbound`) and print, for each of the 5 known carriers, what your rule would keep. Erring long is safe, erring short loses the instruction, so when the boundary is unclear keep MORE.
- Parallel field, ABSENT when there is no prose (25 of the 30 have none, and all 48 body-only mails are a different path entirely). Never an empty string.
- A body-only mail already becomes a rendered receipt; do not double-record its text as a note as well. Decide that explicitly and say which way in the PR.
- Document the field in `docs/api-contract.md`, pin it in `tests/test_view_contract.py` (a scalar gets its own pin test; the two contract dicts pin list element types only), and prove each wiring point red by hand.

**This one HAS an SPA surface.** Write `docs/lovable-operator-note-prompt.md`, add a Not-applied row to `docs/PROMPT-STATUS.md`, and hand the WHOLE prompt in the reply inside a four-backtick fence under the label **"Paste into Lovable:"**. `docs/lovable-untrusted-flag-prompt.md` (item 93) is the nearest precedent: same row, same neighbourhood, same untrusted-text framing. EN + PT-BR strings, exact JSON shape, render rule, do-not-change list, checks.

### 2. Pin `set_tool_decision`'s `statement_id` stamp

T3 wired the stamp into all five `decisions` writers, but `set_tool_decision`'s wire is exercised by NO fixture: a fresh attach writes zero rows to `decisions`, and the T3 fixture has no `decided_by='tool'` row at all (checked by probe, 2026-09-18). A wire no test reaches is a wire nobody knows is working.

Find the path that writes a tool verdict — item 76's self-confirm of clean rows is the candidate — build a fixture that reaches it, and assert the row carries the statement id. If no route can reach it, say so in the PR and record in `docs/api-contract.md` that the wire exists and nothing exercises it, rather than leaving the gap silent. Either outcome closes the item; the wrong outcome is a test that passes without touching `set_tool_decision` (that is the exact trap that made a red proof read green on 2026-09-18).

Append each item to the backlog as its own entry when you first push, taking the next free number AFTER `git merge origin/main` (item 155 already exists; do not renumber it). When the queue is empty, follow SESSION LOOP step 9.

## How to work

- Your worktree, cut fresh: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin` then `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-trace-<item> C:\Users\neuma_p1qrsic\Repo\agentic-ops1-trace origin/main`. One branch per queue item, reusing the `agentic-ops1-trace` directory after each merge (remove the worktree, cut again off origin/main after a fetch). Never edit, commit or stash in the main checkout; never `git stash` anywhere. A hook refuses `cd X && ...`; use `git -C`, `uv run --directory`, absolute paths. The GitHub slug is `011matthias/agentic-ops1.01` (pass `--repo` to `gh`; `MSYS_NO_PATHCONV=1` for colon pathspecs, and then give `-C` a `C:/...` path).
- Siblings edit `web/service.py`, `web/app.py`, `web/intake_mail.py`, `tests/test_view_contract.py`, `docs/api-contract.md`, `docs/PROMPT-STATUS.md`, the backlog and the status file. Append at the END of the relevant block; never renumber, re-sort or reflow. Before the first push `git rebase origin/main` is fine; after any push only `git merge origin/main`, never rebase, never force-push. Re-run the module suite after every merge from main. On a conflict in a shared file keep both sides (the files are CRLF: a resolver regex needs `\r?\n`) — and check whether a sibling's own resolution mangled YOUR rows: on 2026-09-18 a sibling relabelled this session's T1 and T3 status rows as its own item number, and two session-log entries both landed as 13.
- Live reads only. API `https://brisken-expense-recon.fly.dev` (also `api.expenses.brisken.com`): `POST /api/login {"code": ...}` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never print it; read it inside a script). Months: July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`; list `GET /api/expense-batches` (key `batch_id`). Never fetch `GET /runs/{id}/expense-report.pdf` live (it writes render outcomes); `reconciliation-report.pdf` is read-only. No writes to Criss's months; any production mutation beyond a deploy goes through `AskUserQuestion` as a decision with a recommendation, never "say the word". Windows Python cannot open `/c/...` paths: pass `C:\...`. In-machine read-only scans: base64 a script into `flyctl ssh console -a brisken-expense-recon --pty=false -C "sh -c 'echo <b64> | base64 -d > /tmp/x.py && python3 /tmp/x.py; rm -f /tmp/x.py'"` (the image has pypdf). **The mail archive is `/data/inbound`, NOT `/data/mail`** — a scan of the wrong path exits 0 and reports zero findings, so have the script print a count of what it found before you use its output. Read-only DB copy when needed: in-machine `sqlite3.backup`, then `MSYS_NO_PATHCONV=1 flyctl ssh sftp get -a brisken-expense-recon /tmp/<f> 'C:\...\scratchpad\<f>'`; delete both copies when done.
- Build: route-level tests through the FastAPI app, at least one through the CALLER the fix changed; prove each wiring point red by hand (cp the source aside, one-line mutation via a script written with the Write tool, targeted tests, cp back, sha256 equal) because `tools/regress_check.py` prints "RED (no pytest summary line)" whether or not the suite failed; never restore with `git checkout --`. **Check the anchor really sits in the function you think** — on 2026-09-18 a mutation aimed at `set_decision` landed in `set_tool_decision` and read as "this point does not bite". Suite: `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q -p no:cacheprovider` (about 6 minutes alone, longer with siblings running theirs; 2603 passed / 2 skipped at `f721e094`). Run it in the background and wait for the notification. Ruff on the module: `uv run --no-project --with ruff --directory <module dir> ruff check src tests`. Python heredocs with triple quotes and heredocs carrying backslashes are blocked by hooks: write scripts with the Write tool.
- Ship: commit on the item branch with explicit pathspecs, push, `gh pr create --repo 011matthias/agentic-ops1.01` (suite count before and after plus the red-proof lines in the body), wait for CI (`gh pr checks <n> --repo ...`; `test` is the module suite), `gh pr merge --squash --delete-branch` on green. The backlog move to Shipped and the status file update land in the same PR.
- Deploy (pre-authorized, one Fly app shared with the siblings): after the merge, probe the live API for YOUR field first; a sibling's deploy may already carry your commit (`flyctl releases -a brisken-expense-recon`; v188 carries T3, v189 carries T1). If absent and no release is in progress: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add --detach C:\Users\neuma_p1qrsic\Repo\agentic-ops1-deploy-trace origin/main`, confirm your merge is in `git log -1` there, `MSYS_NO_PATHCONV=1 flyctl deploy "<module dir>" --config "<module dir>/fly.toml" -a brisken-expense-recon --remote-only`, then remove that worktree. Then a live API probe of the changed field and a cold browser read-back.
- Cold browser drives: headless Playwright with `channel="chrome"` (`uv run --no-project --with playwright python <script>`; `agent-browser` hung twice on this host). Log in at the gate (the code read from `.env` inside the script), wait for localStorage `erc-token`, dismiss "Leave feedback anywhere" by clicking the "Got it" text, go to `/months`, click the month, land on `/expenses/{id}`; record every non-GET request and assert only the login. The deploy-consumer gate does not see a script drive: state the coverage explicitly in the closing text. Item 155's note has a renderer only AFTER the owner pastes the Lovable prompt, so until then the drive asserts no regression on the changed route and the API read shows the field — say that split in those words rather than claiming a renderer was verified.
- SPA work: `docs/lovable-<slug>-prompt.md` (background in one paragraph, the new fields with their exact JSON shape, the render rule, EN + PT-BR strings, a do-not-change list, checks; no Supabase, auth stays the bearer token), a Not-applied row in `docs/PROMPT-STATUS.md`, and the WHOLE prompt in the reply inside a FOUR-backtick fence. Label every fence: "Paste into Lovable:" or "Continuation prompt for Claude Code:". A file path is not the deliverable.
- Checkpoint branches: `docs/checkpoint-trace-<n>` in `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-trace` (trace-1, trace-2 and trace-3 are used), cut off origin/main at checkpoint time; `checkpoint_scaffold.py --root <that worktree> pre` and `--root <that worktree> finalize` (`--root` goes BEFORE the subcommand), and `finalize` picks the Mini-Checkpoint-N number itself, so write the prose file only after it names it. Run `uv run tools/repair-session-log.py docs/sessions/<date>.md --check` there before pushing AND again after any merge from main. Remove only the worktrees and branches YOU created; print `git worktree list` and `gh pr list --repo 011matthias/agentic-ops1.01 --state open --search trace` at every stop.

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
