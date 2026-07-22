"""docx-office.py: the env-correct launcher for document-skills docx scripts.

Pins the two properties the wrapper exists for: the child runs with
PYTHONUTF8=1 / PYTHONIOENCODING=utf-8, and its exit code propagates
unmodified. Command construction (the --with dependency set) is unit-tested
pure; the end-to-end tests invoke the real uv on PATH with `--deps ""` so no
package resolution slows the suite.
"""
import importlib.util
import subprocess
import sys

from hooklib import TOOLS

spec = importlib.util.spec_from_file_location("docx_office", TOOLS / "docx-office.py")
do = importlib.util.module_from_spec(spec)
spec.loader.exec_module(do)

WRAPPER = TOOLS / "docx-office.py"


def run_wrapper(*argv, timeout=120):
    return subprocess.run(
        [sys.executable, str(WRAPPER), *argv],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_default_deps_are_the_verified_docx_skill_set():
    # Verified against the skill's actual imports 2026-07-22: defusedxml + lxml,
    # no python-docx anywhere in its scripts.
    cmd = do.build_cmd("s.py", [], do.DEFAULT_DEPS)
    assert cmd == ["uv", "run", "--with", "defusedxml", "--with", "lxml", "python", "s.py"]


def test_deps_override_and_passthrough_separator():
    cmd = do.build_cmd("s.py", ["--", "--flag", "x"], "python-docx")
    assert cmd == ["uv", "run", "--with", "python-docx", "python", "s.py", "--flag", "x"]
    assert do.build_cmd("s.py", ["a"], "") == ["uv", "run", "python", "s.py", "a"]


def test_child_gets_utf8_env_and_args_and_exit_zero(tmp_path):
    child = tmp_path / "child.py"
    child.write_text(
        "import os, sys\n"
        "assert os.environ['PYTHONUTF8'] == '1', os.environ.get('PYTHONUTF8')\n"
        "assert os.environ['PYTHONIOENCODING'] == 'utf-8'\n"
        "print('CHILD_OK', sys.argv[1])\n",
        encoding="utf-8",
    )
    p = run_wrapper("--deps", "", str(child), "hello")
    assert p.returncode == 0, f"stdout:\n{p.stdout}\nstderr:\n{p.stderr}"
    assert "CHILD_OK hello" in p.stdout


def test_failing_child_exit_code_propagates(tmp_path):
    child = tmp_path / "child.py"
    child.write_text("import sys\nsys.exit(3)\n", encoding="utf-8")
    p = run_wrapper("--deps", "", str(child))
    assert p.returncode == 3, f"stdout:\n{p.stdout}\nstderr:\n{p.stderr}"
