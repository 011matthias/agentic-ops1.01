"""tools/regress_check.py: the fix-bites-the-caller acceptance criterion.

The tool's whole job is to tell a biting suite from a non-biting one, so the
suite here builds both: a fixture package whose "fix" is a helper called by an
entry point, plus two checkers -- one asserting through the CALLER (bites) and
one asserting only against the HELPER (does not bite, which is exactly the
2026-08-24 verification-theater shape).

The fixture's test command is a plain python script, not a nested pytest run:
regress_check only reads the command's exit code, and a subprocess pytest would
make this suite slow and env-dependent for no extra coverage.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

from hooklib import TOOLS

spec = importlib.util.spec_from_file_location("regress_check", TOOLS / "regress_check.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

SOURCE = '''\
def _shout(word):
    return word.upper()


def render(word):
    return "<" + _shout(word) + ">"
'''

# Asserts through render() -- the caller the "fix" (_shout) is wired into.
CALLER_CHECK = '''\
import sys
sys.path.insert(0, ".")
import subject
assert subject.render("hi") == "<HI>", subject.render("hi")
print("ok")
'''

# Asserts only against the helper. Unwiring _shout from render() leaves this
# green: the shape the tool exists to catch.
HELPER_CHECK = '''\
import sys
sys.path.insert(0, ".")
import subject
assert subject._shout("hi") == "HI"
print("ok")
'''

# The mutation: unwire the helper from the caller, leaving the helper intact.
UNWIRE_OLD = '"<" + _shout(word) + ">"'
UNWIRE_NEW = '"<" + word + ">"'


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "subject.py").write_text(SOURCE, encoding="utf-8")
    return tmp_path


def _argv(tmp_path, check_name, old=UNWIRE_OLD, new=UNWIRE_NEW):
    return [
        "--test", f'"{sys.executable}" {check_name}',
        "--file", "subject.py",
        "--replace", old,
        "--with", new,
        "--cwd", str(tmp_path),
    ]


def test_caller_level_suite_bites(tree, capsys):
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    assert rc.main(_argv(tree, "check.py")) == 0
    assert "TEST BITES" in capsys.readouterr().out


def test_helper_only_suite_does_not_bite(tree, capsys):
    (tree / "check.py").write_text(HELPER_CHECK, encoding="utf-8")
    assert rc.main(_argv(tree, "check.py")) == 1
    out = capsys.readouterr().out
    assert "TEST DOES NOT BITE" in out
    assert "THROUGH the caller" in out


def test_source_is_restored_even_when_the_suite_does_not_bite(tree):
    (tree / "check.py").write_text(HELPER_CHECK, encoding="utf-8")
    rc.main(_argv(tree, "check.py"))
    assert (tree / "subject.py").read_text(encoding="utf-8") == SOURCE


def test_source_is_restored_after_a_biting_run(tree):
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    rc.main(_argv(tree, "check.py"))
    assert (tree / "subject.py").read_text(encoding="utf-8") == SOURCE


def test_red_baseline_is_refused_and_source_untouched(tree, capsys):
    (tree / "check.py").write_text("import sys; sys.exit(1)\n", encoding="utf-8")
    assert rc.main(_argv(tree, "check.py")) == 2
    assert "BASELINE IS RED" in capsys.readouterr().out
    assert (tree / "subject.py").read_text(encoding="utf-8") == SOURCE


def test_mutation_matching_zero_times_is_refused(tree, capsys):
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    assert rc.main(_argv(tree, "check.py", old="not_in_the_file()")) == 3
    assert "matched 0 time(s)" in capsys.readouterr().out
    assert (tree / "subject.py").read_text(encoding="utf-8") == SOURCE


def test_ambiguous_mutation_is_refused(tree, capsys):
    # `word` appears many times; a mutation that matches more than once leaves
    # it ambiguous what was actually disabled.
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    assert rc.main(_argv(tree, "check.py", old="word", new="term")) == 3
    assert "time(s)" in capsys.readouterr().out


def test_unpaired_replace_and_with_is_refused(tree):
    argv = [
        "--test", f'"{sys.executable}" check.py',
        "--file", "subject.py",
        "--replace", UNWIRE_OLD,
        "--cwd", str(tree),
    ]
    assert rc.main(argv) == 3


def test_missing_source_file_is_refused(tree):
    argv = _argv(tree, "check.py")
    argv[argv.index("--file") + 1] = "no_such_file.py"
    assert rc.main(argv) == 3


def test_regex_mode_applies_a_pattern(tree, capsys):
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    # `_shout\(word\)` alone matches twice (the def line and the call), and the
    # tool correctly refuses that; anchor on the call site.
    argv = _argv(
        tree, "check.py", old=r'"<" \+ _shout\(word\) \+ ">"', new='"<" + word + ">"'
    ) + ["--regex"]
    assert rc.main(argv) == 0
    assert "TEST BITES" in capsys.readouterr().out
    assert (tree / "subject.py").read_text(encoding="utf-8") == SOURCE


def test_summarize_reads_a_pytest_tail():
    assert rc.summarize("== 3 failed, 7 passed in 0.4s ==") == "3 failed, 7 passed"
    assert rc.summarize("== 10 passed in 0.2s ==") == "0 failed, 10 passed"
    assert rc.summarize("no summary here") == "(no pytest summary line)"
    # This repo's pytest.ini prints no count line; fall back to the roster.
    assert rc.summarize("FAILED a::b\nFAILED c::d\n") == "2 FAILED line(s)"


def test_restore_survives_a_crashing_test_command(tree, monkeypatch):
    # The finally-block restore must hold even when the runner itself explodes
    # mid-check: a half-restored source file is worse than no check at all.
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    calls = {"n": 0}
    real = rc.run_test

    def boom(cmd, cwd):
        calls["n"] += 1
        if calls["n"] == 2:  # the BITE run
            raise RuntimeError("runner exploded")
        return real(cmd, cwd)

    monkeypatch.setattr(rc, "run_test", boom)
    with pytest.raises(RuntimeError):
        rc.main(_argv(tree, "check.py"))
    assert (tree / "subject.py").read_text(encoding="utf-8") == SOURCE


def test_regress_check_is_listed_in_tools_index():
    index = (Path(TOOLS) / "INDEX.md").read_text(encoding="utf-8")
    assert "regress_check.py" in index
