#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Export a client's n8n workflows into the repo, or diff repo against live (W1-18).

The id -> file map comes from the client's infrastructure.yaml through
infra_yaml.py, never from a second hand-kept list: each workflow with an
`n8n_workflow_id` lands at its `export:` path, or, without one, at
`automations/{key}.n8n.json` (key with `_` -> `-`). The API URL and key are
read from the PRIMARY's context/.env under the instance's `api_url_env` /
`api_key_env` names.

Exports are scrubbed (volatile and instance-bound fields dropped, nodes sorted
by name) and stable-stringified, so a diff means the workflow changed, not
that n8n reordered it.

Read-only against n8n: one GET /workflows/{id} per workflow.

  uv run tools/n8n_export.py --client X --check         # exit 1 + list on drift
  uv run tools/n8n_export.py --client X                 # write the exports
  uv run tools/n8n_export.py --client X --only w2_09    # one workflow (key or n8n id)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import infra_yaml  # noqa: E402
import mcp_config  # noqa: E402

# Fields that change without the workflow changing, or that bind to one
# instance or run. Everything else is the workflow.
DROP_TOP = {"id", "active", "createdAt", "updatedAt", "versionId", "pinData",
            "staticData", "meta", "shared", "tags", "triggerCount", "isArchived",
            "activeVersionId", "versionCounter"}

Fetch = Callable[[str], dict]


def scrub(wf: dict) -> dict:
    out = {k: v for k, v in wf.items() if k not in DROP_TOP}
    if isinstance(out.get("nodes"), list):
        out["nodes"] = sorted(out["nodes"], key=lambda n: str(n.get("name", "")))
    return out


def stable(wf: dict) -> str:
    return json.dumps(wf, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def targets(data: dict, only: str | None = None) -> list[dict]:
    """[{key, n8n_id, path, instance}] for every exportable n8n workflow."""
    out = []
    for inst in data["instances"]:
        if inst["type"] != "n8n":
            continue
        for key, wf in inst["workflows"].items():
            wid = wf.get("n8n_workflow_id")
            if not wid:
                continue
            if only and only not in (key, wid):
                continue
            rel = wf.get("export") or f"automations/{key.replace('_', '-')}.n8n.json"
            out.append({"key": key, "n8n_id": wid, "path": rel, "instance": inst})
    return out


def http_fetch(api_url: str, api_key: str) -> Fetch:
    def fetch(wid: str) -> dict:
        req = urllib.request.Request(f"{api_url.rstrip('/')}/workflows/{wid}",
                                     headers={"X-N8N-API-KEY": api_key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (https URL from infra)
            return json.loads(resp.read().decode("utf-8"))
    return fetch


def fetcher_for(inst: dict, primary: Path, slug: str) -> Fetch:
    env = mcp_config.read_env(primary / "workspace" / "clients" / slug / "context" / ".env")
    url, key = env.get(inst.get("api_url_env") or ""), env.get(inst.get("api_key_env") or "")
    if not url or not key:
        raise SystemExit(f"n8n_export: {slug}: no value for {inst.get('api_url_env')} / "
                         f"{inst.get('api_key_env')} in context/.env")
    return http_fetch(url, key)


def run(client_dir: Path, data: dict, fetch_for: Callable[[dict], Fetch], check: bool,
        only: str | None = None) -> int:
    todo = targets(data, only)
    if not todo:
        print(f"n8n_export: {data['slug']}: no n8n workflow with an n8n_workflow_id"
              + (f" matching {only!r}" if only else ""))
        return 1 if only else 0
    drift, written = [], []
    fetchers: dict[int, Fetch] = {}
    for t in todo:
        f = fetchers.setdefault(id(t["instance"]), fetch_for(t["instance"]))
        live = stable(scrub(f(t["n8n_id"])))
        path = client_dir / t["path"]
        repo = stable(scrub(json.loads(path.read_text(encoding="utf-8")))) if path.is_file() else None
        if repo == live:
            continue
        if check:
            drift.append(f"  {'missing' if repo is None else 'differs'}: {t['path']} ({t['key']}, {t['n8n_id']})")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(live, encoding="utf-8")
            written.append(f"  wrote {t['path']}")
    if check:
        if drift:
            print(f"n8n_export: {len(drift)} of {len(todo)} workflow(s) differ from live:")
            print("\n".join(drift))
            return 1
        print(f"n8n_export: {len(todo)} workflow(s) match live")
        return 0
    print("\n".join(written) if written else f"n8n_export: {len(todo)} workflow(s) already current")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--client", required=True)
    ap.add_argument("--only", default=None, help="one workflow: its infra key or n8n id")
    ap.add_argument("--check", action="store_true", help="diff repo against live, write nothing")
    args = ap.parse_args(argv)
    path = infra_yaml.find(args.client)
    if path is None:
        print(f"n8n_export: no infrastructure.yaml for {args.client!r}", file=sys.stderr)
        return 2
    data = infra_yaml.load(path)
    primary = mcp_config.primary_root(HERE.parent)
    return run(path.parent, data, lambda inst: fetcher_for(inst, primary, data["slug"]),
               args.check, args.only)


if __name__ == "__main__":
    sys.exit(main())
