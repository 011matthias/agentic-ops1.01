"""P5: ingest/sync robustness - subject hardening, CSV collapse + degree
validation, the optimistic lock, and freshness signals."""
from __future__ import annotations

import pytest

from lead_desk.ground import _base_subject
from lead_desk.web.service import (
    StaleWriteError, apply_fields, build_board, now_iso)
from lead_desk.web.store import ContactStore
from lead_desk.web.uploads import import_upload

NOW = "2026-07-16T00:00:00+00:00"


# --- #6 subject normalisation -------------------------------------------------

def test_base_subject_strips_all_prefixes_and_collapses_ws():
    assert _base_subject("Re: Re: AW:  Worth   fifteen minutes") == "worth fifteen minutes"
    assert _base_subject("WG: FWD: Hello") == "hello"
    assert _base_subject("Re[2]: status") == "status"
    assert _base_subject("plain subject") == "plain subject"


# --- #4 CSV collapse + degree validation --------------------------------------

def test_upload_reports_collapse_and_bad_degree(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.create_campaign("c", "C", NOW, status="draft")
        csv = (b"email,first name,company,organisation,warmness\n"
               b"a@x.com,Ann,Acme,AcmeOrg,hot\n")   # company+organisation collapse; 'hot' invalid
        rep = import_upload(s, "c", "leads.csv", csv, "u")
        assert rep["ok"]
        assert "company" in rep["collapsed_columns"]
        assert rep["rejected_degrees"]                 # 'hot' not a real degree
        assert s.get_contact_by_key("a@x.com")["company"] == "Acme"  # first non-empty won


# --- #5 optimistic lock -------------------------------------------------------

def _seed(store):
    store.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "email": "a@x.com", "company": "Old"}, now=NOW)


def test_apply_fields_rejects_stale_write(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        _seed(s)
        current = s.get_contact("c1")["updated_at"]
        # a concurrent writer moves updated_at
        apply_fields(s, "c1", {"company": "Newer"}, "other")
        with pytest.raises(StaleWriteError):
            apply_fields(s, "c1", {"company": "Mine"}, "me", expected_updated_at=current)
        # the stale write did not land
        assert s.get_contact("c1")["company"] == "Newer"


def test_apply_fields_accepts_matching_updated_at(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        _seed(s)
        current = s.get_contact("c1")["updated_at"]
        apply_fields(s, "c1", {"company": "Fresh"}, "me", expected_updated_at=current)
        assert s.get_contact("c1")["company"] == "Fresh"


# --- #2 freshness signals -----------------------------------------------------

def test_build_board_exposes_freshness(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.create_campaign("rome-2026", "Rome", NOW, status="done")
        s.set_state("last_sync_ok", "2026-07-16T08:00:00+00:00", NOW)
        s.set_state("last_sync_diffs", "3", NOW)
        v = build_board(s, {})
        assert v["last_sync_ok"].startswith("2026-07-16")
        assert v["last_sync_diffs"] == 3
