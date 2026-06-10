# Checkpoint: Brisken Expense-Recon Hardening And Ship

**Date:** 2026-06-08
**Status:** SHIPPED to main. PR #80 (`107b85e`) merged — FX + ambiguous LLM judgment + an 11-item hardening/plumbing batch on the expense-reconciliation tool. 98/98 tests green, CI-gated merge.

---

## Summary

Built the FX + ambiguous LLM judgment layers and a full no-client-input hardening pass on the Brisken expense-reconciliation CLI, then shipped the whole lot to `main` through the newly-tiered B6 gate (autonomous commit/push/PR, CI-green auto-merge). Had to land it via an isolated git worktree because a concurrent audit-remediation session hijacked the shared working directory mid-task. Also clarified that the tool's AI runs on Dirk's provided OpenAI key (not optional), and explained the tool + Excel output to the user in plain terms.

---

## What Was Done This Session

### Judgment layer (LLM, provider-agnostic via `LLMClient`)
1. **`judge_fx_match` (D1b)** — FX-converts the receipt into the transaction currency, scores same-purchase confidence + implied rate; always `requires_review=True`; no-client path keeps the `[STUB]` match. (Built start-of-session; committed in this ship.)
2. **`judge_ambiguous`** — LLM tie-break among candidate receipts; the pick is annotated + promoted to the front, but **every candidate stays in the bucket** (reconciliation guarantee, asserted by `test_apply_ambiguous_judgment_promotes_pick_but_keeps_all`). Wired via `_apply_ambiguous_judgment` in the CLI. FX + ambiguous reasoning now also surfaces in the report Note column.

### Hardening / plumbing batch (all "buildable now, no client input")
3. **C3** structured logging across the pipeline + `--verbose` (quiet by default).
4. **A8** `--explain` sheet (per-transaction outcome + confidence + reason trail).
5. **E6** `MatchOutcome` frozen (immutability; `_apply_judgment` now slice-assigns in place).
6. **E7** three currency-layer fields documented (transaction / account-card / book).
7. **Zoho export skeleton** (slice 4.6) — `output/zoho_export.py`, journal-entry CSV, N debits + 1 balancing credit per matched tx, matches-only, placeholder account names.
8. **E1** report-writer tests; **E2** subprocess CLI test; **E5** CI workflow (`.github/workflows/expense-recon-tests.yml`); **E3** README accuracy; **E4** spec §32 build-state note.

Test trajectory: 74 (session start) → 82 (D1b) → 87 (judge_ambiguous) → **98** (full batch).

### Ship (new tiered B6 gate)
9. Committed (`61069ec`) → pushed → PR #80 → CI green (5/5 checks, incl. my `test` job running 98 tests in 13s) → **auto-merged on green** (`107b85e`). Verified the squash commit is on `origin/main`.

### Other
10. Clarified the OpenAI key is **Dirk-provided** (client credential), so the LLM features are the real operating mode. Wrote memory `project_brisken_openai_key.md` + MEMORY.md index line.
11. Plain-terms explanations of how the tool works and the Excel output structure (no files changed).

---

## Key Decisions Made

### judge_ambiguous built guarantee-safe
- **Choice:** the LLM picks the best tied candidate, but ALL candidates stay in the `ambiguous` bucket (pick just promoted + annotated). Never auto-resolves, never drops a receipt.
- **Rationale:** mirrors the FX pattern and preserves the reconciliation guarantee (v2 §25.5). With no real ambiguous data to validate against, a guarantee-asserting test is the safety net.

### Decision to commit under the updated B6 gate
- **Choice:** commit/push/PR/merge autonomously. The user reloaded the gate (now tiered: Band-1 feature-branch work autonomous post-verification, Band-2 auto-merge on green CI) and asked me to decide.
- **Rationale:** verified work (98 tests + smokes), reversible feature-branch, scoped to brisken + one CI file = exactly Band 1. Under the new rule, asking "should I commit?" would be the deferral.

### Landed via an isolated worktree (not a normal commit)
- **Choice:** stash my exact 15 files, create a throwaway worktree on `client/brisken/expense-recon` off `origin/main`, apply the stash there, commit/push/PR from the worktree, then remove it.
- **Rationale:** a concurrent `fix/audit-remediation-2026-06-06` session had switched the branch out from under me and intermingled its uncommitted docs work in the shared tree. Committing in place would have contaminated their branch; a worktree isolates cleanly and never touches their tree.

### Zoho export shipped as an honest skeleton
- **Choice:** correct Zoho journal-entry column shape, but account names are explicit placeholders (`category name` / `Card: {id}` / `(uncategorized - assign)`).
- **Rationale:** the real account mapping needs Chris's chart of accounts (slice 4.1) and the §31 field-mapping decision. Shipping the format now, the mapping later.

---

## Files Modified (all merged to main via PR #80)

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/llm/client.py` | Modified | `FxJudgmentResult` + `AmbiguousCandidate`/`AmbiguousJudgmentResult` + protocol methods + OpenAI/Mock impls |
| `.../matching/judgment.py` | Modified | stub → client-backed FX + ambiguous judgment (no-client stub preserved) |
| `.../cli.py` | Modified | `_apply_ambiguous_judgment`, judgment threading, C3 logging + `--verbose`, `--explain` |
| `.../matching/types.py` | Modified | E6 frozen `MatchOutcome`, E7 currency-layer docs |
| `.../output/report_xlsx.py` | Modified | A8 `--explain` sheet + surface FX/ambiguous reason in Note |
| `.../output/zoho_export.py` | Created | Zoho journal-entry CSV skeleton (slice 4.6) |
| `.../tests/test_fx_judgment_llm.py` | Created | FX (D1b) + ambiguous judgment + guarantee (13 tests) |
| `.../tests/test_report_xlsx.py` | Created | report writer + `--explain` (E1) |
| `.../tests/test_zoho_export.py` | Created | Zoho export skeleton |
| `.../tests/test_cli_subprocess.py` | Created | entry point via subprocess (E2) |
| `.../{README,BLUEPRINT,ANNEALING}.md` | Modified | marked items done, test count 74→98 |
| `specs/1-spec/p1-expense-reconciliation-functional-spec.md` | Modified | E4 §32 build-state note |
| `.github/workflows/expense-recon-tests.yml` | Created | E5 CI gate for the suite |
| `~/.claude/.../memory/project_brisken_openai_key.md` + `MEMORY.md` | Created | Dirk's OpenAI key provenance |

---

## Current Status

Brisken is a custom Python CLI tool (not Make/n8n/Trigger) — no ops-status line applies. The expense-recon engine is feature-complete for everything buildable without client data: deterministic matching, CSV/Excel ingest, per-line LLM categorization, FX + ambiguous judgment, the 5+N-sheet Excel report, Zoho export skeleton, CI. **All merged to `main` (PR #80, `107b85e`).** AI features run on Dirk's OpenAI key (gpt-4o-mini, via `OPENAI_API_KEY` env var).

Two pieces remain, both gated on Chris's data/access: receipt vision OCR (D2) and the real Zoho posting loop (slice 4.1/4.6 mapping). Matcher calibration (A-series) also awaits a real month.

---

## Next Steps

1. **Rotate Dirk's OpenAI key** (security). It leaked into the 2026-06-01 transcript and was flagged for rotation; not confirmed done. Client credential — confirm or rotate before relying further.
2. **When Chris's first real month lands:** build slice 2 pt2 (vision OCR replacing the receipts-CSV bridge), tune the vision prompt to real receipt shapes, run the real statement through the matcher and report the actual match rate, then anneal matcher A-items (A1/A2/A3/A5) against real noise.
3. **When Zoho access lands:** chart-of-accounts ingest (4.1) + real account mapping → wire the Zoho export from skeleton to real (4.6/4.9 `zoho:` config block).
4. **Optional now:** still-unblocked items are mostly exhausted; `judge_ambiguous` finished the LLM-judgment pair. Remaining ANNEALING items are real-data-gated.
5. **Consider the Dirk update** (NOT yet drafted — needs explicit ask): spec + working-tool demo + the "how it learns" / architecture explanations he asked for + "the §38 stack research can stop."

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` — slice map (now reflects FX + ambiguous done)
- `workspace/clients/brisken/automations/expense-reconciliation/ANNEALING.md` — punch list; top has the 2026-06-07 resolved-batch note
- `workspace/clients/brisken/automations/expense-reconciliation/README.md` — current state, 98 tests, file layout
- memory `project_brisken_openai_key.md` — AI runs on Dirk's OpenAI key; Anthropic path moot

### Open Questions
- Has Dirk's OpenAI key been rotated? (flagged 2026-06-01; unconfirmed)
- When will Chris's first real-data sample land? (Dirk-to-Chris brief is the unblocker; unchanged across brisken checkpoints)
- Has Dirk reviewed the spec / BLUEPRINT? (still not surfaced via comms; no brisken comms-log exists)

### Working Notes
- **The brisken work is on `main`, not a feature branch.** PR #80 merged; the local `client/brisken/expense-recon` branch + the throwaway worktree were deleted after merge. To continue, branch off a fresh `origin/main`.
- **This session ended on a contended branch.** A concurrent `fix/audit-remediation-2026-06-06` session owns the current working directory (it switched the branch and has its own uncommitted docs work: comd_eod-capture, comd_weekly-review, eod-capture.yml, weekly-review.yml, docs/INTEGRATIONS.md, etc.). I did NOT touch their files. If checkpoint docs from this session look swept/missing, that's why.
- **B6 gate is now tiered + auto-merge** (rule_no_auto_commit.md rewritten 2026-06-06): Band-1 feature-branch commit/push/PR autonomous after local verification; Band-2 `gh pr merge` auto-fires on green CI; only the irreversible floor (push-to-main, force, deploy, tag, client subtree) needs explicit order.
- **Stash mechanics:** my session-start system-WIP stash is still parked at `stash@{0}` ("On system/no-auto-commit-prototype-carveout: WIP ... pre-brisken switch 2026-06-06"). Not mine to pop; left for whoever owns that branch.
- **Worktree landing recipe** (if contention recurs): `git stash push -- <paths>` → `git worktree add <wt> <branch>` → `git -C <wt> stash apply` → stage/commit/push from the worktree → `git worktree remove`. Keeps the other session's tree untouched.

### Reference Materials
- PR #80: https://github.com/011matthias/agentic-ops1.01/pull/80
- OpenAI pricing: gpt-4o-mini $0.15/M in + $0.60/M out
- Prior brisken checkpoint: `docs/2026-06-01 - Brisken Expense Recon Slice 2 LLM Categorizer/`

---

## How to Continue

`/resume brisken`. The work is on `main` — branch off a fresh `origin/main` for any new brisken work (do NOT reuse this session's contended checkout state). The 4-branch resume tree still holds: (a) if Chris's data arrived → build vision OCR + real-data validation; (b) if Zoho access arrived → chart-of-accounts ingest + real Zoho export; (c) if Dirk sent comms → check `context/`/`reference/`; (d) if neither → the unblocked backlog is now largely exhausted (judgment pair done), so the highest-leverage move is unblocking Chris's data, not more build. Rotate the OpenAI key regardless.

---

## Strategic Feedback

### What Worked Well This Session
- **The tiered B6 gate enabled a clean autonomous ship.** Once the user reloaded the updated rule, commit → push → PR → CI-green → auto-merge ran end to end with no per-step "ship it" tax, and the CI green-gate (my `test` job ran the 98 tests) was the objective re-verification. This is the gate working exactly as designed.
- **The provider-agnostic `LLMClient` protocol** made both judgment additions mechanical and mock-testable with no live API calls — the guarantee-asserting test is the real safety net for `judge_ambiguous`.
- **Worktree isolation** let me land my work without touching a concurrent session's intermingled state. Protecting the work in a labeled stash first meant zero risk of loss during the surgery.

### Suggestions
- **Two agent sessions on one working directory is a real hazard.** The branch got switched out from under me mid-task and foreign uncommitted work intermingled with mine. The repo's own guidance says parallel work should use separate sessions/worktrees per checkout. Worth a structural guard or at least a convention: a session that finds the branch changed unexpectedly should stop and re-confirm scope before any git write.
- **The closing-offer reflex persists.** The B1 stop-hook fired twice this session ("Good spot to checkpoint if you want, or I can keep going", "Say the word and I'll write it"). Hook caught both; corrected both. The generation tendency hasn't shifted, the gate just keeps catching it.

### System Health
- **Autonomy score: ~3 friction events this session** (2 hook-caught closing-offers; 1 self-caught session-start stash slow-path on a Windows file lock; plus 1 minor user fact-correction on the OpenAI-key framing). Elevated-adjacent but all hook/self-caught or low-severity; no user-blocking redirect of the actual work.
- **Concurrent-session contention is an unmodeled system risk.** The friction register has cd/cwd-drift entries; this is a sibling class (shared-checkout state mutation by another actor). Candidate for a structural note in the parallel-sessions guidance.
- **The new tiered B6 gate's first real client PR worked flawlessly** (Band-1 autonomous + Band-2 CI-gated merge). Good signal that the 2026-06-06 rewrite is sound.
