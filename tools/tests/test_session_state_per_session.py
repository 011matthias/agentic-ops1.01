"""Per-session state file: each session reads and writes only its own file.

Until 2026-09-17 every session on the machine shared one temp file, and
ensure_session reset it whenever another session's meter wrote: a sibling wiped
this session's pressure counters, B1 primer state and friction candidates (a
checkpoint `pre` drained zero candidates from a session that had produced
them). These tests drive the real hooks and the CLI as subprocesses with the
temp dir redirected and no AGENTIC_OPS_SESSION_STATE override, so the path
resolution under test is the one a live session gets.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

from hooklib import HOOKS, REPO, TOOLS, run_hook


def _env(tmp_path, **extra) -> dict:
    """Temp dir redirected, no state override, no inherited session id."""
    t = str(tmp_path)
    env = {
        "TMP": t, "TEMP": t, "TMPDIR": t,
        "AGENTIC_OPS_SESSION_STATE": "",
        "CLAUDE_CODE_SESSION_ID": "",
        "AGENTIC_OPS_BG_WATCHES": str(tmp_path / "watches.json"),
        "AGENTIC_OPS_SESSION_DIR": str(tmp_path / "sessions"),
        "AGENTIC_OPS_TELEMETRY_DIR": str(tmp_path / "telemetry"),
        "AGENTIC_OPS_CONTEXT_WINDOW": "1000000",
        "CLAUDE_CONFIG_DIR": str(tmp_path / "claude"),
    }
    env.update(extra)
    return env


def _hook(script, payload, tmp_path):
    return run_hook(script, payload, cwd=tmp_path, env=_env(tmp_path),
                    isolate_state=False)


def _cli(tmp_path, *args, session=""):
    r = subprocess.run(
        [sys.executable, str(TOOLS / "session_state.py"), *args],
        capture_output=True, text=True, timeout=30, cwd=str(REPO),
        env={**os.environ, **_env(tmp_path, CLAUDE_CODE_SESSION_ID=session)},
    )
    return json.loads(r.stdout)


def _state(tmp_path, sid: str) -> dict:
    path = tmp_path / f"agentic-ops-session-state-{sid}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _stash(tmp_path, sid: str):
    return _hook("git-stash-gate.py", {
        "tool_name": "Bash", "session_id": sid, "cwd": str(tmp_path),
        "tool_input": {"command": "git stash push -m wip"},
    }, tmp_path)


def _meter(tmp_path, sid: str):
    return _hook("session-pressure-meter.py", {
        "tool_name": "Read", "session_id": sid, "cwd": str(tmp_path),
        "tool_input": {"file_path": str(tmp_path / "x.py")},
        "transcript_path": "",
    }, tmp_path)


def _transcript(path, text=None, tokens=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    msg = {"role": "assistant", "model": "claude-opus-5", "id": "msg_1"}
    if text is not None:
        msg["content"] = [{"type": "text", "text": text}]
    if tokens is not None:
        msg["usage"] = {"input_tokens": tokens, "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0}
    path.write_text(json.dumps({"type": "assistant", "message": msg}) + "\n",
                    encoding="utf-8")
    return str(path)


# --- hooks bind from the payload ------------------------------------------

def test_gate_writes_candidate_to_its_payload_sessions_file(tmp_path):
    assert _stash(tmp_path, "sess-A").stdout.strip()  # the gate asked
    cands = _state(tmp_path, "sess-A")["candidates"]
    assert [c["signal"] for c in cands] == ["gate-fired-git-stash"]
    assert not (tmp_path / "agentic-ops-session-state.json").exists()


def test_sibling_meter_does_not_wipe_this_sessions_candidates(tmp_path):
    """The 2026-09-17 defect: a sibling's first meter write reset the shared
    file, so the checkpoint drain found nothing."""
    _stash(tmp_path, "sess-A")
    _meter(tmp_path, "sess-B")
    assert _state(tmp_path, "sess-B")["tool_calls"] == 1
    assert _state(tmp_path, "sess-B")["candidates"] == []
    listed = _cli(tmp_path, "--list-candidates", "--json", session="sess-A")
    assert [c["signal"] for c in listed] == ["gate-fired-git-stash"]


def test_meter_counts_stay_per_session_when_interleaved(tmp_path):
    for sid in ("sess-A", "sess-B", "sess-A", "sess-B", "sess-A"):
        _meter(tmp_path, sid)
    assert _state(tmp_path, "sess-A")["tool_calls"] == 3
    assert _state(tmp_path, "sess-B")["tool_calls"] == 2


def test_b1_block_primes_only_the_blocked_session(tmp_path):
    transcript = _transcript(tmp_path / "t.jsonl", text="Done. Want me to deploy it?")
    stop = _hook("stop-b1-gate.py",
                 {"session_id": "sess-A", "transcript_path": transcript}, tmp_path)
    assert json.loads(stop.stdout)["decision"] == "block"
    assert _state(tmp_path, "sess-A")["b1_blocks"] == 1

    other = _hook("input-classifier.py",
                  {"session_id": "sess-B", "prompt": "do the thing"}, tmp_path)
    assert "[B1 PRIMER]" not in other.stdout
    own = _hook("input-classifier.py",
                {"session_id": "sess-A", "prompt": "do the thing"}, tmp_path)
    assert "[B1 PRIMER]" in own.stdout


def test_every_hook_that_imports_session_state_binds():
    """An unbound hook writes to a file nothing reads (fails silently)."""
    importing = []
    for path in sorted(HOOKS.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        if re.search(r"^\s*import session_state\b", src, re.MULTILINE):
            importing.append(path.name)
            assert "session_state.bind_session(" in src, path.name
    assert len(importing) >= 13


# --- CLI resolution --------------------------------------------------------

def test_cli_resolves_claude_code_session_id(tmp_path):
    _stash(tmp_path, "sess-A")
    assert len(_cli(tmp_path, "--list-candidates", "--json", session="sess-A")) == 1
    assert _cli(tmp_path, "--list-candidates", "--json", session="sess-B") == []
    assert _cli(tmp_path, "--list-candidates", "--json",
                "--session-id", "sess-A") != []


def test_status_reads_context_from_this_sessions_transcript(tmp_path):
    _transcript(tmp_path / "claude" / "projects" / "p" / "sess-T.jsonl",
                tokens=612_000)
    st = _cli(tmp_path, "--status", "--json", session="sess-T")
    assert st["session_id"] == "sess-T"
    assert st["context_tokens"] == 612_000
    assert st["context_source"] == "transcript"
    assert st["pressure_band"] == "high"
    assert st["state_file"].endswith("agentic-ops-session-state-sess-T.json")


# --- legacy shared file ----------------------------------------------------

def _legacy(tmp_path, sid: str):
    (tmp_path / "agentic-ops-session-state.json").write_text(json.dumps({
        "session_id": sid, "tool_calls": 5,
        "candidates": [{"signal": "old", "source_hook": "x", "context": "c"}],
    }), encoding="utf-8")


def test_legacy_file_is_read_only_for_the_session_it_records(tmp_path):
    _legacy(tmp_path, "sess-L")
    assert [c["signal"] for c in
            _cli(tmp_path, "--list-candidates", "--json", session="sess-L")] == ["old"]
    assert _cli(tmp_path, "--list-candidates", "--json", session="sess-M") == []


def test_first_write_carries_legacy_state_into_the_session_file(tmp_path):
    _legacy(tmp_path, "sess-L")
    _meter(tmp_path, "sess-L")
    st = _state(tmp_path, "sess-L")
    assert st["tool_calls"] == 6
    assert [c["signal"] for c in st["candidates"]] == ["old"]


def test_blank_session_id_uses_the_legacy_file(tmp_path):
    _hook("git-stash-gate.py", {
        "tool_name": "Bash", "cwd": str(tmp_path),
        "tool_input": {"command": "git stash"},
    }, tmp_path)
    legacy = json.loads((tmp_path / "agentic-ops-session-state.json")
                        .read_text(encoding="utf-8"))
    assert len(legacy["candidates"]) == 1


# --- sweep -------------------------------------------------------------------

def test_new_session_sweeps_stale_session_files_only(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.delenv("AGENTIC_OPS_SESSION_STATE", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    sys.path.insert(0, str(TOOLS))
    try:
        import session_state
        ss = importlib.reload(session_state)
        old = time.time() - 8 * 86400
        stale = tmp_path / "agentic-ops-session-state-old.json"
        stale_lock = tmp_path / "agentic-ops-session-state-old.json.lock"
        fresh = tmp_path / "agentic-ops-session-state-live.json"
        legacy = tmp_path / "agentic-ops-session-state.json"
        for p in (stale, stale_lock, fresh, legacy):
            p.write_text("{}", encoding="utf-8")
        for p in (stale, stale_lock, legacy):
            os.utime(p, (old, old))

        assert ss.bind_session({"session_id": "new"}).endswith(
            "agentic-ops-session-state-new.json")
        assert not stale.exists() and not stale_lock.exists()
        assert fresh.exists() and legacy.exists()
    finally:
        sys.path.remove(str(TOOLS))
