"""Backlog item 117 (2026-09-17 voids audit): one-word merchant aliases acted
as wildcards. token_set_ratio scores 100 whenever the alias's words are a
subset of the vendor's, so "Mercado" filed "Mercado Livre" as NOBRE ATACADO
with its Meals category, and the row read ready with no model call.

The contract pinned here: a generic-word alias names no merchant (ignored
by the resolver, refused when newly added at the settings PUT, accepted
when already stored), a fuzzy hit needs the vendor's distinctive words
covered, and every legitimate hit the live registry makes today still
lands (replayed over all six live months before shipping: no stored receipt
changed resolution)."""
from __future__ import annotations

import pytest

from expense_recon.matching.types import Receipt
from expense_recon.merchant_registry import (
    MerchantRegistry,
    is_generic_alias,
    normalize_merchants_setting,
)
from expense_recon.seed_registry import build_merchants

# The shape of the live registry's Brazilian entries (GET /api/settings,
# 2026-09-17), trimmed to what the cases below need.
LIVE_SHAPE = {
    "NOBRE ATACADO SAO JOSE DA C": {
        "aliases": ["Supermercado", "Mercado", "Atacado", "Varejo"],
        "category": "Meals & Entertainment",
    },
    "ERICK SPORTS": {"aliases": ["Sports"], "category": "Travel & Transport"},
    "MEGA CENTER": {
        "aliases": ["Material de Construcao", "Mega Center"],
        "category": "Professional Services",
    },
    "AUTO POSTO PIMENTEL SAO JOSE": {
        "aliases": ["Auto Posto"], "category": "Travel & Transport",
    },
    "O CASTELINHO": {
        "aliases": ["Comida", "Bebida", "Caipirinha", "Drink"],
        "category": "Meals & Entertainment",
    },
    "CALDINHO DO MARACA": {
        "aliases": ["Caldinho"], "category": "Meals & Entertainment",
    },
    "Espetinho do Ramos": {
        "aliases": ["Espetinho"], "category": "Meals & Entertainment",
    },
    "99": {"aliases": [], "category": "Travel & Transport"},
    "Americanas": {"aliases": [], "category": "Office Supplies & Consumables"},
    "RAC": {"aliases": ["Gasolina", "Alcool", "Diesel"],
            "category": "Travel & Transport"},
    "Supermercado Fenix": {
        "aliases": ["Supermercado", "Mercado"],
        "category": "Meals & Entertainment",
    },
    "PADARIA E PASTELARIA KI-MASSA": {
        "aliases": ["Paes", "Doces", "Cafe"],
        "category": "Meals & Entertainment",
    },
}


def _resolve(vendor: str, clean: str | None = None):
    m = MerchantRegistry(LIVE_SHAPE).resolve(clean, vendor)
    return (m.canonical_name, m.kind) if m else None


@pytest.mark.parametrize("vendor", [
    "Mercado Livre",                        # the audit's first example
    "Decathlon Sports",
    "Leroy Merlin Material de Construcao",  # a 3-word alias, still a subset
    "Auto Posto Shell",                     # a 2-word alias, still a subset
    "Cafe Nero London",
    "Drink Bar Copacabana",
    "Gasolina Comum",                       # a real ER line (ER-00214)
    "Mercado",                              # generic word alone, exact tier
    "Supermercado",
    # review of the first draft: place names and shop words are not a brand
    "Posto Sao Jose Ltda",
    "Atacado Sao Jose",
    "Auto Posto 10",
    "Espetinho e Bebidas",
    "Farmacia Pimentel",                    # why NOBRE E VAREJO stays a loss
    "Cafe Americano",                       # a real ER line, not Americanas
    # named trade-offs: a generic one-word alias no longer matches alone,
    # and a shop word beside part of a longer merchant is not a guess
    "Caldinho",
    "Caldinho Bar",
    "NOBRE ATACADO E VAREJO",
])
def test_a_vendor_no_longer_inherits_a_merchant_through_a_shared_word(vendor):
    assert _resolve(vendor) is None


@pytest.mark.parametrize("vendor, clean, expected", [
    # The live June receipt: the vendor's words sit inside a longer name.
    ("AUTO POSTO PIMENTEL", "Auto Posto Pimentel",
     ("AUTO POSTO PIMENTEL SAO JOSE", "fuzzy")),
    # The live July receipts: legal suffix on the raw, exact via the clean.
    ("SUPERMERCADO FENIX LTDA", "FENIX", ("Supermercado Fenix", "exact")),
    ("MEGA CENTER COMERCIO DE MATERIAIS DE CONSTRUCAO LTDA", "MEGA CENTER",
     ("MEGA CENTER", "exact")),
    # A generic word added to a known name is not distinctive.
    ("O Castelinho Bar", None, ("O CASTELINHO", "fuzzy")),
    # the same distinctive words, whatever shop words surround them
    ("KI-MASSA CAFE", None, ("PADARIA E PASTELARIA KI-MASSA", "fuzzy")),
    ("PADARIA KI-MASSA PÃES E DOCES", None,
     ("PADARIA E PASTELARIA KI-MASSA", "fuzzy")),
    ("OpenAl Inc", None, None),             # not in this registry: no guess
    # a brand that is a number
    ("99 Taxi", None, ("99", "fuzzy")),
    # Truncated OCR, spelling variant, accents, reversed containment.
    ("NOBRE ATACADO", None, ("NOBRE ATACADO SAO JOSE DA C", "fuzzy")),
    ("NOBRE ATACADO SÃO JOSÉ DA C", None,
     ("NOBRE ATACADO SAO JOSE DA C", "fuzzy")),
    ("Ki Massa Padaria", None, ("PADARIA E PASTELARIA KI-MASSA", "fuzzy")),
    ("CALDINHO DO MARACA", None, ("CALDINHO DO MARACA", "exact")),
])
def test_legitimate_hits_still_land(vendor, clean, expected):
    assert _resolve(vendor, clean) == expected


def test_generic_alias_rule():
    assert is_generic_alias("Mercado")
    assert is_generic_alias("Supermecado")          # the live misspelling
    assert is_generic_alias("Comida e Bebida")
    assert is_generic_alias("Caldinho")
    assert is_generic_alias("Auto Posto")
    assert is_generic_alias("Mercados")                # plural
    assert not is_generic_alias("Caldinho do Maraca")
    assert not is_generic_alias("Material de Construcao")
    assert not is_generic_alias("Mercado Livre")


def test_the_seed_never_proposes_a_generic_alias():
    # `--put` goes through the settings PUT, which would refuse it.
    recs = [
        Receipt(
            document_id=f"d{i}", legal_entity_id="e", detected_date=None,
            detected_total=None, detected_currency=None,
            detected_vendor=v, zoho_category=None,
        )
        for i, v in enumerate([
            "SUPERMERCADO FENIX LTDA", "SUPERMERCADO FENIX LTDA",
            "SUPERMERCADO FENIX LTDA", "SUPERMERCADO",
        ])
    ]
    merchants = build_merchants(recs)
    aliases = [a for e in merchants.values() for a in e["aliases"]]
    assert aliases and not any(is_generic_alias(a) for a in aliases)


def test_internal_callers_keep_every_alias():
    # Memory at sign-off and the seed pass no stored map: unchanged shape.
    out = normalize_merchants_setting({"X": {"aliases": ["Mercado", "X Ltda"]}})
    assert out["X"]["aliases"] == ["Mercado", "X Ltda"]


# ── through the routes ──────────────────────────────────────────────

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-item-117"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _store_merchants(client, merchants):
    """Seed the registry the way the live one got its generic aliases:
    written before the PUT guard existed."""
    with RunStore(client.app.state.db_path) as db:
        db.set_settings({"merchants": merchants}, "2026-09-17T00:00:00Z")


def _batch_row(client, monkeypatch, vendor):
    mock = MockLLMClient(extraction_responses=[ExtractedReceipt(
        date="2026-07-01", total="42.50", currency="BRL", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )])
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "Corporate Services"}
    )
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    resp = client.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return client.get(f"/api/expense-batches/{batch}").json()["expenses"][0]


@pytest.mark.parametrize("vendor, wrong", [
    # closed by both rules
    ("Mercado Livre", "NOBRE ATACADO SAO JOSE DA C"),
    # closed by the generic-alias rule alone: a slip that prints only the
    # kind of shop would otherwise hit "Mercado" EXACTLY
    ("MERCADO", "NOBRE ATACADO SAO JOSE DA C"),
    ("Auto Posto Shell", "AUTO POSTO PIMENTEL SAO JOSE"),
    # closed by the coverage rule alone: the alias leads with its own word,
    # but "Leroy Merlin" is distinctive and uncovered
    ("Leroy Merlin Material de Construcao", "MEGA CENTER"),
    # closed by the lead-word rule alone: only the place names are shared
    ("Atacado Sao Jose", "NOBRE ATACADO SAO JOSE DA C"),
])
def test_a_batch_row_keeps_its_own_vendor_despite_a_shared_word(
    client, monkeypatch, vendor, wrong
):
    _store_merchants(client, LIVE_SHAPE)
    row = _batch_row(client, monkeypatch, vendor)
    assert row["vendor"]["display"] != wrong
    assert row["vendor"]["source"] != "registry"
    assert (row.get("posting_category") or {}).get("source") != "registry"


def test_a_batch_row_still_resolves_a_real_variant(client, monkeypatch):
    _store_merchants(client, LIVE_SHAPE)
    row = _batch_row(client, monkeypatch, "O Castelinho Bar")
    assert row["vendor"]["display"] == "O CASTELINHO"
    assert row["vendor"]["source"] == "registry"


def test_settings_put_refuses_a_new_generic_alias(client):
    resp = client.put("/api/settings", json={"merchants": {
        "ERICK SPORTS": {"aliases": ["Sports"], "category": None},
    }})
    assert resp.status_code == 400
    assert "generic word" in resp.json()["error"]
    assert client.get("/api/settings").json()["merchants"] == {}


def test_settings_put_accepts_generic_aliases_already_stored(client):
    _store_merchants(client, LIVE_SHAPE)
    stored = client.get("/api/settings").json()["merchants"]
    # The editor sends the whole map back, with one merchant renamed and an
    # alias moved between merchants: nothing new was added, so it saves.
    stored["ERICK SPORTS LTDA"] = stored.pop("ERICK SPORTS")
    stored["RAC"]["aliases"].append("Mercado")
    resp = client.put("/api/settings", json={"merchants": stored})
    assert resp.status_code == 200, resp.text
    got = client.get("/api/settings").json()["merchants"]
    assert got["ERICK SPORTS LTDA"]["aliases"] == ["Sports"]
    assert "Mercado" in got["RAC"]["aliases"]
    # A distinctive new alias still saves; a new generic one does not.
    got["RAC"]["aliases"].append("Posto RAC Recife")
    assert client.put("/api/settings", json={"merchants": got}).status_code == 200
    for generic in ("Etanol", "Auto Posto Bar", "Lojas"):
        trial = {k: dict(v, aliases=list(v["aliases"])) for k, v in got.items()}
        trial["RAC"]["aliases"].append(generic)
        resp = client.put("/api/settings", json={"merchants": trial})
        assert resp.status_code == 400, generic
