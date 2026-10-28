"""Score the charges the identity build changes against Criss's Zoho postings
(company + amount to the cent + date within 3 days)."""
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from expense_recon.zoho import curated_leaves as cl

SP = Path(sys.argv[1])
P = SP / "payloads"
a = json.loads((SP / "charges_identity-base.json").read_text())
b = json.loads((SP / "charges_identity.json").read_text())
Z = json.loads(Path(os.environ["ZOHO_JSON"]).read_text(encoding="utf-8"))
ORG = {"Cloud Services": "697686691", "Corporate Services": "822741658", "Consulting": "808232536",
       "Brisken Cloud Services, LLC": "697686691", "Brisken Corp Services, LLC": "822741658"}
runs = {bid: {r["transaction_id"]: r for r in json.loads((P / f"run_{bid}.json").read_text(encoding="utf-8"))["rows"]}
        for bid in ("50622baec444", "074a7b8905d7", "51a22ad72864")}
right = wrong = unjoined = 0
for k in a:
    if a[k]["rule"] == b[k]["rule"]:
        continue
    bid, tx = k.split(":", 1)
    r = runs[bid][tx]
    org = ORG.get(b[k]["entity"])
    amt = Decimal(str(r["amount"]).replace(",", ""))
    d = date.fromisoformat(r["date"][:10])
    hits = [e for e in Z["orgs"][org]["expenses"]
            if Decimal(str(e["total"])) == amt and abs((date.fromisoformat(e["date"]) - d).days) <= 3]
    codes = {cl.code_of(e["account_name"], org) for e in hits}
    got = b[k]["rule"][0]
    if not hits:
        unjoined += 1
        verdict = "not booked (as of 09-18)"
    elif got in codes:
        right += 1
        verdict = "RIGHT"
    else:
        wrong += 1
        verdict = f"WRONG (Criss: {sorted(c for c in codes if c)})"
    print(f"{b[k]['vendor'][:34]:<34} {b[k]['entity'][:10]:<10} {r['date'][:10]} {amt:>8} -> {got:<14} {verdict}")
print(f"right {right} wrong {wrong} not joined {unjoined}")
