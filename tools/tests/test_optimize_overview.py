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



def test_legacy_six_column_journal_reports_no_timing(tmp_path):
    """Runs closed before the timestamp column must keep parsing.

    results.tsv is append-only and every run closed before 2026-07-22 carries
    six-column rows. A parser that assumed seven would silently drop them from
    the scoreboard - the same under-reporting the STALE CHECKOUT guard exists
    to prevent, arriving from the other direction. The whole fixture repo here
    is six-column, so the timing line must say so rather than guess.
    """
    repo = make_fixture_repo(tmp_path)
    out = _run(repo, "--scoreboard")
    assert "minutes per round     n/a (0/3 runs carry timestamps)" in out, out
    # ...and the historical six-column runs are still counted, not dropped.
    assert "experiment rounds     4" in out, out


def test_timestamped_journal_yields_minutes_per_round(tmp_path):
    repo = make_fixture_repo(tmp_path)
    _write(repo, "docs/optimize/timed-run/RUN.md",
           "---\ntag: timed-run\nproject: sys\ndirection: minimize\n---\nx\n")
    _write(repo, "docs/optimize/timed-run/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\ttimestamp\n"
           "0\taaaaaaa\t100.0\t0\tbaseline\tbase\t2026-07-22T10:00:00\n"
           "1\tbbbbbbb\t90.0\t-10\tkeep\tone\t2026-07-22T10:02:00\n"
           "2\tccccccc\t85.0\t-5\tkeep\ttwo\t2026-07-22T10:06:00\n")
    _write(repo, "docs/optimize/timed-run/SUMMARY.md", "s\n")
    out = _run(repo, "--scoreboard")
    # 6 minutes spanned / 2 experiment rounds = 3.0
    assert "minutes per round     3.0 median over 1/4 timed run(s)" in out, out


def test_unparseable_timestamp_does_not_crash_the_overview(tmp_path):
    """A hand-mangled stamp must degrade to 'no timing', never raise.

    optimize_overview is a read-only reporting surface wired into the
    SessionStart sweep; it is required to fail open.
    """
    repo = make_fixture_repo(tmp_path)
    _write(repo, "docs/optimize/bad-stamp/RUN.md",
           "---\ntag: bad-stamp\nproject: sys\ndirection: minimize\n---\nx\n")
    _write(repo, "docs/optimize/bad-stamp/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\ttimestamp\n"
           "0\taaaaaaa\t100.0\t0\tbaseline\tbase\tnot-a-date\n"
           "1\tbbbbbbb\t90.0\t-10\tkeep\tone\talso-bad\n")
    out = _run(repo, "--scoreboard")   # _run asserts exit 0
    assert "minutes per round     n/a" in out, out


def _with_summary(repo: Path, tag: str, project: str, summary: str) -> None:
    _write(repo, f"docs/optimize/{tag}/RUN.md",
           f"---\ntag: {tag}\nproject: {project}\ndirection: minimize\n---\nx\n")
    _write(repo, f"docs/optimize/{tag}/results.tsv",
           "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
           "0\taaaaaaa\t10.0\t0\tbaseline\tbase\n")
    _write(repo, f"docs/optimize/{tag}/SUMMARY.md", summary)


def test_prior_art_surfaces_dead_ends_and_sensitivities(tmp_path):
    """The doctrine's promise - 'a documented dead end prevents re-running the
    same experiments' - had no read path. This is that path."""
    repo = make_fixture_repo(tmp_path)
    _with_summary(repo, "platform-a", "platform",
                  "# a\n\n## Kept changes\n\nKEPTBODYSENTINEL\n\n"
                  "## Dead ends\n\n- extraction is score-neutral\n\n"
                  "## Sensitivities\n\n- minification is a judgment call\n\n"
                  "## What a human should review\n\nREVIEWBODYSENTINEL\n")
    out = _run(repo, "--prior-art", "platform")
    assert "extraction is score-neutral" in out
    assert "minification is a judgment call" in out
    # ...and NOT the sections a new manifest does not need. Distinctive
    # sentinels, because a plain word like "nothing" also occurs in the
    # tool's own "nothing to inherit" line and would pass vacuously.
    assert "KEPTBODYSENTINEL" not in out
    assert "REVIEWBODYSENTINEL" not in out


def test_prior_art_is_scoped_to_the_project_slug(tmp_path):
    repo = make_fixture_repo(tmp_path)
    _with_summary(repo, "platform-a", "platform",
                  "## Dead ends\n\n- platform lesson\n")
    _with_summary(repo, "brisken-a", "brisken",
                  "## Dead ends\n\n- brisken lesson\n")
    out = _run(repo, "--prior-art", "platform")
    assert "platform lesson" in out
    assert "brisken lesson" not in out, "leaked another project's journal"


def test_prior_art_names_runs_that_predate_the_heading_contract(tmp_path):
    """Four runs shipped before the contract existed. Silently showing
    nothing for them would read as 'no prior art', which is the opposite of
    the truth and worse than saying so."""
    repo = make_fixture_repo(tmp_path)
    _with_summary(repo, "platform-old", "platform",
                  "# old\n\n## Model limitations\n\nfreeform prose\n")
    out = _run(repo, "--prior-art", "platform")
    assert "no `## Dead ends`" in out
    assert "predate the heading contract" in out
    assert "platform-old" in out


def test_prior_art_on_a_first_run_says_so(tmp_path):
    repo = make_fixture_repo(tmp_path)
    out = _run(repo, "--prior-art", "no-such-project")
    assert "This is the first" in out


def test_prior_art_heading_match_is_case_and_colon_tolerant(tmp_path):
    """A run that wrote `## Dead Ends:` must not be invisible."""
    repo = make_fixture_repo(tmp_path)
    _with_summary(repo, "platform-c", "platform",
                  "## Dead Ends:\n\n- still counts\n")
    out = _run(repo, "--prior-art", "platform")
    assert "still counts" in out
