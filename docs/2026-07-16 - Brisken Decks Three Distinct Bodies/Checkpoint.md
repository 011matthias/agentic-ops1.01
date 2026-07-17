# Checkpoint: Brisken Decks Three Distinct Bodies

**Date:** 2026-07-16
**Status:** Restructure shipped; presenter-flow pass queued (slide 2 growth + train-of-thought audit)

---

## Summary
Rebuilt the three Brisken product-deck storyline proposals (Market Data Hub, Digital Co-Worker, Smart Trading) so each deck's body is a genuinely different structure, after the user corrected that the first pass had kept the shared marketing skeleton and only added content. The set now reads as three different talks; verified end to end and open for review.

---

## What Was Done This Session

### The three rebuilt bodies
1. **MDH → screen-led product tour** (14 slides, 12 visible): SHORT VERSION → THE WAY IT WORKS TODAY (ABAP/Datafeed-RFC pain, 71% strikeable footnote) → WHAT IT IS 5-node ribbon → SIX real product screens (connect provider / data lands / bad rate caught / change request / mapped to SAP / audited to target), each cyan-framed with 3 callouts → safe grid → dual close. Generic marketing middle cut.
2. **DCW → one request's journey** (13 slides): a EUR 2.0m Milan funding request followed across four beat slides carried by a journey rail (Request›Reads›Checks›Books›Replies), an accumulating chat thread, and a filling audit ledger → widen to the team → production proof → close. Card slides cut or merged.
3. **ST → stopwatch trilogy** (12 slides, 11 visible): THE MANUAL CLOCK (amber, 12:00, ACT 10-15 min) → THE AUTOMATED CLOCK (cyan, 0:47) → TWO CLOCKS SIDE BY SIDE → venues → architecture → close ("watch the clock go from twelve minutes to under one"). Redundant third trade-walk cut.

### Verification
1. PowerPoint COM integrity: Slides.Count 14 / 13 / 12, hidden counts correct, no corrupt package.
2. Full PNG render per deck + two fresh-eyes multi-agent QA fan-outs; all findings triaged, the one actionable fix (DCW Analysts card a line short) applied and re-verified.
3. `uv run tools/validate-demo-material.py` PASS on all three (no customer names, no excluded platform labels, no em-dashes, no "free").

### Docs
1. `decks/README.md` exceptions section rewritten to the three distinct bodies.
2. `decks/storyline-proposal-note-2026-07-14.md` gained the "Restructured 2026-07-16" section; flag 4 grew to six per-shot screen approvals.

---

## Key Decisions Made

### Restructure, not re-skin
- **Choice:** Shared bookends stay (hero, THE SHORT VERSION, WHY IT IS SAFE, dual close); the middle of each deck diverges hard via one new structural motif each (screen frame / rail+chat+ledger / stopwatch).
- **Rationale:** The bookends are matched-set signals; the identical middles were what made the decks "the same talk." Plan approved in plan mode after the user's correction.

### Honest-number grammar (ST)
- **Choice:** Only three numbers carry a source badge (ACT 10-15 min, LSEG ~90%, Brisken-framed ~12 vs <1 min); all per-step stopwatch times render muted and labeled illustrative.
- **Rationale:** B4 — no invented figures; the clock dramatizes without implying measured per-step data.

### MDH screenshot whitespace not cropped
- **Choice:** Documented as a flag-4 per-shot caveat instead of cropping.
- **Rationale:** Crop probe (`crop_shots.py`) showed the whitespace is internal to the product UI, not trimmable margin.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/brisken-market-data-hub-storyline-proposal.pptx` | Rebuilt | Screen-led tour body |
| `.../decks/brisken-digital-co-worker-storyline-proposal.pptx` | Rebuilt | One-request journey body |
| `.../decks/brisken-smart-trading-storyline-proposal.pptx` | Rebuilt | Stopwatch trilogy body |
| `.../decks/README.md` | Modified | Three-bodies description, counts, flag-4 caveats |
| `.../decks/storyline-proposal-note-2026-07-14.md` | Modified | "Restructured 2026-07-16" sign-off section |
| Session scratchpad `gen_screens.py`, `finalize_mdh.py`, `gen_dcw_beats.py`, `finalize_dcw.py`, `finalize_st.py`, `render_all.py`, `com_verify.py` | Created (ephemeral) | Parametric slide generation, reorder/renumber, COM verify/render |

Working dirs: `.scratch/deckbuild/{mdhsl,dcwsl,stsl}/` (unpacked), `.scratch/deckbuild/out/` (packed), `.scratch/deckbuild/png/` (renders), `.scratch/deckbuild/backup/` (pre-rebuild originals).

---

## Current Status
All three proposals sit beside the SharePoint mirrors, uncommitted in the working tree on `client/brisken/lead-desk-cockpit`. Nothing touched SharePoint. Dirk's flags remain open: 9 (dual close, recommended), 4 (now six MDH screens, per-shot approval; sheet at `.scratch/mdh-shots/contact-sheet.html`), 1 (71% footnote), 8 (ST value slide omitted pending his number), 3 (optional venue-gap line). MDH Commodities remains mapped only (flags 2, 6).

**User direction for the next pass (given at checkpoint):** slide 2 (THE SHORT VERSION) should grow a bit, and every slide must follow a traceable train of thought so the decks are easy to present.

---

## Next Steps
1. **Presenter-flow pass on all three decks:** grow THE SHORT VERSION slide 2 with a bit more substance, and audit/repair the slide-to-slide through-line so each slide hands off to the next (see continuation prompt in How to Continue).
2. Await Dirk's flag answers; on approval adopt into SharePoint, re-pull mirrors, delete proposals.
3. MDH Commodities rebuild once flags 2 + 6 are answered.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/README.md`
- `.../decks/storyline-proposal-note-2026-07-14.md`
- Plan: `C:\Users\neuma_p1qrsic\.claude\plans\refactored-dazzling-hopper.md` (the approved restructure plan; slide-by-slide tables)

### Open Questions
- Dirk's flags 1, 3, 4, 8, 9 (this set) + 2, 6 (Commodities).

### Working Notes
- Build loop (proven): fresh unpack via pptx-skill `office/unpack.py` → generator/finalize scripts → `clean.py` → `pack.py --original` → COM open + Slides.Count → PNG render (`render_all.py` pattern) → self-inspect → fresh-eyes multi-agent QA → `validate-demo-material.py` → ship.
- Env: `.scratch/pptxenv` (defusedxml, lxml, pywin32, Pillow); base Python 3.14 lacks the deps.
- rId gotcha: new presentation-level rIds must be first FREE above current max (`add_slide.py` handles it); a rId16 collision corrupted a package earlier.
- Footers `NN / N` are hand-set per slide: every insert/delete forces a renumber pass.
- Close PowerPoint (COM `p.Close()` + `app.Quit()`) before packing over an open deliverable; `~$*` lock files.
- cd-guard hook: use `uv run --directory` instead of `cd X && cmd`. Remove-Item path guard: unpack to fresh dir names instead of deleting.
- MDH screen whitespace is internal product UI; not fixable by cropping (probe done).

### Reference Materials
- Screens + verdicts: `.scratch/mdh-shots/` (18 CLEAN per `screening-verdicts.md`; contact sheet HTML for Dirk)
- Palette: bg #0B0E14, panel #141A25, panel2 #1B2330, border #36414F, cyan #3BE3E0, green #46D9A0, amber #FFC96B, ink #F3F6FB, muted #AAB6C7, dim #7C8A9B; Segoe UI (Semibold heads)

---

## How to Continue
Use this prompt in a fresh session:

> Continue the Brisken product-deck storyline work (checkpoint: docs/2026-07-16 - Brisken Decks Three Distinct Bodies/Checkpoint.md). The three restructured proposals sit in `workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/*-storyline-proposal.pptx` (MDH screen tour 14/12 visible, DCW journey 13, ST clock 12/11). Two refinements, all three decks, nothing touches SharePoint:
>
> 1. **Grow slide 2 (THE SHORT VERSION) a bit.** It is the executive-summary-for-a-cold-reader slide. Give it slightly more substance so a reader who only gets the file has the full thread: what this is, what it replaces, what you get, who it is for, and the bridge line into the deck's own spine (MDH "the machine", DCW "one request", ST "the clock"). A bit more meat, not a wall of text; keep the dark-cockpit layout and type scale.
>
> 2. **Traceable train of thought on every slide, so the decks are easy to present.** Audit each deck's slide sequence as a presenter would speak it: every slide must answer the question the previous slide raised and hand off to the next (bridge lines, eyebrow logic, callout order). Where a slide sits disconnected, add or sharpen the hand-off line rather than adding slides. Verify the through-line per deck by reading the rendered PNGs in order and stating the one-sentence narration per slide; if the narration doesn't flow without backtracking, fix the slide.
>
> Build mechanics: unpack → XML-edit → clean.py → pack.py, `.scratch/pptxenv` venv, COM Slides.Count verify, full PNG render + fresh-eyes QA, `uv run tools/validate-demo-material.py` must PASS, footers NN/N renumbered on any insert/delete. Banned: em-dashes, "free", SAP BTP, customer names, invented numbers (sourced badges only). Flags 1/3/4/8/9 stay Dirk's; do not resolve them.

---

## Strategic Feedback

### What Worked Well This Session
- The plan-mode redesign after the correction: the approved slide-by-slide tables made three parallel rebuilds mechanical, and each deck was verified independently before the next.

### Suggestions
- Dirk's flag answers now gate everything downstream (SharePoint adoption, Commodities rebuild, collateral generators). A single short flag-answer session with him unblocks more than any further polish pass.

### System Health
- Autonomy score: 1 human intervention this session (the structure redirect). The first pass optimizing "add content to the existing skeleton" instead of "make the talks distinct" is a Layer-3 intent lesson: when the brief's stated *purpose* (three different talks) conflicts with the path of least structural change, the purpose wins; check the output against the originating complaint, not just the task list. Candidate for agnt_intent-reviewer use before large deliverable builds.
