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
