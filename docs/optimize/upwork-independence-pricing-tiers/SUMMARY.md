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
