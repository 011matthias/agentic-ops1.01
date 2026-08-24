# Enforcement-layer test suite

Regression protection for `.claude/hooks/*` and the wiring contract in
`tools/wire-hooks.py`. This is the "internal muscle" Slice 1: it turns the
hand-run hook fixtures into a suite CI runs on every PR and push to main.

## Run

```bash
uv run --no-project --with pytest pytest tools/tests
```

(`pytest.ini` at repo root sets `testpaths`, so a bare `pytest` works locally
once pytest is installed.)

## Why it exists

Two failure classes dominate the friction register and both live in the Python
enforcement layer, which had zero automated coverage before this suite:

- **enforcement silently dead** (2026-05-18->19): the whole hook block was
  inert for a day with no signal. `test_hooks_registry.py` is the catch.
- **verification-theater**: gates declared working off a one-time manual smoke.
  The behavioral tests pin each gate's block/ask/allow boundary so a regex or
  scope tweak can't silently reopen a hole.

## Coverage

| Target | Test file | Kind |
|--------|-----------|------|
| Registry: every registered hook exists, compiles, disk set == `wire-hooks` registry (`tools/wire-hooks.py` `HOOK_COUNT` is the count's source of truth) | `test_hooks_registry.py` | structural |
| `no-auto-commit-gate` (B6) | `test_no_auto_commit_gate.py` | behavioral (documented 5-test matrix + PowerShell/.cmd spellings) |
| `cd-guard` | `test_cd_guard.py` | behavioral (Bash arm + PowerShell Set-Location arm) |
| `instantly-invasive-gate` (B5) | `test_instantly_invasive_gate.py` | behavioral (incl. -Method + compound read-then-mutate pin) |
| `_shell.normalize_command` | `test_shell_normalize.py` | unit (PowerShell/.cmd matching-view normalizer) |
| `post-action-gate` | `test_post_action_gate.py` | behavioral (ship/B2/streak boundaries, TMP-isolated counter) |
| `gate-skip-detector` | `test_gate_skip_detector.py` | behavioral (pre-publish / iteration-3x / residue boundaries; the 2026-08-24 streak-identity + CI-green false-positive pins) |
| `heredoc-size-gate` | `test_heredoc_size_gate.py` | behavioral (size / triple-quote / python-backslash deny classes, silent-allow set, `HEREDOC_GATE_ALLOW` seam) |
| `em-dash-strip-gate` | `test_em_dash_strip_gate.py` | scope unit + end-to-end |
| `session-pressure-meter` + nac capture | `test_session_state_smoke.py` | wraps existing smoke |
| `stop-b1-gate` | `test_stop_b1_gate.py` | behavioral |

**Not yet behaviorally covered** (registry/compile only): `post-write-gate`
(the dispatcher — a regression here silently kills all post-write content
validation), `input-classifier`, `reference-anchor-gate`,
`auto-approve-protected`. Listed here so the suite's coverage is never
mistaken for complete.

**Tracked gaps (out of scope for this suite):** PowerShell
`Set-Content`/`Out-File` file writes bypass the `Write|Edit`-matched hooks
(they arrive as commands, not Write payloads); the B6 authorization scan is
negation-blind ("don't push yet" matches `\bpush\b`) and verb-agnostic over
its 30-turn lookback.
