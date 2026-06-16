"""Embedded docs in the tool UI (2026-06-16).

The user guide and the how-it-works walkthrough are served inside the tool
at /guide and /how-it-works, reachable from the nav on every page. These
cover the routes (each serves its self-contained HTML verbatim) and the nav
links that surface them.
"""
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


def test_user_guide_served_verbatim(client):
    resp = client.get("/guide")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    # Served as a full standalone document, not wrapped in the app chrome.
    assert "<!DOCTYPE html>" in resp.text
    assert "Brisken Expense Reconciliation, User Guide" in resp.text


def test_how_it_works_served_verbatim(client):
    resp = client.get("/how-it-works")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "How the tool works" in resp.text


def test_nav_links_to_both_docs(client):
    """The docs are reachable from the tool nav (rendered on every page that
    extends base.html, e.g. the runs index)."""
    body = client.get("/").text
    assert 'href="/guide"' in body
    assert 'href="/how-it-works"' in body
