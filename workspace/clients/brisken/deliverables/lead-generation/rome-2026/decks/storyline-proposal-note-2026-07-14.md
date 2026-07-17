# Product decks: storyline proposal, 2026-07-14

Your feedback: the four decks are hard to present because they all run the
same storyline, the problems are not qualified, and a reader without your
background cannot follow the sent PDF alone.

The proposal: keep the visual system exactly as it is, and give each deck its
own presenting spine, so you give four different talks. Two decks are rebuilt
as proposal files next to the originals for you to compare; the other two are
mapped and wait on your calls below. Nothing in SharePoint was touched.

## The four spines

| Deck | Spine | Status |
|---|---|---|
| Digital Co-Worker | Story-led: qualified problem, bank-transfer example as the fix, "what it is" background slide, production proof | Built: `brisken-digital-co-worker-storyline-proposal.pptx` (13 slides) |
| Smart Trading | The clock: sourced minutes-vs-seconds stats on the problem slide, before/after as the fix, one trade walked step by step | Built: `brisken-smart-trading-storyline-proposal.pptx` (12 slides, 10 visible) |
| Market Data Hub | Show the machine: real product screens, pipeline detail from the 46-slide walkthrough (anomaly methods, change requests, audit logs, scheduler) | Mapped, waiting on flags 1 and 4 |
| MDH Commodities | Follow one price: the worked curve case from start to finish, component sourcing made concrete | Mapped, waiting on flags 2 and 6 |

Shared slides stop repeating verbatim: each deck keeps three anchor
governance cards (audit trail, no code, ISO 27001 and SOC 1) and swaps the
other three for product-specific controls; the identical problem diagram now
appears in at most one deck; redundant slides are hidden, not deleted, so
every change is reversible in PowerPoint.

## What was added, and its sources

- Smart Trading problem slide now carries: 10-15 min per manual FX trade
  (Association of Corporate Treasurers) and ~90% spot FX automation (LSEG),
  moved up from the old slide 6.
- Digital Co-Worker problem slide carries the app-switching stats from your
  OnePilot vision doc sources (APA 40%, HBR 1,200 toggles a day).
- Digital Co-Worker gains a proof slide: the chemicals company
  funding-request case and the agricultural company remittance gate, both
  anonymized, wording from the existing use-case decks.
- New Smart Trading slide 4 walks one FX trade: decision, request, approval,
  execution, booked in SAP reconciled to source.

## Your calls (6)

1. **MDH problem stat.** The resources site already publishes: 71% of 41 US
   SAP-treasury job ads describe hand-run integrations (our own market
   research, labeled as such). Put it on the MDH problem slide, or keep it
   website-only?
2. **Commodities anonymization.** Copy says "two ports" and "two delivery
   points", never the real names. Confirm that level, or set your own.
3. **Smart Trading pain line.** Optional line: "We keep meeting desks where
   the venue executes and the treasury system never hears about it." Use it,
   or drop it given your open venue-gap conversations?
4. **Product screenshots.** 30 real MDH screens were screened: 18 clean, 12
   rejected (customer identifiers, real user names, platform labels we
   exclude). Approval sheet: `.scratch/mdh-shots/contact-sheet.html`. Approve
   the ones you want in the MDH deck.
5. **Commodities partners wall.** It is the only deck still showing the
   partners slide; MDH and Smart Trading have theirs hidden. Keep or hide?
6. **Commodities problem number.** The problem slide is qualified
   structurally (components per curve, per port, per tenor). A real count
   from a live setup (how many components, markets, curves) would land
   harder. Can you supply one?
7. **Per-deck audience and channel** (from the 2026-07-15 conversation):
   for each deck, who is the reader, and where does it get sent or shown?
   The intro slide and problem framing tune to that answer.
8. **The value figure.** If the Shark Tank framing (who this is for, what
   is at stake per day or month) should appear on a slide, the number has
   to come from you; we will not put an unsourced figure in front of a
   client.
9. **The closing ask: demo, assessment, or both?** The decks close on the
   twenty-minute demo ask, which matches the June messaging spine. Your
   2026-07-14 protocol with Jochen says assessments return to the website
   and materials, with the Quick Assessment as the door-opener. Should the
   product decks carry a second closing path ("or start with the free
   Quick Assessment"), or does the assessment CTA stay on consulting
   surfaces only?

## Added 2026-07-15, from your audio feedback

Both built proposals now open with a "THE SHORT VERSION" intro slide: what
this is, what it replaces, what you get, then "the next page is where you
are today." This is the executive-summary-in-one-slide you described, so a
cold reader who only gets a link has the thread before the first stat. The
Smart Trading architecture diagram is visible again per your "explicit
diagram" point. Deck counts: Smart Trading 13 slides (11 visible), Digital
Co-Worker 14. The intro slide becomes part of the standard for the MDH and
Commodities rebuilds and the collateral generators.

Both built decks passed the banned-content scan: no customer names and none
of the platform labels you excluded from demo material.

## Added 2026-07-16: the three-deck matched set

Market Data Hub, Digital Co-Worker and Smart Trading now sit beside their
SharePoint mirrors as a matched demonstration set, all built to the R1
storyline standard, so you can flip through the three and decide whether to
adopt it. MDH Commodities is still only mapped (flags 2 and 6).

- **Market Data Hub, full new build** (`brisken-market-data-hub-storyline-proposal.pptx`,
  15 slides, 13 visible). The "show the machine" spine: THE SHORT VERSION intro
  at slide 2; the problem slide rewritten to the Datafeed-RFC / ABAP pain from
  the resources site; a new slide 3 showing a real anomaly-catch product screen
  with three cyan callouts; THE FIX retitled WHAT IT IS; the redundant WHY IT
  FITS slide hidden; the three pipeline step-pairs enriched from the walkthrough
  (named providers and the five anomaly methods; calculated rates and rate
  types; change requests, audit logs, distribution targets and the scheduler);
  the safe grid swapped to three MDH controls (five anomaly checks / change
  requests with a reason / audited to the target) alongside the three shared
  anchors; the runs-on chips reordered; the swapped footer numbers fixed on the
  renumber pass.
- **Digital Co-Worker and Smart Trading**: only the dual-close CTA was added;
  the rest of each deck is untouched.

**Flag 9 (the CTA) is answered on all three, recommended and pending your yes.**
Each closes on one slide with the twenty-minute demo headline plus one
subordinate line, "Or start with the Quick Assessment." Plain text, no
hyperlink (the assessment web page does not exist yet). The word "free" appears
nowhere. If you want the assessment path off the product decks, striking that
one line reverts each close to demo-only.

**Flag 4 (screenshots).** The MDH deck uses one screening-verified-clean screen
as the demonstration pick: the anomaly notification table (GBP FX instruments,
user shown as system, no customer identifiers). The full approval sheet with
all 18 clean shots is at `.scratch/mdh-shots/contact-sheet.html`; tell us which
others you want and we swap them in.

**Flag 1 (the 71% stat).** It is on the MDH problem slide, footnote-sized and
muted with its honest label ("market research, not a Market Data Hub
performance metric"), so it is there for the reader but easy to strike.

All three passed the banned-content scan (no customer names, none of the
excluded platform labels).

## Restructured 2026-07-16: three distinct bodies

The first pass above kept the shared marketing skeleton and only added content
to it, so the three decks still ran the same storyline. This pass gives each
deck a genuinely different body. The shared bookends stay (hero, THE SHORT
VERSION, the safe grid, the dual close); the middle of each deck now diverges.

- **Market Data Hub becomes a screen-led product tour.** The generic
  middle (fits-together diagram, how-it-works overview, three text step-pairs,
  3-card what-it-is, runs-on) is cut. In its place: a 5-node WHAT IT IS ribbon,
  then six real product screens, one per pipeline stage (connect a provider,
  the data lands, a bad rate caught, the four-eyes change request, mapped to
  SAP, audited to the target), each cyan-framed with three callouts. The machine
  is shown, not described. 12 visible slides.
- **Digital Co-Worker becomes one request's journey.** A single funding
  request is followed end to end across four beat slides, carried by a journey
  rail, a growing chat thread, and a filling audit ledger, then widened to the
  team and paid off by the two production cases. The card slides are cut or
  merged. 13 visible slides.
- **Smart Trading becomes a stopwatch trilogy.** The manual clock (amber,
  10-15 min per trade, ACT), the automated clock (cyan, under a minute), the two
  clocks side by side (~12 min vs <1 min). The redundant third trade-walk is
  cut. The three badged numbers keep their named sources; the stopwatch times
  are illustrative. 11 visible slides.

**Flag 4 grows.** MDH now shows six real product screens instead of one, each a
per-shot approval. All six are screening-verified clean (no customer
identifiers, no PII, no excluded platform labels). A few are real product
captures with their own internal whitespace or a status icon; approve or swap
any of them, the full 18-clean sheet is at `.scratch/mdh-shots/contact-sheet.html`.
Flags 1 (the 71% stat) and 9 (the dual close) are unchanged from above.

Three per-shot observations for that review, all inside the real captures, none
of them ours to fix: the Exchange Rates Viewer shot (screen 2) shows USD-to-USD
rows with rates like 17.46, which a treasury reader may query; the mapping shot
(screen 5) is clipped mid-label at its bottom and right edges in the source
capture; and the Target Audit Log shot (screen 6) has rows whose integration
date sits weeks before the rate date. If any of these bother you, swaps are on
the 18-clean sheet.

## Presenter pass 2026-07-16: slide 2 grown, every hand-off explicit

All three decks were audited slide by slide as a presenter would speak them,
so each page answers the one before it and hands to the next. Slide counts
unchanged (MDH 14/12 visible, DCW 13, ST 12/11); nothing in SharePoint touched.

- **THE SHORT VERSION grew.** A fourth row, "Who it is for", names the reader
  per deck, and the closing line now sets up the deck's own spine: MDH "Then
  the machine itself: one pipeline, six real screens.", DCW "Then one request,
  followed end to end.", ST "Then the same trade on our clock."
- **Market Data Hub.** The WHAT IT IS ribbon closes on "Each of the next six
  pages is a real screen of this pipeline, in order." Each screen page's
  eyebrow now carries its pipeline stage (INGEST / VALIDATE / GOVERN /
  DISTRIBUTE / AUDIT), so the tour walks the ribbon. The safe grid's "Audited
  to the target" card points back at screen six instead of restating it. The
  problem slide's source list now says LSEG (was Refinitiv), matching the rest
  of the deck.
- **Digital Co-Worker.** The problem slide closes on "So watch one request.",
  handing into the journey. The AI chip left the WHAT IT RUNS ON row; AI stays
  in the prose, and the four remaining chips match the Smart Trading deck.
  The last three footers were relabeled from "OnePilot" to "Digital Co-Worker,
  part of OnePilot".
- **Smart Trading.** The venue list now appears once (slide 6); the
  architecture page calls back to it ("The venues you just plugged in") and
  closes on "The next page is the full control set." instead of pre-listing
  the control grid. The who-we-are stat reads 5 steps, matching the five-step
  trade walk. One em-dash removed from slide 6.
- **The close slide, all three decks.** The logo now uses your on-dark
  variant (white wordmark), replacing the navy wordmark that was near
  invisible on the dark close. The headline "Built to stay done." was our
  agency's own tagline and had no business in a Brisken deck; each close now
  stamps its own deck's promise instead: MDH "One governed feed.", DCW
  "Busywork, done.", ST "The trade books itself." The twenty-minute demo ask
  and the Quick Assessment line (flag 9) are unchanged.

## If approved: where the standard rolls out

Every client-facing deck we hold, grouped by how the change is made.

**Product decks (SharePoint 2026_PPTX, per-deck spine as above):**

| Deck | Slides | State |
|---|---|---|
| Digital Co-Worker | 11 | proposal built (13) |
| Smart Trading | 11 | proposal built (12) |
| Market Data Hub | 13 | waiting on flags 1, 4 |
| MDH Commodities | 9 | waiting on flags 2, 6 |
| Digital Co-Worker + Trade Automation, combined | 19 | your call: restyle to match the two singles, or retire the combined deck |

**Call collateral (generated, so the standard lands in the generator once
and every future prospect deck inherits it):**

| Deck | Slides |
|---|---|
| TreasuryCentral, generic | 15 |
| TreasuryCentral, Sanofi | 10 |
| TreasuryCentral, Zalando | 10 |
| Use case: Intercompany Funding Request | 9 |
| Use case: Remittance Advice | 9 |
| Use case: Market Data Monitor | 9 |

**Your call whether the standard applies:**

- MDH Walkthrough Demo (47 slides): a live-demo script, a different genre
  from a product deck. Recommend leaving it, it is also our screenshot
  source.
- OnePilot for FSI Overview (40 slides): FSI is a current priority segment;
  if this deck is still shown to FSI prospects it should be next in line.
- OnePilot Solutions Overview (31) and Company Briefing (28): still in use,
  or superseded?

**Recommend retiring instead of restyling:** the 2024-era MDH Overview (18),
Trade Automation Overview (20), and the standalone Digital Co-Worker source
deck (13, known mis-save) are superseded by the 2026 decks above.
