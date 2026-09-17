"""Item 144: a company invoice paid by wire has an exit that is not a lie.

July's Tricarico invoice (BRL 27,203.34, "Payment Method: Wire Transfer",
settled outside the card by bank transfer on 2026-09-17) sat in
`needs_entity`, `needs_person` and `needs_company_or_person`, and both exits
the screen offered stated something untrue. Picking a company card says a
card paid it. Confirming "paid with a private card" says the reviewer paid
it out of her own pocket. A wire is neither, and person resolution is
card-only by the item-40 ruling, so the row could not leave `needs_person`
by any sanctioned action.

Owner ruling 2026-09-17. On a row the reviewer has settled OFF the card
system (its disposition carries a `how`):

* `needs_person` is gone, and `needs_company_or_person` follows from
  `needs_entity` alone. `summary.n_needs_person` and
  `card_review.n_needs_person` both read the `settled_off_card` the card
  pass stamps on the resolution, so the two counts of one payload agree
  about every row;
* `can_mark_private` is false, so the private-card button is not offered;
* the review reason is its own (`needs_entity_settled_outside`) and asks for
  the entity directly instead of naming a paying card.

`needs_entity` STAYS. The row carries no bill-to field: `customer`,
`legal_entity_id` and `entity_source` are all empty on the live payload and
the company name exists only inside the file name. The tool does not know
which company this is, and a card was never what was going to name it.

The negative case below is the contract, and it is what keeps this narrow:
an ordinary card-less row with no disposition is untouched.

Harness mirrors test_private_suggestion_not_a_card_r3 (fixtures copied,
never imported: a shared fixture import is an F811 in CI).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import expense_boxes, settled_off_card  # noqa: E402

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
    base = dict(date="2026-07-30", total="27203.34", currency="BRL",
                vendor="Tricarico Consultoria", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _batch(client, monkeypatch, *extractions) -> str:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "July 2026"}
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


def test_a_wire_settled_outside_the_card_has_an_answerable_exit(
    client, monkeypatch
):
    """The live July row, through `GET /api/expense-batches/{id}`: no card,
    no entity, settled outside by bank transfer."""
    batch = _batch(
        client, monkeypatch, _extraction(payment_hint="Wire Transfer"),
    )
    (row,) = _grid(client, batch)["expenses"]
    assert row["card"] is None and row["legal_entity_id"] == "", "precondition"
    doc = row["document_id"]

    resp = client.post(
        f"/api/runs/{batch}/receipts/{doc}/settled-outside",
        json={"how": "bank_transfer", "note": "Invoice prints Wire Transfer"},
    )
    assert resp.status_code == 200, resp.text

    (row,) = _grid(client, batch)["expenses"]
    assert row["settled_outside"]["how"] == "bank_transfer"
    assert [b for b in row["boxes"] if b in NEEDS] == [
        "needs_entity", "needs_company_or_person",
    ], "the company question stands; the card-only person question does not"
    assert row["can_mark_private"] is False, (
        "a wire is not the reviewer's own card either"
    )
    assert row["review"]["reason_code"] == "needs_entity_settled_outside"
    assert "paying card" not in row["review"]["reason"], (
        "the one instruction the row cannot follow"
    )
    assert "settled outside the card system" in row["review"]["reason"]

    summary = _grid(client, batch)["summary"]
    assert summary["n_needs_person"] == 0
    assert summary["n_needs_entity"] == 1
    assert summary["n_needs_company_or_person"] == 1


def test_an_ordinary_card_less_row_is_untouched(client, monkeypatch):
    """The contract. Nothing about a row with no settled-outside
    disposition moves: it still asks for a person, still offers the private
    card, still reads the generic entity sentence."""
    batch = _batch(
        client, monkeypatch,
        _extraction(vendor="Aposto Karlsruhe", total="42.50", currency="EUR",
                    payment_hint=""),
    )
    (row,) = _grid(client, batch)["expenses"]

    assert "settled_outside" not in row, "precondition: no disposition"
    assert [b for b in row["boxes"] if b in NEEDS] == list(NEEDS)
    assert row["can_mark_private"] is True
    assert row["review"]["reason_code"] == "needs_entity"
    assert "paying card" in row["review"]["reason"]
    assert _grid(client, batch)["summary"]["n_needs_person"] == 1


def test_the_two_person_counts_agree_on_every_row(client, monkeypatch):
    """EQUALITY is the property that broke, so it is what gets pinned.

    `summary.n_needs_person` counts the boxes; `card_review.n_needs_person`
    counts the card resolution. Both answer "how many rows owe a person",
    and the first draft of item 144 moved only the first: a settled-outside
    row read 0 on the summary and 1 on the strip, one payload contradicting
    itself about one row. Both now read the `settled_off_card` the card pass
    stamps, so they agree here before and after the disposition, and on the
    ordinary row beside it that never had one.

    `n_needs_entity` is asserted equal too, in the same call: the company
    question STAYS on a settled-outside row, so that pair is the control
    that the exemption did not leak into the entity half.
    """
    batch = _batch(
        client, monkeypatch,
        _extraction(payment_hint="Wire Transfer"),
        _extraction(vendor="Aposto Karlsruhe", total="42.50", currency="EUR"),
    )

    def counts() -> tuple[dict, dict]:
        grid = _grid(client, batch)
        return grid["summary"], grid["card_review"]

    summary, strip = counts()
    assert summary["n_needs_person"] == strip["n_needs_person"] == 2
    assert summary["n_needs_entity"] == strip["n_needs_entity"] == 2

    doc = _rows(client, batch)["Tricarico Consultoria"]["document_id"]
    resp = client.post(
        f"/api/runs/{batch}/receipts/{doc}/settled-outside",
        json={"how": "bank_transfer", "note": ""},
    )
    assert resp.status_code == 200, resp.text

    summary, strip = counts()
    assert summary["n_needs_person"] == strip["n_needs_person"] == 1, (
        "the settled row leaves BOTH counts, not just the boxes"
    )
    assert summary["n_needs_entity"] == strip["n_needs_entity"] == 2, (
        "and the company question stays on both"
    )

    resp = client.delete(f"/api/runs/{batch}/receipts/{doc}/settled-outside")
    assert resp.status_code == 200, resp.text
    summary, strip = counts()
    assert summary["n_needs_person"] == strip["n_needs_person"] == 2


def test_the_person_sentence_goes_quiet_only_on_a_settled_outside_row(
    client, monkeypatch
):
    """The review reason and the box answer the same question, so they may
    not disagree. Both rows below are carried all the way to otherwise-ready
    (a category and an entity) with no card, which is what leaves
    `needs_person` as the row's one remaining exception."""
    batch = _batch(
        client, monkeypatch,
        _extraction(vendor="Tricarico Consultoria", payment_hint="Wire Transfer"),
        _extraction(vendor="Aposto Karlsruhe", total="42.50", currency="EUR"),
    )
    for row in _grid(client, batch)["expenses"]:
        doc = row["document_id"]
        resp = client.put(
            f"/api/runs/{batch}/expenses/{doc}/entity",
            json={"legal_entity": "BRISKEN Consulting LLC"},
        )
        assert resp.status_code == 200, resp.text
        resp = client.post(f"/api/runs/{batch}/categories", json={
            "document_id": doc, "line_index": 0,
            "category": "Software & Subscriptions",
        })
        assert resp.status_code == 200, resp.text
    wired = _rows(client, batch)["Tricarico Consultoria"]["document_id"]
    resp = client.post(
        f"/api/runs/{batch}/receipts/{wired}/settled-outside",
        json={"how": "bank_transfer", "note": ""},
    )
    assert resp.status_code == 200, resp.text

    rows = _rows(client, batch)
    settled, ordinary = rows["Tricarico Consultoria"], rows["Aposto Karlsruhe"]
    assert "needs_person" not in settled["boxes"]
    assert settled["review"]["reason_code"] != "needs_person"
    assert "needs_person" in ordinary["boxes"]
    assert ordinary["review"]["reason_code"] == "needs_person"


@pytest.mark.parametrize(("entry", "expected"), [
    (None, False),
    ({}, False),
    ({"note": "wire sent", "at": "2026-09-17T17:00:31+00:00"}, False),
    ({"how": "bank_transfer", "note": "", "at": None}, True),
    ({"how": "other"}, True),
    ("bank_transfer", False),
])
def test_only_a_disposition_that_names_a_tender_counts(entry, expected):
    """`settled_off_card` is the one predicate the card pass, the review
    sentence and the boxes read. A half-written entry with no `how` is not a
    disposition, and neither is a value that is not a mapping at all."""
    assert settled_off_card(entry) is expected


def test_the_box_rule_is_the_entity_alone_once_a_row_is_settled_outside():
    """`expense_boxes` directly: `needs_company_or_person` follows from
    `needs_entity` alone, so a settled-outside row with an entity is in no
    box of the three."""
    res = {"entity": "", "person": "", "private": False}
    boxes = expense_boxes(
        categorized=True, review_state="check", res=res, needs_cost_center=False,
        image_missing=False, render_failed=False, settled_outside=True,
    )
    assert [b for b in boxes if b in NEEDS] == [
        "needs_entity", "needs_company_or_person",
    ]
    resolved = expense_boxes(
        categorized=True, review_state="ready",
        res={"entity": "BRISKEN Consulting LLC", "person": "", "private": False},
        needs_cost_center=False, image_missing=False, render_failed=False,
        settled_outside=True,
    )
    assert [b for b in resolved if b in NEEDS] == []
