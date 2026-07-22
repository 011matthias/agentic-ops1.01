"""Background-work liveness watches: the store's rules + the PostToolUse arm.

Covers the load-bearing rule the feature rests on (a heartbeat that keeps
advancing rolls the deadline forward and stays silent; one that stops firing
names the silence in minutes), and proves the advisory actually reaches the
agent through the real hook, since a detector that cannot fire is exactly the
failure mode this replaces.
"""
import json
import sys
import time

import pytest

from hooklib import TOOLS, run_hook

sys.path.insert(0, str(TOOLS))
import bg_watch as bw  # noqa: E402


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Isolate the watch file so no test touches a live session's watches."""
    f = tmp_path / "watches.json"
    monkeypatch.setattr(bw, "WATCH_FILE", str(f))
    return f


def _seed(path, **over):
    """Write one watch straight to the store, bypassing register()."""
    rec = {
        "id": "fanout", "label": "verify fan-out", "eta_seconds": 600,
        "heartbeat": "", "registered": time.time(), "root": "",
        "notified_at": 0.0,
    }
    rec.update(over)
    path.write_text(json.dumps({"watches": [rec]}), encoding="utf-8")
    return rec


# --- registration ----------------------------------------------------------
def test_register_writes_watch(store):
    rec = bw.register("10-lens adversarial verify fan-out", eta_minutes=10)
    assert rec and rec["id"] == "10-lens-adversarial-verify-fan-o"  # slug, 32 max
    assert rec["eta_seconds"] == 600
    assert [w["id"] for w in bw.listing(all_roots=True)] == [rec["id"]]


def test_register_same_id_refreshes_not_duplicates(store):
    bw.register("verify fan-out", eta_minutes=10)
    bw.register("verify fan-out", eta_minutes=30)
    items = bw.listing(all_roots=True)
    assert len(items) == 1 and items[0]["eta_seconds"] == 1800


def test_register_records_heartbeat_absolute(store, tmp_path):
    hb = tmp_path / "progress.jsonl"
    rec = bw.register("fanout", heartbeat=str(hb))
    assert rec["heartbeat"] == str(hb.resolve()) or rec["heartbeat"].endswith(
        "progress.jsonl")


# --- the liveness rule -----------------------------------------------------
def test_overdue_fires_when_deadline_passed(store):
    _seed(store, registered=time.time() - 4560, eta_seconds=600)  # 76 min silent
    due = bw.overdue()
    assert [w["id"] for w in due] == ["fanout"]
    assert due[0]["silent_seconds"] >= 4560
    assert due[0]["signal_source"] == "none"


def test_fresh_watch_is_silent(store):
    _seed(store, registered=time.time() - 60, eta_seconds=600)
    assert bw.overdue() == []


def test_fresh_heartbeat_rolls_the_deadline_forward(store, tmp_path):
    hb = tmp_path / "progress.jsonl"
    hb.write_text("tick", encoding="utf-8")
    # Registered long ago, but the work is still writing: must stay silent.
    _seed(store, registered=time.time() - 9999, eta_seconds=600, heartbeat=str(hb))
    assert bw.overdue() == []


def test_stale_heartbeat_fires(store, tmp_path):
    import os
    hb = tmp_path / "progress.jsonl"
    hb.write_text("tick", encoding="utf-8")
    old = time.time() - 4560
    os.utime(hb, (old, old))
    _seed(store, registered=time.time() - 9999, eta_seconds=600, heartbeat=str(hb))
    due = bw.overdue()
    assert len(due) == 1 and due[0]["signal_source"] == "heartbeat"
    assert due[0]["silent_seconds"] >= 4560


def test_declared_heartbeat_that_never_appeared_fires(store, tmp_path):
    _seed(store, registered=time.time() - 4560, eta_seconds=600,
          heartbeat=str(tmp_path / "never-written.jsonl"))
    due = bw.overdue()
    assert len(due) == 1 and due[0]["signal_source"] == "missing"
    assert "never appeared" in bw.advisory(due)


# --- clearing --------------------------------------------------------------
def test_done_clears_the_watch(store):
    bw.register("verify fan-out")
    assert bw.clear("verify-fan-out") == 1
    assert bw.listing(all_roots=True) == []


def test_done_all_clears_everything(store):
    bw.register("a")
    bw.register("b")
    assert bw.clear(all_watches=True) == 2
    assert bw.overdue() == []


def test_cleared_watch_stops_firing(store):
    _seed(store, registered=time.time() - 4560)
    assert bw.overdue()
    bw.clear("fanout")
    assert bw.overdue() == []


# --- fail-open + hygiene ---------------------------------------------------
def test_corrupt_store_fails_open(store):
    store.write_text("{not json at all", encoding="utf-8")
    assert bw.listing(all_roots=True) == []
    assert bw.overdue() == []
    assert bw.due_advisories() == []
    # and a fresh registration still lands, healing the file
    assert bw.register("verify fan-out")
    assert len(bw.listing(all_roots=True)) == 1


def test_missing_store_fails_open(store):
    assert not store.exists()
    assert bw.due_advisories() == []


def test_ancient_watch_is_pruned(store):
    _seed(store, registered=time.time() - (bw.MAX_AGE_SECONDS + 60))
    assert bw.listing(all_roots=True) == []


def test_renotify_backoff_suppresses_repeat(store):
    _seed(store, registered=time.time() - 4560)
    assert bw.due_advisories()          # first fire
    assert bw.due_advisories() == []    # inside the back-off window
    # past the back-off, it speaks up again
    now = time.time() + bw.RENOTIFY_SECONDS + 1
    assert bw.due_advisories(now=now)


def test_other_worktree_watch_not_shown(store, tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    _seed(store, registered=time.time() - 4560, root=str((tmp_path / "elsewhere")))
    assert bw.overdue(cwd=str(repo)) == []
    assert bw.overdue(cwd=str(repo), now=None) == []
    # ... but it is still visible when explicitly asked for
    assert len(bw.listing(cwd=str(repo), all_roots=True)) == 1


def test_advisory_text_is_actionable(store):
    _seed(store, registered=time.time() - 4560, eta_seconds=600)
    text = bw.advisory(bw.overdue())
    assert "[BG-WATCH]" in text
    assert "silent for 76 min" in text
    assert "bg_watch.py done" in text
    assert "—" not in text  # repo rule: no em-dashes in added prose


def test_sub_minute_intervals_render_in_seconds(store):
    # A short interval must not collapse to the meaningless "0 min".
    _seed(store, registered=time.time() - 20, eta_seconds=5)
    text = bw.advisory(bw.overdue())
    assert "silent for 20 s" in text and "every 5 s" in text
    assert "0 min" not in text


# --- the PostToolUse arm, end to end (subprocess, real hook) ---------------
def _meter_env(tmp_path, watch_file):
    """Redirect every store the meter touches so a test can never pollute the
    developer's live session state, heartbeats, or watches."""
    return {
        "AGENTIC_OPS_BG_WATCHES": str(watch_file),
        "AGENTIC_OPS_SESSION_STATE": str(tmp_path / "session-state.json"),
        "AGENTIC_OPS_SESSION_DIR": str(tmp_path / "hb"),
    }


def _context(stdout: str) -> str:
    out = stdout.strip()
    if not out:
        return ""
    return (json.loads(out).get("hookSpecificOutput") or {}).get(
        "additionalContext", "")


def test_meter_hook_emits_overdue_advisory(tmp_path):
    wf = tmp_path / "watches.json"
    _seed(wf, registered=time.time() - 4560, eta_seconds=600)
    r = run_hook("session-pressure-meter.py",
                 {"session_id": "s1", "tool_name": "Bash", "tool_input": {}},
                 env=_meter_env(tmp_path, wf))
    assert r.returncode == 0
    ctx = _context(r.stdout)
    assert "[BG-WATCH]" in ctx
    assert "verify fan-out" in ctx
    assert "silent for 76 min" in ctx


def test_meter_hook_silent_when_heartbeat_is_fresh(tmp_path):
    wf = tmp_path / "watches.json"
    hb = tmp_path / "progress.jsonl"
    hb.write_text("tick", encoding="utf-8")
    _seed(wf, registered=time.time() - 9999, eta_seconds=600, heartbeat=str(hb))
    r = run_hook("session-pressure-meter.py",
                 {"session_id": "s1", "tool_name": "Bash", "tool_input": {}},
                 env=_meter_env(tmp_path, wf))
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_meter_hook_scopes_on_payload_cwd(tmp_path):
    """The hook resolves the working-tree root from the payload's `cwd`, so a
    watch registered in ANOTHER worktree stays quiet here while one registered
    in this tree fires. Caught in live proof: a payload without `cwd` falls back
    to the hook process's own cwd, which is not necessarily the session's."""
    from hooklib import REPO
    wf = tmp_path / "watches.json"
    env = _meter_env(tmp_path, wf)
    payload = {"session_id": "s1", "tool_name": "Bash", "tool_input": {},
               "cwd": str(REPO)}

    _seed(wf, registered=time.time() - 4560, root=str(tmp_path / "other-worktree"))
    r = run_hook("session-pressure-meter.py", payload, env=env)
    assert r.returncode == 0 and r.stdout.strip() == ""

    _seed(wf, registered=time.time() - 4560, root=str(REPO))
    r = run_hook("session-pressure-meter.py", payload, env=env)
    assert r.returncode == 0 and "[BG-WATCH]" in _context(r.stdout)


def test_meter_hook_silent_with_no_watches(tmp_path):
    r = run_hook("session-pressure-meter.py",
                 {"session_id": "s1", "tool_name": "Bash", "tool_input": {}},
                 env=_meter_env(tmp_path, tmp_path / "watches.json"))
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_meter_hook_survives_corrupt_watch_store(tmp_path):
    wf = tmp_path / "watches.json"
    wf.write_text("<<<corrupt>>>", encoding="utf-8")
    r = run_hook("session-pressure-meter.py",
                 {"session_id": "s1", "tool_name": "Bash", "tool_input": {}},
                 env=_meter_env(tmp_path, wf))
    assert r.returncode == 0
    assert r.stdout.strip() == ""


# --- the CLI, end to end ---------------------------------------------------
def test_cli_watch_check_done_roundtrip(tmp_path):
    import subprocess
    wf = tmp_path / "watches.json"
    env = _meter_env(tmp_path, wf)

    def cli(*args):
        import os
        full = dict(os.environ)
        full.update(env)
        return subprocess.run([sys.executable, str(TOOLS / "bg_watch.py"), *args],
                              capture_output=True, text=True, timeout=60, env=full)

    # `--cwd` AFTER the subcommand must parse: argparse rejects a top-level
    # option in that position, which made every registration in the first live
    # proof exit 2 instead of registering.
    r = cli("watch", "--label", "verify fan-out", "--eta", "0.01",
            "--cwd", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert "verify-fan-out" in r.stdout
    time.sleep(1.1)  # 0.01 min = 1s expected interval
    r = cli("check", "--all-roots")
    assert r.returncode == 0 and "[BG-WATCH]" in r.stdout
    r = cli("done", "verify-fan-out")
    assert r.returncode == 0 and "cleared 1" in r.stdout
    r = cli("check", "--all-roots")
    assert r.returncode == 0 and "[BG-WATCH]" not in r.stdout


def test_cli_json_after_subcommand_parses(tmp_path):
    import os
    import subprocess
    env = dict(os.environ)
    env.update(_meter_env(tmp_path, tmp_path / "watches.json"))
    r = subprocess.run([sys.executable, str(TOOLS / "bg_watch.py"),
                        "watch", "--label", "fanout", "--json"],
                       capture_output=True, text=True, timeout=60, env=env)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["id"] == "fanout"
