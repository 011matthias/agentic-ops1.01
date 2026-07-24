"""Behavioral tests for tools/vercel-as.ps1 (the PowerShell twin).

The .ps1 is the variant that actually runs on the owner's machine: the `bash`
on PATH there is the WSL stub, so the .sh twin would execute in a Linux
filesystem with no Windows `vercel` install. Same contract as
test_vercel_as.py -- argument routing verified by running the real script
against a stub `vercel` that records its argv.

WINDOWS-ONLY BY CONSTRUCTION. The stub shim is a `vercel.bat` relying on
PATHEXT resolution (a PowerShell *function* named `vercel` loses to the real
CLI's own .ps1 on PATH), and the script under test targets a Windows CLI
install. GitHub's ubuntu runners DO ship pwsh, so gating on `which pwsh` alone
is not enough: the suite then runs on Linux, the .bat never executes, argv
comes back empty and 5 tests fail. That exact miss turned the CI hooks job red
on 2026-07-22 (PR #401). The POSIX contract is covered by the .sh twin's suite
(`test_vercel_as.py`), so skipping off-Windows loses no coverage.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

from hooklib import REPO

SCRIPT = REPO / "tools" / "vercel-as.ps1"
PWSH = shutil.which("pwsh") or shutil.which("powershell")
pytestmark = pytest.mark.skipif(
    os.name != "nt" or PWSH is None,
    reason="vercel-as.ps1 is a Windows tool; its .bat stub needs PATHEXT "
           "(ubuntu CI ships pwsh, so the pwsh check alone is insufficient)",
)


def run(identity_and_args: list[str], tmp_path, env_extra: dict | None = None):
    """Run vercel-as.ps1 with a stub `vercel` shim ahead of it on PATH."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    argdump = tmp_path / "argv.json"
    # A PowerShell function named `vercel` would be shadowed by the real CLI's
    # own .ps1 on PATH, so shim via a vercel.bat that wins PATHEXT ordering.
    (bindir / "vercel.bat").write_text(
        "@echo off\r\n"
        f'"{shutil.which("python") or "python"}" "{(bindir / "dump.py").as_posix()}" %*\r\n',
        encoding="utf-8",
    )
    (bindir / "dump.py").write_text(
        "import json,sys,pathlib\n"
        f"pathlib.Path(r'{argdump}').write_text("
        "json.dumps(sys.argv[1:]), encoding='utf-8')\n",
        encoding="utf-8",
    )

    env = dict(os.environ)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    env["VERCEL_CONFIG_UNPAUSE"] = str(tmp_path / "cfg-unpause")
    env["VERCEL_CONFIG_BRISKEN"] = str(tmp_path / "cfg-brisken")
    env.pop("VERCEL_TOKEN_UNPAUSE", None)
    env.pop("VERCEL_TOKEN_BRISKEN", None)
    env.update(env_extra or {})

    proc = subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
         *identity_and_args],
        capture_output=True, text=True, env=env, timeout=120,
    )
    argv = (json.loads(argdump.read_text(encoding="utf-8"))
            if argdump.is_file() else [])
    return proc, argv


def test_identities_get_separate_config_dirs(tmp_path):
    _, a = run(["unpause", "whoami"], tmp_path)
    _, b = run(["brisken", "whoami"], tmp_path)
    cfg_a = a[a.index("--global-config") + 1]
    cfg_b = b[b.index("--global-config") + 1]
    assert cfg_a != cfg_b
    assert "unpause" in cfg_a and "brisken" in cfg_b


def test_brisken_carries_its_scope(tmp_path):
    _, argv = run(["brisken", "project", "ls"], tmp_path)
    assert argv[argv.index("--scope") + 1] == "matthias-neumanns-projects"


def test_unpause_does_not_force_a_foreign_scope(tmp_path):
    _, argv = run(["unpause", "--prod"], tmp_path)
    assert "matthias-neumanns-projects" not in argv


def test_login_is_not_scoped(tmp_path):
    _, argv = run(["brisken", "login"], tmp_path)
    assert "--scope" not in argv
    assert "--global-config" in argv


def test_token_mode_passes_token_through(tmp_path):
    _, argv = run(["unpause", "whoami"], tmp_path,
                  {"VERCEL_TOKEN_UNPAUSE": "tok_abc123"})
    assert argv[argv.index("--token") + 1] == "tok_abc123"


def test_token_is_per_identity_not_shared(tmp_path):
    _, argv = run(["unpause", "whoami"], tmp_path,
                  {"VERCEL_TOKEN_BRISKEN": "tok_brisken"})
    assert "tok_brisken" not in argv


def test_user_args_forwarded_verbatim(tmp_path):
    _, argv = run(["unpause", "--prod", "--force", "--yes"], tmp_path)
    assert argv[-3:] == ["--prod", "--force", "--yes"]


def test_unknown_identity_fails_without_invoking_cli(tmp_path):
    proc, argv = run(["nope", "whoami"], tmp_path)
    assert proc.returncode == 64
    assert argv == []


def test_config_dir_is_created(tmp_path):
    run(["unpause", "whoami"], tmp_path)
    assert (tmp_path / "cfg-unpause").is_dir()
