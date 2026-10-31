#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""One reader for workspace/{clients,projects}/<slug>/infrastructure.yaml.

Three incompatible shapes exist and the builder agents BLOCKed on a fourth
that no file had (layout plan W1-16):

  instances:            list of {type|kind, name, mcp_server, scenarios: [..]}
                        (meji-media's Make org, brisken's Fly apps)
  n8n_instances: / make_instances:
                        map of name -> {mcp_server, credentials, workflows: {..}}
                        (the agnt_n8n-builder fixture, what the agents wrote)
  n8n: / make:          one top-level block per orchestrator, with workflows
                        nested at any depth under `workflows:` maps or as
                        sibling blocks that carry `n8n_workflow_id` (WW)

All of them normalize to:

  {slug, path, type, orchestrator, deploy,
   instances: [{type, name, url, api_url_env, api_key_env, mcp_server,
                credentials: {slug: id},
                workflows: {key: {id, name, n8n_workflow_id, status,
                                  trigger, export, test}}}]}

Read-only. Writes stay targeted Edits to the YAML so comments survive.

  uv run tools/infra_yaml.py --client meji-media          # summary
  uv run tools/infra_yaml.py --client meji-media --json   # normalized form
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
HOMES = (REPO / "workspace" / "clients", REPO / "workspace" / "projects")
ORCHESTRATORS = {"n8n", "make", "trigger-dev", "fastapi"}
ENV_KEYS = ("api_url_env", "api_key_env")


def find(slug: str) -> Path | None:
    """The slug's infrastructure.yaml, clients first (rule_project_status)."""
    for home in HOMES:
        p = home / slug / "infrastructure.yaml"
        if p.is_file():
            return p
    return None


def _workflow(key, d: dict) -> dict:
    wid = d.get("n8n_workflow_id") or d.get("workflow_id")
    return {
        "id": str(d.get("id") or wid or d.get("client_id") or key),
        "name": d.get("name") or d.get("n8n_name") or d.get("display_name"),
        "n8n_workflow_id": wid,
        "status": d.get("status"),
        "trigger": d.get("trigger"),
        "export": d.get("export"),
        "test": d.get("test"),
    }


def _entries(value) -> dict:
    """A workflows/scenarios value: a map of key -> dict, or a list of dicts."""
    out = {}
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, dict):
                out[str(k)] = _workflow(k, v)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            if isinstance(v, dict):
                key = str(v.get("id") or v.get("name") or i)
                out[key] = _workflow(key, v)
    return out


def _is_workflow_key(k: str) -> bool:
    return k in ("workflows", "scenarios") or k.endswith("_scenarios")


def _walk_workflows(node, out: dict) -> None:
    if not isinstance(node, dict):
        return
    for k, v in node.items():
        k = str(k)
        if _is_workflow_key(k):
            out.update(_entries(v))
        elif isinstance(v, dict) and ("n8n_workflow_id" in v or "workflow_id" in v):
            out[k] = _workflow(k, v)
        elif isinstance(v, dict):
            _walk_workflows(v, out)


def _cred_value(v):
    if isinstance(v, dict):
        return v.get("n8n_credential_id") or v.get("connection_id") or v.get("id")
    return v


def _walk_credentials(node, out: dict) -> None:
    if not isinstance(node, dict):
        return
    for k, v in node.items():
        if k in ("credentials", "connections") and isinstance(v, dict):
            for ck, cv in v.items():
                out[str(ck)] = _cred_value(cv)
        elif k in ("credentials", "connections") and isinstance(v, list):
            # meji-media: [{id, type, account}]; key by name or type, then id.
            for cv in v:
                if isinstance(cv, dict):
                    key = str(cv.get("name") or cv.get("type") or cv.get("id"))
                    if key in out:
                        key = f"{key}_{cv.get('id')}"
                    out[key] = _cred_value(cv)
        elif isinstance(v, dict) and not _is_workflow_key(str(k)):
            _walk_credentials(v, out)


def _instance(kind, name, d: dict) -> dict:
    creds: dict = {}
    _walk_credentials(d, creds)
    flows: dict = {}
    _walk_workflows(d, flows)
    account = d.get("client_account") if isinstance(d.get("client_account"), dict) else {}
    return {
        "type": kind,
        "name": name,
        "url": d.get("url") or d.get("api_url") or d.get("zone") or account.get("zone"),
        "api_url_env": d.get("api_url_env"),
        "api_key_env": d.get("api_key_env"),
        "mcp_server": d.get("mcp_server"),
        "credentials": creds,
        "workflows": flows,
    }


def normalize(raw: dict) -> list[dict]:
    instances = []
    for item in raw.get("instances") or []:
        if isinstance(item, dict):
            kind = item.get("type") or item.get("kind")
            instances.append(_instance(kind, item.get("name") or item.get("app"), item))
    for kind in ("n8n", "make"):
        block = raw.get(f"{kind}_instances")
        if isinstance(block, dict):
            for name, d in block.items():
                if isinstance(d, dict):
                    instances.append(_instance(kind, str(name), d))
        top = raw.get(kind)
        if isinstance(top, dict):
            instances.append(_instance(kind, top.get("instance") or kind, top))
    return instances


def _file_orchestrator(client_dir: Path) -> str | None:
    auto = client_dir / "automations"
    if (auto / "trigger.config.ts").is_file():
        return "trigger-dev"
    if (auto / "railway.toml").is_file():
        return "fastapi"
    return None


def detect_orchestrator(raw: dict, instances: list[dict], client_dir: Path) -> str | None:
    """Top-level `orchestrator:` -> an instance `type:` -> file checks.

    .mcp.json is deliberately absent: it is gitignored, so it only answers
    "credentials wired on this machine", never "which orchestrator".
    """
    top = raw.get("orchestrator")
    if isinstance(top, str) and top.strip():
        return top.strip()
    for inst in instances:
        if inst["type"] in ORCHESTRATORS:
            return inst["type"]
    return _file_orchestrator(client_dir)


def load(slug_or_path: str | Path) -> dict:
    p = Path(slug_or_path)
    if not p.is_file():
        found = find(str(slug_or_path))
        if found is None:
            raise FileNotFoundError(f"no infrastructure.yaml for {slug_or_path!r}")
        p = found
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: top level is not a mapping")
    instances = normalize(raw)
    return {
        "slug": p.parent.name,
        "path": str(p),
        "type": raw.get("type"),
        "orchestrator": detect_orchestrator(raw, instances, p.parent),
        # An explicit deploy entry point outranks the orchestrator's default
        # lane (brisken: FastAPI on Fly via deploy.py, never `railway up`).
        "deploy": raw.get("deploy"),
        "instances": instances,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--client", required=True, help="client or project slug, or a file path")
    ap.add_argument("--json", action="store_true", help="print the normalized form")
    args = ap.parse_args(argv)
    try:
        data = load(args.client)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"infra_yaml: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        return 0
    print(f"{data['slug']}: type={data['type']} orchestrator={data['orchestrator']}"
          + (f" deploy={data['deploy']}" if data["deploy"] else ""))
    for inst in data["instances"]:
        print(f"  [{inst['type']}] {inst['name']} mcp_server={inst['mcp_server']} "
              f"credentials={len(inst['credentials'])} workflows={len(inst['workflows'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
