"""assert-live-origin.py: deployed-origin parity assertions (stack-agnostic).

Drives the pure check() against a stubbed fetch so no network is touched. This is
the H6 generalization of local-web-deploy.py's live-origin gate: the structural
kill for the 2026-06-17 "verified on localhost while the Fly origin still served
the old build" regression.
"""
import importlib.util
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "assert-live-origin.py"


def _load():
    spec = importlib.util.spec_from_file_location("assert_live_origin", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ALO = _load()


def _stub_fetch(status, body):
    return lambda url, timeout=25: (status, body)


def test_expect_present_passes(monkeypatch):
    monkeypatch.setattr(ALO, "fetch", _stub_fetch(200, "<h1>Reviewed by Dirk</h1>"))
    ok, _ = ALO.check("https://x.fly.dev", 200, ["Reviewed by"], [], None, "", 5)
    assert ok


def test_expect_missing_fails(monkeypatch):
    monkeypatch.setattr(ALO, "fetch", _stub_fetch(200, "<h1>old</h1>"))
    ok, lines = ALO.check("https://x.fly.dev", 200, ["Reviewed by"], [], None, "", 5)
    assert not ok and any("expected substring absent" in l for l in lines)


def test_expect_absent_still_served_fails(monkeypatch):
    # the regression shape: the OLD content is still on the live origin.
    monkeypatch.setattr(ALO, "fetch", _stub_fetch(200, "<h1>OLD BANNER</h1>"))
    ok, lines = ALO.check("https://x.fly.dev", 200, [], ["OLD BANNER"], None, "", 5)
    assert not ok and any("stale content still served" in l for l in lines)


def test_status_mismatch_fails(monkeypatch):
    monkeypatch.setattr(ALO, "fetch", _stub_fetch(404, "not found"))
    ok, _ = ALO.check("https://x.fly.dev", 200, ["x"], [], None, "", 5)
    assert not ok


def test_asset_parity_matches_and_mismatches(tmp_path, monkeypatch):
    local = tmp_path / "index.html"
    local.write_text('<script src="/_astro/app.abc123.js"></script>', encoding="utf-8")
    pat = ALO.DEFAULT_ASSET_PATTERN
    # live serves the SAME hashed asset -> parity ok
    monkeypatch.setattr(ALO, "fetch", _stub_fetch(200, "x /_astro/app.abc123.js x"))
    ok, _ = ALO.check("https://x.fly.dev", 200, [], [], str(local), pat, 5)
    assert ok
    # live serves a DIFFERENT hash (stale build) -> parity fail
    monkeypatch.setattr(ALO, "fetch", _stub_fetch(200, "x /_astro/app.OLD999.js x"))
    ok, lines = ALO.check("https://x.fly.dev", 200, [], [], str(local), pat, 5)
    assert not ok and any("missing" in l for l in lines)


def test_fetch_error_is_failure(monkeypatch):
    def boom(url, timeout=25):
        raise urllib.error.URLError("dns")
    monkeypatch.setattr(ALO, "fetch", boom)
    ok, lines = ALO.check("https://x.fly.dev", 200, ["x"], [], None, "", 5)
    assert not ok and any("fetch error" in l for l in lines)
