# OnePilot Site, Review-Feedback Revision Blueprint

Status: revision plan (2026-06-20). Source: the 21 reviewer notes on
the hosted prototype dated 18-19 June (after the pre-18th log cleanup).
Reviewers: DIRK (12), Ricardo Merrighi (6), Criss Cavalcanti (2),
Djalma Freitas (1). Target: `brisken-onepilot-website-prototype.html`.
Owner: UnpauseAI for Brisken. Pairs with the full build blueprint
(`brisken-onepilot-website-blueprint.md`).

Ordered by effort, fastest wins first. Each item names its source note.

## 1. Microcopy (fast, low risk)

Apply directly:

- Remittance FAQ header: drop "email". Remittance advice arrives in any
  format (direct link, PDF, CSV upload), so the header should not single
  out email. (DIRK 07:54)
- Trust line: keep "SOC 1 Type II" on one line. Wrap the term in a
  non-breaking span so "Type" and "II" never split across a line break.
  (DIRK 07:53)
- Autonomous-layer line: "FX and market data, governed" becomes "FX and
  market data with governance". (Ricardo)
- Cockpit one-liner: "cash, investments, debt, FX, market risk management
  and governance on one screen." (Ricardo)

Owner call (each is a real wording trade-off, not mechanical):

- "Govern" to "Governance", and "Cleansing, mapping, calculations,
  anomaly detection" shortened to "Cleaning". Both read tighter as-is;
  Ricardo wants the plainer noun. Pick per voice, then apply across all
  instances at once. (Ricardo)
- Four-eyes line ending "...every single record." Confirm the claim is
  true for every record before stating it. (Ricardo, B4)

## 2. Positioning: "autonomous", scoped

Weave "autonomous" through the copy where it is the SAP-ecosystem term
buyers expect (autonomous enterprise, autonomous processes), but anchor
it to specific processes, never the treasury as a whole. State that the
remittance-advice gate and a market-risk monitoring agent run
autonomously; do not imply autonomous payments or an autonomous
treasury, which a treasurer reads as loss of control. (DIRK 07:24)

## 3. Platform map / diagram

- Retire the word "interface" for TreasuryCentral. Unify on "cockpit"
  (already used in the cockpit section) or "command center". Frame the AI
  as the brain of the system, TC as the control surface. (DIRK 07:45)
- Add nodes so the map shows TreasuryCentral spans more than Brisken
  products on OnePilot: SAP, other systems, webapps, website, portals.
  (DIRK 07:33)
- Define one reusable "navigation instruction" text style for cues like
  "Click any node to open it", visually distinct from body copy, and use
  it everywhere the site instructs the reader. (DIRK 07:28)

## 4. Sizing and responsiveness

The page reads small; at 125% browser zoom it looks right, which means
the base scale is too low. Raise the base type scale and content max
width, scale imagery up with the viewport, and make the OnePilot hero
image larger and more prominent. Benchmark against sap.com at 100% zoom.
(DIRK 07:09, 07:17, 07:26)

## 5. Demo section

A live demo cannot run on the prospect's own SAP (connecting to an
external SAP landscape takes weeks), so reframe "See it on your own SAP
setup" to a demo on Brisken's landscape. New heading direction: "see for
yourself", a "stop believing, start doing" line. (DIRK 07:51, 07:52)

## 6. Trust and partners

- Customer logos: build the rolling banner with the named set (Nestle,
  Ford, Siemens, YETI, BAT, Zespri, Equinor, KAUST), sourced from the
  marketing customer-logo assets. (Criss 10:00)
- Footer: add the privacy note Criss flagged. (Criss 09:52)
- Market-data vendors: decide on "Reuters". Refinitiv (already listed) is
  the former Thomson Reuters data business, so adding "Reuters" may
  double-count; either add it as a recognized name or leave Refinitiv.
  (Ricardo)

## 7. FAQ / AEO

Add buyer-question entries (they double as answer-engine bait):

- Deploying AI agents for users without consuming the whole IT budget.
- Whether AI automation in treasury is safe.
- Using AI for liquidity forecasting.
- Using AI to focus the treasurer's day on what matters.

(DIRK 08:03)

## 8. Reposition: OnePilot is the platform, TreasuryCentral is one edition

This is the one large structural item from the review, not a copy edit.
Treat it as a separate work-block; items 1-7 ship independently of it.

> Critical overlay: this section captures what Dirk's OnePilot vision implies
> for the site, taken on its own terms. Before acting on the homepage calls in
> §8.B-C (the Universal-UI-first title / hero), read
> `brisken-onepilot-vision-strategy-fit.md` §4: reconciled against the
> marketing strategy, the homepage and AEO root stay on the SAP-data wedge and
> the Universal UI moves to its own platform/vision page one click away. The
> rest of §8 (the OnePilot-vs-TreasuryCentral hierarchy, the platform-map
> redesign, the AEO re-nesting, the overclaim guardrail) stands.
> The vision was updated 2026-06-20 to the CONTINUOUS version (five competitive
> slices, stronger Gartner adoption stats, "orchestrate don't replace", "your
> best practice not the vendor's"); the §8 line-number citations point to the
> earlier V001 extract, but its substance (the must-hold distinction and the
> overclaim guardrail) is unchanged. See the fit memo §6 for the delta.

### A. Diagnosis

The prototype is built as a TreasuryCentral product site with OnePilot
as the engine underneath it: the `<title>`, meta, nav, hero, platform
map and panels all name TreasuryCentral as the product and call OnePilot
"the AI layer" that "runs it underneath" (prototype audit; title line 7,
meta line 9, map node line 952, panel eyebrow line 1025). The vision
inverts that hierarchy: OnePilot is the framework / Universal UI and
TreasuryCentral is its first scoped edition, the vision's "must hold"
line being "TreasuryCentral isn't a different product; it's OnePilot,
scoped" (vision §7 must-hold table, line 146). This is exactly Dirk's
complaint, that the site makes the edition the headline and demotes the
platform to plumbing (DIRK).

### B. Corrected message hierarchy

The fix is altitude, not content. Nothing built gets discarded; the
SAP-treasury spine drops one level so the platform story can sit above
it (AEO/outbound reconcile §2).

1. **OnePilot, the platform story (new headline).** The Universal UI:
   one composable AI-native cockpit where a user assembles the spaces,
   apps and data their job needs; agents act across all of it within the
   user's exact permissions; it reaches down into ERP, banking and
   market data. The three layers (framework / spaces / agents) and the
   "make users happy again" relief theme are the hero. The four-slice
   gap (Glean; M365 Copilot/Gemini; Agentforce/Copilot Studio;
   Notion/Airtable) is the "why this is different" section (vision §2,
   §4, §5, §6).
2. **The use field (illustrative editions).** A short band naming
   finance/controlling, sales, operations and executive as editions
   OnePilot can scope to, so the reader sees the breadth before the
   proof. Illustrative, not promised products (vision §8, lines 91-94;
   guardrail F).
3. **TreasuryCentral, the first scoped edition (lead proof).** The whole
   committed spine relocates here intact: the master line, the
   SAP-treasury category, the cockpit one-screen view, the three apps,
   the SAP proof marks, the live customers. Headed "TreasuryCentral:
   OnePilot, scoped to the treasurer," carrying the "must hold" line
   (vision §7, line 146) and the TMS guardrail "a TMS runs treasury's
   books; TreasuryCentral runs the treasurer's day" (vision §7, line 77).

The apps relationship, stated once so the build does not mis-nest it:
OnePilot is the framework; TreasuryCentral is one scoped edition, the
pre-composed treasurer cockpit; the apps (Market Data Hub, Brisken Smart
Trading, Remittance Advice Gate, Bank Fee Portal) are OnePilot products
that a scoped edition bundles and uses, not children of TreasuryCentral.
A cluster page answers "how {App} on OnePilot solves {buyer problem}";
TreasuryCentral is referenced as "the pre-composed treasury edition that
bundles these apps", never as the app pages' parent (AEO substrate §2,
the apps are sibling product clusters; MDH is the flagship cluster).

### C. Prototype changes (current to target)

Gap to flag first: the prototype carries neither the shadow-integrations
narrative nor any link to the Answers / AEO cluster pages or the Shadow
Integration Report (grep over the 1605-line file: 0 hits for "shadow
integration", 0 links to the cluster pages; the on-page "Answers" block
at line 1138 is an internal FAQ accordion, not the published cluster
hub). The four published cluster pages already link OUT to
`/shadow-integration-report.html` (e.g. mdh-qa-cluster.html line 373).
So the spine the repositioning re-nests is partly absent from THIS build
and must be added, not just demoted: (a) add the Answers hub + cluster-
page links + the Shadow Integration Report to the prototype's IA (item 8
of the blueprint sitemap, currently not built), and (b) place the
shadow-integrations enemy inside the TreasuryCentral edition section, so
the report link the cluster pages already carry resolves to a real
on-site story. Without (a) the cluster pages stay orphaned at any
altitude.

**Title (line 7).** Current: "Brisken TreasuryCentral, a financial-data
platform for SAP, AI native". Target options:

- "OnePilot by Brisken, the Universal UI for the whole working day"
- "Brisken OnePilot, one AI-native surface for your whole working day"

**Meta description (line 9).** Current leads with TreasuryCentral and
calls OnePilot "the AI layer, runs it underneath". Target options:

- "OnePilot is Brisken's Universal UI: one AI-native surface where you
  compose the spaces, apps and data your job needs, with agents acting
  across all of it inside your permissions. TreasuryCentral is its first
  scoped edition, for the treasurer. From Brisken, an SAP Co-Innovation
  Partner."
- "OnePilot from Brisken: one surface for the whole working day,
  assembled by you, run with AI. TreasuryCentral is OnePilot scoped to
  the SAP treasurer. SAP Co-Innovation Partner."

Mirror the chosen line into og:title / og:description (13-14) and
twitter:description (17); these currently repeat the same inversion.

**Hero (lines 814-816).** Current badge "Modern financial-data platform
for SAP. AI native.", H1 "Financial Data. Solved. End to End.", intro
closing "TreasuryCentral takes them off your team." Target: lead with
the platform. H1 toward "OnePilot, the Universal UI" or the cover-line
"One surface for the whole working day, assembled by you, run with AI"
(vision §1); intro resolves to OnePilot and the relief theme, with
TreasuryCentral named as the first edition, not the thing sold. The hero
SVG already centers on a `UNIVERSAL AI / OnePilot` hub (audit, lines
863-864), so align the copy to the existing art, not the reverse.

**"The AI layer that runs it underneath" framing.** Retire the phrase
site-wide; it is the literal carrier of the inversion (lines 9, 14, 926,
952, 1025-1026). Replace with the surface/framework framing everywhere.
The OnePilot panel (1024-1027) moves from "the autonomous layer that
runs it, on SAP BTP" to "the framework: a composable AI-native surface
where you assemble the spaces, apps and data your job needs, with agents
acting across all of it inside your exact permissions." Keep the
permissioned-agent / governed-autonomy spine ("you stay in command",
four-eye, full-audit, "inside your controls"; the command stack runs
lines 1048-1071, with "You stay in command" at 1046, "inside your
controls" at 1047, and the four-eye / segregation-of-duties / full-audit
guards at 1063) verbatim; just attach it to OnePilot-the-surface
(audit §4).

**Platform map (lines 922-996).** Current: a graph titled "TreasuryCentral
platform map" with TreasuryCentral on top (--ny:10%), OnePilot a mid-stack
"The AI layer" node (--ny:43%), three apps below, SAP at the base; locator
numbers it 1 = TreasuryCentral, 2 = OnePilot. Target:

- Rename section / H2 / aria to "OnePilot platform map" (lines 922-923).
- Make OnePilot the top node, framed as the framework (three layers),
  not "the AI layer" (drop the line-952 sub "The AI layer").
- Nest TreasuryCentral as one scoped-edition node within OnePilot, a
  sibling of the other-function editions, with the three apps (Market
  Data Hub, Brisken Smart Trading, Remittance Advice Gate; use these
  exact node strings, lines 957/962/967) nesting under it as that
  edition's spaces.
- Show finance/controlling, sales, operations, executive as further
  edition nodes so TreasuryCentral reads as "first edition", not "the
  product".
- Renumber the 7-tab locator so OnePilot leads: 1 OnePilot, 2
  TreasuryCentral, 3 Market Data, 4 Smart Trading, 5 Remittance, 6 SAP,
  7 Why now (the apps / SAP / Why-now tabs keep their relative order;
  only OnePilot and TreasuryCentral swap, lines 989-995).

This also satisfies the §3 map ask above (TC as control surface, AI as
brain, nodes showing TC spans more than Brisken products); the two map
edits should land together.

**Cockpit section nesting (lines 998-1001, 1024-1056).** Today "cockpit"
belongs to TreasuryCentral and "the autonomous layer that runs it"
belongs to OnePilot. Reassign: "cockpit / Universal UI / surface" is
OnePilot; TreasuryCentral is "the scoped edition for the treasurer". The
command stack ("what you see = TreasuryCentral; OnePilot flies it
underneath", 1054-1071) keeps the command/permission spine but stops
making OnePilot the hidden pilot; in the vision OnePilot is the surface
the user composes and sees.

### D. Re-nesting the committed spine (preserved, not dropped)

- **Shadow integrations** becomes the headline of the TreasuryCentral
  edition section (and must first be added to the build, per §C). The
  platform's enemy is the ten-tab day / application-centric
  fragmentation (the relief theme); shadow integrations is the concrete
  SAP-specific form that enemy takes for the treasurer. This strengthens
  the spine: it becomes a vivid proof of the general thesis rather than
  the whole thesis (reconcile §4).
- **The four AEO cluster pages** (MDH, Remittance, Bank Fee,
  Migration/why-now; ready-to-publish, 0-hit validated) survive
  unchanged at the page level. They already self-brand "OnePilot ·
  {App}" (nav-product OnePilot, eyebrow "OnePilot · Market Data Hub",
  og:site_name "Brisken OnePilot"; zero of the four mention
  TreasuryCentral), which is the correct, broader parent; keep that
  parent. Do NOT re-parent them under TreasuryCentral or re-scope them
  "to the SAP treasurer": MDH, Bank Fee and Migration have buyer strings
  that are not treasurer-exclusive, and narrowing them would cut their
  query fan-out (AEO substrate §2). Their SAP-specific query phrasing is
  correct AEO targeting and must not be diluted to platform-generic
  language; the engines retrieve on the exact buyer string. Nothing on
  the cluster pages needs to change; the repositioning lives one level up.
- **SAP-treasury outbound** (LinkedIn touches, the targeting radar's
  job-post corpus, SAP Store tuning) needs no re-targeting, and the
  per-app cluster pages stay the outbound landing surfaces. A buyer from
  an MDH LinkedIn touch lands on `mdh-qa-cluster`, a remittance touch on
  `remittance-qa-cluster`; that is the direct buyer-string match the
  corpus is built for. The new TreasuryCentral EDITION page is the
  "grow-into" destination shown one level up (with OnePilot above it as
  the bigger story), not the primary outbound landing (reconcile §3).
- **Proof marks stay attached to TreasuryCentral.** SAP Store, ISO 27001
  / SOC 1 Type II, the three live customers do not float up to OnePilot,
  or the platform reads as a finished vertical it is not (guardrail F;
  reconcile §4). Two facts are genuinely platform-level and can sit at
  the OnePilot altitude as current, real evidence: OnePilot runs on SAP
  BTP (trust band, line 915), and the production proof "a financial-
  services group on S/4HANA Public Cloud already governs several data
  domains from one OnePilot deployment" (line 1124). Both are the
  vision's "already real, in production today" evidence (vision §5,
  line 54) and support the platform claim directly, not the kind of
  vertical-completeness overclaim the guardrail bans.
- **The unbuilt Cluster F** (buy-vs-build / no-code orchestration,
  queries 22-25, "the framework under all seven apps") is the AEO
  surface for the new OnePilot PLATFORM story; build and parent it at
  the platform level, not under the TreasuryCentral edition (AEO
  substrate §8, line 106; it is already the next autonomous build, line
  289). The repositioning gives Cluster F its home and is a reason to
  keep it next in the queue, so the new platform headline has AEO
  substrate behind it instead of none.

### E. Sitemap / IA vs the full build blueprint

Concrete diffs against `brisken-onepilot-website-blueprint.md`:

- §1 goals: add goal #0 above the existing three, "tell the OnePilot
  platform story (Universal UI, user-centric)"; the existing three
  (own the shadow-integrations problem, prove it, convert SAP-treasury
  buyers) demote to the TreasuryCentral edition's goals.
- §2 positioning: keep the named enemy, category and master line
  verbatim, re-scoped under a new TreasuryCentral heading; add the
  OnePilot platform positioning (three layers, relief theme, four-slice
  gap) as the new top-level §2.
- §3 sitemap: TreasuryCentral changes from "the cockpit and flagship" to
  "the first scoped edition (the proof)"; OnePilot moves from the
  subordinate "Platform / autonomous layer" row to the top-level
  home/hero; add a "use field / editions" band; and wire in the Answers
  hub + Shadow Integration Report links that the current prototype is
  missing (§C gap).

### F. Guardrails (the vision's overclaim ban, applied)

Apply the vision's verbatim guardrail to all new copy (vision §10,
line 172): "OnePilot is positioned as the surface and the framework, not
as a finished vertical product in any one domain; TreasuryCentral is
positioned as a scoped edition built on it, not as a replacement TMS.
Where a line reads bigger than the product is, cut it before any external
copy is derived." Operationally:

- Do not let OnePilot inherit TreasuryCentral's concrete proof marks
  (SAP Store, ISO 27001 / SOC 1, the three live customers) as
  platform-wide claims (see D). SAP BTP and the S/4HANA-Public-Cloud
  production proof are the exception: they are true at the platform level.
- The other-function editions are illustrative; phrase as "the same
  surface, scoped to X", never as shipped products.
- Adopt the "{edition} on OnePilot" construction (the vision uses
  "TreasuryCentral on OnePilot", vision line 156) wherever the
  edition/platform relationship is named. Line 926 currently uses the
  wrong form ("runs on OnePilot, the AI layer") and is already in the
  §C retirement set; rewrite it to "TreasuryCentral, the treasurer's
  scoped edition of OnePilot" or similar, do not preserve it.
- Carry over the §2 "autonomous" discipline: autonomous applies to
  specific processes, never the treasury or the platform as a whole.
- `/llms.txt` and the capabilities file keep their concrete SAP-treasury,
  SAP-BTP language as the retrievable substance (it matches the buyer
  strings the engines retrieve on); add the OnePilot Universal-UI framing
  as the top-level description only, with the per-app / SAP-treasury
  capabilities listed beneath. Do not replace the SAP-specific
  machine-readable content with platform-generic language; same
  don't-dilute-AEO-strings rule as the visible cluster pages.

### G. Open decisions for Dirk

1. **Headline pair.** Pick the title + meta option set in §C (platform-
   first wording), since it sets the tone for every downstream surface.
2. **Editions to name.** The vision lists finance/controlling, sales,
   operations, executive (vision §8, lines 91-94). Confirm which to show
   on the map and the use-field band; naming an edition Brisken is not
   near may invite "when can I have it" questions.
3. **BTP placement, not whether.** BTP is a true platform-level
   substrate (OnePilot runs on SAP BTP, line 915), so the question is
   WHERE to surface it, not whether it is platform-true. The open BTP
   decision (Djalma 09:44) is about how prominently to lead with it at
   the OnePilot level versus the TreasuryCentral edition level; this
   stays consistent with §D treating line 1124 as direct platform
   evidence. Confirm placement.
