# Checkpoint: Brisken Messaging Spine + TreasuryCentral Blueprint

**Date:** 2026-06-17
**Status:** Positioning reconciled; restyle blueprint committed and ready to hand to a fresh chat. Prototype itself not yet edited (a concurrent session is actively editing it).

---

## Summary

Compared Brisken's new internal "Messaging Spine" (applications company; TreasuryCentral flagship; OnePilot demoted to the AI layer) against our existing p2 lead-gen framing, recorded the deltas as canonical naming truth, recommended a website layout and the OnePilot AI term, and produced a committed, self-contained restyle blueprint a new chat can run against the OnePilot prototype.

---

## What Was Done This Session

### Positioning analysis
1. Read the pasted Messaging Spine and compared it to `brisken-product-catalog.md`, the `p2` spec, and the OnePilot prototype. Five deltas found: TreasuryCentral (new flagship, absent everywhere), OnePilot demoted from umbrella to AI layer, Trade Automation -> Smart Trading (BST), public roster narrows to five, logos now cleared, Rome T&WCM CTA.
2. Recommended a 3-zoom website architecture: TreasuryCentral (cockpit) / the applications (the buy) / OnePilot + OnePilot Agents (autonomous layer).
3. Named the AI: **OnePilot Agents** (autonomous layer; cockpit/pilot metaphor), avoiding "co-worker" and "interface"; fallback "OnePilot Intelligence". Avoid "copilot".
4. Fused the layout with the marketing strategy (`lead-gen-strategy-2026-06-12.html`, Marketing tab): "shadow integrations" is the named enemy carried across hero -> benchmark band -> application pages -> AI section -> SAP trust row; the four marketing moves map onto site sections.

### Artifacts
5. Recorded the reconciliation + AI naming + website-strategy fusion in `brisken-product-catalog.md` ("Spine reconciliation (2026-06-17)" section).
6. Added two `next_steps` to the `p2` spec (spine sync: BST + Rome CTA + named logos; Dirk confirm: TreasuryCentral/OnePilot hierarchy).
7. Wrote `brisken-treasurycentral-restyle-blueprint.md`: a self-contained build directive (current-structure map, the decision, exact section edits with final drop-in copy, constraints, validate/ship steps). Committed (`c025f7f`) after it was lost once (see Friction).

---

## Key Decisions Made

### TreasuryCentral is the flagship cockpit; OnePilot is the autonomous layer
- **Choice:** Build the nested model (TreasuryCentral = what you see, OnePilot = what runs it), not five peer products.
- **Rationale:** User explicitly liked TreasuryCentral. The cockpit/pilot metaphor resolves OnePilot's double meaning and is reversible in the single prototype file.

### AI term = OnePilot Agents
- **Choice:** "OnePilot Agents" for the acting AI; "the autonomous layer" for OnePilot's role.
- **Rationale:** Brisken wants to avoid "co-worker" (junior) and "interface" (passive). "Agents" conveys acts-not-chats; the pilot metaphor marries autonomy with the governance an AI-wary finance buyer needs.

### Restyle is an edit, not a rebuild
- **Choice:** Blueprint targets the existing prototype (already has shadow integrations, BST rename, benchmark band, AEO answers, trust marks). Only the TreasuryCentral cockpit and the AI branding are genuinely new.
- **Rationale:** Lowest-friction path; preserves a strong existing page.

---

## Files Modified

| File | Action | Purpose | Git state |
|------|--------|---------|-----------|
| `workspace/clients/brisken/deliverables/brisken-treasurycentral-restyle-blueprint.md` | Created | The new-chat restyle directive | Committed `c025f7f` |
| `workspace/clients/brisken/context/lead-generation/brisken-product-catalog.md` | Modified | "Spine reconciliation (2026-06-17)" section: deltas + AI naming + website-strategy fusion | On disk (path is gitignored: `context/`) |
| `workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md` | Modified | Two `next_steps`: spine sync + Dirk hierarchy confirm | Working tree (tracked, uncommitted) |

---

## Current Status

- Positioning truth reconciled and durable. Restyle blueprint committed and safe on `client/brisken/lead-gen-onepilot`.
- The OnePilot prototype is being edited in parallel by another session (today's "Brisken Website Aesthetic Elevation"; latest branch commit `b5835f8` "replace the OnePilot Agents text block with a command-stack diagram"). The two converged independently on the "OnePilot Agents" name. The restyle blueprint carries a coordination note to run in a worktree or sequence after that session.
- Platform (p1): custom SaaS build (expense-recon), no op-count budget; not relevant to this p2 session.

---

## Next Steps

1. Hand the blueprint to a fresh chat: "read `workspace/clients/brisken/deliverables/brisken-treasurycentral-restyle-blueprint.md` and execute it." Run it in a git worktree (the prototype is under concurrent edit).
2. Get Dirk's answer on the one open hierarchy question: is TreasuryCentral the umbrella with OnePilot nested as the AI layer, or are they peers? Does the public 5-product roster drop the other apps to subfunctions, or are they just off the Rome deck? This gates whether the 8-campaign menu collapses.
3. Optionally commit the `p2` spec `next_steps` edit (currently uncommitted) if not swept by the concurrent session.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/deliverables/brisken-treasurycentral-restyle-blueprint.md` (the build directive)
- `workspace/clients/brisken/context/lead-generation/brisken-product-catalog.md` -> "Spine reconciliation (2026-06-17)" (naming truth)
- `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html` (the target; verify the concurrent session's current state first)
- `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html` (Marketing tab; the four moves)

### Open Questions
- TreasuryCentral/OnePilot hierarchy (Dirk). Build proceeds on the nested assumption; reversible.
- Public roster: five named vs the full eight-campaign menu. Confirm scope before collapsing campaigns.

### Working Notes
- The Messaging Spine was a pasted document, not a repo file; its truth is captured in the catalog reconciliation, which is the durable source.
- The prototype already implements marketing Moves 1 (shadow integrations), 2 (benchmark band 81/62/38), 4 (SAP trust band), and the BST rename. The blueprint only adds the cockpit + Move 3 (named AI).
- The lead-gen strategy deck and the catalog exist in both the main clone and the `agentic-ops1-recon-main` worktree; paths in the blueprint are relative to the repo root, valid in either.

### Reference Materials
- Blueprint commit: `c025f7f` on `client/brisken/lead-gen-onepilot`.
- Concurrent prototype work: branch commit `b5835f8`; today's session "Brisken Website Aesthetic Elevation".

---

## How to Continue

The decision work is done and recorded. Pick up by handing the blueprint to a fresh chat in a worktree. Do not edit the prototype from two sessions at once; the untracked-file loss this session (recovered) is the warning.

---

## Strategic Feedback

### What Worked Well This Session
- Directional inputs ("compare", "what do you think", "I liked TreasuryCentral", "generate a blueprint") each built cleanly on the prior turn; no rework. Recording naming truth in the catalog as we went meant the blueprint could reference it rather than restate it.

### Suggestions
- For concurrent Brisken work, open the second stream in a git worktree before starting. This session and the prototype-elevation session shared one clone; an untracked deliverable was swept and had to be recreated. The worktree memory exists; the habit lapsed.

### System Health
- The B2 verification at checkpoint (checking git/file state before asserting "done") caught a silent work-loss the user would otherwise have hit later. Cheap insurance; worth keeping as the default checkpoint discipline.
- The `stop-b1-gate` fired twice this session: once on a genuine closing-offer deferral (corrected by acting) and once as a false positive on an in-answer "if you want a safer option" alternative. The gate is holding on real deferrals; the false-positive rate on the "if you want" pattern is worth a look if it keeps catching non-deferrals.
- Autonomy score: 0 human interventions this session. The two gate fires were structural (hook), and the work-loss was self-caught at checkpoint.
