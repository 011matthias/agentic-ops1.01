"""check-index.py: every tools/*.py|*.sh must have a tools/INDEX.md row.

The only enforcement primitive in tools/ without a regression test (register
#145). Loads the hyphenated script via importlib and drives main(tools_dir,
index_path) against temp trees so the matcher can't silently break.
"""
import importlib.util

from hooklib import TOOLS


def _load():
    path = TOOLS / "check-index.py"
    spec = importlib.util.spec_from_file_location("check_index", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ci = _load()


def test_all_present_passes(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text("| `a.py` | does a |\n", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 0


def test_missing_tool_fails(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "b.sh").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text("| `a.py` | does a |\n", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 1


def test_subdirs_excluded(tmp_path):
    # tools/tests/ and tools/fixtures/ live in subdirs; iterdir() is
    # non-recursive, so a subdir file is intentionally not required.
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    sub = tmp_path / "tests"
    sub.mkdir()
    (sub / "orphan.py").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text("| `a.py` | does a |\n", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 0


def test_missing_index_fails(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 1


def test_live_tree_passes():
    # The real tools/ tree must already satisfy the gate (regression guard).
    assert ci.main() == 0


def test_scorers_subdirectory_is_scanned(tmp_path):
    """tools/scorers/*.py must be covered too (scorer contract clause 7).

    iterdir() over tools/ alone never descends, so before this a new scorer
    could ship with no INDEX.md row and nothing would say so - the contract
    clause existed with no tripwire behind it.
    """
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "scorers").mkdir()
    (tmp_path / "scorers" / "new-metric.py").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text("| `a.py` | does a |\n", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 1


def test_scorer_listed_inside_a_prose_cell_passes(tmp_path):
    """Real scorers share ONE INDEX row, named inline rather than one row each.

    The backtick test must accept that shape, or enforcing the clause would
    force a pointless reformat of the existing scorers row.
    """
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "scorers").mkdir()
    (tmp_path / "scorers" / "new-metric.py").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text(
        "| `a.py` | does a |\n"
        "| `scorers/{name}.py` | Scorers: `new-metric.py ASSET` (a thing). |\n",
        encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 0


def test_missing_scorers_dir_is_not_an_error(tmp_path):
    """A tools/ tree without scorers/ (any other repo) must still pass."""
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text("| `a.py` | does a |\n", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 0
