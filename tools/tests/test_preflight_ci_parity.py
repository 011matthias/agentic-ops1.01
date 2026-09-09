"""preflight-hooks.py must invoke the same pytest as the CI `hooks` job.

A local gate that is a strict subset of the remote one is worse than no local
gate, because it is trusted: every module guarded by `pytest.importorskip` on a
dep CI has and preflight lacks is silently skipped while the tool still prints
"the CI hooks job should pass". `preflight-hooks.py` carries that lesson as a
comment after the 2026-09-08 drift (requests / httpx / pyyaml), and drifted
again on 2026-09-09 when openpyxl was added to CI. A comment is not a gate;
this is.

Compared as sets of `--with` deps, so ordering is free.
"""
import re

from hooklib import REPO, TOOLS

CI = REPO / ".github" / "workflows" / "ci.yml"
PREFLIGHT = TOOLS / "preflight-hooks.py"


def _deps(text: str) -> set:
    return set(re.findall(r'--with"?,?\s*"?([A-Za-z0-9_.-]+)"?', text))


def _ci_hooks_pytest_line() -> str:
    for line in CI.read_text(encoding="utf-8").splitlines():
        if "pytest tools/tests" in line:
            return line
    raise AssertionError("no `pytest tools/tests` run line in the CI hooks job")


def _preflight_pytest_argv() -> str:
    text = PREFLIGHT.read_text(encoding="utf-8")
    m = re.search(r"PYTEST = \((.*?)\]\)", text, re.S)
    assert m, "PYTEST invocation not found in preflight-hooks.py"
    return m.group(1)


def test_preflight_matches_ci_dependency_set():
    ci, pre = _deps(_ci_hooks_pytest_line()), _deps(_preflight_pytest_argv())
    assert pre == ci, (
        f"preflight-hooks.py and the CI hooks job disagree on pytest deps.\n"
        f"  only in CI:        {sorted(ci - pre)}\n"
        f"  only in preflight: {sorted(pre - ci)}")


def test_both_run_the_same_test_path():
    assert "pytest tools/tests" in _ci_hooks_pytest_line()
    assert '"pytest", "tools/tests"' in _preflight_pytest_argv()
