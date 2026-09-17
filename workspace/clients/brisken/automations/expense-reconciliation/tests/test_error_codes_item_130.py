"""Item 130: every refusal carries a stable code beside its English sentence.

Two halves, and the first is the one that keeps this true next month:

* A SOURCE SCAN over the web layer. A new refusal site that answers with an
  `error` and no `code`, a `RunInputError` raised without naming its
  condition, a service refusal dict with no `error_code`, a helper that
  returns a bare English sentence, a settings normalizer raising a plain
  `ValueError`: each one fails here, at the site, before it can reach
  Criss's screen in English.
* ROUTE TESTS through the app, one per refusal FAMILY (auth, not-found,
  validation, a decision, a publish gate, a service refusal dict, an input
  refusal, a settings refusal) plus the setup advisories, so the codes are
  known to survive the wire and not just to exist in the source.

The English `error` is never removed or reworded by any of this: a client
reading it today keeps reading it (docs/api-contract.md, "Error codes").
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import expense_recon  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

SRC = Path(expense_recon.__file__).resolve().parent
WEB = SRC / "web"
CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# The three helpers in app.py that BUILD a refusal body out of a value the
# scan cannot read (a service dict, a coded sentence, a RunInputError).
# Every other JSONResponse with a 4xx/5xx status has to spell its dict out.
BODY_BUILDERS = {"_refusal_response", "_refused", "_input_refused"}

# Helpers that answer with an English sentence instead of raising. Each
# must hand back a `Refusal`, which carries the code and the named values.
SENTENCE_HELPERS = {
    "validate_manual_match",
    "attach_emailed_receipt",
    "confirm_expense_category",
    "validate_trip_fields",
    "validate_expense_field",
    "prepare_row_card_fix",
    "sync_claim_for_decision",
    "statement_advisory",
    "_statement_source_advisory",
}

NORMALIZERS = {
    "normalize_cards_setting": SRC / "cards.py",
    "normalize_merchants_setting": SRC / "merchant_registry.py",
    "normalize_cost_centers_setting": SRC / "cost_centers.py",
    "normalize_intake_setting": WEB / "intake_mail.py",
}


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _dict_keys(node: ast.Dict) -> list[str]:
    return [
        k.value for k in node.keys
        if isinstance(k, ast.Constant) and isinstance(k.value, str)
    ]


def _dict_value(node: ast.Dict, key: str):
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value == key:
            return v
    return None


def _func_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def _enclosing_functions(tree: ast.AST) -> dict[int, str]:
    """line number -> the innermost function def that contains it."""
    out: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                out[line] = node.name
    return out


def _kw(call: ast.Call, name: str):
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


# ── the source scan ──────────────────────────────────────────────────────


def test_every_json_error_body_in_app_names_its_condition():
    """A `JSONResponse` that refuses carries a `code`.

    Regressing any single `"code": "..."` out of a body fails here with the
    line number of the site that lost it.
    """
    tree = _tree(WEB / "app.py")
    inside = _enclosing_functions(tree)
    bad: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _func_name(node) != "JSONResponse":
            continue
        status = _kw(node, "status_code")
        refusing = isinstance(status, ast.Constant) and status.value >= 400
        first = node.args[0] if node.args else None
        if isinstance(first, ast.Dict):
            keys = _dict_keys(first)
            if "error" in keys and "code" not in keys:
                bad.append(f"line {node.lineno}: error body with no code")
            continue
        if not refusing:
            continue
        if inside.get(node.lineno) in BODY_BUILDERS:
            continue
        if isinstance(first, ast.Call) and _func_name(first) == "denial_body":
            continue
        bad.append(
            f"line {node.lineno}: {status.value} whose body the scan cannot read"
        )
    assert not bad, "refusals without a code:\n" + "\n".join(bad)


def test_no_refusal_in_app_answers_as_plain_text():
    """A refusal is JSON, so it can carry a code at all. An HTML or text
    4xx (the download routes answered `"Run not found"` as HTML until
    item 130) cannot, and the SPA's download path parses it as JSON."""
    tree = _tree(WEB / "app.py")
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _func_name(node) not in ("HTMLResponse", "PlainTextResponse", "Response"):
            continue
        status = _kw(node, "status_code")
        if isinstance(status, ast.Constant) and status.value >= 400:
            bad.append(f"line {node.lineno}: {_func_name(node)} {status.value}")
    assert not bad, "refusals answered as plain text:\n" + "\n".join(bad)


def test_every_run_input_error_names_its_condition():
    bad = []
    for path in sorted(SRC.rglob("*.py")):
        tree = _tree(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _func_name(node) != "RunInputError":
                continue
            code = _kw(node, "code")
            if isinstance(code, ast.Constant) and CODE_RE.match(str(code.value)):
                continue
            if isinstance(code, ast.Call) and _func_name(code) == "code_of":
                continue  # a code carried in from the value that was caught
            bad.append(f"{path.name}:{node.lineno}")
    assert not bad, "RunInputError raised without a code: " + ", ".join(bad)


def test_every_service_refusal_dict_names_its_condition():
    """The service layer answers a route with `{error, code: <http status>}`.
    The int status never reaches the wire; `error_code` is what becomes the
    body's `code`, so a refusal dict without one would answer the generic
    `request_refused`."""
    bad = []
    for path in (WEB / "service.py", WEB / "intake_mail.py"):
        for node in ast.walk(_tree(path)):
            if not isinstance(node, ast.Dict):
                continue
            keys = _dict_keys(node)
            if "error" not in keys or "code" not in keys:
                continue
            status = _dict_value(node, "code")
            if not (isinstance(status, ast.Constant)
                    and isinstance(status.value, int)):
                continue
            err_code = _dict_value(node, "error_code")
            if not (isinstance(err_code, ast.Constant)
                    and CODE_RE.match(str(err_code.value))):
                bad.append(f"{path.name}:{node.lineno}")
    assert not bad, "service refusal dicts without an error_code: " + ", ".join(bad)


def test_the_helpers_that_return_a_sentence_return_a_coded_one():
    """`validate_expense_field` and its siblings answer with a sentence the
    route puts on the wire. A bare string there is a sentence with no code,
    which is exactly the defect."""
    bad = []
    for node in ast.walk(_tree(WEB / "service.py")):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in SENTENCE_HELPERS:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Return) or inner.value is None:
                continue
            values = (
                inner.value.elts if isinstance(inner.value, ast.Tuple)
                else [inner.value]
            )
            for value in values:
                if isinstance(value, (ast.JoinedStr, ast.BinOp)) or (
                    isinstance(value, ast.Constant) and isinstance(value.value, str)
                ):
                    bad.append(f"{node.name}:{inner.lineno}")
    assert not bad, "uncoded sentences returned by: " + ", ".join(bad)


def test_the_settings_normalizers_name_their_condition():
    bad = []
    for name, path in NORMALIZERS.items():
        found = False
        for node in ast.walk(_tree(path)):
            if not isinstance(node, ast.FunctionDef) or node.name != name:
                continue
            found = True
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Raise) or inner.exc is None:
                    continue
                call = inner.exc if isinstance(inner.exc, ast.Call) else None
                if call is None or _func_name(call) != "CodedValueError":
                    bad.append(f"{name}:{inner.lineno} raises an uncoded error")
                    continue
                code = _kw(call, "code")
                if not (isinstance(code, ast.Constant)
                        and CODE_RE.match(str(code.value))):
                    bad.append(f"{name}:{inner.lineno} has no code")
        assert found, f"{name} not found in {path.name}"
    assert not bad, "\n".join(bad)


def test_every_setup_advisory_names_its_condition():
    """The amber boxes at the top of a month are prose too (item 130). Each
    advisory carries a code and the numbers its sentence used."""
    bad = []
    for node in ast.walk(_tree(WEB / "service.py")):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in ("_setup_advisories", "_fx_rate_drift_advisories"):
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Dict):
                continue
            keys = _dict_keys(inner)
            if "setting" not in keys:
                continue
            if "code" not in keys or "message" not in keys:
                bad.append(f"{node.name}:{inner.lineno}")
    assert not bad, "advisories without a code: " + ", ".join(bad)


def test_every_code_is_a_stable_snake_case_identifier():
    """A code is an identifier, never a sentence: the SPA keys an i18n entry
    off it, so a space or a capital in one is a key that cannot be written."""
    bad = []
    for path in (*sorted(WEB.glob("*.py")), SRC / "cards.py",
                 SRC / "merchant_registry.py", SRC / "cost_centers.py"):
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Call):
                code = _kw(node, "code")
                if (isinstance(code, ast.Constant)
                        and isinstance(code.value, str)
                        and not CODE_RE.match(code.value)):
                    bad.append(f"{path.name}:{node.lineno}: {code.value!r}")
            if isinstance(node, ast.Dict):
                value = _dict_value(node, "error_code")
                if (isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and not CODE_RE.match(value.value)):
                    bad.append(f"{path.name}:{node.lineno}: {value.value!r}")
    assert not bad, "codes that are not snake_case:\n" + "\n".join(bad)


def test_not_found_always_takes_a_code():
    """`_not_found` composes a 404 body; its second argument IS the code."""
    bad = []
    for node in ast.walk(_tree(WEB / "app.py")):
        if isinstance(node, ast.Call) and _func_name(node) == "_not_found":
            if len(node.args) != 2:
                bad.append(f"line {node.lineno}")
    assert not bad, "_not_found called without a code: " + ", ".join(bad)


# ── the wire ─────────────────────────────────────────────────────────────

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
CORP = {"corp-1672": {"digits": ["1672"], "entity": "Corporate Services",
                      "person": "Nicolas"}}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("EXPENSE_RECON_OPERATOR_CODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


@pytest.fixture
def gated_client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", "test-code-1234")
    with TestClient(create_app(tmp_path)) as c:
        yield c


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


def _month(client, monkeypatch, label="August 2026", n_files=0, extractions=()):
    # Receipt OCR runs through the model even for an empty month (the
    # pipeline refuses a folder source with no client), so every month
    # here is built against the stub.
    _patch_ocr(monkeypatch, *(
        extractions or [_extraction() for _ in range(max(n_files, 1))]
    ))
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    batch_id = body["batch_id"]
    if n_files:
        files = [
            ("files", (f"r{i}.jpg", JPG + bytes([i]), "application/octet-stream"))
            for i in range(n_files)
        ]
        resp = client.post(f"/api/expense-batches/{batch_id}/receipts", files=files)
        assert resp.status_code == 200, resp.text
        assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _classic_run(client):
    files = {
        "statement": ("statement.example.csv",
                      (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv"),
        "receipts": ("receipts.example.csv",
                     (EXAMPLES / "receipts.example.csv").read_bytes(), "text/csv"),
    }
    resp = client.post("/api/intakes", files=files,
                       data={"card_name": "Corp 2838", "month": "2026-06"})
    assert resp.status_code == 200, resp.text
    intake_id = resp.json()["intake_id"]
    resp = client.post(f"/api/intakes/{intake_id}/run",
                       data={"account_id": "2838", "account_card_currency": "USD"})
    assert resp.status_code == 200, resp.text
    return resp.json()["run_id"]


def test_an_unauthenticated_request_is_refused_by_code(gated_client):
    resp = gated_client.get("/api/operator/state")
    assert resp.status_code == 401
    assert resp.json() == {"error": "authentication required",
                           "code": "unauthenticated"}


def test_an_unknown_run_answers_run_not_found(client):
    resp = client.get("/api/runs/nope")
    assert resp.status_code == 404
    assert resp.json() == {"error": "run not found", "code": "run_not_found"}


def test_a_path_no_route_serves_answers_not_found(client):
    resp = client.get("/api/nothing-here")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "not_found"
    # FastAPI's own `detail` survives for anything already reading it.
    assert body["detail"] == "Not Found"


def test_a_body_the_route_cannot_read_answers_validation_failed(client):
    resp = client.post("/api/runs", data={"account_id": "2838"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "validation_failed"
    assert body["error"]
    assert isinstance(body["detail"], list) and body["detail"]


def test_a_field_edit_the_tool_cannot_store_is_refused_by_code(
    client, monkeypatch
):
    batch = _month(client, monkeypatch)
    resp = client.put(f"/api/runs/{batch}/expenses/x.jpg",
                      json={"field": "nope", "value": "1"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "unknown_field"
    assert resp.json()["field"] == "nope"

    # The sentence a helper returns carries the code AND the named value.
    resp = client.put(f"/api/runs/{batch}/expenses/x.jpg",
                      json={"field": "date", "value": "yesterday"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_date"
    assert resp.json()["field"] == "date"
    assert resp.json()["error"] == "date must be YYYY-MM-DD"


def test_a_decision_a_company_card_forbids_is_refused_by_code(client, monkeypatch):
    client.put("/api/settings", json={"cards": CORP})
    batch = _month(client, monkeypatch, n_files=1,
                   extractions=[_extraction(payment_hint="Visa ...1672")])
    grid = client.get(f"/api/expense-batches/{batch}").json()
    doc = grid["expenses"][0]["document_id"]

    resp = client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                       json={"private": True, "reimburse_to": "Dirk"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "company_card"
    assert body["card"]["key"] == "corp-1672"
    assert body["error"].startswith("This expense was paid with the company card")


def test_publishing_a_month_with_no_statement_is_refused_by_code(
    client, monkeypatch
):
    batch = _month(client, monkeypatch)
    resp = client.post(f"/api/runs/{batch}/publish", json={})
    assert resp.status_code == 400
    assert resp.json()["code"] == "no_statement"


def test_an_input_refusal_carries_its_code_and_its_file(client, monkeypatch):
    batch = _month(client, monkeypatch)
    resp = client.post(f"/api/expense-batches/{batch}/set-aside/restore",
                       json={"file": "nope.jpg"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "set_aside_file_not_found"
    assert body["file"] == "nope.jpg"
    assert "nope.jpg" in body["error"]


def test_a_service_refusal_dict_reaches_the_wire_as_a_code(client):
    resp = client.delete("/api/trips/nope")
    assert resp.status_code == 404
    body = resp.json()
    assert body == {"error": "Trip not found", "code": "trip_not_found"}


def test_a_settings_refusal_carries_the_key_it_refused(client):
    resp = client.put("/api/settings", json={"nope": 1})
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "unknown_settings_keys"
    assert body["keys"] == ["nope"]

    resp = client.put("/api/settings",
                      json={"cards": {"x": {"aliases": ["Visa"]}}})
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "card_alias_generic"
    assert body["card"] == "x" and body["alias"] == "Visa"
    assert body["setting"] == "cards"


def test_every_setup_advisory_on_a_real_month_carries_its_code(client):
    run_id = _classic_run(client)
    advisories = client.get(f"/api/runs/{run_id}").json()["summary"][
        "setup_advisories"
    ]
    assert advisories, "this run has no chart of accounts, so it advises"
    assert all(a.get("code") and a.get("message") for a in advisories)
    assert "no_chart_of_accounts" in {a["code"] for a in advisories}
