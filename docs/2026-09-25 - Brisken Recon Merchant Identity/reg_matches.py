"""Every registry match (new resolver) over all vendor strings, fuzzy ones flagged."""
import json
import os
from collections import Counter
from pathlib import Path

from expense_recon.merchant_registry import MerchantRegistry

P = Path(os.environ["PAYLOADS"])
Z = json.loads(Path(os.environ["ZOHO_JSON"]).read_text(encoding="utf-8"))
reg = MerchantRegistry.from_settings(json.loads((P / "settings.json").read_text(encoding="utf-8")))
strings = Counter()
for bid in ("50622baec444", "074a7b8905d7", "51a22ad72864"):
    bj = json.loads((P / f"batch_{bid}.json").read_text(encoding="utf-8"))
    rj = json.loads((P / f"run_{bid}.json").read_text(encoding="utf-8"))
    for e in bj.get("expenses") or []:
        v = e.get("vendor") or {}
        if v.get("raw"):
            strings[v["raw"]] += 1
    for r in rj.get("rows") or []:
        if r.get("vendor"):
            strings[r["vendor"]] += 1
for o in Z["orgs"].values():
    for e in o["expenses"]:
        d = (e.get("description") or "").split("\n")[0].strip()
        if d:
            strings[d] += 1
out = Counter()
for s, n in strings.items():
    m = reg.resolve(None, s)
    if m is not None:
        out[(m.canonical_name, m.kind, s)] += n
for (c, kind, s), n in sorted(out.items()):
    print(f"{kind:<5} {c!r:<42} <- {s!r} x{n}")
