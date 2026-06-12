# Checkpoint: Brisken Expense Recon UI Features

**Date:** 2026-06-12
**Status:** Two UI increments shipped to main; roadmap Tier-1 #1/#3/#4 done; UI-frictionless brainstorm delivered.

---

## Summary
Engaged the user's pasted feature-expansion roadmap (4 tiers, 18 items) for the expense-reconciliation browser UI (p1). Shipped graceful AI-key degradation (the live error the user hit) and the confidence + triage-views increment, then delivered a prioritized brainstorm of UI friction points.

---

## What Was Done This Session
### Shipped (both merged to main, CI-green)
1. **PR #154 — AI degrades gracefully when no key is set.** `use_llm` + no `OPENAI_API_KEY` previously raised a blocking 400 (the user hit this; screenshot). Now it drops the `llm:` block, runs the keyword classifier, completes the reconciliation, and the workbench shows an informational orange notice. Cross-cutting roadmap requirement.
2. **PR #156 — Confidence + triage views (Tier-1 #1/#3/#4).**
   - #1 Graded 0-100 `Match.score` (amount 0.55 / date 0.30 / vendor 0.15 blend); workbench sorted weakest-first (unmatched > review > reconciled, low score first within a rank). `confidence` left unchanged so bucket/assignment + existing asserts hold.
   - #3 Unmatched-transactions first-class view (mirror of the existing unmatched-receipts card).
   - #4 `expense_recon/duplicates.py` (pure, flag-only): `find_duplicate_charges` (same merchant+amount+currency within a date window; recurring-months-apart excluded) + `find_duplicate_receipts` (same merchant+date+total+currency across distinct doc ids). Surfaced as a "Possible duplicates" card + Dup-groups stat.

### Verified
- Suite 262 (after #154) then 273 (after #156) passed, 2 skipped.
- Live HTTP via httpx against the running server after each merge (303 not 400 + notice; triage stat + score chips + unmatched-tx section render). Server restarted twice from merged code (uvicorn does not hot-reload).

### Delivered (no build)
- Prioritized UI-frictionless brainstorm (17 points). Top picks: manual-match escape hatch (NEW), bucket filter chips + clickable stats, bulk + keyboard review (Tier-3 #14), column-map as dropdowns instead of JSON.

---

## Key Decisions Made
### Add a `score` field, do not overwrite `confidence`
- **Choice:** New `Match.score: int = 0` graded 0-100, alongside the existing bucket `confidence`.
- **Rationale:** Tests assert specific confidence values (`>= 0.99` exact, LLM-judgment 0.88/0.12/etc.); overwriting would break them and the bipartite sort_key. Additive field is back-compat; serialize defaults `score` to 0 for old snapshots.

### Duplicates computed in `build_view`, flag-only
- **Choice:** Pure module called at render time; no snapshot schema change, never mutates the reconciliation.
- **Rationale:** Lowest-risk, preserves the reconciliation guarantee, cheap for a month of data. CLI/report wiring deferred.

### Bundle #1+#3+#4 as one PR
- **Choice:** User picked the bundle over the roadmap's literal "#1+#3 first".
- **Rationale:** The graded score drives the triage order which drives where duplicates surface; cohesive as one change.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| src/expense_recon/web/service.py | Modified | #154 graceful-degradation guard; #156 candidate score, triage sort, unmatched-tx list, duplicate groups in build_view |
| src/expense_recon/web/templates/workbench.html | Modified | AI-unavailable notice; score chips; Dup-groups stat; unmatched-transactions + Possible-duplicates cards |
| src/expense_recon/matching/types.py | Modified | `Match.score` field |
| src/expense_recon/matching/deterministic.py | Modified | `_blend_score` + per-branch graded score in match_one |
| src/expense_recon/duplicates.py | Created | find_duplicate_charges / find_duplicate_receipts |
| src/expense_recon/web/serialize.py | Modified | Round-trip Match.score |
| tests/test_web_app.py | Modified | AI-fallback test + workbench triage/dup render assertion |
| tests/test_match_score.py | Created | Graded score bounds + ordering + FX |
| tests/test_duplicates.py | Created | Window inclusion, recurring exclusion, receipt dedup |

---

## Current Status
- **Roadmap Tier-1:** #1 confidence, #3 unmatched-both-directions, #4 duplicates = DONE. Open: #2 one-to-many (biggest, rewrites the 1:1 bipartite core), #5 merchant normalization (partial), #6 control-total tie-out (small).
- **Running server:** live at http://127.0.0.1:8000 from merged-main code (background task `bx662fkfb`), data dir `C:/Users/neuma_p1qrsic/expense-recon-data`. AI fallback + triage features live; the user can retry AI-on (gets the notice) and see score/dup/unmatched sections in any new run.
- **p1 expense-recon:** standalone Python CLI + web UI; orchestrator none. Path A complete; UI feature-expansion in progress.

---

## Next Steps
1. **Next roadmap increment** (user to pick): #6 control-total tie-out (small, standalone, high bookkeeper value) or #5 merchant normalization, before #2 one-to-many.
2. **OR pivot to UI-frictionless brainstorm items:** manual-match escape hatch (removes the hard dead-end where an unmatched tx + unmatched receipt can't be linked in the UI), bucket filter chips + clickable stats, bulk + keyboard review, column-map dropdowns.
3. (gated) 4b Zoho journal POSTING needs Zoho API access from Dirk; (production) Chris runs the pipeline monthly.

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py (build_view = the render model; create_run = the run pipeline)
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/templates/workbench.html
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/deterministic.py (_blend_score + match_one)
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/duplicates.py

### Open Questions
- Next direction: continue the matching-correctness roadmap tiers, or pivot to the UI-frictionless brainstorm items? (user picks)

### Working Notes
- The feature-expansion roadmap was pasted verbatim by the user alongside a screenshot of the AI-key 400 error. Several Tier-1 items were already partly built (confidence buckets, `vendor_similarity` fuzzy match, the unmatched-receipts card), enumerated before building (B7) to avoid rebuild; that shifted "most value for least work" off the roadmap's default suggestion.
- **Server restart mechanics:** the running uvicorn does NOT hot-reload. To pick up new code: stop the PID on port 8000 (PowerShell `Get-NetTCPConnection -LocalPort 8000 -State Listen` then `Stop-Process -Force`), then relaunch `uv run --directory <recon-dir> --all-extras expense-recon-web --port 8000 --data C:/Users/neuma_p1qrsic/expense-recon-data --no-open` in the background. Old background tasks report exit 127 when killed (expected).
- **Worktrees:** `agentic-ops1-reconrun` is the active p1 finance worktree (cuts feature branches off origin/main; ledger via docs branch per G1). `agentic-ops1-reconui` is a DEAD orphan dir (its `.git` is gone) — it still holds stale copies of the web files; ignore it and delete the directory when convenient to stop grep/edit targeting the wrong copy. Untracked `scripts/prep_brisken_exports.py` sits in reconrun (the Request-3 date-CSV converter; never committed, separate concern).
- **UI brainstorm top frictionless picks:** (1) manual-match escape hatch (NEW, not in roadmap, the #1 dead-end remover), (2) bulk + keyboard review (Tier-3 #14), (3) bucket filter chips + clickable stats, (4) column-map dropdowns. Receipt image preview = Tier-3 #12; "always categorize {vendor}" on reclassify seeds Tier-2 #7 rules + Tier-1 #5 merchant map; the `Reset` button does a jarring full `window.location.reload()` worth fixing.

### Reference Materials
- PR #154 (AI fallback), PR #156 (confidence + triage) on github.com/011matthias/agentic-ops1.01

---

## How to Continue
`/comd_resume brisken`, then either name a roadmap item (#6/#5/#2) or a UI-frictionless item (manual-match, filter chips, bulk/keyboard). Build on a fresh `client/brisken/expense-recon-*` branch off main in the reconrun worktree; restart the server from merged code to see changes live.

---

## Strategic Feedback

### What Worked Well This Session
- Pasting the full roadmap plus the live error screenshot gave unambiguous direction; the single AskUserQuestion to pick the next increment kept scope tight on an 18-item roadmap without over-building.

### Suggestions
- UX friction blocks tool adoption as much as match accuracy does. Worth interleaving the frictionless UI items (manual-match, filters, bulk actions) with the matching-correctness tiers rather than finishing all matching tiers first; the manual-match escape hatch in particular removes a hard dead-end the matcher will always have.

### System Health
- The dead `agentic-ops1-reconui` worktree directory caused a read-before-edit slip (read the reconui copy of workbench.html, tried to edit the reconrun copy with it). Removing the orphan directory would prevent grep/edit from targeting a stale duplicate of the web files.
- Autonomy score: 0 human interventions this session (one self-caught slow-path slip, no user corrections of approach).
