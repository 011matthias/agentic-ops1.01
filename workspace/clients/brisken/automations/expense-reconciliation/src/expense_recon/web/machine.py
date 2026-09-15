"""What this process is and how long it has been running (backlog item 50).

Criss's "Failed to fetch" on the attach dialog (2026-09-10) could not be
explained, and the reason is structural: a fetch that rejects never got a
response, so the request never reached this app and NO server-side log can
ever contain it. The machine that served that day was replaced within the
hour and its logs went with it. The hosting half of the item turned out to
be a non-issue (the live machine was already pinned always-on), which
removed the cold-start theory and left the failure unexplained.

What remains buildable is the thing that makes a RECURRENCE provable. This
module is its foundation: one home for the process's own identity and age,
read by `/healthz` and stamped onto every client failure report, so the two
can never disagree about which machine answered.

The decisive comparison it enables: if a client says a request failed N
seconds ago and this process has been running for fewer than N seconds,
then this process did not exist when that request was made. The machine was
replaced or restarted underneath it, which is exactly the question the
backlog item asks and could not answer in September. Fly's own machine
event log is the corroborating source; it outlives the machine, so a report
timestamp is enough to look the event up later.

Uptime is measured on the monotonic clock so an NTP correction cannot make
a process look older or younger than it is; `started_at` is wall-clock,
for a human reading the row.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

# Captured at import, which for this app is process start.
_STARTED_MONOTONIC = time.monotonic()
_STARTED_AT = datetime.now(timezone.utc)


def uptime_seconds() -> float:
    """Seconds this process has been running, on the monotonic clock."""
    return time.monotonic() - _STARTED_MONOTONIC


def started_at() -> str:
    return _STARTED_AT.isoformat()


def snapshot() -> dict:
    """The parallel block `/healthz` and every failure report carry.

    Empty strings off Fly (local dev, tests): absent identity is stated as
    absent rather than invented, so a local row never reads like a
    production one.
    """
    return {
        "machine": os.environ.get("FLY_MACHINE_ID", ""),
        "region": os.environ.get("FLY_REGION", ""),
        "app": os.environ.get("FLY_APP_NAME", ""),
        "started_at": started_at(),
        "uptime_s": round(uptime_seconds(), 1),
    }


def process_predates(seconds_ago: float | None) -> bool | None:
    """Was this process already running `seconds_ago` seconds back?

    The probe's whole point. ``None`` when the caller could not say when
    the failure happened, because "unknown" must never read as "no": a
    false "the machine restarted" would send the next investigation
    chasing the hosting theory that already cost this item one cycle.
    """
    if seconds_ago is None:
        return None
    return uptime_seconds() >= seconds_ago
