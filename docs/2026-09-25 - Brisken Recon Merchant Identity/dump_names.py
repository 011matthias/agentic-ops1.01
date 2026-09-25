"""Dump the 55 model-unsure receipts and 164 guessed charges with today's
identity answers (registry resolve, memory recall). Offline, payloads only."""
import json
import os
from collections import Counter
from pathlib import Path

from expense_recon.learning.consult import MerchantCategoryLookup
from expense_recon.learning.store import MerchantCategory, normalize_vendor
from expense_recon.merchant_registry import MerchantRegistry

P = Path(os.environ["PAYLOADS"])
settings = json.loads((P / "settings.json").read_text(encoding="utf-8"))
memory = json.loads((P / "memory.json").read_text(encoding="utf-8"))
reg = MerchantRegistry.from_settings(settings)
LABELS = {}
for c in settings.get("account_companies") or []:
    for lab in c.get("labels") or []:
        LABELS[lab] = c["label"]
    LABELS[c["label"]] = c["label"]

rows = []
for v in memory["by_vendor"]:
    for c in v["companies"]:
        rows.append(MerchantCategory(
            legal_entity_id=c.get("entity") or "", vendor_norm=v["vendor"],
            category=c.get("category") or None, zoho_account=c.get("zoho_account") or None,
            decision_count=c.get("count") or 1, last_confirmed_at=c.get("last"),
            source_run=("zoho-seed:x" if c.get("seeded") else "run:x"),
            validated_at=c.get("validated") or None, validated_by=c.get("validated_by") or None,
        ))
lk = MerchantCategoryLookup(rows)
print("memory rules", len(lk), "entities", sorted({r.legal_entity_id for r in rows}))

MONTHS = {"50622baec444": "Jul", "074a7b8905d7": "Aug", "51a22ad72864": "Sep"}
recs, charges = [], []
for bid, m in MONTHS.items():
    bj = json.loads((P / f"batch_{bid}.json").read_text(encoding="utf-8"))
    rj = json.loads((P / f"run_{bid}.json").read_text(encoding="utf-8"))
    assert bj.get("category_vocabulary") == "gl", (bid, bj.get("category_vocabulary"))
    for e in bj.get("expenses") or []:
        if e.get("boxes") == []:
            continue
        li = e.get("line_items") or []
        unc = [x for x in li if not x.get("category")]
        if not li or not unc:
            continue
        rv = e.get("review") or {}
        refusal = rv.get("refusal") or ("no_line_items" if not li else (
            "partial:" + str(rv.get("reason_code")) if len(unc) < len(li) else str(rv.get("reason_code"))))
        if refusal != "account_unresolved":
            continue
        ven = e.get("vendor") or {}
        raw = ven.get("raw")
        disp = ven.get("display")
        ent = e.get("legal_entity_id") or ""
        recs.append(dict(month=m, doc=e.get("document_id"), entity=ent, raw=raw, display=disp,
                         source=ven.get("source"), norm=normalize_vendor(raw or ""),
                         reg_raw=(lambda x: x.canonical_name if x else None)(reg.resolve(None, raw)),
                         reg_probe=(lambda x: x.canonical_name if x else None)(reg.resolve(disp, raw)),
                         recall=(lambda x: (x.kind, x.rows[0].vendor_norm, x.category) if x else None)(lk.recall(ent, raw))))
    for r in rj.get("rows") or []:
        if r.get("effective_bucket") != "unmatched":
            continue
        cc = r.get("charge_category") or {}
        if not cc.get("category") or str(cc.get("source") or "").lower() != "vendor":
            continue
        ent = r.get("legal_entity_id") or ""
        d = r.get("vendor")
        charges.append(dict(month=m, tx=r.get("transaction_id"), entity=ent, desc=d, norm=normalize_vendor(d or ""),
                            reg=(lambda x: x.canonical_name if x else None)(reg.resolve(None, d)),
                            recall=(lambda x: (x.kind, x.rows[0].vendor_norm, x.category) if x else None)(lk.recall(ent, d)),
                            category=cc.get("category"), entry_status=r.get("entry_status")))
print("unsure receipts", len(recs), "guessed charges", len(charges))
print("charge sources seen:", Counter((r.get("charge_category") or {}).get("source")
      for bid in MONTHS for r in json.loads((P / f"run_{bid}.json").read_text(encoding="utf-8"))["rows"]
      if r.get("effective_bucket") == "unmatched"))
print("receipt live source:", Counter(r["source"] for r in recs))
print("reach live registry:", sum(r["source"] == "registry" for r in recs),
      "probe(None,raw):", sum(bool(r["reg_raw"]) for r in recs),
      "probe(display,raw):", sum(bool(r["reg_probe"]) for r in recs),
      "memory recall:", sum(bool(r["recall"]) for r in recs))
print("charges registry:", sum(bool(c["reg"]) for c in charges), "memory recall:", sum(bool(c["recall"]) for c in charges))
print("\n--- receipt names (raw | display | source | reg | recall) x count")
for k, n in Counter((r["raw"], r["display"], r["source"], r["reg_probe"], str(r["recall"])) for r in recs).most_common():
    print(n, k)
print("\n--- charge descriptors x count (norm | reg | recall)")
for k, n in Counter((c["desc"], c["reg"], str(c["recall"])) for c in charges).most_common():
    print(n, k)
(P.parent / "names.json").write_text(json.dumps({"receipts": recs, "charges": charges}, indent=1, default=str), encoding="utf-8")
