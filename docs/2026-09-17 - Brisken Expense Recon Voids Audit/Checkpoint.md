# Checkpoint: Brisken Expense Recon Voids Audit

**Date:** 2026-09-17
**Status:** Audit delivered and recorded as backlog items 94-133 (PR #974, merged); nothing built; fresh-chat prompt for the five pre-October defects handed to the owner

---

## Summary

Ran a ten-lens deep audit of the Brisken expense-reconciliation tool for voids and load-bearing functions, reported 40 voids plus 8 protect-lines to the owner in plain language, and appended all 40 to the p1 backlog as unranked items 94-133 on the owner's choice.

---

## What Was Done This Session

### Audit
1. Read-only baseline: 15 recon memory files, status roll-up, loop brief, backlog headings, live API (6 month batches, settings, memory, inbound log, 56 feedback notes) and a detached audit worktree at origin/main c233237f.
2. Workflow `wf_4d50db94-94e`: 10 finder lenses (intake, matching, money/reports, learning, review SPA, operations, quality, Criss fit, live state, architecture) produced 152 raw findings, merged to 50 (42 voids, 8 important functions) plus 27 set-aside lines.
3. Verification: the run hit the session usage limit twice (28/162 agents, then 57/122 after a resume with a leaner verify stage). 30 findings got adversarial verdicts (3 skeptics for critical/high, 1 combined for medium); 20 were spot-checked by hand in code and live data (publish route, bulk confirm, alert default, Dockerfile, disk floor 88 MB of 974 MB, 5 snapshots at 5-day retention, list-vs-page counts, 47 booked receiptless July charges = USD 3,385.47, 4 "Added" mails with zero documents, 42 single-word merchant aliases).
4. Report delivered in chat: ranked voids with proposed change, value and a licence tag (defect / new function / operations / owner data / UI prompt), plus the 27 set-aside observations.

### Recording
1. Owner chose "append all 40" (AskUserQuestion). Generated the block from the merged findings plus reviewer corrections; PR #974 first drafted items 92-131.
2. Main moved during the PR (a sibling added items 92 and 93 at the same insertion point and shipped draft #108 in PR #979). Merged main into the branch (no rebase, no force), renumbered to 94-133 with "audit draft #N" kept in every heading, marked item 110 shipped; diff vs main additions only (616 + 1 lines); 6/6 CI green; squash-merged `04948116`.
3. Wrote a pasteable fresh-chat prompt for items 116, 117, 100, 94 and 121 after confirming none of their code paths moved on main.

---

## Key Decisions Made

### Append all 40 findings, unranked
- **Choice:** Items 94-133 in audit rank order (wrong money first), not ranked against items 1-93; the 8 important functions stay protect-lines, not items.
- **Rationale:** Owner pick; the backlog is the one list, ranking is the owner's pass.

### Keep draft numbers in the headings
- **Choice:** "audit draft #N" in each heading (draft N = item N+2).
- **Rationale:** PR #979 already cited "audit 101 / 108 / 130"; renumbering without markers would break those references.

### Five items to fix before 2026-10-01
- **Choice:** 116 (sign-off wipes merchant keys), 117 (one-word aliases as wildcards), 100 (publish gate, defect half only), 94 (copies in totals, needs a ruling), 121 (alert recipients, needs Dirk's yes); 126 (Criss closes August unaided) as the acceptance test.
- **Rationale:** Each bites at the first real sign-off, and all are defects the licence covers; new-function halves (frozen sign-off copy, receipt chasing) stay out per the no-feature-shipping ruling.

---

## What Did NOT Work (and why)

- **A 162-agent workflow in one run:** subagents hit "You've hit your session limit" at 28 of 162 (reset 11:50 Berlin), then again at 57 of 122 after the resume (reset 16:00); verify and critic phases were lost both times.
- **The original verify aggregation:** a finding whose verifier agents all failed had zero votes, so `survives` was false and it landed in `refuted`; F08-F50 would have been silently dropped. Fixed with an `unverified` bucket before the resume.
- **First journal probe `until :; do ...; done`:** `:` is true, so the loop never ran and the background task "completed" with empty output.
- **`gh pr create --repo 011matthias/agentic-ops1`:** GraphQL "Head sha can't be blank, No commits between main and ..."; the slug is `011matthias/agentic-ops1.01`.
- **Waiting on `gh pr checks` for PR #974:** "no checks reported" for about 30 minutes; the PR was `mergeable_state: dirty` (sibling's backlog append), and GitHub runs no pull_request workflow without a merge ref.
- **Draft item numbers 92-131:** collided with main's 92 and 93, added by a sibling session in the same window.
- **Editing gen_block.py through a Python heredoc:** refused by the heredoc gate (double backslash in the payload); used the Edit tool.
- **`flyctl volumes snapshots list <vol>` without `-a`:** "failed getting app name from volume" GraphQL error; works with `-a brisken-expense-recon`.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Appended (PR #974) | Items 94-133 + 27-line set-aside list |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Row added (PR #974) | Element row for the audit |
| `.claude/patterns/warn-gh-repo-slug-missing-01.md` | Created | Warns on the short repo slug |
| `.claude/patterns/warn-pr-checks-poll-without-mergeable.md` | Created | Warns on a `gh pr checks` poll that never reads mergeability |
| memory `project_brisken_expense_recon_voids_audit.md` | Created | Audit result, numbering trap, top defects |
| memory `reference_workflow_session_limit_budget.md` | Created | Workflow sizing under the session limit |
| memory `MEMORY.md` | Two index lines | Pointers to the above |

---

## Current Status

Backlog items 94-133 are on main; item 110 (draft #108, stale card list on arrival) shipped in PR #979 by a sibling session; nothing else from the audit is built. A sibling session is actively shipping p1 feedback items (134-136 today, Fly v150). Pre-flight flagged `p2-product-decks.md` (56 days) and `p2-targeting.md` (57 days) as stale; both are p2 workstreams this session did not touch, left for the p2 session. Ops: brisken platform plan unknown in `infrastructure.yaml` (no assessment recorded).

---

## Next Steps

1. Paste the fresh-chat prompt (in this session's final reply) and build item 116 first: no ruling needed, and it must land before any month is published.
2. Owner decisions, asked once up front in that chat: reverse the "totals count every row" contract for item 94; Dirk's yes on alert recipients (121); the live alias sweep (117); deleting the three July test runs.
3. Owner ranks items 94-133 against 1-93.
4. Owner arranges item 126: Criss closes August unaided before 2026-10-01.
5. deploy-consumer-gate: stop opening a marker when the deploy words sit inside a search argument of a read-only command (see friction row), and check whether workflow subagents share the parent session id.
6. Record a platform assessment for brisken in `infrastructure.yaml` (Fly app, OpenAI spend) so the ops status line stops reading "unknown".

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 94, 100, 116, 117, 121 (and the block header above item 94)
- memory `project_brisken_expense_recon_voids_audit.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` section "Duplicates on the row" (the contract item 94 reverses)

### Open Questions
- Should a copy the tool has ruled a duplicate leave the month report's listing and totals (item 94)?
- Who receives held-mail and re-match alerts (item 121), and does Dirk approve the settings write?
- Is the frozen copy of the documents at sign-off (item 100's new-function half) quoted under the licence?
- What happens after the PDF: does Criss still re-key every charge into Zoho Books (set-aside list)?

### Working Notes
- Code anchors for the five items were unchanged on main as of 04948116 / 9d62f72b: `registry_upserts_from_expense_run` (web/service.py) rebuilds merchants with aliases/category/zoho_account only; `MerchantRegistry.resolve` (merchant_registry.py) uses `token_set_ratio >= 88`; `publish_run` (web/app.py) has no readiness check; `DEFAULT_ALERT_RECIPIENTS` (web/intake_mail.py) is matthias only; `_expense_export_inputs` has no copy filter. app.py grew about 126 lines since c233237f, so locate by name.
- Reviewer corrections worth keeping: July's 24 receiptless charges are all grey subscription rows; a two-word alias rule does not close the wildcard ("Material de Construcao"); the one-word aliases were hand-entered in the editor, not seeded; the item-94 behaviour is a recorded contract, not an accident.
- Run outputs (temporary): session `tasks/wxjm1lj6t.output` and `tasks/wnqrxlzpk.output`; merged findings and verdicts in the session scratchpad `wf1_results.json`.

### Reference Materials
- PR #974 (audit append), PR #979 (sibling: arrivals refresh the card list, cites draft numbers)
- `docs/us-substantiation-criteria.md`, `docs/electronic-storage-system-description.md` section 12 (compliance gaps the audit leans on)

---

## How to Continue

Open a fresh chat and paste the prompt from this session's final reply. It resumes brisken, asks the owner the two up-front questions, and builds item 116 in its own worktree while waiting, then 117, 100 and 94.

---

## Strategic Feedback

### What Worked Well This Session
- Cache-keyed resume: editing only the verify stage replayed ten finders and the merge for free after the quota reset.
- Doing independent spot-checks by hand while the workflow waited on quota covered 20 of the 50 findings with live evidence instead of leaving them unverified.
- Merge-not-rebase plus draft markers resolved a live numbering collision with a sibling session without a force push and without breaking its citations.

### Suggestions
- Build the item-94-class question into the loop brief: a reviewer-era contract ("the tool flags, the reviewer deletes") silently outlives the change that made the tool decide. When a round moves a decision from person to tool, grep api-contract for rules that assumed the person.

### System Health
- The deploy-consumer gate blocked four closing messages in a session that ran no deploy; a marker opened by a read-only command erodes trust in the gate the same way its earlier false closes did.
- Autonomy score: 6 human interventions (5 "continue" / "am I waiting" nudges during quota waits, 1 decision) (elevated; run /system-dev to close gaps).
