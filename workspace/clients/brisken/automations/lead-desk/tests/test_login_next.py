"""Post-login destination carry-through (?next=).

A gated GET remembers where the person was headed, the magic-link email
carries it, and redeeming the link lands there instead of on the board.
Unsafe destinations (foreign origins, protocol-relative, backslash tricks)
always fall back to '/'.
"""
import pytest
from fastapi.testclient import TestClient

from lead_desk.web import accounts, auth
from lead_desk.web.app import create_app
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore

MATTHIAS = "matthias.silva@brisken.com"


class FakeMailer:
    def __init__(self):
        self.sent = []

    def send_auto(self, send: dict):
        self.sent.append(send)


@pytest.fixture(autouse=True)
def _reset_throttles():
    # The per-IP magic-link throttle is module-global; TestClient shares one
    # client host, so consecutive tests would trip it.
    auth._MAGIC_REQS.clear()
    yield
    auth._MAGIC_REQS.clear()


@pytest.fixture
def gated(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_DESK_AUTH_SECRET", "s3cret")
    app = create_app(tmp_path)
    c = TestClient(app)
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def test_safe_next_path_matrix():
    assert auth.safe_next_path("/review/september-2026") == "/review/september-2026"
    assert auth.safe_next_path("/contacts/x?y=1#z") == "/contacts/x?y=1#z"
    for bad in ("", None, "https://evil.com/x", "//evil.com", "/a\\b",
                "javascript:alert(1)", "review", "/" + "a" * 600):
        assert auth.safe_next_path(bad) == "/"


def test_gate_redirect_carries_next(gated):
    r = gated.get("/review/september-2026", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login?next=%2Freview%2Fseptember-2026"
    # The login page then renders the destination into the magic form.
    r = gated.get("/login?next=%2Freview%2Fseptember-2026")
    assert 'name="next" value="/review/september-2026"' in r.text
    # The board itself stays a bare /login redirect.
    r = gated.get("/", follow_redirects=False)
    assert r.headers["location"] == "/login"


def test_magic_link_carries_next_and_lands_there(gated):
    mail = FakeMailer()
    with ContactStore(gated.db) as store:
        # Mint on the REAL clock: the HTTP redeem below runs at real now, and
        # a fixed mint time turns into an expired token once the wall clock
        # passes it (the repo's recurring test time-bomb class).
        res = accounts.request_magic_link(
            store, MATTHIAS, base_url="https://x", ip=None, now=now_iso(),
            mailer=mail, next_path="/review/september-2026")
    assert res["status"] == "sent"
    assert "&next=%2Freview%2Fseptember-2026" in res["link"]
    verify_path = res["link"].removeprefix("https://x")
    r = gated.get(verify_path, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/review/september-2026"
    assert auth.COOKIE_NAME in r.cookies


def test_verify_with_unsafe_next_lands_on_board(gated):
    mail = FakeMailer()
    with ContactStore(gated.db) as store:
        res = accounts.request_magic_link(
            store, MATTHIAS, base_url="https://x", ip=None, now=now_iso(),
            mailer=mail)
    token = res["link"].split("token=")[1]
    r = gated.get(f"/auth/verify?token={token}&next=https%3A%2F%2Fevil.com",
                  follow_redirects=False)
    assert r.headers["location"] == "/"


def test_login_magic_route_threads_next_into_the_email(gated, monkeypatch):
    mail = FakeMailer()
    monkeypatch.setattr(accounts, "_resolve_mailer", lambda: mail)
    r = gated.post("/login/magic",
                   data={"email": MATTHIAS, "next": "/review/september-2026"},
                   follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == \
        "/login?notice=sent&next=%2Freview%2Fseptember-2026"
    assert len(mail.sent) == 1
    assert "next=%2Freview%2Fseptember-2026" in str(mail.sent[0])


def test_unsafe_next_never_reaches_the_email(gated, monkeypatch):
    mail = FakeMailer()
    monkeypatch.setattr(accounts, "_resolve_mailer", lambda: mail)
    r = gated.post("/login/magic",
                   data={"email": MATTHIAS, "next": "https://evil.com/x"},
                   follow_redirects=False)
    assert r.status_code == 303
    assert "evil.com" not in r.headers["location"]
    assert "evil.com" not in str(mail.sent[0])
