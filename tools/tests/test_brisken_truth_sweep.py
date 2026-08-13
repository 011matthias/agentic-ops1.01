"""Unit tests for the pure capture-adequacy diff logic in
tools/brisken-truth-sweep.py (--verify-live-capture).

The Graph transport and the live Lead Desk are deliberately not exercised
(same policy as test_brisken_outreach_reconcile.py): the window filter, the
internal-only exclusion, the imid dedup, and the three-source DB presence
map are the parts a regression would silently break.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "brisken_truth_sweep", TOOLS / "brisken-truth-sweep.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["brisken_truth_sweep"] = mod
    spec.loader.exec_module(mod)
    return mod


MOD = _load()

DIRK = "dirk.neumann@brisken.com"


def msg(imid, to, sent, cc=(), subject="s", folder="Sent Items",
        mid=None):
    return {"id": mid or imid, "imid": imid, "from": DIRK,
            "to": list(to), "cc": list(cc), "bcc": [],
            "subject": subject, "sent": sent, "received": sent,
            "is_draft": False, "kind": "outbound", "folder": folder,
            "mailbox": DIRK}


# ---- window_outbound ---------------------------------------------------------

def test_window_bounds_are_date_inclusive():
    corpus = {"outbound": [
        msg("<a@x>", ["p@ext.com"], "2026-07-18T00:00:00Z"),
        msg("<b@x>", ["p@ext.com"], "2026-08-01T23:59:59Z"),
        msg("<c@x>", ["p@ext.com"], "2026-07-17T23:59:59Z"),
        msg("<d@x>", ["p@ext.com"], "2026-08-02T00:00:00Z"),
    ]}
    rows = MOD.window_outbound(corpus, "2026-07-18", "2026-08-01")
    assert {m["imid"] for m in rows} == {"<a@x>", "<b@x>"}


def test_internal_only_mail_is_not_a_gap_candidate():
    corpus = {"outbound": [
        msg("<i@x>", ["matthias.silva@brisken.com"], "2026-07-20T09:00:00Z"),
        # external only via BCC (the Zoho dropbox): capture builds payloads
        # from to+cc, so this is invisible to the Lead Desk too
        {**msg("<j@x>", ["dirk.neumann@brisken.com"],
               "2026-07-20T10:00:00Z"),
         "bcc": ["s9hitl_pv69mu@mails4.zohocrm.com"]},
        msg("<k@x>", ["matthias.silva@brisken.com"], "2026-07-20T11:00:00Z",
            cc=["p@ext.com"]),
    ]}
    rows = MOD.window_outbound(corpus, "2026-07-18", "2026-08-01")
    assert [m["imid"] for m in rows] == ["<k@x>"]
    assert rows[0]["external"] == ["p@ext.com"]


def test_folder_copies_dedupe_by_imid():
    corpus = {"outbound": [
        msg("<a@x>", ["p@ext.com"], "2026-07-20T09:00:00Z", mid="id1"),
        msg("<a@x>", ["p@ext.com"], "2026-07-20T09:00:00Z", mid="id2",
            folder="Projects / Rome"),
    ]}
    assert len(MOD.window_outbound(corpus, "2026-07-18", "2026-08-01")) == 1


# ---- diff_capture ------------------------------------------------------------

def test_diff_splits_present_by_source_and_lists_missing():
    rows = MOD.window_outbound({"outbound": [
        msg("<a@x>", ["p@ext.com"], "2026-07-20T09:00:00Z"),
        msg("<b@x>", ["q@ext.com"], "2026-07-21T09:00:00Z"),
        msg("<c@x>", ["r@ext.com"], "2026-07-22T09:00:00Z",
            subject="lost one", folder="Sent Items"),
    ]}, "2026-07-18", "2026-08-01")
    rep = MOD.diff_capture(rows, {"<a@x>": "events",
                                  "<b@x>": "send_attempts"})
    assert (rep["total"], rep["present"]) == (3, 2)
    assert rep["present_by_source"] == {"events": 1, "send_attempts": 1}
    assert len(rep["missing"]) == 1
    m = rep["missing"][0]
    assert m["imid"] == "<c@x>"
    assert m["to"] == ["r@ext.com"]
    assert m["subject"] == "lost one"
    assert m["folder"] == "Sent Items"


def test_diff_all_present_is_adequate():
    rows = [{"imid": "<a@x>", "external": ["p@ext.com"]}]
    rep = MOD.diff_capture(rows, {"<a@x>": "events"})
    assert rep["missing"] == [] and rep["present"] == 1


# ---- db_imid_sources (local sqlite copy, three sources) ----------------------

def _mini_db(path):
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE outreach_events (ext_key TEXT, direction TEXT);
        CREATE TABLE send_attempts (internet_message_id TEXT);
        CREATE TABLE unmatched_events (payload TEXT);
    """)
    con.executemany("INSERT INTO outreach_events VALUES (?, ?)", [
        ("<cap@x>", "outbound"),
        ("<in@x>", "inbound"),           # inbound: not a send
        ("cadence:7:1", "outbound"),     # worker event: cadence key, no imid
        (None, "outbound"),
    ])
    con.execute("INSERT INTO send_attempts VALUES ('<wrk@x>')")
    con.executemany("INSERT INTO unmatched_events VALUES (?)", [
        (json.dumps({"internet_message_id": "<park@x>"}),),
        (json.dumps({"email": "no-imid@x.com"}),),
        ("not json",),
    ])
    con.commit()
    con.close()


def test_db_imid_sources_reads_all_three_tables(tmp_path):
    db = tmp_path / "copy.sqlite"
    _mini_db(db)
    out = MOD.db_imid_sources(db)
    assert out["<cap@x>"] == "events"
    assert out["<wrk@x>"] == "send_attempts"
    assert out["<park@x>"] == "unmatched"
    assert "<in@x>" not in out            # inbound ext_keys are not sends
    assert None not in out
