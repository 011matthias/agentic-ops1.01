# Client Page Structure Standard

**Hard constraint.** Every client-facing static page under
`platform/public/clients/{slug}/**` (prospect proposal sites) and
`platform/public/docs/{client}/**` (active-client gated doc sites)
abides by ONE structural standard. Three qualities are load-bearing:
**overseeability** (the client always knows where they are in the
material), **clarity** (sections, labels, and navigation are
predictable across clients), and **transparency** (the client always
knows when a page was last updated and what changed).

This rule is the source of truth for client-page structure. It
sits beside [[rule_platform_standards]] (the marketing site) and
[[rule_deliverables]] (self-contained HTML hero exports). The
deliverable rule's HTML QoL requirements (dark/light toggle,
copy-to-clipboard, Ctrl/Cmd+K, state persistence) apply here too,
with the augmentation in §3 below.

## Scope

In scope:
- `platform/public/clients/{slug}/**` — prospect proposal sites
  (one folder per prospect, multi-page HTML)
- `platform/public/docs/{client}/**` — active-client gated doc
  sites (one folder per shipped client; gated per
  [[rule_gated_access]])

Out of scope (but rules overlap):
- The platform Next.js app (`platform/src/app/**` →
  [[rule_platform_standards]])
- Self-contained one-off HTML deliverables outside the
  per-client folder (→ [[rule_deliverables]])
- Email bodies, PDFs, video scripts (→
  [[rule_human_communication]])

## 1. Canonical page rosters

Two roster families exist. New work picks one and stays in it.

### Family A — Prospect proposal site (default)

Seven top-level pages, in navigation order:

| # | File | Purpose |
|---|---|---|
| 1 | `index.html` | Hero + one-page overview |
| 2 | `solution.html` | Architecture / what we build |
| 3 | `workflow.html` | Step-by-step flow (the pipeline) |
| 4 | `timeline.html` | Weeks 1–N milestones |
| 5 | `investment.html` | Pricing, phases, terms |
| 6 | `onboarding.html` | What we need from the client |
| 7 | `faq.html` | Common questions |

Optional eighth page:
- `gdpr.html` — when EU healthcare or other regulated data is
  involved (menovia, openwebui-email-compliance,
  ai-shipment-support-bot precedent)
- `brief.html` — when the prospect supplied a structured RFP/brief
  worth reproducing verbatim (Track-1/Track-2 family)

Optional PDF variants (`*-pdf.html`, `print.html`,
`proposal-pdf.html`): allowed only when the prospect has asked
for a one-file printable. Otherwise rely on the per-page
`@media print` stylesheet (§6).

### Family B — Active-client doc site

Active clients (post-handoff or under retainer) get a doc-site
shape governed by the client's actual operating needs, not the
prospect template. Examples in the current repo:

- `clients/brisken-lead-automation/` — adds `dashboard.html` and
  `changelog.html`, drops `workflow.html` and `onboarding.html`
- `docs/meji-media/` — domain-specific operating pages
  (`build-plan`, `lead-scoring`, `volume-forecast`, etc.)
- `docs/warme-wimmer/` — multilingual runbook + flowchart set

The shared shape requirement is just §2 below (navigation
chrome + last-updated stamp). The page ROSTER is free.

## 2. Navigation chrome (every page)

Every page in either family carries:

1. **Top site-nav** (`<nav class="site-nav">`):
   - Left: brand + ` &middot; ` separator + client/prospect label
   - Center/Right: page-link tabs (the roster from §1) with the
     current page marked `.active`
   - Right: status badge + theme toggle button
2. **Left sidebar** (`<aside class="sidebar">`):
   - "Steps" or "Sections" label
   - Numbered `step-list` of the roster, with `.active` on current
3. **Main content** (`<main class="main-content">`):
   - One `<section class="hero">` with badge + h1 + sub + stats-row
   - Sectioned body — every `<h2>` carries an `id` for deep linking
4. **Footer** (`<footer>` or `.footer` div):
   - One-line attribution: client name + UnpauseAI + canonical
     contact + year
   - Last-updated stamp (§4)

If a page is intentionally chromeless (PDF-rendered variants,
print-only views, embedded dashboards), declare it with a
top-of-file HTML comment: `<!-- chrome-allow: chromeless -->`.
The corrector script in §6 honors this marker.

## 3. Dark/light mode — must actually work

The current state on the repo (31 client roots audited 2026-06-01):
all 31 declare `[data-theme]` CSS hooks; ZERO carry the JS that
makes the toggle work. The CSS is dead weight without the script.

Every page MUST include both:

1. The boot script in `<head>` BEFORE any body content paints,
   to prevent a flash of light-on-dark or vice versa:
   ```html
   <script>(function(){var t=localStorage.getItem('theme');
     var d=document.documentElement;
     d.setAttribute('data-theme',
       t==='dark'||(t!=='light'&&window.matchMedia('(prefers-color-scheme:dark)').matches)?'dark':'light');
   })();</script>
   ```
2. A clickable toggle in the site-nav (`<button class="nav-theme">`)
   that flips the attribute and persists the choice:
   ```html
   <button class="nav-theme" onclick="(function(){
     var d=document.documentElement;
     var c=d.getAttribute('data-theme')==='dark'?'light':'dark';
     d.setAttribute('data-theme',c);
     localStorage.setItem('theme',c);
   })()" aria-label="Toggle theme">&#9788;/&#9790;</button>
   ```

The corrector (`tools/normalize-client-pages.py`) injects both
when missing.

## 4. Last-updated transparency

Every page carries a `Last updated: YYYY-MM-DD` line in the
footer (or top-of-hero for dashboard-style pages). The date is
the actual date of the last meaningful edit — not the year, not
"recently", not absent. Sources, in order of preference:

1. Explicit `data-updated="YYYY-MM-DD"` attribute on `<body>` or
   `<footer>` written at edit time (manual but authoritative)
2. Git mtime of the file at last commit (machine-derivable, used
   by `normalize-client-pages.py --backfill-dates` for a one-time
   backfill)

For active-client doc sites (Family B), a richer
`changelog.html` is required (see brisken precedent) — the page
links to it from the footer.

## 5. Page structural primitives (the existing CSS class set)

The 31 client roots already converged on a shared CSS primitive
set. Treat this as the canonical pattern; do not fork:

- `.site-nav`, `.nav-left`, `.nav-logo`, `.nav-client`,
  `.nav-links`, `.nav-status`, `.nav-theme`
- `.sidebar`, `.sidebar-label`, `.step-list`, `.step-item`,
  `.step-link`, `.step-num`, `.step-line`
- `.main-content`, `.content-inner`
- `.hero`, `.hero-badge`, `.hero-sub`, `.stats-row`,
  `.stat-card`, `.stat-value`, `.stat-label`
- `.callout`, `.callout-title` + color variants
  (`.callout.green`, `.callout.orange`)
- `.zones`, `.zone`, `.zone-blue`, `.zone-purple`,
  `.zone-green`, `.zone-items`, `.zone-arrows`
- `.solution-grid`, `.sol-card`, `.sol-num`, `.sol-title`,
  `.sol-desc`
- `.timeline-strip`, `.tl-card`
- `.cta-section`, `.cta-btn`
- `.footer`

A new client page reuses these classes. Adding a new primitive
class is allowed when the existing set genuinely doesn't fit;
it must be documented in this rule the same change.

## 6. Print + PDF behavior

Every page includes the canonical `@media print` block:

```css
@media print {
  .site-nav, .sidebar, .mobile-nav-toggle, .cta-section { display: none !important; }
  .main-content { margin-left: 0 !important; }
  body { padding-top: 0 !important; }
  h2 { page-break-before: always; }
  h2:first-of-type { page-break-before: avoid; }
}
```

Pages missing this print with the nav and sidebar visible,
failing the "save as PDF" use case. The corrector injects it
where absent.

## 7. The "overseeability" test

The simplest test for whether a client-page set passes this rule.

Open the index in a private browser window. Without scrolling
the sidebar, can the reader answer:

1. Which client is this for? (top-nav `.nav-client` label)
2. What's the project? (hero h1)
3. How many sections are there? (sidebar `step-list` count)
4. Where am I in the set? (sidebar `.active`)
5. When was this last touched? (footer last-updated stamp)
6. How do I reach the next section? (sidebar links + arrow CTA)
7. Who do I email if I have a question? (footer canonical contact)

If any of these takes more than two seconds, the page fails.
Run the corrector before deploying.

## 8. Strategic decisions (not auto-corrected)

These are deliberately NOT mechanically corrected — they need
the project owner's judgement per client:

- Whether an active-client site should migrate from Family A
  (proposal shape) to Family B (operating-doc shape). The trigger
  is usually project handoff; document the migration in the
  client's `comms-log.md` when it happens.
- Page-roster pruning (removing `workflow.html` when the workflow
  is trivial, removing `onboarding.html` when there's nothing
  to ask for) — per-client editorial decision.
- Whether to add `gdpr.html` or a regulator-specific page —
  driven by the actual compliance requirement, not the template.

## 9. Enforcement

Three mechanisms:

1. **`tools/audit-client-pages.py`** (new) — repo-root script
   that walks `platform/public/clients/**` and
   `platform/public/docs/**`, runs the §2–§6 probes, and
   reports drift. Severity-banded. Run before any client-page
   deploy.
2. **`tools/normalize-client-pages.py`** (new) — the corrective
   tool. Injects the boot script (§3), the nav-theme button
   (§3), the print stylesheet (§6), and the last-updated footer
   line (§4 — optional backfill mode). Safe to re-run;
   idempotent.
3. The existing `post-write-gate.py` dispatcher already routes
   `platform/public/**` writes into `validate-deliverable.py`.
   The dispatcher's `in_deliverable_scope()` check already
   covers this rule's scope.

**Self-detection.** A client opening a page, finding stale
content, or being unable to use the theme toggle is a friction
event (`client-page-structure-drift`) — log at
`/comd_checkpoint`. The recurrence-kill is to strengthen the
audit script (§9.1), not to fix the page in isolation.

## Why

The 2026-06-01 audit found:
- 0/31 client roots have a working theme toggle even though
  31/31 ship the CSS for it
- 21/31 carry no last-updated stamp
- 4/31 missing site-nav; 5/31 missing sidebar; 5/31 missing
  the print stylesheet
- The canonical 7-page proposal roster is implicit across
  20/31 sites but had never been written down

Overseeability is the single most cited "this feels professional"
signal in client-facing work. The 31 sites already converged on
80%+ of the standard organically; making it explicit closes the
remaining 20% and prevents drift on the next site built.

Related: [[rule_platform_standards]], [[rule_deliverables]],
[[rule_gated_access]], [[rule_human_communication]].
