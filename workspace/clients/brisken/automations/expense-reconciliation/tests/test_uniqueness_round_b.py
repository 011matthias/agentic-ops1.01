"""A clean pair keeps its match when its rivals are spoken for or name
another merchant (backlog item 69, round B, owner-approved 2026-09-15).

The bilateral-uniqueness gate (2026-07-23) withdraws a clean rate-derived
pair's auto-resolution right whenever ANY other clean rate-derived pair
shares its receipt or its charge. That is the right default and it is also
too blunt: measured against the human labels it demoted 36 of the six
bundles' 95 receipts and another 11 across the two live months, with the
correct charge already sitting first in the reviewer's list. The rival that
blocked them was usually not a rival at all.

Two refinements, no threshold moves:

* **spoken for** — a rival already claimed by bank-printed EXACT evidence
  elsewhere cannot also take this pairing, so it does not block;
* **vendor dominance** — a pair with a live rival left keeps its right when
  the merchant agrees on IT and on no rival. Vendor only PROMOTES a pair
  that already carries clean rate evidence, the opposite direction from the
  FX vendor floor the S1 optimize run refuted.

Plus the masked-BIN fix in `_card_keys`: a digit run immediately followed
by a mask character is the issuer's BIN, not this card.

Tests run through `match_month`, which IS the caller of the gate, and one
runs through the FastAPI route so the dataclass default is proven on the
path the hosted app takes (the Docker image ships only `src/`, so the
default is what Fly runs).
"""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal

import pytest

from expense_recon.matching.deterministic import (
    MatchingConfig,
    _card_keys,
    match_month,
    uniqueness_verdicts,
)
from expense_recon.matching.types import MatchType, Receipt, Transaction


# ── fixtures: a BRL receipt on a USD card, the April month's shape ──────


def _tx(
    tx_id: str = "2838:1",
    amount: str = "9.69",
    vendor: str = "ERICK SPORTS",
    day: int = 1,
    currency: str = "USD",
    account_id: str = "2838",
) -> Transaction:
    return Transaction(
        transaction_id=tx_id,
        legal_entity_id="corpserv",
        account_id=account_id,
        transaction_date=date(2026, 4, day),
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency=currency,
        account_card_currency="USD",
        vendor_from_statement=vendor,
    )


def _receipt(
    doc: str = "ER#001",
    total: str = "49.98",
    base: str | None = "9.69",
    vendor: str = "Erick Sports",
    day: int = 1,
    currency: str = "BRL",
    payment_mode: str | None = None,
) -> Receipt:
    return Receipt(
        document_id=doc,
        legal_entity_id="corpserv",
        detected_vendor=vendor,
        detected_date=date(2026, 4, day),
        detected_total=Decimal(total),
        detected_currency=currency,
        base_amount=Decimal(base) if base else None,
        exchange_rate=Decimal("0.193945") if base else None,
        payment_mode=payment_mode,
    )


def _pair(outcome, tx_id: str, doc: str):
    """The assigned match for (tx, receipt), or None."""
    return next(
        (
            m
            for m in outcome.matches
            if m.transaction_id == tx_id and m.document_id == doc
        ),
        None,
    )


def _deferred(outcome, tx_id: str, doc: str):
    return next(
        (
            m
            for m in outcome.judgment_required
            if m.transaction_id == tx_id and m.document_id == doc
        ),
        None,
    )


# ── 1. a rival that is spoken for does not block ────────────────────────


def _spoken_for_month(with_exact: bool):
    """One BRL receipt two USD charges agree with on the derived rate.

    `2838:1` is the true pair (its base amount agrees exactly). `2838:2`
    is 9.75, still inside the 1% base-amount band, and carries the SAME
    merchant, so vendor dominance cannot separate them: the ONLY thing
    that can is `2838:2` being spoken for. It is, when `with_exact`, by a
    same-currency USD receipt of its own amount.
    """
    t1 = _tx("2838:1", "9.69")
    t2 = _tx("2838:2", "9.75")
    receipts = [_receipt("ER#BRL")]
    if with_exact:
        receipts.append(
            _receipt(
                "ER#USD", total="9.75", base=None, currency="USD",
                vendor="Erick Sports",
            )
        )
    return match_month([t1, t2], receipts, MatchingConfig())


def test_a_rival_charge_spoken_for_elsewhere_does_not_block():
    outcome = _spoken_for_month(with_exact=True)

    kept = _pair(outcome, "2838:1", "ER#BRL")
    assert kept is not None, "the true pair must resolve deterministically"
    assert kept.match_type is MatchType.FX_BASE_AMOUNT
    assert "Kept deterministic: the rival pairing is spoken for." in kept.reason

    # the rival took its own bank-printed charge, which is why it was never
    # a rival for this receipt
    assert _pair(outcome, "2838:2", "ER#USD").match_type is MatchType.EXACT


def test_without_an_exact_anywhere_the_same_shape_still_demotes():
    """The negative. Same two charges, same receipt, same merchant on both:
    nothing is spoken for, so the gate holds and nobody auto-matches."""
    outcome = _spoken_for_month(with_exact=False)

    assert _pair(outcome, "2838:1", "ER#BRL") is None
    deferred = _deferred(outcome, "2838:1", "ER#BRL") or _deferred(
        outcome, "2838:2", "ER#BRL"
    )
    assert deferred is not None
    assert "Demoted to judgment" in deferred.reason
    assert "Kept deterministic" not in deferred.reason


def test_spoken_for_off_restores_the_pre_round_b_demotion():
    outcome = match_month(
        [_tx("2838:1", "9.69"), _tx("2838:2", "9.75")],
        [
            _receipt("ER#BRL"),
            _receipt("ER#USD", total="9.75", base=None, currency="USD",
                     vendor="Erick Sports"),
        ],
        MatchingConfig(uniqueness_spoken_for=False),
    )
    assert _pair(outcome, "2838:1", "ER#BRL") is None


# ── 2. vendor dominance, through match_month ────────────────────────────


def _dominance_month(rival_vendor: str, cfg: MatchingConfig | None = None):
    """One charge, two receipts whose base amounts agree equally well. The
    merchant is the only thing that can separate them."""
    return match_month(
        [_tx()],
        [
            _receipt("ER#SAME", vendor="Erick Sports"),
            _receipt("ER#OTHER", vendor=rival_vendor),
        ],
        cfg or MatchingConfig(),
    )


def test_vendor_dominance_keeps_the_pair_whose_merchant_agrees():
    outcome = _dominance_month("Quinta Wu Zabriskie")

    kept = _pair(outcome, "2838:1", "ER#SAME")
    assert kept is not None
    assert kept.match_type is MatchType.FX_BASE_AMOUNT
    assert "Kept deterministic: the merchant agrees (1.00)" in kept.reason
    assert "no rival's does (best 0." in kept.reason
    # the losing receipt is deferred, never bound to the same charge
    assert _pair(outcome, "2838:1", "ER#OTHER") is None


def test_two_receipts_naming_the_same_merchant_stay_demoted():
    """Dominance needs a gap. Equal agreement resolves for nobody."""
    outcome = _dominance_month("Erick Sports")
    assert outcome.matches == []


def test_vendor_dominance_off_restores_the_pre_round_b_demotion():
    outcome = _dominance_month(
        "Quinta Wu Zabriskie",
        MatchingConfig(uniqueness_vendor_dominance_min=0.0),
    )
    assert outcome.matches == []


def test_both_knobs_off_is_exactly_the_2026_07_23_gate():
    cfg = MatchingConfig(
        uniqueness_spoken_for=False, uniqueness_vendor_dominance_min=0.0
    )
    assert _dominance_month("Quinta Wu Zabriskie", cfg).matches == []
    assert (
        _pair(
            match_month(
                [_tx("2838:1", "9.69"), _tx("2838:2", "9.75")],
                [
                    _receipt("ER#BRL"),
                    _receipt("ER#USD", total="9.75", base=None,
                             currency="USD", vendor="Erick Sports"),
                ],
                cfg,
            ),
            "2838:1",
            "ER#BRL",
        )
        is None
    )


# ── 3. the margin arithmetic, on the gate itself ────────────────────────


def _verdict(own: float, rival: float, cfg: MatchingConfig | None = None):
    """One receipt, two rate-derived claimants, neither spoken for: the
    only question left is whether the merchant separates them."""
    cands = [
        ("tx-own", "doc", MatchType.FX_BASE_AMOUNT, 0.5, own),
        ("tx-rival", "doc", MatchType.FX_BASE_AMOUNT, 0.5, rival),
    ]
    return uniqueness_verdicts(cands, cfg or MatchingConfig())[("tx-own", "doc")]


@pytest.mark.parametrize(
    "own, rival, keep",
    [
        (1.00, 0.20, True),    # the live July shape: merchant agrees, rival does not
        (0.75, 0.50, True),    # exactly the margin: inclusive
        (0.90, 0.90, False),   # both agree: nothing to choose between them
        (0.60, 0.40, False),   # a gap of 0.20, under the 0.25 margin
        (0.40, 0.00, False),   # dominant, but under the 0.50 floor
    ],
)
def test_dominance_margin(own, rival, keep):
    v = _verdict(own, rival)
    assert v.keep is keep
    assert v.basis == ("vendor_dominance" if keep else "")
    assert v.kind == ("" if keep else "uniqueness")
    assert v.best_rival_vendor == rival


def test_a_pair_with_no_rival_at_all_says_nothing_new():
    """Bilaterally unique all along: kept, and its reason is untouched, so
    no existing workbench string moves."""
    v = uniqueness_verdicts(
        [("tx", "doc", MatchType.FX_BASE_AMOUNT, 0.5, 0.9)], MatchingConfig()
    )[("tx", "doc")]
    assert v.keep and v.basis == "unique" and v.note == ""


def test_exact_candidates_are_not_gated_at_all():
    """The gate governs rate-derived evidence only; bank-printed exact
    agreement was never subject to it and still is not."""
    verdicts = uniqueness_verdicts(
        [
            ("tx-a", "doc", MatchType.EXACT, 0.5, 1.0),
            ("tx-b", "doc", MatchType.PROBABLE, 0.5, 1.0),
        ],
        MatchingConfig(),
    )
    assert verdicts == {}


# ── 4. the card gate still refuses, and neither rule can rescue it ──────


def test_a_contradicted_card_is_kept_by_neither_rule():
    """The receipt names card 9999, absent from this 2838 statement, so its
    true charge sits on another card's statement. A spoken-for rival and a
    perfect merchant agreement change nothing: the pair is still demoted,
    and it says why."""
    outcome = match_month(
        [_tx("2838:1", "9.69"), _tx("2838:2", "9.75")],
        [
            _receipt("ER#BRL", payment_mode="Visa ...9999"),
            _receipt("ER#USD", total="9.75", base=None, currency="USD",
                     vendor="Erick Sports"),
        ],
        MatchingConfig(),
    )
    assert _pair(outcome, "2838:1", "ER#BRL") is None
    deferred = _deferred(outcome, "2838:1", "ER#BRL")
    assert deferred is not None
    assert "payment card is absent from this statement" in deferred.reason


def test_a_contradicted_card_is_demoted_even_when_bilaterally_unique():
    outcome = match_month(
        [_tx()], [_receipt(payment_mode="Visa ...9999")], MatchingConfig()
    )
    assert outcome.matches == []


# ── 5. the masked BIN ───────────────────────────────────────────────────


def test_a_masked_bin_is_a_prefix_not_a_card():
    """The August SARL TRAIN'S billet. "42463153XXXXXX38" prints the first
    8 digits of a Visa and hides the rest; the trailing "38" is too short
    to be a last-4. Read as an identifier it became a card the statement
    does not contain, and the card gate demoted the receipt's true pair."""
    assert _card_keys("42463153XXXXXX38") == set()
    assert _card_keys("42463153xxxxxx38") == set()
    assert _card_keys("42463153######38") == set()
    assert _card_keys("424631•53") == set()


def test_a_separator_between_the_digits_and_the_mask_is_not_covered():
    """The boundary, stated rather than assumed. The rule is "immediately
    followed", so a grouped spelling ("4246 3153 **** **38") still reads
    its groups as identifiers. Neither live month contains one, and
    widening the rule across separators would drop a real card out of an
    ordinary label like "Card 1234 - XYZ Ltd", where losing the card also
    loses the contradiction gate's protection. Reopen this with a spelling
    that actually occurs, not with a hypothesis."""
    assert _card_keys("4246 3153 **** **38") == {"4246", "3153"}
    assert _card_keys("4246-3153-XXXX-XX38") == {"4246", "3153"}


@pytest.mark.parametrize(
    "spelling, keys",
    [
        ("VISA - ******0340", {"340"}),
        ("CorpServ 2838/1672 (Chase)", {"2838", "1672"}),
        ("1 - CorpServ 2838/1672 (Chase)", {"2838", "1672"}),
        ("************3876", {"3876"}),
        ("BCS Chase Visa ...9693", {"9693"}),
        ("Visa ...1176", {"1176"}),
        ("...2544", {"2544"}),
        ("PAYE", set()),
        ("DEBIT MASTERCARD", set()),
        (None, set()),
    ],
)
def test_every_existing_spelling_keeps_its_keys(spelling, keys):
    """A mask that PRECEDES a run is the ordinary spelling of a last-4 and
    is untouched; only a run FOLLOWED by one is a BIN. Pinned against the
    live payment modes of both months."""
    assert _card_keys(spelling) == keys


# ── 6. the three knobs are file-loadable, in lockstep with the defaults ─


def test_from_dict_accepts_the_three_round_b_keys():
    cfg = MatchingConfig.from_dict(
        {
            "uniqueness_spoken_for": False,
            "uniqueness_vendor_dominance_min": 0.7,
            "uniqueness_vendor_dominance_margin": 0.1,
        }
    )
    assert cfg.uniqueness_spoken_for is False
    assert cfg.uniqueness_vendor_dominance_min == 0.7
    assert cfg.uniqueness_vendor_dominance_margin == 0.1


def test_the_shipped_defaults_are_the_round_b_values():
    """The Docker image ships only `src/`, so the dataclass default is what
    the hosted app runs. `test_match_tuning.py` proves the asset file says
    the same."""
    cfg = MatchingConfig()
    assert cfg.uniqueness_spoken_for is True
    assert cfg.uniqueness_vendor_dominance_min == 0.5
    assert cfg.uniqueness_vendor_dominance_margin == 0.25


# ── 7. route level: the default reaches the hosted path ─────────────────

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(autouse=True)
def _ecb(monkeypatch):
    """The month's EUR:USD reference rate, 1.10.

    Units per ONE EUR, the ECB's own shape: a pair X:USD is
    units["USD"] / units["X"], and EUR itself is 1. Every month answers the
    same rates, so no test has to know which month its charges fall in.
    Typed Settings rates were retired 2026-09-23; a rate now reaches a
    month only by being fetched."""
    from expense_recon.web import ecb_rates

    def _fetch(start, end, **kw):
        months = ["2026-%02d" % m for m in range(1, 13)]
        return {m: {"USD": "1.10"} for m in months if start <= m <= end}

    monkeypatch.setattr(ecb_rates, "fetch_monthly", _fetch)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _xlsx_bytes(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_route_a_spoken_for_rival_lets_the_true_pair_reconcile(
    client, monkeypatch
):
    """The live July Enchilada / Wix instance, end to end through the app.

    The EUR receipt agrees with the ENCHILADA charge at the month's
    reference rate (30.00 x 1.10 = 33.00, exact) and ALSO lands within the
    clean reference band of the WIX charge at 33.50. Before round B that rival
    demoted it and the reviewer had to pick a pair the tool had already
    solved. WIX holds a bank-printed exact match with its own USD receipt,
    so it was never available: the EUR pair reconciles on its own, and the
    reason the SPA renders says why.
    """
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-08-10", total="30.00", currency="EUR",
                vendor="Enchilada Karlsruhe", reference="ZE-81005",
                line_items=(), confidence=0.9, notes="",
            ),
            ExtractedReceipt(
                date="2026-08-10", total="33.50", currency="USD",
                vendor="Wix.com", reference="WX-2211",
                line_items=(), confidence=0.9, notes="",
            ),
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=False, same_purchase_confidence=0.1,
                implied_rate=1.0, converted_amount=Decimal("0"),
                reasoning="not consulted: the pair resolves deterministically",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )

    resp = client.put("/api/settings", json={
        "entities": {"Corporate Services": {}},
        "cards": {
            "corp-2838": {
                "label": "Corporate card (Chase)", "digits": ["2838"],
                "entity": "Corporate Services", "currency": "USD",
            },
        },
    })
    assert resp.status_code == 200, resp.text

    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "August 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + str(i).encode(), "application/octet-stream"))
            for i, name in enumerate(["Enchilada.jpg", "Wix.jpg"])
        ],
    ))
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("August2026.xlsx", _xlsx_bytes([
            (datetime(2026, 8, 10), "ENCHILADA KARLSRUHE", "Sale", -33.00),
            (datetime(2026, 8, 10), "WIX.COM 1251593381", "Sale", -33.50),
        ]), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))

    view = client.get(f"/api/runs/{batch_id}").json()
    row = next(r for r in view["rows"] if "ENCHILADA" in r["vendor"])
    assert row["effective_bucket"] == "reconciled", row
    chosen = next(c for c in row["candidates"] if c["is_chosen"])
    assert chosen["match_type"] == "fx_reference"
    assert chosen["requires_review"] is False
    assert (
        "Kept deterministic: the rival pairing is spoken for." in chosen["reason"]
    ), chosen["reason"]

    wix = next(r for r in view["rows"] if "WIX" in r["vendor"])
    assert wix["effective_bucket"] == "reconciled"
