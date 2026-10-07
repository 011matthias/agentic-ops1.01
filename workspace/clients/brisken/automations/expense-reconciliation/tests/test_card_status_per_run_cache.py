"""Item 190's cost regression has its own cache now (2026-10-07).

Item 190 measured `GET /api/cards/status` at ~0.07 s before the receipt side
was added and ~2.2 s after, because every month's full Expenses-page view is
rebuilt to answer `receipt_card_counts` on every build of the roll-up, and the
roll-up's own memo (`test_card_status_memo.py`) invalidates on ANY write
anywhere in the data folder, not only a write to one of these months. During
active use that is every few seconds, so the 2.2 s lands on whoever is
looking at the months list when it does (the owner's report: the months
page's card filter tab "taking way too long to load").

The fix: each month's receipt-card counts are kept under that month's own
`month_updated_at`, so a write that invalidates the folder-level memo but
touches a DIFFERENT month does not cost this month its cached counts.

Time is controlled the same way `test_month_updated_at.py` controls it
(replacing the app's `_now_iso`): `month_updated_at` reads its candidates to
the second, so two writes inside one real wall-clock second would otherwise
look identical to the cache by coincidence, not by the behavior under test.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
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

T0 = datetime(2031, 1, 6, 9, 0, 0, tzinfo=timezone.utc)


class Clock:
    """A settable stand-in for `app._now_iso`, same output format."""

    def __init__(self, start: datetime):
        self.now = start

    def __call__(self) -> str:
        return self.now.isoformat(timespec="seconds")

    def advance(self, **delta) -> str:
        self.now += timedelta(**delta)
        return self()


@pytest.fixture
def clock(monkeypatch):
    c = Clock(T0)
    monkeypatch.setattr("expense_recon.web.app._now_iso", c)
    return c


def _receipt(vendor: str) -> ExtractedReceipt:
    return ExtractedReceipt(
        date="2026-09-10", total="42.50", currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


@pytest.fixture
def client(tmp_path, monkeypatch, clock):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(
        extraction_responses=[
            _receipt("Perplexity"), _receipt("Notion"), _receipt("Figma"),
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 8,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _month(client, label: str, i: int) -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (f"r{i}.jpg", b"\xff\xd8\xff\xe0" + bytes([i]) * 64,
                          "application/octet-stream"))],
    ))
    return batch_id


@pytest.fixture
def receipt_card_counts_calls(monkeypatch):
    """How many times a month's Expenses view is actually asked for its
    per-card receipt counts (the ~0.3 s-per-month cost item 190 measured)."""
    import expense_recon.web.app as app_module

    calls = {"n": 0}
    real = app_module.receipt_card_counts

    def counted(view):
        calls["n"] += 1
        return real(view)

    monkeypatch.setattr(app_module, "receipt_card_counts", counted)
    return calls


def test_an_unrelated_write_does_not_recount_an_unchanged_month(
    client, clock, receipt_card_counts_calls,
):
    """A new month C is a write to the data folder (bumps the folder-level
    memo's key, forcing a rebuild of the roll-up), but months A and B did
    not change, so their counts come back from the per-run cache: only C
    is counted for the first time."""
    july = _month(client, "July 2026", 1)
    clock.advance(seconds=5)
    august = _month(client, "August 2026", 2)

    resp = client.get("/api/cards/status")
    assert resp.status_code == 200, resp.text
    assert receipt_card_counts_calls["n"] == 2  # July + August, both cold

    clock.advance(seconds=5)
    september = _month(client, "September 2026", 3)

    resp = client.get("/api/cards/status")
    assert resp.status_code == 200, resp.text
    # Only September is new; July and August must not pay for its arrival.
    assert receipt_card_counts_calls["n"] == 3
    no_card = {m["run_id"] for m in resp.json()["no_card"]["months"]}
    assert no_card == {july, august, september}


def test_editing_one_month_only_recounts_that_month(
    client, clock, receipt_card_counts_calls,
):
    july = _month(client, "July 2026", 1)
    clock.advance(seconds=5)
    august = _month(client, "August 2026", 2)

    assert client.get("/api/cards/status").status_code == 200
    assert receipt_card_counts_calls["n"] == 2

    # A receipt added to July is a write to July's own data (bumps its
    # `month_updated_at`) and, like any write, invalidates the folder-level
    # memo too. August did not change.
    clock.advance(seconds=5)
    _done(client, client.post(
        f"/api/expense-batches/{july}/receipts",
        files=[("files", ("r-extra.jpg",
                          b"\xff\xd8\xff\xe0" + bytes([9]) * 64,
                          "application/octet-stream"))],
    ))

    assert client.get("/api/cards/status").status_code == 200
    # July recounts (its data changed); August's cached entry still covers it.
    assert receipt_card_counts_calls["n"] == 3
    assert august  # sanity: fixture used, not merely created
