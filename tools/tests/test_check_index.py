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


# --- whole-name-in-table-row matching (2026-07-22 residual fix: the old
# backtick-prefix substring test accepted a prose mention anywhere and a
# prefix of a longer name) ----------------------------------------------------

def test_prefix_of_longer_name_does_not_count(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text(
        "| `a.py.legacy-wrapper` | wraps a |\n", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 1


def test_prose_mention_outside_table_row_does_not_count(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text(
        "Removed tools: `a.py` was retired 2026-07-01.\n", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 1


def test_name_with_args_in_row_still_counts(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text(
        "| `a.py --dry-run FILE` | does a |\n", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 0


def test_bare_name_in_row_still_counts(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "INDEX.md").write_text(
        "| `a.py` | does a |\n", encoding="utf-8")
    assert ci.main(tmp_path, tmp_path / "INDEX.md") == 0


def _client_tree(tmp_path):
    """tools/ that passes on its own, plus one client with automations/tools/."""
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "INDEX.md").write_text("| `a.py` | does a |\n", encoding="utf-8")
    (tools / "a.py").write_text("x", encoding="utf-8")
    ctools = tmp_path / "workspace" / "clients" / "acme" / "automations" / "tools"
    ctools.mkdir(parents=True)
    (ctools / "sync.mjs").write_text("x", encoding="utf-8")
    (ctools / "fetch.py").write_text("x", encoding="utf-8")
    return tools, tmp_path / "workspace" / "clients", ctools


def test_client_tools_dir_without_readme_fails(tmp_path, capsys):
    tools, clients, _ = _client_tree(tmp_path)
    assert ci.main(tools, tools / "INDEX.md", clients) == 1
    assert "acme/automations/tools/README.md missing" in capsys.readouterr().err


def test_client_tools_unlisted_script_fails_and_listed_passes(tmp_path, capsys):
    tools, clients, ctools = _client_tree(tmp_path)
    (ctools / "README.md").write_text("| `sync.mjs --dry-run` | pulls |\n", encoding="utf-8")
    assert ci.main(tools, tools / "INDEX.md", clients) == 1
    assert "fetch.py" in capsys.readouterr().err
    (ctools / "README.md").write_text("| `sync.mjs --dry-run` | pulls |\n| `fetch.py` | reads |\n", encoding="utf-8")
    assert ci.main(tools, tools / "INDEX.md", clients) == 0


def test_real_main_scans_the_repo_clients_dir(monkeypatch):
    seen = []
    monkeypatch.setattr(ci, "_client_problems", lambda d: seen.append(d) or [])
    assert ci.main() == 0
    assert seen and seen[0].as_posix().endswith("workspace/clients")
