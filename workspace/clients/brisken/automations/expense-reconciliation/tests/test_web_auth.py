"""Password gate tests (hosted-only auth, operator-only role model).

The gate is active only when EXPENSE_RECON_OPERATOR_CODE is set, so local
loopback use stays open. When set, every request outside the open set
(/api/login, /healthz) needs the signed session token as an
``Authorization: Bearer`` header (a legacy cookie session is also
accepted). Operator is the only role (owner decision 2026-07-22): an
authenticated session has the full surface.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web import auth  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

OP_CODE = "operator-code-1"


def _client(tmp_path):
    return TestClient(create_app(tmp_path))


@pytest.fixture
def gated_client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    with _client(tmp_path) as c:
        yield c


def test_no_code_means_open(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_OPERATOR_CODE", raising=False)
    with _client(tmp_path) as c:
        assert c.get("/api/operator/state").status_code == 200


def test_gate_blocks_without_token(gated_client):
    # JSON 401 on every surface — reads, mutations, downloads. Never a
    # redirect: there is no HTML login page to redirect to.
    for method, path in (
        ("GET", "/api/operator/state"),
        ("GET", "/api/runs/some-run"),
        ("GET", "/runs/some-run/report.xlsx"),
        ("GET", "/feedback.jsonl"),
        ("POST", "/api/runs/some-run/publish"),
    ):
        resp = gated_client.request(method, path, follow_redirects=False)
        assert resp.status_code == 401, (method, path)
        assert resp.json()["error"] == "authentication required"


def test_api_login_returns_bearer_token(gated_client):
    ok = gated_client.post("/api/login", json={"code": OP_CODE})
    assert ok.status_code == 200
    assert ok.json()["role"] == auth.ROLE_OPERATOR
    assert ok.json()["token"]
    assert gated_client.post("/api/login", json={"code": "wrong"}).status_code == 401


def test_bearer_token_authenticates(gated_client):
    token = gated_client.post("/api/login", json={"code": OP_CODE}).json()["token"]
    hdr = {"Authorization": f"Bearer {token}"}
    ok = gated_client.get("/api/operator/state", headers=hdr)
    assert ok.status_code == 200
    assert {"intakes", "operator_runs", "published_runs", "feedback"} <= ok.json().keys()
    # Mutations accept the same bearer (404 proves the handler ran).
    resp = gated_client.post("/api/runs/missing/publish", headers=hdr)
    assert resp.status_code == 404
    assert resp.json() == {"error": "run not found"}


def test_legacy_cookie_session_still_accepted(gated_client, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_AUTH_SECRET", "s3cret")
    gated_client.cookies.set(auth.COOKIE_NAME, auth.issue_token(auth.ROLE_OPERATOR))
    assert gated_client.get("/api/operator/state").status_code == 200


def test_healthz_and_login_open_even_when_gated(gated_client):
    assert gated_client.get("/healthz").status_code == 200
    # /api/login itself must be reachable to obtain the token.
    assert gated_client.post("/api/login", json={"code": "wrong"}).status_code == 401


def test_gate_disabled_login_still_hands_out_a_token(tmp_path, monkeypatch):
    # The SPA calls /api/login unconditionally; with the gate off it gets
    # an operator token back rather than an error.
    monkeypatch.delenv("EXPENSE_RECON_OPERATOR_CODE", raising=False)
    with _client(tmp_path) as c:
        body = c.post("/api/login", json={}).json()
        assert body["role"] == auth.ROLE_OPERATOR
        assert body["token"]


# ── auth unit level ────────────────────────────────────────────────────


def test_code_role_operator_only(monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    assert auth.code_role(OP_CODE) == auth.ROLE_OPERATOR
    assert auth.code_role("wrong") is None
    # The retired user code grants nothing anymore.
    assert auth.code_role("user-code-1") is None


def test_token_round_trip_and_tamper(monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_AUTH_SECRET", "s3cret")
    op = auth.issue_token(auth.ROLE_OPERATOR)
    assert auth.token_role(op) == auth.ROLE_OPERATOR
    # a bare mac without the role prefix fails => one re-login
    _, _, mac = op.partition(":")
    assert auth.token_role(mac) is None
    # a token carrying the retired user role fails => one re-login
    assert auth.token_role(f"user:{mac}") is None
    assert auth.token_role(None) is None
    # unknown roles cannot be minted either
    with pytest.raises(ValueError):
        auth.issue_token("user")


def test_operator_code_alone_enables_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    with _client(tmp_path) as c:
        resp = c.get("/api/operator/state", follow_redirects=False)
        assert resp.status_code == 401


# ── CORS (the SPA's cross-origin seam) ─────────────────────────────────


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
