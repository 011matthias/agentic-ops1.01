"""Round 6 (backlog items 2-depiction + 8): the multi-category merchant
flag, the grid's `books_as` split depiction, and the category-variance
chip data.

The owner's 2026-08-19 rulings: (a) presentation may never change the
books — a receipt that genuinely books to two accounts keeps splitting in
the export, and the grid must DEPICT that split as one receipt booking to
N accounts; (b) a vendor can legitimately be multi-category — the
merchant book keeps canonicalizing the NAME but stops auto-stamping the
CATEGORY for flagged vendors, and category variance inside a batch is
surfaced per row so a human can audit it.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from expense_recon.categorize import categorize_receipts_with_registry
from expense_recon.llm.client import (
    _EXTRACT_INSTRUCTIONS,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Receipt,
)
from expense_recon.merchant_registry import (
    MerchantRegistry,
    normalize_merchants_setting,
)
from expense_recon.output.zoho_expense_export import (
    build_expense_rows,
    expense_posting_parts,
)


# ── multi_category flag: registry semantics ──────────────────────────


MERCHANTS = {
    "Mega Center": {
        "aliases": ["MEGA CENTER CONSTR LTDA"],
        "category": "Meals & Entertainment",
        "zoho_account": "E1 - Meals",
        "multi_category": True,
    },
    "Uber": {
        "aliases": ["UBER BV"],
        "category": "Travel & Transport",
        "zoho_account": "E2 - Travel",
    },
}


def test_multi_category_resolves_name_but_never_category():
    reg = MerchantRegistry(MERCHANTS)
    m = reg.resolve(None, "MEGA CENTER CONSTR LTDA")
    assert m is not None
    assert m.canonical_name == "Mega Center"
    assert m.category is None
    assert m.zoho_account is None
    # Control: an unflagged merchant keeps its default.
    u = reg.resolve(None, "UBER BV")
    assert u is not None and u.category == "Travel & Transport"


def test_normalize_preserves_multi_category_flag():
    out = normalize_merchants_setting(MERCHANTS)
    assert out["Mega Center"]["multi_category"] is True
    # Absent (or falsy) flag stays absent — existing entries keep their shape.
    assert "multi_category" not in out["Uber"]
    out2 = normalize_merchants_setting(
        {"X": {"aliases": [], "category": None, "zoho_account": None,
               "multi_category": False}}
    )
    assert "multi_category" not in out2["X"]


def _receipt(doc, vendor, total="10.00", items=()):
    return Receipt(
        document_id=doc,
        legal_entity_id="e",
        detected_date=None,
        detected_total=Decimal(total),
        detected_currency="USD",
        detected_vendor=vendor,
        detected_reference=None,
        line_items=tuple(items),
    )


def test_multi_category_vendor_is_judged_per_receipt():
    """A flagged vendor gets the canonical NAME but its receipt runs
    through the normal judgment path (the LLM is consulted); an unflagged
    vendor is registry-stamped and the LLM never sees it."""
    reg = MerchantRegistry(MERCHANTS)
    flagged = _receipt(
        "a.jpg", "MEGA CENTER CONSTR LTDA",
        items=[LineItem(description="cement bags", line_total=Decimal("10.00"),
                        quantity=None, unit_price=None)],
    )
    stamped = _receipt(
        "b.jpg", "UBER BV",
        items=[LineItem(description="trip fare", line_total=Decimal("10.00"),
                        quantity=None, unit_price=None)],
    )
    client = MockLLMClient()
    out, matches = categorize_receipts_with_registry(
        [flagged, stamped], registry=reg, client=client,
    )
    by_doc = {r.document_id: r for r in out}
    # Both resolve their canonical display name.
    assert by_doc["a.jpg"].canonical_vendor == "Mega Center"
    assert by_doc["b.jpg"].canonical_vendor == "Uber"
    # The flagged one was judged (an LLM classify call happened for it);
    # the stamped one carries the registry categorization untouched.
    assert any("cement" in str(args) for name, args in client.calls)
    assert not any("trip fare" in str(args) for name, args in client.calls)
    b_cat = by_doc["b.jpg"].line_items[0].categorization
    assert b_cat is not None and b_cat.category == "Travel & Transport"


# ── expense_posting_parts: grid and export agree by construction ─────


def _cat(category, account=None):
    return Categorization(
        category=category, zoho_account=account, confidence=1.0,
        source=ClassificationSource.LINE, reasoning="t",
    )


def _split_receipt():
    return _receipt(
        "s.jpg", "Recanto", total="30.00",
        items=[
            LineItem(description="pizza", line_total=Decimal("20.00"),
                     quantity=None, unit_price=None,
                     categorization=_cat("Meals & Entertainment")),
            LineItem(description="beer", line_total=Decimal("6.00"),
                     quantity=None, unit_price=None,
                     categorization=_cat("Meals & Entertainment")),
            LineItem(description="paint", line_total=Decimal("4.00"),
                     quantity=None, unit_price=None,
                     categorization=_cat("Professional Services")),
        ],
    )


def test_posting_parts_match_export_rows_exactly():
    r = _split_receipt()
    parts = expense_posting_parts(r)
    rows = build_expense_rows([r])
    assert [(account, str(amount)) for account, amount, _d in parts] == [
        (row[1], row[2]) for row in rows
    ]
    # And the split is what the ruling requires: sums exact, one part per
    # account, order = first appearance.
    assert [(a, str(amt)) for a, amt, _ in parts] == [
        ("Meals & Entertainment", "26.00"),
        ("Professional Services", "4.00"),
    ]


def test_posting_parts_single_account_and_bare_receipt():
    single = _receipt(
        "one.jpg", "DB AG", total="24.30",
        items=[LineItem(description="ticket", line_total=Decimal("24.30"),
                        quantity=None, unit_price=None,
                        categorization=_cat("Travel & Transport"))],
    )
    assert [(a, str(amt)) for a, amt, _ in expense_posting_parts(single)] == [
        ("Travel & Transport", "24.30")
    ]
    bare = _receipt("bare.jpg", "ANNADA", total="5.00")
    parts = expense_posting_parts(bare)
    assert len(parts) == 1
    assert parts[0][0] == "(uncategorized - assign)"
    assert str(parts[0][1]) == "5.00"


# ── item 6 rides along: vendor is the merchant, never the terminal bank ──


def test_extraction_prompt_forbids_bank_as_vendor():
    assert "never the bank" in _EXTRACT_INSTRUCTIONS


# ── web layer: books_as + is_split + category_variance on the grid ───


@pytest.fixture
def web_client(tmp_path, monkeypatch):
    fastapi = pytest.importorskip("fastapi")  # noqa: F841
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from expense_recon.web.app import create_app

    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _extraction(vendor, total="10.00"):
    return ExtractedReceipt(
        date="2026-06-02", total=total, currency="USD", vendor=vendor,
        reference=None, line_items=(), confidence=0.9, notes="",
    )


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def test_grid_variance_chip_and_books_as(web_client, monkeypatch):
    """Two receipts of one vendor reclassified into different categories
    flag BOTH rows with the variance chip; an unrelated vendor stays
    unflagged. books_as reflects the override (grid == export overlay
    order) and is_split is honest for single-account receipts."""
    _patch_ocr(
        monkeypatch,
        _extraction("Staples", "42.50"),
        _extraction("Staples", "17.00"),
        _extraction("Uber", "9.99"),
    )
    resp = web_client.post(
        "/api/expense-batches",
        files=[
            ("files", ("a.jpg", JPG, "application/octet-stream")),
            ("files", ("b.jpg", JPG + b"2", "application/octet-stream")),
            ("files", ("c.jpg", JPG + b"3", "application/octet-stream")),
        ],
        data={"legal_entity": "Corporate Services"},
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    job = web_client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job

    grid = web_client.get(f"/api/expense-batches/{batch_id}").json()
    docs = {e["vendor"]["display"]: e["document_id"] for e in grid["expenses"]}
    staples_docs = [
        e["document_id"] for e in grid["expenses"]
        if e["vendor"]["display"] == "Staples"
    ]
    assert len(staples_docs) == 2

    # Reclassify the two Staples receipts into DIFFERENT categories.
    for doc, cat in zip(
        staples_docs, ["Meals & Entertainment", "Travel & Transport"]
    ):
        r = web_client.post(
            f"/api/runs/{batch_id}/categories",
            json={"document_id": doc, "line_index": 0, "category": cat},
        )
        assert r.status_code == 200, r.text

    grid = web_client.get(f"/api/expense-batches/{batch_id}").json()
    rows = {e["document_id"]: e for e in grid["expenses"]}
    for doc in staples_docs:
        cv = rows[doc]["category_variance"]
        assert cv["varies"] is True
        assert cv["categories"] == [
            "Meals & Entertainment", "Travel & Transport"
        ]
        assert cv["n_vendor_receipts"] == 2
    uber = rows[docs["Uber"]]
    assert uber["category_variance"]["varies"] is False

    # books_as follows the override: one part, the overridden account,
    # the receipt's own total; a single-account receipt is not "split".
    first = rows[staples_docs[0]]
    assert first["is_split"] is False
    assert first["books_as"] == [
        {"account": "Meals & Entertainment", "amount": "42.50"}
    ]
