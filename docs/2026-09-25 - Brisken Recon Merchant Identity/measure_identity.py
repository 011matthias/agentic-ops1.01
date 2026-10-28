"""Item 216 cause 3: identity reach before/after + every merge the resolver makes.
Offline: payloads + the 24-month Zoho pull. No network, no model."""
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from expense_recon import merchant_registry as mr
from expense_recon.learning.consult import MerchantCategoryLookup
from expense_recon.learning.store import MerchantCategory, normalize_vendor
from expense_recon.merchant_identity import MerchantIdentityResolver, identity_key
from expense_recon.vendor_names import clean_vendor_name

P = Path(os.environ["PAYLOADS"])
ZOHO = Path(os.environ["ZOHO_JSON"])
settings = json.loads((P / "settings.json").read_text(encoding="utf-8"))
memory = json.loads((P / "memory.json").read_text(encoding="utf-8"))
reg_new = mr.MerchantRegistry.from_settings(settings)


class OldRegistry(mr.MerchantRegistry):
    def _probe_pairs(self, vendor_clean, vendor_raw):
        seen, out = set(), []
        for raw in (vendor_clean, clean_vendor_name(vendor_raw), vendor_raw):
            norm = normalize_vendor(str(raw)) if raw else ""
            if norm and norm not in seen:
                seen.add(norm)
                out.append((norm, str(raw)))
        return out


reg_old = OldRegistry(settings.get("merchants"))
ident = MerchantIdentityResolver(reg_new)

rows = []
for v in memory["by_vendor"]:
    for c in v["companies"]:
        rows.append(MerchantCategory(
            legal_entity_id=c.get("entity") or "", vendor_norm=v["vendor"],
            category=c.get("category") or None, zoho_account=c.get("zoho_account") or None,
            decision_count=c.get("count") or 1, last_confirmed_at=c.get("last"),
            source_run=("zoho-seed:x" if c.get("seeded") else "run:x"),
            validated_at=c.get("validated") or None, validated_by=c.get("validated_by") or None))


class OldLookup(MerchantCategoryLookup):
    def recall(self, entity, vendor):  # exact normalized key, as before
        if not vendor:
            return None
        vn = normalize_vendor(vendor)
        e = (entity or "").strip()
        h = self._by_key.get((e, vn))
        if h is not None and h.category:
            return ("company", h.vendor_norm, h.category, h.zoho_account)
        if e:
            n = self._by_key.get(("", vn))
            if n is not None and n.category:
                return ("no_company", n.vendor_norm, n.category, n.zoho_account)
        return None


lk_old = OldLookup(rows)
lk_new = MerchantCategoryLookup(rows, identity=ident)


def rc(x):
    return None if x is None else (x.kind, x.rows[0].vendor_norm, x.category, x.zoho_account)


# ---- human canonical (my reading of each name) --------------------------------
HUMAN = [
    (r"anthropic|claude", "Anthropic"), (r"lovable", "Lovable"), (r"wispr", "Wispr Flow"),
    (r"rize", "Rize"), (r"openrouter", "OpenRouter"), (r"railway", "Railway"),
    (r"^amazon web services|aws", "Amazon Web Services"), (r"amazon|amz\*", "Amazon"),
    (r"lidl", "LIDL"), (r"atacadao popular", "Atacadao Popular"), (r"nathalia", "Nathalia Bezerra"),
    (r"cantinho", "Cantinho Abencoado"), (r"jose claudio", "Jose Claudio Cavalcanti"),
    (r"vercel", "Vercel"), (r"petrocal", "Petrocal"), (r"brave", "Brave"), (r"zoho", "Zoho"),
    (r"pressmaster", "Pressmaster"), (r"wi-fi onboard", "LATAM Wi-Fi"), (r"openai|chatgpt", "OpenAI"),
    (r"^sap ", "SAP"), (r"networksolutions|network solutions", "Network Solutions"),
    (r"base44", "Base44"), (r"bloomberg", "Bloomberg"), (r"adobe", "Adobe"), (r"regus", "Regus"),
    (r"resend", "Resend"), (r"saasrise", "SaaSRise"), (r"proton", "Proton"),
    (r"annual membership fee", "Chase card fee"), (r"sendgrid|twilio", "Twilio SendGrid"),
    (r"github", "GitHub"), (r"serverpilot", "ServerPilot"), (r"linkedin", "LinkedIn"),
    (r"mega cente", "Mega Center"), (r"microsoft", "Microsoft"), (r"at&|att\*", "AT&T"),
    (r"wix", "Wix"), (r"godaddy", "GoDaddy"), (r"google\*play", "Google Play"),
    (r"google \*cloud", "Google Cloud"), (r"digitalocean", "DigitalOcean"), (r"afi tech", "Afi"),
    (r"elevenlabs|eleven labs", "ElevenLabs"), (r"easypark", "EasyPark"),
]


def human(name):
    t = (name or "").lower()
    for pat, h in HUMAN:
        if re.search(pat, t):
            return h
    return name


MONTHS = {"50622baec444": "Jul", "074a7b8905d7": "Aug", "51a22ad72864": "Sep"}
names = json.loads((P.parent / "names.json").read_text(encoding="utf-8"))
recs, charges = names["receipts"], names["charges"]

print("=== 55 model-unsure receipts")
for r in recs:
    r["reg_old"] = (lambda m: m.canonical_name if m else None)(reg_old.resolve(r["display"], r["raw"]))
    r["reg_old_raw"] = (lambda m: m.canonical_name if m else None)(reg_old.resolve(None, r["raw"]))
    r["reg_new"] = (lambda m: m.canonical_name if m else None)(reg_new.resolve(None, r["raw"]))
    i = ident.resolve(None, r["raw"])
    r["key"] = i.key if i else ""
    r["mem_old"] = lk_old.recall(r["entity"], r["raw"])
    r["mem_new"] = rc(lk_new.recall(r["entity"], r["raw"]))
    r["human"] = human(r["raw"])
print(f"registry live {sum(r['source'] == 'registry' for r in recs)}  "
      f"probe old (display,raw) {sum(bool(r['reg_old']) for r in recs)}  "
      f"old (None,raw) {sum(bool(r['reg_old_raw']) for r in recs)}  "
      f"new (None,raw) {sum(bool(r['reg_new']) for r in recs)}")
print(f"memory recall old {sum(bool(r['mem_old']) for r in recs)}  new {sum(bool(r['mem_new']) for r in recs)}")
print("per name: raw | human | reg_old | reg_new | key | mem_old | mem_new")
for k, n in Counter((r["raw"], r["human"], r["reg_old"], r["reg_new"], r["key"],
                     str(r["mem_old"] and r["mem_old"][:2]), str(r["mem_new"] and r["mem_new"][:2]))
                    for r in recs).most_common():
    print(" ", n, k)

print("\n=== 164 guessed charges")
for c in charges:
    c["reg_old"] = (lambda m: m.canonical_name if m else None)(reg_old.resolve(None, c["desc"]))
    c["reg_new"] = (lambda m: m.canonical_name if m else None)(reg_new.resolve(None, c["desc"]))
    i = ident.resolve(None, c["desc"])
    c["key"] = i.key if i else ""
    c["mem_old"] = lk_old.recall(c["entity"], c["desc"])
    c["mem_new"] = rc(lk_new.recall(c["entity"], c["desc"]))
    c["human"] = human(c["desc"])
print(f"registry old {sum(bool(c['reg_old']) for c in charges)} new {sum(bool(c['reg_new']) for c in charges)}; "
      f"memory old {sum(bool(c['mem_old']) for c in charges)} new {sum(bool(c['mem_new']) for c in charges)}")
for k, n in Counter((c["desc"], c["human"], c["reg_new"], c["key"], str(c["mem_new"] and c["mem_new"][:2]))
                    for c in charges).most_common():
    print(" ", n, k)

print("\n=== identity consistency per human merchant (receipts + guessed charges): distinct keys before -> after")
per = defaultdict(lambda: [set(), set(), 0])
for x in recs + charges:
    name = x.get("raw") or x.get("desc")
    h = x["human"]
    per[h][0].add(normalize_vendor(name))
    per[h][1].add(x["key"])
    per[h][2] += 1
multi = [(h, len(a), len(b), n, sorted(b)) for h, (a, b, n) in per.items() if len(a) > 1 or len(b) > 1]
for h, a, b, n, keys in sorted(multi, key=lambda t: -t[3]):
    print(f"  {h:<22} rows={n:<3} spellings {a} -> keys {b}  {keys}")
one_before = sum(n for h, (a, b, n) in per.items() if len(a) == 1)
one_after = sum(n for h, (a, b, n) in per.items() if len(b) == 1)
print(f"  rows whose merchant has ONE key: before {one_before}, after {one_after}, of {sum(v[2] for v in per.values())}")

# ---- every merge over all strings ------------------------------------------------
print("\n=== every merge identity_key makes (all vendor strings: 3 months + memory keys + 24-month Zoho)")
strings = Counter()
zoho_vn = defaultdict(Counter)  # key -> Criss's vendor names
for bid in MONTHS:
    bj = json.loads((P / f"batch_{bid}.json").read_text(encoding="utf-8"))
    rj = json.loads((P / f"run_{bid}.json").read_text(encoding="utf-8"))
    for e in bj.get("expenses") or []:
        v = e.get("vendor") or {}
        for s in (v.get("raw"), v.get("display")):
            if s:
                strings[s] += 1
    for r in rj.get("rows") or []:
        if r.get("vendor"):
            strings[r["vendor"]] += 1
for r in rows:
    strings[r.vendor_norm] += 1
z = json.loads(ZOHO.read_text(encoding="utf-8"))
for oid, o in z["orgs"].items():
    for e in o["expenses"]:
        d = (e.get("description") or "").split("\n")[0].strip()
        if d:
            strings[d] += 1
            if e.get("vendor_name"):
                zoho_vn[identity_key(d)][e["vendor_name"]] += 1
        if e.get("vendor_name"):
            strings[e["vendor_name"]] += 1
    for b in o["bills"]:
        if b.get("vendor_name"):
            strings[b["vendor_name"]] += 1
groups = defaultdict(set)
for s in strings:
    k = identity_key(s)
    if k:
        groups[k].add(normalize_vendor(s))
merges = {k: v for k, v in groups.items() if len(v) > 1}
print(f"  {len(strings)} distinct strings -> {len(groups)} keys; {len(merges)} keys merge 2+ spellings")
for k in sorted(merges):
    vn = zoho_vn.get(k)
    vset = {identity_key(n) for n in (vn or {})}
    flag = "  <-- Zoho vendor names differ: " + str(dict(vn)) if len(vset) > 1 else ""
    print(f"  {k!r}: {sorted(merges[k])}{flag}")

# ---- registry: what the new probe changes ------------------------------------------
print("\n=== registry resolve old vs new over every string")
chg = []
for s in strings:
    a, b = reg_old.resolve(None, s), reg_new.resolve(None, s)
    ca, cb = (a.canonical_name if a else None), (b.canonical_name if b else None)
    if ca != cb:
        chg.append((s, ca, cb, b.kind if b else None, round(b.score, 1) if b else None))
for t in sorted(chg, key=lambda t: str(t[2])):
    print("  ", t)
print("  changed:", len(chg), " of which a DIFFERENT canonical (not None->X):", sum(1 for t in chg if t[1]))

# ---- memory folds ----------------------------------------------------------------
print("\n=== memory: rules per identity (folds)")
for f in lk_new.folds:
    print("  ", "FOLD" if f.decided else "REFUSED", f.legal_entity_id or "(no company)", repr(f.key), f.vendor_norms,
          f.category, f.zoho_account)
per_ident = Counter((r.legal_entity_id, ident.key(r.vendor_norm)) for r in rows)
print(f"  {len(rows)} rules -> {len(per_ident)} (company, merchant) identities; "
      f"{sum(n - 1 for n in per_ident.values() if n > 1)} rows would merge")
