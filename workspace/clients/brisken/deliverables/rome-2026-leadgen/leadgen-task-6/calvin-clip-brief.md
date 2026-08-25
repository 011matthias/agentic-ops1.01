# Calvin clip brief: "A bank transfer, from an email"

**Asset class:** Lane-1 forwardable, soft CTA. Third of the three named in
`specs/1-spec/p2-bant-lead-generation.md` next_steps (the MDH teardown and the
ABM one-pager template are built; this one had no build evidence).
**Runtime:** 90 seconds. **Status:** brief ready for Dirk's review; not yet recorded.
**Prepared:** 2026-07-09.

Everything on screen traces to Brisken's own Digital Co-Worker deck, slide 8
("Use Case: Create Bank Transfer from an Email request"). Nothing here is invented
product behaviour. Sources are listed in section 9.

---

## 1. The job this asset does

It gets forwarded. That is the whole specification.

A treasury buyer does not forward a pitch. They forward a thing that makes them
look informed to the person one level up who has to sign. So the clip has to be
legible with no context, no audio, and no prior knowledge of Brisken, and it has to
end without asking for anything expensive.

The booking ask lives in the message that carries the clip, never in the clip.
That division is what makes it forwardable: the recipient can pass it on without
passing on a sales ask they did not make.

## 2. Who watches it, and the objection it has to answer

Primary: the treasurer or the SAP-treasury owner in the accounts the radar has
already triggered. Secondary, and the one that actually matters, is whoever they
forward it to: a finance lead who did not ask for an AI product and is defaulting
to no.

That second viewer has one objection, and it is not "does it work". It is **"what
happens when it is wrong, and who was in control when it was".** An AI clip that
shows only speed confirms their fear. The clip therefore spends its most valuable
seconds, the middle, on the approval and the audit trail, not on the automation.

Brisken's own deck already carries this line as a footnote: *"Every step is checked
and logged, and you can put a person in the loop wherever you want one."* In the
clip it is promoted from footnote to the central beat.

## 3. What is actually on screen

The real flow, in Brisken's order (deck slide 8): an email funding request arrives;
Calvin fetches the mail, summarizes it and suggests the action; fetches the cash
position from S/4HANA Cash Management; creates the memo record; confirms success in
chat and suggests the next action. The user stays in the OnePilot chat box the whole
time.

Two things are added to that flow for the clip, both true to the product and both
absent from slide 8's static rendering:

- **A visible approval gate** before the memo record is written. Slide 8 implies it;
  the clip shows the human clicking it.
- **The audit-trail line** appearing as the record is booked.

Nothing else is added. No architecture diagram, no logo wall, no roadmap.

### Demo payload

Use the demo tenant's own values. If the tenant has none, seed it with a
recognizably synthetic request (a round figure, a fictional entity code, a
non-existent counterparty). Every number on screen is demo data and is never
described as a customer figure.

## 4. Shot list

Times are cumulative. Silent-first: the clip is designed to play with sound off, so
the on-screen text is the script. The optional voice track in section 5 adds nothing
the text does not already carry.

| # | In | Out | What we see | On-screen text |
|---|---|---|---|---|
| 1 | 0:00 | 0:05 | An email sitting in an inbox. Subject line legible: a funding request with an amount and a deadline. Nothing moves. | *This lands on a Tuesday.* |
| 2 | 0:05 | 0:14 | Fast, unglamorous: three windows open in sequence. Mail, the SAP cash position, the memo-record entry screen. A cursor keying digits. | *Today someone reads it, checks the cash position in SAP, and keys the memo record.* <br> sub: *A workspace assembled by hand.* |
| 3 | 0:14 | 0:22 | Hard cut to the OnePilot chat box. The user types one plain sentence and hits enter. | *Or they ask.* |
| 4 | 0:22 | 0:34 | Calvin reads the mail, returns a two-line summary, and proposes the action. | *It reads the request and proposes the action.* |
| 5 | 0:34 | 0:47 | Calvin pulls the cash position from S/4HANA Cash Management. The figure lands in the chat, sourced and timestamped. | *It pulls the cash position from S/4HANA.* <br> sub: *Calvin builds the workspace around the request.* |
| 6 | 0:47 | 1:00 | **The beat.** An approval prompt. The cursor hovers. A person clicks approve. Only then does anything move. | *Nothing is written until a person says go.* <br> sub: *Four-eye approval and segregation of duties where you want them.* |
| 7 | 1:00 | 1:12 | The memo record is created in S/4HANA. The record ID appears. A log line writes itself underneath. | *It books the memo record. Every step is logged.* |
| 8 | 1:12 | 1:20 | Calvin confirms in chat and suggests the next action. The user has not left the chat box. | *It confirms, and suggests what is next.* |
| 9 | 1:20 | 1:30 | End card. Static. | See section 6. |

Shot 2 is the one to resist cutting. Without the manual path, shot 4 reads as a
chatbot demo. With it, shot 4 reads as a job that disappeared.

Shot 6 gets the longest hold of any single action in the clip. That is deliberate,
and if the edit runs long, take the seconds from shots 4 and 7, never from 6.

## 5. Voice, captions, and words to avoid

Captions are burned in, not a sidecar track: the clip autoplays muted in a LinkedIn
feed and is watched muted in an email client. The on-screen text in section 4 *is*
the caption. Keep each card under about eight words so it is readable in the two
seconds it holds.

A voice track is optional and adds trust only if a Brisken person records it in
their own voice. A synthetic voice on an AI product clip is a self-inflicted wound.
If it is recorded: speak the on-screen lines nearly verbatim, use S/4HANA and
memo record without apology (the audience uses those words daily), and stop talking
during shot 6 so the click carries it.

Banned on screen and in voice: *revolutionary, seamless, effortless, unlock, empower,
game-changing, next-generation, leverage, robust, streamline,* any sentence
containing *"not just X, but Y"*, and the word *simply*. Also banned: the phrase
*"AI-powered"* as a standalone claim. The clip shows the AI doing a job; a label
adds nothing and invites the objection.

No em-dashes in any on-screen text.

## 6. The end card, and what may be claimed on it

Three lines, in this order:

> **A bank transfer, from an email.**
> Calvin built the workspace. You stayed in control. Every step was logged.
>
> Calvin is an agent on OnePilot, running inside your SAP landscape.
> Brisken is an SAP Co-Innovation Partner.
>
> `brisken.com/onepilot`

No booking link, no calendar, no "request a demo". One first-party URL.

**What must not appear on this end card:**

- **SAP Business Technology Platform, or BTP.** Dirk's standing directive, on the
  board as "Exclude BTP from all demos": leave BTP out of all demo material. The
  deck's own "runs on SAP's own cloud, BTP, so it sits inside your landscape, not
  beside it" carries the trust signal without the name, so the card says "inside your
  SAP landscape". The first cut of this clip shipped with the BTP line and had to be
  re-rendered; the directive lives in Planner, not in any file the write gates read.

- **"Listed on the SAP Store."** False for this product. The 2026-06-17 Store audit
  found exactly two buyable Brisken listings, Market Data Hub and Trade Automation.
  Neither the Digital Co-Worker nor the Remittance Advice Gate is on any SAP
  channel. This is the single most likely accuracy slip on this asset, because the
  line is correct on the MDH teardown and would be copied across without thinking.
- **A named customer.** The proof for this exact flow is a chemicals manufacturer
  running an AI funding-request process on S/4HANA On-Prem, and it is anonymized in
  Brisken's decks. Customer *logos* were cleared for use on 2026-06-17; the mapping
  of a specific logo to a specific use case was not. Keep it anonymized until Dirk
  clears the mapping.
- **ISO 27001 / SOC 1 Type II**, unless Dirk confirms the certificate scope first.
  The catalog records this as "compliance posture stated on app slides", which is
  Brisken asserting it about themselves, not a verified certificate we have read.
  It is fine on a slide Brisken presents; putting it on an asset that will be
  forwarded to a risk-averse finance buyer raises the evidentiary bar.

## 7. What we call the agent

Two of Brisken's own sources disagree, and the clip cannot straddle them.

The Messaging Spine (16 Jun, "Dirk approves") and the TreasuryCentral restyle
blueprint both rule out *"digital co-worker"*: it reads junior, it is crowded by the
"digital workforce" category, and it is the exact frame an AI-wary finance buyer
distrusts. The recommended public term is **OnePilot Agents**. Yet the Digital
Co-Worker deck, still carrying that label throughout, was sent to Adidas on
2026-07-07.

The reconciliation is clean, because the two names are not competing for the same
slot:

- **OnePilot Agents** is the category. It is what the product is.
- **Calvin** is the name of one agent, and it is already on screen in the chat box
  in Brisken's own slide 8.

So the clip says *"Calvin is an agent on OnePilot"* and never says *"digital
co-worker"*. That keeps the on-screen artefact honest, retires the deprecated label,
and needs no new asset from Brisken.

The clip also does not lead with OnePilot the platform, and does not mention
TreasuryCentral. Dirk's 2026-06-20 direction was explicit: in acquisition contexts
the platform is the enabler behind the outcome, not the headline. The outcome here
is the bank transfer.

## 8. Where the clip goes

It is the soft CTA for the two campaigns that the p2 spec pairs it with (spec §9B,
"Remittance / Digital Workforce"): the **Remittance Advice Gate** campaign and the
**AI Digital Workforce** campaign. It also has one live, named home right now:
Adidas, Carol Tse, whose confirmed interest is AI on OnePilot for intercompany
funding and remittance advice, and who already holds the Digital Co-Worker deck.

**The title in Planner conflates two products.** The task is called
"Calvin / Remittance", but the flow above is a funding request becoming a bank
transfer. It is not remittance advice. Remittance Advice Gate is the separate app
where an unstructured remittance email is read and posted into SAP cash application,
proven at an agricultural customer on ChatGPT. The two share a story (an AI gate,
governed, posting into SAP) which is why the spec buckets them together, and that is
a sound reason to lead the Remittance campaign with this clip. It is not a reason to
describe the clip as a remittance demo. If the Remittance campaign is ever run at
volume, it earns its own 45-second cut built on the agricultural proof. That is a
second asset, not this one.

**Carrier messages are not drafted here.** The emails and Sales Navigator messages
that deliver the clip are the comms-draft class and are held until an explicit ask
plus Dirk's sending-identity gate.

## 9. Where every claim comes from

| Claim on screen | Source |
|---|---|
| The five-step flow, in this order | `context/Products/Digital Co-Worker.pptx`, slide 8 |
| The agent is named Calvin | Same slide; "Calvin" labels the chat participant |
| Cash position comes from S/4HANA Cash Management | Same slide, node labels |
| Checked, logged, person-in-the-loop | `.scratch/deckgen/build-digital-coworker.js`, slide 5 footer |
| Runs inside your SAP landscape | Digital Co-Worker deck, slide 7 (BTP named there; the name is withheld per Dirk's exclude-BTP directive, the placement claim is not) |
| SAP Co-Innovation Partner | Digital Co-Worker deck, slide 4 (About / Partnerships) |
| Chemicals customer, AI funding-request process, anonymized | `context/lead-generation/evidence/brisken-product-catalog.md`, customer proof section |
| Not on the SAP Store | Store audit 2026-06-17, recorded in the catalog and `aeo-substrate.md` §8 |
| "OnePilot Agents", not "co-worker" | Messaging Spine 2026-06-16; `brisken-treasurycentral-restyle-blueprint.md` §2 |

No timing claim, no headcount claim, and no percentage appears in this clip. None of
those is sourced, and a soft-CTA forwardable does not need one.

## 10. Open questions for Dirk

1. Can a Brisken person screen-record the live Calvin demo? Path A in the runbook
   depends on it, and it is worth a week of waiting. If not, Path B ships a labelled
   schematic instead.
2. ISO 27001 / SOC 1 Type II: is there a certificate, and what is in scope? Answer
   decides whether the end card carries the third trust line.
3. Does the chemicals customer clear a named reference for this flow? If yes, the end
   card gets materially stronger and the clip gets a tenth shot.
4. "Digital Co-Worker" is on a deck that went to Adidas two days ago. Confirm the
   clip may retire the label while the deck still carries it, or the two assets will
   read as two products.
