# Checkpoint: UWI Marketing Evidence Research

**Date:** 2026-10-29
**Status:** Research delivered; hygiene PR and MEMORY.md compaction still open

---

## Summary
While HERO's reply is pending, the owner asked for evidence-only marketing research for UnpauseAI: documented cases, proof of concept, application to our offers, strategies side by side. Six research tracks produced a 10-strategy comparison, published as a private artifact. The July BFSG premise and the BAFA route are refuted.

---

## What Was Done This Session
### Research
1. Six parallel tracks, claims that decide a ranking re-checked against primary sources (marked ✓ on the page).
2. Published https://claude.ai/artifact/3WVzzEWh3PZZHPvbzJizzV (private): base-rates strip, 10-row matrix, offer-filter chips, evidence cards, gaps.

### Memory
1. Created `project_uwi_marketing_evidence_2026_10_26.md` (verdicts, base rates, gaps).
2. Corrected `project_compliance_deadline_wedges.md` with the BFSG scope finding.
3. Added an index line to MEMORY.md.

---

## Key Decisions Made
### Evidence-only, no new ideas
- **Choice:** Rate each strategy by documented cases (A-D grades) and by fit to our five offers.
- **Rationale:** Owner order. Result: only the Upwork baseline is Supported; 1, 2, 3, 5, 6 Mixed; 4 and 9 Thin; 7 and 8 Against.

---

## What Did NOT Work (and why)
- **HERO reply check via iCloud IMAP parenthesised search:** returned None and crashed; criteria must be passed as separate args. Also the sending mailbox is not the iCloud one.
- **HERO reply check via Gmail IMAP:** AUTHENTICATIONFAILED with the stored app password. Reply status stays unverified.
- **WebFetch on PDFs:** returned compressed binary; extract locally with pypdf (`pdf_grep.py`).
- **Triple-quoted Python in a heredoc:** blocked by heredoc-size-gate; use Write.
- **Single fan-out for six tracks:** all tracks hit the shared 200-search cap per turn, leaving thin areas; split future fan-outs across turns.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| memory/project_uwi_marketing_evidence_2026_10_26.md | created | verdicts and base rates |
| memory/project_compliance_deadline_wedges.md | edited | BFSG correction |
| memory/MEMORY.md | edited | index line |

---

## Current Status
Artifact published. No repo files changed by the research. Checkout was 7+ behind origin/main; sibling sessions live. The ledger entries for this checkpoint go through a docs worktree.

---

## Next Steps
1. Owner: which mailbox sent the HERO email, and whether question 6 (webhooks) was included.
2. Owner pick among strategies 1, 2, 3, 5, 6 to run while HERO is pending; start logging the 12 demos' funnel (demo, conversation, offer, close).
3. Docs PR from a new branch off origin/main: delete the resurrected u1 files (`status/u1-cold-email-infra.md`, `context/cold-email-purchase-checklist.md`, `context/u1-list-and-sequences.md`), correct u8-bfsg status, fix u9 commit count (8 to 9), add an uwi-general pointer to the artifact. Needs owner go.
4. Compact MEMORY.md by judgment with Edit (D10 in the layout plan also tracks it).

---

## Context for Next Session
### Files to Read First
- memory/project_uwi_marketing_evidence_2026_10_26.md
- workspace/projects/upwork-independence/status/uwi-general.md (decisions 1-8)

### Open Questions
- HERO mailbox and question 6.
- Gaps on the page: BNI Karlsruhe seat, walk-in UWG legality, Steuerberater referral yields, Craftnote/openHandwerk partner programs.

### Working Notes
Strategies 1, 3, 6 share one audience (trade firms on HERO) and reuse the Waerme Wimmer proof. Demo-first has no published conversion rate anywhere.

### Reference Materials
- https://claude.ai/artifact/3WVzzEWh3PZZHPvbzJizzV

---

## How to Continue
`/resume upwork-independence`; read the memory file, do not re-run the research.

---

## Strategic Feedback

### What Worked Well This Session
- Re-checking the deciding claims at the source caught a suspect Bitkom figure before it shipped (72% confirmed on the second match).

### Suggestions
- Split future research fan-outs across turns to stay under the shared search cap.

### System Health
- MEMORY.md is 23 KB against a 24.4 KB read limit. Autonomy score: 1 human intervention (the research redirect); fully autonomous otherwise.
