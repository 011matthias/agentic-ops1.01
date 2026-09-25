"""Item 214 (owner ruling 2026-09-25): the card strip asks only where the
receipt carries no payment info, and its dropdown lists cards only.

Owner, verbatim: "yes it should show assign to card, if the payment info is
not in the receipt. dropdown should only consist of cards"; private-list
cards in the dropdown: "yes and expenses that are suggested a private have
only private cards in drop down unless user clicks that its not private";
"New card..." removed.

Pinned here, route-level through the FastAPI app:
* a private row whose printed number is on the list leaves
  `unresolved_hints` (September's DB Fernverkehr, 3281), and so does a hint
  the strip itself assigned for the month; a row Criss made private by hand
  on a receipt printing no number stays (July `0028__`, September `0046__`);
  `n_private_rows` counts the rows that left, so the four counts add up;
* `card_review.private_cards[]` lists the ACTIVE list entries with their
  dropdown label, and each group's `private_card_options[]` names the cards
  the route accepts for it: all of them on a number-less hint, none on a
  hint printing a number the list does not hold;
* the route's `{"hint", "private_card": "3281"}`: the month's private hint
  for the card's person, never a list write (learn or not), and its
  refusals (`private_card_not_listed` for an unknown or switched-off card,
  `private_card_number_mismatch` for a receipt printing another number,
  `assignment_two_targets` beside `card` or `private_to`);
* `private_to` (the published SPA's "Private card of...") still answers.

Harness mirrors test_private_card_list (fixtures copied, never imported: a
shared fixture import is an F811 in CI).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cards import private_card_fits_hint  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

CORP = {
    "corp-1672": {"label": "Credit Card Chase Visa - 1672", "digits": ["1672"],
                  "entity": "Corporate Services", "person": "Nicolas"},
}
# Live hints, verbatim (September and April 2026).
DB_3281 = "DEBIT-MASTERCARD ***** ***** ***** 3281"
KARTE = "Kartenzahlung erhalten"
EC = "EC-Karte"
VISA_2598 = "VISA ***2598"
LISTED = {
    "3281": {"person": "Dirk Neumann", "note": "placeholder"},
    "4444": {"person": "Ana", "active": False},
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-09-01", total="42.50", currency="EUR",
                vendor="DB Fernverkehr", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _create_batch(client, n_files=1, label="September 2026", seed=0):
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    batch_id = body["batch_id"]
    files = [
        ("files", (f"r{i}.jpg", JPG + bytes([i, seed]),
                   "application/octet-stream"))
        for i in range(n_files)
    ]
    resp = client.post(f"/api/expense-batches/{batch_id}/receipts",
                       files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_vendor(client, batch) -> dict:
    return {e["vendor"]["display"]: e for e in _grid(client, batch)["expenses"]}


def _put_settings(client, **groups):
    r = client.put("/api/settings", json=groups)
    assert r.status_code == 200, r.text
    return r.json()


def _groups(strip) -> dict:
    return {g["hint"]: g for g in strip["unresolved_hints"]}


def _four_receipts(client, monkeypatch):
    _put_settings(client, cards=CORP, private_cards=LISTED)
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint=DB_3281),
        _extraction(vendor="Bakery", total="3.10", payment_hint=KARTE),
        _extraction(vendor="Kiosk", total="4.20", payment_hint=EC),
        _extraction(vendor="Brazil Shop", total="9.90", payment_hint=VISA_2598),
    )
    return _create_batch(client, n_files=4)


# ── what leaves the strip, what stays ───────────────────────────────


def test_a_resolved_private_number_leaves_the_strip_and_a_hand_mark_stays(
    client, monkeypatch,
):
    batch = _four_receipts(client, monkeypatch)
    rows = _by_vendor(client, batch)
    # Criss marks the number-less Bakery receipt private by hand
    doc = rows["Bakery"]["document_id"]
    r = client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                    json={"private": True, "reimburse_to": "Dirk Neumann"})
    assert r.status_code == 200, r.text

    grid = _grid(client, batch)
    rows = {e["vendor"]["display"]: e for e in grid["expenses"]}
    assert rows["DB Fernverkehr"]["private_source"] == "private_card_list"
    assert rows["Bakery"]["private_source"] == "row"
    strip = grid["card_review"]
    groups = _groups(strip)
    # 3281 resolves to the list: no card question left, so it leaves
    assert DB_3281 not in groups
    # private by hand on a receipt printing no card: still asks which card
    assert KARTE in groups
    assert EC in groups and VISA_2598 in groups
    assert strip["n_private_rows"] == 1
    assert strip["n_unresolved_rows"] == 3
    assert (
        strip["n_private_rows"] + strip["n_unresolved_rows"]
        + strip["n_resolved_rows"] + strip["n_no_hint"]
    ) == len(grid["expenses"])


def test_the_dropdown_lists_active_private_cards_and_what_fits_each_group(
    client, monkeypatch,
):
    batch = _four_receipts(client, monkeypatch)
    strip = _grid(client, batch)["card_review"]
    # the switched-off 4444 is not offered
    assert strip["private_cards"] == [{
        "digits": "3281", "person": "Dirk Neumann",
        "label": "3281 · Dirk Neumann (private)",
    }]
    groups = _groups(strip)
    # a receipt printing no number may be any listed card
    assert groups[EC]["private_card_options"] == ["3281"]
    assert groups[KARTE]["private_card_options"] == ["3281"]
    # a receipt printing 2598 is answered by 2598 alone: list it in Settings
    assert groups[VISA_2598]["private_card_options"] == []
    assert groups[VISA_2598]["suggested_private"] is True


def test_an_empty_list_offers_no_private_card(client, monkeypatch):
    _put_settings(client, cards=CORP)
    _patch_ocr(monkeypatch, _extraction(vendor="Kiosk", payment_hint=EC))
    strip = _grid(client, _create_batch(client))["card_review"]
    assert strip["private_cards"] == []
    assert strip["n_private_rows"] == 0
    (group,) = strip["unresolved_hints"]
    assert group["private_card_options"] == []


# ── the route's private-card pick ───────────────────────────────────


def test_picking_a_private_card_makes_the_hint_private_for_its_person(
    client, monkeypatch,
):
    batch = _four_receipts(client, monkeypatch)
    r = client.post(f"/api/expense-batches/{batch}/cards", json={
        "assignments": [{"hint": EC, "private_card": "3281"}],
        # the remember switch changes nothing: the card is listed already
        "learn": True,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["results"] == [{
        "hint": EC, "private_to": "Dirk Neumann", "n_rows": 1,
        "learned": False, "digits": "", "private_card": "3281",
    }]
    rows = {e["vendor"]["display"]: e for e in body["batch"]["expenses"]}
    assert rows["Kiosk"]["private"] is True
    assert rows["Kiosk"]["private_source"] == "month"
    assert rows["Kiosk"]["reimburse_to"] == "Dirk Neumann"
    # the strip answered it, so it leaves the strip too
    strip = body["batch"]["card_review"]
    assert EC not in _groups(strip)
    assert strip["n_private_rows"] == 2
    # month record only; the list is exactly what the owner typed
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        exp = store.get_run(batch).config["expense"]
    assert exp["private_hints"] == {EC: "Dirk Neumann"}
    stored = client.get("/api/settings").json()["private_cards"]
    assert set(stored) == {"3281", "4444"}
    assert stored["3281"]["person"] == "Dirk Neumann"


def test_a_private_card_pick_is_refused_where_it_cannot_be_the_card(
    client, monkeypatch,
):
    batch = _four_receipts(client, monkeypatch)
    url = f"/api/expense-batches/{batch}/cards"

    def _code(assignment):
        r = client.post(url, json={"assignments": [assignment]})
        assert r.status_code == 400, r.text
        return r.json()["code"]

    assert _code({"hint": EC, "private_card": "9999"}) == "private_card_not_listed"
    assert _code({"hint": EC, "private_card": "Dirk"}) == "private_card_not_listed"
    # switched off in Settings
    assert _code({"hint": EC, "private_card": "4444"}) == "private_card_not_listed"
    # the receipt prints 2598: a pick never overrides a printed number
    assert (
        _code({"hint": VISA_2598, "private_card": "3281"})
        == "private_card_number_mismatch"
    )
    assert _code(
        {"hint": EC, "private_card": "3281", "card": "corp-1672"}
    ) == "assignment_two_targets"
    assert _code(
        {"hint": EC, "private_card": "3281", "private_to": "Dirk Neumann"}
    ) == "assignment_two_targets"
    # nothing was written by any refusal
    rows = _by_vendor(client, batch)
    assert rows["Kiosk"]["private"] is False


def test_the_published_private_to_still_answers(client, monkeypatch):
    batch = _four_receipts(client, monkeypatch)
    r = client.post(f"/api/expense-batches/{batch}/cards", json={
        "assignments": [{"hint": EC, "private_to": "Ana"}], "learn": False,
    })
    assert r.status_code == 200, r.text
    assert "private_card" not in r.json()["results"][0]
    row = _by_vendor(client, batch)["Kiosk"]
    assert row["private_source"] == "month" and row["reimburse_to"] == "Ana"


# ── the fit rule ────────────────────────────────────────────────────


@pytest.mark.parametrize("hint,digits,fits", [
    (EC, "3281", True),
    ("", "3281", True),
    ("VISA CREDIT", "3281", True),
    (DB_3281, "3281", True),
    (VISA_2598, "3281", False),
    ("COMPRA CREDITO VISA ********1340", "0340", False),
    ("Visa 0340", "0340", True),
    ("Mastercard xxxx.xxxx.xxxx.78", "5678", True),
    ("Mastercard xxxx.xxxx.xxxx.78", "3281", False),
    ("0501-1462-9129", "9129", True),
])
def test_private_card_fits_hint(hint, digits, fits):
    assert private_card_fits_hint(hint, digits) is fits
