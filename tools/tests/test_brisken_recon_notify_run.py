"""The notifier's self-updating runner (backlog item 120, 2026-09-21).

What is actually being pinned here is not "git works". It is the two
resolutions that decide whether a migration off the shared working tree is
harmless or loud, and both fail SILENTLY if they are wrong:

  * the state file. A fresh one is not a clean slate, it is an instruction
    to announce every existing run, intake, feedback note and re-match at
    once. A runner that resolved it to a new path in the new clone would
    pass every other check and arrive as a mail storm.
  * the credentials. A notifier that cannot authenticate sends nothing and
    would otherwise exit 0, which is indistinguishable from a quiet day.
    That is the exact shape of the failure this runner exists to end, so it
    must be fatal.

The git half is covered only for its contract (never destructive, never
fatal); the value of a fast-forward is not in doubt.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "brisken-recon-notify-run.py"


def _load():
    spec = importlib.util.spec_from_file_location("notify_run", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["notify_run"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def mod(monkeypatch):
    for var in (
        "RECON_NOTIFY_HOME", "RECON_NOTIFY_ENV_FILE", "RECON_NOTIFY_STATE",
    ):
        monkeypatch.delenv(var, raising=False)
    return _load()


def _clone_at(mod, monkeypatch, path: Path) -> None:
    monkeypatch.setattr(mod, "CLONE", path)


# --- the state file: an existing one always wins -----------------------


def test_an_existing_state_file_is_preferred_over_a_new_path(
    mod, monkeypatch, tmp_path,
):
    """The mail-storm guard.

    The new clone has no state; the shared tree beside it has the real one.
    Resolving to the clone's own path would make the first run announce the
    entire history. So the runner must find the existing file.
    """
    clone = tmp_path / "agentic-ops1-notify"
    shared = tmp_path / "agentic-ops1"
    (clone / "tools").mkdir(parents=True)
    state = shared / ".scratch" / "recon-notify-state.json"
    state.parent.mkdir(parents=True)
    state.write_text('{"seen_runs": ["r1"]}', encoding="utf-8")
    _clone_at(mod, monkeypatch, clone)

    assert mod.resolve_state_file() == state


def test_the_clones_own_state_wins_once_it_has_one(mod, monkeypatch, tmp_path):
    """A self-contained setup needs no configuration: if the clone holds a
    real state file, that is the one, and the shared tree stops mattering."""
    clone = tmp_path / "agentic-ops1-notify"
    shared = tmp_path / "agentic-ops1"
    own = clone / ".scratch" / "recon-notify-state.json"
    own.parent.mkdir(parents=True)
    own.write_text("{}", encoding="utf-8")
    other = shared / ".scratch" / "recon-notify-state.json"
    other.parent.mkdir(parents=True)
    other.write_text("{}", encoding="utf-8")
    _clone_at(mod, monkeypatch, clone)

    assert mod.resolve_state_file() == own


def test_with_no_state_anywhere_it_falls_back_rather_than_failing(
    mod, monkeypatch, tmp_path,
):
    """A first-ever install has no state and must still run; the fallback is
    a path in the clone, which is the only case where announcing from empty
    is the correct behaviour."""
    clone = tmp_path / "agentic-ops1-notify"
    clone.mkdir()
    _clone_at(mod, monkeypatch, clone)

    assert mod.resolve_state_file() == clone / ".scratch" / "recon-notify-state.json"


# --- the credentials: absence is fatal, never a quiet exit 0 -----------


def test_missing_credentials_exit_non_zero_rather_than_pretending(
    mod, monkeypatch, tmp_path, capsys,
):
    """`LastTaskResult` is the only signal the Windows scheduler shows. A
    notifier that cannot send must not report success, or the alarm going
    quiet looks exactly like nothing having happened."""
    clone = tmp_path / "agentic-ops1-notify"
    clone.mkdir()
    _clone_at(mod, monkeypatch, clone)
    monkeypatch.setattr(mod, "update_clone", lambda c: (True, "up to date"))
    monkeypatch.setattr(mod, "current_commit", lambda c: "d" * 40)

    def _never(*a, **k):  # pragma: no cover - the point is it is not called
        raise AssertionError("the notifier must not run without credentials")

    monkeypatch.setattr(mod.subprocess, "run", _never)

    assert mod.main(["--once"]) == 2
    assert "no Graph credentials" in capsys.readouterr().err


def test_the_credentials_are_read_where_they_already_live(
    mod, monkeypatch, tmp_path,
):
    """One copy of the secret on this machine. The runner reads the shared
    tree's gitignored `.env` rather than taking a second copy into the new
    clone, where it would also go stale on a rotation."""
    clone = tmp_path / "agentic-ops1-notify"
    shared = tmp_path / "agentic-ops1"
    clone.mkdir()
    env = shared / "workspace" / "clients" / "brisken" / "context" / ".env"
    env.parent.mkdir(parents=True)
    env.write_text("BRISKEN_TENANT_ID=x\n", encoding="utf-8")
    _clone_at(mod, monkeypatch, clone)

    assert mod.resolve_env_file() == env


# --- the update: never destructive, never fatal ------------------------


def test_the_update_is_fetch_plus_ff_only_and_nothing_else(
    mod, monkeypatch, tmp_path,
):
    """No reset, no checkout, no clean, no force. On a clone nobody edits a
    fast-forward always succeeds; if it ever does not, something is in that
    clone that should not be, and overwriting it destroys the evidence."""
    calls: list[tuple[str, ...]] = []

    def _fake_git(*args, cwd):
        calls.append(args)
        return True, ""

    monkeypatch.setattr(mod, "_git", _fake_git)
    ok, _ = mod.update_clone(tmp_path)

    assert ok
    assert calls == [
        ("fetch", "--quiet", "origin", "main"),
        ("merge", "--ff-only", "origin/main"),
    ]
    flat = " ".join(" ".join(c) for c in calls)
    for destructive in ("reset", "clean", "--force", "checkout", "stash"):
        assert destructive not in flat


def test_a_failed_update_runs_anyway_on_the_last_good_commit(
    mod, monkeypatch, tmp_path,
):
    """A notifier that refuses to alarm until its git is healthy has turned
    a maintenance problem into an outage. The staleness is recorded instead.
    """
    clone = tmp_path / "agentic-ops1-notify"
    clone.mkdir()
    env = clone / "workspace" / "clients" / "brisken" / "context" / ".env"
    env.parent.mkdir(parents=True)
    env.write_text("x=1\n", encoding="utf-8")
    _clone_at(mod, monkeypatch, clone)
    monkeypatch.setattr(mod, "update_clone", lambda c: (False, "fetch failed: offline"))
    monkeypatch.setattr(mod, "current_commit", lambda c: "e" * 40)

    ran: list[list[str]] = []

    class _Done:
        returncode = 0

    def _fake_run(cmd, **kwargs):
        ran.append(cmd)
        return _Done()

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)

    assert mod.main(["--once"]) == 0
    assert ran, "the notifier still runs when the update fails"
    log = (clone / ".scratch" / "recon-notify-runs.log").read_text(encoding="utf-8")
    assert "STALE" in log and "offline" in log


def test_the_run_records_the_commit_it_ran_from(mod, monkeypatch, tmp_path):
    """Verification by behaviour: "Ready" proves nothing, and neither does
    an exit code on its own. The log is what answers "it ran, from this
    commit" after the fact."""
    clone = tmp_path / "agentic-ops1-notify"
    clone.mkdir()
    env = clone / "workspace" / "clients" / "brisken" / "context" / ".env"
    env.parent.mkdir(parents=True)
    env.write_text("x=1\n", encoding="utf-8")
    _clone_at(mod, monkeypatch, clone)
    monkeypatch.setattr(mod, "update_clone", lambda c: (True, "up to date"))
    monkeypatch.setattr(mod, "current_commit", lambda c: "abcdef1234567890" + "0" * 24)

    class _Done:
        returncode = 0

    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **k: _Done())

    assert mod.main(["--once"]) == 0
    log = (clone / ".scratch" / "recon-notify-runs.log").read_text(encoding="utf-8")
    assert "commit=abcdef12" in log and "exit=0" in log


def test_the_log_is_bounded(mod, tmp_path):
    """An unbounded log on a machine nobody watches is its own small fault."""
    log = tmp_path / ".scratch" / "recon-notify-runs.log"
    for i in range(mod.LOG_KEEP + 25):
        mod.append_log(log, f"line {i}")
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == mod.LOG_KEEP
    assert lines[-1] == f"line {mod.LOG_KEEP + 24}"


# --- what is handed to the notifier ------------------------------------


def test_the_notifier_is_run_from_the_clone_with_both_paths_pinned(
    mod, monkeypatch, tmp_path,
):
    """The whole point of the runner, in one assertion: the code comes from
    the clone that just updated itself, and the credentials and state come
    from where they already are."""
    clone = tmp_path / "agentic-ops1-notify"
    shared = tmp_path / "agentic-ops1"
    clone.mkdir()
    env = shared / "workspace" / "clients" / "brisken" / "context" / ".env"
    env.parent.mkdir(parents=True)
    env.write_text("x=1\n", encoding="utf-8")
    state = shared / ".scratch" / "recon-notify-state.json"
    state.parent.mkdir(parents=True)
    state.write_text("{}", encoding="utf-8")
    _clone_at(mod, monkeypatch, clone)
    monkeypatch.setattr(mod, "update_clone", lambda c: (True, "up to date"))
    monkeypatch.setattr(mod, "current_commit", lambda c: "f" * 40)

    seen: list[list[str]] = []

    class _Done:
        returncode = 0

    monkeypatch.setattr(
        mod.subprocess, "run", lambda cmd, **k: (seen.append(cmd), _Done())[1]
    )

    assert mod.main(["--once", "--dry-run"]) == 0
    cmd = seen[0]
    assert cmd[:4] == ["uv", "run", "--directory", str(clone)]
    assert cmd[4] == "tools/brisken-recon-notify.py"
    assert str(env) in cmd and str(state) in cmd
    # Unknown flags reach the notifier rather than being swallowed.
    assert "--once" in cmd and "--dry-run" in cmd


def test_the_notifiers_exit_code_is_the_runners_exit_code(
    mod, monkeypatch, tmp_path,
):
    """The runner must not mask a failing notifier behind its own success."""
    clone = tmp_path / "agentic-ops1-notify"
    clone.mkdir()
    env = clone / "workspace" / "clients" / "brisken" / "context" / ".env"
    env.parent.mkdir(parents=True)
    env.write_text("x=1\n", encoding="utf-8")
    _clone_at(mod, monkeypatch, clone)
    monkeypatch.setattr(mod, "update_clone", lambda c: (True, "up to date"))
    monkeypatch.setattr(mod, "current_commit", lambda c: "a" * 40)

    class _Failed:
        returncode = 7

    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **k: _Failed())
    assert mod.main(["--once"]) == 7
