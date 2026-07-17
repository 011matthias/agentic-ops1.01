"""edge_cdp target-selection unit tests.

The websocket/CDP round-trips need a live Edge on :9222 and can't run in CI,
but `select_target` -- the part agents get wrong by reaching for Playwright
instead -- is pure and covered here. (Importing edge_cdp does NOT import
websockets; that dependency is lazy-loaded only inside _connect.)
"""
import sys

from hooklib import TOOLS

sys.path.insert(0, str(TOOLS))
import edge_cdp  # noqa: E402


def test_select_page_by_url_substring():
    targets = [
        {"type": "page", "url": "https://planner.cloud.microsoft/x", "title": "Planner"},
        {"type": "page", "url": "https://mail.example.com", "title": "Mail"},
    ]
    t = edge_cdp.select_target(targets, "planner.cloud.microsoft")
    assert t and t["title"] == "Planner"


def test_select_skips_non_page_type():
    targets = [
        {"type": "service_worker", "url": "https://planner.cloud.microsoft/sw"},
        {"type": "page", "url": "https://planner.cloud.microsoft/app"},
    ]
    assert edge_cdp.select_target(targets, "planner")["type"] == "page"


def test_select_none_when_no_match():
    assert edge_cdp.select_target([{"type": "page", "url": "https://a"}], "zzz") is None


def test_select_first_when_match_none():
    ts = [{"type": "page", "url": "https://a"}, {"type": "page", "url": "https://b"}]
    assert edge_cdp.select_target(ts, None)["url"] == "https://a"


def test_select_matches_title_too():
    ts = [{"type": "page", "url": "https://x", "title": "Brisken Planner"}]
    assert edge_cdp.select_target(ts, "Planner") is not None
