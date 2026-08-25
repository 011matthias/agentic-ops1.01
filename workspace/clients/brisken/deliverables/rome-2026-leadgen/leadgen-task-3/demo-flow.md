# Sanofi demo flow: TreasuryCentral, tailored to a treasury GPO

**For:** Dirk Neumann, presenting
**Prospect:** Ian Haegemans, Treasury Process & Analytics Expert, Global Process Owner Team, Sanofi (Brussels)
**Call:** next-week Friday, about 16:00. Dirk sends the invite.
**Deck:** `collateral-pack/brisken-treasurycentral-sanofi.pdf` (10 slides)
**Prepared:** 2026-07-09

Sourcing: the person, role, call slot and deliverable all come from Dirk's forwarded
instruction, captured in the Planner task description and the 2026-07-09 checkpoint.
Everything marked HYPOTHESIS is our reading, not something Ian said. Do not assert a
hypothesis to him as if he had said it.

## What we actually know

| Fact | Source |
|---|---|
| Ian Haegemans, Treasury Process & Analytics Expert, Global Process Owner Team, Sanofi, Brussels | Dirk's forward, in the Planner task description |
| ian.haegemans@sanofi.com | same |
| He replied to the Rome booth Tier 1 follow-up | same |
| Call confirmed for next-week Friday about 16:00; "Friday is perfect"; Dirk sends the invite | Dirk's forward, quoted in the 2026-07-09 checkpoint working notes |
| Dirk's ask of us: "Now I need you to prepare the collateral for this." | Dirk's forward |
| He stood at the Brisken booth and encoded a token on 2026-06-24, typing his own title | `brisken-token-registrations.csv` row 95, `fob_encoded: true` |
| Sanofi is a Dirk-owned CRM **lead**, not a client, with four earlier trade-show contacts | `context/zoho-crm.json` |

Nothing else about Ian or Sanofi treasury is in our first-party records; the comms log has
no Sanofi thread yet. Public, sourced research on Sanofi's treasury sits in
`call-prep-brief.md`. Read that before this. The two facts that shape the whole call:

- Sanofi's **Treasury Core Model** already redesigned 40+ treasury processes onto SAP
  S/4HANA Treasury, live since September 2020. They are not migrating. They finished.
- Ian's own public words, three months ago: Sanofi treasury is *"making progress to level up
  our data governance maturity and building out a data foundation to become AI-ready"*.

Anything he has not said and the brief has not sourced is unknown. Do not assert it.

One name to keep straight: **Isabelle Badoux**. She is a real contact in Dirk's own Zoho
CRM, "General Manager Head of Global Treasury Operations, Systems & Treasury
Transformation", Belgium, captured at a trade show. She was not at Rome, and on 2026-07-09
she was removed from the Rome event sheet along with everyone else who was never invited.

Nothing on record connects her to this call, and an earlier session was corrected for
asserting a seat relationship between her and Ian that was pure inference. Do not raise her
name with Ian. Dirk should know she is in his CRM, because she is the senior treasury
systems and transformation owner at the account, which matters after Friday, not during it.

## The one thing to get right

Sanofi already won the argument we would normally be making. The Treasury Core Model
standardised 40+ processes onto SAP S/4HANA Treasury, and Ian's team monitors adherence to
it with KPI dashboards. Walking in to sell process standardisation would be selling him his
own last five years.

The pitch is the sentence after that one. When the process is standard but the data feeding
it is assembled differently in each entity, the adherence KPI measures the assembling, not
the adherence. A governed data layer is what makes that metric mean something, and it is
the precondition for the AI-ready data foundation he has publicly said he is building.

That is exactly the deck's Sanofi problem line, and it is why the Sanofi cover reads
differently from the Zalando one:

> A global treasury runs one process. The data behind it lives in a dozen places.

Lead with the process and the governance. The analytics follow. Do not lead with the
technology layer.

## Run of show (45 minutes assumed)

The deck carries the middle. The first six minutes and the last eight are not on any
slide, and they are where the call is won.

**0 to 3, reconnect and set the agenda.** Rome, then: "I want to spend most of this on
your process rather than our slides. I will show you the cockpit, and I would rather stop
whenever something maps to what you actually own."

**3 to 8, discovery before slide 2.** Ask, and listen. The answers change which slides get
weight:

1. Which part of the Core Model do you own, and how many entities run it?
2. When you look at process adherence across entities, how much of the deviation is really
   process, and how much is the data arriving in different shapes?
3. What still gets hand-assembled before it reaches the dashboard?
4. When you need to prove a number to audit, what does that take today?

If 2 and 4 draw energy, the governance slide is the centre of this call and the engines
slide is context. If 3 draws it, invert that. Question 2 is the one that opens the call up;
it is the difference between his metric describing reality and describing a spreadsheet.

**8 to 14, the problem (slide 2).** Use his own words from discovery back to him. The
slide has three columns: sources, the manual middle, systems. The manual middle is the
part a GPO cannot standardise away with policy, because it is not a policy problem.

**14 to 22, the cockpit and the three engines (slides 3 and 4).** Market Data Hub, Smart
Trading, Digital Co-Worker. Keep this to what they do, not how they are built. The line
that matters for him: curated once, governed end to end.

**22 to 32, architecture and governance (slides 5 and 6).** For a GPO this is the
substance, not the plumbing. Audit trail on every value and every change. Segregation of
duty on the changes that matter. Automatic checks that catch bad data before it lands.
Spend real time here. This is the slide that answers "how do I standardise once and prove
it stayed standard".

**32 to 38, OnePilot and proof (slides 7 and 8).** TreasuryCentral is the edition; OnePilot
is the layer underneath. Evonik and RWZ build on OnePilot directly.

Two cautions on this pair. Dirk has not yet signed off on naming **Evonik and RWZ** on the
proof slide; that was flagged for his review in the 2026-07-09 checkpoint and is still
open. And **do not say BTP**, per the standing directive. The deck in this pack has been
rebuilt without it.

**38 to 45, close and next step.** Slide 10 currently reads "When we talk, we will show
TreasuryCentral live on your SAP data." That sentence was written for the pre-call email,
where "when we talk" pointed at this call. On the call itself it promises the thing that is
already happening, and it commits to a live run on Sanofi's own data, which is not what a
first call is. Land the close verbally instead:

> "The next step I would suggest is a working session on the one process you own, with
> your own field names on the screen. Half a day, your people and mine."

Then stop talking.

## Objections to expect

**"We already have a TMS."** TreasuryCentral is not a treasury management system and does
not replace one. It is the layer between the sources and the systems, so the TMS receives
values that were curated once and checked before they arrived. Ask what the TMS is fed by
today; that is usually where the manual middle lives.

**"How does this fit S/4HANA?"** Never raise migration timing here. That is the Zalando
angle and it is factually wrong for Sanofi, who went live on S/4HANA Treasury in September
2020. If he raises S/4HANA, the answer is that TreasuryCentral sits in front of it: the
Core Model defines how the process runs, and the layer decides what arrives to run it on.

**"We already standardised. That is what the Treasury Core Model is."** Agree, completely,
and then move one step: the process is standard, and the data arriving into it is still
assembled differently in different places. A process-adherence KPI built on hand-assembled
inputs measures the assembling, not the adherence. Ask what still gets touched by hand
before it reaches his dashboard.

**"Our data is not clean enough for this."** That is the argument for the checks, not
against them. Bad values get caught before they reach the system of record rather than
being reconciled afterwards.

**"Who else in pharma runs this?"** We have no pharma reference we can name. Say so, and
name Evonik and RWZ as the OnePilot references we do have, subject to Dirk's sign-off on
using them. Do not invent a pharma logo.

## Do not say

- **BTP.** Standing directive from Dirk, task "Exclude BTP from all demos". Removed from the
  deck and the one-pager in this pack; keep it out of the talk track too. Nothing replaces
  it. The material simply omits it, because it is not what makes a treasurer buy. If Ian
  presses on what the cockpit runs on, naming it in conversation is fine.
- **Verve, or the universal-UI vision.** The vision is the enabler behind the product, not
  the lead at a first treasurer call. Lead with the treasurer outcome.
- **Any Sanofi system, program or number he has not told us about.** We have none on
  record. Guessing one and being wrong costs the call.
- **Isabelle Badoux**, unless he raises her first.

## Settled, from the thread itself

Read out of Dirk's mailbox 2026-07-09, so these are not open:

- **Friday, 16:00.** Ian offered "next week from Tuesday-Friday somewhere after 16:00 or
  between 13:30 and 14:00". Dirk proposed "THU or FRI 16:00" and asked whether to send an
  invite. Ian: "Friday is perfect."
- **Ian comes alone** unless he adds someone. He named nobody. Adela Dolezalova and Maria
  Moeller belong to the Zalando thread, where Lokesh asked for them.
- **The invite is unsent** and no duration was agreed. Ian's own alternative window,
  13:30 to 14:00, was 30 minutes, so 30 sits inside what he offered.

## Open questions for Dirk before the call

Tracked as Planner task `VeH5a5bwf0Ky5jns-nt8bGUAMA-a`, assigned to him.

1. Is a live TreasuryCentral environment available to show? Slide 10 as written implies a
   live run on Sanofi's own data.
2. Evonik and RWZ on the proof slide: does he sign off on naming them to Sanofi?
3. Meeting length, then send the invite. This flow assumes 45 minutes. At 30, cut slides 4
   and 7 and keep discovery.
