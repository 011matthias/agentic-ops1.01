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
    reference_keys,
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
        "entities": {"Corporate Services": {}, "Consulting": {}, "Cloud Services": {}},
        "cards": {
            "corp-2838": {
                "label": "Corporate card (Chase)", "digits": ["2838"],
                "entity": "Corporate Services", "currency": "USD",
            },
            "cons-1176": {
                "label": "Consulting card (Chase)", "digits": ["1176"],
                "entity": "Consulting", "currency": "USD",
            },
            "cloud-9693": {
                "label": "Cloud card (Chase)", "digits": ["9693"],
                "entity": "Cloud Services", "currency": "USD",
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

    # And the export (the Zoho CSV, the month PDF and report.xlsx all build
    # from `_expense_export_inputs`): the invoice row ships as Consulting,
    # not with the batch's Corporate Services or the entity placeholder.
    by_ref = _csv_rows_by_reference(client, batch_id)
    assert by_ref["H0LHY2WQ-0032"]["Legal Entity"] == "Consulting"
    assert by_ref["H0LHY2WQ0032"]["Legal Entity"] == "Consulting"


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
    too: both copies return to the pool and compete again. And nothing is
    lent across an ignored group (review F3), so the copy that names the
    statement's card wins the charge outright on the card signal and the
    card-less copy is simply unmatched, with no duplicate marker."""
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
    assert row["effective_bucket"] == "reconciled"
    assert "Receipt-" in row["chosen_document_id"], "the copy naming card 2838"
    assert view["summary"]["n_duplicate_copies"] == 0
    (invoice,) = view["unmatched_receipts"]
    assert "Invoice-" in invoice["document_id"]
    assert not invoice.get("duplicate"), "no marker outlives the ruling"
    (group,) = view["duplicate_groups"]
    assert group["resolution"] == "ignore"
    assert group["basis"] == "reference", "the ruling does not change how it was found"
    # the invoice copy no longer carries its twin's card
    grid = _grid(client, batch_id)
    inv = next(e for e in grid["expenses"] if "Invoice-" in e["document_id"])
    assert inv["payment_hint"] in (None, "")


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
    other_ccy = _receipt("d", "DZ9BH3VA0036", currency="EUR")
    assert find_duplicate_receipts([a, b, other_ccy]) == []
    assert find_duplicate_receipts_by_reference([a, b, other_ccy]) == [["a", "b"]]
    # A third receipt on the same reference with ANOTHER total does not
    # merely stay out of the group: it proves the reference is an account
    # id, and the group is gone (see the account-id tests below).
    other_total = _receipt("c", "DZ9BH3VA0036", total="51.39")
    assert find_duplicate_receipts_by_reference([a, b, other_total, other_ccy]) == []


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


# ── unit: a reference shared across totals is an account id (review F1) ──


def test_an_account_id_on_receipts_of_different_totals_is_no_reference():
    """July 2026: Anthropic's account id `NQTJA4FE` sits in
    `detected_reference` on five top-ups with five totals. Two top-ups of
    ONE amount under that id would twin, the second would leave the pool
    and its charge would go unmatched with no candidate. A reference that
    appears on two or more receipts with different totals is an account id,
    and no receipt carrying it gets a key."""
    top_ups = [
        _receipt("0047", "NQTJA4FE", total="48.49", vendor="Anthropic, PBC"),
        _receipt("0048", "NQTJA4FE", total="45.44", vendor="Anthropic, PBC"),
        _receipt("0049", "NQTJA4FE", total="45.35", vendor="Anthropic, PBC"),
        _receipt("0050", "NQTJA4FE", total="47.23", vendor="Anthropic, PBC"),
        _receipt("0051", "NQTJA4FE", total="48.31", vendor="Anthropic, PBC"),
        # the shape the rule exists for: a sixth top-up of an amount already
        # seen under the same account id, on another day
        _receipt("0052", "NQTJA4FE", total="48.31", vendor="Anthropic, PBC",
                 day=date(2026, 7, 29)),
    ]
    assert reference_keys(top_ups) == {}
    assert find_duplicate_receipts_by_reference(top_ups) == []
    assert collapsed_duplicate_copies(top_ups) == set()
    # each on its own still reads as a reference: only the list can tell
    assert reference_key(top_ups[0]) == "NQTJA4FE"


def test_a_hotel_folio_on_two_receipts_is_no_reference():
    """Bundle 01-10-2024_ER-00181: two Bella Sky Hotel receipts on one folio
    `37939838` with different totals. Same rule, different extractor."""
    night = _receipt("a", "37939838", total="1890.00", vendor="Bella Sky Hotel",
                     currency="DKK", day=date(2024, 10, 3))
    dinner = _receipt("b", "37939838", total="412.50", vendor="Bella Sky Hotel",
                      currency="DKK", day=date(2024, 10, 3))
    assert reference_keys([night, dinner]) == {}
    assert find_duplicate_receipts_by_reference([night, dinner]) == []


def test_a_stripe_pair_still_twins_beside_an_account_id():
    """The rule silences the account id and nothing else: a Stripe invoice
    and its receipt, spelled two ways, twin in the same list."""
    receipts = [
        _receipt("0047", "NQTJA4FE", total="48.49", vendor="Anthropic, PBC"),
        _receipt("0048", "NQTJA4FE", total="45.44", vendor="Anthropic, PBC"),
        _receipt("inv", "H0LHY2WQ-0032", vendor="Lovable Labs Incorporated"),
        _receipt("rcpt", "H0LHY2WQ0032", vendor="Lovable Labs Incorporated (@lovable)",
                 day=date(2026, 8, 23)),
    ]
    assert reference_keys(receipts) == {"inv": "H0LHY2WQ0032", "rcpt": "H0LHY2WQ0032"}
    assert find_duplicate_receipts_by_reference(receipts) == [["inv", "rcpt"]]


def test_a_receipt_with_no_total_does_not_vote_on_the_account_id():
    a = _receipt("a", "REF12345", total="50.00")
    b = _receipt("b", "REF12345", total="50.00")
    c = Receipt(
        document_id="c", legal_entity_id="", detected_date=date(2026, 8, 21),
        detected_total=None, detected_currency="USD", detected_vendor="x",
        detected_reference="REF12345",
    )
    assert find_duplicate_receipts_by_reference([a, b, c]) == [["a", "b"]]


@pytest.mark.parametrize("raw", ["00144", "00184", "0001514"])
def test_a_padded_till_counter_is_under_the_floor(raw):
    """Bundle 01-06-2025_ER-00194 prints its till counters padded. `00144`
    is the counter `144`, not a five-digit number."""
    assert reference_key(_receipt("d", raw)) is None


def test_a_padded_real_number_keeps_its_key():
    assert reference_key(_receipt("d", "0012345")) == "0012345"


# ── unit: the inheritance keeps out of the reviewer's and operator's way ──


def test_an_ignored_group_lends_nothing():
    """A reviewer's `ignore` says the two documents are two purchases; a
    card lent across them would keep the card-less one scoped to the
    other's card while its own charge waits on the statement."""
    invoice = _receipt("inv", "H0LHY2WQ-0032")
    receipt = _receipt("rcpt", "H0LHY2WQ0032", payment_mode="Visa ...1176",
                       entity="Consulting")
    gid = duplicate_group_id("receipt", ["inv", "rcpt"])
    out = inherit_card_from_copies([invoice, receipt], {gid: "ignore"})
    assert out[0].payment_mode is None and out[0].legal_entity_id == ""
    # `confirmed` is not `ignore`: acknowledging a duplicate keeps the lend
    out = inherit_card_from_copies([invoice, receipt], {gid: "confirmed"})
    assert out[0].payment_mode == "Visa ...1176"


def test_an_operator_assigned_hint_word_is_not_overwritten():
    """`resolve_hinted_card_ex` keys the operator's assignment on the exact
    stored payment mode. Rewriting "Link" to the twin's card label would
    silently lose that ruling to the twin's card."""
    link = _receipt("a", "HMVWDWIL0028", payment_mode="Link")
    card = _receipt("b", "HMVWDWIL-0028", payment_mode="Visa ...3645")
    kept = inherit_card_from_copies([link, card], None, {"Link": "corp-2838"})
    assert kept[0].payment_mode == "Link"
    # a hint on some OTHER word does not protect this member
    lent = inherit_card_from_copies([link, card], None, {"PAYE": "corp-2838"})
    assert lent[0].payment_mode == "Visa ...3645"
    # the entity half is unaffected by the hint
    ent = inherit_card_from_copies(
        [link, _receipt("c", "HMVWDWIL0028", payment_mode="Visa ...3645",
                        entity="Consulting")],
        None, {"Link": "corp-2838"},
    )
    assert ent[0].payment_mode == "Link" and ent[0].legal_entity_id == "Consulting"


def test_a_masked_bin_no_longer_lends_round_b_flipped_it():
    """The August 2026 `0000` / `0018` Petit Train shape, after round B.

    Round A pinned this AS IT WAS and said the flip had to be conscious:
    `_card_keys("42463153XXXXXX38")` read the masked BIN as a card
    ({"42463153", "3153"}), so the inheritance treated `0000` as
    card-bearing and lent that string to the `PAYE` copy `0018`, while the
    card chain read the same string as an ABSENT card and the
    card-contradiction gate demoted the receipt's true pair.

    Round B (2026-09-15) made a digit run immediately followed by a mask
    character a card PREFIX, so the string carries no card at all, which is
    what it actually says. Nothing is lent, and on the live August month
    `0000` went from `demoted_card` to a clean match on PETIT TRAIN TOUR.
    """
    from expense_recon.matching.deterministic import _card_keys

    assert _card_keys("42463153XXXXXX38") == set()
    train = _receipt("0000", "16530", total="37.19", currency="EUR",
                     vendor="SARL TRAIN'S", payment_mode="42463153XXXXXX38")
    billet = _receipt("0018", "16530", total="37.19", currency="EUR",
                      vendor="Le Petit Train", payment_mode="PAYE")
    out = inherit_card_from_copies([train, billet])
    assert out[1].payment_mode == "PAYE"


# ── route: the reviewer's ignore frees the card-less copy (review F3) ────


def test_not_a_duplicate_frees_the_card_less_copy_for_its_own_charge(
    client, monkeypatch
):
    """The invoice copy names no card, the receipt copy names card 1176
    (Consulting), and THIS statement (Corporate Services) carries the
    invoice's own LOVABLE 50.00. While the pair is a group the invoice
    borrows 1176 and leaves this scope (0 reconciled). Once the reviewer
    rules the pair `ignore`, nothing is lent: the invoice copy is a
    Corporate Services document again and takes its charge; the receipt
    copy, on the Consulting card, stays out. Grid and CSV say the same."""
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
        (datetime(2026, 8, 21), "LOVABLE", "Sale", -50.00),
    ])
    view = _view(client, batch_id)
    assert view["summary"]["n_reconciled"] == 0, "scoped to 1176 while grouped"
    (group,) = view["duplicate_groups"]

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": group["group_id"], "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text

    view = _view(client, batch_id)
    row = _row(view, "LOVABLE")
    assert view["summary"]["n_reconciled"] == 1
    assert row["chosen_document_id"] is not None
    assert "Invoice-" in row["chosen_document_id"]
    assert row["effective_bucket"] == "reconciled"
    assert view["summary"]["n_duplicate_copies"] == 0

    grid = _grid(client, batch_id)
    invoice = next(e for e in grid["expenses"] if "Invoice-" in e["document_id"])
    assert invoice["payment_hint"] in (None, "")
    assert invoice["legal_entity_id"] == "Corporate Services"
    assert invoice["entity_source"] == "batch"

    by_ref = _csv_rows_by_reference(client, batch_id)
    assert by_ref["H0LHY2WQ-0032"]["Legal Entity"] == "Corporate Services"
    assert by_ref["H0LHY2WQ0032"]["Legal Entity"] == "Consulting"


def _csv_rows_by_reference(client, batch_id) -> dict[str, dict]:
    import csv

    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    return {r["Reference#"]: r for r in rows}


# ── route: an operator's hint assignment beats the twin's card (F8a) ────


def test_an_operator_assignment_on_the_tender_word_beats_the_twins_card(
    client, monkeypatch
):
    """The invoice copy reads "Link", its receipt copy names card 1176.
    Untouched, the invoice borrows 1176 (Consulting). Once the operator
    assigns "Link" -> corp-2838 for this batch, the grid keeps "Link" on the
    invoice and resolves it through the assignment (Corporate Services),
    because the assignment is keyed on that exact stored string and a
    rewrite to the twin's label would have lost it silently."""
    _register_cards(client)
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated", "50.00", "2026-08-21",
                    "H0LHY2WQ-0032", payment_hint="Link"),
        _extraction("Lovable Labs Incorporated (@lovable)", "50.00", "2026-08-21",
                    "H0LHY2WQ0032", payment_hint="Visa ...1176"),
    )
    batch_id = _batch(
        client, ["Invoice-H0LHY2WQ-0032.jpg", "Receipt-2714-0234.jpg"],
        legal_entity="",
    )
    grid = _grid(client, batch_id)
    invoice = next(e for e in grid["expenses"] if "Invoice-" in e["document_id"])
    assert invoice["card"]["key"] == "cons-1176", "borrowed while unassigned"

    resp = client.post(
        f"/api/expense-batches/{batch_id}/cards",
        json={"assignments": [{"hint": "Link", "card": "corp-2838"}]},
    )
    assert resp.status_code == 200, resp.text
    for view in (resp.json()["batch"], _grid(client, batch_id)):
        invoice = next(e for e in view["expenses"] if "Invoice-" in e["document_id"])
        assert invoice["payment_hint"] == "Link"
        assert invoice["card"]["key"] == "corp-2838"
        assert invoice["legal_entity_id"] == "Corporate Services"
        assert invoice["entity_source"] == "card"
    by_ref = _csv_rows_by_reference(client, batch_id)
    assert by_ref["H0LHY2WQ-0032"]["Legal Entity"] == "Corporate Services"
    assert by_ref["H0LHY2WQ0032"]["Legal Entity"] == "Consulting"


# ── route: a collecting batch's grid and export apply it (review F5) ────


def test_a_collecting_batch_grid_and_export_apply_the_inheritance(
    client, monkeypatch
):
    """No statement, no re-match: the September 2026 shape on deploy. The
    invoice copy reads "No legal entity yet" until its receipt copy names
    card 9693 (Cloud Services); the grid and the CSV then carry that card
    and entity on the invoice row, and `n_needs_entity` drops."""
    _register_cards(client)
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated", "204.09", "2026-09-05",
                    "890D70BF-0032"),
        _extraction("Lovable Labs Incorporated (@lovable)", "204.09", "2026-09-05",
                    "890D70BF0032", payment_hint="Visa ...9693"),
        _extraction("Hetzner", "8.00", "2026-09-06", "", payment_hint=None),
    )
    batch_id = _batch(
        client,
        ["Invoice-890D70BF-0032.jpg", "Receipt-2547-4241-0916.jpg", "hetzner.jpg"],
        legal_entity="", label="September 2026",
    )
    grid = _grid(client, batch_id)
    rows = {e["document_id"]: e for e in grid["expenses"]}
    invoice = next(e for d, e in rows.items() if "Invoice-" in d)
    hetzner = next(e for d, e in rows.items() if "hetzner" in d)
    assert invoice["payment_hint"] == "Visa ...9693"
    assert invoice["card"]["key"] == "cloud-9693"
    assert invoice["legal_entity_id"] == "Cloud Services"
    assert invoice["entity_source"] == "card"
    assert hetzner["legal_entity_id"] == "", "a document with no copy is untouched"
    assert grid["summary"]["n_needs_entity"] == 1, "only the Hetzner row"
    (group,) = grid["duplicate_groups"]
    assert group["basis"] == "reference"

    by_ref = _csv_rows_by_reference(client, batch_id)
    assert by_ref["890D70BF-0032"]["Legal Entity"] == "Cloud Services"
    assert by_ref["890D70BF0032"]["Legal Entity"] == "Cloud Services"
