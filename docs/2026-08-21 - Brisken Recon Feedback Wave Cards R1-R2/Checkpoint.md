# Checkpoint: Brisken Recon Feedback Wave Cards R1-R2

**Date:** 2026-08-21
**Status:** Cards R1 + R2 shipped and live; rounds 3-8 planned and queued

---

## Summary

The 2026-08-21 operator feedback wave (14 in-app notes, the first full sweep
since capture went global in #544/#545) was triaged into an approved 8-PR
program (plan: `~/.claude/plans/looks-like-there-is-keen-aurora.md`), and the
first two rounds shipped end-to-end today: Cards R1 (PR #555, the card
registry) and Cards R2 (PR #556, Zoho decoupling), both merged, Fly-deployed,
and live-verified.

---

## What Was Done This Session

### Triage
1. Pulled `/feedback.jsonl` live: 24 non-test notes, 14 new (2026-08-21,
   operator=matthias); mapped all 14 + 2 untracked July-27 notes to themes
   A-G with live evidence (batch 8f8ccac0bafc probe, intake log probe).
2. Three Explore fan-outs mapped the code (batches/intake, cards/entity/Zoho,
   memory/i18n/grid — the last also read the SPA repo
   `011matthias/brisken-expense-review` and found 12 concrete defects).
3. User rulings captured: cards-first sequencing; notes 5/7 = the two account
   dropdowns; export never blocks on unresolved card/entity (placeholders,
   adjustable later).

### Cards R1 (PR #555)
1. New `src/expense_recon/cards.py`: `settings["cards"]` registry with
   multi-digit identity (statement marker "2838" + plastic last-4 "1672" are
   ONE card — the actual root cause of the 13 unassigned January rows),
   `effective_cards` read-time composition (settings > legacy maps > /data
   presets, no write migration), `resolve_card` replacing three inconsistent
   matchers.
2. API: `GET /api/cards`, PUT settings `cards` branch, `cards_effective`;
   consumers (resolve_entity / apply_master_data / available_entities / batch
   snapshot) switched with legacy pins untouched.
3. Adversarial review (4 lenses, 13 confirmed): fold() keeps merged-key digit
   identity; field-aware `entity_for`/`zoho_account_for` (no cross-map
   shadowing = no silent COA-gate disarm); digit floor 3.

### Cards R2 (PR #556)
1. Per-card Zoho-OPTIONAL setup advisories (`setting: "cards"`); doctor same.
2. Conservative money-path resolver `resolve_account_map`: bare-digit keys
   match labels ("2838" resolves "2838 - May 2026"), label keys exact-only,
   ambiguity keeps the placeholder. Expense export tries earlier digit runs
   (dual-identity labels) exact-only.
3. `merchants_inert` on GET settings (zoho_account without category is a
   no-op — the "importance not evident" root).
4. Adversarial review (2 lenses, 3 confirmed, all EXECUTED wrong-money
   scenarios in the first draft: year-token merges, first-match ambiguity,
   word-key wildcards, BIN-fragment sweeps) — redesigned + every scenario
   pinned as a test.

### Bookkeeping
1. Backlog rewritten with the wave (items 10-17) + shipped rows; status file
   rows for R1/R2; loop brief brought current (PR #557).
2. Lovable prompts authored: `docs/lovable-cards-prompt.md`,
   `docs/lovable-zoho-decoupling-prompt.md` (handed to owner this session).

---

## Key Decisions Made

### Cards-first sequencing (user, 2026-08-21)
- **Choice:** Cards R1→R2→R3 before the quick wins/intake/memory rounds.
- **Rationale:** The headline ask; the smaller items follow.

### Export policy on unresolved card/entity (user)
- **Choice:** Placeholders, never block; assignment stays adjustable after
  export (re-export folds it in). Pin as an R3 test.

### Money paths never guess (from the R2 adversarial review)
- **Choice:** `resolve_account_map` denies on ANY ambiguity; label-shaped
  keys stay exact-only. A visible `Card: ...` placeholder beats a silently
  wrong posting (B4).

### Read-time composition over write migration (R1)
- **Choice:** legacy `card_entities`/`card_accounts` stay authoritative until
  an explicit card exists; persisted migration deferred to R4.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| src/expense_recon/cards.py | new | registry + composition + resolvers |
| src/expense_recon/web/{app,service,store}.py | edit | API + consumers + advisories |
| src/expense_recon/output/zoho_export.py, zoho_expense_export.py | edit | conservative card resolution |
| src/expense_recon/doctor.py | edit | per-card optional wording |
| tests/test_cards.py (new) + 6 test files | edit | 40+ new/updated pins incl. all review scenarios |
| docs/lovable-cards-prompt.md, lovable-zoho-decoupling-prompt.md | new | owner UI halves |
| workspace/clients/brisken/status/p1-{improvement-backlog,expense-reconciliation,recon-loop-prompt}.md | edit | wave record, shipped rows, fresh-chat brief |

(All under `workspace/clients/brisken/automations/expense-reconciliation/`
unless pathed; shipped via PRs #555/#556/#557.)

---

## Current Status

Live origin `brisken-expense-recon.fly.dev` runs R2: healthz 200,
`GET /api/cards` lays out the 5 real seeded cards (only 2838 has an entity —
the other 4 await assignment in the new editor), `merchants_inert` present
([] — all 28 seeded merchants carry categories). Advisories are snapshotted
per run: existing runs keep old wording by design; new runs get the per-card
optional text. Suite 1148/2; calibrate green. brisken ops: platform plan
unknown (~?/? ops/mo, never assessed).

---

## Next Steps

1. Cards R3 in a FRESH session (entity-less batch + card review + assignment
   learning + refresh-master-data) — paste the loop brief
   (`workspace/clients/brisken/status/p1-recon-loop-prompt.md`, current as of
   PR #557).
2. Then rounds in order: intake quick wins + delete month; body-only mail
   (Dirk's real held mail = acceptance test); memory validate/adjust;
   language + receipt visibility; Cards R4 (needs owner answers, in backlog
   item 10).
3. Owner: apply the two Lovable prompts; DOM-probe after publish.
4. p2 status files are 23-30d stale (flagged by the sweep) — a p2 session
   should refresh or archive them.

---

## Context for Next Session

### Files to Read First
- workspace/clients/brisken/status/p1-recon-loop-prompt.md (the brief)
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 10-17)
- ~/.claude/plans/looks-like-there-is-keen-aurora.md (full wave design)

### Open Questions
- R4 owner questions (backlog item 10): per-entity export files? cash/personal
  tenders as cards? per-entity zoho_account? retire the presets file?
- Which of the 4 entity-less cards belong to which legal entity (operator
  data entry once the Cards editor is published).

### Working Notes
- Advisory text is snapshotted into run.summary at creation — do not chase
  "stale" wording on old runs after a deploy.
- `gh pr merge` false-FAIL gotcha applies with sibling worktrees: confirm via
  `gh pr view N --json state,mergedAt`.
- Both adversarial reviews EXECUTED their scenarios against worktree code —
  keep that pattern for R3 (the entity-resolution chain is money-adjacent).
- The primary clone carries dirty ledger files from other sessions; this
  checkpoint's ledger edits ship from the recon worktree docs branch.

### Reference Materials
- PRs #555, #556, #557 (011matthias/agentic-ops1.01)

---

## How to Continue

Fresh chat → `/comd_resume brisken` → paste the loop brief → start Cards R3
(design section "Theme A Round 3" in the plan file; branch
`client/brisken/recon-cards-r3` off origin/main in the recon worktree).

---

## Strategic Feedback

### What Worked Well This Session
- The adversarial-review-before-ship pattern earned its keep twice: R2's
  review EXECUTED three wrong-money scenarios in my own draft (visible
  placeholder would have become silent wrong posting) before anything
  shipped. The finding-verify (refute-by-execution) loop is the strongest
  quality gate this workstream has.

### Suggestions
- The feedback widget wave arrived attributed (operator names, run_ids,
  DOM anchors) and was triageable in minutes — worth repeating the pattern
  on the Lead Desk surfaces before September.

### System Health
- Autonomy: 2 human decision points (plan approval, sequencing/dropdown
  answers), 0 corrections. Gates: B1:0 B2:6 B3:1 B4:5 skipped:0. The
  friction candidates were all detector false-positives on repeated git
  inspections; no register rows this session.
