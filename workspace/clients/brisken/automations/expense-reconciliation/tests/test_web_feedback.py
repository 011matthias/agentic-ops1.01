"""Anchored reviewer feedback: the SPA widget posts to /api/feedback;
/feedback.jsonl is the raw download. See web/app.py + web/auth.py."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402

OP_CODE = "operator-code-1"


@pytest.fixture
def data_root(tmp_path):
    return tmp_path


@pytest.fixture
def client(data_root):
    app = create_app(data_root)
    with TestClient(app) as c:
        yield c


def test_post_lands_in_jsonl_with_session_attribution(client, data_root):
    resp = client.post(
        "/api/feedback",
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
    assert entry["role"] == "operator"  # the only role
    assert entry["comment"] == "This total looks off"
    assert entry["page"] == "/runs/abc123"
    assert entry["run_id"] == "abc123"
    assert entry["section"] == "Needs your attention"
    assert entry["anchor"] == "USD 1,234.56"
    assert entry["pos"] == {"pageX": 100, "pageY": 2000, "pct": 41, "vw": 1440, "vh": 900}
    assert entry["ts"]


def test_non_run_page_has_no_run_id(client, data_root):
    client.post("/api/feedback", json={"comment": "nav note", "path": "/memory"})
    entry = json.loads(
        (data_root / "feedback.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert entry["run_id"] is None


def test_feedback_requires_login_when_gated(data_root, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    with TestClient(create_app(data_root)) as gated:
        resp = gated.post("/api/feedback", json={"comment": "hi"})
        assert resp.status_code == 401


def test_bad_payloads_rejected(client, data_root):
    assert client.post("/api/feedback", json={"comment": "   "}).status_code == 400
    assert (
        client.post(
            "/api/feedback", content=b"not json",
            headers={"Content-Type": "application/json"},
        ).status_code
        == 400
    )
    assert client.post("/api/feedback", json=["a", "list"]).status_code == 400
    assert not (data_root / "feedback.jsonl").exists()


def test_raw_download_carries_the_notes(client):
    client.post(
        "/api/feedback", json={"comment": "Rename this column", "path": "/runs/r1"}
    )
    raw = client.get("/feedback.jsonl")
    assert raw.status_code == 200
    assert raw.headers["content-type"].startswith("application/x-ndjson")
    assert "Rename this column" in raw.text


def test_empty_raw_download(client):
    raw = client.get("/feedback.jsonl")
    assert raw.status_code == 200
    assert raw.text == ""


def test_state_api_reports_feedback_count(client):
    assert client.get("/api/operator/state").json()["feedback"]["count"] == 0
    client.post("/api/feedback", json={"comment": "note one"})
    client.post("/api/feedback", json={"comment": "note two"})
    state = client.get("/api/operator/state").json()
    assert state["feedback"]["count"] == 2
