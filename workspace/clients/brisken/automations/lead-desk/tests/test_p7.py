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


# --- #2 magic-link request throttle ------------------------------------------

def test_magic_throttle():
    ip = "203.0.113.9"
    auth._MAGIC_REQS.pop(ip, None)
    for _ in range(auth.MAGIC_MAX_REQS):
        assert not auth.magic_blocked(ip, now=100.0)
        auth.record_magic_request(ip, now=100.0)
    assert auth.magic_blocked(ip, now=100.0)
    # the window slides: far in the future the requests have aged out
    assert not auth.magic_blocked(ip, now=100.0 + auth.MAGIC_WINDOW + 1)


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
    # The gate is on iff LEAD_DESK_AUTH_SECRET is set (no access codes anymore).
    monkeypatch.setenv("LEAD_DESK_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("LEAD_DESK_INSECURE_COOKIE", "1")
    return TestClient(create_app(tmp_path))


def test_security_headers_present(gated):
    r = gated.get("/login")
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in r.headers


def test_csrf_blocks_cookie_post_without_token(gated):
    # Magic-link is the only login now; seat a valid session cookie directly.
    email = "matthias.silva@brisken.com"
    gated.cookies.set(auth.COOKIE_NAME, auth.issue_token(email))
    # a cookie-authed mutating POST with NO csrf field is rejected
    r = gated.post("/worker/kill", data={"on": "1"}, follow_redirects=False)
    assert r.status_code == 403
    # the same POST WITH the session csrf token is accepted (303 redirect)
    r2 = gated.post("/worker/kill", data={"on": "1", "csrf": auth.csrf_token(email)},
                    follow_redirects=False)
    assert r2.status_code == 303
