# agnt-evals grader samples

Synthetic, hand-written transcripts used by `tools/tests/test_agnt_evals.py`
to pin the deterministic graders in `tools/eval-agents.py`. They are NOT
model output and NOT agent fixtures — the agent fixtures live in the
sibling `agnt_*` directories; these files exercise the GRADING layer only,
so the grader's pass/fail matrix runs in CI with zero LLM calls.

| File | Grader | Expected |
|---|---|---|
| sample-intent-clean-pass.txt | grade_exact_ok | pass |
| sample-intent-violations-pass.txt | grade_intent_violations | pass |
| sample-intent-violations-missing-tag.txt | grade_intent_violations | fail (posture-mismatch absent) |
| sample-intent-violations-preamble.txt | grade_intent_violations | fail (preamble before header) |
| sample-intent-violations-misorder.txt | grade_intent_violations | fail (severity order violated) |
| sample-comms-violations-pass.txt | grade_comms_violations | pass |
| sample-research-blocked-pass.txt | grade_research_blocked | pass |
| sample-research-blocked-leakage.txt | grade_research_blocked | fail (SUCCESS-shape leakage) |
