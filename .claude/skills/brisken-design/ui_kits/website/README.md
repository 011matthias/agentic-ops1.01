# Website UI kit

Two surfaces, one chrome:

- **HomeScreen.jsx** — `brisken.com`, the TreasuryCentral marketing site: hero + research
  stat, customer wall, credentials run, OnePilot platform map, dark demo CTA, proof section
  with real certification badges, and the Answers accordion.
- **OnePilotScreen.jsx** — `onepilot.brisken.com`, the platform site: ink hero with three
  sourced stats, application grid (live vs illustration), governance triple, and the
  treasurer's day before/after table.
- **SiteChrome.jsx** — sticky header (nav, "Live on SAP", ☼/☾ toggle, Book a demo) and the
  full footer. Click the logo to switch between the two sites, as the real sites cross-link.
- **DemoDialog.jsx** — the demo request dialog, including its consent line and sent state.
- **ds.jsx** — resolves the design-system component bundle; falls back to inline equivalents
  so the kit renders standalone.

**Fidelity note.** The two live sites' stylesheets could not be read — only their rendered
text. Copy, section order and IA are faithful to the sites; the visual treatment (type scale,
card style, spacing, dark mode) is the **deck's** system applied to that content. Treat it as
brand-correct, not pixel-verified. The light/dark toggle exercises the `[data-theme="dark"]`
scope in `tokens/colors.css`.

Not built, for lack of any visual source: the OnePilot **product** UI (the composed
workspace surface itself) and the orbit/map animations on both sites.
