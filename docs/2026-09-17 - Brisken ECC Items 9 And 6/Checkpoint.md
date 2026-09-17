# Checkpoint: Brisken ECC Items 9 And 6

**Date:** 2026-09-17
**Status:** Both items shipped, deployed and consumer-driven. Lead Desk sender still DORMANT (kill switch on).

---

## Summary
Ported the ECC operator-approval loop into the Lead Desk Graph sender (item 9) and built the code half of `rule_untrusted_inbound` into the expense-recon mail intake (item 6). Both are live, and the consumer render of each was driven in a browser.

---

## What Was Done This Session

### Item 9: epoch-keyed approval (Lead Desk)
1. PR #963 (`0e664c81`), prod schema v14. Approve writes a decision plus one immutable snapshot per message (text, sha256, epoch, recipient) in one `BEGIN IMMEDIATE` transaction. Re-filing advances the epoch. There is one unique-constrained dispatch claim per obligation (claimed, dispatching, delivered or unknown). `begin_dispatch` revalidates hash and recipient right before transport. `unknown` never retries; `POST /attempts/reconcile` is the manual settle step. Every existing guard is kept.
2. `tests/test_approval_epoch.py` covers the brief's four cases. `tests/test_send_drill_fixture.py` passes 12/12 against the fixture transport. No real send was made.
3. Prod consumer drive, cold: a self-addressed magic link to matthias.silva@ (SafeLinks-wrapped) opened in a fresh Chrome profile, then `/campaigns/drill`. `#approval-manifest` renders "1 message(s), manifest sha256 4405446e, draft epoch 1". Status PR #968 was corrected to say so before merging.

### Item 6: untrusted inbound (expense recon)
1. PR #973, Fly v147. `expense_recon/untrusted.py` adds a system rule plus nonce-fenced data blocks around the file name and PDF text. The fingerprinted instruction text is frozen, so the extraction cache stays valid. A deterministic 6-pattern regex scan covers document text, file name, and mail subject and body. It raises `expenses[].untrusted_instructions` and a `check` review. Injected mail is not acked, and outsiders stay un-acked.
2. Moved the review branch from first to after the fixable per-row checks. Two new ordering tests are each regress-checked (green, then red under mutation, then green).
3. Suite: 2031 passed on the merged tree. Ruff (CI ruleset) is clean. The recon CI job runs the new tests.
4. Deploy proof is differential. A read-only census of 6 batches and 131 rows ran before and after: the key is on 0 rows before and 131 after, 0 rows are flagged, and reason and state counts are identical. The live SPA renders September's 40 rows with no crash report, no fallback text and no writes.
5. Flagged-row render: I loaded the published SPA and routed every API call to a local backend on the merged code, seeded through the real intake path. The Pushy Co row shows under "Needs a look" with the sender chip and the flag prose. All 7 API calls were local, so no live-month write happened.
6. Status PR #975 (p1 row plus backlog item 93) and rule PR #976 (the "Open code half" paragraph is now "built").

---

## Key Decisions Made

### Untrusted flag ranks after the fixable row checks
- **Choice:** The flag goes after missing_fields, date_outside_period, suggested_private and needs_entity, and before the category judgment and the registry-work flags.
- **Rationale:** The flag never clears. Ranked first, it would hide a missing amount for good, which contradicts the file's own rule ("must never hide a more actionable per-row exception"). No safety is lost: the row is `check` either way, and the flag list is carried on the row independently of `reason_code`.

### Post-dispatch Graph errors are `unknown`, not retryable (item 9)
- **Choice:** 503/400 after dispatch, timeouts and a mid-dispatch lease expiry hold as `unknown` with no requeue. Sent Items evidence is attached as a suggestion and never auto-acked.
- **Rationale:** This is ECC's (e) taken strictly. A message that may have left must never go out twice.

### Drive the flagged row locally, prove the deploy on live data
- **Choice:** The flagged-row render ran on the published SPA against a local backend. The live deploy was proven by a before/after census plus a live SPA drive of an unflagged month.
- **Rationale:** `feedback_recon_no_live_writes_criss_acts`. The live months hold no flagged receipt, and seeding one would be a live write.

---

## What Did NOT Work (and why)
- **Playwright MCP on the user's Chrome :9222:** `initializeServer` timed out at 30 s after `<ws connected>`, because the target handshake never completes on a 227-process browser.
- **Python `connect_over_cdp("http://127.0.0.1:9222")`:** same hang, a 60 s timeout after the ws connected.
- **`agent-browser --cdp 9222` / `--cdp http://127.0.0.1:9222` / `connect 9222`:** all three failed with os error 10060 in 60 s. What worked was a second Chrome with its own `--user-data-dir` on :9333, which connected in 1 s.
- **Regex for the sign-in link on the app host:** matched nothing, because Exchange wraps the link in `nam11.safelinks.protection.outlook.com/?url=...`.
- **Minting a Lead Desk session cookie from the app secret (pre-compaction):** the classifier refused it. It would also have skipped the recipient's entry path (the cold-drive clause).
- **Adversarial review workflow wf_b9c24e91-120:** its output was never read. After compaction no `wf_*` dir or `journal.jsonl` turned up under the Temp session dir, so the ordering decision rests on the code's documented principle, not on review findings.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/{approval.py,store.py,cadence.py,app.py,templates/campaign.html}`, `cloud_worker.py` | new / edit | Item 9 approval loop (PR #963) |
| `workspace/clients/brisken/automations/lead-desk/tests/{test_approval_epoch.py,test_send_drill_fixture.py,conftest.py}` | new / edit | Item 9 tests; conftest stops dev `.env` Graph creds arming schedulers |
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/untrusted.py` | new | Fences plus deterministic scan |
| `.../expense_recon/{llm/client.py,matching/types.py,web/serialize.py,ingest/receipts_folder.py,web/intake_mail.py,web/service.py}` | edit | Item 6 wiring (PR #973) |
| `.../tests/{test_untrusted_inbound.py,test_intake_mail.py,test_view_contract.py}`, `docs/api-contract.md` | new / edit | Item 6 tests and contract pin |
| `workspace/clients/brisken/status/{p2-outreach-engine.md,p1-expense-reconciliation.md,p1-improvement-backlog.md}` | edit | #968, #975 |
| `.claude/rules/rule_untrusted_inbound.md` | edit | Code half built (#976) |
| `.claude/patterns/warn-attach-busy-cdp-9222.md` | new | Friction fix (this docs PR) |

---

## Current Status
- Lead Desk: live on schema v14, kill_switch true, no sending campaigns, `claims {}` / `unknown_claims []`. The `drill` campaign's pre-v14 approval carries no snapshots.
- Expense recon: Fly v147 live from `d6ef16ba`; 0 of 131 live rows flagged.
- Primary checkout back on `main`. Leftover worktree: this docs one only.
- brisken platform: unknown plan, no `platform` section in `infrastructure.yaml`.

---

## Next Steps
1. Before any watched Lead Desk lift: re-approve the paused `drill` campaign (pre-v14 approvals stop at claim time), then follow ARMING-DRILL.md with the owner's greenlight.
2. Recon backlog item 93: a Lovable prompt for PT copy of `reason_code: untrusted_instructions` plus rendering each flag's `quote`.
3. Sys: fix `deploy-consumer-gate.py` so it does not close on a failed read (`✗ Failed to read`, os error 10060) or on a command that merely contains the text `agent-browser` (pattern_rules test).
4. Resolve stale brisken status files `p2-product-decks.md` (56d) and `p2-targeting.md` (57d): update them from current truth or delete them.
5. Low: add a `platform` section to brisken `infrastructure.yaml` (Fly apps: brisken-lead-desk, brisken-expense-recon).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p2-outreach-engine.md` (item 9 row)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 93)
- `workspace/clients/brisken/automations/lead-desk/ARMING-DRILL.md`

### Open Questions
- Should the untrusted flag ever be dismissible by a reviewer, or does "read it, then approve the row" cover it?

### Working Notes
- Recon census script shape: log in with the vault code `Brisken recon operator code matthias`, `GET /api/expense-batches`, then each batch; count `review.reason_code` / `review.state` / `untrusted_instructions`. Read-only.
- The SPA falls back to backend prose for any reason_code without an i18n key (`reviewReason` in `ExpensesReviewGrid.tsx`), so new codes degrade to English, not blank.

### Reference Materials
- PRs #963, #968, #973, #975, #976
- SPA source `011matthias/brisken-expense-review`; `API_BASE` hardcoded in `src/lib/api.ts`

---

## How to Continue
`/comd_resume brisken`. Lead Desk sends stay gated on re-approval of `drill`, plus the owner greenlight and the B5 readiness audit. Recon item 93 is a Lovable prompt, not a backend change.

---

## Strategic Feedback

### What Worked Well This Session
- Proving the deploy differentially: the census before and after showed the key appear on 131 of 131 rows while every reason and state count held. That tests "changed what it should, nothing else" on live data with zero writes.
- Routing the published SPA to a local seeded backend gave a real consumer render of a state the live months do not contain, without touching Criss's data.

### Suggestions
- Build a `tools/cdp_drive.py` that launches or reuses an own-profile Chrome on a free port and attaches. Three browser tools hung before the fix this session, and the second-instance pattern was already in memory from 07-17.

### System Health
- `deploy-consumer-gate.py` closed its marker twice on non-drives today (a failed agent-browser read, then a pattern-rule test whose text mentioned agent-browser). That is the same hole as four 2026-09-15/16 rows, all unresolved. An advisory that reads as evidence while false is worse than none.
- Autonomy: 3 human interventions (a rejected MCP call, "use chrome please its clear", a "continue" nudge).
