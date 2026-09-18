"""The card-review strip counts the same rows the boxes do (backlog item
146).

`summary.n_needs_entity` / `n_needs_person` / `n_suggested_private` /
`n_private` are box counts (`n_box`), and `expense_boxes` puts a decided
copy in NO box by item 94's owner ruling of 2026-09-17: a copy writes no
CSV row, no listing row, no reimbursement and no cost-center bucket, so
nothing done to its company, person, cost center or private flag changes
the month. `build_card_review` computed its four twins straight off the
resolution, every receipt in the month included, so one payload answered
the same question twice and Criss saw both answers at once: live July 2026
read `summary.n_needs_person` 13 beside `card_review.n_needs_person` 15,
and `n_needs_entity` 14 beside 16, the gap being exactly the two decided
copies (Aposto Karlsruhe, Lovable Labs Incorporated).

The month here is the August shape in miniature that `test_copies_out_of_
totals.py` drives, with two changes that make every one of the four
counters load-bearing: the month declares no legal entity (so no row has
one), and both Lovable documents print a card number no registered card
carries (so the chain refuses the hint and suggests a private card). The
copy is therefore a row with no entity, no person and a private
suggestion: each of the four counters would read one too high without the
exclusion.

The grouping is deliberately NOT excluded and is asserted here too. A
decided copy is still a row on screen with a payment hint somebody can
assign, so `unresolved_hints`, `n_unresolved_rows`, `n_no_hint` and
`n_resolved_rows` keep counting it; none of them has a `summary` twin to
disagree with.

Route-level through the FastAPI app, the way `test_copies_out_of_totals.py`
drives item 94. Asserting agreement alone is what let the item-144 test
pass on a fixture holding no copy at all, so every count below is also
asserted at its absolute value, and the copy's own existence is asserted
before the counts are read.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
FILES = ["Invoice-HMVWDWIL.jpg", "Receipt-2167-5718.jpg", "train.jpg"]
# A card number no month here registers, so `resolve_hinted_card_ex`
# refuses it and the row reads `suggested_private` (item 41).
HINT = "VISA 4242"
# The four strip counters that have a `summary` twin. Item 146 is the
# claim that each pair reads the same rows.
TWINS = (
    "n_needs_entity", "n_needs_person", "n_suggested_private", "n_private",
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(vendor, total, day, currency="USD", hint=None):
    return ExtractedReceipt(
        date=day, total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint,
    )


def _wire(monkeypatch):
    """The Lovable 15.00 invoice and its receipt (one purchase, two
    documents, one card number printed on both), plus one ordinary EUR
    expense that prints no payment method at all."""
    mock = MockLLMClient(
        extraction_responses=[
            _extraction("Lovable Labs Incorporated", "15.00", "2026-08-31",
                        hint=HINT),
            _extraction("Lovable Labs Incorporated", "15.00", "2026-08-31",
                        hint=HINT),
            _extraction("Petit Train Touristique de Colmar", "32.00",
                        "2026-08-23", currency="EUR"),
        ],
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


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _batch(client):
    """A month with NO legal entity declared, so no row inherits one and
    `needs_entity` is a real population rather than a structural zero."""
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "", "label": "August 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + str(i).encode(), "application/octet-stream"))
            for i, name in enumerate(FILES)
        ],
    ))
    return batch_id


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _rows(grid) -> dict:
    return {e["document_id"]: e for e in grid["expenses"]}


def _copy_id(grid) -> str:
    (copy,) = [
        e["document_id"] for e in grid["expenses"]
        if (e.get("duplicate") or {}).get("is_extra")
    ]
    return copy


def _assert_holds_a_decided_copy(grid) -> str:
    """The fixture's premise, asserted before any count is read off it. A
    refactor that stops producing a copy here must redden this test rather
    than leave the counts below agreeing about nothing."""
    copy_id = _copy_id(grid)
    row = _rows(grid)[copy_id]
    assert row["counts_in_total"] is False
    assert row["boxes"] == []
    summary = grid["summary"]
    assert summary["n_copies_set_aside"] == 1
    assert (summary["n_receipts"], summary["n_expenses"]) == (3, 2)
    assert len(grid["expenses"]) == 3
    return copy_id


def _assert_twins_agree(grid, expected: dict) -> None:
    """Both halves of item 146. Agreement alone passes when a pair is
    wrongly zero, so each count is pinned to its absolute value too."""
    strip = {n: grid["card_review"][n] for n in TWINS}
    assert strip == {n: grid["summary"][n] for n in TWINS}
    assert strip == expected


def _assert_grouping_keeps_the_copy(grid, copy_id: str) -> None:
    """The boundary: the assignment surface still shows the copy. Three
    receipts, two printing one hint and one printing none."""
    strip = grid["card_review"]
    (group,) = strip["unresolved_hints"]
    assert group["hint"] == HINT
    assert group["n_rows"] == 2
    assert copy_id in group["documents"]
    assert strip["n_unresolved_rows"] == 2
    assert strip["n_no_hint"] == 1
    assert strip["n_resolved_rows"] == 0


def test_the_strip_counts_the_rows_the_boxes_count(client, monkeypatch):
    """The decided copy is out of all four counters.

    Three receipts, one of them a decided copy. Nothing carries an entity
    (the month declares none) and nothing carries a person (no card is
    registered, and person resolution is card-only by item 40), so the two
    rows that count are both in `needs_entity` and `needs_person`. The two
    Lovable documents print a card number no registered card carries, so
    each is `suggested_private`; the train receipt prints no payment method
    and is not. Nothing is confirmed private yet.

    Expected: 2, 2, 1, 0. Without the exclusion the strip reads 3, 3, 2, 0.
    """
    _wire(monkeypatch)
    grid = _grid(client, _batch(client))
    (group,) = grid["duplicate_groups"]
    assert group["verdict"] == "copy" and group["decided_by"] == "tool"
    copy_id = _assert_holds_a_decided_copy(grid)

    # The copy is exactly the row that would inflate each counter.
    copy_row = _rows(grid)[copy_id]
    assert copy_row["legal_entity_id"] == ""
    assert not copy_row["person"]
    assert copy_row["suggested_private"] is True

    _assert_twins_agree(grid, {
        "n_needs_entity": 2,
        "n_needs_person": 2,
        "n_suggested_private": 1,
        "n_private": 0,
    })
    _assert_grouping_keeps_the_copy(grid, copy_id)


def test_a_copy_confirmed_private_is_out_of_n_private_too(
    client, monkeypatch
):
    """`n_private` is the fourth twin and needs a confirmed private row to
    be anything but zero, which the tool never stamps by itself (item 41:
    it suggests, the operator confirms). Confirming it on the COPY is the
    only way to reach that state on a row the month does not count.

    The confirmation moves the copy out of the other three populations
    (private needs no entity, its person IS `reimburse_to`, and a
    confirmed row is no longer merely suggested), so those three would
    agree here even unfixed. `n_private` is the one under test: the copy
    carries the flag, the strip must not count it.

    Expected: 2, 2, 1, 0, with the copy row itself reading private.
    """
    _wire(monkeypatch)
    batch_id = _batch(client)
    copy_id = _assert_holds_a_decided_copy(_grid(client, batch_id))

    resp = client.post(
        f"/api/runs/{batch_id}/expenses/{copy_id}/private",
        json={"private": True, "reimburse_to": "Cristiane Cavalcanti"},
    )
    assert resp.status_code == 200, resp.text

    grid = _grid(client, batch_id)
    assert _assert_holds_a_decided_copy(grid) == copy_id
    copy_row = _rows(grid)[copy_id]
    assert copy_row["private"] is True
    assert copy_row["reimburse_to"] == "Cristiane Cavalcanti"
    assert copy_row["suggested_private"] is False

    _assert_twins_agree(grid, {
        "n_needs_entity": 2,
        "n_needs_person": 2,
        "n_suggested_private": 1,
        "n_private": 0,
    })
    # Still an assignable row on the strip: the private flag says who paid,
    # not which card, and the hint is still unresolved.
    _assert_grouping_keeps_the_copy(grid, copy_id)


def test_not_a_copy_brings_the_document_back_into_all_four(
    client, monkeypatch
):
    """The exclusion is keyed on the copy DECISION, not on the document.
    "Not a copy" puts the row back in every box it qualifies for (item 94),
    and each strip counter rises with its twin: 3, 3, 2, 0."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    grid = _grid(client, batch_id)
    copy_id = _assert_holds_a_decided_copy(grid)
    (group,) = grid["duplicate_groups"]

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": group["group_id"], "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text

    grid = _grid(client, batch_id)
    assert grid["summary"]["n_expenses"] == 3
    assert grid["summary"]["n_copies_set_aside"] == 0
    assert "counts_in_total" not in _rows(grid)[copy_id]

    _assert_twins_agree(grid, {
        "n_needs_entity": 3,
        "n_needs_person": 3,
        "n_suggested_private": 2,
        "n_private": 0,
    })
    _assert_grouping_keeps_the_copy(grid, copy_id)
