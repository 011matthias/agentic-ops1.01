"""Shared liveness reads for the ops surfaces (board freshness strip, drill
status): worker heartbeat age, per-mailbox capture watermark ages, truth-scan
heartbeat, and the persisted alert state rows. Read-only over the state KV
plus the capture watermark file - no Graph calls, so a page render can afford
it on every hit. drill.status_report and the web board both build from here,
so the two surfaces can never disagree on what "fresh" means."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .cloud_worker import _capture_state_path
from .truth_scan import ALERT_KEY as TRUTH_ALERT_KEY
from .truth_scan import HEARTBEAT_KEY as TRUTH_HEARTBEAT_KEY
from .web.store import ContactStore

# Freshness thresholds for the board strip: the capture tick runs every ~15
# minutes, so a heartbeat older than 2 hours means live capture is down; the
# deep truth scan is daily, so older than 2 days means the reconcile stopped.
HEARTBEAT_FRESH_MINUTES = 2 * 60
TRUTH_SCAN_FRESH_MINUTES = 2 * 24 * 60


def age_minutes(ts: str | None, at: datetime) -> float | None:
    """Minutes between an ISO timestamp and ``at`` (None on absent/bad ts)."""
    if not ts:
        return None
    try:
        then = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return round((at - then).total_seconds() / 60, 1)


def fmt_age(minutes: float | None) -> str:
    """A human age for the strip: '12m', '3.4h', '2.1d', or 'never'."""
    if minutes is None:
        return "never"
    minutes = max(minutes, 0)
    if minutes < 90:
        return f"{int(minutes)}m"
    hours = minutes / 60
    if hours < 48:
        return f"{hours:.1f}h"
    return f"{hours / 24:.1f}d"


def state_json(store: ContactStore, key: str) -> dict:
    """A state row parsed as a JSON object; {} on absent or malformed."""
    raw = store.get_state(key)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def capture_watermark_ages(data_dir: str | Path,
                           at: datetime) -> dict[str, float | None]:
    """Per-mailbox capture watermark age in minutes. The watermark lives in
    the cloud capture state FILE (not the state KV), which the web tier can
    read because it shares the worker's data dir on the Fly volume."""
    try:
        marks = (json.loads(_capture_state_path(Path(data_dir))
                            .read_text(encoding="utf-8"))
                 .get("watermarks") or {})
    except (OSError, json.JSONDecodeError):
        marks = {}
    return {mbx: age_minutes(ts, at) for mbx, ts in marks.items()}


def guard_alerts(store: ContactStore) -> dict[str, dict]:
    """Every persisted send_guard_alert:{campaign} state row, by campaign."""
    alerts: dict[str, dict] = {}
    for key in store.state_keys_with_prefix("send_guard_alert:"):
        raw = store.get_state(key) or "{}"
        try:
            alerts[key.split(":", 1)[1]] = json.loads(raw)
        except json.JSONDecodeError:
            alerts[key.split(":", 1)[1]] = {"raw": raw}
    return alerts


def freshness_report(store: ContactStore, data_dir: str | Path,
                     at: datetime | None = None) -> dict:
    """Everything the board strip needs in one dict: worker heartbeat (age +
    counters), per-mailbox capture watermark ages, truth-scan heartbeat (ts +
    counts), and the persisted truth-scan / cloud-worker alerts."""
    at = at or datetime.now(timezone.utc)
    heartbeat = state_json(store, "worker_heartbeat")
    hb_age = age_minutes(heartbeat.get("ts"), at)
    ages = capture_watermark_ages(data_dir, at)
    known = [a for a in ages.values() if a is not None]
    scan = state_json(store, TRUTH_HEARTBEAT_KEY)
    scan_age = age_minutes(scan.get("ts"), at)
    return {
        "heartbeat": heartbeat or None,
        "heartbeat_age_minutes": hb_age,
        "heartbeat_age": fmt_age(hb_age),
        "heartbeat_fresh": hb_age is not None and hb_age < HEARTBEAT_FRESH_MINUTES,
        "capture_watermark_ages_minutes": ages,
        "capture_watermark_ages": {m: fmt_age(a) for m, a in ages.items()},
        "capture_watermark_age_minutes": max(known) if known else None,
        "truth_scan": scan or None,
        "truth_scan_age_minutes": scan_age,
        "truth_scan_age": fmt_age(scan_age),
        "truth_scan_fresh": scan_age is not None and scan_age < TRUTH_SCAN_FRESH_MINUTES,
        "truth_scan_alert": state_json(store, TRUTH_ALERT_KEY) or None,
        "cloud_worker_alert": state_json(store, "cloud_worker_alert") or None,
    }
