"""Item 145: no page of either client-facing PDF carries a banned dash form.

The house deliverable standard (`.claude/rules/rule_deliverables.md`) bans
every dash form from a client-facing document: the em-dash character, the
`&mdash;` entity, and ` -- ` used as a substitute for one. Both documents
broke it in the one string a reader sees first. Live on 2026-09-17 (Fly
v171), page 1 of August's reconciliation joined "Reconciliation" to its
month with an em-dash, and the month and trip reports titled themselves the
same way.

The three titles are built in `service.py`, not in the builders, which is why
no builder test saw them: every existing PDF test passes its own `title=`.
So these tests drive the ROUTES, where the real title is composed, extract
each page's text, and read it for all three banned forms.

Each test also pins the title it expects to read. A page-text assertion of
the "nothing contains X" shape passes on a document that renders nothing at
all, so the positive half is what keeps it honest.
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("pypdf")
pytest.importorskip("reportlab")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from tests.test_feedback_notes_52_53_62_63 import (  # noqa: E402
    CARDS,
    _attach,
    _done,
    _expense,
    _extraction,
    _pick_card,
    _wire,
)
from tests.test_trip_settlement import (  # noqa: E402
    _create_trip,
    _create_trip_batch,
)
from tests.test_trip_settlement import _extraction as _trip_extraction  # noqa: E402
from tests.test_trip_settlement import _wire as _trip_wire  # noqa: E402

# Every form the deliverable standard bans, by the name a failure prints.
# The em-dash is BUILT, not typed: this file sits under a client path, where
# `em-dash-strip-gate.py` rewrites the character on Write and Edit. A literal
# here would be stripped by a later pass and the check would go quietly
# vacuous, which is the one failure a guard must not have.
BANNED = {
    "em-dash U+2014": chr(0x2014),
    "&mdash; entity": "&mdash;",
    "double hyphen": " -- ",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


def _png(color: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (300, 400), color).save(buf, format="PNG")
    return buf.getvalue()


def _pages(client, path: str) -> list[str]:
    """The text a reader gets off each page of a downloaded document."""
    resp = client.get(path)
    assert resp.status_code == 200, resp.text
    return [
        (page.extract_text() or "")
        for page in PdfReader(io.BytesIO(resp.content)).pages
    ]


def _dashes(pages: list[str]) -> list[str]:
    """Every banned form on every page, with the words around it so a
    failure names the string rather than only the page."""
    out: list[str] = []
    for n, text in enumerate(pages, start=1):
        for name, needle in BANNED.items():
            start = text.find(needle)
            if start >= 0:
                context = text[max(0, start - 40):start + len(needle) + 40]
                out.append(f"page {n}: {name} in {context!r}")
    return out


def _month_with_two_cards(client, monkeypatch) -> str:
    """A real August: two cards, a statement, receipts held on either card,
    one on no card, and a reviewer's card pick."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated (@lovable)", "25.00", "2026-08-05"),
        _extraction("Pressmaster", "135.00", "2026-08-23"),
        _extraction("Zoom", "15.00", "2026-08-10", "Visa ending 2838"),
        _extraction("Taxi", "30.00", "2026-08-12"),
    )
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"}
    )
    _done(client, resp)
    batch = resp.json()["batch_id"]
    files = [("files", (f"receipt-{c}.png", _png(c), "image/png"))
             for c in ("red", "green", "blue", "yellow")]
    _done(client, client.post(f"/api/expense-batches/{batch}/receipts", files=files))
    _attach(client, batch, [
        ("2838", datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
        ("2838", datetime(2026, 8, 14), "WEB*NETWORKSOLUTIONS", "Sale", -40.00),
        ("3645", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
    ])
    lovable = _expense(client, batch, "Lovable Labs Incorporated (@lovable)")
    assert _pick_card(
        client, batch, lovable["document_id"], "corp-2838"
    ).status_code == 200
    return batch


def test_the_reconciliation_report_prints_no_banned_dash(client, monkeypatch):
    batch = _month_with_two_cards(client, monkeypatch)
    pages = _pages(client, f"/runs/{batch}/reconciliation-report.pdf")
    assert "Reconciliation: August 2026" in pages[0]
    assert _dashes(pages) == []


def test_the_month_report_prints_no_banned_dash(client, monkeypatch):
    batch = _month_with_two_cards(client, monkeypatch)
    pages = _pages(client, f"/runs/{batch}/expense-report.pdf")
    assert "Expense report: August 2026" in pages[0]
    assert _dashes(pages) == []


def test_the_trip_report_prints_no_banned_dash(client, monkeypatch):
    """The third title `service.py` composes, on the trip-batch branch."""
    _trip_wire(monkeypatch, _trip_extraction("Hotel Roma", "100.00", "2026-04-15"))
    trip = _create_trip(client)
    batch = _create_trip_batch(client, trip)
    pages = _pages(client, f"/runs/{batch}/expense-report.pdf")
    assert "Trip report: TEST - Rome" in pages[0]
    assert _dashes(pages) == []
