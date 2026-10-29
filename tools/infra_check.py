#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Consistency check for a client's infrastructure.yaml (layout plan W1-16).

Errors (exit 1):
  - an n8n instance whose mcp_server is not `n8n-{slug}` (the name
    /comd_n8n-instances writes into .mcp.json, and the one the builder
    agents look up)
  - a workflow `export:` or `test:` path, or the top-level `deploy:` entry
    point, that does not exist (resolved against the client folder, then the
    repo root)
  - an instance `api_url_env` / `api_key_env` / `*_env` name missing from
    automations/.env.example, the tracked list of the env vars the code needs

Advisories (printed, exit 0): the file is over 40 KB, or a scalar is over
500 characters. Both mean history is piling up in what should be current
state; it belongs in the status file or the comms log.

  uv run tools/infra_check.py --client meji-media
  uv run tools/infra_check.py --all
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import infra_yaml  # noqa: E402

MAX_BYTES = 40 * 1024
MAX_SCALAR = 500


def _env_names(raw: dict) -> set[str]:
    """Every `*_env` value set on an instance-level block."""
    names: set[str] = set()
    blocks = []
    blocks += [b for b in raw.get("instances") or [] if isinstance(b, dict)]
    for kind in ("n8n", "make"):
        if isinstance(raw.get(kind), dict):
            blocks.append(raw[kind])
        if isinstance(raw.get(f"{kind}_instances"), dict):
            blocks += [b for b in raw[f"{kind}_instances"].values() if isinstance(b, dict)]
    for b in blocks:
        for k, v in b.items():
            if str(k).endswith("_env") and isinstance(v, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", v):
                names.add(v)
    return names


def _long_scalars(node, path="", out=None) -> list[str]:
    out = [] if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            _long_scalars(v, f"{path}.{k}" if path else str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _long_scalars(v, f"{path}[{i}]", out)
    elif isinstance(node, str) and len(node) > MAX_SCALAR:
        out.append(f"{path} ({len(node)} chars)")
    return out


def _resolve(ref: str, client_dir: Path) -> Path | None:
    for base in (client_dir, infra_yaml.REPO):
        if (base / ref).exists():
            return base / ref
    return None


def check(slug_or_path: str) -> tuple[list[str], list[str]]:
    data = infra_yaml.load(slug_or_path)
    path = Path(data["path"])
    client_dir, slug = path.parent, data["slug"]
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []
    advisories: list[str] = []

    for inst in data["instances"]:
        if inst["type"] == "n8n" and inst["mcp_server"] != f"n8n-{slug}":
            errors.append(f"n8n instance {inst['name']}: mcp_server is "
                          f"{inst['mcp_server']!r}, expected 'n8n-{slug}'")
        for key, wf in inst["workflows"].items():
            for field in ("export", "test"):
                ref = wf.get(field)
                if isinstance(ref, str) and ref and _resolve(ref, client_dir) is None:
                    errors.append(f"workflow {key}: {field} path not found: {ref}")

    deploy = data.get("deploy")
    if isinstance(deploy, str) and _resolve(deploy, client_dir) is None:
        errors.append(f"deploy entry point not found: {deploy}")

    names = _env_names(raw)
    if names:
        example = client_dir / "automations" / ".env.example"
        listed = set()
        if example.is_file():
            listed = set(re.findall(r"^\s*([A-Z][A-Z0-9_]*)\s*=",
                                    example.read_text(encoding="utf-8"), re.MULTILINE))
        for name in sorted(names - listed):
            errors.append(f"env var {name} is not listed in automations/.env.example")

    size = path.stat().st_size
    if size > MAX_BYTES:
        advisories.append(f"file is {size // 1024} KB (> {MAX_BYTES // 1024} KB): "
                          "move history into status/ or the comms log")
    for item in _long_scalars(raw):
        advisories.append(f"long scalar {item}")
    return errors, advisories


def _all_slugs() -> list[str]:
    return sorted({p.parent.name for home in infra_yaml.HOMES
                   for p in home.glob("*/infrastructure.yaml")})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--client", help="client or project slug, or a file path")
    group.add_argument("--all", action="store_true", help="every tracked infrastructure.yaml")
    args = ap.parse_args(argv)
    targets = _all_slugs() if args.all else [args.client]
    failed = False
    for target in targets:
        try:
            errors, advisories = check(target)
        except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
            print(f"ERROR {target}: {exc}")
            failed = True
            continue
        for e in errors:
            print(f"ERROR {target}: {e}")
        for a in advisories:
            print(f"advisory {target}: {a}")
        failed = failed or bool(errors)
        if not errors:
            print(f"ok {target}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
