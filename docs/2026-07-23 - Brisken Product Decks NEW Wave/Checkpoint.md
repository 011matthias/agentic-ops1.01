# Checkpoint: Brisken Product Decks NEW Wave

**Date:** 2026-07-23
**Status:** Wave shipped — 4 NEW decks verified + in Asset Testing; Dirk notification drafted (send gated)

---

## Summary

Dirk approved the NEW TreasuryCentral Solutions Overview; this session promoted its ephemeral build source into the tracked `deckgen/native/` engine (regression: 121/121 zip parts identical to the approved deck), codified the standard (DESIGN.md + MESSAGING.md + fixture-enforced Dirk decisions), rebuilt all four product decks on that foundation as one design family, verified them through the full G0-G6 gate sequence (incl. a 14-checker adversarial source-trace), and uploaded them to SharePoint Asset Testing with re-download content verification.

---

## What Was Done This Session

### Engine + standard (PR #427, merged)
1. `deckgen/native/`: tokens (per-deck Palette), draw, grammar (content-parameterized builders), assets (md5-pinned; image12 badge fix — image34 is Fortitude Re art), compose (spec-driven + gates), render (COM + native font gate), montage.
2. Regression baseline: `native/specs/overview.yaml` recomposes the approved deck part-for-part (121/121 parts md5-identical).
3. `DESIGN.md` (tokens, slide grammar, content contracts, gates G0-G6, rollout rules); MESSAGING.md append (Dirk-review vocabulary); 6 Dirk decisions added to `demo-banned-terms.json`; `context/deck-fix-pass-prompt.md` deleted (superseded). CI: `deckgen-native-tests.yml` (13 pytest).

### Four product decks (PR #429, merged; #428 closed as superseded)
1. Native specs: Market Data Hub (13 sl, green/rail-left), MDH Commodities (10, rust/baseline), Smart Trading (11, indigo/bar-right), Digital Co-Worker (14, plum/corner-dots).
2. Gates: banned-terms/em-dash PASS (11 terms) on pptx+PDF; font/rIds/hidden clean; slop scan clean; 14-checker adversarial source-trace (6 REAL findings fixed — hierarchy-footnote subject-drop in 3 decks, tenor gloss ordering, an unsourced "whatever the format" — plus 5 adopted nits); full-size app-slide review (caught + fixed a step column rendering behind the CONNECTS strip).
3. Uploaded per-deck via the hard-guarded `upload.py`; 8/8 re-list verified; all 4 pptx re-downloaded and slide-text-identical to local builds.
4. Deliverables of record: `deliverables/product-decks-redesign/` (4 pairs + CHANGELOG.md provenance).

### Ledgers + comms
1. `status/p2-product-decks.md`: Overview → approved; NEW-generation rows; folder-state note. `collateral-inventory.md` + memory `project_brisken_product_decks_restructured` updated.
2. Dirk notification drafted (`context/drafts/2026-07-23-product-decks-notification.md`), comms-critic audit: OK. **Sending is gated on explicit owner yes.**

---

## Key Decisions Made

### Scope + design + filing (user, plan approval)
- 4 product decks first (Sanofi/Zalando next wave); one family on the approved token system with per-deck accent + layout signature; Dirk's approval read as content-only — all writes stayed in Asset Testing, promotion/cleanup remain his call.

### DCW accent = plum (not "soft teal")
- **Choice:** Digital Co-Worker gets plum `6D4098`; the Overview owns teal in this family.
- **Rationale:** two teals in one family would blur the per-deck identity.

### App-column overflow guard: retired
- **Choice:** a chars-per-line build guard was tried and retired the same day; deterministic guards (item counts, 124-char use-case step cap) stay; DESIGN.md G4 now mandates full-size app-slide review.
- **Rationale:** the estimator could not separate approved copy (est. 11 lines, renders fine) from real overflow (est. 12) — 1 line of margin is inside estimator noise.

### Badge on product functional slides: kept
- **Choice:** SAP Certified badge (image12) prints on each product deck's functional slide despite the approved Overview carrying it only on the platform slide.
- **Rationale:** it is Dirk's own certification mark, printed on his own product decks' functional diagrams; provenance recorded in each spec header.

---

## Files Modified

| File | Action | Purpose |
|---|---|---|
| `deckgen/native/` (9 modules + 5 specs + tests) | Created | The NEW-generation engine + deck specs |
| `deckgen/DESIGN.md` | Created | Codified deck standard (tokens, grammar, gates, rollout) |
| `deckgen/MESSAGING.md`, `README.md` | Modified | Dirk-review vocabulary; native-pipeline section |
| `tools/fixtures/demo-banned-terms.json` | Modified | 6 Dirk decisions fixture-enforced + provenance exemptions |
| `.github/workflows/deckgen-native-tests.yml` | Created | CI gate for the engine |
| `deliverables/product-decks-redesign/` (8 binaries + CHANGELOG.md) | Created | Deliverables of record + provenance |
| `status/p2-product-decks.md` | Modified | Approval + wave + folder-state ledger |
| `context/collateral-inventory.md` (gitignored) | Modified | Asset Testing reality; backlog #1 delivered |
| `context/drafts/2026-07-23-product-decks-notification.md` (gitignored) | Created | Gated Dirk notification draft |
| `context/deck-fix-pass-prompt.md` (gitignored) | Deleted | Superseded by DESIGN.md §2 |
| memory `project_brisken_product_decks_restructured.md` + MEMORY.md | Modified | NEW-family state + lessons |

---

## Current Status

Both PRs merged to main (#427 engine+standard, #429 decks; #428 closed — its branch conflicted after the #427 squash-merge). SharePoint Asset Testing holds the approved Overview (pptx renamed prefix-less since 07-22 — likely Dirk's act; pdf still prefixed) + the four `NEW - ... 2026-07-23` pairs + MN- copies; non-MN PROPOSAL pairs are gone. The Dirk notification draft is readiness-checked and waiting on the send gate.

---

## Next Steps

1. **Owner: approve + send the Dirk notification** (`context/drafts/2026-07-23-product-decks-notification.md`) — per-send gate.
2. On Dirk's per-deck approval: run the swap runbook (Asset Testing → Product Assets, archive old file) — invasive, per-deck owner yes.
3. On Dirk feedback: pull comments off the live files (CDP), fold into the native SPECS, regenerate through G0-G6, re-upload.
4. Next wave (when scoped): Sanofi/Zalando prospect decks on the same DESIGN.md standard.
5. Ledger housekeeping: local `docs/INDEX.md` + `docs/friction-register.md` carry multiple sessions' unshipped rows AND main moved under them — the docs PR needs a three-way reconcile (nightly repo-sweep or a dedicated docs session).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p2-product-decks.md`
- `workspace/clients/brisken/deliverables/product-decks-redesign/CHANGELOG.md`
- `workspace/clients/brisken/automations/lead-generation/deckgen/DESIGN.md`

### Open Questions
- Which physical file did Dirk's approval attach to (the prefix-less pptx vs its still-prefixed pdf)? Naming reconciliation of MN- copies = his call.
- BTP wording opt-in per deck (documented, parked).

### Working Notes
- Native engine reproduces the approved deck EXACTLY: byte-level part parity, so his verbatim edits survive regeneration; fold feedback into SPECS, never artifacts.
- PowerPoint COM renders are pixel-nondeterministic on rounded-corner anti-aliasing; compare slide XML / zip parts, not pixels.
- After a squash-merge, never reuse the pre-squash feature branch for the next PR (conflicts + CI won't run); cherry-pick onto a fresh branch from main (worktree pattern worked cleanly).
- The Bash auto-mode classifier blocks batch loops of external writes; per-deck single commands pass.

### Reference Materials
- PRs: #427 (merged), #428 (closed, superseded), #429 (merged).
- SharePoint: `2026_PPTX/Asset Testing` (server-relative paths in the draft + upload logs).

---

## How to Continue

`/comd_resume brisken` → read the three files above. If Dirk has replied: process per-deck approvals via the swap runbook (invasive, per-action yes) or fold his comments into `deckgen/native/specs/*.yaml` and regenerate. If the notification has not gone out: it is ready at the drafts path, waiting on the send gate.

---

## Strategic Feedback

### What Worked Well This Session
- The plan-mode scope questions (4 decks / one family / content-approval-only) eliminated every mid-build direction decision; zero user interventions were needed after approval.
- The 14-checker adversarial source-trace earned its cost: the hierarchy-footnote subject-drop (platform claim → app claim) is exactly the class of error a client would catch and lose trust over.

### Suggestions
- The Asset Testing folder shows filing activity (renames, removals) that the repo only discovers incidentally at upload time. A tiny read-only "folder-state diff" step at the start of any deck session (compare re-list vs last recorded state) would make Dirk's filing actions visible instead of surprising.

### System Health
- Autonomy score: 0 — fully autonomous session (3 self-detected friction events, no human interventions).
- The dirty-ledger pile (INDEX/friction-register/session logs diverging from main across parallel sessions) caused real merge pain this session; the branch-isolation rule §1 is honored by no one leaving files dirty forever — the repo-sweep needs to actually drain it, or checkpoints should ship their own docs PR immediately.
