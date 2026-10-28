"""Memory read-tracking (session-pressure-meter rider) + memory_audit.py.

Read detection is driven THROUGH the wired meter with real PostToolUse
payloads (rule_behaviors B2). The audit runs as a subprocess against a fixture
store. Nothing here touches the real memory store or live telemetry.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

from hooklib import TOOLS, run_hook

STORE = "c--Users-someone-Repo-agentic-ops1"
MEM = f"C:/Users/someone/.claude/projects/{STORE}/memory"


@pytest.fixture
def env(tmp_path):
    tel = tmp_path / "telemetry"
    return {
        "env": {
            "AGENTIC_OPS_TELEMETRY_DIR": str(tel),
            "AGENTIC_OPS_SESSION_STATE": str(tmp_path / "state.json"),
            "AGENTIC_OPS_BG_WATCHES": str(tmp_path / "watches.json"),
            "AGENTIC_OPS_SESSION_DIR": str(tmp_path / "sessions"),
        },
        "reads": tel / "memory-reads.jsonl",
        "tmp": tmp_path,
    }


def _meter(env, tool, tool_input):
    p = run_hook("session-pressure-meter.py",
                 {"hook_event_name": "PostToolUse", "session_id": "s-9",
                  "tool_name": tool, "tool_input": tool_input}, env=env["env"])
    assert p.returncode == 0


def _reads(env):
    if not env["reads"].is_file():
        return []
    return [(r["store"], r["file"]) for r in
            (json.loads(x) for x in env["reads"].read_text(encoding="utf-8").splitlines())]


# ------------------------------------------------------------ read tracking
def test_read_tool_on_memory_file_is_recorded(env):
    _meter(env, "Read", {"file_path": MEM.replace("/", "\\") + "\\feedback_x.md"})
    assert _reads(env) == [(STORE, "feedback_x.md")]
    rec = json.loads(env["reads"].read_text(encoding="utf-8"))
    assert set(rec) == {"ts", "session_id", "store", "file"} and rec["session_id"] == "s-9"


def test_shell_readers_are_recorded_including_same_command_variables(env):
    _meter(env, "Bash", {"command": f'cat "{MEM}/project_a.md" | head -5'})
    _meter(env, "Bash", {"command": f'M="{MEM}"; sed -n 1,20p "$M/reference_b.md"; head "${{M}}/user_c.md"'})
    _meter(env, "PowerShell", {"command": f'Get-Content "{MEM}/feedback_d.md"'})
    assert _reads(env) == [(STORE, "project_a.md"), (STORE, "reference_b.md"),
                           (STORE, "user_c.md"), (STORE, "feedback_d.md")]


def test_variable_prefix_does_not_expand_a_longer_name(env):
    _meter(env, "Bash", {"command": f'M="{MEM}"; cat "$MEMORY_HOME/x.md"'})
    assert _reads(env) == []


def test_non_reads_are_not_recorded(env):
    _meter(env, "Bash", {"command": f'ls "{MEM}"'})                   # listing, not reading
    _meter(env, "Bash", {"command": f'grep -rn foo "{MEM}/x.md"'})    # search, not read
    _meter(env, "Write", {"file_path": f"{MEM}/new.md", "content": "x"})
    _meter(env, "Read", {"file_path": "C:/Users/someone/Repo/docs/feedback_x.md"})
    assert _reads(env) == []


def test_memory_files_themselves_are_never_written(env, tmp_path):
    mem = tmp_path / ".claude" / "projects" / STORE / "memory"
    mem.mkdir(parents=True)
    target = mem / "feedback_x.md"
    target.write_text("original", encoding="utf-8")
    before = target.stat().st_mtime_ns
    time.sleep(0.01)
    _meter(env, "Read", {"file_path": str(target)})
    assert target.read_text(encoding="utf-8") == "original"
    assert target.stat().st_mtime_ns == before
    assert _reads(env) == [(STORE, "feedback_x.md")]


# ----------------------------------------------------------------- audit
def _memory(d, name, mtype, description, body="", modified=None):
    mod = f"  modified: {modified}\n" if modified else ""
    (d / name).write_text(
        f"---\nname: {name[:-3]}\ndescription: \"{description}\"\nmetadata:\n"
        f"  node_type: memory\n  type: {mtype}\n{mod}---\n\n{body}\n", encoding="utf-8")


def _set_old(path, days):
    t = time.time() - days * 86400
    os.utime(path, (t, t))


@pytest.fixture
def store(tmp_path):
    mem = tmp_path / "projects" / STORE / "memory"
    mem.mkdir(parents=True)
    _memory(mem, "feedback_keep.md", "feedback", "Rule about pending CI checks.", "red / pending CI")
    _memory(mem, "project_old_pending.md", "project", "Build pending owner approval.")
    _memory(mem, "project_fresh_pending.md", "project", "Migration waits on a pending vendor answer.")
    _memory(mem, "project_unread.md", "project", "A finished decision record.")
    _memory(mem, "reference_tool_notes.md", "reference", "How the tool behaves on Windows.")
    _memory(mem, "reference_tool_notes_v2.md", "reference", "How the tool behaves on Windows, again.")
    _memory(mem, "project_brisken_recon_mail_intake.md", "project", "Mail intake accepts any sender.")
    _memory(mem, "project_brisken_recon_master_data.md", "project", "FX and card maps live in settings.")
    _memory(mem, "user_unindexed.md", "user", "Not in the index.")
    for f in ("feedback_keep.md", "project_old_pending.md", "project_unread.md"):
        _set_old(mem / f, 120)
    index = [
        "# Memory Index", "",
        "- [Keep](feedback_keep.md) - rule",
        "- [Old pending](project_old_pending.md) - x",
        "- [Fresh pending](project_fresh_pending.md) - x",
        "- [Unread](project_unread.md) - x",
        "- [Tool notes](reference_tool_notes.md) - x",
        "- [Tool notes v2](reference_tool_notes_v2.md) - x",
        "- [Recon mail intake](project_brisken_recon_mail_intake.md) - x",
        "- [Recon master data](project_brisken_recon_master_data.md) - x",
        "- [Ghost](project_ghost.md) - file was deleted",
    ]
    (mem / "MEMORY.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return mem


def _audit(mem, env):
    p = subprocess.run([sys.executable, str(TOOLS / "memory_audit.py"), "--memory-dir", str(mem),
                        "--format", "json"], capture_output=True, text=True, timeout=60,
                       env={**os.environ, **env["env"]})
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def _buckets(out):
    return {r["file"]: (r["bucket"], r["reason"]) for r in out["rows"]}


def _seed_reads(env, entries):
    env["reads"].parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    with env["reads"].open("a", encoding="utf-8") as fh:
        for days_ago, fname in entries:
            ts = (now - timedelta(days=days_ago)).isoformat(timespec="seconds")
            fh.write(json.dumps({"ts": ts, "session_id": "s", "store": STORE, "file": fname}) + "\n")


def test_index_integrity_duplicates_and_stale_without_telemetry(store, env):
    out = _audit(store, env)
    b = _buckets(out)
    m = out["meta"]
    assert (m["files"], m["index_entries"], m["read_based_retire_enabled"]) == (9, 9, False)
    assert b["project_ghost.md"][0] == "Retire" and "missing file" in b["project_ghost.md"][1]
    assert b["user_unindexed.md"][0] == "Verify" and "no MEMORY.md line" in b["user_unindexed.md"][1]
    assert b["reference_tool_notes.md"][0] == "Merge"
    assert "reference_tool_notes_v2.md" in b["reference_tool_notes.md"][1]
    # a shared long prefix is not a duplicate
    assert b["project_brisken_recon_mail_intake.md"][0] == "Keep"
    # stale open work: project type, 60+ days; not a feedback rule, not a fresh one
    assert b["project_old_pending.md"][0] == "Verify" and "pending" in b["project_old_pending.md"][1]
    assert b["project_fresh_pending.md"][0] == "Keep"
    assert b["feedback_keep.md"][0] == "Keep"
    # no telemetry -> nothing retired on reads
    assert b["project_unread.md"][0] == "Keep"


def test_read_based_retire_needs_coverage_and_age(store, env):
    _seed_reads(env, [(40, "feedback_keep.md"), (3, "feedback_keep.md"), (1, "project_fresh_pending.md")])
    out = _audit(store, env)
    b = _buckets(out)
    rows = {r["file"]: r for r in out["rows"]}
    assert out["meta"]["read_based_retire_enabled"] is True
    assert b["project_unread.md"][0] == "Retire"           # 0 reads, untouched 120d
    assert b["feedback_keep.md"][0] == "Keep"               # old but read
    assert (rows["feedback_keep.md"]["reads_30d"], rows["feedback_keep.md"]["reads_90d"]) == (1, 2)
    assert b["project_brisken_recon_master_data.md"][0] == "Keep"  # unread but recently written


def test_reads_from_another_store_do_not_count(store, env):
    env["reads"].parent.mkdir(parents=True, exist_ok=True)
    old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(timespec="seconds")
    env["reads"].write_text(json.dumps({"ts": old, "session_id": "s", "store": "other-store",
                                        "file": "project_unread.md"}) + "\n", encoding="utf-8")
    assert _audit(store, env)["meta"]["reads_total"] == 0


def test_text_output_reports_counts_and_changes_nothing(store, env):
    before = {p.name: p.read_bytes() for p in store.iterdir()}
    p = subprocess.run([sys.executable, str(TOOLS / "memory_audit.py"), "--memory-dir", str(store)],
                       capture_output=True, text=True, timeout=60, env={**os.environ, **env["env"]})
    assert "9 index entries" in p.stdout and "no read-based Retire" in p.stdout
    assert "Nothing was changed" in p.stdout
    assert {q.name: q.read_bytes() for q in store.iterdir()} == before
