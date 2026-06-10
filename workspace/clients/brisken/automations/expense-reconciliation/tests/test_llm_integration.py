"""End-to-end LLM integration tests (BLUEPRINT 2.9).

These make REAL OpenAI calls and are skipped unless
EXPENSE_RECON_LIVE_OPENAI=1 and OPENAI_API_KEY are both set. CI never
sets the flag, so the suite stays free and offline; a developer runs
this deliberately when calibrating against the live API.

    EXPENSE_RECON_LIVE_OPENAI=1 OPENAI_API_KEY=sk-... uv run pytest \
        tests/test_llm_integration.py -v
"""
from __future__ import annotations

import os
from decimal import Decimal

import pytest

LIVE = os.environ.get("EXPENSE_RECON_LIVE_OPENAI") == "1" and os.environ.get("OPENAI_API_KEY")

pytestmark = pytest.mark.skipif(
    not LIVE,
    reason="set EXPENSE_RECON_LIVE_OPENAI=1 + OPENAI_API_KEY to run live OpenAI tests",
)


def _make_receipt_png() -> tuple[bytes, str]:
    """A tiny synthetic receipt image rendered with Pillow so the live
    test needs no fixture file. Plain black text on white — legible to
    gpt-4o-mini vision."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (480, 320), "white")
    draw = ImageDraw.Draw(img)
    lines = [
        "BLUEBOTTLE COFFEE",
        "123 Market St",
        "Date: 2026-05-14",
        "",
        "Latte            5.50",
        "Croissant        4.00",
        "",
        "TOTAL USD        9.50",
        "Ref: BB-88421",
    ]
    y = 16
    for line in lines:
        draw.text((20, y), line, fill="black")
        y += 30
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), "image/png"


def test_live_vision_extracts_header_and_line_items():
    from expense_recon.llm.client import OpenAIClient

    client = OpenAIClient(model="gpt-4o-mini")
    png, mime = _make_receipt_png()

    result = client.extract_receipt(file_name="bluebottle.png", images=[(png, mime)])

    assert result.total is not None and Decimal(result.total) == Decimal("9.50")
    assert (result.currency or "").upper() == "USD"
    assert result.vendor and "blue" in result.vendor.lower()
    assert result.date == "2026-05-14"
    descs = " ".join(i.description.lower() for i in result.line_items)
    assert "latte" in descs and "croissant" in descs
    assert client.cost_tracker.call_count == 1
    assert client.cost_tracker.total_cost_usd > 0


def test_live_text_pdf_path_extracts_from_text_layer():
    from expense_recon.llm.client import OpenAIClient

    client = OpenAIClient(model="gpt-4o-mini")
    text = (
        "Uber\nTrip receipt\n2026-06-02\n"
        "Total $24.50\nUberX ride downtown\nReference: TRIP-9931\n"
    )

    result = client.extract_receipt(file_name="uber.pdf", text=text)

    assert result.total is not None and Decimal(result.total) == Decimal("24.50")
    assert result.vendor and "uber" in result.vendor.lower()
