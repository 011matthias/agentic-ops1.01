# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""web-build-signals.py — deterministic session-entry state probe for local-web.

One JSON of cheap signals so a web-build session leads with 2-3 pointed next
steps instead of scope interrogation (pattern from impeccable's
context-signals.mjs, adopted 2026-06-11). No LLM, never throws: every probe
degrades to null/empty rather than failing the whole report.

Signals:
  git        — current branch + changed files under workspace/projects/local-web
  devServer  — TCP probe on the astro dev port (4321)
  sites      — per slug: BRIEF.md / theme.css / TEST.md presence, dist build
               presence, latest .critique score (from audit --persist snapshots)
  dist       — whether dist/ exists and is newer than the newest source edit

Mapping the signals to a lead (prose, agent-side, mirror of SKILL.md routing):
  no BRIEF for a site in scope        -> CONCEIVE first
  BRIEF + no dist / stale dist        -> BUILD, then SHIP
  low critique score / FAILs latest   -> rework against the snapshot findings
  changed files pointing at one slug  -> scope to that slug by name
  dev server up                       -> live iteration available

Never auto-runs anything off the recommendation; the agent proposes, the
owner confirms. Usage: uv run tools/web-build-signals.py
"""
from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCAL_WEB = REPO / "workspace" / "projects" / "local-web"
APP = LOCAL_WEB / "app"
SITES_DIR = APP / "src" / "sites"
DIST = APP / "dist"
SNAP_DIR = LOCAL_WEB / ".critique"
DEV_PORTS = (4321,)


def git_signals() -> dict:
    out = {"branch": None, "changedLocalWeb": []}
    try:
        out["branch"] = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=str(REPO), timeout=10,
        ).stdout.strip() or None
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(REPO), timeout=10,
        ).stdout
        out["changedLocalWeb"] = sorted({
            line[3:].strip().strip('"')
            for line in status.splitlines()
            if "workspace/projects/local-web/" in line.replace("\\", "/")
        })[:50]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return out


def dev_server_up() -> bool:
    for port in DEV_PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return True
        except OSError:
            continue
    return False


def latest_score(slug: str) -> dict | None:
    if not SNAP_DIR.is_dir():
        return None
    snaps = sorted(SNAP_DIR.glob(f"*__{slug}.json"))
    if not snaps:
        return None
    try:
        d = json.loads(snaps[-1].read_text(encoding="utf-8"))
        return {"score": d.get("score"), "fail": d.get("fail"), "warn": d.get("warn"), "ts": d.get("ts")}
    except (OSError, json.JSONDecodeError):
        return None


def site_signals() -> list[dict]:
    sites = []
    if not SITES_DIR.is_dir():
        return sites
    for d in sorted(p for p in SITES_DIR.iterdir() if p.is_dir()):
        slug = d.name
        sites.append({
            "slug": slug,
            "brief": (d / "BRIEF.md").is_file(),
            "theme": (d / "theme.css").is_file(),
            "testMd": (d / "TEST.md").is_file(),
            "distBuilt": (DIST / slug / "index.html").is_file(),
            "critique": latest_score(slug),
        })
    return sites


def dist_signals() -> dict:
    if not DIST.is_dir():
        return {"exists": False, "fresh": None}
    try:
        dist_m = max((p.stat().st_mtime for p in DIST.rglob("*.html")), default=0)
        src_m = max((p.stat().st_mtime for ext in ("*.astro", "*.css")
                     for p in (APP / "src").rglob(ext)), default=0)
        return {"exists": True, "fresh": dist_m >= src_m}
    except OSError:
        return {"exists": True, "fresh": None}


def main() -> int:
    print(json.dumps({
        "git": git_signals(),
        "devServer": dev_server_up(),
        "sites": site_signals(),
        "dist": dist_signals(),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
