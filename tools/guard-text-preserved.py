#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Guard: the visible text of a set of HTML pages is byte-identical to a
locked baseline snapshot.

The failure mode of any page-WEIGHT optimize run is trivial and fatal:
deleting content makes the page smaller, so "delete the pricing section"
scores as a win. `validate-html.py` cannot catch it (the smaller page is
still structurally valid HTML). This guard closes that hole by pinning the
one thing a representation-level optimization must never change: what the
reader sees.

Normalization deliberately ignores everything a legitimate weight win
touches, and nothing else:

  * `<script>` / `<style>` bodies are dropped   -> minifying CSS/JS passes
  * HTML comments are dropped                   -> comment stripping passes
  * tags and attributes are dropped             -> markup slimming passes
  * runs of whitespace collapse to one space    -> reindenting passes
  * character entities are unescaped            -> `&amp;` vs `&` passes

What survives normalization is the rendered text, in document order. Any
removal, reordering, or rewording of visible copy changes the digest and
fails the guard.

Missing files fail too: deleting a page is the largest possible "win" and
must never be one.

Usage:
    # once, BEFORE lock-on (the snapshot then becomes a locked guard_file)
    uv run tools/guard-text-preserved.py --snapshot BASELINE.json FILE.html [...]

    # as an optimize guard (argv only, no shell operators)
    uv run tools/guard-text-preserved.py BASELINE.json FILE.html [...]

Exit 0 = every page's visible text matches. Exit 1 = drift (discard the
experiment). Exit 2 = usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html import unescape
from pathlib import Path

# Non-greedy, DOTALL: drop the *bodies* of elements whose text is not rendered.
_DROP_ELEMENTS = re.compile(
    r"<(script|style|template|noscript)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG = re.compile(r"<[^>]+>", re.DOTALL)
_WS = re.compile(r"\s+")


def visible_text(html: str) -> str:
    """Reduce an HTML document to its rendered text, normalized."""
    out = _DROP_ELEMENTS.sub(" ", html)
    out = _COMMENT.sub(" ", out)
    # Replace tags with a space, not "": <p>a</p><p>b</p> must not become "ab".
    out = _TAG.sub(" ", out)
    out = unescape(out)
    return _WS.sub(" ", out).strip()


def digest(path: Path) -> str:
    text = visible_text(path.read_text(encoding="utf-8", errors="replace"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rel(path: Path) -> str:
    """Stable key across platforms: forward slashes, as given on argv."""
    return str(path).replace("\\", "/")


def snapshot(baseline: Path, targets: list[Path]) -> int:
    payload = {
        "_schema": "guard-text-preserved/1",
        "pages": {_rel(p): digest(p) for p in sorted(targets, key=_rel)},
    }
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"snapshot: {len(payload['pages'])} page(s) -> {baseline}")
    for k in payload["pages"]:
        print(f"  {k}")
    return 0


def check(baseline: Path, targets: list[Path]) -> int:
    try:
        payload = json.loads(baseline.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unreadable baseline {baseline}: {exc}", file=sys.stderr)
        return 2
    pages = payload.get("pages")
    if not isinstance(pages, dict) or not pages:
        print(f"ERROR: baseline {baseline} declares no pages", file=sys.stderr)
        return 2

    given = {_rel(p) for p in targets}
    failures: list[str] = []

    # Every baselined page must still exist and still read the same. Driving
    # the loop from the BASELINE (not from argv) is what makes deleting a page
    # a failure rather than a smaller argv list.
    for key, want in sorted(pages.items()):
        path = Path(key)
        if not path.is_file():
            failures.append(f"MISSING  {key} (baselined page no longer exists)")
            continue
        got = digest(path)
        if got != want:
            failures.append(f"DRIFT    {key} (visible text changed)")
        else:
            print(f"ok       {key}")

    for extra in sorted(given - set(pages)):
        print(f"note     {extra} not in baseline (not checked)")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print(f"FAIL: {len(failures)} of {len(pages)} page(s) drifted; a weight "
              "optimization must not change what the reader sees.",
              file=sys.stderr)
        return 1
    print(f"PASS: visible text preserved across {len(pages)} page(s).")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--snapshot", action="store_true",
                    help="write the baseline instead of checking against it")
    ap.add_argument("baseline", help="path to the baseline JSON")
    ap.add_argument("pages", nargs="*", help="HTML files")
    args = ap.parse_args(argv)

    targets = [Path(p) for p in args.pages]
    if args.snapshot:
        missing = [str(p) for p in targets if not p.is_file()]
        if not targets or missing:
            print(f"ERROR: need existing HTML files; missing={missing}",
                  file=sys.stderr)
            return 2
        return snapshot(Path(args.baseline), targets)
    return check(Path(args.baseline), targets)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
