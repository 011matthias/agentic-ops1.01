# Checkpoint: Platform Style Standards Trio

**Date:** 2026-06-01
**Status:** Rules committed (ee85a46); content corrections + email migration applied locally, uncommitted.

---

## Summary
Audited unpauseai.com (platform/) for structural and aesthetic drift,
extracted three Layer-1 standards (platform content, human-to-human
communication, client-page structure), wrote two enforcement tools
(validate-platform-content.py, normalize-client-pages.py), migrated
the canonical public email to admin@unpauseai.com, and applied 276
structural corrections to client pages.

---

## What Was Done This Session

### Rules written (3)
1. `.claude/rules/rule_platform_standards.md` — marketing-site
   content standard. Brand spelling, banned typography, banned
   vocabulary, proposal-markdown canonical shape, IA + CTA copy
   uniformity, visual system, data-accuracy posture. Defers 3
   strategic decisions to owner (overlapping `/services`-`/work`-
   `/automations` pages, header coverage of `/assessment` +
   `/oneproposal`, canonical email — last one resolved by user
   mid-session).
2. `.claude/rules/rule_human_communication.md` — outbound human-
   to-human language standard. Two-register system (soft for
   initial pricing/access, polite-firm for holding under
   pushback), anchor on client words, closing discipline (3
   sanctioned closings, never offers), length ceiling, voice-pass
   checklist, video-script gloss rule, peer-competence test.
   Operationalizes 5 prior feedback memories at Layer 1.
3. `.claude/rules/rule_client_page_structure.md` — client-page
   structure (overseeability, clarity, transparency). Two
   canonical roster families (A: 7-page prospect proposal, B:
   free-form active-client doc), required nav chrome, working
   dark mode requirement, last-updated transparency requirement,
   CSS primitive set, print behavior, 7-question
   "overseeability" test.

### Enforcement tools written (2)
1. `tools/validate-platform-content.py` — enforces
   rule_platform_standards. 6 check classes: em-dashes, brand
   typos, banned vocab, heading drift, email consistency, dead
   JSX links. Severity-banded (HIGH = ship-blocker). Quoted-text
   guard downgrades banned words inside attributed quotations to
   LOW for review.
2. `tools/normalize-client-pages.py` — corrective tool for
   rule_client_page_structure. Idempotent injector: theme boot
   script (was 0/31 working), toggle-onclick wire-up (existing
   `toggleTheme()` callsites preserved), print stylesheet,
   last-updated stamp (optional `--backfill-dates` mode using
   git mtime).

### Content corrections applied
- **Brand typos**: `UnpausAI` → `UnpauseAI` in 2 proposal markdowns
  (sample-crm-automation.md, openwebui-email-compliance.md).
- **Em-dashes**: 3 public JSX pages cleaned (automations,
  buy/[slug], oneproposal — 10 occurrences total). 18 proposal
  markdowns swept by `strip-em-dash.py` (90 ` -- ` substitutes
  → `; `).
- **Heading drift**: 11 proposal markdowns normalized to
  canonical `## Timeline & Milestones` and `## Our Proposed
  Solution`.
- **Banned words in our copy**: `comprehensive technology audit`
  → `full technology audit`; `to ensure data stays in Europe` →
  `so data stays in Europe`.

### Email migration to `admin@unpauseai.com`
- 13 replacements across 8 platform/src files (Footer,
  ProposalCTA, contact, terms, privacy, assessment-thank-you,
  lib/email.ts, api/contact/route.ts)
- 110 + 5 replacements across 66 client/docs HTML+JS files
  (prospect proposals + Wimmer + Meji doc sites)
- `rule_platform_standards.md` §1 updated
- `validate-platform-content.py` SANCTIONED set updated

### Client-page structure corrections
- 241 boot scripts injected (every client page now applies
  stored / system-preferred theme on initial paint — previously
  dead CSS)
- 35 print stylesheets injected (those pages now print without
  nav + sidebar overlay)
- Re-running the normalizer reports 0 fixes needed → corrector
  is idempotent and the first pass touched every page once.

### Commit landed
`ee85a46 rule: add platform / human-comms / client-page
standards + 2 enforcement tools` — 5 files (3 rules + 2 tools),
1492 insertions. Content corrections + email migration stay
uncommitted, awaiting separate ship order.

---

## Key Decisions Made

### Canonical public email = admin@unpauseai.com
- **Choice:** Migrate from `nicolas.neumann@unpauseai.com` (in
  13 surfaces) to `admin@unpauseai.com`.
- **Rationale:** User directive mid-session. Resolves a §1 open
  fork the platform rule had flagged. Touches the entire
  contact-surface set; one Python pass.

### Three rules, not one mega-rule
- **Choice:** Platform content, human-to-human comms, and
  client-page structure each get their own rule file.
- **Rationale:** Distinct scopes (website content vs. messages
  vs. multi-page HTML), distinct enforcement (`validate-
  platform-content.py` vs. `lint-comms-draft.py` vs.
  `normalize-client-pages.py`), distinct strategic decision
  sets. One mega-rule would force every audit to load 3x the
  context.

### Strategic decisions explicitly deferred
- Three: overlapping `/services` / `/work` / `/automations`
  pages, header nav coverage of `/assessment` + `/oneproposal`,
  whether to migrate active-client doc sites from Family A to
  Family B shape. Each documented in its rule's "Strategic
  decisions" section with a recommended direction.
- **Rationale:** Business / editorial decisions, not style
  decisions. Auto-correction would foreclose options.

### Commit scope = rules + their enforcement tools
- **Choice:** Per user "commit these rules", landed
  the 5 source-of-truth files. Content corrections (276 page
  edits + 21 markdown edits + 8 platform/src edits + 66
  HTML/JS edits) stay uncommitted.
- **Rationale:** Per rule_no_auto_commit B6. "Commit" was one
  step, not a chain. Corrections vs. rules-themselves are
  separable concerns deserving separate commits.

### Boot-script injection, not full toggleTheme rewrite
- **Choice:** Inject only the IIFE that applies data-theme on
  initial paint; leave existing `toggleTheme()` callsites
  (50+ files) intact even though they use per-client
  localStorage keys (`menovia-theme`, etc.) instead of the
  shared `theme` key.
- **Rationale:** Existing per-page `toggleTheme()` still works
  for in-session toggling. Persistence-key mismatch is a
  separate cleanup. Full rewrite would have churned 50 files
  with unclear test coverage on each.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/rules/rule_platform_standards.md` | Created (committed) | Marketing-site content standard |
| `.claude/rules/rule_human_communication.md` | Created (committed) | Outbound human-comms language standard |
| `.claude/rules/rule_client_page_structure.md` | Created (committed) | Client-page structural standard |
| `tools/validate-platform-content.py` | Created (committed) | Enforces rule_platform_standards |
| `tools/normalize-client-pages.py` | Created (committed) | Corrective tool for rule_client_page_structure |
| `platform/src/lib/email.ts` | Modified | Default sender admin@unpauseai.com |
| `platform/src/components/Footer.tsx` | Modified | Public contact admin@ |
| `platform/src/components/proposal/ProposalCTA.tsx` | Modified | Email + em-dash cleanup |
| `platform/src/app/(public)/contact/page.tsx` | Modified | Public contact admin@ |
| `platform/src/app/(public)/terms/page.tsx` | Modified | Public contact admin@ |
| `platform/src/app/(public)/privacy/page.tsx` | Modified | Public contact admin@ |
| `platform/src/app/(public)/assessment/thank-you/page.tsx` | Modified | Public contact admin@ |
| `platform/src/app/api/contact/route.ts` | Modified | CONTACT_EMAIL default admin@ |
| `platform/src/app/(public)/automations/page.tsx` | Modified | `&mdash;` → `:` |
| `platform/src/app/(public)/buy/[slug]/page.tsx` | Modified | 2x `&mdash;` → `:` |
| `platform/src/app/(public)/oneproposal/page.tsx` | Modified | 7 em-dash variants → `; ` / `:` / `(...)` |
| `platform/src/content/proposals/*.md` (21 files) | Modified | em-dash sweep + heading normalization + 2 brand typo fixes + 2 banned-word fixes |
| `platform/public/clients/{slug}/*.html` (60+ folders) | Modified | Email migration + boot script + print block |
| `platform/public/docs/{client}/*.html` (Meji + Wimmer) | Modified | Email migration + boot script + print block |
| `docs/2026-06-01 - Platform Style Standards Trio/Checkpoint.md` | Created | This file |
| `docs/sessions/2026-06-01.md` | Updated | Session 2 entry |
| `docs/sessions/2026-06-01-context.yaml` | Updated | Platform section merged |
| `docs/INDEX.md` | Updated | Top of `system` section |
| `docs/friction-register.md` | Updated | 1 row appended |

---

## Current Status
Rules + enforcement tools landed on main (ee85a46). Content
corrections + email migration applied to working tree, awaiting
separate ship order. Validator clean (0 HIGH); TypeScript
clean. Normalizer idempotent — re-run reports 0 fixes.

**Uncommitted local changes (count):**
- 8 platform/src files (email migration + JSX em-dash fixes)
- 21 proposal markdowns (em-dash sweep + headings + typos + banned words)
- 66 client/docs HTML+JS files (email migration)
- 241 client HTML files (boot script + print block)
  — significant overlap with email-touched files above
- This checkpoint folder + the session log / context / INDEX / friction-register updates

---

## Next Steps
1. Decide whether to ship the content corrections + email
   migration in a follow-up commit (single commit
   "content: standardize platform language, structure, email to
   admin@" is the natural shape).
2. Resolve the 2 remaining strategic decisions deferred in
   rule_platform_standards.md §8: overlapping
   `/services`-`/work`-`/automations` pages; header coverage of
   `/assessment` + `/oneproposal`.
3. Optional: run `normalize-client-pages.py --apply
   --backfill-dates` to inject "Last updated:" stamps from git
   mtime into the 21/31 client roots that lack them. Pure
   transparency win; defer if a different per-page date source
   is preferred.
4. Optional: harmonize per-page `toggleTheme()` callsites to
   use the shared `theme` localStorage key. Currently 50+
   pages use per-client keys (`menovia-theme`, etc.). Cosmetic;
   defer until next site-template refresh.

---

## Context for Next Session

### Files to Read First
- `.claude/rules/rule_platform_standards.md` — load the source of truth
- `.claude/rules/rule_human_communication.md` — load before any outbound draft
- `.claude/rules/rule_client_page_structure.md` — load before any client-page edit
- `tools/validate-platform-content.py` — the enforcement script the rule cites
- `tools/normalize-client-pages.py` — the corrector the rule cites
- Recent git log: `ee85a46` (rule commit), `f5347be` (Meji corporate cold sample, prior session)

### Open Questions
- Should the 276-page client structure corrections + 13-file
  email migration ship as ONE commit or split (email migration
  vs structure injection)? Single commit recommended:
  cohesive theme, low blast radius (no API contract changes).
- For the 21/31 client roots without `Last updated:`, is git
  mtime acceptable as the date source, or should the
  user-visible date reflect the last MEANINGFUL edit (manual
  stamp)?

### Working Notes
- Boot-script injection rationale: per-client `toggleTheme()`
  exists on 50+ pages but each uses a different
  localStorage key (`menovia-theme`, `localTheme`). My boot
  script reads the shared `theme` key. They coexist without
  conflict — toggle still works in-session per page; only
  cross-page persistence is local-keyed. Not worth a 50-file
  rewrite now.
- Em-dash replacement convention adopted from existing
  `strip-em-dash.py`: ` — ` and ` -- ` → `; `. For JSX
  literals I varied per context (`:` after label-then-
  description, `;` for semicolon-able prose, `(...)` for
  parenthetical em-dash pairs).
- The two LOW findings remaining in the validator are
  intentional: `leverage` and `robust` inside attributed
  quotations (the ChatGPT example sentence in
  oneproposal/page.tsx, a verbatim-quoted job-posting phrase
  in ai-marketing-make-expert.md). Both keep the source's
  wording on purpose.
- Track-1/2 family proposals (Centerpiece/Track/Compensation/
  Pages/Downloadable artifact/Next steps headings) are
  explicitly exempted from heading-drift checks.

### Reference Materials
- Prior commit: `123a2d8 rule: add no-auto-commit gate (B6)`
  — the rule that gated this session's commit boundary
- Session log: `docs/sessions/2026-06-01.md`
- Existing tools used: `tools/strip-em-dash.py` (for the
  proposal sweep), `tools/wire-hooks.py` (hooks intact),
  `tools/validate-deliverable.py` + `validate-output.py` (the
  post-write-gate dispatcher cited by the new rule)

---

## How to Continue
For the next session:
1. `/resume` will load these new rules at session start (loaded as project rules per the always-on convention).
2. If continuing this work: pick up from the "Uncommitted local changes" listing in Current Status. The natural next move is a single content-correction commit covering email migration + em-dash sweep + heading normalization + boot script injection.
3. If switching back to Meji Piece 3: read `docs/2026-06-01 - Meji Piece 3 mejixmas Domain Setup/Checkpoint.md` from the morning session; the 3-4 week warmup clock is running, no client touchpoint until then.

---

## Strategic Feedback

### What Worked Well This Session
- The user's directive "compile a summary... look for inconsistencies... write a rule... then correct" mapped cleanly to a single multi-step pass: audit → rule → enforcement tool → corrections. Each rule's "Why" section closes the loop by citing the specific audit findings that motivated it.
- Picking up an existing tool (`tools/strip-em-dash.py`) instead of re-implementing the em-dash sweep saved one tool call and matched an established convention (`; ` as the substitution).
- The dry-run-first-then-apply pattern on the new `normalize-client-pages.py` caught the toggle-onclick decision before churning 50 files unnecessarily.

### Suggestions
- The three rules cite each other heavily (`[[rule_platform_standards]]`, `[[rule_client_page_structure]]`, etc.). Consider a brief one-line `## Rule index` at the top of `.claude/rules/INDEX.md` (does this exist?) so the cross-references render reliably in a memory-style graph.
- The `normalize-client-pages.py --backfill-dates` mode is the cheapest single-pass transparency win available (21/31 client roots gain a Last-updated stamp). One short prompt at the right moment unlocks it.

### System Health
- 31/31 client roots ship `[data-theme]` CSS but 0/31 had a working boot script until this session. That's an 8-month-old gap that no one noticed because the visual default (light) is correct and any user with light-mode preference saw no bug. The lesson generalizes: CSS-only "fixes" without their JS counterparts are silently dead, and the validator/audit pattern (count files with X and Y, not just X) is the only way to catch that class. The new `validate-platform-content.py` extends this pattern to em-dashes-vs-mdash, but it doesn't yet check for the broader CSS-vs-JS coexistence class. Worth a follow-up `validate-html-coexistence.py` next time a similar dead-CSS pattern surfaces.

### Autonomy score
Autonomy score: 1 human intervention this session (the
mid-Write tool interrupt that resolved with "continue"). The
stop-b1-gate hook also fired once on a closing-offer pattern
in my draft summary and I rewrote it before the user saw it
(structural catch, no human turn cost).
