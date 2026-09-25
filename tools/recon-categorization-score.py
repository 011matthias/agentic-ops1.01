# /// script
# requires-python = ">=3.12"
# dependencies = ["rapidfuzz>=3.0"]
# ///
"""Brisken expense-recon categorization score: how right the tool's accounts
are, by where each answer came from, measured against Criss's own postings.

"Categorized" counts answers, not their source or quality, and the app's own
`n_charges_category_guessed` hides most guesses. This turns the item-216
analysis (`docs/2026-09-25 - Brisken Recon Categorization Analysis/measure.py`
+ `truth.py`) into one reproducible instrument, so a change can be judged by
whether it made the tool more right, not only more confident.

Inputs, both offline:
  * a payload directory as the app's API returns it: `batch_<id>.json`
    (`GET /api/expense-batches/{id}`), `run_<id>.json` (`GET /api/runs/{id}`),
    `settings.json`, optionally `batches.json` and `memory.json`;
  * the Zoho Books pull (`context/expense-reconciliation/zoho-books-24mo.json`
    shape: `orgs[org_id].expenses[]`), Criss's postings = the truth.

Outputs, per month and total: the screen-rule receipt baseline (copies with
`boxes: []` excluded), the refusal breakdown, the join to Criss's postings in
two strengths, accuracy by answer source, open-row accuracy, an
amount-weighted view and the precision of the per-company
`merchants[].accounts` map when settings carry one. Writes
`categorization-score.json` + `.md` and prints the markdown. The join
constants are part of the output, so two runs are comparable.

Usage (from the repo root):
  uv run tools/recon-categorization-score.py --payload-dir DIR [--zoho F]
  uv run tools/recon-categorization-score.py --fetch --payload-dir DIR \\
      --batch 50622baec444 --batch 074a7b8905d7 --batch 51a22ad72864

`--fetch` reads the live app once per endpoint, 15 s apart, and stops when
one read takes over 45 s (the backend is one Fly machine Criss works on).
The operator code comes from `EXPENSE_RECON_OPERATOR_CODE` or the gitignored
brisken `context/.env`; it and the session token are never printed or
written. `--module` points at the expense-recon `src/` whose chart
(`curated_leaves`) and registry (`MerchantRegistry`) the score reuses.
Exit 0 on a score, 2 when inputs are missing or a fetch is braked.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODULE_REL = Path("workspace/clients/brisken/automations/expense-reconciliation/src")
CONTEXT_REL = Path("workspace/clients/brisken/context")
ZOHO_REL = CONTEXT_REL / "expense-reconciliation" / "zoho-books-24mo.json"
DEFAULT_BASE_URL = "https://brisken-expense-recon.fly.dev"
CODE_ENV = "EXPENSE_RECON_OPERATOR_CODE"

# The join and its variants. Changing any of these changes every number, so
# they are printed with the score.
JOIN_WINDOW_DAYS = 3        # Criss books on the Chase post date, a day after the charge
STRICT_WINDOW_DAYS = 1      # strict: within a day AND a shared descriptor token, or same day
TOKEN_MIN_LEN = 3
TOKEN_STOP = frozenset({"inc", "llc", "ltd", "com", "the", "and", "www", "pty", "gmbh"})
CLOSED_ENTRY_STATUSES = ("posted", "subscription")   # booked before the tool ran
SOURCES = ("REGISTRY", "LEARNED", "LINE", "VENDOR")
# Refusals that mean "no chart to judge against" (posting_resolution.ENTITY_MISSING,
# curated_leaves.NOT_COVERED): the fix is the company, not the account, so these
# receipts count as intake, beside the ones a review verdict stopped earlier.
COMPANY_REFUSALS = ("entity_missing", "org_not_curated")

FETCH_GAP_S = 15.0
FETCH_BRAKE_S = 45.0
FETCH_TIMEOUT_S = 120.0

OUT_STEM = "categorization-score"


class InputError(Exception):
    """Inputs missing or unreadable; exit 2."""


# ---- module + paths ------------------------------------------------------------

def main_clone_root() -> Path | None:
    """The primary clone of this repo, for gitignored context a worktree lacks."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(out).parent if out else None


def context_path(rel: Path) -> Path:
    """`rel` in this checkout, else in the main clone (context/ is gitignored)."""
    here = REPO / rel
    if here.exists():
        return here
    main = main_clone_root()
    return main / rel if main and (main / rel).exists() else here


def curated_leaves(module_src: Path | None = None):
    src = str(module_src or REPO / MODULE_REL)
    if src not in sys.path:
        sys.path.insert(0, src)
    from expense_recon.zoho import curated_leaves as cl
    return cl


# ---- small helpers -------------------------------------------------------------

def dec(x) -> Decimal | None:
    try:
        return Decimal(str(x).replace(",", "")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def iso_date(x) -> date | None:
    try:
        return date.fromisoformat(str(x)[:10]) if x else None
    except ValueError:
        return None


def tokens(s: str | None) -> set[str]:
    return {
        t for t in re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split()
        if len(t) >= TOKEN_MIN_LEN and t not in TOKEN_STOP
    }


def month_key(label: str | None) -> str | None:
    """`July 2026` -> `2026-07`; None when the label is not a calendar month."""
    try:
        return datetime.strptime(str(label).strip(), "%B %Y").strftime("%Y-%m")
    except ValueError:
        return None


def answer_source(src: str | None) -> str | None:
    """The tier an answer came from. A matched row joins its lines' sources
    with "; "; a REVIEW part is a refused line, so `LINE; REVIEW` is LINE.
    Two different tiers on one row read MIXED."""
    parts = {p.strip().upper() for p in (src or "").split(";") if p.strip()}
    if not parts:
        return None
    kept = sorted(parts - {"REVIEW"})
    if not kept:
        return "REVIEW"
    return kept[0] if len(kept) == 1 else "MIXED"


def ratio(n: int, d: int) -> str:
    return f"{n}/{d}"


# ---- payloads --------------------------------------------------------------------

def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc


def load_payloads(payload_dir: Path) -> dict:
    """Months (chronological, each with its batch and run payload), settings
    and memory from one payload directory."""
    if not payload_dir.is_dir():
        raise InputError(f"payload dir not found: {payload_dir}")
    ids = [p.stem.removeprefix("batch_") for p in sorted(payload_dir.glob("batch_*.json"))]
    if not ids:
        raise InputError(f"no batch_<id>.json in {payload_dir}")
    months = []
    for bid in ids:
        batch = _read_json(payload_dir / f"batch_{bid}.json")
        run_path = payload_dir / f"run_{bid}.json"
        run = _read_json(run_path) if run_path.exists() else {}
        label = batch.get("label") or run.get("label") or bid
        months.append({
            "id": bid, "label": label, "month": month_key(label),
            "vocab": batch.get("category_vocabulary") or run.get("category_vocabulary"),
            "batch": batch, "run": run, "has_run": run_path.exists(),
        })
    months.sort(key=lambda m: (m["month"] or "9999", str(m["label"])))
    settings_path = payload_dir / "settings.json"
    if not settings_path.exists():
        raise InputError(f"settings.json missing in {payload_dir}")
    memory_path = payload_dir / "memory.json"
    return {
        "months": months,
        "settings": _read_json(settings_path),
        "memory": _read_json(memory_path) if memory_path.exists() else None,
    }


def companies(settings: dict) -> tuple[dict, dict]:
    """(entity label -> company label, company label -> org id) from the
    settings' `account_companies` (the app holds two spellings per company)."""
    label_of, org_of = {}, {}
    for c in settings.get("account_companies") or []:
        name, org = c.get("label"), str(c.get("org_id") or "")
        if not name or not org:
            continue
        org_of[name] = org
        for lab in [name, *(c.get("labels") or [])]:
            label_of[lab] = name
    if not org_of:
        raise InputError("settings.json carries no account_companies")
    return label_of, org_of


# ---- receipts: screen-rule baseline and refusals ------------------------------------

def is_categorized(expense: dict) -> bool:
    """The screen's rule: every line carries a category (no lines: not)."""
    lines = expense.get("line_items") or []
    return bool(lines) and all(li.get("category") for li in lines)


def receipt_baseline(month: dict, label_of: dict) -> dict:
    batch = month["batch"]
    every = batch.get("expenses") or []
    expenses = [e for e in every if e.get("boxes") != []]
    n_cat = sum(1 for e in expenses if is_categorized(e))
    summary = batch.get("summary") or {}
    refusals = []
    for e in expenses:
        lines = e.get("line_items") or []
        open_lines = [li for li in lines if not li.get("category")]
        if lines and not open_lines:
            continue
        review = e.get("review") or {}
        if review.get("refusal"):
            key = str(review["refusal"])
            group = "intake" if key in COMPANY_REFUSALS else "refused"
        elif not lines:
            group, key = "intake", "no_line_items"
        elif len(open_lines) < len(lines):
            group, key = "partial", f"partial:{review.get('reason_code')}"
        else:
            group, key = "intake", str(review.get("reason_code"))
        refusals.append({
            "document_id": e.get("document_id"), "group": group, "key": key,
            "company": label_of.get(e.get("legal_entity_id") or "", e.get("legal_entity_id") or None),
            "currency": e.get("currency"),
            "open_amount": str(sum((dec(li.get("line_total")) or Decimal(0)) for li in open_lines)),
        })
    screen_cat, screen_uncat = summary.get("n_categorized"), summary.get("n_uncategorized")
    return {
        "n_receipts": len(expenses), "n_copies": len(every) - len(expenses),
        "n_categorized": n_cat, "n_uncategorized": len(expenses) - n_cat,
        "screen": {"n_categorized": screen_cat, "n_uncategorized": screen_uncat,
                   "agrees": screen_cat == n_cat and screen_uncat == len(expenses) - n_cat},
        "refusal_groups": dict(Counter(r["group"] for r in refusals)),
        "refusal_keys": dict(Counter(r["key"] for r in refusals).most_common()),
        "refusals": refusals,
    }


def charge_baseline(month: dict) -> dict:
    run = month["run"]
    rows = run.get("rows") or []
    unmatched = [r for r in rows if r.get("effective_bucket") == "unmatched"]
    with_account = [r for r in unmatched if (r.get("charge_category") or {}).get("category")]
    refused = [r for r in unmatched
               if not (r.get("charge_category") or {}).get("category")
               and (r.get("review") or {}).get("refusal")]
    summary = run.get("summary") or month["batch"].get("summary") or {}
    return {
        "n_charges": len(rows), "n_unmatched": len(unmatched),
        "with_account": len(with_account), "refused": len(refused),
        "no_answer": len(unmatched) - len(with_account) - len(refused),
        "account_sources": dict(Counter(
            answer_source((r.get("charge_category") or {}).get("source")) for r in with_account
        ).most_common()),
        "app_guess_counter": summary.get("n_charges_category_guessed"),
    }


# ---- truth and the join ---------------------------------------------------------------

def tool_rows(months: list[dict], label_of: dict) -> list[dict]:
    """Every charge row on a GL month except refunds, in month order."""
    out = []
    for m in months:
        if m["vocab"] != "gl":
            continue
        for r in m["run"].get("rows") or []:
            if r.get("effective_bucket") == "refund":
                continue
            pc = r.get("posting_category") or {}
            rv = r.get("review") or {}
            entity = r.get("legal_entity_id") or ""
            out.append({
                "month": m["label"], "tx": r.get("transaction_id"),
                "company": label_of.get(entity, entity or None),
                "date": iso_date(r.get("date")), "amount": dec(r.get("amount")),
                "currency": r.get("currency"), "vendor": r.get("vendor") or "",
                "bucket": r.get("effective_bucket"), "entry_status": r.get("entry_status"),
                "code": pc.get("category"), "raw_source": pc.get("source"),
                "source": answer_source(pc.get("source")), "refusal": rv.get("refusal"),
            })
    return out


def truth_rows(zoho: dict, org_of: dict, months: set[str], cl) -> list[dict]:
    """Criss's postings in the given calendar months for the curated companies."""
    company_of_org = {org: name for name, org in org_of.items()}
    out = []
    for org, block in (zoho.get("orgs") or {}).items():
        company = company_of_org.get(str(org))
        if not company:
            continue
        for e in block.get("expenses") or []:
            d = iso_date(e.get("date"))
            if not d or d.strftime("%Y-%m") not in months:
                continue
            account = e.get("account_name")
            code = cl.code_of(account, str(org))
            out.append({
                "company": company, "org": str(org), "date": d, "total": dec(e.get("total")),
                "currency": e.get("currency_code"), "desc": e.get("description") or "",
                "vendor": e.get("vendor_name") or "", "account": account, "code": code,
                "postable": cl.is_postable(str(org), code) if code else None,
            })
    return out


def loose_rule(dd: int, overlap: int) -> bool:
    return True


def strict_rule(dd: int, overlap: int) -> bool:
    return (dd <= STRICT_WINDOW_DAYS and overlap >= 1) or dd == 0


def join(rows: list[dict], truth: list[dict], rule) -> list[tuple[int, int, int, int]]:
    """One-to-one pairs `(row, truth, day_diff, overlap)`: same company, amount
    to the cent, dates within JOIN_WINDOW_DAYS and `rule`; nearest date first,
    then most shared descriptor tokens, then input order."""
    by_key = defaultdict(list)
    for j, t in enumerate(truth):
        by_key[(t["company"], t["total"])].append(j)
    cands = []
    for i, r in enumerate(rows):
        if r["amount"] is None or r["date"] is None:
            continue
        for j in by_key.get((r["company"], r["amount"]), ()):
            t = truth[j]
            dd = abs((t["date"] - r["date"]).days)
            if dd > JOIN_WINDOW_DAYS:
                continue
            overlap = len(tokens(r["vendor"]) & (tokens(t["desc"]) | tokens(t["vendor"])))
            if rule(dd, overlap):
                cands.append((dd, -overlap, i, j))
    cands.sort()
    seen_r, seen_t, pairs = set(), set(), []
    for dd, neg_ov, i, j in cands:
        if i in seen_r or j in seen_t:
            continue
        seen_r.add(i)
        seen_t.add(j)
        pairs.append((i, j, dd, -neg_ov))
    return sorted(pairs)


def verdict(row: dict, truth_row: dict) -> str:
    if row["refusal"]:
        return "refused"
    if not row["code"]:
        return "no_answer"
    return "agree" if row["code"] == truth_row["code"] else "disagree"


def answer_kind(code: str | None, cl) -> str | None:
    """`code` when the answer is a chart code (or several), `label` when it is
    text the chart does not know, e.g. a retired bucket label."""
    parts = [p.strip() for p in (code or "").split(";") if p.strip()]
    if not parts:
        return None
    return "code" if all(cl.leaf(p) for p in parts) else "label"


def _source_table(joined: list[dict]) -> dict:
    table = {}
    for src in [*SOURCES, "MIXED"]:
        answered = [x for x in joined if x["answered"] and x["source"] == src]
        if not answered and src == "MIXED":
            continue
        table[src] = {
            "answered": len(answered),
            "right": sum(1 for x in answered if x["verdict"] == "agree"),
            "code_answers": sum(1 for x in answered if x["kind"] == "code"),
            "label_answers": sum(1 for x in answered if x["kind"] == "label"),
        }
    other = [x for x in joined if x["answered"] and x["source"] not in (*SOURCES, "MIXED")]
    if other:
        table["OTHER"] = {"answered": len(other), "right": sum(1 for x in other if x["verdict"] == "agree"),
                          "code_answers": sum(1 for x in other if x["kind"] == "code"),
                          "label_answers": sum(1 for x in other if x["kind"] == "label")}
    return table


def _amounts(joined: list[dict]) -> dict:
    out = {}
    for ccy in sorted({x["currency"] or "?" for x in joined}):
        rows = [x for x in joined if (x["currency"] or "?") == ccy]
        by = defaultdict(Decimal)
        for x in rows:
            by[x["verdict"]] += x["amount"]
        answered = by["agree"] + by["disagree"]
        out[ccy] = {
            **{k: str(by[k]) for k in ("agree", "disagree", "no_answer", "refused")},
            "right_share_of_answered": (
                f"{(100 * by['agree'] / answered).quantize(Decimal('0.1'))}%" if answered else None
            ),
        }
    return out


def score_join(rows: list[dict], truth: list[dict], pairs, cl) -> dict:
    joined = []
    for i, j, dd, overlap in pairs:
        r, t = rows[i], truth[j]
        v = verdict(r, t)
        joined.append({
            "month": r["month"], "tx": r["tx"], "company": r["company"], "vendor": r["vendor"],
            "amount": r["amount"], "currency": r["currency"], "entry_status": r["entry_status"],
            "open": r["entry_status"] not in CLOSED_ENTRY_STATUSES, "bucket": r["bucket"],
            "code": r["code"], "source": r["source"], "raw_source": r["raw_source"],
            "kind": answer_kind(r["code"], cl) if v in ("agree", "disagree") else None,
            "truth_code": t["code"], "truth_account": t["account"], "verdict": v,
            "answered": v in ("agree", "disagree"), "day_diff": dd, "overlap": overlap,
        })
    answered = [x for x in joined if x["answered"]]
    open_rows = [x for x in joined if x["open"]]
    open_answered = [x for x in open_rows if x["answered"]]
    return {
        "joined": len(joined), "unjoined_truth": len(truth) - len(joined),
        "unjoined_rows": len(rows) - len(joined),
        "verdicts": dict(Counter(x["verdict"] for x in joined)),
        "right": sum(1 for x in answered if x["verdict"] == "agree"), "answered": len(answered),
        "by_source": _source_table(joined),
        "by_month": {m: dict(Counter(x["verdict"] for x in joined if x["month"] == m))
                     for m in dict.fromkeys(x["month"] for x in joined)},
        "by_company": dict(Counter(x["company"] for x in joined)),
        "day_diff": dict(sorted(Counter(x["day_diff"] for x in joined).items())),
        "open_rows": {
            "joined": len(open_rows), "answered": len(open_answered),
            "right": sum(1 for x in open_answered if x["verdict"] == "agree"),
            "verdicts": dict(Counter(x["verdict"] for x in open_rows)),
            "by_source": _source_table(open_rows),
        },
        "amounts": _amounts(joined),
        "rows": [{**x, "amount": str(x["amount"])} for x in joined],
    }


# ---- the per-company account map (items 180/181) --------------------------------------------

def map_lever(settings: dict, rows: list[dict], truth: list[dict], pairs, org_of: dict,
              module_src: Path | None = None) -> dict:
    """Precision of `settings.merchants[name].accounts` against Criss, through
    the engine's own `MerchantRegistry.resolve` + `company_account`, probed
    with the bank descriptor (the charge path)."""
    merchants = settings.get("merchants") or {}
    mapped = sorted(n for n, e in merchants.items()
                    if isinstance(e, dict) and isinstance(e.get("accounts"), dict) and e["accounts"])
    if not mapped:
        return {"available": False, "n_merchants_with_map": 0}
    curated_leaves(module_src)  # puts the module on sys.path
    from expense_recon.merchant_registry import MerchantRegistry, company_account

    registry = MerchantRegistry(merchants)
    entity_orgs = {}
    for c in settings.get("account_companies") or []:
        for lab in [c.get("label"), *(c.get("labels") or [])]:
            if lab:
                entity_orgs[lab] = str(c.get("org_id") or "")
    covered, effect, per_merchant = [], Counter(), defaultdict(Counter)
    for i, j, _dd, _ov in pairs:
        r, t = rows[i], truth[j]
        match = registry.resolve(None, r["vendor"])
        if match is None or not match.accounts:
            continue
        hit = company_account(match.accounts, org_of.get(r["company"] or ""), entity_orgs)
        if not hit:
            continue
        ok = hit[1] == t["code"]
        today = verdict(r, t)
        covered.append(ok)
        per_merchant[match.canonical_name]["agree" if ok else "disagree"] += 1
        if ok and today == "agree":
            effect["kept_right"] += 1
        elif ok and today == "disagree":
            effect["fixed_wrong"] += 1
        elif ok:
            effect["filled_empty"] += 1
        elif today == "agree":
            effect["broke_right"] += 1
        else:
            effect["wrong"] += 1
    return {
        "available": True, "n_merchants_with_map": len(mapped),
        "covered": len(covered), "agree": sum(covered),
        "effect_vs_today": dict(effect),
        "per_merchant": {k: dict(v) for k, v in sorted(per_merchant.items())},
        "probe": "bank descriptor via MerchantRegistry.resolve(None, vendor), then company_account",
    }


# ---- the report -------------------------------------------------------------------------------

def build_report(payload_dir: Path, zoho_path: Path, *, truth_months: list[str] | None = None,
                 module_src: Path | None = None) -> dict:
    cl = curated_leaves(module_src)
    data = load_payloads(payload_dir)
    settings, months = data["settings"], data["months"]
    label_of, org_of = companies(settings)
    if not zoho_path.exists():
        raise InputError(f"Zoho pull not found: {zoho_path}")
    zoho = _read_json(zoho_path)

    per_month, gl = {}, [m for m in months if m["vocab"] == "gl"]
    for m in months:
        per_month[m["label"]] = {
            "id": m["id"], "vocab": m["vocab"], "has_run": m["has_run"],
            "receipts": receipt_baseline(m, label_of),
            "charges": charge_baseline(m) if m["has_run"] else None,
        }
    gl_labels = [m["label"] for m in gl]
    receipts_total = {
        k: sum(per_month[lab]["receipts"][k] for lab in gl_labels)
        for k in ("n_receipts", "n_copies", "n_categorized", "n_uncategorized")
    }
    receipts_total["refusal_groups"] = dict(sum(
        (Counter(per_month[lab]["receipts"]["refusal_groups"]) for lab in gl_labels), Counter()))
    receipts_total["refusal_keys"] = dict(sum(
        (Counter(per_month[lab]["receipts"]["refusal_keys"]) for lab in gl_labels), Counter()).most_common())

    window = sorted(set(truth_months or [m["month"] for m in gl if m["month"]]))
    rows = tool_rows(months, label_of)
    truth = truth_rows(zoho, org_of, set(window), cl)
    loose_pairs, strict_pairs = join(rows, truth, loose_rule), join(rows, truth, strict_rule)
    memory = data["memory"] or {}
    return {
        "tool": "recon-categorization-score",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "payload_dir": str(payload_dir),
            "months": [{"id": m["id"], "label": m["label"], "vocab": m["vocab"],
                        "updated_at": m["batch"].get("updated_at") or m["run"].get("updated_at")}
                       for m in months],
            "settings_gl_revision": settings.get("gl_revision"),
            "curated_revision": cl.curated_revision(),
            "memory_rules": sum(len(v.get("companies") or []) for v in memory.get("by_vendor") or []),
            "zoho_pull": str(zoho_path), "zoho_pulled_at": zoho.get("pulled_at"),
            "truth_months": window, "truth_rows": len(truth),
            "truth_rows_unresolved": sum(1 for t in truth if not t["code"]),
            "tool_rows": len(rows),
        },
        "constants": {
            "join": f"same company + amount to the cent + |date| <= {JOIN_WINDOW_DAYS} days, one to one, "
                    "nearest date then most shared descriptor tokens then input order",
            "strict_join": f"loose join restricted to (|date| <= {STRICT_WINDOW_DAYS} AND >= 1 shared "
                           "descriptor token) OR same day",
            "tokens": f"lowercase alphanumeric runs, length >= {TOKEN_MIN_LEN}, minus {sorted(TOKEN_STOP)}",
            "right": "the tool's code equals the code of the account Criss posted to (curated_leaves.code_of)",
            "answered": "the row carries an account and no refusal; a non-code answer counts as answered, not right",
            "source": "posting_category.source; REVIEW parts dropped, two tiers on one row = MIXED",
            "open_row": f"entry_status not in {list(CLOSED_ENTRY_STATUSES)}",
            "receipt_rule": "a receipt is categorized when every line carries a category; copies (boxes == []) excluded",
            "receipt_groups": "engine refused = review.refusal other than "
                              f"{list(COMPANY_REFUSALS)}; partial = some lines open; intake = no company "
                              "or a review verdict (statement, private, date) stopped it first",
            "rows": "every charge row on a GL-vocabulary month except refunds",
            "truth": "Zoho expenses of the account_companies orgs dated in truth_months",
        },
        "months": per_month,
        "receipts_total_gl": receipts_total,
        "accuracy": {
            "loose": score_join(rows, truth, loose_pairs, cl),
            "strict": score_join(rows, truth, strict_pairs, cl),
        },
        "account_map": map_lever(settings, rows, truth, loose_pairs, org_of, module_src),
    }


def _src_cell(entry: dict | None) -> str:
    if not entry or not entry["answered"]:
        return "0/0"
    cell = ratio(entry["right"], entry["answered"])
    if entry["label_answers"]:
        cell += f" ({entry['right']}/{entry['code_answers']} on codes, {entry['label_answers']} non-code)"
    return cell


def render_markdown(rep: dict) -> str:
    inp, acc = rep["inputs"], rep["accuracy"]
    loose, strict = acc["loose"], acc["strict"]
    out = [
        "# Recon categorization score",
        "",
        f"Payload `{inp['payload_dir']}` · Zoho pull {inp['zoho_pulled_at']} · chart "
        f"{inp['curated_revision']} (settings {inp['settings_gl_revision']}) · truth months "
        f"{', '.join(inp['truth_months'])} ({inp['truth_rows']} postings) · {rep['generated_at']}",
        "",
        "## Receipts (screen rule, copies excluded)",
        "",
        "| Month | Vocab | Receipts | Categorized | Screen agrees | Open: engine refused / partial / intake |",
        "|---|---|---|---|---|---|",
    ]
    for label, m in rep["months"].items():
        r = m["receipts"]
        g = r["refusal_groups"]
        out.append(f"| {label} | {m['vocab']} | {r['n_receipts']} | {r['n_categorized']} | "
                   f"{'yes' if r['screen']['agrees'] else 'NO'} | "
                   f"{g.get('refused', 0)} / {g.get('partial', 0)} / {g.get('intake', 0)} |")
    t = rep["receipts_total_gl"]
    g = t["refusal_groups"]
    out += [f"| **GL total** | gl | {t['n_receipts']} | {t['n_categorized']} | | "
            f"{g.get('refused', 0)} / {g.get('partial', 0)} / {g.get('intake', 0)} |", "",
            "Open receipts by reason (GL): " + ", ".join(f"{k} {n}" for k, n in t["refusal_keys"].items()),
            "", "## Receiptless charges", "",
            "| Month | Unmatched | With an account | Refused | No answer | Account sources | App's guess counter |",
            "|---|---|---|---|---|---|---|"]
    for label, m in rep["months"].items():
        c = m["charges"]
        if not c or m["vocab"] != "gl":
            continue
        srcs = ", ".join(f"{k} {n}" for k, n in c["account_sources"].items())
        out.append(f"| {label} | {c['n_unmatched']} | {c['with_account']} | {c['refused']} | "
                   f"{c['no_answer']} | {srcs} | {c['app_guess_counter']} |")
    out += ["", "## Accuracy against Criss's postings", "",
            "| Answer source | Loose join | Strict join |", "|---|---|---|"]
    for src in [*SOURCES, "MIXED", "OTHER"]:
        if src in loose["by_source"] or src in strict["by_source"]:
            out.append(f"| {src} | {_src_cell(loose['by_source'].get(src))} | "
                       f"{_src_cell(strict['by_source'].get(src))} |")
    out += [f"| **All answered** | **{ratio(loose['right'], loose['answered'])}** | "
            f"**{ratio(strict['right'], strict['answered'])}** |",
            f"| Joined rows | {loose['joined']} | {strict['joined']} |",
            f"| Refused / no answer | {loose['verdicts'].get('refused', 0)} / "
            f"{loose['verdicts'].get('no_answer', 0)} | {strict['verdicts'].get('refused', 0)} / "
            f"{strict['verdicts'].get('no_answer', 0)} |",
            "", f"Joined by company (loose): {', '.join(f'{k} {n}' for k, n in loose['by_company'].items())}. "
            f"Postings not joined: {loose['unjoined_truth']} (booked after the pull, or no matching charge).",
            "", "## Open rows (still to be booked when the tool ran)", ""]
    for name, s in (("Loose", loose), ("Strict", strict)):
        o = s["open_rows"]
        out.append(f"- {name}: right on {o['right']} of {o['answered']} answered, "
                   f"{o['joined']} joined ({', '.join(f'{k} {n}' for k, n in sorted(o['verdicts'].items()))})")
    out += ["", "## By amount (loose join)", "",
            "| Currency | Right | Wrong | No answer | Refused | Right share of answered |",
            "|---|---|---|---|---|---|"]
    for ccy, a in loose["amounts"].items():
        out.append(f"| {ccy} | {a['agree']} | {a['disagree']} | {a['no_answer']} | {a['refused']} | "
                   f"{a['right_share_of_answered'] or '-'} |")
    lever = rep["account_map"]
    out += ["", "## Per-company account map (`merchants[].accounts`)", ""]
    if not lever["available"]:
        out.append("No merchant in settings carries a per-company map, so there is nothing to score yet.")
    else:
        eff = lever["effect_vs_today"]
        out.append(f"{lever['n_merchants_with_map']} merchants carry a map; on the loose join it answers "
                   f"{lever['covered']} rows and agrees with Criss on {lever['agree']} "
                   f"(fixes {eff.get('fixed_wrong', 0)} wrong answers, fills {eff.get('filled_empty', 0)} "
                   f"empty ones, breaks {eff.get('broke_right', 0)} right ones).")
    out += ["", "## Constants", ""] + [f"- {k}: {v}" for k, v in rep["constants"].items()]
    return "\n".join(out) + "\n"


# ---- fetch ------------------------------------------------------------------------------------

def operator_code(env_file: Path | None) -> str:
    code = os.environ.get(CODE_ENV, "").strip()
    if code:
        return code
    path = env_file or context_path(CONTEXT_REL / ".env")
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == CODE_ENV:
                return value.strip().strip('"').strip("'")
    except OSError:
        pass
    raise InputError(f"{CODE_ENV} is not set and not in {path}")


class Braked(Exception):
    """A read crossed the brake; the fetch stops so the live machine recovers."""


def fetch(out_dir: Path, base_url: str, batch_ids: list[str], code: str, *,
          opener=urllib.request.urlopen, sleep=time.sleep, clock=time.monotonic,
          gap_s: float = FETCH_GAP_S, brake_s: float = FETCH_BRAKE_S,
          log=print) -> list[str]:
    """Read each endpoint once, `gap_s` apart; stop when one read takes longer
    than `brake_s`. Returns the files written. The token stays in memory."""
    out_dir.mkdir(parents=True, exist_ok=True)
    state = {"token": None, "reads": 0}

    def call(method: str, path: str, body: dict | None = None):
        if state["reads"]:
            sleep(gap_s)
        state["reads"] += 1
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if state["token"]:
            headers["Authorization"] = f"Bearer {state['token']}"
        req = urllib.request.Request(base_url.rstrip("/") + path, data=data, headers=headers, method=method)
        start = clock()
        try:
            with opener(req, timeout=FETCH_TIMEOUT_S) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise InputError(f"{method} {path}: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise Braked(f"{method} {path}: {exc}") from exc
        took = clock() - start
        log(f"  {method} {path}  {took:.1f} s")
        if took > brake_s:
            raise Braked(f"{method} {path} took {took:.0f} s (brake {brake_s:.0f} s); stopped")
        return payload

    written = []

    def save(name: str, payload) -> None:
        (out_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        written.append(name)

    call("GET", "/healthz")
    state["token"] = call("POST", "/api/login", {"code": code}).get("token")
    if not state["token"]:
        raise InputError("login returned no token")
    listing = call("GET", "/api/expense-batches")
    known = {str(b.get("batch_id") or b.get("run_id") or b.get("id")): b.get("label")
             for b in (listing.get("batches") if isinstance(listing, dict) else listing) or []}
    unknown = [b for b in batch_ids if b not in known]
    if not batch_ids or unknown:
        listed = ", ".join(f"{k} {v}" for k, v in known.items())
        raise InputError(f"name the months with --batch (unknown: {unknown or 'none given'}); listed: {listed}")
    save("batches.json", listing)
    for bid in batch_ids:
        save(f"batch_{bid}.json", call("GET", f"/api/expense-batches/{bid}"))
        save(f"run_{bid}.json", call("GET", f"/api/runs/{bid}"))
    save("settings.json", call("GET", "/api/settings"))
    save("memory.json", call("GET", "/api/memory"))
    return written


# ---- CLI --------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--payload-dir", type=Path, required=True)
    ap.add_argument("--zoho", type=Path, default=None, help=f"default: {ZOHO_REL} (main-clone fallback)")
    ap.add_argument("--module", type=Path, default=None, help=f"expense-recon src/ (default: {MODULE_REL})")
    ap.add_argument("--truth-months", default=None, help="YYYY-MM,... (default: the GL months' calendar months)")
    ap.add_argument("--out", type=Path, default=None, help="where the .json/.md go (default: the payload dir)")
    ap.add_argument("--fetch", action="store_true", help="read the live app into --payload-dir first")
    ap.add_argument("--batch", action="append", default=[], help="month id to fetch (repeatable)")
    ap.add_argument("--base-url", default=os.environ.get("EXPENSE_RECON_BASE_URL", DEFAULT_BASE_URL))
    ap.add_argument("--env-file", type=Path, default=None)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        if args.fetch:
            print(f"fetching {len(args.batch)} month(s) from {args.base_url}, {FETCH_GAP_S:.0f} s apart")
            fetch(args.payload_dir, args.base_url, args.batch, operator_code(args.env_file))
        months = [m.strip() for m in args.truth_months.split(",")] if args.truth_months else None
        rep = build_report(args.payload_dir, args.zoho or context_path(ZOHO_REL),
                           truth_months=months, module_src=args.module)
    except (InputError, Braked) as exc:
        print(f"recon-categorization-score: {exc}", file=sys.stderr)
        return 2
    out = args.out or args.payload_dir
    out.mkdir(parents=True, exist_ok=True)
    md = render_markdown(rep)
    (out / f"{OUT_STEM}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str),
                                          encoding="utf-8")
    (out / f"{OUT_STEM}.md").write_text(md, encoding="utf-8")
    sys.stdout.write(md)
    print(f"\nwrote {out / (OUT_STEM + '.json')} and .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
