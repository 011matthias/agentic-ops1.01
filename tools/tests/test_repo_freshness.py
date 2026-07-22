"""repo_freshness: stale-checkout detector tests.

Fabricates `origin/main` in tmp git repos via `git update-ref` (the
test_optimize_overview / test_validate_html_weight pattern) so behind-counts
are exact and no network is touched. The CLI is exercised as a subprocess,
the adopter surface (warn_if_stale) in-process.
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

from hooklib import TOOLS


def _load():
    spec = importlib.util.spec_from_file_location(
        "repo_freshness", TOOLS / "repo_freshness.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=str(repo), check=True, capture_output=True,
    )


def _mk_repo(tmp_path: Path, behind: int) -> Path:
    """Repo whose HEAD is `behind` commits behind a fabricated origin/main."""
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "f.txt").write_text("0", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-m", "c0")
    for i in range(behind):
        (repo / "f.txt").write_text(str(i + 1), encoding="utf-8")
        _git(repo, "commit", "-am", f"c{i + 1}")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    if behind:
        _git(repo, "reset", "--hard", f"HEAD~{behind}")
    return repo


def test_behind_count_zero_when_current(tmp_path):
    rf = _load()
    assert rf.behind_count(_mk_repo(tmp_path, 0)) == 0


def test_behind_count_counts_missing_commits(tmp_path):
    rf = _load()
    assert rf.behind_count(_mk_repo(tmp_path, 3)) == 3


def test_behind_count_none_outside_git(tmp_path):
    rf = _load()
    assert rf.behind_count(tmp_path) is None


def test_banner_only_when_behind():
    rf = _load()
    assert rf.staleness_banner(None) is None
    assert rf.staleness_banner(0) is None
    line = rf.staleness_banner(4, context="unit test")
    assert "4 commit(s) behind" in line and "unit test" in line


def test_warn_if_stale_prints_and_returns(tmp_path):
    rf = _load()
    repo = _mk_repo(tmp_path, 2)
    buf = io.StringIO()
    assert rf.warn_if_stale("adopter", repo=repo, out=buf) == 2
    assert "[STALE-CHECKOUT]" in buf.getvalue()
    buf2 = io.StringIO()
    assert rf.warn_if_stale("adopter", repo=tmp_path, out=buf2) is None
    assert buf2.getvalue() == ""


def _cli(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / "repo_freshness.py"),
         "--repo", str(repo), *args],
        capture_output=True, text=True, timeout=30,
    )


def test_cli_json_reports_behind(tmp_path):
    proc = _cli(_mk_repo(tmp_path, 2), "--format", "json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["behind"] == 2 and data["stale"] is True


def test_cli_quiet_silent_when_current(tmp_path):
    proc = _cli(_mk_repo(tmp_path, 0), "--quiet")
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_cli_banner_when_behind(tmp_path):
    proc = _cli(_mk_repo(tmp_path, 1))
    assert proc.returncode == 0
    assert "[STALE-CHECKOUT]" in proc.stdout


def test_cli_exit_zero_outside_git(tmp_path):
    proc = _cli(tmp_path, "--quiet")
    assert proc.returncode == 0
