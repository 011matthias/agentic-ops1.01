"""roll-hours-month.py: the Brisken hours-tracker month rollover.

`mondays_for` is pure and always runs. The workbook cases build a synthetic
tracker (metadata band, engagement table at A7, Overview block at J1:L13, plus a
tab carrying no engagement table) and importorskip openpyxl, mirroring
test_validate_output_cells.py so the suite is robust in a CI env without the dep.

The contract under test is what a hand-rolled month has repeatedly got wrong:
every engagement tab survives (including the optional OneAssessment one), the
data rows go but their number_format stays (the append tool donates row 8's
style to each new row), the table ref shrinks to header + one blank buffer row,
the by-week anchors move to the new month starting at the Monday of the 1st, and
the Overview block at J1:L13 is not eaten by the clear.
"""
import datetime as dt
import importlib.util

import pytest

from hooklib import TOOLS

pytest.importorskip("openpyxl")

SCRIPT = TOOLS / "roll-hours-month.py"


def _load():
    spec = importlib.util.spec_from_file_location("roll_hours_month", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rhm = _load()


# --- mondays_for -----------------------------------------------------------

def test_mondays_start_at_the_monday_of_the_first():
    # 2026-09-01 is a Tuesday, so its week starts 2026-08-31: a Sep 1 row still
    # lands in a bucket instead of falling outside the block.
    weeks = rhm.mondays_for(2026, 9)
    assert weeks[0] == dt.date(2026, 8, 31)
    assert weeks == [dt.date(2026, 8, 31), dt.date(2026, 9, 7),
                     dt.date(2026, 9, 14), dt.date(2026, 9, 21),
                     dt.date(2026, 9, 28)]


def test_mondays_when_the_first_is_a_monday():
    weeks = rhm.mondays_for(2026, 6)          # 2026-06-01 is a Monday
    assert weeks[0] == dt.date(2026, 6, 1)


def test_mondays_cover_every_day_of_the_month():
    for month in range(1, 13):
        weeks = rhm.mondays_for(2026, month)
        assert weeks[0] <= dt.date(2026, month, 1)
        assert weeks[-1] + dt.timedelta(days=6) >= rhm.dt.date(
            2026, month, rhm.calendar.monthrange(2026, month)[1])


# --- workbook rollover -----------------------------------------------------

def _tracker(path):
    from openpyxl import Workbook
    from openpyxl.worksheet.table import Table

    wb = Workbook()
    del wb[wb.sheetnames[0]]
    for title, table_name in (("Expense Reconciliation", "HoursLog"),
                              ("Lead Generation", "LeadGenLog"),
                              ("OneAssessment", "OneAssessmentLog")):
        ws = wb.create_sheet(title)
        ws["A4"], ws["B4"] = "Period", "August 2026"
        ws["A5"], ws["B5"] = "Hourly rate", 14
        for col, head in enumerate(["Date", "Task", "Start", "End", "Hours",
                                    "Billable", "Earnings", "Notes"], start=1):
            ws.cell(row=7, column=col, value=head)
        for r in (8, 9):
            ws.cell(row=r, column=1, value=dt.datetime(2026, 8, r)).number_format = "yyyy-mm-dd"
            ws.cell(row=r, column=2, value="prior month work")
            ws.cell(row=r, column=5, value=1.0).number_format = "0.00"
            ws.cell(row=r, column=6, value="Yes")
            ws.cell(row=r, column=7, value=14).number_format = '#,##0.00" €"'
        ws["J7"] = "By week"
        for i, r in enumerate(range(9, 14)):
            ws.cell(row=r, column=10, value=dt.datetime(2026, 8, 3 + 7 * i))
            ws.cell(row=r, column=11, value=f"=SUMPRODUCT(${table_name}[Hours])")
        ws.tables[table_name] = Table(displayName=table_name, ref="A7:H9")

    meta = wb.create_sheet("_meta")
    meta["A1"] = "notes that should not survive a rollover"
    wb.save(path)
    return path


def _rolled(tmp_path):
    from openpyxl import load_workbook

    src = _tracker(tmp_path / "hours-tracker-2026-08-august.xlsx")
    dest = tmp_path / "hours-tracker-2026-09-september.xlsx"
    import shutil
    shutil.copy2(src, dest)
    assert rhm.roll(dest, dest, 2026, 9, False) == 0
    return load_workbook(dest)


def test_every_engagement_tab_survives_and_meta_is_dropped(tmp_path):
    wb = _rolled(tmp_path)
    assert wb.sheetnames == ["Expense Reconciliation", "Lead Generation",
                             "OneAssessment"]


def test_data_rows_are_cleared(tmp_path):
    ws = _rolled(tmp_path)["Expense Reconciliation"]
    for r in (8, 9):
        for c in range(1, 9):
            assert ws.cell(row=r, column=c).value is None


def test_cell_styles_survive_the_clear(tmp_path):
    # The append tool donates row 8's number_format to each new row; a General
    # donor renders Earnings as a bare "28" instead of "28.00 €".
    ws = _rolled(tmp_path)["Expense Reconciliation"]
    assert ws.cell(row=8, column=1).number_format == "yyyy-mm-dd"
    assert ws.cell(row=8, column=5).number_format == "0.00"
    assert ws.cell(row=8, column=7).number_format == '#,##0.00" €"'


def test_table_ref_shrinks_to_one_buffer_row(tmp_path):
    wb = _rolled(tmp_path)
    for title, name in (("Expense Reconciliation", "HoursLog"),
                        ("Lead Generation", "LeadGenLog"),
                        ("OneAssessment", "OneAssessmentLog")):
        assert wb[title].tables[name].ref == "A7:H8"


def test_by_week_block_is_reanchored(tmp_path):
    ws = _rolled(tmp_path)["Lead Generation"]
    assert [ws.cell(row=r, column=10).value for r in range(9, 14)] == [
        dt.datetime(2026, 8, 31), dt.datetime(2026, 9, 7),
        dt.datetime(2026, 9, 14), dt.datetime(2026, 9, 21),
        dt.datetime(2026, 9, 28)]


def test_overview_block_is_not_eaten_by_the_clear(tmp_path):
    # The Overview sits at J1:L13, inside the data-row range; clearing has to
    # blank A..H only, never delete rows.
    ws = _rolled(tmp_path)["Expense Reconciliation"]
    assert ws["J7"].value == "By week"
    assert ws["K9"].value == "=SUMPRODUCT($HoursLog[Hours])"


def test_period_label_resets_to_the_new_month(tmp_path):
    ws = _rolled(tmp_path)["OneAssessment"]
    assert ws["B4"].value == "September 2026"
    assert ws["B5"].value == 14


def test_billable_dropdown_covers_the_buffer_row(tmp_path):
    ws = _rolled(tmp_path)["Expense Reconciliation"]
    dvs = [dv for dv in ws.data_validations.dataValidation
           if dv.formula1 == '"Yes,No"']
    assert len(dvs) == 1
    assert str(dvs[0].sqref) == "F8"
