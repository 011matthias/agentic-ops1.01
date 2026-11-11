"""Tests for tools/brisken-mail-search.py.

No network: a fake Graph session answers by URL. The caller-level tests run
through main() so the allowlist, the coverage accounting and the exit code are
exercised the way the agent will hit them, not only through the helpers.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "brisken-mail-search.py"
spec = importlib.util.spec_from_file_location("brisken_mail_search", TOOL)
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)

G = ms.GRAPH
DIRK = "dirk.neumann@brisken.com"


class FakeResp:
    def __init__(self, status: int, body: dict, headers: dict | None = None):
        self.status_code = status
        self._body = body
        self.headers = headers or {}

    def json(self):
        return self._body


class FakeSession:
    """Routes GETs by exact URL. Has no post/patch/delete: a write would raise."""

    def __init__(self, routes: dict[str, tuple[int, dict]]):
        self.routes = routes
        self.calls: list[str] = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append(url)
        if url not in self.routes:
            raise AssertionError(f"unexpected GET {url}")
        route = self.routes[url]
        if isinstance(route, list):  # a sequence of answers, one per call
            route = route.pop(0) if len(route) > 1 else route[0]
        return FakeResp(*route)


def _folders(mbx, *folders):
    return {f"{G}/users/{mbx}/mailFolders": (200, {"value": list(folders)})}


def _msg(subject, sender, received="2026-07-10T09:00:00Z", att=True):
    return {"id": f"id-{subject}", "subject": subject, "receivedDateTime": received,
            "from": {"emailAddress": {"address": sender}}, "hasAttachments": att,
            "isDraft": False, "internetMessageId": f"<{subject}@x>"}


@pytest.fixture
def wired(monkeypatch):
    def install(routes):
        sess = FakeSession(routes)
        monkeypatch.setattr(ms.requests, "Session", lambda: sess)
        monkeypatch.setattr(ms.truth, "load_env", lambda: {})
        monkeypatch.setattr(ms.truth, "get_token", lambda creds: "tok")
        monkeypatch.setattr(ms, "_sleep", lambda s: None)
        return sess
    return install


# ---------------------------------------------------------------- allowlist

def test_only_the_three_mailboxes_resolve():
    assert ms.resolve_mailboxes("all") == [
        "dirk.neumann@brisken.com", "matthias.silva@brisken.com",
        "cristiane.cavalcanti@brisken.com"]
    with pytest.raises(ms.Refused):
        ms.resolve_mailboxes("ceo@brisken.com")


def test_get_refuses_a_foreign_mailbox_before_any_request():
    sess = FakeSession({})
    with pytest.raises(ms.Refused):
        ms.get(sess, f"{G}/users/someone.else@brisken.com/messages", "tok")
    assert sess.calls == []


# ---------------------------------------------------------------- filters

def test_filter_escapes_quotes_and_composes():
    f = ms.build_filter("2026-07-01", "2026-08-01", "o'neil@x.com", True)
    assert "receivedDateTime ge 2026-07-01T00:00:00Z" in f
    assert "receivedDateTime lt 2026-08-01T00:00:00Z" in f
    assert "address eq 'o''neil@x.com'" in f
    assert f.endswith("hasAttachments eq true")


def test_domain_match_is_suffix_on_the_address_not_substring():
    m = _msg("Invoice", "billing@regus.com")
    assert ms.matches(m, None, None, "regus.com")
    assert ms.matches(m, "INVOICE", None, "@regus.com")
    assert not ms.matches(_msg("Invoice", "billing@notregus.com.evil"), None, None, "regus.com")
    assert not ms.matches(m, "receipt", None, None)


# ---------------------------------------------------------------- through main()

def test_failed_folder_makes_the_search_incomplete(wired, capsys):
    inbox = {"id": "F1", "displayName": "Inbox", "totalItemCount": 3, "childFolderCount": 0}
    archive = {"id": "F2", "displayName": "Archive", "totalItemCount": 9, "childFolderCount": 0}
    routes = _folders(DIRK, inbox, archive)
    routes[f"{G}/users/{DIRK}/mailFolders/F1/messages"] = (200, {"value": [
        _msg("Your Regus invoice", "billing@regus.com"),
        _msg("Lunch", "friend@gmail.com")]})
    routes[f"{G}/users/{DIRK}/mailFolders/F2/messages"] = (
        503, {"error": {"code": "ServiceUnavailable", "message": "try later"}})
    wired(routes)

    rc = ms.main(["search", "--mailbox", "dirk", "--since", "2026-07-01", "--walk",
                  "--sender-domain", "regus.com", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 3
    assert out["complete"] is False
    assert out["hit_count"] == 1 and out["hits"][0]["folder"] == "Inbox"
    box = out["mailboxes"][0]
    assert box["folders_scanned"] == 1 and box["folders_total"] == 2
    assert box["failures"][0]["folder"] == "Archive"


def test_clean_walk_is_complete_and_says_so(wired, capsys):
    inbox = {"id": "F1", "displayName": "Inbox", "totalItemCount": 1, "childFolderCount": 1}
    child = {"id": "C1", "displayName": "Receipts", "totalItemCount": 1, "childFolderCount": 0}
    empty = {"id": "F3", "displayName": "Junk", "totalItemCount": 0, "childFolderCount": 0}
    routes = _folders(DIRK, inbox, empty)
    routes[f"{G}/users/{DIRK}/mailFolders/F1/childFolders"] = (200, {"value": [child]})
    routes[f"{G}/users/{DIRK}/mailFolders/F1/messages"] = (200, {"value": []})
    routes[f"{G}/users/{DIRK}/mailFolders/C1/messages"] = (200, {"value": [
        _msg("GitHub receipt", "noreply@github.com")]})
    sess = wired(routes)

    rc = ms.main(["search", "--mailbox", "dirk", "--since", "2026-07-01", "--walk",
                  "--subject", "receipt"])
    text = capsys.readouterr().out
    assert rc == 0
    assert "COMPLETE" in text and "[Inbox / Receipts]" in text
    assert all("/mailFolders/F3/messages" not in u for u in sess.calls), "empty folder was queried"


def test_default_search_reads_received_mail_in_one_query(wired, capsys):
    hit = {**_msg("Your Regus invoice", "billing@regus.com"), "parentFolderId": "FX"}
    routes = {
        f"{G}/users/{DIRK}/messages": (200, {"value": [hit, _msg("Lunch", "a@gmail.com")]}),
        f"{G}/users/{DIRK}/mailFolders/FX": (200, {"displayName": "22 - SALES"}),
    }
    sess = wired(routes)
    rc = ms.main(["search", "--mailbox", "dirk", "--since", "2026-10-01",
                  "--sender-domain", "regus.com", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["complete"] is True
    assert [h["folder"] for h in out["hits"]] == ["22 - SALES"]
    assert not any(u.endswith("/mailFolders") for u in sess.calls), "default must not walk folders"


def test_throttled_request_is_retried_not_counted_as_a_gap(wired, capsys):
    routes = {f"{G}/users/{DIRK}/messages": [
        (429, {"error": {"code": "TooManyRequests"}}, {"Retry-After": "2"}),
        (200, {"value": [_msg("Regus invoice", "billing@regus.com")]})]}
    sess = wired(routes)
    rc = ms.main(["search", "--mailbox", "dirk", "--since", "2026-10-01", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["complete"] is True and out["hit_count"] == 1
    assert len(sess.calls) == 2


def test_probe_window_count_is_the_broad_differential(wired, capsys):
    routes = {f"{G}/users/{DIRK}/mailFolders/inbox": (200, {"totalItemCount": 12}),
              f"{G}/users/{DIRK}/messages": (200, {"value": [], "@odata.count": 0})}
    wired(routes)
    rc = ms.main(["probe", "--mailbox", "dirk", "--since", "2030-01-01", "--until", "2030-02-01"])
    assert rc == 1, "an empty window must fail the probe: a zero inside it proves nothing"
    assert "window 2030-01-01..2030-02-01: 0 message(s)" in capsys.readouterr().out


def test_blocked_mailbox_probe_fails_with_the_policy_error(wired, capsys):
    criss = "cristiane.cavalcanti@brisken.com"
    wired({f"{G}/users/{criss}/mailFolders/inbox": (403, {"error": {
        "code": "ErrorAccessDenied",
        "message": "Blocked by tenant configured AppOnly AccessPolicy settings."}})})
    rc = ms.main(["probe", "--mailbox", "criss"])
    text = capsys.readouterr().out
    assert rc == 1
    assert "BLOCKED (403)" in text and "AccessPolicy" in text


def test_probe_known_sender_not_found_is_a_failed_instrument(wired, capsys):
    routes = {f"{G}/users/{DIRK}/mailFolders/inbox": (200, {"totalItemCount": 12}),
              f"{G}/users/{DIRK}/messages": (200, {"value": []})}
    wired(routes)
    rc = ms.main(["probe", "--mailbox", "dirk", "--known-from", "no-reply@zohoexpense.com",
                  "--since", "2026-07-01"])
    assert rc == 1
    assert "NOT FOUND" in capsys.readouterr().out
