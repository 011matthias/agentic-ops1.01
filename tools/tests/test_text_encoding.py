"""W1-31: subprocess text decoding never depends on the machine's code page.

A `text=True` call without `encoding=` decodes with the locale codec (cp1252
on this Windows box), so one 0x8d byte in git or gh output over German content
raised UnicodeDecodeError in the status sweep, which then exited 0.
"""
from __future__ import annotations

import ast
import subprocess
import sys

from hooklib import HOOKS, TOOLS

# Files a scheduled job runs straight from main (the notifier clone, RepoSweep,
# AgenticOpsWeeklySynthesis). Left out of the first W1-31 PR under the client-ops guard; each
# is converted in its own owner-approved change, then removed from this set.
DEFERRED: set[str] = set()


def _bare_text_calls(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kws = {k.arg: k.value for k in node.keywords if k.arg}
        text = kws.get("text")
        if (isinstance(text, ast.Constant) and text.value is True
                and "encoding" not in kws):
            hits.append(node.lineno)
    return hits


def test_no_text_true_call_without_encoding():
    offenders = []
    for root in (TOOLS, HOOKS):
        for p in sorted(root.rglob("*.py")):
            if p.name in DEFERRED:
                continue
            offenders += [f"{p.name}:{n}" for n in _bare_text_calls(p)]
    assert not offenders, offenders


def test_scanner_flags_a_bare_call(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("import subprocess\nsubprocess.run(['a'], text=True)\n", encoding="utf-8")
    assert _bare_text_calls(f) == [2]
    f.write_text(
        "import subprocess\nsubprocess.run(['a'], text=True, encoding='utf-8')\n",
        encoding="utf-8")
    assert _bare_text_calls(f) == []


def test_undecodable_byte_does_not_raise():
    child = "import sys; sys.stdout.buffer.write(b'caf\\x8d ok')"
    out = subprocess.run(
        [sys.executable, "-c", child], capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=30)
    assert out.stdout.endswith(" ok") and "�" in out.stdout
