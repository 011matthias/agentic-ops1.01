"""A sign-in link survives being fetched by something that is not the person.

Brisken mail arrives through Microsoft Safe Links, which rewrites every URL
and fetches it before the recipient ever sees the message. While GET
/auth/verify redeemed the single-use token, that fetch spent it, and the
person clicking their own link landed on "invalid, expired, or already used".

The contract these tests hold: a GET never spends a link, a POST does, and
the POST is still single-use.
"""
import pytest
from fastapi.testclient import TestClient

from lead_desk.web import accounts, auth
from lead_desk.web.app import create_app
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore

DIRK = "dirk.neumann@brisken.com"


class FakeMailer:
    def __init__(self):
        self.sent = []

    def send_auto(self, send: dict):
        self.sent.append(send)


@pytest.fixture(autouse=True)
def _reset_throttles():
    auth._MAGIC_REQS.clear()
    yield
    auth._MAGIC_REQS.clear()


@pytest.fixture
def gated(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_DESK_AUTH_SECRET", "s3cret")
    monkeypatch.setenv("LEAD_DESK_INSECURE_COOKIE", "1")
    c = TestClient(create_app(tmp_path))
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def _fresh_link(client, *, next_path=""):
    """Mint a real link on the real clock (a fixed mint time turns expired
    once the wall clock passes it: the repo's recurring test time-bomb)."""
    with ContactStore(client.db) as store:
        res = accounts.request_magic_link(
            store, DIRK, base_url="https://x", ip=None, now=now_iso(),
            mailer=FakeMailer(), next_path=next_path)
    assert res["status"] == "sent"
    return res["link"].removeprefix("https://x"), \
        res["link"].split("token=")[1].split("&")[0]


def test_a_scanner_fetch_does_not_spend_the_link(gated):
    """The failure Dirk reported on 2026-09-09, as a test."""
    path, token = _fresh_link(gated)

    # Whatever fetches the link ahead of him - twice, to be unkind.
    for _ in range(2):
        scan = gated.get(path, follow_redirects=False)
        assert scan.status_code == 200          # the page itself, not a bounce
        assert auth.COOKIE_NAME not in scan.cookies  # no session handed out

    # He then clicks it himself and is signed in.
    r = gated.post("/auth/verify", data={"token": token},
                   follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert auth.COOKIE_NAME in r.cookies
    assert gated.get("/", follow_redirects=False).status_code == 200


def test_the_landing_page_names_who_is_signing_in(gated):
    path, token = _fresh_link(gated)
    page = gated.get(path)
    assert DIRK in page.text
    assert f'name="token" value="{token}"' in page.text
    assert 'method="post" action="/auth/verify"' in page.text


def test_redeeming_is_still_single_use(gated):
    _, token = _fresh_link(gated)
    first = gated.post("/auth/verify", data={"token": token},
                       follow_redirects=False)
    assert first.status_code == 303 and first.headers["location"] == "/"
    gated.cookies.clear()
    second = gated.post("/auth/verify", data={"token": token},
                        follow_redirects=False)
    assert second.headers["location"] == "/login?err=badlink"
    assert auth.COOKIE_NAME not in second.cookies


def test_a_spent_link_reports_itself_on_arrival(gated):
    """No button on a dead link: the error shows on the page he lands on,
    not after another click."""
    path, token = _fresh_link(gated)
    gated.post("/auth/verify", data={"token": token}, follow_redirects=False)
    gated.cookies.clear()
    r = gated.get(path, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login?err=badlink"


def test_a_garbage_token_never_renders_a_button(gated):
    r = gated.get("/auth/verify?token=not-a-real-token", follow_redirects=False)
    assert r.headers["location"] == "/login?err=badlink"
    r = gated.get("/auth/verify", follow_redirects=False)
    assert r.headers["location"] == "/login?err=badlink"


def test_peek_respects_expiry_and_use(gated):
    """The store half, directly: expired and spent both read as dead."""
    _, token = _fresh_link(gated)
    h = auth.hash_magic_token(token)
    with ContactStore(gated.db) as store:
        assert store.peek_login_token(h, now_iso()) == DIRK
        assert store.peek_login_token(h, "2099-01-01T00:00:00+00:00") is None
        assert store.consume_login_token(h, now_iso()) == DIRK
        assert store.peek_login_token(h, now_iso()) is None
