"""Replay the receiptless-charge categorizer on the live GL months with a
model that refuses, so only rules answer. Run under the base tree and the
build tree; diff the JSON outputs."""
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from expense_recon.categorize_charges import categorize_charges
from expense_recon.learning.consult import MerchantCategoryLookup
from expense_recon.learning.store import MerchantCategory
from expense_recon.llm.client import ClassificationResult, MockLLMClient
from expense_recon.matching.types import MatchOutcome, Transaction
from expense_recon.merchant_registry import MerchantRegistry

P = Path(os.environ["PAYLOADS"])
settings = json.loads((P / "settings.json").read_text(encoding="utf-8"))
memory = json.loads((P / "memory.json").read_text(encoding="utf-8"))
reg = MerchantRegistry.from_settings(settings)
entity_orgs = {}
for c in settings["account_companies"]:
    for lab in [c["label"], *c["labels"]]:
        entity_orgs[lab] = c["org_id"]
rows = [MerchantCategory(
    legal_entity_id=c.get("entity") or "", vendor_norm=v["vendor"],
    category=c.get("category") or None, zoho_account=c.get("zoho_account") or None,
    decision_count=c.get("count") or 1, last_confirmed_at=c.get("last"),
    source_run=("zoho-seed:x" if c.get("seeded") else "run:x"),
    validated_at=c.get("validated") or None, validated_by=c.get("validated_by") or None)
    for v in memory["by_vendor"] for c in v["companies"]]
lk = MerchantCategoryLookup(rows)


class Refuses(MockLLMClient):
    def classify_line_items(self, items, *a, **k):
        return [ClassificationResult(None, None, 0.2, "unsure") for _ in items]

    def classify_by_vendor(self, *a, **k):
        return ClassificationResult(None, None, 0.2, "unsure")


out = {}
for bid in ("50622baec444", "074a7b8905d7", "51a22ad72864"):
    rj = json.loads((P / f"run_{bid}.json").read_text(encoding="utf-8"))
    txs = []
    for r in rj["rows"]:
        if r.get("effective_bucket") != "unmatched" or not r.get("vendor"):
            continue
        txs.append(Transaction(
            transaction_id=r["transaction_id"], legal_entity_id=r.get("legal_entity_id") or "",
            account_id=r.get("account_id") or "card",
            transaction_date=date.fromisoformat(r["date"][:10]), posting_date=None,
            amount=Decimal(str(r["amount"]).replace(",", "")), transaction_currency=r.get("currency") or "USD",
            account_card_currency="USD", vendor_from_statement=r["vendor"]))
    got = categorize_charges(
        MatchOutcome(unmatched_transactions=[t.transaction_id for t in txs]), txs,
        client=Refuses(), learned=lk, registry=reg, entity_orgs=entity_orgs)
    live = {r["transaction_id"]: r for r in rj["rows"]}
    for t in txs:
        c = got.get(t.transaction_id)
        cc = live[t.transaction_id].get("charge_category") or {}
        out[f"{bid}:{t.transaction_id}"] = {
            "vendor": t.vendor_from_statement, "entity": t.legal_entity_id,
            "entry_status": live[t.transaction_id].get("entry_status"),
            "live": [cc.get("category"), cc.get("source")],
            "rule": [c.category, str(c.source.value if hasattr(c.source, "value") else c.source)] if c and c.category else None,
        }
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print(len(out), "charges;", sum(1 for v in out.values() if v["rule"]), "answered by a rule")
