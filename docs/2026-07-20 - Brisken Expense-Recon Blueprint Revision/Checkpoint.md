# Checkpoint: Brisken Expense-Recon Blueprint Revision

**Date:** 2026-07-20
**Status:** Blueprint revision shipped (PR #284 merged); two build tiers queued as ready-to-paste prompts.

---

## Summary

Criss's first real expense-recon test reconciled 0 of 94 charges. Diagnosed the three root causes on her exact files (run locally, no API), then revised the tool's BLUEPRINT ("using-the-data" half) to remove stale elements and add the fix roadmap, and handed off two isolated build-chat prompts.

---

## What Was Done This Session

### Diagnosis (Criss's first test run, run `b67133b8df98`)
1. Task 1 — no notification: root-caused to two structural facts. The user page was removed 2026-07-20, so Criss now uploads via the **operator "run now"** form, which creates an **unpublished run** (not an intake); `/api/operator/state` (what the dev-side notifier polls) reports only intakes + *published* runs, so her run is invisible to it. Separately, `tools/brisken-recon-notify.py` is not scheduled on the dev box.
2. Task 2 — retrieved her exact uploaded files off the Fly volume (`flyctl ssh sftp get /data/runs/b67133b8df98/…`, `MSYS_NO_PATHCONV=1`) and ran the pipeline locally with NO LLM (owner cost directive). Result: 0/94 matched. Three root causes, all reproduced:
   - **Sign:** Chase activity CSV lists purchases as negative (`Type=Sale`); matcher rejects non-positive charges → 0 candidates; abs() → 34.
   - **Cross-currency LLM-gated:** BRL receipts vs USD charges; the deterministic exact-FX short-circuit needs the charge's original foreign amount, which the activity CSV lacks but the **statement PDF carries**.
   - **Receiptless charges never categorized:** `categorize_receipts` runs on receipts; receiptless USD SaaS charges (Anthropic, Adobe, Microsoft, OpenAI) get no category and never reach the Zoho journal.

### Strategy + blueprint revision (PR #284, merged)
3. Ran 3 Explore + 2 Plan subagents to map the blueprint's post-ingest sections and the matching/categorization/output code against the findings.
4. Revised `BLUEPRINT.md`: removed stale elements (Anthropic/Claude → OpenAI, EU/UK-card items 3.11/3.12, never-built Streamlit UI, pre-Path-A gates, LD-3's aspirational 5+N layout); added a dated "Using-the-data revision" section + new slices (3.15, Slice 10/11/12); amended LD-2/LD-5/3.7/3.10/Slice 9/4.11/8.5/entry_status. CI green; merged.
5. Delivered two isolated build-chat prompts (Tier 1 = matching/FX/sign; Tier 2 = categorize-every-charge), scoped to disjoint files so they don't collide.

---

## Key Decisions Made

### No-API testing loop is the standing workflow
- **Choice:** retrieve the files Criss uploads from the Fly volume and run the pipeline locally with NO `llm:` block; `calibrate` is the no-LLM harness.
- **Rationale:** owner directive to save money during testing. Cross-currency can't auto-match without the LLM, so the Tier-1 fixes (PDF-first + deterministic FX) are what make no-LLM testing productive.

### Two isolated build tiers, not one
- **Choice:** split the fixes into Tier 1 (`ingest/*` + `matching/*`) and Tier 2 (`categorize*` + `output/*` + post-match hook in `cli.py`), each on its own worktree, Tier 2 via a `ReconcileResult` side-map to avoid touching Tier 1's frozen types.
- **Rationale:** user asked for two separate chats that don't get in each other's way. Disjoint file ownership is the anti-collision contract.

### Blueprint edit, not code, this session
- **Choice:** revise the doc only; hand off code as prompts.
- **Rationale:** the user's ask was to improve the blueprint; the code is a downstream build.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` | Modified (PR #284, merged) | Revised the "using-the-data" half: removals + build-ons + new slices |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Modified | Record 0/94 finding, blueprint revision, two queued build tiers |
| memory `project_brisken_expense_recon_testing_loop.md` | Created | Retrieve-from-Fly no-LLM loop + notifier blind spot + sign gap + cross-currency findings |
| `C:\Users\neuma_p1qrsic\.claude\plans\glimmering-herding-glade.md` | Created | The approved plan (blueprint revision + the two prompts) |

---

## Current Status

Blueprint revised and merged to `main`. The tool behaves as-is (0/94 on Criss's cross-currency month) until the two build tiers land. Criss's run `b67133b8df98` exists on the app but is unpublished/0-match; not published back to her. Platform: custom Fly SaaS (tier "unknown", not ops-metered) — no ops-audit needed.

---

## Next Steps
1. Run **Tier 1** build (sign normalization + PDF-first + deterministic FX) in a fresh chat with the prompt from the plan file / delivered message. Verify with `calibrate` (no API): matches 0/36 → ~30-34/36.
2. Run **Tier 2** build (categorize every charge) in a second chat. Independent of Tier 1; can run in parallel.
3. After Tier 1 lands, get the Chase **statement PDF** (not just the activity CSV) from Criss so the deterministic FX path has original amounts.
4. Decide the receiptless-LEARNED posting posture (default: withhold-until-confirmed).
5. Schedule `brisken-recon-notify.py` (user registers the Windows task) OR extend the state API to surface unpublished operator runs, so future uploads notify.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` ("Using-the-data revision (2026-07-20)")
- `C:\Users\neuma_p1qrsic\.claude\plans\glimmering-herding-glade.md` (the two build prompts)
- memory `project_brisken_expense_recon_testing_loop.md`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- Receiptless-LEARNED posting posture (auto-post known vendors vs withhold-until-confirmed)?
- Deterministic-FX reference-rate source (monthly config table vs daily fetch)?
- Is `ER-00215` even the intended counterpart for card 2838 (it only covers the Brazilian subset)?

### Working Notes
- Criss's run id: `b67133b8df98`. Operator code `mn040307` (vault "Expense Recon App"). Fly token in `~/.fly/config.yml` `access_token:` (has a space — extract the whole line).
- Verified: Chase PDF parser already captures original foreign amount (`statement_pdf.py:_attach_fx` 281-283, `_build_tx` 306-308) — PDF-first is wiring, not new parser code.
- Verified: abs() on the Chase amounts flips 0 → 34 review candidates locally.
- The 35 canonical FX candidates stub out to "needs review" with no LLM (`judgment.py` STUB).

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/284 (merged)
- Live app: brisken-expense-recon.fly.dev (operator code `mn040307`)

---

## How to Continue

Open two fresh chats and paste the Tier 1 and Tier 2 prompts (in the plan file / this session's final message). Start Tier 1 first. Each uses its own worktree and verifies with `calibrate` against Criss's retrieved files, no API.

---

## Strategic Feedback

### What Worked Well This Session
- The mid-turn steers ("she uploaded from operator page", "not on API", "improve the blueprint") were tight and corrected direction early, before wasted work compounded.

### Suggestions
- When handing a build to a fresh chat, the disjoint-file-ownership contract is the thing that makes parallel work safe; keep specifying it explicitly in the handoff prompts.

### System Health
- The recon notifier has a real design gap: `/api/operator/state` hides unpublished operator runs, so the dev-side notifier can never see a user's upload now that everyone is on the operator page. Worth folding into Tier 1 or a small follow-up (extend the state API), not just scheduling the notifier.
- Autonomy score: 3 human interventions this session.
