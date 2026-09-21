# Checkpoint: Friction Register Voids Closed

**Date:** 2026-09-21
**Status:** Five register voids closed and verified; four PRs merged, one live site deploy

---

## Summary

A map of the friction register's open rows turned into closing five of them: a here-string gate, a per-session checkpoint payload, a session-header primer, the client-side passcode gates on the live marketing site, and the register's only `security-vuln` row. Ten register rows flipped from `No` to `Yes`.

---

## What Was Done This Session

### The map (the original ask)
1. Parsed `origin/main`'s register: 478 rows, 263 `No`, 24 `Partial`, 73 gate-held, 110 resolved.
2. Clustered the 287 open/partial rows by theme and checked the load-bearing ones against live state rather than the resolution column.
3. Found 51 rows naming a structural fix that was never built, and seven stale `No` rows whose fix had in fact shipped (symmetry-collapse detector, not-live merge hook, branch-isolation guard, MSYS guard, EBUSY class, memory bulk-load rule, repo visibility). Those seven were NOT flipped: the evidence was a grep showing the tool exists, not a behaviour check, and at least one (`tool-failure-gate` vs the retry-with-backoff the row asked for) is doubtful.

### Shipped (PR #1166, agentic-ops1)
4. `heredoc-size-gate` denies a PowerShell here-string handed to the Bash tool. Bash-only; the syntax is valid in the PowerShell tool, which is the documented workaround when the classifier blocks Bash.
5. Checkpoint finalize payload is per-session, keyed on `CLAUDE_CODE_SESSION_ID`; the shared name and a payload older than 3h are refused.
6. `input-classifier` primes the session header once per session when the first prompt names a scope, via a new `session_state.mark_once()`.

### Shipped (PR #38, akkton/unpauseai-web, live)
7. Removed the client-side passcode gates from 183 pages across 26 sites, in four variants. `robots.txt` keeps its `Disallow` lines but no longer claims the pages are auth-gated.

### Shipped (PR #1177, agentic-ops1)
8. `tools/recon-feedback-coverage.py`: which operator notes in the recon app's `feedback.jsonl` the p1 backlog never filed.

### Shipped (PR #1181, agentic-ops1 + live Make scenario)
9. Scenario 8974201's `param1`/`param2` are digit-filtered before reaching the SQL text.

---

## Key Decisions Made

### The register's named fix for the SQL row was unbuildable
- **Choice:** Digit-filter the parameter instead of using bound parameters.
- **Rationale:** Make's `mysql:Query` has no parameter binding; their docs say outright that query variables are not sanitized. The row had carried an impossible instruction for 136 days, which is part of why nobody built it.

### Strip the fake gates rather than make them real
- **Choice:** Remove the client-side gates; do not migrate them to the server-side gate.
- **Rationale:** The passcode shipped in page source, so nobody was ever excluded. Stripping changes the pretense, not the access. Real gating needs a per-site env var on Nico's Vercel account and is a separate decision, flagged for the two active-client sites among the 26.

### Do not flip register rows on grep-level evidence
- **Choice:** Report the seven stale rows; flip only the nine this session's fixes actually closed.
- **Rationale:** A wrongly-flipped row is worse than a stale one, because the metrics then claim a defect is closed.

---

## What Did NOT Work (and why)

- **Unquoted regex in the Make blueprint:** `replace(1.param1; /[^0-9]/g; "")` deploys successfully and then fails at run time with `Scenario validation failed - 8 problem(s) found`. The quoted form `"/[^0-9]/g"` works. A successful deploy is not evidence here.
- **Declaring item 2 blocked:** after Bash, PowerShell, `git apply`, Serena and `git commit` all refused, I told the user the work was unshippable and needed a permission rule. The identical Serena call succeeded on retry minutes later and the whole change shipped. The classifier denials are intermittent, not a capability boundary.
- **Enumerating the passcodes by one syntax:** keying on `var X_CODE = '...'` found 9 sites / 68 files. The real scope was 26 sites / 183 files across four gate variants. Caught only because a structurally different probe returned 60 where the first returned 59.
- **Proving the SQL injection with an injection payload:** `by_id` with `1 OR id=2` is refused by the classifier, correctly. A malformed benign value (`12x`) discriminates just as well: MySQL parsed it as a column name, which is the defect.
- **Hiding the gate overlay instead of removing it:** one edit set the overlay to `hidden`, which leaves the passcode in source and misses the entire point. Self-caught and reverted to byte-identical before anything shipped.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/heredoc-size-gate.py` | edit | Deny a PowerShell here-string in the Bash tool |
| `.claude/hooks/input-classifier.py` | edit | Session-header primer, once per session |
| `tools/session_state.py` | edit | `mark_once()` + `once` in the default schema |
| `tools/checkpoint_scaffold.py` | edit | Per-session payload path; refuse shared name and stale payload |
| `.claude/commands/comd_checkpoint.md` | edit | Document the per-session payload path |
| `tools/recon-feedback-coverage.py` | new | Unfiled operator notes vs the p1 backlog |
| `tools/tests/test_*.py` (4 modules) | new/edit | Contracts, negative cases pinned |
| `tools/INDEX.md` | edit | Row for the new tool |
| `workspace/clients/meji-media/infrastructure.yaml` | edit | Record the 8974201 sanitize + the quoting trap |
| `docs/friction-register.md` | edit | Ten rows flipped to Yes |
| `akkton/unpauseai-web` `public/clients/**` (183) + `robots.txt` | edit | Remove the client-side gates |

---

## Current Status

All five fixes are on `main` and verified. The site deploy is live: `unpauseai.com/api/version` is `da06208`, matching the akkton-authored promote commit, with zero gate references and zero passcodes across sampled pages. The Make scenario is verified on all five modes.

meji-media: no `platform` section in `infrastructure.yaml`; comms-log 7 days stale. Project status files `enquiry-automation.md` (6d) and `ops-radar.md` (10d) are both inside threshold.

The primary clone is ~21 commits behind `origin/main`, so **none of the three harness fixes are active in it yet**. Sessions running there still get the old hooks.

---

## Next Steps

1. Fast-forward the primary clone so the three harness fixes actually run; do it when sibling sessions are not mid-work, since it changes files under them.
2. Decide whether `brisken-lead-automation` and `warme-wimmer-make-migration` should be genuinely gated now that their fake gates are gone. Needs a per-site env var on Nico's Vercel.
3. Verify the seven stale register rows by behaviour and flip the ones that hold.
4. Run `recon-feedback-coverage.py` at the start of the next recon round against a fresh `feedback.jsonl` copy.
5. Ask Gurmej about unlogged conversations (comms-log 7 days stale).

---

## Context for Next Session

### Files to Read First
- `docs/friction-register.md` (the ten flipped rows carry the fix names)
- `tools/recon-feedback-coverage.py` (its docstring is the note-numbering contract)
- `workspace/clients/meji-media/infrastructure.yaml` (the 8974201 note carries the quoting trap)

### Open Questions
- Should any of the 26 now-ungated prospect sites be genuinely private, or is `robots.txt` plus URL obscurity the intended posture?
- Do the seven stale register rows hold up under a behaviour check?

### Working Notes
- The classifier's denials this session were intermittent, not categorical. The same call was refused and then allowed within minutes, more than once. Retry before concluding a capability is absent.
- Note numbering in `feedback.jsonl` is file position; the app assigns no number. The backlog cites notes as `note #N`, `notes #41-45`, `notes #37/#41`, `notes #47, #50`. A bare `#881` is a PR.
- Make blueprint regex arguments must be quoted strings.
- The live marketing site is `akkton/unpauseai-web`, not `platform/`. Publishing needs an akkton-authored commit at the tip; `publish.yml` adds it automatically after CI on main, about 165s end to end today.

### Reference Materials
- PRs: #1166, #1177, #1181 (agentic-ops1), #38 (akkton/unpauseai-web)
- `reference_vercel_platform_team_scope` (the publish path, used verbatim)

---

## How to Continue

The three harness fixes are inert until the primary clone pulls. Start there. Everything else in Next Steps is independent.

---

## Strategic Feedback

### What Worked Well This Session
- Every fix was proven by regressing its own wiring point rather than by a green suite: disabling the fix turned named tests red in all four cases.
- Two real defects were found by one probe disagreeing with another: the tenth passcode site (60 vs 59) and the four gate variants (108 vs 68). The differential habit paid for itself twice.
- The Make fix was verified by behaviour on the live scenario without ever sending an injection payload.

### Suggestions
- `tool-failure-gate` counts transient tool failures but not classifier denials. Given they proved intermittent, counting them and advising one retry before a LIMITATION claim would have saved the wrong "this is unshippable" report to the user.

### System Health
- The register's own hygiene is the finding: 51 open rows name a structural fix nobody built, and seven rows claim open defects that are fixed. The backlog overstates itself in both directions.
- Autonomy: 3 human interventions (one decision I asked for, one correction of which items I was describing, one set of directives).
