# Checkpoint: Warme Wimmer Doc Site — UX Revamp + Server-Side Auth + Open Feedback

**Date:** 2026-05-07 (retroactive — covers the 2026-05-06 evening session that crashed twice on `API Error 400: messages.422.content.3.image.source.base64: image cannot be empty`)
**Status:** PRs #108, #112, #113, #114 all merged + deployed to https://unpauseai.com/docs/warme-wimmer/. Auth gate now server-side; passcode rotated; live data is gated. PR #115 (vestigial `middleware.ts` removal) shipped incidentally to unblock Next.js 16 builds.

---

## Summary

Three back-to-back ship cycles on the Wärme Wimmer doc site over 2026-05-06 evening:

1. **Full UX revamp** — 5 new pages (Start hier persona landing, Runbook, FAQ, Glossary, Contacts), Cmd+K search, persona cards, page-intro callouts, per-scenario Quick-Fix block, R-00 callout-intro restructure, dashboard error inline-expand, Outlook trend KPI
2. **Auth migration** — client-side JS gate (`wimmer2026` in plain JS, viewable via view-source) replaced with Next.js middleware + HMAC-SHA256 cookie + rotated passcode in Vercel env
3. **Two follow-up auth fixes** — middleware logic moved into `proxy.ts` (single-file convention); bare `/docs/warme-wimmer` (no trailing slash) coverage; env var whitespace trim

Closed with two un-actioned feedback items the next session needs to handle: em-dash overuse + lockdown, and an unscoped "lots of UI improvement work" remark.

---

## What Was Done

### PR #108 — Doc-site full UX revamp

Build script (`tools/build-warme-wimmer-doc-site.py`):
- Shell refactor: extracted `render_shell()`, `render_auth_gate()`, `render_header()`, `render_footer()`. ~100 lines of duplicated chrome collapsed to one source.
- Header health badge driven by live `make_status` (green/amber/grey based on `n_active`/`n_total`)
- "Tag N nach Go-Live" computed from `GO_LIVE_DATE = 2026-04-28`
- Footer "Letzter Build: {ts} · Live-Daten: {fetched_at}" on every page
- S-* pages: when `MAKE_TOKEN` missing, status card shows `unavailable-note` instead of silently omitting
- CSS: defined `--grey` / `--grey-light` (were undefined → grey badges invisible); added print stylesheet, Cmd+K search modal, mobile breakpoints, persona-cards, scenario-meta rows, error-list, callout, CDN-fail banner
- `render_scenario_status_card`: 3 new rows — Make-UI link (+ History deep-link), Owner / Eskalation, Runbook link — plus a "Letzte Fehler/Warnungen" details block when any non-OK runs exist
- `fetch_make_status`: collects `recent_errors` (timestamp + status code + type, last 5 non-OK runs) per scenario
- `render_dashboard_table` "Letzte 50" cell becomes a `<details>` with timestamps + Make-History deep-link when there are errors; inline status-code legend below the table
- `render_dashboard_kpis` Outlook KPI now shows trend: `+0.53 GB seit 2026-05-03 · ~45 Tage bis 60% bei 177 MB/Tag`
- 2-pass build: pass 1 scans headings; pass 2 injects `WIMMER_SEARCH_INDEX` (503 entries) for Cmd+K modal
- `validate_anchors` writes broken-anchor build report to `.build-report.txt`. Current build: 2 pre-existing umlaut issues on `s-00` (markdown lib drops `ü`, source links use full umlauts — logged, unfixed)
- New `PAGE_META` entries: `0-Start-Hier.md`, `R-runbook.md`, `R-faq.md`, `R-glossary.md`, `R-contacts.md`
- New sidebar group "Orientierung" placed first

Content-restructure script (`tools/notion-restructure-v18.py`):
- `FIREFLIES_BY_ANCHOR` constant: 2 known URLs populated (`m-04-21`, `m-04-24`); 8 placeholders for backfill
- `render_meeting_section`: H2 emits `{#m-04-XX}` attr-list (fixes 10 broken chronology + decision-log links). Notes-dropdown strips YAML frontmatter + H1, uses `<details markdown="1">` so inner markdown is processed (fixes the unreadable-text-wall bug)
- `render_start_here_page`: full rewrite as 4 persona cards (Sabine / Raphael / Auditor / 03:00-Eskalation) with target-page deep links
- `PAGE_INTROS` + `inject_page_intro`: every R-* and M-* page opens with a "Was ist das? / Wann brauchst du das?" callout
- `QUICK_FIX_BY_SCENARIO` + `inject_quick_fix`: per-scenario "Wenn das Szenario kippt" block (3 numbered steps + runbook link) injected on each S-XX page
- `restructure_r00_audit_to_bottom` + `fix_r00_intro_callout`: R-00 opens with the callout; the dense "Evidence-Verifikation 2026-04-15" block moves to a bottom `<details>`
- `build_pages` loads new `doc-site/*.md` and maps to `R-runbook.md`, `R-glossary.md`, `R-faq.md`, `R-contacts.md`

New content sources (under `workspace/clients/warme-wimmer/context/doc-site/`):
- `glossary.md` — 18 terms (Sammelbearbeiter, Wimmer-Assistent, Sabine-Sicht/Audit-Sicht, GoBD, Mailgun-Rewrite, etc.)
- `runbook.md` — 8 incident decision trees with anchored links from per-scenario Quick-Fix blocks
- `contacts.md` — role/escalation matrix with channel + verfügbarkeit per person
- `faq.md` — top 10 questions from M-04-24 / M-04-17

`.gitignore`: ignore `platform/public/docs/warme-wimmer/.build-report.txt` (per-build artifact)

### Mid-session conversation (between #108 and #112)

The user pivoted from celebrating the revamp ship to asking strategic questions. Three exchanges, captured because the answers shape future work:

- **Question A — Reassess auth?** Yes. `wimmer2026` is in plain JS; view-source defeats it. The actual leak risk is moderate (Hero-IDs/connection-IDs aren't usable without separate auth) but the contract risk ("we said this is private") is real now that the site is referenced in client comms. Recommendation: cheapest meaningful fix is server-side server-enforced gate.
- **Question B — Move doc site / whole platform to Lovable + agent-backend pattern (like /oneproposal)?** Mixed answer. Doc site **no**: the hard part is the live-data wiring (Make REST + status.yaml + anchor validation + search index), not the chrome — Lovable would split data layer from visual layer and add a re-prompt step to every content change. Whole platform **worth piloting on ONE new proposal first**: marketing pages and net-new Track-2 proposal sites are exactly where Lovable shines. Validator pipeline (`tools/validate-proposal.py` 40+ checks) is the constraint to design around. Pilot path: pick the next prospect, build their Track-2 site through Lovable, port the validator hooks, compare quality + time-to-deliver.
- **Question C — Vercel password swap requires Pro plan?** Yes ($20/user/mo); on Hobby it's only available for preview deploys. Free alternative: Next.js middleware password gate (~30 lines), same security model, full control, gives a base for OAuth + allowlist later. Recommended that path.
- **Confirmation — "the login stays the same right?"** Yes — same passcode initially, same look; change is purely under the hood (server validates instead of JS).

### PR #112 — Server-side password gate

Plan written to `~/.claude/plans/waerme-wimmer-so-what-i-wise-newell.md` (separate file from the revamp plan); approved; implemented:

- New `platform/src/lib/wimmer-auth.ts`:
  - `WIMMER_COOKIE = "wimmer-auth"`, `WIMMER_PATH_PREFIX = "/docs/warme-wimmer/"`, `COOKIE_MAX_AGE_S = 30 days`
  - `expectedCookie(secret)` returns `HMAC-SHA256(secret, "granted-v1")` hex
  - `cookieMatches(value, secret)` constant-time compare via `timingSafeEqual`
  - `validateFromUrl(s)` open-redirect guard — only accepts URLs starting with `/docs/warme-wimmer/`
- New `platform/src/middleware.ts`:
  - Case-insensitive 308 redirect (preserved logic from old `proxy.ts`)
  - Cookie check on `/docs/warme-wimmer/:path*` matcher
  - Mismatch → `NextResponse.rewrite("/wimmer-login?from=" + encoded current path)`
- New `platform/src/app/(public)/wimmer-login/page.tsx`:
  - Server-rendered login form, visually identical to the old client-side gate (same logo SVG, gradient, padding)
  - Reads `?from=…&err=…` query params; renders "Falscher Code" message when `err=1`
- New `platform/src/app/api/wimmer-unlock/route.ts`:
  - POST handler, validates passcode against `WIMMER_ACCESS_CODE` env var
  - Sets cookie: `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, `Max-Age=2592000`
  - 302 redirect back to validated `from` URL (defaulting to `/docs/warme-wimmer/`)
- `tools/build-warme-wimmer-doc-site.py`:
  - Removed `ACCESS_CODE = "wimmer2026"` constant (was line 40)
  - Removed `WIMMER_CODE`, `checkAuth()`, and the IIFE that hides `#auth-gate` from `AUTH_THEME_JS`
  - Deleted `render_auth_gate()` function and removed call from `render_shell()`
  - Removed `<div id="auth-gate">…</div>` from every generated page
  - Passcode no longer ships in HTML
- `platform/src/proxy.ts` — kept (has `/admin` and `/portal` matchers that were never wired); marked DEAD CODE in a 1-line comment so the next reader doesn't get confused
- Vercel env: added `WIMMER_ACCESS_CODE` (rotated to a new value, NOT `wimmer2026`) and `WIMMER_AUTH_SECRET` (32-byte random hex) to production + preview environments. Communicated new code to Irina + Raphael over WhatsApp.

### PR #113 — Middleware logic moved into proxy.ts

The separate `platform/src/middleware.ts` introduced by PR #112 was folded into `platform/src/proxy.ts`. Rationale (inferred from commit title): Next.js framework conventions wanted the gate inside the existing proxy.ts entry point, not a parallel file. Net effect: same logic, single file, no behavioral change.

### PR #114 — Bare path coverage + env var trim

Two small bugs surfaced after #113 deployed:
- Bare `/docs/warme-wimmer` (no trailing slash) bypassed the `:path*` matcher → fixed by including both `/docs/warme-wimmer` and `/docs/warme-wimmer/:path*` in the matcher
- Trailing whitespace in Vercel env vars caused HMAC mismatch on first request after deploy → trimmed values via `.trim()` at read time

### PR #115 — Vestigial middleware.ts removal (Next.js 16 build fix)

Incidental: leftover empty `middleware.ts` from the #112→#113 file move blocked Next.js 16 production builds. Removed. Not WW-specific; platform-wide concern.

### PR #116 — `/oneproposal` CTA swap (UNRELATED — different project, mention only)

`unpauseai.com/oneproposal` is the public marketing landing for the **OneProposal product**; its CTAs now point to `app.unpauseai.com`. **`app.unpauseai.com` is a separate project entirely and has zero connection to the Wärme Wimmer doc site, WW auth, WW data, or any other client-facing work.** Listed here only because the commit landed on the same evening as the WW work. Do not conflate the two — `unpauseai.com/docs/warme-wimmer/` (client doc site, this checkpoint's subject) and `app.unpauseai.com` (separate product) live in parallel and should never be cross-referenced as if they share infrastructure.

---

## Key Decisions Made

- **Skip local dev verification, ship #108 straight to live** — user judgement call after a 404-on-trailing-slash confused the local preview. Quote: "I bet that it's not broken to such an extent where we can't have it live."
- **Free middleware approach over Vercel Pro** — same security model, no $20/mo bill, full control. Plan-able toward future OAuth allowlist if user count grows.
- **Rotate the passcode** — `wimmer2026` had been in plaintext JS since the doc-site launched; anyone who view-sourced has it. New code set in Vercel env, communicated to Irina + Raphael over WhatsApp.
- **HMAC cookie, not random token** — middleware verifies statelessly without DB/KV. Rotating either env var invalidates all sessions.
- **Doc site stays in this codebase, not Lovable** — the value is in the live-data wiring, not the chrome.
- **`FIREFLIES_BY_ANCHOR` lives in code constant**, not YAML override — single source, zero override complexity. Backfill is one constant edit.
- **S-04 third mermaid kept** — intentional Phase-2 SOLL architecture (`## 3. Ziel-Architektur`), not a leftover.
- **`.build-report.txt` is gitignored** — per-build artifact.

---

## Friction Events

- `live-without-local-verify` — shipped #108 without confirming UI works locally; user explicit "save me trouble" decision (not a process violation; risk acknowledged in the moment)
- `chat-crashed-on-image-base64` — Anthropic API 400 `invalid_request_error` twice in a row mid-session; lost the screenshots and any final implementation steps after the auth migration
- `middleware-pattern-pivot` — separate `middleware.ts` (#112) had to fold into `proxy.ts` (#113) one PR later. Lesson: Next.js middleware conventions wanted single-file pattern; verify framework expectations before designing two-file split
- `bare-path-bypass` — the `:path*` matcher didn't catch the bare `/docs/warme-wimmer` route; gate was bypassable for the window between #112 and #114 deploy. Lesson: include both `/prefix` and `/prefix/:path*` in matchers
- 2 pre-existing umlaut anchor mismatches on `s-00` — markdown lib drops `ü`, source links use full umlauts; logged in build report, unfixed

---

## Open Items From the Crash

### 1. Em-dash audit + lockdown (high priority, structural)

User feedback verbatim:
> "we're overusing m dashes. We shouldn't be using a single m dash anywhere except as a so-called em dash. Also, double dash as a replacement for the m dash is stupid. That should not be in place very much. Get that locked down and fix that."

Current state:
- ~290 em-dashes across 24 shipped HTML files (verified by grep)
- ~165 em-dashes in source MDs
- Hundreds of ` -- ` occurrences (mix of legitimate code flags inside fenced blocks + em-dash substitutes in prose)

Existing tooling:
- `tools/voice-check.py:93-95` already detects ` — ` (em-dash with spaces). Wired into `tools/validate-deliverable.py:264-281`. Dispatched via `.claude/hooks/post-write-gate.py` for `/platform/public/`, `/deliverables/`, `/hero-exports/`, `/notion-pages/`.
- Voice-check does NOT detect ` -- ` (double-dash em-dash substitute).
- `.claude/hooks/post-write-gate.py:in_deliverable_scope` does NOT include `/doc-site/`, so the new `glossary/runbook/contacts/faq` files dodge validation entirely on edit.

What "locked down" means: see Next Steps below.

### 2. "Lots of UI improvement work" — unscoped

User said: "there is a lot of UI work that we should be doing. improvement work" — no specifics. Don't guess. Next session needs to scope this conversation: which pages, which elements, what behavior is wrong.

---

## Backlog (separate concerns, not new — surfaced during revamp)

- Backfill 8 unknown Fireflies URLs in `tools/notion-restructure-v18.py:FIREFLIES_BY_ANCHOR`
- Fix 2 pre-existing umlaut anchor mismatches on `s-00`
- Decide auth migration v2 — OAuth + Google allowlist when WW user count exceeds the current 3 people; ~3-4h work
- `proxy.ts` `/admin` and `/portal` matchers are still dormant (never enforced); separate concern, separate PR
- Pre-send hook to drop zero-byte images and prevent the API 400 crash class (harness concern, not WW-specific)

---

## Next Steps

1. **Em-dash lockdown** (priority order):
   - Add ` -- ` detection to `tools/voice-check.py` after line 95 — regex matches space-hyphen-hyphen-space, category `em-dash-substitute`. Verify voice-check skips fenced code blocks so `--no-verify` flags in code remain clean.
   - Extend `.claude/hooks/post-write-gate.py:in_deliverable_scope` (lines 53-63) to include `/doc-site/` — otherwise glossary/runbook/contacts/faq dodge validation on edit.
   - Sweep existing em-dashes + ` -- ` in `workspace/clients/warme-wimmer/context/doc-site/{glossary,runbook,contacts,faq}.md` (≈45 em-dashes, ≈13 ` -- ` cases) — review per occurrence; replace with comma/period/colon/parenthetical.
   - Sweep prose em-dashes in `workspace/clients/warme-wimmer/context/hero-exports/notion-pages/*.md` (≈165 em-dashes). Leave ` -- ` inside fenced code untouched.
   - `uv run tools/build-warme-wimmer-doc-site.py` → rebuild.
   - Verify: `grep -c "—" platform/public/docs/warme-wimmer/*.html | grep -v ":0$"` returns nothing.
   - Ship as PR #117.
2. **Scope the "UI improvements" conversation** — concrete asks, not a guessing game. Browse the live site together; user identifies specific UX problems.
3. Then 5 backlog items above as cleanup work.
