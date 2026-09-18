"""tools/recon_uptime_probe.py (backlog item 123): the outside-in monitor.

The probe runs against local stand-ins (an http.server for /healthz and the
SPA shell, a TCP thread for the port-25 banner) through the real CLI, so exit
codes and the retry are what the workflow will see. The notifier runs against
the two seams (a recorded fake `gh`, a local endpoint in place of Resend) so
the alert policy is asserted call by call and nothing real is ever opened
or sent.
"""
from __future__ import annotations

import http.server
import json
import os
import shlex
import socket
import subprocess
import sys
import threading

import pytest

from hooklib import TOOLS

sys.path.insert(0, str(TOOLS))
import recon_uptime_probe as rup  # noqa: E402

PROBE = TOOLS / "recon_uptime_probe.py"

HEALTHY = {
    "status": "ok",
    "server": {"uptime_s": 4242},
    "disk": {"available": True, "free_pct": 63.4, "free_bytes": 650_000_000,
             "total_bytes": 1_000_000_000, "floor_bytes": 50_000_000,
             "intake_refusing": False},
}


# --------------------------------------------------------------- stand-ins --

class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_):  # keep pytest output clean
        pass

    def _send(self, status: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        srv = self.server
        if self.path == "/healthz":
            self._send(srv.healthz_status, json.dumps(srv.healthz).encode())
        elif self.path == "/":
            self._send(srv.spa_status, b"<!doctype html><title>shell</title>", "text/html")
        else:
            self._send(404, b"{}")

    def do_POST(self):
        srv = self.server
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        srv.posts.append({
            "path": self.path,
            "user_agent": self.headers.get("User-Agent"),
            "authorization": self.headers.get("Authorization"),
            "body": json.loads(raw or b"{}"),
        })
        if self.path == "/emails":
            self._send(200, b'{"id": "fake-mail-id"}')
        else:
            self._send(500, b'{"message": "refused"}')


class _Web(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), _Handler)
        self.healthz = json.loads(json.dumps(HEALTHY))
        self.healthz_status = 200
        self.spa_status = 200
        self.posts: list[dict] = []

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"


@pytest.fixture
def web():
    srv = _Web()
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()


class _Mx:
    """Port-25 stand-in. Counts every accepted connection; answers with
    `banner` when set, otherwise closes without a word."""

    def __init__(self, banner: bytes | None = b"220 test brisken-expense-intake\r\n"):
        self.banner = banner
        self.connections = 0
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.sock.settimeout(0.2)
        self.port = self.sock.getsockname()[1]
        self._stop = False
        self._t = threading.Thread(target=self._serve, daemon=True)
        self._t.start()

    def _serve(self):
        while not self._stop:
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.connections += 1
            with conn:
                if self.banner:
                    conn.sendall(self.banner)
                    conn.settimeout(1.0)
                    try:
                        conn.recv(64)  # QUIT
                        conn.sendall(b"221 bye\r\n")
                    except OSError:
                        pass

    def close(self):
        self._stop = True
        self.sock.close()
        self._t.join(timeout=2)


@pytest.fixture
def mx():
    srv = _Mx()
    try:
        yield srv
    finally:
        srv.close()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_probe(web: _Web, mx_port: int, *extra: str, api: str | None = None) -> tuple[int, dict, str]:
    p = subprocess.run(
        [sys.executable, str(PROBE), "probe", "--json",
         "--api", api or web.url, "--mx", f"127.0.0.1:{mx_port}", "--spa", web.url,
         "--timeout", "3", "--retry-delay", "0.05", *extra],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        env=_base_env(),
    )
    data = json.loads(p.stdout) if p.stdout.strip() else {}
    return p.returncode, data, p.stderr


def _base_env() -> dict:
    """The caller's environment minus anything the tool reads, so a
    developer's real keys or seams never leak into a test run."""
    return {k: v for k, v in os.environ.items()
            if not k.startswith(("RECON_UPTIME_", "RESEND_", "BRIEFING_", "GITHUB_", "FAKE_GH_"))}


# ------------------------------------------------------------------ probe --

def _states(data: dict) -> dict:
    return {c["name"]: c["state"] for c in data["checks"]}


def _check(data: dict, name: str) -> dict:
    return next(c for c in data["checks"] if c["name"] == name)


def test_defaults_are_the_production_contract():
    assert rup.RETRY_DELAY_S == 5
    assert rup.TIMEOUT_S == 10
    assert rup.WARN_FREE_PCT == 15
    assert rup.MX_PORT == 25
    a = rup.build_parser().parse_args(["probe"])
    assert (a.retry_delay, a.timeout) == (5, 10)
    assert a.api == "https://brisken-expense-recon.fly.dev"
    assert a.mx == "mx.expenses.brisken.com"
    assert a.spa == "https://expenses.brisken.com"


def test_probe_all_ok(web, mx):
    rc, data, err = run_probe(web, mx.port)
    assert rc == 0, err
    assert _states(data) == {"api": "OK", "mx": "OK", "spa": "OK"}
    assert data["down"] is False and data["warn"] is False
    assert data["summary"] == "all OK"
    assert "summary: all OK" in err
    assert _check(data, "api")["free_pct"] == 63.4
    assert "free_pct=63.4" in _check(data, "api")["detail"]
    assert _check(data, "mx")["detail"].startswith("220 test")
    assert mx.connections == 1


def test_probe_intake_refusing_is_down_naming_the_disk(web, mx):
    web.healthz["disk"]["intake_refusing"] = True
    web.healthz["disk"]["free_pct"] = 2.1
    rc, data, err = run_probe(web, mx.port)
    assert rc == 1
    assert _states(data) == {"api": "DOWN", "mx": "OK", "spa": "OK"}
    api = _check(data, "api")
    assert "intake_refusing" in api["detail"] and "2.1" in api["detail"]
    assert api["attempts"] == 2
    assert data["summary"] == "DOWN: api"


def test_probe_mx_nothing_listening_is_down_after_one_retry(web):
    rc, data, _ = run_probe(web, _free_port())
    assert rc == 1
    assert _states(data) == {"api": "OK", "mx": "DOWN", "spa": "OK"}
    mxc = _check(data, "mx")
    assert mxc["attempts"] == 2
    assert mxc["detail"].startswith("after retry: connect failed")


def test_probe_mx_retry_is_a_second_connection(web):
    silent = _Mx(banner=None)
    try:
        rc, data, _ = run_probe(web, silent.port)
    finally:
        silent.close()
    assert rc == 1
    assert _check(data, "mx")["state"] == "DOWN"
    assert "closed before a banner" in _check(data, "mx")["detail"]
    assert silent.connections == 2


def test_probe_free_pct_below_floor_is_warn_not_down(web, mx):
    web.healthz["disk"]["free_pct"] = 10.0
    rc, data, err = run_probe(web, mx.port)
    assert rc == 0
    assert _states(data) == {"api": "WARN", "mx": "OK", "spa": "OK"}
    assert data["warn"] is True and data["down"] is False
    assert "does not page" in _check(data, "api")["detail"]
    assert "WARN on api" in data["summary"]
    assert _check(data, "api")["attempts"] == 1


def test_probe_unreachable_api_is_down_with_mx_and_spa_ok(web, mx):
    rc, data, _ = run_probe(web, mx.port, api="https://127.0.0.1:9")
    assert rc == 1
    assert _states(data) == {"api": "DOWN", "mx": "OK", "spa": "OK"}


def test_probe_healthz_without_disk_block_is_down(web, mx):
    del web.healthz["disk"]
    rc, data, _ = run_probe(web, mx.port)
    assert rc == 1
    assert "no disk block" in _check(data, "api")["detail"]


def test_probe_sends_a_browser_user_agent(web, mx):
    seen: list[str] = []
    orig = _Handler.do_GET

    def spy(self):
        seen.append(self.headers.get("User-Agent") or "")
        orig(self)

    _Handler.do_GET = spy
    try:
        run_probe(web, mx.port)
    finally:
        _Handler.do_GET = orig
    assert seen and all(ua.startswith("Mozilla/5.0") for ua in seen)
    assert not any("Python-urllib" in ua for ua in seen)


# ----------------------------------------------------------------- notify --

FAKE_GH = r'''
import json, os, sys
args = sys.argv[1:]
body = sys.stdin.read() if "-" in args else ""
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"args": args, "stdin": body}) + "\n")
sub = " ".join(args[:2])
if sub == "issue list":
    print(os.environ.get("FAKE_GH_OPEN_ISSUES", "[]"))
elif sub == "label list":
    names = json.loads(os.environ.get("FAKE_GH_LABELS", "[]"))
    print(json.dumps([{"name": n} for n in names]))
elif sub == "issue create":
    print("https://github.com/o/r/issues/99")
'''


@pytest.fixture
def seams(tmp_path, web):
    """A recorded fake gh + the local endpoint standing in for Resend."""
    fake = tmp_path / "fake_gh.py"
    fake.write_text(FAKE_GH, encoding="utf-8")
    log = tmp_path / "gh-calls.jsonl"
    cmd = " ".join(shlex.quote(p.replace("\\", "/")) for p in (sys.executable, str(fake)))
    env = {
        **_base_env(),
        "RECON_UPTIME_GH_CMD": cmd,
        "FAKE_GH_LOG": str(log),
        "RECON_UPTIME_RESEND_URL": web.url + "/emails",
        "RESEND_API_KEY": "re_test_not_a_real_key",
        "BRIEFING_TO": "dev@example.test",
    }

    class Seams:
        def __init__(self):
            self.env = env
            self.web = web

        def calls(self) -> list[list[str]]:
            if not log.exists():
                return []
            return [json.loads(line)["args"]
                    for line in log.read_text(encoding="utf-8").splitlines() if line]

        def subcommands(self) -> list[str]:
            return [" ".join(c[:2]) for c in self.calls()]

        def stdin_of(self, sub: str) -> str:
            for line in log.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                if " ".join(rec["args"][:2]) == sub:
                    return rec["stdin"]
            raise AssertionError(f"no {sub} call recorded")

        def mails(self) -> list[dict]:
            return [p for p in web.posts if p["path"] == "/emails"]

    return Seams()


def _result_file(tmp_path, down: bool) -> str:
    checks = [
        {"name": "api", "target": "https://x/healthz", "attempts": 2 if down else 1,
         "state": "DOWN" if down else "OK",
         "detail": "after retry: HTTP 502" if down else "200 status=ok free_pct=63.4 uptime_s=1"},
        {"name": "mx", "target": "mx:25", "attempts": 1, "state": "OK",
         "detail": "220 host brisken-expense-intake"},
        {"name": "spa", "target": "https://x/", "attempts": 1, "state": "OK",
         "detail": "200 (512 bytes)"},
    ]
    result = {"checked_at": "2026-09-18T10:00:00+00:00", "checks": checks,
              "down": down, "warn": False, "summary": "DOWN: api" if down else "all OK"}
    p = tmp_path / ("down.json" if down else "ok.json")
    p.write_text(json.dumps(result), encoding="utf-8")
    return str(p)


def run_notify(env: dict, result: str, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PROBE), "notify", "--result", result, "--repo", "o/r", *extra],
        capture_output=True, text=True, encoding="utf-8", timeout=60, env=env)


def test_notify_down_without_issue_opens_one_issue_and_one_mail(tmp_path, seams):
    p = run_notify(seams.env, _result_file(tmp_path, down=True))
    assert p.returncode == 0, p.stderr
    subs = seams.subcommands()
    assert subs == ["issue list", "label list", "label create", "issue create"]
    create = next(c for c in seams.calls() if c[:2] == ["issue", "create"])
    title = create[create.index("--title") + 1]
    assert title == "expenses.brisken.com is down (2026-09-18 10:00 UTC)"
    assert "--label" in create and create[create.index("--label") + 1] == "recon-uptime"
    body = seams.stdin_of("issue create")
    assert "| api | DOWN |" in body and "after retry: HTTP 502" in body
    assert [m["body"]["to"] for m in seams.mails()] == ["dev@example.test"]
    mail = seams.mails()[0]
    assert "is down" in mail["body"]["subject"]
    assert mail["body"]["from"] == "onboarding@resend.dev"
    assert mail["user_agent"] == "agentic-ops-recon-uptime/1.0"
    assert mail["authorization"] == "Bearer re_test_not_a_real_key"
    assert "re_test_not_a_real_key" not in p.stdout + p.stderr
    assert "issue opened: https://github.com/o/r/issues/99" in p.stdout


def test_notify_down_with_existing_label_does_not_recreate_it(tmp_path, seams):
    env = {**seams.env, "FAKE_GH_LABELS": json.dumps(["recon-uptime"])}
    p = run_notify(env, _result_file(tmp_path, down=True))
    assert p.returncode == 0, p.stderr
    assert seams.subcommands() == ["issue list", "label list", "issue create"]
    assert len(seams.mails()) == 1


def test_notify_down_with_open_issue_comments_only(tmp_path, seams):
    env = {**seams.env, "FAKE_GH_OPEN_ISSUES": json.dumps([{"number": 7, "title": "t", "url": "u"}])}
    p = run_notify(env, _result_file(tmp_path, down=True))
    assert p.returncode == 0, p.stderr
    assert seams.subcommands() == ["issue list", "issue comment"]
    comment = next(c for c in seams.calls() if c[:2] == ["issue", "comment"])
    assert comment[2] == "7"
    assert "| api | DOWN |" in seams.stdin_of("issue comment")
    assert seams.mails() == []
    assert "no mail" in p.stdout


def test_notify_ok_with_open_issue_recovers_closes_and_mails_once(tmp_path, seams):
    env = {**seams.env, "FAKE_GH_OPEN_ISSUES": json.dumps([{"number": 7, "title": "t", "url": "u"}])}
    p = run_notify(env, _result_file(tmp_path, down=False))
    assert p.returncode == 0, p.stderr
    assert seams.subcommands() == ["issue list", "issue comment", "issue close"]
    assert seams.stdin_of("issue comment").startswith("recovered at 2026-09-18 10:00 UTC")
    close = next(c for c in seams.calls() if c[:2] == ["issue", "close"])
    assert close[2] == "7"
    mails = seams.mails()
    assert len(mails) == 1 and "recovered" in mails[0]["body"]["subject"]


def test_notify_ok_without_issue_writes_nothing_and_mails_nothing(tmp_path, seams):
    p = run_notify(seams.env, _result_file(tmp_path, down=False))
    assert p.returncode == 0, p.stderr
    assert seams.subcommands() == ["issue list"]  # the one read needed to know
    assert seams.mails() == []
    assert "nothing to do" in p.stdout


def test_notify_dry_run_calls_neither_seam(tmp_path, seams):
    for down in (True, False):
        p = run_notify(seams.env, _result_file(tmp_path, down=down), "--dry-run")
        assert p.returncode == 0, p.stderr
        assert "DRY-RUN" in p.stdout
        assert "dev@example.test" in p.stdout
    assert seams.calls() == []
    assert seams.mails() == []


def test_notify_without_resend_key_skips_mail_and_still_opens_the_issue(tmp_path, seams):
    env = {k: v for k, v in seams.env.items() if k != "RESEND_API_KEY"}
    p = run_notify(env, _result_file(tmp_path, down=True))
    assert p.returncode == 0, p.stderr
    assert "issue create" in seams.subcommands()
    assert seams.mails() == []
    assert "RESEND_API_KEY unset, skipping" in p.stdout


def test_notify_refused_mail_is_a_notifier_error_after_the_issue_exists(tmp_path, seams):
    env = {**seams.env, "RECON_UPTIME_RESEND_URL": seams.web.url + "/nope"}
    p = run_notify(env, _result_file(tmp_path, down=True))
    assert p.returncode == 2
    assert "issue create" in seams.subcommands()
    assert "RESEND_ERR" in p.stdout and "notify error" in p.stderr


def test_notify_unreadable_result_is_exit_2(tmp_path, seams):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    p = run_notify(seams.env, str(bad))
    assert p.returncode == 2
    assert seams.calls() == []


def test_notify_failing_gh_is_exit_2(tmp_path, seams):
    env = {**seams.env, "RECON_UPTIME_GH_CMD": shlex.join(
        [sys.executable.replace("\\", "/"), "-c", "import sys; sys.exit(3)"])}
    p = run_notify(env, _result_file(tmp_path, down=True))
    assert p.returncode == 2
    assert "gh issue list failed (3)" in p.stderr
    assert seams.mails() == []
