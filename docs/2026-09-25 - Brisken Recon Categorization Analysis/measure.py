"""Offline baseline + refusal breakdown + deterministic lever counts.

Reads ONLY the saved payloads in $TEMP/recon (batch_*.json, run_*.json,
settings.json, memory.json) plus the item-180 suggestions markdown and the
module's curated_leaves. Writes analysis.json beside the payloads and prints
a compact summary. No network, no model calls.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from expense_recon.zoho import curated_leaves as cl

S = Path(os.environ["RECON_DIR"])
SUGG = Path(os.environ["SUGG_MD"])
ORG = {"Cloud Services": "697686691", "Consulting": "808232536", "Corporate Services": "822741658"}
LABELS = {}
settings = json.loads((S / "settings.json").read_text(encoding="utf-8"))
for c in settings.get("account_companies") or []:
    for lab in c.get("labels") or []:
        LABELS[lab] = c["label"]
    LABELS[c["label"]] = c["label"]


def company_of(label: str | None) -> str | None:
    if not label:
        return None
    return LABELS.get(label, label)


def dec(x) -> Decimal:
    try:
        return Decimal(str(x).replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


# ---- item-180 suggestions table ------------------------------------------
EXTRA_ALIASES = {
    "SendGrid (Twilio)": ["sendgrid", "twilio"],
    "Microsoft 365": ["microsoft", "msft"],
    "Google Workspace": ["google workspace", "gsuite", "workspace brisken", "google llc"],
    "Google Cloud": ["google cloud", "google  cloud", "google *cloud"],
    "Trello (Atlassian)": ["trello", "atlassian"],
    "Afi (M365 backup)": ["afi technologies", "afi "],
    "Wispr Flow": ["wispr"],
    "Hugging Face": ["hugging"],
    "Network Solutions": ["network solutions", "networksolutions"],
    "Host Europe": ["host europe", "hosteurope"],
    "OpenAI": ["openai", "chatgpt"],
    "Anthropic": ["anthropic", "antropic"],
    "Lovable": ["lovable"],
    "Redis": ["redis"],
    "Zoho": ["zoho"],
    "ElevenLabs": ["elevenlabs", "eleven labs"],
    "DigitalOcean": ["digitalocean", "digital ocean"],
    "GitHub": ["github"],
    "GoDaddy": ["godaddy", "go daddy"],
    "Base44": ["base44"],
    "Bloomberg": ["bloomberg"],
    "Supabase": ["supabase"],
    "Railway": ["railway"],
    "Vercel": ["vercel"],
    "Resend": ["resend"],
    "Rize": ["rize"],
    "Fireflies": ["fireflies"],
    "OpenRouter": ["openrouter"],
    "Cursor": ["cursor"],
    "Obsidian": ["obsidian"],
    "Perplexity": ["perplexity"],
    "Pressmaster": ["pressmaster"],
    "Proton": ["proton"],
    "Typora": ["typora"],
    "Wix": ["wix"],
    "Brave": ["brave"],
    "Adobe": ["adobe"],
    "AWS": ["amazon web services", "aws"],
    "ServerPilot": ["serverpilot"],
    "Hostinger": ["hostinger"],
    "Canva": ["canva"],
    "Slack": ["slack"],
    "Namecheap": ["namecheap"],
    "Registro.br": ["registro br", "registro.br"],
}
sugg = {}  # (vendor_key, company) -> code
sugg_alias = {}  # vendor_key -> aliases
for line in SUGG.read_text(encoding="utf-8").splitlines():
    if not line.startswith("| ") or line.startswith("| Vendor") or line.startswith("|---"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 4:
        continue
    vendor, company, code = cells[0], cells[1], cells[2]
    if company not in ORG:
        continue
    if code and code.lower() != "none" and re.match(r"^E\d", code):
        sugg[(vendor, company)] = code
    aliases = EXTRA_ALIASES.get(vendor) or [norm(vendor.split("(")[0])]
    sugg_alias[vendor] = [a.lower() for a in aliases]


def sugg_vendor(text: str | None) -> str | None:
    t = (text or "").lower()
    if not t:
        return None
    best = None
    for v, aliases in sugg_alias.items():
        for a in aliases:
            if a and a in t:
                if best is None or len(a) > best[1]:
                    best = (v, len(a))
    return best[0] if best else None


# ---- memory rules -----------------------------------------------------------
memory = json.loads((S / "memory.json").read_text(encoding="utf-8"))
mem_rules = []  # (entity, vendor_norm, category, zoho_account, seeded, validated)
for v in memory.get("by_vendor") or []:
    for c in v.get("companies") or []:
        mem_rules.append((c.get("entity") or "", v.get("vendor"), c.get("category"), c.get("zoho_account"), bool(c.get("seeded")), bool(c.get("validated"))))
mem_by_key = {(company_of(e) or "", vn): (cat, acc, seeded, val) for e, vn, cat, acc, seeded, val in mem_rules}


def mem_rule_for(vendor_text: str | None, company: str | None):
    """Mimic MerchantCategoryLookup.recall: own company, then no-company."""
    vn = norm(vendor_text)
    if not vn:
        return None
    # normalize_vendor in the app strips corporate suffixes; approximate by
    # trying full text, then progressively shorter token prefixes
    toks = vn.split()
    cands = [" ".join(toks[:k]) for k in range(len(toks), 0, -1)]
    for key in cands:
        hit = mem_by_key.get((company or "", key))
        if hit and hit[0]:
            return ("company", key) + hit
    if company:
        for key in cands:
            hit = mem_by_key.get(("", key))
            if hit and hit[0]:
                return ("no_company", key) + hit
    return None


# ---- load months -----------------------------------------------------------
batches = json.loads((S / "batches.json").read_text(encoding="utf-8"))
items = batches.get("batches") if isinstance(batches, dict) else batches
months = []
for b in items:
    bid = b.get("id") or b.get("run_id")
    bj = json.loads((S / f"batch_{bid}.json").read_text(encoding="utf-8"))
    rj = json.loads((S / f"run_{bid}.json").read_text(encoding="utf-8"))
    months.append((bid, b.get("label"), bj, rj))
months.sort(key=lambda m: m[1])

out = {"months": {}, "gl_refusals": {}, "levers": {}}
gl_rows = []  # per refused receipt: dict
gl_lines_total = Counter()
charge_rows = []

print("=== BASELINE (screen rule: an expense is categorized when EVERY line carries a category; copies boxes=[] excluded)")
print(f"{'month':<14} {'vocab':<7} {'exp':>4} {'cat':>4} {'uncat':>5} {'pct':>5} | {'lines':>5} {'lcat':>5} | {'charges':>7} {'rec':>4} {'unm':>4} {'unm_cat':>7} {'unm_ref':>7} {'unm_none':>8} | screen n_categorized/n_uncategorized")
for bid, label, bj, rj in months:
    vocab = bj.get("category_vocabulary")
    ex_all = bj.get("expenses") or []
    ex = [e for e in ex_all if e.get("boxes") != []]
    copies = len(ex_all) - len(ex)
    def is_cat(e):
        li = e.get("line_items") or []
        return bool(li) and all(x.get("category") for x in li)
    n_cat = sum(1 for e in ex if is_cat(e))
    lines = [x for e in ex for x in (e.get("line_items") or [])]
    n_lcat = sum(1 for x in lines if x.get("category"))
    rows = rj.get("rows") or []
    buckets = Counter(r.get("effective_bucket") for r in rows)
    unm = [r for r in rows if r.get("effective_bucket") == "unmatched"]
    unm_cat = sum(1 for r in unm if (r.get("charge_category") or {}).get("category"))
    unm_ref = sum(1 for r in unm if (r.get("review") or {}).get("refusal"))
    unm_none = len(unm) - unm_cat - unm_ref
    sm = bj.get("summary") or {}
    print(f"{label:<14} {vocab:<7} {len(ex):>4} {n_cat:>4} {len(ex)-n_cat:>5} {100*n_cat/max(1,len(ex)):>4.0f}% | {len(lines):>5} {n_lcat:>5} | {len(rows):>7} {buckets.get('reconciled',0):>4} {len(unm):>4} {unm_cat:>7} {unm_ref:>7} {unm_none:>8} | {sm.get('n_categorized')}/{sm.get('n_uncategorized')} copies={copies}")
    out["months"][label] = {
        "id": bid, "vocab": vocab, "n_expenses": len(ex), "n_copies": copies, "n_categorized": n_cat,
        "n_lines": len(lines), "n_lines_categorized": n_lcat, "n_charges": len(rows), "buckets": dict(buckets),
        "unmatched_categorized": unm_cat, "unmatched_refused": unm_ref, "unmatched_no_answer": unm_none,
        "screen_n_categorized": sm.get("n_categorized"), "screen_n_uncategorized": sm.get("n_uncategorized"),
    }
    if vocab != "gl":
        continue
    for e in ex:
        li = e.get("line_items") or []
        comp = company_of(e.get("legal_entity_id"))
        vend = (e.get("vendor") or {}).get("display") or (e.get("vendor") or {}).get("raw")
        rv = e.get("review") or {}
        uncat_lines = [x for x in li if not x.get("category")]
        if not li or uncat_lines:
            refusal = rv.get("refusal") or ("no_line_items" if not li else ("partial:" + str(rv.get("reason_code")) if len(uncat_lines) < len(li) else str(rv.get("reason_code"))))
            gl_rows.append({
                "month": label, "doc": e.get("document_id"), "company": comp, "entity_source": e.get("entity_source"),
                "vendor": vend, "sugg_vendor": sugg_vendor(vend), "refusal": refusal, "reason_code": rv.get("reason_code"),
                "n_lines": len(li), "n_uncat_lines": len(uncat_lines), "total": str(e.get("total")), "currency": e.get("currency"),
                "uncat_amount": str(sum(dec(x.get("line_total")) for x in uncat_lines)),
                "card": (e.get("card") or {}).get("key"), "card_source": e.get("card_source"), "card_ending": e.get("card_ending"),
                "reference": e.get("reference"), "without_charge": e.get("without_charge"), "waits_for": e.get("waits_for_statements"),
                "boxes": e.get("boxes"), "confidences": [x.get("confidence") for x in uncat_lines],
                "uncat_desc": [x.get("description") for x in uncat_lines][:3],
                "mem_rule": mem_rule_for(vend, comp),
            })
    for r in unm:
        cc = r.get("charge_category") or {}
        rv = r.get("review") or {}
        comp = company_of(r.get("legal_entity_id"))
        charge_rows.append({
            "month": label, "tx": r.get("transaction_id"), "company": comp, "vendor": r.get("vendor"),
            "sugg_vendor": sugg_vendor(r.get("vendor")), "amount": r.get("amount"), "currency": r.get("currency"),
            "category": cc.get("category"), "source": cc.get("source"), "refusal": rv.get("refusal"),
            "entry_status": r.get("entry_status"), "reason_code": rv.get("reason_code"), "card": r.get("coverage_key"),
            "mem_rule": mem_rule_for(r.get("vendor"), comp),
        })

# ---- refusal breakdown ------------------------------------------------------
print("\n=== GL MONTHS: uncategorized RECEIPTS by refusal x month (rows; uncategorized line amounts)")
by = defaultdict(lambda: defaultdict(lambda: [0, Decimal(0)]))
for g in gl_rows:
    by[g["refusal"]][g["month"]][0] += 1
    by[g["refusal"]][g["month"]][1] += dec(g["uncat_amount"])
for ref, per in sorted(by.items(), key=lambda kv: -sum(v[0] for v in kv[1].values())):
    print(f"  {ref:<36} total={sum(v[0] for v in per.values()):>3}  " + "  ".join(f"{m}={v[0]}" for m, v in sorted(per.items())))
out["gl_refusals"]["by_refusal_month"] = {k: {m: [v[0], str(v[1])] for m, v in per.items()} for k, per in by.items()}

print("\n=== by refusal x company")
byc = Counter((g["refusal"], g["company"]) for g in gl_rows)
for (ref, comp), n in sorted(byc.items(), key=lambda kv: -kv[1]):
    print(f"  {ref:<36} {str(comp):<20} {n}")

print("\n=== top vendors per refusal (rows)")
for ref in by:
    vc = Counter((g["sugg_vendor"] or norm(g["vendor"])[:28]) for g in gl_rows if g["refusal"] == ref)
    print(f"  {ref}: " + ", ".join(f"{v}={n}" for v, n in vc.most_common(14)))

# ---- no-company rows: paths ------------------------------------------------
print("\n=== entity_missing rows: what could give them a company")
em = [g for g in gl_rows if g["refusal"] == "entity_missing"]
paths = Counter()
for g in em:
    if g["company"]:
        k = "shows a company already (item 206 sweep at next edit/re-match)"
    elif g["card"]:
        k = "card resolved but no company (card without entity)"
    elif g["card_ending"]:
        k = "printed card ending, not in registry"
    elif g["reference"] and re.search(r"[A-Z0-9]{6,}-\d{3,}", g["reference"] or ""):
        k = "no card; Stripe-style billing account in reference (item 204 account key)"
    elif g["sugg_vendor"]:
        k = "no card; vendor in the item-180 list (a vendor->company convention could answer)"
    else:
        k = "no card, no account, not a listed vendor (person must pick)"
    paths[k] += 1
for k, n in paths.most_common():
    print(f"  {n:>3}  {k}")
out["levers"]["entity_missing_paths"] = dict(paths)
print("  entity_missing rows waiting for a statement:", sum(1 for g in em if g["waits_for"]))
print("  entity_missing by card_source:", Counter(g["card_source"] for g in em))
print("  entity_missing vendors:", Counter(g["sugg_vendor"] or norm(g["vendor"])[:24] for g in em).most_common(20))

# ---- model unsure rows: would the item-180 account decide them? ------------
print("\n=== account_unresolved (model unsure) rows: coverage by the item-180 per-company account list")
au = [g for g in gl_rows if g["refusal"] == "account_unresolved"]
cov = Counter()
decided = []
for g in au:
    v = g["sugg_vendor"]
    code = sugg.get((v, g["company"])) if v else None
    if code:
        cov["decided by a listed (vendor, company) account"] += 1
        decided.append((g["month"], g["company"], v, code, g["uncat_amount"], g["currency"]))
    elif v:
        cov["vendor listed, no code for this company"] += 1
    else:
        cov["vendor not in the list"] += 1
for k, n in cov.most_common():
    print(f"  {n:>3}  {k}")
print("  confidences on unsure lines:", Counter(round(c or 0, 1) for g in au for c in g["confidences"]).most_common())
print("  unsure but NOT a listed vendor:", Counter(norm(g["vendor"])[:26] for g in au if not g["sugg_vendor"]).most_common(25))
out["levers"]["account_unresolved_coverage"] = dict(cov)
out["levers"]["account_unresolved_decided_rows"] = decided

# ---- seeded memory rules ---------------------------------------------------
print("\n=== memory rules that would answer refused/unsure rows (recall: own company, then no-company)")
mc = Counter()
for g in gl_rows:
    r = g["mem_rule"]
    if r:
        kind, key, cat, acc, seeded, val = r
        code = cl.code_of(acc, ORG.get(g["company"] or "")) if acc and g["company"] else None
        postable = cl.is_postable(ORG.get(g["company"] or ""), code) if code else False
        mc[(g["refusal"], "seeded" if seeded else "taught", "account resolves+postable" if postable else ("account names nothing here" if acc else "no account"))] += 1
for k, n in sorted(mc.items(), key=lambda kv: -kv[1]):
    print(f"  {n:>3}  {k}")
out["levers"]["memory_rule_reach"] = {" | ".join(k): n for k, n in mc.items()}

# ---- partial lines ---------------------------------------------------------
print("\n=== partially categorized receipts (some lines have a category, others not)")
part = [g for g in gl_rows if 0 < g["n_uncat_lines"] < g["n_lines"]]
print("  rows:", len(part), " uncategorized lines:", sum(g["n_uncat_lines"] for g in part),
      " amount by ccy:", {c: str(sum(dec(g["uncat_amount"]) for g in part if g["currency"] == c)) for c in {g["currency"] for g in part}})
print("  sample line descriptions:", [d for g in part[:12] for d in g["uncat_desc"]][:16])

# ---- charges ---------------------------------------------------------------
print("\n=== GL MONTHS: receiptless charges (unmatched rows)")
cc = Counter((c["month"], "categorized" if c["category"] else ("refused:" + str(c["refusal"]) if c["refusal"] else "no answer (" + str(c["entry_status"]) + ")")) for c in charge_rows)
for k, n in sorted(cc.items()):
    print(f"  {k[0]:<14} {k[1]:<40} {n}")
print("  charge category sources:", Counter(c["source"] for c in charge_rows if c["category"]))
print("  refused charges by vendor:", Counter(c["sugg_vendor"] or norm(c["vendor"])[:24] for c in charge_rows if c["refusal"]).most_common(20))
print("  categorized charges by vendor (top):", Counter(c["sugg_vendor"] or norm(c["vendor"])[:24] for c in charge_rows if c["category"]).most_common(20))
print("  categorized charge codes (top):", Counter(c["category"] for c in charge_rows if c["category"]).most_common(15))

out["gl_rows"] = gl_rows
out["charge_rows"] = charge_rows
out["suggestions"] = {f"{v}|{c}": code for (v, c), code in sugg.items()}
(S / "analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("\nwrote", S / "analysis.json", "gl_rows", len(gl_rows), "charge_rows", len(charge_rows), "sugg", len(sugg))
