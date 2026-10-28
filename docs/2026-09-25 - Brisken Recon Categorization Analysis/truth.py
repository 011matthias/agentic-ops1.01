"""Ground truth: Criss's own Zoho Books postings (24-month pull on disk,
2026-09-18) joined to the live months' charge rows, offline.

For every charge the tool holds on a GL month, find the Zoho expense Criss
entered for it (same company, same amount, date within 3 days, best
descriptor overlap), then compare the account the tool answers with the
account she posted to. Also scores the item-180 suggestion list and the
seeded memory rules against the same truth. No network.
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from expense_recon.zoho import curated_leaves as cl

S = Path(os.environ["RECON_DIR"])
ZOHO = Path(os.environ["ZOHO_JSON"])
SUGG = Path(os.environ["SUGG_MD"])
ORG = {"Cloud Services": "697686691", "Consulting": "808232536", "Corporate Services": "822741658"}
ORG_NAME = {v: k for k, v in ORG.items()}

settings = json.loads((S / "settings.json").read_text(encoding="utf-8"))
LABELS = {}
for c in settings.get("account_companies") or []:
    for lab in c.get("labels") or []:
        LABELS[lab] = c["label"]
    LABELS[c["label"]] = c["label"]


def company_of(label):
    return LABELS.get(label, label) if label else None


def dec(x):
    try:
        return Decimal(str(x).replace(",", "")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def toks(s):
    return {t for t in norm(s).split() if len(t) >= 3 and t not in {"inc", "llc", "ltd", "com", "the", "and"}}


EXTRA_ALIASES = {
    "SendGrid (Twilio)": ["sendgrid", "twilio"], "Microsoft 365": ["microsoft", "msft"],
    "Google Workspace": ["google workspace", "gsuite", "workspace brisken", "google llc"],
    "Google Cloud": ["google cloud", "google  cloud", "google *cloud"], "Trello (Atlassian)": ["trello", "atlassian"],
    "Afi (M365 backup)": ["afi technologies", "afi "], "Wispr Flow": ["wispr"], "Hugging Face": ["hugging"],
    "Network Solutions": ["network solutions", "networksolutions"], "Host Europe": ["host europe", "hosteurope"],
    "OpenAI": ["openai", "chatgpt"], "Anthropic": ["anthropic", "antropic"], "Lovable": ["lovable"], "Redis": ["redis"],
    "Zoho": ["zoho"], "ElevenLabs": ["elevenlabs", "eleven labs"], "DigitalOcean": ["digitalocean", "digital ocean"],
    "GitHub": ["github"], "GoDaddy": ["godaddy", "go daddy"], "Base44": ["base44"], "Bloomberg": ["bloomberg"],
    "Supabase": ["supabase"], "Railway": ["railway"], "Vercel": ["vercel"], "Resend": ["resend"], "Rize": ["rize"],
    "Fireflies": ["fireflies"], "OpenRouter": ["openrouter"], "Cursor": ["cursor"], "Obsidian": ["obsidian"],
    "Perplexity": ["perplexity"], "Pressmaster": ["pressmaster"], "Proton": ["proton"], "Typora": ["typora"], "Wix": ["wix"],
    "Brave": ["brave"], "Adobe": ["adobe"], "AWS": ["amazon web services", "aws"], "ServerPilot": ["serverpilot"],
    "Hostinger": ["hostinger"], "Canva": ["canva"], "Slack": ["slack"], "Namecheap": ["namecheap"],
    "Registro.br": ["registro br", "registro.br"],
}
sugg, sugg_alias = {}, {}
for line in SUGG.read_text(encoding="utf-8").splitlines():
    if not line.startswith("| ") or line.startswith("| Vendor") or line.startswith("|---"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 4 or cells[1] not in ORG:
        continue
    if re.match(r"^E\d", cells[2]):
        sugg[(cells[0], cells[1])] = cells[2]
    sugg_alias[cells[0]] = [a.lower() for a in (EXTRA_ALIASES.get(cells[0]) or [norm(cells[0].split("(")[0])])]


def sugg_vendor(text):
    t = (text or "").lower()
    best = None
    for v, aliases in sugg_alias.items():
        for a in aliases:
            if a and a in t and (best is None or len(a) > best[1]):
                best = (v, len(a))
    return best[0] if best else None


memory = json.loads((S / "memory.json").read_text(encoding="utf-8"))
mem = {}
for v in memory.get("by_vendor") or []:
    for c in v.get("companies") or []:
        mem[(company_of(c.get("entity")) or "", v.get("vendor"))] = (c.get("category"), c.get("zoho_account"), bool(c.get("seeded")), bool(c.get("validated")))


def mem_rule(vendor_text, company):
    vn = norm(vendor_text)
    t = vn.split()
    cands = [" ".join(t[:k]) for k in range(len(t), 0, -1)]
    for key in cands:
        if (company or "", key) in mem:
            return ("company", key) + mem[(company or "", key)]
    if company:
        for key in cands:
            if ("", key) in mem:
                return ("no_company", key) + mem[("", key)]
    return None


# ---- truth --------------------------------------------------------------
z = json.loads(ZOHO.read_text(encoding="utf-8"))
truth = []  # dict per Zoho expense in 2026-07..09 for the three orgs
for org, blk in z["orgs"].items():
    if org not in ORG_NAME:
        continue
    for e in blk.get("expenses") or []:
        d = str(e.get("date") or "")
        if not d.startswith(("2026-07", "2026-08", "2026-09")):
            continue
        acc = e.get("account_name")
        code = cl.code_of(acc, org)
        truth.append({
            "org": org, "company": ORG_NAME[org], "date": date.fromisoformat(d), "total": dec(e.get("total")),
            "currency": e.get("currency_code"), "desc": e.get("description") or "", "vendor": e.get("vendor_name") or "",
            "account": acc, "code": code, "postable": cl.is_postable(org, code) if code else None,
            "paid_through": e.get("paid_through_account_name"), "ref": e.get("reference_number"), "id": e.get("expense_id"),
        })
print("=== TRUTH: Zoho expenses Jul-Sep 2026 per company (count; account resolves to a curated code; postable)")
for comp in ORG:
    rows = [t for t in truth if t["company"] == comp]
    for m in ("2026-07", "2026-08", "2026-09"):
        mm = [t for t in rows if str(t["date"]).startswith(m)]
        if mm:
            print(f"  {comp:<20} {m}  n={len(mm):>3}  code_resolves={sum(1 for t in mm if t['code'])}  postable={sum(1 for t in mm if t['postable'])}  paid_through={Counter(t['paid_through'] for t in mm).most_common(3)}")
unres = Counter((t["company"], t["account"]) for t in truth if not t["code"])
if unres:
    print("  truth accounts that resolve to NO curated code:", unres.most_common())
notpost = Counter((t["company"], t["account"]) for t in truth if t["code"] and not t["postable"])
if notpost:
    print("  truth accounts marked N (not postable) in the curated list:", notpost.most_common())

# ---- tool rows ------------------------------------------------------------
batches = json.loads((S / "batches.json").read_text(encoding="utf-8"))
items = batches.get("batches") if isinstance(batches, dict) else batches
rows = []
for b in items:
    bid = b.get("id") or b.get("run_id")
    bj = json.loads((S / f"batch_{bid}.json").read_text(encoding="utf-8"))
    if bj.get("category_vocabulary") != "gl":
        continue
    rj = json.loads((S / f"run_{bid}.json").read_text(encoding="utf-8"))
    for r in rj.get("rows") or []:
        if r.get("effective_bucket") in ("refund",):
            continue
        pc = r.get("posting_category") or {}
        rv = r.get("review") or {}
        rows.append({
            "month": b.get("label"), "tx": r.get("transaction_id"), "company": company_of(r.get("legal_entity_id")),
            "date": date.fromisoformat(r["date"]) if r.get("date") else None, "amount": dec(r.get("amount")), "currency": r.get("currency"),
            "vendor": r.get("vendor") or "", "bucket": r.get("effective_bucket"), "card": r.get("coverage_key"),
            "code": pc.get("category"), "account": pc.get("zoho_account"), "source": pc.get("source"),
            "refusal": rv.get("refusal"), "entry_status": r.get("entry_status"), "reason_code": rv.get("reason_code"),
            "sugg_vendor": sugg_vendor(r.get("vendor")),
        })
print(f"\ntool charge rows on GL months (refunds excluded): {len(rows)}; by month {Counter(r['month'] for r in rows)}")

# ---- join -------------------------------------------------------------------
used = set()
pairs = []
cands_all = []
for i, r in enumerate(rows):
    if r["amount"] is None or r["date"] is None:
        continue
    for j, t in enumerate(truth):
        if t["company"] != r["company"] or t["total"] != r["amount"]:
            continue
        dd = abs((t["date"] - r["date"]).days)
        if dd > 3:
            continue
        ov = len(toks(r["vendor"]) & (toks(t["desc"]) | toks(t["vendor"])))
        cands_all.append((dd, -ov, i, j))
cands_all.sort()
matched_r, matched_t = {}, set()
for dd, negov, i, j in cands_all:
    if i in matched_r or j in matched_t:
        continue
    matched_r[i] = (j, dd, -negov)
    matched_t.add(j)
print(f"joined: {len(matched_r)} tool rows <-> Zoho rows; truth rows unjoined: {len(truth)-len(matched_t)}")
print("  join quality: date diff", Counter(v[1] for v in matched_r.values()), " descriptor overlap>0:", sum(1 for v in matched_r.values() if v[2] > 0))
unj_truth = [t for j, t in enumerate(truth) if j not in matched_t]
print("  unjoined truth by company/month:", Counter((t["company"], str(t["date"])[:7]) for t in unj_truth))
print("  unjoined truth sample:", [(str(t["date"]), t["company"], t["desc"][:22], str(t["total"]), t["paid_through"][:24] if t["paid_through"] else None) for t in unj_truth[:12]])
unj_rows = [r for i, r in enumerate(rows) if i not in matched_r]
print("  unjoined tool rows by month/company:", Counter((r["month"], r["company"]) for r in unj_rows))

# ---- compare ----------------------------------------------------------------
def verdict(r, t):
    if r["refusal"]:
        return "engine refused"
    if not r["code"]:
        return "no answer"
    return "agree" if r["code"] == t["code"] else "disagree"

res = []
for i, (j, dd, ov) in matched_r.items():
    r, t = rows[i], truth[j]
    v = verdict(r, t)
    res.append({**{k: r[k] for k in ("month", "company", "vendor", "bucket", "code", "account", "source", "refusal", "entry_status", "sugg_vendor", "amount", "currency", "card")},
                "truth_code": t["code"], "truth_account": t["account"], "truth_postable": t["postable"], "verdict": v, "date_diff": dd})

print("\n=== ENGINE vs CRISS (joined rows), by month")
for m in sorted({x["month"] for x in res}):
    c = Counter(x["verdict"] for x in res if x["month"] == m)
    print(f"  {m:<14} " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))
print("\n=== by answer source (matched receipt line vs receiptless guess)")
c = Counter((x["bucket"], x["source"], x["verdict"]) for x in res)
for k, n in sorted(c.items(), key=lambda kv: (kv[0][0], kv[0][1] or "", kv[0][2])):
    print(f"  {k[0]:<11} {str(k[1]):<14} {k[2]:<15} {n}")
answered = [x for x in res if x["verdict"] in ("agree", "disagree")]
print(f"\n  ACCURACY on answered rows: {sum(1 for x in answered if x['verdict']=='agree')}/{len(answered)}")
for src in sorted({x["source"] for x in answered}, key=str):
    a = [x for x in answered if x["source"] == src]
    print(f"    source {str(src):<14} {sum(1 for x in a if x['verdict']=='agree')}/{len(a)}")

print("\n=== DISAGREEMENTS (vendor | company | engine -> Criss)")
dis = Counter((x["sugg_vendor"] or norm(x["vendor"])[:22], x["company"], x["code"], x["truth_code"]) for x in res if x["verdict"] == "disagree")
for (v, comp, ec, tc), n in dis.most_common(40):
    print(f"  {n:>2}  {v:<22} {comp:<19} {ec} ({cl.binding(ec, ORG[comp]).name if cl.binding(ec, ORG[comp]) else '?'})  ->  {tc} ({cl.binding(tc, ORG[comp]).name if tc and cl.binding(tc, ORG[comp]) else '?'})")

print("\n=== per-vendor truth (joined rows): which account Criss uses, and how the engine did")
pv = defaultdict(Counter)
for x in res:
    pv[(x["sugg_vendor"] or norm(x["vendor"])[:22], x["company"])][(x["truth_code"], x["verdict"])] += 1
for (v, comp), c in sorted(pv.items(), key=lambda kv: -sum(kv[1].values()))[:45]:
    print(f"  {v:<22} {comp:<19} " + ", ".join(f"{tc}:{vd}={n}" for (tc, vd), n in c.most_common()))

# ---- lever precision --------------------------------------------------------
print("\n=== LEVER PRECISION vs Criss (joined rows)")
sc = Counter()
for x in res:
    code = sugg.get((x["sugg_vendor"], x["company"])) if x["sugg_vendor"] else None
    if code:
        sc[("item-180 suggestion", "agree" if code == x["truth_code"] else "disagree", x["verdict"])] += 1
for k, n in sorted(sc.items()):
    print(f"  {k[0]:<22} suggestion {k[1]:<9} (engine today: {k[2]:<15}) {n}")
mc = Counter()
mdis = Counter()
for x in res:
    r = mem_rule(x["vendor"], x["company"])
    if not r:
        continue
    kind, key, cat, acc, seeded, val = r
    code = cl.code_of(acc, ORG[x["company"]]) if acc else None
    if not code:
        mc[("memory rule", "seeded" if seeded else "taught", "names no leaf here", x["verdict"])] += 1
        continue
    ok = code == x["truth_code"]
    mc[("memory rule", "seeded" if seeded else "taught", "agree" if ok else "disagree", x["verdict"])] += 1
    if not ok:
        mdis[(key, x["company"], code, x["truth_code"])] += 1
for k, n in sorted(mc.items()):
    print(f"  {k[0]:<12} {k[1]:<7} {k[2]:<20} (engine today: {k[3]:<15}) {n}")
if mdis:
    print("  memory rule disagreements:", mdis.most_common(15))

# ---- unanswered rows Criss booked -------------------------------------------
print("\n=== rows the tool left without an account but Criss booked (joined): by reason")
c = Counter((x["verdict"], x["refusal"] or x["entry_status"], x["sugg_vendor"] or norm(x["vendor"])[:20]) for x in res if x["verdict"] in ("engine refused", "no answer"))
for k, n in c.most_common(30):
    print(f"  {n:>2} {k}")

(S / "truth.json").write_text(json.dumps({"res": res, "unjoined_truth": [dict(t, date=str(t["date"]), total=str(t["total"])) for t in unj_truth],
                                          "unjoined_rows": [dict(r, date=str(r["date"]), amount=str(r["amount"])) for r in unj_rows]},
                                         ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("\nwrote", S / "truth.json")
