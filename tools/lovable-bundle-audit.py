# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.31"]
# ///
"""Audit the published Brisken expense SPA bundle for the fields it reads.

A renderer cannot show a field it never names, so the decisive evidence that
a Lovable prompt was applied is the API FIELD NAME in a published JS chunk,
not display copy. This crawls every `/assets/*.js` reference transitively
until the set stops growing (48 files, ~975 KB as of 2026-09-15).

The CONTROLS block is the point of the script. A first version fetched only
the chunks the index names directly, found 16 of them, and reported
known-present fields (`ready_to_post`, `coverage`) as ABSENT. That is a blind
instrument, not a finding, and its confident negative would have sent someone
re-pasting a prompt that had already shipped. This one refuses to report on
the round's fields until every control is found.

Edit NEW for the round being audited; leave CONTROLS alone.

    uv run tools/lovable-bundle-audit.py

Exit 0 applied, 1 not applied, 2 instrument invalid.
"""
from __future__ import annotations

import re
import sys

import requests

BASE = "https://expenses.brisken.com"

# The round under audit. Field names the applied renderer must contain.
# Case 9 build 5 (item 204). `month_suggestion` is left out on purpose: it is
# a TypeScript type (src/lib/api.ts), erased at build, so it can never appear
# in a bundle; the renderer reads advisory_detail.code instead.
NEW = {
    "waits_for_statements": "case 9: the API list of cards a receipt waits for",
    "waits_for_statement": "case 9: the waiting-line i18n key",
    "card_suggestion": "case 9: the suggested card on a row",
    "cardSuggest": "case 9: the suggestion chip namespace",
    "cards/by-vendor": "case 9: the apply-to-vendor endpoint",
    "cardVendor": "case 9: the by-vendor offer namespace",
    "dry_run": "case 9: the by-vendor preview flag",
    "statement_month_differs": "case 9: the statement-month advisory",
}

# Fields known to be rendered today. If any is absent the crawl is blind and
# nothing above can be concluded. Never trim this to make a run pass.
CONTROLS = {
    "ready_to_post": "the post gate",
    "n_needs_entity": "MISSING ENTITY tile",
    "n_duplicate_copies": "the duplicates round",
    "seen_undefined": "the card-definition round",
    "unmatched_receipts": "the workbench list",
}

ASSET = re.compile(r'["\'`](?:\.)?(/?assets/[A-Za-z0-9_.\-]+\.js)["\'`]')


def fetch_corpus(session: requests.Session) -> dict[str, str]:
    r = session.get(BASE + "/", timeout=60)
    r.raise_for_status()
    corpus = {"/index.html": r.text}
    pending = {"/" + m.lstrip("/") for m in ASSET.findall(r.text)}
    seen: set[str] = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        try:
            resp = session.get(BASE + path, timeout=60)
        except Exception as exc:  # noqa: BLE001 - one bad chunk is not fatal
            print(f"  !! {path}: {exc}")
            continue
        if resp.status_code != 200:
            continue
        corpus[path] = resp.text
        for m in ASSET.findall(resp.text):
            cand = "/" + m.lstrip("/")
            if cand not in seen:
                pending.add(cand)
    return corpus


def report(title: str, sigs: dict[str, str], corpus: dict[str, str]) -> list[str]:
    print(title)
    print("-" * 72)
    absent = []
    for sig, label in sigs.items():
        hits = [p for p, body in corpus.items() if sig in body]
        where = hits[0].split("/")[-1][:30] if hits else "-"
        flag = "" if hits else "   <-- ABSENT"
        print(f"  {sig:<28} {len(hits):>3}  {where}{flag}")
        if not hits:
            absent.append(sig)
    print()
    return absent


def main() -> int:
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (bundle-audit)"
    corpus = fetch_corpus(session)
    total = sum(len(v) for v in corpus.values())
    print(f"fetched {len(corpus)} file(s), {total // 1024} KB\n")

    control_absent = report(
        "CONTROLS (known present; any ABSENT means the crawl is blind)",
        CONTROLS, corpus,
    )
    new_absent = report("THIS ROUND", NEW, corpus)

    if control_absent:
        print("INSTRUMENT INVALID: control(s) absent, so the crawl missed chunks.")
        print("Draw no conclusion about the round's fields from this run.")
        return 2
    if new_absent:
        print("NOT APPLIED (instrument validated by the controls):")
        for sig in new_absent:
            print(f"  - {sig}: {NEW[sig]}")
        return 1
    print("APPLIED: every signature present, controls validate the crawl.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
