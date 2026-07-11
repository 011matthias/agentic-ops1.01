# Checkpoint: Brisken Lead-Gen Red-Team Review

**Date:** 2026-06-12
**Status:** Review complete — report delivered, no doc edits applied yet

---

## Summary
Skeptical GTM red-team of the p2 OnePilot lead-gen plan (the deck + 2 specs + radar + 3 context files built in Session 4), run as a 56-agent verified workflow: 11 attack dimensions, per-finding adversarial verification against the source files, plus a completeness critic. Delivered top-3 kill findings, 12 ranked holes, and a betting paragraph. No source documents were modified — this was analysis only.

---

## What Was Done This Session
### Red-team workflow
1. Read all 7 target files in full myself first (deck, p2-bant spec, orchestration spec, targeting-radar, product-catalog, evidence-pack, negotiation-benchmarks).
2. Ran `redteam-brisken-leadgen` workflow: 11 finder agents (one per attack dimension) → per-finding refuter (default-refute) verifying every quote + citation + math + checking for preemption → completeness critic for missed surfaces.
3. 44 findings produced, 42 survived verification, 2 rejected; critic added 3 net-new (prior-contact contamination, GDPR controller scope, deck "Agreed" stamp).
4. Synthesized into the user-requested structure and delivered in-chat.

### Verification discipline
- Every attacked claim quoted verbatim + file:line, re-checked by an independent agent. Verifiers downgraded most "kill" labels to "weakened" — correctly — because the docs internally concede a lot and the cash downside is bounded (~$99/mo seat; Lane 1 zero-spend).

---

## Key Decisions Made
### Top-3 framing = "the money never closes for UnpauseAI" + the close-rate dishonesty
- **Choice:** Led with (A) the commission leg being unsourced/unsigned/deferred-past-leverage with a 12-mo window < 6-18mo cycle; (B) attribution being uncollectable in a tiny universe Brisken already owns ("any opportunity we sourced" unfalsifiable, no account-lock, no audit right); (C) the deck transferring Dirk's >90% warm close onto cold demos 5× against the spec's own "do not promise 90% on cold."
- **Rationale:** Verification showed the volume/causal attacks are real but bounded (low cash at risk); the genuinely fatal failure mode is that even total success pays us ~nothing, and the close-rate slide detonates the relationship exactly at the deferred-commission talk.

### Highest-ER single fix = one pre-outreach email to Dirk
- **Choice:** Recommended collapsing the cure into one message that (1) captures the verbatim offer, (2) gets OnePilot list ACV + the >90% numerator/denominator, (3) gets a one-paragraph signed structure (rate band, first-year-ACV basis, ≥18-mo attribution from demo date, dated account-lock/exclusion list, visible-artifact payment trigger).
- **Rationale:** Neutralizes findings A, B, C and the leverage inversion at near-zero cost; Dirk's refusal to sign a paragraph before receiving free pipeline is itself the kill signal.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| (none) | — | Read-only review; no source docs edited. The workflow script persisted under the session workflows dir. |

---

## Current Status
Red-team report delivered in-chat. The p2 lead-gen docs are unchanged and still in the Session-4 state (branch `client/brisken/lead-gen-onepilot`, uncommitted WIP). The plan remains gated on Dirk's go-live decision. None of the recommended deck edits or term-sheet fixes have been applied — they are the owner's call.

---

## Next Steps
1. **Owner decision:** which red-team fixes to apply before the deck/plan goes to Dirk. The cheap, high-value batch: the one pre-outreach email (ACV + verbatim offer + signed one-paragraph structure + account-lock list).
2. **Deck edits (20 min, if approved):** funnel terminus → "Booked BANT demo into your close motion"; stat-card → "your close rate on today's inbound leads (your figure)"; add the population-split line under Honest expectations; relabel "Agreed:" → "Your offer as we understood it, to confirm at terms."
3. **Spec edits (if approved):** print the funnel rate model (6 accounts × 3-5 personas); set attribution window ≥18 mo; re-tag radar per §5 (Colgate/Corteva A1, rest B); add numbered kill gates (G1 wk4 / G2 wk8 / G3 wk12) to §8.
4. **GDPR hygiene (half day, if pursued):** Art. 30 record + LIA, tracker retention rule, named-exec dossiers out of git, controller-processor clause, drop the logged-in stealth scrape.

---

## Context for Next Session
### Files to Read First
- This checkpoint + the in-chat red-team report (the report is the deliverable; it was not written to a file)
- `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html` (the deck the fixes target)
- `workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md` (§2 terms, §7 economics)
- `workspace/clients/brisken/specs/2-build/p2-lead-gen-orchestration.md` (§0 hardening, §1 deferred-money reframe)
- `workspace/clients/brisken/context/lead-generation/targeting-radar.md` (§5 tiers vs §6 live list inconsistency)

### Open Questions
- Will the owner apply the fixes to the docs, or keep the red-team as a strategic input only?
- Does Dirk's actual verbal offer (still uncaptured, [p2-bant §Phase 0 item 0]) match the deck's "Agreed" framing?
- OnePilot list ACV — the single missing number the whole commission case multiplies by; absent from all 7 files.

### Working Notes
- **Why most "kill" → "weakened":** the docs concede uncertainty repeatedly (TBD-until-live, realistic-not-promised, cold-closes-lower), and the cash at risk is bounded to ~$99/mo + unpaid labor. So the true risk profile is *low cash loss, high opportunity-cost, high probability we work and collect ~nothing* — not a budget burn.
- **The two rejected findings:** an AEO "internal contradiction" that conflated the captive SAP-Store advisor with open-web LLM search; a Tier-C "coverage theater" claim the docs already pre-empt ("not an active target until a trigger appears"). Don't re-raise.
- **Strongest novel finding (critic):** prior-contact contamination — in a ~55-182 named universe Brisken's own sales worked for years AND already blasted with 2M emails, "sourced" is unfalsifiable and the "personal" first DM likely lands on someone who already got the spam.
- **Confirmed (not weakened) findings to trust most:** the close-rate transfer (html:257/239/440 vs spec:117-119), the sender-identity ToS dilemma (deck promises "outreach on us" + "real Brisken profile"), the unauditable commission trigger, the unfalsifiable per-account trust surround.
- Workflow: 56 agents, ~7.06M subagent tokens, 538 tool uses, ~22 min wall-clock. Full output at the task output file (truncated in-notification; paged via Read).

### Reference Materials
- Workflow script: `.../workflows/scripts/redteam-brisken-leadgen-wf_8643390a-108.js`
- Run ID `wf_8643390a-108` (resumable same-session if re-run needed)

---

## How to Continue
The analysis is done and delivered. To act on it, pick which fixes to apply from Next Steps and edit the Session-4 docs on branch `client/brisken/lead-gen-onepilot`. The single highest-leverage move is drafting the one pre-outreach email to Dirk (ACV + verbatim offer + one-paragraph signed structure + account-lock list) — but per the no-unrequested-drafts rule, only draft it on an explicit ask.

---

## Strategic Feedback

### What Worked Well This Session
- Clean, well-scoped adversarial brief with named attack dimensions + an explicit "quote verbatim or write unsourced" evidence rule. That constraint is exactly what made the verification layer able to kill 2 findings and downgrade ~20 — the discipline lived in the prompt, not just the output.

### Suggestions
- The red-team report was delivered in-chat only (per the brief, no file write). If it should inform doc edits next session, consider saving the top-3 + the one-email fix as a short note in `context/lead-generation/` — otherwise it dies with this conversation's context. (Did NOT write it unprompted; flagging as a choice.)

### System Health
- Self-critiquing workflow (finder → default-refute verifier → completeness critic) is a strong reusable pattern for any "review before it ships to client" gate. Worth considering as a `/comd_review`-adjacent skill or a saved workflow, since the same shape applies to proposals, deliverables, and specs — not just this deck.
- Autonomy score: 0 — fully autonomous session.
