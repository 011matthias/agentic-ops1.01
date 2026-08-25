"""Passwordless (magic-link) login + admin-approval account flow (v6).

Covers the pure primitives (email validation, token hash/entropy), the store
(users + single-use login_tokens + seed admins), the accounts orchestration
(request -> pending/sent, verify single-use + revocation-safe, admin gate), and
the HTTP flow end-to-end with an injected fake mailer (Graph is never touched).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lead_desk.web import accounts, auth
from lead_desk.web.app import create_app
from lead_desk.web.store import ContactStore


# --- fixtures ----------------------------------------------------------------

class FakeMailer:
    """Records send_auto payloads instead of hitting Graph."""

    def __init__(self):
        self.sent = []

    def send_auto(self, send: dict):
        self.sent.append(send)


@pytest.fixture(autouse=True)
def _reset_throttles():
    # The per-IP throttles are module-global; TestClient shares one client host
    # across tests, so clear it each test for determinism.
    auth._MAGIC_REQS.clear()
    yield


@pytest.fixture
def store(tmp_path):
    with ContactStore(tmp_path / "ld.sqlite") as s:
        yield s


NOW = "2026-07-24T10:00:00+00:00"
EXP = "2026-07-24T10:15:00+00:00"          # token expiry (NOW + 15 min)
LATER_OK = "2026-07-24T10:10:00+00:00"     # before expiry
LATER_EXP = "2026-07-24T10:20:00+00:00"    # after expiry

MATTHIAS = "matthias.silva@brisken.com"
DIRK = "dirk.neumann@brisken.com"


# --- pure primitives ---------------------------------------------------------

def test_email_validation():
    assert auth.valid_email("A.B@Brisken.com")
    assert auth.normalize_email("  A.B@Brisken.com ") == "a.b@brisken.com"
    for bad in ("", "nope", "a@b", "a b@c.com", "@x.com", "x@y", None):
        assert not auth.valid_email(bad)


def test_magic_token_entropy_and_hash():
    raw, h = auth.new_magic_token()
    assert len(raw) >= 32 and h == auth.hash_magic_token(raw)
    assert auth.new_magic_token()[0] != auth.new_magic_token()[0]   # random
    assert raw not in h                                             # only hash stored


def test_seed_admins_constant():
    assert MATTHIAS in auth.SEED_ADMIN_EMAILS and DIRK in auth.SEED_ADMIN_EMAILS
    assert auth.is_seed_admin(MATTHIAS) and not auth.is_seed_admin("x@y.com")


# --- store: schema + seed ----------------------------------------------------

def test_migration_seeds_two_approved_admins(store):
    for e in (MATTHIAS, DIRK):
        u = store.get_user(e)
        assert u is not None and u["role"] == "admin" and u["status"] == "approved"
    assert store.count_admins() == 2


def test_login_token_single_use_and_expiry(store):
    raw, h = auth.new_magic_token()
    store.create_login_token(h, MATTHIAS, NOW, EXP, "1.2.3.4")
    # past expiry -> None (and NOT marked used, so a later in-window call could
    # still work; here we just prove the time gate)
    assert store.consume_login_token(h, LATER_EXP) is None
    # in-window -> returns the email, single use
    assert store.consume_login_token(h, LATER_OK) == MATTHIAS
    assert store.consume_login_token(h, LATER_OK) is None           # already used


def test_pending_user_lifecycle(store):
    assert store.create_pending_user("New.Person@brisken.com", "New", NOW) is True
    assert store.create_pending_user("new.person@brisken.com", "", NOW) is False  # idempotent
    u = store.get_user("new.person@brisken.com")
    assert u["status"] == "pending" and u["role"] == "member"
    store.set_user_status("new.person@brisken.com", "approved", "admin@x", NOW)
    assert store.get_user("new.person@brisken.com")["status"] == "approved"


def test_purge_expired_tokens(store):
    _, h = auth.new_magic_token()
    store.create_login_token(h, MATTHIAS, NOW, LATER_OK, None)
    assert store.purge_expired_tokens(LATER_EXP) == 1


# --- accounts: request_magic_link -------------------------------------------

def test_request_unknown_email_becomes_pending_and_notifies_admins(store):
    mail = FakeMailer()
    res = accounts.request_magic_link(store, "stranger@brisken.com",
                                      base_url="https://x", ip="1.1.1.1",
                                      now=NOW, mailer=mail)
    assert res["status"] == "pending_new"
    assert store.get_user("stranger@brisken.com")["status"] == "pending"
    # both seeded admins were emailed the request
    assert {m["to"] for m in mail.sent} == {MATTHIAS, DIRK}


def test_request_approved_sends_single_use_link(store):
    mail = FakeMailer()
    res = accounts.request_magic_link(store, MATTHIAS, base_url="https://x",
                                      ip=None, now=NOW, mailer=mail)
    assert res["status"] == "sent" and "/auth/verify?token=" in res["link"]
    assert len(mail.sent) == 1 and mail.sent[0]["to"] == MATTHIAS
    # the raw token is in the email link but only its hash is stored
    raw = res["link"].split("token=")[1]
    assert store.consume_login_token(auth.hash_magic_token(raw), LATER_OK) == MATTHIAS


def test_request_approved_without_mailer_mints_no_token(store):
    res = accounts.request_magic_link(store, MATTHIAS, base_url="https://x",
                                      ip=None, now=NOW, mailer=None)
    assert res["status"] == "no_mailer"
    # no orphan token was created
    assert store.conn.execute("SELECT COUNT(*) FROM login_tokens").fetchone()[0] == 0


def test_request_pending_and_disabled_and_invalid(store):
    store.create_pending_user("waiting@brisken.com", "", NOW)
    store.upsert_user("gone@brisken.com", "", "member", "disabled", "a", NOW)
    m = FakeMailer()
    assert accounts.request_magic_link(store, "waiting@brisken.com",
                                       base_url="x", ip=None, now=NOW, mailer=m)["status"] == "pending"
    assert accounts.request_magic_link(store, "gone@brisken.com",
                                       base_url="x", ip=None, now=NOW, mailer=m)["status"] == "disabled"
    assert accounts.request_magic_link(store, "not-an-email",
                                       base_url="x", ip=None, now=NOW, mailer=m)["status"] == "invalid"


# --- accounts: verify + revocation safety -----------------------------------

def test_verify_and_login_single_use(store):
    mail = FakeMailer()
    link = accounts.request_magic_link(store, MATTHIAS, base_url="https://x",
                                       ip=None, now=NOW, mailer=mail)["link"]
    raw = link.split("token=")[1]
    assert accounts.verify_and_login(store, raw, LATER_OK) == MATTHIAS
    assert accounts.verify_and_login(store, raw, LATER_OK) is None   # single use
    assert store.get_user(MATTHIAS)["last_login_at"] == LATER_OK


def test_verify_fails_if_approval_revoked_after_issue(store):
    mail = FakeMailer()
    link = accounts.request_magic_link(store, MATTHIAS, base_url="https://x",
                                       ip=None, now=NOW, mailer=mail)["link"]
    raw = link.split("token=")[1]
    store.set_user_status(MATTHIAS, "disabled", "someone", NOW)      # revoked
    assert accounts.verify_and_login(store, raw, LATER_OK) is None   # fails closed


# --- accounts: admin resolution ---------------------------------------------

def test_is_admin_resolution(store):
    store.upsert_user("member@brisken.com", "", "member", "approved", "a", NOW)
    assert accounts.is_admin(store, MATTHIAS) is True               # seeded admin
    assert accounts.is_admin(store, "member@brisken.com") is False  # approved member
    assert accounts.is_admin(store, "stranger@brisken.com") is False  # not a user
    assert accounts.is_admin(store, "local") is True                # ungated dev


# --- HTTP integration --------------------------------------------------------

@pytest.fixture
def app_mail(tmp_path, monkeypatch):
    """A gated app whose auth-email path is wired to a fake mailer."""
    monkeypatch.setenv("LEAD_DESK_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("LEAD_DESK_INSECURE_COOKIE", "1")
    monkeypatch.setenv("LEAD_DESK_AUTH_EMAILS", "1")
    monkeypatch.setenv("LEAD_DESK_BASE_URL", "https://lead-desk.test")
    mail = FakeMailer()
    monkeypatch.setattr(accounts, "_resolve_mailer", lambda: mail)
    client = TestClient(create_app(tmp_path))
    client._mail = mail  # type: ignore[attr-defined]
    return client


def _magic_login(client, email):
    """Drive the full email -> link -> verify flow; leaves client authed."""
    r = client.post("/login/magic", data={"email": email}, follow_redirects=False)
    assert r.status_code == 303 and "notice=sent" in r.headers["location"]
    link = client._mail.sent[-1]["body"]
    token = link.split("token=")[1].split()[0].strip()
    r2 = client.get(f"/auth/verify?token={token}", follow_redirects=False)
    assert r2.status_code == 303 and r2.headers["location"] == "/"
    assert auth.COOKIE_NAME in r2.cookies


def test_login_page_is_email_only(app_mail):
    html = app_mail.get("/login").text
    assert 'action="/login/magic"' in html and 'name="email"' in html
    # access code fully removed - no code field, no fallback
    assert 'name="code"' not in html and 'Use an access code' not in html


def test_magic_flow_end_to_end_admin(app_mail):
    _magic_login(app_mail, MATTHIAS)
    r = app_mail.get("/", follow_redirects=False)
    assert r.status_code == 200
    # admin sees the Users nav link + can open the admin page
    assert "/admin/users" in r.text
    assert app_mail.get("/admin/users").status_code == 200


def test_admin_page_is_admin_only(app_mail):
    # seed an approved member, log in as them -> /admin/users forbidden
    with ContactStore(app_mail.app.state.db_path) as s:
        s.upsert_user("member@brisken.com", "M", "member", "approved", "seed", NOW)
    _magic_login(app_mail, "member@brisken.com")
    assert app_mail.get("/admin/users", follow_redirects=False).status_code == 403
    assert "/admin/users" not in app_mail.get("/").text     # nav link hidden


def test_new_request_then_admin_approve(app_mail):
    # a stranger asks for access -> pending, no link
    app_mail.post("/login/magic", data={"email": "newbie@brisken.com"},
                  follow_redirects=False)
    with ContactStore(app_mail.app.state.db_path) as s:
        assert s.get_user("newbie@brisken.com")["status"] == "pending"
    # an admin approves via the admin route (CSRF-protected)
    _magic_login(app_mail, MATTHIAS)
    csrf = auth.csrf_token(MATTHIAS)
    r = app_mail.post("/admin/users/approve",
                      data={"email": "newbie@brisken.com", "csrf": csrf},
                      follow_redirects=False)
    assert r.status_code == 303
    with ContactStore(app_mail.app.state.db_path) as s:
        assert s.get_user("newbie@brisken.com")["status"] == "approved"


def test_cannot_disable_last_admin(app_mail):
    _magic_login(app_mail, MATTHIAS)
    csrf = auth.csrf_token(MATTHIAS)
    # disable Dirk (allowed; two admins -> one left)
    r1 = app_mail.post("/admin/users/disable", data={"email": DIRK, "csrf": csrf},
                       follow_redirects=False)
    assert r1.status_code == 303
    # now disabling the sole remaining admin is blocked
    r2 = app_mail.post("/admin/users/disable", data={"email": MATTHIAS, "csrf": csrf},
                       follow_redirects=False)
    assert r2.status_code == 400


def test_magic_request_is_rate_limited(app_mail):
    # exhaust the per-IP magic budget; the next one is throttled
    for _ in range(auth.MAGIC_MAX_REQS):
        app_mail.post("/login/magic", data={"email": MATTHIAS}, follow_redirects=False)
    r = app_mail.post("/login/magic", data={"email": MATTHIAS}, follow_redirects=False)
    assert "err=throttled" in r.headers["location"]
