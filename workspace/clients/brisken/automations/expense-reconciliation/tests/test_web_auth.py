"""Password gate tests (hosted-only auth).

The gate is active only when EXPENSE_RECON_ACCESS_CODE is set, so local
loopback use stays open. When set, every page needs a session cookie
obtained by posting the right code to /login. INSECURE_COOKIE lets the
http TestClient keep the cookie (production keeps the Secure flag).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402


def _client(tmp_path):
    return TestClient(create_app(tmp_path))


def test_no_code_means_open(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_ACCESS_CODE", raising=False)
    with _client(tmp_path) as c:
        assert c.get("/").status_code == 200


def test_gate_blocks_without_session(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", "s3cret")
    monkeypatch.setenv("EXPENSE_RECON_INSECURE_COOKIE", "1")
    with _client(tmp_path) as c:
        # GET redirects to the login page; the page itself is reachable.
        r = c.get("/", follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/login"
        assert c.get("/login").status_code == 200
        # A state-changing call without a session is rejected outright.
        assert c.post("/runs", files={}, follow_redirects=False).status_code == 401


def test_wrong_code_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", "s3cret")
    monkeypatch.setenv("EXPENSE_RECON_INSECURE_COOKIE", "1")
    with _client(tmp_path) as c:
        r = c.post("/login", data={"code": "nope"}, follow_redirects=False)
        assert r.status_code == 401
        assert auth_cookie(c) is None


def test_correct_code_unlocks(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", "s3cret")
    monkeypatch.setenv("EXPENSE_RECON_INSECURE_COOKIE", "1")
    with _client(tmp_path) as c:
        r = c.post("/login", data={"code": "s3cret"}, follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/"
        # Cookie now carries the session; the gated page loads.
        assert c.get("/").status_code == 200
        # Logout drops the session and re-gates.
        c.post("/logout")
        assert c.get("/", follow_redirects=False).status_code == 303


def test_healthz_open_even_when_gated(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", "s3cret")
    with _client(tmp_path) as c:
        assert c.get("/healthz").status_code == 200


def auth_cookie(client):
    from expense_recon.web.auth import COOKIE_NAME

    return client.cookies.get(COOKIE_NAME)
