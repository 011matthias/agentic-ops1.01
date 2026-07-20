"""friction-watch.py: register parsing, the 2026-07-10 unresolved-counting fix,
the hook-contained sub-bucket, and the synthesis-cadence signal.

First behavioral suite for this tool. The counting fix closes the undercount
where `No (caught by hook)` rows silently counted as RESOLVED (tools said 67
unresolved while the true No/Partial backlog was ~130) -- the trend-flattering
metric the comd_system-dev Goodhart guard forbids.
"""
import datetime
import importlib.util

from hooklib import TOOLS


def _load():
    spec = importlib.util.spec_from_file_location(
        "friction_watch", TOOLS / "friction-watch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fw = _load()

HEADER = ("# Friction Register\n\n"
          "| Date | Client | Type | Description | Resolved? | Fix |\n"
          "|---|---|---|---|---|---|\n")


def _rows(*cells):
    return fw.parse_register(HEADER + "".join(cells))


def _row(date="2026-06-01", client="meji", typ="agent-deferred",
         desc="did a thing", resolved="No", fix="memory"):
    return f"| {date} | {client} | {typ} | {desc} | {resolved} | {fix} |\n"


# --- classification matrix ---------------------------------------------------

def test_exact_no_partially_empty_unresolved():
    rows = _rows(_row(resolved="No"), _row(resolved="Partially"), _row(resolved=""))
    assert [r["unresolved"] for r in rows] == [True, True, True]
    assert [r["hook_contained"] for r in rows] == [False, False, False]


def test_annotated_no_caught_by_hook_is_unresolved_and_contained():
    rows = _rows(_row(resolved="No (caught by hook)"))
    assert rows[0]["unresolved"] and rows[0]["hook_contained"]


def test_annotated_no_caught_never_actioned_is_contained():
    rows = _rows(_row(resolved="No (caught each time, never user-actioned)"))
    assert rows[0]["unresolved"] and rows[0]["hook_contained"]


def test_partially_annotated_unresolved_not_contained():
    rows = _rows(_row(resolved="Partially (rule shipped, reflex remains)"))
    assert rows[0]["unresolved"] and not rows[0]["hook_contained"]


def test_yes_forms_resolved():
    rows = _rows(_row(resolved="Yes (2026-05-20)"),
                 _row(resolved="yes (hook caught + held)"))
    assert not rows[0]["unresolved"] and not rows[1]["unresolved"]
    # 'caught' inside a YES cell must not create a contained bucket entry
    assert not rows[1]["hook_contained"]


def test_not_applicable_is_resolved_word_boundary_pin():
    rows = _rows(_row(resolved="not applicable"))
    assert not rows[0]["unresolved"]


# --- 2026-07-20: the 7-cell-row undercount ----------------------------------
# 305/531 real register rows carry a trailing 7th note cell ("Yes (4th
# occurrence)" etc.). The old right-anchored ROW_RE read the FIX text as
# "resolved" for those rows, so most of the register was silently classified
# resolved -- the same trend-flattering undercount class as the 2026-07-10
# fix above. Resolved is now anchored by SHAPE (first verdict-shaped cell at
# index >= 4 that leaves a Fix cell after it).

def test_seven_cell_row_no_is_unresolved():
    rows = _rows("| 2026-07-11 | brisken | infrastructure-deferred | desc text. "
                 "| No | structural -- build the detector | Yes (4th occurrence) |\n")
    assert rows[0]["unresolved"]
    assert rows[0]["resolved"] == "No"
    assert rows[0]["fix"].startswith("structural")


def test_seven_cell_row_yes_is_resolved():
    rows = _rows("| 2026-07-11 | brisken | slow-path | desc. "
                 "| Yes (2026-07-12 structural) | documented | No regression |\n")
    assert not rows[0]["unresolved"]


def test_seven_cell_fix_starting_tbd_does_not_win_over_real_no():
    rows = _rows("| 2026-05-08 | system | agent-deferred | desc. "
                 "| No | TBD -- Layer 1 candidate | self-detected |\n")
    assert rows[0]["unresolved"] and rows[0]["resolved"] == "No"


def test_pipe_inside_description_still_finds_resolved():
    rows = _rows("| 2026-06-01 | meji | slow-path | desc with a \\| pipe "
                 "| second desc frag | Partially (kept) | memory |\n")
    assert rows[0]["unresolved"]
    assert rows[0]["resolved"].startswith("Partially")


def test_seven_cell_hook_contained():
    rows = _rows("| 2026-07-14 | brisken | agent-deferred | closing offer. "
                 "| No (caught by hook) | structural -- stop-b1 backstop | recurring |\n")
    assert rows[0]["unresolved"] and rows[0]["hook_contained"]


# --- signal behavior ---------------------------------------------------------

def test_stale_excludes_hook_contained():
    rows = _rows(
        _row(date="2026-01-01", resolved="No"),
        _row(date="2026-01-01", resolved="No (caught by hook)"),
    )
    stale = fw.find_stale(rows, age_days=7)
    assert len(stale) == 1 and not stale[0]["hook_contained"]


def test_concentration_includes_hook_contained():
    rows = _rows(
        _row(resolved="No (caught by hook)"),
        _row(resolved="No (caught by hook)"),
        _row(resolved="No"),
    )
    conc = fw.find_concentration(rows, threshold=3)
    assert conc and conc[0][1] == 3


# --- cadence signal ----------------------------------------------------------

def _cadence_repo(tmp_path, ledger_text=None, reviews=False):
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    if ledger_text is not None:
        (tmp_path / "docs" / "anneal-ledger.md").write_text(
            ledger_text, encoding="utf-8")
    if reviews:
        (tmp_path / "docs" / "reviews").mkdir()
        (tmp_path / "docs" / "reviews" / "2026-07-10.md").write_text(
            "x", encoding="utf-8")
    return tmp_path


LEDGER = ("# Anneal Ledger\n\n| Date | X |\n|---|---|\n"
          "| 2026-06-18 | baseline |\n")


def test_cadence_fires_on_stale_ledger_and_missing_reviews(tmp_path):
    # No git remote in tmp -> git-show path fails -> local-file fallback.
    repo = _cadence_repo(tmp_path, ledger_text=LEDGER, reviews=False)
    c = fw.find_cadence(repo=repo, cadence_days=21,
                        today=datetime.date(2026, 7, 10))
    assert c is not None
    blob = " ".join(c["breaches"])
    assert "22d" in blob and "/comd_system-dev" in blob
    assert "docs/reviews/ never written" in blob


def test_cadence_silent_when_fresh(tmp_path):
    fresh = LEDGER.replace("2026-06-18", "2026-07-01")
    repo = _cadence_repo(tmp_path, ledger_text=fresh, reviews=True)
    c = fw.find_cadence(repo=repo, cadence_days=21,
                        today=datetime.date(2026, 7, 10))
    assert c is None


def test_cadence_no_ledger_at_all(tmp_path):
    repo = _cadence_repo(tmp_path, ledger_text=None, reviews=True)
    c = fw.find_cadence(repo=repo, cadence_days=21,
                        today=datetime.date(2026, 7, 10))
    assert c is not None and "no anneal-ledger row found" in c["breaches"][0]


def test_cadence_renders_in_text():
    report = {"signals": {"concentration": [], "memory_sprawl": [], "stale": [],
                          "recurrence": [],
                          "cadence": {"breaches": ["no anneal-ledger row for 22d (>21d) -- run /comd_system-dev"],
                                      "last_ledger_row": "2026-06-18",
                                      "ledger_age_days": 22, "reviews_exist": False}},
              "params": {"age_days": 7}}
    out = fw.render_text(report)
    assert "CADENCE" in out and "22d" in out
