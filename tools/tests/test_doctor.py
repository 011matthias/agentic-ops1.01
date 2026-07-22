"""doctor.py: smoke tests for the health-check aggregator.

The battery itself is other tools' tested behavior; these tests pin the
ORCHESTRATION contract: check registry shape, --list/--only wiring, result
classification, and the exit-code rule (any RED -> 1).
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys

from hooklib import TOOLS


def _load():
    spec = importlib.util.spec_from_file_location("doctor", TOOLS / "doctor.py")
    mod = importlib.util.module_from_spec(spec)
    # dataclass creation on 3.13+ resolves cls.__module__ via sys.modules,
    # so a spec-loaded module must be registered before exec.
    sys.modules["doctor"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_registry_shape():
    d = _load()
    names = [c.name for c in d.CHECKS]
    assert len(names) == len(set(names)), "check names must be unique"
    for c in d.CHECKS + d.HEALS + (d.DEEP_CHECK,):
        assert (TOOLS.parent / c.args[0]).is_file(), f"missing script: {c.args[0]}"
        assert c.timeout > 0


def test_heals_are_the_sanctioned_correctives_only():
    d = _load()
    scripts = {c.args[0] for c in d.HEALS}
    assert scripts == {"tools/wire-hooks.py", "tools/normalize-client-pages.py"}
    assert ("--ensure",) == tuple(a for c in d.HEALS for a in c.args[1:] if c.name == "wire-hooks-ensure")


def _cli(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / "doctor.py"), *args],
        capture_output=True, text=True, timeout=timeout,
    )


def test_list_exits_zero_and_names_every_check():
    d = _load()
    proc = _cli("--list")
    assert proc.returncode == 0
    for c in d.CHECKS:
        assert c.name in proc.stdout


def test_unknown_only_exits_two():
    proc = _cli("--only", "no-such-check")
    assert proc.returncode == 2


def test_single_fast_check_end_to_end():
    # check-index is sub-second and hermetic to the repo: real subprocess,
    # real uv launch path, real JSON report write.
    proc = _cli("--only", "check-index", timeout=180)
    assert proc.returncode in (0, 1)  # health verdict, not a crash
    assert "check-index" in proc.stdout
    assert "[doctor]" in proc.stdout


def test_run_check_classifies_timeout(monkeypatch):
    d = _load()

    def fake_run(*a, **k):
        raise subprocess.TimeoutExpired(cmd=a[0], timeout=1)

    monkeypatch.setattr(d.subprocess, "run", fake_run)
    r = d._run_check(d.CHECKS[0])
    assert r["timed_out"] is True and r["ok"] is False


def test_run_check_classifies_red(monkeypatch):
    d = _load()

    def fake_run(*a, **k):
        return subprocess.CompletedProcess(a[0], 1, stdout="boom\n", stderr="")

    monkeypatch.setattr(d.subprocess, "run", fake_run)
    r = d._run_check(d.CHECKS[0])
    assert r["ok"] is False and r["exit"] == 1 and r["tail"] == ["boom"]
