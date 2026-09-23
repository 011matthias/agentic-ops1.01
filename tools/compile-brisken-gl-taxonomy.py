#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Compile Dirk's marked chart of accounts into a committed runtime asset.

Run by hand, by a human who has the workbook, when Dirk re-issues the sheet.
Never at runtime. The output is committed and reviewed as a diff.

    uv run tools/compile-brisken-gl-taxonomy.py \\
        --workbook "<gitignored>/CoA-expense-relevant-BCS-BTS-260923.xlsx" \\
        --revision 2026-09-23 \\
        --expected-counts 697686691=67,808232536=64,822741658=68

`--check` recompiles to memory and byte-compares against the committed asset,
exiting non-zero on drift, so a hand-edited asset is caught.

WHY A COMPILED .py ASSET
The workbook lives under the client's gitignored `context/`, so it is absent on
Fly and in a fresh worktree; runtime must never reach for it. It cannot be JSON
beside the module either: the image's Dockerfile copies only `pyproject.toml`,
`uv.lock` and `src`, and the wheel target is `packages = ["src/expense_recon"]`,
so a data file would be the first non-.py file under `src/` and would put "did
hatchling carry it" on every deploy's critical path. A .py literal reaches Fly
with zero packaging change, and there is a precedent two files away in
`zoho/category_accounts.py`.

THE SHEET IS THE SOURCE; THE PULL IS A CROSS-CHECK
`zoho-books-coa.json` is silently truncated for Cloud Services: 199 accounts on
a 200-row page boundary, zero `cost_of_goods_sold` and zero `other_expense`
while both sibling orgs carry theirs. Nineteen accounts Dirk marked Y are absent
from it, including the account Anthropic posts to under Cloud Services. So the
pull reports and never vetoes.

NON-POSTABLE ROWS ARE COMPILED IN, WITH A REASON
Omitting them would collapse four different facts into one "unknown reference":
Dirk marked it N here, Zoho deactivated it, it is a roll-up, or this org has no
such account at all. Different people fix those, so a refusal has to say which.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import re
import sys

import openpyxl

# Tab label -> (org id, our name). VERIFIED by matching every Account ID in each
# tab against the live pull rather than trusting the label: each tab resolved to
# exactly one org, zero crossover. BTS is Consulting LLC and NOT the TEST-BTS
# sandbox, which is a clone of it; the label reads like the sandbox, and
# assuming so would aim the whole mapping at a test company.
TAB_TO_ORG = {
    "BCS": ("697686691", "Cloud Services"),
    "BTS": ("808232536", "Consulting LLC"),
    "CorpServ": ("822741658", "Corporate Services"),
}
SANDBOX_ORG_ID = "822116290"

Z_CODE = re.compile(r"^Z.*Z$")
DO_NOT_USE = re.compile(r"do\s*not\s*use", re.I)
# CorpServ prefixes its own account names ("CorpServ | Travel Expense | Food")
# where the other two orgs do not. The prefix is presentation, not identity, so
# it is stripped before a name is compared or used to build a branch.
ENTITY_PREFIX = re.compile(r"^(CorpServ|BCS|BTS)\s*\|\s*", re.I)

REQUIRED = ("Account ID", "Account Name", "Account Code", "Account Type",
            "Account Status", "Parent Account", "Expense Relevant")

# Reasons a leaf is present but not postable in a given org.
NOT_RELEVANT = "not_expense_relevant"
INACTIVE = "inactive"
RETIRED = "do_not_use"
ROLLUP = "roll_up"


def _s(v):
    return "" if v is None else str(v).strip()


def _strip_prefix(name):
    return ENTITY_PREFIX.sub("", name).strip()


def read_tab(ws, tab):
    rows = list(ws.iter_rows(values_only=True))
    header = [_s(h) for h in rows[0]]
    # Column ORDER differs per tab: CorpServ puts `Expense Relevant` fifth and
    # has no Why / How decided; BTS carries ~13 extra CF.* columns. Every lookup
    # is by header NAME, never by index.
    col = {name: i for i, name in enumerate(header)}
    missing = [n for n in REQUIRED if n not in col]
    if missing:
        raise SystemExit("tab %s is missing columns %s" % (tab, missing))

    out = []
    for r in rows[1:]:
        aid = _s(r[col["Account ID"]])
        if not aid:
            continue
        out.append({
            "account_id": aid,
            "name": _s(r[col["Account Name"]]),
            "code": _s(r[col["Account Code"]]),
            "type": _s(r[col["Account Type"]]),
            "status": _s(r[col["Account Status"]]),
            "parent": _s(r[col["Parent Account"]]),
            "verdict": _s(r[col["Expense Relevant"]]).upper(),
        })
    return out


def classify(rows):
    """Decide postability per row, and why not when not.

    A row is a roll-up when another row in the same tab names it as parent.
    Dirk's own convention: inside COGS the roll-up is N and you post to a leaf,
    outside COGS the parent is postable, so roll-up-ness is recorded but only
    refuses when he did not mark the row Y.
    """
    parents = {_strip_prefix(r["parent"]) for r in rows if r["parent"]}
    for r in rows:
        bare = _strip_prefix(r["name"])
        r["is_rollup"] = bare in parents
        if r["verdict"] != "Y":
            r["postable"], r["reason"] = False, NOT_RELEVANT
        elif r["status"] != "Active":
            r["postable"], r["reason"] = False, INACTIVE
        elif Z_CODE.match(r["code"]) or DO_NOT_USE.search(r["name"]):
            r["postable"], r["reason"] = False, RETIRED
        else:
            r["postable"], r["reason"] = True, ""
    return rows


def branch_of(row, by_name):
    """Root-to-parent chain, entity prefix stripped, walking Parent Account.

    Built from NAMES because the code is not a path: `Business Travel Expenses
    - CRM` is E600010-20 while its children are E600010-10-20-*, nested under
    the Conferences parent, identically in all three sheets. A prefix-derived
    hierarchy mis-resolves CRM travel.
    """
    chain, seen = [], set()
    cur = _strip_prefix(row["parent"])
    while cur and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        nxt = by_name.get(cur)
        cur = _strip_prefix(nxt["parent"]) if nxt and nxt["parent"] else ""
    return tuple(reversed(chain))


def compile_all(workbook, expected):
    wb = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
    if set(wb.sheetnames) != set(TAB_TO_ORG):
        raise SystemExit("tabs %s do not match the known set %s"
                         % (wb.sheetnames, sorted(TAB_TO_ORG)))

    leaves = {}
    org_tabs, counts, fatal = {}, {}, []
    for tab in wb.sheetnames:
        org_id, _org_name = TAB_TO_ORG[tab]
        if org_id == SANDBOX_ORG_ID:
            raise SystemExit("tab %s maps to the sandbox org; refusing" % tab)
        rows = classify(read_tab(wb[tab], tab))
        by_name = {_strip_prefix(r["name"]): r for r in rows}
        org_tabs[org_id] = tab

        seen_codes = set()
        for r in rows:
            code = r["code"]
            if not code:
                continue
            if code in seen_codes:
                fatal.append("%s: duplicate code %s" % (tab, code))
            seen_codes.add(code)
            # A Y row that is inactive, retired or a roll-up contradicts itself.
            # Dirk marked it postable, so either he is wrong or our detection
            # is, and somebody has to say which. Never a silent drop.
            if r["verdict"] == "Y" and r["reason"] in (INACTIVE, RETIRED):
                fatal.append("%s: %s %s is marked Y but is %s"
                             % (tab, code, r["name"], r["reason"]))
            entry = leaves.setdefault(code, {"branch": (), "bindings": {}})
            if r["postable"] and not entry["branch"]:
                entry["branch"] = branch_of(r, by_name)
            entry["bindings"][org_id] = (
                r["account_id"], r["name"], r["postable"], r["reason"])

        counts[org_id] = sum(1 for r in rows if r["postable"])

    if fatal:
        for line in fatal:
            print("FATAL: " + line, file=sys.stderr)
        raise SystemExit("%d contradiction(s) in the sheet; nothing written" % len(fatal))

    for org_id, want in expected.items():
        got = counts.get(org_id)
        if got != want:
            raise SystemExit(
                "postable count for org %s is %s, expected %s. A count that "
                "moves must move --expected-counts in the same commit, so an "
                "added or deleted leaf is a reviewed diff." % (org_id, got, want))
    if set(expected) != set(counts):
        raise SystemExit("--expected-counts covers %s, compiled %s"
                         % (sorted(expected), sorted(counts)))
    return leaves, org_tabs, counts


def render(leaves, org_tabs, counts, revision, workbook_name, sha):
    o = io.StringIO()
    w = o.write
    w('"""Dirk\'s curated Zoho expense accounts, per legal entity. GENERATED.\n\n')
    w("Do not edit by hand. Regenerate with:\n\n")
    w("    uv run tools/compile-brisken-gl-taxonomy.py --workbook <sheet> \\\\\n")
    w("        --revision <the sheet's save date> --expected-counts <org=n,...>\n\n")
    w("Source: %s, marked `Expense Relevant` by Dirk, saved %s.\n\n"
      % (workbook_name, revision))
    w("LEAVES maps an account CODE to (branch, {org_id: (account_id, name,\n")
    w("postable, reason)}). The code is the identity because it is stable across\n")
    w("the three orgs while the name is not: E100010-31 reads `Travel Expense |\n")
    w("Food` in BCS and BTS and `CorpServ | Travel Expense | Food` in CorpServ.\n")
    w("`account_id` is the numeric Zoho id and is the only thing that may reach a\n")
    w("payload; a NAME passed where an id was expected does not error, it posts\n")
    w("to a default. Non-postable rows are present WITH a reason so a refusal can\n")
    w("say which of four facts it hit rather than `unknown reference`.\n")
    w('"""\n\n')
    w("CURATED_REVISION = %r\n" % revision)
    w("SOURCE_WORKBOOK = %r\n" % workbook_name)
    w("SOURCE_SHA256 = %r\n\n" % sha)
    w("# Also the rollout and rollback lever: an org absent here is simply not\n")
    w("# covered, and the chain refuses for it instead of guessing.\n")
    w("CURATED_ORG_IDS = (\n")
    for org in sorted(org_tabs):
        w("    %r,  # %s\n" % (org, org_tabs[org]))
    w(")\n\n")
    w("ORG_TABS = {\n")
    for org in sorted(org_tabs):
        w("    %r: %r,\n" % (org, org_tabs[org]))
    w("}\n\n")
    w("POSTABLE_COUNTS = {\n")
    for org in sorted(counts):
        w("    %r: %d,\n" % (org, counts[org]))
    w("}\n\n")
    w("LEAVES = {\n")
    for code in sorted(leaves):
        entry = leaves[code]
        w("    %r: (\n" % code)
        w("        %r,\n" % (entry["branch"],))
        w("        {\n")
        for org in sorted(entry["bindings"]):
            w("            %r: %r,\n" % (org, entry["bindings"][org]))
        w("        },\n")
        w("    ),\n")
    w("}\n")
    return o.getvalue()


def cross_check(leaves, coa_path):
    raw = json.load(io.open(coa_path, encoding="utf-8"))
    live = set()
    for payload in raw.values():
        seq = payload
        if isinstance(payload, dict):
            for k in ("chartofaccounts", "accounts", "chart_of_accounts"):
                if isinstance(payload.get(k), list):
                    seq = payload[k]
                    break
        if isinstance(seq, list):
            for a in seq:
                if isinstance(a, dict) and a.get("account_id"):
                    live.add(str(a["account_id"]))
    absent = collections.Counter()
    for code, entry in leaves.items():
        for org, (aid, name, postable, _r) in entry["bindings"].items():
            if postable and aid not in live:
                absent[org] += 1
                print("    absent from pull: org %s  %-16s %s" % (org, code, name))
    print("cross-check: %d postable leaves absent from the live pull %s"
          % (sum(absent.values()), dict(absent)))
    print("(reported, not vetoed: the pull is known to truncate)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", required=True)
    ap.add_argument("--revision", required=True, help="the sheet's save date, YYYY-MM-DD")
    ap.add_argument("--expected-counts", required=True,
                    help="org_id=count,... asserted before anything is written")
    ap.add_argument("--out", default=(
        "workspace/clients/brisken/automations/expense-reconciliation/"
        "src/expense_recon/zoho/_curated_leaves_data.py"))
    ap.add_argument("--coa-pull", help="zoho-books-coa.json; reports only")
    ap.add_argument("--check", action="store_true",
                    help="compare against the committed asset, write nothing")
    args = ap.parse_args()

    expected = {}
    for part in args.expected_counts.split(","):
        org, _, n = part.partition("=")
        expected[org.strip()] = int(n)

    raw = io.open(args.workbook, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    leaves, org_tabs, counts = compile_all(args.workbook, expected)
    name = args.workbook.replace("\\", "/").rsplit("/", 1)[-1]
    text = render(leaves, org_tabs, counts, args.revision, name, sha)

    for org in sorted(counts):
        print("%-10s %3d postable" % (org_tabs[org], counts[org]))
    print("%d distinct codes, sha256 %s" % (len(leaves), sha[:16]))

    if args.check:
        current = io.open(args.out, encoding="utf-8").read()
        if current != text:
            raise SystemExit("DRIFT: %s differs from a fresh compile" % args.out)
        print("asset matches a fresh compile")
    else:
        io.open(args.out, "w", encoding="utf-8", newline="\n").write(text)
        print("wrote %s" % args.out)

    if args.coa_pull:
        cross_check(leaves, args.coa_pull)


if __name__ == "__main__":
    main()
