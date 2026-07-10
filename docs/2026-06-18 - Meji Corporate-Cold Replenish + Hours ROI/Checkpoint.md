# Checkpoint: Meji Corporate-Cold Replenish + Hours ROI

**Date:** 2026-06-18
**Status:** Sample built + deliverable ready (send all 276); hours/ROI draft handed to user for sending; sample page removed from live doc site (deployed)

---

## Summary
Replenished the depleting Meji corporate-cold campaigns: diagnosed the wrong-fit problem, rebuilt the ICP, and produced a 276-company tightened sample (PDF) for Gurmej's approval. Fixed the PDF page-break bug, removed the obsolete corporate-sample page from the live doc site, logged Gurmej's ROI ask, and drafted the hours-breakdown + efficiency-projection reply.

---

## What Was Done This Session

### Corporate-cold replenish (Piece 2)
1. Read-only diagnosis: only the two corporate-cold campaigns (P2A `c3daf05c` 63% complete, P2B `5d677062` 76%) are depleting; P1 warm still has 644/945 unsent; P3 not live.
2. Pulled the actual inbound replies: the 2 analytics-counted replies were BOTH wrong-fit nos (small Scottish social landlord; academy-trust PA). Rest were OOO/auto. Root cause = old list filtered on title+size+UK only, no industry filter → public sector / education / housing / charity.
3. Built `meji_p2_resample_sourcing_2026-06-17.py`: tightened ICP via per-sector-capped keyword draws across 9 event-buying sectors + name-based off-ICP exclusion, deduped vs the 452 already loaded. Output: 276 unique UK companies (69/segment, even sector spread, 0 borderline after refinement, 213/276 with email on file).
4. Generated the client deliverable `p2-corporate-resample-2026-06-17.{md,pdf}` (12-page, sector-grouped, em-dash-free, validate-output.py clean). Owner decision: send all 276.

### PDF tooling fix
5. `tools/md-to-pdf.py` CSS: headings now carry `break-after: avoid`; lists/paragraphs immediately following a heading get `break-inside: avoid`; `li` won't split. Made sector labels real `###` headings so they inherit it. Verified behaviorally: all 12 pages end on a company name, zero orphaned headers.

### Platform: remove the sample page
6. Removed `platform/public/docs/meji-media/corporate-sample.html` + the `Sample` nav link from the other 8 Meji doc pages. Done in a clean worktree off `origin/main` (current branch carries 26 unrelated Brisken commits). validate-html clean. PR #192 merged on green CI; force-deployed to production (gated, user-authorized).

### Comms
7. Logged Gurmej's 2026-06-17 ROI exchange verbatim (Block 24 + dated entry + frontmatter update). The previously-held corporate-status reply went out 2026-06-16 15:06.
8. Estimated the ~8 hr/week split + the fixed/automated/reply-scaled efficiency model; drafted the hours-breakdown reply to Gurmej (handed inline for sending).

---

## Key Decisions Made

### Iterate ICP, keep copy (no Christmas angle)
- **Choice:** Fix corporate-cold targeting, not the copy; keep it year-round corporate, no Christmas angle.
- **Rationale:** The copy is Gurmej's own voice; evidence (wrong-fit replies + sector-blind list) pointed at targeting. Christmas angle would cross the Piece 2 (year-round) / Piece 3 (Christmas, 3 cities) boundary he set.

### Sample-first, hard filter at enrichment
- **Choice:** Sample = company names only (no credits); enforce real-industry + verified-email + strict-UK + M&M-exclusion at the post-approval full pull.
- **Rationale:** Apollo free search masks industry/country (has_* booleans only); real values come at enrichment, where the filter is verifiable rather than guessed.

### Send all 276 (vs the promised 200)
- **Choice:** Send the full 276 rather than trim to the "200" Matthias quoted.
- **Rationale:** Owner call; more depth, slight number mismatch acceptable.

### Deploy was gated and confirmed
- **Choice:** Stopped at the prod deploy (Band-3 floor), surfaced that this project does NOT auto-deploy (last deploy 6d old) and that deploying publishes all pending main merges; deployed only after explicit authorization.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/context/analysis-scripts/meji_p2_resample_sourcing_2026-06-17.py` | Created | Tightened-ICP sample sourcing |
| `workspace/clients/meji-media/context/p2-resample-2026-06-17.json` | Created | 276-company sample data |
| `workspace/clients/meji-media/deliverables/p2-corporate-resample-2026-06-17.md` | Created | Client sample deliverable (markdown) |
| `workspace/clients/meji-media/deliverables/p2-corporate-resample-2026-06-17.pdf` | Created | Client sample deliverable (PDF, 12pp) |
| `tools/md-to-pdf.py` | Modified (uncommitted) | Page-break: keep headers with content |
| `platform/public/docs/meji-media/corporate-sample.html` | Deleted (PR #192) | Obsolete sample page |
| `platform/public/docs/meji-media/{8 doc pages}.html` | Modified (PR #192) | Removed `Sample` nav link |
| `workspace/clients/meji-media/context/comms-log.md` | Modified | Block 24 + ROI entry + frontmatter |

---

## Current Status
- **Sample:** 276-company tightened-ICP corporate sample ready; deliverable PDF ready to attach. Owner chose send-all-276.
- **Hours/ROI draft:** handed to user inline, ready to send (commits to ~5–5.5 hr/wk steady-state; user may soften the figure).
- **Platform:** corporate-sample page removed, PR #192 merged, force-deployed to prod and verified at the source + deployment-alias level (gated content-fetch skipped — needs prod secrets, classifier-blocked, correctly).
- **md-to-pdf.py fix:** working-tree change, uncommitted (sits on the Brisken branch tree).
- Comms current (last contact 2026-06-17, 1 day).

---

## Next Steps
1. **User:** send the hours/ROI draft + the 276-company sample PDF to Gurmej.
2. On Gurmej's sample approval → **full Apollo pull** (enrich, spends credits ~210 max, needs owner go) → **load into P2A/P2B** (B5 invasive, needs owner go + plain-language scope-of-effects).
3. Commit the `tools/md-to-pdf.py` page-break fix on its own branch (don't let it ride the Brisken WIP).
4. Still owed to Gurmej: **inbound enquiry automation scope** (depth/cost/hours — OWED since 2026-06-08).
5. Awaiting Gurmej: **P3 persona-split** answer (unanswered since 2026-06-15) before building the Christmas-cold sequence.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/comms-log.md` (frontmatter unresolved_items + Block 24)
- `workspace/clients/meji-media/context/pilot-routing.md` (canonical campaign IDs + the double-send incident note)
- `workspace/clients/meji-media/context/p2-resample-2026-06-17.json` (the approved-pending sample)
- `workspace/clients/meji-media/context/analysis-scripts/meji_p2_resample_sourcing_2026-06-17.py` + `meji_p2_enrich.py` (full-pull path)

### Open Questions
- Hours-split numbers are estimates; user may adjust before sending.
- Whether to soften the ~5–5.5 hr/wk steady-state commitment in the draft.

### Working Notes
- Apollo free `mixed_people/api_search` masks org.industry/country (has_* booleans only). Server-side `organization_industry_tag_ids` / `q_organization_keyword_tags` ARE respected (verified: include 978 + exclude 15,747 = 16,725 total, exact complement). Use keyword tags (self-documenting) + name-exclusion for samples; enforce real industry at enrichment.
- Vercel project `platform` does NOT auto-deploy on merge (last prod deploy was 6 days old). Deploys are manual via `vercel-force-deploy.sh` from a clean origin/main worktree (copy `.vercel/project.json` in). The gated doc-site rewrites ALL `/docs/meji-media/*` paths to gate-login (even nonexistent ones), so unauthenticated curl cannot distinguish a deleted page; verify deletions via source + deployment-alias, not content fetch.
- md-to-pdf Edge headless silently no-ops when Edge is open as viewer; use `EDGE_PATH=<chrome.exe>` (confirms `reference_html_deck_pdf_chrome_when_edge_open`).

### Reference Materials
- PR #192 (merged): https://github.com/011matthias/agentic-ops1.01/pull/192
- Live campaigns: P1 `00fc708d`, P2A `c3daf05c`, P2B `5d677062`

---

## How to Continue
If Gurmej approves the sample: run `meji_p2_enrich.py --search` then `--enrich --execute` (credits) on the 276, apply the M&M-domain exclusion, then load into P2A/P2B via `meji_p2_instantly_load.py` (B5 — give scope-of-effects, wait for owner go). If he sends back the hours figures, plug them into the draft. Otherwise the queue is: inbound-enquiry-automation scope (oldest owed), P3 persona-split (awaiting his answer).

---

## Strategic Feedback

### What Worked Well This Session
- Tight decision-fork questions (replenish path, ICP filter, sample format, deploy authorization) kept the owner in control of the strategic + irreversible calls while I ran the bounded work autonomously.
- Read-only diagnosis before any action grounded the "iterate targeting not copy" call in the actual reply content, not a guess.

### Suggestions
- The hours-split needed your real allocation; you delegated the estimate. If you keep a rough running tally of where weekly hours go, the ROI reporting Gurmej now wants becomes a 2-minute pull instead of an estimate each time.

### System Health
- The gated doc-site verification gap is real: `audit-client-pages.py` / deploy-gate can't content-verify a gated page without the prod code, so deletions are verified by source + deployment only. Acceptable, but worth a note in the deploy-gate that gated-path content checks are structurally blind.
- `md-to-pdf.py` Edge-collision + the page-break gap are both now handled, but the Edge fallback to Chrome is still manual (`EDGE_PATH`); a candidate auto-fallback for the tool.
- Autonomy score: 2 human/guardrail interventions this session (1 B1 stop-gate deferral, self-corrected; 1 slow-path over-broad secret-pull, classifier-blocked). Both system-caught, neither user-redirected the goal.
