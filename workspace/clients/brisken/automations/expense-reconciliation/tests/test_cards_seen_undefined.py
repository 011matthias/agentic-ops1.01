"""The card-definition screen shows the cards that actually charge.

`/api/cards` composed the registry plus the shipped presets, so it listed
the cards somebody had already defined and nothing else. On the live data
that means it shows 2838 and four cards carrying no charges at all, while
0340, 3645 and 4700 charge 53 of April's 94 rows and appear nowhere on the
screen where a card gets defined. The reviewer's actual move, define the
card these charges are on, was the one move the screen could not start.

Three things are under test:

1. **A card the months charge but the registry cannot name is reported**,
   with the digits to define it as, where it was seen, and how many
   charges it carries, so the decision to define it can be made from the
   row.
2. **A card the registry knows is NOT reported**, however it was
   registered. A "you have not defined this" list that includes defined
   cards is one nobody reads twice.
3. **The identity matches the coverage panel's.** Both come from
   `_charge_card_identity`, so a card listed here is the same card the
   coverage row is about; two derivations would be two answers.
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


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, n=4):
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-04-15", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ] * n,
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _batch(client, label="April 2026"):
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _carded_csv(*rows: tuple[str, str, str, str]) -> bytes:
    body = "".join(f"{d},{a},{v},{c}\n" for d, a, v, c in rows)
    return ("Date,Amount,Vendor,Card\n" + body).encode()


def _upload(client, batch_id, body: bytes):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("statement.csv", body, "application/octet-stream")},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
            "map_card": "Card",
        },
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"


def _cards(client) -> dict:
    resp = client.get("/api/cards")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_key(entries: list[dict]) -> dict[str, dict]:
    return {e["suggested_key"]: e for e in entries}


def test_a_card_the_month_charges_but_nobody_defined_is_listed(
    client, monkeypatch
):
    """The live April shape: a registered card alongside cards the tool has
    only ever met on a statement."""
    _wire(monkeypatch)
    client.put("/api/settings", json={
        "cards": {"2838": {"entity": "Corporate Services", "digits": ["2838"]}}
    })
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "3645"),
        ("2026-04-22", "31.10", "UBER", "3645"),
        ("2026-04-24", "9.99", "SLACK", "0340"),
    ))

    seen = _by_key(_cards(client)["seen_undefined"])
    assert set(seen) == {"3645", "0340"}, seen
    assert seen["3645"]["n_charges"] == 2
    assert seen["0340"]["n_charges"] == 1
    # Enough to decide from the row: where it was seen, and its digits.
    assert seen["3645"]["months"] == ["April 2026"]
    assert seen["3645"]["digits"] == ["3645"]
    # Busiest first, so the card worth defining is the one at the top.
    assert [e["suggested_key"] for e in _cards(client)["seen_undefined"]] == [
        "3645", "0340",
    ]


def test_a_leading_zero_survives_to_the_screen(client, monkeypatch):
    """`_card_keys` strips leading zeros on purpose, so that Chase's "0340"
    and the Zoho payment mode's "340" land on one match key. Handing that
    stripped form to a person is the wrong direction: Dirk knows the card
    as 0340, and a definition screen offering "340" invites him to define
    it under a name that appears on no statement he owns."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-24", "9.99", "SLACK", "0340"),
    ))

    entry = _cards(client)["seen_undefined"][0]
    assert entry["suggested_key"] == "0340", entry
    assert entry["digits"] == ["0340"], entry
    assert entry["observed"] == "0340", entry
    # The internal key stays normalized: it is what joins to the charge.
    assert entry["key"] == "digits:340", entry


def test_a_registered_card_is_never_listed_as_undefined(client, monkeypatch):
    """A "you have not defined this" list that includes defined cards is
    one nobody reads twice."""
    _wire(monkeypatch)
    client.put("/api/settings", json={
        "cards": {
            "2838": {"entity": "Corporate Services", "digits": ["2838"]},
            "3645": {"entity": "", "digits": ["3645"]},
        }
    })
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "3645"),
    ))

    payload = _cards(client)
    assert payload["seen_undefined"] == [], payload["seen_undefined"]
    # A card with no entity is still DEFINED; that gap is the entity
    # column's business, not this list's.
    assert {c["key"] for c in payload["cards"]} >= {"2838", "3645"}


def test_the_undefined_card_is_the_same_card_the_coverage_row_is_about(
    client, monkeypatch
):
    """One derivation of "which card is this charge on". Two would be two
    answers, and the reviewer would define a card that the coverage panel
    then does not credit."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-05", "12.00", "AWS", "3645"),
        ("2026-04-22", "31.10", "UBER", "3645"),
    ))

    seen = _cards(client)["seen_undefined"]
    coverage = client.get(f"/api/runs/{batch_id}").json()["coverage"]
    unknown = [c for c in coverage if not c.get("in_registry", True) or True]
    charged = {c["label"]: c["n_transactions"] for c in unknown if c["n_transactions"]}

    assert len(seen) == 1
    assert seen[0]["suggested_key"] == "3645"
    assert seen[0]["n_charges"] == charged.get("3645"), (seen, charged)


def test_a_month_with_no_statement_contributes_nothing(client, monkeypatch):
    """An expense batch holds receipts, not charges. Reading a snapshot
    that has no transactions must not invent a card or cost the settings
    screen a parse."""
    _wire(monkeypatch)
    _batch(client)
    assert _cards(client)["seen_undefined"] == []


def test_the_field_is_present_even_when_every_card_is_known(client):
    """Parallel field: a renderer reading it gets an empty list rather than
    a missing key."""
    assert _cards(client)["seen_undefined"] == []
