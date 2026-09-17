"""Item 87 (note #33): a card that cannot be read or is not known gets a fix
that sticks.

Read on the live July month first (2026-09-17): of 33 rows with no company or
person, 16 print only a tender word ("VISA") and 8 print no card at all. The
card-review strip assigns by printed hint, so it could move all seven "VISA"
receipts to one card at once and could not reach the eight at all. And two
hints the strip claimed to have learned never resolved again: a whole-string
alias lost to a word alias four cards share, and a masked BIN was taught as a
card number the matcher ignores.

Pinned here, route-level through the FastAPI app:

* a per-row card fix (`card_key`) settles one row, whatever it printed;
* the key must name an active registry card, and a card defined after the
  month was created can still be picked;
* publishing the month remembers the fix for the vendor, and next month a
  receipt from that vendor that prints no card number takes it, while a
  printed card number always wins;
* the strip's learning sticks for the two hint shapes that used to fail.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cards import (  # noqa: E402
    cards_from_setting,
    learnable_hint_tokens,
    normalize_cards_setting,
    resolve_hinted_card_ex,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

CARDS = {
    "corp-1672": {
        "label": "Corporate card (Chase)",
        "digits": ["1672"],
        "entity": "Corporate Services",
        "person": "Nicolas",
        "zoho_account": "Chase 1672",
    },
    "cloud-9999": {
        "label": "Cloud card",
        "digits": ["9999"],
        "entity": "Cloud Services",
        "person": "Dirk",
        "zoho_account": "Chase 9999",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-07-10", total="42.50", currency="BRL",
                vendor="Marinho", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


_SEQ = [0]


def _create_batch(client, monkeypatch, *extractions, label="July 2026") -> str:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    files = []
    for _ in extractions:
        _SEQ[0] += 1
        files.append(("files", (f"r{_SEQ[0]}.jpg", JPG + bytes([_SEQ[0] % 256, 7]),
                                "application/octet-stream")))
    resp = client.post(f"/api/expense-batches/{batch_id}/receipts", files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(client, batch_id, hint: str) -> dict:
    rows = [e for e in _grid(client, batch_id)["expenses"] if e["payment_hint"] == hint]
    assert len(rows) == 1, [e["payment_hint"] for e in _grid(client, batch_id)["expenses"]]
    return rows[0]


def _fix(client, batch_id, doc, key):
    return client.put(
        f"/api/runs/{batch_id}/expenses/{doc}", json={"field": "card_key", "value": key}
    )


def _publish(client, batch_id) -> dict:
    resp = client.post(f"/api/runs/{batch_id}/publish")
    assert resp.status_code == 200, resp.text
    return resp.json()["memory"]


# ── the per-row fix, this month ──────────────────────────────────────


def test_a_row_that_prints_no_card_is_fixed_by_hand(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    batch = _create_batch(
        client, monkeypatch,
        _extraction(),                           # no payment method at all
        _extraction(vendor="Aposto", payment_hint="VISA"),
    )
    before = _grid(client, batch)
    assert before["summary"]["n_needs_company_or_person"] == 2
    row = _row(client, batch, "")
    assert row["card"] is None and row["card_source"] == "none"
    assert "needs_company_or_person" in row["boxes"]

    resp = _fix(client, batch, row["document_id"], "corp-1672")
    assert resp.status_code == 200, resp.text

    row = _row(client, batch, "")
    assert row["card"]["key"] == "corp-1672"
    assert row["card_source"] == "override"
    assert row["person"] == "Nicolas" and row["person_source"] == "card"
    assert row["legal_entity_id"] == "Corporate Services"
    assert "needs_company_or_person" not in row["boxes"]
    assert "card_key" in row["edited_fields"]
    after = _grid(client, batch)
    assert after["summary"]["n_needs_company_or_person"] == 1
    # the other row, which prints a tender word, is untouched
    visa = _row(client, batch, "VISA")
    assert visa["card"] is None and visa["suggested_private"] is True

    # clearing the fix puts the row back
    assert _fix(client, batch, row["document_id"], "").status_code == 200
    assert _row(client, batch, "")["card"] is None


def test_an_unknown_or_inactive_card_is_refused(client, monkeypatch):
    client.put("/api/settings", json={"cards": {
        **CARDS, "old-0001": {"label": "Old", "digits": ["0001"], "active": False},
    }})
    batch = _create_batch(client, monkeypatch, _extraction())
    doc = _row(client, batch, "")["document_id"]
    resp = _fix(client, batch, doc, "no-such-card")
    assert resp.status_code == 400 and "not a defined card" in resp.json()["error"]
    resp = _fix(client, batch, doc, "old-0001")
    assert resp.status_code == 400 and "inactive" in resp.json()["error"]
    assert _row(client, batch, "")["card"] is None


def test_a_card_defined_after_the_month_was_created_can_be_picked(client, monkeypatch):
    batch = _create_batch(client, monkeypatch, _extraction())
    client.put("/api/settings", json={"cards": CARDS})
    doc = _row(client, batch, "")["document_id"]
    resp = _fix(client, batch, doc, "cloud-9999")
    assert resp.status_code == 200, resp.text
    row = _row(client, batch, "")
    assert row["card"]["key"] == "cloud-9999" and row["person"] == "Dirk"


# ── remembered at sign-off, applied next month ───────────────────────


def test_publishing_remembers_the_fix_and_next_month_takes_it(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    july = _create_batch(client, monkeypatch, _extraction())
    assert _fix(client, july, _row(client, july, "")["document_id"], "corp-1672").status_code == 200
    memory = _publish(client, july)
    assert memory["saved"] is True
    fields = {c["field"]: c["value"] for c in client.get("/api/memory").json()["field_corrections"]}
    assert fields.get("card_key") == "corp-1672"

    august = _create_batch(
        client, monkeypatch,
        _extraction(date="2026-08-03"),                          # prints nothing
        _extraction(date="2026-08-05", payment_hint="VISA"),     # a tender word
        _extraction(date="2026-08-07", payment_hint="Visa ...9999"),  # a known card
        _extraction(date="2026-08-09", payment_hint="Visa ...5555"),  # an unknown card
        label="August 2026",
    )
    nothing = _row(client, august, "")
    assert nothing["card"]["key"] == "corp-1672"
    assert nothing["card_source"] == "learned"
    assert nothing["person"] == "Nicolas"
    assert "needs_company_or_person" not in nothing["boxes"]
    assert "card" not in (nothing["data_quality_note"] or "")

    tender = _row(client, august, "VISA")
    assert tender["card"]["key"] == "corp-1672" and tender["card_source"] == "learned"
    assert tender["suggested_private"] is False

    printed = _row(client, august, "Visa ...9999")
    assert printed["card"]["key"] == "cloud-9999" and printed["card_source"] == "hint"

    unknown = _row(client, august, "Visa ...5555")
    assert unknown["card"] is None, "a printed number the registry lacks is never overridden"
    assert unknown["card_source"] == "none"
    assert unknown["suggested_private"] is True


# ── the strip's learning sticks ──────────────────────────────────────


def test_a_masked_bin_hint_learns_as_its_string():
    assert learnable_hint_tokens("42463153XXXXXX38") == (None, "42463153XXXXXX38", None)
    assert learnable_hint_tokens("VISA - ******0340") == ("0340", None, None)


def test_a_whole_string_alias_beats_a_word_alias_other_cards_share():
    cards = cards_from_setting(normalize_cards_setting({
        "a": {"label": "A", "digits": ["1111"], "aliases": ["Corp"]},
        "b": {"label": "B", "digits": ["2222"], "aliases": ["Corp", "Paid via Corp Services card"]},
        "c": {"label": "C", "digits": ["3333"], "aliases": ["Corp"]},
    }))
    card, ambiguous = resolve_hinted_card_ex("Paid via Corp Services card", cards, None)
    assert card is not None and card.key == "b" and not ambiguous
    # a word alias alone stays ambiguous: nothing was taught for it
    card, ambiguous = resolve_hinted_card_ex("Corp", cards, None)
    assert card is None


@pytest.mark.parametrize("hint", ["42463153XXXXXX38", "Paid via Corp Services card"])
def test_a_hint_learned_on_the_strip_resolves_next_month(client, monkeypatch, hint):
    client.put("/api/settings", json={"cards": {
        **CARDS,
        "corp-a": {"label": "Corp A", "digits": ["4444"], "aliases": ["Corp"]},
        "corp-b": {"label": "Corp B", "digits": ["5555"], "aliases": ["Corp"]},
    }})
    july = _create_batch(client, monkeypatch, _extraction(payment_hint=hint))
    resp = client.post(
        f"/api/expense-batches/{july}/cards",
        json={"assignments": [{"hint": hint, "card": "corp-1672"}], "learn": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["results"][0]["learned"] is True

    august = _create_batch(
        client, monkeypatch, _extraction(date="2026-08-02", payment_hint=hint),
        label="August 2026",
    )
    row = _row(client, august, hint)
    assert row["card"] is not None and row["card"]["key"] == "corp-1672", (
        "the strip said learned, and the same hint came back unresolved"
    )
