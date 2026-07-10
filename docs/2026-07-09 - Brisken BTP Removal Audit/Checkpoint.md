# Checkpoint: Brisken BTP Removal Audit

**Date:** 2026-07-09
**Status:** Repo and one subdomain clean and verified. Three client-reachable artifacts still carry BTP, all held pending owner authorization.

---

## Summary

Ran Dirk's standing Planner directive ("leave SAP BTP out of all demo materials") to ground truth across decks, demos, and every brisken.com subdomain, verifying against live origins rather than the repo. Cleaned the six SAP one-pagers at their generator, the OnePilot prototype source, and the Rome 2026 collateral; scoped the banned-content gate to the owner's decision and fixed two bugs in it.

---

## What Was Done This Session

### Audit (live, not repo)
1. Enumerated brisken.com DNS via the GoDaddy API: 14 reachable subdomains, 8 Lovable, 5 Vercel.
2. Scanned every live origin for `BTP` and `Business Technology Platform`, following same-host PDF links. Found 11 hits in 6 PDFs on `resources.brisken.com` and 2 on `rome2026.brisken.com`.
3. Verified `demo.brisken.com` and `sap-ai-brief.brisken.com` are dangling DNS: TLS handshake fails, HTTP returns 409, nothing served.
4. Read-only SharePoint verification via CDP: downloaded and text-extracted both TreasuryCentral decks.

### Fixes
1. `.scratch/brisken-sap-assets/gen_onepagers.py`: removed BTP from the shared TRUST strip and from four places in the OnePilot page (eyebrow, architecture target node, codeless-framework bullet, caps chip). Substitutes lifted verbatim from sibling one-pagers ("on your SAP data", "delivered as SaaS"), so no new claim was introduced.
2. Rebuilt all six one-pagers, synced into `resources-site/`, confirmed 1 page each.
3. Stripped the BTP meta description from the four identical OnePilot prototype copies.
4. Rome 2026: removed the `Runs on: SAP BTP` hero row, the `Built on SAP BTP` trust chip, and the `Runs on SAP BTP as SaaS` sentence from landing + hub; dropped `· on SAP BTP` from the onepager markdown; removed the badge from the print HTML and re-rendered the PDF with Chrome headless, checked visually.
5. `tools/validate-demo-material.py` + `tools/fixtures/demo-banned-terms.json`: scoped exemptions to the owner's decision; fixed two bugs (unreadable files bypassed `is_exempt` entirely; `pypdf` had no `cryptography` dep so an AES-encrypted contract failed as `<unreadable>`). Committed as `1c64d7a`.

### Verification
- Gate exits 0 across `workspace/clients/brisken`, exits 1 on planted `SAP BTP` and `Business Technology Platform`, skips the encrypted contract.
- `pytest tools/tests`: 179 passed.
- `validate-html.py` on 4 edited files: exit 0; span/div tags balanced.
- 23 shipped PDFs: all readable, 0 hits.
- `resources.brisken.com`: 0 hits, cache-busted against the origin.

---

## Key Decisions Made

### Scope of the directive: demos + subdomains only
- **Choice:** Owner chose to leave BTP in place in AEO/QA outreach pages, LinkedIn repositioning copy, SAP PartnerFinder/Store copy, and internal analysis docs. Exempted each in the gate with a written reason.
- **Rationale:** Dirk's directive names demo material. The SAP-surface copy is written for SAP's own directory, where "built on SAP BTP" is a partner credential rather than a demo claim. Several internal docs exist to analyse the BTP positioning; one literally asks Dirk "Keep stating it on the site, or drop it?" Stripping the term would make them incoherent.

### Do not commit anything beyond the two tool files
- **Choice:** Committed only `tools/validate-demo-material.py` and `tools/fixtures/demo-banned-terms.json`.
- **Rationale:** `brisken-rome-2026-hub.html` and most other touched files carry uncommitted edits from a parallel session (DECK SLOTS changes, a mid-flight `deliverables/` reorg, `app.py` +301 lines). Committing them would sweep up unverified work.

### Hold the push
- **Choice:** `1c64d7a` was committed locally and deliberately not pushed.
- **Rationale:** The branch was 6 ahead of origin; pushing publishes 5 commits from the stopped session onto open PR #201, which under the repo's CI-gated auto-merge could land them on main. The Band-1 verification precondition fails for commits I did not verify.
- **OVERTAKEN BY EVENTS (re-verified 2026-07-10):** the branch is now level with origin and `1c64d7a` is contained in `origin/client/brisken/lead-gen-onepilot`. A later session pushed it, carrying the 5 unverified commits with it. The hold no longer exists; what remains is to check whether PR #201's CI went green and what landed.

### Hold the proto deploy
- **Choice:** Prototype source is fixed; the Fly app is not redeployed.
- **Rationale:** `onepilot-site/app.py` carries +301 uncommitted lines from the stopped session. `flyctl deploy` from this tree ships that unreviewed code alongside a one-line meta fix.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `tools/validate-demo-material.py` | Modified | `cryptography` dep; unreadable files now respect a wildcard exemption |
| `tools/fixtures/demo-banned-terms.json` | Modified | Scoped exemptions (context/, specs/, blueprints, AEO, LinkedIn, SAP surfaces) with reasons |
| `.scratch/brisken-sap-assets/gen_onepagers.py` | Modified | Source of the 6 one-pagers; 5 BTP sites removed. **Gitignored, so unversioned** |
| `deliverables/lead-generation/sap-assets/*.pdf` (6) | Regenerated | BTP-free one-pagers |
| `resources-site/*.pdf` (6) | Replaced | Payload for resources.brisken.com |
| `onepilot-site/site/index.html` | Modified | Prototype meta description |
| `onepilot-site/site/brisken-onepilot-website-prototype.html` | Modified | Same, identical copy |
| `deliverables/brisken-onepilot-website-prototype.html` | Modified | Same, identical copy |
| `deliverables/lead-generation/onepilot/brisken-onepilot-website-prototype.html` | Modified | Same, identical copy |
| `deliverables/lead-generation/rome-2026/brisken-rome-2026-landing.html` | Modified | Hero row, trust chip, trust sentence |
| `deliverables/lead-generation/rome-2026/brisken-rome-2026-hub.html` | Modified | Hero row, trust chip |
| `deliverables/lead-generation/rome-2026/brisken-rome-2026-onepager.md` | Modified | Credentials line |
| `deliverables/lead-generation/rome-2026/brisken-rome-2026-onepager.pdf` | Regenerated | BTP-free, 1 page, visually checked |
| `.scratch/brisken-rome-2026-onepager-print.html` | Modified | Removed the `Runs on SAP BTP` badge |

---

## Current Status

Platform: brisken `infrastructure.yaml` declares `tier: "unknown"` (custom SaaS build, not a workflow-engine op count), so no ops budget applies.

**Clean and verified:** `resources.brisken.com` (7 PDFs, 0 hits, cache-busted), `onepilot.brisken.com`, `www` and 6 other subdomains, `rome-2026/decks`, `dirk-send-pack`, `call-collateral`, both SharePoint TreasuryCentral decks, the MDH demo film source in `~/Repo/video-gen`.

**Still carries BTP, all held for the owner:**
1. `rome2026.brisken.com` — one credentials-strip span plus the hosted `brisken-rome-2026-onepager.pdf`. Lovable, in Brisken's account; no API or git path.
2. SharePoint `2026_VIDEO/calvin-clip-16x9-1080p.mp4` and `calvin-clip-1x1-1080.mp4` — end card. Uploaded 19:06 CEST; commit `df8eab0` removed BTP at 21:17, so the bytes Dirk was emailed at 20:41 predate the fix. Clean render sits on PR #207, unmerged.
3. `brisken-onepilot-proto.fly.dev` — the NAME-gated demo share link still serves the old meta description. Source fixed, image not rebuilt.

Session 10's note that Dirk holds two BTP-carrying TreasuryCentral decks is **stale**: both were replaced at 18:25 today and verified clean by download.

---

## HELD ACTIONS (require an explicit owner go)

Every item below was deliberately **not executed**. Each is either an irreversible deploy, a write into a live client system, or a push carrying work I did not verify. Status re-verified 2026-07-10.

### H1. Push of `1c64d7a` — RESOLVED, but not by me
- **Was held because:** the branch sat 6 ahead of origin; pushing publishes 5 commits from the stopped parallel session onto open PR #201, which under CI-gated auto-merge could land them on main.
- **Current state:** `git branch -r --contains 1c64d7a` returns `origin/client/brisken/lead-gen-onepilot`; branch is 0 ahead, 0 behind. **A later session pushed it**, carrying the 5 unverified commits with it.
- **What remains:** check PR #201's CI result and what actually landed. The hold is gone; the exposure it guarded against was realised by another session.

### H2. rome2026.brisken.com — STILL OPEN
- **Blast radius:** a live brisken.com subdomain a prospect can open. Lovable-hosted in **Brisken's** account; no API, no git path, no CI. Manual editor change plus a re-publish.
- **Verified still dirty 2026-07-10:** 1 hit in the page, 1 hit in the hosted `/brisken-rome-2026-onepager.pdf` (235,702 B, i.e. the pre-fix render; our rebuilt one is 145,421 B).
- **Exact change:** delete the `<span>SAP BTP</span>` and one `<span>·</span>` from `div.brk-creds` (before/after in Working Notes). Then replace the hosted PDF with `deliverables/lead-generation/rome-2026/brisken-rome-2026-onepager.pdf`.
- **Why not done:** driving a no-code editor in a live client site is a state-changing action in a system I cannot verify against. Owner chose the paste-ready route.

### H3. Calvin clip on SharePoint — STILL OPEN
- **Blast radius:** overwrites two MP4s in Brisken's tenant that Dirk was emailed a link to at 20:41. Overwrite is not cleanly reversible; he may have the files open. No email would be sent.
- **Verified still dirty 2026-07-10:** `2026_VIDEO/calvin-clip-16x9-1080p.mp4` = 2,389,847 B and `calvin-clip-1x1-1080.mp4` = 2,019,329 B, both `TimeLastModified 2026-07-09T17:06Z`. The BTP-free re-renders are 2,387,289 B and 2,016,429 B. Different bytes, so the tenant holds the pre-fix cut.
- **Proof it is the pre-fix build:** upload 17:06Z (19:06 CEST) predates commit `df8eab0` (21:17) which removed BTP from the end card.
- **Depends on:** PR #207 (`leadgen/task-6`, OPEN, MERGEABLE) carries the clean render.
- **Owner decision so far:** "verify live state first, then report." Verification done; the overwrite itself is a separate authorisation.

### H4. Redeploy of `brisken-onepilot-proto` — STILL OPEN AND BLOCKED
- **Blast radius:** `flyctl deploy` is a gated-floor deploy of the NAME-gated demo app Dirk shares.
- **Verified still dirty 2026-07-10:** the deployed page still serves `no-code platform on SAP BTP`. The 4 source copies are fixed; the Fly app serves a built image.
- **Blocked by:** `onepilot-site/app.py` carries **+300 uncommitted lines** from the stopped session. Deploying from this tree ships that unreviewed code alongside a one-line meta fix.
- **Unblock path:** review or revert `app.py` first, then deploy, then re-verify by `POST /welcome` with any name (read-only: the gate only sets a signed cookie and persists nothing) and `GET /`.

---

## Next Steps

1. **H1 fallout:** `1c64d7a` is already on origin. Check PR #201's CI and confirm what the 5 pushed commits landed.
2. **H2:** apply the rome2026 Lovable edit and swap the hosted onepager PDF.
3. **H3:** decide on replacing the two Calvin clip cuts on SharePoint, and whether to merge PR #207 first.
4. **H4:** review or revert `app.py`, then redeploy `brisken-onepilot-proto`.
5. Move `gen_onepagers.py` out of gitignored `.scratch/` into `tools/` (or accept the gate as the only backstop).
6. Wire `validate-demo-material.py` into `post-write-gate.py` for `deliverables/**` and `resources-site/**`. It is a tool, not a gate, and that is the failure mode that produced three BTP leaks on 2026-07-09.

---

## Context for Next Session

### Files to Read First
- `tools/fixtures/demo-banned-terms.json` — the directive and every exemption reason
- `tools/validate-demo-material.py` — the gate; run it before any deck/demo/subdomain deploy
- `.scratch/brisken-sap-assets/gen_onepagers.py` — the one-pager source of truth, unversioned
- `docs/sessions/2026-07-09.md` — Sessions 10 and 11 record the two prior BTP leaks

### Open Questions
- Who has edit access to Brisken's Lovable account for `rome2026.brisken.com`?
- Should `gen_onepagers.py` be promoted to `tools/`, given the BTP fix currently lives only in a gitignored directory?
- Does Dirk want the two dangling subdomains (`demo`, `sap-ai-brief`) removed from DNS or provisioned?

### Working Notes

**Paste-ready rome2026 fix.** The live page has exactly one BTP occurrence:

```html
<!-- BEFORE -->
<div class="brk-creds brk-mono">
  <span>SAP Co-Innovation Partner</span><span>·</span><span>SAP Store</span><span>·</span><span>SAP BTP</span><span>·</span><span>ISO 27001</span><span>·</span><span>SOC 1 Type II</span>
</div>
<!-- AFTER: delete the SAP BTP span and one separator -->
<div class="brk-creds brk-mono">
  <span>SAP Co-Innovation Partner</span><span>·</span><span>SAP Store</span><span>·</span><span>ISO 27001</span><span>·</span><span>SOC 1 Type II</span>
</div>
```

Then replace the hosted `/brisken-rome-2026-onepager.pdf` with the rebuilt local file.

**Concurrency incident.** A parallel session was committing to the same branch and working tree throughout. It ran a Vercel deploy at roughly 21:39 that published the PDFs this session had rebuilt three minutes earlier. The live result is correct and verified, but it reached production through an uncontrolled deploy. Detected by an unexplained `digital-co-worker.pdf` appearing mid-session and `index.html` changing mtime; confirmed by `git log` timestamps.

**Deployed proto verification method.** The welcome gate only sets a signed cookie (`sign_name`) and persists nothing server-side, so passing it is read-only. `POST /welcome` with any name, then `GET /` reveals the served HTML. This is how the stale meta description was found.

**Byte-identity is the reliable SharePoint check.** REST `Length` comes back as a string (cast it). Comparing SharePoint bytes and sha256 against the local pre-fix and post-fix renders proves which build the tenant holds, without needing ffmpeg or OCR.

**pypdf false positives.** Plain `grep BTP` matches base64 blobs (`...RUBTPmGyy...`). The gate's `\bBTP\b` does not. Do not hand-grep; run the gate.

### Reference Materials
- `https://resources.brisken.com/` — Vercel project `resources-site`, deployed from the local working tree, not from git
- `https://rome2026.brisken.com/` — Lovable, `185.158.133.1`
- `https://brisken-onepilot-proto.fly.dev/` — NAME-gated prototype demo
- SharePoint: `/sites/MARKETING/Shared Documents/20_Assets/BRISKEN PRESENTATIONS/OnePilot - Cloud Solutions Presentations/{2026_PPTX,2026_VIDEO}`
- PR #201 (open, this branch), PR #207 (open, clean Calvin clip)

---

## How to Continue

Run `uv run tools/validate-demo-material.py --client brisken --dir workspace/clients/brisken` first; it should exit 0. A green gate proves the repo is clean and proves nothing about the live surfaces.

Then work the **HELD ACTIONS** section above (H1 to H4). H1 has already been overtaken (the branch was pushed by another session). H2, H3 and H4 are all still open and each needs an explicit owner go, because each is either an irreversible deploy or a write into a live client system. Do not treat a repo-side fix as done until the origin that serves it has been re-fetched and scanned; that mistake is exactly what H4 records.

---

## Strategic Feedback

### What Worked Well This Session
- Stopping the parallel session the moment it surfaced. Two agents writing one working tree produced a production deploy nobody ordered; killing it immediately kept the damage to "the right bytes shipped by the wrong path".
- Answering the scope question with a real carve-out (keep BTP on SAP's own surfaces) rather than a blanket strip. That distinction is the difference between honouring the directive and deleting a partner credential from SAP's directory.

### Suggestions
- The one-pager generator lives in gitignored `.scratch/`. Its BTP fix is one `rm -rf .scratch` from being lost, and the next regeneration from an older copy silently reintroduces the term. Promote it to `tools/` with a row in `tools/INDEX.md`.

### System Health
- `validate-demo-material.py` is a tool, not a gate. It is not wired into `post-write-gate.py` or CI, so it only fires when an agent remembers to run it. That is the same failure mode that produced three BTP leaks on 2026-07-09. Wiring it into the PostToolUse dispatcher for `workspace/clients/*/deliverables/**` and `resources-site/**` would close the loop.
- Autonomy score: 1 human intervention this session.
