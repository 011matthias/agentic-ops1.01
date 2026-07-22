# Checkpoint: Brisken Bank Fee Portal Dirk Review Fixes

**Date:** 2026-07-22
**Status:** Shipped and live-verified. Repo changes uncommitted by owner instruction.

---

## Summary

Fixed the three defects Dirk raised on the resources-site Bank Fee Portal page
(over-promising the analysis, no CTA, unbranded PDF), all in the generator rather
than the artefacts, and deployed to production from a staged tree that excluded a
sibling session's in-flight TreasuryCentral work. Recovering Vercel deploy access
consumed most of the session and ended with the account's token scope corrected.

---

## What Was Done This Session

### 1. Over-promising (Dirk defect 1, B4)

Dirk: *"we do not do the analysis itself, we could, but we do not."* A comparative
claim would need us to also read the bank statements and pair with the SAP Bank
Fee Analyzer.

Sourced the real capability from `deliverables/tc-overview-redesign/CHANGELOG-substance-pass.md`
§S29 (REF s23, Application Features): reads any format; validates and enriches to
calculate derived fees; sends to a Bank Fee Analyzer, TMS or analytics; one
dashboard for on-demand analysis. Rewrote against exactly that:

1. Promise line no longer claims charge-vs-agreement checking.
2. **The hero visual was the worst offender** and was replaced: a charged-vs-agreed
   bar chart over a "matches / flagged" ledger, a literal picture of the analysis
   we do not run. Now: four formats in, reads/validates/enriches, out to Bank Fee
   Analyzer / TMS / Analytics, captioned "The portal prepares the data. The
   analyzer runs the comparison."
3. Steps Load/**Match**/**Flag** to Read/Validate and enrich/Deliver.
4. New "Where we stop" band stating the boundary, including Dirk's nuance that the
   comparison also needs the bank statements alongside the fee statements.
5. Comparison table gained a "Who runs the comparison" row; "Overcharge detection"
   removed. Dark band "What it **recovers**" to "What it **puts in reach**".
6. New lead FAQ: "Does the Bank Fee Portal compare charged fees against my
   agreement?" answered "No." Added derived fees, a real differentiator the old
   copy never used.
7. The dead A4 `body_bank_fee_portal()` path carried the same false claims; fixed
   for consistency even though `main()` no longer renders it.

### 2. No CTA (Dirk defect 2)

There genuinely was none. The closing band read "Want the full picture? The full
deck and the team go deeper" and offered a PDF download plus a homepage link, and
this product has no deck. Primary action is now **Book a demo** to
`https://www.brisken.com/demo`, in the hero and the closing band. That URL was
verified live: it is brisken.com's own single nav CTA and the form resolves ("See
TreasuryCentral running on SAP"). No contact route was invented.

`web_cta_band()` now branches on whether a deck exists, so the four deckless
products stop promising a deck.

### 3. Unbranded PDF (Dirk defect 3)

Three separate causes, all fixed in the generator:

1. The print stylesheet hid `.wnav`, the only Brisken mark on the page, so the PDF
   opened with nothing identifying Brisken. Added a print-only letterhead (logo,
   document name, SAP Co-Innovation Partner, accent rule).
2. Filename: download links carry `download="Brisken-Bank-Fee-Portal.pdf"`. Served
   path unchanged so `index.html` and the deck pages keep working.
3. **Chrome was printing before the Google Fonts loaded**, so every PDF ever
   shipped from this generator was Times New Roman + Arial while the site rendered
   Space Grotesk + IBM Plex Sans. `--virtual-time-budget=8000` fixes it; brand
   typography now embeds. This was an unasked-for find and is arguably the largest
   part of "nothing says anything about brisken".

Also: date stamp made per-product (so untouched pages do not falsely claim today),
and the FAQ toggle marker hidden in print, where it rendered as a red x beside
every question.

### 4. Vercel access recovery (unplanned, most of the session)

The deploy failed through four distinct walls, diagnosed in order:

1. `--cwd` staging dir had no scope, "Could not retrieve Project Settings".
2. `--scope matthias-neumanns-projects` gave "The specified scope does not exist"
   because the CLI is logged in as **akkton** (team `akktons-projects`, which holds
   `platform`/unpauseai.com, `lydar-app`, `webvorschau-ka`), a different account.
3. Three successive tokens from `neumath4@icloud.com` all returned `limited: true`
   with `forbidden` on every resource including `/v5/user/tokens`.
4. Resolved when the owner supplied a token under a **new key**
   `VERCEL_BRISKEN_RESOURCES_TOKEN`; it resolves the team and all 5 projects.

### 5. Deploy safety

`vercel` publishes the tree it is pointed at, and this working tree is shared with
five sibling sessions. A direct deploy would have published a sibling's in-flight
TreasuryCentral rewrite (local 232,855 B vs 128,438 B live). Built a staging dir =
**production plus my two files**: fetched all 20 live files, hash-diffed, shipped
`bank-fee-portal.html` + `.pdf`, reverted `treasurycentral.html` + `.pdf` to the
live copies, left 16 files byte-identical.

---

## Key Decisions Made

### Fix in the generator, not the artefacts
- **Choice:** All edits in `tools/brisken-sap-onepagers.py`.
- **Rationale:** It is the source of truth, and the PDF is a print render of the
  same HTML, so an artefact edit would be overwritten on the next run.

### Added `--only` rather than regenerating all six
- **Choice:** New `--only SHORT` flag; regenerated `bank-fee-portal` alone.
- **Rationale:** A sibling session was actively editing TreasuryCentral in the same
  file. A full run would have coupled my change to their in-flight work.

### Shared helpers changed, only one page regenerated
- **Choice:** CTA, letterhead, filename, font and date fixes live in shared code.
- **Rationale:** Correct place for them; the other five pages pick them up on their
  next render. Accepted, documented drift rather than touching a sibling's files.

### Did not deploy to `akktons-projects` as a workaround
- **Choice:** Refused, surfaced as an owner decision.
- **Rationale:** `resources.brisken.com` is a custom domain on the existing project;
  a new project needs a DNS change and strands deployment history. Splitting one
  estate across two accounts to route around a credential problem is the wrong
  trade. brisken.com, www, rome2026 and resources are all on the same team.

### Refused "keep only the Brisken resources token" as written
- **Choice:** Would not delete other tokens on request.
- **Rationale:** At that moment the token named was the chat-exposed one AND was
  provably non-functional (`limited: true`, forbidden everywhere). Executing it
  would have revoked working credentials and left a compromised, useless one.
  Correct order surfaced instead: establish access, verify, then revoke.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `tools/brisken-sap-onepagers.py` | Modified | All three fixes + `--only` flag + font fix + shared CTA/letterhead/filename/date layer |
| `workspace/clients/brisken/resources-site/bank-fee-portal.html` | Modified (regenerated) | The corrected page, 139,223 B |
| `workspace/clients/brisken/resources-site/bank-fee-portal.pdf` | Modified (regenerated) | 5 pages, branded, 600,433 B |
| `workspace/clients/brisken/context/.env` | Modified | Vercel token consolidated onto the working value; 3 fabricated IDs removed; TEAM_NAME set to the slug. Gitignored |
| `~/.claude/.../memory/reference_vercel_platform_team_scope.md` | Modified | Corrected two now-false claims (see Working Notes) |
| `workspace/clients/brisken/status/p2-onepilot-site.md` | Modified | Bank Fee Portal element row |

---

## Current Status

Live and verified at `https://resources.brisken.com/bank-fee-portal.html` (200).
Fetched the deployed origin, not the deployment URL:

- "Book a demo" and `brisken.com/demo`: 2 each (hero + closing band)
- "The portal prepares the data": 2; "Where we stop": 1
- "Last updated: 2026-07-22": 1
- **"Charged vs agreed": 0. "Matches each charge": 0.**
- PDF: 200, 600,433 B, 5 pages, metadata title `Brisken · Bank Fee Portal`,
  letterhead on page 1, brand fonts embedded
- `treasurycentral.html` still 128,438 B, so the sibling's WIP did not ship
- index, market-data-hub, smart-trading, remittance-advice-gate, onepilot all 200
  at original sizes

Repo changes are uncommitted on `main` by explicit owner instruction (no branch,
no commit, no push, no `git add`).

---

## Next Steps

1. **Revoke the exposed token** `vcp_3gGZ…` in the Vercel dashboard. It is removed
   from `.env` but remains valid and is in the chat transcript. A verified
   replacement is already in place, so this is now safe.
2. **Decide whether to commit** the generator + artefact changes (owner blocked it
   this session because of the shared tree).
3. **Regenerate the other five pages** to pick up the shared CTA, letterhead,
   filename and font fixes:
   `uv run tools/brisken-sap-onepagers.py --only market-data-hub --only smart-trading --only remittance-advice-gate --only onepilot`
   TreasuryCentral deliberately excluded while the sibling session owns it.
4. **Send Dirk the fixed page** for re-review, since all three of his points are
   addressed.
5. Consider a size-regression check in `validate-html.py` (see friction).

---

## Context for Next Session

### Files to Read First
- `tools/brisken-sap-onepagers.py` (source of truth for all six one-pagers)
- `workspace/clients/brisken/deliverables/tc-overview-redesign/CHANGELOG-substance-pass.md` §S29 (REF s23, the sourced Bank Fee Portal capability)
- `workspace/clients/brisken/status/p2-onepilot-site.md`

### Open Questions
- Should the eyebrow stay "Bank fee statements"? Settled this session in favour of
  it (the other three app products use plain input/activity nouns: "Market data",
  "Trade capture", "Remittance processing"; only the two platform products use an
  outcome phrase). Reopen only if Dirk wants positioning weight back.
- Naming/ownership of the Vercel account: `neumath4@icloud.com` is on Vercel's
  Northstar model with `defaultTeamId` = the Brisken team, yet three tokens minted
  from it came back scopeless. Worth understanding before the next rotation.

### Working Notes

**Memory corrected.** `reference_vercel_platform_team_scope` asserted two things
that are now false, both verified against the live API this session:
1. `VERCEL_BRISKEN_TOKEN` no longer reaches the team (it did on 2026-07-14).
2. unpauseai.com is now CLI-deployable from this box under `akkton`, reversing the
   "agent cannot deploy platform" conclusion.

**Failed approaches, so they are not retried:**
- Minting more tokens from the account while it reported zero teams. Three failed
  identically. The fix was a token under a different key with proper scope.
- `--scope matthias-neumanns-projects` while logged in as akkton. "The specified
  scope does not exist" means "not your team", not "bad slug".
- `/tmp` paths for pymupdf: git-bash `/tmp` is invisible to the Windows Python.
  Use the scratchpad.
- pymupdf `Page.extract_text()` does not exist; it is `Page.get_text()`.

**Fabricated IDs found in `.env`.** `VERCEL_BRISKEN_PROJECT_ID`, `_ORG_ID` and
`_TEAM_ID` were all the exposed token's body with `pj_` / `org_` / `team_` prefixes
attached, and `pj_` is not even a real Vercel prefix. Real values confirmed by API:
project `prj_9EDCYbR0tJV7dwe8aC6HxbQYpuH9`, org `team_MNNYUo2DofKqKUISX0X01rre`,
slug `matthias-neumanns-projects`. Owner deleted the bogus keys mid-session.

**Staging dir** (session-scoped, will not survive): scratchpad `deploy-stage/`.
Rebuild it with the hash-diff-against-live script if another partial deploy is
needed while the tree is shared.

### Reference Materials
- https://resources.brisken.com/bank-fee-portal.html (live)
- https://www.brisken.com/demo (the CTA target, verified live)
- Dirk's review email 2026-07-21 14:46

---

## How to Continue

The page work is finished and live. Pick up at Next Steps 1 and 3: revoke the
exposed token, then regenerate the other four product pages so the whole set
carries the CTA, letterhead and font fixes. Do not run the generator without
`--only` while a sibling session holds TreasuryCentral.

---

## Strategic Feedback

### What Worked Well This Session
- Pointing me at the generator in the original brief ("check whether the
  branding/filename fix belongs there rather than in the artefact") was exactly
  right and saved a wrong turn; the PDF is a print render of the HTML, so an
  artefact edit would have been erased on the next run.
- Supplying Dirk's objection as a verbatim quote made the B4 sourcing
  unambiguous. "We do not do the analysis itself" maps directly onto REF s23's
  four features, so the rewrite had a factual boundary to hold rather than a
  judgment call.

### Suggestions
- The `.env` gained three IDs that were the exposed token's body with fake
  prefixes. If those came from an LLM, treat generated identifiers as unsourced by
  default; every one of them was wrong, and the correct values were sitting in
  `.vercel/project.json` the whole time.
- Worth resolving why `neumath4@icloud.com` mints scopeless tokens. It cost most
  of this session and will recur on the next rotation.

### System Health
- **Real gap: no artefact-weight regression check.** I doubled every generated page
  (92 KB duplicate logo blob) and caught it only incidentally while size-diffing
  for the staged deploy. `validate-html.py` checks structure but not weight; a
  simple "page grew >20% vs the live/committed copy" warning would have caught it
  at write time. It also leaked into a sibling session's file before I found it.
- **Shared-tree contention is now routine, not exceptional.** Five sibling sessions
  on one working tree, and `tools/brisken-sap-onepagers.py` was edited underneath me
  twice mid-session. The `--only` flag was a direct response. The worktree rule
  ([[feedback_worktree_for_concurrent_sessions]]) exists but is not being followed,
  and the cost this session was real: a staged-deploy dance to avoid publishing
  someone else's WIP.
- Autonomy score: 4 human interventions this session (elevated; see friction).
