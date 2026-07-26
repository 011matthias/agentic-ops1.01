# Checkpoint: Platform Deploy Reframe + Health-Pass Round 3

**Date:** 2026-07-25
**Status:** unpauseai.com deploy blocker resolved at the root (wrong target, not missing creds); stranded content ported as a green PR awaiting Nico's go-live.

---

## Summary

A multi-day attempt to get Vercel credentials so this machine could deploy `agentic-ops1/platform` was chasing the wrong target the whole time: the website was split out of the monorepo into its own repo `akkton/unpauseai-web` (2026-07-25), and production is deliberately Nicolas's `vercel --prod` step. The GitHub collab invite from akkton was the tell; acting on it, the three stranded AEO blog posts were ported into the new repo as a CI-green PR, and the tooling + memory were corrected so this dead end cannot recur.

---

## What Was Done This Session

### The reframe (the load-bearing finding)
1. `akkton/unpauseai-web` is a private standalone repo, default branch `main`, actively pushed (commit "stand this up as the standalone website repo", 2026-07-25). Its `docs/publishing.md` (Nico's) is authoritative: merging `main` does NOT deploy; going live is his `vercel --prod`; contributors preview on their OWN free Vercel account (zero production access). Matthias was never meant to have production access — which is why every token/seat/login path dead-ended.
2. Live production 404s on the three AEO posts and matches unpauseai-web's content, not the monorepo's — strong evidence our week of `platform/` PRs never reached the live site.
3. `agentic-ops` keeps only a narrow role now: it generates some static gated doc-site pages (`public/docs/warme-wimmer/`) into a sibling checkout of unpauseai-web.

### Delivered
1. **PR #1 on `akkton/unpauseai-web`** (`content/port-aeo-blog-posts`) — ported the 3 stranded posts (cold-email-no-replies-diagnostic, make-contractor-left-takeover, spf-dkim-dmarc-cold-email-minimum) verbatim from `agentic-ops1` origin/main. `blog.ts` auto-discovers `*.md`, added `domainkey` to cspell. Full CI green in the clean env (type-check/lint/build, spell, Playwright); build generates all 3 as `/blog/<slug>` routes. Not merged — Nico's review + go-live.
2. **PR #400** — `tools/vercel-as.sh`: per-identity `--global-config` auth stores so akkton and matthias logins coexist (the wrapper approach, before the reframe made production-deploy moot for Matthias).
3. **PR #401** — `tools/vercel-as.ps1`: the PowerShell twin (the `.sh` is unusable here — PATH `bash` is the WSL stub).
4. **PR #402** — fixed the red `main` that #401 caused (the ps1 test suite was pwsh-gated, but ubuntu CI ships pwsh; re-gated on `os.name=='nt'`).
5. **PR #403 (OPEN, owner review)** — narrows the no-auto-commit gate: a non-green `gh pr merge` now needs an order that NAMES the override ("merge anyway"), not any generic ship word.

### Health-pass round 3 (already checkpointed in ledgers #381/#393/#397, merged this session)
PRs #374 (brisken-outreach-reconcile), #380/#389 (validator blind-spot fixes), #383 (git-stash gate), #391/#394 (optimize verify follow-ups). The optimize-audit adversarial verify (21 stale / 11 confirmed / 0 refuted) and the S1 fixture re-validation (unblocked; later shipped by sibling sessions #404-#418) are in those ledgers + the S1 memory.

---

## Key Decisions Made

### Port scope: posts only, not the whole AEO sprint
- **Choice:** PR #1 carries the 3 blog posts, not the #376 `sitemap.ts` blog enumeration or `llms.txt`.
- **Rationale:** posts are self-contained (auto-discovered, own routes); the SEO wiring is entangled with how Nico structures the new site. Flagged in the PR as a separate port if wanted.

### No preview project in Matthias's personal Vercel account
- **Choice:** skipped the `vercel` preview deploy.
- **Rationale:** render already proven three ways (local `next build` generated all 3 routes, clean-env CI build, identical template already serving 3 live posts); a preview would leave a standing project for near-zero added proof.

### PR #1 and #403 left unmerged
- **Choice:** stop at PR-open on both.
- **Rationale:** #1 is Nico's repo and his go-live step; #403 changes gate semantics and the owner interrupted the merge for review.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `akkton/unpauseai-web:src/content/blog/{3 posts}.md` | Create | Port stranded AEO posts (PR #1) |
| `akkton/unpauseai-web:cspell.config.json` | Edit | Whitelist `domainkey` (DKIM selector) |
| `tools/vercel-as.sh` + `tools/tests/test_vercel_as.py` | Create | Multi-account wrapper (PR #400) |
| `tools/vercel-as.ps1` + `tools/tests/test_vercel_as_ps1.py` | Create | PowerShell twin + CI-gate fix (PR #401/#402) |
| `tools/vercel-force-deploy.sh` | Edit | `--identity`/`VFD_IDENTITY` routing |
| `.claude/hooks/no-auto-commit-gate.py` + rule + test + fixture | Edit | Red-merge needs named override (PR #403, open) |
| `~/.claude/.../memory/reference_vercel_platform_team_scope.md` + `MEMORY.md` | Edit | Record the site-moved architecture change |

---

## Current Status

unpauseai.com is served from `akkton/unpauseai-web`, not this monorepo. The stranded content is a green PR (#1) awaiting Nico. 011matthias has WRITE on that repo. `main` on `agentic-ops1` is green. No client `infrastructure.yaml`/comms in scope (system session).

---

## Next Steps

1. **Owner (Nico):** review + merge unpauseai-web PR #1, then `vercel --prod` to take the 3 posts live. Confirm via a `/blog/<slug>` fetch (currently 404).
2. **Owner (Matthias):** decide on `agentic-ops1` PR #403 (red-merge gate narrowing) — approve or adjust; it changes gate semantics.
3. Decide whether the #376 AEO `sitemap.ts`/`llms.txt` pieces also get ported to unpauseai-web (separate PR).
4. Decide whether any other stranded `platform/` work (e.g. the #337 client-page theme-toggle heals) needs porting to unpauseai-web, or is retired with the monorepo platform.
5. Register archive: run `archive-register` in this checkpoint's docs PR (register is 412 KB, >200 KB advisory).

---

## Context for Next Session

### Files to Read First
- `akkton/unpauseai-web:docs/publishing.md` — the authoritative deploy/preview workflow
- `reference_vercel_platform_team_scope.md` (memory) — the corrected architecture note
- This checkpoint

### Open Questions
- Do the #376 AEO sitemap/llms pieces belong in unpauseai-web, or does Nico have his own SEO setup?
- Is any non-blog `platform/` work from this week worth re-landing in unpauseai-web, or is it all retired?

### Working Notes
- The website split happened 2026-07-25 02:31; the invite + `publishing.md`'s "preview from your own Vercel account, not from ours" are Nico explicitly designing the Matthias-collaboration workflow. Production access was never the ask.
- unpauseai-web CI = tsc/eslint/`npm run build`/cspell (`src/**/*.{tsx,ts,md}`)/Playwright chromium. cspell has its own dictionary — new technical terms in content need whitelisting there, not in agentic-ops1's config.
- The `vercel-as` wrapper (#400/#401) still has real value for Matthias's OWN-account previews and the Brisken deploys, even though production-deploy of unpauseai.com is off the table for him.

### Reference Materials
- unpauseai-web PR #1: https://github.com/akkton/unpauseai-web/pull/1
- agentic-ops1 PR #403 (open): red-merge gate narrowing

---

## How to Continue

The deploy thread is Nico's to close (merge PR #1 + `vercel --prod`). On the agentic-ops1 side, the only open item is owner review of PR #403. Everything else is landed and green.

---

## Strategic Feedback

### What Worked Well This Session
- The invite reframed the whole problem, and following it (verify the repo, read `publishing.md`, port + prove) beat continuing to force a credential path. The port was proven against the target repo's own CI before pushing, so PR #1 was green first try.
- The red-merge incident became a structural fix (#403) instead of just a "be careful" note.

### Suggestions
- Before acquiring access to deploy/modify an external system, verify what that system actually IS (which repo/project/branch serves it) — a B7 enumeration of the target, not just the capability. Days were spent on `agentic-ops1/platform` without ever confirming the Vercel project's git connection.

### System Health
- **Autonomy: 4 human interventions (elevated — run /system-dev to close gaps).** The user supplied the invite (the unlock), rejected one blocking merge call, and corrected two unrunnable shell commands. The command failures trace to a standing memory (`feedback_user_commands_powershell_syntax`) that did not hold — a candidate for a structural guard on agent-authored user-facing commands.
