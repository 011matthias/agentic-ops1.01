# Checkpoint: Meji Doc-Site Polish

**Date:** 2026-07-20
**Status:** Complete, live on unpauseai.com

---

## Summary
Polished the Meji Media gated doc site (`platform/public/docs/meji-media/`, 9 pages) across three shipped PRs: full-width content, banned `--` cleanup, and the UnpauseAI browser-tab favicon. Continued from the pre-compaction nav-bar unification (#277).

---

## What Was Done This Session
### Layout + content (3 PRs, all merged + force-deployed)
1. **#278 full-width** — removed the `max-width:1200px` cap on `.main` (8 pages) and `.guide-content` (guide) so content fills the width beside the sidebar; the right-side gutter on wide viewports is gone. 24px readable inset kept.
2. **#279 `--` cleanup** — replaced 28 banned `--` em-dash substitutes (6 pages) with context-aware punctuation: colon after a label (`</strong>`, `</code>`, the `AN --` JS titles), comma for mid-clause connectors. Per `rule_deliverables`.
3. **#280 favicon** — added `<link rel="icon" type="image/svg+xml" href="/icon.svg">` to all 9 heads; the pages linked no favicon so browsers showed a generic globe. `/icon.svg` is the canonical UnpauseAI mark the rest of the site already serves.

### Verification
- Headless screenshots at 1440px across every template family (index/build-plan/volume-forecast standard `.main`, guide bespoke `.guide-content`) for the full-width change.
- `validate-html` + `validate-deliverable`: 0 hits on all 9 pages per PR.
- Live `curl` 200 on the meji routes + `/icon.svg` after each force-deploy.

---

## Key Decisions Made
### Left the 111 `&ndash;` entities as-is
- **Choice:** Fixed only the 28 `--`; did not convert the en-dash entities (~all in guide.html).
- **Rationale:** `&ndash;` is not on the `rule_deliverables` ban list (`—`, `&mdash;`, `--`) and the validators pass it. Converting ~100 of them (clause-separators + a numeric range `5–25` + table placeholders) is a judgment-heavy copy rewrite of a live client page, so it was surfaced to the owner as a decision, not done unilaterally. Owner has not yet ruled.

### Favicon by reference, not inline
- **Choice:** `href="/icon.svg"` absolute path rather than an inline data-URI.
- **Rationale:** Keeps one canonical UnpauseAI mark (matches every other unpauseai.com tab), auto-updates if the brand mark changes, and follows the Vercel absolute-static-path rule. `/icon.svg` confirmed live (200).

### Isolated every change in its own worktree
- **Choice:** Each fix built in a fresh worktree off `origin/main`, deployed by copying `platform/.vercel` into the worktree.
- **Rationale:** Two sibling Claude sessions are live on `main` in the shared clone; worktree isolation avoids index/HEAD contention (branch-isolation rule). `.vercel` is gitignored and lives only in the main clone, hence the copy.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `platform/public/docs/meji-media/*.html` (9) | Modified | full-width (`max-width:none`), #278 |
| `platform/public/docs/meji-media/*.html` (6) | Modified | `--` → punctuation, #279 |
| `platform/public/docs/meji-media/*.html` (9) | Modified | favicon `<link>`, #280 |

---

## Current Status
All three PRs merged on green CI (5/5 each), force-deployed to production (`unpauseai.com`), production alias verified over the settle window, live routes 200. Worktrees deregistered and branches deleted (one orphaned dir, `agentic-ops1-mejifw`, left a Windows-locked folder after git deregistered it; cosmetic, clears on reboot).

No `platform` section in meji `infrastructure.yaml` reconciliation needed for this doc-site work (static pages, not Make scenarios).

---

## Next Steps
1. **Owner decision on the en-dashes:** convert the ~111 `&ndash;` in guide.html to punctuation (closer to Gurmej's "no dashes" directive) or leave them (rule-compliant as-is). Not started pending the call.
2. Otherwise nothing owed on the doc site; return to the standing meji forward pipeline (`context/next-outbound-deliverables.md`): RAD-01 bounce attribution, RAD-02 unsub-integrity, DMARC step 2 on mejixmas.com (~07-23), August multi-inbox build.

---

## Context for Next Session
### Files to Read First
- `platform/public/docs/meji-media/guide.html` (the en-dash decision lives here)
- `workspace/clients/meji-media/context/next-outbound-deliverables.md` (the real forward pipeline)

### Open Questions
- Convert guide.html en-dashes, or leave them? (owner call)

### Working Notes
- Full-width fix: root cause was `.main { max-width:1200px; margin:0 }` inside `.page-layout { margin-left: 200px sidebar }`; on viewports > ~1400px this left an empty right gutter. Fix = `max-width:none`. guide uses `.guide-content` not `.main`.
- Dash counts (Python, reliable): 0 real `—`/`&mdash;`; 28 `--`; 111 `&ndash;` (103 in guide). NOTE: literal-char grep misses HTML entities; count `&ndash;`/`&mdash;` as strings.
- Deploy pattern that works from a worktree: `cp -r <main>/platform/.vercel <wt>/platform/.vercel` then `tools/vercel-force-deploy.sh --dir <wt>/platform --domain unpauseai.com`. `.vercel` is gitignored, absent in worktrees.
- Gated pages return 200 serving the gate to unauth `curl`; can't verify page body content without the grant cookie, so verification is: source has the change + `/icon.svg` 200 + route 200 + alias verified.

### Reference Materials
- PRs: #278 (full-width), #279 (dashes), #280 (favicon), #277 (nav, pre-compaction)
- Live: https://unpauseai.com/docs/meji-media/

---

## How to Continue
The doc site is done and live. If the owner wants the guide en-dashes converted, that's the one open task; otherwise pick up the meji outbound pipeline. Ledger for this session ships via a `docs/...` PR (branch-isolation §1).

---

## Strategic Feedback

### What Worked Well This Session
- Tight visual-fix loop: headless-Edge screenshots gave direct before/after confirmation for the full-width change without needing the browser MCP (which was down).

### Suggestions
- The three doc-site fixes (nav, width, dashes, favicon) each shipped as a separate PR + deploy over two sessions. When several small polish items on the same page-set are known, batching them into one PR would save four force-deploy cycles. Worth a quick "any other polish on these pages?" sweep before the first deploy next time.

### System Health
- `tools/validate-html.py` and `validate-deliverable.py` do NOT flag `--` or `&ndash;` even though `rule_deliverables` bans `--` in client HTML. The em-dash strip gate only fires on Write/Edit tool calls, so script-written edits (like this session's) bypass it. Gap: no static check catches `--` in already-committed client HTML. Candidate: add a `--`/em-dash scan to `validate-deliverable.py` so CI catches it regardless of how the file was written.
- Autonomy score: 0 human interventions this session. One B1 deferral (offering the dash pass instead of acting) was caught structurally by the stop-b1-gate hook, not by the user; the hook held.
