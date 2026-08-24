"""heredoc-size-gate (PreToolUse:Bash|PowerShell): the decision matrix.

Pins the three deny classes (size / triple-quote / python-backslash), the
silent-allow cases that must stay silent (short ASCII patch, commit-message
heredoc, here-string, no heredoc at all), the unterminated-opener rule that
keeps a stray `<<WORD` inside a quoted string from false-denying, and the
user-ordered HEREDOC_GATE_ALLOW seam.

Trigger: friction register 2026-08-22 + 2026-08-24 (the same "unexpected EOF on
a large Python heredoc" failure twice, the second time also silently corrupting
an escaped backslash). The 2026-08-22 fix was `documented` and did not hold.
"""
import json

import pytest

from hooklib import load_hook, permission_decision, run_hook

GATE = "heredoc-size-gate.py"


def _run(cmd, tool="Bash", env=None, tmp_path=None):
    base = {}
    if tmp_path is not None:
        base["AGENTIC_OPS_SESSION_STATE"] = str(tmp_path / "s.json")
    base.update(env or {})
    return run_hook(GATE, {"tool_name": tool, "tool_input": {"command": cmd}}, env=base)


def _reason(p):
    out = p.stdout.strip()
    if not out:
        return ""
    try:
        return (json.loads(out).get("hookSpecificOutput") or {}).get(
            "permissionDecisionReason", ""
        )
    except json.JSONDecodeError:
        return ""


def _heredoc(tag, body, opener="cat > out.py"):
    return f"{opener} <<'{tag}'\n{body}\n{tag}\n"


# ------------------------------------------------------------------ deny: size


def test_oversized_heredoc_is_denied(tmp_path):
    body = "\n".join(f"line_{i} = {i}" for i in range(120))
    p = _run(_heredoc("PYEOF", body), tmp_path=tmp_path)
    assert permission_decision(p.stdout) == "deny"
    assert "HEREDOC TOO LARGE" in _reason(p)
    assert "Write tool" in _reason(p)


def test_heredoc_at_the_cap_is_allowed(tmp_path):
    gate = load_hook(GATE)
    body = "\n".join(f"x{i} = {i}" for i in range(gate.MAX_HEREDOC_LINES))
    p = _run(_heredoc("EOF", body), tmp_path=tmp_path)
    assert p.stdout.strip() == "", "a heredoc exactly at the cap must pass"


def test_one_line_over_the_cap_is_denied(tmp_path):
    gate = load_hook(GATE)
    body = "\n".join(f"x{i} = {i}" for i in range(gate.MAX_HEREDOC_LINES + 1))
    assert permission_decision(_run(_heredoc("EOF", body), tmp_path=tmp_path).stdout) == "deny"


# ---------------------------------------------------------- deny: triple-quote


def test_python_triple_quote_block_is_denied(tmp_path):
    body = 'def f():\n    """docstring"""\n    return 1'
    p = _run(_heredoc("PYEOF", body), tmp_path=tmp_path)
    assert permission_decision(p.stdout) == "deny"
    assert "TRIPLE-QUOTED" in _reason(p)


def test_single_quote_triple_block_is_denied(tmp_path):
    body = "TEXT = '''\nmulti\nline\n'''"
    assert permission_decision(_run(_heredoc("PYEOF", body), tmp_path=tmp_path).stdout) == "deny"


# ------------------------------------------------------------- deny: backslash


def test_double_backslash_in_python_heredoc_is_denied(tmp_path):
    # The exact 2026-08-24 silent-corruption shape: a regex escape that
    # collapses in transit and changes the payload's meaning.
    body = "import re\nROW = re.compile(r'^[|]" + chr(92) * 2 + "s*(?P<d>x)')"
    p = _run("python - <<'PYEOF'\n" + body + "\nPYEOF\n", tmp_path=tmp_path)
    assert permission_decision(p.stdout) == "deny"
    assert "DOUBLE BACKSLASH" in _reason(p)


def test_double_backslash_outside_python_context_is_allowed(tmp_path):
    # A non-Python heredoc (a config/text payload) is not the documented
    # failure class; the gate must not widen into general text.
    body = "path = C:" + chr(92) * 2 + "Users" + chr(92) * 2 + "shared"
    p = _run(_heredoc("CFGEOF", body, opener="cat > app.ini"), tmp_path=tmp_path)
    assert p.stdout.strip() == ""


def test_py_tag_alone_marks_python_context(tmp_path):
    # `cat > f <<'PYEOF'` has no `python` in the prefix; the PY* tag carries it.
    body = "x = '" + chr(92) * 2 + "d+'"
    assert permission_decision(_run(_heredoc("PYEOF", body), tmp_path=tmp_path).stdout) == "deny"


# ------------------------------------------------------------- silent allowals


def test_no_heredoc_is_silent(tmp_path):
    assert _run("git status && ls -la", tmp_path=tmp_path).stdout.strip() == ""


def test_short_ascii_patch_heredoc_is_silent(tmp_path):
    p = _run(_heredoc("EOF", "s/foo/bar/\nw\nq", opener="ed file.txt"), tmp_path=tmp_path)
    assert p.stdout.strip() == ""


def test_commit_message_heredoc_is_silent(tmp_path):
    # The house convention for multi-line commit messages must keep working.
    msg = "sys: fix the thing\n\nBody line one.\nBody line two."
    p = _run(f"git commit -F - <<'MSG'\n{msg}\nMSG\n", tmp_path=tmp_path)
    assert p.stdout.strip() == ""


def test_here_string_is_not_a_heredoc(tmp_path):
    assert _run('grep foo <<< "some foo text"', tmp_path=tmp_path).stdout.strip() == ""


def test_stray_marker_in_a_quoted_string_does_not_false_deny(tmp_path):
    # `<<NOTE` with no terminator line: the triple-quote / backslash rules are
    # gated on a TERMINATED heredoc precisely so this cannot fire.
    cmd = "echo \"see <<NOTE\" && python -c \"print(''' x ''')\""
    assert _run(cmd, tmp_path=tmp_path).stdout.strip() == ""


def test_unterminated_but_huge_body_still_denies(tmp_path):
    # The "unexpected EOF" bug itself: opener present, terminator missing.
    body = "\n".join(f"row_{i}()" for i in range(200))
    p = _run("python - <<'PYEOF'\n" + body, tmp_path=tmp_path)
    assert permission_decision(p.stdout) == "deny"


def test_non_shell_tool_is_ignored(tmp_path):
    p = run_hook(GATE, {"tool_name": "Write", "tool_input": {"file_path": "x.py"}})
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_malformed_payload_fails_open():
    p = run_hook(GATE, {})
    assert p.returncode == 0 and p.stdout.strip() == ""


# ------------------------------------------------------------------- the seam


def test_allow_env_downgrades_deny_to_advisory(tmp_path):
    body = "\n".join(f"line_{i} = {i}" for i in range(120))
    p = _run(_heredoc("PYEOF", body), env={"HEREDOC_GATE_ALLOW": "1"}, tmp_path=tmp_path)
    assert permission_decision(p.stdout) is None, "override must not deny"
    assert "OVERRIDE ACTIVE" in p.stdout


# ------------------------------------------------------------- unit: classify


@pytest.mark.parametrize(
    "cmd,kind",
    [
        ("python - <<'PY'\n" + "a\n" * 100 + "PY\n", "size"),
        ("python - <<'PY'\nx = \"\"\"y\"\"\"\nPY\n", "triple-quote"),
        ("python - <<'PY'\nr'" + chr(92) * 2 + "d'\nPY\n", "backslash"),
        ("python - <<'PY'\nprint(1)\nPY\n", None),
    ],
    ids=["size", "triple-quote", "backslash", "clean"],
)
def test_classify_matrix(cmd, kind):
    gate = load_hook(GATE)
    hit = gate.classify(cmd)
    assert (hit[0] if hit else None) == kind
