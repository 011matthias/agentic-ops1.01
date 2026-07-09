# SAP-surfaces repositioning copy: PartnerFinder + Discovery Center

**For:** Dirk (review + publish)
**From:** UnpauseAI
**Date:** 2026-07-07
**Status:** draft for review. Both surfaces sit behind your SAP partner login, which we do not hold. We hand you paste-ready copy; the click is yours, the same way we did LinkedIn.

This is the second half of the one-company repositioning. The LinkedIn
profile and company page (copy dated 2026-06-29), the live brisken.com
hero, and these two SAP surfaces all carry the same story: lead with the
treasury outcome, OnePilot as the governed AI layer underneath,
TreasuryCentral as the cockpit, live with customers today. You asked to
"update this as well with the same story as you have on brisken.com and
LI"; this is that, mapped to each SAP field.

**The spine (identical across all surfaces):**

- **TreasuryCentral** is the single screen treasury works in (cash,
  investments, debt, FX, market data, governance) on your SAP data.
- **OnePilot** is the AI layer underneath, on SAP BTP, that operates the
  applications and keeps every step governed. Your team sets the rules
  and approves the exceptions; the OnePilot agents do the routine work;
  the audit trail stays intact.
- **Applications live today:** Market Data Hub, Brisken Smart Trading
  (BST), Remittance Advice Gate, Bank Fee Portal.
- **Trust marks:** SAP Co-Innovation Partner, SAP PartnerEdge, part of
  SAP Industry Cloud for Financial Services and Commodities, listed on
  the SAP Store, built on SAP BTP, ISO 27001, SOC 1 Type II.
- **Retired naming to purge everywhere:** "Trade Automation" and
  "TraderPlus" both become **Brisken Smart Trading (BST)**.

One accuracy note before the copy. The PartnerFinder editor (section 1) was
opened live and walked field by field, so its field names and character caps
below are what the editor actually shows, not a guess. The Discovery Center
mission (section 2) has not been opened, so its field labels still follow SAP's
standard mission schema; map each block to the matching field when you open the
editor, and where a label differs the block header says what it is for.

---

## 1. SAP PartnerFinder (editor id 0001663611)

Your ask #1. The profile is a partner directory entry: a headline, an
about, an offerings list, industries, and your SAP competencies. Below is
each field in the spine.

**Live-editor note (inspected 2026-07-08).** The editor for 0001663611
(BRISKEN LLC) was opened live and walked field by field. Structure:
**At-a-Glance** holds the **Heading**, the **Description**, a **media slot**
(image or video), and the contact email; **Services** and **Resources** are
their own tabs; **Focus Industries** and **Partner Website** are already
populated. Caps are live-confirmed: Heading ~130 chars, Description 400,
Services 1500. **Save** (draft) and **Publish** (live) are separate buttons, so
a save does not go public. The editor does not accept browser automation (it
registers a change only on real manual typing), so paste and type each block
yourself. The **Locations** tab was not opened; if it carries fillable fields,
send a screen-read and we fit copy to it.

### Heading (At-a-Glance, required, ~130-char cap)

> Treasury, run by AI. Governed SAP data, live with customers.

60 characters. The live box shows 70 remaining with this line in, so the real
cap is ~130, not the ~68 first assumed; either the short line above or a fuller
variant fits. The prior heading ("AI powered process automation for on the SAP
BTP") also carried a grammar slip worth clearing.

### Description (At-a-Glance, required, 400-char cap)

Live cap confirmed at 400 characters. Replace the old OnePilot codeless-framework
blurb with this (387 chars, fits):

> Brisken builds AI-powered treasury applications that run on your SAP data, live with customers today. TreasuryCentral is the single cockpit for cash, investments, debt, FX, market data and governance. Underneath it, OnePilot is the governed AI layer that operates the apps and audits every step. SAP Co-Innovation Partner, on the SAP Store, built on SAP BTP, ISO 27001 and SOC 1 Type II.

### Profile image (At-a-Glance media slot)

The current media graphic is the old OnePilot chat-box diagram. Replace it with
the on-brand hero we produced: `sap-assets/partnerfinder-hero.webp` (WebP,
2560x1440, ~155 KB, under SAP's 500 KB image cap). Use Change File on the media
slot, then Save. It carries the same spine: TreasuryCentral cockpit, OnePilot
governed AI layer, the four live apps, SAP trust marks.

The slot also accepts a YouTube or Vimeo URL in place of the image. **A demo film now
exists** (built 2026-07-09): 58 seconds, 1920x1080, six real Market Data Hub screens
lifted from your own `BRISKEN MDH WALKTHROUGH DEMO SLIDES 250710.pptx`, cut to the same
spine as everything else. Four candidate screens were dropped because they showed a
customer name (BASF), a colleague's email address, or a named individual in a log column.
Nothing in it is generated, redrawn or upscaled.

The slot takes one asset, so it is the hero image **or** the film, not both. The film is
the stronger of the two. It needs a YouTube or Vimeo URL on a Brisken account first;
unlisted is enough. A square cut exists for LinkedIn. Replacing the six stills with a
live screen recording is a further upgrade and is specced in
`mdh-demo-recording-shotlist.md`.

### Services (its own tab, required, 1500-char cap)

The Services tab is a single free-text field, cap 1500, prompt "Provide a
detailed description for the value of your company and the services it
provides." Paste this (1322 chars, fits), which keeps the A/B split and turns
the retired "TraderPlus" into Brisken Smart Trading. Markers are `A)` / `B)`
(not `< A >`) so a form sanitizer cannot strip the angle brackets:

> We build AI-powered treasury applications that run on your SAP data, live with customers today. Our solutions are SAP certified and built in co-innovation with SAP on the SAP Business Technology Platform (BTP).
>
> A) BRISKEN CLOUD SOLUTIONS: TreasuryCentral is the single cockpit for cash, investments, debt, FX, market data and governance, on your SAP data; OnePilot is the governed AI layer underneath that operates the applications and audits every step. (1) Market Data Hub (MDH): market data from Bloomberg, Refinitiv, CME Group, 360T, Deutsche Börse and OANDA into SAP, one governed feed, no code. (2) Brisken Smart Trading (BST): trade capture from venues such as Refinitiv FXall and Bloomberg FX GO straight into SAP TRM, no manual re-key. (3) Remittance Advice Gate: AI reads remittance messages and posts them into SAP S/4HANA. (4) OnePilot codeless framework: build your own apps and automation on SAP BTP without a line of code.
>
> B) BRISKEN CONSULTING SERVICES: (1) custom cloud development on SAP BTP and HANA. (2) SAP Treasury and Cash Management projects: deep expertise in treasury and risk management, cash management, payments and electronic banking, from design to implementation and support. (3) BRISKEN RapSoDy turnkey projects: fixed-scope, fixed-price SAP treasury and cash-management implementations.

### Resources tab (10 of 10 slots used, live tab read 2026-07-09)

**Edit / Add Resource dialog.** A card is not a file upload into SAP. Each has four
fields: **Link to Resource** (a URL; a brochure card points at a hosted PDF, a Store
card points at its SAP Store listing), **Resource Name**, **Short Description** (hard
cap **155 chars**, confirmed on the empty dialog), and a **Resource Type** dropdown
(Brochure / SAP Reference / Event / Packages). No SAP file size or format limit, only
a working URL.

The tab is **full: all 10 slots are used**, and six of the ten are Market Data Hub.
Our six brand one-pagers are hosted at `resources.brisken.com` (dedicated Vercel
project; each ~260 KB, one A4 page, zero em-dashes). Only two map onto existing
brochure cards; the rest need a shelf rebalance (below), so this is not a
drop-into-open-slots job.

**Decision (2026-07-09): rebalance the shelf.** The tab was ~60% Market Data Hub and
carried no TreasuryCentral, OnePilot, Remittance or Bank Fee. Remove four MDH-skewed
cards (none is deleted from SAP Store, only from this Resources shelf) and give each
core product a card.

**Remove these 4 current cards:**

- `02 - Market Data Hub: Briefing` (redundant with the MDH Overview)
- `05 - SAP Insider Webinar: Market Data Governance` (dated event, MDH-heavy)
- `08 - SAP Store: MDH for European Central Bank (ECB)` (niche MDH Store variant)
- `09 - SAP Store: MDH for Commodities` (niche MDH Store variant)

**Final 10-card shelf** (product-forward). Do column: K keep as-is, E edit text, N add
new, R rename. The number is the name prefix (cosmetic order); adjust if you prefer.

| # | Resource Name | Short Description (<=155) | Type | Link to Resource | Do |
|---|---|---|---|---|---|
| 01 | `01 - TreasuryCentral: The Cockpit` | One screen for cash, investments, debt, FX, market data and governance, on your SAP data, with every move logged. | Brochure | `https://resources.brisken.com/treasurycentral.pdf` | N |
| 02 | `02 - OnePilot: The Governed AI Layer` | The AI layer that operates your SAP treasury apps on SAP BTP, governed and audited, in production today. Build your own, no code. | Brochure | `https://resources.brisken.com/onepilot.pdf` | N |
| 03 | `03 - Market Data Hub: Overview` | One governed market-data feed into SAP, no code. Bloomberg, Refinitiv, 360T, CME and more, governed and distributed to SAP and non-SAP. | Brochure | `https://resources.brisken.com/market-data-hub-deck.pdf` | E (old card 01) |
| 04 | `04 - Brisken Smart Trading: Overview` | Straight-through trade capture from FXall, Bloomberg FX GO, 360T and BidFX into SAP TRM and FAM. Governed, no manual re-key. | Brochure | `https://resources.brisken.com/smart-trading-deck.pdf` | E+R (old card 04; drop "SAP TPI") |
| 05 | `05 - Remittance Advice Gate: Overview` | AI reads unstructured remittance emails and attachments and posts them into SAP S/4HANA, matched and governed, no manual keying. | Brochure | `https://resources.brisken.com/remittance-advice-gate.pdf` | N |
| 06 | `06 - Bank Fee Portal: Overview` | Analyze and validate bank fees against your agreements inside SAP, with variance flags and a full audit trail. | Brochure | `https://resources.brisken.com/bank-fee-portal.pdf` | N (confirm copy first) |
| 07 | `07 - SAP Blueprint: Brisken Market Data Hub` | keep the existing SAP-authored text | SAP Reference | keep existing link | K (old card 03) |
| 08 | `08 - SAP Store: Market Data Hub` | keep the existing text | Packages | keep existing link | K (old card 06) |
| 09 | `09 - SAP Store: Brisken Smart Trading` | Straight-through processing for FX trading into SAP TRM. Integrate venues such as FXall, Bloomberg FX GO and bank sites, governed end to end. | Packages | keep the existing SAP Store link | R (old card 07 TraderPlus) |
| 10 | `10 - BRISKEN RapSoDy: Rapid Solution Deployment` | keep the existing text | Packages | keep existing link | K |

**Which file each card points at (decided 2026-07-09).** Cards 03 and 04 point at the
**full decks**, taken from the latest SharePoint versions (`Brisken - Market Data Hub
2026-07.pdf`, 12 pages; `Brisken - Smart Trading 2026.pdf`, 10 pages), not at the concise
one-pagers. The other four brochure cards point at the one-page sheets, which have no deck
equivalent. Both files are re-hosted at `resources.brisken.com` because SAP needs a public URL
and a SharePoint link is gated. The Smart Trading deck arrived with three em-dashes (slide 3's
venue list, slide 6's two stat attributions) against a house style of zero; the hosted copy was
corrected at source and re-exported, the SharePoint original left untouched, so the two now
differ by that punctuation alone. Both deck URLs were verified live (200, zero em-dashes, no
"TraderPlus") on 2026-07-09. The walk-in pack for the whole shelf is `sap-resources-cards.html`.

Net mix: MDH keeps 3 cards (Overview + SAP Blueprint + SAP Store), BST 2 (Overview + SAP
Store), and TreasuryCentral, OnePilot, Remittance Advice Gate, Bank Fee Portal one each.
Renaming the SAP Store BST listing itself (card 09) is your click on SAP Store; here we
only fix the card text off "TraderPlus". Bank Fee Portal (06) is the one sheet not
verbatim-sourced, eyeball it before publish.

### Focus Industries, Website, contact (leave as-is)

Focus Industries is already populated with a sensible set (Banking, Insurance,
Chemicals, Consumer Products, Industrial Manufacturing and more); no change
needed. Partner Website is already www.brisken.com. Contact email untouched.

### Keywords / competencies

Neither the Services tab (one free-text field) nor the Resources tab (cards)
exposes a separate keyword field, so the keywords already sit inside the
Services copy above. If the unopened Locations tab has a keyword or tag field,
these fit: SAP treasury, SAP TRM, market data integration, S/4HANA, treasury
automation, Brisken Smart Trading, remittance automation, bank fee analysis,
SAP BTP, no-code orchestration, AI agents for finance, financial data
governance. Leave existing SAP competencies and certifications as they are.

### PartnerFinder field map (live editor)

| Field | Where | Cap | Action |
|---|---|---|---|
| Heading | At-a-Glance | ~130 chars | replace |
| Description | At-a-Glance | 400 chars | replace |
| Media image | At-a-Glance | 500 KB image | replace with partnerfinder-hero.webp |
| Services | Services tab | 1500 chars | replace |
| Resources | Resources tab | 10/10 slots full, Short Desc 155 | improve 01, repurpose 02 to TreasuryCentral, replace+rename 04, rename 07 off TraderPlus; Remittance/BankFee/OnePilot need a freed slot |
| Focus Industries | At-a-Glance | controlled list | leave (populated) |
| Partner Website | At-a-Glance | url | leave (www.brisken.com) |
| Locations | Locations tab | not opened | send a screen-read |

---

## 2. SAP Discovery Center mission 3904

Your later add ("one of their largest lead sources"). The 2026-06-17 SAP
audit found mission 3904 consulting-framed and carrying the retired
"Trade Automation" / "TraderPlus" names, with zero reviews, no
screenshots, no demo, no datasheet, and a description that opens on the
STP acronym instead of the buyer's problem. Two kinds of fix: the copy
below (reframe to the outcome spine, purge the old names), and the
content-gap actions after it (screenshots, demo, datasheet, reviews),
which need your assets.

**Scope check before you paste.** The audit read this as the
trade-automation mission (BST). Confirm that when you open the editor. If
the mission is actually broader than trading, promote the OnePilot
platform paragraph above the BST detail; if it is trading-specific, the
copy below is already in the right order.

### Mission title

> Automate trade capture into SAP TRM with Brisken Smart Trading

### Short description (the line under the title)

> Bring trades from your execution venues into SAP Treasury and Risk Management automatically, governed end to end, with no manual re-keying. Brisken Smart Trading runs on OnePilot, Brisken's AI orchestration layer on SAP BTP.

### Description / overview (reframed from the consulting version)

> Treasury teams that trade FX, money-market and derivatives still re-key most of those trades into SAP by hand, from the execution venue or a spreadsheet into SAP TRM. The re-key is slow, it is a control risk (two systems, two chances to fumble a number), and it breaks whenever a venue or a format changes.
>
> Brisken Smart Trading removes the re-key. It captures the trade at the execution venue and creates the deal in SAP TRM straight through, with validation and a full audit trail. Your team sets the rules and approves the exceptions; the OnePilot agents handle the routine flow.
>
> Brisken Smart Trading is one application on OnePilot, Brisken's governed AI orchestration layer on SAP Business Technology Platform. The same layer runs the Market Data Hub (provider feeds into SAP) and the Remittance Advice Gate (AI posts remittances into SAP S/4HANA). TreasuryCentral is the single cockpit your team works in across all of them.

### What it does (capabilities)

- Straight-through trade capture from the execution venue (360T, FXall, Bloomberg FX GO and others) into SAP TRM and FAM.
- Configured, not coded: no ABAP and no per-venue custom interface to maintain.
- Governed by design: validation, four-eye approval, segregation of duties, and a full audit trail on every deal.
- A managed interface that survives venue and format changes, so the flow does not break when a provider changes a field.
- Runs inside your SAP estate on SAP BTP, not beside it.

### Use cases

- A treasury desk executing FX on 360T posts every deal into SAP TRM without touching a keyboard twice.
- A group consolidating trades from several venues governs them from one place, on one audit trail.

### Why SAP (trust footer)

> Brisken is an SAP Co-Innovation Partner, listed on the SAP Store, built on SAP BTP, ISO 27001 and SOC 1 Type II.

### Tags / keywords

SAP TRM, trade automation, straight-through processing, 360T, FXall,
treasury, SAP BTP, S/4HANA, no-code integration.

### Content-gap actions (not copy: these need your assets or your click)

These close the IMPROVEMENT-band gaps the audit found. They are the
difference between a listing that reads well and one that converts:

1. **Purge the old names.** Replace every "Trade Automation" and
   "TraderPlus" string on the mission with "Brisken Smart Trading (BST)".
2. **Add screenshots.** TreasuryCentral and the trade-capture flow. A
   listing with no visual reads as unfinished.
3. **Add a demo.** No demo video exists yet (brisken.com, the Rome hub,
   SharePoint and any prior Loom checked 2026-07-08, none found; the only clips
   are the private Universal-UI vision reveal, which stays off SAP surfaces). The
   cheap path: a 60 to 90 second screen capture of TreasuryCentral plus one app
   flow (Brisken Smart Trading or the Remittance Advice Gate), hosted unlisted on
   YouTube or Vimeo, then dropped into this mission's demo field and the
   PartnerFinder At-a-Glance media slot. We can script it; the recording is your
   screen.
4. **Attach a one-page datasheet (PDF).** We can produce this from the
   BST copy above on your word.
5. **Seed reviews.** Zero reviews on both SAP listings is the single
   biggest trust gap. The review requests reach your real customers, so
   they are yours to send; the paste-ready ask text is in section 5 below.

---

## 3. What we kept out, and why

Same two exclusions as the LinkedIn copy, and they matter more here
because these surfaces lean hardest on SAP goodwill.

- **Verve / the Universal-UI vision, by name.** It stays the in-room
  reveal, off every public surface. Naming it on an SAP listing pulls the
  page off the treasury outcome that the SAP buyer came for.
- **Anti-SAP framing** ("one vendor's frozen best practice"). The whole
  motion here runs on the Co-Innovation trust mark, the Store listing and
  BTP. That line is for a private room with a non-SAP-aligned buyer, never
  on an SAP-owned page.

---

## 4. Publish checklist

| Surface | What changes | Gate |
|---|---|---|
| PartnerFinder (0001663611) | Headline, About, Offerings, Industries, Keywords | Your partner login; you paste, or we walk it in on a screen-share |
| Discovery Center mission 3904 | Title, Short description, Description, Capabilities, Use cases, Tags; purge retired names | Your partner cockpit; same as above |
| Discovery Center assets | Screenshots, demo, datasheet, review seeding | Needs your assets / customer relationships |

All copy is within SAP's field limits at the lengths written, uses no
em-dashes and none of the buzzword filler, and matches the voice already
live on brisken.com and LinkedIn. Tell us to proceed and we either walk
the changes in with you on a screen-share or you paste each block into the
matching field. Either way the click is yours.

---

## 5. Review-seeding ask (paste-ready, for you to send your customers)

This closes item 5 in section 2. Zero reviews is the biggest trust hole on
both SAP surfaces, and one line from a real customer outweighs anything we
write on the page. Below is the message, in your voice, for you to send. The
requests reach your own customers, so the send stays yours.

**Who to send to.** Your two or three warmest live customers, ideally ones
already running the Market Data Hub or Brisken Smart Trading in production.
One genuine review on the Discovery Center mission moves the needle most; the
SAP Store listing is the second target if a customer is willing to do both.

**How to use it.** Fill the `[brackets]`, pick the app each customer runs,
drop your SAP Store listing link where marked. Send from your own address,
one customer at a time, never a blast.

---

**Subject:** Would you leave a short SAP review for Brisken?

> Hi [First name],
>
> Your team has had [the Market Data Hub / Brisken Smart Trading / your OnePilot apps] live on your SAP for a while now. SAP lists us in two places, the Discovery Center and the SAP Store, and neither carries a customer review yet. If the solution has earned it, a couple of lines from you there would carry more weight with other treasury teams than anything we can say about ourselves.
>
> It takes about two minutes. Each page has a spot to leave a rating and a short comment:
>
> - Discovery Center: https://discovery-center.cloud.sap/missiondetail/3904/
> - SAP Store: [your SAP Store listing link]
>
> A sentence or two on what it changed for you, less manual re-keying, one governed feed, whatever stood out, is plenty. No pressure at all if now is not the moment.
>
> Thank you either way,
> Dirk

---

**Voice notes.** Register A: you are asking a favor, so it stays soft and
gives an easy out. It references the working relationship through the live
solution, not through performed warmth. Zero em-dashes, no buzzwords. If you
would rather point a customer at one surface only, keep the Discovery Center
line and drop the SAP Store one, that mission is the priority. The Discovery
Center link is the live mission 3904; the SAP Store link is the one field you
fill, since that listing URL is yours, not in our hands.
