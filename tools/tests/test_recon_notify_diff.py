"""Unit tests for the pure diff logic in tools/brisken-recon-notify.py.

The transport half (Graph token, sendMail, app login) is deliberately not
exercised here: it needs live credentials and a live app. The diff is the
part a regression would silently break (double-sends or missed uploads).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "recon_notify", TOOLS / "brisken-recon-notify.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["recon_notify"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_empty_state_announces_everything():
    mod = _load()
    remote = {
        "intakes": [{"intake_id": "i1", "label": "Corp 2838"}],
        "published_runs": [{"run_id": "r1", "label": "Corp 2838"}],
    }
    new_intakes, new_pubs = mod.diff_state({}, remote)
    assert [i["intake_id"] for i in new_intakes] == ["i1"]
    assert [r["run_id"] for r in new_pubs] == ["r1"]


def test_seen_items_not_reannounced():
    mod = _load()
    state = {"seen_intakes": ["i1"], "seen_published": ["r1"]}
    remote = {
        "intakes": [
            {"intake_id": "i1", "label": "old"},
            {"intake_id": "i2", "label": "new"},
        ],
        "published_runs": [{"run_id": "r1", "label": "old"}],
    }
    new_intakes, new_pubs = mod.diff_state(state, remote)
    assert [i["intake_id"] for i in new_intakes] == ["i2"]
    assert new_pubs == []


def test_apply_to_state_marks_all_visible():
    mod = _load()
    remote = {
        "intakes": [{"intake_id": "i1"}, {"intake_id": "i2"}],
        "published_runs": [{"run_id": "r9"}],
    }
    state = mod.apply_to_state({"seen_intakes": ["gone"]}, remote)
    assert state == {"seen_intakes": ["i1", "i2"], "seen_published": ["r9"]}
    # idempotent second pass announces nothing
    assert mod.diff_state(state, remote) == ([], [])


def test_sender_is_hard_allowlisted():
    mod = _load()
    assert mod.SENDER in mod.ALLOWED_SENDERS
    assert mod.ALLOWED_SENDERS == frozenset(
        {"matthias.silva@brisken.com", "dirk.neumann@brisken.com"}
    )
