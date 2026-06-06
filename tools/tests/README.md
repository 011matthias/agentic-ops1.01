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
| Registry: all 12 hooks exist, compile, disk set == `wire-hooks` registry | `test_hooks_registry.py` | structural |
| `no-auto-commit-gate` (B6) | `test_no_auto_commit_gate.py` | behavioral (documented 5-test matrix) |
| `cd-guard` | `test_cd_guard.py` | behavioral |
| `instantly-invasive-gate` (B5) | `test_instantly_invasive_gate.py` | behavioral |
| `em-dash-strip-gate` | `test_em_dash_strip_gate.py` | scope unit + end-to-end |
| `session-pressure-meter` + nac capture | `test_session_state_smoke.py` | wraps existing smoke |

**Not yet behaviorally covered** (registry/compile only): `stop-b1-gate`,
`gate-skip-detector`, `post-action-gate`, `post-write-gate`, `input-classifier`,
`reference-anchor-gate`, `auto-approve-protected`. `stop-b1-gate` already has a
documented 10/10 manual smoke worth porting next. Listed here so the suite's
coverage is never mistaken for complete.
