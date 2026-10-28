#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Pull Brisken's Zoho Books chart of accounts completely, and prove it.

Read-only. Writes a NEW file; the caller diffs it before replacing the
canonical snapshot (whole-file-write floor, rule_behaviors B2).

    uv run tools/pull-brisken-zoho-coa.py --env <path/to/.env> \\
        --out .scratch/zoho-books-coa.new.json

WHY THIS IS NOT "FOLLOW THE PAGINATION"

Backlog item 182 filed this as a pull that stopped paginating: 199 accounts
for Cloud Services on a 200-row page boundary. That reading was wrong, and
the wrongness matters because the obvious fix does not work.

Measured live 2026-09-24 against org 697686691, walking `has_more_page` to
exhaustion every time:

    default      per_page=200  ->  199 rows, 1 page,  has_more_page False
    default      per_page=100  ->   89 rows, 1 page,  has_more_page False
    default      per_page=50   ->   47 rows, 1 page,  has_more_page False
    showbalance  per_page=200  ->  247 rows, 2 pages, 39 cost_of_goods_sold
    showbalance  per_page=100  ->   86 rows, 1 page,  has_more_page False

A SMALLER page returns FEWER total rows, and the server reports completion
every single time. So there is no page size at which this endpoint can be
trusted for this org, and a "short page means keep going" assertion would
fire on every call while proving nothing. The two listings are not even
nested: 7 accounts appear only in the default listing and 55 only under
`showbalance`, and their union (254) still omits one account Dirk marked
expense-relevant.

`showbalance` is also not the documented spelling. `show_balance` is
accepted and ignored (199 rows, unchanged); `showbalance` changes the
result set. Both are passed here deliberately, because what each returns is
an observed fact about this tenant rather than a documented contract, and
the cost of passing a parameter that turns out to be inert is zero.

WHAT MAKES THE CHECK REAL

Completeness cannot be judged from inside the listing, because the listing
is the thing that is lying. It needs an answer key from outside: the
compiled curated taxonomy (`_curated_leaves_data.LEAVES`), which comes from
Dirk's workbook and not from any pull. For each curated org this tool
asserts that every account_id the taxonomy says that org can POST to is
present. That assertion has independent ground truth, which "we saw N rows"
never did.

`GET /chartofaccounts/{id}` is the repair path, and it sees accounts no
listing returns. `2031056000023745007 E600010-30-10 'Marketing Expenses -
people'` comes back active and typed `expense` by id while appearing in
none of the eight listing parameterizations. So a missing account is topped
up by id, and only an account that even by-id cannot produce is a failure.

A non-curated org has no answer key, so its listing is merged and reported
and never asserted. Saying "complete" about those would be the same
unfounded confidence this tool exists to remove.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

# Listing parameterizations to merge. Neither is a superset of the other on
# Cloud Services, and both are short on their own; the union is the best any
# amount of listing can do. per_page stays at the maximum because smaller
# pages measured strictly worse.
LISTING_PLANS: tuple[tuple[str, dict[str, str]], ...] = (
    ("default", {}),
    ("showbalance", {"showbalance": "true"}),
)

FIELDS = (
    "account_id",
    "account_name",
    "account_code",
    "account_type",
    "parent_account_name",
    "is_active",
    "description",
)


class PullError(RuntimeError):
    """The pull could not be proven complete."""


# ── the parts with no network in them, so they can be tested ─────────────


def merge_listings(fetch, org_id, plans=LISTING_PLANS, per_page=200):
    """Every listing parameterization, merged by account_id.

    `fetch(path, **params)` returns the decoded JSON body. Later plans do not
    overwrite an earlier plan's row: the rows agree on identity, and keeping
    the first seen makes the merge order-stable for the diff a human reads.
    """
    merged: dict[str, dict] = {}
    seen_by_plan: dict[str, int] = {}
    for name, extra in plans:
        rows, page = 0, 1
        while True:
            body = fetch(
                "/chartofaccounts",
                organization_id=org_id,
                page=page,
                per_page=per_page,
                **extra,
            )
            batch = body.get("chartofaccounts") or []
            for a in batch:
                aid = str(a.get("account_id") or "")
                if aid and aid not in merged:
                    merged[aid] = a
            rows += len(batch)
            if not (body.get("page_context") or {}).get("has_more_page"):
                break
            page += 1
            if page > 60:
                # Not a real chart size for this tenant; a server that keeps
                # claiming more pages is a loop, and a loop that never ends
                # is worse than a pull that says where it stopped.
                raise PullError(
                    f"org {org_id} plan {name!r}: more than 60 pages, aborting"
                )
        seen_by_plan[name] = rows
    return merged, seen_by_plan


def top_up_by_id(fetch, org_id, merged, want_ids):
    """Fetch by id every wanted account the listings missed.

    Returns (recovered, unrecoverable). `merged` is updated in place. An
    account the by-id endpoint refuses is left out rather than faked; the
    caller decides whether that is fatal.
    """
    recovered, unrecoverable = [], []
    for aid in sorted(set(want_ids) - set(merged)):
        body = fetch(f"/chartofaccounts/{aid}", organization_id=org_id)
        row = body.get("chart_of_account") or body.get("chartofaccount") or {}
        if not row.get("account_id"):
            unrecoverable.append(aid)
            continue
        merged[str(row["account_id"])] = row
        recovered.append(aid)
    return recovered, unrecoverable


def curated_answer_key(leaves):
    """org_id -> {account_id: (code, name)} for POSTABLE bindings only.

    Postable is the load-bearing set: those are the accounts the posting
    chain can actually resolve to, so an absent one is a refusal the reviewer
    will see. A non-postable binding absent from the chart changes nothing,
    because the chain refuses it either way, so it is reported and not
    asserted.
    """
    want: dict[str, dict[str, tuple[str, str]]] = collections.defaultdict(dict)
    for code, (_branch, bindings) in leaves.items():
        for org_id, binding in bindings.items():
            account_id, name, postable = binding[0], binding[1], binding[2]
            if postable:
                want[str(org_id)][str(account_id)] = (code, name)
    return dict(want)


def slim(row):
    return {k: row.get(k) for k in FIELDS}


# ── the network ───────────────────────────────────────────────────────────


def read_env(path):
    env = {}
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def make_fetch(env):
    dc = env.get("ZOHO_DC", "com")
    api = f"https://www.zohoapis.{dc}/books/v3"
    data = urllib.parse.urlencode(
        {
            "refresh_token": env["ZOHO_BOOKS_REFRESH_TOKEN"],
            "client_id": env["ZOHO_CLIENT_ID"],
            "client_secret": env["ZOHO_CLIENT_SECRET"],
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(
        f"https://accounts.zoho.{dc}/oauth/v2/token", data=data, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r)
    scope = tok.get("scope", "")
    # Read the granted scope off the token rather than inferring it from a
    # successful call, per project_brisken_zoho_books.
    print(f"granted scope: {scope}")
    access = tok["access_token"]

    def fetch(path, **params):
        url = f"{api}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        rq = urllib.request.Request(
            url, headers={"Authorization": f"Zoho-oauthtoken {access}"}
        )
        try:
            with urllib.request.urlopen(rq, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            try:
                det = json.load(e)
            except Exception:
                det = {}
            if e.code == 404:
                # An id that is not in this org. Not fatal on its own: the
                # caller reports it as unrecoverable.
                return {}
            raise PullError(
                f"{path} -> HTTP {e.code} code={det.get('code')} "
                f"{det.get('message')!r}"
            ) from e

    return fetch


def organizations(fetch, fallback_ids=()):
    """The orgs to walk, without depending on a scope this tool does not need.

    `/organizations` lives under `ZohoBooks.settings.READ`, which the token
    carried until 2026-08 and does not carry on 2026-09-24: its granted scope
    now reads `expenses.CREATE expenses.READ contacts.READ accountants.READ`,
    so the org listing 401s with code 57 while `/chartofaccounts` keeps
    working on `accountants.READ`.

    Losing the whole pull because the directory call needs a scope the pull
    itself does not would be the tool failing for a reason unrelated to its
    job. So a 401 falls back to the ids the caller already knows (the compare
    snapshot's keys plus the curated orgs), and says it did.
    """
    try:
        orgs = fetch("/organizations").get("organizations") or []
        if orgs:
            return orgs
    except PullError as e:
        print(f"  /organizations unavailable ({e}); using known org ids")
    return [{"organization_id": oid, "name": None} for oid in fallback_ids]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--env",
        default="workspace/clients/brisken/context/.env",
        help="gitignored env holding ZOHO_BOOKS_REFRESH_TOKEN et al",
    )
    ap.add_argument(
        "--out",
        default=".scratch/zoho-books-coa.new.json",
        help="NEW file; diff it against the canonical snapshot before replacing",
    )
    ap.add_argument(
        "--compare",
        default="workspace/clients/brisken/context/zoho-books-coa.json",
        help="existing snapshot to report drift against; skipped when absent",
    )
    ap.add_argument(
        "--orgs", help="comma-separated org ids; default every org on the token"
    )
    args = ap.parse_args(argv)

    sys.path.insert(
        0,
        str(
            pathlib.Path(__file__).resolve().parents[1]
            / "workspace/clients/brisken/automations/expense-reconciliation/src"
        ),
    )
    from expense_recon.zoho import _curated_leaves_data as curated

    want_by_org = curated_answer_key(curated.LEAVES)
    fetch = make_fetch(read_env(args.env))

    compare = pathlib.Path(args.compare)
    known = list(want_by_org)
    if compare.exists():
        known = list(json.loads(compare.read_text(encoding="utf-8"))) or known
    orgs = organizations(fetch, fallback_ids=known)
    # The directory is where org names come from, and it is exactly what a
    # token without settings.READ cannot read. Carrying the previous
    # snapshot's names forward keeps the fallback from quietly writing a
    # field's worth of nulls over data the old file had.
    prior_names = {}
    if compare.exists():
        prior_names = {
            oid: ((payload.get("org") or {}).get("name"))
            for oid, payload in json.loads(
                compare.read_text(encoding="utf-8")
            ).items()
        }
    wanted = {o.strip() for o in args.orgs.split(",")} if args.orgs else None
    snapshot, failures = {}, []

    for o in orgs:
        oid = str(o["organization_id"])
        if wanted and oid not in wanted:
            continue
        merged, by_plan = merge_listings(fetch, oid)
        want = want_by_org.get(oid, {})
        recovered, unrecoverable = top_up_by_id(fetch, oid, merged, want)
        org_name = o.get("name") or prior_names.get(oid)
        types = collections.Counter(a.get("account_type") for a in merged.values())
        print(
            f"  {oid} {org_name!r}: merged={len(merged)} "
            f"plans={by_plan} cogs={types.get('cost_of_goods_sold', 0)} "
            f"other_expense={types.get('other_expense', 0)}"
        )
        if want:
            print(
                f"      curated postable={len(want)} "
                f"recovered_by_id={len(recovered)} unrecoverable={len(unrecoverable)}"
            )
            for aid in recovered:
                code, name = want[aid]
                print(f"        by-id: {aid} {code} {name!r}")
            for aid in unrecoverable:
                code, name = want[aid]
                print(f"        UNRECOVERABLE: {aid} {code} {name!r}")
                failures.append((oid, aid, code, name))
        else:
            print("      no curated answer key for this org: merged, not asserted")
        snapshot[oid] = {
            "org": {
                "organization_id": oid,
                "name": org_name,
                "currency_code": o.get("currency_code"),
            },
            "accounts": [slim(a) for a in merged.values()],
        }

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(snapshot, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nwrote {out} ({out.stat().st_size} bytes)")

    if compare.exists():
        old = json.loads(compare.read_text(encoding="utf-8"))
        print(f"\n=== drift vs {compare}")
        for oid, cur in snapshot.items():
            prev = old.get(oid)
            if prev is None:
                print(f"  {oid}: absent from the old snapshot")
                continue
            pa = {str(a["account_id"]) for a in prev["accounts"]}
            ca = {str(a["account_id"]) for a in cur["accounts"]}
            print(
                f"  {oid} {cur['org']['name']!r}: {len(pa)} -> {len(ca)} "
                f"(+{len(ca - pa)} -{len(pa - ca)})"
            )

    if failures:
        print(
            f"\nFAILED: {len(failures)} curated postable account(s) could not be "
            "obtained by listing or by id. The snapshot is incomplete; do not "
            "promote it."
        )
        return 1
    print("\nOK: every curated postable account is present in the pull.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
