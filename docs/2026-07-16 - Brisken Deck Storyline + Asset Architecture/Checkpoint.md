# Checkpoint: Brisken Deck Storyline + Asset Architecture

**Date:** 2026-07-16
**Status:** Two R1 proposal decks built + a whole-estate asset architecture drafted; MDH build + Dirk sign-off pending.

---

## Summary
Fixed Dirk's "decks are hard to explain / all look the same / not enough
background" feedback by building a per-deck storyline standard on Digital
Co-Worker and Smart Trading (proposal .pptx beside the mirrors), added an
exec-summary intro slide to both after his audio feedback, then swept
Brisken's assessment collateral (web + SharePoint) and designed a six-role
asset architecture for the whole client-facing estate.

---

## What Was Done This Session

### Deck storyline standard (built)
1. **Digital Co-Worker proposal** (`brisken-digital-co-worker-storyline-proposal.pptx`, now 14 slides): qualified problem slide (APA 40% + HBR 1,200-toggles, sourced from Dirk's own vision doc), bank-transfer example promoted to the fix-reveal, new "WHAT IT IS" functional-overview slide, new "WHERE IT ALREADY RUNS" anonymized production-proof slide, new "THE SHORT VERSION" exec-summary intro at pos 2.
2. **Smart Trading proposal** (`brisken-smart-trading-storyline-proposal.pptx`, 13 slides, 2 hidden): problem re-laid as 2-col + sourced stat pair (ACT 10-15 min, LSEG ~90%), "minutes to seconds" promoted to fix-reveal, new "ONE TRADE, ON THE CLOCK" storyboard, safe-grid card swap, "THE SHORT VERSION" intro, architecture diagram un-hidden per Dirk's explicit-diagram directive.
3. **MDH screenshot screening:** 30 real product screens hygiene-screened (18 clean / 12 disqualified for customer identifiers, real names, platform labels); contact sheet at `.scratch/mdh-shots/contact-sheet.html`.
4. **Sign-off note for Dirk** (`storyline-proposal-note-2026-07-14.md`): four per-deck spines + 9 open flags.

### Assessment research + asset architecture
5. Swept assessment collateral: live web (brisken.com = "Book a demo" only), SharePoint MARKETING drive (Graph app-only), the 2026-07-14 Dirk/Jochen protocol. Found the full "Analysis of Potential" (AOP) + Treasury Assessment family + the pre-assessment funnel ("Apply for your Free Treasury Assessment").
6. Designed a **six-role asset architecture** (3-lens design workflow + adversarial judge): Sent Deck / Room Instrument / Proof Capsule / Web Surface / Offer Vehicle / First Touch, with per-role skeletons, a CTA ladder resolving the June-spine vs July-pivot tension, governance, ranked changes, retire list.

### Records written
7. `brisken-assessment-context.md`, `brisken-asset-architecture.md` (both in `context/lead-generation/evidence/`), a comms-log research entry, and the GTM-pivot fact into the Jochen memory.

---

## Key Decisions Made

### Storyline standard = per-deck distinctive spine, one visual system
- **Choice:** Keep Dirk's dark-cockpit visual system untouched; differentiate the four decks by presenting spine (MDH = product screens, ST = the clock/metrics, DCW = story + production proof, Commodities = one worked case), not by re-skinning.
- **Rationale:** His complaint was "all look the same" AND "hard to explain"; the fix is narrative + de-duplicated shared slides, not new branding.

### Output = proposal files, never overwrite mirrors
- **Choice:** All builds are `*-storyline-proposal.pptx` XML-edited copies; redundant slides hidden (`show="0"`), never deleted.
- **Rationale:** SharePoint is source of truth, Dirk edits directly; the `decks/README.md` mirror contract forbids regeneration.

### Six-role taxonomy keyed on reader knowledge + attention
- **Choice:** Roles are defined by "what does the reader know, how long will they look" (Dirk's own axis), not funnel stage or file type.
- **Rationale:** The adversarial judge found the reader-context lens the only one that survives Dirk's cold-link-vs-room asymmetry and his per-asset questions.

### CTA ladder answers flag 9 (recommended, pending Dirk)
- **Choice:** June spine governs naming, July pivot governs the offer ladder. Demo where a product earned attention, Quick Assessment where none has, dual close on sent decks; "free" banned from CTA copy (DACH pays ~15k EUR).
- **Rationale:** The two policies govern different axes and stop conflicting once separated.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../rome-2026/decks/brisken-digital-co-worker-storyline-proposal.pptx` | Created | R1 proposal deck (14 slides) |
| `.../rome-2026/decks/brisken-smart-trading-storyline-proposal.pptx` | Created | R1 proposal deck (13 slides) |
| `.../rome-2026/decks/storyline-proposal-note-2026-07-14.md` | Created | Dirk sign-off note, 9 flags |
| `.../rome-2026/decks/README.md` | Modified | Recorded the two proposals + note as non-mirror exceptions |
| `.scratch/mdh-shots/contact-sheet.html` + `screening-verdicts.md` | Created | Screenshot approval sheet (18 clean) |
| `context/lead-generation/evidence/brisken-assessment-context.md` | Created | Durable assessment reference |
| `context/lead-generation/evidence/brisken-asset-architecture.md` | Created | Six-role structure standard |
| `context/comms-log.md` | Modified | Audio-feedback + research entries |
| `~/.claude/.../memory/project_jochen_treasury_assessment.md` | Modified | Added 2026-07-14 GTM-pivot facts |

---

## Current Status
Two of four product decks built to the R1 standard and open in PowerPoint for
Matthias's review; both pass the banned-content validator. MDH ("SHOW THE
MACHINE") and Commodities ("FOLLOW ONE PRICE") are slide-mapped but not built
(deferred on Dirk flags 1/2/4/6). The asset architecture is internal-only;
Dirk-facing distillation waits for his approval of the deck standard.
Platform (expense-recon): custom SaaS build, tier unknown, not op-count-gated;
no ops-audit needed. Brisken comms current (logged today).

---

## Next Steps
1. **Build MDH + Smart Trading + DCW to the R1 standard as a matched set** to show Dirk (this session's next deliverable — see the implementation prompt handed to Matthias). MDH is the big new build (SHOW THE MACHINE spine, product screens, walkthrough-sourced pipeline detail).
2. Await Dirk's answers to the 9 flags (esp. flag 9 = the CTA ladder, flag 4 = screenshot approvals, flag 1 = the 71% job-ads stat).
3. On approval: adopt into SharePoint, re-pull mirrors, delete proposals; then roll the R1 standard to Commodities + the combined deck decision.
4. Deferred architecture work items (post-approval): assessment R4 web page (blocking dependency for the CTA), promote deckgen out of `.scratch/`, validator probes, ASSET-REGISTER.md.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/lead-generation/evidence/brisken-asset-architecture.md` (the six-role standard + R1 skeleton)
- `workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/storyline-proposal-note-2026-07-14.md` (four spines + 9 flags)
- `workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/README.md` (mirror contract)
- The two built proposal .pptx (clone source for new slides + the R1 pattern)
- `.scratch/mdh-source-parse.txt` (MDH walkthrough enrichment content)

### Open Questions
- Dirk's 9 flags, unresolved (CTA ladder, screenshots, commodities anonymization + number, Shadow-Integration stat, partners wall, combined-deck retire, sendable-assessment-deck yes/no).
- Whether to apply the dual-close CTA on the demonstration decks now (recommended version) or hold it until the assessment web page exists.

### Working Notes
- **PPTX build mechanic:** unpack (defusedxml) → XML-edit slides → reorder `p:sldIdLst` + `presentation.xml.rels` + `[Content_Types].xml` → pack (defusedxml + lxml) via the pptx skill's `office/pack.py`. **GOTCHA hit this session:** a NEW slide's relationship Id must not collide with existing presentation-level rels (ST's slides ended at rId15 but rId16 was already the notesMaster → duplicate corrupted the package; caught by opening via PowerPoint COM). Always pick the first free rId above the max, and verify by opening the packed file via COM before shipping.
- **QA loop:** export changed slides to PNG via PowerPoint COM (`$pp.Presentations.Open(...).Slides.Item(N).Export(...)`), Read the PNGs, fix overflow/footer/icon issues, re-render. One text-overflow was caught and trimmed this way.
- **Intro slide ("THE SHORT VERSION"):** 3-row what-this-is / what-it-replaces / what-you-get card, closing bridge "The next page is where you are today." Built by a reusable `intro_slide()` helper in the scratchpad `build_intros.py`.
- **Graph SharePoint read:** app-only client-credentials from `context/.env` reach the MARKETING drive directly by drive-ID (`b!b9O4ZXcn...`); `/sites?search` 403s and `/root/search(q=)` 500s, but `/root:/path:/children` and `/root:/path:/content` work. Space in a path → URL-quote it (control-char error otherwise).

### Reference Materials
- SharePoint assessment paths: `25_CONTENT/AOP/`, `20_Assets/BRISKEN PRESENTATIONS/Consulting Solutions Presentations/CON_Treasury Services/` (+ `Treasury Assessment/` subfolder), `01_MEETINGS/JOCHEN IN KA 260714/Protokoll-Jochen-Treasury-Assessment_2026-07-14.docx`.
- Audio source: `iCloudDrive/UnpauseAI/Brisken_/Dirk assets.m4a` (transcribed via faster-whisper, small model).

---

## How to Continue
Run the implementation prompt (below, handed to Matthias) to build MDH + refresh
DCW/ST as a matched R1 set. Everything routes through the same pipeline: XML-edit
copies of the mirrors → pack → PowerPoint COM render QA → `validate-demo-material.py`
→ proposal file beside the mirror → open for review. Never touch SharePoint or the
mirrors; hidden slides stay hidden.

---

## Strategic Feedback

### What Worked Well This Session
- Handing the audio file path directly ("extract anything useful") let the whole feedback loop run autonomously: transcribe → extract directives → apply to both decks → log → surface. No back-and-forth.
- The "brainstorm a structure, then implement to show Dirk" sequencing is the right shape — design once at the estate level, then demonstrate on three concrete decks before committing.

### Suggestions
- When Dirk gives audio feedback, keep dropping the file path; local faster-whisper handles German cleanly and the directives are richer than a text summary would be.
- Consider batching the 9 flags into one short Dirk-facing message (or a Loom over the two decks) rather than waiting for a flag-by-flag reply — several flags are cheap yes/nos.

### System Health
- **Source-of-truth risk surfaced:** the deck generators (`build-*.js`) live in the gitignored `.scratch/deckgen/`; a `.scratch` wipe would delete the only source for six client-facing decks. Flagged as ranked change #3 in the architecture doc; worth a real fix soon.
- The pptx build/QA loop is now a well-worn path but entirely ad-hoc scratchpad scripts. If deck work continues at this rate, a small `tools/pptx-slide-ops.py` (unpack/insert-slide/reorder/renumber-footers/pack with rId-collision-safety) would retire the recurring GOTCHA.
- Autonomy score: 1 (one hook-caught B1 closing deferral, self-corrected; no user interventions).
