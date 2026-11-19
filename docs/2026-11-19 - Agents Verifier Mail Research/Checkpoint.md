# Checkpoint: Agents Verifier Mail Research

**Date:** 2026-11-19
**Status:** Shipped (PR #1747, merged `e8a28a99`, CI green)

---

## Summary

Chose three agents from 90 days of usage data and built them with the instruments they need: a browser-driving `agnt_done-verifier`, a read-only `agnt_brisken-mail-reader`, and `agnt_sourced-researcher`. Each was run once on a real task, and what the runs exposed was fixed before merge.

---

## What Was Done This Session

### Usage analysis (why these three)
1. Git, 90 days: Brisken ~55% of file touches, expense-recon alone 2,232 of ~6,100. Friction register, 90 days: 158 of 294 rows Brisken; `verification-theater` 43, `slow-path` 108 (mostly hook-caught shell traps).
2. Transcripts, 30 days (older ones are pruned): `general-purpose` 55 calls, own agents 4 (proposal-research 2, comms-critic 2). The pipeline agents (build-orchestrator, implementation, testing, bug-fixer, deployer, n8n/make builders) had zero calls. 36 of the 55 general-purpose calls were classifiable: 14 market/GTM research, 13 KIT study, 4 WW/n8n, 2 recon, 2 fact checks.

### Built (PR #1747)
1. `tools/spa-readback.py`: cold-seat Playwright read-back on the installed Chrome (fresh context, service workers blocked), write guard (non-GET API calls aborted except the login POST), API replay with a 45 s brake, `press_sequentially` login, `--expect` / `--absent` / `--expect-url` / `--require-api`, `drive-blind` kept apart from content failures, refuses Git-Bash-mangled path arguments.
2. `tools/brisken-mail-search.py`: three-mailbox allowlist asserted on the CLI and on every Graph URL; default reads received mail in one all-folder query, `--walk` for sent copies and drafts; coverage report with `COMPLETE` / exit 3; 429/503/504 retried; `probe` counts the window's mail and checks a known sender.
3. `agnt_done-verifier` rewritten around drives, cold seat, differential baseline, freshness; recon settings built in. New `agnt_brisken-mail-reader` (FOUND / NOT FOUND / BLIND, earned negatives) and `agnt_sourced-researcher` (source, publisher, date, type per figure; TBD gaps).
4. `rule_brisken_graph_first`: Criss's mailbox is reachable (app-only 200 on 2026-11-11, inbox 33,312, 35 folders); the line saying she 403s was stale.

### Verification
1. 23 tests (12 spa-readback incl. 4 live local drives, 11 mail-search through `main()`); `regress_check.py` bit on the write guard, the folder-failure accounting and the retry.
2. Live, read-only: cold recon drive PASS (login POST the only write, 5 API calls); Criss GitHub receipts found (2 PDFs); Dirk Regus October: the one-query search (19 s) and the full 2,354-folder walk (25+ min) returned the same 4 messages.
3. Each agent run once as a general-purpose subagent reading its own file; their ambiguity notes were folded back (covered-by-drive rule, no `| tail`, vendor-claim and undated-page rules, probe as the broad differential).
4. `preflight-hooks.py --full`: 2,200 passed, 6 skipped (the live drives skip without Playwright, as in CI).

---

## Key Decisions Made

### Build instruments, not only prompts
- **Choice:** Each agent got a tested tool rather than instructions to hand-write Playwright or Graph code.
- **Rationale:** The register shows ad-hoc scan scripts rebuilt session after session; an agent that improvises its instrument cannot be regress-tested.

### Received mail via the aggregate, walk only for sent/drafts
- **Choice:** Default search is one query on `/users/{mbx}/messages`; `--walk` is opt-in.
- **Rationale:** Measured equal results (4/4 Regus hits) at 19 s vs 25+ min; the aggregate's known blind spot is the owner's own sent copies (feedback_brisken_outreach_truth_is_mailbox), which `--walk` covers.

### Recommended against a recon-builder agent and new pipeline agents
- **Choice:** Long build loops stay in the main session; agents cover the narrow repeated steps around them.
- **Rationale:** The pipeline agents went unused for 30 days while recon was the dominant work.

---

## What Did NOT Work (and why)

- **Service-worker hypothesis for the blind first recon drive:** blocking service workers left the guard at zero API requests; the real cause was Git Bash rewriting `--api-pattern /api/` into `C:/Program Files/Git/api/`. It cost three extra live drives on Criss's system.
- **Per-folder walk as the default mail search:** one month of Dirk's mailbox took 25+ minutes over 2,354 folders; the smoke-test agent reported BLIND mid-run.
- **Piping tool JSON through `2>&1 | python -c json.load`:** uv's "Installed N packages" stderr line broke the parse; write stdout and stderr to separate files instead.
- **`cd ... && gh pr merge`:** blocked by `block-merge-chained-after-any-command`; the merge must be its own call.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/agents/agnt_done-verifier.md` | rewritten | Browser drives, cold seat, differential, freshness |
| `.claude/agents/agnt_brisken-mail-reader.md` | created | Read-only Brisken mail agent |
| `.claude/agents/agnt_sourced-researcher.md` | created | Sourced market research agent |
| `tools/spa-readback.py` + `tools/tests/test_spa_readback.py` | created | Drive instrument + tests |
| `tools/brisken-mail-search.py` + `tools/tests/test_brisken_mail_search.py` | created | Mail instrument + tests |
| `.claude/rules/rule_brisken_graph_first.md` | edited | Criss reachable |
| `CLAUDE.md`, `tools/INDEX.md` | edited | Agent count 14, two INDEX rows |

---

## Current Status

All of PR #1747 is on `main`; the resumed session already listed the two new agent types, so the definitions load. brisken: no platform section in `infrastructure.yaml` (ops status unknown), no comms-log, and five status files stale 45-70 days (pre-existing, untouched here: p1-recon-loop-prompt, p2-lead-gen-general, p2-lovable-rebuild, p2-onepilot-site, p2-outreach-engine).

---

## Next Steps

1. Build the Stop-event session-header check deferred since 2026-10-29 (now `infrastructure-deferred`; the header was skipped again this session).
2. Decide `agnt_deployer`: it only knows Railway while the live apps deploy to Fly through `deploy.py`; rewrite for Fly or retire it.
3. Add `tools/eval-agents.py` fixtures for the three agents (a recon drive with a known baseline, a mail question with a known answer, a research question with a known price) so prompt edits get a before/after grade.
4. Next Brisken session: bring the five stale status files current or delete what shipped.

---

## Context for Next Session

### Files to Read First
- `.claude/agents/agnt_done-verifier.md`
- `.claude/agents/agnt_brisken-mail-reader.md`
- `tools/INDEX.md` rows for `spa-readback.py` and `brisken-mail-search.py`

### Open Questions
- Should `agnt_deployer` be rewritten for Fly or removed?
- Should the 13 KIT study delegations get their own agent? (Personal scope; the `skript` skill and `WS2627\Claude\CLAUDE.md` system already cover them.)

### Working Notes
- Recon SPA (`expenses.brisken.com`) calls `https://api.expenses.brisken.com/api/...`; landing makes 5 API calls (login, expense-batches x2, settings, cards/status), slowest ~1.4 s. Cold drive command is in the verifier's recon paragraph.
- Dirk's mailbox: 2,354 folders, ~3,200 received messages per month. Criss's: 35 folders, inbox 33,312.
- Regus invoices to Dirk land in Deleted Items (Oct 2026: invoice 709-70284 on 10-02).

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/1747

---

## How to Continue

Use the agents by name (`agnt_done-verifier` after a deploy, `agnt_brisken-mail-reader` for any "did X arrive" question, `agnt_sourced-researcher` for research fan-outs). For a drive from Git Bash, keep the `MSYS_NO_PATHCONV=1` prefix.

---

## Strategic Feedback

### What Worked Well This Session
- Smoke-testing each agent on a real task before merge found two defects that unit tests could not: the blind first drive and the 25-minute walk. The mail agent's honest BLIND (instead of a fake NOT FOUND) showed its negative rule works under pressure.

### Suggestions
- Reasoning review (Layer 2): a probe that saw nothing right after I launched it was my own invocation; I reached for an external cause (service worker) first. When a fresh probe reads zero, dump its raw inputs (`--dump-requests`, the argv the tool received) before hypothesizing about the target.

### System Health
- **Autonomy:** 0 human interventions after the build order (the user asked three questions and gave one order). Gates: B1:0 B2:6 B3:1 skipped:1. The session header was skipped again at start; that check has been deferred in three checkpoints and is now the clearest structural gap.
