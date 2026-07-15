"""Anchored reviewer feedback: the base.html double-click widget posts to
/feedback; reading the log is operator-only. See web/app.py + web/auth.py."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402

USER_CODE = "user-code-1"
OP_CODE = "operator-code-1"


@pytest.fixture
def data_root(tmp_path):
    return tmp_path


@pytest.fixture
def gated_client(data_root, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", USER_CODE)
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    monkeypatch.setenv("EXPENSE_RECON_INSECURE_COOKIE", "1")
    app = create_app(data_root)
    with TestClient(app) as c:
        yield c


def _login(client, code):
    resp = client.post("/login", data={"code": code}, follow_redirects=False)
    assert resp.status_code == 303


def test_widget_rides_every_logged_in_page(gated_client):
    _login(gated_client, USER_CODE)
    for path in ("/", "/help"):
        resp = gated_client.get(path)
        assert resp.status_code == 200
        assert 'id="fbPop"' in resp.text
        assert "feedback-fab" in resp.text


def test_login_page_carries_no_widget(gated_client):
    resp = gated_client.get("/login")
    assert resp.status_code == 200
    assert "fbPop" not in resp.text


def test_post_lands_in_jsonl_with_session_attribution(gated_client, data_root):
    _login(gated_client, USER_CODE)
    resp = gated_client.post(
        "/feedback",
        json={
            "comment": "This total looks off",
            "section": "Needs your attention",
            "anchor": "USD 1,234.56",
            "selector": "#run > table > tr:nth-of-type(2)",
            "pos": {
                "pageX": 100,
                "pageY": 2000.7,
                "pct": 41,
                "vw": 1440,
                "vh": 900,
                "docH": True,  # bool is not a coordinate; dropped
                "bogus": 12,  # unknown field; dropped
            },
            "path": "/runs/abc123",
            "title": "Run abc123",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    lines = (data_root / "feedback.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["role"] == "user"
    assert entry["comment"] == "This total looks off"
    assert entry["page"] == "/runs/abc123"
    assert entry["run_id"] == "abc123"
    assert entry["section"] == "Needs your attention"
    assert entry["anchor"] == "USD 1,234.56"
    assert entry["pos"] == {"pageX": 100, "pageY": 2000, "pct": 41, "vw": 1440, "vh": 900}
    assert entry["ts"]


def test_non_run_page_has_no_run_id(gated_client, data_root):
    _login(gated_client, OP_CODE)
    gated_client.post("/feedback", json={"comment": "nav note", "path": "/memory"})
    entry = json.loads(
        (data_root / "feedback.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert entry["role"] == "operator"
    assert entry["run_id"] is None


def test_feedback_requires_login(gated_client):
    resp = gated_client.post("/feedback", json={"comment": "hi"})
    assert resp.status_code == 401


def test_bad_payloads_rejected(gated_client, data_root):
    _login(gated_client, USER_CODE)
    assert gated_client.post("/feedback", json={"comment": "   "}).status_code == 400
    assert (
        gated_client.post(
            "/feedback", content=b"not json", headers={"Content-Type": "application/json"}
        ).status_code
        == 400
    )
    assert gated_client.post("/feedback", json=["a", "list"]).status_code == 400
    assert not (data_root / "feedback.jsonl").exists()


def test_log_routes_are_operator_only(gated_client):
    _login(gated_client, USER_CODE)
    for path in ("/feedback-log", "/feedback.jsonl"):
        resp = gated_client.get(path, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"


def test_operator_sees_the_note_in_log_and_raw(gated_client):
    _login(gated_client, USER_CODE)
    gated_client.post(
        "/feedback", json={"comment": "Rename this column", "path": "/runs/r1"}
    )
    _login(gated_client, OP_CODE)  # switch the session cookie to operator
    page = gated_client.get("/feedback-log")
    assert page.status_code == 200
    assert "Rename this column" in page.text
    assert "/runs/r1" in page.text
    raw = gated_client.get("/feedback.jsonl")
    assert raw.status_code == 200
    assert raw.headers["content-type"].startswith("application/x-ndjson")
    assert "Rename this column" in raw.text


def test_empty_log_renders(gated_client):
    _login(gated_client, OP_CODE)
    page = gated_client.get("/feedback-log")
    assert page.status_code == 200
    assert "No feedback yet" in page.text
    raw = gated_client.get("/feedback.jsonl")
    assert raw.status_code == 200
    assert raw.text == ""


def test_state_api_reports_feedback_count(gated_client):
    _login(gated_client, OP_CODE)
    assert gated_client.get("/api/operator/state").json()["feedback"]["count"] == 0
    gated_client.post("/feedback", json={"comment": "note one"})
    gated_client.post("/feedback", json={"comment": "note two"})
    state = gated_client.get("/api/operator/state").json()
    assert state["feedback"]["count"] == 2
