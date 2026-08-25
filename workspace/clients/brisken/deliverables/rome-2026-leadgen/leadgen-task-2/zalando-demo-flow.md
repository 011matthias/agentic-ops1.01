# Zalando TreasuryCentral demo flow

Run-of-show for Dirk. 40 minutes, discovery-led. Slide numbers refer to
`deck/brisken-treasurycentral-zalando.pdf` (10 slides).

The structure differs from the Sanofi call on purpose. With Sanofi there is a named process pain
(global process owner, one process, many data sources). With Zalando there is nothing on record:
Lokesh tapped the token and replied to a generic email. Leading with the product story here would be
guessing at a problem in front of three people, one of whom (Maria) we have never met. So the first
ten minutes buy the angle, and the middle of the deck branches on what they say.

## Minute 0 to 3, open without a claimed history

No slides. Cover 1 only.

Do not say "as we discussed at the booth". Say that they came by the stand, that the conversation at
an event like that is never a real one, and that the point of this call is to find out whether the
thing is relevant to them at all. Then hand over: ask Lokesh what made him reply.

Ask Maria what she owns before the deck opens. Everything after minute 10 is aimed at her.

## Minute 3 to 10, discovery

Five questions, in this order. Stop when the angle is obvious; do not run the list to the end for
completeness.

1. Which SAP release is treasury on today, and is an S/4HANA move in flight?
2. Cash and liquidity management: standard SAP, or something built for Zalando?
3. Where does the team still re-key or reconcile by hand? Bank files, market rates, remittances, trade capture?
4. Who owns the feeds today, treasury or IT?
5. What made this worth a call now?

Question 2 is the one to listen hardest to. A tailored in-house cash management layer is what
consenso described in 2018, and if it is still there, it is the entire conversation.

## Minute 10 to 25, the deck, branched

Slides 2 and 3 always. Slide 2 frames the manual middle; slide 3 is the cockpit. If discovery produced
a specific pain, name it out loud on slide 2 in their words rather than reading the slide.

On slide 4 (three engines), lead with whichever engine their answer to question 3 pointed at, and
spend the time there. The other two get a sentence each.

| If they said | Lead with | The line that lands |
|---|---|---|
| Remittances, bank files, manual posting | AI automation and orchestration | Digital co-workers read the messy remittance advice and post it into S/4HANA, on their own data, governed |
| Rates, FX, curves, many providers | Market Data Hub | Every rate curated once, from any source to every system |
| Hedging, trade capture, a venue that does not reach SAP | Smart Trading | The middle between the trading venue and SAP, closed, from capture through to the deal |
| Nothing specific | Market Data Hub | It is the least assumption-heavy of the three and the easiest to show |

Slides 5 and 6 (architecture, governance) are the answer to Adela's questions, and she will have them.
Segregation of duty, the audit trail, automatic anomaly checks, ISO 27001 and SOC 1 are the material.
Let her ask rather than pre-empting.

Slide 7 (OnePilot underneath) matters only if they push on what it actually is. Skip it if the room is
already convinced.

Slide 8 is the proof: Evonik and RWZ build on OnePilot directly, SAP and non-SAP, on-prem included.
Then the S/4 line, as a question: if an S/4HANA move is on their roadmap, the feeds get re-decided at
that moment, and this is the decision that only gets made once.

## Minute 25 to 35, show it live

The deck's own close promises a live look at "the cockpit, the connectivity and the AI, end to end".
That promise is what the deck is for; the deck is not the demo. Whatever is shown live should be the
engine chosen on slide 4.

## Minute 35 to 40, close

Slides 9 and 10. The concrete next step is the ask, not "let me know if you want to go further".
Two candidates depending on how the room reads:

- Warm: a working session with Adela and whoever owns the feeds, on Zalando's actual data flow.
- Cool: send the one-pager and the engine deck, and propose a follow-up once their S/4 timeline is known.

## Do not say BTP

Dirk's standing directive (Planner task "Exclude BTP from all demos") is to leave SAP BTP out of all
demo materials. The deck in `deck/` has been rebuilt with both BTP references removed. The spoken
equivalent is "it runs on SAP's own cloud, inside your landscape". If Adela asks the platform question
directly, answer it directly; the directive governs our materials, not honest answers to a direct
question.

## Objections worth having an answer ready for

**"We already built our own cash management layer."** That is the 2018 consenso finding, so it is
plausible rather than certain. The response is not that the build is wrong; it is that the build has
one owner, no audit trail across feeds, and breaks when a provider changes a field. TreasuryCentral is
the same middle with the governance attached.

**"We are mid-migration, come back later."** The proof slide exists for this. The feeds get decided
during the migration, and deciding them once is cheaper than deciding them twice.

**"Who are you, and who else runs this?"** Evonik and RWZ, on OnePilot directly. SAP co-innovation
partner. ISO 27001 and SOC 1 Type II. Do not oversell the customer list beyond the two named.
