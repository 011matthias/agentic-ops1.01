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


def test_nav_links_to_all_docs(client):
    """The docs are reachable from the tool nav (rendered on every page that
    extends base.html, e.g. the runs index)."""
    body = client.get("/").text
    assert 'href="/guide"' in body
    assert 'href="/how-it-works"' in body


# The full app tab bar (Runs / Compare / Memory / Guide / How it works) is
# present on the doc pages too, so every tab navigates within the same window
# instead of dropping the reader onto a chromeless standalone page.
_APP_TABS = ('href="/"', 'href="/compare"', 'href="/memory"',
             'href="/guide"', 'href="/how-it-works"')


@pytest.mark.parametrize("path,active_href", [
    ("/guide", '/guide'),
    ("/how-it-works", '/how-it-works'),
])
def test_doc_pages_carry_app_nav(client, path, active_href):
    body = client.get(path).text
    for tab in _APP_TABS:
        assert tab in body, f"{path} is missing tab {tab}"
    # the current doc's tab is marked active
    assert f'class="nav-tab active" href="{active_href}"' in body
