# Checkpoint: Brisken TC Overview Dirk Review Integration

**Date:** 2026-07-22
**Status:** Deck integrated + live in Asset Testing (0 placeholders). resources.brisken.com assessed as already-matching (no change made). One owner decision open.

---

## Summary

Pulled Dirk's SharePoint review of the NEW TreasuryCentral Solutions Overview deck (7 comments + 4 in-place text edits, including the before/after content that closed the last 3 `[NEEDS INPUT]` placeholders), folded all of it back into the build source, re-verified and re-uploaded. Then assessed the resources.brisken.com TreasuryCentral page + PDF against the same content and concluded no change was necessary.

---

## What Was Done This Session

### 1. Retrieved Dirk's feedback (autonomously, from the live file)
1. Listed Asset Testing with editor/modified metadata; spotted the NEW pptx at 475,256 B modified 11:53, ~29 KB larger than what was shipped and 52 min after the PDF upload; the PDF was untouched, so only the pptx carried edits.
2. Downloaded that live version via CDP (`download_dirk.py`), byte-exact.
3. Extracted **7 modern-comment parts** (`ppt/comments/modernComment_*.xml`) mapped to slides via slide rels, and diffed all 31 slides' text runs against the shipped deck to surface **4 in-place edits**.

### 2. Integrated all 11 feedback items into the source
Folded into `build2.py` / `build.py` (not patched into the pptx) so the source stays canonical and his verbatim edits survive regeneration.

- **His 4 verbatim edits, adopted as-is:** S22 "Validates it against your SAP customer master and invoices"; S23 cash-flow before-line reorder; S30 "rating and credit report attributes" + "Feeds SAP Credit Management and business partner, or any risk system". (S31 was a run-boundary re-save, no text change.)
- **His 7 comments, resolved:** S8 TreasuryCentral reframed "one workspace on OnePilot" + new caption "OnePilot connects your SAP and non-SAP systems alike"; S9 dropped "SAP & SAP OneExposure" for "SAP: on-prem, private & public cloud" (same de-specifying applied to S13); S10 governance gained the AI vocabulary (grounded in SAP, not free-floating; human-in-the-loop / HITL); S12 MDH emphasises SAP **and** non-SAP + "Assembling the audit trail by hand"; S18 DCW workload-removed column rewritten to the concrete work + "every action logged"; S19 "SAP process steps" / "Records & notes" replacing "SAP postings" / "Memo records" (cascaded to the S18 CONNECTS-TO strip); S25 the three before/after fills.

### 3. Verified
1. Rebuilt (31 slides), rendered all slides via PowerPoint COM, inspected montages g2–g5 plus full-res s12/s25.
2. Caught and fixed **2 layout regressions the new text introduced**: MDH step 4 clipped out of its card (reverted step 2, shortened step 4, moved the governance emphasis to the roomier freed column); success-card REPLACED box colliding with the highlight line (card re-spaced, h 3.5 -> 3.82).
3. Gate scan on the built deck: **0 em-dashes, 0 banned terms** (checked seamless/robust/leverage/BTP/ChatGPT/"your live SAP data"/central-repository).
4. Exported PDF (435,967 B), staged both files to deliverables.
5. Re-uploaded pptx+pdf to Asset Testing; verified PDF byte-exact, PROPOSAL pair untouched.

### 4. Chased an anomaly rather than assuming
"MN - " prefixed copies (Overview pair + PROPOSAL pair) appeared in Asset Testing at 12:18, mid-session. The `MN - Overview` pptx was 478,834 B vs the 475,256 B I had integrated from — a gap that could have hidden feedback. Downloaded it and diffed: **identical 7 comments, 0 slide-text differences**. The delta is a PowerPoint-Online metadata/thumbnail rewrite. Nothing was missed. Left the files alone (did not create them, intent unknown) and surfaced them instead.

### 5. resources.brisken.com assessment (no change made)
Read the generator (`tools/brisken-sap-onepagers.py`, `web_body_treasurycentral`) which produces both the page and its PDF (the PDF is a print-render of the same page), then WebFetched the live page to confirm they match. Verdict: **already matches this content** — the phrasings Dirk asked to remove were never there (no "SAP OneExposure", no "SAP postings"/"memo records", no LLM name-drop on that page), the hierarchy is already "TreasuryCentral is the treasury workspace... Underneath it, OnePilot runs two applications", and the governance vocabulary (audit trail, four-eye, segregation of duties, HITL in plain words) is present. Reported "not necessary" rather than making cosmetic edits.

### 6. Descoped mid-session
User interrupted: "skip sanofi step dont deploy that". Sanofi TreasuryCentral deck update dropped; nothing deployed anywhere.

---

## Key Decisions Made

### Fold feedback into the build source, not the pptx
- **Choice:** Edit `build2.py`/`build.py` and regenerate, rather than patching Dirk's edited pptx.
- **Rationale:** The source is canonical; patching the artifact would have left the generator stale and silently lost his 4 verbatim edits on the next rebuild.

### Regenerate clean (no comment bubbles)
- **Choice:** Ship a deck with the comments resolved and removed, not preserved.
- **Rationale:** Comments were feedback to act on, not content to archive. SharePoint version history retains his annotated copy.

### Apply "remove SAP OneExposure" beyond the commented slide
- **Choice:** He flagged it on S9; also removed it from S13.
- **Rationale:** He called the term "too specific" — a content judgment about the term, not that one slide. Keeping it on one slide and not the other would be incoherent.

### Move the MDH governance emphasis instead of bloating the steps
- **Choice:** When the step card overflowed, reverted the step-2 addition and put "Assembling the audit trail by hand." in the freed column.
- **Rationale:** Honors his "data governance and compliance emphasis" ask while fitting the layout; the column had room, the step card did not.

### Do not touch the "MN - " files
- **Choice:** Verify their content, then leave them and surface to the owner.
- **Rationale:** Files I did not create, with unknown intent. Renaming/deleting them would be presumptuous, and the verification already proved no feedback was missed.

### Report "not necessary" on resources.brisken.com
- **Choice:** Make no content edit; state the evidence for why none is needed.
- **Rationale:** The user explicitly invited that answer ("if its not necessary, feel free to say so"). Editing already-correct copy would be churn, and the deploy was forbidden this session anyway.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `deliverables/tc-overview-redesign/NEW - ... 2026-07-21.pptx` | Modified | Rebuilt with Dirk's feedback (457,659 B on SharePoint) |
| `deliverables/tc-overview-redesign/NEW - ... 2026-07-21.pdf` | Modified | Re-exported, 435,967 B |
| `deliverables/tc-overview-redesign/CHANGELOG-substance-pass.md` | Modified | "Dirk review integration" section; `[NEEDS INPUT]` marked RESOLVED (0 remaining) |
| `workspace/clients/brisken/status/p2-product-decks.md` | Modified | "Dirk review integrated" subsection + MN-folder note |
| scratchpad `tc-overview-new/build2.py`, `build.py` | Modified | Deck source (ephemeral scratchpad, not tracked) |
| SharePoint `2026_PPTX/Asset Testing` | Uploaded | NEW pptx+pdf replaced with the integrated pair (verified) |

Not modified (deliberately): `tools/brisken-sap-onepagers.py`, `resources-site/*` — no change necessary.

---

## Current Status

- **Overview deck:** Dirk's review fully integrated, visually verified, live in Asset Testing. **0 `[NEEDS INPUT]` placeholders remain** — he supplied the last three.
- **Asset Testing Overview family:** `NEW - ...2026-07-21` (integrated), `MN - ...2026-07-21` (pre-integration copy, user-made), `MN - ...2026-08 PROPOSAL`, plus the original PROPOSAL pair.
- **resources.brisken.com:** assessed, unchanged, not deployed.
- **Sanofi deck:** untouched (descoped by user).
- No commits made this session; ledger files below are written but uncommitted.
- **Platform (brisken):** `infrastructure.yaml` tier "unknown", ops budget TBD — a custom SaaS build, not a workflow-engine op count, so no ops-limit verdict applies.
- **Status sweep:** `p2-product-decks.md` current (0d). Four sibling workstreams flagged stale at 31d (`p2-lead-gen-general`, `p2-onepilot-site`, `p2-outreach`, `p2-targeting`) — none touched this session, so they were left alone rather than given invented progress.

---

## Next Steps

1. **Owner decision:** the resources.brisken.com **OnePilot** page (not TreasuryCentral) describes a customer as "a ChatGPT-powered deployment" — an LLM-vendor name-drop against Dirk's language rules. One-word fix + regenerate + deploy, or leave. Blocked on the user because it is out of the page scope they named and they instructed no deploy.
2. **Sanofi TreasuryCentral deck** — apply the same messaging pass when the user re-scopes it.
3. **Dirk:** choose the Overview DIRECTION (clone-and-patch `2026-08 PROPOSAL` vs the `NEW` rebuild).
4. **"MN - " naming reconciliation** in Asset Testing — owner call whether `MN -` becomes canonical (if so, republish the integrated deck under that name and drop the duplicate `NEW -` pair).
5. Ledger files (INDEX/session log/friction register) need a `docs/...` branch PR to reach main.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/deliverables/tc-overview-redesign/CHANGELOG-substance-pass.md` — full provenance incl. the Dirk-review section
- `workspace/clients/brisken/status/p2-product-decks.md` — workstream state
- `tools/brisken-sap-onepagers.py` (`web_body_treasurycentral`, ~line 1047) — the resources page + PDF source
- `workspace/clients/brisken/automations/lead-generation/deckgen/MESSAGING.md` — the messaging lock

### Open Questions
- Is `MN -` the intended canonical naming for Asset Testing, or a personal working copy?
- Should the OnePilot resources page drop the "ChatGPT-powered" phrasing?

### Working Notes
- **Deck build source is ephemeral.** `build2.py` imports `build.py` helpers from the session scratchpad (`tc-overview-new/`). It is NOT tracked. If it is gone next session and the deck needs another pass, the deck must be rebuilt from the committed pptx or the source re-created. Worth promoting to `tools/` if the Overview keeps iterating.
- **Comment extraction recipe that worked:** modern PowerPoint comments live in `ppt/comments/modernComment_*.xml` (text in `<...text>` elements); map comment part -> slide via `ppt/slides/_rels/slideN.xml.rels` targets. `ppt/authors.xml` gave one author for all 7 (the sync account), so authorship is not a reliable signal of who wrote them; content is.
- **Slide-position mapping** (physical 1-based) for the 31-slide deck: 8 hierarchy, 9 platform-functional, 10 governance, 12 MDH app, 13 MDH functional, 15 Smart Trading, 18 DCW app, 19 DCW functional, 21-23 use cases, 25 success stories, 26 contact, 28 legacy-vs, 29-31 appendix hubs.
- **Layout capacity is tight** on the 3-column app slides (`s_app`) and the success cards. Adding a clause to a step reliably overflows; check the render before assuming text fits.
- **Rendering:** LibreOffice/soffice is not installed; PowerPoint COM (`render.ps1`) is the working path for PNG + PDF export.
- **resources.brisken.com deploys only on a manual `vercel deploy`** — a PR does nothing to the live site (documented lesson in `project_brisken_resources_subdomain_and_dns`).

### Reference Materials
- Asset Testing: `/sites/MARKETING/Shared Documents/20_Assets/BRISKEN PRESENTATIONS/OnePilot - Cloud Solutions Presentations/2026_PPTX/Asset Testing`
- Live page checked: `https://resources.brisken.com/treasurycentral.html`
- CDP automation Edge on port 9223 (signed-in SharePoint tab required)

---

## How to Continue

The deck work is complete and shipped. Pick up at Next Step 1 (the ChatGPT line decision) or 2 (Sanofi) once the user re-scopes. If touching resources.brisken.com, edit `tools/brisken-sap-onepagers.py`, run `uv run tools/brisken-sap-onepagers.py`, then deploy with the Vercel token and byte-verify live vs local — a PR alone will not update the site.

---

## Strategic Feedback

### What Worked Well This Session
- "Dirk made a few edits and left a few comments" with no attachment was enough — the feedback was retrievable straight off SharePoint. Not having to relay comments by hand removed a whole transcription step and any paraphrase risk.
- The mid-session interrupt to descope Sanofi landed before real effort was spent (only a download had started), which is the cheapest possible moment to change scope.

### Suggestions
- When Dirk reviews a deck, a one-line "he's reviewed X, it's in Asset Testing" is all that is needed; the comments and edits can be pulled directly. No need to summarize them.

### System Health
- **The deck build source lives in an ephemeral scratchpad.** This Overview has now had three substantial passes (rebuild, substance, Dirk-review) and each one depended on `build2.py` still being in the session scratchpad. That is a real single point of failure for a deck that keeps iterating; promoting the generator into `tools/` (as `brisken-sap-onepagers.py` already is) would make the next pass reproducible instead of lucky.
- **Autonomy score: 1 human intervention this session** (the Sanofi/no-deploy descope, a scope change rather than a correction). 2 self-detected friction events, both minor and logged.
