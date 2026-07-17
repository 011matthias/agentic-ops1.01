"""Worker CLI: ``lead-desk-worker tick|status|capture`` (+ --dry-run modes).

The tick is the whole contract, in this exact order (the ordering IS the
cadence-halt guarantee - capture runs before claim, so a reply that arrived
five minutes ago halts the send server-side):

    1. pre-flight readiness (all read-only; any fail = clean abort)
    2. replay unacked results from the journal (crash reconcile)
    3. capture replies/bounces -> POST /events (halts cadences)
    4. claim due sends -> execute -> ack, throttled
    5. heartbeat

Scheduled every 15 min, weekdays, "run only when user is logged on"
(Outlook COM needs the interactive session). Outside the send window the
tick still captures replies, then exits without claiming.

    lead-desk-worker tick --home <state-dir>
    lead-desk-worker tick --dry-run          # print, touch nothing
    lead-desk-worker tick --draft-to-self    # full pipeline -> own Drafts
    lead-desk-worker status                  # server + local readiness
    lead-desk-worker capture [--dry-run]     # capture pass only
"""
from __future__ import annotations

import argparse
import json
import random
import time
import urllib.request
from datetime import datetime, timezone

from . import capture_local, com_mail, sender
from .api import ApiRejected, ApiUnavailable, LeadDeskApi
from .config import DIRK_SMTP, MAILBOXES, SEND_FROM, WorkerConfig, load_config
from .journal import Journal

MAX_CLAIM = 25
CLOCK_SKEW_LIMIT_S = 300


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(cfg: WorkerConfig, record: dict) -> None:
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    with (cfg.runs_dir / f"{day}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), **record}, ensure_ascii=False) + "\n")


def _alert(cfg: WorkerConfig, subject: str, body: str) -> None:
    """Resend email alert (tools/send_email.py pattern: stdlib + real UA)."""
    print(f"ALERT: {subject}\n{body}")
    if not (cfg.resend_api_key and cfg.alert_to):
        return
    payload = json.dumps({
        "from": "onboarding@resend.dev", "to": [cfg.alert_to],
        "subject": f"[lead-desk-worker] {subject}", "text": body,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload, method="POST",
        headers={"Authorization": f"Bearer {cfg.resend_api_key}",
                 "Content-Type": "application/json",
                 "User-Agent": "agentic-ops-lead-desk-worker/1.0"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception as exc:  # noqa: BLE001 - alerting must never crash the run
        print(f"  (alert email failed: {exc})")


def _preflight(cfg: WorkerConfig, api: LeadDeskApi, need_outlook: bool) -> dict | None:
    """Read-only readiness block (rule_instantly_invasive pattern). Returns
    {status, ol, accounts} or None after printing/logging the failure."""
    checks: list[tuple[str, bool, str]] = []

    kill_local = cfg.kill_engaged()
    checks.append(("local kill switch off", not kill_local, str(cfg.kill_file)))
    if not cfg.worker_secret:
        checks.append(("worker secret configured", False, "LEAD_DESK_WORKER_SECRET"))
    try:
        status = api.status()
        checks.append(("app reachable", True, cfg.base_url))
        checks.append(("server kill switch off", not status.get("kill_switch"), ""))
        server_time = datetime.fromisoformat(status["server_time"])
        skew = abs((server_time - datetime.now(timezone.utc)).total_seconds())
        checks.append((f"clock skew {int(skew)}s < {CLOCK_SKEW_LIMIT_S}s",
                       skew < CLOCK_SKEW_LIMIT_S, ""))
    except (ApiUnavailable, ApiRejected, KeyError, ValueError) as exc:
        checks.append(("app reachable", False, str(exc)[:200]))
        status = None

    ol = accounts = None
    if need_outlook:
        try:
            ol = com_mail.get_outlook()
            auto = com_mail.resolve_account(ol, SEND_FROM)
            dirk = com_mail.resolve_account(ol, DIRK_SMTP)
            checks.append((f"account {SEND_FROM}", auto is not None, ""))
            checks.append((f"account {DIRK_SMTP}", dirk is not None, ""))
            accounts = {"auto": auto, "dirk": dirk, "self_smtp": SEND_FROM}
        except Exception as exc:
            checks.append(("Outlook COM up", False, str(exc)[:200]))

    ok = all(passed for _, passed, _ in checks)
    for name, passed, detail in checks:
        print(f"  [{'ok' if passed else 'FAIL'}] {name}" + (f" ({detail})" if detail and not passed else ""))
    if not ok:
        return None
    return {"status": status, "ol": ol, "accounts": accounts}


def cmd_status(cfg: WorkerConfig) -> int:
    api = LeadDeskApi(cfg)
    print("Pre-flight:")
    ready = _preflight(cfg, api, need_outlook=True)
    if ready is None:
        return 1
    print("\nCampaigns:")
    for c in (ready["status"] or {}).get("campaigns", []):
        print(f"  {c['campaign']:<20} {c['status']:<9} "
              f"in_window={c['in_window']} sent_today={c['daily_sent']}"
              f"/{c['daily_cap']}")
    pending = Journal(cfg.journal_path).pending()
    print(f"\nJournal pending: {len(pending)}")
    for k, e in pending.items():
        print(f"  {k}: {e.get('state')}")
    return 0


def cmd_capture(cfg: WorkerConfig, dry_run: bool) -> int:
    api = LeadDeskApi(cfg)
    ol = com_mail.get_outlook()
    report = capture_local.run_capture(ol, api, cfg, MAILBOXES, dry_run=dry_run)
    print(json.dumps(report, indent=1, default=str))
    _log(cfg, {"cmd": "capture", **{k: v for k, v in report.items() if k != "payloads"}})
    return 0


def cmd_tick(cfg: WorkerConfig, dry_run: bool, draft_to_self: bool) -> int:
    api = LeadDeskApi(cfg)
    journal = Journal(cfg.journal_path)
    alerts: list[str] = []
    counters = {"sent": 0, "drafted": 0, "failed": 0, "replies": 0,
                "bounces": 0, "ambiguous": 0}

    print("Pre-flight:")
    ready = _preflight(cfg, api, need_outlook=not dry_run)
    fails_file = cfg.home / ".consec-fails"
    if ready is None:
        _log(cfg, {"cmd": "tick", "aborted": "preflight"})
        # Two consecutive hard preflight failures deserve a human ping.
        try:
            fails = int(fails_file.read_text().strip() or "0") + 1
        except (OSError, ValueError):
            fails = 1
        fails_file.write_text(str(fails))
        if fails == 2:
            _alert(cfg, "worker cannot run",
                   "Pre-flight failed twice in a row (Outlook down, app "
                   "unreachable, or kill switch). Sends are queuing server-side.")
        return 1
    fails_file.write_text("0")
    status, ol, accounts = ready["status"], ready["ol"], ready["accounts"]

    if dry_run:
        claims = api.claim(max_items=MAX_CLAIM, peek=True)
        print("\n--dry-run (peek): due sends, nothing leased or executed:")
        print(json.dumps(claims, indent=1)[:4000])
        print(f"\nJournal pending: {len(journal.pending())}")
        _log(cfg, {"cmd": "tick", "dry_run": True,
                   "claims": len(claims.get('claims', []))})
        return 0

    # 2. replay unacked results (crash reconcile) BEFORE anything new.
    replay = sender.replay_pending(ol, accounts, journal, api, alerts)
    counters["ambiguous"] = replay["ambiguous"]

    # 3. capture replies/bounces FIRST so the server halts cadences before
    #    we claim.
    try:
        cap = capture_local.run_capture(ol, api, cfg, MAILBOXES)
        counters["replies"] = cap.get("events_posted", 0)
        print(f"capture: {cap}")
    except Exception as exc:  # noqa: BLE001 - capture failure must not block sending decisions... but it MUST block claims (stop conditions unseen)
        _alert(cfg, "capture failed - not claiming",
               f"Inbox capture failed ({exc}); claiming is skipped this tick "
               "because unseen replies could mean sending to someone who "
               "already answered.")
        _log(cfg, {"cmd": "tick", "aborted": "capture-failed", "error": str(exc)[:300]})
        return 1

    # 4. claim + execute, throttled.
    claims = api.claim(max_items=MAX_CLAIM)
    sends = claims.get("claims", [])
    print(f"claimed {len(sends)} send(s)")
    for i, send in enumerate(sends):
        outcome = sender.execute_one(ol, accounts, send, journal, api,
                                     draft_to_self=draft_to_self)
        if outcome in ("sent", "ack_pending"):
            counters["sent"] += 1
        elif outcome == "drafted":
            counters["drafted"] += 1
        else:
            counters["failed"] += 1
        print(f"  [{i + 1}/{len(sends)}] {send['to']}: {outcome}")
        if outcome == "com_error":
            _alert(cfg, "COM error inside send window",
                   f"{send['attempt_key']} to {send['to']}: crashed between "
                   ".Send() issue and confirmation. Reconcile will search "
                   "Sent Items next tick; resolve on the campaign page if "
                   "it stays ambiguous.")
        if i < len(sends) - 1:
            pause = send.get("throttle_seconds", 12) + \
                random.uniform(0, send.get("jitter_seconds", 4))
            time.sleep(pause)

    for msg in alerts:
        _alert(cfg, "ambiguous send needs a human", msg)

    # 5. heartbeat + audit log.
    try:
        api.heartbeat(counters)
    except (ApiUnavailable, ApiRejected):
        pass
    journal.compact()
    _log(cfg, {"cmd": "tick", **counters})
    print(f"tick done: {counters}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-worker")
    p.add_argument("command", choices=["tick", "status", "capture"])
    p.add_argument("--home", default=None,
                   help="state/secrets dir (default: LEAD_DESK_WORKER_HOME)")
    p.add_argument("--dry-run", action="store_true",
                   help="print everything, execute nothing")
    p.add_argument("--draft-to-self", action="store_true",
                   help="full pipeline but save into our own Drafts, no ack")
    args = p.parse_args(argv)

    cfg = load_config(args.home)
    if args.command == "status":
        return cmd_status(cfg)
    if args.command == "capture":
        return cmd_capture(cfg, args.dry_run)
    return cmd_tick(cfg, args.dry_run, args.draft_to_self)


if __name__ == "__main__":
    raise SystemExit(main())
