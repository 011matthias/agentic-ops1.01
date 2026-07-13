"""Append-only JSONL write-ahead journal for send execution.

The E1/E2/E3 CSV resume-log pattern, structured. Every send walks the state
machine and each transition is journaled BEFORE the action it describes:

    claimed     lease taken, nothing irreversible yet
    com_issued  written IMMEDIATELY BEFORE .Send() - the irreversible call
    com_sent    .Send() returned (readback may still be pending)
    drafted     staged in Dirk's Drafts (draft-dirk mode; no send occurred)
    acked       result delivered to the app (terminal)
    nacked      failure delivered to the app (terminal)

Crash reconcile reads the latest non-terminal state per key:
    claimed     safe: COM never fired -> nack(transient), server re-queues
    com_issued  AMBIGUOUS: search Sent Items; found -> ack with evidence;
                not found -> leave leased + alert. NEVER resend.
    com_sent /
    drafted     outcome known, only the ack was lost -> replay it.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

TERMINAL = ("acked", "nacked")


class Journal:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, key: str, state: str, **meta) -> None:
        entry = {"key": key, "state": state,
                 "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 **meta}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def latest_by_key(self) -> dict[str, dict]:
        latest: dict[str, dict] = {}
        for e in self.entries():
            if e.get("key"):
                latest[e["key"]] = e
        return latest

    def pending(self) -> dict[str, dict]:
        """Latest entry per key whose state is not terminal (needs reconcile)."""
        return {k: e for k, e in self.latest_by_key().items()
                if e.get("state") not in TERMINAL}

    def compact(self, keep_terminal_days: int = 14) -> None:
        """Drop terminal entries older than the window; keep all pending."""
        cutoff = datetime.now(timezone.utc).timestamp() - keep_terminal_days * 86400
        latest = self.latest_by_key()
        keep_keys = set()
        for k, e in latest.items():
            if e.get("state") not in TERMINAL:
                keep_keys.add(k)
                continue
            try:
                ts = datetime.fromisoformat(e["ts"]).timestamp()
            except (KeyError, ValueError):
                ts = 0
            if ts >= cutoff:
                keep_keys.add(k)
        kept = [e for e in self.entries() if e.get("key") in keep_keys]
        tmp = self.path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for e in kept:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        tmp.replace(self.path)
