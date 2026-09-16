"""The tip band is merchant-scoped (backlog item 63).

`amount_probable_tolerance_pct` is 20%, and it exists for one reason: a
card charge carries a tip the receipt printed before. A tip changes the
amount; it never changes who was paid. Until now the band ignored the
merchant entirely, so on the real August month it paired ADOBE 16.23 with
a Lovable 15.00 receipt, ANTHROPIC 104.95 with an Obsidian 96.00 one, and
bound five such pairs outright. Measured on that month: 41 of 71
same-currency non-exact candidate pairs named different merchants (all at
vendor agreement <= 0.40), and the 30 true ones all scored exactly 1.00.

A same-currency pair that spends the band now has to agree on the vendor,
or have no vendor named on one side. Exact amounts are untouched, and so
is every FX path: the S1 optimize run measured vendor as non-separable
there (banks truncate foreign vendor strings to aggregators).
"""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal

import pytest

from expense_recon.matching.deterministic import (
    MatchingConfig,
    _normalize,
    match_one,
)
from expense_recon.matching.types import MatchType, Receipt, Transaction

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _tx(vendor, amount, day=1, **kw):
    return Transaction(
        f"t-{vendor}-{amount}",
        "ent",
        "card-2838",
        date(2026, 8, day),
        None,
        Decimal(amount),
        kw.pop("ccy", "USD"),
        "USD",
        vendor,
        **kw,
    )


def _rec(vendor, total, day=1, ccy="USD", doc=None):
    return Receipt(
        doc or f"d-{vendor}-{total}",
        "ent",
        date(2026, 8, day),
        Decimal(total),
        ccy,
        vendor,
    )


# ── the defect, at the matcher ──────────────────────────────────────────


def test_different_merchants_do_not_share_the_tip_band():
    """The item's own example: ADOBE 16.23 was offered a Lovable 15.00
    receipt. 7.6% apart, inside the 20% band, and plainly not the same
    purchase."""
    assert match_one(
        _tx("ADOBE  *800-833-6687", "16.23"),
        _rec("Lovable Labs Incorporated", "15.00"),
        MatchingConfig(),
    ) is None


def test_the_second_named_example_is_gone_too():
    """ANTHROPIC 104.95 offered an Obsidian 96.00 receipt (8.5% apart)."""
    assert match_one(
        _tx("ANTHROPIC* CLAUDE SUB", "104.95"),
        _rec("Obsidian", "96.00"),
        MatchingConfig(),
    ) is None


def test_the_tip_case_the_band_exists_for_survives():
    """The reason the band is 20% wide: a restaurant charge carries a tip
    the printed receipt does not. Same merchant, so it stays."""
    m = match_one(
        _tx("HOSTARIA PANTHEON", "28.00"),
        _rec("Hostaria Pantheon", "24.00"),
        MatchingConfig(),
    )
    assert m is not None
    assert m.match_type is MatchType.PROBABLE


def test_an_exact_amount_still_matches_across_different_vendor_strings():
    """The floor is scoped to the band, not to matching at large. A bank
    string that agrees on nothing but the amount still reconciles when the
    amount is exact; that is the case vendor text is known to be bad at."""
    m = match_one(
        _tx("SQ *MEGA CENTE CONSTR", "41.00"),
        _rec("Nordstrom Rack", "41.00"),
        MatchingConfig(),
    )
    assert m is not None
    assert m.match_type is MatchType.EXACT


def test_a_receipt_that_names_no_vendor_keeps_the_band():
    """An unnamed side is missing evidence, not conflicting evidence. The
    reconciliation guarantee says never drop a pair on absence."""
    m = match_one(_tx("ADOBE", "16.23"), _rec(None, "15.00"), MatchingConfig())
    assert m is not None
    assert m.match_type is MatchType.PROBABLE


def test_a_statement_that_names_no_vendor_keeps_the_band():
    m = match_one(_tx("", "16.23"), _rec("Lovable", "15.00"), MatchingConfig())
    assert m is not None
    assert m.match_type is MatchType.PROBABLE


def test_bank_truncation_clears_the_floor_on_its_own():
    """The failure mode a vendor floor could plausibly cause: banks
    truncate, so the two strings never read alike. `vendor_similarity` was
    built for exactly that (token-best-ratio, ANNEALING A3) and scores this
    real pair at 0.86, well clear of the floor. No alias needed."""
    m = match_one(
        _tx("MEGA CENTE CONSTR", "28.00"),
        _rec("Mega Center Comercio De Materiais", "24.00"),
        MatchingConfig(),
    )
    assert m is not None
    assert m.vendor_score > 0.5


def test_a_confirmed_alias_reopens_the_band():
    """When a bank bills through an aggregator the strings share nothing,
    and the fuzzy ratio cannot rescue it. Once a reviewer has confirmed
    that ARIBASUPPLIERBILLING IS this merchant, `_vendor_score` pins to 1.0
    and later months keep matching."""
    tx = _tx("ARIBASUPPLIERBILLING", "30.88")
    rec = _rec("Lovable Labs Incorporated (@lovable)", "25.00")
    assert match_one(tx, rec, MatchingConfig()) is None

    cfg = MatchingConfig(
        vendor_aliases=frozenset({
            ("ent", _normalize("ARIBASUPPLIERBILLING"),
             _normalize("Lovable Labs Incorporated (@lovable)")),
        })
    )
    m = match_one(tx, rec, cfg)
    assert m is not None
    assert m.match_type is MatchType.PROBABLE


def test_fx_pairs_keep_the_band_untouched():
    """The exact-FX path compares the receipt to the statement's own
    printed original amount. Vendor is not separable there (S1: 26/55 true
    pairs below 0.2 similarity), so the floor must not reach it."""
    tx = _tx(
        "MEGA CENTE CONSTR",
        "35.00",
        ccy="USD",
        original_amount=Decimal("160.00"),
        original_currency="BRL",
    )
    m = match_one(tx, _rec("Padaria Sao Jose", "150.00", ccy="BRL"), MatchingConfig())
    assert m is not None
    assert m.match_type is MatchType.PROBABLE


def test_the_floor_is_tunable_and_zero_disables_it():
    tx = _tx("ADOBE  *800-833-6687", "16.23")
    rec = _rec("Lovable Labs Incorporated", "15.00")
    assert match_one(tx, rec, MatchingConfig()) is None
    assert match_one(
        tx, rec, MatchingConfig(amount_probable_min_vendor_score=0.0)
    ) is not None
    assert MatchingConfig.from_dict(
        {"amount_probable_min_vendor_score": 0.0}
    ).amount_probable_min_vendor_score == 0.0


# ── the same defect, through the route the reviewer reads ───────────────


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _extraction(vendor, total, day):
    return ExtractedReceipt(
        date=f"2026-08-{day:02d}", total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _xlsx_bytes(rows):
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _august(client, monkeypatch):
    """One ADOBE charge that is NOT the Lovable receipt, and one restaurant
    charge that IS its receipt plus a tip."""
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client",
        lambda cfg: (
            MockLLMClient(
                extraction_responses=[
                    _extraction("Lovable Labs Incorporated", "15.00", 31),
                    _extraction("Hostaria Pantheon", "24.00", 20),
                ],
                fx_responses=[],
            ),
            None,
        ),
    )
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", ("Receipt-2247.jpg", JPG + b"1", "application/octet-stream")),
            ("files", ("Receipt-9981.jpg", JPG + b"2", "application/octet-stream")),
        ],
    ))
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx",
            _xlsx_bytes([
                (datetime(2026, 8, 31), "ADOBE  *800-833-6687", "Sale", -16.23),
                (datetime(2026, 8, 20), "HOSTARIA PANTHEON", "Sale", -28.00),
            ]),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(view, vendor):
    return next(r for r in view["rows"] if r["vendor"] == vendor)


def test_the_adobe_row_no_longer_lists_the_lovable_receipt(client, monkeypatch):
    view = _august(client, monkeypatch)
    offered = {
        c["receipt"]["vendor"] for c in _row(view, "ADOBE  *800-833-6687")["candidates"]
    }
    assert "Lovable Labs Incorporated" not in offered
    assert offered == set()


def test_the_tip_pair_still_reaches_the_reviewer(client, monkeypatch):
    """Dropping wrong candidates must not cost the right one: the same
    payload still offers the restaurant receipt against its tipped charge."""
    view = _august(client, monkeypatch)
    cands = _row(view, "HOSTARIA PANTHEON")["candidates"]
    assert [c["receipt"]["vendor"] for c in cands] == ["Hostaria Pantheon"]
    assert cands[0]["match_type"] == "probable"


def test_nothing_is_dropped_from_the_month(client, monkeypatch):
    """The reconciliation guarantee: the un-offered receipt is unmatched,
    not absent."""
    view = _august(client, monkeypatch)
    assert view["summary"]["n_receipts"] == 2
    assert view["summary"]["invariant_ok"] is True
    unmatched = {r["vendor"] for r in view["unmatched_receipts"]}
    assert unmatched == {"Lovable Labs Incorporated"}
