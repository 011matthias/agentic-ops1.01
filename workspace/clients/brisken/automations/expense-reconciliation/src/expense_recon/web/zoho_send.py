"""Send one finished month into Zoho Books from the app.

Owner decision 2026-09-28: a "Send to Zoho" button in the app, pressed by
Criss when her month is done. Until then posting was an operator-run CLI
action and the web layer held no Zoho import at all.

This is the ONE web module allowed to reach the posting package, and it
reaches it only through `zoho.reconcile_month.run_month`, the runner that
posted July and August into the TEST-BTS sandbox and read both back to the
cent. Nothing here re-derives a guard; each one still lives where it did:

* **Sandbox only.** `run_month` refuses every org but TEST-BTS
  (`assert_org`). Production stays read-only by owner ruling (2026-09-24)
  until Brisken signs off a per-org mapping in `ORG_PROFILES`.
* **A server switch.** `EXPENSE_RECON_ZOHO_POST=1` must be set on the
  server. It is checked here, so a switched-off server answers before any
  Zoho read, and again by the runner before a live run.
* **Nothing twice.** The durable ledger (`zoho-post-ledger.sqlite` under
  the data root) refuses a reference already sent, and the occupancy check
  refuses a month somebody entered by hand.
* **What is sent is what was looked at.** The preview answers a `confirm`
  value (`plan_fingerprint`); the send passes it back, and the runner
  aborts before its first write when the plan it built differs.
* **One send at a time**, per server process.

`tests/test_zoho_posting_is_gated.py` pins that no other web module
imports the posting package or reads a Zoho credential.
"""
from __future__ import annotations

import os
import threading
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path

from ..batch_period import month_from_label
from ..zoho import reconcile_month as rm

LEDGER_NAME = "zoho-post-ledger.sqlite"

_SEND_LOCK = threading.Lock()

# The runner's refusal codes, said the way Criss would say them. A code
# missing here falls back to the runner's own detail sentence.
_HELD_BACK = {
    "account_unresolved": "Its category does not match an account in Zoho.",
    "paid_through_unresolved": "The card it was paid with is not set up in Zoho.",
    "amount_unreadable": "Its amount could not be read.",
    "foreign_currency_unresolvable": "Its currency could not be worked out.",
    "currency_not_defined_in_org": "Its currency is not set up in Zoho.",
    "exchange_rate_missing": "It is in a foreign currency and has no exchange rate.",
    "already_in_ledger": "Already sent to Zoho.",
    "date_precedes_period_window": "Its date is well before this month.",
    "card_or_entity_unassigned": "The card or the company still has to be picked.",
    "conflicting_reference_dates": (
        "Two receipts share this reference number but carry different dates."
    ),
    rm.REFUSAL_BLANK_REFERENCE: "It has no reference number.",
}

_BLOCKED = {
    "ALREADY_OCCUPIED": (
        "Zoho already holds entries for this card and month that were not "
        "sent from here, most likely typed in by hand. Sending would enter "
        "them twice."
    ),
    "LOCKED_PERIOD": "This month is closed for sending; it was entered by hand.",
    "UNVERIFIABLE": (
        "Zoho could not be checked for entries already in this month, so "
        "nothing is sent. Try again in a few minutes."
    ),
}


class SendRefused(ValueError):
    """The send cannot start; the message is for the person who pressed it."""


def switched_on(environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(rm.POST_ENV) == "1"


def month_of(label: str | None) -> str | None:
    """`YYYY-MM` when the month's name says which month it is, else None."""
    ym = month_from_label(label)
    return f"{ym[0]:04d}-{ym[1]:02d}" if ym else None


def ledger_path(data_root: str | Path) -> Path:
    return Path(data_root) / LEDGER_NAME


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _held_back(run: rm.MonthRun) -> list[dict]:
    return [
        {
            "reference": r.reference,
            "reason": r.reason,
            "message": _HELD_BACK.get(r.reason, r.detail),
            "detail": r.detail,
        }
        for r in run.refusals
    ]


def _entries(run: rm.MonthRun) -> list[dict]:
    if run.send_plan is None:
        return []
    names = run.account_names
    out = []
    for p in run.send_plan.postable:
        payload = p.payload
        lines = payload.get("line_items") or [{"account_id": payload.get("account_id")}]
        out.append({
            "reference": p.reference,
            "date": payload.get("date"),
            "vendor": payload.get("vendor_name") or "",
            "amount": _money(p.total),
            "currency": payload.get("currency_code") or run.org.base_currency,
            "accounts": [
                names.get(str(li.get("account_id")), str(li.get("account_id")))
                for li in lines
            ],
        })
    return out


def _blocked_reason(run: rm.MonthRun) -> str | None:
    if not run.abort_reason:
        return None
    verdict = run.occupancy.verdict if run.occupancy is not None else ""
    return _BLOCKED.get(
        verdict,
        "Zoho could not be read, so nothing is sent. Try again in a few minutes.",
    )


def _common(run: rm.MonthRun) -> dict:
    return {
        "month": run.period,
        "company": run.org.label,
        "test_company": run.org.org_id == rm.SANDBOX_ORG_ID,
        "currency": run.org.base_currency,
    }


def preview(
    *, csv_path: Path, period: str, ledger: Path,
    environ: Mapping[str, str] | None = None,
) -> dict:
    """What pressing Send would enter, read from Zoho and posting nothing.

    `status` is `ready` (something to send), `nothing_to_send`, or
    `blocked` with a `reason`. `confirm` goes back with the send."""
    lines: list[str] = []
    try:
        run = rm.run_month(
            period=period, csv_path=csv_path, ledger_path=ledger,
            dry_run=True, environ=environ, emit=lines.append,
        )
    except (rm.RunRefused, rm.ZohoAuthError, rm.ZohoAPIError, ValueError,
            AssertionError) as exc:
        raise SendRefused(_refusal_text(exc)) from exc
    body = {
        **_common(run),
        "enabled": True,
        "count": len(run.send_plan.postable) if run.send_plan is not None else 0,
        "total": _money(run.planned_total),
        "entries": _entries(run),
        "held_back": _held_back(run),
        "already_sent": len(run.ours_in_ledger),
        "confirm": run.fingerprint,
        "reason": _blocked_reason(run),
        # The runner's own sentence behind a block, for whoever checks it.
        "detail": run.abort_reason,
    }
    if body["reason"]:
        body["status"] = "blocked"
        body["confirm"] = ""
    elif body["count"] == 0:
        body["status"] = "nothing_to_send"
    else:
        body["status"] = "ready"
    return body


def send(
    *, csv_path: Path, period: str, ledger: Path, confirm: str,
    environ: Mapping[str, str] | None = None,
) -> dict:
    """Send the confirmed plan, then read every new entry back from Zoho.

    Raises `SendRefused` when the send cannot start (switched off, another
    send running, Zoho refusing the login). Everything after the first read
    reports in the returned body, `ok` false on any problem."""
    if not switched_on(environ):
        raise SendRefused("Sending to Zoho is switched off on the server.")
    if not _SEND_LOCK.acquire(blocking=False):
        raise SendRefused("Another month is being sent right now. Try again once it finishes.")
    try:
        lines: list[str] = []
        try:
            run = rm.run_month(
                period=period, csv_path=csv_path, ledger_path=ledger,
                dry_run=False, environ=environ, emit=lines.append,
                expect_fingerprint=confirm,
            )
        except (rm.RunRefused, rm.ZohoAuthError, rm.ZohoAPIError, ValueError,
                AssertionError) as exc:
            raise SendRefused(_refusal_text(exc)) from exc
    finally:
        _SEND_LOCK.release()
    return _send_body(run, lines)


def _send_body(run: rm.MonthRun, lines: list[str]) -> dict:
    report = run.report
    posted = list(report.posted) if report is not None else []
    readback = list(run.readback)
    reason = None
    if run.abort_reason and run.abort_reason.startswith("plan changed"):
        reason = (
            "The month changed after the preview was opened. Nothing was "
            "sent; open the preview again and confirm what it shows now."
        )
    elif run.abort_reason:
        reason = _blocked_reason(run)
    elif report is not None and report.aborted:
        reason = (
            "Zoho stopped answering partway through. What was sent is listed; "
            "the rest was held back so nothing can be entered twice. It needs "
            "a check before this month is sent again."
        )
    totals_match = bool(posted) and run.stored_total == run.planned_total
    return {
        **_common(run),
        "ok": run.exit_code == 0,
        "reason": reason,
        "sent": len(posted),
        "checked_ok": sum(1 for r in readback if r.clean),
        "total_sent": _money(run.planned_total if posted else Decimal("0")),
        "total_in_zoho": _money(run.stored_total),
        "totals_match": totals_match,
        "problems": [
            {"reference": r.reference, "problems": list(r.problems)}
            for r in readback if not r.clean
        ],
        "rejected": [
            {"reference": ref, "message": msg}
            for ref, msg in (report.rejected if report is not None else ())
        ],
        "unsure": [
            {"reference": ref, "message": msg}
            for ref, msg in (report.ambiguous if report is not None else ())
        ],
        "held_back": _held_back(run),
        # The runner's own step-by-step output, for whoever checks a send
        # afterwards. The app does not show it.
        "log": lines,
    }


def _refusal_text(exc: Exception) -> str:
    if isinstance(exc, rm.ZohoAuthError):
        return "Zoho refused the app's login. The Zoho connection needs to be renewed."
    if isinstance(exc, rm.ZohoAPIError):
        return "Zoho answered with an error, so nothing was sent. Try again in a few minutes."
    if isinstance(exc, ValueError) and "credentials missing" in str(exc):
        return "The server has no Zoho login set up, so nothing can be sent."
    if isinstance(exc, AssertionError):
        return "The send was stopped by a safety check before anything reached Zoho."
    return str(exc)
