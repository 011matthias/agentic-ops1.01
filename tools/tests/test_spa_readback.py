"""Tests for tools/spa-readback.py.

The pure half (text checks, write guard, verdict, blind detection) runs
everywhere. The live half drives a real headless Chrome against a local server
whose page renders its text from JS after a delay, POSTs to /api/save and GETs
/api/data twice; it skips where Playwright or Chrome is missing (the CI hooks
job installs neither). The live tests are the caller-level ones: they go
through main(), the route guard and the replay cache, not the helpers.
"""
from __future__ import annotations

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "spa-readback.py"
spec = importlib.util.spec_from_file_location("spa_readback", TOOL)
sr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sr)


# ---------------------------------------------------------------- pure logic

def test_write_methods_are_everything_but_safe_verbs():
    assert not sr.is_write_method("GET")
    assert not sr.is_write_method("options")
    for m in ("POST", "PUT", "PATCH", "DELETE"):
        assert sr.is_write_method(m)


def test_check_text_is_case_insensitive_by_default():
    res, reasons = sr.check_text("Status: POOLED in May", ["pooled"], ["Arriving"])
    assert res["expect"]["pooled"] is True
    assert res["absent"]["Arriving"] is False
    assert reasons == []


def test_check_text_flags_missing_and_fallback():
    _, reasons = sr.check_text("Status: Arriving", ["Pooled"], ["arriving"])
    assert any("missing-content" in r for r in reasons)
    assert any("fallback-rendered" in r for r in reasons)


def test_blank_page_is_blind_not_missing():
    report = {"rendered_chars": 3, "api": {"requests": 0}, "text_reasons": []}
    v, reasons = sr.verdict(report, require_api=True)
    assert v == "FAIL"
    assert sum("drive-blind" in r for r in reasons) == 2


def test_a_guard_that_saw_nothing_fails_the_drive_even_without_require_api():
    report = {"rendered_chars": 900, "text_reasons": [],
              "api": {"routed_total": 0, "requests": 0}}
    v, reasons = sr.verdict(report, require_api=False)
    assert v == "FAIL"
    assert any("intercepted no request" in r for r in reasons)


def test_git_bash_rewritten_path_arguments_are_refused():
    assert sr.msys_mangled(["C:/Program Files/Git/api/", "/api/", "https://x/api/"]) == [
        "C:/Program Files/Git/api/"]
    rc = sr.main(["https://example.invalid/", "--api-pattern", "C:/Program Files/Git/api/"])
    assert rc == 2


def test_landing_check_names_the_wrong_destination():
    report = {"rendered_chars": 500, "api": {"requests": 2}, "text_reasons": [],
              "expect_url": "/review/42", "final_url": "https://x/board"}
    v, reasons = sr.verdict(report, require_api=True)
    assert v == "FAIL" and any(r.startswith("[landing]") for r in reasons)


def test_load_secret_reads_env_file_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("SPA_TEST_CODE", raising=False)
    f = tmp_path / ".env"
    f.write_text("OTHER=1\nSPA_TEST_CODE='abc123'\n", encoding="utf-8")
    assert sr.load_secret("SPA_TEST_CODE", str(f)) == "abc123"
    assert sr.load_secret("MISSING_KEY", str(f)) is None


# ---------------------------------------------------------------- live drive

PAGE = """<!doctype html><html><body><div id="root"></div><script>
fetch('/api/data').then(r => r.json()).then(d => {
  fetch('/api/data');
  fetch('/api/save', {method: 'POST', body: 'x'}).catch(() => {});
  setTimeout(() => {
    document.getElementById('root').innerText =
      'Monthly overview. Status of the batch: ' + d.status + '. Month: May 2026.';
  }, 400);
});
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    seen: list = []

    def log_message(self, *a):
        pass

    def _send(self, body: bytes, ctype: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        _Handler.seen.append(("GET", self.path))
        if self.path.startswith("/api/data"):
            return self._send(json.dumps({"status": "pooled"}).encode(), "application/json")
        return self._send(PAGE.encode(), "text/html")

    def do_POST(self):
        _Handler.seen.append(("POST", self.path))
        return self._send(b"{}", "application/json")


@pytest.fixture
def server():
    pytest.importorskip("playwright.sync_api")
    if not any(Path(p).is_file() for p in sr.CHROME_PATHS):
        pytest.skip("installed Chrome not found")
    _Handler.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()


def _run(url, *extra, tmp_path):
    return sr.main([url, "--settle-ms", "800", "--timeout", "20", "--replay-api",
                    "--require-api", "--screenshot", str(tmp_path / "shot.png"), *extra])


def test_live_pass_renders_js_text_and_blocks_the_write(server, tmp_path):
    rc = _run(server, "--expect", "pooled", "--absent", "Arriving",
              "--wait-text", "Month: May", tmp_path=tmp_path)
    assert rc == 0
    posts = [p for m, p in _Handler.seen if m == "POST"]
    assert posts == [], f"write guard let a POST through: {posts}"
    data_gets = [p for m, p in _Handler.seen if m == "GET" and p.startswith("/api/data")]
    assert len(data_gets) == 1, f"replay should serve the 2nd GET from cache: {data_gets}"


def test_live_fail_when_claimed_value_is_not_rendered(server, tmp_path):
    rc = _run(server, "--expect", "Arriving", tmp_path=tmp_path)
    assert rc == 1


def test_live_fail_when_fallback_renders(server, tmp_path):
    rc = _run(server, "--expect", "Monthly overview", "--absent", "pooled", tmp_path=tmp_path)
    assert rc == 1


def test_live_allow_write_lets_the_named_post_through(server, tmp_path):
    rc = _run(server, "--expect", "pooled", "--allow-write", "/api/save", tmp_path=tmp_path)
    assert rc == 0
    assert ("POST", "/api/save") in _Handler.seen
