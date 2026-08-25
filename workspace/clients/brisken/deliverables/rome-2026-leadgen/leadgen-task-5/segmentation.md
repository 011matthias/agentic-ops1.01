# Tier 2 (warm-engaged): how the 18 were derived

Source of truth: `workspace/clients/brisken/context/lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx` (298 rows, read 2026-07-09), overlaid with Dirk's own `dirk_notes` and `stop` columns.

Planner task "Rome Tier 2 warm-engaged: LinkedIn + Sales Nav" says "~20 warm-engaged contacts". The filter below lands on **18**.

## The filter

Start from every row with a non-empty `dirk_notes`, minus `stop`, minus notes that just read `GA`:

**53 rows.** Then remove five groups that belong to other Planner tasks:

| Removed | N | Why | Owning task |
|---|---|---|---|
| Hottest-5 accounts | 10 | VW, JTI, Roche, LSEG people carry booth-audio recaps and get bespoke 1:1 sends | "Rome Tier 1 hottest-5: LinkedIn + Sales Nav" |
| Already emailed 2026-07-08 | 3 | `post_event_outreach` set (Joergensen, Ermakov, Rolsted, all DSV) | "Rome Tier 1 leads: LinkedIn + Sales Nav" |
| `no_show` = Yes | 7 | Shell cluster, Badoux, the two Zalando referrals; a "good to see you in Rome" note is factually false for them | Shell call prep / Zalando collateral / Tier 3 did-not-attend branch |
| Dirk redirected the note to GA | 2 | Bruno Forret ("General awareness is always good"), Fabio Mora ("=> GA") | Tier 4 GA, or no sequence |
| SAP partners and consultancies | 13 | Generic `personal outreach DN` stamp with no substance behind it; Dirk's standing rule is to leave partners for later | held, see below |

53 minus 35 = **18**.

## The 13 held partner rows

Rohit Bali (Deloitte), Lars Richter (Eprox), Michael Diet (INTENSUM), Jean-Michele Szczecina (KPMG), Andriy Sharandakov (LeverX), Kiosses Christos + Stephan Meyerhoff (Nagarro), Aniket Kulkarni (PwC), Marcus Reinsfelder (SINVA), Jochen Stiebe (Target Networks), Dan Staniford + Sebastian Ramos (Tradeweb), Laura Koekkoek (Zanders).

Each carries only the bare string `personal outreach DN`. Nothing in the sheet says what the conversation was about, so there is no honest way to write a personalized connection note for them. They are candidates for the Sales Nav watch list (harmless, it is a tracking list) but not for a note.

**Open question for Dirk**, in `SUMMARY.md`.

## The one genuine ambiguity: the SAP employees

`post-event-sequences.md` says "leave Partners and SAP for later", which defers `attendee_type` = SAP employee. Two paragraphs down, the same file names "the ICD Dashboard follow-up" as a Tier-2 angle. That follow-up IS three SAP employees (Lasecki, Hamid, Brueckner), plus Mehlkopf on an individual-outreach note.

Resolved in favour of including them: Dirk wrote a specific, substantive note against each of those four names, and a named note outranks a blanket category defer. The 13 partners have no such note, which is exactly the line the defer rule was drawn on.

## The five spines

| Spine | N | Angle | Who |
|---|---|---|---|
| 1 · MDH | 3 | Market Data Hub, plus TRM | Georgiou, Boclinca, Timeshov (BSTDB) |
| 2 · AI / OnePilot | 3 | AI automation, remittance advice | Teisner-Kjaer, Vergel, Gupta |
| 3 · Connectivity | 5 | SAP Public Cloud API auth, ICD Dashboard | Jellonek, Brueckner, Mehlkopf, Lasecki, Hamid |
| 4 · Warm reconnect | 4 | No product angle; two are live Brisken customers | Fjotland, Schelstraete (Equinor), Opanasyk, Ehlers (DSV) |
| 5 · Ecosystem | 3 | Keep-in-orbit, and one partnership ask | Wandhoefer, Hill, Jones |

The task description anticipated three spines (MDH / AI-OnePilot / connectivity). Spines 4 and 5 exist because seven of the eighteen have no product angle in Dirk's note at all. Writing them a product note would invent a conversation that did not happen.

## Per-person facts that drive the copy

Three rows carry a constraint the copy has to respect, and one of them is a blocker:

- **Akash Gupta (Maersk)** did not attend Rome. He replied to the E3 wave asking for AI-in-treasury use case documentation, and Dirk answered "I will put something together and send it out to you" on 2026-06-24. That material has no build evidence anywhere in the repo. His note references it. **Do not send his invite until the material exists**, or the note repeats a promise that is now two weeks old.
- **Uffe Teisner-Kjaer (Grundfos)** already has a call agreed with Dirk for after the summer vacation ("I have already talked to Dirk", E3, 2026-06-24). His note points at that call rather than proposing a new one.
- **Njal Fjotland (Equinor)** attended the conference but has no booth record. Dirk's E1 was a proactive "come by our booth" note with no reply on file. His note therefore says "Rome went by quickly", not "good to see you at our booth".

The `met_at_our_booth` column in `tier2-roster.csv` is the field that decides the opener. Eight of the eighteen have a booth record; the rest attended the conference but did not register at Booth #2, so their notes open on the conference, not the booth.
