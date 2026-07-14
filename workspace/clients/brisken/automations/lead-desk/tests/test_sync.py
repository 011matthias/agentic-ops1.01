"""The continuous sheet -> DB sync is non-destructive: it refreshes sheet-owned
identity/classification but never clobbers the app's pipeline fields on an
existing contact, and imports brand-new contacts in full."""
from __future__ import annotations

import openpyxl

from lead_desk.migrate import import_workbook
from lead_desk.web.store import ContactStore

NOW = "2026-07-14T00:00:00+00:00"
HEADER = [
    "first_name", "last_name", "company", "job_title", "email", "alt_email",
    "phone", "country", "linkedin_url", "Tier", "Tier_reason", "lead_type",
    "stop", "email outreach_status", "linkedin_status", "source",
    "in_our_booth", "scanned_at_booth", "if_we_know_them", "brisken_customer",
    "attendee_type", "sponsor_opt_in", "no_show", "fob_encoded",
    "booth_registered_at", "crm_owner", "crm_last_activity",
    "next_step", "last_outreach", "last_reply", "outreach_log", "dirk_notes",
]


def _make_xlsx(path, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Master contacts"
    ws.append(HEADER)
    for r in rows:
        ws.append([r.get(h, "") for h in HEADER])
    wb.save(path)


def test_resync_preserves_app_fields_and_imports_new(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as db:
        # An existing contact carrying app-owned pipeline work.
        db.upsert_contact({
            "contact_id": "x", "natural_key": "ann@x.com",
            "first_name": "Ann", "last_name": "Lee", "company": "OldCo",
            "email": "ann@x.com", "tier": "T3",
            "next_step": "call Monday", "bant_need": 1,
        }, now=NOW)

        xlsx = tmp_path / "m.xlsx"
        _make_xlsx(xlsx, [
            {"first_name": "Ann", "last_name": "Lee", "company": "NewCo",
             "email": "ann@x.com", "Tier": "T1", "next_step": "SHEET step"},
            {"first_name": "Bob", "last_name": "New", "company": "Fresh",
             "email": "bob@f.com", "Tier": "T2", "next_step": "import me"},
        ])
        import_workbook(db, xlsx, "rome-2026", {}, preserve_app_fields=True)

        ann = db.get_contact("x")
        assert ann["company"] == "NewCo"          # sheet refreshed identity
        assert ann["tier"] == "T1"                # sheet refreshed classification
        assert ann["next_step"] == "call Monday"  # app-owned PRESERVED
        assert ann["bant_need"] == 1              # app-owned PRESERVED

        bob = db.find_by_email("bob@f.com")
        assert bob is not None
        assert bob["next_step"] == "import me"     # new contact imported in full


def test_migrate_mode_still_takes_sheet_next_step(tmp_path):
    """Without preserve_app_fields (the one-time migrate), the sheet wins."""
    with ContactStore(tmp_path / "t.sqlite") as db:
        db.upsert_contact({
            "contact_id": "x", "natural_key": "ann@x.com",
            "first_name": "Ann", "email": "ann@x.com", "next_step": "old",
        }, now=NOW)
        xlsx = tmp_path / "m.xlsx"
        _make_xlsx(xlsx, [{"first_name": "Ann", "email": "ann@x.com",
                           "Tier": "T1", "next_step": "SHEET step"}])
        import_workbook(db, xlsx, "rome-2026", {}, preserve_app_fields=False)
        assert db.get_contact("x")["next_step"] == "SHEET step"
