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


# Prints a pytest-shaped FAILED roster line, so summarize() can attribute the
# red to a named test the way a real pytest run would.
ROSTER_CHECK = '''\
import sys
sys.path.insert(0, ".")
import subject
if subject.render("hi") != "<HI>":
    print("FAILED check.py::test_render")
    sys.exit(1)
print("ok")
'''

# The shape the CRLF doubling actually broke. `\\r\\n` -> `\\r\\r\\n` reads back
# as two newlines, so the backslash continuation joins with a blank line and the
# next line is an unexpected indent. 15 of 185 CRLF files under tools/ went this
# way (2026-09-17). The file itself is valid Python before AND after the
# mutation, so any parse error is the tool's doing, not the mutation's.
CONTINUATION_SOURCE = '''\
def _shout(word):
    return word.upper()


def render(word):
    tag = "<" + _shout(word) + ">" \\
        if word else ""
    return tag
'''


def crlf(text: str) -> bytes:
    return text.replace("\n", "\r\n").encode("utf-8")


@pytest.fixture
def tree(tmp_path):
    # Explicit LF bytes: Path.write_text would hand the fixture the platform's
    # line ending, which is the very variable these tests pin down.
    (tmp_path / "subject.py").write_bytes(SOURCE.encode("utf-8"))
    return tmp_path


@pytest.fixture
def crlf_tree(tmp_path):
    (tmp_path / "subject.py").write_bytes(crlf(SOURCE))
    return tmp_path


def _bytes_seen_by_each_run(monkeypatch, tree):
    """Record subject.py's bytes at every run_test call, BITE included."""
    seen = []
    real = rc.run_test

    def spy(cmd, cwd):
        seen.append((tree / "subject.py").read_bytes())
        return real(cmd, cwd)

    monkeypatch.setattr(rc, "run_test", spy)
    return seen


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


# --- line endings: the mutation must change the replacement and nothing else ---


def test_crlf_source_is_mutated_byte_for_byte(crlf_tree, monkeypatch, capsys):
    # Before 2026-09-17 the tool read bytes and wrote them back through
    # Path.write_text, so on Windows every CRLF came back as \r\r\n and the
    # mutated file was corrupt from line 1 on.
    (crlf_tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    seen = _bytes_seen_by_each_run(monkeypatch, crlf_tree)
    rc.main(_argv(crlf_tree, "check.py"))
    capsys.readouterr()

    expected = crlf(SOURCE).replace(
        UNWIRE_OLD.encode("utf-8"), UNWIRE_NEW.encode("utf-8"), 1
    )
    assert seen[1] == expected, seen[1]
    assert (crlf_tree / "subject.py").read_bytes() == crlf(SOURCE)


def test_lf_source_gains_no_carriage_returns(tree, monkeypatch, capsys):
    # The same bug in the other direction: a text-mode write on Windows
    # rewrites a pure-LF file as CRLF throughout.
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    seen = _bytes_seen_by_each_run(monkeypatch, tree)
    rc.main(_argv(tree, "check.py"))
    capsys.readouterr()

    assert b"\r" not in seen[1], seen[1]
    assert seen[1] == SOURCE.encode("utf-8").replace(
        UNWIRE_OLD.encode("utf-8"), UNWIRE_NEW.encode("utf-8"), 1
    )


def test_crlf_continuation_source_does_not_fake_a_bite(tmp_path, capsys):
    # THE invalidation. A helper-only suite does not bite, but on a CRLF source
    # whose mutation corrupted the file, every run red-lines at import and the
    # tool reported exit 0 / TEST BITES. The verdict has to be 1 here.
    (tmp_path / "subject.py").write_bytes(crlf(CONTINUATION_SOURCE))
    (tmp_path / "check.py").write_text(HELPER_CHECK, encoding="utf-8")
    assert rc.main(_argv(tmp_path, "check.py")) == 1
    assert "TEST DOES NOT BITE" in capsys.readouterr().out


def test_multiline_search_matches_a_crlf_file(crlf_tree, capsys):
    # A --replace typed with \n (every shell, every heredoc) has to find its
    # target in a CRLF file; matching raw bytes would report "matched 0 time(s)".
    (crlf_tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    argv = _argv(
        crlf_tree,
        "check.py",
        old='def render(word):\n    return "<" + _shout(word) + ">"',
        new='def render(word):\n    return "<" + word + ">"',
    )
    assert rc.main(argv) == 0
    out = capsys.readouterr().out
    assert "matched 0 time(s)" not in out
    assert "TEST BITES" in out
    assert (crlf_tree / "subject.py").read_bytes() == crlf(SOURCE)


def test_mixed_newline_file_is_left_byte_exact(tmp_path, monkeypatch, capsys):
    # Uniform-ending files round-trip through LF space; a mixed file must not,
    # or the tool would silently renormalize lines it was never asked to touch.
    mixed = SOURCE.replace("\n", "\r\n").replace(
        'def render(word):\r\n', 'def render(word):\n'
    )
    (tmp_path / "subject.py").write_bytes(mixed.encode("utf-8"))
    (tmp_path / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    seen = _bytes_seen_by_each_run(monkeypatch, tmp_path)
    rc.main(_argv(tmp_path, "check.py"))
    capsys.readouterr()

    assert seen[1] == mixed.encode("utf-8").replace(
        UNWIRE_OLD.encode("utf-8"), UNWIRE_NEW.encode("utf-8"), 1
    )
    assert (tmp_path / "subject.py").read_bytes() == mixed.encode("utf-8")


# --- a red that is not a bite ---


def test_non_compiling_mutation_is_refused_not_counted_as_red(tree, capsys):
    # A mutation that breaks the parser fails every run regardless of what the
    # suite asserts, so it is evidence about nothing. Exit 5, distinct from RED.
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    argv = _argv(tree, "check.py", new='"<" +')
    assert rc.main(argv) == 5
    out = capsys.readouterr().out
    assert "BROKEN MUTATION" in out
    assert "TEST BITES" not in out
    # Refused before the write: the source never moved.
    assert (tree / "subject.py").read_bytes() == SOURCE.encode("utf-8")


def test_broken_bytes_on_disk_are_refused_even_if_the_text_compiled(
    tree, monkeypatch, capsys
):
    # The instrument check. If a write path ever mangles the file again, the
    # red that follows is a syntax error wearing a bite's clothes.
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    real_write = rc.Path.write_bytes
    subject = tree / "subject.py"

    def mangle(self, data):
        if self == subject and b"_shout(word) + " not in data:
            data = b"  " + data  # the mutated write only
        return real_write(self, data)

    monkeypatch.setattr(rc.Path, "write_bytes", mangle, raising=False)
    assert rc.main(_argv(tree, "check.py")) == 5
    out = capsys.readouterr().out
    assert "do not compile" in out
    assert "TEST BITES" not in out


def test_unattributed_red_is_named_as_such(tree, capsys):
    # A runner with no FAILED roster and no count line: the red is real but
    # cannot be traced to an assertion, and the verdict has to say so.
    (tree / "check.py").write_text(CALLER_CHECK, encoding="utf-8")
    assert rc.main(_argv(tree, "check.py")) == 0
    out = capsys.readouterr().out
    assert "UNATTRIBUTED" in out
    assert "TEST BITES (UNATTRIBUTED)" in out


def test_attributed_red_is_a_plain_bite(tree, capsys):
    (tree / "check.py").write_text(ROSTER_CHECK, encoding="utf-8")
    assert rc.main(_argv(tree, "check.py")) == 0
    out = capsys.readouterr().out
    assert "UNATTRIBUTED" not in out
    assert "TEST BITES: green" in out


def test_non_python_target_skips_the_compile_gate(tmp_path, capsys):
    # The tool is not only for Python sources; a .js/.txt mutation that would
    # never compile as Python must still run.
    (tmp_path / "subject.txt").write_bytes(b"alpha\r\nbeta\r\n")
    (tmp_path / "check.py").write_text(
        'import sys, pathlib\n'
        'assert "beta" in pathlib.Path("subject.txt").read_text(), "gone"\n'
        'print("ok")\n',
        encoding="utf-8",
    )
    argv = [
        "--test", f'"{sys.executable}" check.py',
        "--file", "subject.txt",
        "--replace", "beta", "--with", "gamma",
        "--cwd", str(tmp_path),
    ]
    assert rc.main(argv) == 0
    assert "TEST BITES" in capsys.readouterr().out
    assert (tmp_path / "subject.txt").read_bytes() == b"alpha\r\nbeta\r\n"


def test_syntax_error_reads_bytes_and_ignores_non_python():
    src = Path("subject.py")
    assert rc.syntax_error(b"x = 1\r\n", src) is None
    assert "IndentationError" in rc.syntax_error(b"x = 1\r\n  y = 2\r\n", src)
    # A .txt that is not Python is not the compile gate's business.
    assert rc.syntax_error(b"not python at all: {", Path("notes.txt")) is None


def test_newline_style_reads_the_dominant_terminator():
    assert rc.newline_style("a\r\nb\r\n") == "\r\n"
    assert rc.newline_style("a\nb\n") == "\n"
    assert rc.newline_style("no newline at all") == "\n"


def test_regress_check_is_listed_in_tools_index():
    index = (Path(TOOLS) / "INDEX.md").read_text(encoding="utf-8")
    assert "regress_check.py" in index
