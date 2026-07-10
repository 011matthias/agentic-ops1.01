# Fixtures for agnt_comms-critic

Two bare draft messages exercising the critic's draft-internal checks. The
grading contract lives in `.claude/agents/agnt_comms-critic.md` Step 6
(literal `OK`, or `## Critic findings — {N} item(s)` + numbered
`[SEV] [tag]` items + `Structural hits already flagged by validate-output.py:`
and `Memories applied:` tail lines).

- `test-clean.md` — well-formed deferential draft. Expected output: exactly `OK`.
- `test-violations.md` — planted violations for the four draft-internal
  checks: `[imperative-tone]` (HIGH), `[pre-concession]` (HIGH),
  `[unsourced-identity-claim]` (HIGH), `[closing-offer]` (MEDIUM).

**Two checks are inert on these fixtures by design.** Check 1
(unanswered-question) and Check 6 (anchor-drift) read
`workspace/clients/{client}/context/comms-log.md`; the fixtures ship no
client dir (a synthetic `workspace/clients/_fixture-*/` would be exactly the
file class rule_no_file_bloat W1 exists to prevent, and `context/` is
gitignored so it would not even ship). The eval grader therefore does not
assert on those two tags; if one fires anyway it is reported informationally,
not as a failure. v2 option: ship a fixture comms-log inside THIS directory
and pass it via the invocation preamble.

Re-runnable via `uv run tools/eval-agents.py run --fixture comms-clean`
(or `comms-violations`); grading contract pinned in
`tools/tests/test_agnt_evals.py`.
