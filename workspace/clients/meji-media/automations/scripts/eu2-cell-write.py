# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""One-shot cell writer for eu2 Google Sheet via Make.com.
Deploys a temp scheduled scenario with updateCell modules, runs once, deletes."""

import json, sys, time, httpx

TOKEN = "2dc52dfc-ed0c-4d7f-b9cc-bcb3b03e696a"
ZONE = "eu2.make.com"
TEAM_ID = 2826470
CONN_ID = 13838215
SHEET_ID = "1nZcLJzjJ0Ff1j4yZQfxB09REsL2MZe4kt1xuVwaiS-M"
BASE = f"https://{ZONE}/api/v2"
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}


def write_cells(edits: list[tuple[str, str]]) -> bool:
    """Deploy a scenario with N updateCell modules, run once, delete."""
    flow = []
    for i, (cell, value) in enumerate(edits):
        flow.append({
            "id": 10 + i,
            "module": "google-sheets:updateCell",
            "version": 2,
            "parameters": {"__IMTCONN__": CONN_ID},
            "mapper": {
                "cell": cell,
                "from": "drive",
                "value": value,
                "select": "map",
                "sheetId": "Leads",
                "spreadsheetId": SHEET_ID,
                "valueInputOption": "USER_ENTERED",
            },
            "metadata": {"designer": {"x": 300 * i, "y": 0}},
        })

    bp = {"name": "TEMP-cell-writer", "flow": flow, "metadata": {}}

    with httpx.Client(timeout=60, headers=HEADERS) as client:
        # Deploy
        body = {
            "teamId": TEAM_ID,
            "blueprint": json.dumps(bp),
            "scheduling": json.dumps({"type": "indefinitely", "interval": 900}),
        }
        r = client.post(f"{BASE}/scenarios", json=body)
        if r.status_code not in (200, 201):
            print(f"  DEPLOY FAILED: {r.status_code} {r.text}", file=sys.stderr)
            return False
        sid = r.json().get("scenario", {}).get("id")
        print(f"  Deployed scenario {sid}")

        try:
            # Activate
            r = client.post(f"{BASE}/scenarios/{sid}/start")
            if r.status_code != 200:
                print(f"  ACTIVATE FAILED: {r.status_code} {r.text}", file=sys.stderr)
                return False
            print(f"  Activated, waiting for scheduled run...")

            # Wait for execution
            time.sleep(5)
            for attempt in range(20):
                r = client.get(f"{BASE}/scenarios/{sid}/logs?pg[limit]=1&pg[sortDir]=desc")
                logs = r.json().get("scenarioLogs", [])
                if logs and logs[0].get("status") is not None:
                    status = logs[0]["status"]
                    ops = logs[0].get("operations", 0)
                    print(f"  Execution: status={status}, ops={ops}")
                    return status == 1
                time.sleep(3)

            print("  Timeout waiting for execution", file=sys.stderr)
            return False
        finally:
            # Stop and delete
            try:
                client.post(f"{BASE}/scenarios/{sid}/stop")
                time.sleep(1)
            except Exception:
                pass
            client.delete(f"{BASE}/scenarios/{sid}")
            print(f"  Cleaned up scenario {sid}")


if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) % 2 == 0:
        print("Usage: uv run eu2-cell-write.py CELL VALUE [CELL VALUE ...]")
        sys.exit(1)

    args = sys.argv[1:]
    edits = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]
    print(f"Writing {len(edits)} cell(s): {edits}")
    ok = write_cells(edits)
    if ok:
        print("SUCCESS")
    else:
        print("FAILED")
    sys.exit(0 if ok else 1)
