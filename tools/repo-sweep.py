# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Nightly unattended repo sweep: commit, push, and PR uncommitted work.

Prevents the weeks-long uncommitted-backlog problem (2026-07-17: 301 dirty
entries, 64-file conflict resolution) by sweeping quiesced working trees on
a schedule. Non-LLM, deterministic, safety-gated.

Per-repo policy:
  pr    - never commit on main: branch sys/sweep-YYYYMMDD, thematic commits,
          push, open PR, wait for CI (bounded), squash-merge on green
          (mirrors rule_no_auto_commit Bands 1-2).
  push  - commit on the current branch and push it (personal backup repos).

Safety gates (any hit = skip, log, continue):
  - repo missing / not git / merge-rebase in progress / detached HEAD
  - quiesce: if ANY dirty file changed within --quiesce-minutes, the repo
    is mid-work; skip entirely (partial sweeps make incoherent commits)
  - credential-shaped filenames are never committed even if untracked
  - files > 50 MB are excluded and logged
  - > 5000 dirty entries means something is broken; skip and log

Default is dry-run. The scheduled task passes --execute.
Log: %USERPROFILE%/.repo-sweep.log (one block per run).
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import os
import subprocess
import sys
import time

REPOS = [
    {"path": r"C:\Users\neuma_p1qrsic\Repo\agentic-ops1", "policy": "pr"},
    {"path": r"C:\Users\neuma_p1qrsic\Repo\video-gen", "policy": "push"},
    {"path": r"C:\Users\neuma_p1qrsic\Repo\agentic-dev1", "policy": "push"},
]

LOG_FILE = os.path.join(os.path.expanduser("~"), ".repo-sweep.log")
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ENTRIES = 5000
CI_WAIT_SECONDS = 15 * 60

CREDENTIAL_PATTERNS = [
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "*_key",
    "*token*", "*secret*", "*credential*", "*password*", ".netrc",
    ".npmrc", ".pypirc",
]
CREDENTIAL_ALLOW = [".env.example", ".env.sample", ".env.template", ".env.dist"]


def is_credential_name(path: str) -> bool:
    base = os.path.basename(path).lower()
    if base in CREDENTIAL_ALLOW:
        return False
    return any(fnmatch.fnmatch(base, p) for p in CREDENTIAL_PATTERNS)


def group_for_path(path: str) -> str:
    """Thematic commit group for a repo-relative posix path (pr policy)."""
    parts = path.split("/")
    top = parts[0]
    if top == "docs":
        return "docs"
    if top in (".claude", "tools", "scripts", ".github") or top in (".gitignore",):
        return "system"
    if top == "platform":
        return "platform"
    if top == "workspace" and len(parts) >= 3 and parts[1] == "clients":
        return f"client:{parts[2]}"
    if top == "workspace":
        return "workspace"
    return "misc"


def run(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return run(["git", "-C", repo, *args], cwd=repo)


def dirty_entries(repo: str) -> list[tuple[str, str]]:
    """[(status, repo-relative posix path)] for tracked changes + untracked."""
    out = git(repo, "status", "--porcelain").stdout
    entries = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        status, path = line[:2], line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append((status, path))
    return entries


def newest_mtime(repo: str, entries: list[tuple[str, str]]) -> float:
    newest = 0.0
    for _, rel in entries:
        full = os.path.join(repo, rel.replace("/", os.sep))
        try:
            newest = max(newest, os.path.getmtime(full))
        except OSError:
            pass  # deleted files have no mtime; deletion age is unknowable
    return newest


def blocked_state(repo: str) -> str | None:
    gitdir = git(repo, "rev-parse", "--git-dir").stdout.strip()
    if not gitdir:
        return "not a git repo"
    gitdir = os.path.join(repo, gitdir) if not os.path.isabs(gitdir) else gitdir
    for marker in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD"):
        if os.path.exists(os.path.join(gitdir, marker)):
            return f"operation in progress ({marker})"
    branch = git(repo, "branch", "--show-current").stdout.strip()
    if not branch:
        return "detached HEAD"
    return None


def plan(repo: str, entries: list[tuple[str, str]]) -> tuple[dict[str, list[str]], list[str]]:
    """(group -> paths to commit, skipped-with-reason lines)."""
    groups: dict[str, list[str]] = {}
    skipped: list[str] = []
    for status, rel in entries:
        full = os.path.join(repo, rel.replace("/", os.sep))
        if is_credential_name(rel):
            skipped.append(f"{rel} (credential-shaped)")
            continue
        if status != " D" and os.path.isfile(full) and os.path.getsize(full) > MAX_FILE_BYTES:
            skipped.append(f"{rel} (>50MB)")
            continue
        groups.setdefault(group_for_path(rel), []).append(rel)
    return groups, skipped


def log(lines: list[str]) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    block = "\n".join(f"[{stamp}] {ln}" for ln in lines) + "\n"
    print(block, end="")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(block)


def wait_for_ci_and_merge(repo: str, branch: str, lines: list[str]) -> None:
    pr = run(["gh", "pr", "list", "--head", branch, "--json", "number",
              "--jq", ".[0].number"], cwd=repo).stdout.strip()
    if not pr:
        lines.append(f"  no PR found for {branch}; leaving pushed branch")
        return
    deadline = time.time() + CI_WAIT_SECONDS
    while time.time() < deadline:
        checks = run(["gh", "pr", "checks", pr], cwd=repo)
        combined = checks.stdout + checks.stderr
        if "fail" in combined:
            lines.append(f"  PR #{pr}: CI red; left open for review")
            return
        if checks.returncode == 0 and "pending" not in combined:
            merge = run(["gh", "pr", "merge", pr, "--squash", "--delete-branch"], cwd=repo)
            lines.append(f"  PR #{pr}: CI green -> squash-merged"
                         if merge.returncode == 0 else
                         f"  PR #{pr}: merge failed: {merge.stderr.strip()[:120]}")
            return
        time.sleep(60)
    lines.append(f"  PR #{pr}: CI still pending after {CI_WAIT_SECONDS // 60}m; left open")


def sweep_repo(cfg: dict, execute: bool, quiesce_minutes: int) -> None:
    repo, policy = cfg["path"], cfg["policy"]
    name = os.path.basename(repo)
    lines = [f"=== {name} (policy={policy}) ==="]

    if not os.path.isdir(repo):
        lines.append("  skip: path missing")
        return log(lines)
    reason = blocked_state(repo)
    if reason:
        lines.append(f"  skip: {reason}")
        return log(lines)

    entries = dirty_entries(repo)
    if not entries:
        lines.append("  clean; nothing to sweep")
        return log(lines)
    if len(entries) > MAX_ENTRIES:
        lines.append(f"  skip: {len(entries)} entries exceeds sanity cap {MAX_ENTRIES}")
        return log(lines)

    age_min = (time.time() - newest_mtime(repo, entries)) / 60
    if age_min < quiesce_minutes:
        lines.append(f"  skip: newest change {age_min:.0f}m ago (< quiesce {quiesce_minutes}m)")
        return log(lines)

    groups, skipped = plan(repo, entries)
    for s in skipped:
        lines.append(f"  excluded: {s}")
    if not groups:
        lines.append("  nothing committable after exclusions")
        return log(lines)

    today = dt.date.today().strftime("%Y-%m-%d")
    branch = git(repo, "branch", "--show-current").stdout.strip()
    lines.append(f"  plan: {sum(len(v) for v in groups.values())} paths in "
                 f"{len(groups)} commit(s) on branch {branch}")
    for g, paths in sorted(groups.items()):
        lines.append(f"    {g}: {len(paths)} paths")
    if not execute:
        lines.append("  DRY-RUN: no changes made")
        return log(lines)

    sweep_branch = branch
    if policy == "pr":
        if branch in ("main", "master"):
            sweep_branch = f"sys/sweep-{today.replace('-', '')}"
            git(repo, "checkout", "-B", sweep_branch)
            lines.append(f"  branched {sweep_branch} (never commit on main)")

    for g, paths in sorted(groups.items()):
        git(repo, "add", "-A", "--", *paths)
        msg = f"sweep: {g} backlog {today}\n\nAutomated-by: tools/repo-sweep.py"
        c = git(repo, "commit", "-q", "-m", msg)
        lines.append(f"  commit {g}: {'ok' if c.returncode == 0 else c.stderr.strip()[:100]}")

    push = git(repo, "push", "-u", "origin", sweep_branch)
    lines.append(f"  push {sweep_branch}: {'ok' if push.returncode == 0 else push.stderr.strip()[:140]}")
    if push.returncode != 0:
        return log(lines)

    if policy == "pr":
        existing = run(["gh", "pr", "list", "--head", sweep_branch, "--json", "number",
                        "--jq", ".[0].number"], cwd=repo).stdout.strip()
        if not existing:
            pr = run(["gh", "pr", "create", "--fill-first",
                      "--title", f"sweep: uncommitted backlog {today}",
                      "--body", "Automated nightly sweep by tools/repo-sweep.py. "
                                "Quiesce-gated; credential-shaped and >50MB files excluded.\n\n"
                                "\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)"],
                     cwd=repo)
            lines.append(f"  PR: {'created' if pr.returncode == 0 else pr.stderr.strip()[:140]}")
        wait_for_ci_and_merge(repo, sweep_branch, lines)
        if branch in ("main", "master"):
            git(repo, "checkout", branch)
            git(repo, "pull", "--ff-only")
            lines.append(f"  returned to {branch}")
    log(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--execute", action="store_true", help="act (default: dry-run)")
    ap.add_argument("--quiesce-minutes", type=int, default=120)
    ap.add_argument("--repo", help="sweep only the repo whose folder name matches")
    args = ap.parse_args()

    for cfg in REPOS:
        if args.repo and os.path.basename(cfg["path"]) != args.repo:
            continue
        try:
            sweep_repo(cfg, args.execute, args.quiesce_minutes)
        except Exception as ex:  # one repo's failure must not stop the others
            log([f"=== {os.path.basename(cfg['path'])} ===", f"  ERROR: {ex}"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
