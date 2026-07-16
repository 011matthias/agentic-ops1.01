"""P7: session token expiry, login throttle, CSRF, security headers, /sync open."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lead_desk.web import auth
from lead_desk.web.app import create_app


# --- #1 token iat + server-side expiry ---------------------------------------

def test_token_roundtrips_and_expires():
    t = auth.issue_token("matthias", now=1000.0)
    assert auth.read_user(t, now=1000.0) == "matthias"
    assert auth.read_user(t, now=1000.0 + 11 * 3600) == "matthias"       # within 12h
    assert auth.read_user(t, now=1000.0 + 13 * 3600) is None             # past 12h


def test_old_format_token_rejected():
    # the pre-P7 "user.mac" shape must not validate -> forces a re-login
    import hashlib
    import hmac
    mac = hmac.new(auth._secret(), b"matthias", hashlib.sha256).hexdigest()
    assert auth.read_user(f"matthias.{mac}") is None


# --- #2 login throttle --------------------------------------------------------

def test_login_throttle():
    ip = "203.0.113.9"
    auth._LOGIN_FAILS.pop(ip, None)
    for _ in range(auth.LOGIN_MAX_FAILS):
        assert not auth.login_blocked(ip, now=100.0)
        auth.record_login_fail(ip, now=100.0)
    assert auth.login_blocked(ip, now=100.0)
    # the window slides: far in the future the fails have aged out
    assert not auth.login_blocked(ip, now=100.0 + auth.LOGIN_WINDOW + 1)


# --- #3 CSRF token ------------------------------------------------------------

def test_csrf_valid():
    tok = auth.issue_token("matthias")   # real iat, so csrf_for_cookie can read it
    csrf = auth.csrf_for_cookie(tok)
    assert csrf and auth.csrf_valid(tok, csrf)
    assert not auth.csrf_valid(tok, "wrong")
    assert not auth.csrf_valid(None, csrf)


# --- #5 /sync is reachable by the ingest bearer -------------------------------

def test_sync_is_open_path():
    assert auth.path_is_open("/sync")


# --- integration: gate ON, headers + CSRF enforced ----------------------------

@pytest.fixture
def gated(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_DESK_ACCESS_CODES", "matthias:testcode123")
    monkeypatch.setenv("LEAD_DESK_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("LEAD_DESK_INSECURE_COOKIE", "1")
    return TestClient(create_app(tmp_path))


def test_security_headers_present(gated):
    r = gated.get("/login")
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in r.headers


def test_csrf_blocks_cookie_post_without_token(gated):
    login = gated.post("/login", data={"code": "testcode123"}, follow_redirects=False)
    assert login.status_code == 303                      # cookie set on the client
    # a cookie-authed mutating POST with NO csrf field is rejected
    r = gated.post("/worker/kill", data={"on": "1"}, follow_redirects=False)
    assert r.status_code == 403
    # the same POST WITH the session csrf token is accepted (303 redirect)
    user = auth.read_user(gated.cookies.get(auth.COOKIE_NAME))
    r2 = gated.post("/worker/kill", data={"on": "1", "csrf": auth.csrf_token(user)},
                    follow_redirects=False)
    assert r2.status_code == 303
