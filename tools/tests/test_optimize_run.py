"""optimize_run.py engine: protocol regression tests in throwaway git repos.

Each test builds a minimal tmp repo (toy scorer pinned in ITS OWN PINS.json,
asset file, RUN.md manifest), then drives the REAL engine as a subprocess
(`uv run <real engine path>` with cwd=tmp repo; the engine discovers its
repo via `git rev-parse`, so state/journal/branches are fully isolated).

The engine executes everything a fumble could corrupt - so these tests
assert BEHAVIOR: branch history shape, TSV rows, git tree state after
keep/discard/crash, lock-state lifecycle.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from hooklib import REPO

ENGINE = REPO / "tools" / "optimize_run.py"
FIXTURES = REPO / "tools" / "fixtures" / "optimize"
PYEXE = sys.executable.replace("\\", "/")

sys.path.insert(0, str(REPO / "tools"))
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("pin_scorer", REPO / "tools" / "pin_scorer.py")
_pin = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_pin)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"git {args}: {proc.stderr}"
    return proc


def make_repo(tmp_path: Path, numbers=("5", "4"), guard=False,
              scorer="toy-scorer.py", direction="minimize",
              budgets: dict | None = None, stop: dict | None = None,
              assets=("numbers.txt",), mode="converge",
              pin_sha: str | None = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "tools" / "scorers").mkdir(parents=True)
    (repo / ".claude" / "hooks").mkdir(parents=True)
    (repo / "docs" / "optimize" / "t1").mkdir(parents=True)

    shutil.copy(REPO / "tools" / "pin_scorer.py", repo / "tools" / "pin_scorer.py")
    shutil.copy(REPO / ".claude" / "hooks" / "_globs.py",
                repo / ".claude" / "hooks" / "_globs.py")
    scorer_dst = repo / "tools" / "scorers" / scorer
    shutil.copy(FIXTURES / scorer, scorer_dst)

    pins = {scorer: {"sha": pin_sha or _pin.blob_sha(str(scorer_dst)),
                     "direction": _pin.scorer_direction(str(scorer_dst)),
                     "pinned": "2026-07-17"}}
    (repo / "tools" / "scorers" / "PINS.json").write_text(
        json.dumps(pins, indent=2), encoding="utf-8")

    (repo / "numbers.txt").write_text("\n".join(numbers) + "\n",
                                      encoding="utf-8")
    (repo / ".gitignore").write_text(
        "/.claude/optimize/\ndocs/optimize/*/logs/\n__pycache__/\n",
        encoding="utf-8")

    b = {"rounds": 10, "wall_clock_minutes": 240,
         "score_timeout_seconds": 120, "max_rework_attempts": 2}
    b.update(budgets or {})
    s = {"consecutive_reverts": 5}
    s.update(stop or {})
    guard_lines = ""
    if guard:
        shutil.copy(FIXTURES / "toy-guard.py", repo / "toy-guard.py")
        guard_lines = (f"guards:\n  - {PYEXE} toy-guard.py numbers.txt\n"
                       f"guard_files:\n  - toy-guard.py\n")
    manifest = (
        "---\n"
        "tag: t1\n"
        "goal: minimize the sum of numbers.txt\n"
        f"scorer: tools/scorers/{scorer}\n"
        "scorer_args:\n  - numbers.txt\n"
        f"direction: {direction}\n"
        "assets:\n" + "".join(f"  - {a}\n" for a in assets)
        + guard_lines
        + "budgets:\n" + "".join(f"  {k}: {v}\n" for k, v in b.items())
        + f"mode: {mode}\n"
        + "stop:\n" + "".join(f"  {k}: {v}\n" for k, v in s.items())
        + "---\n\nToy run for engine tests.\n"
    )
    (repo / "docs" / "optimize" / "t1" / "RUN.md").write_text(
        manifest, encoding="utf-8")

    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    _git(repo, "config", "user.email", "test@test.local")
    _git(repo, "config", "user.name", "Engine Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def engine(repo: Path, *args: str, env: dict | None = None,
           expect: int = 0) -> subprocess.CompletedProcess:
    import os
    full_env = dict(os.environ)
    full_env.update(env or {})
    proc = subprocess.run(["uv", "run", str(ENGINE), *args],
                          capture_output=True, text=True, cwd=str(repo),
                          env=full_env, timeout=300)
    if expect is not None:
        assert proc.returncode == expect, (
            f"engine {args}: rc={proc.returncode}\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}")
    return proc


def tsv_rows(repo: Path) -> list[list[str]]:
    text = (repo / "docs" / "optimize" / "t1" / "results.tsv").read_text(
        encoding="utf-8")
    return [ln.split("\t") for ln in text.splitlines()[1:] if ln]


def edit_numbers(repo: Path, numbers) -> None:
    (repo / "numbers.txt").write_text("\n".join(numbers) + "\n",
                                      encoding="utf-8")


def state(repo: Path) -> dict | None:
    p = repo / ".claude" / "optimize" / "run.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------- lifecycle --

def test_happy_path_lifecycle(tmp_path):
    """start -> keep -> discard -> stop: branch shape, TSV, tree state."""
    repo = make_repo(tmp_path)                       # baseline sum = 9
    out = engine(repo, "start", "t1").stdout
    assert "LOCK-ON" in out and "baseline: SCORE=9" in out
    st = state(repo)
    assert st["branch"] == "optimize/t1" and st["best_score"] == 9
    assert _git(repo, "rev-parse", "--abbrev-ref",
                "HEAD").stdout.strip() == "optimize/t1"

    edit_numbers(repo, ("2", "3"))                   # sum 5 -> improvement
    out = engine(repo, "round", "--desc", "shrink both numbers").stdout
    assert "r1: KEEP" in out and "SCORE=5" in out
    assert (repo / "numbers.txt").read_text().startswith("2")

    edit_numbers(repo, ("9", "9"))                   # sum 18 -> worse
    out = engine(repo, "round", "--desc", "try bigger numbers").stdout
    assert "r2: DISCARD" in out
    # revert restored the last KEPT asset, not the seed
    assert (repo / "numbers.txt").read_text().splitlines() == ["2", "3"]

    rows = tsv_rows(repo)
    assert [r[5] for r in rows] == ["baseline (asset as-is)",
                                    "shrink both numbers",
                                    "try bigger numbers"]
    assert [r[4] for r in rows] == ["baseline", "keep", "discard"]

    out = engine(repo, "stop", "--reason", "test done").stdout
    assert "Locks OFF" in out and state(repo) is None
    assert tsv_rows(repo)[-1][4] == "stopped"
    # every round left exactly one durable journal commit
    log = _git(repo, "log", "--oneline").stdout
    assert log.count("journal") == 2 and "r0 baseline" in log


def test_maximize_direction(tmp_path):
    repo = make_repo(tmp_path, direction="minimize")
    # flip scorer+manifest to maximize by rewriting scorer header + re-pin
    scorer = repo / "tools" / "scorers" / "toy-scorer.py"
    scorer.write_text(scorer.read_text(encoding="utf-8").replace(
        "# direction: minimize", "# direction: maximize"), encoding="utf-8")
    pins = {"toy-scorer.py": {"sha": _pin.blob_sha(str(scorer)),
                              "direction": "maximize", "pinned": "2026-07-17"}}
    (repo / "tools" / "scorers" / "PINS.json").write_text(
        json.dumps(pins), encoding="utf-8")
    run = repo / "docs" / "optimize" / "t1" / "RUN.md"
    run.write_text(run.read_text(encoding="utf-8").replace(
        "direction: minimize", "direction: maximize"), encoding="utf-8")
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "flip")

    engine(repo, "start", "t1")
    edit_numbers(repo, ("2", "3"))                   # 5 < 9 = WORSE now
    out = engine(repo, "round", "--desc", "smaller is worse here").stdout
    assert "r1: DISCARD" in out


# ------------------------------------------------------------ start refusals

def test_start_refuses_dirty_tree(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "unrelated.txt").write_text("x", encoding="utf-8")
    proc = engine(repo, "start", "t1", expect=1)
    assert "not clean" in proc.stderr


def test_start_refuses_unpinned_scorer(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "tools" / "scorers" / "PINS.json").write_text("{}", encoding="utf-8")
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "unpin")
    proc = engine(repo, "start", "t1", expect=1)
    assert "not pinned" in proc.stderr


def test_start_refuses_pin_hash_mismatch(tmp_path):
    repo = make_repo(tmp_path, pin_sha="0" * 40)
    proc = engine(repo, "start", "t1", expect=1)
    assert "re-pin" in proc.stderr


def test_start_refuses_direction_mismatch(tmp_path):
    repo = make_repo(tmp_path, direction="maximize")  # scorer header says minimize
    proc = engine(repo, "start", "t1", expect=1)
    assert "direction mismatch" in proc.stderr


def test_start_refuses_asset_glob_covering_machinery(tmp_path):
    repo = make_repo(tmp_path, assets=("tools/**",))
    proc = engine(repo, "start", "t1", expect=1)
    assert "locked machinery" in proc.stderr


def test_start_refuses_second_run(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    proc = engine(repo, "start", "t1", expect=1)
    assert "already active" in proc.stderr


def test_start_broken_baseline_leaves_nothing(tmp_path):
    repo = make_repo(tmp_path, numbers=("not-a-number",))
    proc = engine(repo, "start", "t1", expect=1)
    assert "baseline scoring failed" in proc.stderr
    assert state(repo) is None
    branches = _git(repo, "branch", "--list").stdout
    assert "optimize/t1" not in branches
    assert not (repo / "docs" / "optimize" / "t1" / "results.tsv").exists()


def test_start_refuses_failing_baseline_guard(tmp_path):
    repo = make_repo(tmp_path, guard=True, numbers=("5", "4"))  # 2 lines < 3
    proc = engine(repo, "start", "t1", expect=1)
    assert "baseline guard failed" in proc.stderr
    assert state(repo) is None


# ------------------------------------------------------------- round rules --

def test_round_crash_on_scorer_nonzero(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    edit_numbers(repo, ("oops",))
    out = engine(repo, "round", "--desc", "break the asset").stdout
    assert "r1: CRASH" in out
    assert (repo / "numbers.txt").read_text().splitlines() == ["5", "4"]
    assert tsv_rows(repo)[-1][4] == "crash"


def test_round_timeout_kills_process_tree(tmp_path):
    repo = make_repo(tmp_path, scorer="toy-slow-scorer.py",
                     budgets={"score_timeout_seconds": 3})
    # slow scorer would sleep 300s at baseline; start must crash fast
    t0 = time.monotonic()
    proc = engine(repo, "start", "t1", expect=1)
    elapsed = time.monotonic() - t0
    assert "baseline scoring failed (timeout)" in proc.stderr
    assert elapsed < 60, f"timeout kill took {elapsed:.0f}s - tree not killed?"


def test_round_guard_fail_discards_score_win_then_rework(tmp_path):
    repo = make_repo(tmp_path, guard=True, numbers=("3", "3", "3"))  # sum 9, 3 lines
    engine(repo, "start", "t1")
    edit_numbers(repo, ("4",))                       # sum 4: BETTER score, 1 line: guard FAIL
    out = engine(repo, "round", "--desc", "collapse to one line").stdout
    assert "guard failed" in out
    st = state(repo)
    assert st["best_score"] == 9                     # win NOT kept
    edit_numbers(repo, ("1", "1", "2"))              # sum 4 AND 3 lines
    out = engine(repo, "round", "--rework", "--desc",
                 "same sum, restore 3 lines").stdout
    assert "r1: KEEP" in out and state(repo)["best_score"] == 4


def test_round_rework_cap_discards(tmp_path):
    repo = make_repo(tmp_path, guard=True, numbers=("3", "3", "3"))
    engine(repo, "start", "t1")
    edit_numbers(repo, ("4",))
    engine(repo, "round", "--desc", "guard-failing win")
    edit_numbers(repo, ("2",))                       # still 1 line
    engine(repo, "round", "--rework", "--desc", "still failing")
    edit_numbers(repo, ("1",))                       # still 1 line -> cap
    out = engine(repo, "round", "--rework", "--desc", "third strike").stdout
    assert "r1: GUARD_FAIL" in out or "GUARD_FAIL" in out.upper()
    # tree restored to baseline; journal records the round as guard_fail
    assert (repo / "numbers.txt").read_text().splitlines() == ["3", "3", "3"]
    assert tsv_rows(repo)[-1][4] == "guard_fail"
    assert state(repo)["best_score"] == 9


def test_round_simplification_keeps_equal_score(tmp_path):
    repo = make_repo(tmp_path, numbers=("5", "4", "0"))
    engine(repo, "start", "t1")
    edit_numbers(repo, ("5", "4"))                   # same sum 9, simpler
    out = engine(repo, "round", "--simplification",
                 "--desc", "drop the zero line").stdout
    assert "r1: KEEP" in out
    # without the flag, equal is a discard
    edit_numbers(repo, ("4", "5"))
    out = engine(repo, "round", "--desc", "reorder, same sum").stdout
    assert "r2: DISCARD" in out


def test_round_forced_discard(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    edit_numbers(repo, ("1",))                       # huge win
    out = engine(repo, "round", "--discard",
                 "--desc", "win not worth the complexity").stdout
    assert "r1: DISCARD" in out and state(repo)["best_score"] == 9


def test_round_refuses_without_asset_change(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    proc = engine(repo, "round", "--desc", "nothing changed", expect=1)
    assert "no asset change" in proc.stderr


def test_round_refuses_foreign_dirty_path(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    (repo / "unrelated.txt").write_text("drift", encoding="utf-8")
    edit_numbers(repo, ("1", "1"))
    proc = engine(repo, "round", "--desc", "x", expect=1)
    assert "OUTSIDE the asset scope" in proc.stderr


def test_round_refuses_rounds_exhausted(tmp_path):
    repo = make_repo(tmp_path, budgets={"rounds": 1})
    engine(repo, "start", "t1")
    edit_numbers(repo, ("1", "1"))
    engine(repo, "round", "--desc", "use the only round")
    edit_numbers(repo, ("1", "0"))
    proc = engine(repo, "round", "--desc", "over budget", expect=1)
    assert "ROUNDS EXHAUSTED" in proc.stderr


def test_round_refuses_wall_clock_exhausted(tmp_path):
    repo = make_repo(tmp_path, budgets={"wall_clock_minutes": 60})
    engine(repo, "start", "t1")
    st = state(repo)
    edit_numbers(repo, ("1", "1"))
    late = "2027-01-01T12:00:00"
    proc = engine(repo, "round", "--desc", "too late",
                  env={"OPTIMIZE_NOW": late}, expect=1)
    assert "WALL-CLOCK EXHAUSTED" in proc.stderr
    assert st is not None


def test_round_aborts_on_scorer_hash_drift(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    scorer = repo / "tools" / "scorers" / "toy-scorer.py"
    scorer.write_text(scorer.read_text(encoding="utf-8")
                      .replace("SCORE: {total}", "SCORE: 0"), encoding="utf-8")
    edit_numbers(repo, ("1", "1"))
    proc = engine(repo, "round", "--desc", "gamed metric", expect=1)
    assert "scorer hash drift" in proc.stderr


def test_round_aborts_on_manifest_drift(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    run = repo / "docs" / "optimize" / "t1" / "RUN.md"
    run.write_text(run.read_text(encoding="utf-8")
                   .replace("rounds: 10", "rounds: 999"), encoding="utf-8")
    edit_numbers(repo, ("1", "1"))
    proc = engine(repo, "round", "--desc", "moved instructions", expect=1)
    assert "manifest" in proc.stderr and "drift" in proc.stderr


def test_round_aborts_on_tsv_tamper(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    tsv = repo / "docs" / "optimize" / "t1" / "results.tsv"
    tsv.write_text(tsv.read_text(encoding="utf-8").replace("9", "1"),
                   encoding="utf-8")
    edit_numbers(repo, ("1", "1"))
    proc = engine(repo, "round", "--desc", "rewrote history", expect=1)
    assert "append-only" in proc.stderr


def test_goal_reached_announced(tmp_path):
    repo = make_repo(tmp_path, stop={"goal_score": 5})
    engine(repo, "start", "t1")
    edit_numbers(repo, ("2", "3"))
    out = engine(repo, "round", "--desc", "hit the goal").stdout
    assert "GOAL REACHED" in out


def test_plateau_announced(tmp_path):
    repo = make_repo(tmp_path, stop={"consecutive_reverts": 2})
    engine(repo, "start", "t1")
    for i, nums in enumerate((("9", "9"), ("8", "8"))):
        edit_numbers(repo, nums)
        out = engine(repo, "round", "--desc", f"worse try {i}").stdout
    assert "PLATEAU" in out


# ------------------------------------------------------------------ resume --

def test_resume_restores_dirty_tree_and_repro_checks(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    edit_numbers(repo, ("1", "1"))                   # in-flight edit, no round
    out = engine(repo, "resume").stdout
    assert "restoring last kept state" in out
    assert (repo / "numbers.txt").read_text().splitlines() == ["5", "4"]
    assert "reproducibility check OK" in out


def test_resume_logs_dangling_experiment_as_crash(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    # simulate crash between experiment commit and journal commit
    edit_numbers(repo, ("1", "1"))
    _git(repo, "add", "--", "numbers.txt")
    _git(repo, "commit", "-q", "-m", "experiment(t1): r1: interrupted try")
    out = engine(repo, "resume").stdout
    assert "logging r1 as crash" in out
    assert tsv_rows(repo)[-1][4] == "crash"
    assert (repo / "numbers.txt").read_text().splitlines() == ["5", "4"]
    # numbering continues after the recovered round
    edit_numbers(repo, ("2", "2"))
    out = engine(repo, "round", "--desc", "post-recovery round").stdout
    assert "r2: KEEP" in out


def test_resume_surfaces_reproducibility_mismatch(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    # drift the ENVIRONMENT the score depends on without touching the run
    # branch state: rewrite the asset via a committed change on the branch
    # is asset-visible; instead simulate by tampering state's best_score
    st_path = repo / ".claude" / "optimize" / "run.json"
    st = json.loads(st_path.read_text(encoding="utf-8"))
    st["best_score"] = 42
    st_path.write_text(json.dumps(st), encoding="utf-8")
    out = engine(repo, "resume").stdout
    assert "REPRODUCIBILITY MISMATCH" in out


# -------------------------------------------------------------------- stop --

def test_stop_with_missing_branch_still_unlocks(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "branch", "-q", "-D", "optimize/t1")
    out = engine(repo, "stop").stdout
    assert "locks off" in out.lower()
    assert state(repo) is None


def test_status_reports_run(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    out = engine(repo, "status").stdout
    assert '"tag": "t1"' in out and '"best_score": 9' in out


# --- FIX-2: resume must ADOPT a committed journal, never discard a kept win --

def test_resume_adopts_committed_keep_after_crash_window(tmp_path):
    repo = make_repo(tmp_path)                        # baseline 9
    engine(repo, "start", "t1")
    st0 = state(repo)                                 # base_sha=r0, round0, best9
    edit_numbers(repo, ("2", "3"))                    # 5, a real win
    engine(repo, "round", "--desc", "shrink")         # KEEP -> HEAD=J1, round1
    # Simulate SIGKILL in the journal-commit -> save_state window: roll the
    # run-state cache back to the pre-round values while HEAD stays at J1.
    stp = repo / ".claude" / "optimize" / "run.json"
    st = json.loads(stp.read_text(encoding="utf-8"))
    st.update({"base_sha": st0["base_sha"], "round": 0, "best_score": 9.0,
               "consecutive_non_keeps": 0,
               "tsv_lines": st0["tsv_lines"], "tsv_sha256": st0["tsv_sha256"]})
    stp.write_text(json.dumps(st), encoding="utf-8")
    out = engine(repo, "resume").stdout
    assert "adopting the durable journal" in out
    s2 = state(repo)
    assert s2["best_score"] == 5.0 and s2["round"] == 1      # win recovered
    assert (repo / "numbers.txt").read_text().splitlines() == ["2", "3"]
    assert [r[4] for r in tsv_rows(repo)] == ["baseline", "keep"]  # no crash row
    assert "reproducibility check OK" in out


# --- FIX-4: a parked guard_fail is never destroyed or mislabeled by resume --

def test_resume_preserves_parked_guard_fail(tmp_path):
    repo = make_repo(tmp_path, guard=True, numbers=("3", "3", "3"))  # 9, 3 lines
    engine(repo, "start", "t1")
    edit_numbers(repo, ("4",))                        # 4 (better) but 1 line: guard fail
    engine(repo, "round", "--desc", "collapse to one line")
    assert state(repo).get("pending_rework")
    out = engine(repo, "resume").stdout
    assert "parked guard_fail" in out
    assert (repo / "numbers.txt").read_text().strip() == "4"   # not destroyed
    assert [r[4] for r in tsv_rows(repo)] == ["baseline"]       # no crash row
    edit_numbers(repo, ("1", "1", "2"))               # 4 AND 3 lines
    out = engine(repo, "round", "--rework", "--desc", "restore lines").stdout
    assert "r1: KEEP" in out and state(repo)["best_score"] == 4


def test_plain_round_refused_on_parked_rework(tmp_path):
    repo = make_repo(tmp_path, guard=True, numbers=("3", "3", "3"))
    engine(repo, "start", "t1")
    edit_numbers(repo, ("4",))
    engine(repo, "round", "--desc", "guard-failing win")
    edit_numbers(repo, ("2", "2", "2"))
    proc = engine(repo, "round", "--desc", "plain round on parked", expect=1)
    assert "parked guard_fail" in proc.stderr


# --- FIX-3: guard scripts are auto-locked, hash-verified, refused in-scope ---

def test_start_refuses_guard_script_inside_asset_scope(tmp_path):
    repo = make_repo(tmp_path, guard=True, numbers=("1", "1", "1"),
                     assets=("numbers.txt", "toy-guard.py"))
    proc = engine(repo, "start", "t1", expect=1)
    assert "sits inside the asset scope" in proc.stderr


def test_round_aborts_on_guard_script_drift(tmp_path):
    repo = make_repo(tmp_path, guard=True, numbers=("3", "3", "3"))
    engine(repo, "start", "t1")
    g = repo / "toy-guard.py"
    g.write_text(g.read_text(encoding="utf-8") + "\n# tamper\n", encoding="utf-8")
    edit_numbers(repo, ("1", "1", "1"))
    proc = engine(repo, "round", "--desc", "win while guard is neutered",
                  expect=1)
    assert "guard script" in proc.stderr and "changed mid-run" in proc.stderr


# --- FIX-5: stop clears a corrupt run.json instead of dying -----------------

def test_stop_clears_corrupt_state(tmp_path):
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    stp = repo / ".claude" / "optimize" / "run.json"
    stp.write_text("{ this is not json", encoding="utf-8")
    out = engine(repo, "stop").stdout
    assert "unparseable" in out and "locks OFF" in out
    assert not stp.exists()


def test_round_still_dies_on_corrupt_state(tmp_path):
    # only stop recovers corrupt state; round must not silently proceed
    repo = make_repo(tmp_path)
    engine(repo, "start", "t1")
    edit_numbers(repo, ("1", "1"))
    (repo / ".claude" / "optimize" / "run.json").write_text(
        "{bad", encoding="utf-8")
    proc = engine(repo, "round", "--desc", "x", expect=1)
    assert "unparseable" in proc.stderr
