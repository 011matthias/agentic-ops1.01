"""Contract test: the element type of every list field on the two view payloads.

Backlog item 21. On 2026-08-22 Criss's batch page died on React error #31 for
every batch that HAD a parse issue: `parse_issues` ships as objects
(`{file, line, message, severity}`) and the SPA typed it `string[]` and
rendered each item directly. Nothing caught it. The SPA is a separate repo
with no type-check against the live API, and the rest of the suite asserts the
backend's shape only where a feature test happens to touch it, so a
`str -> dict` change in a list is invisible until it reaches her screen.

This test pins the ELEMENT TYPE of every list field on the two payloads the
SPA renders — the expense-batch view (`build_expense_view`, GET
/api/expense-batches/{id}) and the run view (`build_view`, GET
/api/runs/{id}) — probed over the HTTP layer so the pinned shape is what
actually ships, `jsonable_encoder` included.

Three assertions per view:

1. **No unpinned field.** The set of list paths in the payload equals
   `CONTRACT`'s. A new list field fails until it is pinned here — which is the
   moment to decide whether the SPA needs a prompt for it.
2. **No element-type drift.** Every non-empty list matches its pinned kind.
   `parse_issues[]` flipping to `string` (or a `string[]` field flipping to
   `object`) fails in CI.
3. **Non-vacuity.** Every path in `MUST_COVER` is actually non-empty in the
   fixtures. Without this a weakened fixture would let assertion 2 pass by
   observing nothing — the exact shape of a test that guards nothing.

Paths use `.` for object keys and `[]` for list elements, so
`expenses[].books_as[]` is "the books_as list on an element of expenses".
Kinds are the JSON kinds (`string` / `number` / `boolean` / `object` /
`array` / `null`), `|`-joined and sorted when a list is heterogeneous.

What this does NOT cover, deliberately: the type of a scalar field. A
`books_as[].amount` going from `"42.50"` to `42.50`, or a non-list field
growing into an object, passes here. Pinning every leaf would be a table of
several hundred paths that churns on every round; lists are where the crash
class lives, because a list is the only place the SPA maps over elements it
did not individually type.

The human-readable companion is `docs/api-contract.md`; when a pin changes
here, that doc and the relevant Lovable prompt change with it.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import (  # noqa: E402
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


# ── the pinned contract ──────────────────────────────────────────────
#
# path -> element kind. Adding, removing, or retyping a list field on either
# view means editing this table, `docs/api-contract.md`, and the SPA in the
# same change. That is the point: the edit is the reminder.

EXPENSE_BATCH_CONTRACT = {
    "account_options[]": "string",
    "card_review.resolved[]": "object",
    "card_review.resolved[].hints[]": "string",
    "card_review.unresolved_hints[]": "object",
    "card_review.unresolved_hints[].documents[]": "string",
    # Item 35: the member spellings of a canonically-grouped hint row.
    # Parallel to `hint` (which keeps the most-frequent spelling), so a
    # stale SPA renders one truthful row while an updated one shows the
    # group and submits every spelling on Assign.
    "card_review.unresolved_hints[].spellings[]": "string",
    "category_options[]": "string",
    # PR 3: per-card coverage. `digits[]` and `statements[]` are the two
    # lists inside an entry; both are plain strings, and both are empty on
    # an entry the month knows only from its registry.
    "coverage[]": "object",
    "coverage[].digits[]": "string",
    "coverage[].statements[]": "string",
    "duplicate_groups[]": "object",
    "duplicate_groups[].members[]": "string",
    "entity_options[]": "string",
    "expenses[]": "object",
    "expenses[].books_as[]": "object",
    "expenses[].category_variance.categories[]": "string",
    "expenses[].edited_fields[]": "string",
    "expenses[].line_items[]": "object",
    # Legacy raw issue rows: (file, line, message, severity) tuples, kept for
    # any existing reader. `parse_issues` is the shape the SPA renders.
    "parse_errors[]": "array",
    "parse_errors[][]": "number|string",
    "parse_issues[]": "object",
    "set_aside[]": "object",
    # PR 2b-2b-2: the statement uploads this month has taken. The month page
    # is where the next one is uploaded, so the grid carries it too.
    "statements[]": "object",
    "summary.upload_issues[]": "string",
    # Item 20: the same rejections with a stable code beside the prose. The
    # prose list stays `string[]` on purpose — enriching it in place is the
    # move that took the batch page down (see docs/api-contract.md).
    "summary.upload_issue_details[]": "object",
    # Item 38: the trip entity on a trip batch's grid (null on company
    # months, so the path appears only via the trip fixture). The roster
    # is person NAMES, plain strings.
    "trip.travelers[]": "string",
}

RUN_CONTRACT = {
    "assignable_receipts[]": "object",
    "category_options[]": "string",
    "coverage[]": "object",
    "coverage[].digits[]": "string",
    "coverage[].statements[]": "string",
    "duplicate_charges[]": "array",
    "duplicate_charges[][]": "object",
    "duplicate_groups[]": "object",
    "duplicate_groups[].members[]": "string",
    "duplicate_receipts[]": "array",
    "duplicate_receipts[][]": "object",
    "duplicate_receipts[][].line_items[]": "object",
    "parse_errors[]": "array",
    "parse_errors[][]": "number|string",
    "parse_issues[]": "object",
    "rows[]": "object",
    "rows[].candidates[]": "object",
    "rows[].candidates[].receipt.line_items[]": "object",
    "statements[]": "object",
    "summary.setup_advisories[]": "object",
    "unmatched_receipts[]": "object",
    "unmatched_receipts[].line_items[]": "object",
    "unmatched_transactions[]": "object",
}

# Paths the fixtures MUST actually populate. Everything the SPA renders as
# text belongs here; a path outside it is pinned but only checked when the
# fixture happens to fill it.
EXPENSE_BATCH_MUST_COVER = {
    "parse_issues[]",
    "parse_errors[]",
    "set_aside[]",
    "expenses[]",
    "expenses[].books_as[]",
    "expenses[].line_items[]",
    "expenses[].edited_fields[]",
    "expenses[].category_variance.categories[]",
    "duplicate_groups[]",
    "card_review.unresolved_hints[]",
    "card_review.unresolved_hints[].spellings[]",
    "card_review.resolved[]",
    "card_review.resolved[].hints[]",
    "summary.upload_issues[]",
    "summary.upload_issue_details[]",
    "account_options[]",
    "category_options[]",
    "entity_options[]",
    "statements[]",
    "coverage[]",
    "coverage[].digits[]",
    "coverage[].statements[]",
    "trip.travelers[]",
}

RUN_MUST_COVER = {
    "parse_issues[]",
    "parse_errors[]",
    "rows[]",
    "rows[].candidates[]",
    "unmatched_transactions[]",
    "unmatched_receipts[]",
    "assignable_receipts[]",
    "duplicate_groups[]",
    "duplicate_charges[]",
    "duplicate_receipts[]",
    "category_options[]",
    "summary.setup_advisories[]",
    "statements[]",
    "coverage[]",
    "coverage[].digits[]",
    "coverage[].statements[]",
}


# ── the probe ────────────────────────────────────────────────────────


def _kind(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):  # before int: bool is an int subclass
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _walk(node, path: str, out: dict[str, set[str]]) -> None:
    """Record the element kinds of every list reachable from `node`.

    Elements of a list are merged into one representative object before
    recursing, so an optional key present on only one element still gets
    walked; list-valued keys CONCATENATE across elements, so a nested list is
    covered when any element fills it (one row with no candidates must not
    hide the shape of the row that has them).
    """
    if isinstance(node, dict):
        for key, value in node.items():
            _walk(value, f"{path}.{key}" if path else key, out)
        return
    if not isinstance(node, list):
        return

    here = path + "[]"
    out.setdefault(here, set()).update(_kind(x) for x in node)
    merged: dict = {}
    for element in node:
        if isinstance(element, dict):
            for key, value in element.items():
                if isinstance(value, list):
                    prior = merged.get(key)
                    merged[key] = (prior if isinstance(prior, list) else []) + value
                elif key not in merged or merged[key] is None:
                    merged[key] = value
        elif isinstance(element, list):
            _walk(element, here, out)
    if merged:
        _walk(merged, here, out)


def probe(*payloads: dict) -> dict[str, set[str]]:
    """Union the list-path -> element-kind map across several payloads."""
    out: dict[str, set[str]] = {}
    for payload in payloads:
        _walk(payload, "", out)
    return out


def _assert_contract(observed: dict[str, set[str]], contract: dict[str, str],
                     must_cover: set[str], view: str) -> None:
    new = sorted(set(observed) - set(contract))
    assert not new, (
        f"{view}: unpinned list field(s) {new}. Add them to the contract table "
        f"in this file and to docs/api-contract.md, and check whether the SPA "
        f"renders them (item 21: parse_issues shipped as objects against a "
        f"string[] renderer and took the page down)."
    )
    gone = sorted(set(contract) - set(observed))
    assert not gone, (
        f"{view}: pinned list field(s) {gone} are no longer in the payload. "
        f"Remove the pin here and in docs/api-contract.md if that is "
        f"intended, and tell the SPA."
    )
    drift = {
        path: (contract[path], "|".join(sorted(kinds)))
        for path, kinds in observed.items()
        if kinds and "|".join(sorted(kinds)) != contract[path]
    }
    assert not drift, (
        f"{view}: element-type drift {drift} (pinned, actual). The SPA renders "
        f"these; a str->object change breaks its page. Update the SPA + the "
        f"Lovable prompt, then re-pin here and in docs/api-contract.md."
    )
    uncovered = sorted(p for p in must_cover if not observed.get(p))
    assert not uncovered, (
        f"{view}: the fixtures no longer populate {uncovered}, so their element "
        f"type is unchecked. Restore the fixture coverage rather than dropping "
        f"the path from MUST_COVER."
    )


# ── fixtures: the payloads ───────────────────────────────────────────


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-07-01", total="42.50", currency="USD", vendor="Staples",
                reference="", line_items=(), confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _transaction(tx_id: str, day: int, vendor: str = "AMAZON",
                 amount: str = "180") -> Transaction:
    return Transaction(
        transaction_id=tx_id, legal_entity_id="le1", account_id="amex-usd",
        transaction_date=date(2026, 4, day), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor,
    )


def _receipt(doc_id: str, day: int, vendor: str = "AMAZON", amount: str = "180",
             items: tuple = ()) -> Receipt:
    return Receipt(
        document_id=doc_id, legal_entity_id="le1", detected_date=date(2026, 4, day),
        detected_total=Decimal(amount), detected_currency="USD",
        detected_vendor=vendor, detected_reference="R" + doc_id,
        line_items=tuple(items),
    )


def _item(total: str) -> LineItem:
    return LineItem(description="one item", line_total=Decimal(total))


def _statement_run(client) -> dict:
    """The real pipeline over the bundled examples: matched rows, unmatched
    transactions, assignable receipts, setup advisories."""
    resp = client.post("/api/runs", files={
        "statement": ("statement.example.csv",
                      (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv"),
        "receipts": ("receipts.example.csv",
                     (EXAMPLES / "receipts.example.csv").read_bytes(), "text/csv"),
    }, data={"account_id": "amex-9001", "legal_entity_id": "brisken-llc",
             "account_card_currency": "USD", "receipts_source": "csv"})
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    view = client.get(f"/api/runs/{job['run_id']}").json()
    assert view["rows"], view
    return view


def _synthetic_run(client, data_root: Path) -> dict:
    """A seeded snapshot for the buckets the example pair does not reach:
    ambiguous candidates, duplicate charges, duplicate receipts, parse issues
    of BOTH severities."""
    t1, t2, t3 = (_transaction("t1", 7), _transaction("t2", 8),
                  _transaction("t3", 9, "CAFE", "20"))
    r1, r2 = _receipt("d1", 7), _receipt("d2", 8, items=[_item("180")])
    r3 = _receipt("d3", 9, "CAFE", "20", items=[_item("20")])
    r4 = _receipt("d4", 10, "SOLO", "77", items=[_item("77")])
    # identical merchant + date + total + currency -> one duplicate-receipt group
    r5 = _receipt("d5", 11, "TWICE", "31", items=[_item("31")])
    r6 = _receipt("d6", 11, "TWICE", "31", items=[_item("31")])
    outcome = MatchOutcome(
        matches=[Match(transaction_id="t1", document_id="d1",
                       match_type=MatchType.EXACT, confidence=0.99, reason="exact",
                       score=95, amount_score=1.0, date_score=1.0, vendor_score=0.9)],
        unmatched_transactions=["t2"],
        unmatched_receipts=["d4", "d5", "d6"],
        ambiguous=[
            Match(transaction_id="t3", document_id="d3",
                  match_type=MatchType.AMBIGUOUS, confidence=0.6,
                  reason="two candidates", requires_review=True, score=61,
                  amount_score=1.0, date_score=0.8, vendor_score=0.4),
            Match(transaction_id="t3", document_id="d2",
                  match_type=MatchType.AMBIGUOUS, confidence=0.55,
                  reason="two candidates", requires_review=True, score=55,
                  amount_score=0.9, date_score=0.7, vendor_score=0.3),
        ],
    )
    snapshot = snapshot_to_dict(
        [t1, t2, t3], [r1, r2, r3, r4, r5, r6], outcome,
        [("statement.csv", 12, "row 12 unparseable", "error"),
         ("receipt_01_p7.png", 0, "looks like a report summary page", "warning")],
    )
    store = RunStore(data_root / "recon-web.sqlite")
    store.create_run(
        run_id="contract-synth", created_at="2026-07-21T00:00:00", label="synthetic",
        operator=None, summary={}, snapshot=snapshot, config={},
        work_dir=str(data_root), llm_enabled=False, has_coa=False,
    )
    store.close()
    view = client.get("/api/runs/contract-synth").json()
    assert view["parse_issues"], view
    return view


def _expense_batch(client, monkeypatch_setattr) -> dict:
    """One batch carrying every list surface the grid renders: a quarantined
    statement page (parse issue + set-aside), an unsupported upload (upload
    issue), a generic and an exact payment hint (card review, both halves),
    a duplicate pair, a field edit, and one vendor booked to two categories."""
    client.put("/api/settings", json={
        "entities": {
            "Corporate Services": {"account_picks": ["E500 Office Supplies"]},
            "Cloud Services": {},
        },
        "cards": {
            "corp-1672": {
                "label": "Corporate card (Chase)",
                "digits": ["2838", "1672"],
                "entity": "Corporate Services",
                "currency": "USD",
            },
        },
    })
    mock = MockLLMClient(extraction_responses=[
        # two Staples receipts: reclassified below into different categories
        _extraction(vendor="Staples", tax="5.00", tax_label="VAT",
                    payment_hint="Visa"),
        # an unregistered card under two spellings -> ONE grouped
        # unresolved row (item 35), covering the spellings[] pin
        _extraction(vendor="Staples", total="12.00", date="2026-07-02",
                    payment_hint="****0340"),
        # an identical pair -> a duplicate group
        _extraction(vendor="Dup Co", total="9.00", date="2026-07-03",
                    payment_hint="Visa ...1672"),
        _extraction(vendor="Dup Co", total="9.00", date="2026-07-03",
                    payment_hint="CARTAO ***********0340"),
        # a statement page among the receipts -> quarantine + parse issue
        _extraction(vendor=None, total="8796.35", document_type="statement"),
    ])
    monkeypatch_setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))

    resp = client.post("/api/expense-batches", files=[
        ("files", ("a.jpg", JPG, "application/octet-stream")),
        ("files", ("b.jpg", JPG + b"2", "application/octet-stream")),
        ("files", ("c.jpg", JPG + b"3", "application/octet-stream")),
        ("files", ("d.jpg", JPG + b"4", "application/octet-stream")),
        ("files", ("stmt.jpg", JPG + b"5", "application/octet-stream")),
        # not a receipt type -> summary.upload_issues
        ("files", ("notes.txt", b"not a receipt", "text/plain")),
    ], data={"legal_entity": "Corporate Services", "label": "Contract fixture"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "done", job
    batch_id = body["batch_id"]

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    staples = [e["document_id"] for e in grid["expenses"]
               if e["vendor"]["display"] == "Staples"]
    assert len(staples) == 2, grid["expenses"]
    # same vendor, two categories -> category_variance.categories
    for doc, category in zip(staples, ["Meals & Entertainment", "Travel & Transport"]):
        r = client.post(f"/api/runs/{batch_id}/categories",
                        json={"document_id": doc, "line_index": 0, "category": category})
        assert r.status_code == 200, r.text
    # a field override -> expenses[].edited_fields
    r = client.put(f"/api/runs/{batch_id}/expenses/{staples[0]}",
                   json={"field": "vendor", "value": "Edited Vendor"})
    assert r.status_code == 200, r.text

    view = client.get(f"/api/expense-batches/{batch_id}").json()
    assert view["parse_issues"], view["summary"]
    return view


def _reconciling_month(client, monkeypatch_setattr) -> tuple[dict, dict]:
    """A month that has taken TWO statement uploads, so `statements[]` is
    populated on both views it appears on.

    Its own batch rather than an extra step on `_expense_batch`: attaching a
    statement graduates a month into reconciliation, and that batch is
    carrying the grid's whole list surface (set-aside, card review, category
    variance, an edit). Coverage that specific stays where it is; this one
    only has to make the new pin non-vacuous, which is the reason MUST_COVER
    exists at all.
    """
    mock = MockLLMClient(extraction_responses=[_extraction()])
    monkeypatch_setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    # A registry card whose digits match the statement's account, so the
    # month's coverage entry carries a `digits[]` the pin can observe. A
    # batch snapshots the composed registry at CREATION, so this settings
    # write has to happen first.
    client.put("/api/settings", json={"cards": {"amex-9001": {
        "label": "Amex (contract fixture)", "digits": ["9001"],
        "entity": "Corporate Services",
    }}})
    resp = client.post("/api/expense-batches", files=[
        ("files", ("m.jpg", JPG + b"m", "application/octet-stream")),
    ], data={"legal_entity": "Corporate Services", "label": "Contract month"})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    for _ in range(2):
        r = client.post(
            f"/api/expense-batches/{batch_id}/statement",
            files={"statement": (
                "statement.example.csv",
                (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv",
            )},
            data={"account_id": "amex-9001",
                  "account_legal_entities": '{"amex-9001": "Corporate Services"}',
                  "account_card_currency": "USD"},
        )
        assert r.status_code == 200, r.text
        assert client.get(f"/jobs/{r.json()['job_id']}").json()["status"] == "done"

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    run = client.get(f"/api/runs/{batch_id}").json()
    assert len(grid["statements"]) == 2, grid["statements"]
    assert grid["statements"] == run["statements"]
    assert grid["coverage"] == run["coverage"], "one month, one coverage"
    assert any(c["digits"] and c["statements"] for c in grid["coverage"]), (
        grid["coverage"]
    )
    return grid, run


def _trip_batch(client, monkeypatch_setattr) -> dict:
    """A trip batch (item 38), so the `trip` object — and its travelers
    roster, the one new LIST — is observed on the expense-batch view."""
    trip = client.post("/api/trips", json={
        "name": "Contract trip", "start": "2026-07-01", "end": "2026-07-10",
        "travelers": ["Dirk Neumann", "Criss"],
    })
    assert trip.status_code == 200, trip.text
    mock = MockLLMClient(extraction_responses=[_extraction()])
    monkeypatch_setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", files=[
        ("files", ("t.jpg", JPG + b"t", "application/octet-stream")),
    ], data={"batch_type": "trip", "trip_id": trip.json()["trip_id"]})
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    view = client.get(f"/api/expense-batches/{resp.json()['batch_id']}").json()
    assert view["trip"]["travelers"], view["trip"]
    return view


@pytest.fixture(scope="module")
def payloads(tmp_path_factory):
    """Both views, built once — every list surface the SPA renders."""
    data_root = tmp_path_factory.mktemp("contract")
    monkey = pytest.MonkeyPatch()
    monkey.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkey.delenv("OPENAI_API_KEY", raising=False)
    try:
        app = create_app(data_root)
        with TestClient(app) as client:
            run_a = _statement_run(client)
            run_b = _synthetic_run(client, data_root)
            batch = _expense_batch(client, monkey.setattr)
            month_grid, month_run = _reconciling_month(client, monkey.setattr)
            trip_grid = _trip_batch(client, monkey.setattr)
        yield {
            "run": (run_a, run_b, month_run),
            "expense_batch": (batch, month_grid, trip_grid),
        }
    finally:
        monkey.undo()


# ── the tests ────────────────────────────────────────────────────────


def test_expense_batch_view_list_contract(payloads):
    observed = probe(*payloads["expense_batch"])
    _assert_contract(observed, EXPENSE_BATCH_CONTRACT, EXPENSE_BATCH_MUST_COVER,
                     "expense-batch view")


def test_run_view_list_contract(payloads):
    observed = probe(*payloads["run"])
    _assert_contract(observed, RUN_CONTRACT, RUN_MUST_COVER, "run view")


def test_parse_issues_are_objects_with_the_documented_keys(payloads):
    """The 2026-08-22 regression, pinned directly: the SPA reads `file`,
    `line`, `message`, `severity` off each entry. A flip back to a bare
    string, or a renamed key, fails here."""
    for view_name, views in payloads.items():
        for view in views:
            for issue in view["parse_issues"]:
                assert isinstance(issue, dict), (view_name, issue)
                assert set(issue) == {"file", "line", "message", "severity"}, (
                    view_name, issue)
                assert isinstance(issue["file"], str)
                assert isinstance(issue["line"], int)
                assert isinstance(issue["message"], str)
                assert issue["severity"] in ("error", "warning"), issue


def test_probe_detects_a_string_to_object_flip():
    """The probe itself: if it could not tell `["a"]` from `[{...}]`, every
    assertion above would be decorative."""
    before = probe({"parse_issues": ["row 12 unparseable"]})
    after = probe({"parse_issues": [
        {"file": "s.csv", "line": 12, "message": "unparseable", "severity": "error"},
    ]})
    assert before["parse_issues[]"] == {"string"}
    assert after["parse_issues[]"] == {"object"}
    # and the nested-list merge keeps a filled list visible behind an empty one
    merged = probe({"rows": [{"candidates": []}, {"candidates": [{"id": "x"}]}]})
    assert merged["rows[].candidates[]"] == {"object"}
