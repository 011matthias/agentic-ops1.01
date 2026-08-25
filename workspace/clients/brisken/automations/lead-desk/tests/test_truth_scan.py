"""T5: scheduled deep truth reconcile - folder-cache diffing, retry + alert
semantics, ingest dedupe / unmatched behavior, run log + heartbeat state,
the every-7th-run full scan, and the creds-guarded scheduler. FakeMailer
pattern from test_cloud_worker extended with folder-walk recorders - no
network, no Graph.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from lead_desk import truth_scan
from lead_desk.graph_mail import (
    DIRK_SMTP, GraphMailer, GraphRetryError, NotAllowlisted,
)
from lead_desk.truth_scan import run_scan
from lead_desk.web.service import ingest_event, now_iso
from lead_desk.web.store import ContactStore

NOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)


class FakeMailer:
    """Records folder walks + pulls; behavior configured per test."""

    def __init__(self):
        self.folders: dict[str, list[dict]] = {}    # mailbox -> folder rows
        self.messages: dict[str, list[dict]] = {}   # folder_id -> messages
        self.fail: dict[str, Exception] = {}        # folder_id -> raises
        self.listed: list[str] = []
        self.pulled: list[tuple[str, str, str]] = []  # (mbx, folder, since)

    def list_mail_folders(self, mailbox):
        self.listed.append(mailbox)
        return [dict(f) for f in self.folders.get(mailbox, [])]

    def pull_folder_outbound(self, mailbox, folder_id, since_iso):
        self.pulled.append((mailbox, folder_id, since_iso))
        exc = self.fail.get(folder_id)
        if exc is not None:
            raise exc
        return [dict(m) for m in self.messages.get(folder_id, [])]


def folder(fid, path="Sent Items", count=3):
    return {"id": fid, "path": path, "total_item_count": count}


def msg(imid, to, subject="Rome intro"):
    return {"id": f"g-{imid}", "internet_message_id": imid, "to": [to],
            "cc": [], "subject": subject,
            "sent_at": "2026-07-10T10:00:00Z", "folder_id": "f1"}


def make_contact(store, cid, email):
    store.upsert_contact({"contact_id": cid, "natural_key": cid,
                          "campaign": "rome-2026", "email": email}, now_iso())


def scan(store, m, **kw):
    kw.setdefault("now", NOW)
    kw.setdefault("sleep", lambda s: None)
    return run_scan(store, m, **kw)


# -- folder-cache diffing ------------------------------------------------------

def test_scan_skips_unchanged_folder_counts(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        m = FakeMailer()
        m.folders[DIRK_SMTP] = [folder("f1", count=5)]
        s.upsert_folder_cache(DIRK_SMTP, "f1", "Sent Items", 5, now_iso())
        rep = scan(s, m)
        assert m.pulled == []                     # unchanged count: no pull
        assert rep["folders_scanned"] == 0
        # count moved -> the folder is scanned and the cache row refreshed
        m2 = FakeMailer()
        m2.folders[DIRK_SMTP] = [folder("f1", count=6)]
        rep2 = scan(s, m2)
        assert [p[1] for p in m2.pulled] == ["f1"]
        assert rep2["folders_scanned"] == 1
        assert s.get_folder_cache(DIRK_SMTP)["f1"]["total_item_count"] == 6


def test_scan_full_ignores_folder_cache_skip_only_respects_skip_flag(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        m = FakeMailer()
        m.folders[DIRK_SMTP] = [folder("f1", count=5),
                                folder("f2", "Junk", 9)]
        s.upsert_folder_cache(DIRK_SMTP, "f1", "Sent Items", 5, now_iso())
        s.upsert_folder_cache(DIRK_SMTP, "f2", "Junk", 9, now_iso())
        s.conn.execute("UPDATE folder_cache SET skip = 1 WHERE folder_id = 'f2'")
        s.conn.commit()
        rep = scan(s, m, full=True)
        # unchanged count is scanned anyway on a full run...
        assert [p[1] for p in m.pulled] == ["f1"]
        assert rep["full"] is True
        assert rep["window_since"] == truth_scan.FULL_SCAN_SINCE
        assert m.pulled[0][2] == truth_scan.FULL_SCAN_SINCE
        # ...but skip=1 is respected even then, and its cache row untouched
        assert s.get_folder_cache(DIRK_SMTP)["f2"]["skip"] == 1


# -- retry + failure surface ---------------------------------------------------

def test_scan_records_failed_folders_and_alert(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        m = FakeMailer()
        m.folders[DIRK_SMTP] = [folder("f1")]
        m.fail["f1"] = GraphRetryError(429, "HTTP 429: throttled")
        naps: list[int] = []
        rep = run_scan(s, m, now=NOW, sleep=naps.append)
        assert naps == [5, 15, 45]                # x3 retries, backoff
        assert len(m.pulled) == 4                 # initial + 3 retries
        assert rep["folders_scanned"] == 0
        assert len(rep["folders_failed"]) == 1
        assert rep["folders_failed"][0]["path"] == "Sent Items"
        assert "429" in rep["folders_failed"][0]["error"]
        alert = json.loads(s.get_state("truth_scan_alert"))
        assert "1 folder(s) failed" in alert["alert"]
        # the failed folder's cache row was NOT advanced: next run retries it
        assert s.get_folder_cache(DIRK_SMTP) == {}


# -- ingest behavior -----------------------------------------------------------

def test_scan_feeds_ingest_dedupes_existing_events(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        make_contact(s, "c1", "lead@acme.com")
        # live capture already ingested this exact message (same imid)
        res = ingest_event(s, {
            "email": "lead@acme.com", "type": "sent", "direction": "outbound",
            "channel": "email", "occurred_at": "2026-07-10T10:00:00Z",
            "subject": "Rome intro", "detail": "auto: sent mail",
            "source": "graph-auto", "internet_message_id": "<m1@brisken>"})
        assert res["inserted"]
        m = FakeMailer()
        m.folders[DIRK_SMTP] = [folder("f1")]
        m.messages["f1"] = [msg("<m1@brisken>", "lead@acme.com")]
        rep = scan(s, m)
        assert rep["deduped"] == 1 and rep["inserted"] == 0
        assert s.count_events() == 1              # no new row


def test_scan_unknown_address_lands_unmatched(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        m = FakeMailer()
        m.folders[DIRK_SMTP] = [folder("f1")]
        m.messages["f1"] = [msg("<u1@brisken>", "stranger@new.com")]
        rep = scan(s, m)
        assert rep["queued"] == 1 and rep["inserted"] == 0
        rows = s.list_unmatched()
        assert len(rows) == 1 and rows[0]["email"] == "stranger@new.com"
        assert s.count_contacts() == 0            # never auto-creates


# -- run log + state keys ------------------------------------------------------

def test_scan_writes_truth_run_and_heartbeat(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        make_contact(s, "c1", "lead@acme.com")
        m = FakeMailer()
        m.folders[DIRK_SMTP] = [folder("f1")]
        m.messages["f1"] = [msg("<m1@brisken>", "lead@acme.com")]
        rep = scan(s, m)
        assert rep["inserted"] == 1
        run = s.conn.execute("SELECT * FROM truth_runs").fetchone()
        assert run["kind"] == "deep-scan"
        assert run["events_added"] == 1
        assert run["folders_scanned"] == 1
        assert json.loads(run["folders_failed"]) == []
        assert run["started_at"] and run["finished_at"]
        assert json.loads(run["report"])["corpus_messages"] == 1
        hb = json.loads(s.get_state("truth_scan_heartbeat"))
        assert hb["ts"] and hb["counts"]["inserted"] == 1
        # a recovered event means live capture missed it -> alert set
        alert = json.loads(s.get_state("truth_scan_alert"))
        assert "1 event(s) live capture missed" in alert["alert"]
        # the folder cache row carries the hit stamp
        row = s.get_folder_cache(DIRK_SMTP)["f1"]
        assert row["total_item_count"] == 3 and row["last_hit"]


def test_scan_clean_run_clears_alert(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.set_state("truth_scan_alert",
                    json.dumps({"alert": "stale"}), now_iso())
        m = FakeMailer()
        m.folders[DIRK_SMTP] = [folder("f1")]     # pull yields nothing new
        rep = scan(s, m)
        assert rep["folders_failed"] == [] and rep["inserted"] == 0
        assert s.get_state("truth_scan_alert") is None


def test_every_7th_run_is_full(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.set_state("truth_scan_run_count", "6", now_iso())
        m = FakeMailer()
        m.folders[DIRK_SMTP] = [folder("f1", count=5)]
        s.upsert_folder_cache(DIRK_SMTP, "f1", "Sent Items", 5, now_iso())
        rep = scan(s, m)                          # run 7
        assert rep["full"] is True and rep["run_count"] == 7
        assert [p[1] for p in m.pulled] == ["f1"]  # cache diff ignored
        assert m.pulled[0][2] == truth_scan.FULL_SCAN_SINCE
        assert s.get_state("truth_scan_run_count") == "7"
        # run 8 is windowed again: unchanged count skips
        m2 = FakeMailer()
        m2.folders[DIRK_SMTP] = [folder("f1", count=5)]
        rep2 = scan(s, m2)
        assert rep2["full"] is False and m2.pulled == []
        assert s.get_state("truth_scan_run_count") == "8"


def test_dry_run_pulls_but_writes_nothing(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        m = FakeMailer()
        m.folders[DIRK_SMTP] = [folder("f1")]
        m.messages["f1"] = [msg("<m1@brisken>", "stranger@new.com")]
        rep = scan(s, m, dry_run=True)
        assert m.pulled                           # it DID pull + diff
        assert rep["would_ingest"] == 1
        assert s.count_events() == 0 and s.list_unmatched() == []
        assert s.conn.execute(
            "SELECT COUNT(*) FROM truth_runs").fetchone()[0] == 0
        assert s.get_state("truth_scan_run_count") is None
        assert s.get_state("truth_scan_heartbeat") is None
        assert s.get_folder_cache(DIRK_SMTP) == {}


# -- scheduler guard -----------------------------------------------------------

def test_scheduler_guarded_without_creds(tmp_path, monkeypatch):
    """App startup without Graph creds logs a skip and never builds a
    mailer or scans (mirrors the sync-scheduler guard)."""
    from fastapi.testclient import TestClient

    import lead_desk.truth_scan as ts
    import lead_desk.web.app as webapp

    monkeypatch.delenv("LEAD_DESK_TRUTH_SCAN_DISABLED", raising=False)
    monkeypatch.delenv("LEAD_DESK_TRUTH_SCAN_INTERVAL", raising=False)
    monkeypatch.setattr(webapp, "have_creds", lambda: False)
    called = []
    monkeypatch.setattr(ts, "run_scan", lambda *a, **k: called.append(1))
    with TestClient(webapp.create_app(tmp_path / "d")) as client:
        assert client.get("/healthz").status_code == 200
    assert called == []


# -- GraphMailer folder-walk primitives ---------------------------------------

class _Resp:
    def __init__(self, status_code, body=None, text=""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text

    def json(self):
        return self._body


class FolderHttp:
    """Requests-shaped fake for the /mailFolders tree + per-folder pulls."""

    def __init__(self):
        self.children: dict[str | None, list[dict]] = {}
        self.folder_messages: dict[str, list[dict]] = {}
        self.pull_status = 200
        self.calls: list[str] = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        if "/childFolders?" in url:
            fid = url.split("/mailFolders/", 1)[1].split("/childFolders", 1)[0]
            return _Resp(200, {"value": self.children.get(fid, [])})
        if "/messages?" in url:
            if self.pull_status != 200:
                return _Resp(self.pull_status, {}, "throttled")
            fid = url.split("/mailFolders/", 1)[1].split("/messages", 1)[0]
            return _Resp(200, {"value": self.folder_messages.get(fid, [])})
        if url.split("?", 1)[0].endswith("/mailFolders"):
            return _Resp(200, {"value": self.children.get(None, [])})
        return _Resp(404, {}, "no route")


def test_list_mail_folders_walks_tree_and_skips_empty():
    http = FolderHttp()
    http.children[None] = [
        {"id": "r1", "displayName": "Inbox", "totalItemCount": 4,
         "childFolderCount": 1},
        {"id": "r2", "displayName": "Empty", "totalItemCount": 0,
         "childFolderCount": 0},
    ]
    http.children["r1"] = [
        {"id": "s1", "displayName": "Adidas", "totalItemCount": 2,
         "childFolderCount": 0},
    ]
    m = GraphMailer(token="tok", http=http)
    out = m.list_mail_folders(DIRK_SMTP)
    assert [(f["id"], f["path"], f["total_item_count"]) for f in out] == \
        [("r1", "Inbox", 4), ("s1", "Inbox / Adidas", 2)]
    with pytest.raises(NotAllowlisted):
        m.list_mail_folders("other@evil.com")


def test_pull_folder_outbound_maps_filters_and_raises_retry_on_429():
    http = FolderHttp()
    http.folder_messages["f1"] = [{
        "id": "g1", "internetMessageId": "<m1>",
        "toRecipients": [{"emailAddress": {"address": "A@x.com"}}],
        "ccRecipients": [{"emailAddress": {"address": "b@y.com"}}],
        "subject": "Hi", "sentDateTime": "2026-07-10T10:00:00Z"}]
    m = GraphMailer(token="tok", http=http)
    out = m.pull_folder_outbound(DIRK_SMTP, "f1", "2026-07-01T00:00:00Z")
    assert out == [{"id": "g1", "internet_message_id": "<m1>",
                    "to": ["a@x.com"], "cc": ["b@y.com"], "subject": "Hi",
                    "sent_at": "2026-07-10T10:00:00Z", "folder_id": "f1"}]
    url = http.calls[-1]
    assert f"from/emailAddress/address eq '{DIRK_SMTP}'" in url
    assert "sentDateTime ge 2026-07-01T00:00:00Z" in url
    assert "isDraft eq false" in url
    http.pull_status = 429
    with pytest.raises(GraphRetryError):
        m.pull_folder_outbound(DIRK_SMTP, "f1", "2026-07-01T00:00:00Z")
    with pytest.raises(NotAllowlisted):
        m.pull_folder_outbound("other@evil.com", "f1", "2026-07-01T00:00:00Z")
