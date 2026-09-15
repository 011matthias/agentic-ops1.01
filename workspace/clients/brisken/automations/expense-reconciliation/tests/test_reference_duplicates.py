"""One purchase is one candidate, by its number (backlog item 69, round A,
owner-approved 2026-09-15).

Item 56 collapses an invoice and its receipt when they agree on vendor +
date + total + currency. The copies that still reached the matcher are the
ones that print the vendor differently ("Anthropic, PBC" vs "Anthropic, PBC
(@anthropic)") or carry a re-mail's date, and on August 2026 the copy that
named no card then bound a stranger's charge of the same amount: the
Lovable 50 invoice took BASE44 50.00 on the Corporate Services statement
while its receipt copy named card 1176, a Consulting card that statement
does not carry.

Two structural moves, no threshold:

* a second duplicate key: normalized reference + total + currency, vendor
  spelling and date ignored (`find_duplicate_receipts_by_reference`), listed
  beside the vendor/date groups with `basis: "reference"` and collapsed the
  same way;
* the kept copy inherits the card (and, when exactly one is named, the
  entity) its copies name (`inherit_card_from_copies`), before the card
  chain, so the invoice copy leaves the other entity's statement scope.

Route-level through the FastAPI app, the way `test_duplicate_collapse.py`
drives item 56, plus unit tests for the reference normalization and the
inheritance rules.
"""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.duplicates import (  # noqa: E402
    collapsed_duplicate_copies,
    duplicate_group_id,
    duplicate_row_flags,
    find_duplicate_receipt_groups,
    find_duplicate_receipts,
    find_duplicate_receipts_by_reference,
    inherit_card_from_copies,
    reference_key,
)
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CHASE_HEADERS = ("Date", "Description", "Type", "Amount")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor, total, day, reference, payment_hint=None):
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference=reference, line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("15.00"),
                reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _register_cards(client):
    """The two cards the August shape needs: 2838 is Corporate Services
    (the statement's card), 1176 is Consulting (named by the receipt copy,
    absent from the statement)."""
    resp = client.put("/api/settings", json={
        "entities": {"Corporate Services": {}, "Consulting": {}},
        "cards": {
            "corp-2838": {
                "label": "Corporate card (Chase)", "digits": ["2838"],
                "entity": "Corporate Services", "currency": "USD",
            },
            "cons-1176": {
                "label": "Consulting card (Chase)", "digits": ["1176"],
                "entity": "Consulting", "currency": "USD",
            },
        },
    })
    assert resp.status_code == 200, resp.text


def _batch(client, files, legal_entity="Corporate Services", label="August 2026"):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": legal_entity, "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + str(i).encode(), "application/octet-stream"))
            for i, name in enumerate(files)
        ],
    ))
    return batch_id


def _xlsx_bytes(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(CHASE_HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _attach(client, batch_id, rows):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("August2026.xlsx", _xlsx_bytes(rows), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    return _done(client, resp)


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(view, vendor):
    return next(r for r in view["rows"] if r["vendor"] == vendor)


# ── the Lovable 50 shape ────────────────────────────────────────────────


def test_a_copy_that_borrows_its_card_does_not_take_a_strangers_charge(
    client, monkeypatch
):
    """The August 2026 defect, end to end. The invoice copy names no card,
    the receipt copy names card 1176 (Consulting), the Corporate Services
    statement carries BASE44 50.00 four days later. Before this round the
    invoice copy, alone in the pool with no card, took BASE44 as an exact
    match. Now it inherits card 1176, the card chain derives Consulting, and
    the pair is dropped as cross-entity: BASE44 stays unmatched, honestly."""
    _register_cards(client)
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated", "50.00", "2026-08-21",
                    "H0LHY2WQ-0032"),
        _extraction("Lovable Labs Incorporated (@lovable)", "50.00", "2026-08-21",
                    "H0LHY2WQ0032", payment_hint="Visa ...1176"),
    )
    batch_id = _batch(client, ["Invoice-H0LHY2WQ-0032.jpg", "Receipt-2714-0234.jpg"])
    _attach(client, batch_id, [
        (datetime(2026, 8, 25), "BASE44", "Sale", -50.00),
        (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
    ])

    view = _view(client, batch_id)
    assert view["summary"]["n_reconciled"] == 0
    base44 = _row(view, "BASE44")
    assert base44["chosen_document_id"] is None
    assert base44["candidates"] == [], "a Consulting receipt is no candidate here"
    assert base44["effective_bucket"] == "unmatched"
    # Both copies are still the month's receipts: the receipt copy collapsed
    # as the duplicate it is, the invoice copy unmatched with its card.
    assert view["summary"]["n_receipts"] == 2
    assert view["summary"]["n_duplicate_copies"] == 1
    unmatched = {r["document_id"]: r for r in view["unmatched_receipts"]}
    assert len(unmatched) == 2

    # The grid says the same thing the matcher acted on: the invoice copy
    # carries card 1176 and the Consulting entity, from its copy.
    grid = _grid(client, batch_id)
    invoice = next(
        e for e in grid["expenses"] if "Invoice-" in e["document_id"]
    )
    assert invoice["payment_hint"] == "Visa ...1176"
    assert invoice["card"]["key"] == "cons-1176"
    assert invoice["legal_entity_id"] == "Consulting"
    assert invoice["entity_source"] == "card"


def test_an_invoice_and_its_receipt_spelled_differently_make_one_exact_match(
    client, monkeypatch
):
    """The vendor/date key misses a pair whose vendor is spelled two ways;
    the reference key does not. One candidate, exact, and the group says on
    what basis it was found."""
    _register_cards(client)
    _wire(
        monkeypatch,
        _extraction("Anthropic, PBC", "51.38", "2026-08-05", "DZ9BH3VA-0036"),
        _extraction("Anthropic, PBC (@anthropic)", "51.38", "2026-08-05",
                    "DZ9BH3VA0036", payment_hint="Visa ...2838"),
    )
    batch_id = _batch(client, ["Invoice-DZ9BH3VA-0036.jpg", "Receipt-2462-7346-1610.jpg"])
    _attach(client, batch_id, [
        (datetime(2026, 8, 5), "ANTHROPIC", "Sale", -51.38),
    ])

    view = _view(client, batch_id)
    assert view["summary"]["n_reconciled"] == 1
    assert view["summary"]["n_review"] == 0, "one document, not two candidates"
    row = _row(view, "ANTHROPIC")
    assert len(row["candidates"]) == 1
    assert row["candidates"][0]["match_type"] == "exact"
    (group,) = view["duplicate_groups"]
    assert group["kind"] == "receipt"
    assert group["basis"] == "reference"
    assert len(group["members"]) == 2
    assert view["summary"]["n_duplicate_copies"] == 1
    extra = view["unmatched_receipts"][0]
    assert extra["duplicate"]["is_extra"] is True
    assert extra["duplicate"]["group_id"] == group["group_id"]


def test_not_a_duplicate_re_expands_a_reference_group(client, monkeypatch):
    """The reviewer's `ignore` is the escape hatch for the reference key
    too: both copies return to the pool and compete again."""
    _register_cards(client)
    _wire(
        monkeypatch,
        _extraction("Anthropic, PBC", "51.38", "2026-08-05", "DZ9BH3VA-0036"),
        _extraction("Anthropic, PBC (@anthropic)", "51.38", "2026-08-05",
                    "DZ9BH3VA0036", payment_hint="Visa ...2838"),
    )
    batch_id = _batch(client, ["Invoice-DZ9BH3VA-0036.jpg", "Receipt-2462-7346-1610.jpg"])
    _attach(client, batch_id, [(datetime(2026, 8, 5), "ANTHROPIC", "Sale", -51.38)])
    view = _view(client, batch_id)
    (group,) = view["duplicate_groups"]
    assert group["basis"] == "reference"
    assert len(_row(view, "ANTHROPIC")["candidates"]) == 1

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": group["group_id"], "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("rematch") is not None

    view = _view(client, batch_id)
    row = _row(view, "ANTHROPIC")
    assert len(row["candidates"]) == 2, "both copies compete again"
    assert row["effective_bucket"] == "review"
    assert view["summary"]["n_duplicate_copies"] == 0
    (group,) = view["duplicate_groups"]
    assert group["resolution"] == "ignore"
    assert group["basis"] == "reference", "the ruling does not change how it was found"


def test_a_vendor_date_group_keeps_its_id_when_a_reference_group_overlaps(
    client, monkeypatch
):
    """Groups are sets of members and the two keys never merge. A and B are
    a vendor/date pair; B and C share a reference but C is spelled and dated
    differently. The reviewer's resolutions are keyed by group id and the
    live July month holds saved ones, so {A, B} must keep the id it had
    before this round, {B, C} is a second group (basis reference), and no
    {A, B, C} appears. B sits in both; its row marker is deterministic and
    shows the group in which B is the extra copy."""
    _register_cards(client)
    _wire(
        monkeypatch,
        # A: a scan that reads no reference; B: the same invoice with its
        # number; C: the re-mailed body, spelled and dated differently
        _extraction("Redis Inc.", "13200.00", "2026-07-22", ""),
        _extraction("Redis Inc.", "13200.00", "2026-07-22", "IUS25300"),
        _extraction("Redis", "13200.00", "2026-07-28", "IUS25300"),
    )
    batch_id = _batch(client, ["a-scan.jpg", "b-invoice.jpg", "c-rendered-body.jpg"],
                      legal_entity="", label="July 2026")
    grid = _grid(client, batch_id)
    # the intake prefixes a counter in upload order
    a, b, c = sorted(e["document_id"] for e in grid["expenses"])
    assert a.endswith("a-scan.jpg") and b.endswith("b-invoice.jpg")
    assert c.endswith("c-rendered-body.jpg")

    groups = {tuple(g["members"]): g for g in grid["duplicate_groups"]}
    assert set(groups) == {(a, b), (b, c)}, sorted(groups)
    assert groups[(a, b)]["group_id"] == duplicate_group_id("receipt", [a, b])
    assert "basis" not in groups[(a, b)], "the old key's group renders as before"
    assert groups[(b, c)]["basis"] == "reference"
    assert grid["summary"]["n_duplicate_groups"] == 2

    markers = {e["document_id"]: e["duplicate"] for e in grid["expenses"]}
    assert markers[a]["is_extra"] is False and markers[a]["copy"] == 1
    assert markers[b]["group_id"] == groups[(a, b)]["group_id"]
    assert markers[b]["is_extra"] is True, "the marker never hides a collapse"
    assert markers[c]["group_id"] == groups[(b, c)]["group_id"]
    assert markers[c]["is_extra"] is True


# ── unit: the reference normalization ───────────────────────────────────


def _receipt(doc, ref, total="50.00", day=date(2026, 8, 21), vendor="Lovable",
             payment_mode=None, entity="", currency="USD"):
    return Receipt(
        document_id=doc, legal_entity_id=entity, detected_date=day,
        detected_total=Decimal(total), detected_currency=currency,
        detected_vendor=vendor, detected_reference=ref,
        payment_mode=payment_mode,
    )


@pytest.mark.parametrize("raw, expected", [
    ("H0LHY2WQ-0032", "H0LHY2WQ0032"),
    ("h0lhy2wq0032", "H0LHY2WQ0032"),
    ("2247 1655 6392", "224716556392"),
    ("Beleg-Nr. 2742", "BELEGNR2742"),
    ("NFC-e 166769; Protocolo 226260674307863", "NFCE166769PROTOCOLO226260674307863"),
])
def test_reference_key_is_uppercase_alphanumerics(raw, expected):
    assert reference_key(_receipt("d", raw)) == expected


@pytest.mark.parametrize("raw", ["4563", "1514", "AB-12", "", None, "  --  "])
def test_reference_key_refuses_short_references(raw):
    assert reference_key(_receipt("d", raw)) is None


@pytest.mark.parametrize("raw", [
    "20260821",   # YYYYMMDD
    "21082026",   # DDMMYYYY
    "08212026",   # MMDDYYYY
    "260821",     # YYMMDD
    "2026-08-21", # the same date with separators
])
def test_reference_key_refuses_the_receipts_own_date(raw):
    assert reference_key(_receipt("d", raw, day=date(2026, 8, 21))) is None


def test_reference_key_keeps_a_digit_string_that_is_not_the_date():
    assert reference_key(_receipt("d", "20260822", day=date(2026, 8, 21))) == "20260822"
    assert reference_key(_receipt("d", "20260821", day=None)) == "20260821"


@pytest.mark.parametrize("raw, total", [
    ("1320000", "13200.00"),   # the total with its cents
    ("13200", "13200.00"),     # the total without them
    ("13,200.00", "13200.00"), # printed with separators
    ("17573", "175.73"),
])
def test_reference_key_refuses_the_receipts_own_total(raw, total):
    assert reference_key(_receipt("d", raw, total=total)) is None


def test_reference_key_keeps_a_digit_string_that_is_not_the_total():
    assert reference_key(_receipt("d", "1320001", total="13200.00")) == "1320001"
    assert reference_key(_receipt("d", "271025", total="43.12")) == "271025"


# ── unit: the second key and the combined group list ─────────────────────


def test_reference_groups_ignore_vendor_spelling_and_date():
    a = _receipt("a", "DZ9BH3VA-0036", vendor="Anthropic, PBC", day=date(2026, 8, 5))
    b = _receipt("b", "DZ9BH3VA0036", vendor="Anthropic, PBC (@anthropic)",
                 day=date(2026, 8, 7))
    other_total = _receipt("c", "DZ9BH3VA0036", total="51.39")
    other_ccy = _receipt("d", "DZ9BH3VA0036", currency="EUR")
    assert find_duplicate_receipts([a, b, other_total, other_ccy]) == []
    assert find_duplicate_receipts_by_reference([a, b, other_total, other_ccy]) == [["a", "b"]]


def test_reference_groups_compare_currency_case_insensitively():
    a = _receipt("a", "IUS25300", currency="usd")
    b = _receipt("b", "IUS25300", currency="USD")
    assert find_duplicate_receipts_by_reference([a, b]) == [["a", "b"]]


def test_a_group_both_keys_find_is_one_group_with_no_basis():
    a = _receipt("a", "H0LHY2WQ-0032")
    b = _receipt("b", "H0LHY2WQ0032")
    assert find_duplicate_receipts([a, b]) == [["a", "b"]]
    assert find_duplicate_receipts_by_reference([a, b]) == [["a", "b"]]
    assert find_duplicate_receipt_groups([a, b]) == [(["a", "b"], None)]


def test_overlapping_groups_stay_two_groups_and_the_old_id_holds():
    a = _receipt("a", None, vendor="Redis Inc.", day=date(2026, 7, 22))
    b = _receipt("b", "IUS25300", vendor="Redis Inc.", day=date(2026, 7, 22))
    c = _receipt("c", "IUS25300", vendor="Redis", day=date(2026, 7, 28))
    groups = find_duplicate_receipt_groups([a, b, c])
    assert groups == [(["a", "b"], None), (["b", "c"], "reference")]
    assert duplicate_group_id("receipt", ["a", "b"]) == duplicate_group_id("receipt", ["b", "a"])
    # collapse: every member after the first of each group; b by the first,
    # c by the second; a document collapsed by one group and kept by the
    # other is collapsed
    assert collapsed_duplicate_copies([a, b, c]) == {"b", "c"}
    # `ignore` on the reference group re-expands ONLY that group
    ignored = {duplicate_group_id("receipt", ["b", "c"]): "ignore"}
    assert collapsed_duplicate_copies([a, b, c], ignored) == {"b"}


def test_row_flags_prefer_the_group_where_the_row_is_an_extra_copy():
    groups = [
        {"group_id": "g1", "kind": "receipt", "members": ["a", "b"], "resolution": None},
        {"group_id": "g2", "kind": "receipt", "members": ["b", "c"], "resolution": None},
    ]
    flags = duplicate_row_flags(groups, kind="receipt")
    assert flags["b"]["group_id"] == "g1" and flags["b"]["is_extra"] is True
    # and the same answer whatever the list order
    flags_rev = duplicate_row_flags(list(reversed(groups)), kind="receipt")
    assert flags_rev["b"]["group_id"] == "g1"
    # a row that is copy 1 in both keeps the first listed group
    both_first = [
        {"group_id": "g1", "kind": "receipt", "members": ["a", "b"], "resolution": None},
        {"group_id": "g2", "kind": "receipt", "members": ["a", "c"], "resolution": None},
    ]
    assert duplicate_row_flags(both_first, kind="receipt")["a"]["group_id"] == "g1"


# ── unit: the inheritance ────────────────────────────────────────────────


def test_the_copy_with_no_card_inherits_the_card_its_copy_names():
    invoice = _receipt("inv", "H0LHY2WQ-0032")
    receipt = _receipt("rcpt", "H0LHY2WQ0032", payment_mode="Visa ...1176",
                       entity="Consulting")
    out = inherit_card_from_copies([invoice, receipt])
    assert out[0].payment_mode == "Visa ...1176"
    assert out[0].legal_entity_id == "Consulting"
    assert out[1] is receipt, "a copy that names its card keeps its own object"
    # order and membership untouched
    assert [r.document_id for r in out] == ["inv", "rcpt"]


def test_a_non_card_tender_word_is_replaced_by_the_card():
    link = _receipt("a", "HMVWDWIL0028", payment_mode="Link")
    card = _receipt("b", "HMVWDWIL-0028", payment_mode="Visa ...3645")
    out = inherit_card_from_copies([link, card])
    assert out[0].payment_mode == "Visa ...3645"


def test_a_copy_that_names_a_card_keeps_it():
    a = _receipt("a", "REF12345", payment_mode="Visa ...2838")
    b = _receipt("b", "REF12345", payment_mode="Visa ...1176")
    out = inherit_card_from_copies([a, b])
    assert out[0].payment_mode == "Visa ...2838"
    assert out[1].payment_mode == "Visa ...1176"


def test_copies_naming_different_cards_lend_nothing():
    none = _receipt("a", "REF12345")
    c1 = _receipt("b", "REF12345", payment_mode="Visa ...2838")
    c2 = _receipt("c", "REF12345", payment_mode="Visa ...1176")
    out = inherit_card_from_copies([none, c1, c2])
    assert out[0].payment_mode is None


def test_two_spellings_of_one_card_still_lend():
    none = _receipt("a", "REF12345")
    c1 = _receipt("b", "REF12345", payment_mode="Visa ...3645")
    c2 = _receipt("c", "REF12345", payment_mode="[Visa] - 3645")
    out = inherit_card_from_copies([none, c1, c2])
    assert out[0].payment_mode == "Visa ...3645"


def test_entity_is_lent_only_when_exactly_one_is_named():
    a = _receipt("a", "REF12345")
    b = _receipt("b", "REF12345", entity="Consulting")
    c = _receipt("c", "REF12345", entity="Corporate Services")
    assert inherit_card_from_copies([a, b])[0].legal_entity_id == "Consulting"
    assert inherit_card_from_copies([a, b, c])[0].legal_entity_id == ""
    own = _receipt("d", "REF12345", entity="Cloud Services")
    assert inherit_card_from_copies([own, b])[0].legal_entity_id == "Cloud Services"


def test_inheritance_needs_a_reference_group_not_a_vendor_date_group():
    """Two receipts with no usable reference are a vendor/date pair and
    nothing lends: without a document number the two are the same
    purchase by circumstance, not by identity."""
    a = _receipt("a", "4563", payment_mode=None)
    b = _receipt("b", "4563", payment_mode="Visa ...2838")
    assert find_duplicate_receipts([a, b]) == [["a", "b"]]
    out = inherit_card_from_copies([a, b])
    assert out is not None and out[0].payment_mode is None
