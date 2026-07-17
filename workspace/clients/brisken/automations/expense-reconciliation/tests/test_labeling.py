"""labeling.py: evidence tiers, AUTO uniqueness, and the propose->accept->check
CLI flow (the ground-truth fixture builder for matcher calibration)."""
from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from expense_recon.cli import main as cli_main
from expense_recon.labeling import (
    auto_pairs,
    build_candidates,
    evidence_for,
)
from expense_recon.matching.types import Receipt, Transaction


def _tx(tx_id="tx-1", amount="100.00", currency="USD", day=10,
        vendor="ACME NYC", raw="", original=None, original_currency=None):
    return Transaction(
        transaction_id=tx_id,
        legal_entity_id="le-1",
        account_id="card-1",
        transaction_date=date(2026, 4, day),
        posting_date=date(2026, 4, min(day + 1, 28)),
        amount=Decimal(amount),
        transaction_currency=currency,
        account_card_currency="USD",
        vendor_from_statement=vendor,
        raw_text=raw,
        original_amount=Decimal(original) if original else None,
        original_currency=original_currency,
    )


def _receipt(doc_id="r-1", total="100.00", currency="USD", day=10,
             vendor="Acme", reference=None, base_amount=None):
    return Receipt(
        document_id=doc_id,
        legal_entity_id="le-1",
        detected_date=date(2026, 4, day) if day else None,
        detected_total=Decimal(total) if total else None,
        detected_currency=currency,
        detected_vendor=vendor,
        detected_reference=reference,
        base_amount=Decimal(base_amount) if base_amount else None,
    )


# --------------------------------------------------------------- evidence --

def test_e2_same_currency_exact_amount():
    ev = evidence_for(_tx(), _receipt())
    assert "E2:amount-exact" in ev


def test_e1_original_amount_beats_fx_gap():
    # USD card charge for a BRL purchase: statement FX detail pairs the
    # original BRL amount with the BRL receipt; USD amounts never touch.
    tx = _tx(amount="581.51", original="3099.99", original_currency="BRL")
    r = _receipt(total="3099.99", currency="BRL")
    ev = evidence_for(tx, r)
    assert "E1:original-amount" in ev
    assert "E2:amount-exact" not in ev


def test_e3_base_amount_within_tolerance_is_not_conclusive():
    tx = _tx(amount="581.51")
    r = _receipt(total="3099.99", currency="BRL", base_amount="580.00")
    ev = evidence_for(tx, r)
    assert ev == ("E3:base-amount",)
    cands = build_candidates([tx], [r])
    assert auto_pairs(cands) == {}  # E3 alone never AUTO


def test_e4_reference_hit_normalized():
    tx = _tx(raw="CARTAO 04-260G COMPRA")
    r = _receipt(total="55.55", reference="04260G")
    assert "E4:ref" in evidence_for(tx, r)


def test_date_window_excludes_far_candidates():
    assert evidence_for(_tx(day=1), _receipt(day=28)) == ()


def test_dateless_receipt_still_candidates_on_amount():
    assert "E2:amount-exact" in evidence_for(_tx(), _receipt(day=None))


# --------------------------------------------------- AUTO uniqueness rule --

def test_auto_requires_mutual_uniqueness():
    # Two identical coffee charges + one receipt: conclusive but contested
    # from the tx side is fine (one receipt, one winner? No: the receipt has
    # TWO conclusive candidates) -> PICK. And two receipts claiming one tx
    # also demote each other.
    tx_a, tx_b = _tx("tx-a", day=10), _tx("tx-b", day=11)
    r = _receipt("r-1")
    cands = build_candidates([tx_a, tx_b], [r])
    assert auto_pairs(cands) == {}  # two conclusive candidates -> PICK

    r1, r2 = _receipt("r-1"), _receipt("r-2")
    cands = build_candidates([_tx("tx-a")], [r1, r2])
    assert auto_pairs(cands) == {}  # one tx claimed by two receipts -> PICK


def test_auto_on_clean_unique_pair():
    cands = build_candidates(
        [_tx("tx-a"), _tx("tx-b", amount="42.00", day=20)],
        [_receipt("r-1"), _receipt("r-2", total="42.00", day=20)],
    )
    assert auto_pairs(cands) == {"r-1": "tx-a", "r-2": "tx-b"}


# ------------------------------------------------------------ CLI E2E flow --

def _write_bundle(tmp_path: Path) -> Path:
    (tmp_path / "statement.csv").write_text(
        "Transaction Date,Post Date,Description,Amount\n"
        "04/10/2026,04/11/2026,ACME NYC,100.00\n"
        "04/20/2026,04/21/2026,OTHER SHOP,42.00\n"
        "04/22/2026,04/23/2026,MYSTERY VENDOR,77.77\n",
        encoding="utf-8",
    )
    (tmp_path / "receipts.csv").write_text(
        "document_id,detected_date,detected_total,detected_currency,"
        "detected_vendor,detected_reference\n"
        "r-1,2026-04-10,100.00,USD,Acme,\n"
        "r-2,2026-04-20,42.00,USD,Other Shop,\n"
        "r-3,2026-04-01,9999.99,USD,Nowhere,\n",
        encoding="utf-8",
    )
    cfg = {
        "statement": {
            "path": "statement.csv",
            "account_id": "card-1",
            "legal_entity_id": "le-1",
            "account_card_currency": "USD",
            "column_map": {
                "transaction_date": "Transaction Date",
                "posting_date": "Post Date",
                "amount": "Amount",
                "vendor": "Description",
            },
        },
        "receipts": {"path": "receipts.csv", "source": "csv"},
        "output": {"path": "report.xlsx"},
    }
    config = tmp_path / "run.json"
    config.write_text(json.dumps(cfg), encoding="utf-8")
    return config


def test_propose_accept_check_roundtrip(tmp_path, capsys):
    config = _write_bundle(tmp_path)

    assert cli_main(["label", "propose", "--config", str(config)]) == 0
    out = capsys.readouterr().out
    assert "AUTO:          2" in out
    assert "NONE:          1" in out

    proposal = tmp_path / "labels-proposed.csv"
    rows = list(csv.DictReader(proposal.open(encoding="utf-8")))
    assert {r["document_id"]: r["verdict"] for r in rows} == {
        "r-1": "AUTO", "r-2": "AUTO", "r-3": "NONE",
    }
    # Human overrides one AUTO as ambiguous (decision token "exclude"
    # maps to label status "excluded" -- 2026-07-17 regression) and marks
    # the unmatched receipt as legitimately not on this card.
    for r in rows:
        if r["document_id"] == "r-2":
            r["decision"] = "exclude"
        if r["document_id"] == "r-3":
            r["decision"] = "no_charge"
    with proposal.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    assert cli_main(["label", "accept", "--config", str(config)]) == 0
    labels = list(csv.DictReader(
        (tmp_path / "labels.csv").open(encoding="utf-8")))
    by_doc = {r["document_id"]: r for r in labels}
    assert by_doc["r-1"]["status"] == "confirmed"
    assert by_doc["r-1"]["source"] == "auto"
    assert by_doc["r-2"]["status"] == "excluded"
    assert by_doc["r-2"]["transaction_id"] == ""
    assert by_doc["r-3"]["status"] == "no_charge"

    assert cli_main(["label", "check", "--config", str(config)]) == 0
    assert "Result: OK" in capsys.readouterr().out


def test_accept_rejects_double_claimed_transaction(tmp_path):
    config = _write_bundle(tmp_path)
    cli_main(["label", "propose", "--config", str(config)])
    proposal = tmp_path / "labels-proposed.csv"
    rows = list(csv.DictReader(proposal.open(encoding="utf-8")))
    for r in rows:
        r["decision"] = rows[0]["decision"] or r["decision"]
        if r["document_id"] == "r-2":
            r["decision"] = rows[0]["cand1_tx_id"] or r["decision"]
    # Force r-1 and r-2 onto the same transaction id.
    tx = next(r["decision"] for r in rows if r["document_id"] == "r-1")
    for r in rows:
        if r["document_id"] == "r-2":
            r["decision"] = tx
    with proposal.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    try:
        cli_main(["label", "accept", "--config", str(config)])
    except SystemExit as exc:
        assert "claimed by both" in str(exc)
    else:
        raise AssertionError("accept should refuse a double-claimed tx")


def test_check_flags_unknown_ids(tmp_path):
    config = _write_bundle(tmp_path)
    (tmp_path / "labels.csv").write_text(
        "document_id,transaction_id,status,source,evidence\n"
        "r-1,tx-does-not-exist,confirmed,human,\n"
        "ghost,,excluded,human,\n",
        encoding="utf-8",
    )
    assert cli_main(["label", "check", "--config", str(config)]) == 1
