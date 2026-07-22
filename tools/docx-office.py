#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Launch a document-skills docx/office script with the right env + deps.

The docx skill's Python scripts (merge_runs.py, comment.py, office/validate.py,
...) import defusedxml + lxml, and on Windows they need PYTHONUTF8=1 /
PYTHONIOENCODING=utf-8 or non-ASCII document text mangles the console pipes.
Four sessions rebuilt that incantation by hand (friction register 2026-07-13..17);
this wrapper is the incantation.

Usage:
    uv run tools/docx-office.py SCRIPT.py [args...]
    uv run tools/docx-office.py --deps defusedxml,lxml,python-docx SCRIPT.py [args...]
    uv run tools/docx-office.py SCRIPT.py -- --flags-for-the-child

Runs: uv run --with <dep> ... python SCRIPT.py [args...]
with PYTHONUTF8=1 + PYTHONIOENCODING=utf-8 in the child env. stdout/stderr are
inherited unmodified; the child's exit code is propagated. `--deps ""` runs
with no extra packages.
"""
import argparse
import os
import shutil
import subprocess
import sys

DEFAULT_DEPS = "defusedxml,lxml"


def build_cmd(script: str, args: list[str], deps: str) -> list[str]:
    """Assemble the uv invocation for `script` with `deps` (comma-separated)."""
    cmd = ["uv", "run"]
    for dep in deps.split(","):
        if dep.strip():
            cmd += ["--with", dep.strip()]
    cmd += ["python", script]
    # An initial `--` is our separator, not a child argument.
    if args and args[0] == "--":
        args = args[1:]
    return cmd + args


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--deps", default=DEFAULT_DEPS,
                        help=f'comma-separated --with packages (default: {DEFAULT_DEPS}; "" = none)')
    parser.add_argument("script", help="Python script to run (e.g. the docx skill's merge_runs.py)")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="arguments passed through to the script")
    ns = parser.parse_args()

    if shutil.which("uv") is None:
        print("docx-office: uv not found on PATH", file=sys.stderr)
        return 127

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(build_cmd(ns.script, ns.args, ns.deps), env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
