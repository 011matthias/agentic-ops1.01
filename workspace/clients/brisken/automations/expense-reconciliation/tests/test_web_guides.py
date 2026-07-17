"""Help page (2026-07-15): one merged trilingual page at /help replaces the
old standalone /guide + /how-it-works docs (which drifted). Those paths now
301 to /help; the nav links to /help."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def test_help_page_renders_in_app_chrome(client):
    resp = client.get("/help")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    # rendered inside base.html (brand nav present), not a standalone doc
    assert "EXPENSE RECONCILIATION" in resp.text
    # trilingual content
    assert "lang-block" in resp.text


def test_old_guide_paths_redirect_permanently(client):
    for path in ("/guide", "/how-it-works"):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 301, path
        assert resp.headers["location"] == "/help"


def test_nav_links_to_help(client):
    body = client.get("/").text  # gate disabled => operator home
    assert 'href="/help"' in body
    # the retired standalone doc links are gone
    assert 'href="/guide"' not in body
    assert 'href="/how-it-works"' not in body
