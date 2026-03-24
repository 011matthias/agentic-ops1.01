# Sanity Check

Run these validations on every draft before presenting to the user. Report any warnings alongside the draft.

## 1. Claims Match Project State

For every factual claim in the message, verify against source files:

| Claim Type | Verify Against |
|------------|---------------|
| "X is live / done / complete" | Spec frontmatter `stage` field |
| "X is being tested" | Spec frontmatter `stage: test` |
| "We're working on X" | Latest checkpoint status |
| "Blocked on Y" | Latest checkpoint blockers list |
| Feature description | Spec content |
| Technical details (IDs, URLs) | infrastructure.yaml or infrastructure-ids.md |

**Flag if:** A claim doesn't match the verified state. Example: message says "A1 is live" but spec says `stage: build`.

## 2. Names Are Correct

Cross-reference every person name in the draft against the `contacts` list in comms-profile.md.

**Flag if:** A name appears that isn't in the contacts list, or a name is misspelled.

## 3. Technical Details Accurate

If the message includes scenario IDs, webhook URLs, data store names, connection references, or other technical identifiers:

- Verify each against `infrastructure.yaml` or `context/infrastructure-ids.md`
- Verify URLs are complete and correctly formatted

**Flag if:** Any ID or URL doesn't match the source files.

## 4. No Promises Beyond Scope

Check that the message doesn't:
- Commit to specific deadlines not discussed in process-notes or specs
- Promise features not in any spec's scope
- Imply included work that would be additional scope

**Flag if:** Message implies commitment to something not documented.

## 5. Blocker List Current

If the message references blockers or waiting items:
- Verify they match the latest checkpoint's blocker list
- Check if any have been resolved since the checkpoint

**Flag if:** Message mentions a blocker that may have been resolved, or misses an active blocker.

## 6. No Information Leakage

The message must NOT mention any of these to non-technical contacts:

- UTIL scenarios or test fixtures
- Agent infrastructure (build-orchestrator, testing-agent, etc.)
- Internal tooling (Make.com MCP, n8n MCP)
- `ship: false` items in infrastructure.yaml
- Test data or dev credentials
- Internal process (checkpoints, specs, skill system)
- Hourly rate or contract details (unless specifically discussing billing)

For technical-to-dev messages: some technical details are expected, but still avoid mentioning the agent/skill infrastructure.

**Flag if:** Any internal detail would be visible to the client.

## 7. Tone Consistency

Verify the draft matches the target tone from comms-profile:
- Casual messages shouldn't use formal language
- Professional messages shouldn't be too chatty
- Technical messages should match the recipient's technical level

**Flag if:** Tone significantly mismatches the profile.

## 8. Feasibility Check (scope/proposal/technical-to-dev only)

For message types `scope-discussion`, `proposal`, or `technical-to-dev`, also run [FEASIBILITY-CHECK.md](FEASIBILITY-CHECK.md):

- **Quality gates:** Full feature loop? Options differentiated? No over-promising?
- **Complexity flags:** Specs touched, new infrastructure needed, effort estimate, dependencies
- **Constraint check:** Client tech stack, team capability, contract context

Present feasibility findings as inline flags below the sanity check results.

---

## Reporting

Present warnings as a brief list below the draft:

```
---
Sanity check:
- [OK] Claims match project state
- [WARN] Message says "A1 is live" but spec shows stage: test
- [OK] Names verified
- [OK] No information leakage
```

Only show items that have warnings. If everything passes, show a single line: "Sanity check passed."
