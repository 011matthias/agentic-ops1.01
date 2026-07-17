"""Sender orchestration with fake COM + fake API: the crash matrix."""
import pytest

from lead_desk.worker import sender
from lead_desk.worker.journal import Journal


class FakeApi:
    def __init__(self, fail_result: bool = False):
        self.results: list[dict] = []
        self.fail_result = fail_result

    def result(self, payload):
        if self.fail_result:
            from lead_desk.worker.api import ApiUnavailable
            raise ApiUnavailable("down")
        self.results.append(payload)
        return {"ok": True}


def make_send(**kw):
    subject, body = kw.pop("subject", "Hi {x}"), kw.pop("body", "Body text")
    base = {
        "attempt_key": "cadence:1:1", "lease_id": "L1",
        "send_mode": "auto-matthias", "to": "jane@acme.com",
        "cc": ["dirk.neumann@brisken.com"], "bcc": ["drop@zoho"],
        "subject": subject, "body": body,
        "body_hash": sender.body_hash(subject, body),
        "throttle_seconds": 0, "jitter_seconds": 0,
    }
    base.update(kw)
    return base


ACCOUNTS = {"auto": object(), "dirk": object(), "self_smtp": "me@brisken.com"}


@pytest.fixture
def journal(tmp_path):
    return Journal(tmp_path / "journal.jsonl")


def test_body_hash_mismatch_nacks_config(journal, monkeypatch):
    api = FakeApi()
    send = make_send(body_hash="deadbeef")
    called = []
    monkeypatch.setattr(sender.com_mail, "send_auto",
                        lambda *a, **k: called.append(1))
    out = sender.execute_one(None, ACCOUNTS, send, journal, api)
    assert out == "hash_mismatch"
    assert called == []  # never reached COM
    assert api.results[0]["error_class"] == "config"


def test_auto_send_happy_path_acks_with_evidence(journal, monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(sender.com_mail, "send_auto", lambda ol, acct, s: None)
    monkeypatch.setattr(sender.com_mail, "readback_sent",
                        lambda acct, to, subj, since: {
                            "imid": "<im1>", "entry_id": "E1",
                            "ts": "2026-07-15T09:00:00+02:00"})
    out = sender.execute_one(None, ACCOUNTS, make_send(), journal, api)
    assert out == "sent"
    ack = api.results[0]
    assert ack["status"] == "sent" and ack["internet_message_id"] == "<im1>"
    assert journal.pending() == {}  # acked = terminal


def test_readback_miss_still_acks_deterministically(journal, monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(sender.com_mail, "send_auto", lambda ol, acct, s: None)
    monkeypatch.setattr(sender.com_mail, "readback_sent",
                        lambda *a, **k: None)
    out = sender.execute_one(None, ACCOUNTS, make_send(), journal, api)
    assert out == "sent"
    assert api.results[0]["internet_message_id"] is None  # imid is enrichment only


def test_unresolved_recipient_parks_no_retry(journal, monkeypatch):
    api = FakeApi()

    def boom(ol, acct, s):
        raise sender.com_mail.UnresolvedRecipients(["Jane Doe"])
    monkeypatch.setattr(sender.com_mail, "send_auto", boom)
    out = sender.execute_one(None, ACCOUNTS, make_send(), journal, api)
    assert out == "unresolved"
    assert api.results[0]["error_class"] == "resolve"


def test_com_error_after_issue_never_nacks(journal, monkeypatch):
    """The ambiguous window: .Send() may have fired. A nack would re-queue =
    possible double-send, so the journal must stay pending instead."""
    api = FakeApi()

    def boom(ol, acct, s):
        raise RuntimeError("RPC server unavailable")
    monkeypatch.setattr(sender.com_mail, "send_auto", boom)
    out = sender.execute_one(None, ACCOUNTS, make_send(), journal, api)
    assert out == "com_error"
    assert api.results == []  # nothing told the server anything
    assert journal.pending()["cadence:1:1"]["state"] == "com_error"


def test_ack_failure_leaves_replayable_journal(journal, monkeypatch):
    api = FakeApi(fail_result=True)
    monkeypatch.setattr(sender.com_mail, "send_auto", lambda ol, acct, s: None)
    monkeypatch.setattr(sender.com_mail, "readback_sent", lambda *a, **k: None)
    out = sender.execute_one(None, ACCOUNTS, make_send(), journal, api)
    assert out == "ack_pending"
    entry = journal.pending()["cadence:1:1"]
    assert entry["state"] == "ack_failed"
    assert entry["ack"]["status"] == "sent"


def test_draft_dirk_mode_acks_drafted_without_send(journal, monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(sender.com_mail, "load_dirk_draft",
                        lambda ol, acct, s: {"duplicate": False, "entry_id": "D1"})
    sent_called = []
    monkeypatch.setattr(sender.com_mail, "send_auto",
                        lambda *a, **k: sent_called.append(1))
    out = sender.execute_one(None, ACCOUNTS,
                             make_send(send_mode="draft-dirk"), journal, api)
    assert out == "drafted"
    assert sent_called == []  # nothing auto-sent in Dirk's name
    assert api.results[0]["status"] == "drafted"


# -- replay_pending: the crash matrix ------------------------------------------

def test_replay_claimed_requeues_transient(journal, monkeypatch):
    api = FakeApi()
    journal.write("cadence:2:1", "claimed", to="a@x.com", lease_id="L2")
    out = sender.replay_pending(None, ACCOUNTS, journal, api, alerts=[])
    assert out["requeued"] == 1
    assert api.results[0]["error_class"] == "transient"
    assert journal.pending() == {}


def test_replay_com_issued_with_evidence_acks_sent(journal, monkeypatch):
    api = FakeApi()
    journal.write("cadence:3:1", "com_issued", to="a@x.com", subject="Hello",
                  lease_id="L3")
    monkeypatch.setattr(sender.com_mail, "search_sent_for",
                        lambda acct, to, subj, since: {
                            "imid": "<found>", "ts": "2026-07-15T09:00:00+02:00"})
    out = sender.replay_pending(None, ACCOUNTS, journal, api, alerts=[])
    assert out["replayed"] == 1
    assert api.results[0]["status"] == "sent"
    assert api.results[0]["internet_message_id"] == "<found>"


def test_replay_com_issued_without_evidence_alerts_never_resends(journal, monkeypatch):
    api = FakeApi()
    alerts: list[str] = []
    journal.write("cadence:4:1", "com_issued", to="a@x.com", subject="Hello",
                  lease_id="L4")
    monkeypatch.setattr(sender.com_mail, "search_sent_for",
                        lambda *a, **k: None)
    out = sender.replay_pending(None, ACCOUNTS, journal, api, alerts=alerts)
    assert out["ambiguous"] == 1
    assert api.results == []  # neither acked nor nacked: human decides
    assert alerts and "NOT resending" in alerts[0]


def test_replay_com_sent_delivers_lost_ack(journal):
    api = FakeApi()
    journal.write("cadence:5:1", "com_sent", lease_id="L5")
    out = sender.replay_pending(None, ACCOUNTS, journal, api, alerts=[])
    assert out["replayed"] == 1
    assert api.results[0]["attempt_key"] == "cadence:5:1"
    assert api.results[0]["status"] == "sent"
