# Rome 2026 · TreasuryCentral call collateral

Per-call demo decks for Tier 1 booth follow-up leads who replied and asked
for a call. One tailored TreasuryCentral overview per prospect, built in the
same dark-cockpit visual system as the product decks (MDH / Smart Trading /
Digital Co-Worker). Dirk presents these live; nothing is sent on its own.

| File | Prospect | Call | Tailoring |
|---|---|---|---|
| `brisken-treasurycentral-sanofi.*` | Ian Haegemans, Sanofi (Treasury Process & Analytics, Global Process Owner) | confirmed next week Friday ~16:00 | problem framed on one global process; proof line on standardise-once, governed and analytics-ready |
| `brisken-treasurycentral-zalando.*` | Lokesh Doggala, Zalando; +Adela Dolezalova (external, via Trillion), +Maria Moeller | Dirk books end of next week or later | problem framed on deliver-on-SAP-fast; proof line on an S/4HANA move, stated conditionally |

Lokesh's title is left off on purpose. Three of our sources disagree: the booth
registration says "Treasury Consultant", the Tier-1 send list says "Senior
Treasury Consultant", and Dirk's 2026-07-09 forward says "SAP Consultant,
Corporate Solutions". None has been verified.

The proof line reads "An S/4HANA move", never "your migration". Nothing on file
says Zalando has one in flight; the newest evidence is a consenso S/4Finance
readiness check published 2018-09-20.

**No SAP BTP anywhere in these decks**, per Dirk's directive (Planner: "Exclude
BTP from all demos"). Both decks named it on slides 5 and 9 until 2026-07-09;
the source now says "runs inside your SAP landscape" and "runs on SAP's own
cloud". Re-check with a text extraction after any rebuild.

`.pptx` = editable source, `.pdf` = send-ready. Ten slides: cover, problem,
the cockpit, three engines, architecture, governance, OnePilot, proof, who we
are, close.

## Content sourcing (every claim traced)

- Cockpit framing and the "market data, trading, AI automation and
  orchestration ... all live with customers today, not on a roadmap" line:
  Dirk's own Rome booth follow-up email, 2026-07-08.
- Three engines, architecture, governance (audit trail, segregation of duty,
  ISO 27001 / SOC 1): the approved MDH / Smart Trading / Digital Co-Worker
  decks.
- "One cockpit for the whole treasury", "live in weeks, not a rebuild",
  S/4HANA migration timing: the TreasuryCentral homepage (onepilot-site).
- "Teams like Evonik and RWZ build on OnePilot directly": Dirk's hottest-leads
  send pack (VW note).

Build script: `.scratch/deckgen/build-treasurycentral.js <sanofi|zalando>`
(shares the primitives in `build-mdh.js`). Render to PDF/PNG via
`.scratch/deckgen/pdf-export.py` and `render-one.py`.
