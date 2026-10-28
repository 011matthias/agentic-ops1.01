"""Front 1 step 5: which receiptless charges Zoho already holds, read-only.

Through the command's own `main()` on saved payloads (the CLI is the caller;
no network, no Zoho): an open charge Zoho holds is listed with its expense
id, a gray / yellow charge Zoho does not hold is listed as not found, the
company, currency, cent and three-day window all narrow the join, one Zoho
expense settles one charge, and the one-cent control reads zero.
"""
from __future__ import annotations

import csv
import json

from expense_recon.zoho import booked_report as br

SETTINGS = {"account_companies": [
    {"label": "Cloud Services", "org_id": "111",
     "labels": ["Brisken Cloud Services, LLC", "Cloud Services"]},
    {"label": "Corporate Services", "org_id": "333",
     "labels": ["Brisken Corp Services, LLC", "Corporate Services"]},
]}


def _row(tid, d, vendor, amount, entity="Cloud Services", **kw):
    row = {
        "transaction_id": tid, "date": d, "vendor": vendor, "amount": amount,
        "currency": "USD", "legal_entity_id": entity,
        "effective_bucket": "unmatched", "row_type": "purchase",
        "section": "noreceipt", "entry_status": None,
    }
    row.update(kw)
    return row


def _exp(eid, d, total, currency="USD", vendor="Vendor"):
    return {"expense_id": eid, "date": d, "total": total, "currency_code": currency,
            "vendor_name": vendor, "account_name": "Software", "paid_through_account_name": "Chase 9693"}


ROWS = [
    _row("open_held", "2026-08-16", "OPENAI OPENAI.COM", "80.44"),
    _row("open_other_company", "2026-08-16", "GITHUB", "433.00", entity="Corporate Services"),
    _row("open_wrong_ccy", "2026-08-16", "HOSTINGER", "50.00"),
    _row("open_far", "2026-08-01", "DIGITALOCEAN", "13.02"),
    _row("open_twin_a", "2026-08-20", "ANTHROPIC", "20.00"),
    _row("open_twin_b", "2026-08-21", "ANTHROPIC", "20.00"),
    _row("gray", "2026-08-03", "BLOOMBERG", "39.99", entry_status="subscription"),
    _row("gray_booked", "2026-08-04", "SLACK", "8.75", entry_status="subscription"),
    _row("yellow", "2026-08-05", "SAP", "481.07", section="posted", entry_status="posted"),
    _row("payment", "2026-08-06", "PAYMENT THANK YOU", "-500.00", row_type="payment",
         section="posted", entry_status="posted"),
    _row("matched", "2026-08-07", "LOVABLE", "15.00", effective_bucket="reconciled", section="matched"),
]
ZOHO = {
    "111": [
        _exp("Z1", "2026-08-17", 80.44, vendor="Open AI"),
        _exp("Z3", "2026-08-16", 50.00, currency="EUR"),
        _exp("Z4", "2026-08-09", 13.02),
        _exp("Z5", "2026-08-21", 20.00, vendor="Anthropic"),
        _exp("Z6", "2026-08-04", 8.75, vendor="Slack"),
    ],
    # GITHUB's twin sits in ANOTHER company's org: not this charge's booking.
    "999": [_exp("Z2", "2026-08-16", 433.00)],
}


def _run(tmp_path, rows=ROWS, zoho=ZOHO):
    run_p = tmp_path / "run.json"
    run_p.write_text(json.dumps({"run_id": "aug", "label": "August 2026", "rows": rows}))
    set_p = tmp_path / "settings.json"
    set_p.write_text(json.dumps(SETTINGS))
    z_p = tmp_path / "zoho.json"
    z_p.write_text(json.dumps({"orgs": {k: {"expenses": v} for k, v in zoho.items()}}))
    out = tmp_path / "out.csv"
    code = br.main([
        "--run-payload", str(run_p), "--settings", str(set_p),
        "--zoho-pull", str(z_p), "--month", "2026-08", "--csv", str(out),
    ])
    with out.open(encoding="utf-8") as fh:
        return code, list(csv.DictReader(fh))


def test_the_report_lists_held_open_charges_and_unbooked_closed_ones(tmp_path, capsys):
    code, rows = _run(tmp_path)
    assert code == 0
    held = {r["transaction_id"]: r["zoho_expense_id"] for r in rows if r["list"] == "held"}
    # company, currency, cent and the 3-day window each keep a charge out;
    # of the two same-amount ANTHROPIC charges, the closer date takes Z5.
    assert held == {"open_held": "Z1", "open_twin_b": "Z5"}
    not_found = {r["transaction_id"]: r["state"] for r in rows if r["list"] == "not_found"}
    assert not_found == {"gray": "gray", "yellow": "yellow"}
    printed = capsys.readouterr().out
    assert "moved one cent matched 0" in printed
    assert "WARNING" not in printed


def test_one_zoho_expense_settles_one_charge(tmp_path):
    report = br.build_report(ROWS, ZOHO, br.org_of_entity(SETTINGS))
    ids = [r["zoho_expense_id"] for r in br.join(ROWS, ZOHO, br.org_of_entity(SETTINGS)) if r["zoho_expense_id"]]
    assert len(ids) == len(set(ids)) == report["n_matched"] == 3


def test_a_blind_join_is_reported_as_blind(tmp_path, capsys):
    # Every Zoho expense matches its charge AND its one-cent shift: the
    # control cannot tell them apart, so the report refuses to call the
    # pairs findings.
    rows = [_row("a", "2026-08-16", "X", "10.00"), _row("b", "2026-08-16", "Y", "10.01")]
    zoho = {"111": [_exp("Z1", "2026-08-16", 10.00), _exp("Z2", "2026-08-16", 10.01),
                    _exp("Z3", "2026-08-16", 10.02)]}
    code, _ = _run(tmp_path, rows, zoho)
    assert code == 3
    assert "WARNING" in capsys.readouterr().out


def test_a_missing_input_is_refused_not_guessed(tmp_path, capsys):
    assert br.main(["--month", "2026-08"]) == 2
    assert "name the month" in capsys.readouterr().err
