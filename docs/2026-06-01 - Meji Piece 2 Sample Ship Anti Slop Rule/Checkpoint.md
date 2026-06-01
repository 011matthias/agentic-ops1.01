# Checkpoint: Meji Piece 2 Sample Ship + Anti Slop Rule

**Date:** 2026-06-01
**Status:** SHIPPED. Piece 2 sample deliverable live at `unpauseai.com/docs/meji-media/corporate-sample` + PDF + cover-message draft ready for Gurmej. Anti AI-slop rule codified after two slop incidents in same week.

---

## Summary

Piece 2 corporate-cold sample (200 unique UK companies across 4 locked ICP segments) shipped end-to-end: Apollo source, gated platform deploy matching existing meji-media design system, Playwright print-to-PDF. Two iterations of wording refinement on the platform page, followed by structural promotion of "anti-AI-slop" discipline from feedback memory to a Layer 2 rule after the same per-category-narration pattern recurred within a week. Also closed loop on the mailbox reauth saga: backend verified all 3 mejievent.com mailboxes flipped active after Workspace OAuth trust fix.

---

## What Was Done This Session

### Mailbox reauth saga closed
- Root cause confirmed: Workspace app-trust restriction (Instantly OAuth Client-ID was configured for 1 Org Unit only). Fixed by extending to entire org via admin.google.com → API Controls.
- Backend verified via `meji_mejievent_mailbox_health_2026-05-26.py`: all 3 mejievent.com mailboxes flipped `status=1`, `timestamp_updated` advanced from 2025-10-19 to 2026-05-30.

### Credentials captured + Apollo audit
- Apollo Master Key, Porkbun API + secret, Workspace temp Super Admin all saved to gitignored `.env`.
- Apollo plan confirmed Basic ($65/mo, 2,500 credits). Seat lightly used (26 contacts, 20 accounts). ICP universe sized at ~91K UK contacts across the 4 segments.

### Pilot routing canonicalized + Layer 1 hook built
- `workspace/clients/meji-media/context/pilot-routing.md` established as single source of truth with the 3-piece routing table.
- `project_meji_pilot_routing.md` memory pointer indexed in MEMORY.md.
- After the same mejievent.com → Piece 1 mistake recurred in a draft 90 min after pilot-routing.md was written, promoted to a hook: `tools/validate-pilot-routing.py` wired into `.claude/hooks/post-write-gate.py` dispatcher. End-to-end verified: fires HIGH advisory on cross-wire pattern, silent on clean drafts.

### Client comms (Gurmej)
- 2026-05-30 22:01 BST outbound: status across 3 pieces + Managing-Director ICP question + Workspace per-user heads-up + 6/+10 hrs transparency block. Sent (user-edited final).
- 2026-05-31 16:24 BST inbound: MD ICP confirmed + Workspace mailboxes greenlit. All open items closed.

### Piece 2 sample sourcing + deliverable
- Apollo `mixed_people/api_search` across 4 ICP segments, free read path, 200 unique UK companies pulled.
- HTML deliverable shipped to `platform/public/docs/meji-media/corporate-sample.html`, matching existing platform design system (volume-forecast template lineage). `Sample` nav link added to all 8 existing meji-media doc pages.
- Gated by existing `MEJI_ACCESS_CODE` env var (`meji2026`). No new gate config needed.
- PDF generated via Playwright print-to-PDF, A4, headed/footed, ~172 KB.

### Page wording iterations
- v1: original sample list (PR #62).
- v2: added rationale block under "The Four ICP Segments" — segment variance, value-weighted split, runway math, what we don't see (PR #63).
- v3: cut per-segment narration on universe variance after user critique (PR #64). Replaced H3 + 4-sentence paragraph with one trailing clause.

### Anti AI-slop standard codified
- `feedback_no_per_category_narration.md` memory written first.
- Then promoted to `.claude/rules/rule_anti_slop.md` after recognizing same pattern triggered two corrections in a week (routing cross-wire + universe-variance narration). PR #65 merged.
- Rule bans: per-category narration on intuitive variance, three-part lists where two work, empty section intros, hedging buffers, corporate thesaurus, performed humanness, em-dashes, headings that re-state body, closing meta-summary.
- Required protocol: information-per-token check, symmetry-collapse check, heading-earns-it check, voice scan.

---

## Key Decisions Made

### Sample-approval gate goes out as URL + PDF + cover message together
- **Choice:** Three artifacts, not just one. URL = interactive, PDF = offline / pass-along, cover message = thread readability.
- **Rationale:** Gurmej's prior pattern shows he sometimes reads on mobile, sometimes scrolls Upwork. Multi-format avoids forcing him through any one path.

### M&M past-customer exclusion at enrich, not sample
- **Choice:** Sample stays as the 200 raw Apollo matches. Exclusion runs at enrich (email-domain cross-ref against `xmas_2020.full_data_parties.leader_email`).
- **Rationale:** UTIL 8974201 modes don't expose arbitrary SQL for company-name cross-ref. Enrich step has email domains, which cross-ref reliably. Sample-approval gate is about "does the shape look right," not "is this an existing customer," so exclusion timing doesn't gate Gurmej review.

### 100/40/30/30 sample split weighted to buyer position
- **Choice:** Not proportional to raw universe (would over-weight MD), not equal across segments. Weighted to where the corporate-Christmas-party buyer actually sits at each company size.
- **Rationale:** PA tier is the booker at mid-market companies (biggest slot, 100). HR is secondary at the same size (40). CEO/MD at small companies ARE the buyer by default but the booking value is smaller, so 30 each.

### Promote anti-slop discipline from memory to rule (two-strike threshold)
- **Choice:** Wrote feedback memory first, then escalated to rule when same pattern recurred within hours.
- **Rationale:** Per Layer 1 self-annealing escalation pattern. Memory failed the recall test ([[feedback_no_per_category_narration]] was 0 minutes old when the next slop instance happened). Same shape as the 2026-05-26 `rule_no_auto_commit.md` memory → rule → hook promotion.

---

## Files Modified

| File | Action | Purpose |
|---|---|---|
| `platform/public/docs/meji-media/corporate-sample.html` | Created | New gated doc page, 200-company sample |
| `platform/public/docs/meji-media/{8 existing pages}` | Modified | Added "Sample" nav link |
| `.claude/rules/rule_anti_slop.md` | Created | Layer 2 voice rule banning AI-slop patterns |
| `.claude/hooks/post-write-gate.py` | Modified | Routes drafts to `validate-pilot-routing.py` |
| `tools/validate-pilot-routing.py` | Created | Cross-wire detection on client draft files |
| `workspace/clients/meji-media/context/pilot-routing.md` | Created | Canonical mailbox/campaign/geography table |
| `workspace/clients/meji-media/context/piece3-mejixmas-setup-plan.md` | Created | End-to-end Piece 3 runbook (mostly executed in parallel Session 1) |
| `workspace/clients/meji-media/context/comms-log.md` | Modified | 4 new internal entries + 2 inbound + 1 outbound + Blocks 13-14 verbatim |
| `workspace/clients/meji-media/context/.env` | Modified | Apollo + Porkbun + Workspace creds + plan info |
| `workspace/clients/meji-media/context/drafts/reply-to-gurmej-2026-05-31-piece2-sample.md` | Created | Cover message draft |
| `workspace/clients/meji-media/context/analysis-scripts/meji_p2_sample_sourcing_2026-05-31.py` | Created | Apollo sampler |
| `workspace/clients/meji-media/context/analysis-scripts/meji_p2_build_platform_page_2026-06-01.py` | Created | Platform-page builder |
| `workspace/clients/meji-media/deliverables/p2-corporate-sample-2026-06-01.pdf` | Created (regen 3x) | Print-to-PDF of the deployed page |
| `memory/project_meji_pilot_routing.md` | Created | Canonical-file pointer |
| `memory/feedback_no_per_category_narration.md` | Created | Slop-pattern feedback memory (now superseded by rule_anti_slop) |
| `memory/MEMORY.md` | Modified | Index entries for both new memories |

PRs merged: #62 (sample page), #63 (rationale block), #64 (tightening), #65 (anti-slop rule). All squash-merged. Vercel auto-deploy + `vercel-force-deploy.sh` after each platform PR.

---

## Current Status

Piece 2 is in the sample-approval gate, waiting for the cover message + PDF + URL to land with Gurmej and for his "go" reply. Piece 3 is on the 3-4 week warmup clock per the parallel session that shipped the mejixmas.com domain end-to-end. Piece 1 is build-prep pending: per-venue enrichment of the 983 leads + campaign-config review against the existing Christmas Bookers campaign.

Platform feasibility for meji: no `platform:` section in `infrastructure.yaml`. Run platform feasibility assessment next time before quoting ops volumes.

---

## Next Steps

1. User sends Gurmej the cover message + PDF + URL (sample-approval gate). Cover at `workspace/clients/meji-media/context/drafts/reply-to-gurmej-2026-05-31-piece2-sample.md`, PDF at `workspace/clients/meji-media/deliverables/p2-corporate-sample-2026-06-01.pdf`, URL `https://unpauseai.com/docs/meji-media/corporate-sample` (code `meji2026`).
2. On Gurmej's "go": enrich the 200 sample companies to ~1,500 verified contacts (cost ~1,500 of 2,500 monthly Apollo credits), apply M&M past-customer exclusion via `xmas_2020.full_data_parties.leader_email` domain match, load into Corporate Events campaign (`245913f7`), activate.
3. Piece 1 build prep: per-venue lookup of the 983 past-attendee leads against `xmas_2020.full_data_parties` + `delegates` via UTIL 8974201; review existing Christmas Bookers campaign (`1f40cb36`) 2-step sequence config; plan the swap-in for Gurmej's 3-touch copy with Touch 1 scheduled early June.
4. Investigate `gurmej.pawar@mejimedia.co` warmup_score=0 before Piece 1 sends (other 2 of 3 Piece 1 mailboxes are at 100).
5. Piece 3 next milestone: day-30 warmup checkpoint (tighten DMARC to `p=quarantine` if aggregate reports clean).
6. Run platform feasibility assessment for meji-media (no `platform:` section in `infrastructure.yaml`).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/pilot-routing.md` (canonical mailbox/campaign/geography routing)
- `workspace/clients/meji-media/context/comms-log.md` (most recent 5 entries cover the Piece 2 sample ship and Gurmej's MD/Workspace greenlight)
- `workspace/clients/meji-media/context/piece3-mejixmas-setup-plan.md` (Piece 3 status, warmup clock, day-30 DMARC tighten note)
- `workspace/clients/meji-media/context/drafts/reply-to-gurmej-2026-05-31-piece2-sample.md` (cover message awaiting send)
- `.claude/rules/rule_anti_slop.md` (Layer 2 voice rule shipped this session)
- `workspace/clients/meji-media/context/p2-sample-2026-05-31.json` (raw 200-company Apollo data)

### Open Questions
- Will Gurmej greenlight the sample with simple "go" or surface specific exclusions / industry-vertical overweights?
- Does `gurmej.pawar@mejimedia.co` warmup_score=0 mean dropped from rotation, paused, or never warmed? Affects Piece 1 sending plan.
- Once Piece 2 launches, when is the right moment to surface the deferred Make → n8n migration proposal (per `[[project_meji_commercial_model]]` trigger: when outbound motion is live)?

### Working Notes
- Apollo `mixed_people/api_search` returns company name + title without credit spend; PII (person name, email, exact employee count) is masked. Enrichment endpoints (`people/match`, `organizations/enrich`) burn credits.
- Apollo `organization.id` is NOT exposed in the free response, so dedup logic uses normalized `organization.name` as the key.
- Workspace OAuth app-trust restriction is the single most likely cause of "OAuth grant accepted but silently revoked" behavior on Workspace-hosted mailboxes. Step zero on any Workspace + cold-tool reconnect runbook: admin.google.com → Security → API Controls → confirm the app is Trusted for the entire organization, not just one OU.
- Apollo Master Key is broadly scoped; if the dropdown shows individual endpoint scopes, the minimum useful set for prospecting is `mixed_people/api_search`, `mixed_companies/search`, `organizations/{search,show,enrich,bulk_enrich}`, `people/{match,bulk_match,show}`, `contacts/search`, `accounts/search`, `reports/sync_report`.

### Reference Materials
- Live URL (gated, `meji2026`): https://unpauseai.com/docs/meji-media/corporate-sample
- Source-of-truth file for pilot routing: `workspace/clients/meji-media/context/pilot-routing.md`
- PRs: #62, #63, #64 (platform), #65 (rule)

---

## How to Continue

`/resume meji-media` will load this checkpoint via the YAML fast-path. The first thing to check is whether Gurmej has replied to the cover message in Upwork: if yes, transcribe verbatim into `comms-log.md` (per `[[feedback_embed_client_screenshots]]`) and execute the enrichment + load step. If no reply yet, start Piece 1 build prep (per-venue enrichment + campaign-config review) since that runs autonomously without any client input.

---

## Strategic Feedback

### What Worked Well This Session
- **Two-strike memory → rule promotion** worked exactly as designed. The first slop incident (routing cross-wire) got a memory + canonical file. When the next incident (universe-variance bloat) happened within a week, the escalation to a Layer 2 rule was automatic, not a debate. Same pattern as the `rule_no_auto_commit.md` lineage.
- **Network outage handled silently.** When Apollo + Porkbun + Instantly all returned `WinError 10051` mid-sample-build, the background TCP-poll auto-resumed the run when connectivity returned. No user re-prompt, no manual retry loop.
- **HTML + PDF dual deliverable strategy.** Gurmej gets the link for interactive review and the PDF for offline / forwarding. The cover message references both. This is now a reusable pattern for any sample-approval-gate deliverable.

### Suggestions
- The local `main` has been diverged from `origin/main` since at least the prior session and across both today's sessions (2 local-only commits never pushed: `ee85a46` rule + `d301b8d` merge). Worth a cleanup pass under user supervision next time the user is sitting in the repo. Suggested: `git reset --hard origin/main` after confirming the 2 commits are either pushed elsewhere or genuinely abandoned.

### System Health
- The `rule_anti_slop.md` standard is now in the canonical rules set but its enforcement is currently agent-discipline only. The natural next step (not built yet) is two additions to `validate-output.py`: a symmetry-collapse detector (N bullets / N paragraphs with similar shape + length → flag) and a per-category-narration detector (N-row lists where each entry's prose follows the same grammar template → flag). Both would be Layer 1 backstops to the Layer 2 rule. Worth building if a third slop incident lands without the rule catching it.

Autonomy score: 2 human interventions this session.
