"""Testing-mode roles: two access codes, role-carrying session cookie,
operator-only route gating. See web/auth.py."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web import auth  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

USER_CODE = "user-code-1"
OP_CODE = "operator-code-1"


@pytest.fixture
def gated_client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", USER_CODE)
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    monkeypatch.setenv("EXPENSE_RECON_INSECURE_COOKIE", "1")
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _login(client, code):
    resp = client.post("/login", data={"code": code}, follow_redirects=False)
    assert resp.status_code == 303
    return resp


def test_code_role_resolution(monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", USER_CODE)
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    assert auth.code_role(USER_CODE) == auth.ROLE_USER
    assert auth.code_role(OP_CODE) == auth.ROLE_OPERATOR
    assert auth.code_role("wrong") is None


def test_token_round_trip_and_tamper(monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_AUTH_SECRET", "s3cret")
    tok = auth.issue_token(auth.ROLE_USER)
    assert auth.token_role(tok) == auth.ROLE_USER
    op = auth.issue_token(auth.ROLE_OPERATOR)
    assert auth.token_role(op) == auth.ROLE_OPERATOR
    # role swap without re-signing fails
    _, _, mac = tok.partition(":")
    assert auth.token_role(f"operator:{mac}") is None
    # legacy (pre-role) token shape fails => one re-login
    assert auth.token_role(mac) is None
    assert auth.token_role(None) is None


def test_user_login_sees_user_home(gated_client):
    _login(gated_client, USER_CODE)
    resp = gated_client.get("/")
    assert resp.status_code == 200
    assert "Send your documents" in resp.text
    assert "Reconcile a month" not in resp.text  # no operator run form


def test_operator_login_sees_operator_home(gated_client):
    _login(gated_client, OP_CODE)
    resp = gated_client.get("/")
    assert resp.status_code == 200
    assert "Reconcile a month" in resp.text


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/compare"),
        ("GET", "/memory"),
        ("GET", "/jobs/deadbeef"),
        ("GET", "/intakes/xyz/prepare"),
    ],
)
def test_user_gets_redirected_from_operator_get_routes(gated_client, method, path):
    _login(gated_client, USER_CODE)
    resp = gated_client.request(method, path, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


def test_user_gets_403_json_from_operator_api_routes(gated_client):
    # API paths never redirect to the HTML home; a wrong-role caller gets a
    # JSON 403 the SPA front end can act on (operator-only surface).
    _login(gated_client, USER_CODE)
    resp = gated_client.get("/api/operator/state", follow_redirects=False)
    assert resp.status_code == 403
    assert resp.json()["error"]


# --- SPA front end: token login + bearer auth + scoped CORS ---------------


def test_api_login_returns_bearer_token(gated_client):
    ok = gated_client.post("/api/login", json={"code": OP_CODE})
    assert ok.status_code == 200
    assert ok.json()["role"] == auth.ROLE_OPERATOR
    assert ok.json()["token"]
    assert gated_client.post("/api/login", json={"code": "wrong"}).status_code == 401


def test_bearer_token_authenticates_operator_api(gated_client):
    token = gated_client.post("/api/login", json={"code": OP_CODE}).json()["token"]
    # no credentials -> JSON 401, never an HTML redirect
    assert gated_client.get(
        "/api/operator/state", follow_redirects=False
    ).status_code == 401
    ok = gated_client.get(
        "/api/operator/state", headers={"Authorization": f"Bearer {token}"}
    )
    assert ok.status_code == 200
    assert {"intakes", "published_runs", "feedback"} <= ok.json().keys()


def test_cors_reflects_lovable_origin_only(gated_client):
    lovable = gated_client.options(
        "/api/login",
        headers={"Origin": "https://demo.lovable.app",
                 "Access-Control-Request-Method": "POST"},
    )
    assert lovable.headers.get("access-control-allow-origin") == "https://demo.lovable.app"
    evil = gated_client.options(
        "/api/login",
        headers={"Origin": "https://evil.example.com",
                 "Access-Control-Request-Method": "POST"},
    )
    assert evil.headers.get("access-control-allow-origin") is None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/runs"),
        ("POST", "/memory/reset"),
        ("POST", "/intakes/xyz/run"),
        ("POST", "/runs/abc/publish"),
        ("POST", "/runs/abc/commit-memory"),
        ("POST", "/runs/abc/forget"),
    ],
)
def test_user_403_on_operator_post_routes(gated_client, method, path):
    _login(gated_client, USER_CODE)
    resp = gated_client.request(method, path)
    assert resp.status_code == 403
    assert resp.json()["error"] == "operator access required"


def test_operator_passes_operator_routes(gated_client):
    _login(gated_client, OP_CODE)
    assert gated_client.get("/compare").status_code == 200
    assert gated_client.get("/memory").status_code == 200
    assert gated_client.get("/api/operator/state").status_code == 200


def test_gate_disabled_defaults_to_operator(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_ACCESS_CODE", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_OPERATOR_CODE", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.get("/")
        assert resp.status_code == 200
        assert "Reconcile a month" in resp.text  # full operator surface


def test_operator_code_alone_enables_gate(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_ACCESS_CODE", raising=False)
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"
