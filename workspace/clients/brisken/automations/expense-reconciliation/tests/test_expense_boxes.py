"""Item 84: the Expenses view's boxes open the expenses they count.

Route-level through `GET /api/expense-batches/{id}` on a seeded month:

* every row names the boxes it belongs to (`expenses[].boxes[]`), and every
  box count on the summary is the number of rows carrying that box;
* Categorized uses the count's own rule, so a two-line receipt whose second
  line has no category shows a category and sits in `uncategorized`
  (July 2026: the tile read 49 while 51 rows showed a category);
* a receipt the app can show is not missing its image, whatever extraction
  recorded (July 2026: 2 rows read "missing" and all opened);
* MISSING ENTITY and NEEDS PERSON are one box, `needs_company_or_person`,
  holding rows that miss either (owner ruling 2026-09-16), while
  `n_needs_entity` and `n_needs_person` keep their questions.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.types import (  # noqa: E402
    Categorization,
    ClassificationSource,
    LineItem,
    MatchOutcome,
    Receipt,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.service import EXPENSE_BOXES, expense_boxes  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

OFFICE = "Office Supplies & Consumables"


def _line(category: str | None) -> LineItem:
    return LineItem(
        description="item", line_total=Decimal("10"),
        categorization=(
            Categorization(
                category=category, zoho_account="6100 Office Supplies",
                confidence=0.9, source=ClassificationSource.LINE,
            )
            if category else None
        ),
    )


def _rc(doc: str, *, lines=(), entity: str = "", **kw) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id=entity, detected_date=date(2026, 7, 10),
        detected_total=Decimal("20"), detected_currency="USD",
        detected_vendor="Staples", line_items=tuple(lines), **kw,
    )


RECEIPTS = [
    _rc("two_lines", lines=(_line(OFFICE), _line(None))),
    _rc("all_lines", lines=(_line(OFFICE), _line(OFFICE)), receipt_name="all.jpg"),
    _rc("no_lines"),
    # a file on disk, but extraction recorded no image reference
    _rc("on_disk.pdf", lines=(_line(OFFICE),)),
    # neither a file nor a reference: the one row really missing its image
    _rc("nothing", lines=(_line(OFFICE),), entity="Corporate Services"),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _seed(client) -> dict:
    work_dir = client._data_root / "run84"
    (work_dir / "receipts").mkdir(parents=True)
    (work_dir / "receipts" / "on_disk.pdf").write_bytes(b"%PDF-1.4 seeded")
    snapshot = snapshot_to_dict(
        [], RECEIPTS,
        MatchOutcome(unmatched_receipts=[r.document_id for r in RECEIPTS]), [],
    )
    store = RunStore(client._data_root / "recon-web.sqlite")
    store.create_run(
        run_id="run84", created_at="2026-07-31T00:00:00", label="July 2026",
        operator=None, summary={}, snapshot=snapshot,
        config={"mode": "expense_generation"},
        work_dir=str(work_dir), llm_enabled=False, has_coa=False,
    )
    store.close()
    resp = client.get("/api/expense-batches/run84")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _boxes(view) -> dict[str, list[str]]:
    return {e["document_id"]: e["boxes"] for e in view["expenses"]}


def test_every_box_count_is_the_rows_that_carry_the_box(client):
    view = _seed(client)
    s = view["summary"]
    for box in EXPENSE_BOXES:
        if f"n_{box}" in s:
            assert s[f"n_{box}"] == sum(
                1 for e in view["expenses"] if box in e["boxes"]
            ), box


def test_categorized_is_every_line_not_the_shown_category(client):
    view = _seed(client)
    row = next(e for e in view["expenses"] if e["document_id"] == "two_lines")
    assert (row["posting_category"] or {}).get("category"), "the row shows a category"
    boxes = _boxes(view)
    assert "uncategorized" in boxes["two_lines"]
    assert "categorized" not in boxes["two_lines"]
    assert "uncategorized" in boxes["no_lines"]
    assert {d for d, b in boxes.items() if "categorized" in b} == {
        "all_lines", "on_disk.pdf", "nothing",
    }
    assert (view["summary"]["n_categorized"], view["summary"]["n_uncategorized"]) == (3, 2)


def test_a_receipt_the_app_can_show_is_not_missing_its_image(client):
    view = _seed(client)
    by_doc = {e["document_id"]: e for e in view["expenses"]}
    assert by_doc["on_disk.pdf"]["receipt_image_available"] is True
    assert {d for d, b in _boxes(view).items() if "missing_receipt_image" in b} == {
        "two_lines", "no_lines", "nothing",
    }
    assert view["summary"]["n_missing_receipt_image"] == 3


def test_missing_company_and_missing_person_are_one_box(client):
    """`nothing` carries the batch's company but no person, so it misses one
    of the two: it is in the merged box and in `needs_person` only."""
    view = _seed(client)
    boxes = _boxes(view)
    s = view["summary"]
    assert "needs_entity" not in boxes["nothing"]
    assert "needs_person" in boxes["nothing"]
    assert "needs_company_or_person" in boxes["nothing"]
    assert s["n_needs_company_or_person"] == 5
    assert s["n_needs_entity"] == 4
    assert s["n_needs_person"] == 5


def test_the_run_payload_counts_a_missing_image_by_the_same_rule(client):
    """One name, one question on both payloads: the workbench summary of a
    month with a statement counts the same three rows."""
    from expense_recon.matching.types import Transaction

    work_dir = client._data_root / "run84s"
    (work_dir / "receipts").mkdir(parents=True)
    (work_dir / "receipts" / "on_disk.pdf").write_bytes(b"%PDF-1.4 seeded")
    tx = Transaction(
        transaction_id="t1", legal_entity_id="", account_id="card-2838",
        transaction_date=date(2026, 7, 10), posting_date=None,
        amount=Decimal("999"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="ELSEWHERE",
    )
    snapshot = snapshot_to_dict(
        [tx], RECEIPTS,
        MatchOutcome(
            unmatched_transactions=["t1"],
            unmatched_receipts=[r.document_id for r in RECEIPTS],
        ), [],
    )
    store = RunStore(client._data_root / "recon-web.sqlite")
    store.create_run(
        run_id="run84s", created_at="2026-07-31T00:00:00", label="July 2026",
        operator=None, summary={}, snapshot=snapshot,
        config={"mode": "expense_generation"},
        work_dir=str(work_dir), llm_enabled=False, has_coa=False,
    )
    store.close()
    view = client.get("/api/runs/run84s").json()
    assert "rows" in view, "the workbench payload"
    assert view["summary"]["n_missing_receipt_image"] == 3


@pytest.mark.parametrize(("res", "expected"), [
    ({"entity": "", "person": "", "private": False}, {"needs_entity", "needs_person"}),
    ({"entity": "", "person": "Dirk", "private": True}, set()),
    ({"entity": "Corp", "person": "", "private": False}, {"needs_person"}),
    ({"entity": "Corp", "person": "Dirk"}, set()),
])
def test_the_merged_box_is_either_half(res, expected):
    boxes = expense_boxes(
        categorized=True, review_state="ready", res=res,
        needs_cost_center=False, image_missing=False, render_failed=False,
    )
    halves = {b for b in boxes if b in ("needs_entity", "needs_person")}
    assert halves == expected
    assert ("needs_company_or_person" in boxes) == bool(expected)
