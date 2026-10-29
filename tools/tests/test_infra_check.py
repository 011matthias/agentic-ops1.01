"""infra_check.py: the infrastructure.yaml consistency gate (W1-16).

Negative cases are the contract: a correct file stays silent, each broken
reference is named.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

from hooklib import TOOLS

WW_DIR = TOOLS / "fixtures" / "infra_yaml" / "ww-shape"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(TOOLS / "infra_check.py"), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)


def _copy(tmp_path):
    dst = tmp_path / "ww-shape"
    shutil.copytree(WW_DIR, dst)
    return dst / "infrastructure.yaml"


def _edit(f, old, new):
    text = f.read_text(encoding="utf-8")
    assert old in text
    f.write_text(text.replace(old, new), encoding="utf-8")


def test_meji_media_passes():
    r = _run("--client", "meji-media")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok meji-media" in r.stdout


def test_all_tracked_files_pass():
    r = _run("--all")
    assert r.returncode == 0, r.stdout + r.stderr


def test_ww_shape_fixture_passes(tmp_path):
    r = _run("--client", str(_copy(tmp_path)))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ERROR" not in r.stdout and "advisory" not in r.stdout


def test_wrong_mcp_server_is_an_error(tmp_path):
    f = _copy(tmp_path)
    _edit(f, "mcp_server: n8n-ww-shape", "mcp_server: n8n-someone-else")
    r = _run("--client", str(f))
    assert r.returncode == 1 and "expected 'n8n-ww-shape'" in r.stdout


def test_missing_export_and_test_paths_are_errors(tmp_path):
    f = _copy(tmp_path)
    (f.parent / "automations" / "n8n" / "absence-notice.json").unlink()
    (f.parent / "automations" / "tests" / "test_absence_notice.py").unlink()
    r = _run("--client", str(f))
    assert r.returncode == 1
    assert "export path not found" in r.stdout and "test path not found" in r.stdout


def test_env_name_missing_from_env_example_is_an_error(tmp_path):
    f = _copy(tmp_path)
    _edit(f.parent / "automations" / ".env.example", "N8N_API_URL_WW_SHAPE=\n", "")
    r = _run("--client", str(f))
    assert r.returncode == 1 and "N8N_API_URL_WW_SHAPE" in r.stdout
    assert "N8N_API_KEY_WW_SHAPE" not in r.stdout


def test_size_and_long_scalar_are_advisories_only(tmp_path):
    f = _copy(tmp_path)
    long_note = "x" * 600
    filler = "\n".join(f"# filler line {i:05d} " + "y" * 60 for i in range(700))
    _edit(f, "  webhook_security:\n", f"  note: {long_note}\n  webhook_security:\n")
    f.write_text(f.read_text(encoding="utf-8") + filler + "\n", encoding="utf-8")
    r = _run("--client", str(f))
    assert r.returncode == 0, r.stdout
    assert "file is" in r.stdout and "long scalar n8n.note (600 chars)" in r.stdout
