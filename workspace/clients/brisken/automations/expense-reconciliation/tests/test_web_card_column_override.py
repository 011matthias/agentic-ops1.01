"""The statement's card column can be named explicitly (WS3 escape hatch).

`inspect.guess_column_map` claims `card` from deliberately tight header
patterns, because a false positive scopes every receipt to a card that is
really something else. The cost of that tightness is that a statement
spelling the column any other way silently loses card scoping -- and until
now neither front end could say which column it was, because
`_parse_run_form` exposed overrides for five fields and `card` was not one
of them.

These cover the new `map_card` override end to end: the resolver honors it,
an empty value stays a no-op (so every existing run keeps the guessed map
byte for byte), and the form field actually reaches the resolved config
through `POST /api/runs`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import (  # noqa: E402
    LOCAL_RUN_CONFIG_NAME,
    STATEMENT_MAP_FIELDS,
    RunForm,
    _resolve_statement_map,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

# "Acct Last 4" is outside the guess's patterns (^card$, card number/no/#,
# card last 4) on purpose: this is the statement the operator has to rescue.
UNGUESSABLE = (
    "Date,Description,Amount,Acct Last 4\n"
    "04/01/2026,COFFEE SHOP NYC,5.75,2838\n"
    "04/02/2026,AWS CLOUD SERVICES,100.00,3645\n"
)
# A plain "Card" header is claimed by the guess with no help needed.
GUESSABLE = (
    "Date,Description,Amount,Card\n"
    "04/01/2026,COFFEE SHOP NYC,5.75,2838\n"
)


def _run_form(**kw) -> RunForm:
    base = dict(
        account_id="chase-2838",
        account_legal_entities={},
        account_card_currency="USD",
        sheet_name=None,
        column_map_overrides={},
        receipts_source="csv",
        expense_column_map={},
        receipts_default_currency="",
        use_llm=False,
    )
    base.update(kw)
    return RunForm(**base)


def _csv(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "statement.csv"
    path.write_text(body, encoding="utf-8")
    return path


def test_card_is_an_overridable_field():
    assert "card" in STATEMENT_MAP_FIELDS


# ── the resolver ─────────────────────────────────────────────────────


def test_guess_declines_a_header_outside_its_patterns(tmp_path):
    """Baseline: without help, this statement has no card column at all,
    which is exactly the silent scoping loss the override exists to fix."""
    column_map = _resolve_statement_map(_csv(tmp_path, UNGUESSABLE), _run_form())
    assert "card" not in column_map


def test_override_names_the_card_column(tmp_path):
    column_map = _resolve_statement_map(
        _csv(tmp_path, UNGUESSABLE),
        _run_form(column_map_overrides={"card": "Acct Last 4"}),
    )
    assert column_map["card"] == "Acct Last 4"
    # The other fields still come from the guess.
    assert column_map["amount"] == "Amount"
    assert column_map["transaction_date"] == "Date"


def test_override_wins_over_the_guess(tmp_path):
    """A guessable header plus an explicit override resolves to the
    override, not the guess."""
    column_map = _resolve_statement_map(
        _csv(tmp_path, GUESSABLE + "04/02/2026,X,1.00,3645\n"),
        _run_form(column_map_overrides={"card": "Description"}),
    )
    assert column_map["card"] == "Description"


def test_empty_override_is_a_no_op(tmp_path):
    """`map_card=""` must not write an empty header over the guess -- this
    is what keeps every run that sends no card override unchanged."""
    column_map = _resolve_statement_map(
        _csv(tmp_path, GUESSABLE), _run_form(column_map_overrides={"card": ""})
    )
    assert column_map["card"] == "Card"


# ── the form field reaches the run ───────────────────────────────────


def test_api_runs_threads_map_card_into_the_resolved_config(tmp_path):
    """POST /api/runs with map_card lands in the run's config column_map.
    The pipeline runs in the background and is irrelevant here; what is
    asserted is that the form field survived _parse_run_form ->
    prepare_run -> _resolve_statement_map."""
    app = create_app(tmp_path)
    client = TestClient(app)
    res = client.post(
        "/api/runs",
        files={
            "statement": ("statement.csv", UNGUESSABLE.encode(), "text/csv"),
            "receipts": (
                "receipts.csv",
                (EXAMPLES / "receipts.example.csv").read_bytes(),
                "text/csv",
            ),
        },
        data={
            "account_id": "chase-2838",
            "account_card_currency": "USD",
            "receipts_source": "csv",
            "map_card": "Acct Last 4",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["job_id"]

    # prepare_run writes a self-contained copy of the resolved config beside
    # the uploads; it is the run's own record of the column map it used.
    configs = list(tmp_path.glob(f"**/{LOCAL_RUN_CONFIG_NAME}"))
    assert configs, "prepare_run wrote no run config"
    cfg = json.loads(configs[0].read_text(encoding="utf-8"))
    assert cfg["statement"]["column_map"]["card"] == "Acct Last 4"
