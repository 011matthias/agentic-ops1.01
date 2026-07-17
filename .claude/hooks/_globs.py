"""Git-style glob matching for repo-relative posix paths (shared helper).

Used by optimize-run-gate.py (asset-scope enforcement) and tools/
optimize_run.py (asset staging + validation). NOT a hook itself - the `_`
prefix keeps it out of the hook registry scan, same convention as _shell.py.

Semantics (git pathspec-like, deliberately stricter than fnmatch):
  **   matches any number of path segments (including zero when it sits
       between slashes, e.g. `a/**/b` matches `a/b`)
  *    matches within ONE segment only - never crosses `/`. Plain fnmatch
       lets `*` cross separators, which would silently WIDEN an optimize
       run's declared asset scope; scope must never be wider than declared.
  ?    matches one non-separator character
  A pattern with no glob chars that names a directory prefix (`dir/`) or a
  bare path matches that exact file, or anything under it when it ends in /.

All matching is case-insensitive (Windows checkout) on `\\`->`/` normalized,
repo-relative paths with no leading slash.
"""
from __future__ import annotations

import re

__all__ = ["glob_to_regex", "matches_any", "match_one"]

_SPECIALS = re.escape(".^$+{}[]()|")


def glob_to_regex(pattern: str) -> re.Pattern:
    """Compile one git-style glob into a case-insensitive anchored regex."""
    p = pattern.replace("\\", "/").strip().lstrip("/")
    # A trailing slash means "everything under this directory".
    if p.endswith("/"):
        p += "**"
    out = []
    i = 0
    while i < len(p):
        c = p[i]
        if c == "*":
            if p[i:i + 2] == "**":
                # `**/` between separators may also match zero segments
                if p[i:i + 3] == "**/":
                    out.append(r"(?:[^/]+/)*")
                    i += 3
                else:
                    out.append(r".*")
                    i += 2
            else:
                out.append(r"[^/]*")
                i += 1
        elif c == "?":
            out.append(r"[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE)


def match_one(pattern: str, rel_path: str) -> bool:
    """Does one git-style glob match a repo-relative posix path?"""
    rel = rel_path.replace("\\", "/").lstrip("/")
    return bool(glob_to_regex(pattern).match(rel))


def matches_any(patterns: list[str], rel_path: str) -> bool:
    """Does any of the git-style globs match the repo-relative posix path?"""
    return any(match_one(p, rel_path) for p in patterns)
