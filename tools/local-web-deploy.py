# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
local-web-deploy.py — the ONE sanctioned "ship local-web" path.

Why this exists (2026-06-01 incident): a logo change was built locally,
screenshotted on a localhost preview, and declared "live-verified" — but it
was never deployed, so the real fly.dev origin still served the old build.
A localhost preview can only prove the build OUTPUT; it can never prove the
deployed ORIGIN. "Live" is a fact about the production origin, full stop.

This tool makes "deployed + live-verified" a single executable fact:

  1. npm run build            (the deliverable-rule postbuild gate runs here)
  2. fingerprint local dist   (content-hashed /_astro/ asset refs per page)
  3. flyctl deploy            (remote builder, rolling)
  4. fetch each fly.dev URL   (cache-busted) and assert the live HTML carries
                              the SAME hashed asset refs as the local build

If step 4 fails, the live origin is NOT serving this build -> exit 1. You
cannot get a green result from this tool without the production URL actually
serving the bytes you just built.

Usage:
  uv run tools/local-web-deploy.py                 # build + deploy + verify
  uv run tools/local-web-deploy.py --no-deploy     # verify live == current dist only
  uv run tools/local-web-deploy.py --skip-build    # deploy + verify existing dist
  uv run tools/local-web-deploy.py --only pronto-pronto
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "workspace" / "projects" / "local-web" / "app"
DIST = APP / "dist"
HOST = "https://local-web-ka.fly.dev"
FLYCTL = r"C:\Users\neuma_p1qrsic\.fly\bin\flyctl.exe"

ASSET_RE = re.compile(r"/_astro/[A-Za-z0-9._-]+\.(?:webp|js|css)")


def run(cmd: list[str], cwd: Path | None = None) -> int:
    # On Windows, npm/npx are .cmd shims that CreateProcess won't resolve
    # from a bare name — resolve the real path before spawning.
    exe = shutil.which(cmd[0]) or cmd[0]
    resolved = [exe, *cmd[1:]]
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(resolved, cwd=cwd).returncode


def slugs_from_dist() -> list[str]:
    return sorted(
        p.parent.name
        for p in DIST.glob("*/index.html")
        if p.parent.name != "_astro"
    )


def fingerprint_local(slug: str) -> set[str]:
    html = (DIST / slug / "index.html").read_text(encoding="utf-8", errors="ignore")
    return set(ASSET_RE.findall(html))


def fetch_live(slug: str) -> str:
    url = f"{HOST}/{slug}/?cb={uuid.uuid4().hex}"
    req = urllib.request.Request(url, headers={"User-Agent": "local-web-deploy/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="ignore")


def verify(slugs: list[str]) -> bool:
    ok = True
    for slug in slugs:
        local = fingerprint_local(slug)
        if not local:
            print(f"  [{slug}] WARN: no hashed assets in local dist — skipping")
            continue
        try:
            live_html = fetch_live(slug)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  [{slug}] FAIL: live fetch error: {e}")
            ok = False
            continue
        live = set(ASSET_RE.findall(live_html))
        missing = local - live
        if missing:
            ok = False
            print(f"  [{slug}] FAIL: live origin missing {len(missing)} asset(s) from this build:")
            for m in sorted(missing)[:8]:
                print(f"            {m}")
            print("          -> the deployed site is NOT serving this build.")
        else:
            print(f"  [{slug}] OK: live origin serves this build ({len(local)} assets matched)")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-deploy", action="store_true", help="verify live == current dist, no deploy")
    ap.add_argument("--skip-build", action="store_true", help="reuse existing dist, do not rebuild")
    ap.add_argument("--only", metavar="SLUG", help="restrict verify to one site slug")
    args = ap.parse_args()

    if not args.skip_build:
        print("== build ==")
        if run(["npm", "run", "build"], cwd=APP) != 0:
            print("FAIL: build failed.")
            return 1

    if not DIST.exists():
        print(f"FAIL: no dist at {DIST} (run without --skip-build).")
        return 1

    if not args.no_deploy:
        print("== deploy ==")
        rc = run([FLYCTL, "deploy", ".", "--config", str(APP / "fly.toml"),
                  "--remote-only", "--now"], cwd=APP)
        if rc != 0:
            print("FAIL: flyctl deploy failed.")
            return 1

    print("== verify live origin ==")
    slugs = [args.only] if args.only else slugs_from_dist()
    if verify(slugs):
        print(f"\nVERIFIED LIVE: {HOST} serves the current build for {len(slugs)} site(s).")
        return 0
    print("\nNOT LIVE: deployed origin does not match the local build (see above).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
