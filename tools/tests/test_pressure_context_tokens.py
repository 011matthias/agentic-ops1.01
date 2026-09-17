"""Tests for the context-size pressure signal (ECC port item 2).

session-pressure-meter.py reads the latest assistant `usage` record from the
payload's transcript_path and bands on context = input + cache_read +
cache_creation tokens. Tool-call counts are the fallback when the transcript is
unreadable. The subprocess tests run THROUGH the wired meter (rule_behaviors
B2 fix-bites-the-caller): disabling the meter's read_context_usage call must
turn them red.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys

import pytest

from hooklib import REPO, TOOLS, run_hook

METER = "session-pressure-meter.py"


@pytest.fixture
def iso(tmp_path, monkeypatch):
    """Isolate every shared file the meter touches (state, bg watches,
    sibling-session heartbeats) and return (env, session_state module)."""
    env = {
        "AGENTIC_OPS_SESSION_STATE": str(tmp_path / "state.json"),
        "AGENTIC_OPS_BG_WATCHES": str(tmp_path / "watches.json"),
        "AGENTIC_OPS_SESSION_DIR": str(tmp_path / "sessions"),
        "AGENTIC_OPS_CONTEXT_WINDOW": "1000000",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    sys.path.insert(0, str(TOOLS))
    import session_state
    session_state = importlib.reload(session_state)
    yield env, session_state
    sys.path.remove(str(TOOLS))


def assistant(tokens: int, msg_id: str = "msg_1", sidechain: bool = False,
              model: str = "claude-opus-5") -> dict:
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "message": {
            "id": msg_id,
            "model": model,
            "usage": {
                "input_tokens": 10,
                "cache_read_input_tokens": tokens - 1010,
                "cache_creation_input_tokens": 1000,
                "output_tokens": 500,
            },
        },
    }


def write_transcript(path, *entries, filler: str = "") -> str:
    lines = [json.dumps(e) for e in entries]
    if filler:
        lines.append(filler)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def meter(env, session_id: str, transcript: str = "") -> str:
    payload = {"session_id": session_id, "tool_name": "Bash", "tool_input": {}}
    if transcript:
        payload["transcript_path"] = transcript
    r = run_hook(METER, payload, env=env)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


# ---- read_context_usage ----------------------------------------------------

def test_reads_latest_main_thread_usage(iso, tmp_path):
    _, ss = iso
    tx = write_transcript(
        tmp_path / "t.jsonl",
        {"type": "user", "message": {"content": "hi"}},
        assistant(120_000, "msg_a"),
        assistant(312_000, "msg_b"),
        # A later subagent turn must not stand in for the main context.
        assistant(40_000, "msg_side", sidechain=True),
    )
    got = ss.read_context_usage(tx)
    assert got["tokens"] == 312_000
    assert got["message_id"] == "msg_b"
    assert got["model"] == "claude-opus-5"


def test_skips_zero_usage_and_lookalike_lines(iso, tmp_path):
    _, ss = iso
    tx = write_transcript(
        tmp_path / "t.jsonl",
        assistant(250_000, "msg_real"),
        # A tool result quoting "usage" and "compact_boundary" is not a record.
        {"type": "user", "message": {"content": 'x "usage" "compact_boundary"'}},
        {"type": "assistant", "message": {"id": "syn", "model": "<synthetic>",
                                          "usage": {"input_tokens": 0}}},
        filler="{not json",
    )
    assert ss.read_context_usage(tx)["tokens"] == 250_000


def test_compaction_after_last_usage_is_unknown(iso, tmp_path):
    _, ss = iso
    tx = write_transcript(
        tmp_path / "t.jsonl",
        assistant(600_000),
        {"type": "system", "subtype": "compact_boundary",
         "compactMetadata": {"trigger": "manual", "preTokens": 600_000}},
    )
    assert ss.read_context_usage(tx) is None


def test_usage_beyond_first_tail_chunk_is_found(iso, tmp_path):
    _, ss = iso
    big = json.dumps({"type": "user", "message": {"content": "x" * 600_000}})
    tx = write_transcript(tmp_path / "t.jsonl", assistant(410_000), filler=big)
    assert ss.read_context_usage(tx)["tokens"] == 410_000


def test_missing_or_empty_transcript_is_none(iso, tmp_path):
    _, ss = iso
    assert ss.read_context_usage(str(tmp_path / "absent.jsonl")) is None
    assert ss.read_context_usage("") is None
    (tmp_path / "empty.jsonl").write_text("", encoding="utf-8")
    assert ss.read_context_usage(str(tmp_path / "empty.jsonl")) is None


# ---- bands -----------------------------------------------------------------

@pytest.mark.parametrize("tokens,band", [
    (0, None), (299_999, None), (300_000, "moderate"), (499_999, "moderate"),
    (500_000, "high"), (700_000, "critical"), (950_000, "critical"),
])
def test_context_bands_on_1m_window(iso, tokens, band):
    _, ss = iso
    assert ss.context_band(tokens) == band


def test_bands_scale_with_window(iso):
    _, ss = iso
    assert ss.context_band(60_000, window=200_000) == "moderate"
    assert ss.context_band(140_000, window=200_000) == "critical"


# ---- the wired meter (caller-level) ----------------------------------------

def test_meter_advises_on_context_not_tool_calls(iso, tmp_path):
    env, _ = iso
    tx = write_transcript(tmp_path / "t.jsonl", assistant(320_000))
    out = meter(env, "S1", tx)  # first tool call of the session
    assert "PRESSURE: MODERATE" in out
    assert "context ~320k tokens (32% of the 1M window)" in out
    assert meter(env, "S1", tx) == ""  # same band: silent


def test_meter_escalates_and_rearms_after_compaction(iso, tmp_path):
    env, _ = iso
    t = tmp_path / "t.jsonl"
    assert "MODERATE" in meter(env, "S1", write_transcript(t, assistant(320_000)))
    assert "HIGH" in meter(env, "S1", write_transcript(t, assistant(520_000)))
    # Compaction: context drops, the advisory stays silent but re-arms.
    assert meter(env, "S1", write_transcript(t, assistant(45_000))) == ""
    assert "MODERATE" in meter(env, "S1", write_transcript(t, assistant(310_000)))


def test_interleaved_sibling_session_does_not_re_advise(iso, tmp_path):
    env, _ = iso
    tx_a = write_transcript(tmp_path / "a.jsonl", assistant(330_000))
    assert "MODERATE" in meter(env, "A", tx_a)
    meter(env, "B", str(tmp_path / "b-missing.jsonl"))  # sibling resets state
    assert meter(env, "A", tx_a) == ""


def test_unreadable_transcript_falls_back_to_tool_calls(iso, tmp_path):
    env, ss = iso
    ss.ensure_session("F")
    for _ in range(79):
        ss.bump_tool("Bash")
    out = meter(env, "F", str(tmp_path / "missing.jsonl"))
    assert "PRESSURE: MODERATE" in out
    assert "tool-call proxy" in out


def test_status_exposes_context_tokens(iso, tmp_path):
    env, _ = iso
    meter(env, "S9", write_transcript(tmp_path / "t.jsonl", assistant(512_000)))
    r = subprocess.run(
        [sys.executable, str(TOOLS / "session_state.py"), "--status", "--json"],
        capture_output=True, text=True, timeout=30, cwd=str(REPO),
        env={**os.environ, **env},
    )
    st = json.loads(r.stdout)
    assert st["context_tokens"] == 512_000
    assert st["pressure_signal"] == "context"
    assert st["pressure_band"] == "high"
    assert st["context_model"] == "claude-opus-5"
