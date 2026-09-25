"""Item 216 cause 3: one canonical merchant identity for memory, the registry
and the alias learner.

The reach fixture is the live measurement of 2026-09-25 (the 55 GL-month
receipts the model was unsure about, by extracted name, against the live
registry's software merchants): memory and the registry now reach 35 of them,
the app's own `resolve(None, raw)` reached 13. The route tests run through
`categorize_receipts_with_registry` on the GL engine with a model that
refuses, so an answer can only come from the identity reaching a rule.
"""
from __future__ import annotations

import io
import json
from datetime import date, datetime
from decimal import Decimal

import pytest
from openpyxl import Workbook

from expense_recon.categorize import categorize_receipts_with_registry
from expense_recon.learning import (
    LearningStore,
    MerchantCategory,
    MerchantCategoryLookup,
    identity_alias_candidates,
    learn_from_expense_run,
)
from expense_recon.learning.capture import category_key
from expense_recon.llm.client import ClassificationResult, ExtractedReceipt, MockLLMClient
from expense_recon.matching.types import (
    ClassificationSource,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.merchant_identity import MerchantIdentityResolver, identity_key
from expense_recon.merchant_registry import MerchantRegistry

CORP, CORP_ORG = "Corporate Services", "822741658"
ENTITY_ORGS = {CORP: CORP_ORG, "Cloud Services": "697686691"}
COGS_INFRA = "COGS - Other Infra and IT Costs for Cloud Business"  # E700030-30 in CorpServ
SOFTWARE = "Software & Subscriptions"

# The eight extracted names item 216 lists, and the merchant each is.
ITEM_216_NAMES = {
    "Anthropic, PBC": "anthropic",
    "Anthropic, PBC (@anthropic)": "anthropic",
    "Wispr AI, Inc. (dba Wispr Flow)": "wispr flow",
    "Rize Labs, Inc.": "rize labs",
    "OpenRouter, Inc": "openrouter",
    "Railway Corporation": "railway",
    "Vercel Inc.": "vercel",
    "Pressmaster FZCO": "pressmaster",
}

# Live registry's software merchants (settings read 2026-09-25), verbatim.
LIVE_SAAS = {
    "Anthropic": {"aliases": [], "category": SOFTWARE, "zoho_account": None},
    "Brave Software, Inc.": {"aliases": [], "category": SOFTWARE, "zoho_account": None},
    "Lovable Labs": {"aliases": [], "category": SOFTWARE, "zoho_account": None},
    "Lovable Labs Incorporated": {"aliases": [], "category": SOFTWARE, "zoho_account": None},
    "ZOHO Corp.": {"aliases": [], "category": SOFTWARE, "zoho_account": None},
}

# The 55 model-unsure receipts by extracted name (count), live 2026-09-25.
UNSURE_55 = {
    "Anthropic, PBC": 17, "Lovable Labs Incorporated": 10,
    "Wispr AI, Inc. (dba Wispr Flow)": 3, "Rize Labs, Inc.": 3,
    "Anthropic, PBC (@anthropic)": 3, "OpenRouter, Inc": 2,
    "Railway Corporation": 2, "Anthropic, PBC @anthropic": 2, "Amazon.de": 1,
    "LIDL, Zeppelinstraße 76185 Karlsruhe": 1, "ATACADAO POPULAR-MARAIAL": 1,
    "LOCAL SHOP B LTDA": 1, "Lovable Labs Incorporated (@lovable)": 1,
    "CANTINHO ABENCOADO": 1, "Private payee A": 1, "Vercel Inc.": 1,
    "PETROCAL PETROLEO CAVALCANTI LTDA": 1, "Brave Software, Inc.": 1,
    "ZOHO Corp.": 1, "Pressmaster FZCO": 1, "Wi-Fi Onboard / LATAM": 1,
}


class _Refuses(MockLLMClient):
    """A model that is never sure: any answer must come from a rule."""

    def classify_line_items(self, items, *a, **k):
        return [ClassificationResult(None, None, 0.2, "unsure") for _ in items]

    def classify_by_vendor(self, *a, **k):
        return ClassificationResult(None, None, 0.2, "unsure")


def _receipt(vendor: str, doc: str = "d1", entity: str = CORP, clean=None) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id=entity, detected_date=date(2026, 9, 3),
        detected_total=Decimal("20"), detected_currency="USD",
        detected_vendor=vendor, line_items=(), vendor_clean=clean,
    )


def _rule(vendor_norm, *, entity=CORP, category=SOFTWARE, account=COGS_INFRA,
          seeded=False) -> MerchantCategory:
    return MerchantCategory(
        legal_entity_id=entity, vendor_norm=vendor_norm, category=category,
        zoho_account=account, decision_count=1, last_confirmed_at="2026-09-01",
        source_run=("zoho-seed:2026" if seeded else "run-1"),
        validated_at=None, validated_by=None,
    )


def _cat(r: Receipt):
    return r.line_items[0].categorization


# ---- the resolver ------------------------------------------------------------


@pytest.mark.parametrize("name,key", sorted(ITEM_216_NAMES.items()))
def test_the_eight_item_216_names_reach_their_merchant(name, key):
    assert identity_key(name) == key
    canonical = {"anthropic": "Anthropic", "wispr flow": "Wispr Flow",
                 "rize labs": "Rize Labs", "openrouter": "OpenRouter",
                 "railway": "Railway", "vercel": "Vercel",
                 "pressmaster": "Pressmaster"}[key]
    reg = MerchantRegistry({c: {"aliases": [], "category": SOFTWARE}
                            for c in ("Anthropic", "Wispr Flow", "Rize Labs",
                                      "OpenRouter", "Railway", "Vercel", "Pressmaster")})
    ident = MerchantIdentityResolver(reg).resolve(None, name)
    assert (ident.source, ident.canonical) == ("registry", canonical)


@pytest.mark.parametrize("a,b", [
    ("GOOGLE *ADS9208169978", "Google LLC"),          # Ads is not Workspace
    ("GOOGLE *CLOUD B2vMDX", "GOOGLE*PLAY"),
    ("LinkedIn SN P3060910829", "LinkedIn P3045212688"),  # Sales Navigator
    ("Amazon web services", "Amazon.de"),
    ("TWILIO SENDGRID WWW.TWILIO.CO CA", "Twilio Inc"),
    ("MP *RECANTODOSABO", "MP *PARADAOBRIGAT"),        # one processor, two shops
    ("TST*BARBAROSSA COFFEE -", "TST*THE GOOSES ACRE"),
    ("WEB*NETWORKSOLUTIONS", "LOVABLE"),
])
def test_two_merchants_sharing_a_token_do_not_merge(a, b):
    assert identity_key(a) != identity_key(b)
    # Both Google merchants are held: a registry holding only "Google Ads"
    # would take a bare "Google LLC" by its fuzzy tier (a one-word name
    # inside a longer merchant scores 100), the same rule that reads LOVABLE
    # as Lovable Labs on 65 live rows. That limit is the registry's, recorded
    # in item 216, and no live string trips it.
    reg = MerchantRegistry({"Google Ads": {"aliases": ["GOOGLE *ADS"]},
                            "Google Workspace": {"aliases": ["Google LLC"]},
                            "Amazon": {"aliases": ["Amazon.de"]},
                            "Twilio SendGrid": {"aliases": []},
                            "Twilio": {"aliases": []}})
    ra = MerchantIdentityResolver(reg).resolve(None, a)
    rb = MerchantIdentityResolver(reg).resolve(None, b)
    assert ra.key != rb.key


@pytest.mark.parametrize("a,b", [
    ("OPENAI OPENAI.COM CA", "OPENAI"),
    ("MICROSOFT#G172123598", "Microsoft-G170285625 701-2817490 WA"),
    ("SERVERPILOT.IO SERVERPILOT.I WA", "serverpilot"),
    ("GITHUB, INC. GITHUB.COM CA", "github inc"),
    ("BASE44.COM", "base44 com"),
    ("PROTON AG* PROTON AG", "Proton"),
    ("ADOBE  *800-833-6687", "Adobe"),
    ("Lovable Labs Incorporated (@lovable)", "lovable labs"),
])
def test_one_merchants_spellings_share_a_key(a, b):
    assert identity_key(a) == identity_key(b)


def test_the_measured_reach_on_the_55_unsure_receipts():
    reg = MerchantRegistry(LIVE_SAAS)
    reached = {n for n in UNSURE_55 if reg.resolve(None, n) is not None}
    assert sum(UNSURE_55[n] for n in reached) == 35
    assert set(UNSURE_55) - reached == {
        "Wispr AI, Inc. (dba Wispr Flow)", "Rize Labs, Inc.", "OpenRouter, Inc",
        "Railway Corporation", "Amazon.de", "LIDL, Zeppelinstraße 76185 Karlsruhe",
        "ATACADAO POPULAR-MARAIAL", "LOCAL SHOP B LTDA",
        "CANTINHO ABENCOADO", "Private payee A", "Vercel Inc.",
        "PETROCAL PETROLEO CAVALCANTI LTDA", "Pressmaster FZCO",
        "Wi-Fi Onboard / LATAM",
    }


# ---- memory: recall and the read-time fold -----------------------------------


def test_a_rule_under_the_short_name_reaches_every_spelling():
    lk = MerchantCategoryLookup([_rule("anthropic")])
    for name in ("Anthropic, PBC", "Anthropic, PBC (@anthropic)",
                 "ANTHROPIC ANTHROPIC.COM CA"):
        got = lk.recall(CORP, name)
        assert got is not None and got.zoho_account == COGS_INFRA, name


def test_spellings_that_agree_fold_and_a_person_outranks_the_seed():
    lk = MerchantCategoryLookup([
        _rule("anthropic", account=COGS_INFRA),
        _rule("anthropic pbc", account="Other account", seeded=True),
    ])
    assert lk.recall(CORP, "Anthropic, PBC").zoho_account == COGS_INFRA
    (fold,) = lk.folds
    assert fold.decided and fold.vendor_norms == ("anthropic", "anthropic pbc")


def test_spellings_that_disagree_are_reported_and_keep_their_own_answer():
    lk = MerchantCategoryLookup([
        _rule("anthropic", account=COGS_INFRA),
        _rule("anthropic pbc", account="Other account"),
    ])
    (fold,) = lk.folds
    assert not fold.decided
    assert lk.recall(CORP, "Anthropic").zoho_account == COGS_INFRA
    assert lk.recall(CORP, "Anthropic PBC").zoho_account == "Other account"
    assert lk.recall(CORP, "Anthropic, PBC (@anthropic)") is None


def test_a_registry_alias_joins_the_fold():
    reg = MerchantRegistry({"Wispr Flow": {"aliases": ["Wispr AI"], "category": SOFTWARE}})
    rows = [_rule("wispr ai")]
    assert MerchantCategoryLookup(rows).recall(CORP, "Wispr Flow") is None
    lk = MerchantCategoryLookup(rows, identity=MerchantIdentityResolver(reg))
    assert lk.recall(CORP, "Wispr Flow").zoho_account == COGS_INFRA


# ---- route level: categorize_receipts_with_registry on the GL engine ---------


def test_route_memory_reaches_a_receipt_spelled_differently():
    lk = MerchantCategoryLookup([_rule("anthropic")])
    out, _ = categorize_receipts_with_registry(
        [_receipt("Anthropic, PBC (@anthropic)")], registry=None, learned=lk,
        client=_Refuses(), entity_orgs=ENTITY_ORGS,
    )
    cat = _cat(out[0])
    assert cat.source == ClassificationSource.LEARNED
    assert cat.category == "E700030-30"


def test_route_the_registry_account_comes_from_the_rule_its_alias_holds():
    reg = MerchantRegistry({"Wispr Flow": {"aliases": ["Wispr AI"], "category": SOFTWARE}})
    lk = MerchantCategoryLookup([_rule("wispr ai")])
    out, matches = categorize_receipts_with_registry(
        [_receipt("Wispr AI, Inc. (dba Wispr Flow)")], registry=reg, learned=lk,
        client=_Refuses(), entity_orgs=ENTITY_ORGS,
    )
    assert matches["d1"].canonical_name == "Wispr Flow"
    cat = _cat(out[0])
    assert cat.source == ClassificationSource.REGISTRY
    assert cat.category == "E700030-30"


def test_route_the_rule_is_asked_about_the_matched_merchant():
    """Only the extracted brand resolves; the raw OCR line does not. The
    account must still come from the matched merchant's rule."""
    reg = MerchantRegistry({"Wispr Flow": {"aliases": ["Wispr AI"], "category": SOFTWARE}})
    lk = MerchantCategoryLookup([_rule("wispr ai")])
    out, matches = categorize_receipts_with_registry(
        [_receipt("WSPR FLW INVOICE 0042", clean="Wispr Flow")], registry=reg,
        learned=lk, client=_Refuses(), entity_orgs=ENTITY_ORGS,
    )
    assert matches["d1"].canonical_name == "Wispr Flow"
    cat = _cat(out[0])
    assert (cat.source, cat.category) == (ClassificationSource.REGISTRY, "E700030-30")


def test_route_the_per_company_map_reaches_the_extracted_name():
    reg = MerchantRegistry({"Anthropic": {
        "aliases": [], "category": SOFTWARE, "accounts": {CORP: "E700030-30"}}})
    out, matches = categorize_receipts_with_registry(
        [_receipt("Anthropic, PBC (@anthropic)")], registry=reg, learned=None,
        client=_Refuses(), entity_orgs=ENTITY_ORGS,
    )
    assert matches["d1"].canonical_name == "Anthropic"
    cat = _cat(out[0])
    assert (cat.source, cat.category) == (ClassificationSource.REGISTRY, "E700030-30")


# ---- capture ---------------------------------------------------------------------


def test_a_correction_is_stored_under_the_merchant_and_recalled_by_another_spelling(tmp_path):
    r = _receipt("Anthropic, PBC")
    assert category_key(r) == (CORP, "anthropic")
    with LearningStore(tmp_path / "learning.sqlite") as store:
        learn_from_expense_run(
            store, receipts=[r], effective_receipts=[r], field_overrides={},
            category_overrides={("d1", 0): {"category": SOFTWARE, "zoho_account": COGS_INFRA}},
            source_run="run-9", now_iso="2026-09-25T00:00:00Z",
        )
        lk = MerchantCategoryLookup.from_store(store)
    assert [row.vendor_norm for row in lk._rows] == ["anthropic"]
    assert lk.recall(CORP, "Anthropic, PBC (@anthropic)").zoho_account == COGS_INFRA


# ---- the alias learner -----------------------------------------------------------


def _tx(tx_id: str, desc: str) -> Transaction:
    return Transaction(
        transaction_id=tx_id, legal_entity_id=CORP, account_id="card",
        transaction_date=date(2026, 9, 3), posting_date=None, amount=Decimal("20"),
        transaction_currency="USD", account_card_currency="USD",
        vendor_from_statement=desc,
    )


def _pairs(*pairs):
    txs, recs, matches = [], [], []
    for i, (desc, vendor) in enumerate(pairs):
        txs.append(_tx(f"t{i}", desc))
        recs.append(_receipt(vendor, doc=f"d{i}"))
        matches.append(Match(f"t{i}", f"d{i}", MatchType.EXACT, 0.99, "test pair"))
    return txs, recs, MatchOutcome(matches=matches)


def test_a_person_confirmed_pair_proposes_the_unresolved_spelling():
    ident = MerchantIdentityResolver(MerchantRegistry(LIVE_SAAS))
    txs, recs, outcome = _pairs(
        ("ANTHROPIC* CLAUDE SUB", "Anthropic, PBC"),   # descriptor unresolved
        ("LOVABLE", "Lovable Labs Incorporated"),       # both resolve: nothing to add
        ("OPENAI *CHATGPT SUBSCR", "OpenAI, LLC"),      # neither resolves: nothing
        ("ZOHO* ZOHO-ONE", "Anthropic, PBC"),           # confirmed by the TOOL
    )
    cands, conflicts = identity_alias_candidates(
        transactions=txs, receipts=recs, outcome=outcome,
        person_confirmed_tx_ids={"t0", "t1", "t2"}, identity=ident,
    )
    assert [(c.canonical, c.alias) for c in cands] == [("Anthropic", "ANTHROPIC* CLAUDE SUB")]
    assert conflicts == 0


def test_two_registry_merchants_on_one_pair_are_a_conflict_not_an_alias():
    ident = MerchantIdentityResolver(MerchantRegistry(LIVE_SAAS))
    txs, recs, outcome = _pairs(("ZOHO CORP", "Brave Software, Inc."))
    cands, conflicts = identity_alias_candidates(
        transactions=txs, receipts=recs, outcome=outcome,
        person_confirmed_tx_ids={"t0"}, identity=ident,
    )
    assert cands == [] and conflicts == 1


# ---- the memory plan and Publish (routes) ----------------------------------------
#
# Driven through `GET /api/runs/{id}/memory-plan` and `POST .../publish`, the
# callers the wiring changed: a month with a statement whose one pairing a
# person or the tool confirmed, and corrections on a receipt the registry
# names under a longer canonical than its extracted name.

JPG = b"\xff\xd8\xff\xe0fake-jpeg-identity-216"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CONTOSO = {"Contoso Cloud": {"aliases": [], "category": SOFTWARE, "zoho_account": None}}
DESC = "CTSO*CLOUDSUB 8NK"
_UPLOADS = [0]


@pytest.fixture
def client(tmp_path, monkeypatch):
    testclient = pytest.importorskip("fastapi.testclient")
    from expense_recon.web.app import create_app

    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with testclient.TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _month(client, monkeypatch, merchants, *vendors) -> str:
    """A July month for Corporate Services, one receipt per vendor (USD 20.00,
    21.00, ... so no two read as copies), the registry set first."""
    assert client.put("/api/settings", json={"merchants": merchants}).status_code == 200
    mock = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date="2026-07-02", total=f"{20 + i}.00", currency="USD", vendor=v,
            reference="", line_items=(), confidence=0.9, notes="",
        )
        for i, v in enumerate(vendors)
    ])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": CORP, "label": "July 2026"})
    _done(client, resp)
    batch = resp.json()["batch_id"]
    files = []
    for _v in vendors:
        _UPLOADS[0] += 1
        body = JPG + bytes([_UPLOADS[0] % 256]) * 3
        files.append(("files", (f"r{_UPLOADS[0]}.jpg", body, "application/octet-stream")))
    _done(client, client.post(f"/api/expense-batches/{batch}/receipts", files=files))
    return batch


def _paired_month(client, monkeypatch, merchants, vendor, description, *, by) -> str:
    """`_month` with one receipt, a statement holding its USD 20.00 charge, and
    the pairing confirmed by a person (the decisions route) or by the tool
    (`set_tool_decision`, what `apply_self_confirmations` writes)."""
    from expense_recon.web.store import RunStore

    batch = _month(client, monkeypatch, merchants, vendor)
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    ws.append([datetime(2026, 7, 2), description, "Sale", -20.00])
    buf = io.BytesIO()
    wb.save(buf)
    _done(client, client.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": ("July2026.xlsx", buf.getvalue(), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": json.dumps({"card-2838": CORP}),
            "account_card_currency": "USD",
        },
    ))
    (row,) = [
        r for r in client.get(f"/api/runs/{batch}").json()["rows"]
        if description in (r["vendor"] or "")
    ]
    tx, doc = row["transaction_id"], row["candidates"][0]["document_id"]
    if by == "person":
        resp = client.post(f"/api/runs/{batch}/decisions", json={
            "transaction_id": tx, "status": "confirmed", "chosen_document_id": doc,
        })
        assert resp.status_code == 200, resp.text
    else:
        store = RunStore(client._data_root / "recon-web.sqlite")
        try:
            assert store.set_tool_decision(
                batch, tx, "confirmed", doc, "2026-07-03T00:00:00Z", "exact_vendor_75",
            )
        finally:
            store.close()
    return batch


def _lessons(client, batch) -> dict[str, dict]:
    resp = client.get(f"/api/runs/{batch}/memory-plan")
    assert resp.status_code == 200, resp.text
    return {lsn["id"]: lsn for lsn in resp.json()["lessons"]}


def _publish(client, batch, **ticks) -> dict:
    resp = client.post(f"/api/runs/{batch}/publish", json={"override": True, **ticks})
    assert resp.status_code == 200, resp.text
    return resp.json()["memory"]


def _merchants(client) -> dict:
    return client.get("/api/settings").json()["merchants"]


def _set_category(client, batch, doc, category) -> None:
    resp = client.put(
        f"/api/runs/{batch}/expenses/{doc}", json={"field": "category", "value": category},
    )
    assert resp.status_code == 200, resp.text


def test_route_a_person_confirmed_pairing_offers_its_spelling_and_publish_saves_it(
    client, monkeypatch,
):
    batch = _paired_month(client, monkeypatch, CONTOSO, "Contoso Cloud, Inc.", DESC, by="person")
    lesson = _lessons(client, batch)["registry:Contoso Cloud"]
    assert f"new spelling {DESC}" in lesson["description"]
    assert lesson["default_keep"] is True and lesson["owner_gated"] is False
    # The lesson names the pairing that proved it: the bank's line and the receipt.
    assert [(s["kind"], s["vendor"]) for s in lesson["sources"]] == [
        ("charge", DESC), ("receipt", "Contoso Cloud, Inc."),
    ]
    _publish(client, batch)
    assert _merchants(client)["Contoso Cloud"]["aliases"] == [DESC]


def test_route_a_tool_confirmed_pairing_offers_no_spelling(client, monkeypatch):
    batch = _paired_month(client, monkeypatch, CONTOSO, "Contoso Cloud, Inc.", DESC, by="tool")
    assert not any("new spelling" in lsn["description"] for lsn in _lessons(client, batch).values())
    _publish(client, batch)
    assert _merchants(client)["Contoso Cloud"]["aliases"] == []


def test_route_an_owner_gated_merchants_spelling_is_shown_and_never_saved(client, monkeypatch):
    anthropic = {"Anthropic": {"aliases": [], "category": SOFTWARE, "zoho_account": None}}
    batch = _paired_month(
        client, monkeypatch, anthropic, "Anthropic, PBC", "ANTHROPIC* CLAUDE SUB", by="person",
    )
    lesson = _lessons(client, batch)["registry:Anthropic"]
    assert "new spelling ANTHROPIC* CLAUDE SUB" in lesson["description"]
    assert lesson["owner_gated"] is True and lesson["default_keep"] is False
    memory = _publish(client, batch, keep=["registry:Anthropic"])
    assert memory["learned"]["lessons"]["refused_owner_gated"] == ["registry:Anthropic"]
    assert _merchants(client)["Anthropic"]["aliases"] == []


def test_route_a_correction_is_planned_under_the_registry_merchant_with_its_row(
    client, monkeypatch,
):
    # "CONTOSO" resolves to the registry's "Contoso Cloud", whose key is not
    # the extracted name's: the write and the lesson's rows must share it.
    batch = _month(client, monkeypatch, CONTOSO, "CONTOSO")
    (row,) = client.get(f"/api/expense-batches/{batch}").json()["expenses"]
    _set_category(client, batch, row["document_id"], "Office Supplies & Consumables")
    lesson = _lessons(client, batch)[f"merchant_category:{CORP}|contoso cloud"]
    assert [s["document_id"] for s in lesson["sources"]] == [row["document_id"]]


def test_route_a_kept_conflict_candidate_is_saved_under_the_registry_merchant(
    client, monkeypatch,
):
    batch = _month(client, monkeypatch, CONTOSO, "CONTOSO", "CONTOSO")
    a, b = (r["document_id"] for r in client.get(f"/api/expense-batches/{batch}").json()["expenses"])
    _set_category(client, batch, a, "Office Supplies & Consumables")
    _set_category(client, batch, b, "Equipment & Hardware")
    pick = next(
        lsn for lsn in _lessons(client, batch).values()
        if lsn["kind"] == "conflict" and lsn["table"] == "merchant_category"
        and "Equipment" in lsn["description"]
    )
    assert pick["key"] == {"legal_entity_id": CORP, "vendor_norm": "contoso cloud"}
    _publish(client, batch, keep=[pick["id"]])
    cats = {
        (c["entity"], c["vendor"]): c["category"]
        for c in client.get("/api/memory").json()["categories"]
    }
    assert cats == {(CORP, "contoso cloud"): "Equipment & Hardware"}
