# Checkpoint: Brisken Recon Items 117 And 121

**Date:** 2026-09-17
**Status:** Items 117 + 121 shipped and deployed (Fly v153); stopped at the HIGH pressure band (~500k) by the owner's loop rule

---

## Summary
Of the five pre-October voids-audit defects in the brief, three (94, 116, 100) were already being built by sibling session b5b01897 on owner rulings from 12:21; this session built the other two, 117 (one-word merchant aliases as wildcards) and 121 (held-mail alerts), deployed both as v153, and deleted the three legacy July test runs on owner yes.

---

## What Was Done This Session

### Collision check before building
1. The handoff prompt said nothing had moved on main; `git worktree list` showed three sibling worktrees (item-94, items-116-95, items-99-100) with files edited minutes earlier. Sibling transcripts (b5b01897) showed the owner had already ruled 94 "exclude everywhere", 99 "only when complete", 100 "gate only". The item-94 question was not re-asked; those items were left to the sibling (all merged later: #993, #997, #998).

### Item 117 (PR #1003, merged 76f7e380)
1. `merchant_registry.py`: aliases made only of generic words (`GENERIC_MERCHANT_WORDS`, plurals folded) are ignored; a fuzzy hit needs the merchant's first distinctive word and is discounted by the vendor's uncovered distinctive words; exact distinctive-word equality matches at the full threshold; number-only names identified by the number.
2. `web/app.py` settings PUT passes the stored map: a NEW generic alias -> 400, stored ones accepted.
3. `seed_registry.build_merchants` drops generic aliases (its `--put` would otherwise 400).
4. Replay harness over a read-only sftp copy of `/data/recon-web.sqlite` (all six months, 133 receipts) + local ER exports + registry self-probes + audit probes: 0 live receipts changed, only two ER wildcards closed, no new hit. Re-run inside the v153 container against live settings: same.
5. Adversarial review of draft 1 found three real defects (place-name wildcards, lost KI-MASSA hits, seed refusal); fixed in commit 2. Replay then caught "Cafe Americano" -> Americanas from the new same-words rule; fixed by using the full threshold there.
6. `tests/test_merchant_alias_wildcards.py`: route-level rows per rule, PUT, seed; five `regress_check` proofs red through a caller. Suite 2132 passed / 2 skipped.

### Item 121 (PR #1001, merged 9da9fdbc, built by a background agent)
1. `_maybe_alert` split: operator alert unchanged; `_maybe_notify_held_sender` sends one "Receipt not filed yet" notice per held status to the From address under the ack's exact guards (auto_ack, not auto-generated, no untrusted flags, @brisken.com or known_senders only), stamp `held_notice_at`. Four caller-level tests; suite 2092/2.

### Live writes (owner yes, each)
1. Deleted runs f639bef7813a / 1e09b8362948 / b67133b8df98 via typed-confirm after a read-only readiness check (unpublished, no borrowed/lent receipts, July/August reference none). Each 404s; `pooled_back` 0; memory kept. They held April 2026 Zoho ER lines, not July receipts.

### Deploy + records
1. v153 from detached origin/main worktree; healthz 200; deployed module markers present; in-container resolver check on live data. PR #1008 recorded both items (backlog headings + Shipped paragraphs, item-100 note, p1 status row).

---

## Key Decisions Made

### Item 121 recipients (owner)
- **Choice:** "one to matthias and one to the email it was sent by"; no `alert_recipients` settings write.
- **Rationale:** owner directive; the sender half is limited to our own senders because rule_untrusted_inbound forbids inbound From deciding a recipient.

### Item 117 stored aliases (owner)
- **Choice:** the 42 stored one-word aliases stay in settings, inert.
- **Rationale:** owner asked whether they are "in the way"; after the fix they do nothing, so no live write.

### Item 117 rule shape (agent)
- **Choice:** lead-word + coverage + exact distinctive-set match; NOT the reviewer's "distinctive words only" scoring.
- **Rationale:** that scoring files "Farmacia Pimentel" under AUTO POSTO PIMENTEL SAO JOSE; a false negative falls to the model, a false positive prints a wrong merchant as ready. Accepted loss: "NOBRE ATACADO E VAREJO", brand+place vendors.

### Items 96 / 97 (agent)
- **Choice:** not started.
- **Rationale:** both rewrite the reconciliation and month-report PDFs that owner items 137/138 (card separation, another session) restructure; the session also reached HIGH pressure.

---

## What Did NOT Work (and why)
- **Trusting the handoff prompt's "nothing has moved on main":** it was derived from `git log` only; three sibling worktrees with uncommitted work on items 94/116/100 existed.
- **Draft-1 coverage rule alone:** place names count as distinctive, so "Posto Sao Jose Ltda" and "Atacado Sao Jose" still matched; ignoring generic aliases lost "KI-MASSA CAFE".
- **Word-variant ratio 80 for the same-distinctive-words rule:** "americano"/"americanas" scores 84, filing "Cafe Americano" as Americanas; needs 88.
- **Word-variant ratio 88 for coverage:** "openal"/"openai" (one OCR letter) is 83; coverage needs 80.
- **`regress_check.py` with `/c/...` paths:** the tool runs pytest as a native Windows process; baseline read "no pytest summary line". Use `C:/...`.
- **`git merge ... | tail -1 && git push`:** the pipe hid the merge conflict and the push ran with the pre-merge commit (harmless on a feature branch).
- **First CI waiter `until ... = "0/7"`:** hangs forever if the check count differs; stopped and replaced with a bounded loop.
- **`uv run tools/session_state.py --status` from the primary clone:** printed sibling session 043738ec's reading (347k) while this session was at ~500k; the PostToolUse `[PRESSURE: ...]` advisory was the correct reading.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `expense-reconciliation/src/expense_recon/merchant_registry.py` | Edit | item 117 resolver rules + `normalize_merchants_setting(stored=)` |
| `expense-reconciliation/src/expense_recon/web/app.py` | Edit | PUT passes stored merchants |
| `expense-reconciliation/src/expense_recon/seed_registry.py` | Edit | seed drops generic aliases |
| `expense-reconciliation/tests/test_merchant_alias_wildcards.py` | Create | item 117 contract |
| `expense-reconciliation/src/expense_recon/web/intake_mail.py` | Edit (agent) | item 121 sender notice |
| `expense-reconciliation/tests/test_intake_mail.py` | Edit (agent) | item 121 tests |
| `expense-reconciliation/docs/api-contract.md` | Append | "A generic word is not a merchant alias" |
| `expense-reconciliation/docs/electronic-storage-system-description.md` | Edit (agent) | §11.3 outbound mail kinds |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edit | 117/121 shipped, item-100 note |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | element row |

---

## Current Status
Live: Fly v153 (117 + 121 + siblings' 94/95/99/100/102/116). Owner-side: fix known sender `neuamth4@icloud.com`; paste the sibling's pending SPA prompts (PROMPT-STATUS). Backlog headings of 94/95/99/100/116 were not yet marked SHIPPED on main at 13:40 UTC (sibling's to record). brisken ops status: platform unknown plan (no `platform` assessment in infrastructure.yaml). Comms log: none for brisken.

---

## Next Steps
1. Next defect items that avoid the PDFs and matching (verify no sibling claim first): 106 (mailed forward reads "Added"), 113 (failed/interrupted re-match leaves the month stale), 114 (dropped receipts have no safety copy), 103 (one receipt bound to two charges), 101 (confirm-all backend half), 105, 111, 112, 115, 130, 93.
2. After owner items 137/138 land: 96, 97, then matching items 131, 132, 133.
3. `graph_notify.py` header still says "Two message kinds" (now three).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 93-138, grep the heading, read in full)
- memory `project_brisken_expense_recon_voids_audit`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`
- `automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

### Open Questions
- None blocking; items 118 and 126 stay owner-side.

### Working Notes
- Sibling-claim check that works: `git worktree list` + `git -C <wt> status --porcelain` for every `client/brisken/p1-*` worktree + grep sibling transcripts (`~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<sid>.jsonl`) for the item number and their AskUserQuestion answers.
- Live snapshot copy for replays: `flyctl ssh sftp get -a brisken-expense-recon /data/recon-web.sqlite <scratchpad>`; delete after (receipt text inside). In-container read-only runs: base64 a script into `/tmp` via `flyctl ssh console -C "sh -c '...'"`, open sqlite with `mode=ro`.
- Probe helper: `%TEMP%\claude\recon-probe\api.py` (`get()`, token cached); POSTs need a hand-built Request with `api.token()`.
- CI waiter: poll `gh pr view N --json headRefOid,statusCheckRollup` bounded, break when head moved or all COMPLETED.

### Reference Materials
- PRs #1001, #1003, #1008; Fly releases v152 (sibling), v153 (this session)

---

## How to Continue
Paste the continuation prompt from the chat into a fresh session; it carries the pressure-stop and checkpoint loop.

---

## Strategic Feedback

### What Worked Well This Session
- Reading sibling transcripts before building: it surfaced three owner rulings already given and avoided building 94/116/100 twice.
- Replay before shipping plus an adversarial reviewer: the reviewer found three defects in a green draft, and the replay found a fourth (Cafe Americano) that the reviewer's own proposal would have introduced.

### Suggestions
- `tools/session_registry.py --check` should list sibling worktrees with dirty files per branch; that is the evidence a handoff prompt needs, and git history alone cannot show it.

### System Health
- `session_state.py --status` still reports another session's context reading after #1006 when run from the shared primary clone; trust the PostToolUse `[PRESSURE]` advisory until fixed.
- Autonomy: 1 human intervention (the owner decision round; the continuation directive was direction, not an unblock).
