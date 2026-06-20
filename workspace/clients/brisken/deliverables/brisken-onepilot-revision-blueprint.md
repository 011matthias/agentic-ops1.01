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

## 8. Open decision (owner only)

Keep the "hosted on SAP BTP" claim, or drop it? Djalma questioned
whether we should keep stating it. This is a positioning and contractual
call, not a copy edit; resolve before the BTP line ships anywhere new.
(Djalma 09:44)
