"""Cards R3 (2026-08-21): entity-less batches, per-receipt entity from the
paying card, the card-review strip, hint -> card assignment with optional
learning, and the refresh-master-data snapshot-trap fix.

Owner rulings pinned here as tests:
* The batch-creation legal-entity ask is GONE — the tool takes receipts
  from any entity; entity resolves per receipt from the card.
* An unresolved card/entity NEVER blocks an export: the CSV ships with a
  visible placeholder, the assignment stays adjustable after export, and a
  re-export folds it in (grid == export by construction).
* Generic tender words ("Visa", "Cartão de crédito") never AUTO-resolve a
  card: they can be assigned explicitly for one batch, and are refused as
  learned settings tokens.

Same harness as test_web_expense_batches: MockLLMClient via
cli._build_llm_client, TestClient runs jobs in-process.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cards import (  # noqa: E402
    Card,
    is_generic_tender,
    learnable_hint_tokens,
    resolve_hinted_card,
    stamp_card_entities,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
JPG2 = b"\xff\xd8\xff\xe0other-jpeg-bytes"
JPG3 = b"\xff\xd8\xff\xe0third-jpeg-bytes"

COL_PAID_THROUGH = EXPENSE_COLUMNS.index("Paid Through")
COL_ENTITY = EXPENSE_COLUMNS.index("Legal Entity")

CARDS_V1 = {
    "corp-2838": {
        "label": "Corporate card (Chase)",
        "digits": ["2838", "1672"],
        "entity": "Corporate Services",
        "zoho_account": "CHASE VISA - 2838 - TRAVEL",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date="2026-08-01",
        total="42.50",
        currency="USD",
        vendor="Staples",
        reference="",
        line_items=(),
        confidence=0.9,
        notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _create_batch(client, files=None, legal_entity="", **data):
    payload = [
        ("files", (n, d, "application/octet-stream"))
        for n, d in (files or [("a.jpg", JPG)])
    ]
    resp = client.post(
        "/api/expense-batches",
        files=payload,
        data={"legal_entity": legal_entity, **data},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "done", job
    return body["batch_id"]


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _export_rows(client, batch_id) -> list[list[str]]:
    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == list(EXPENSE_COLUMNS)
    return rows[1:]


def _put_cards(client, cards: dict) -> None:
    resp = client.put("/api/settings", json={"cards": cards})
    assert resp.status_code == 200, resp.text


# ── unit: the resolution + learning primitives ──────────────────────


def test_generic_tender_predicate():
    for text in ("Visa", "cartão de crédito", "Cartao de Credito", "CASH",
                 "débito", "Apple Pay", "pix",
                 # Compound tenders and DE vocabulary are generic too
                 # (adversarial review: "Visa Credit" bypassed the exact-
                 # phrase check and became a learnable alias).
                 "Visa Credit", "credit visa", "cartao visa",
                 "Mastercard Debit", "Kreditkarte", "EC-Karte", "Bar",
                 # Item 35 (2026-08-28): the three April tender phrases
                 # that rendered as assignable cards. "30" is below the
                 # card-digit floor and identifies nothing, so it must not
                 # block genericity.
                 "CARTAO TEF", "COMPRA CREDITO VISA",
                 "Cartao Credito 30 Dias", "compra crédito"):
        assert is_generic_tender(text), text
    for text in ("Visa ...1672", "CorpServ", "brisken", "", None, "2838",
                 "Visa CorpServ",
                 # A pure number carries no tender vocabulary: leave it
                 # alone rather than declaring it generic.
                 "30", "12 12",
                 # A distinctive word keeps a compra-phrase identifying.
                 "Compra Loja Central"):
        assert not is_generic_tender(text), text


def test_learnable_hint_tokens():
    # Exactly one digit run: that run is the card digit.
    assert learnable_hint_tokens("Visa ...1672") == ("1672", None, None)
    # SEVERAL runs: no digit is deterministic (expiry / auth / BIN noise);
    # the exact hint string becomes the alias instead. This is the pin for
    # the year-poisoning repro: "Visa 1672 exp 12/2026" must never teach
    # 2026 (which would resolve every future hint printing that year).
    digit, alias, refusal = learnable_hint_tokens("Visa 1672 exp 12/2026")
    assert (digit, alias, refusal) == (None, "Visa 1672 exp 12/2026", None)
    digit, alias, refusal = learnable_hint_tokens("5412 75** **** 3456")
    assert (digit, alias) == (None, "5412 75** **** 3456") and refusal is None
    # Digitless, non-generic: alias.
    assert learnable_hint_tokens("CorpServ") == (None, "CorpServ", None)
    # Generic tender: refused with a reason, nothing learnable.
    digit, alias, refusal = learnable_hint_tokens("Cartão de crédito")
    assert digit is None and alias is None and refusal


def test_resolve_hinted_card_assignment_beats_resolver_and_respects_active():
    cards = {
        "a": Card(key="a", digits=("1111",), entity="X"),
        "b": Card(key="b", digits=("2222",), entity="Y"),
        "off": Card(key="off", digits=("3333",), entity="Z", active=False),
    }
    # Exact assignment wins even for a generic word the resolver refuses.
    assert resolve_hinted_card("Visa", cards, {"Visa": "b"}).key == "b"
    # Assignment to an inactive card does not resolve.
    assert resolve_hinted_card("Visa", cards, {"Visa": "off"}) is None
    # No assignment: digit resolution, ambiguity refused.
    assert resolve_hinted_card("Visa ...1111", cards, None).key == "a"
    both = {
        "a": Card(key="a", digits=("1111",), entity="X"),
        "dup": Card(key="dup", digits=("1111",), entity="Y"),
    }
    assert resolve_hinted_card("1111", both, None) is None


def test_stamp_card_entities_only_fills_from_entity_bearing_cards():
    cards = {
        "a": Card(key="a", digits=("1111",), entity="Corporate Services"),
        "no-ent": Card(key="no-ent", digits=("2222",)),
    }
    def _receipt(doc, entity, hint):
        return Receipt(
            document_id=doc, legal_entity_id=entity, detected_date=None,
            detected_total=None, detected_currency=None, detected_vendor="v",
            payment_mode=hint,
        )

    receipts = [
        _receipt("r1", "", "Visa ...1111"),
        _receipt("r2", "", "2222"),
        _receipt("r3", "Cloud", "1111"),
        _receipt("r4", "", None),
    ]
    out = stamp_card_entities(receipts, cards)
    assert out[0].legal_entity_id == "Corporate Services"
    assert out[1].legal_entity_id == ""      # card without entity: no stamp
    assert out[2].legal_entity_id == "Corporate Services"  # card beats batch
    assert out[3].legal_entity_id == ""      # no hint: untouched


# ── entity-less creation + needs_entity review ──────────────────────


def test_entityless_batch_creates_and_flags_needs_entity(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    batch = _create_batch(client, legal_entity="")
    grid = _grid(client, batch)
    assert grid["legal_entity_id"] == ""
    row = grid["expenses"][0]
    assert row["legal_entity_id"] == ""
    assert row["entity_source"] == "none"
    assert row["card"] is None
    assert row["review"]["reason_code"] == "needs_entity"
    assert grid["summary"]["n_needs_entity"] == 1
    strip = grid["card_review"]
    assert strip["n_needs_entity"] == 1
    (hint,) = strip["unresolved_hints"]
    assert hint["hint"] == "Visa" and hint["generic"] is True


def test_entityless_label_has_no_double_space(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch = _create_batch(client, legal_entity="")
    grid = _grid(client, batch)
    assert "  " not in grid["label"]


# ── card resolves entity + paid-through, at ingest and in the view ──


def test_card_digit_hint_resolves_entity_and_paid_through(client, monkeypatch):
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client, legal_entity="")
    grid = _grid(client, batch)
    row = grid["expenses"][0]
    assert row["legal_entity_id"] == "Corporate Services"
    assert row["entity_source"] == "card"
    assert row["card"]["key"] == "corp-2838"
    assert row["card"]["hint"] == "Visa ...1672"
    assert row["review"]["reason_code"] != "needs_entity"
    assert row["posting_paid_through"]["account"] == "CHASE VISA - 2838 - TRAVEL"
    assert row["posting_paid_through"]["source"] == "card"
    assert grid["summary"]["n_needs_entity"] == 0
    (resolved,) = grid["card_review"]["resolved"]
    assert resolved["card"]["key"] == "corp-2838" and resolved["n_rows"] == 1
    # The export carries the same resolution (grid == export).
    (export_row,) = _export_rows(client, batch)
    assert export_row[COL_ENTITY] == "Corporate Services"
    assert export_row[COL_PAID_THROUGH] == "CHASE VISA - 2838 - TRAVEL"
    # Ingest stamped the entity too (learned lookups saw it): the stored
    # snapshot receipt carries the card's entity, not "".
    with RunStore(client._data_root / "recon-web.sqlite") as db:
        run = db.get_run(batch)
    assert run.snapshot["receipts"][0]["legal_entity_id"] == "Corporate Services"


def test_generic_tender_never_auto_resolves_even_with_cards(client, monkeypatch):
    _put_cards(client, CARDS_V1)
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint="Visa"),
        _extraction(vendor="Cafe", payment_hint="Cartão de crédito"),
    )
    batch = _create_batch(
        client, files=[("a.jpg", JPG), ("b.jpg", JPG2)], legal_entity=""
    )
    grid = _grid(client, batch)
    assert all(e["card"] is None for e in grid["expenses"])
    assert grid["summary"]["n_needs_entity"] == 2
    hints = {h["hint"]: h for h in grid["card_review"]["unresolved_hints"]}
    assert set(hints) == {"Visa", "Cartão de crédito"}
    assert all(h["generic"] for h in hints.values())


# ── the ruled export policy: placeholders, never block ──────────────


def test_entityless_export_never_blocks_placeholders(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    batch = _create_batch(client, legal_entity="")
    (row,) = _export_rows(client, batch)
    assert row[COL_ENTITY] == "(entity - assign)"
    assert row[COL_PAID_THROUGH] == "(paid-through - assign)"


def test_assign_after_export_reexport_folds_it_in(client, monkeypatch):
    """The ruled adjustable-after-export loop: export with placeholders ->
    assign the hint to a card -> re-export -> the new file carries the
    entity and the card's account. Exports are regenerable on demand."""
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    batch = _create_batch(client, legal_entity="")
    (before,) = _export_rows(client, batch)
    assert before[COL_ENTITY] == "(entity - assign)"

    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [{"hint": "Visa", "card": "corp-2838"}]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    (result,) = body["results"]
    assert result["n_rows"] == 1 and result["learned"] is False
    row = body["batch"]["expenses"][0]
    assert row["legal_entity_id"] == "Corporate Services"
    assert row["entity_source"] == "card"

    (after,) = _export_rows(client, batch)
    assert after[COL_ENTITY] == "Corporate Services"
    assert after[COL_PAID_THROUGH] == "CHASE VISA - 2838 - TRAVEL"


# ── assignment semantics: batch-scoped vs learned ───────────────────


def test_generic_assignment_is_batch_only_never_learned(client, monkeypatch):
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    batch = _create_batch(client, legal_entity="")
    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [{"hint": "Visa", "card": "corp-2838"}],
              "learn": True},
    )
    assert resp.status_code == 200, resp.text
    (result,) = resp.json()["results"]
    assert result["learned"] is False and "generic tender" in result["note"]
    # Settings carry no trace of the generic word.
    settings = client.get("/api/settings").json()
    stored = settings.get("cards") or {}
    assert "Visa" not in str(stored.get("corp-2838", {}).get("aliases", []))
    # A NEW batch with the same generic hint stays unresolved.
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    batch2 = _create_batch(client, files=[("c.jpg", JPG3)], legal_entity="")
    row2 = _grid(client, batch2)["expenses"][0]
    assert row2["card"] is None and row2["legal_entity_id"] == ""


def test_digit_assignment_learns_and_next_batch_auto_resolves(client, monkeypatch):
    """The learning claim, end to end: assign an unknown digit hint once
    with learn, and the NEXT batch resolves it with no assignment."""
    _put_cards(client, {
        "corp-2838": {
            "label": "Corporate card",
            "digits": ["2838"],
            "entity": "Corporate Services",
            "zoho_account": "CHASE VISA - 2838 - TRAVEL",
        },
    })
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...9944"))
    batch = _create_batch(client, legal_entity="")
    assert _grid(client, batch)["expenses"][0]["card"] is None

    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [{"hint": "Visa ...9944", "card": "corp-2838"}],
              "learn": True},
    )
    assert resp.status_code == 200, resp.text
    (result,) = resp.json()["results"]
    assert result["learned"] is True
    stored = (client.get("/api/settings").json().get("cards") or {})
    assert "9944" in stored["corp-2838"]["digits"]

    _patch_ocr(monkeypatch, _extraction(payment_hint="9944 something"))
    batch2 = _create_batch(client, files=[("c.jpg", JPG3)], legal_entity="")
    row2 = _grid(client, batch2)["expenses"][0]
    assert row2["card"]["key"] == "corp-2838"
    assert row2["legal_entity_id"] == "Corporate Services"


def test_assignment_validation_errors(client, monkeypatch):
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    batch = _create_batch(client, legal_entity="")
    post = lambda body: client.post(  # noqa: E731
        f"/api/expense-batches/{batch}/cards", json=body
    )
    assert post({"assignments": [{"hint": "Visa", "card": "nope"}]}).status_code == 400
    assert post(
        {"assignments": [{"hint": "Amex", "card": "corp-2838"}]}
    ).status_code == 400
    assert post({"assignments": []}).status_code == 400
    assert post({"assignments": "x"}).status_code == 400


def test_generic_alias_rejected_at_settings_edge(client):
    resp = client.put(
        "/api/settings",
        json={"cards": {"c": {"label": "x", "aliases": ["Visa"]}}},
    )
    assert resp.status_code == 400
    assert "generic tender" in resp.json()["error"]


def test_field_override_entity_beats_card(client, monkeypatch):
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client, legal_entity="")
    doc = _grid(client, batch)["expenses"][0]["document_id"]
    resp = client.put(
        f"/api/runs/{batch}/expenses/{doc}/entity",
        json={"legal_entity": "Cloud Services"},
    )
    assert resp.status_code == 200, resp.text
    row = _grid(client, batch)["expenses"][0]
    assert row["legal_entity_id"] == "Cloud Services"
    assert row["entity_source"] == "override"
    (export_row,) = _export_rows(client, batch)
    assert export_row[COL_ENTITY] == "Cloud Services"


# ── refresh-master-data: the snapshot trap, fixed explicitly ────────


def test_refresh_master_data_applies_settings_edits_audited(client, monkeypatch):
    # v1 settings: the card exists but carries NO entity.
    _put_cards(client, {"corp-2838": {"label": "Corp", "digits": ["2838"]}})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...2838"))
    batch = _create_batch(client, legal_entity="")
    assert _grid(client, batch)["expenses"][0]["legal_entity_id"] == ""

    # The settings edit alone does NOT reach the existing batch (snapshot).
    _put_cards(client, {
        "corp-2838": {"label": "Corp", "digits": ["2838"],
                      "entity": "Corporate Services"},
    })
    assert _grid(client, batch)["expenses"][0]["legal_entity_id"] == ""

    # The explicit refresh does, and says what changed.
    resp = client.post(f"/api/expense-batches/{batch}/refresh-master-data")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert any(c["field"] == "cards" for c in body["changes"])
    row = body["batch"]["expenses"][0]
    assert row["legal_entity_id"] == "Corporate Services"
    assert row["entity_source"] == "card"
    with RunStore(client._data_root / "recon-web.sqlite") as db:
        run = db.get_run(batch)
    (audit,) = run.snapshot["master_data_refreshes"]
    assert audit["changes"] == body["changes"]

    # Idempotent: a second refresh reports no changes and adds no audit row.
    resp2 = client.post(f"/api/expense-batches/{batch}/refresh-master-data")
    assert resp2.json()["changes"] == []
    with RunStore(client._data_root / "recon-web.sqlite") as db:
        run = db.get_run(batch)
    assert len(run.snapshot["master_data_refreshes"]) == 1


def test_refresh_preserves_batch_assignments(client, monkeypatch):
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    batch = _create_batch(client, legal_entity="")
    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [{"hint": "Visa", "card": "corp-2838"}]},
    )
    assert resp.status_code == 200
    client.post(f"/api/expense-batches/{batch}/refresh-master-data")
    row = _grid(client, batch)["expenses"][0]
    assert row["card"] is not None and row["card"]["key"] == "corp-2838"


# ── batch entity still works as the fallback (legacy flow intact) ───


# ── adversarial-review regression pins (2026-08-21, 3-lens pass) ────


def test_year_token_never_poisons_cross_card_resolution(client, monkeypatch):
    """The executed HIGH repro: learning "Visa 1672 exp 12/2026" must not
    make an unrelated "Amex 5500 11/2026" resolve via the year token."""
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa 1672 exp 12/2026"))
    batch = _create_batch(client, legal_entity="")
    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [
            {"hint": "Visa 1672 exp 12/2026", "card": "corp-2838"}
        ], "learn": True},
    )
    assert resp.status_code == 200, resp.text
    stored = client.get("/api/settings").json().get("cards") or {}
    assert "2026" not in (stored.get("corp-2838", {}).get("digits") or [])
    # The exact hint recurs -> resolves via the learned exact alias.
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa 1672 exp 12/2026"))
    b2 = _create_batch(client, files=[("c.jpg", JPG3)], legal_entity="")
    assert _grid(client, b2)["expenses"][0]["card"]["key"] == "corp-2838"
    # An unrelated card's hint sharing only the year does NOT.
    _patch_ocr(monkeypatch, _extraction(payment_hint="Amex 5500 11/2026"))
    b3 = _create_batch(client, files=[("d.jpg", JPG + b"4")], legal_entity="")
    assert _grid(client, b3)["expenses"][0]["card"] is None


def test_alias_never_overrides_contradicting_digits():
    cards = {"a": Card(key="a", digits=("1111",), aliases=("CorpServ",),
                       entity="X")}
    # Digitless hint: the alias resolves it.
    assert resolve_hinted_card("CorpServ", cards).key == "a"
    # Digit-bearing hint whose digits match NO card: the word alias must
    # not claim it (different physical card) — review, not guess.
    assert resolve_hinted_card("CorpServ 2222", cards) is None
    # Exact learned string (digits and all) still resolves.
    cards2 = {"a": Card(key="a", digits=("1111",),
                        aliases=("Visa 9 exp 12/2026",), entity="X")}
    assert resolve_hinted_card("Visa 9 exp 12/2026", cards2) is not None


def test_masked_pan_bin_never_cross_matches():
    cards = {"a": Card(key="a", digits=("5412",), entity="X")}
    # 5412 here is the BIN prefix of a masked PAN, not the last-4.
    assert resolve_hinted_card("5412 75** **** 3456", cards) is None
    cards2 = {"a": Card(key="a", digits=("3456",), entity="X")}
    assert resolve_hinted_card("5412 75** **** 3456", cards2).key == "a"


def test_stored_generic_alias_is_inert_at_read_time():
    cards = {"a": Card(key="a", aliases=("Visa",), entity="X")}
    assert resolve_hinted_card("Visa", cards) is None


def test_legacy_generic_map_key_never_becomes_an_alias():
    from expense_recon.cards import effective_cards, resolve_card

    composed = effective_cards({"card_entities": {"Visa": "EntCorp"}})
    assert resolve_card("Visa", composed, on_ambiguity="none") is None


def test_ambiguity_blocks_the_flat_map_guess(client, monkeypatch):
    """Executed HIGH repro S1: when the registry refuses an ambiguous
    hint, the paid-through flat map must not guess an account either."""
    _put_cards(client, {
        "a": {"digits": ["2838"], "entity": "Corporate Services",
              "zoho_account": "acctA"},
        "b": {"digits": ["12838"], "zoho_account": "acctB"},
    })
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...2838"))
    batch = _create_batch(client, legal_entity="")
    row = _grid(client, batch)["expenses"][0]
    assert row["card"] is None  # ambiguous between a and b: review
    assert row["posting_paid_through"]["source"] != "card"
    (export_row,) = _export_rows(client, batch)
    assert export_row[COL_PAID_THROUGH] == "(paid-through - assign)"
    (hint,) = _grid(client, batch)["card_review"]["unresolved_hints"]
    assert hint["ambiguous"] is True


def test_card_account_flat_map_exact_length_semantics():
    from expense_recon.output.zoho_expense_export import _card_account

    # 3-digit key no longer wildcards onto a different last-4.
    assert _card_account("Visa ...9340", {"340": "acctX"}) is None
    # Leading-zero variants still land on the same key.
    assert _card_account("Visa ...0340", {"340": "acctX"}) == "acctX"
    # 5-digit key no longer cross-matches an unrelated card's last-4.
    assert _card_account("Visa ...2838", {"12838": "acctB"}) is None
    assert _card_account("Visa ...2838", {"2838": "acctA"}) == "acctA"


def test_duplicate_hint_assignment_rejected(client, monkeypatch):
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    batch = _create_batch(client, legal_entity="")
    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [
            {"hint": "Visa", "card": "corp-2838"},
            {"hint": "Visa", "card": "corp-2838"},
        ]},
    )
    assert resp.status_code == 400
    assert "more than once" in resp.json()["error"]


def test_new_cards_cannot_replace_an_existing_card(client, monkeypatch):
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    batch = _create_batch(client, legal_entity="")
    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"new_cards": {"corp-2838": {"label": "Oops", "entity": "Wrong"}},
              "learn": True},
    )
    assert resp.status_code == 400
    assert "already exists" in resp.json()["error"]
    stored = client.get("/api/settings").json().get("cards") or {}
    assert stored["corp-2838"]["digits"] == ["2838", "1672"]


def test_learn_unaffected_by_unrelated_stored_generic_alias(client, monkeypatch):
    """A pre-R3 stored generic alias elsewhere in settings must neither
    block learning on a clean card nor resolve anything itself."""
    _put_cards(client, CARDS_V1)
    # Inject invalid legacy state BEHIND the API (the edge now rejects it).
    with RunStore(client._data_root / "recon-web.sqlite") as db:
        stored = dict(db.get_settings().get("cards") or {})
        stored["visa-legacy"] = {"label": "Legacy", "aliases": ["Visa"]}
        db.set_settings({"cards": stored}, "2026-08-21T00:00:00Z")
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...7777"))
    batch = _create_batch(client, legal_entity="")
    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [{"hint": "Visa ...7777", "card": "corp-2838"}],
              "learn": True},
    )
    assert resp.status_code == 200, resp.text
    stored = client.get("/api/settings").json().get("cards") or {}
    assert "7777" in stored["corp-2838"]["digits"]
    assert stored["visa-legacy"]["aliases"] == ["Visa"]  # untouched
    # And the stored generic alias resolves nothing.
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa"))
    b2 = _create_batch(client, files=[("c.jpg", JPG3)], legal_entity="")
    assert _grid(client, b2)["expenses"][0]["card"] is None


def test_refresh_preserves_batch_only_assignment_target(client, monkeypatch):
    """Refresh re-derives from settings but must not undo an operator's
    confirmed assignment to a batch-only (learn:false) card."""
    _put_cards(client, CARDS_V1)
    _patch_ocr(monkeypatch, _extraction(payment_hint="MYNEWCARD"))
    batch = _create_batch(client, legal_entity="")
    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [{"hint": "MYNEWCARD", "card": "fresh-1"}],
              "new_cards": {"fresh-1": {"label": "Fresh",
                                        "entity": "Cloud Services"}}},
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/expense-batches/{batch}/refresh-master-data")
    assert resp.status_code == 200
    row = resp.json()["batch"]["expenses"][0]
    assert row["card"] is not None and row["card"]["key"] == "fresh-1"
    assert row["legal_entity_id"] == "Cloud Services"


def test_graduation_bakes_card_resolved_entities(client, monkeypatch):
    """The executed HIGH repro F1: an entity assigned via a card must
    reach the entity-scoped matcher at statement attach — pre-fix the
    month reconciled 0 with no warning."""
    _put_cards(client, CARDS_V1)
    _patch_ocr(
        monkeypatch,
        _extraction(date="2026-04-15", vendor="STAPLES NYC",
                    payment_hint="Visa"),
    )
    batch = _create_batch(client, legal_entity="")
    row = _grid(client, batch)["expenses"][0]
    assert row["review"]["reason_code"] == "needs_entity"
    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [{"hint": "Visa", "card": "corp-2838"}]},
    )
    assert resp.status_code == 200, resp.text

    attach = client.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(),
            "text/csv",
        )},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    assert attach.status_code == 200, attach.text
    job = client.get(f"/jobs/{attach.json()['job_id']}").json()
    assert job["status"] == "done", job
    assert "warning" not in (job.get("stage") or "")
    view = client.get(f"/api/runs/{batch}").json()
    staples = next(r for r in view["rows"] if "STAPLES" in r["vendor"])
    assert staples["effective_bucket"] == "reconciled"


def test_batch_entity_fallback_and_card_overrides_it(client, monkeypatch):
    _put_cards(client, CARDS_V1)
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint=None),
        _extraction(vendor="Cafe", payment_hint="Visa ...2838"),
    )
    batch = _create_batch(
        client, files=[("a.jpg", JPG), ("b.jpg", JPG2)],
        legal_entity="Cloud Services",
    )
    grid = _grid(client, batch)
    by_vendor = {e["vendor"]["display"]: e for e in grid["expenses"]}
    no_hint = by_vendor["Staples"]
    carded = by_vendor["Cafe"]
    assert no_hint["legal_entity_id"] == "Cloud Services"
    assert no_hint["entity_source"] == "batch"
    # The card is receipt-level evidence and outranks the batch default.
    assert carded["legal_entity_id"] == "Corporate Services"
    assert carded["entity_source"] == "card"
    assert grid["summary"]["n_needs_entity"] == 0
