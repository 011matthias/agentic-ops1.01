"""Login throttle tests (`POST /api/login`).

The shared operator code is the app's entire security boundary, so the
throttle is the thing standing between an attacker and unlimited guesses.
Covered here: the per-IP lockout and its doubling, the global budget that
catches a caller rotating a forged `Fly-Client-IP`, success clearing the
caller's record, the 429 shape the SPA sees, and the no-op paths (gate
off, throttle disabled) that must not change existing behavior.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web import ratelimit  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

OP_CODE = "operator-code-1"


@pytest.fixture
def gated(tmp_path, monkeypatch):
    """Gate on, throttle at its shipped defaults."""
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    monkeypatch.delenv("EXPENSE_RECON_LOGIN_RATELIMIT", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _login(client, code="wrong", ip=None):
    headers = {"Fly-Client-IP": ip} if ip else {}
    return client.post("/api/login", json={"code": code}, headers=headers)


# ── per-IP tier ────────────────────────────────────────────────────────


def test_sixth_failure_from_one_ip_is_throttled(gated):
    # Default allowance is 5 failures per window.
    for i in range(5):
        assert _login(gated, ip="203.0.113.7").status_code == 401, i
    blocked = _login(gated, ip="203.0.113.7")
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["scope"] == "ip"
    assert body["retry_after"] > 0
    assert blocked.headers["Retry-After"] == str(body["retry_after"])


def test_lockout_is_scoped_to_the_offending_ip(gated):
    for _ in range(5):
        _login(gated, ip="203.0.113.7")
    assert _login(gated, ip="203.0.113.7").status_code == 429
    # A different caller is unaffected while the global budget is intact.
    assert _login(gated, ip="198.51.100.4").status_code == 401


def test_correct_code_still_works_from_a_clean_ip(gated):
    for _ in range(5):
        _login(gated, ip="203.0.113.7")
    ok = _login(gated, code=OP_CODE, ip="198.51.100.4")
    assert ok.status_code == 200
    assert ok.json()["token"]


def test_a_locked_out_ip_cannot_pass_even_with_the_right_code(gated):
    """The throttle runs before the code check; that is the point."""
    for _ in range(5):
        _login(gated, ip="203.0.113.7")
    assert _login(gated, code=OP_CODE, ip="203.0.113.7").status_code == 429


def test_success_clears_the_callers_failures(gated):
    for _ in range(4):
        assert _login(gated, ip="203.0.113.7").status_code == 401
    assert _login(gated, code=OP_CODE, ip="203.0.113.7").status_code == 200
    # Record cleared, so the allowance starts over rather than tripping.
    for i in range(5):
        assert _login(gated, ip="203.0.113.7").status_code == 401, i


# ── global tier (the forged-header backstop) ───────────────────────────


def test_rotating_the_ip_header_still_hits_the_global_budget(gated, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_LOGIN_GLOBAL_MAX", "12")
    # Every attempt from a fresh address, so the per-IP tier never fires.
    for i in range(12):
        assert _login(gated, ip=f"203.0.113.{i}").status_code == 401, i
    blocked = _login(gated, ip="198.51.100.99")
    assert blocked.status_code == 429
    assert blocked.json()["scope"] == "global"


# ── no-op paths ────────────────────────────────────────────────────────


def test_throttle_disabled_by_env_never_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    monkeypatch.setenv("EXPENSE_RECON_LOGIN_RATELIMIT", "0")
    with TestClient(create_app(tmp_path)) as c:
        for _ in range(12):
            assert _login(c, ip="203.0.113.7").status_code == 401


def test_gate_off_login_is_untouched(tmp_path, monkeypatch):
    """No code configured means nothing to brute force; the local dev path
    keeps handing out a token however often it is called."""
    monkeypatch.delenv("EXPENSE_RECON_OPERATOR_CODE", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        for _ in range(12):
            assert c.post("/api/login", json={}).status_code == 200


def test_healthz_is_not_throttled(gated):
    for _ in range(6):
        _login(gated, ip="203.0.113.7")
    assert gated.get("/healthz").status_code == 200


# ── policy unit level ──────────────────────────────────────────────────


def test_client_ip_prefers_fly_header_then_forwarded_then_peer():
    class _Req:
        def __init__(self, headers, host="10.0.0.1"):
            self.headers = headers
            self.client = type("C", (), {"host": host})()

    assert ratelimit.client_ip(_Req({"fly-client-ip": "1.2.3.4"})) == "1.2.3.4"
    # First hop of X-Forwarded-For when Fly's header is absent.
    assert ratelimit.client_ip(_Req({"x-forwarded-for": "5.6.7.8, 9.9.9.9"})) == "5.6.7.8"
    assert ratelimit.client_ip(_Req({})) == "10.0.0.1"
    # A hostile header cannot bloat the stored key.
    long = ratelimit.client_ip(_Req({"fly-client-ip": "x" * 500}))
    assert len(long) == 64


def test_ipv6_is_bucketed_by_prefix_not_by_address():
    """A caller holding a /64 must not get 2**64 fresh buckets. The real
    live key seen on Fly was a /128 Telekom address; these two differ only
    below the /64 and so must share a bucket."""
    a = ratelimit.bucket_key("2003:c6:3f3c:3200:5c56:c79:7bc4:fffa")
    b = ratelimit.bucket_key("2003:c6:3f3c:3200:dead:beef:1:2")
    assert a == b == "2003:c6:3f3c:3200::/64"
    # A different /64 is genuinely a different caller.
    assert ratelimit.bucket_key("2003:c6:3f3c:3201::1") != a


def test_ipv4_keeps_the_full_address_and_junk_passes_through():
    assert ratelimit.bucket_key("198.51.100.4") == "198.51.100.4"
    assert ratelimit.bucket_key("testclient") == "testclient"
    assert ratelimit.bucket_key("") == "unknown"


def test_ipv6_rotation_within_one_prefix_still_locks_out(gated):
    """The per-IP tier holds against the rotation it would otherwise miss —
    without needing the global budget to catch it."""
    for i in range(5):
        assert _login(gated, ip=f"2003:c6:3f3c:3200::{i + 1}").status_code == 401, i
    blocked = _login(gated, ip="2003:c6:3f3c:3200::ffff")
    assert blocked.status_code == 429
    assert blocked.json()["scope"] == "ip"
    # A different /64 is unaffected.
    assert _login(gated, ip="2003:c6:3f3c:3299::1").status_code == 401


def test_lockout_doubles_per_extra_failure_and_caps():
    pol = ratelimit.Policy(max_attempts=5, lockout=60, lockout_cap=3600)
    assert ratelimit._lock_seconds(5, pol) == 60
    assert ratelimit._lock_seconds(6, pol) == 120
    assert ratelimit._lock_seconds(7, pol) == 240
    # Caps rather than growing without bound.
    assert ratelimit._lock_seconds(99, pol) == 3600


def test_failures_age_out_of_the_window(tmp_path):
    """A lockout is not permanent: once the failures fall outside the
    window the caller is allowed to try again."""
    pol = ratelimit.Policy(max_attempts=3, window=900, lockout=60)
    with RunStore(tmp_path / "db.sqlite") as store:
        now = 10_000.0
        for _ in range(3):
            store.record_login_failure("1.2.3.4", now)
        assert ratelimit.evaluate(store, "1.2.3.4", now + 1, pol).allowed is False
        # Well past the window: the rows no longer count.
        assert ratelimit.evaluate(store, "1.2.3.4", now + 1000, pol).allowed is True


def test_store_stats_scope_and_prune(tmp_path):
    with RunStore(tmp_path / "db.sqlite") as store:
        store.record_login_failure("a", 100.0)
        store.record_login_failure("a", 200.0)
        store.record_login_failure("b", 300.0)

        n, last = store.login_failure_stats(0.0, ip="a")
        assert (n, last) == (2, 200.0)
        n_all, last_all = store.login_failure_stats(0.0)
        assert (n_all, last_all) == (3, 300.0)

        store.clear_login_failures("a")
        assert store.login_failure_stats(0.0, ip="a") == (0, 0.0)
        assert store.login_failure_stats(0.0)[0] == 1

        store.prune_login_failures(400.0)
        assert store.login_failure_stats(0.0)[0] == 0
