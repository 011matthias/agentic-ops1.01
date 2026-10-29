#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Render the gitignored .mcp.json for a checkout from tracked sources (W1-17).

Before this tool the per-client MCP servers lived in one hand-edited file in
the primary clone: a worktree session had none, and an n8n key sat in both
context/.env and .mcp.json (the 2026-09-13 25-hour outage shape).

Sources:
  workspace/clients/{c}/infrastructure.yaml   instance `mcp_server`,
                                              `api_url_env`, `api_key_env`
  workspace/clients/{c}/context/.env          the values those names point at
  <primary>/.mcp.local.json                   machine-only servers (tokens in a
                                              URL, the CDP port): the `local:`
                                              passthrough. Each entry may carry
                                              `"_scope": ["meji-media", "platform"]`;
                                              no `_scope` = every checkout.

Scope of a render:
  primary clone   every client's servers + every local entry (nothing a running
                  session or ClaudeRemoteControl has today disappears)
  worktree        only the session's client (branch `client/{c}/...`, or
                  --client) and `platform` for platform/ and proposal/ branches

An n8n instance renders as `npx n8n-mcp` with the two env values read from the
PRIMARY's context/.env (the only place client context exists). A missing
variable skips that server and says so; it never renders a half-wired entry.

  uv run tools/mcp_config.py --check            # exit 1 + names-only diff
  uv run tools/mcp_config.py --ensure           # write only on change
  uv run tools/mcp_config.py --adopt            # one-time: seed .mcp.local.json
  uv run tools/mcp_config.py --ensure --hook    # SessionStart: quiet, fail-open

Values never print; the diff names servers and env keys only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import infra_yaml  # noqa: E402

LOCAL_NAME = ".mcp.local.json"
SCOPE_KEY = "_scope"
PLATFORM = "platform"
RESTART = "restart Claude Code to load"
N8N_BASE_ENV = {
    "MCP_MODE": "stdio",
    "LOG_LEVEL": "error",
    "DISABLE_CONSOLE_OUTPUT": "true",
}


def _git(root: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
    )
    return out.stdout.strip() if out.returncode == 0 else ""


def primary_root(root: Path) -> Path:
    """The main worktree: parent of the shared .git dir (clone or linked)."""
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common).parent if common else root


def current_branch(root: Path) -> str:
    return _git(root, "rev-parse", "--abbrev-ref", "HEAD")


def scope_from_branch(branch: str) -> set[str]:
    """Scope tokens a branch name implies: client slug and/or `platform`."""
    parts = branch.split("/")
    if len(parts) >= 2 and parts[0] == "client":
        return {parts[1]}
    if parts[0] in ("platform", "proposal"):
        return {PLATFORM}
    return set()


def read_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if m and not line.lstrip().startswith("#"):
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            env[m.group(1)] = v
    return env


def client_slugs(primary: Path) -> list[str]:
    base = primary / "workspace" / "clients"
    if not base.is_dir():
        return []
    return sorted(p.parent.name for p in base.glob("*/infrastructure.yaml"))


def read_local(primary: Path) -> dict[str, dict]:
    p = primary / LOCAL_NAME
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return {k: v for k, v in (data.get("mcpServers") or {}).items() if isinstance(v, dict)}


def render(primary: Path, scope: set[str] | None) -> tuple[dict[str, dict], list[str]]:
    """Return ({server: config}, warnings). scope=None means the union."""
    servers: dict[str, dict] = {}
    warnings: list[str] = []
    local = read_local(primary)
    slugs = client_slugs(primary)
    wanted = slugs if scope is None else [s for s in slugs if s in scope]

    for slug in wanted:
        try:
            data = infra_yaml.load(primary / "workspace" / "clients" / slug / "infrastructure.yaml")
        except Exception as exc:  # a broken client file must not blank the others
            warnings.append(f"{slug}: infrastructure.yaml unreadable ({exc.__class__.__name__})")
            continue
        env = read_env(primary / "workspace" / "clients" / slug / "context" / ".env")
        for inst in data["instances"]:
            name = inst.get("mcp_server")
            if not name:
                continue
            if inst["type"] == "n8n":
                url_env, key_env = inst.get("api_url_env"), inst.get("api_key_env")
                missing = [n for n in (url_env, key_env) if not n or not env.get(n)]
                if missing:
                    warnings.append(f"{slug}: {name} skipped, no value for {', '.join(str(m) for m in missing)}")
                    continue
                servers[name] = {
                    "command": "npx",
                    "args": ["n8n-mcp"],
                    "env": {**N8N_BASE_ENV, "N8N_API_URL": env[url_env], "N8N_API_KEY": env[key_env]},
                }
            elif name not in local:
                warnings.append(f"{slug}: {name} ({inst['type']}) has no entry in {LOCAL_NAME}")

    for name, cfg in local.items():
        tags = cfg.get(SCOPE_KEY)
        if scope is not None and tags and not (set(tags) & scope):
            continue
        servers[name] = {k: v for k, v in cfg.items() if k != SCOPE_KEY}
    return servers, warnings


def describe_diff(old: dict[str, dict], new: dict[str, dict]) -> list[str]:
    lines = []
    for n in sorted(new.keys() - old.keys()):
        lines.append(f"  + {n}")
    for n in sorted(old.keys() - new.keys()):
        lines.append(f"  - {n}")
    for n in sorted(new.keys() & old.keys()):
        if old[n] != new[n]:
            keys = sorted(k for k in set(old[n]) | set(new[n]) if old[n].get(k) != new[n].get(k))
            lines.append(f"  ~ {n} (changed: {', '.join(keys)})")
    return lines


def target_for(root: Path, client: str | None) -> tuple[Path, set[str] | None, str]:
    """(primary, scope, label). Scope None = union, only in the primary clone."""
    primary = primary_root(root)
    if client:
        return primary, {client} | ({PLATFORM} if client == PLATFORM else set()), f"client {client}"
    if root.resolve() == primary.resolve():
        return primary, None, "primary (union)"
    scope = scope_from_branch(current_branch(root))
    return primary, scope, f"worktree scope {sorted(scope) or 'none'}"


def current(root: Path) -> dict[str, dict]:
    p = root / ".mcp.json"
    if not p.is_file():
        return {}
    return (json.loads(p.read_text(encoding="utf-8")).get("mcpServers")) or {}


def write(root: Path, servers: dict[str, dict]) -> Path | None:
    """Write .mcp.json; back up the old file first. Returns the backup path."""
    p = root / ".mcp.json"
    backup = None
    if p.is_file():
        scratch = root / ".scratch"
        scratch.mkdir(exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = scratch / f"mcp.json.pre-ensure-{stamp}"
        backup.write_bytes(p.read_bytes())
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"mcpServers": dict(sorted(servers.items()))}, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    return backup


def adopt(root: Path) -> int:
    """Seed .mcp.local.json from the existing .mcp.json (one time, primary only).

    n8n servers are not adopted: they are rendered from infra + .env. A server
    named as a client instance's mcp_server is scoped to that client, vercel to
    platform; anything else is unscoped.
    """
    primary = primary_root(root)
    target = primary / LOCAL_NAME
    if target.exists():
        print(f"mcp_config: {LOCAL_NAME} already exists, left alone")
        return 0
    owner: dict[str, str] = {}
    for slug in client_slugs(primary):
        try:
            for inst in infra_yaml.load(primary / "workspace" / "clients" / slug / "infrastructure.yaml")["instances"]:
                if inst.get("mcp_server"):
                    owner[inst["mcp_server"]] = slug
        except Exception:
            continue
    out: dict[str, dict] = {}
    for name, cfg in current(primary).items():
        if cfg.get("command") == "npx" and cfg.get("args") == ["n8n-mcp"]:
            continue
        entry = dict(cfg)
        if name in owner:
            entry[SCOPE_KEY] = [owner[name]]
        elif name == "vercel":
            entry[SCOPE_KEY] = [PLATFORM]
        out[name] = entry
    target.write_text(json.dumps({"mcpServers": out}, indent=2) + "\n", encoding="utf-8")
    print(f"mcp_config: wrote {LOCAL_NAME} with {', '.join(sorted(out)) or 'no servers'}")
    return 0


def worktrees_named_in(command: str, primary: Path) -> list[Path]:
    """Worktrees whose path appears in a `git worktree add` command line."""
    if not re.search(r"\bworktree\s+add\b", command):
        return []
    norm = command.replace("\\", "/").lower()
    found = []
    for line in _git(primary, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            wt = Path(line[9:])
            if wt.resolve() != primary.resolve() and wt.as_posix().lower() in norm.replace("//", "/"):
                found.append(wt)
    return found


def unadopted(primary: Path) -> list[str]:
    """Hand-written servers the primary holds that no .mcp.local.json carries.

    Rendering before --adopt would silently drop them (context7, playwright,
    the Make URL), so ensure and check refuse until the local file exists.
    """
    if (primary / LOCAL_NAME).is_file():
        return []
    return sorted(n for n, c in current(primary).items()
                  if not (c.get("command") == "npx" and c.get("args") == ["n8n-mcp"]))


REFUSE = "run `uv run tools/mcp_config.py --adopt` first; rendering now would drop: "


def ensure(root: Path, client: str | None, quiet: bool) -> int:
    primary, scope, label = target_for(root, client)
    if pending := unadopted(primary):
        print(f"mcp_config: refused, {REFUSE}{', '.join(pending)}", file=sys.stderr)
        return 0 if quiet else 1
    servers, warnings = render(primary, scope)
    old = current(root)
    for w in warnings:
        print(f"mcp_config: warning: {w}", file=sys.stderr)
    if servers == old:
        if not quiet:
            print(f"mcp_config: .mcp.json already current ({label}, {len(servers)} servers)")
        return 0
    backup = write(root, servers)
    print(f"mcp_config: rendered .mcp.json ({label}):")
    print("\n".join(describe_diff(old, servers)))
    if backup:
        print(f"mcp_config: previous file kept at {backup}")
    print(f"mcp_config: {RESTART}")
    return 0


def check(root: Path, client: str | None) -> int:
    primary, scope, label = target_for(root, client)
    if pending := unadopted(primary):
        print(f"mcp_config: {REFUSE}{', '.join(pending)}")
        return 1
    servers, warnings = render(primary, scope)
    old = current(root)
    for w in warnings:
        print(f"mcp_config: warning: {w}", file=sys.stderr)
    if servers == old:
        print(f"mcp_config: current ({label}, {len(servers)} servers)")
        return 0
    print(f"mcp_config: .mcp.json differs from the render ({label}):")
    print("\n".join(describe_diff(old, servers)))
    return 1


def parse_mcp_list(text: str) -> tuple[list[str], list[str]]:
    """(connected names, failed names) from `claude mcp list` output.

    Names only: a Make server's URL carries its token. "Needs authentication"
    is a setup state, not a failed connection, so it is neither list.
    """
    ok: list[str] = []
    bad: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(.+?):\s.*\s-\s(.*)$", line)
        if not m:
            continue
        name, status = m.group(1).strip(), m.group(2)
        if "Connected" in status:
            ok.append(name)
        elif "Needs authentication" in status:
            continue
        else:
            bad.append(name)
    return ok, bad


def mcp_health() -> int:
    """Doctor check (W1-36): exit 1 when any configured MCP server fails to connect."""
    try:
        proc = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"mcp_config: claude mcp list unavailable ({exc.__class__.__name__}), skipped")
        return 0
    ok, bad = parse_mcp_list(proc.stdout)
    if bad:
        print(f"mcp_config: {len(bad)} MCP server(s) failed to connect: {', '.join(bad)}")
        return 1
    print(f"mcp_config: {len(ok)} MCP server(s) connected, none failed")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--ensure", action="store_true")
    mode.add_argument("--adopt", action="store_true")
    mode.add_argument("--mcp-health", action="store_true",
                      help="doctor check: exit 1 if `claude mcp list` shows a failed connection")
    mode.add_argument("--after-worktree-add", action="store_true",
                      help="PostToolUse: read the hook payload on stdin, ensure the new worktree")
    ap.add_argument("--root", type=Path, default=None, help="checkout to render for (default: cwd's)")
    ap.add_argument("--client", default=None, help="render this client's scope instead of the branch's")
    ap.add_argument("--hook", action="store_true", help="quiet, fail-open, always exit 0")
    args = ap.parse_args(argv)
    root = (args.root or Path(_git(Path.cwd(), "rev-parse", "--show-toplevel") or Path.cwd())).resolve()
    try:
        if args.mcp_health:
            return mcp_health()
        if args.adopt:
            return adopt(root)
        if args.after_worktree_add:
            payload = json.loads(sys.stdin.read() or "{}")
            cmd = (payload.get("tool_input") or {}).get("command", "")
            for wt in worktrees_named_in(cmd, primary_root(root)):
                ensure(wt, None, quiet=True)
            return 0
        if args.check:
            return check(root, args.client)
        return ensure(root, args.client, quiet=args.hook)
    except Exception as exc:
        if args.hook or args.after_worktree_add:
            print(f"mcp_config: skipped ({exc.__class__.__name__}: {exc})", file=sys.stderr)
            return 0
        print(f"mcp_config: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
