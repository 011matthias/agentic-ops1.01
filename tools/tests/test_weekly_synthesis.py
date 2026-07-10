"""weekly_synthesis.py: the deterministic no-LLM weekly sensor.

Pins: report assembly on the live tree (all four sections), JSON contract,
fail-loud send delegation, and the version-controlled registration command
(the gap with MejiWeeklyReview was an uncommitted Register-ScheduledTask).
No test sends email: the send path is monkeypatched; the real path is
covered by --preflight at registration time.
"""
import importlib.util
import json
import subprocess
import sys

from hooklib import TOOLS

SCRIPT = TOOLS / "weekly_synthesis.py"


def _load():
    spec = importlib.util.spec_from_file_location("weekly_synthesis", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ws = _load()


def test_report_sections_local_mode():
    r = ws.build_report(scheduled=False)
    assert r["backlog"]["total_rows"] > 0
    text = ws.render_text(r)
    for section in ("SIGNALS", "BACKLOG", "CADENCE", "ASSETS"):
        assert section in text, f"missing section {section}"
    assert "hook-contained" in text
    assert "sensor commit" in text


def test_json_contract():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--local", "--no-email", "--format", "json"],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    r = json.loads(proc.stdout)
    for k in ("date", "mode", "signals", "backlog", "cadence", "assets"):
        assert k in r, f"missing key {k}"
    assert r["mode"] == "local"


def test_send_delegates_to_send_email(monkeypatch):
    calls = {}

    def fake_run(argv, **kw):
        calls["argv"] = argv
        calls["input"] = kw.get("input", "")

        class P:
            returncode = 0
            stdout = "RESEND_OK {}"
            stderr = ""
        return P()

    monkeypatch.setattr(ws.subprocess, "run", fake_run)
    assert ws.send("subject-x", "body-y") is True
    assert str(calls["argv"][1]).endswith("send_email.py")
    assert calls["argv"][2] == "subject-x"
    assert calls["input"] == "body-y"


def test_send_failure_returns_false(monkeypatch):
    def fake_run(argv, **kw):
        class P:
            returncode = 1
            stdout = ""
            stderr = "RESEND_ERR boom"
        return P()

    monkeypatch.setattr(ws.subprocess, "run", fake_run)
    assert ws.send("s", "b") is False


def test_print_registration_golden_substrings():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--print-registration"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0
    for token in ("Register-ScheduledTask", "uv.exe", "-StartWhenAvailable",
                  "--scheduled", "agentic-ops1-cadence", "AgenticOpsWeeklySynthesis"):
        assert token in proc.stdout, f"missing {token}"


def test_registration_targets_pinned_worktree_not_primary_clone():
    assert "agentic-ops1-cadence" in ws.REGISTRATION
    assert "Repo\\agentic-ops1\"" not in ws.REGISTRATION
