# Checkpoint: Expense-Recon Notes 109-110

**Date:** 2026-10-02
**Status:** notes #109-#110 itemized as backlog items 244-245 (PR #1550); their SPA prompt is the only unpublished one (bundle-verified); loop queue empty

---

## Summary
Started from a stale item-240 handover (a sibling had applied it), read the live feedback store instead and turned the two new owner notes into items 244-245: one Lovable prompt, one route test. At hand-over a bundle audit showed the two older prompts I had listed as pending were already published, so the record was corrected and a noisy pattern rule was fixed.

---

## What Was Done This Session

### Notes #109-#110 (PR #1550, `036a1f09`)
1. #109: live read-only drive measured the `/months` header tabs clipped behind a hidden horizontal scroller (PT 724 of 905 px: "Comparar", "Configurações"; EN "Settings"). Prompt §1 gives them their own `flex-wrap` row.
2. #110 answered from the code: "Paid by bank transfer" is one `PUT payment_path = "bill"`; the note's row (August Perplexity USD 25.00, waiting for 0340) is card-paid. New route test pins that a mistaken move returns once the statement charge is matched (regress on `month_paths` line 300). Prompt §2 adds tooltip key `expx.bills.moveToBill.tip`.
3. Both prompt halves applied to a scratch SPA clone and run against the live API with writes aborted: 0 clipped tabs at 800-2500 px EN + PT, tooltip renders on focus.

### Hand-over and record (PR #1551 mini-checkpoint, PR #1552)
1. `tools/lovable-bundle-audit.py` with this round's markers: `receipts_reread` (item 240) and the item-242 pill class live, `moveToBill.tip` absent, controls valid. PROMPT-STATUS + backlog 241-242 marked PUBLISHED (#1552); the 244-245 prompt handed over in a four-backtick fence.

### Checkpoint-time structural fix
1. `warn-owner-publish-without-named-prompt` fired on two closings that named the prompt file: the stop text is code-stripped, so a file name in backticks vanished before the rule's exemption looked. Stop events now also carry `final_text_raw` (unstripped); the rule matches the publish phrase on `final_text` and checks the file name with `not_regex_match` on `final_text_raw`. Wired-hook test `test_stop_raw_text_keeps_what_the_strip_drops` + a seed row; regress (strip the raw field in the hook) turns it red.

---

## Key Decisions Made

### #110 answered plus a tooltip, the visibility change left to the owner
- **Choice:** pin the behavior with a test and make the button explain itself; do not restrict when it shows.
- **Rationale:** the note is a question. Showing the button only with `bill_suggestion` would also hide it from bank-paid invoices with no detected signal, which is the owner's trade-off to make.

---

## What Did NOT Work (and why)
- **Regress on `if held_by_charge:` in `resolve_payment_path`:** TEST DOES NOT BITE; `month_paths` passes `held_by_charge=False` and checks the hold itself.
- **Vite dev via the 8.3 short path `NEUMA_~1`:** `@fs` 403 and `@vite/client` 404, no hydration, Log in stayed disabled; the long path works.
- **`Locator.hover` on the bank-transfer button:** timed out behind the first-visit feedback dialog; remove `[data-fb-widget] [role=dialog]` and focus instead.
- **Trusting PROMPT-STATUS for "not pasted":** both listed prompts were already published (SPA `2d3e505`, `e1bc910`).
- **`preflight-hooks.py --full` under PowerShell:** 15 failures, all `bash` resolving to WSL's `bash.EXE` with no `/bin/bash` (`test_cd_guard`, `test_recon_uptime_workflow`, `vercel-as.sh`); environmental, CI is Linux.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `expense-reconciliation/docs/lovable-nav-no-scroll-bill-tip-prompt.md` | created | SPA prompt for items 244-245 |
| `expense-reconciliation/tests/test_bills_path_218.py` | edited | mistaken bill move returns on the statement charge |
| `expense-reconciliation/docs/PROMPT-STATUS.md` | edited | 244-245 row; 240 and 241-242 PUBLISHED |
| `status/p1-improvement-backlog.md`, `status/p1-expense-reconciliation.md` | edited | items 244-245, 241-242 headings, status row |
| `.claude/hooks/_pattern_rules.py`, `.claude/hooks/pattern-rules-gate.py`, `tools/pattern_rules.py` | edited | `final_text_raw` stop field |
| `.claude/patterns/warn-owner-publish-without-named-prompt.md` | edited | conditions with the raw-text exemption |
| `tools/tests/test_pattern_rules_gate.py` | edited | wired-hook test + seed row |

---

## Current Status
p1 recon backend unchanged (test and docs only, no deploy). Feedback store: 110 notes, all itemized. One unpublished prompt (244-245). brisken ops status: platform unknown plan (pre-flight). `p2-lovable-rebuild.md` and `p2-onepilot-site.md` are 22 days stale (p2 work, not touched here).

---

## Next Steps
1. Owner publishes `docs/lovable-nav-no-scroll-bill-tip-prompt.md`; verify `moveToBill.tip` with the bundle audit, then a cold drive (header `nav` `overflow-x: visible`, below the logo, no clipped tab).
2. Owner call on item 245: show "Paid by bank transfer" only with `bill_suggestion`?
3. Criss adds 1672 to the 2838 card (item 243 takes effect) and reviews the five tool confirmations item 240 reopened.
4. Before the next recon round, read `/feedback.jsonl` for notes after #110.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 243-245
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` "Not applied"

### Open Questions
- Item 245 button visibility (above).

### Working Notes
- PROMPT-STATUS "Not applied" still lists several rows whose own text says PUBLISHED; audit them with the bundle tool before quoting any as pending.
- Driving a local SPA build against live data: clone `011matthias/brisken-expense-review`, `npm install`, `npm run dev -- --port 5189` from the LONG path; CORS admits localhost; abort every API non-GET except `/api/login`.

### Reference Materials
- Session scratchpad: `nav109.py`, `nav109_local.py`, `apply_prompt.py`, `audit.py` (bundle audit with this round's markers)

---

## How to Continue
`/comd_resume brisken`; nothing in flight. Check the bundle for `moveToBill.tip` once the owner reports the publish.

---

## Strategic Feedback

### What Worked Well This Session
- Checking `git log origin/main` and the sibling worktrees before acting on the handed prompt: item 240 was done and 243 was mid-build, so neither was redone.
- Proving a Lovable prompt on a local SPA clone against the live API before hand-over; it caught the tooltip-behind-dialog trap and confirmed the wrap at five widths.

### Suggestions
- Give `tools/lovable-bundle-audit.py` a `--pending` mode that reads each "Not applied" row's key column from PROMPT-STATUS and audits them all, so the file is refreshed mechanically at checkpoint instead of drifting (this session's verification-theater row).

### System Health
- **Gates:** B1:0 B2:5 B3:2 skipped:1. Autonomy: 0 human interventions (the owner's two requests were requests, not corrections).
- A warn-only pattern (`warn-git-write-after-script-semicolon`) fired and the command ran anyway, its second occurrence; no damage, the script succeeded. Consider promoting it to block on the next recurrence.
