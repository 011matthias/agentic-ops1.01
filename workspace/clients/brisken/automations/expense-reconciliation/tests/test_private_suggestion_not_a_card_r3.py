"""Residual R3: a wire is not a card, so it suggests no private card.

Item 41 suggests a private expense when a receipt's payment method resolves
to no registered company card: the question is "which card paid this, and if
it was yours, who do we reimburse". The rule fired on ANY non-empty payment
method, so July's restored Tricarico invoice (BRL 27,203.34, "Payment Method:
Wire Transfer", recorded as settled outside the card by bank transfer on
2026-09-17) read `suggested_private` and asked Criss to name a private card
for a bank payment. The tool's own ruling of 2026-09-15 calls a settled-outside
receipt real company spend; the same words already offer "paid by bank
transfer" on the unmatched-receipt chip.

Item 144 (owner ruling 2026-09-17) then settled what this round left open,
and the two halves are told apart by WHO said no card paid it. A printed
tender is the document's claim about itself and moves nothing but the
suggestion. The reviewer's own settled-outside disposition moves the exits
too: the option to confirm a private card goes (a wire is not her card
either), and the `needs_person` box goes (person resolution is card-only,
so on a row no card paid it is an ask nobody can answer).

Pinned here:
* a bank-transfer / wire tender, and a receipt the reviewer settled outside
  the card, suggest no private card;
* on a TENDER alone, nothing else moves: `can_mark_private` stays true and
  the row keeps all three of `needs_entity`, `needs_person`,
  `needs_company_or_person`;
* on a settled-outside DISPOSITION, `can_mark_private` is false and
  `needs_person` is gone, while `needs_entity` (and so
  `needs_company_or_person`) stands: the company is genuinely unknown, and
  a card was never going to be what named it;
* a card tender no company card matches still suggests private (VISA, Cash,
  and the Brazilian POS word TEF, which is a card payment on a cupom fiscal).

Harness mirrors test_private_expense (fixtures copied, never imported: a
shared fixture import is an F811 in CI).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
NEEDS = ("needs_entity", "needs_person", "needs_company_or_person")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _batch(client, monkeypatch, *extractions) -> str:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"}
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (f"r{i}.jpg", JPG + bytes([i]), "application/octet-stream"))
               for i in range(len(extractions))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _rows(client, batch_id) -> dict:
    return {e["vendor"]["display"]: e for e in _grid(client, batch_id)["expenses"]}


def test_a_bank_transfer_tender_suggests_no_private_card(client, monkeypatch):
    """The live row's shape: an invoice printing "Payment Method: Wire
    Transfer", no company card in sight."""
    batch = _batch(
        client, monkeypatch,
        _extraction(vendor="Tricarico Consultoria", total="27203.34",
                    currency="BRL", payment_hint="Wire Transfer"),
    )
    (row,) = _grid(client, batch)["expenses"]

    assert row["suggested_private"] is False
    assert row["review"]["reason_code"] == "needs_entity", (
        "the row still asks which company books it, in the tool's own words"
    )
    assert "suggested_private" not in row["boxes"]
    assert [b for b in row["boxes"] if b in NEEDS] == list(NEEDS), (
        "a printed tender alone is the document's claim about itself: the "
        "company / person question is unchanged (item 144 moves this only "
        "once the REVIEWER settles the row off the card)"
    )
    assert row["can_mark_private"] is True, (
        "the option stays: the tool stops SUGGESTING a private card, it does "
        "not refuse one"
    )
    summary = _grid(client, batch)["summary"]
    assert summary["n_suggested_private"] == 0
    assert summary["n_needs_company_or_person"] == 1


def test_a_card_tender_no_company_card_matches_still_suggests_private(
    client, monkeypatch
):
    """The negative case, and the reason the rule is narrow. VISA and Cash
    are money someone may have paid out of pocket; TEF is a card payment on a
    Brazilian cupom fiscal (July's Fenix groceries receipt prints TEF and
    settles a card charge), whatever the settled-outside chip makes of the
    word. This harness has NO card registry: once the registry's cards are
    Visa credit cards, VISA CREDIT and TEF stop suggesting (owner ruling
    2026-09-24, pinned in test_card_type_not_private)."""
    batch = _batch(
        client, monkeypatch,
        _extraction(vendor="Aposto Karlsruhe", payment_hint="VISA CREDIT"),
        _extraction(vendor="Bezerra LTDA", total="8.00", payment_hint="Cash"),
        _extraction(vendor="Supermercado Fenix", total="325.88", payment_hint="TEF"),
    )
    rows = _rows(client, batch)

    for vendor in ("Aposto Karlsruhe", "Bezerra LTDA", "Supermercado Fenix"):
        assert rows[vendor]["suggested_private"] is True, vendor
        assert rows[vendor]["review"]["reason_code"] == "suggested_private", vendor
    assert _grid(client, batch)["summary"]["n_suggested_private"] == 3


def test_a_receipt_settled_outside_the_card_suggests_no_private_card(
    client, monkeypatch
):
    """The reviewer has already answered the question the suggestion asks:
    no card paid this one."""
    batch = _batch(
        client, monkeypatch,
        _extraction(vendor="Brauhaus Kuehler Krug", total="140.00",
                    payment_hint="EC-Karte"),
    )
    (row,) = _grid(client, batch)["expenses"]
    assert row["suggested_private"] is True, "precondition: a card tender"
    doc = row["document_id"]

    resp = client.post(
        f"/api/runs/{batch}/receipts/{doc}/settled-outside",
        json={"how": "bank_transfer", "note": "wire sent 2026-08-11"},
    )
    assert resp.status_code == 200, resp.text

    (row,) = _grid(client, batch)["expenses"]
    assert row["settled_outside"]["how"] == "bank_transfer"
    assert row["suggested_private"] is False
    assert "suggested_private" not in row["boxes"]
    # Item 144: the reviewer's own disposition, unlike a printed tender,
    # takes both card-shaped exits away. Pinned in full by
    # test_bank_transfer_exit_item_144.
    assert [b for b in row["boxes"] if b in NEEDS] == [
        "needs_entity", "needs_company_or_person",
    ]
    assert row["can_mark_private"] is False

    resp = client.delete(f"/api/runs/{batch}/receipts/{doc}/settled-outside")
    assert resp.status_code == 200, resp.text
    (row,) = _grid(client, batch)["expenses"]
    assert row["suggested_private"] is True, "undone, the question comes back"
    assert row["can_mark_private"] is True, "and so does the private option"
    assert [b for b in row["boxes"] if b in NEEDS] == list(NEEDS)
