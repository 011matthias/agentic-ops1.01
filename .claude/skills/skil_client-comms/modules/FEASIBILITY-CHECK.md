# Feasibility Check

Quality gates and complexity flags for outbound messages that discuss scope, propose work, or present technical options. Triggered automatically by SANITY-CHECK.md for message types: `scope-discussion`, `proposal`, `technical-to-dev`.

---

## Quality Gates

These catch the structural problems from the Meji Media drafting retrospective (Rounds 4 and 5).

### 1. Full Feature Loop

Every feature or capability mentioned in the message must cover the complete loop:
- **Trigger:** How does it start?
- **Action:** What does it do?
- **Measurement:** How do you know it's working?

**Flag if:** A feature is proposed without explaining how results are measured or verified. Example: "We'll set up A/B testing for the emails" without mentioning how they'll see which variant performs better.

**Fix:** Add a measurement section or acknowledge it as a follow-up item.

### 2. Option Differentiation

When presenting options to the client, each must be meaningfully different.

**Flag if:**
- Two options differ only in minor detail (e.g., "basic formulas" vs "formulas with weekly breakdown")
- Options are essentially the same with different labels
- More than 3 options (decision fatigue)

**Fix:** Merge similar options. Ensure each remaining option has an obviously different trade-off (e.g., cost vs capability, simple vs comprehensive, DIY vs automated).

### 3. No Over-Promising

Check claims against what's actually built, tested, or feasible.

**Flag if:**
- Message implies a timeline that hasn't been discussed
- Message commits to scope beyond what's in specs
- Message uses confidence language ("will definitely", "guaranteed") for uncertain outcomes

**Fix:** Soften language or add caveats. "Should take about X" not "will take exactly X."

---

## Complexity Flags

These give the user grounding when discussing work with clients. Not shown to the client — shown alongside the draft as internal notes.

### Specs Touched

Count how many existing specs this proposed work would affect.

- **0 specs:** Entirely new work. May need a new spec.
- **1 spec:** Contained change. Note which one.
- **2+ specs:** Cross-cutting. Flag it: "This touches specs a1 and a3. Changes need to be coordinated."

### New Infrastructure Required

Flag if the proposal implies infrastructure that doesn't exist yet:

- New scenario/workflow needed
- New data store or database table
- New webhook or API endpoint
- New credentials or third-party access
- New sheet/document structure

Example: "Feasibility: This would require a new Make.com scenario for the weekly report."

### Effort Estimation

Provide a rough effort range based on:

- **Orchestrator complexity:** Make.com scenarios typically 2-6h per scenario. n8n workflows similar. Trigger.dev tasks 1-4h per task.
- **Integration count:** Each new external system adds 1-3h for auth, testing, edge cases.
- **Similar past work:** Reference comparable features already built for this client.

Format: "Estimated effort: ~3-4h (similar to the A2 follow-up sequence build)."

Don't give exact hours to the client. These are internal reference numbers for the user.

### Dependency Check

Flag if the proposed work depends on things that aren't resolved yet:

- Open items from the comms log ("This depends on Anuj confirming the API format, which is still open")
- Undelivered prerequisites ("Need the email templates before this can be built")
- Third-party access not yet granted

---

## Constraint Check

Cross-reference against known project constraints.

### Client Tech Stack
From `context/process-notes.md` and `infrastructure.yaml`:
- Does the client's existing setup support what's being proposed?
- Are there known limitations? (e.g., "their CRM doesn't support webhooks")

### Team Capability
From `context/comms-profile.md` (contact technical levels):
- Is the proposed solution something the client can maintain?
- Will a non-technical contact need to interact with it? If so, is the UX simple enough?

### Contract Context
From `context/process-notes.md`:
- Hourly vs fixed? (hourly: effort estimates are informational; fixed: effort estimates affect margins)
- Scope boundaries defined? (flag if proposal goes beyond agreed scope)

---

## Output Format

Present feasibility findings as inline flags below the draft, similar to sanity check warnings:

```
---
Feasibility:
- [FLAG] No measurement mechanism for A/B testing. How will they know which variant works?
- [INFO] This would require a new Make.com scenario (~3-4h). Touches specs a1, a3.
- [INFO] Estimated effort: ~2-3h, similar to the reply detection build.
- [WARN] Depends on email templates from Gurmej (still open).
```

Severity levels:
- **[FLAG]** — Quality issue in the draft itself. Should be fixed before sending.
- **[WARN]** — Risk or dependency the user should be aware of. May or may not need fixing.
- **[INFO]** — Contextual note for the user's reference. Not a problem.

If everything passes: "Feasibility check passed."
