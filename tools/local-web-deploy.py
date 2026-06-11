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

This tool makes "deployed + live-verified + behaving" a single executable
fact (gate list mirrors skil_web-build modules/SHIP.md §2):

  1. npm run build                  (deliverable-rule postbuild gate)
  2. aesthetics audit --strict      (hard-fail classes block the deploy)
  3. flyctl deploy                  (remote builder, rolling)
  4. live-origin parity             (cache-busted fetch; hashed /_astro/ refs
                                     must match this exact build)
  5. axe-check.cjs                  (zero WCAG 2 A/AA violations, DoD 11)
  6. verify-rendered.cjs            (hero paints, brand font loaded, DoD 14)
  7. impeccable detect (ADVISORY)   (their 41 detectors; availability
                                     failures WARN loudly, never block —
                                     gates 1-6 are the authoritative ones)

A skipped or unrunnable hard gate is a FAILED gate: missing flyctl / Chrome /
node_modules exit 1 with the fix instruction (no graceful degradation;
CLI-Anything HARNESS.md doctrine, adopted 2026-06-11).

Usage:
  uv run tools/local-web-deploy.py                 # full gauntlet
  uv run tools/local-web-deploy.py --no-deploy     # gates against current live, no deploy
  uv run tools/local-web-deploy.py --skip-build    # reuse existing dist, do not rebuild
  uv run tools/local-web-deploy.py --only pronto-pronto
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
APP = REPO / "workspace" / "projects" / "local-web" / "app"
DIST = APP / "dist"
HOST = "https://local-web-ka.fly.dev"
FLYCTL = r"C:\Users\neuma_p1qrsic\.fly\bin\flyctl.exe"
IMPECCABLE_PIN = "impeccable@2.3.2"  # version-pinned: npx must not float to an unreviewed release

ASSET_RE = re.compile(r"/_astro/[A-Za-z0-9._-]+\.(?:webp|js|css)")


def resolve(cmd: str, fix: str) -> str:
    """No graceful degradation: a missing hard-gate dependency is exit 1 + fix."""
    exe = shutil.which(cmd)
    if not exe:
        print(f"FAIL: '{cmd}' not found on PATH. Fix: {fix}")
        raise SystemExit(1)
    return exe


def run(cmd: list[str], cwd: Path | None = None) -> int:
    # On Windows, npm/npx are .cmd shims that CreateProcess won't resolve
    # from a bare name — resolve the real path before spawning.
    exe = shutil.which(cmd[0]) or cmd[0]
    resolved = [exe, *cmd[1:]]
    print(f"  $ {' '.join(cmd)}")
    try:
        return subprocess.run(resolved, cwd=cwd).returncode
    except (FileNotFoundError, OSError) as e:
        print(f"FAIL: could not run {cmd[0]}: {e}")
        return 1


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
            # A page with zero hashed assets has no fingerprint to verify —
            # that is an unverifiable gate, which is a failed gate.
            print(f"  [{slug}] FAIL: no hashed assets in local dist; live-origin parity is unverifiable")
            ok = False
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


def gate_aesthetics(only: str | None) -> bool:
    print("== gate: aesthetics audit (--strict) ==")
    uv = resolve("uv", "install UV (https://github.com/astral-sh/uv)")
    cmd = [uv, "run", str(TOOLS / "audit-local-web-aesthetics.py"), "--strict", "--persist"]
    if only:
        cmd += ["--only", only]
    rc = subprocess.run(cmd, cwd=REPO).returncode
    if rc != 0:
        print("FAIL: aesthetics hard fails block the deploy (see findings above).")
        return False
    return True


def gate_node_tool(script: str, urls: list[str], extra: list[str] | None = None) -> bool:
    print(f"== gate: {script} ==")
    node = resolve("node", "install Node.js (the local-web app already requires it)")
    rc = run([node, str(TOOLS / script), *(extra or []), *urls], cwd=REPO)
    if rc != 0:
        print(f"FAIL: {script} gate did not pass (exit {rc}).")
        return False
    return True


def advisory_impeccable() -> None:
    """Second opinion from impeccable's 41 deterministic detectors. Advisory:
    OUR gates are authoritative; an availability failure WARNs, never blocks."""
    print("== advisory: impeccable detect (second opinion, non-blocking) ==")
    npx = shutil.which("npx")
    if not npx:
        print("  WARN: npx not found; advisory detector skipped. (Hard gates already passed.)")
        return
    try:
        proc = subprocess.run(
            [npx, "--yes", IMPECCABLE_PIN, "detect", "--fast", "--json", str(DIST)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=240, cwd=str(REPO),
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"  WARN: impeccable detect could not run ({type(e).__name__}: {e}). Advisory only.")
        return
    out = (proc.stdout or "").strip()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        tail = out[-400:] if out else (proc.stderr or "")[-400:]
        print(f"  WARN: impeccable output not parseable (exit {proc.returncode}). Tail: {tail}")
        return
    issues = data if isinstance(data, list) else next(
        (data[k] for k in ("issues", "findings", "results", "violations") if isinstance(data.get(k), list)), [])
    if not issues:
        print("  OK: impeccable detect found 0 issues.")
        return
    print(f"  ADVISORY: impeccable flags {len(issues)} issue(s) — triage against our own rules, do not auto-fix:")
    for it in issues[:8]:
        if isinstance(it, dict):
            rid = it.get("rule") or it.get("id") or "?"
            msg = it.get("message") or it.get("description") or ""
            loc = it.get("file") or it.get("path") or ""
            print(f"    [{rid}] {msg} {('(' + str(loc) + ')') if loc else ''}")
        else:
            print(f"    {it}")
    if len(issues) > 8:
        print(f"    ... and {len(issues) - 8} more (re-run npx {IMPECCABLE_PIN} detect {DIST} for the full list)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-deploy", action="store_true", help="run all gates against current live, no deploy")
    ap.add_argument("--skip-build", action="store_true", help="reuse existing dist, do not rebuild")
    ap.add_argument("--only", metavar="SLUG", help="restrict gates to one site slug")
    args = ap.parse_args()

    if not args.skip_build:
        print("== build ==")
        if run(["npm", "run", "build"], cwd=APP) != 0:
            print("FAIL: build failed.")
            return 1

    if not DIST.exists():
        print(f"FAIL: no dist at {DIST} (run without --skip-build).")
        return 1

    if not gate_aesthetics(args.only):
        return 1

    if not args.no_deploy:
        print("== deploy ==")
        if not Path(FLYCTL).is_file():
            print(f"FAIL: flyctl not found at {FLYCTL}. Fix: iwr https://fly.io/install.ps1 -useb | iex")
            return 1
        rc = run([FLYCTL, "deploy", ".", "--config", str(APP / "fly.toml"),
                  "--remote-only", "--now"], cwd=APP)
        if rc != 0:
            print("FAIL: flyctl deploy failed.")
            return 1

    print("== verify live origin ==")
    slugs = [args.only] if args.only else slugs_from_dist()
    if not verify(slugs):
        print("\nNOT LIVE: deployed origin does not match the local build (see above).")
        return 1

    live_urls = [f"{HOST}/{slug}/" for slug in slugs]
    if not gate_node_tool("axe-check.cjs", live_urls):
        return 1
    if not gate_node_tool("verify-rendered.cjs", live_urls):
        return 1

    advisory_impeccable()

    print(f"\nVERIFIED LIVE: {HOST} serves the current build for {len(slugs)} site(s); "
          f"axe + rendered-behavior gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
