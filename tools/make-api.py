# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Make.com REST API utility for blueprint and data store operations.

Bypasses MCP tools (which return 500 on blueprint operations) by calling
the Make.com REST API directly.

Usage:
    # Update existing scenario blueprint
    uv run tools/make-api.py update --zone eu1.make.com --scenario-id 4596203 \
        --blueprint path/to/blueprint.json

    # Create new scenario with blueprint
    uv run tools/make-api.py deploy --zone eu1.make.com --team-id 964106 \
        --blueprint path/to/blueprint.json [--folder-id 123]

    # Download current blueprint from a scenario
    uv run tools/make-api.py get --zone eu1.make.com --scenario-id 4596203 \
        [--output blueprint.json]

    # List scenarios in a team
    uv run tools/make-api.py list --zone eu1.make.com --team-id 964106

    # List all records in a data store
    uv run tools/make-api.py ds-list --zone eu1.make.com --datastore-id 98605

    # Get a single record from a data store
    uv run tools/make-api.py ds-get --zone eu1.make.com --datastore-id 98605 --key main

    # Create or update a data store record
    uv run tools/make-api.py ds-upsert --zone eu1.make.com --datastore-id 98605 \
        --key initial_standard_a --data '{"subject":"...","body_html":"..."}'

    # Run a tool-type scenario
    uv run tools/make-api.py scenario-run --zone eu1.make.com --scenario-id 4598123 \
        --data '{"cell":"M3","value":"2026-03-01T00:00:00Z"}'

Environment:
    MAKE_API_TOKEN  — Make.com API token (or use --token flag)
"""

import argparse
import json
import os
import sys

import httpx


def get_token(args: argparse.Namespace) -> str:
    token = getattr(args, "token", None) or os.environ.get("MAKE_API_TOKEN")
    if not token:
        print("Error: No API token. Set MAKE_API_TOKEN env var or use --token flag.", file=sys.stderr)
        sys.exit(1)
    return token


def base_url(zone: str) -> str:
    return f"https://{zone}/api/v2"


def headers(token: str) -> dict:
    return {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }


def load_blueprint(path: str) -> dict:
    """Load blueprint JSON and strip fields that are invalid for API deployment."""
    with open(path, "r", encoding="utf-8") as f:
        bp = json.load(f)

    # API format: flow + name + metadata. Strip scheduling and interface.
    for key in ["scheduling", "interface"]:
        bp.pop(key, None)

    # name is required by the API (NOT NULL constraint). Default to empty if missing.
    if "name" not in bp:
        bp["name"] = ""

    # Ensure metadata.scenario.slots exists (some blueprints omit it)
    bp.setdefault("metadata", {}).setdefault("scenario", {}).setdefault("slots", None)

    return bp


def cmd_update(args: argparse.Namespace) -> None:
    """Update an existing scenario's blueprint."""
    token = get_token(args)
    bp = load_blueprint(args.blueprint)

    url = f"{base_url(args.zone)}/scenarios/{args.scenario_id}"
    body = {"blueprint": json.dumps(bp)}

    print(f"Updating scenario {args.scenario_id} on {args.zone}...")
    with httpx.Client(timeout=60) as client:
        resp = client.patch(url, headers=headers(token), json=body)

    if resp.status_code == 200:
        data = resp.json()
        scenario = data.get("scenario", data)
        print(f"Success! Scenario '{scenario.get('name', 'unknown')}' updated.")
        if scenario.get("isinvalid"):
            print("Warning: Scenario marked as invalid. Check connections and module config.")
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def cmd_deploy(args: argparse.Namespace) -> None:
    """Create a new scenario with a blueprint."""
    token = get_token(args)
    bp = load_blueprint(args.blueprint)

    url = f"{base_url(args.zone)}/scenarios"
    body = {
        "teamId": args.team_id,
        "blueprint": json.dumps(bp),
        "scheduling": json.dumps({"type": "indefinitely"}),
    }
    if args.folder_id:
        body["folderId"] = args.folder_id

    print(f"Creating scenario in team {args.team_id} on {args.zone}...")
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers(token), json=body)

    if resp.status_code in (200, 201):
        data = resp.json()
        scenario = data.get("scenario", data)
        print("Success! Scenario created:")
        print(f"  ID: {scenario.get('id')}")
        print(f"  Name: {scenario.get('name', 'unnamed')}")
        if scenario.get("isinvalid"):
            print("  Warning: Scenario marked as invalid. Check connections.")
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def cmd_get(args: argparse.Namespace) -> None:
    """Download a scenario's current blueprint."""
    token = get_token(args)

    url = f"{base_url(args.zone)}/scenarios/{args.scenario_id}/blueprint"
    print(f"Fetching blueprint for scenario {args.scenario_id}...")
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers(token))

    if resp.status_code == 200:
        data = resp.json()
        bp = data.get("response", data.get("blueprint", data))
        output = json.dumps(bp, indent=2, ensure_ascii=False)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Blueprint saved to {args.output}")
        else:
            print(output)
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """List scenarios in a team."""
    token = get_token(args)

    url = f"{base_url(args.zone)}/scenarios"
    params = {"teamId": args.team_id}
    print(f"Listing scenarios for team {args.team_id} on {args.zone}...")
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers(token), params=params)

    if resp.status_code == 200:
        data = resp.json()
        scenarios = data.get("scenarios", data.get("response", []))
        if not scenarios:
            print("No scenarios found.")
            return
        for s in scenarios:
            status = "active" if s.get("islinked") else "inactive"
            print(f"  [{s.get('id')}] {s.get('name', 'unnamed')} ({status})")
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def cmd_ds_list(args: argparse.Namespace) -> None:
    """List all records in a data store."""
    token = get_token(args)

    url = f"{base_url(args.zone)}/data-stores/{args.datastore_id}/data"
    params = {"pg[limit]": 100}
    print(f"Listing records in data store {args.datastore_id} on {args.zone}...")
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers(token), params=params)

    if resp.status_code == 200:
        data = resp.json()
        records = data.get("records", data.get("response", []))
        if not records:
            print("No records found.")
            return
        for r in records:
            key = r.get("key", r.get("Key", "?"))
            fields = {k: (v[:80] + "..." if isinstance(v, str) and len(v) > 80 else v)
                      for k, v in r.items() if k != "key"}
            print(f"  [{key}] {json.dumps(fields, ensure_ascii=False)}")
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def cmd_ds_get(args: argparse.Namespace) -> None:
    """Get a single record from a data store."""
    token = get_token(args)

    url = f"{base_url(args.zone)}/data-stores/{args.datastore_id}/data/{args.key}"
    print(f"Fetching record '{args.key}' from data store {args.datastore_id}...")
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers(token))

    if resp.status_code == 200:
        data = resp.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def cmd_ds_upsert(args: argparse.Namespace) -> None:
    """Create or update a data store record."""
    token = get_token(args)
    record_data = json.loads(args.data)

    # Try PUT (update) first, fall back to POST (create)
    # PUT expects flat fields (no 'data' wrapper), POST expects {"key": ..., ...fields}
    url = f"{base_url(args.zone)}/data-stores/{args.datastore_id}/data/{args.key}"
    print(f"Upserting record '{args.key}' in data store {args.datastore_id}...")
    with httpx.Client(timeout=30) as client:
        resp = client.put(url, headers=headers(token), json=record_data)

        if resp.status_code == 404:
            # Record doesn't exist, create it
            url = f"{base_url(args.zone)}/data-stores/{args.datastore_id}/data"
            body = {"key": args.key, **record_data}
            resp = client.post(url, headers=headers(token), json=body)

    if resp.status_code in (200, 201):
        print(f"Success! Record '{args.key}' saved.")
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def cmd_scenario_run(args: argparse.Namespace) -> None:
    """Run a tool-type scenario with input data."""
    token = get_token(args)
    input_data = json.loads(args.data) if args.data else {}

    url = f"{base_url(args.zone)}/scenarios/{args.scenario_id}/run"
    body = {"data": input_data} if input_data else {}
    print(f"Running scenario {args.scenario_id} on {args.zone}...")
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers(token), json=body)

    if resp.status_code in (200, 201):
        data = resp.json()
        print(f"Success! Output: {json.dumps(data, indent=2, ensure_ascii=False)}")
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Make.com REST API utility")
    parser.add_argument("--token", help="Make.com API token (or set MAKE_API_TOKEN)")
    sub = parser.add_subparsers(dest="command", required=True)

    # update
    p_update = sub.add_parser("update", help="Update a scenario's blueprint")
    p_update.add_argument("--zone", required=True, help="e.g. eu1.make.com")
    p_update.add_argument("--scenario-id", required=True, type=int)
    p_update.add_argument("--blueprint", required=True, help="Path to blueprint JSON")

    # deploy
    p_deploy = sub.add_parser("deploy", help="Create a new scenario with blueprint")
    p_deploy.add_argument("--zone", required=True, help="e.g. eu1.make.com")
    p_deploy.add_argument("--team-id", required=True, type=int)
    p_deploy.add_argument("--blueprint", required=True, help="Path to blueprint JSON")
    p_deploy.add_argument("--folder-id", type=int, default=None)

    # get
    p_get = sub.add_parser("get", help="Download a scenario's blueprint")
    p_get.add_argument("--zone", required=True, help="e.g. eu1.make.com")
    p_get.add_argument("--scenario-id", required=True, type=int)
    p_get.add_argument("--output", help="Output file path (default: stdout)")

    # list
    p_list = sub.add_parser("list", help="List scenarios in a team")
    p_list.add_argument("--zone", required=True, help="e.g. eu1.make.com")
    p_list.add_argument("--team-id", required=True, type=int)

    # ds-list
    p_ds_list = sub.add_parser("ds-list", help="List all records in a data store")
    p_ds_list.add_argument("--zone", required=True, help="e.g. eu1.make.com")
    p_ds_list.add_argument("--datastore-id", required=True, type=int)

    # ds-get
    p_ds_get = sub.add_parser("ds-get", help="Get a single data store record")
    p_ds_get.add_argument("--zone", required=True, help="e.g. eu1.make.com")
    p_ds_get.add_argument("--datastore-id", required=True, type=int)
    p_ds_get.add_argument("--key", required=True, help="Record key")

    # ds-upsert
    p_ds_upsert = sub.add_parser("ds-upsert", help="Create or update a data store record")
    p_ds_upsert.add_argument("--zone", required=True, help="e.g. eu1.make.com")
    p_ds_upsert.add_argument("--datastore-id", required=True, type=int)
    p_ds_upsert.add_argument("--key", required=True, help="Record key")
    p_ds_upsert.add_argument("--data", required=True, help="JSON object with field values")

    # scenario-run
    p_run = sub.add_parser("scenario-run", help="Run a tool-type scenario")
    p_run.add_argument("--zone", required=True, help="e.g. eu1.make.com")
    p_run.add_argument("--scenario-id", required=True, type=int)
    p_run.add_argument("--data", default=None, help="JSON input data")

    args = parser.parse_args()

    commands = {
        "update": cmd_update,
        "deploy": cmd_deploy,
        "get": cmd_get,
        "list": cmd_list,
        "ds-list": cmd_ds_list,
        "ds-get": cmd_ds_get,
        "ds-upsert": cmd_ds_upsert,
        "scenario-run": cmd_scenario_run,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
