"""Item 255 (owner 2026-10-09): the save-to-memory window shows its
correction lines in Portuguese when the operator reads in Portuguese.

The SPA (Lovable `0f0a63d`) asks `GET /api/runs/{id}/memory-plan?lang=pt`
and reads each lesson's `descriptions[lang]`, then `description_pt`, then
`description`. Route-level:

* every lesson carries both sentences, built from the same parts, so the
  vendor, company, card and amounts are identical in both;
* `?lang=pt` also puts the Portuguese sentence in `description`; no `lang`
  (or one we do not write) keeps English there;
* no English connector survives in a Portuguese sentence, across corrections,
  merchant-list entries, conflicts, owner-held merchants and an
  already-saved month.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-255"
CORP = "Corporate Services"
CARDS = {
    "corp-1672": {
        "label": "Corporate card (Chase)", "digits": ["1672"],
        "entity": CORP, "person": "Nicolas", "zoho_account": "Chase 1672",
    },
}
MERCHANTS = {"Obsidian": {"aliases": ["Obsidian"], "category": None, "zoho_account": None}}

# Phrases only the English templates write. Names (vendors, cards,
# categories) are printed as stored, so they are not on this list.
ENGLISH = (
    "From now on", "receipts", "Merchant list", "Seen on", "corrected row",
    "paid with", "paid through", "Replaces", "Memory already", "Already saved",
    "Held for the owner", "rows disagree", "This option", "no company",
    "entry updated", "new spelling", "filled in", " and ",
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        resp = c.put("/api/settings", json={"cards": CARDS, "merchants": MERCHANTS})
        assert resp.status_code == 200, resp.text
        yield c


def _batch(client, monkeypatch, vendors) -> tuple[str, list[str]]:
    mock = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date=f"2026-07-1{i}", total=f"4{i}.50", currency="USD", vendor=v,
            reference="", line_items=(), confidence=0.9, notes="",
        )
        for i, v in enumerate(vendors)
    ])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": CORP, "label": "July 2026"})
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    resp = client.post(f"/api/expense-batches/{batch}/receipts", files=[
        ("files", (f"r{i}.jpg", JPG + bytes([i, 5]) * (i + 1), "application/octet-stream"))
        for i in range(len(vendors))
    ])
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    rows = client.get(f"/api/expense-batches/{batch}").json()["expenses"]
    return batch, [r["document_id"] for r in rows]


def _edit(client, batch, doc, field, value) -> None:
    resp = client.put(f"/api/runs/{batch}/expenses/{doc}", json={"field": field, "value": value})
    assert resp.status_code == 200, resp.text


def _lessons(client, batch, lang=None) -> list[dict]:
    url = f"/api/runs/{batch}/memory-plan" + (f"?lang={lang}" if lang else "")
    resp = client.get(url)
    assert resp.status_code == 200, resp.text
    return resp.json()["lessons"]


def _card_lesson(lessons) -> dict:
    return next(lsn for lsn in lessons
                if lsn["table"] == "field_correction" and lsn["key"]["field"] == "card_key")


def _assert_portuguese(lessons) -> None:
    assert lessons
    for lsn in lessons:
        pt = lsn["descriptions"]["pt"]
        assert pt == lsn["description_pt"], lsn["id"]
        assert pt != lsn["descriptions"]["en"], (lsn["id"], pt)
        left = [w for w in ENGLISH if w in pt]
        assert not left, (lsn["id"], left, pt)
        assert "como com" not in pt and "como como" not in pt, (lsn["id"], pt)


def test_a_remembered_card_reads_in_portuguese(client, monkeypatch):
    batch, (doc,) = _batch(client, monkeypatch, ["OBSIDIAN"])
    _edit(client, batch, doc, "card_key", "corp-1672")

    card = _card_lesson(_lessons(client, batch, "pt"))
    assert card["description"] == (
        "De agora em diante, os recibos de OBSIDIAN em Corporate Services são "
        "preenchidos como pagos com Corporate card (Chase) (Nicolas). "
        "De 1 linha corrigida: OBSIDIAN 40.50 USD 2026-07-10."
    ), card["description"]
    assert card["descriptions"]["en"] == (
        "From now on, OBSIDIAN receipts in Corporate Services are filled in as "
        "paid with Corporate card (Chase) (Nicolas). "
        "From 1 corrected row: OBSIDIAN 40.50 USD 2026-07-10."
    ), card["descriptions"]["en"]


def test_a_merchant_list_card_change_reads_in_portuguese(client, monkeypatch):
    batch, (doc,) = _batch(client, monkeypatch, ["OBSIDIAN"])
    _edit(client, batch, doc, "card_key", "corp-1672")

    reg = next(lsn for lsn in _lessons(client, batch) if lsn["id"] == "registry:Obsidian")
    assert reg["description_pt"] == (
        "Lista de comerciantes, Obsidian: pago com Corporate card (Chase) (Nicolas), "
        "então o próximo recibo recebe esse cartão. "
        "Visto em 1 recibo: OBSIDIAN 40.50 USD 2026-07-10."
    ), reg["description_pt"]


def test_without_lang_the_description_stays_english(client, monkeypatch):
    batch, (doc,) = _batch(client, monkeypatch, ["OBSIDIAN"])
    _edit(client, batch, doc, "card_key", "corp-1672")

    for lang in (None, "en", "de"):
        card = _card_lesson(_lessons(client, batch, lang))
        assert card["description"] == card["descriptions"]["en"], lang
        assert card["description"].startswith("From now on, OBSIDIAN"), lang
        assert card["description_pt"].startswith("De agora em diante"), lang


def test_portuguese_reaches_every_kind_of_lesson(client, monkeypatch):
    """Corrections (category, paid-through, vendor name), merchant-list
    entries, a conflict, and an owner-held merchant."""
    batch, (a, b, c) = _batch(client, monkeypatch, ["Staples", "Staples", "OpenAI"])
    _edit(client, batch, a, "category", "Office Supplies & Consumables")
    _edit(client, batch, b, "category", "Equipment & Hardware")
    _edit(client, batch, a, "paid_through", "Petty Cash")
    _edit(client, batch, b, "tax_label", "Flight Tax")
    _edit(client, batch, c, "category", "Software & Subscriptions")

    lessons = _lessons(client, batch, "pt")
    kinds = {lsn["kind"] for lsn in lessons}
    assert {"correction", "conflict"} <= kinds, kinds
    _assert_portuguese(lessons)
    for lsn in lessons:
        assert lsn["description"] == lsn["descriptions"]["pt"], lsn["id"]

    conflicts = [lsn["description"] for lsn in lessons if lsn["kind"] == "conflict"]
    assert any("as linhas divergem. Esta opção memoriza categoria Equipment & Hardware"
               in d for d in conflicts), conflicts
    paid = next(lsn["description"] for lsn in lessons
                if lsn["table"] == "field_correction" and lsn["key"]["field"] == "paid_through")
    assert "são preenchidos como pagos por meio de Petty Cash" in paid, paid
    tax = next(lsn["description"] for lsn in lessons
               if lsn["table"] == "field_correction" and lsn["key"]["field"] == "tax_label")
    assert "são preenchidos com a linha de imposto Flight Tax." in tax, tax
    gated = [lsn for lsn in lessons if lsn["owner_gated"]]
    assert gated, [lsn["id"] for lsn in lessons]
    for lsn in gated:
        assert lsn["description"].endswith(
            " Reservado ao responsável: nunca é gravado por esta lista."), lsn["description"]
        assert lsn["descriptions"]["en"].endswith(
            " Held for the owner: never written from a checklist."), lsn["descriptions"]["en"]


def test_an_already_saved_month_says_so_in_portuguese(client, monkeypatch):
    batch, (doc,) = _batch(client, monkeypatch, ["OBSIDIAN"])
    _edit(client, batch, doc, "card_key", "corp-1672")
    resp = client.post(f"/api/runs/{batch}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text

    lessons = _lessons(client, batch, "pt")
    saved = [lsn for lsn in lessons if lsn["already_saved"]]
    assert saved, [(lsn["id"], lsn["descriptions"]["en"]) for lsn in lessons]
    for lsn in saved:
        assert lsn["description"].endswith(" Já salva deste mês."), lsn["description"]
        assert lsn["descriptions"]["en"].endswith(" Already saved from this month.")
    _assert_portuguese(lessons)
