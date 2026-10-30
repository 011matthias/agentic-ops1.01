#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Rewrite real email addresses in test data to placeholders (layout plan W1-20).

The repo is public, and the WW scripts and their logic tests carry customer
addresses. This rewrites them before the import, and the pytest beside it
keeps them out afterwards. Rewrites, per occurrence:

  consumer-domain address       -> person-N@example.com
  --all-domains, other domains  -> person-N@<same domain> (the domain may be
                                   what the logic under test keys on); role
                                   local parts (info@, noreply@, ...) are kept
  never touched                 reserved test domains (example.com/.org/.net,
                                *.example, *.test, *.invalid, *.localhost),
                                existing person-N placeholders, and every
                                --keep-domain (the client's own domain, where
                                a sender or recipient address is functional)

N is assigned in order of first appearance across all files of one run, and
starts above the highest placeholder already present, so an address shared by
two records still shares one placeholder and a later run never reuses a
number. Numbers, not hashes: a hash of an address lets anyone holding a
candidate address confirm it was in the data.

Prints counts per file, never an address. Skips context/, node_modules/,
.git/, files over 5 MB and files that are not UTF-8.

Usage:
  uv run tools/scrub-test-data.py PATH [PATH ...]           # dry run, exit 0
  uv run tools/scrub-test-data.py --check PATH ...          # exit 1 if anything would change
  uv run tools/scrub-test-data.py --write PATH ...          # rewrite in place
  options: --all-domains, --keep-domain DOMAIN (repeatable)
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pii_scan import CONSUMER_DOMAINS, EMAIL  # noqa: E402

PLACEHOLDER = re.compile(r"^person-(\d+)$")
RESERVED_EXACT = frozenset({"example.com", "example.org", "example.net"})
RESERVED_TLDS = (".example", ".test", ".invalid", ".localhost")
ROLE_LOCAL_PARTS = frozenset({
    "info", "kontakt", "contact", "office", "buero", "mail", "post", "team",
    "hello", "hallo", "noreply", "no-reply", "donotreply", "do-not-reply",
    "support", "service", "hilfe", "kundenservice", "kundendienst",
    "rechnung", "rechnungen", "invoice", "invoices", "billing",
    "buchhaltung", "accounting", "admin", "sales", "vertrieb", "schaden",
    "mailer-daemon", "postmaster", "webmaster", "git", "bounce", "bounces",
    "notification", "notifications", "newsletter", "news", "marketing",
    "presse", "press", "jobs", "karriere", "bewerbung", "datenschutz",
    "privacy", "security", "abuse",
})
SKIP_DIRS = frozenset({"context", "node_modules", ".git", "__pycache__"})
MAX_BYTES = 5_000_000


def _reserved(domain: str) -> bool:
    return (domain in RESERVED_EXACT
            or any(domain.endswith("." + d) for d in RESERVED_EXACT)
            or domain.endswith(RESERVED_TLDS))


def _kept(domain: str, keep: frozenset[str]) -> bool:
    return any(domain == k or domain.endswith("." + k) for k in keep)


def classify(address: str, all_domains: bool, keep: frozenset[str]) -> str | None:
    """'consumer' or 'other' when the address gets rewritten, else None."""
    local, _, domain = address.lower().rpartition("@")
    if PLACEHOLDER.match(local) or _reserved(domain) or _kept(domain, keep):
        return None
    if domain in CONSUMER_DOMAINS:
        return "consumer"
    if all_domains and local not in ROLE_LOCAL_PARTS:
        return "other"
    return None


def iter_files(paths: list[Path]):
    for p in paths:
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not SKIP_DIRS.intersection(f.relative_to(p).parts[:-1]):
                    yield f


def read_text(f: Path) -> str | None:
    try:
        if f.stat().st_size > MAX_BYTES:
            return None
        with open(f, encoding="utf-8", newline="") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


class Scrubber:
    def __init__(self, all_domains: bool = False, keep: frozenset[str] = frozenset(),
                 start: int = 0):
        self.all_domains = all_domains
        self.keep = keep
        self.mapping: dict[str, str] = {}
        self.next_n = start + 1

    def _placeholder(self, address: str, kind: str) -> str:
        key = address.lower()
        if key not in self.mapping:
            domain = "example.com" if kind == "consumer" else key.rpartition("@")[2]
            self.mapping[key] = f"person-{self.next_n}@{domain}"
            self.next_n += 1
        return self.mapping[key]

    def scrub(self, text: str) -> tuple[str, Counter]:
        counts: Counter = Counter()

        def sub(m: re.Match) -> str:
            kind = classify(m.group(0), self.all_domains, self.keep)
            if kind is None:
                return m.group(0)
            counts[kind] += 1
            return self._placeholder(m.group(0), kind)

        return EMAIL.sub(sub, text), counts


def highest_placeholder(texts) -> int:
    top = 0
    for text in texts:
        for m in EMAIL.finditer(text):
            pm = PLACEHOLDER.match(m.group(0).rpartition("@")[0].lower())
            if pm:
                top = max(top, int(pm.group(1)))
    return top


def plan(paths: list[Path], all_domains: bool = False,
         keep: frozenset[str] = frozenset()) -> list[tuple[Path, str, Counter]]:
    """[(file, new_text, counts)] for every file that would change."""
    texts = [(f, t) for f in iter_files(paths) if (t := read_text(f)) is not None]
    s = Scrubber(all_domains, keep, start=highest_placeholder(t for _, t in texts))
    out = []
    for f, text in texts:
        new, counts = s.scrub(text)
        if counts:
            out.append((f, new, counts))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+", type=Path)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="rewrite the files in place")
    mode.add_argument("--check", action="store_true", help="exit 1 if anything would change")
    ap.add_argument("--all-domains", action="store_true",
                    help="also rewrite personal local parts on non-consumer domains")
    ap.add_argument("--keep-domain", action="append", default=[],
                    help="never rewrite addresses on this domain (repeatable)")
    args = ap.parse_args(argv)

    missing = [str(p) for p in args.paths if not p.exists()]
    if missing:
        print(f"scrub-test-data: no such path: {', '.join(missing)}", file=sys.stderr)
        return 2
    keep = frozenset(d.lower().lstrip("@") for d in args.keep_domain)
    changes = plan(args.paths, args.all_domains, keep)
    total = Counter()
    for f, new, counts in changes:
        total.update(counts)
        detail = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"{f.as_posix()}: {detail}")
        if args.write:
            with open(f, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
    verb = "rewritten" if args.write else "to rewrite"
    print(f"scrub-test-data: {len(changes)} file(s), {sum(total.values())} address "
          f"occurrence(s) {verb}")
    return 1 if (args.check and changes) else 0


if __name__ == "__main__":
    sys.exit(main())
