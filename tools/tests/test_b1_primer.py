"""B1 primer: stop-b1-gate records a block, input-classifier primes the next turn.

The Stop gate is post-hoc (it fires after the deferring response exists, costing
a turn redo). The 2026-07-22 hook-log census found 608 blocks against 2554 clean
stops with no downward trend across July, and 92% of blocks inside bursts (2+
within an hour). These tests pin the loop that turns a recorded block into a
pre-generation nudge on the FOLLOWING turn, exactly once per block.

State is redirected via AGENTIC_OPS_SESSION_STATE so the developer's live
session state is never touched.
"""
from __future__ import annotations

import importlib.util
import json

from hooklib import TOOLS, permission_decision, run_hook


def _load_state_module(path):
    spec = importlib.util.spec_from_file_location("session_state", TOOLS / "session_state.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.STATE_FILE = str(path)
    return mod


def _ctx(proc) -> str:
    out = proc.stdout.strip()
    if not out:
        return ""
    try:
        obj = json.loads(out)
    except json.JSONDecodeError:
        return ""
    return (obj.get("hookSpecificOutput") or {}).get("additionalContext", "") or ""


def _prompt(state_path, text="do the thing"):
    return run_hook(
        "input-classifier.py",
        {"prompt": text},
        env={"AGENTIC_OPS_SESSION_STATE": str(state_path)},
    )


# --- session_state counter semantics --------------------------------------

def test_counter_starts_clean_and_bumps(tmp_path):
    st = _load_state_module(tmp_path / "s.json")
    assert st.b1_priming_due() == 0
    st.bump_b1_block()
    assert st.b1_priming_due() == 1
    st.bump_b1_block()
    assert st.b1_priming_due() == 2


def test_mark_primed_clears_due_but_keeps_total(tmp_path):
    st = _load_state_module(tmp_path / "s.json")
    st.bump_b1_block()
    st.mark_b1_primed()
    assert st.b1_priming_due() == 0
    assert st.load()["b1_blocks"] == 1
    # a further block re-arms the primer
    st.bump_b1_block()
    assert st.b1_priming_due() == 1


def test_legacy_state_without_keys_heals(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"session_id": "old", "tool_calls": 3}), encoding="utf-8")
    st = _load_state_module(p)
    assert st.b1_priming_due() == 0
    st.bump_b1_block()
    assert st.load()["b1_blocks"] == 1


def test_new_session_resets_the_counter(tmp_path):
    st = _load_state_module(tmp_path / "s.json")
    st.ensure_session("sess-a")
    st.bump_b1_block()
    st.ensure_session("sess-b")
    assert st.b1_priming_due() == 0


# --- stop-b1-gate records; input-classifier primes -------------------------

def test_block_records_and_next_prompt_primes_once(tmp_path):
    state = tmp_path / "s.json"
    env = {"AGENTIC_OPS_SESSION_STATE": str(state)}
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(json.dumps({
        "type": "assistant",
        "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Done. Want me to deploy it?"}
        ]},
    }) + "\n", encoding="utf-8")

    stop = run_hook(
        "stop-b1-gate.py",
        {"transcript_path": str(transcript)},
        env=env,
    )
    assert json.loads(stop.stdout)["decision"] == "block"

    primed = _ctx(_prompt(state))
    assert "[B1 PRIMER]" in primed
    assert "1 deferral" in primed          # singular, count surfaced
    # exactly once: the following turn is silent again
    assert "[B1 PRIMER]" not in _ctx(_prompt(state))


def test_clean_stop_records_nothing(tmp_path):
    state = tmp_path / "s.json"
    env = {"AGENTIC_OPS_SESSION_STATE": str(state)}
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(json.dumps({
        "type": "assistant",
        "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Shipped and verified; PR #1 merged."}
        ]},
    }) + "\n", encoding="utf-8")

    stop = run_hook("stop-b1-gate.py", {"transcript_path": str(transcript)}, env=env)
    assert stop.stdout.strip() == ""
    assert permission_decision(stop.stdout) is None
    assert "[B1 PRIMER]" not in _ctx(_prompt(state))


def test_second_block_rearms_the_primer(tmp_path):
    state = tmp_path / "s.json"
    st = _load_state_module(state)
    st.bump_b1_block()
    assert "[B1 PRIMER]" in _ctx(_prompt(state))
    st.bump_b1_block()
    ctx = _ctx(_prompt(state))
    assert "[B1 PRIMER]" in ctx
    assert "2 deferrals" in ctx            # plural + cumulative count


def test_primer_composes_with_exploratory_gate(tmp_path):
    state = tmp_path / "s.json"
    st = _load_state_module(state)
    st.bump_b1_block()
    ctx = _ctx(_prompt(state, "maybe we could perhaps rethink the approach"))
    assert "[GATE]" in ctx and "[B1 PRIMER]" in ctx


def test_primer_silent_with_no_blocks(tmp_path):
    assert "[B1 PRIMER]" not in _ctx(_prompt(tmp_path / "s.json"))


def test_fail_open_on_corrupt_state(tmp_path):
    state = tmp_path / "s.json"
    state.write_text("{ this is not json", encoding="utf-8")
    proc = _prompt(state)
    assert proc.returncode == 0
    assert "[B1 PRIMER]" not in _ctx(proc)
