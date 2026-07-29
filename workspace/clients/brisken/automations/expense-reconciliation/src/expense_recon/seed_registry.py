"""Seed the canonical merchant registry from existing data (2026-07-29).

One-time bootstrap for `settings["merchants"]`: cluster the raw vendor
strings across existing Zoho Expense Report (ER) files, pick a canonical
brand per cluster, and set each merchant's default category from the ER's
own `zoho_category` label. The output is the exact `settings["merchants"]`
shape; apply it via `PUT /api/settings` (or the Merchants editor).

Deterministic + LLM-free: it reads the ER PDF's machine-readable EXPENSE
SUMMARY (the same text-layer parser `reconcile()` uses), so seeding a
month's worth of reports costs nothing and never calls a model.

Clustering: group raw vendors by normalized key, then merge groups whose
cleaned brands match on rapidfuzz `token_set_ratio` (the same instrument
the live resolver uses). The most frequent raw in a cluster names the
canonical (brand-cleaned); the others become aliases. The category is the
bucket the majority ER label maps to; when no label clearly maps, the
category is left None (B4: never guess a category into the seed) and only
the `zoho_account` label is kept.

Usage:
    # dry-run: print the merchants JSON for review (default)
    uv run python -m expense_recon.seed_registry --er-dir ./er-pdfs
    # write it to a file
    uv run python -m expense_recon.seed_registry --er-dir ./er-pdfs --out merchants.json
    # apply to a running settings API (production config change — deliberate)
    uv run python -m expense_recon.seed_registry --er-dir ./er-pdfs \
        --put https://brisken-expense-recon.fly.dev --code <login-code>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

from .matching.deterministic import _normalize as normalize_vendor
from .matching.types import Receipt
from .merchant_registry import DEFAULT_FUZZY_THRESHOLD, normalize_merchants_setting
from .vendor_names import clean_vendor_name

# ER account-label keyword -> one of EXPENSE_CATEGORIES. First match wins;
# order matters (travel before the generic ones). A label that matches
# nothing yields no category (the LLM fills it at generate time).
_BUCKET_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("travel", "airfare", "flight", "hotel", "lodging", "taxi", "train",
      "rail", "transport", "mileage", "car rental", "uber", "parking",
      "toll", "fuel"), "Travel & Transport"),
    (("meal", "food", "restaurant", "entertainment", "catering", "coffee",
      "dining"), "Meals & Entertainment"),
    (("software", "subscription", "saas", "license", "licence", "cloud",
      "hosting", "domain"), "Software & Subscriptions"),
    (("office", "supplies", "stationery", "stationary", "consumable",
      "printing"), "Office Supplies & Consumables"),
    (("equipment", "hardware", "computer", "laptop", "device", "furniture",
      "machinery"), "Equipment & Hardware"),
    (("marketing", "advertising", "advert", " ads ", "promotion", "campaign",
      "sponsorship"), "Marketing & Advertising"),
    (("professional", "consulting", "consultant", "legal", "accounting",
      "audit", "advisory", "notary", "service fee"), "Professional Services"),
    (("utilit", "premises", "rent", "electricity", "water", "internet",
      "telecom", "mobile"), "Utilities & Premises"),
)


def _label_leaf(label: str) -> str:
    """The most specific segment of a nested GL label. Brisken's chart nests
    the real category UNDER a parent ('E100010-31 - Travel Expense | Food'),
    so the LEAF after the last '|' (else after ' - ') carries the signal, not
    the parent. Without a leaf marker the whole label is returned."""
    s = label
    if "|" in s:
        s = s.rsplit("|", 1)[1]
    elif " - " in s:
        s = s.split(" - ", 1)[1]
    return s.strip()


def label_to_bucket(label: str | None) -> str | None:
    """Map an ER GL label to one of the fixed expense categories, or None when
    nothing clearly matches. Reads the LEAF segment first (so 'Travel Expense
    | Food' -> Meals via 'Food', not Travel via the parent), then falls back
    to the whole label."""
    if not label:
        return None
    for text in (_label_leaf(label), label):
        low = f" {text.lower()} "
        for keywords, bucket in _BUCKET_KEYWORDS:
            if any(k in low for k in keywords):
                return bucket
    return None


import re

# Vendor strings that are OCR / statement noise, not a merchant brand: an
# amount fragment ("BRL94.00"), an "Expense Location" tail, a bare payment
# processor / bank (a payment method, not the shop), or too few real
# characters to be a name. Dropped before clustering.
_AMOUNT_RE = re.compile(r"^[A-Za-z]{0,3}\s*[\d][\d.,]*$")
_NOISE_PREFIXES = ("expense location", "brl", "usd", "eur")
_PROCESSOR_BLOCKLIST = frozenset({
    "cielo", "ton", "pagbank", "rede", "stone", "getnet", "pix",
    "mercadopago", "picpay", "banco do brasil", "pagseguro",
})


def _is_noise_vendor(v: str) -> bool:
    s = (v or "").strip()
    if len(re.sub(r"[^a-z0-9]", "", s.lower())) < 3:
        return True
    if _AMOUNT_RE.match(s):
        return True
    low = s.lower()
    if any(low.startswith(p) for p in _NOISE_PREFIXES):
        return True
    if normalize_vendor(s) in _PROCESSOR_BLOCKLIST:
        return True
    return False


def _most_common(raws: list[str], counts: Counter) -> str:
    """The most frequent raw string (ties broken lexicographically)."""
    return sorted(set(raws), key=lambda x: (-counts[x], x))[0]


def cluster_receipts(
    receipts: list[Receipt],
    *,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
    min_count: int = 1,
) -> list[dict]:
    """Cluster raw vendor strings into merchants. Returns a list of
    `{canonical, aliases, category, zoho_account, count}`, most-frequent
    first. Pure + deterministic (no network, no model)."""
    raw_counts: Counter = Counter()
    raw_labels: dict[str, Counter] = {}
    for r in receipts:
        raw = (r.detected_vendor or "").strip()
        if not raw or _is_noise_vendor(raw):
            continue
        raw_counts[raw] += 1
        raw_labels.setdefault(raw, Counter())
        if r.zoho_category:
            raw_labels[raw][r.zoho_category.strip()] += 1

    # Exact groups by normalized key, then union groups whose cleaned brands
    # match on token_set_ratio. Union-find keyed on the sorted normalized
    # keys, smaller key as root => stable clusters run-to-run.
    groups: dict[str, list[str]] = {}
    for raw in raw_counts:
        key = normalize_vendor(raw)
        if key:
            groups.setdefault(key, []).append(raw)
    keys = sorted(groups)
    reps = {
        k: (clean_vendor_name(_most_common(groups[k], raw_counts))
            or _most_common(groups[k], raw_counts))
        for k in keys
    }
    parent = {k: k for k in keys}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            hi, lo = (ra, rb) if ra > rb else (rb, ra)
            parent[hi] = lo

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if fuzz.token_set_ratio(
                normalize_vendor(reps[a]), normalize_vendor(reps[b])
            ) >= threshold:
                union(a, b)

    clusters: dict[str, list[str]] = {}
    for k in keys:
        clusters.setdefault(find(k), []).extend(groups[k])

    out: list[dict] = []
    for raws in clusters.values():
        total = sum(raw_counts[r] for r in raws)
        if total < min_count:
            continue
        canonical_raw = _most_common(raws, raw_counts)
        canonical = clean_vendor_name(canonical_raw) or canonical_raw
        aliases: list[str] = []
        seen = {normalize_vendor(canonical)}
        for r in sorted(set(raws), key=lambda x: (-raw_counts[x], x)):
            nk = normalize_vendor(r)
            if nk and nk not in seen:
                seen.add(nk)
                aliases.append(r)
        label_counts: Counter = Counter()
        for r in raws:
            label_counts.update(raw_labels.get(r, {}))
        category = zoho_account = None
        if label_counts:
            top_label, _ = label_counts.most_common(1)[0]
            zoho_account = top_label
            category = label_to_bucket(top_label)
        out.append({
            "canonical": canonical,
            "aliases": aliases,
            "category": category,
            "zoho_account": zoho_account,
            "count": total,
        })
    out.sort(key=lambda c: (-c["count"], c["canonical"]))
    return out


def build_merchants(
    receipts: list[Receipt],
    *,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
    min_count: int = 1,
) -> dict:
    """The `settings["merchants"]` map seeded from `receipts`, validated into
    the stored shape."""
    merchants = {
        c["canonical"]: {
            "aliases": c["aliases"],
            "category": c["category"],
            "zoho_account": c["zoho_account"],
        }
        for c in cluster_receipts(receipts, threshold=threshold, min_count=min_count)
    }
    return normalize_merchants_setting(merchants)


# ── loading + CLI ───────────────────────────────────────────────────


def _load_from_er_dir(er_dir: Path, legal_entity_id: str) -> list[Receipt]:
    from .ingest.expense_report_pdf import parse_expense_report_pdf_tolerant

    receipts: list[Receipt] = []
    pdfs = sorted(p for p in er_dir.rglob("*.pdf"))
    for pdf in pdfs:
        parsed, _issues = parse_expense_report_pdf_tolerant(
            pdf, legal_entity_id=legal_entity_id
        )
        receipts.extend(parsed)
    print(f"parsed {len(receipts)} expense rows from {len(pdfs)} ER file(s)",
          file=sys.stderr)
    return receipts


def _load_from_json(path: Path, legal_entity_id: str) -> list[Receipt]:
    """A JSON list of {detected_vendor, zoho_category} (e.g. exported from a
    live run snapshot). Only those two fields drive the seed."""
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Receipt(
            document_id=str(i), legal_entity_id=legal_entity_id,
            detected_date=None, detected_total=None, detected_currency=None,
            detected_vendor=(row.get("detected_vendor") or row.get("vendor")),
            zoho_category=(row.get("zoho_category") or row.get("category")),
        )
        for i, row in enumerate(rows)
    ]


def _put_settings(base_url: str, code: str | None, merchants: dict) -> None:
    """Apply the seed to a running settings API (a production config change).
    Logs in for a bearer token, then PUTs {merchants}."""
    import urllib.request

    base = base_url.rstrip("/")

    def _req(path: str, payload: dict, token: str | None = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(
            f"{base}{path}", data=json.dumps(payload).encode(),
            headers=headers, method=("PUT" if path.endswith("settings") else "POST"),
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or "{}")

    if not code:
        raise SystemExit("--put requires --code (the settings login code)")
    token = _req("/api/login", {"code": code}).get("token")
    if not token:
        raise SystemExit("login failed: no token returned")
    _req("/api/settings", {"merchants": merchants}, token=token)
    print(f"applied {len(merchants)} merchants to {base}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Seed the merchant registry.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--er-dir", help="directory of Zoho ER PDFs")
    src.add_argument("--receipts-json", help="JSON list of {detected_vendor, zoho_category}")
    ap.add_argument("--legal-entity-id", default="seed")
    ap.add_argument("--threshold", type=float, default=DEFAULT_FUZZY_THRESHOLD)
    ap.add_argument("--min-count", type=int, default=1,
                    help="drop clusters seen fewer than N times")
    ap.add_argument("--out", help="write the merchants JSON to this file")
    ap.add_argument("--put", metavar="BASE_URL",
                    help="apply to a running settings API (production config change)")
    ap.add_argument("--code", help="login code for --put")
    args = ap.parse_args(argv)

    if args.er_dir:
        receipts = _load_from_er_dir(Path(args.er_dir), args.legal_entity_id)
    else:
        receipts = _load_from_json(Path(args.receipts_json), args.legal_entity_id)

    merchants = build_merchants(
        receipts, threshold=args.threshold, min_count=args.min_count
    )
    payload = json.dumps({"merchants": merchants}, indent=2, ensure_ascii=False)

    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"wrote {len(merchants)} merchants -> {args.out}", file=sys.stderr)
    if args.put:
        _put_settings(args.put, args.code, merchants)
    if not args.out and not args.put:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
