# Checkpoint: Brisken Deck Archive Story Audit

**Date:** 2026-07-16
**Status:** Complete — analysis delivered + reusable fix-pass prompt saved to Brisken context

---

## Summary
Read the actual slide text (via app-only Graph, read-only) of Dirk's full
SharePoint presentation archive (130 pptx, 2016→2026), narrated the strategic
story-evolution, then compared our four 2026 rebuilds against their historical
originals for storyline alignment. Abstracted Dirk's MDH deck-fix prompt into
a reusable, parameterized template for the other deck assets.

---

## What Was Done This Session

### 1. Archive discovery + extraction (Graph, app-only, read-only)
1. Browsed `20_Assets/BRISKEN PRESENTATIONS/**` on the MARKETING site via the
   BRISKEN MARKETING OPS app-only credential (Sites.Selected READ is granted;
   no CDP / no COM needed — graph-first honored).
2. Built a full recursive inventory: **130 pptx, 2016→2026** (`.scratch/sp_pptx_inventory.json`).
3. Deduped the ~100 data-provider rebrands (OANDA/Reuters/Bloomberg copies) and
   micro-versions (MDH V000→V07) to **23 genuinely distinct decks**; extracted
   slide text → `.scratch/deck_texts/ALL.md`.
4. Extracted the 5 live 2026 rebuilds → `.scratch/deck_texts/OURS_2026.md`.

### 2. Story-evolution narration (the "what story does each tell" answer)
Traced Brisken's arc across 7 eras: SAP-certified MDH app (2016–17) → product +
RAPSODY fixed-price SAP consulting (2020–21) → platform rebrand under "OnePilot
Codeless Framework" + app catalog (2022–23) → the **2023 AI VC pitch** ($5M seed,
brisken.ai, "digital labor market") → 2024 consolidation + "Calvin" co-worker →
consulting arm (AOP, $8k assessments) → **2026 FSI repositioning** to a
vendor-neutral orchestration layer.

### 3. Our-vs-original alignment audit (the follow-up ask)
Verdict: the four rebuilds tell the **same core story** as their originals;
telling changed (problem-first reflow, encyclopedic middle compressed to a
6-step flow, added trust/payoff beats), claims unchanged.
- **MDH** — aligned; technical catalog distilled to Ingest→Validate→Cleanse→Transform→Govern→Distribute.
- **Smart Trading** — aligned; renamed from Trade Automation/TraderPlus, added sourced ~12min→<1min payoff.
- **Digital Co-Worker** — aligned to the 2024 product (same 4 roles, same Calvin email→SAP scenario); deliberately drops the 2023 startup-pitch framing.
- **MDH Commodities** — aligned in spirit, genuinely new as a told story (composite forward curve); least battle-tested (Dirk parked it).

### 4. Deliverable: abstracted deck-fix-pass prompt
Approved Dirk's MDH-pass prompt and generalized it into a two-parameter
template (`[REFERENCE DECK]` / `[TARGET DECK]`) with 3 additions:
(9) footer-renumber-after-reorder, hard content guards (Evonik/RWZ/BTP/sourced-stats),
and a post-run validation loop (PDF re-export + `validate-demo-material.py` + SharePoint re-upload).

---

## Key Decisions Made

### Scope: curate distinct decks, not all 130
- **Choice:** Read 23 story-distinct decks + 5 live 2026 rebuilds; skip the ~100 provider-rebrands/micro-versions.
- **Rationale:** The rebrands tell the same story with a different feed name; reading all 130 is pure token waste for zero narrative gain.

### Graph app-only, not CDP/COM
- **Choice:** All SharePoint reads via the BRISKEN MARKETING OPS app-only credential.
- **Rationale:** Reads are read-only → autonomy; Sites.Selected READ is granted on MARKETING; graph-first rule bans the desktop/CDP path when Graph covers it.

### Approve-with-additions, not rubber-stamp
- **Choice:** Endorsed Dirk's 9-pattern prompt but added 3 gaps backed by live evidence (broken footers, banned-content regression, sandbox can't self-validate).
- **Rationale:** The prompt licenses free rewording by an AI; without content guards + a validation loop, banned content (Evonik/RWZ) and pagination drift ride back in — already observed in the with-UCs deck.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/context/deck-fix-pass-prompt.md | Created | Reusable parameterized deck-fix-pass template (durable client ops knowledge) |
| .scratch/sp_inventory.py · sp_browse_decks.py · sp_extract_decks.py · sp_extract_2026.py | Created (ephemeral) | Graph app-only SharePoint browse/inventory/extract tooling |
| .scratch/sp_pptx_inventory.json · deck_texts/ALL.md · deck_texts/OURS_2026.md | Created (ephemeral) | Extracted inventory + slide-text corpus for the audit |

---

## Current Status
Analysis delivered and the fix-pass template is saved to Brisken context. No
code shipped, no git ops, no SharePoint writes (all reads). One open content
defect surfaced in Dirk's own in-progress **Digital Co-Worker "with UCs"** deck,
not yet actioned (his working file; acting would be outbound/invasive).

---

## Next Steps
1. **(Optional, read-only)** Run `uv run tools/validate-demo-material.py --client brisken --dir <folder>` on the "with UCs" deck to machine-confirm the Evonik/RWZ hits on slides 10+11.
2. When applying the fix-pass to a sibling deck, paste the template from `deck-fix-pass-prompt.md`, fill `[REFERENCE DECK]=Market Data Hub` + the target, and run our post-pass validation loop.
3. The "with UCs" deck needs Dirk to fix its paste-error slide 11 (WHO-WE-ARE body under a "CASES / Funding Requests" title) + the Evonik/RWZ regression BEFORE a fix-pass, or the pass polishes a slide about to change.

---

## Context for Next Session

### Files to Read First
- workspace/clients/brisken/context/deck-fix-pass-prompt.md (the deliverable)
- .scratch/deck_texts/OURS_2026.md (live text of the 5 rebuilds)
- .scratch/deck_texts/ALL.md (23 historical decks)
- .scratch/sp_pptx_inventory.json (full 130-pptx map with item IDs for re-fetch)

### Open Questions
- **Positioning coherence:** our product decks re-anchor hard to SAP ("the AI layer for SAP treasury, runs on SAP's own cloud"), while the 2026 OnePilot-for-FSI overview (Eduardo's) pushes vendor-neutral ("non-SAP cores, no core replacement"). House-level answer not settled.
- Does Dirk want the fix-pass applied to TreasuryCentral/Use-Case decks now, or hold until he finishes the with-UCs edit?

### Working Notes
- **Graph SharePoint browse pattern (reusable):** app-only token → `/sites/{SID}/drive/root:/{path}:/children` to walk, `/drive/items/{id}/children` to recurse by id, `/drive/items/{id}/content` to download, then python-pptx. SID = `brisken.sharepoint.com,65b8d36f-2777-4cff-bd80-58ff9022d17c,e9089a15-9498-4149-a6f3-b4bc8e4d21ac`. Scripts in `.scratch/sp_*.py`.
- **Archive structure:** old decks live under `OnePilot_Archive/`, `OnePilot_Apps/*/Archived PPTX/`, `Consulting Solutions Presentations/CON_Treasury Services/RAPSODY Marketing Assets 2023 and before/`. Current set in `2026_PPTX/`.
- **Confirmed content defect** (with-UCs deck, Dirk 07-14): slides 10 AND 11 read "Evonik and RWZ already build on the platform" (banned per his 07-10 directive; standalone DC correctly says "Customer teams"); slide 11 is a paste error (WHO-WE-ARE body under a CASES title); footers show "10 / 11" twice on a 17-slide deck.
- **Naming lineage:** "Smart Trading" (our 2026 name) recycles SAP's old "SAP Smart Trading" label; the "TraderPlus"/TPI brand is retired. "Trade Automation" was the 2024 interim name.

### Reference Materials
- Rule: `.claude/rules/rule_brisken_graph_first.md`
- Memory: `reference_brisken_graph_app_creds`, `project_brisken_product_decks_restructured`

---

## How to Continue
The audit is done and the template is banked. To apply it: open
`deck-fix-pass-prompt.md`, fill the two brackets, hand the numbered block to the
deck-editing agent, then run the post-pass validation loop on our side. Do NOT
run it against Dirk's with-UCs deck until he clears its slide-11 paste error and
Evonik/RWZ regression.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the ACTUAL slide text of both old and new decks before asserting any "aligned/not-aligned" verdict (B4) — the alignment claims are evidence-backed, not filename/memory guesses. This is what caught the Evonik/RWZ regression and the paste-error slide.
- The curate-then-extract pattern (dedupe 130→23 first, then extract) kept the token cost proportional to the narrative value.

### Suggestions
- When you approve-with-changes on an artifact, I could quote the inserted sections inline in the same turn so a "did you actually insert them?" follow-up isn't needed. Noted for future approve-and-edit turns.

### System Health
- No skill/rule gap: the graph-first rule + app-creds memory made the SharePoint reads fully autonomous, no CDP fallback, no user action. This is the payoff of the 2026-07-14 Graph provisioning.
- Autonomy score: 1 human intervention this session (one minor closing-offer at the end of the alignment analysis; see friction register). Clean session.
