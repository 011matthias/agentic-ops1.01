# Restyle blueprint: embed the TreasuryCentral layout into the OnePilot prototype

Purpose: a self-contained directive a fresh chat can execute end to end.
It re-layers the existing OnePilot prototype around **TreasuryCentral**
(the cockpit), the **applications** (the jobs you buy), and **OnePilot +
OnePilot Agents** (the autonomous layer underneath). This is a targeted
edit of a strong existing page, not a rebuild. Delete this file once the
restyle ships.

> Coordination note: a concurrent session is actively elevating this same
> prototype's aesthetics (see "Brisken Website Aesthetic Elevation",
> 2026-06-17). Run this restyle in a git worktree, or sequence it after
> that session lands, so the two sets of edits to
> `brisken-onepilot-website-prototype.html` do not clobber each other.
> See memory `feedback_worktree_for_concurrent_sessions`.

## 0. How to use this

Point the new chat at this file: "read
`workspace/clients/brisken/deliverables/lead-generation/onepilot/brisken-treasurycentral-restyle-blueprint.md`
and execute it." Everything needed is here or linked below. The chat
will already load CLAUDE.md, the rules, and memory at session start; this
file carries the task-specific truth.

Upstream sources (read these first, in order):
1. The file to edit: `deliverables/lead-generation/onepilot/brisken-onepilot-website-prototype.html`
   (single-file HTML, self-contained, polished).
2. Naming + positioning truth:
   `context/lead-generation/evidence/brisken-product-catalog.md`, the "Spine
   reconciliation (2026-06-17)" section (TreasuryCentral, OnePilot
   Agents, BST, avoid co-worker/interface/copilot, the cockpit/pilot
   metaphor, the website-strategy fusion).
3. The evergreen site blueprint:
   `deliverables/lead-generation/onepilot/brisken-onepilot-website-blueprint.md` (positioning,
   sitemap, AEO). Predates the spine; its "named co-worker" and
   "Trade Automation" lines are stale; reconcile per section 7.
4. The marketing spine it serves:
   `deliverables/lead-generation/strategy/lead-gen-strategy-2026-06-12.html`, Marketing tab
   (the four moves: name the problem, publish the benchmark, name and
   prove the AI, work the SAP relationship).

## 1. What the prototype already has (do not rebuild these)

Current top-to-bottom structure, with the live section ids:

- `nav`: brisken / OnePilot; links Problem / Platform / Why now; theme
  toggle (works, keep it); CTA "More details" to `#products`.
- `header.hero` + `#report`: H1 "Financial data, solved end to end.";
  OnePilot-as-platform sub; tangle-to-governed-gate-to-SAP SVG; the
  benchmark band (81% / 62% / 38%, "Shadow Integration Report"). Move 2,
  already embedded.
- `.trust-band`: SAP Co-Innovation Partner, SAP Store, BTP, ISO 27001,
  SOC 1, data partners. Move 4, already embedded.
- `#problem`: "A shadow integration is any data feed into SAP that
  someone built by hand and no one maintains." Move 1, named enemy.
- `#platform`: "One governed platform, configured by AI, not hand-coded";
  4-step flow (Ingest / Validate / Govern / Distribute); time-to-value;
  connectivity; then three sub-blocks:
  - `#ai`: "AI agents, Part of the platform, inside your governance" +
    live-customer proof.
  - `#products`: "Two flagship apps, one platform underneath" (Market
    Data Hub + BST Brisken Smart Trading; rest listed in a line).
  - `#trust`: credentials + proof.
- `#why-now`: S/4HANA migration as the buying window.
- `#demo`: "See it on your own SAP setup" CTA band.
- `#answers`: three AEO Q&As + "OnePilot vs the usual paths" table.
- `#feedback`: double-click-to-annotate reviewer collector (works, keep
  it intact; it posts to the Fly host).
- `footer`.

So Moves 1, 2, 4 are done and BST is already renamed. The restyle adds
the one thing missing: the TreasuryCentral cockpit and the three-zoom
product story, and it brands the AI (Move 3).

## 2. The decision being embedded

- **TreasuryCentral is the flagship**, "the AI treasury cockpit on your
  SAP data: cash, investments, debt, FX, news and governance in one
  place." Confirmed public name (not "Treasury Hub"). It is the top zoom,
  what the buyer sees.
- **OnePilot is the autonomous layer**, the no-code platform on SAP BTP
  that moves and governs the data underneath every application. Not a
  product on a peer shelf; the named foundation.
- **OnePilot Agents** is the AI (Move 3). Avoid "co-worker" (junior,
  crowded by the "digital workforce" lane, the exact frame an AI-wary
  finance buyer distrusts), "interface" (passive, undersells the act
  step), and "copilot" (redundant beside OnePilot; crowded by MS/GitHub).
  Safer premium fallback if needed: "OnePilot Intelligence."
- **The metaphor that ties it together:** TreasuryCentral is the cockpit
  (what you see); OnePilot is the pilot that flies the operation, under
  your governance, every move logged; the treasurer stays in command.
- **BST = Brisken Smart Trading**, successor to Trade Automation +
  TraderPlus. Already in the prototype; keep it.

## 3. Target architecture (three zoom levels)

One platform at three zooms. New narrative order:

1. Problem (shadow integrations); keep `#problem` as-is.
2. **Cockpit: TreasuryCentral**; NEW section, the whole picture the
   buyer gets. Goes right after `#problem`.
3. **Applications**; relabel `#products`. The jobs you buy; lead with
   the Wave 1 trio (Market Data Hub, BST, Remittance Advice Gate), rest
   on the same platform.
4. **Autonomous layer: OnePilot + OnePilot Agents**; the existing flow
   + `#ai` block, rebranded. What runs it.
5. Trust, Why now, Demo, Answers, Feedback; keep.

Net section order after the edit:
hero+benchmark, trust-band, problem, **treasury-central (new)**,
applications (was products), platform/autonomous-layer (flow + OnePilot
Agents), trust, why-now, demo, answers, feedback.

Add a `TreasuryCentral` link to the top `nav-links` (between Problem and
Platform). Keep the nav to 3-4 links; if it crowds, drop "Why now."

## 4. Exact edits (keyed to the current prototype)

Reuse the page's existing CSS classes (`.section`, `.wrap`, `.eyebrow`,
`.grid-2`, `.grid-3`, `.card`, `.flow`, `.btn`). Do not fork the styles.
All copy below is final; drop it in. Sentence case headings.

### 4a. Hero sub (light touch, `header.hero`)

Keep H1 and the SVG. Update the sub so the cockpit/pilot vocabulary
appears up top:

> OnePilot is the autonomous layer that moves market data, trades, bank
> files and remittances in and out of SAP, governed end to end. Run the
> applications together and you get TreasuryCentral, one cockpit for the
> whole treasury. You buy the outcome, not another integration project.

Optionally update the hero badge to: "TreasuryCentral, the AI treasury
cockpit for SAP."

### 4b. NEW section: TreasuryCentral (insert after `#problem`, before `#platform`)

```html
<section class="section" id="treasury-central">
  <div class="wrap">
    <span class="eyebrow">The cockpit</span>
    <h2>TreasuryCentral: one cockpit for the whole treasury</h2>
    <p class="section-sub">Run the applications together and you get TreasuryCentral, the single screen your team works in: cash, investments, debt, FX, market news and governance in one place, on your SAP data. The applications feed it; OnePilot keeps it running, governed end to end.</p>
    <div class="grid-3">
      <div class="card"><h3>One view of the money</h3><p>Cash, investments and debt across entities, current and reconciled to SAP, not stitched from spreadsheets.</p></div>
      <div class="card"><h3>FX and market data, governed</h3><p>Rates, curves and exposures from your providers, validated before they reach a decision.</p></div>
      <div class="card"><h3>Control built in</h3><p>Audit trail, manage-by-exception, four-eye and segregation of duties on every record.</p></div>
    </div>
  </div>
</section>
```

(The "cash, investments, debt, FX, news, governance in one place" line
traces to Brisken's own TreasuryCentral one-liner; keep it; do not invent
screens or metrics beyond it.)

### 4c. Applications (rework the `#products` sub-block)

TreasuryCentral now holds the "flagship" role, so remove the "Flagship"
labels from the app cards and reframe these as the jobs:

> Eyebrow: "The applications"
> H3: "Pick the job you need first"
> Lead row (`grid-2` or `grid-3`): Market Data Hub; BST, Brisken Smart
> Trading; Remittance Advice Gate, each its one-liner (keep MDH and BST
> copy; add Remittance: "AI reads the messy remittance emails and posts
> them into SAP, so the team stops retyping. Live today on a governed AI
> gate.").
> Trailing line: "On the same platform: Cash Flow & Exposure Hub, Bank
> Fee Portal, Credit Data Hub, ESG Data Hub, plus the AI Digital
> Workforce as a cross-sell."

Point each app card's CTA (if you add one) at `#demo`; in production these
become the per-campaign demo landing pages (site-engine handshake).

### 4d. Autonomous layer + OnePilot Agents (rework `#ai`)

Keep the 4-step flow. Rebrand the AI sub-block:

> Eyebrow: "The autonomous layer"
> H3: "OnePilot runs it. You stay in command."
> Body: "OnePilot is the autonomous layer underneath every application:
> the no-code platform on SAP BTP that moves and governs the data, with
> OnePilot Agents doing the repetitive work inside your controls. Think
> cockpit and pilot: TreasuryCentral is what you see; OnePilot flies the
> operation; every move is logged, with four-eye and segregation of
> duties where you want them. Not a chat box bolted on, not a dashboard
> you babysit. Live today: an agricultural customer posts remittances
> into S/4HANA on a governed AI gate, and a chemicals customer runs an AI
> funding-request process across a complex SAP integration."

Rename the section eyebrow `#ai` from "AI agents" to "OnePilot Agents"
wherever it appears. Do not use "co-worker," "assistant," "interface," or
"copilot" anywhere on the page.

### 4e. Nav + section headers

Update the `#platform` H2 from "One governed platform..." to lead with the
layer framing, for example: "The autonomous layer that runs it, on SAP
BTP." Add the TreasuryCentral nav link. Keep `#trust`, `#why-now`,
`#demo`, `#answers`, `#feedback` unchanged.

## 5. Hard constraints (from the rules; non-negotiable)

- **Zero em-dashes**: no U+2014, no `&mdash;` entity, and no double-hyphen substitute. Use commas,
  semicolons, colons, or split sentences. The `em-dash-strip-gate.py`
  hook auto-strips on every Edit to this client path, so write clean or
  it will mangle spacing.
- **No emoji in nav or anywhere.** Plain text labels only.
- **Keep the dark/light toggle working** (boot script + `.nav-theme`
  button already present). Do not add a second toggle.
- **Last-updated**: bump any date stamp in the footer to the actual edit
  date.
- **Anti-slop voice** (`rule_anti_slop`): no per-category narration of
  identical shape, no three-part lists where two work, no corporate
  thesaurus (robust, leverage, ensure, facilitate, comprehensive,
  streamline, optimize, holistic, drive, unlock), no "not just X but Y,"
  no performed humanness. The three TreasuryCentral cards above each
  carry distinct information; keep that discipline if you add more.
- **B4 data accuracy**: every product claim traces to the catalog or the
  spine. The named logos are cleared for use (catalog reconciliation);
  anonymized customer proof can become named where a logo exists. Do not
  invent customers, numbers, or screens.

## 6. Do not break

- The `#feedback` double-click annotation collector and its JS.
- The hero SVG animation and the benchmark band.
- The theme toggle and its boot script.
- The `onepilot-site` sync: the served copy is built by
  `onepilot-site/sync-site.py` copying this HTML to `site/index.html`.
  Edit the deliverable HTML only; the `site/` copy is gitignored.

## 7. Validate, sync, ship

1. `uv run tools/validate-html.py workspace/clients/brisken/deliverables/lead-generation/onepilot/brisken-onepilot-website-prototype.html`
   Fix every failure before going further (B2 gate; do not deploy on a
   fail).
2. Reconcile the upstream blueprint so the two do not drift: in
   `brisken-onepilot-website-blueprint.md`, update the sitemap/positioning
   lines that still say "Trade Automation" and "the named co-worker" to
   TreasuryCentral-flagship, BST, and OnePilot Agents. Small edit; same
   commit.
3. Feature-branch commit + push + PR auto-run once validation passes
   (Band 1). Let CI merge on green (Band 2).
4. Deploy is gated (Band 3, explicit order needed). The host is the
   internal pre-Dirk Fly app `brisken-onepilot-proto` (gated review, not
   brisken.com). To publish for review, from `onepilot-site/`:
   `uv run sync-site.py` then `flyctl deploy ./ --remote-only --ha=false`.
   Run these only on the user's go.
5. After deploy, verify per the deploy gate: fetch the gated URL, confirm
   200 + the TreasuryCentral section renders, theme toggle flips, feedback
   form posts.

## 8. The one thing not to overstep

The OnePilot-vs-TreasuryCentral nesting is owner-pending, but the user
picked TreasuryCentral as the cockpit flagship, so build the nested model
(cockpit shows, pilot flies, OnePilot the layer beneath). It is fully
reversible in this single file. Do not assert a hierarchy fact on the
page beyond "TreasuryCentral is the cockpit, OnePilot is the layer that
runs it"; do not add products, customers, or numbers not in the catalog
or the spine.
