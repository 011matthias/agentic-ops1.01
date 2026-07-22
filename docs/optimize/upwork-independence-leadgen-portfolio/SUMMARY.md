# upwork-independence-leadgen-portfolio — run summary

**Result: 2,159 → 3,013 kEUR net won-client value (+40%), 4 rounds, converged.**
Score = client contribution won over a 30-month horizon, minus the acquisition
cost (your hours at the ~EUR33/hr fallback + cash) of winning them. The winner
cleared the pessimistic stress floor (engine-enforced), so it is robust, not
optimism-only.

## The question this run answered

"How are we going to win clients?" GTM-v2 optimized delivery + pricing and hit a
MARKET-REACH ceiling; this run optimized the acquisition side: how to split a
fixed acquisition budget (1,800 hours + EUR12k cash over the horizon) across the
five OWNED channels, given the delivery capacity from GTM-v2. Upwork is the
status quo being replaced, scored only as a contrast baseline.

## The winning acquisition playbook (`acquisition-portfolio.json`)

| Channel | Effort (share of acq hours) | Clients won | Value | Role |
|---|---|---|---|---|
| cold_email_b2b (UK/US) | **0.38** (~680 h) | 49.9 | EUR 1.50M | volume engine, pool-saturated |
| linkedin_outbound | **0.29** (~520 h) | 23.3 | EUR 0.70M | B2B fill |
| referral_partnership | **0.15** (~275 h) | 14.9 | EUR 0.45M | warm, pool-saturated |
| content_aeo_inbound | **0.18** (~320 h) | 21.8 | EUR 0.44M | compounding inbound |
| demo_first_local | **0.00** | 0 | 0 | dropped (see below) |

110 clients total, **value EUR 3.08M**, net EUR 3.01M. Both budgets bind at the
optimum: 1,798 of 1,800 acquisition hours used AND the delivery serviceable cap
(110 clients) is BINDING. You are simultaneously acquisition-hours-limited and
delivery-capacity-limited; the efficient frontier fills every delivery slot with
the most valuable clients you have the hours to win.

## Kept change + boundary probes (the journal)

| r | change | kEUR | verdict |
|---|---|---|---|
| 1 | naive hedge → value-weighted mix (drop demo, load B2B + content) | 3013.27 | keep +854.23 |
| 2 | add demo-first-local 0.15 | 2735.75 | discard (demo doesn't earn budget) |
| 3 | all-in on cold-email | 1432.69 | discard (pool caps at 50; must diversify) |
| 4 | drop AEO/content | 2737.76 | discard (content earns its slots) |

## How we win clients (the answer)

**Diversify across owned channels, prioritizing value-per-client, because no
single channel reaches enough and delivery capacity is the binding constraint.**
Concretely:

1. **Cold-email B2B (UK/US) is the volume engine** — the largest reachable pool
   (50 clients) at the best value-per-hour, saturated first. UK/US only; DE cold
   email stays illegal (UWG Sec.7).
2. **LinkedIn + referral fill the rest of the B2B book** — all three B2B channels
   pay ~EUR30k/client, so effort loads onto them until their pools run out.
3. **Fund AEO/content inbound past its fixed-cost threshold** — it needs ~200 h
   of corpus build and ramps slowly (5 mo), but then compounds cheaply and wins
   ~22 clients; dropping it (r4) loses ~EUR275k it is not replaced.
4. **All-in on any one channel fails** (r3: cold-email alone nets 1,433 vs 3,013)
   because each pool is small relative to what you need. The market-reach ceiling
   GTM-v2 hit is real; diversification is how you beat it.

## The cross-model tension worth the owner's attention

**Demo-first-local is dropped here, yet GTM-v2 kept a 24% local book.** Both are
right about different things: local clients are cheap to DELIVER (GTM-v2 valued
the recurring-care annuity) but expensive to WIN (this run: ~27 h to win one for
~EUR4k, while the same hours win a B2B client worth ~EUR30k). When ACQUISITION
hours are the binding constraint, local loses. Reconciliation: run local NOT as a
primary client-winning engine but as spare-capacity fill, or where a demo doubles
as AEO proof / a warm inbound you did not have to chase. Do not spend scarce
outbound hours manufacturing local demos.

## The independence upside

The owned portfolio nets **EUR 3.0M** over the horizon; the all-Upwork status quo
nets **EUR 0.85M** for the same delivery capacity (platform fee + no compounding +
capped pool). The ~EUR2.2M gap is the prize for owning the pipeline. Upwork is
still worth running as transitional cash while the owned channels ramp (content
especially is slow to produce), but it is the thing being replaced, not invested
in.

## Model limitations the winner leans on (validate before acting)

- **The reachable pools per channel** (cold 50, LinkedIn 30, referral 15, content
  25) drive the diversification and the client count. They are ASSUMPTION-tagged;
  the RANKING (B2B-heavy, content-funded, demo-dropped) is more stable than the
  exact mix.
- **The acquisition-hours budget (1,800 h) binds.** If you can free more time for
  winning clients (subcontract more delivery, per GTM-v2) or lift conversion, you
  win more clients; the model would then push harder into the larger pools.
- **Per-client values** come from GTM-v2 (B2B ~EUR30k, local ~EUR4k). The 7x gap
  is what makes B2B dominate acquisition; if local's care annuity is richer than
  modeled, its acquisition priority rises.

## What a human should review

The playbook is trustworthy in direction: **win clients through a diversified
owned mix led by cold-email B2B, filled out with LinkedIn + referral, and a
funded AEO/content inbound engine; keep demo-first-local as fill, not focus; and
treat Upwork as transitional, not a channel to invest in.** Before acting on the
exact split, validate the per-channel reachable pools and whether ~1,800 hours is
really all the acquisition time available, since both bind the answer.

---

*The two sections below were retrofitted 2026-07-22 so `optimize_overview.py
--prior-art upwork-independence` can read this run. They transcribe the r2-r4
probes and the "Model limitations the winner leans on" and "cross-model tension"
sections above; no new analysis.*

## Dead ends

Three boundary probes, all discarded. A later run should not re-derive them
against this model:

- **Demo-first-local does not earn acquisition budget (r2: +0.15 local,
  2735.75).** A local client costs ~27 h to win for ~EUR4k, while the same hours
  win a B2B client worth ~EUR30k. See the sensitivity below before reading this
  as "drop local" outright; GTM-v2 reached the opposite conclusion on delivery
  grounds and both are right about different things.
- **All-in on one channel fails (r3: all cold-email, 1432.69 vs 3013.27).**
  Cold-email's reachable pool caps at 50 clients, so hours past saturation are
  wasted. The market-reach ceiling is real and diversification is how you beat it.
- **AEO/content earns its slots (r4: drop content, 2737.76).** It needs ~200 h of
  corpus build and a 5-month ramp, then wins ~22 clients (~EUR275k) that the
  already-near-saturated B2B pools do not replace.

Settled and not worth a round: Upwork was scored only as a contrast baseline
(EUR0.85M vs the owned portfolio's EUR3.0M for the same delivery capacity). It is
the thing being replaced, not a channel to optimize.

## Sensitivities

- **Both budgets bind simultaneously**, which is what makes the answer an
  efficient frontier rather than a ranking: 1,798 of 1,800 acquisition hours are
  used AND the 110-client delivery serviceable cap is binding. Move either and
  the mix moves.
- **The per-channel reachable pools** (cold 50, LinkedIn 30, referral 15, content
  25) drive both the diversification and the client count, and are
  ASSUMPTION-tagged. The RANKING (B2B-heavy, content-funded, demo-dropped) is
  more stable than the exact split.
- **Per-client values are inherited from GTM-v2** (B2B ~EUR30k, local ~EUR4k).
  That 7x gap is the entire reason B2B dominates acquisition; if local's care
  annuity is richer than modelled, local's acquisition priority rises.
- **This run and GTM-v2 disagree about local, and the disagreement is real, not
  an error to resolve by picking one.** Local is cheap to DELIVER (GTM-v2 kept a
  24% local book for the recurring-care annuity) and expensive to WIN (dropped
  here). When ACQUISITION hours bind, local loses. Do not inherit either verdict
  standalone: the reconciliation is to run local as spare-capacity fill or where
  a demo doubles as AEO proof, never as a use of scarce outbound hours.
