# OnePilot product UI kit

Recreation of the OnePilot application (`brisken-demo.app.onepilot.ai`,
`brisken-swt-qa.app.onepilot.ai`) from the screenshots supplied 2026-07-27.

- **Shell.jsx** — the spaces sidebar (lowercase letterspaced `onepilot` wordmark, pill search,
  grouped space list, signed-in user with a blue-outline Sign Out), the top bar (hamburger,
  page title in Poppins Regular, inline search on list views, round red assistant mark), and
  the assistant side panel.
- **Screens.jsx** — `HomeView` (centred welcome line), `AuditView` (Filter pill, refresh +
  export icon buttons, six-column audit table), `InvestmentView` (Overview / Requests tabs,
  net-position pies, position timeline, positions table with green net and red redemptions).
- **appds.jsx** — app primitives: `Icon` (Lucide), `AppButton`, `IconButton`, `AppCard`,
  `DataTable`, `Pie`.

Click any space in the sidebar to switch views, the hamburger to collapse it, and the red
circle to open the assistant.

**Palette** is the `[data-theme="app"]` scope in `tokens/colors.css`: canvas `#131314`,
surface `#1E1F20`, input `#292A2C`, text `#E3E3E3`, muted `#90959A`, accent `#1876D2`,
mark `#E8352E`, chart `#1876D2 / #069669 / #D97708 / #7C3AED`.

**Caveats.** Sampled from screenshots, not source: exact type sizes, paddings and the
timeline chart geometry are approximations. Icons are Lucide, a flagged substitution for the
product's own icon set. The product's screens beyond these three (Function Composer, Element
Builder, Sources, Integration Monitor detail) are not built.
