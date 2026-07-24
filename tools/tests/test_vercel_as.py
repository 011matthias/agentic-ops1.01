"""Behavioral tests for tools/vercel-as.sh (multi-account Vercel identities).

The script's whole job is ARGUMENT ROUTING: put each identity's auth store in
its own `--global-config` dir so the akkton (unpauseai.com) and matthias
(brisken) logins coexist instead of evicting each other, and attach the right
`--scope` / `--token`. So the tests run the real script with a STUB `vercel`
on PATH that records its argv -- no network, no login, no real CLI.

Recorded incident this guards (2026-07-22): the CLI session was matthias-5647,
the akkton org that owns `platform` reported "scope does not exist", and the
unpauseai.com force-deploy could not run. Deploying under the only visible
scope would have created a phantom project under the wrong team.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from hooklib import REPO

SCRIPT = REPO / "tools" / "vercel-as.sh"
pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash unavailable")


def run(identity_and_args: list[str], tmp_path, env_extra: dict | None = None):
    """Run vercel-as.sh with a stub `vercel` that dumps argv to a file."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    argdump = tmp_path / "argv.txt"
    stub = bindir / "vercel"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$@" > "{argdump.as_posix()}"\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{bindir.as_posix()}{os.pathsep}{env['PATH']}"
    # Keep every identity's config dir inside tmp: never touch the real ~/.
    env["VERCEL_CONFIG_UNPAUSE"] = (tmp_path / "cfg-unpause").as_posix()
    env["VERCEL_CONFIG_BRISKEN"] = (tmp_path / "cfg-brisken").as_posix()
    env.pop("VERCEL_TOKEN_UNPAUSE", None)
    env.pop("VERCEL_TOKEN_BRISKEN", None)
    env.update(env_extra or {})

    proc = subprocess.run(
        ["bash", str(SCRIPT), *identity_and_args],
        capture_output=True, text=True, env=env, timeout=60,
    )
    argv = (argdump.read_text(encoding="utf-8").splitlines()
            if argdump.is_file() else [])
    return proc, argv


def test_identities_get_separate_config_dirs(tmp_path):
    """The core property: two identities never share an auth store."""
    _, a = run(["unpause", "whoami"], tmp_path)
    _, b = run(["brisken", "whoami"], tmp_path)
    cfg_a = a[a.index("--global-config") + 1]
    cfg_b = b[b.index("--global-config") + 1]
    assert cfg_a != cfg_b
    assert "unpause" in cfg_a and "brisken" in cfg_b


def test_brisken_carries_its_scope(tmp_path):
    _, argv = run(["brisken", "project", "ls"], tmp_path)
    assert "--scope" in argv
    assert argv[argv.index("--scope") + 1] == "matthias-neumanns-projects"


def test_unpause_does_not_force_a_foreign_scope(tmp_path):
    """akkton's own account scope is its default; forcing matthias's scope
    here is exactly the wrong-team deploy this script exists to prevent."""
    _, argv = run(["unpause", "--prod"], tmp_path)
    assert "matthias-neumanns-projects" not in argv


def test_login_is_not_scoped(tmp_path):
    """`login` establishes the session; there is nothing to scope yet."""
    _, argv = run(["brisken", "login"], tmp_path)
    assert "--scope" not in argv
    assert "--global-config" in argv


def test_token_mode_passes_token_through(tmp_path):
    _, argv = run(["unpause", "whoami"], tmp_path,
                  {"VERCEL_TOKEN_UNPAUSE": "tok_abc123"})
    assert "--token" in argv
    assert argv[argv.index("--token") + 1] == "tok_abc123"


def test_token_is_per_identity_not_shared(tmp_path):
    """A brisken token must never leak into an unpause invocation."""
    _, argv = run(["unpause", "whoami"], tmp_path,
                  {"VERCEL_TOKEN_BRISKEN": "tok_brisken"})
    assert "tok_brisken" not in argv


def test_user_args_are_forwarded_verbatim(tmp_path):
    _, argv = run(["unpause", "--prod", "--force", "--yes"], tmp_path)
    assert argv[-3:] == ["--prod", "--force", "--yes"]


def test_unknown_identity_fails_loudly(tmp_path):
    proc, argv = run(["nope", "whoami"], tmp_path)
    assert proc.returncode == 64
    assert argv == []          # the CLI was never invoked
    assert "unknown identity" in proc.stderr


def test_missing_args_shows_usage(tmp_path):
    proc, argv = run(["unpause"], tmp_path)
    assert proc.returncode == 64 and argv == []


@pytest.mark.skipif(sys.platform == "win32" and shutil.which("bash") is None,
                    reason="needs bash")
def test_config_dir_is_created(tmp_path):
    run(["unpause", "whoami"], tmp_path)
    assert (tmp_path / "cfg-unpause").is_dir()
