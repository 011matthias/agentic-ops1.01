# Checkpoint: Brisken OnePilot Launch + Site Polish

**Date:** 2026-06-23
**Status:** onepilot.brisken.com live (public, orbit page). brisken.com + the Fly review host updated and verified. All work shipped on `client/brisken/lead-gen-onepilot`, not merged.

---

## Summary
Took the reviewed OnePilot orbit page from internal-review-only to **live on the public onepilot.brisken.com**, then ran a batch of owner-review polish across the OnePilot page and the brisken.com (TreasuryCentral) site: finished orbit review rounds 5b–7, rebuilt the applications block, replaced "Book a demo" with an inline lead-capture modal, generalized the SAP-specific definition, built more brisken.com→onepilot links, and spaced/rewired the brisken.com CTA + map node.

---

## What Was Done This Session

### OnePilot orbit page — review rounds 5b–7 (Fly + dev1, commits 39decd4 / f3fe325 / 09bea98)
1. **5b — real Brisken logo + favicon.** Replaced the drawn 3-polygon cube stand-in with the real brisken.com wordmark (theme-swapped, defined once in CSS) in nav + footer, and the real cube PNG favicon (page `<link>` + the `app.py /favicon.ico` route). Backed by `feedback_use_original_logos`.
2. **6 — applications as cards + show-all + centered nav.** The "not limited to SAP/finance" callout became proper app cards; grid defaults to 3 (BST treasury / Market Data Hub SAP / Sales & account desk illustration) with a "Show all (5 more)" toggle; the three other-field cards marked "Illustration"; top nav switched to a `1fr auto 1fr` grid so the links are page-centered.
3. **7 — vertically centered orbit.** Raised the single vertical anchor (JS `cy=H*0.50`, core `top:50%`, orbit `transform-origin:50% 50%`) from 58% so the constellation sits at viewport center (measured live: core at 50.0%).

### onepilot.brisken.com launch (Vercel, commit 6d1615e)
4. Published the **pristine dev1 orbit source** (no name gate, no review annotator) as `website/onepilot.html`, replacing the placeholder. Repointed the two Fly prototype links to `https://www.brisken.com`; added canonical/og:url/og:image (og-op.png)/twitter/apple-touch-icon for onepilot.brisken.com. Deployed via the personal Vercel scope using a user-supplied token. **Resolves the two-surfaces question:** onepilot.brisken.com (Vercel, public) vs brisken-onepilot.fly.dev (Fly, gated internal review).

### Contact modal (Vercel + Fly, commit 4b9d1d6)
5. Removed "Book a demo" (the #demo button, footer link, softened the FAQ/JSON-LD prose). The "Contact us" fab + a replacement #demo button + footer link now open an on-brand inline modal posting to the existing `/api/book-demo` (Neon + ntfy), reusing the demo form's spam guards (honeypot + `elapsed_ms`≥3000), mapping the message → `preferred_date`, tagging `source_page`. Verified live end-to-end (open → validate → submit → success).

### Definition generalized (Vercel + Fly, commit 49b642f)
6. Reworded "What is OnePilot?" + "How do you get started?" (visible + FAQPage JSON-LD) **and** the Organization + SoftwareApplication JSON-LD descriptions so the definition is general (runs a team's work on one surface across ERP/banking/market data/email/spreadsheets; **SAP is one example**); TreasuryCentral kept as the honest first shipped edition.

### brisken.com → onepilot.brisken.com links (Vercel, commit 4c1e280)
7. Added 4 contextual inline links (no copy changes, wrapping existing "OnePilot" mentions) in the map intro, the "powered by OnePilot" heading, the SAP-foundation section, and the platform FAQ — 6 total now (was 2), well distributed.

### brisken.com CTA spacing + map node redirect (Vercel, commit 9f2dfcd)
8. Spaced out the CTA credentials (fixed a latent `.cta-band p` specificity bug zeroing `.cta-fine` top margin; now `.cta-band .cta-fine` margin-top 32px + line-height 1.7 + band padding 64px). Made the **OnePilot map hub node navigate to onepilot.brisken.com** instead of opening the in-page panel (locator/nav still open the panel).

### Hours
9. Logged **1.5h to Lead Generation** (rounds 5b–7 + the onepilot.brisken.com launch) via `/comd_brisken-hours`. Lead Generation now 32 rows / 66.0h / EUR 924. Fixed a tracker control-check mismatch (added the missing `J11` week-of-2026-06-22 bucket).

---

## Key Decisions Made

### Public OnePilot page = pristine dev1 source, not the Fly deliverable
- **Choice:** onepilot.brisken.com serves the dev1 `onepilot-orbit.html` (no name gate, no review annotator), copied to `website/onepilot.html` on the Vercel site that owns the domain.
- **Rationale:** The Fly host is the gated internal-review mirror (carries the annotator); the public site must be clean. Repointed Fly-only links to public ones.

### Contact form reuses the launched book-demo backend
- **Choice:** The "Contact us" modal POSTs to the existing `/api/book-demo` (Neon + ntfy), message mapped into `preferred_date` (no schema change).
- **Rationale:** Converts a dead link into a real funnel on infra already live; a dedicated `message` column would need a user-side Neon migration.

### SAP is an example, not the definition
- **Choice:** Generalized OnePilot's definition everywhere (visible + all JSON-LD); TreasuryCentral-on-SAP stays the one honest shipped edition.
- **Rationale:** Owner direction; consistent with the positioning memory (platform breadth, not SAP-bound).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/website/onepilot.html | Created (replaced placeholder) | Public onepilot.brisken.com orbit page + contact modal + general FAQ |
| workspace/clients/brisken/website/treasury.html | Modified | 4 OnePilot links, CTA spacing fix, OnePilot map node → onepilot.brisken.com |
| workspace/clients/brisken/deliverables/brisken-onepilot-platform.html | Modified | Fly review host: rounds 5b–7, contact modal, general FAQ |
| workspace/clients/brisken/onepilot-site/app.py | Modified | `/favicon.ico` serves the real cube PNG |
| ../agentic-dev1/.../onepilot-orbit.html | Modified (untracked) | Canonical source: all rounds, parallel-edited |
| workspace/hours-tracker.xlsx | Modified (local, gitignored) | +1.5h Lead Gen; J11 week bucket fix |
| ~/.claude/.../memory/project_brisken_onepilot_site_hosting.md | Modified | Rounds 5b–7, launch, two-surfaces resolution |
| ~/.claude/.../memory/project_local_password_vault.md | Modified | Use `$HOME\vault.py` not `~/vault.py` for user commands |

---

## Current Status
- **onepilot.brisken.com** — LIVE (Vercel, public): orbit page, centered, real logo, app cards + show-all, contact modal, general definition. Verified (200, Playwright e2e).
- **brisken-onepilot.fly.dev** — gated internal review host, same content + the review annotator (relative `/api/book-demo` degrades gracefully there, no API).
- **brisken.com / www** — TreasuryCentral; 6 links to onepilot.brisken.com, spaced CTA, OnePilot map node opens the platform site.
- No `platform` ops section for brisken in infrastructure.yaml; the Vercel/Fly hosts are outside the Make/n8n ops model (lightweight ops line N/A).

---

## Next Steps
1. **User:** save the Vercel token to the vault — `uv run C:\Users\neuma_p1qrsic\vault.py add "Vercel Brisken" client=brisken token=vcp_... notes="...30 days, expires ~2026-07-22"` (the `~/vault.py` form fails in PowerShell). Token expires **~2026-07-22**; renew then for the next deploy.
2. **User:** clean the verification test lead — `delete from leads where email like '%brisken-demo.invalid%'` (one row created testing the contact modal; one ntfy ping fired).
3. **Tool:** extend `tools/log-brisken-hours.py` to add a weekly "By week" bucket when logging into a new week (and grow the 3-slot control range when a 4th week appears — currently full: 06-08/06-15/06-22).
4. Decide whether/when `client/brisken/lead-gen-onepilot` merges to main (still the owner's open call; both sites live via direct deploy regardless).
5. Optional fast-follow: the "Ask OnePilot" AI-assistant version of the contact button (on-brand Rome demo piece).

---

## Context for Next Session

### Files to Read First
- workspace/clients/brisken/website/onepilot.html (public OnePilot page)
- workspace/clients/brisken/website/treasury.html (brisken.com TreasuryCentral)
- workspace/clients/brisken/website/api/book-demo.js (lead backend the modal posts to)
- ../agentic-dev1/docs/handoffs/onepilot-gravity-well/onepilot-orbit.html (canonical orbit source, untracked)

### Open Questions
- Merge timing of `client/brisken/lead-gen-onepilot` into main (owner's call).
- Should the OnePilot **locator chip** + nav also redirect to onepilot.brisken.com for full consistency, or keep opening the in-page summary? (Currently only the hub node redirects.)
- Dedicated `message` column for the contact form (Neon migration, user-side) vs the current `preferred_date` mapping.

### Working Notes
- **Three diverging copies of the orbit page** now exist: dev1 `onepilot-orbit.html` (canonical, pristine), the ops1 Fly deliverable `brisken-onepilot-platform.html` (+ review annotator), and the public `website/onepilot.html` (+ link repoints + deploy meta + relative API). Edits this session were applied to all three in parallel via `.scratch` transform scripts. This is real maintenance debt — a future build-split or an assemble step would help.
- **Vercel auth:** the CLI here logs in as `akkton` (only akkton's-projects). onepilot.brisken.com lives under `matthias-neumanns-projects` (orgId team_MNNYUo2DofKqKUISX0X01rre, project brisken-onepilot, linked via `.vercel/project.json`). Deploy needs the personal-account token inline: `vercel deploy --prod --cwd workspace/clients/brisken/website --token <T> --yes`.
- **CTA specificity bug:** `.cta-band p` (0,1,1) was overriding `.cta-fine` (0,1,0), so its top margin had always collapsed to 0 (that was the cramping). Fixed by `.cta-band .cta-fine`.
- **OnePilot node redirect** is a one-line special-case in the `.mm-node` click handler (`if(t==='onepilot') window.location.href=...`); `tierBtn('onepilot')` still resolves so the locator/nav/`applyHash` can still open the in-page #onepilot panel.

### Reference Materials
- Vercel project: brisken-onepilot (prj_Avie4cXev9Axx4WfKNAJfob3FEap), scope matthias-neumanns-projects
- Fly app: brisken-onepilot (fra), deploy `flyctl deploy ./ --config fly.onepilot.toml --remote-only --ha=false` from onepilot-site/ after `sync-site.py`
- ntfy topic + Neon leads table per the 2026-06-21 brisken.com launch checkpoint

---

## How to Continue
Both sites are live. To change OnePilot page content: edit the dev1 source + the ops1 deliverable + `website/onepilot.html` in parallel, then deploy to Vercel (token) and Fly (sync + flyctl), and verify the deployed origins. To change brisken.com: edit `website/treasury.html` and `vercel deploy --prod` with the personal token. Remaining items are user-side (vault token, test-lead cleanup) + the hours-tool improvement.

---

## Strategic Feedback

### What Worked Well This Session
- Tight review-round loop: each owner note → parallel edit → deploy → live verify (curl + Playwright) → commit. The live computed-style/Playwright checks caught two issues before they stood (the CTA specificity bug and confirming the node redirect), which is exactly the B2 "verify behavior not config" payoff.
- The user supplying the Vercel token unblocked the launch cleanly after the akkton/personal-scope wall.

### Suggestions
- The three-copy orbit page is the main drag. Worth a small "assemble onepilot page" step (dev1 source → ops1 deliverable with annotator + Fly relative-API, → website copy with link repoints + meta) so a single edit propagates, instead of three parallel `.scratch` transforms per change.

### System Health
- `tools/log-brisken-hours.py` has a structural gap: it doesn't maintain the "By week" buckets, and the control check sums a fixed 3 slots (now full). It will mis-tie on the next new week. Highest-value tool fix.
- Memory-only fixes are fragile: the `~/vault.py`→`$HOME` PowerShell lesson was already in memory (2026-06-21) and still slipped this session — a sign that user-facing-command shell correctness wants a structural check, not just recall.
- Autonomy score: 5 friction events; 1 genuine user intervention (the `~/vault.py` slip), the rest agent/hook self-caught. Slightly elevated — `/system-dev` could close the hours-tool + three-copy gaps.
