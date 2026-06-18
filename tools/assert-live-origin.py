# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""assert-live-origin.py — prove a DEPLOYED ORIGIN serves the expected build.

"Live" is a fact about the production origin, never about a localhost preview or
a local dist (2026-06-01 local-web logo incident; 2026-06-17 brisken-expense-recon
regression: a fix verified on localhost while the Fly origin
`brisken-expense-recon.fly.dev` still served the pre-fix image). A localhost
render proves the build OUTPUT; only a cache-busted fetch of the production URL
proves the deployed ORIGIN.

This is the stack-agnostic generalization of tools/local-web-deploy.py's
live-origin parity gate (which is Astro/_astro-specific and hardwired to
local-web-ka.fly.dev). Any Fly / Vercel / Railway origin can assert its deploy:

  uv run tools/assert-live-origin.py https://brisken-expense-recon.fly.dev \
      --expect "Reviewed by" --expect-absent "OLD BANNER TEXT"

  # Astro-style hashed-asset parity against a local build:
  uv run tools/assert-live-origin.py https://site.fly.dev/page/ \
      --match-assets dist/page/index.html

Checks (every requested one must hold):
  * HTTP status == --status (default 200)
  * every --expect substring present in the live body
  * every --expect-absent substring NOT present (the OLD build is gone)
  * every hashed asset in --match-assets present live (build parity)

The fetch is cache-busted (?cb=) with an explicit User-Agent so a CDN / edge
cache cannot mask a stale origin. Exit 0 verified, 1 assertion failed, 2 on
fetch / usage error.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DEFAULT_ASSET_PATTERN = r"/_astro/[A-Za-z0-9._-]+\.(?:webp|js|css)"


def fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    """Cache-busted GET of the production URL; returns (status, body)."""
    sep = "&" if "?" in url else "?"
    busted = f"{url}{sep}cb={uuid.uuid4().hex}"
    req = urllib.request.Request(busted, headers={"User-Agent": "assert-live-origin/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="ignore")


def local_assets(path: Path, pattern: str) -> set[str]:
    return set(re.findall(pattern, path.read_text(encoding="utf-8", errors="ignore")))


def check(url, status, expect, expect_absent, match_assets, asset_pattern, timeout=25):
    """Pure assertion core (no argv, no exit). Returns (ok: bool, lines: list[str])."""
    lines: list[str] = []
    try:
        code, body = fetch(url, timeout)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        return False, [f"FAIL: fetch error for {url}: {e}"]

    ok = True
    if code != status:
        ok = False
        lines.append(f"FAIL: status {code} != expected {status}")
    else:
        lines.append(f"OK: status {code}")

    for s in expect:
        if s in body:
            lines.append(f"OK: present: {s!r}")
        else:
            ok = False
            lines.append(f"FAIL: expected substring absent from live origin: {s!r}")

    for s in expect_absent:
        if s in body:
            ok = False
            lines.append(f"FAIL: stale content still served (should be gone): {s!r}")
        else:
            lines.append(f"OK: absent: {s!r}")

    if match_assets:
        local = local_assets(Path(match_assets), asset_pattern)
        if not local:
            ok = False
            lines.append(f"FAIL: no assets matched {asset_pattern!r} in {match_assets}; parity unverifiable")
        else:
            live = set(re.findall(asset_pattern, body))
            missing = local - live
            if missing:
                ok = False
                lines.append(f"FAIL: live origin missing {len(missing)} asset(s) from this build:")
                for m in sorted(missing)[:8]:
                    lines.append(f"        {m}")
            else:
                lines.append(f"OK: live origin serves this build ({len(local)} assets matched)")

    return ok, lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Assert a deployed origin serves the expected build.")
    ap.add_argument("url", help="the production origin URL to verify")
    ap.add_argument("--status", type=int, default=200, help="expected HTTP status (default 200)")
    ap.add_argument("--expect", action="append", default=[], metavar="STR",
                    help="substring that MUST appear in the live body (repeatable)")
    ap.add_argument("--expect-absent", action="append", default=[], metavar="STR",
                    help="substring that must NOT appear, i.e. the old build is gone (repeatable)")
    ap.add_argument("--match-assets", metavar="LOCALFILE",
                    help="a local built file whose hashed asset refs must all appear live")
    ap.add_argument("--asset-pattern", default=DEFAULT_ASSET_PATTERN,
                    help="regex for hashed asset refs (default: Astro /_astro/)")
    ap.add_argument("--timeout", type=int, default=25)
    args = ap.parse_args()

    if not (args.expect or args.expect_absent or args.match_assets):
        print("usage error: give at least one of --expect / --expect-absent / --match-assets",
              file=sys.stderr)
        return 2

    ok, lines = check(args.url, args.status, args.expect, args.expect_absent,
                      args.match_assets, args.asset_pattern, args.timeout)
    print(f"== assert-live-origin: {args.url} ==")
    for ln in lines:
        print(f"  {ln}")
    if ok:
        print("VERIFIED: deployed origin serves the expected build.")
        return 0
    print("NOT LIVE: deployed origin does not match expectations (see above).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
