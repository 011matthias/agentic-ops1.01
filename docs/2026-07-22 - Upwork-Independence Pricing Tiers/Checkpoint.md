# Checkpoint: Upwork-Independence Pricing Tiers

**Date:** 2026-07-22
**Status:** Complete — run closed, both PRs merged, GTM optimize thread finished

---

## Summary

Built and ran `upwork-independence-pricing-tiers`, the third and final GTM-family
optimize run: it prices the OFFER itself as a good/better/best menu that a
heterogeneous prospect population self-selects into. 2649.94 -> 4775.09 kEUR (+80%),
converged; the menu captures +661 kEUR over the best single flat price. Scorer + two
guards shipped as their own PR (#311, hash-pinned) before lock-on; run journal shipped
as #312.

---

## What Was Done This Session

### Model design (before locking anything)
1. Prototyped the pricing model in scratch and **rejected the first design**: with pure
   saturating value curves the high segment saturates too, so a single flat price beat
   the tier menu. Tiering only pays under single-crossing.
2. Rebuilt the value model as `value(s,q) = LIN*q + SAT*(1-exp(-K*q))` — micro is
   pure-saturating (caps out fast), scale is linear-dominated (value climbs with
   volume). That is what makes versioning earn its keep, and it is economically real
   (a scaleup absorbs 40 leads/mo profitably; a micro business cannot).
3. Added convex delivery cost (`D_QUAD`) and scope-scaling oversight so high scope has
   genuine resistance rather than a free ride to the bound.
4. Validated the design against three criteria before locking: interior optima, 3-tier
   beats best-flat (~10%), sensible self-selection. All passed.

### Locked surfaces (PR #311)
5. `tools/scorers/pricing-tiers.py` — the locked scorer, hash-pinned `e5327b02`.
6. `tools/pricing-tiers-validate.py` — schema + monotone good/better/best ladder + no
   tier priced below its own delivery cost.
7. `tools/pricing-tiers-stress-guard.py` — pessimistic-surplus floor >= 0 (RECIPES
   rule 3), independent reimplementation.
8. Registered both in `tools/INDEX.md` + `tools/scorers/README.md`; verified scorer
   reproduces the prototype exactly, guards accept AND reject correctly, ruff clean,
   `pin_scorer.py check` green.

### The run (PR #312)
9. Manifest + baseline asset, lock-on in an isolated worktree off `origin/main`.
10. 6 rounds: 2 keeps (2649.94 -> 3453.07 -> 4775.09) + 4 boundary-probe discards.
11. Wrote `SUMMARY.md`, shipped, cleaned up worktrees and branches.

---

## Key Decisions Made

### Rebuilt the value model rather than tuning around a bad result
- **Choice:** When the first prototype showed flat-pricing beating the tier menu, I
  changed the model's *structure* (linear + saturating value, single-crossing) instead
  of nudging parameters until tiering "won".
- **Rationale:** A model that only produces the desired answer after parameter-fitting
  is not evidence. The structural fix is also the economically honest one.

### Accepted `best.scope = 1.0` as a genuine result, not an artifact
- **Choice:** Shipped with the premium tier at full scope rather than adding resistance
  until it moved off the bound.
- **Rationale:** v1's fault was prices pegging with *no* resistance in the model. Here
  convex delivery cost and scope-scaling oversight actively push back and full service
  still wins for a volume-absorbing segment. "Premium tier = the full package" is the
  right answer. Documented explicitly so a reviewer does not mistake it for v1's bug.

### One round moved two tiers at once
- **Choice:** Round 2 changed both `better` and `best` in a single hypothesis.
- **Rationale:** The levers are incentive-coupled. Tested separately, thinning the mid
  alone *dips* (-64) and would have been reverted, and raising best alone loses 265.
  Only the coupled move climbs. A round is one hypothesis, not one variable.

### Did not rewrite main's history to fix a cosmetic commit subject
- **Choice:** Left the mangled `@ (#311)` squash subject on main.
- **Rationale:** Band 3 (force-push to main) for a cosmetic subject is a bad trade. PR
  title, body and diff are all correct.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `tools/scorers/pricing-tiers.py` | Created | Locked scorer, pinned `e5327b02` |
| `tools/pricing-tiers-validate.py` | Created | Ladder + per-tier-margin guard |
| `tools/pricing-tiers-stress-guard.py` | Created | Pessimistic-surplus floor guard |
| `tools/scorers/PINS.json` | Modified | Pin entry for the new scorer |
| `tools/INDEX.md` | Modified | Registered scorer + both guards |
| `tools/scorers/README.md` | Modified | Registered-scorers table row |
| `docs/optimize/upwork-independence-pricing-tiers/RUN.md` | Created | Run manifest (locked) |
| `docs/optimize/upwork-independence-pricing-tiers/results.tsv` | Created (engine) | Append-only journal |
| `docs/optimize/upwork-independence-pricing-tiers/SUMMARY.md` | Created | Run write-up |
| `workspace/projects/upwork-independence/pricing-tiers.json` | Created | The asset; final = winning menu |
| `memory/project_upwork_independence_gtm_optimize.md` | Modified | pricing-tiers DONE block |
| `memory/MEMORY.md` | Modified | Index line for the above |

---

## Current Status

Run **closed and shipped**. Both PRs merged to `main` (#311 scorer, #312 run). Worktrees
removed, local + remote branches deleted, no active run state. The winning menu:

| Tier | Price/mo | Scope | Self-selected by |
|---|---|---|---|
| Good | EUR 650 | 0.20 thin | micro (150 prospects) |
| Better | EUR 1,850 | 0.55 mid | core (95) |
| Best | EUR 6,300 | 1.00 full | scale (30) |

No client platform touched (internal strategy project) — no ops status line, no
infrastructure reconciliation, no comms log.

---

## Next Steps

1. **Validate the two load-bearing assumptions before acting on the prices:** the scale
   segment's size (30) and value curve (what a funded scaleup really pays), and whether
   the micro segment converts at EUR650/mo. The ranking is robust; the absolute EUR is not.
2. **Build the PowerShell-here-string-in-Bash guard** (see friction below) — third
   occurrence of an identical mechanism, documented-only fix has now failed twice.
3. **Next optimize target, if one is wanted:** Brisken expense-recon match accuracy vs
   Criss's labeled fixtures. Different and better class — real ground truth instead of
   planning assumptions, which is where this harness is most trustworthy.
4. Optional/lower value: Route-1 demo-site Lighthouse/AEO composite; a GTM v3 making
   subcontract intensity a decision with a span-of-control cost (only worth it once
   subcontracting is validated in the real world).

---

## Context for Next Session

### Files to Read First
- `docs/optimize/upwork-independence-pricing-tiers/SUMMARY.md` — the result and its caveats
- `docs/optimize/upwork-independence-pricing-tiers/results.tsv` — the 6-round journal
- `tools/scorers/pricing-tiers.py` — the locked model (ASSUMPTION tags are inline)
- `workspace/projects/upwork-independence/pricing-tiers.json` — the winning menu
- memory `project_upwork_independence_gtm_optimize` — all four runs in one place

### Open Questions
- Do the assumed segment sizes (150/95/30) reflect the real reachable prospect mix? The
  whole absolute-EUR result rides on this.
- Is EUR6,300/mo actually sellable to a funded scaleup in this market? The premium tier
  contributes 1,671 kEUR of the winner and has never been price-tested with a live buyer.
- Does the micro segment convert at EUR650, or is a thin plan at that price a support
  burden that the model's flat delivery-cost curve understates?

### Working Notes
- **Failed approach (worth not repeating):** pure saturating value curves for all three
  segments. Produces flat-price-beats-menu and a degenerate optimum where two segments
  pile into one tier. The linear term on the high segment is what creates the
  single-crossing that makes versioning pay.
- **Round ordering matters and is not obvious:** naive single-lever rounds do not climb
  monotonically here (r1-as-best-raise = -265; thin-mid-alone = -64). Verified offline
  against the locked scorer before driving the loop, which is why the run took 6 rounds
  instead of thrashing.
- **The offline-optimum technique** (import the locked scorer read-only, coordinate-ascend
  with the guard constraints, then drive the real loop with hand-built targets) worked
  again here, third run running. It is the reliable way to avoid a stuck hill-climb.
- **Engine precondition not in the docs:** `optimize_run.py start` aborts unless the tree
  is clean *outside* the manifest dir, so the baseline asset must be committed first.
- **`--discard` is optional for losing probes:** the engine auto-discards anything that
  does not improve, so plain rounds suffice; the flag forces a discard on a would-be keep.

### Reference Materials
- PR #311 (scorer + guards), PR #312 (run) — 011matthias/agentic-ops1.01
- `docs/optimize/RECIPES.md` — constructed-metric protocol (rule 3 = the stress guard)
- `.claude/rules/rule_optimize_loop.md` — three-surface lock model

---

## How to Continue

The GTM thread is finished; nothing here is mid-flight. Pick up either by
validating the assumptions in Open Questions (real-world work, not a loop task), or by
starting the expense-recon accuracy run, which needs its own scorer PR first
(fixture-accuracy % vs labels, with a held-out slice as the mandatory floor guard per
RECIPES rule 3).

---

## Strategic Feedback

### What Worked Well This Session
- "lets complete GTM then" was exactly the right size of instruction: it named the goal
  and delegated the how. Because the earlier turn had already surfaced the candidate
  list with reasoning, three words were enough to launch a full three-surface run with
  no further clarification.
- Letting the prototype kill its own first design early (before any file was locked) cost
  about ten minutes and saved shipping a scorer that would have produced a confidently
  wrong strategic answer.

### Suggestions
- The three GTM runs now produce absolute EUR figures that look authoritative and are
  not. Worth deciding once, explicitly, whether any of these numbers may appear in a
  client-facing or investor-facing artifact, or whether they stay internal
  direction-finders. Right now only the SUMMARY caveats prevent misuse.

### System Health
- The optimize harness held cleanly under a fourth run with zero engine friction: locks
  armed, guards fired, hash checks passed, keep/revert exact. The scorer-authoring path
  (create -> test -> `git clean` -> re-Write -> pin) is now well-worn but is still a
  workaround for the fact that a new scorer locks the instant it exists; a
  `--draft`/unpinned grace state would remove the clean-and-rewrite dance.
- Shell-dialect slips in the Bash tool are now a three-time recurrence with a
  documented-only fix. This is the clearest infrastructure-deferred item in the register
  and is a ten-line PreToolUse check.
- **Correction to this session's own shipped claim.** A sibling session's same-day
  optimize-harness audit established that a pessimistic-case guard over the SAME model
  is not a held-out guard: it tests robustness to bad assumptions, not generalization,
  and inherits every blind spot of the scorer it checks. My
  `pricing-tiers-stress-guard.py` is exactly that, yet its docstring, PR #311 and the
  run SUMMARY all cite "RECIPES rule 3 (held-out score floor, mandatory)". The guard is
  worth keeping as an anti-optimism floor; the CLAIM is wrong and is now the 5th
  instance of this substitution across 5 runs. Rule 3 has never actually been executed
  as written in this repo. Fix one of two ways: rename these guards to
  "stress/robustness floor" and stop citing rule 3, or reserve rule-3 language for runs
  with real held-out ground truth. The expense-recon accuracy target would be the first
  run that can honestly satisfy it.
- Autonomy score: 0 human interventions this session (4 self-detected friction events,
  no user corrections, no user-performed tasks).
