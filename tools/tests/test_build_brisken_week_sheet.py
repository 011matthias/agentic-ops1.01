"""build-brisken-week-sheet.py: week selection and the output filename.

These are the two pure decisions the tool makes before it touches a workbook,
and both are client-visible: `last_completed_monday` decides which week Dirk
gets on a Monday, and `default_out` names the file he receives.

The cross-month case is the one that bit: the week 2026-08-31..09-06 was named
`week-aug31-06`, which reads as a range inside August. Same-month names are
pinned byte-for-byte so the three books already delivered keep their filenames.
"""
import datetime as dt
import importlib.util

import pytest

from hooklib import TOOLS

pytest.importorskip("openpyxl")

SCRIPT = TOOLS / "build-brisken-week-sheet.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_week", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bw = _load()


def _name(monday):
    lo = dt.date.fromisoformat(monday)
    return bw.default_out(lo, lo + dt.timedelta(days=6)).name


# --- default_out -----------------------------------------------------------

def test_delivered_names_are_unchanged():
    # The three books already sent to Dirk. Renaming a delivered file is a
    # broken reference, so these are pinned.
    assert _name("2026-08-03") == "hours-tracker-2026-08-week-aug03-09.xlsx"
    assert _name("2026-08-10") == "hours-tracker-2026-08-week-aug10-16.xlsx"
    assert _name("2026-08-17") == "hours-tracker-2026-08-week-aug17-23.xlsx"


def test_a_week_straddling_two_months_names_both():
    assert _name("2026-08-31") == "hours-tracker-2026-08-week-aug31-sep06.xlsx"


def test_a_week_straddling_the_year_end_names_both():
    assert _name("2026-12-28") == "hours-tracker-2026-12-week-dec28-jan03.xlsx"


def test_a_week_inside_one_month_names_one():
    assert _name("2026-09-07") == "hours-tracker-2026-09-week-sep07-13.xlsx"


# --- last_completed_monday -------------------------------------------------

def test_last_completed_week_excludes_the_running_week():
    # Wednesday 2026-09-09: the running week (Sep 7) is not finished, so the
    # last completed one starts Aug 31.
    assert bw.last_completed_monday(dt.date(2026, 9, 9)) == dt.date(2026, 8, 31)


def test_on_a_monday_the_week_that_just_ended_is_the_one_delivered():
    # The standing cadence is "the running week goes out on the Monday after it
    # closes", so a Monday must select the week that ended yesterday.
    monday = dt.date(2026, 9, 7)
    assert bw.last_completed_monday(monday) == dt.date(2026, 8, 31)
    assert bw.last_completed_monday(monday) + dt.timedelta(days=6) == dt.date(2026, 9, 6)


def test_selected_week_is_always_a_monday():
    for offset in range(14):
        day = dt.date(2026, 9, 1) + dt.timedelta(days=offset)
        assert bw.last_completed_monday(day).weekday() == 0
