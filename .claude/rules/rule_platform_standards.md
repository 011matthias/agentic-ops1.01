# Platform Standards (unpauseai.com)

**Hard constraint.** All public-facing content on the UnpauseAI platform
(`platform/`) — landing pages, proposal templates, proposal markdowns,
client-portal copy, transactional email bodies, and OG metadata — abides
by ONE structural and aesthetic standard. This rule is the source of
truth for that standard. The existing `rule_deliverables.md` covers
self-contained HTML deliverables (hero exports, dashboards, doc sites);
this rule covers the Next.js platform itself.

Scope of "public-facing":
- `platform/src/app/(public)/**` — landing pages, services, work,
  automations, oneproposal, about, contact, assessment, proposals,
  terms, privacy, buy
- `platform/src/components/**` rendered by the above (Header, Footer,
  ProposalLayout, ProposalCTA, ProposalHeader, catalog cards)
- `platform/src/content/proposals/**` — proposal markdowns
- `platform/src/lib/email.ts` / `platform/src/app/api/admin/invite/route.ts`
  / role-promotion transactional-email bodies (rendered to clients)
- `platform/src/app/layout.tsx` / per-page `metadata` exports — title,
  description, OG copy

Scope of "internal" (this rule does NOT apply, except brand spelling):
- `platform/src/app/admin/**` — admin dashboards (em-dash placeholders
  in tables are allowed; see exemptions)
- `platform/src/app/portal/**` — client portal interior (em-dash
  placeholders in tables are allowed)
- API route business logic, library code, comments in source

## 1. Brand identity (lexical)

- Brand name is `UnpauseAI` — one word, capital U, capital A. Never
  `Unpause AI`, never `UnPauseAI`, never `Unpauseai`, never `UnpausAI`
  (the e-dropped typo — `validate-platform-content.py` catches this).
- Product name is `OneProposal` — one word, two caps.
- Public contact email is `admin@unpauseai.com` (canonical as of
  2026-06-01; replaces the prior `nicolas.neumann@unpauseai.com`
  default). Legacy alias `hello@unpauseai.com` is NOT canonical;
  reuse the env-driven `CONTACT_EMAIL` (defaults to admin@) for any
  new surface. Transactional email `from:` is
  `no-reply@unpauseai.com`. No other unpauseai.com address may
  appear in public-facing surfaces without an explicit user decision
  recorded in the comms log.
- Tagline: "Built to stay done. EU-based automation consultancy."
  (Footer is the canonical home; reuse it verbatim in any place
  that needs a one-line descriptor.)

## 2. Language (banned typography + banned constructions)

These are non-negotiable for public-facing surfaces.

- **Enumerated voice bans** (corporate-thesaurus words, banned
  meta-phrases, "not just X but Y", sentence-opening adverbs,
  performed-humanness): the single canonical list lives in
  [[rule_anti_slop]] and applies in full here. Platform-specific
  exception: a banned corporate-thesaurus word is allowed inside a
  verbatim quotation of the source posting (block-quoted or quoted
  with attribution).
- **Em-dashes**: zero. Banned forms are `—` (U+2014), `&mdash;` entity,
  and ` -- ` (space-dash-dash-space) as a typographic substitute.
  Replace with semicolons (`; ` is the conventional substitution in
  `tools/strip-em-dash.py`), colons, commas, or by splitting into two
  sentences. Choose the punctuation that preserves meaning; default
  to semicolon when in doubt.
- **Contractions in prose, full forms in table cells.**
- **Dates**: every visible date stamp must reflect the actual prep or
  last-update day. Footer copyright year uses `new Date().getFullYear()`
  (already correct); never hardcode the year. Proposal frontmatter
  `created:`, `sent:`, and any "Last updated:" footer in a page must
  be queried/verified, never invented.

## 3. Structure (proposal markdown canonical shape)

Every proposal markdown in `platform/src/content/proposals/` follows
the canonical section order. Headings are level-2 (`##`), exactly as
written below:

1. `## What We Understood` — restate the prospect's brief in our words
2. `## Our Proposed Solution` — what we will build (always
   `Our Proposed Solution`, not `Proposed Solution` and not
   `What We're Proposing`)
3. Optional: `## How It Works` or `## Architecture` — for proposals
   that need a diagram or component breakdown
4. `## Timeline & Milestones` — always with `&`, not `and`, and never
   bare `## Timeline`
5. `## Investment` — pricing
6. `## About UnpauseAI` — boilerplate; never `## About UnpausAI`
   (e-dropped typo)
7. Optional: `## Research Notes` — research block carried over from
   `agnt_proposal-research` for our own reference

Track-based proposals (Track 1 video-led, Track 2 full-site) use the
shape `## Centerpiece` → `## Track` → `## Compensation` → `## Pages`
→ `## Downloadable artifact` → `## Next steps` instead. That alternate
shape is sanctioned for the Track-1/Track-2 family ONLY.

## 4. Information architecture (nav + offering pages)

Three offering pages currently exist and overlap in purpose:
`(public)/services`, `(public)/work`, `(public)/automations`. Until
the strategic owner consolidates them (see Section 8), the rule is:

- Header (`Header.tsx`) and Footer (`Footer.tsx`) link to the SAME
  navigation set. A link that exists in one must exist in the other,
  or be intentionally hidden from both with a code comment explaining
  why.
- Every `Link href="/foo"` in a public page must resolve to a real
  page under `app/(public)/foo/page.tsx`. No dead links.
- CTA destinations are uniform per kind:
  - "Tell us about your workflow" → `/contact`
  - "Get a personalized assessment" → `/assessment`
  - Proposal-specific "Let's talk, {prospect}" → `mailto:admin@unpauseai.com` (the `CONTACT_EMAIL` env value, defaults to admin@; §1 canonical)

## 5. Voice and CTA copy (uniform vocabulary)

- H1: sentence case ("Get in touch", "Battle-tested workflows") —
  except the home page hero and explicit Title-Case product names
  ("Automation Marketplace", "OneProposal", "UnpauseAI").
- H2 / eyebrow labels: short single-or-double-word Title Case
  ("Process", "Technology", "Marketplace", "Architecture",
  "What We Do", "Who We Are").
- Primary CTA button copy is one of these — no improvising new
  phrasings without updating this rule first:
  - "Get in touch" / "Send Message" (form submit)
  - "Request Assessment" (when target is `/assessment`)
  - "Request a Quote" (when target is `/contact` from a pricing
    context)
  - "Let's Talk, {prospect}" (Proposal CTA only)
- Tertiary link CTAs (arrow links): "{Phrase} →" using the literal
  `&rarr;` entity (already convention; do not switch to Unicode `→`).
- No exclamation marks in body copy. CTAs may use them sparingly
  (max one per page) — but the default is no.

## 6. Visual system (already in `globals.css` — do not fork)

- Palette: blue `#2563eb`, purple `#7c3aed`, green `#059669`, orange
  `#d97706`, with `*-dark`, `*-light`, `*-bg` variants. New pages
  pick a single accent and stick to it; no new palette extensions
  without updating `globals.css` AND this rule.
- Typography: Geist Sans (body) + Geist Mono (code/inline). Do not
  introduce a third font family.
- Card primitive: `rounded-xl border border-border bg-surface p-X`
  with `transition-all hover:-translate-y-0.5 hover:shadow-md` —
  reuse, do not fork.
- Section primitive: `border-t border-border` between full-width
  sections; `mx-auto max-w-{3xl|4xl|5xl} px-6 py-{16|20}` inside.
- Pill button (CTA): `rounded-full bg-accent px-6 py-3 text-sm
  font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)]
  transition-all hover:bg-accent-light hover:-translate-y-0.5`.
  Don't redesign per-page.
- Dark mode: managed by `ThemeProvider` + the inline script in
  `layout.tsx`. Never add a per-page dark-mode toggle.
- Animations live in `globals.css` (`animate-fade-in-up`,
  `animate-stagger-N`, `.scroll-reveal`). Don't define new
  `@keyframes` inline.

## 7. Data accuracy on public surfaces

Inherits B4 ("about to write a data value into a deliverable") from
`rule_behaviors.md`. On the platform specifically:

- Every numeric claim on a landing page ("processes thousands of
  automated operations monthly", "build within 24 hours") must trace
  to a queryable source — admin Builds table, client comms-log, a
  real published case study. If not query-able, the claim is "TBD"
  or rephrased as a capability ("can process ...") rather than
  a measured one ("processes ...").
- Tool / integration lists (`/services`, `/work`, `/about`) must
  match `platform/src/content/catalog.ts` and the actual stack used
  in shipped client work. Do not add a tool here that has never
  shipped in `workspace/clients/`.
- Prospect-facing proposal pages must reflect what was actually
  scoped with the prospect. No back-filled "we proposed X" copy on
  pages whose `frontmatter.sent` is null.

## 8. Strategic decisions deferred to the user

This rule does NOT decide:
- Which of `/services`, `/work`, `/automations` is canonical and
  which (if any) should be removed or merged.
- Whether `/oneproposal` and `/assessment` belong in the header
  nav (currently only `/assessment` is in the footer).

When the owner decides these, update this rule in the same change.

## 9. Exemptions (admin/portal only)

The em-dash ban exempts these PATTERNS, in `(admin)/**` and
`(portal)/**` ONLY:

- The `"—"` empty-state placeholder used in table cells
  (`?? "—"`, `<span>—</span>`). This is a typographic convention
  for "no value" and forcing `"-"` (single hyphen) or `"N/A"`
  would hurt scannability. The admin/portal pages are
  authenticated-only and not client-facing.
- Em-dashes in `metadata.title` of admin pages
  (`"Builds — Admin"`). Same reasoning; not crawled, not public.

Public-facing `(public)/**` JSX gets NO exemption.

## 10. Enforcement

Three mechanisms, all working together:

1. **`tools/validate-platform-content.py`** — repo-root script that
   walks `platform/src/app/(public)/**`, `platform/src/content/proposals/**`,
   and `platform/src/components/{Header,Footer,proposal/*}.tsx`,
   and reports:
   - em-dash hits (`—`, `&mdash;`, ` -- `)
   - banned-word hits with line + context (corporate thesaurus +
     meta-phrases)
   - brand-spelling typos (`UnpausAI`, `Unpauseai`, `UnPauseAI`,
     `Unpause AI`)
   - dead `/path` references in JSX vs. actual pages in
     `app/(public)/`
   - canonical heading drift in proposal markdowns (Timeline /
     Proposed Solution variants)

   Exit non-zero if any HIGH-severity finding fires. Run before any
   platform deploy (extends the "Deploy verification gate" in
   `rule_behaviors.md`).

2. **`tools/strip-em-dash.py`** (existing) — the corrective tool.
   Run on a proposal markdown to mechanically replace ` — ` /
   ` -- ` with `; `. Use this before sending any new proposal.

3. **Post-write hook** (`post-write-gate.py`) — already routes
   `platform/public/**` writes into `validate-deliverable.py`.
   This rule extends the dispatcher's `in_deliverable_scope()` to
   also fire `validate-platform-content.py` on writes under
   `platform/src/app/(public)/**` and `platform/src/content/proposals/**`.
   That wiring change is part of this rule's implementation, not a
   future commitment.

**Self-detection.** A violation of any section above caught by the
user (em-dash slip into a proposal, brand typo on a landing page,
banned word in a JSX heading) is a friction event
(`platform-standards-drift`) — log at `/comd_checkpoint`. The
recurrence-kill is to strengthen `validate-platform-content.py`,
not to memorize harder.

## Why

The UnpauseAI platform accumulated style drift across ~30 proposal
markdowns + ~12 public pages + multiple components. Concrete symptoms
caught in the 2026-06-01 audit:

- 2 proposal markdowns shipped with the brand typo `UnpausAI`
- 18 of ~30 proposals use ` -- ` as an em-dash substitute (banned
  by `rule_deliverables.md` since 2026-05-08, never enforced for
  the platform itself)
- 3 public JSX pages embed literal `—` or `&mdash;`
- `ProposalCTA.tsx` uses `hello@unpauseai.com` while every other
  surface uses `nicolas.neumann@unpauseai.com`
- Three different headings used for the same proposal section
  ("Timeline & Milestones" vs "Timeline and Milestones" vs
  "Timeline")
- Three overlapping offering pages (`/services` / `/work` /
  `/automations`) with no clear primary
- Header and Footer nav-link sets are not aligned (Header is
  missing `/assessment`)

Style drift on a marketing surface is the same problem class as
verification theater ([[rule_behaviors]] Layer 2): "compiles" is
not "correct". A page that ships is not necessarily a page that
matches the standard. This rule + `validate-platform-content.py`
make the standard executable.
