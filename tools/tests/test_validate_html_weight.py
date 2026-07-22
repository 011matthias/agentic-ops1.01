"""validate-html.py [artefact-weight]: size growth vs the committed origin/main
version (friction register 2026-07-22: a PDF regeneration silently doubled a
92KB logo blob into every page).

Unit tests drive check_weight() directly against throwaway fixture repos
(origin/main fabricated via `git update-ref`, the test_optimize_overview.py
pattern). CLI tests run the tool as a subprocess (stdlib-only, so
sys.executable reproduces the wired `uv run` behavior) and pin the
exit-code contract: WARNING findings report but never fail.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from hooklib import TOOLS

TOOL = TOOLS / "validate-html.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_html", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vh = _load()


def page(pad: int) -> str:
    """A structurally clean single-line page (no newlines, so blob size ==
    on-disk size regardless of autocrlf) padded to a controllable byte size."""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width'>"
        "<title>t</title></head><body><p>" + "x" * pad + "</p></body></html>"
    )


def _git(repo: Path, *args: str) -> None:
    proc = subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"git {args}: {proc.stderr}"


def _repo_with_baseline(tmp_path: Path, content: str,
                        set_origin: bool = True) -> Path:
    """Init a repo, commit page.html, mark that commit as origin/main.
    Returns the page path."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "config", "user.email", "t@t.local")
    _git(repo, "config", "user.name", "T")
    p = repo / "page.html"
    p.write_text(content, encoding="utf-8", newline="")
    _git(repo, "add", "page.html")
    _git(repo, "commit", "-q", "-m", "baseline")
    if set_origin:
        _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return p


# --- check_weight unit behavior ---------------------------------------------

def test_growth_over_threshold_warns(tmp_path):
    p = _repo_with_baseline(tmp_path, page(40_000))
    base = p.stat().st_size
    p.write_text(page(100_000), encoding="utf-8", newline="")
    cur = p.stat().st_size

    hits = vh.check_weight(p)
    assert len(hits) == 1
    h = hits[0]
    assert h["category"] == "artefact-weight"
    assert h["severity"] == "WARNING"
    assert "vs origin/main" in h["message"]
    assert f"({base} -> {cur} bytes)" in h["message"]
    assert "duplicated embedded assets" in h["message"]


def test_small_growth_below_absolute_floor_is_silent(tmp_path):
    # 100%+ relative growth, but only ~3 KB absolute: below the 10 KB floor.
    p = _repo_with_baseline(tmp_path, page(1_000))
    p.write_text(page(4_000), encoding="utf-8", newline="")
    assert vh.check_weight(p) == []


def test_growth_below_ratio_threshold_is_silent(tmp_path):
    # ~12 KB absolute growth (over the floor) but only ~12% relative: under 1.20.
    p = _repo_with_baseline(tmp_path, page(100_000))
    p.write_text(page(112_000), encoding="utf-8", newline="")
    assert vh.check_weight(p) == []


def test_new_file_not_on_origin_main_skips(tmp_path):
    p = _repo_with_baseline(tmp_path, page(1_000))
    new = p.parent / "new.html"
    new.write_text(page(200_000), encoding="utf-8", newline="")
    assert vh.check_weight(new) == []


def test_no_origin_main_ref_skips(tmp_path):
    p = _repo_with_baseline(tmp_path, page(1_000), set_origin=False)
    p.write_text(page(200_000), encoding="utf-8", newline="")
    assert vh.check_weight(p) == []


def test_file_outside_any_repo_skips(tmp_path):
    p = tmp_path / "loose.html"
    p.write_text(page(200_000), encoding="utf-8", newline="")
    assert vh.check_weight(p) == []


# --- CLI exit-code contract --------------------------------------------------

def _run_tool(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True)


def test_warning_alone_does_not_fail_exit_code(tmp_path):
    p = _repo_with_baseline(tmp_path, page(40_000))
    p.write_text(page(100_000), encoding="utf-8", newline="")
    r = _run_tool(str(p))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "[WARNING] [artefact-weight]" in r.stdout


def test_structural_failure_still_exits_1(tmp_path):
    # Regression guard: existing HIGH/MEDIUM behavior is unchanged.
    p = tmp_path / "broken.html"
    p.write_text("<html><head></head><body><div><p>x</div></body></html>",
                 encoding="utf-8")
    r = _run_tool(str(p))
    assert r.returncode == 1


def test_json_mode_includes_weight_finding(tmp_path):
    p = _repo_with_baseline(tmp_path, page(40_000))
    p.write_text(page(100_000), encoding="utf-8", newline="")
    r = _run_tool(str(p), "--format", "json")
    assert r.returncode == 0, r.stdout + r.stderr
    payload = json.loads(r.stdout)
    assert payload["by_category"].get("artefact-weight") == 1
    assert payload["by_severity"].get("WARNING") == 1
