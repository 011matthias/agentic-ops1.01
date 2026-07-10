"""Deterministic-grader tests for tools/eval-agents.py.

Grades the synthetic samples in tools/fixtures/agnt-evals/ (hand-written,
zero LLM calls) so the grading layer — the free half of the eval harness —
is pinned in CI. The paid generation half is local-only by design (the
agents read machine-local memory files a CI runner does not have).
"""
import importlib.util
import json

from hooklib import FIXTURES, REPO, TOOLS

SAMPLES = FIXTURES / "agnt-evals"


def _load():
    spec = importlib.util.spec_from_file_location("eval_agents", TOOLS / "eval-agents.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ea = _load()


def _sample(name):
    return (SAMPLES / name).read_text(encoding="utf-8")


def _passes(checks):
    return all(ok for _, ok, _ in checks)


def _failed_names(checks):
    return {name for name, ok, _ in checks if not ok}


# --- manifest sanity --------------------------------------------------------

def test_manifest_paths_exist():
    for fid, spec in ea.EVAL_SUITE.items():
        assert (REPO / spec["agent_md"]).is_file(), f"{fid}: agent md missing"
        assert (REPO / spec["fixture"]).is_file(), f"{fid}: fixture missing"
        assert spec["grader"] in ea.GRADERS, f"{fid}: unknown grader"


def test_sanitizer_strips_answer_key():
    for fid in ("intent-clean", "intent-violations"):
        raw = (REPO / ea.EVAL_SUITE[fid]["fixture"]).read_text(encoding="utf-8")
        assert "Expected agent behavior" in raw, "fixture lost its answer key?"
        assert "Expected agent behavior" not in ea.sanitize_fixture(raw)


def test_sanitizer_passthrough_when_no_key():
    assert ea.sanitize_fixture("plain text\nno key here\n") == "plain text\nno key here\n"


# --- grade_exact_ok ---------------------------------------------------------

def test_intent_clean_pass():
    assert _passes(ea.grade_exact_ok(_sample("sample-intent-clean-pass.txt")))


def test_exact_ok_rejects_ok_period():
    assert not _passes(ea.grade_exact_ok("OK."))


def test_exact_ok_rejects_trailing_text():
    assert not _passes(ea.grade_exact_ok("OK\nNo issues found."))


def test_exact_ok_tolerates_surrounding_whitespace():
    assert _passes(ea.grade_exact_ok("  OK \n"))


# --- grade_intent_violations -------------------------------------------------

def test_intent_violations_pass():
    checks = ea.grade_intent_violations(_sample("sample-intent-violations-pass.txt"))
    assert _passes(checks), _failed_names(checks)


def test_intent_violations_detects_missing_tag():
    checks = ea.grade_intent_violations(_sample("sample-intent-violations-missing-tag.txt"))
    failed = _failed_names(checks)
    assert "tag:posture-mismatch" in failed
    assert "item-count>=7" in failed


def test_intent_violations_detects_preamble():
    checks = ea.grade_intent_violations(_sample("sample-intent-violations-preamble.txt"))
    assert "no-preamble-header" in _failed_names(checks)


def test_intent_violations_detects_misorder():
    checks = ea.grade_intent_violations(_sample("sample-intent-violations-misorder.txt"))
    failed = _failed_names(checks)
    assert "severity-non-increasing" in failed
    # and ONLY the ordering check fails on this sample
    assert failed == {"severity-non-increasing"}


# --- grade_comms_violations ---------------------------------------------------

def test_comms_violations_pass():
    checks = ea.grade_comms_violations(_sample("sample-comms-violations-pass.txt"))
    assert _passes(checks), _failed_names(checks)


def test_comms_inert_tags_not_required():
    # The log-dependent tags must not be part of the required set.
    required_tags = {tag for _, tag in ea.COMMS_REQUIRED}
    assert "unanswered-question" not in required_tags
    assert "anchor-drift" not in required_tags


# --- grade_research_blocked ---------------------------------------------------

def test_research_blocked_pass():
    checks = ea.grade_research_blocked(_sample("sample-research-blocked-pass.txt"))
    assert _passes(checks), _failed_names(checks)


def test_research_blocked_detects_success_leakage():
    checks = ea.grade_research_blocked(_sample("sample-research-blocked-leakage.txt"))
    assert "no-success-leakage" in _failed_names(checks)


# --- compare ------------------------------------------------------------------

def _fake_grades(tmp_path, name, verdicts):
    d = tmp_path / name
    d.mkdir()
    (d / "grades.json").write_text(json.dumps({
        "git_rev": name,
        "fixtures": {fid: {"verdict": v} for fid, v in verdicts.items()},
    }), encoding="utf-8")
    return d


def test_compare_flags_regression(tmp_path, capsys):
    a = _fake_grades(tmp_path, "base", {"intent-clean": "GREEN", "comms-clean": "GREEN"})
    b = _fake_grades(tmp_path, "head", {"intent-clean": "GREEN", "comms-clean": "RED"})
    rc = ea.cmd_compare(type("A", (), {"run_a": str(a), "run_b": str(b)})())
    out = capsys.readouterr().out
    assert rc == 1 and "REGRESSION" in out and "comms-clean" in out


def test_compare_clean_and_improvement(tmp_path, capsys):
    a = _fake_grades(tmp_path, "base", {"intent-clean": "RED"})
    b = _fake_grades(tmp_path, "head", {"intent-clean": "GREEN"})
    rc = ea.cmd_compare(type("A", (), {"run_a": str(a), "run_b": str(b)})())
    out = capsys.readouterr().out
    assert rc == 0 and "improved" in out


# --- local re-grade determinism (auto-skips in CI / fresh machines) -----------

def test_regrade_is_deterministic():
    import pytest
    runs = sorted((REPO / ".scratch" / "evals").glob("*/grades.json"))
    if not runs:
        pytest.skip("no local graded eval run present")
    run_dir = runs[-1].parent
    before = runs[-1].read_text(encoding="utf-8")
    ea.grade_run(run_dir)
    after = (run_dir / "grades.json").read_text(encoding="utf-8")
    assert before == after
