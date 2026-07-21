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


def test_scoreboard_measures_the_loop_itself(tmp_path):
    repo = make_fixture_repo(tmp_path)
    out = _run(repo, "--scoreboard")
    assert "SCOREBOARD" in out
    # brisken run: 3 experiment rows (keep, discard, keep) -> 2 keeps;
    # sys run: 1 (keep); platform run has no journal.
    assert "experiment rounds     4" in out
    assert "3/4 (75%)" in out
    # no manifest declares assets -> nothing classifies as production
    assert "0/3 production" in out


def test_scoreboard_counts_production_assets(tmp_path):
    """The production-vs-planning split is the metric the harness most needs:
    a loop that only optimizes its own planning JSON is advising itself."""
    repo = tmp_path / "kinds"
    repo.mkdir()
    _git(repo.parent, "init", "-q", str(repo))
    _write(repo, "docs/optimize/plan-run/RUN.md",
           "---\ntag: plan-run\nproject: p\ndirection: maximize\n"
           "assets:\n  - workspace/projects/upwork/gtm-plan.json\n---\nx\n")
    _write(repo, "docs/optimize/plan-run/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
           "0\ta\t1\t0\tbaseline\tb\n1\t-\tNA\tNA\tstopped\tdone\n")
    _write(repo, "docs/optimize/real-run/RUN.md",
           "---\ntag: real-run\nproject: p\ndirection: minimize\n"
           "assets:\n  - platform/public/clients/acme/**\n---\nx\n")
    _write(repo, "docs/optimize/real-run/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
           "0\ta\t9\t0\tbaseline\tb\n1\t-\tNA\tNA\tstopped\tdone\n")
    out = _run(repo, "--scoreboard")
    assert "1/2 production" in out
    assert "1 planning-model" in out


def test_stale_checkout_names_the_runs_it_cannot_see(tmp_path):
    """This view derives from the working tree, so a checkout behind
    origin/main under-reports closed runs and silently skews every metric.
    That is not hypothetical: it is what a 13-PR-stale main did during the
    audit that motivated this check (1 of 4 runs shown, keep rate 80% vs the
    true 48%)."""
    repo = make_fixture_repo(tmp_path)
    _git(repo, "config", "user.email", "t@t.local")
    _git(repo, "config", "user.name", "T")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "checkout state")
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()

    # a run that landed on origin/main but is not in this checkout
    _write(repo, "docs/optimize/newer-run/RUN.md",
           "---\ntag: newer-run\nproject: sys\ndirection: minimize\n---\nx\n")
    _write(repo, "docs/optimize/newer-run/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
           "0\ta\t5\t0\tbaseline\tb\n1\t-\tNA\tNA\tstopped\tdone\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "landed on origin/main")
    ahead = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", ahead)
    _git(repo, "reset", "-q", "--hard", head)

    out = _run(repo, "--scoreboard")
    assert "STALE CHECKOUT" in out
    assert "newer-run" in out
    assert "MISSING 1 run(s)" in out


def test_completeness_is_unknown_without_an_origin_ref(tmp_path):
    """No origin/main to compare against is not the same as 'complete';
    claiming a match it never checked would be exactly the kind of
    unearned confidence this harness exists to prevent."""
    repo = make_fixture_repo(tmp_path)
    out = _run(repo, "--scoreboard")
    assert "STALE CHECKOUT" not in out
    assert "UNKNOWN (no origin/main ref" in out


def test_sweep_is_silent_on_a_clean_fleet(tmp_path):
    """A SessionStart sweep that chatters on every session gets ignored;
    silence when there is nothing to decide is what makes it wirable."""
    repo = tmp_path / "clean"
    repo.mkdir()
    _git(repo.parent, "init", "-q", str(repo))
    _write(repo, "docs/optimize/done-run/RUN.md",
           "---\ntag: done-run\nproject: p\ndirection: minimize\n---\nx\n")
    _write(repo, "docs/optimize/done-run/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
           "0\ta\t10\t0\tbaseline\tb\n1\t-\tNA\tNA\tstopped\tdone\n")
    _write(repo, "docs/optimize/done-run/SUMMARY.md", "s\n")
    assert _run(repo, "--sweep").strip() == ""


def test_sweep_surfaces_runs_needing_a_decision(tmp_path):
    repo = make_fixture_repo(tmp_path)
    out = _run(repo, "--sweep")
    assert "need attention" in out
    assert "sys-teach-demo: INTERRUPTED" in out          # no stopped row
    assert "platform-weight-v1: ACTIVE" in out           # live run state
    assert "brisken-recon-v1" not in out                 # closed WITH summary


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
