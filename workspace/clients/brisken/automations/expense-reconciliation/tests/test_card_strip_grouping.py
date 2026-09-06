"""Backlog item 35 (canonical half): the unknown-card strip groups
digit-bearing hints by their canonical digit run, server-side.

User test 2026-08-28: the April strip rendered ONE card (0340) as five
assignable rows because `build_card_review` grouped by verbatim hint
string. The owner ruling: "there should only be clearly defined cards
listed and not stuff like 'cartao de credito', we want the card number."

Pinned here:
* Five spellings of one card are ONE row: `n_rows` summed, `documents`
  concatenated, member spellings in the PARALLEL `spellings[]` (most
  frequent first), `hint` carrying the most-frequent spelling so a stale
  SPA still renders and assigns a real hint string.
* The group key is zero-stripped (matcher equivalence) while `digits`
  keeps the longest printed run — leading zero preserved for display.
* Digit-less hints (generic tenders included) never group: one row per
  verbatim string, `digits: null`, `generic` marking the sub-strip.
* Assigning the representative spelling heals the WHOLE group: the digit
  fold on assignment resolves every sibling spelling.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cards import Card, hint_digit_run  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import build_card_review  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _res(hint: str, *, card: Card | None = None, ambiguous: bool = False,
         entity: str = "") -> dict:
    return {
        "hint": hint,
        "card": card,
        "entity": entity,
        "entity_source": "none" if not entity else "card",
        "ambiguous": ambiguous,
        "card_map_blocked": False,
    }


# ── unit: the digit-run rule ─────────────────────────────────────────


def test_hint_digit_run_takes_the_last_run_verbatim():
    assert hint_digit_run("***********0340") == "0340"
    assert hint_digit_run("VISA - ******0340") == "0340"
    assert hint_digit_run("0340") == "0340"
    # multi-run hints take the LAST run: the masked-PAN rule, and a
    # deterministic display pick for strings the resolver refused anyway
    assert hint_digit_run("Visa 1672 exp 2026") == "2026"
    assert hint_digit_run("Cartao de Credito") is None
    assert hint_digit_run("") is None
    assert hint_digit_run(None) is None
    # runs below the matcher's 3-digit floor identify nothing
    assert hint_digit_run("Cartao Credito 30 Dias") is None


# ── unit: the grouping ───────────────────────────────────────────────


def test_five_spellings_of_one_card_are_one_row():
    resolution = {
        "d1": _res("***********0340"),
        "d2": _res("***********0340"),
        "d3": _res("VISA - ******0340"),
        "d4": _res("****0340"),
        "d5": _res("CARTAO ***********0340"),
        # a mode label printing the zero-stripped form joins the group
        "d6": _res("mode 340"),
    }
    strip = build_card_review(resolution)
    (entry,) = strip["unresolved_hints"]
    assert entry["n_rows"] == 6
    assert sorted(entry["documents"]) == ["d1", "d2", "d3", "d4", "d5", "d6"]
    # display digits keep the longest printed run: leading zero preserved
    assert entry["digits"] == "0340"
    # spellings: most frequent first, every member listed exactly once
    assert entry["spellings"][0] == "***********0340"
    assert set(entry["spellings"]) == {
        "***********0340", "VISA - ******0340", "****0340",
        "CARTAO ***********0340", "mode 340",
    }
    # `hint` is the representative spelling — a real hint string from the
    # batch, so a stale SPA's Assign still submits something assignable
    assert entry["hint"] == "***********0340"
    assert entry["generic"] is False
    assert strip["n_unresolved_rows"] == 6


def test_different_digit_runs_never_group():
    strip = build_card_review({
        "d1": _res("****0340"),
        "d2": _res("****2838"),
    })
    assert len(strip["unresolved_hints"]) == 2
    assert {e["digits"] for e in strip["unresolved_hints"]} == {"0340", "2838"}


def test_digitless_hints_stay_one_row_per_verbatim_string():
    strip = build_card_review({
        "d1": _res("Cartao de Credito"),
        "d2": _res("Cartao de Credito"),
        "d3": _res("CARTAO TEF"),
        "d4": _res("CorpServ"),  # digit-less but identifying: not generic
    })
    by_hint = {e["hint"]: e for e in strip["unresolved_hints"]}
    assert set(by_hint) == {"Cartao de Credito", "CARTAO TEF", "CorpServ"}
    for e in strip["unresolved_hints"]:
        assert e["digits"] is None
        assert e["spellings"] == [e["hint"]]
    assert by_hint["Cartao de Credito"]["n_rows"] == 2
    assert by_hint["Cartao de Credito"]["generic"] is True
    assert by_hint["CARTAO TEF"]["generic"] is True
    assert by_hint["CorpServ"]["generic"] is False


def test_ambiguity_marks_the_whole_group():
    strip = build_card_review({
        "d1": _res("****0340"),
        "d2": _res("VISA 0340", ambiguous=True),
    })
    (entry,) = strip["unresolved_hints"]
    assert entry["ambiguous"] is True


# ── through the caller: the grid payload and the assignment heal ─────


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def test_grouped_strip_and_representative_assignment_heal(client, monkeypatch):
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint="***********0340"),
        _extraction(vendor="Other Co", total="9.00",
                    payment_hint="VISA - ******0340"),
    )
    resp = client.post("/api/expense-batches", files=[
        ("files", ("a.jpg", JPG, "application/octet-stream")),
        ("files", ("b.jpg", JPG + b"2", "application/octet-stream")),
    ], data={"legal_entity": "", "label": "April 2026"})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    (entry,) = grid["card_review"]["unresolved_hints"]
    assert entry["n_rows"] == 2
    assert entry["digits"] == "0340"
    assert len(entry["spellings"]) == 2

    # assign ONLY the representative spelling to a new card: the digit
    # fold must resolve the sibling spelling too (the stale-SPA path)
    resp = client.post(f"/api/expense-batches/{batch_id}/cards", json={
        "assignments": [{"hint": entry["hint"], "card": "card-0340"}],
        "new_cards": {"card-0340": {
            "label": "Visa 0340", "entity": "Corporate Services",
        }},
    })
    assert resp.status_code == 200, resp.text
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert grid["card_review"]["unresolved_hints"] == []
    (resolved,) = grid["card_review"]["resolved"]
    assert resolved["n_rows"] == 2
