#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deploy brisken-expense-recon, but only a tree that IS origin/main.

    uv run <tree>/workspace/clients/brisken/automations/expense-reconciliation/deploy.py
    ... deploy.py --dry-run          # every check, print the flyctl command, ship nothing
    ... deploy.py --image REF        # roll back to an image, keeping today's fly.toml

`flyctl deploy` ships whatever tree it is pointed at, `fly.toml` included, so
a worktree cut before the last merge silently undoes both code and platform
settings. On 2026-09-25 the machine was resized to shared-cpu-4x after a CPU
throttle outage (#1395); any deploy from an older tree would have shrunk it
back to one vCPU, and several sessions were deploying from such trees. This
script is the only sanctioned deploy path (`recon-accuracy-deploy-gate.py`
denies a direct `flyctl deploy` of this app), and it refuses before anything
ships when:

1. `git fetch origin main` fails: freshness cannot be proven.
2. The module has uncommitted or untracked files: the stamp would not
   describe what ships.
3. The module differs from origin/main: the tree is behind (or carries
   unmerged work). Only the module is compared, because the build context is
   the module; an unrelated merge elsewhere does not force a refresh.
4. A live machine is bigger than fly.toml's [[vm]]: someone resized the app
   without syncing fly.toml, and this deploy would shrink it.

Then it deploys with the GIT_COMMIT build stamp and verifies behaviour, not
the exit code: /healthz must report this commit and the live machine must
carry fly.toml's size. A tree that predates this script cannot run it, which
is the point: a stale tree has no path to a deploy.

Stdlib only. Never prints the Fly token.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import urllib.request
from pathlib import Path

APP = "brisken-expense-recon"
MODULE = Path(__file__).resolve().parent
HEALTH_URL = f"https://{APP}.fly.dev/healthz"
USER_AGENT = "brisken-recon-deploy/1"
VERIFY_BUDGET_S = 240


class Refused(Exception):
    """A precondition failed; nothing was deployed."""


# ── pure checks (unit-tested) ──────────────────────────────────────────────

def memory_mb(value: object) -> int:
    """fly.toml memory ('1024mb', '1gb', 1024) -> MB."""
    if isinstance(value, int):
        return value
    m = re.fullmatch(r"\s*(\d+)\s*(mb|gb)?\s*", str(value).lower())
    if not m:
        raise ValueError(f"unreadable memory value {value!r}")
    n = int(m.group(1))
    return n * 1024 if m.group(2) == "gb" else n


def desired_vm(fly_toml: dict) -> dict:
    """The [[vm]] block as {cpu_kind, cpus, memory_mb}."""
    vms = fly_toml.get("vm") or []
    if not vms:
        raise Refused("fly.toml has no [[vm]] block; the deploy would not pin a size")
    vm = vms[0]
    return {
        "cpu_kind": str(vm.get("cpu_kind", "shared")),
        "cpus": int(vm.get("cpus", 1)),
        "memory_mb": memory_mb(vm.get("memory", 256)),
    }


def shrink_problem(desired: dict, live: list[dict]) -> str | None:
    """Why deploying `desired` would shrink a live machine, or None."""
    for g in live:
        smaller = []
        if g.get("cpu_kind") == "performance" and desired["cpu_kind"] != "performance":
            smaller.append(f"cpu_kind {g['cpu_kind']} -> {desired['cpu_kind']}")
        if int(g.get("cpus", 0)) > desired["cpus"]:
            smaller.append(f"cpus {g['cpus']} -> {desired['cpus']}")
        if int(g.get("memory_mb", 0)) > desired["memory_mb"]:
            smaller.append(f"memory {g['memory_mb']} MB -> {desired['memory_mb']} MB")
        if smaller:
            return (
                f"machine {g.get('id', '?')} is bigger than fly.toml says "
                f"({'; '.join(smaller)}). Someone resized the app without "
                "syncing fly.toml. Bring fly.toml's [[vm]] in step via a PR "
                "first, or this deploy shrinks the live machine."
            )
    return None


def freshness_problem(*, dirty: str, changed: str, behind: int, ahead: int) -> str | None:
    """Why this tree must not ship, or None."""
    if dirty.strip():
        return (
            "the module has uncommitted or untracked files, so the commit "
            f"stamp would not describe what ships:\n{dirty.rstrip()}"
        )
    if changed.strip():
        refresh = "git -C <tree> checkout --detach origin/main"
        where = []
        if behind:
            where.append(f"{behind} commit(s) behind origin/main")
        if ahead:
            where.append(f"{ahead} commit(s) not on origin/main")
        return (
            f"the module differs from origin/main ({', '.join(where) or 'diverged'}); "
            "shipping it would undo merged work, fly.toml's machine size "
            f"included. Files that differ:\n{changed.rstrip()}\n"
            f"Refresh the tree ({refresh}) and run this script from it."
        )
    return None


# ── effects ────────────────────────────────────────────────────────────────

def git(module: Path, *args: str, timeout: int = 60) -> str:
    out = subprocess.run(
        ["git", "-C", str(module), *args],
        capture_output=True, text=True, timeout=timeout,
    )
    if out.returncode != 0:
        raise Refused(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def check_tree(module: Path) -> str:
    """Fetch, then refuse unless the module is clean and equal to
    origin/main. Returns the HEAD sha."""
    try:
        git(module, "fetch", "origin", "main", "--quiet", timeout=90)
    except (Refused, subprocess.SubprocessError, OSError) as exc:
        raise Refused(f"git fetch origin main failed, so freshness cannot be proven ({exc})") from exc
    head = git(module, "rev-parse", "HEAD").strip()
    dirty = git(module, "status", "--porcelain", "--untracked-files=all", "--", ".")
    changed = git(module, "diff", "--name-only", "HEAD", "origin/main", "--", ".")
    counts = git(module, "rev-list", "--left-right", "--count", "HEAD...origin/main").split()
    ahead, behind = int(counts[0]), int(counts[1])
    problem = freshness_problem(dirty=dirty, changed=changed, behind=behind, ahead=ahead)
    if problem:
        raise Refused(problem)
    return head


def fly_env() -> dict:
    """Child env with FLY_API_TOKEN, read from ~/.fly/config.yml when flyctl
    cannot discover its own token (seen 2026-09-23). Never printed."""
    env = dict(os.environ)
    if not env.get("FLY_API_TOKEN"):
        cfg = Path.home() / ".fly" / "config.yml"
        try:
            for line in cfg.read_text(encoding="utf-8").splitlines():
                if line.startswith("access_token:"):
                    env["FLY_API_TOKEN"] = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
    return env


def flyctl() -> str:
    exe = shutil.which("flyctl") or shutil.which("fly")
    if not exe:
        raise Refused("flyctl is not on PATH")
    return exe


def live_guests() -> list[dict]:
    out = subprocess.run(
        [flyctl(), "machine", "list", "-a", APP, "--json"],
        capture_output=True, text=True, timeout=90, env=fly_env(),
    )
    if out.returncode != 0:
        raise Refused(f"cannot read the live machines: {out.stderr.strip()[-400:]}")
    guests = []
    for m in json.loads(out.stdout or "[]"):
        g = dict((m.get("config") or {}).get("guest") or {})
        g["id"] = m.get("id")
        guests.append(g)
    if not guests:
        raise Refused("flyctl lists no machines for the app; nothing to compare against")
    return guests


def healthz() -> dict | None:
    req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - a restarting machine answers nothing
        return None


def preflight() -> tuple[str, dict]:
    """Every refusal check. Returns (HEAD sha, desired vm)."""
    head = check_tree(MODULE)
    with open(MODULE / "fly.toml", "rb") as fh:
        desired = desired_vm(tomllib.load(fh))
    problem = shrink_problem(desired, live_guests())
    if problem:
        raise Refused(problem)
    return head, desired


def deploy_command(head: str, image: str | None) -> list[str]:
    cmd = [flyctl(), "deploy", str(MODULE), "--config", str(MODULE / "fly.toml"), "-a", APP]
    if image:
        return [*cmd, "--image", image]
    return [*cmd, "--remote-only", "--build-arg", f"GIT_COMMIT={head}"]


def verify(head: str, desired: dict, image: str | None) -> list[str]:
    """Problems with the live result; empty means verified."""
    deadline = time.monotonic() + VERIFY_BUDGET_S
    body = None
    while time.monotonic() < deadline:
        body = healthz()
        commit = ((body or {}).get("server") or {}).get("commit")
        if body and body.get("status") == "ok" and (image or commit == head):
            break
        time.sleep(5)
    problems = []
    commit = ((body or {}).get("server") or {}).get("commit")
    if not body or body.get("status") != "ok":
        problems.append(f"/healthz did not answer ok within {VERIFY_BUDGET_S} s")
    elif not image and commit != head:
        problems.append(f"/healthz reports commit {commit!r}, not {head} (someone else deployed?)")
    for g in live_guests():
        got = (g.get("cpu_kind"), int(g.get("cpus", 0)), int(g.get("memory_mb", 0)))
        want = (desired["cpu_kind"], desired["cpus"], desired["memory_mb"])
        if got != want:
            problems.append(f"machine {g['id']} runs {got}, fly.toml says {want}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="run every check, ship nothing")
    ap.add_argument("--image", help="deploy this registry image instead of building (rollback)")
    args = ap.parse_args(argv)
    try:
        head, desired = preflight()
    except Refused as exc:
        print(f"REFUSED, nothing deployed: {exc}", file=sys.stderr)
        return 2
    cmd = deploy_command(head, args.image)
    print(f"tree OK: module == origin/main at {head[:12]}, clean")
    print(f"size OK: fly.toml {desired} is not smaller than the live machine")
    print("deploy:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    if args.dry_run:
        print("dry run: nothing deployed")
        return 0
    rc = subprocess.run(cmd, cwd=str(MODULE), env=fly_env()).returncode
    if rc != 0:
        print(f"flyctl deploy exited {rc}", file=sys.stderr)
        return rc
    problems = verify(head, desired, args.image)
    if problems:
        print("NOT VERIFIED:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    what = f"image {args.image}" if args.image else f"commit {head}"
    print(f"VERIFIED: /healthz ok on {what}; machine size matches fly.toml {desired}")
    print("Now open expenses.brisken.com and one month: the API answering is not the screen working.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
