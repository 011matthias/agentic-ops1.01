"""uploads.import_upload: CSV/xlsx parsing, global-contact adoption,
idempotent enrollment, manual degrees from the file, unmapped/skip reporting."""
from __future__ import annotations

import io

from lead_desk.identity import contact_id_for, natural_key
from lead_desk.web import uploads
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore


# -- helpers -------------------------------------------------------------------

def make_contact(store, cid_suffix, email=None, **fields):
    """Upsert a contact the same way the importer keys it (email natural key)."""
    nk = natural_key(email, fields.get("first_name"), fields.get("last_name"),
                     fields.get("company"), None if email else int(cid_suffix))
    cid = contact_id_for(nk)
    data = {"contact_id": cid, "natural_key": nk, "campaign": "rome-2026",
            "email": email}
    data.update(fields)
    store.upsert_contact(data, now_iso())
    return cid


def make_campaign(store, campaign_id="camp-1", name="Camp 1"):
    store.create_campaign(campaign_id, name, now_iso())
    return campaign_id


def xlsx_bytes(headers, rows):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


CSV_ALIASED = (
    "E-Mail,First Name,Company Name\n"
    "anna@acme.com,Anna,Acme GmbH\n"
    "bruno@beta.io,Bruno,Beta AG\n"
).encode("utf-8")


def _assert_two_row_import(store, campaign_id, report):
    assert report["ok"] is True
    assert report["rows"] == 2
    assert report["new_contacts"] == 2
    assert report["adopted_existing"] == 0
    assert report["enrolled"] == 2
    assert report["already_enrolled"] == 0
    assert report["unmapped_columns"] == []
    assert report["skipped"] == []
    cid = contact_id_for("anna@acme.com")
    contact = store.get_contact(cid)
    assert contact is not None
    assert contact["first_name"] == "Anna"
    assert contact["company"] == "Acme GmbH"
    assert contact["email"] == "anna@acme.com"
    enr = store.find_enrollment(cid, campaign_id)
    assert enr is not None
    assert enr["approved_at"] is None  # enrollment is inert until approval


# -- 1. CSV with header aliases --------------------------------------------------

def test_csv_upload_aliases_create_and_enroll(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        camp = make_campaign(s)
        report = uploads.import_upload(s, camp, "leads.csv", CSV_ALIASED, "tester")
        _assert_two_row_import(s, camp, report)


def test_upload_unknown_campaign_rejected(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        report = uploads.import_upload(s, "nope", "leads.csv", CSV_ALIASED, "tester")
        assert report == {"ok": False, "error": "unknown campaign"}


# -- 2. XLSX ----------------------------------------------------------------------

def test_xlsx_upload_same_result(tmp_path):
    data = xlsx_bytes(
        ["E-Mail", "First Name", "Company Name"],
        [["anna@acme.com", "Anna", "Acme GmbH"],
         ["bruno@beta.io", "Bruno", "Beta AG"]],
    )
    with ContactStore(tmp_path / "db.sqlite") as s:
        camp = make_campaign(s)
        report = uploads.import_upload(s, camp, "leads.xlsx", data, "tester")
        _assert_two_row_import(s, camp, report)


# -- 3. Existing global contact is adopted, never duplicated ----------------------

def test_existing_contact_is_adopted_not_duplicated(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, "1", email="prior@acme.com",
                           first_name="Pia", last_name="Prior", company="Prior AG")
        s.add_event(contact_id=cid, ts="2026-07-10T09:00:00+00:00",
                    channel="email", direction="outbound", type="sent",
                    detail="pre-existing history", now=now_iso())
        assert s.count_events() == 1

        camp = make_campaign(s)
        csv_data = (
            "E-Mail,First Name,Title\n"
            "prior@acme.com,Pia-Maria,CFO\n"
        ).encode("utf-8")
        report = uploads.import_upload(s, camp, "leads.csv", csv_data, "tester")

        assert report["ok"] is True
        assert report["adopted_existing"] == 1
        assert report["new_contacts"] == 0
        assert report["enrolled"] == 1
        assert s.count_contacts() == 1  # same contact_id, no duplicate row

        contact = s.get_contact(cid)
        assert contact is not None
        assert contact["campaign"] == "rome-2026"       # legacy tag kept
        assert contact["first_name"] == "Pia-Maria"     # non-empty field refreshed
        assert contact["last_name"] == "Prior"          # absent field untouched
        assert contact["job_title"] == "CFO"            # alias 'Title' mapped

        events = s.get_events(cid)                      # prior history intact
        assert len(events) == 1
        assert events[0]["ts"] == "2026-07-10T09:00:00+00:00"
        assert s.find_enrollment(cid, camp) is not None


# -- 4. Re-upload is idempotent ----------------------------------------------------

def test_reupload_same_file_is_idempotent(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        camp = make_campaign(s)
        first = uploads.import_upload(s, camp, "leads.csv", CSV_ALIASED, "tester")
        assert first["enrolled"] == 2

        second = uploads.import_upload(s, camp, "leads.csv", CSV_ALIASED, "tester")
        assert second["ok"] is True
        assert second["new_contacts"] == 0
        assert second["adopted_existing"] == 2
        assert second["enrolled"] == 0
        assert second["already_enrolled"] == 2
        assert s.count_contacts() == 2
        n_enr = s.conn.execute(
            "SELECT COUNT(*) FROM enrollments WHERE campaign_id = ?", (camp,)
        ).fetchone()[0]
        assert n_enr == 2


# -- 5. degree column -> manual degree on the enrollment ----------------------------

def test_degree_column_sets_manual_degree(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        camp = make_campaign(s)
        csv_data = (
            "E-Mail,First Name,Warmness\n"       # 'Warmness' aliases to degree
            "wanda@acme.com,Wanda,Warm\n"
            "carl@beta.io,Carl,\n"               # no degree given
        ).encode("utf-8")
        report = uploads.import_upload(s, camp, "leads.csv", csv_data, "tester")

        assert report["ok"] is True
        assert report["manual_degrees_from_file"] == 1
        enr = s.find_enrollment(contact_id_for("wanda@acme.com"), camp)
        assert enr["degree"] == "warm"           # lowercased
        assert enr["degree_source"] == "manual"
        assert "leads.csv" in enr["degree_rule"]
        other = s.find_enrollment(contact_id_for("carl@beta.io"), camp)
        assert other["degree"] is None
        assert other["degree_source"] == "rules"


# -- 6. Unmapped columns reported; rows without identity skipped --------------------

def test_unmapped_columns_and_skipped_rows(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        camp = make_campaign(s)
        csv_data = (
            "E-Mail,First Name,Favorite Color\n"
            "anna@acme.com,Anna,blue\n"
            ",,green\n"                          # no email, no name, no company
        ).encode("utf-8")
        report = uploads.import_upload(s, camp, "leads.csv", csv_data, "tester")

        assert report["ok"] is True
        assert report["unmapped_columns"] == ["favorite_color"]
        assert report["rows"] == 2
        assert report["new_contacts"] == 1
        assert report["enrolled"] == 1
        assert report["skipped"] == ["row 3: no email and no name/company"]
        assert s.count_contacts() == 1


def test_upload_with_no_data_rows_errors(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        camp = make_campaign(s)
        report = uploads.import_upload(
            s, camp, "leads.csv", b"E-Mail,First Name\n", "tester")
        assert report == {"ok": False, "error": "no data rows found"}
