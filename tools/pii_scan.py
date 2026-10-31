#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Count personal data in files before they go public (layout plan W1-14).

The repo is public by owner decision, so a roster, an address export or an
IBAN that reaches a push is world-readable. gitleaks (CI) only knows
credentials; nothing looked for people. This scanner does, and it reports
COUNTS per file, never the values, so its own output is safe to print, log
and put in a CI job.

Detectors (thresholds are per file; calibrated 2026-10-28 so ordinary
checkpoints and status files stay silent):

  consumer       >= 3 distinct addresses on consumer mail domains, or >= 8
                 occurrences of <= 2 of them (the 10-09 checkpoint shape)
  emails         >= 20 distinct addresses on any domain
  iban           >= 1 IBAN that passes the mod-97 check
  phone_de       >= 3 distinct German numbers (+49 / 0049 / mobile 015x-017x)
  pii_keys       >= 50 JSON name/email/phone keys (an export, not a config)
  high_entropy   a single-line file that looks like a token
  conf_names     docs/ only: a name from any client's
                 context/confidential-names.txt (gitignored, local only)

Allowlisted: tools/tests/, */fixtures/, .claude/skills/, *.example.*, and any
file carrying an inline `pii-allow: <reason>` marker.

Usage:
  uv run tools/pii_scan.py --all                 # every tracked file
  uv run tools/pii_scan.py --range BASE...HEAD   # lines added in a range
  uv run tools/pii_scan.py FILE [FILE ...]
Exit 1 when anything is flagged, 0 when clean.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
from pathlib import Path

CONSUMER_DOMAINS = frozenset({
    "gmail.com", "googlemail.com", "gmx.de", "gmx.net", "gmx.at", "gmx.ch",
    "gmx.com", "web.de", "t-online.de", "freenet.de", "arcor.de", "posteo.de",
    "mailbox.org", "mail.de", "online.de", "yahoo.com", "yahoo.de",
    "hotmail.com", "hotmail.de", "outlook.com", "outlook.de", "live.com",
    "live.de", "msn.com", "icloud.com", "me.com", "mac.com", "aol.com",
    "aol.de", "proton.me", "protonmail.com", "protonmail.ch", "mail.com",
})
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})")
IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b")
PHONE_DE = re.compile(
    r"(?:\+49|\b0049|\b0(?=1[5-7]\d))[\s/().-]{0,3}\d(?:[\s/().-]?\d){7,12}"
)
# A key counts only with a value shaped like the data: a bare "name" key is
# every DB schema snapshot and workflow export (drizzle meta, n8n nodes).
PII_KEY = re.compile(
    r'"(?:(?:first|last|full)_?name"\s*:\s*"[^"\s][^"]*"'
    r'|e-?mail"\s*:\s*"[^"@\s]+@'
    r'|(?:phone|telefon|mobile)"\s*:\s*"\s*[+\d])',
    re.IGNORECASE,
)
ALLOW_MARKER = re.compile(r"pii-allow:[ \t]*[^\s]")  # the reason is on the same line

THRESHOLDS = {"consumer": 3, "emails": 20, "iban": 1, "phone_de": 3,
              "pii_keys": 50, "high_entropy": 1, "conf_names": 1}
CONSUMER_REPEAT = 8  # occurrences of <= 2 consumer addresses
MAX_BYTES = 5_000_000


def allowlisted_path(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    name = rel.rsplit("/", 1)[-1]
    return (rel.startswith(("tools/tests/", ".claude/skills/", "fixtures/"))
            or "/fixtures/" in rel or ".example." in name)


def _iban_ok(raw: str) -> bool:
    s = raw.replace(" ", "")
    if not 15 <= len(s) <= 34:
        return False
    digits = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return int(digits) % 97 == 1


def _entropy(s: str) -> float:
    counts = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in counts.values())


def confidential_names(roots: list[Path]) -> list[str]:
    """Names from every client's gitignored context/confidential-names.txt.

    One name per line, `#` comments. Read from each root (the repo and, for a
    worktree, the primary clone that holds the gitignored context/)."""
    names: set[str] = set()
    for root in roots:
        for f in root.glob("workspace/clients/*/context/confidential-names.txt"):
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    line = line.split("#", 1)[0].strip()
                    if len(line) >= 3:
                        names.add(line)
            except OSError:
                continue
    return sorted(names)


def scan_text(rel: str, text: str, names: list[str] = (),
              whole_file: bool = True) -> dict[str, int]:
    """Detector -> count for one file's (added) text; empty when clean.

    `whole_file` is False for the added lines of an EDIT: a one-line change to
    source is not a one-line token file (replay 2026-10-28: a recon regex)."""
    rel = rel.replace("\\", "/")
    if allowlisted_path(rel) or ALLOW_MARKER.search(text):
        return {}
    found: dict[str, int] = {}
    addrs = [(m.group(0).lower(), m.group(1).lower()) for m in EMAIL.finditer(text)]
    consumer = [a for a, dom in addrs if dom in CONSUMER_DOMAINS]
    distinct_consumer = len(set(consumer))
    if distinct_consumer >= THRESHOLDS["consumer"] or (
        distinct_consumer and len(consumer) >= CONSUMER_REPEAT
    ):
        found["consumer"] = distinct_consumer
    distinct_any = len({a for a, _ in addrs})
    if distinct_any >= THRESHOLDS["emails"]:
        found["emails"] = distinct_any
    ibans = {m.group(0).replace(" ", "") for m in IBAN.finditer(text) if _iban_ok(m.group(0))}
    if len(ibans) >= THRESHOLDS["iban"]:
        found["iban"] = len(ibans)
    phones = {re.sub(r"\D", "", m.group(0))[-9:] for m in PHONE_DE.finditer(text)}
    if len(phones) >= THRESHOLDS["phone_de"]:
        found["phone_de"] = len(phones)
    keys = len(PII_KEY.findall(text))
    if keys >= THRESHOLDS["pii_keys"]:
        found["pii_keys"] = keys
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if whole_file and len(lines) == 1:
        tok = lines[0].strip()
        if len(tok) >= 20 and " " not in tok and len(tok) <= 4096 and _entropy(tok) >= 3.5:
            found["high_entropy"] = 1
    if names and rel.startswith("docs/"):
        low = text.lower()
        hits = sum(1 for n in names if re.search(rf"\b{re.escape(n.lower())}\b", low))
        if hits >= THRESHOLDS["conf_names"]:
            found["conf_names"] = hits
    return found


def _git(repo: Path, *args: str, timeout: int = 30) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                             timeout=timeout, encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def name_roots(repo: Path) -> list[Path]:
    """The repo plus, for a linked worktree, the primary clone."""
    roots = [repo]
    common = _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common:
        primary = Path(common.strip()).parent
        if primary != repo:
            roots.append(primary)
    return roots


def added_text(repo: Path, rng: str, timeout: int = 30
               ) -> dict[str, tuple[str, bool]] | None:
    """Path -> (the text a range ADDS, whether the file is new).

    Scanning only added lines keeps a ledger that already carries old
    addresses (the friction-register archive) from tripping on every append.
    None when git cannot resolve the range."""
    diff = _git(repo, "diff", "--unified=0", "--no-color", "--no-renames",
                "--diff-filter=AM", rng, timeout=timeout)
    if diff is None:
        return None
    files: dict[str, list[str]] = {}
    new: set[str] = set()
    current = None
    from_null = False
    for line in diff.splitlines():
        if line.startswith("--- "):
            from_null = line[4:].strip() == "/dev/null"
        elif line.startswith("+++ "):
            path = line[4:]
            current = path[2:] if path.startswith("b/") else None
            if current:
                files.setdefault(current, [])
                if from_null:
                    new.add(current)
        elif current and line.startswith("+"):
            files[current].append(line[1:])
    return {p: ("\n".join(ls), p in new) for p, ls in files.items()}


def has_marker(repo: Path, rel: str, ref: str = "HEAD") -> bool:
    body = _git(repo, "show", f"{ref}:{rel}")
    return bool(body and ALLOW_MARKER.search(body))


def scan_range(repo: Path, rng: str, timeout: int = 30) -> dict[str, dict[str, int]] | None:
    texts = added_text(repo, rng, timeout=timeout)
    if texts is None:
        return None
    names = confidential_names(name_roots(repo))
    head = rng.split("..")[-1].lstrip(".") or "HEAD"
    hits = {}
    for rel, (text, is_new) in texts.items():
        found = scan_text(rel, text, names, whole_file=is_new)
        if found and not has_marker(repo, rel, head):
            hits[rel] = found
    return hits


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def scan_paths(repo: Path, rels: list[str]) -> dict[str, dict[str, int]]:
    names = confidential_names(name_roots(repo))
    hits = {}
    for rel in rels:
        text = _read(repo / rel)
        if text is None:
            continue
        found = scan_text(rel, text, names)
        if found:
            hits[rel] = found
    return hits


def expand_paths(repo: Path, paths: list[str]) -> tuple[list[str], list[str]]:
    """Repo-relative files for the given paths, plus the ones that do not exist.

    A directory stands for every file under it. Until 2026-10-29 a directory
    argument was read as one file, failed to read, and the scan reported
    "0 file(s) flagged" for a folder holding 880 addresses."""
    rels, missing = [], []
    for p in paths:
        path = Path(p).resolve()
        if path.is_dir():
            files = sorted(f for f in path.rglob("*")
                           if f.is_file() and ".git" not in f.relative_to(path).parts)
        elif path.is_file():
            files = [path]
        else:
            missing.append(p)
            continue
        rels += [os.path.relpath(f, repo).replace("\\", "/") for f in files]
    return rels, missing


def format_hits(hits: dict[str, dict[str, int]]) -> list[str]:
    return [f"{rel}: " + " ".join(f"{k}={v}" for k, v in sorted(found.items()))
            for rel, found in sorted(hits.items())]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", action="store_true", help="every tracked file")
    ap.add_argument("--range", dest="rng", help="BASE...HEAD: scan added lines")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args(argv)
    top = _git(Path(args.repo), "rev-parse", "--show-toplevel")
    repo = Path(top.strip()) if top else Path(args.repo).resolve()
    if args.rng:
        hits = scan_range(repo, args.rng)
        if hits is None:
            print(f"pii_scan: cannot resolve range {args.rng}", file=sys.stderr)
            return 2
    elif args.all:
        listed = _git(repo, "ls-files", "-z") or ""
        hits = scan_paths(repo, [p for p in listed.split("\0") if p])
    else:
        rels, missing = expand_paths(repo, args.paths)
        if missing:
            # Scanning nothing would print a clean result for a typo.
            for p in missing:
                print(f"pii_scan: no such path: {p}", file=sys.stderr)
            return 2
        hits = scan_paths(repo, rels)
    for line in format_hits(hits):
        print(line)
    print(f"pii_scan: {len(hits)} file(s) flagged", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
