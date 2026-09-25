"""Which of a month's receiptless charges Zoho already holds (front 1 step 5).

The hosted app never reads Zoho (`tests/test_zoho_posting_is_gated.py`), so
its only "already booked" signals are Criss's workbook fills and a reviewer's
click. Measured 2026-09-25: Zoho already held 11 (August) and 15 (September)
of the charges the app calls open, and August's 45 gray "booked through
recurring" rows had a Zoho expense for 2. This command answers both halves
from the command line, read-only:

* **held**: open charges (no receipt, no closing verdict) that a Zoho expense
  in the charge's own company matches, with the Zoho expense id, so Criss can
  mark them already booked in the app herself;
* **not_found**: charges the app closed on a colour or a mark (yellow, the
  reviewer's already-booked, gray) that no Zoho expense matches.

A match is the same company (the charge's entity mapped to its org through
`settings.account_companies`), the same currency, the same amount to the cent
and a date within `MATCH_DAYS` days. Each Zoho expense settles one charge at
most (closest date first), so two same-amount subscriptions cannot both claim
one entry.

**The join proves it can see.** Every run also scores a control: the same
join with every charge moved by one cent. A join that finds as many pairs for
the shifted amounts as for the real ones is not discriminating anything, and
the report says so instead of printing the pairs as findings
(`rule_behaviors` instrument-validity sub-clause).

It writes nothing anywhere but the CSV it is asked for: Zoho is read with
`list_expenses` (GET), the app with GET. Marking a charge booked from this
report is Criss's click (or an owner-approved write), never this command's.

    python -m expense_recon.zoho.booked_report --run-payload run.json \\
        --settings settings.json --zoho-pull zoho-expenses.json --csv out.csv
    python -m expense_recon.zoho.booked_report --run-id 074a7b8905d7 \\
        --month 2026-08 --env-file context/.env --csv out.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.request
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..web.month_readiness import (
    charge_booked_recurring,
    charge_needs_receipt,
    charge_no_receipt_expected,
)

MATCH_DAYS = 3
# The Zoho read window beyond the charges' own first and last date.
PULL_MARGIN_DAYS = 10
DEFAULT_BASE_URL = "https://brisken-expense-recon.fly.dev"

OPEN = "open"
YELLOW = "yellow"
REVIEWER_BOOKED = "reviewer_booked"
GRAY = "gray"
NO_RECEIPT_EXPECTED = "no_receipt_expected"
CLOSED_STATES = (YELLOW, REVIEWER_BOOKED, GRAY, NO_RECEIPT_EXPECTED)


class ReportError(Exception):
    """An input the report cannot run on; the CLI prints it and exits 2."""


def _amount(text: object) -> Decimal | None:
    try:
        return abs(Decimal(str(text).replace(",", "").strip()))
    except (InvalidOperation, ValueError):
        return None


def _date(text: object) -> date | None:
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def org_of_entity(settings: dict) -> dict[str, str]:
    """Every spelling of a company (`account_companies[].label` and its
    `labels`) to its Zoho org id."""
    out: dict[str, str] = {}
    for company in settings.get("account_companies") or []:
        org = str(company.get("org_id") or "")
        if not org:
            continue
        for label in [company.get("label"), *(company.get("labels") or [])]:
            if label:
                out[str(label)] = org
    return out


def charge_state(row: dict) -> str | None:
    """Where one receiptless purchase stands, by the month gate's own
    predicates; None for anything else (a matched charge, a credit, a fee)."""
    if row.get("effective_bucket") != "unmatched":
        return None
    if (row.get("row_type") or "purchase") != "purchase":
        return None
    if charge_needs_receipt(row):
        return OPEN
    if row.get("section") == "posted":
        return YELLOW if row.get("entry_status") == "posted" else REVIEWER_BOOKED
    if charge_booked_recurring(row):
        return GRAY
    if charge_no_receipt_expected(row):
        return NO_RECEIPT_EXPECTED
    return None


def join(
    rows: list[dict],
    zoho_orgs: dict[str, list[dict]],
    org_of: dict[str, str],
    *,
    days: int = MATCH_DAYS,
    cent_shift: Decimal = Decimal("0"),
) -> list[dict]:
    """One result per receiptless purchase: its state, its org, and the
    Zoho expense that matches it (or None). Greedy by date distance so each
    Zoho expense settles one charge at most."""
    charges = []
    for row in rows:
        state = charge_state(row)
        amount = _amount(row.get("amount"))
        if state is None or amount is None:
            continue
        charges.append({
            "row": row, "state": state,
            "org": org_of.get(str(row.get("legal_entity_id") or ""), ""),
            "amount": amount + cent_shift, "date": _date(row.get("date")),
            "currency": str(row.get("currency") or "").upper(),
        })
    pairs = []
    for i, ch in enumerate(charges):
        if not ch["org"] or ch["date"] is None:
            continue
        for exp in zoho_orgs.get(ch["org"]) or []:
            exp_date = _date(exp.get("date"))
            exp_amount = _amount(exp.get("total"))
            if exp_date is None or exp_amount is None:
                continue
            gap = abs((exp_date - ch["date"]).days)
            if (
                gap <= days
                and exp_amount == ch["amount"]
                and str(exp.get("currency_code") or "").upper() == ch["currency"]
            ):
                pairs.append((gap, i, str(exp.get("expense_id") or ""), exp))
    pairs.sort(key=lambda p: (p[0], p[1], p[2]))
    taken_charge: dict[int, dict] = {}
    taken_exp: set[str] = set()
    for _gap, i, exp_id, exp in pairs:
        if i in taken_charge or exp_id in taken_exp:
            continue
        taken_charge[i] = exp
        taken_exp.add(exp_id)
    out = []
    for i, ch in enumerate(charges):
        exp = taken_charge.get(i)
        row = ch["row"]
        out.append({
            "transaction_id": row.get("transaction_id") or "",
            "date": row.get("date") or "",
            "vendor": row.get("vendor") or "",
            "amount": row.get("amount") or "",
            "currency": ch["currency"],
            "company": row.get("legal_entity_id") or "",
            "org_id": ch["org"],
            "state": ch["state"],
            "zoho_expense_id": str(exp.get("expense_id") or "") if exp else "",
            "zoho_date": str(exp.get("date") or "") if exp else "",
            "zoho_vendor": str(exp.get("vendor_name") or exp.get("description") or "") if exp else "",
            "zoho_account": str(exp.get("account_name") or "") if exp else "",
            "zoho_paid_through": str(exp.get("paid_through_account_name") or "") if exp else "",
        })
    return out


def build_report(rows: list[dict], zoho_orgs: dict[str, list[dict]], org_of: dict[str, str]) -> dict:
    """The two lists, their counts, and the one-cent control."""
    results = join(rows, zoho_orgs, org_of)
    control = join(rows, zoho_orgs, org_of, cent_shift=Decimal("0.01"))
    held = [r for r in results if r["state"] == OPEN and r["zoho_expense_id"]]
    not_found = [r for r in results if r["state"] in CLOSED_STATES and not r["zoho_expense_id"]]
    n_matched = sum(1 for r in results if r["zoho_expense_id"])
    n_control = sum(1 for r in control if r["zoho_expense_id"])
    by_state: dict[str, dict[str, int]] = {}
    for r in results:
        s = by_state.setdefault(r["state"], {"charges": 0, "in_zoho": 0})
        s["charges"] += 1
        s["in_zoho"] += bool(r["zoho_expense_id"])
    return {
        "n_zoho_expenses": {org: len(v or []) for org, v in sorted(zoho_orgs.items())},
        "by_state": by_state,
        "n_matched": n_matched,
        "n_matched_control": n_control,
        # The join discriminates when the shifted amounts find (almost)
        # nothing: the control is the count a blind join would also print.
        "discriminates": n_matched > 0 and n_control * 4 <= n_matched,
        "no_company": sum(1 for r in results if not r["org_id"]),
        "held": held,
        "not_found": not_found,
    }


CSV_FIELDS = (
    "list", "transaction_id", "date", "vendor", "amount", "currency", "company",
    "state", "zoho_expense_id", "zoho_date", "zoho_vendor", "zoho_account",
    "zoho_paid_through",
)


def write_csv(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for name in ("held", "not_found"):
            for r in report[name]:
                writer.writerow({"list": name, **r})


def render(report: dict, *, label: str) -> str:
    lines = [f"Zoho already-booked report: {label}", ""]
    lines.append("Zoho expenses read per org: " + ", ".join(
        f"{org} {n}" for org, n in report["n_zoho_expenses"].items()))
    lines.append(
        f"Join: {report['n_matched']} charges matched; the same join with every "
        f"amount moved one cent matched {report['n_matched_control']}."
    )
    if not report["discriminates"]:
        lines.append(
            "WARNING: the control matched too many (or nothing matched at all); "
            "do not read the lists below as findings."
        )
    if report["no_company"]:
        lines.append(f"{report['no_company']} charges carry no company the settings map to an org.")
    lines.append("")
    for state, c in sorted(report["by_state"].items()):
        lines.append(f"  {state:20s} {c['charges']:4d} charges, {c['in_zoho']:4d} in Zoho")
    lines += ["", f"Open charges Zoho already holds ({len(report['held'])}):"]
    for r in report["held"]:
        lines.append(
            f"  {r['date']}  {r['vendor'][:32]:32s} {r['currency']} {r['amount']:>10s}  "
            f"{r['company']}  -> Zoho {r['zoho_expense_id']} ({r['zoho_date']}, {r['zoho_vendor'][:28]})"
        )
    lines += ["", f"Charges closed by a colour or a mark that Zoho does not hold ({len(report['not_found'])}):"]
    for r in report["not_found"]:
        lines.append(
            f"  {r['date']}  {r['vendor'][:32]:32s} {r['currency']} {r['amount']:>10s}  "
            f"{r['company']}  [{r['state']}]"
        )
    return "\n".join(lines) + "\n"


# ── inputs ──────────────────────────────────────────────────────────────


def _load_env_file(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _api_get(base_url: str, token: str | None, path: str, body: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        base_url.rstrip("/") + path, data=data, headers=headers,
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - fixed https host
        return json.loads(resp.read().decode("utf-8"))


def fetch_month(base_url: str, run_id: str) -> tuple[dict, dict]:
    """(run payload, settings) read from the app with GET only; the login
    is the one POST, and it writes nothing."""
    code = os.environ.get("EXPENSE_RECON_OPERATOR_CODE", "").strip()
    if not code:
        raise ReportError("EXPENSE_RECON_OPERATOR_CODE is not set (pass --env-file)")
    token = _api_get(base_url, None, "/api/login", {"code": code}).get("token")
    if not token:
        raise ReportError("the app's login returned no token")
    return (
        _api_get(base_url, token, f"/api/runs/{run_id}"),
        _api_get(base_url, token, "/api/settings"),
    )


def pull_zoho(org_ids: list[str], rows: list[dict]) -> dict[str, list[dict]]:
    """Every expense of each org dated around the charges, read-only
    (`ZohoClient.list_expenses`: GET, Status.All by Zoho's default)."""
    from .client import ZohoClient, zoho_config_from_env

    dates = sorted(d for d in (_date(r.get("date")) for r in rows) if d)
    if not dates:
        raise ReportError("the month holds no dated charge")
    start = str(dates[0] - timedelta(days=PULL_MARGIN_DAYS))
    end = str(dates[-1] + timedelta(days=PULL_MARGIN_DAYS))
    return {
        org: ZohoClient(zoho_config_from_env(org)).list_expenses(
            date_start=start, date_end=end)
        for org in org_ids
    }


def _zoho_from_file(path: Path) -> dict[str, list[dict]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    orgs = raw.get("orgs") if isinstance(raw, dict) else None
    if not isinstance(orgs, dict):
        raise ReportError(f"{path} is not a Zoho pull ({{'orgs': {{org: {{'expenses': [...]}}}}}})")
    return {
        str(org): (v.get("expenses") if isinstance(v, dict) else v) or []
        for org, v in orgs.items()
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run-id", help="the month's run id, read from the app with GET")
    ap.add_argument("--month", default="", help="YYYY-MM, labels the report and the CSV")
    ap.add_argument("--run-payload", type=Path, help="a saved GET /api/runs/{id} payload instead")
    ap.add_argument("--settings", type=Path, help="a saved GET /api/settings payload instead")
    ap.add_argument("--zoho-pull", type=Path, help="a saved Zoho pull instead of a live read")
    ap.add_argument("--env-file", type=Path, help="KEY=VALUE file with the app code and the Books token")
    ap.add_argument("--base-url", default=os.environ.get("EXPENSE_RECON_BASE_URL", DEFAULT_BASE_URL))
    ap.add_argument("--csv", type=Path, help="write both lists here")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        if args.env_file is not None:
            _load_env_file(args.env_file)
        if args.run_payload is not None:
            run = json.loads(args.run_payload.read_text(encoding="utf-8"))
            if args.settings is None:
                raise ReportError("--run-payload needs --settings (the company-to-org map)")
            settings = json.loads(args.settings.read_text(encoding="utf-8"))
        elif args.run_id:
            run, settings = fetch_month(args.base_url, args.run_id)
        else:
            raise ReportError("name the month: --run-id, or --run-payload with --settings")
        rows = run.get("rows") or []
        org_of = org_of_entity(settings)
        if not org_of:
            raise ReportError("settings carry no account_companies with an org id")
        zoho = (
            _zoho_from_file(args.zoho_pull) if args.zoho_pull is not None
            else pull_zoho(sorted(set(org_of.values())), rows)
        )
        report = build_report(rows, zoho, org_of)
    except (ReportError, OSError, ValueError) as exc:
        print(f"booked_report: {exc}", file=sys.stderr)
        return 2
    label = " ".join(p for p in (args.month, str(run.get("label") or ""), str(run.get("run_id") or "")) if p)
    sys.stdout.write(render(report, label=label))
    if args.csv is not None:
        write_csv(report, args.csv)
        print(f"wrote {args.csv}")
    return 0 if report["discriminates"] or not report["n_matched"] else 3


if __name__ == "__main__":
    sys.exit(main())
