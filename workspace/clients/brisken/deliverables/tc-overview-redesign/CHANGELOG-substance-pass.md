# TreasuryCentral Solutions Overview (NEW); substance pass changelog

**Deck:** `NEW - Brisken - TreasuryCentral Solutions Overview 2026-07-21.pptx` (31 slides)
**Date:** 2026-07-21
**Goal:** a reader who does not know treasury or SAP can follow every slide. Substance added, never filler. Every added claim traces to a source line below.

## Sources (the only facts the deck may use)

- **REF sN** = Dirk's reference deck `OnePilot Solutions Overview 2026.pptx`, slide N (text extracted verbatim).
- **MDH / ST / DCW / OV** = the deckgen specs `market-data-hub.yaml` / `smart-trading.yaml` / `digital-co-worker.yaml` / `overview-revision.yaml`.
- **MSG** = `deckgen/MESSAGING.md` (Dirk's 8 Sanofi comments + naming lock).

## Status: Dirk's 2026-07-21 review integrated. 0 placeholders remain.

---

## Dirk review integration (2026-07-21, later pass)

Dirk reviewed the NEW deck in SharePoint and left 7 comments + 4 in-place text
edits. All folded back into the source (`build2.py` / `build.py`) and re-rendered.
His comments came off slides 8, 9, 10, 12, 18, 19, 25 (PowerPoint slide numbers).

**His 4 verbatim text edits (adopted as-is):**
- **S22 Remittance Advice Gate**, step 3: "Maps it to your SAP naming." ->
  "Validates it against your SAP customer master and invoices."
- **S23 Cash Flow & Exposure Hub**, before-line reorder: "...comes in Excel, CSV
  and PDF from departments that do not use SAP." (format list moved ahead of the
  department clause).
- **S30 Credit Data Hub**, step 2: "rating, score and attributes" ->
  "rating and credit report attributes"; step 3: "Feeds SAP Credit Management
  (SAP's credit-limit module) or any risk system." -> "Feeds SAP Credit
  Management and business partner, or any risk system." (his gloss removal kept).
- **S31 ESG**: run-boundary only, no text change.

**His 7 comments (resolved):**
- **S8 hierarchy** ("TreasuryCentral is just one use case of OnePilot;
  connectors should be more than just SAP; size fine-tuning"): TreasuryCentral
  sub changed to "one workspace on OnePilot"; added the caption "OnePilot
  connects your SAP and non-SAP systems alike."; band spacing re-balanced.
- **S9 functional** ("remove SAP OneExposure, too specific; generalize instead
  of SAP: on-prem, private & public cloud"): destination "SAP & SAP OneExposure"
  -> "SAP: on-prem, private & public cloud"; "Non-SAP" line strengthened. Applied
  the same de-specifying on S13 ("SAP OneExposure" -> "Exposure & risk systems").
- **S10 governance** ("grounded in, HITL, AI keywords missing"): intro now reads
  "...the AI included: it is grounded in SAP, not free-floating, and keeps a
  human in the loop on the moves that matter."; four-eyes card adds "A human
  stays in the loop (HITL)..."; footer adds "AI grounded in SAP, with a human in
  the loop."
- **S12 Market Data Hub** ("emphasize SAP AND non-SAP; data governance and
  compliance emphasis"): step 4 -> "Pushes it into SAP and non-SAP systems...";
  added "Assembling the audit trail by hand." to the freed column.
- **S18 Digital Co-Worker** ("fine-tune to the value it adds and the workload it
  takes off; governance emphasis"): freed column rewritten to the concrete work
  removed ("Reading each request, checking balances, keying into SAP, writing
  back."; "The copy-paste across a dozen systems, all day."); step 3 adds "every
  action logged."
- **S19 DCW functional** ('SAP process steps or documents, not "SAP postings";
  generalize memo records'): destinations "SAP postings" -> "SAP process steps",
  "Memo records" -> "Records & notes"; the S18 CONNECTS-TO strip updated to
  match ("outputs SAP process steps, records, confirmations, replies").
- **S25 success stories** (he supplied the before/after): the 3 [NEEDS INPUT]
  placeholders are now filled with his own words (see below).

---

## Per-slide changelog

Only substantive additions are listed. Design-only slides (cover, dividers, hierarchy, customer wall) carry no new factual claims and are omitted.

### S3 Short version
- Four "what it is / replaces / get / for" lines. Source: **OV** sv-rows (short-version patch), verbatim intent.

### S4 About Brisken (rewritten, grounded)
- Headline "An SAP co-innovation partner, live in production." Source: **REF s3** ("SAP Co-Innovation Partner").
- "SAP Co-Innovation Partner and Partner Edge member; SAP Industry Cloud for Financial Services and for Commodities." Source: **REF s3** (Partnerships list).
- "OnePilot runs on SAP's own cloud, inside your landscape." Source: **MSG** (the old platform naming maps to "on SAP's own cloud"); "inside your landscape" = **MDH** sv-rows ("sits inside your landscape, not beside it").
- Gloss "book of records (the official system where the numbers are final)." Plain-language gloss of a term used in **MSG** spine.
- "Deployed across financial services, chemicals, food & drink, oil & gas, commodity and agricultural treasuries." Source: **OV/MDH/ST/DCW** platform-context captions (industry list).
- "Market-data partners: 360T, CME, Refinitiv, Bloomberg, OANDA. Headquarters: Houston, TX." Source: **REF s3** (Partnerships + Offices).

### S7 The platform (hub)
- Spine paragraph "We run on top of your SAP systems and data..." Source: **MSG** "The spine".
- Card "Systems connected: Banks, market data, counterparties, email and spreadsheets, joined once." Source: **REF s9** (Data Sources list).
- Card "Data flowing where it's needed: Pushed or pulled to every target, on a schedule or on demand: SAP and non-SAP systems." Source: **REF s7/s12** (push/pull; "delivery to any target system"). *(Rewritten in verification to replace a generic line.)*
- Card "Your record stays in SAP... We connect your systems and push the updates into it." Source: **MSG** ("your book of records stays where it is"). *(The earlier "we do not hold your data" was removed in verification: REF s24 shows a Brisken portal that stores data, so the absolute claim was unsupported.)*

### S10 Governance (NEW slide)
- Four control definitions in plain language. Source: **REF s9 + s13** governance list ("Audit Trail and Compliance", "4-eye principle / Segregation of Duties", "Anomaly Alerts and Error Notifications", "Manage by exception").
  - Audit trail = "Every action is logged and can be reviewed later, end to end."
  - Four-eyes / segregation of duty = "The person who enters something is not the one who approves it."
  - Anomaly alerts = "The system flags what looks wrong before it posts, not after."
  - Manage by exception = "People only touch the cases that need judgment."
- "Certified to ISO 27001 and SOC 1 Type II." Source: **REF s13** ("ISO 27001 and SOC1 Type II").

### S9 / S13 / S16 / S19 Functional overview diagrams (grounded lists)
- Platform sources/destinations. Source: **REF s9** (Data Sources / Data Destinations / Integration Technologies).
- Protocol strip "RFC/OData, AMQP, SFTP, REST, HTTP, email, Excel add-in." Source: **REF s9/s13** (Integration Technologies).
- MDH sources (Bloomberg/Refinitiv/360T, central banks, exchanges) + dests (SAP ECC & S/4HANA, SAP OneExposure, analytics, non-SAP). Source: **REF s13** + **MDH** usecases.
- ST sources (360T, FXall, Bloomberg FX GO, Citi Pulse, BidFX; any OMS/TMS; banks/brokers) + dests (SAP TRM & FAM, ECC, S/4HANA, SAP Analytics Cloud). Source: **REF s16**.
- DCW sources (emails/requests, remittance advices/invoices, funding requests, bank statements) + dests (SAP postings, memo records, confirmations, replies). Source: **DCW** func-diagram-dcw + fd-dest-list.

### S12 Market Data Hub (problem / mechanism / freed)
- Gloss "Market data means the FX and interest rates, commodity prices and credit ratings a treasury runs on." Source: **MDH** UC1 (FX & interest rates), UC "Commodity Price Curves" (prices), UC4 (credit ratings). *(Reworded in verification: "rates" alone was imprecise for commodity prices and credit ratings.)*
- Problem "Your rates live in a dozen places, lined up by hand. Re-keying, fixing formats, chasing bad values, reconciling before month-end." Source: **MDH** pb-body / UC1 col1.
- Mechanism steps (pulls from Bloomberg/Refinitiv/360T/OANDA/central banks; checks each value; calculates inversions/triangulation; pushes into SAP on a schedule or on demand). Source: **MDH** UC1 + Anomaly-Catch UC.
- Connects-to strip. Source: **MDH** UC1 col2 (any protocol: API, ODATA, SFTP, email, Excel add-in; SAP ECC and S/4HANA).

### S15 Smart Trading (problem / mechanism / freed)
- Gloss "Autonomous trading means the trade carries itself from the decision to the booked deal, with no manual re-keying." Source: **ST** sv-rows + **MSG** (trading -> autonomous trading).
- Problem "You trade on a venue, then you book in SAP... re-keying the ticket, chasing the approval, building the deal entry." Source: **ST** pb-headline / UC1 col1.
- Mechanism (reads exposure from SAP positions; sends request to venue; matches the fill; books in SAP Treasury). Source: **ST** UC1 col1 (the six-step journey).
- Gloss "exposure (the money at risk from currency or price moves)." Plain gloss added on first use (verification finding).
- "Manual FX runs 10 to 15 minutes a trade (The Association of Corporate Treasurers)." Source: **ST** pb-body + UC1 (ACT attribution spelled out per verification).
- Connects-to strip. Source: **REF s16** + **ST** UC1 col2.

### S18 Digital Co-Worker (problem / mechanism / freed)
- Gloss "It does the busywork of a request across your systems: read it, check the balance, open SAP, key it in, write back." Source: **DCW** pb-body.
- Problem / mechanism / freed. Source: **DCW** sv-rows + pb-body + features-dcw.
- Connects-to strip (email/files/forms -> SAP S/4HANA & ECC; outputs postings/memo records/confirmations/replies). Source: **DCW** func-diagram-dcw.

### S21 Use case: Intercompany Funding Request
- Gloss "intercompany funding: when one company in a group lends cash to another, run through the group's own in-house bank." Plain gloss of **DCW** UC1 terms.
- Before (chemicals group, subsidiaries email the in-house bank, analyst keys it in, spans email/SAP in-house cash/live cash position, month-end spike). Source: **DCW** UC1 col1 + Challenges.
- Six steps (reads email; pulls amount/currency/entity/value date; checks group cash position + intercompany limit; drafts funding memo in SAP; routes for approval; posts and confirms). Source: **DCW** UC1 col1, verbatim mechanism.
- Checkpoint "A person approves the moves that matter." Source: **DCW** UC1 col2.

### S22 Use case: Remittance Advice Gate
- Gloss "remittance advice: the note a payer sends listing which invoices a payment covers." Plain gloss (term from **REF s26** / **DCW** UC2).
- Before (arrives by email, body or attachment, every layout; a person keys it in). Source: **REF s26** (Description + Challenges).
- Steps (reads any format; identifies and structures; maps to SAP naming; delivers to SAP S/4HANA or a processor like Serrala or HighRadius; flags odd for review). Source: **REF s26** (AI-Powered Transformation; "Send data to SAP S/4HANA. Or to ... Serrala, BPI, HighRadius").
- Checkpoint "A person sets the guardrails and reviews the exceptions." Source: **REF s29** ("set guardrails, remove human from the process").

### S23 Use case: Cash Flow & Exposure Hub
- Gloss "exposure: the money at risk from currency or price moves, which treasury hedges." Plain gloss.
- Before (data from departments not on SAP, in Excel/CSV/PDF; converted and mapped by hand for cash and hedging). Source: **REF s22** (Description + Challenges).
- Steps (collects any source/format; validates and maps to SAP naming; integrates with cash and exposure management in S/4HANA or ECC; enriches for analytics; monitors completeness/timeliness). Source: **REF s22** (Application Features).
- Checkpoint "A person acts on the position; the assembling is done." Derived from **REF s22** (monitor + decision-support framing).

### S25 Success stories (grounded skeleton)
- FSI: "Financial Services / SAP S/4HANA, public cloud / a single OnePilot deployment governing several financial-data domains / one platform to govern all data integrations and controls." Source: **REF s28** (verbatim: "SAP S/HANA Public Cloud", "Single OnePilot Deployment - Supporting Multiple Financial Data Domains", "one platform to govern all data integrations and controls").
- Agriculture: "SAP S/4HANA, private cloud / Remittance Advice Gate, run by the Digital Co-Worker / guardrails set, the person taken out of the routine path." Source: **REF s29**.
- Chemicals: "SAP S/4HANA, on-premise / the intercompany funding process, run by the Digital Co-Worker / a complex process with many SAP touch-points, fully automated." Source: **REF s30**.
- **REPLACED** before/after now filled from Dirk's 2026-07-21 comment (verbatim): FSI "Replaced a manual solution."; Agriculture "Replaced an expensive custom third-party solution."; Chemicals "Replaced a manual solution." Intro reworded to "Three production deployments, each replacing a manual or custom-built way of working." Source: **Dirk review comment, S25**.

### S28 Appendix: Legacy vs OnePilot
- Left column (custom-built/cumbersome/unstable; technical issues/maintenance; inflexible; old technology, no AI/in-memory/cloud). Source: **REF s8** (Issues table).
- Right column (off-the-shelf, no custom code; managed subscription, low maintenance; 100% configurable, connects to any app/process/data source; cloud app, no hardware cost, scalable, AI-ready). Source: **REF s8** (Solution table).

### S29 Appendix: Bank Fee Portal
- Gloss "a bank fee statement is the bank's own record of what it charged you." Plain gloss.
- Before (formats CAMT.086, XML, Twist BSB, each bank's own; read and checked by hand; derived fees hard to catch). Source: **REF s23** (Challenges: "CAMT.086, XML, Twist BSB, as well as bank proprietary format").
- Steps (reads any format; validates and enriches to calculate derived fees; sends to a Bank Fee Analyzer, TMS or analytics; one dashboard for on-demand analysis). Source: **REF s23** (Application Features).
- Header credited to "THE BANK FEE PORTAL" (its own app), not the Digital Co-Worker (verification finding: REF s23 presents it as a standalone OnePilot app).

### S30 Appendix: Credit Data Hub
- Gloss "a credit rating is an agency's score of how likely a counterparty is to pay." Plain gloss.
- Before (several agencies, some API, some only PDF; re-keyed by hand; a stale rating = a limit decision on old data). Source: **REF s24** + **MDH** UC4.
- Steps (collects by API or PDF; extracts rating/score/attributes into structured data; feeds SAP Credit Management or any risk system; alerts on a rating change). Source: **REF s24** + **MDH** UC4 ("into SAP Credit Management").
- SAP Credit Management glossed as "SAP's credit-limit module."
- Header credited to "THE CREDIT DATA HUB" (verification finding).

### S31 Appendix: ESG Data Hub
- Gloss "ESG data is environmental, social and governance scores used for reporting." Plain gloss.
- Before (many providers, many formats, plus internal unstructured reports; reconciled by hand each cycle). Source: **REF s25** (Description + Challenges).
- Steps (collects any source/provider; normalizes/structures/enriches; feeds SAP Sustainability Control Tower or other tools; runs on a schedule, monitored). Source: **REF s25** (Application Features).
- SAP Sustainability Control Tower glossed as "SAP's ESG-reporting module."
- Header credited to "THE ESG DATA HUB" (verification finding).

---

## [NEEDS INPUT] placeholders: RESOLVED (0 remaining)

All three sat on **S25 Success stories**. The substance-pass source deck carried
no before/after, so each card showed a visible placeholder. Dirk's 2026-07-21
review supplied the before/after in his own words, and all three are now filled:

1. **Financial Services (SAP S/4HANA public cloud)**; "Replaced a manual solution."
2. **Agriculture (SAP S/4HANA private cloud, Remittance Advice Gate)**; "Replaced an expensive custom third-party solution."
3. **Chemicals (SAP S/4HANA on-premise, intercompany funding)**; "Replaced a manual solution."

These are qualitative (what each replaced), not numeric; that is what Dirk
provided, and nothing was invented beyond his wording. Optional (not blocking):
a measured metric on any app slide would land harder still, but none is required
and none was fabricated.

---

## Verification record

Every added claim was checked two ways before this deck shipped:

1. **Slop scan**; zero corporate-thesaurus words from the anti-slop ban list.
2. **Adversarial source-trace**; seven independent checkers, one per slide cluster, each re-read the source files and flagged any claim not traceable to a line. Six issues were found and all six fixed:
   - "we do not hold your data" (unsourced, contradicted by REF s24) -> removed.
   - "the right value ... at the right moment" (generic) -> replaced with the sourced push/pull mechanism.
   - MDH "rates" (imprecise for prices/ratings) -> "rates, prices and ratings".
   - "exposure" unglossed on first use -> glossed at S15.
   - "(ACT)" bare acronym -> "The Association of Corporate Treasurers".
   - Appendix hubs credited to the Digital Co-Worker (hierarchy blur) -> re-credited to each app by name.
   - Plus: all em-dashes removed (house deliverable standard).
