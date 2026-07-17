"""optimize_overview.py: behavior tests against throwaway fixture repos.

Follows the test_optimize_run.py pattern: the tool is driven as a
subprocess (`uv run <real tool path>` with cwd=tmp repo) so its PEP 723
deps (pyyaml) resolve without polluting the dep-free CI test env. The
tool discovers its repo via `git rev-parse`, so fixtures are isolated.
"""
import subprocess
from pathlib import Path

from hooklib import REPO

TOOL = REPO / "tools" / "optimize_overview.py"


def _git(repo: Path, *args: str) -> None:
    proc = subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"git {args}: {proc.stderr}"


def _run(repo: Path, *args: str) -> str:
    proc = subprocess.run(["uv", "run", str(TOOL), *args], cwd=str(repo),
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _write(repo: Path, rel: str, content: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def make_fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "fleet"
    repo.mkdir()
    _git(repo.parent, "init", "-q", str(repo))

    # CLOSED run (stopped row + SUMMARY.md), project brisken
    _write(repo, "docs/optimize/brisken-recon-v1/RUN.md",
           "---\ntag: brisken-recon-v1\nproject: brisken\n"
           "direction: maximize\n---\nx\n")
    _write(repo, "docs/optimize/brisken-recon-v1/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
           "0\taaaaaaa\t80.0\t0\tbaseline\tbaseline\n"
           "1\tbbbbbbb\t83.5\t+3.5\tkeep\ttighten normalization\n"
           "2\tccccccc\t81.0\tNA\tdiscard\tlooser threshold\n"
           "3\tddddddd\t85.0\t+1.5\tkeep\tseed table\n"
           "4\t-\tNA\tNA\tstopped\tgoal reached\n")
    _write(repo, "docs/optimize/brisken-recon-v1/SUMMARY.md", "s\n")

    # INTERRUPTED run (journal, no stopped row, no run.json), project sys
    _write(repo, "docs/optimize/sys-teach-demo/RUN.md",
           "---\ntag: sys-teach-demo\nproject: sys\n"
           "direction: minimize\n---\nx\n")
    _write(repo, "docs/optimize/sys-teach-demo/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
           "0\taaaaaaa\t26145.0\t0\tbaseline\tbaseline\n"
           "1\tbbbbbbb\t25425.0\t-720\tkeep\tstrip comments\n")

    # ACTIVE run (run.json in this checkout), project platform
    _write(repo, "docs/optimize/platform-weight-v1/RUN.md",
           "---\ntag: platform-weight-v1\nproject: platform\n"
           "direction: minimize\n---\nx\n")
    _write(repo, ".claude/optimize/run.json",
           '{"tag": "platform-weight-v1", "round": 3, '
           '"best_score": 41200.0, "branch": "optimize/platform-weight-v1"}\n')
    return repo


def test_fleet_view_classifies_all_three_statuses(tmp_path):
    repo = make_fixture_repo(tmp_path)
    out = _run(repo)

    assert "project: brisken" in out
    assert "brisken-recon-v1" in out and "CLOSED" in out
    assert "80.0 -> 85.0" in out          # baseline -> last keep (ratchet)
    assert "summary=yes" in out

    assert "project: sys" in out
    assert "INTERRUPTED" in out
    assert "resume` or `stop" in out      # warning with remediation

    assert "project: platform" in out
    assert "ACTIVE" in out
    assert "r3 best=41200.0" in out


def test_project_filter_limits_output(tmp_path):
    repo = make_fixture_repo(tmp_path)
    out = _run(repo, "--project", "brisken")
    assert "brisken-recon-v1" in out
    assert "sys-teach-demo" not in out
    assert "platform-weight-v1" not in out


def test_empty_repo_reports_no_runs(tmp_path):
    repo = tmp_path / "empty"
    repo.mkdir()
    _git(repo.parent, "init", "-q", str(repo))
    assert "no runs found" in _run(repo)


def test_manifest_without_project_groups_unassigned(tmp_path):
    repo = tmp_path / "legacy"
    repo.mkdir()
    _git(repo.parent, "init", "-q", str(repo))
    _write(repo, "docs/optimize/old-run/RUN.md",
           "---\ntag: old-run\ndirection: minimize\n---\nx\n")
    _write(repo, "docs/optimize/old-run/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
           "0\taaaaaaa\t10\t0\tbaseline\tbaseline\n"
           "1\t-\tNA\tNA\tstopped\tdone\n")
    out = _run(repo)
    assert "project: (unassigned)" in out
    assert "CLOSED" in out
    assert "summary=NO" in out            # closed without SUMMARY.md warns
    assert "closed without SUMMARY.md" in out
