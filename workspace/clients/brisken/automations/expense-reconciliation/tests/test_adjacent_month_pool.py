"""The adjacent-month candidate pool (backlog item 61).

A receipt is filed by the month PRINTED ON IT; a charge lands in the
statement that BILLED it. Those two boundaries do not line up. Chase opens
August's workbook on 07-31 and July's on 06-30, so a subscription invoiced
on the last day of a month posts on the 1st of the next statement while its
receipt is already one batch away, and the charge renders as "no receipt
found" forever.

The month's candidate pool therefore spans its NEIGHBOURS the way it already
spans trips (R4b): a receipt in the month either side joins the pool when its
date falls inside THIS statement's own period, travels through the same
`borrowed_receipts` / `receipt_sources` snapshot keys, and is arbitrated by
the same `receipt_claims` table, so one receipt still settles exactly one
charge.

What is under test:

1. **The borrow happens and is named**, on both sides: the month's row says
   which neighbour settled it, the candidate says where the receipt lives,
   and the neighbour's own grid says which month took it.
2. **The period, not the calendar, decides.** The same fixture with the
   receipt dated inside its own month and nothing is borrowed. This is the
   differential probe: one field moves, the answer moves.
3. **Only the months either side lend.** A batch two months away holding a
   receipt dated squarely inside this period contributes nothing.
4. **One receipt never settles two charges**, when the two borrowers are
   months rather than a month and a trip.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

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
from expense_recon.web.service import (  # noqa: E402
    ADJACENT_FALLBACK_DAYS,
    statement_period_for_month,
)
from expense_recon.web.store import RunRow, RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("71.64"),
                reasoning="same purchase",
            )
        ] * 40,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _receipt(vendor: str, total: str, date: str) -> ExtractedReceipt:
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _month(client, label: str, *, fname: str) -> str:
    """A company month created empty (the 2026-09-08 decoupling), with one
    receipt added through the add route. `fname` differs per month so the
    position-prefixed document ids do not collide."""
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(
        f"/jobs/{resp.json()['job_id']}"
    ).json()["status"] == "done"
    added = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (fname, JPG, "application/octet-stream"))],
    )
    assert added.status_code == 200, added.text
    assert client.get(
        f"/jobs/{added.json()['job_id']}"
    ).json()["status"] == "done"
    return batch_id


def _csv(*rows: tuple[str, str, str]) -> bytes:
    body = "".join(f"{d},{a},{v}\n" for d, a, v in rows)
    return ("Date,Amount,Vendor\n" + body).encode()


def _attach(client, batch_id: str, body: bytes):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statement.csv", body, "application/octet-stream",
        )},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
        },
    )
    assert resp.status_code == 200, resp.text
    assert client.get(
        f"/jobs/{resp.json()['job_id']}"
    ).json()["status"] == "done"


def _doc_id(client, batch_id: str) -> str:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        return (store.get_run(batch_id).snapshot or {})["receipts"][0][
            "document_id"
        ]


# The August statement the fixtures share: its period runs 07-31..08-31,
# exactly as Chase cuts it live, and its 08-01 Google charge is the one
# whose receipt was printed the day before.
AUGUST_CSV = _csv(
    ("07/31/2026", "80.28", "OPENAI"),
    ("08/01/2026", "71.64", "GOOGLE WORKSPACE"),
    ("08/15/2026", "25.00", "LOVABLE"),
)


def _august_view(client, august: str) -> dict:
    resp = client.get(f"/api/runs/{august}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _google_row(view: dict) -> dict:
    return next(
        r for r in view["rows"] if r["vendor"] == "GOOGLE WORKSPACE"
    )


# ── the borrow ───────────────────────────────────────────────────────


def test_august_settles_its_first_day_charge_from_julys_receipt(
    client, monkeypatch
):
    """The live shape end to end: the Google receipt printed 07-31 sits in
    July's batch, the charge posts 08-01 on August's statement, and August
    settles it from July's pool. Both payloads name each other, and August's
    own receipt count never absorbs the borrowed one."""
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-07-31"),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    july = _month(client, "July 2026", fname="jul.jpg")
    august = _month(client, "August 2026", fname="aug.jpg")
    borrowed_doc = _doc_id(client, july)

    _attach(client, august, AUGUST_CSV)

    view = _august_view(client, august)
    row = _google_row(view)
    assert row["chosen_document_id"] == borrowed_doc, (
        "July's receipt never reached August's matcher"
    )
    # The claim is keyed to the receipt's HOME month, not the borrower, so
    # `receipt_source_run` resolves a reviewer's later verdict to the same
    # row and one receipt cannot be claimed twice under two keys.
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        claims = store.get_claims_by_run(august)
    borrowed_claim = next(
        c for c in claims if c["document_id"] == borrowed_doc
    )
    assert borrowed_claim["receipt_run_id"] == july
    assert borrowed_claim["transaction_id"] == row["transaction_id"]
    # The row names the neighbour, shaped as an adjacent borrow: no trip id,
    # an explicit kind, so the badge cannot read it as a trip.
    assert row["settled_by"] == {
        "run_id": july, "label": "July 2026", "kind": "adjacent",
    }
    # The candidate names where the receipt lives, whether or not it wins.
    cand = next(
        c for c in row["candidates"] if c["document_id"] == borrowed_doc
    )
    assert cand["from_batch"] == row["settled_by"]
    assert view["summary"]["n_adjacent_borrowed"] == 1
    # August's own pool is untouched: one receipt, and the borrowed copy is
    # never one of August's unmatched receipts.
    assert view["summary"]["n_receipts"] == 1
    assert all(
        r.get("document_id") != borrowed_doc
        for r in view["unmatched_receipts"]
    )
    # A row settled from August's own pool says nothing about a batch.
    own = next(r for r in view["rows"] if r["vendor"] == "LOVABLE")
    assert "settled_by" not in own
    assert all("from_batch" not in c for c in own["candidates"])

    # July's side, with no new code: the claims table already names the
    # month that took the receipt.
    grid = client.get(f"/api/expense-batches/{july}").json()
    exp = next(
        e for e in grid["expenses"] if e["document_id"] == borrowed_doc
    )
    assert exp["settled_by"]["run_id"] == august
    assert exp["settled_by"]["label"] == "August 2026"


def test_a_receipt_inside_its_own_month_is_not_borrowed(
    client, monkeypatch
):
    """The differential probe: the same fixture with July's receipt dated
    07-10 instead of 07-31. It is outside August's statement period, so
    nothing is borrowed and the 08-01 charge keeps its empty hands. A borrow
    that fired here would be pulling a whole neighbouring month into the
    pool, which is the failure this period rule exists to prevent."""
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-07-10"),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    july = _month(client, "July 2026", fname="jul.jpg")
    august = _month(client, "August 2026", fname="aug.jpg")
    borrowed_doc = _doc_id(client, july)

    _attach(client, august, AUGUST_CSV)

    view = _august_view(client, august)
    row = _google_row(view)
    assert row["effective_bucket"] == "unmatched"
    assert not row["candidates"]
    assert "settled_by" not in row
    assert view["summary"]["n_adjacent_borrowed"] == 0
    assert all(
        c["document_id"] != borrowed_doc
        for r in view["rows"] for c in r["candidates"]
    )


def test_only_the_month_either_side_lends(client, monkeypatch):
    """Two months away is not adjacent. June's receipt is dated squarely
    inside August's period, so only the label rule keeps it out."""
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-07-31"),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    june = _month(client, "June 2026", fname="jun.jpg")
    august = _month(client, "August 2026", fname="aug.jpg")
    far_doc = _doc_id(client, june)

    _attach(client, august, AUGUST_CSV)

    view = _august_view(client, august)
    assert view["summary"]["n_adjacent_borrowed"] == 0
    assert _google_row(view)["effective_bucket"] == "unmatched"
    assert all(
        c["document_id"] != far_doc
        for r in view["rows"] for c in r["candidates"]
    )


def test_one_receipt_never_settles_two_neighbouring_months(
    client, monkeypatch
):
    """The cross-batch claim, months only. June's statement runs to 07-31
    and August's opens on it, so both are adjacent to July and both could
    take the same 07-31 receipt. The first settles it; the second's charge
    stays unmatched rather than double-claiming the receipt."""
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-07-31"),
        _receipt("Anthropic", "52.00", "2026-06-15"),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    july = _month(client, "July 2026", fname="jul.jpg")
    june = _month(client, "June 2026", fname="jun.jpg")
    august = _month(client, "August 2026", fname="aug.jpg")
    borrowed_doc = _doc_id(client, july)

    _attach(client, june, _csv(
        ("06/15/2026", "52.00", "ANTHROPIC"),
        ("07/31/2026", "71.64", "GOOGLE WORKSPACE"),
    ))
    june_view = client.get(f"/api/runs/{june}").json()
    june_row = next(
        r for r in june_view["rows"] if r["vendor"] == "GOOGLE WORKSPACE"
    )
    assert june_row["chosen_document_id"] == borrowed_doc
    assert june_view["summary"]["n_adjacent_borrowed"] == 1

    _attach(client, august, AUGUST_CSV)
    aug_view = _august_view(client, august)
    assert aug_view["summary"]["n_adjacent_borrowed"] == 0
    assert _google_row(aug_view)["effective_bucket"] == "unmatched"
    assert all(
        c["document_id"] != borrowed_doc
        for r in aug_view["rows"] for c in r["candidates"]
    ), "the receipt June settled must never reach August's pool"


# ── the period ───────────────────────────────────────────────────────


class _Tx:
    def __init__(self, d):
        self.transaction_date = d


def _run(label: str) -> RunRow:
    return RunRow(
        run_id="r", created_at="", label=label, operator=None, summary={},
        snapshot={}, config={}, work_dir="", llm_enabled=False,
        has_coa=False,
    )


def test_the_period_comes_from_the_charges_not_the_calendar():
    """No calendar rule predicts a workbook that opens on 07-31; the
    charges are the only source that knows."""
    lo, hi = statement_period_for_month(
        _run("August 2026"),
        [_Tx(date(2026, 7, 31)), _Tx(date(2026, 8, 31)), _Tx(None)],
    )
    assert (lo, hi) == (date(2026, 7, 31), date(2026, 8, 31))


def test_a_month_with_no_statement_falls_back_to_its_label():
    """A month that has not been given a statement has no charges to read a
    period off. The label's calendar month plus a fixed margin keeps the
    helper answerable; an unlabelled one has no period at all."""
    margin = timedelta(days=ADJACENT_FALLBACK_DAYS)
    lo, hi = statement_period_for_month(_run("August 2026"), [])
    assert lo == date(2026, 8, 1) - margin
    assert hi == date(2026, 8, 31) + margin
    # December rolls the year rather than overflowing the month.
    _, dec_hi = statement_period_for_month(_run("December 2026"), [])
    assert dec_hi == date(2026, 12, 31) + margin
    # A label that is a timestamp names no month, so there is no period.
    assert statement_period_for_month(
        _run("chase-2838 2026-07-24"), []
    ) is None
