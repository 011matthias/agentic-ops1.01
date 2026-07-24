# upwork-independence-pricing-tiers - run summary

**Result:** 2649.94 -> 4775.09 kEUR total contribution surplus (30-month horizon),
+80%, converged. 2 keeps + 4 boundary-probe discards. The winning menu captures
**+661.5 kEUR over the best single flat price** (the money versioning earns over
one-size-fits-all pricing).

This is the third and final GTM-family run. GTM-v2 priced ONE retainer;
leadgen-portfolio optimized how clients are won. This priced the OFFER itself as a
good/better/best menu that a heterogeneous prospect population self-selects into.

## The winning menu

| Tier | Price/mo | Scope | Buys it | Margin/mo |
|---|---|---|---|---|
| Good | EUR650 | 0.20 (thin) | micro segment (150 prospects) | ~EUR376 |
| Better | EUR1850 | 0.55 (mid) | core segment (95) | ~EUR1377 |
| Best | EUR6300 | 1.00 (full) | scale segment (30) | ~EUR5380 |

Each segment self-selects the tier that maximizes its own surplus. Delivery load at
the optimum is 112/150 client-equivalents (capacity not binding).

## Three findings (robust across the assumptions)

1. **Tier the offer, do not flat-price.** A single flat price forces a lose-lose:
   price it for the core and you exclude the numerous low-WTP micro segment AND leave
   the scaleups' willingness on the table. Splitting into three tiers captures +661
   kEUR over the best flat price the model can find.

2. **Both the entry tier and the premium tier earn their place, independently.**
   Dropping the entry tier costs 803 kEUR (the micro volume the cheap thin plan wins);
   collapsing the premium tier costs 1671 kEUR (the scaleup willingness a distinct high
   tier captures). Neither is decoration; the probes (r5, r6) priced each one.

3. **The premium price and the mid tier are incentive-coupled.** You cannot just
   "raise the premium price". Raising best alone makes the scale segment defect DOWN to
   the cheaper mid tier, where it gets more surplus (r3 probe: best -> EUR8500 loses 1671
   kEUR). Premium-capture only works if the mid tier is thinned in the SAME move so the
   scaleup still prefers best. That is why the winning r2 moved two tiers at once, and
   it is the core versioning / incentive-compatibility constraint of any tiered offer.

## The optimum is an interior peak, not a bound (the 4 probes)

| Probe | Menu change | Score | What breaks |
|---|---|---|---|
| r3 | best EUR6300 -> EUR8500 | 3103.65 | scale defects down to better (IC ceiling on best price) |
| r4 | good scope 0.20 -> 0.45 | 769.48 | core trades down to the fat entry tier (cannibalization) |
| r5 | drop entry (good = better) | 3971.96 | lose the micro segment entirely |
| r6 | collapse premium (best = better) | 3103.65 | scale pays EUR1850 not EUR6300 (lose the capture) |

The only bound in the winner is best.scope = 1.0 (the premium tier is the full
package), which is a genuine result, not a no-resistance artifact: the model carries
convex delivery cost and scope-scaling oversight that push back on high scope, and
full service still wins for the volume-absorbing scale segment. Every price and the
good/better scopes land interior.

## Reconciliation with the earlier GTM runs

- The **core** segment IS the GTM-v2 ~EUR2500 retainer client. Here it lands at
  EUR1850, slightly lower, because the menu now also monetizes the scaleups above it
  (at EUR6300) and the micro below it (at EUR650). Tiering shifts money from the mid
  price point to the ends of the distribution.
- The **premium tier is the highest-leverage thing GTM-v2 + leadgen did not have:**
  EUR6300/mo scaleup clients that a single ~EUR2500 retainer left entirely uncaptured.
- The delivery-capacity load (112/150 client-equivalents) reconciles with
  leadgen-portfolio's serviceable ceiling; capacity is not the binding constraint on
  the pricing menu (the versioning trade-off is).

## Honest-number caveat

The SCORE is only as real as the locked segment economics, which are ASSUMPTION-tagged
planning estimates of the B2B prospect willingness-to-pay distribution (reviewed on PR
#311). The RANKING is robust: tier the offer, keep the entry deliberately thin,
differentiate the mid tier enough to hold the premium segment in the top tier. The
absolute EUR scales with the assumed prospect distribution.

**Highest-sensitivity inputs to validate before acting:** the scale segment's size
(30 prospects) and value curve (how much a funded scaleup will really pay for
done-for-you volume), and the micro segment's size (150) and whether it actually
converts at EUR650/mo. Validate these against real quotes, then the menu prices follow.

---

*The two sections below were retrofitted 2026-07-22 so `optimize_overview.py
--prior-art upwork-independence` can read this run. They transcribe the r3-r6
probe table and the honest-number caveat above. One addition beyond
transcription, flagged inline: the journal's stop reason is `user stop`, not a
convergence signal.*

## Dead ends

Four boundary probes, all discarded. Each priced one piece of the menu, so a
later run should not re-derive them:

- **Raising the premium price alone fails (r3: best EUR6300 to EUR8500,
  3103.65).** The scale segment defects DOWN to the cheaper mid tier, where it
  gets more surplus. This is an incentive-compatibility ceiling, not a demand
  ceiling.
- **The entry tier must stay deliberately thin (r4: good scope 0.20 to 0.45,
  769.48).** Fattening it toward the mid tier's 0.55 makes the core segment trade
  down and cannibalize. This is the single largest discard in the run.
- **The entry tier earns its place (r5: drop it, 3971.96, -803).** Folding good
  up to better loses the numerous micro segment entirely.
- **The premium tier earns its place (r6: collapse best into better, 3103.65,
  -1671).** Without a distinct high tier the scale segment pays EUR1850 instead
  of EUR6300.

## Sensitivities

- **The run ended on `user stop`, not on plateau or a convergence check.** The
  journal's final row reads `stopped / user stop`, while this SUMMARY's headline
  says "converged". The four probes did map the menu's boundaries, but no
  plateau or budget signal fired, so treat the result as "no further hypothesis
  was tested", not "the search was exhausted". This is exactly the
  ran-out-of-ideas versus found-an-optimum distinction, and it is why
  `upwork-independence-gtm-v2-confirm` was worth running against gtm-v2.
- **`best.scope = 1.0` is the one lever pegged at a bound in the winner.** This
  SUMMARY argues it is a genuine result rather than a no-resistance artifact,
  because the model carries convex delivery cost and scope-scaling oversight that
  push back on high scope. Inherit the argument WITH the pegging, not instead of
  it. Every price and the good/better scopes land interior.
- **The premium price and the mid tier are incentive-coupled.** They cannot be
  moved independently: capturing premium willingness requires thinning the mid
  tier in the SAME move so the scale segment still prefers best. A later run that
  treats these as two separate levers will reproduce r3.
- **The segment economics are ASSUMPTION-tagged planning estimates** of the B2B
  prospect willingness-to-pay distribution (reviewed on PR #311). The RANKING is
  robust; the absolute EUR scales with the assumed distribution.
- **Highest-sensitivity inputs:** the scale segment's size (30) and value curve,
  and the micro segment's size (150) and whether it converts at EUR650/mo.
- **The mid tier lands BELOW GTM-v2's single retainer** (EUR1850 vs ~EUR2500)
  because the menu monetizes the ends of the distribution instead. Do not read
  the two numbers as a contradiction or inherit EUR2500 into a tiered menu.
