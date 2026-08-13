"""Arming-drill CLI: the codified half of ARMING-DRILL.md (the runbook at
the lead-desk root). Steps 1-4 wrap the same engine plumbing the armed
worker runs, so the drill rehearses the real code paths; ``step4-verify``
and ``status`` are read-only checks. Runbook steps 5-7 are human-verified
on purpose (judgment calls plus the owner-present arm), so they have no
subcommand.

Safety model (rule_brisken_graph_send_by_id, send only explicit targets):
the two commands that SEND (step3, step4) take an explicit ``--to`` and
REFUSE, with a hard exit and no Graph call, any address that

* resolves to an existing contact (``store.find_by_email``) - a drill send
  must never reach a real prospect, whatever was typed;
* is not the sanctioned target for that step: step3 sends ONLY
  matthias -> matthias (``--to`` must equal SEND_FROM); step4 sends ONLY
  to the explicitly passed NDR address and refuses the deny-floor domains.

step4 then registers a namespaced ``drill-ndr-*`` contact for its address
(the refusal check above admits only our own prior drill contact), because
the NDR -> bounce -> auto-suppress path being rehearsed is contact-matched:
capture keys the bounce on the failed recipient and the sink suppresses
that CONTACT. Without the drill contact the bounce would park in the
unmatched queue instead of rehearsing the suppress.

Import-safe without creds (guarded like cloud_worker.main): the Graph
mailer is built only inside a command, after the guards pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import cloud_worker
from .graph_mail import DEFAULT_DENY_DOMAINS, SEND_FROM, GraphMailer
from .sync import have_creds
from .web.service import now_iso
from .web.store import ContactStore

DRILL_SUBJECT_PREFIX = "LEAD DESK ARMING DRILL"
DRILL_CONTACT_PREFIX = "drill-ndr-"


def _open_store(data_dir: str | Path) -> ContactStore:
    return ContactStore(Path(data_dir) / "lead-desk.sqlite")


def _refuse(msg: str) -> int:
    print(f"REFUSED: {msg}")
    return 2


def _verdict(step: str, checks: dict[str, bool]) -> int:
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if all(checks.values()):
        print(f"PASS {step}")
        return 0
    print(f"FAIL {step}")
    return 1


def _leased_count(store: ContactStore) -> int:
    return store.conn.execute(
        "SELECT COUNT(*) FROM send_attempts WHERE status = 'leased'"
    ).fetchone()[0]


def _drill_contact_id(addr: str) -> str:
    return DRILL_CONTACT_PREFIX + hashlib.sha1(
        addr.encode("utf-8")).hexdigest()[:10]


def _age_minutes(ts: str | None, at: datetime) -> float | None:
    if not ts:
        return None
    try:
        then = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return round((at - then).total_seconds() / 60, 1)


# -- steps --------------------------------------------------------------------

def step1(data_dir: str | Path) -> int:
    """Dry-run tick (peek): prove the dormant engine is inert. Checks the
    machine-checkable pass criteria (kill switch reported true, zero leases
    taken, watermarks untouched); the due_preview is printed for the human
    to match against expectation (empty while dormant)."""
    data_dir = Path(data_dir)
    state_path = cloud_worker._capture_state_path(data_dir)

    def watermarks() -> str | None:
        try:
            return state_path.read_text(encoding="utf-8")
        except OSError:
            return None

    marks_before = watermarks()
    with _open_store(data_dir) as store:
        leased_before = _leased_count(store)
    report = cloud_worker.run_tick(data_dir, dry_run=True)
    print(json.dumps(report, indent=1, default=str))
    with _open_store(data_dir) as store:
        leased_after = _leased_count(store)
    return _verdict("step1", {
        "kill_switch_reported_true": report.get("kill_switch") is True,
        "zero_leases_taken": leased_after == leased_before,
        "watermarks_unchanged": watermarks() == marks_before,
    })


def step2(data_dir: str | Path) -> int:
    """Draft-to-self tick: the full pipeline (claim -> render -> Graph),
    with every mail landing as a draft in OUR mailbox and nothing acked.
    Needs a claimable send: drill campaign in 'sending' plus the scoped
    kill lift from ARMING-DRILL.md step 2."""
    report = cloud_worker.run_tick(Path(data_dir), draft_to_self=True)
    print(json.dumps(report, indent=1, default=str))
    claimed = report.get("claimed", 0)
    if not claimed:
        print("NOTE: nothing was claimed (kill switch on, or no campaign in "
              "status 'sending'), so nothing was drafted. See ARMING-DRILL.md "
              "step 2 for the scoped kill lift.")
    counters = report.get("counters") or {}
    print("Now inspect the staged draft(s) in the matthias Drafts folder: "
          "rendered copy, recipient, and for a reply-step campaign the RE: "
          "threading on the real anchor conversation.")
    return _verdict("step2", {
        "claimed_at_least_one": claimed > 0,
        "nothing_sent_or_acked": counters.get("sent", 0) == 0
        and counters.get("drafted", 0) == 0,
    })


def step3(data_dir: str | Path, to: str, mailer=None) -> int:
    """One live self-send matthias -> matthias through the engine's Graph
    send path (send_auto + Sent Items readback), with a timestamped drill
    subject. PASS = the readback finds the mail and reports its imid."""
    to_n = (to or "").strip().lower()
    if to_n != SEND_FROM:
        return _refuse(
            f"step3 sends only {SEND_FROM} -> {SEND_FROM}; got --to {to!r}")
    with _open_store(data_dir) as store:
        hit = store.find_by_email(to_n)
        if hit is not None:
            return _refuse(
                f"{to_n} resolves to contact {hit['contact_id']!r}; a drill "
                "send never targets a contacts-table address")
    if mailer is None:
        mailer = GraphMailer()
    at = datetime.now(timezone.utc)
    subject = f"{DRILL_SUBJECT_PREFIX} step3 {at:%Y-%m-%d %H:%M:%S}Z"
    mailer.send_auto({
        "from": SEND_FROM, "to": to_n, "subject": subject,
        "body": "Arming drill step 3: live self-send through the Graph "
                "engine path. See ARMING-DRILL.md."})
    print(f"sent {subject!r} -> {to_n}; reading back Sent Items...")
    evidence = mailer.readback_sent(SEND_FROM, to_n, subject,
                                    at - timedelta(minutes=2))
    imid = (evidence or {}).get("imid")
    if imid:
        print(f"  imid: {imid}")
    return _verdict("step3", {"sent_items_readback_found_imid": bool(imid)})


def step4(data_dir: str | Path, to: str, mailer=None) -> int:
    """Send one drill mail to the chosen invalid address so the NDR ->
    bounce -> auto-suppress path can be verified (step4-verify). Refuses
    any known contact and the deny-floor domains, then registers the
    namespaced drill contact the captured bounce will match."""
    to_n = (to or "").strip().lower()
    if not to_n or "@" not in to_n:
        return _refuse(f"--to must be an email address; got {to!r}")
    if to_n.rsplit("@", 1)[-1] in set(DEFAULT_DENY_DOMAINS):
        return _refuse(
            f"{to_n} is on the deny floor {DEFAULT_DENY_DOMAINS}; pick a "
            "nonexistent user at another real domain")
    drill_cid = _drill_contact_id(to_n)
    with _open_store(data_dir) as store:
        hit = store.find_by_email(to_n)
        if hit is not None and hit["contact_id"] != drill_cid:
            return _refuse(
                f"{to_n} resolves to contact {hit['contact_id']!r}; the NDR "
                "drill address must not be a known contact")
        if hit is None:
            store.upsert_contact(
                {"contact_id": drill_cid, "natural_key": drill_cid,
                 "campaign": "drill", "first_name": "DRILL",
                 "last_name": "NDR", "company": "DRILL", "email": to_n},
                now_iso())
            print(f"registered drill contact {drill_cid} for {to_n}")
    if mailer is None:
        mailer = GraphMailer()
    at = datetime.now(timezone.utc)
    subject = f"{DRILL_SUBJECT_PREFIX} step4 {at:%Y-%m-%d %H:%M:%S}Z"
    mailer.send_auto({
        "from": SEND_FROM, "to": to_n, "subject": subject,
        "body": "Arming drill step 4: NDR probe to a nonexistent address. "
                "See ARMING-DRILL.md."})
    print(f"sent {subject!r} -> {to_n}")
    print("Now wait for the NDR to be captured (<= 2 capture ticks, ~30 min; "
          "this command cannot wait that out), then run:\n"
          f"  lead-desk-drill step4-verify --to {to_n}")
    return 0


def step4_verify(data_dir: str | Path, to: str) -> int:
    """Read-only follow-up to step4: did the NDR land as a bounce event,
    and did the sink auto-suppress the drill contact (reason=bounced)?"""
    to_n = (to or "").strip().lower()
    with _open_store(data_dir) as store:
        row = store.find_by_email(to_n)
        if row is None:
            parked = [u for u in store.list_unmatched("open")
                      if (u["email"] or "").lower() == to_n]
            print(f"FAIL step4-verify: no contact for {to_n} ({len(parked)} "
                  "open unmatched event(s) for it; run step4 first - it "
                  "registers the drill contact the bounce must match)")
            return 1
        bounces = [e for e in store.get_events(row["contact_id"])
                   if e["type"] == "bounce"]
    if bounces:
        print(f"  bounce at {bounces[0]['ts']}: {bounces[0]['subject']!r}")
    return _verdict("step4-verify", {
        "bounce_event_recorded": bool(bounces),
        "auto_suppressed_reason_bounced":
            bool(row["suppressed"]) and row["suppress_reason"] == "bounced",
    })


# -- readiness audit ----------------------------------------------------------

def status_report(data_dir: str | Path, at: datetime | None = None) -> dict:
    """The readiness audit read before any kill lift and at step 7: kill
    switch, guard alerts, attempt counts, capture watermark age, heartbeat
    age, campaigns currently in 'sending'. Read-only; no creds needed."""
    data_dir = Path(data_dir)
    at = at or datetime.now(timezone.utc)
    out: dict = {"at": at.isoformat(timespec="seconds")}
    with _open_store(data_dir) as store:
        out["kill_switch"] = (store.get_state("kill_switch") or "0") == "1"
        alerts: dict[str, dict] = {}
        for key in store.state_keys_with_prefix("send_guard_alert:"):
            raw = store.get_state(key) or "{}"
            try:
                alerts[key.split(":", 1)[1]] = json.loads(raw)
            except json.JSONDecodeError:
                alerts[key.split(":", 1)[1]] = {"raw": raw}
        out["guard_alerts"] = alerts
        counts = {r["status"]: r["n"] for r in store.conn.execute(
            "SELECT status, COUNT(*) AS n FROM send_attempts GROUP BY status")}
        out["attempts"] = counts
        out["drafted"] = counts.get("drafted", 0)
        out["parked"] = counts.get("parked", 0)
        out["sending_campaigns"] = [
            r["campaign_id"] for r in store.list_campaigns()
            if r["status"] == "sending"]
        heartbeat: dict = {}
        raw = store.get_state("worker_heartbeat")
        if raw:
            try:
                heartbeat = json.loads(raw)
            except json.JSONDecodeError:
                heartbeat = {}
        out["heartbeat_age_minutes"] = _age_minutes(heartbeat.get("ts"), at)
    try:
        marks = (json.loads(cloud_worker._capture_state_path(data_dir)
                            .read_text(encoding="utf-8"))
                 .get("watermarks") or {})
    except (OSError, json.JSONDecodeError):
        marks = {}
    ages = {mbx: _age_minutes(ts, at) for mbx, ts in marks.items()}
    out["capture_watermark_ages_minutes"] = ages
    known = [a for a in ages.values() if a is not None]
    out["capture_watermark_age_minutes"] = max(known) if known else None
    return out


def status(data_dir: str | Path) -> int:
    print(json.dumps(status_report(data_dir), indent=1, default=str))
    return 0


# -- CLI ----------------------------------------------------------------------

_GRAPH_STEPS = ("step1", "step2", "step3", "step4")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="lead-desk-drill",
        description="Guided arming-drill steps (see ARMING-DRILL.md; steps "
                    "5-7 are human-verified and have no subcommand)")
    p.add_argument("--data",
                   default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("step1", help="dry-run tick: dormant engine is inert")
    sub.add_parser("step2",
                   help="draft-to-self tick: pipeline drafts into our mailbox")
    s3 = sub.add_parser("step3", help="one live self-send matthias -> matthias")
    s3.add_argument("--to", required=True)
    s4 = sub.add_parser("step4", help="NDR probe to the chosen invalid address")
    s4.add_argument("--to", required=True)
    s4v = sub.add_parser("step4-verify",
                         help="check bounce event + auto-suppression")
    s4v.add_argument("--to", required=True)
    sub.add_parser("status", help="readiness audit (read-only)")
    args = p.parse_args(argv)

    if args.cmd in _GRAPH_STEPS and not have_creds():
        print("ERROR: BRISKEN_GRAPH_* credentials not configured")
        return 2

    data = Path(args.data)
    if args.cmd == "step1":
        return step1(data)
    if args.cmd == "step2":
        return step2(data)
    if args.cmd == "step3":
        return step3(data, args.to)
    if args.cmd == "step4":
        return step4(data, args.to)
    if args.cmd == "step4-verify":
        return step4_verify(data, args.to)
    return status(data)


if __name__ == "__main__":
    raise SystemExit(main())
