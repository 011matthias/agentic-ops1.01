"""Note #60 (owner, 2026-09-17): a receipt that prints only the last two
digits of the card.

"when creating expenses, some receipts only show the last 2 digits of the
cards number, we need to strategize what we can do, so the card attribution
stays accurate". Live, "42463153XXXXXX38" is on August's SARL TRAIN'S,
which a human fixed by hand to card 2838. Two digits sat below the matcher's
3-digit floor, so the hint named no card.

The rule pinned here: two digits behind a mask or an ending word name the
card when exactly ONE active card ends in them, and the row says it was
named that way (`card_ending`). Two cards sharing the ending is a contest,
never a guess: on the live registry 3876 / 1176 share "76" and 0113 / 6013
share "13", and each pair spans two companies. A bare two-digit number is
not an ending. A printed last-4 and an operator's taught string both
outrank the ending.
"""
from __future__ import annotations

import pytest

from expense_recon.cards import (
    cards_from_setting,
    hint_digit_run,
    is_generic_tender,
    learnable_hint_tokens,
    masked_short_ending,
    normalize_cards_setting,
    resolve_hinted_card_ex,
)

# The live registry's numbers and companies, 2026-09-17.
LIVE = {
    "3645": ("3645", "Corporate Services"),
    "3876": ("3876", "Corporate Services"),
    "card-0113": ("0113", "Corporate Services"),
    "card-6013": ("6013", "Cloud Services"),
    "card-9693": ("9693", "Cloud Services"),
    "card-8311": ("8311", "Cloud Services"),
    "card-0340": ("0340", "Corporate Services"),
    "card-1176": ("1176", "Consulting"),
    "card-2838": ("2838", "Corporate Services"),
}


def _cards(**extra):
    raw = {
        key: {"label": key, "digits": [digits], "entity": entity}
        for key, (digits, entity) in LIVE.items()
    }
    raw.update(extra)
    return cards_from_setting(normalize_cards_setting(raw))


# ── unit: what counts as an ending ───────────────────────────────────


@pytest.mark.parametrize("hint,ending", [
    ("42463153XXXXXX38", "38"),
    ("Visa **38", "38"),
    ("Visa ••38", "38"),
    ("VISA ..38", "38"),
    ("credit card ending in 38", "38"),
    ("Cartao final 38", "38"),
])
def test_a_masked_two_digit_tail_is_an_ending(hint, ending):
    assert masked_short_ending(hint) == ending
    assert hint_digit_run(hint) == ending  # the strip groups on it
    assert is_generic_tender(hint) is False


@pytest.mark.parametrize("hint", [
    "Cartao Credito 30 Dias",           # a quantity, no mask
    "Pay $15.00 with a bank transfer",  # a price
    "VISA x38",                         # one x is an instalment marker, not a mask
    "3x 38",
    "xx38; xx49",                       # two different endings name nothing
    "Visa ...3645",                     # a last-4 is not a short ending
    "VISA",
    "",
    None,
])
def test_anything_else_is_not_an_ending(hint):
    assert masked_short_ending(hint) is None


def test_the_bin_is_never_shown_as_the_card_number():
    # item 69 round B made the matcher ignore it; the strip now agrees
    assert hint_digit_run("42463153XXXXXX38") == "38"
    assert hint_digit_run("VISA CREDITO 124631******3876") == "3876"


def test_an_ending_hint_still_learns_as_its_string():
    # unchanged from item 87: two digits are never taught as card digits
    assert learnable_hint_tokens("42463153XXXXXX38") == (None, "42463153XXXXXX38", None)


# ── unit: resolution ─────────────────────────────────────────────────


def test_a_unique_ending_names_the_card():
    card, ambiguous = resolve_hinted_card_ex("42463153XXXXXX38", _cards(), None)
    assert card is not None and card.key == "card-2838" and not ambiguous


@pytest.mark.parametrize("hint,keys", [
    ("Visa **76", {"3876", "card-1176"}),
    ("Mastercard XX13", {"card-0113", "card-6013"}),
])
def test_a_shared_ending_is_a_contest_not_a_guess(hint, keys):
    card, ambiguous = resolve_hinted_card_ex(hint, _cards(), None)
    assert card is None and ambiguous is True


def test_an_ending_no_card_has_names_nothing():
    card, ambiguous = resolve_hinted_card_ex("Visa **99", _cards(), None)
    assert card is None and ambiguous is False


def test_an_inactive_card_does_not_break_a_tie():
    cards = _cards(**{"3876": {"label": "3876", "digits": ["3876"], "active": False}})
    card, _ = resolve_hinted_card_ex("Visa **76", cards, None)
    assert card is not None and card.key == "card-1176"


def test_a_word_alias_cannot_override_the_ending():
    # "Corp" is on five cards; the ending says 2838 and wins
    cards = _cards(**{
        key: {"label": key, "digits": [d], "entity": e, "aliases": ["Corp"]}
        for key, (d, e) in LIVE.items() if e == "Corporate Services"
    })
    card, _ = resolve_hinted_card_ex("Corp XXXXXX38", cards, None)
    assert card is not None and card.key == "card-2838"


def test_a_taught_exact_string_outranks_the_ending():
    # an operator assigned this printed string to 0340 once; the ending is
    # only inference, so the decision stands
    cards = _cards(**{"card-0340": {
        "label": "card-0340", "digits": ["0340"],
        "aliases": ["42463153XXXXXX38"],
    }})
    card, _ = resolve_hinted_card_ex("42463153XXXXXX38", cards, None)
    assert card is not None and card.key == "card-0340"


# ── route level: the expense row (B2, through the caller) ────────────

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-14", total="32.00", currency="EUR",
                vendor="SARL TRAIN'S", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _batch(client, monkeypatch, *extractions) -> tuple[str, dict]:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": "June 2026"})
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    files = [
        ("files", (f"r{i}.jpg", JPG + bytes([i, 9]), "application/octet-stream"))
        for i, _ in enumerate(extractions)
    ]
    resp = client.post(f"/api/expense-batches/{batch}/receipts", files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    view = client.get(f"/api/expense-batches/{batch}").json()
    return view, {e["payment_hint"]: e for e in view["expenses"]}


def _live_setting() -> dict:
    return {
        key: {"label": key, "digits": [digits], "entity": entity,
              "person": f"owner of {digits}"}
        for key, (digits, entity) in LIVE.items()
    }


def test_a_two_digit_receipt_gets_its_card_company_and_person(client, monkeypatch):
    client.put("/api/settings", json={"cards": _live_setting()})
    _view, rows = _batch(
        client, monkeypatch,
        _extraction(payment_hint="42463153XXXXXX38"),
        _extraction(vendor="Padaria", total="12.00", payment_hint="Visa **76"),
        _extraction(vendor="Uber", total="30.00", payment_hint="Visa ...3645"),
    )
    ending = rows["42463153XXXXXX38"]
    assert ending["card"]["key"] == "card-2838"
    assert ending["card_source"] == "hint"
    assert ending["card_ending"] == "38"
    assert ending["legal_entity_id"] == "Corporate Services"
    assert ending["person"] == "owner of 2838"
    assert ending["suggested_private"] is False

    shared = rows["Visa **76"]
    assert shared["card"] is None and shared["card_ending"] == ""
    # a contest between two known cards is not a private expense
    assert shared["suggested_private"] is False

    last4 = rows["Visa ...3645"]
    assert last4["card"]["key"] == "3645" and last4["card_ending"] == ""


def test_the_strip_groups_the_contest_on_its_two_digits(client, monkeypatch):
    client.put("/api/settings", json={"cards": _live_setting()})
    view, rows = _batch(
        client, monkeypatch,
        _extraction(payment_hint="Visa **76"),
        _extraction(vendor="Padaria", total="12.00", payment_hint="VISA XXXX76"),
    )
    assert all(r["card"] is None for r in rows.values())
    groups = view["card_review"]["unresolved_hints"]
    assert len(groups) == 1, groups
    assert groups[0]["digits"] == "76"
    assert groups[0]["ambiguous"] is True
    assert groups[0]["n_rows"] == 2
