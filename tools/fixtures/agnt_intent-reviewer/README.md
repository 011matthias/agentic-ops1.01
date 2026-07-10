# Test fixtures for agnt_intent-reviewer

Persistent fixtures for re-running the intent-reviewer's smoke tests across sessions. Re-runnable; never deleted.

## Files

- **test-violations.md** — paired user-input + plan with planted violations exercising I1–I7. Expected output: FAIL shape with at least 7 distinct findings (severity HIGH for I1, I2, I4, I6, I7; severity MEDIUM for I3, I5).
- **test-clean.md** — paired user-input + plan with clean directive + anchored plan. Expected output: `OK`.

## How to re-run

1. Open a session in this repo.
2. Invoke the agent via the Task tool with `subagent_type: agnt_intent-reviewer` (or, while the agent isn't picked up by the runtime registry mid-session of its creation, role-play via the `general-purpose` agent with the agnt_intent-reviewer.md content as the prompt — same workaround used in Phase 1/2/3).
3. Pass `plan_path` = absolute path to the fixture file.
4. Compare the agent's output against the "Expected agent behavior" section at the bottom of each fixture.

## What "PASS" means for the fixtures

- **test-violations.md PASS** = agent returns a FAIL shape that catches the full violation set listed at the bottom of the file, with no false positives and no rewrites. Severity ordering: HIGH first, MEDIUM after. Each finding cites a memory or rule by filename.
- **test-clean.md PASS** = agent returns exactly `OK` (single line, no preamble, no trailing text).

## What "FAIL" means

- test-violations.md FAIL modes: missing one of I1–I7 findings; proposing a replacement plan; padding with vague advice; mis-classifying input as `directive` when Context dominates and shows pushback.
- test-clean.md FAIL modes: any output other than `OK`; flagging non-violations; padding ("plan looks good!" etc.).

## Notes

- These fixtures are independent of any real client data. The Gurmej/Matthias names + the 983 figure mirror real Meji context only for realism; the violation patterns are the test.
- The clean fixture intentionally includes a `Context` section with previously-defined items to exercise the agent's I4 (re-ask-of-stated) negative case. Adding a re-ask in the plan would be a fixture mutation, not a behavior change.
- If a check fires when it shouldn't (false positive) OR misses when it should (false negative), it's a fixture incident — log against the agent spec, not the fixture, unless the fixture itself is ambiguous.

## Runnable via the eval harness

Re-runnable via `uv run tools/eval-agents.py run --fixture intent-clean` (or `intent-violations`); the answer-key section below is stripped before the fixture reaches the agent, and the grading contract is pinned in `tools/tests/test_agnt_evals.py`.
