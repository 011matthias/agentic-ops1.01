"""One read-only prefetch of the three GL months + settings + memory.

GET only (plus the login POST), 15 s apart, brake at 45 s per read.
Writes into ./payloads beside this script.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://api.expenses.brisken.com"
OUT = Path(__file__).parent / "payloads"
OUT.mkdir(exist_ok=True)
MONTHS = {"july": "50622baec444", "august": "074a7b8905d7", "september": "51a22ad72864"}

vault = json.loads(Path(r"C:\Users\neuma_p1qrsic\.passwords.json").read_text(encoding="utf-8"))
code = vault["Expense Recon App"]["operator_code"]
req = urllib.request.Request(
    BASE + "/api/login", data=json.dumps({"code": code}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
tok = json.loads(urllib.request.urlopen(req, timeout=30).read())["token"]


def get(path: str, name: str) -> None:
    t0 = time.time()
    r = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {tok}"})
    body = urllib.request.urlopen(r, timeout=60).read()
    dt = time.time() - t0
    (OUT / name).write_bytes(body)
    print(f"{name}: {len(body)} bytes in {dt:.1f}s", flush=True)
    if dt > 45:
        print("BRAKE: read took > 45 s, stopping", flush=True)
        sys.exit(2)


plan = [("/api/expense-batches", "batches.json"), ("/api/settings", "settings.json"),
        ("/api/memory", "memory.json")]
for m, bid in MONTHS.items():
    plan.append((f"/api/expense-batches/{bid}", f"batch_{bid}.json"))
    plan.append((f"/api/runs/{bid}", f"run_{bid}.json"))
for i, (path, name) in enumerate(plan):
    if i:
        time.sleep(15)
    get(path, name)
print("DONE")
