"""The uptime workflow's own shell steps (backlog item 123).

`test_recon_uptime_probe.py` proves the probe script; this file proves the
CALLER, the `run:` block in `.github/workflows/expense-recon-uptime.yml`
that decides whether the notifier gets to run at all.

The distinction is the whole point. GitHub starts a `run:` step as
`bash -e {0}`, and a script's own `set -uo pipefail` does not undo the `-e`
it was launched with. So the original step, which captured `rc=$?` on the
line after the probe, never reached that line when the probe reported the
app DOWN: the shell aborted, the step went red, the Notify step was skipped
by its implicit `success()` condition, and the outage alerted nobody. The
probe's own tests all passed throughout, because the defect lived in the
three lines of YAML between them and the alert. Live proof, run
35361771075 (2026-09-18, `api_override=https://127.0.0.1:9`): "summary:
DOWN: api" followed by "Process completed with exit code 1", Notify skipped.

Each test runs the REAL step text out of the YAML under `bash -e`, with a
stub on PATH standing in for `uv` so the probe's verdict is a dial. The
negative case that matters is the middle one: a DOWN app (exit 1) must
leave the step GREEN so the notifier runs.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

from hooklib import REPO

WORKFLOW = REPO / ".github" / "workflows" / "expense-recon-uptime.yml"

BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(BASH is None, reason="no bash on PATH")


def _steps() -> dict[str, dict]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return {s["name"]: s for s in doc["jobs"]["probe"]["steps"] if "name" in s}


def _probe_script() -> str:
    step = _steps()["Probe (read-only GETs + a port-25 banner)"]
    return step["run"]


def _run_step(tmp_path: Path, script: str, uv_exit: int,
              api_override: str = "") -> subprocess.CompletedProcess:
    """Run the step's own text under `bash -e`, exactly as GitHub does,
    with a stub `uv` that reports `uv_exit` and writes a probe payload."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "uv"
    stub.write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        echo '{"ok": false, "checks": []}'
        exit %d
        """) % uv_exit, encoding="utf-8")
    stub.chmod(0o755)

    script_file = tmp_path / "step.sh"
    script_file.write_text(script, encoding="utf-8", newline="\n")

    env = dict(os.environ)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["API_OVERRIDE"] = api_override
    # GitHub's default shell for a `run:` block on Linux.
    return subprocess.run(
        [BASH, "-e", str(script_file)],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )


# ------------------------------------------------------- the three verdicts --

@needs_bash
def test_all_ok_leaves_the_step_green(tmp_path):
    assert _run_step(tmp_path, _probe_script(), uv_exit=0).returncode == 0


@needs_bash
def test_app_down_leaves_the_step_green_so_the_notifier_runs(tmp_path):
    """The regression. Exit 1 is "the app is down", which is the notifier's
    business: the step must stay green or the alert never fires."""
    done = _run_step(tmp_path, _probe_script(), uv_exit=1,
                     api_override="https://127.0.0.1:9")
    assert done.returncode == 0, (
        "a DOWN app aborted the step (rc=%d); the Notify step would be "
        "skipped and the outage would alert nobody" % done.returncode
    )


@needs_bash
def test_broken_probe_fails_the_step(tmp_path):
    """Exit 2 is "the probe itself broke", which IS this job's failure:
    probe.json cannot be trusted, so the notifier must not run on it."""
    assert _run_step(tmp_path, _probe_script(), uv_exit=2).returncode == 2


@needs_bash
def test_the_probe_verdict_is_written_where_notify_reads_it(tmp_path):
    """The two steps are joined by a file, not a variable: `probe.json` in
    the workspace. A step that stops writing it breaks the notifier
    silently."""
    _run_step(tmp_path, _probe_script(), uv_exit=1)
    assert (tmp_path / "probe.json").is_file()
    assert "--result probe.json" in _steps()["Notify (issue + mail policy)"]["run"]


# --------------------------------------------------------------- the wiring --

def test_notify_runs_on_the_probe_steps_success():
    """No `if:` on Notify, so it inherits `success()`: it runs after a green
    probe step (app OK or app DOWN) and is skipped after a red one (the
    probe broke). That is the intended policy, and it is only safe because
    a DOWN app keeps the probe step green."""
    assert "if" not in _steps()["Notify (issue + mail policy)"]


def test_the_schedule_is_the_ten_minute_cron():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML reads the bare `on:` key as the boolean True.
    triggers = doc.get("on", doc.get(True))
    assert [c["cron"] for c in triggers["schedule"]] == ["*/10 * * * *"]
