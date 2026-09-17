# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Append-only local usage telemetry for the harness (JSONL, never committed).

WHY THIS EXISTS
---------------
The harness had no usage data at all: 57 skills, 12 agents and ~140 memory
files, and no way to tell a load-bearing one from a dead one except recall.
ECC's skill-run tracker showed the cheap fix: record each invocation as one
identifier-only line and let a stocktake join it against the inventory.

`session-pressure-meter.py` (PostToolUse, all tools) is the only writer; it
calls `record_from_payload` on every tool call, and the audit tools are the
readers. Two streams:

  skill-runs.jsonl    {ts, session_id, kind, name, ok}   -> skill_stocktake.py
  memory-reads.jsonl  {ts, session_id, store, file}      -> memory_audit.py

A memory read is a Read of, or a cat/sed/head/tail/Get-Content on, a file
under ~/.claude/projects/<store>/memory/. The memory files themselves are
never written.

WHERE
-----
`~/.claude/agentic-ops-telemetry/` (override: AGENTIC_OPS_TELEMETRY_DIR). Not
the OS temp dir where session_state lives: stocktake windows are 30 and 90
days, and Windows Storage Sense purges %TEMP%. Outside every checkout, so all
worktrees feed one store and nothing can be committed by accident.

PRIVACY
-------
Identifiers only. A skill or agent name is persisted only when it looks like
an identifier (bounded charset and length); prompts, args and descriptions are
never written.

DEFENSIVE
---------
Every writer swallows its own errors. A telemetry failure must never break the
tool call the meter rides on.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_RUNS = "skill-runs.jsonl"
_IDENT = re.compile(r"^[A-Za-z0-9._:@/-]{1,128}$")


def telemetry_dir() -> Path:
    env = os.environ.get("AGENTIC_OPS_TELEMETRY_DIR")
    return Path(env) if env else Path.home() / ".claude" / "agentic-ops-telemetry"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append(stream: str, record: dict) -> None:
    try:
        d = telemetry_dir()
        d.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n"
        with open(d / stream, "a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass


def read(stream: str, since_days: float | None = None) -> list[dict]:
    """All parseable records, optionally only those newer than `since_days`."""
    path = telemetry_dir() / stream
    if not path.is_file():
        return []
    cutoff = None
    if since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if not isinstance(rec, dict):
                continue
            if cutoff is not None:
                ts = parse_ts(rec.get("ts"))
                if ts is None or ts < cutoff:
                    continue
            out.append(rec)
    return out


def parse_ts(value) -> datetime | None:
    try:
        ts = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def coverage_days(stream: str) -> float:
    """Days since the oldest record: how much history a verdict can lean on."""
    oldest = None
    for rec in read(stream):
        ts = parse_ts(rec.get("ts"))
        if ts and (oldest is None or ts < oldest):
            oldest = ts
    if oldest is None:
        return 0.0
    return (datetime.now(timezone.utc) - oldest).total_seconds() / 86400


def _identifier(value) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip()
    return v if _IDENT.match(v) else None


def _ok(payload: dict) -> bool:
    resp = payload.get("tool_response")
    if isinstance(resp, dict):
        if resp.get("is_error") is True or resp.get("isError") is True:
            return False
        status = resp.get("status")
        if isinstance(status, str) and re.search(r"error|fail", status, re.I):
            return False
        err = resp.get("error")
        if isinstance(err, str) and err.strip():
            return False
    return True


def skill_run_record(payload: dict) -> dict | None:
    """{ts, session_id, kind, name, ok} for a Skill or Agent call, else None."""
    tool = payload.get("tool_name")
    ti = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    if tool == "Skill":
        kind, name = "skill", _identifier(ti.get("skill"))
    elif tool == "Agent":
        # The Agent tool defaults to general-purpose when no type is passed.
        kind, name = "agent", _identifier(ti.get("subagent_type") or "general-purpose")
    else:
        return None
    if not name:
        return None
    return {
        "ts": _now(),
        "session_id": _identifier(payload.get("session_id")) or "",
        "kind": kind,
        "name": name,
        "ok": _ok(payload),
    }


# --------------------------------------------------------------------------
# Memory reads
# --------------------------------------------------------------------------
MEMORY_READS = "memory-reads.jsonl"
# A file in a Claude Code auto-memory store: ~/.claude/projects/<slug>/memory/<f>.md
_MEMORY_PATH = re.compile(
    r"\.claude/projects/(?P<store>[^/\s\"';|&]+)/memory/(?P<file>[^/\s\"';|&*?]+\.md)\b",
    re.IGNORECASE,
)
# Shell readers whose target is a file the agent is reading, not searching.
_READERS = re.compile(r"\b(cat|sed|head|tail|less|more|type|Get-Content|gc)\b", re.IGNORECASE)
_ASSIGN = re.compile(r"(?:^|[;&|\s])(?:\$env:)?([A-Za-z_]\w*)=([\"']?)([^\"'\s;&|]+)\2")


def _expand_vars(command: str) -> str:
    """Resolve `M="dir"; cat "$M/x.md"`-style references inside one command.
    Only assignments made in the same command are known; anything else stays
    unresolved and simply does not match."""
    values = {m.group(1): m.group(3) for m in _ASSIGN.finditer(command)}
    for name, value in values.items():
        pattern = r"\$\{" + re.escape(name) + r"\}|\$" + re.escape(name) + r"\b"
        command = re.sub(pattern, lambda _m, v=value: v, command)
    return command


def memory_paths_read(payload: dict) -> list[tuple[str, str]]:
    """(store, file) pairs a Read or a shell reader call opened."""
    tool = payload.get("tool_name")
    ti = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    if tool == "Read":
        texts = [str(ti.get("file_path") or "")]
    elif tool in ("Bash", "PowerShell"):
        command = str(ti.get("command") or "")
        if not _READERS.search(command):
            return []
        texts = [_expand_vars(command)]
    else:
        return []
    found = []
    for text in texts:
        for m in _MEMORY_PATH.finditer(text.replace("\\", "/")):
            pair = (m.group("store"), m.group("file"))
            if pair not in found:
                found.append(pair)
    return found


def record_from_payload(payload: dict) -> None:
    """The meter's single entry point. Never raises."""
    try:
        rec = skill_run_record(payload)
        if rec:
            append(SKILL_RUNS, rec)
    except Exception:
        pass
    try:
        session = _identifier(payload.get("session_id")) or ""
        for store, fname in memory_paths_read(payload):
            append(MEMORY_READS, {"ts": _now(), "session_id": session,
                                  "store": store, "file": fname})
    except Exception:
        pass
