"""mcp_config.py: render .mcp.json per checkout from infra + .env + local (W1-17).

A fixture primary holds two clients (one n8n, one make) and a .mcp.local.json;
nothing reads the real .mcp.json or any real context/.env. Secret-shaped
values are built at runtime so no scanner has a literal to flag.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys

import pytest

from hooklib import TOOLS

KEY_VALUE = "k" + "ey-" + "x" * 12


def _load():
    spec = importlib.util.spec_from_file_location("mcp_config", TOOLS / "mcp_config.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mcp_config"] = mod
    spec.loader.exec_module(mod)
    return mod


N8N_INFRA = """\
instances:
  - type: n8n
    name: acme_prod
    mcp_server: n8n-acme
    api_url_env: N8N_API_URL_ACME
    api_key_env: N8N_API_KEY_ACME
"""
MAKE_INFRA = """\
instances:
  - type: make
    name: beta_make
    mcp_server: make-beta
"""
LOCAL = {
    "mcpServers": {
        "context7": {"command": "npx", "args": ["-y", "ctx"]},
        "make-beta": {"type": "http", "url": "https://make.example/mcp/x", "_scope": ["beta"]},
        "vercel": {"type": "http", "url": "https://mcp.vercel.example", "_scope": ["platform"]},
    }
}


@pytest.fixture()
def primary(tmp_path):
    for slug, infra in (("acme", N8N_INFRA), ("beta", MAKE_INFRA)):
        d = tmp_path / "workspace" / "clients" / slug
        (d / "context").mkdir(parents=True)
        (d / "infrastructure.yaml").write_text(infra, encoding="utf-8")
    (tmp_path / "workspace" / "clients" / "acme" / "context" / ".env").write_text(
        f"N8N_API_URL_ACME=https://acme.example/api/v1\nN8N_API_KEY_ACME={KEY_VALUE}\n", encoding="utf-8"
    )
    (tmp_path / ".mcp.local.json").write_text(json.dumps(LOCAL), encoding="utf-8")
    return tmp_path


def test_primary_renders_the_union(primary):
    mc = _load()
    servers, warnings = mc.render(primary, None)
    assert set(servers) == {"n8n-acme", "make-beta", "context7", "vercel"}
    assert servers["n8n-acme"]["env"]["N8N_API_KEY"] == KEY_VALUE
    assert "_scope" not in servers["make-beta"]
    assert warnings == []


def test_client_scope_carries_only_that_client(primary):
    mc = _load()
    acme, _ = mc.render(primary, {"acme"})
    assert set(acme) == {"n8n-acme", "context7"}
    beta, _ = mc.render(primary, {"beta"})
    assert set(beta) == {"make-beta", "context7"}


def test_vercel_only_in_platform_scope(primary):
    mc = _load()
    assert "vercel" not in mc.render(primary, {"acme"})[0]
    assert "vercel" in mc.render(primary, {"platform"})[0]


def test_missing_env_skips_the_server_and_names_the_variable(primary):
    mc = _load()
    (primary / "workspace" / "clients" / "acme" / "context" / ".env").write_text("N8N_API_URL_ACME=u\n", encoding="utf-8")
    servers, warnings = mc.render(primary, {"acme"})
    assert "n8n-acme" not in servers
    assert any("N8N_API_KEY_ACME" in w for w in warnings)
    assert not any(KEY_VALUE in w for w in warnings)


def test_make_instance_without_local_entry_warns(primary):
    mc = _load()
    (primary / ".mcp.local.json").write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    _, warnings = mc.render(primary, {"beta"})
    assert any("make-beta" in w and "no entry" in w for w in warnings)


def test_scope_from_branch():
    mc = _load()
    assert mc.scope_from_branch("client/acme/p1-thing") == {"acme"}
    assert mc.scope_from_branch("platform/header") == {"platform"}
    assert mc.scope_from_branch("proposal/foo") == {"platform"}
    assert mc.scope_from_branch("sys/layout-w1-17") == set()


def test_ensure_writes_once_then_is_a_noop(primary, capsys):
    mc = _load()
    assert mc.main(["--ensure", "--root", str(primary)]) == 0
    first = capsys.readouterr().out
    assert "restart Claude Code to load" in first
    written = json.loads((primary / ".mcp.json").read_text(encoding="utf-8"))
    assert set(written["mcpServers"]) == {"n8n-acme", "make-beta", "context7", "vercel"}
    assert mc.main(["--ensure", "--root", str(primary)]) == 0
    second = capsys.readouterr().out
    assert "already current" in second and "restart" not in second


def test_check_exit_codes_and_no_values_in_output(primary, capsys):
    mc = _load()
    assert mc.main(["--check", "--root", str(primary)]) == 1
    out = capsys.readouterr().out
    assert "+ n8n-acme" in out and KEY_VALUE not in out
    mc.main(["--ensure", "--root", str(primary)])
    capsys.readouterr()
    assert mc.main(["--check", "--root", str(primary)]) == 0
    # a changed key is named by env key, never by value
    (primary / "workspace" / "clients" / "acme" / "context" / ".env").write_text(
        f"N8N_API_URL_ACME=https://acme.example/api/v1\nN8N_API_KEY_ACME={KEY_VALUE}-rotated\n", encoding="utf-8"
    )
    assert mc.main(["--check", "--root", str(primary)]) == 1
    out = capsys.readouterr().out
    assert "~ n8n-acme" in out and KEY_VALUE not in out


def test_ensure_backs_up_the_previous_file(primary):
    mc = _load()
    (primary / ".mcp.json").write_text(json.dumps({"mcpServers": {"stale": {"command": "x"}}}), encoding="utf-8")
    mc.main(["--ensure", "--root", str(primary)])
    (backup,) = (primary / ".scratch").glob("mcp.json.pre-ensure-*")
    assert "stale" in backup.read_text(encoding="utf-8")


def test_ensure_refuses_until_adopted_and_drops_nothing(tmp_path, primary, capsys):
    mc = _load()
    (primary / ".mcp.local.json").unlink()
    hand = {"mcpServers": {"playwright": {"command": "npx", "args": ["pw"]}}}
    (primary / ".mcp.json").write_text(json.dumps(hand), encoding="utf-8")
    assert mc.main(["--ensure", "--root", str(primary)]) == 1
    assert "playwright" in capsys.readouterr().err
    assert json.loads((primary / ".mcp.json").read_text(encoding="utf-8")) == hand
    assert mc.main(["--ensure", "--hook", "--root", str(primary)]) == 0  # hook mode never fails a session


def test_adopt_scopes_and_then_renders_the_same_file(primary, capsys):
    mc = _load()
    (primary / ".mcp.local.json").unlink()
    hand = {"mcpServers": {
        "make-beta": {"type": "http", "url": "https://make.example/mcp/x"},
        "context7": {"command": "npx", "args": ["-y", "ctx"]},
        "vercel": {"type": "http", "url": "https://mcp.vercel.example"},
        "n8n-acme": {"command": "npx", "args": ["n8n-mcp"], "env": {"N8N_API_KEY": "old"}},
    }}
    (primary / ".mcp.json").write_text(json.dumps(hand), encoding="utf-8")
    assert mc.main(["--adopt", "--root", str(primary)]) == 0
    local = json.loads((primary / ".mcp.local.json").read_text(encoding="utf-8"))["mcpServers"]
    assert set(local) == {"make-beta", "context7", "vercel"}
    assert local["make-beta"]["_scope"] == ["beta"] and local["vercel"]["_scope"] == ["platform"]
    assert "_scope" not in local["context7"]
    capsys.readouterr()
    # only the n8n key (rotated in .env) differs: the hand-written servers survive
    assert mc.main(["--check", "--root", str(primary)]) == 1
    out = capsys.readouterr().out
    assert "~ n8n-acme" in out and "make-beta" not in out and "context7" not in out


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True)


def test_worktree_gets_only_its_client(primary):
    mc = _load()
    _git(primary, "init", "-b", "main")
    (primary / ".gitignore").write_text(".mcp.json\n.scratch/\n.mcp.local.json\ncontext/\n", encoding="utf-8")
    _git(primary, "add", ".gitignore", "workspace")
    _git(primary, "commit", "-m", "fixture")
    wt = primary.parent / (primary.name + "-wt")
    _git(primary, "worktree", "add", "-b", "client/beta/thing", str(wt))
    assert mc.main(["--ensure", "--root", str(wt)]) == 0
    got = json.loads((wt / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    assert set(got) == {"make-beta", "context7"}  # no n8n-acme, no vercel
    # the n8n key is read from the PRIMARY's context, which the worktree lacks
    wt2 = primary.parent / (primary.name + "-wt2")
    _git(primary, "worktree", "add", "-b", "client/acme/thing", str(wt2))
    assert not (wt2 / "workspace" / "clients" / "acme" / "context" / ".env").exists()
    assert mc.main(["--ensure", "--root", str(wt2)]) == 0
    got2 = json.loads((wt2 / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    assert got2["n8n-acme"]["env"]["N8N_API_KEY"] == KEY_VALUE


def test_worktree_add_hook_ensures_the_named_worktree(primary, monkeypatch, capsys):
    mc = _load()
    _git(primary, "init", "-b", "main")
    (primary / ".gitignore").write_text(".mcp.json\n.scratch/\n.mcp.local.json\n", encoding="utf-8")
    _git(primary, "add", ".gitignore", "workspace")
    _git(primary, "commit", "-m", "fixture")
    wt = primary.parent / (primary.name + "-hookwt")
    _git(primary, "worktree", "add", "-b", "client/beta/hook", str(wt))
    cmd = f'git -C "{primary}" worktree add -b client/beta/hook "{wt}" origin/main'
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps({"tool_input": {"command": cmd}})))
    assert mc.main(["--after-worktree-add", "--root", str(primary)]) == 0
    assert (wt / ".mcp.json").is_file()
    # an unrelated command touches nothing
    other = primary.parent / (primary.name + "-other")
    _git(primary, "worktree", "add", "-b", "client/beta/other", str(other))
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps({"tool_input": {"command": "git status"}})))
    assert mc.main(["--after-worktree-add", "--root", str(primary)]) == 0
    assert not (other / ".mcp.json").exists()


def test_parse_mcp_list_names_only_and_auth_is_not_a_failure():
    mc = _load()
    token = "t" * 16
    text = "\n".join([
        "Checking MCP server health…",
        "",
        f"make-x: https://make.example/mcp/u/{token}/stateless (HTTP) - ✔ Connected",
        "playwright: npx -y @playwright/mcp@latest --cdp-endpoint http://localhost:9222 - ✔ Connected",
        "firebase: npx -y firebase-tools mcp - ✗ Failed to connect",
        "vercel: https://mcp.vercel.example (HTTP) - ! Needs authentication",
    ])
    ok, bad = mc.parse_mcp_list(text)
    assert ok == ["make-x", "playwright"]
    assert bad == ["firebase"]


def test_adopt_excludes_the_local_file_when_gitignore_lacks_it(primary):
    mc = _load()
    _git(primary, "init", "-b", "main")
    (primary / ".gitignore").write_text(".mcp.json\n", encoding="utf-8")  # an older main: no .mcp.local.json line
    (primary / ".mcp.local.json").unlink()
    (primary / ".mcp.json").write_text(json.dumps({"mcpServers": {"context7": {"command": "npx"}}}), encoding="utf-8")
    assert mc.main(["--adopt", "--root", str(primary)]) == 0
    probe = subprocess.run(["git", "-C", str(primary), "check-ignore", "-q", ".mcp.local.json"])
    assert probe.returncode == 0
    status = subprocess.run(["git", "-C", str(primary), "status", "--porcelain", "--", ".mcp.local.json"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    assert status == ""
    # idempotent: a second adopt adds no duplicate line
    mc.ensure_excluded(primary)
    exclude = (primary / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert exclude.count(".mcp.local.json") == 1
