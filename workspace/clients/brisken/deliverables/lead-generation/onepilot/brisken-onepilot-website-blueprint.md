# OnePilot Website Build, Blueprint

Status: blueprint + prototype (2026-06-16). The prototype is a
self-contained HTML homepage in this folder
(`brisken-onepilot-website-prototype.html`); the production build path
is in section 7. Owner: UnpauseAI for Brisken. Implements the p2
marketing plan (the "Marketing Plan" tab of
`lead-gen-strategy-2026-06-12.html`) and the AEO substrate
(`context/lead-generation/outreach-assets/aeo-substrate.md`).

## 1. Goal

A Brisken / OnePilot marketing site that does three jobs:

1. Own the problem ("shadow integrations") so buyers and AI search both
   associate that phrase with OnePilot.
2. Prove it with Brisken's own research and SAP-ecosystem trust.
3. Convert SAP-treasury buyers into booked demos, and feed the AI-search
   answer layer that makes the outbound campaigns land warmer.

## 2. Positioning (source of truth for all copy)

- **Named enemy: "shadow integrations."** Hand-keyed data and home-built
  scripts moving market data, trades, bank files and remittances in and
  out of SAP. Fragile, unowned, unmonitored.
- **Category: governed, no-code financial-data orchestration for SAP.**
- **Master line: "Replace your shadow integrations with governed
  orchestration."**
- **Proof spine:** SAP Co-Innovation Partner, listed on the SAP Store,
  ISO 27001 / SOC 1 Type II, runs on SAP BTP, data partners (Bloomberg,
  Refinitiv, 360T, OANDA, CME), live customers (FSI S/4HANA Public Cloud,
  agricultural ChatGPT remittance, chemicals AI funding-request).

## 3. Sitemap

| Page | Job |
|---|---|
| Home | The full narrative on one page (this prototype) |
| TreasuryCentral | The cockpit and flagship: one screen for cash, investments, debt, FX, market news and governance on SAP data |
| Applications | Per-app pages, leading with the Wave 1 trio (Market Data Hub, BST, Remittance Advice Gate); the rest on the same platform |
| Platform / autonomous layer | How OnePilot runs it: ingest, govern, distribute; the no-code framework on SAP BTP; OnePilot Agents; security |
| The Shadow Integration Report | The research asset: the lead magnet and the AEO authority page |
| AI Digital Workforce | Governed AI for finance ops, the email-to-bank-transfer example (cross-sell) |
| Why now | ECC 2027 / S/4HANA migration as the buying window |
| Answers | The AEO hub: buyer-question Q&A clusters with FAQPage schema |
| Trust / About | Partner badges, certifications, customers |
| Book a demo | The conversion endpoint |
| Machine-readable | `/llms.txt`, `/onepilot-capabilities.md`, FAQPage JSON-LD on every Answers cluster |

## 4. The four marketing moves, mapped to site features

| Move | Where it lives on the site |
|---|---|
| Name the problem | Hero, the Problem section, the master line in nav / footer / meta description |
| Publish the benchmark | The Shadow Integration Report page, a hero stat, and the citations in Answers |
| Name and prove the AI | OnePilot Agents (the autonomous layer), governance-first, one customer metric (Dirk-gated) |
| Make the SAP relationship work | Trust strip on every page, SAP Store deep-links, co-sell-ready CTA, Built-on-BTP |
| AEO substrate (enabler) | The Answers hub, extractable 40 to 60 word answers, FAQPage JSON-LD, `llms.txt` |

## 5. Design system

The prototype reuses the deck's visual language (palette, system font,
card / flow / callout components, dark and light). Final Brisken brand
assets (logo, exact brand colors, typeface) are TBD from Brisken; the
prototype uses the deck palette as a stand-in so the layout and content
read clearly now. Required quality-of-life: dark/light toggle, keyboard
jump (Ctrl/Cmd+K), print stylesheet, a visible last-updated stamp. Zero
em-dashes, no emoji in navigation (deliverable rules).

## 6. AEO and SEO plan

- Each Answers cluster: H2/H3 in the buyer's exact words, a self-contained
  40 to 60 word answer block (reads correctly with no surrounding
  context, because the engine extracts the passage alone), a comparison
  table (OnePilot vs custom Datafeed config vs single-vendor interface),
  sourced stats with dates, and FAQPage JSON-LD.
- The differentiator is always no-code, multi-vendor, governed,
  SAP-listed. Never "SAP cannot do this."
- Third-party presence (SAP Community answers, review profiles) per the
  AEO substrate; real participation only.
- `/llms.txt` and a capabilities file so AI agents can parse OnePilot
  without rendering JavaScript.

## 7. Tech and build path

- **Prototype (now):** self-contained HTML in this folder, matching the
  deck. Content-layout fidelity, not production.
- **Production (next):** build on the proper client stack in
  `agentic-dev1` (the landed-client split), multi-page, brand assets
  applied. A public marketing site, so no gated access is needed.
- **Publish on brisken.com or a subdomain:** Dirk-gated (owned property),
  the same gate class as the AEO substrate and the SAP Store edits.

## 8. What we need from Brisken

- Brand assets (logo, colors, typeface) and the domain or subdomain.
- One named customer and a usable metric for a published reference
  (Dirk-gated).
- SAP co-sell status (active account-exec referral, or listed only) to
  finalize the trust and CTA framing.
- Sign-off to publish.

## 9. Honest notes

- The benchmark stat on the site is from a first sample of 21 live
  SAP-treasury job ads (17 described the shadow-integration work; see
  `context/lead-generation/outreach-assets/shadow-integration-benchmark.md`). Widen to a
  publishable figure before the site goes live. The prototype shows the
  real first-sample number, labeled as such.
- Brand colors are a stand-in until Brisken's assets arrive.
- No contact email is invented; the prototype converts via "Book a demo."
