# Checkpoint: Brisken OnePilot Review Batch + Real Logos

**Date:** 2026-06-21
**Status:** Dirk-signed-off page-level review batch implemented, deployed, and verified live. Real customer logos embedded after a substitution correction.

---

## Summary
Implemented the full page-level batch Dirk signed off from the 18-19 June OnePilot
prototype review (copy fixes + four decisions + structural changes), deployed to the
Fly host, and verified on the live origin. Then corrected a logo miss: the eight
customer "logos" were first shipped as monochrome text wordmarks; the user required
the real, original brand logos, which were sourced, visually verified, embedded, and
redeployed.

---

## What Was Done This Session

### Review sign-off batch (commit 021f156)
1. Copy: remittance reframed off email-only to any-format; `SOC 1 Type II` made
   non-breaking (`&nbsp;`); "FX and market data, governed" -> "with governance";
   cockpit line -> "...market risk management and governance on one screen".
2. Decisions: D1 Govern -> Governance (label); D4 dropped every "SAP BTP" /
   "Business Technology Platform" mention + the two "Built on SAP BTP" badges;
   D2 "autonomous layer" -> "AI layer" everywhere so nothing implies the
   treasury/payments run autonomously; D3 no Reuters added (no change).
3. Structure: platform-map "interface" -> "cockpit" + an ecosystem endpoint strip
   (SAP S/4HANA & ECC, other systems, bank/provider portals, web apps); demo
   reframed to a live demo on Brisken's own SAP environment, heading "See for
   yourself: stop believing, start doing"; four buyer FAQs (IT budget, AI safety,
   liquidity forecasting, focus-the-day) added to the accordion AND the FAQPage
   JSON-LD; footer privacy note; type/heading scale bumped for 100% zoom; OnePilot
   hub node enlarged.

### Real customer logos (commit 27df8b8)
1. First pass shipped the 8 customers (Nestlé, Ford, Siemens, YETI, BAT, Zespri,
   Equinor, KAUST) as monochrome text wordmarks. User correction: always use the
   real original logos, never substitutes.
2. Sourced official logos from Wikimedia Commons + English Wikipedia via the
   MediaWiki imageinfo/search API (Clearbit's logo API is dead). Rendered each in
   a real browser (localhost contact sheet via Playwright) and visually verified
   before embedding. Caught two bad matches: the search returned a sports-club
   logo for "BAT" (fixed to the real British American Tobacco "A Better Tomorrow"
   mark) and a departmental seal for KAUST (fixed to the official KAUST mark).
3. Embedded all 8 as base64 data URIs matching the existing banner pattern;
   dropped the unused `.logo-wm` CSS; added height/width balance for the
   stacked/bilingual marks.

### Deploy + verification (both passes)
1. `sync-site.py` (flat deliverable -> `site/index.html`), kept the sorted
   duplicate in sync, `flyctl deploy` to `brisken-onepilot-proto` (fra), twice.
2. Verified each time on the live origin by minting a real name-gate cookie via
   the `/welcome` POST and grepping the gated HTML; for logos, also drove the gate
   in Playwright and screenshotted the live banner. `validate-html.py`: 0 hits.

### Memory
- Created `feedback_use_original_logos.md` + MEMORY.md pointer.

---

## Key Decisions Made

### Scope held to the signed-off batch only
- **Choice:** Implemented only the page-level sign-off sheet, not the broader OnePilot
  positioning (which the sheet itself excludes as "a separate conversation").
- **Rationale:** The platform-first reposition is still gated on Dirk; keeping
  "AI layer" framing (current) while only removing the "autonomous" overclaim stays
  inside D2's scope without pre-empting the bigger call.

### Real logos, sourced + verified, not substituted
- **Choice:** Source official brand logos and visually verify each before embedding;
  never ship text-wordmark stand-ins.
- **Rationale:** Direct user directive. The established banner already used real
  embedded logos; a substitute reads as low-effort and wrong.

### Did not open a whole-branch PR to main
- **Choice:** Commit + push to `client/brisken/lead-gen-onepilot`; no `gh pr create`/merge.
- **Rationale:** The branch aggregates large in-flight work from prior sessions
  (revision blueprint, fit memo, the uncommitted project-sort reorg). The ship target
  the user ordered was the Fly deploy (done + verified). A main merge is the owner's call.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html` | Modified (tracked) | Review batch + real logos; the sync source |
| `workspace/clients/brisken/deliverables/lead-generation/onepilot/brisken-onepilot-website-prototype.html` | Modified (untracked dup) | Sorted-reorg copy kept byte-identical |
| `workspace/clients/brisken/onepilot-site/site/index.html` | Synced (gitignored) | Served copy for the Fly build |
| `~/.claude/.../memory/feedback_use_original_logos.md` | Created | Always-use-original-logos rule |
| `~/.claude/.../memory/MEMORY.md` | Modified | Index pointer |

Commits (pushed, branch `client/brisken/lead-gen-onepilot`): 021f156, 27df8b8.

---

## Current Status
All signed-off page-level changes are live on `https://brisken-onepilot-proto.fly.dev/`
(name-gated) and verified on the deployed origin, including the eight real customer
logos in the rolling banner. Host is a custom FastAPI static host on Fly (not a
workflow-engine), so no ops audit applies. Comms current (Dirk 2026-06-20).

---

## Next Steps
1. Update the prototype footer `Last updated:` stamp (still reads 2026-06-18; it was
   edited 2026-06-20/21) per the deliverable last-updated rule. Quick one-line fix.
2. Await Dirk on the broader OnePilot positioning (platform-first hierarchy + the
   three open decisions) — the separate conversation the sign-off sheet excluded.
3. Rome E2 send Mon 2026-06-22 (`send-rome-campaign.ps1 -Wave E2`, 105 recipients),
   E3 Tue 2026-06-23; warm/customer message for the 8 pulled contacts still owed
   (sender Matthias or Dirk TBD).
4. Optional: commit the project-sort reorg (the sorted-path duplicate is currently
   an untracked copy kept in sync by hand).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html` (the live prototype source)
- `workspace/clients/brisken/deliverables/brisken-onepilot-review-signoff.md` (the batch that was implemented)
- `workspace/clients/brisken/onepilot-site/app.py` + `sync-site.py` (gate + deploy pipeline)

### Open Questions
- Touch the Rome landing page hierarchy before 24 Jun, or leave it for the booth?
- Warm/customer outreach sender + timing.

### Working Notes
- **Logo sourcing recipe (reusable):** MediaWiki API `action=query&prop=imageinfo&iiprop=url`
  resolves a `File:` title to its `upload.wikimedia.org` URL; `list=search&srnamespace=6`
  finds candidates. Commons for most; non-free corporate marks (KAUST) live on
  `en.wikipedia.org` at `upload.wikimedia.org/wikipedia/en/...`. Always render +
  eyeball before embedding: a name search returned a wrong file twice this session.
- **Live verification of the gated prototype:** `curl -c jar -b jar -L --data
  "name=X&next=/" .../welcome` mints a server-signed cookie (the app HMACs it with the
  live secret), then the jar fetches `/`. For a rendered check, Playwright can't open
  `file://` (blocked) — serve via `python -m http.server` and navigate to localhost.
- The three HTML copies (flat tracked / sorted untracked / `site/index.html` gitignored)
  must stay byte-identical; `sync-site.py` reads the FLAT path, so edit there.

### Reference Materials
- Live prototype: https://brisken-onepilot-proto.fly.dev/ (name-gated)
- Fly app: `brisken-onepilot-proto` (fra)

---

## How to Continue
The prototype batch is shipped and verified; the next prototype move is Dirk's
positioning decision, not more edits. The active operational thread is the Rome
campaign (E2 send Monday). If picking up the prototype, fix the last-updated stamp
first, then wait on Dirk.

---

## Strategic Feedback

### What Worked Well This Session
- Visual verification before embedding caught two wrong logo files (BAT sports club,
  KAUST seal) that a name-match-and-ship pass would have published. Render-and-eyeball
  is the right gate for any sourced asset.

### Suggestions
- When a request implies an external asset (logos, images, fonts) that isn't on hand,
  the default should be source-the-real-thing or ask, never substitute-and-offer. That
  was the session's one correction and it is now a memory.

### System Health
- The "always use original logos" miss is a judgment gap, not a tooling gap; logged as
  `feedback_use_original_logos`. No structural hook fits cleanly (a gate can't tell a
  wordmark substitute from a real logo at write time).
- Autonomy score: 1 human intervention this session (the logo correction).
