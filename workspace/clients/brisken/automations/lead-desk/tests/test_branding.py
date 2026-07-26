"""Brisken branding: packaged static assets served ungated (basename-only),
brand tokens + logos wired into base and login, favicon real."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lead_desk.web import auth
from lead_desk.web.app import create_app


@pytest.fixture
def gated(tmp_path, monkeypatch):
    # Gate is on iff LEAD_DESK_AUTH_SECRET is set (no access codes anymore).
    monkeypatch.setenv("LEAD_DESK_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("LEAD_DESK_INSECURE_COOKIE", "1")
    return TestClient(create_app(tmp_path))


def login(client):
    # Magic-link is the only login; seat a valid session cookie directly.
    client.cookies.set(auth.COOKIE_NAME, auth.issue_token("matthias.silva@brisken.com"))
    return client


def test_static_assets_serve_ungated(gated):
    """The login page needs tokens + logo BEFORE auth, so /static is open."""
    for name, ctype in (("tokens.css", "text/css"),
                        ("brisken-logo-light.png", "image/png"),
                        ("brisken-logo-dark.png", "image/png"),
                        ("favicon.png", "image/png")):
        r = gated.get(f"/static/{name}", follow_redirects=False)
        assert r.status_code == 200, name
        assert r.headers["content-type"].startswith(ctype), name
    assert "--brand-cyan" in gated.get("/static/tokens.css").text


def test_static_is_basename_only(gated):
    """Traversal and unknown names 404; nothing but the packaged dir serves."""
    assert gated.get("/static/..%2Fapp.py", follow_redirects=False).status_code == 404
    assert gated.get("/static/nope.css", follow_redirects=False).status_code == 404
    assert gated.get("/static/app.py", follow_redirects=False).status_code == 404


def test_gate_still_intact(gated):
    """Opening /static must not have loosened the cookie gate."""
    assert gated.get("/", follow_redirects=False).status_code == 303


def test_login_is_branded(gated):
    html = gated.get("/login").text
    assert "brisken-logo-light.png" in html and "brisken-logo-dark.png" in html
    assert "/static/tokens.css" in html
    assert "Lead Desk" in html


def test_nav_carries_logo_and_product_tag(gated):
    html = login(gated).get("/").text
    assert "brisken-logo-light.png" in html
    assert "LEAD DESK" in html                       # nav product tag
    assert "/static/tokens.css" in html
    assert "/static/favicon.png" in html


def test_favicon_ico_serves_png(gated):
    r = gated.get("/favicon.ico")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert r.content[:4] == b"\x89PNG"
