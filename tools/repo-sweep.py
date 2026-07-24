# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Nightly unattended repo sweep: commit, push, and PR uncommitted work.

Prevents the weeks-long uncommitted-backlog problem (2026-07-17: 301 dirty
entries, 64-conflict merge) by sweeping quiesced working trees on a schedule.
Non-LLM, deterministic, safety-gated, self-healing.

Per-repo policy:
  pr    - never commit on main: branch sys/sweep-YYYYMMDD-HHMM, thematic
          commits, adopt+supersede any older open sweep PRs, push, open PR,
          poll structured CI state (gh pr view --json), self-heal a
          CONFLICTING PR once via a local `git merge origin/main` (the
          .gitattributes merge=union rules resolve append-only ledgers),
          squash-merge on green (mirrors rule_no_auto_commit Bands 1-2).
  push  - commit on the current branch and push it (personal backup repos).

Safety gates (any hit = skip, log, continue):
  - repo missing / not git / merge-rebase in progress / detached HEAD
  - quiesce: if ANY dirty file changed within --quiesce-minutes, the repo
    is mid-work; skip entirely (partial sweeps make incoherent commits).
    Deleted paths age via their nearest existing ancestor directory (NTFS
    bumps the parent dir mtime on unlink), never epoch-0.
  - untracked directories are expanded to per-file entries before gating
    (porcelain lists them as ONE entry; a directory-level add would bypass
    the per-file gates -- the .remotion 193MB first-night lesson)
  - regenerable cache/tooling dirs (.remotion, node_modules, .venv,
    __pycache__, ...) are never committed at any depth
  - credential-shaped filenames are never committed even if untracked
  - files > 50 MB are excluded and logged
  - > 5000 dirty entries means something is broken; skip and log

Micro-mode: --normalize-sessions FILE... repairs the union-merge artifact in
docs/sessions/*.md (duplicated frontmatter counters, colliding Session
numbers) by recomputing everything from the body. Idempotent, fail-open.

Session-log fan-out: before batching docs/, per-session shard files
(docs/sessions/YYYY-MM-DD-<sid>.md, written by /comd_checkpoint and
/comd_eod-capture) are folded into the canonical daily file via
tools/merge-session-logs.py, so the sweep commits folded canonical files,
not shards. Fail-open: a fold failure logs and the sweep continues with the
shards as-is (the .gitattributes union rules still cover them).

Default is dry-run. The scheduled task passes --execute.
Log: %USERPROFILE%/.repo-sweep.log (one block per run).
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
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
NO_CHECKS_GRACE = 180

CREDENTIAL_PATTERNS = [
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "*_key",
    "*token*", "*secret*", "*credential*", "*password*", ".netrc",
    ".npmrc", ".pypirc",
]
CREDENTIAL_ALLOW = [".env.example", ".env.sample", ".env.template", ".env.dist"]

# Regenerable cache/tooling dirs: never commit-worthy at ANY path depth.
# First-night lesson (2026-07-17): an untracked .remotion/ appeared as ONE
# porcelain entry, so a directory-level `git add` swallowed a 193MB browser
# exe past the per-file size gate and GitHub rejected the push.
JUNK_DIRS = {
    ".remotion", "node_modules", ".venv", "__pycache__", ".next", ".astro",
    ".pytest_cache", ".ruff_cache", ".git", ".mypy_cache", ".tox",
}

RED_CONCLUSIONS = {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED",
                   "STARTUP_FAILURE"}


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


def classify_rollup(rollup: list[dict]) -> str:
    """Overall check state from gh's statusCheckRollup: none|red|pending|green."""
    if not rollup:
        return "none"
    red = pending = False
    for c in rollup:
        if c.get("__typename") == "StatusContext":
            state = (c.get("state") or "").upper()
            if state in ("FAILURE", "ERROR"):
                red = True
            elif state in ("PENDING", "EXPECTED"):
                pending = True
        else:  # CheckRun
            conclusion = (c.get("conclusion") or "").upper()
            status = (c.get("status") or "").upper()
            if conclusion in RED_CONCLUSIONS:
                red = True
            elif status != "COMPLETED":
                pending = True
    if red:
        return "red"
    if pending:
        return "pending"
    return "green"


def decide_pr_action(checks: str, mergeable: str, healed: bool,
                     grace_expired: bool) -> str:
    """The sweep-PR decision table. Red beats conflict beats everything."""
    if checks == "red":
        return "leave_red"
    if mergeable == "CONFLICTING":
        return "leave_conflict" if healed else "heal"
    if checks == "green":
        return "merge" if mergeable == "MERGEABLE" else "wait"
    if checks == "none":
        return "leave_nochecks" if grace_expired else "wait"
    return "wait"  # pending


def sweep_branch_name(now: dt.datetime) -> str:
    return f"sys/sweep-{now.strftime('%Y%m%d-%H%M')}"


def failed_check_names(rollup: list[dict]) -> list[str]:
    names = []
    for c in rollup:
        if c.get("__typename") == "StatusContext":
            if (c.get("state") or "").upper() in ("FAILURE", "ERROR"):
                names.append(c.get("context") or "status-context")
        elif (c.get("conclusion") or "").upper() in RED_CONCLUSIONS:
            names.append(c.get("name") or "check")
    return names


def normalize_session_frontmatter(text: str) -> str:
    """Repair union-merge artifacts in a docs/sessions/*.md file.

    Renumbers '### Session N' headings sequentially, recomputes the
    `sessions:` and `friction_events:` counters from the body, unions
    duplicated inline-list keys, and drops duplicate frontmatter lines.
    Idempotent; returns the input unchanged on any parse failure.
    """
    try:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return text
        try:
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        except StopIteration:
            return text
        front, body = lines[1:end], lines[end + 1:]

        n = 0

        def renumber(m: re.Match) -> str:
            nonlocal n
            n += 1
            return f"### Session {n}"

        body_text = re.sub(r"^### Session \d+", renumber,
                           "\n".join(body), flags=re.MULTILINE)
        friction = sum(int(m.group(1)) for m in
                       re.finditer(r"^\*\*Friction:\*\*\s*(\d+)", body_text,
                                   flags=re.MULTILINE))

        def items(val: str) -> list[str]:
            return [x.strip() for x in val.strip().strip("[]").split(",") if x.strip()]

        list_keys = ("projects_touched", "work_types")
        merged_lists: dict[str, list[str]] = {k: [] for k in list_keys}
        out: list[str] = []
        seen: set[str] = set()
        for ln in front:
            m = re.match(r"^(\w+):\s*(.*)$", ln)
            if not m:
                if ln not in seen:
                    out.append(ln)
                    seen.add(ln)
                continue
            key, val = m.group(1), m.group(2)
            if key in list_keys:
                for item in items(val):
                    if item not in merged_lists[key]:
                        merged_lists[key].append(item)
                if key not in seen:
                    out.append(ln)  # placeholder, rewritten below
                    seen.add(key)
            elif key in ("sessions", "friction_events"):
                if key not in seen:
                    out.append(ln)  # placeholder, rewritten below
                    seen.add(key)
            else:
                if key not in seen:
                    out.append(ln)
                    seen.add(key)

        rebuilt = []
        for ln in out:
            m = re.match(r"^(\w+):", ln)
            key = m.group(1) if m else None
            if key == "sessions":
                rebuilt.append(f"sessions: {n}")
            elif key == "friction_events":
                rebuilt.append(f"friction_events: {friction}")
            elif key in list_keys:
                rebuilt.append(f"{key}: [{', '.join(merged_lists[key])}]")
            else:
                rebuilt.append(ln)

        result = "\n".join(["---", *rebuilt, "---", body_text])
        if text.endswith("\n"):
            result += "\n"
        return result
    except Exception:
        return text


def fold_session_shards(repo: str, execute: bool, lines: list[str]) -> None:
    """Fold docs/sessions shard files (YYYY-MM-DD-<sid>.md) into the canonical
    daily files (tools/merge-session-logs.py) before the docs batch commits,
    then normalize the folded files' frontmatter. Fail-open: any failure logs
    and the sweep continues -- the union rules still cover raw shards."""
    sessions_dir = os.path.join(repo, "docs", "sessions")
    if not os.path.isdir(sessions_dir):
        return
    try:
        import importlib.util
        tool = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "merge-session-logs.py")
        spec = importlib.util.spec_from_file_location("merge_session_logs", tool)
        msl = sys.modules.get(spec.name)
        if msl is None:
            msl = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = msl  # dataclass resolution needs the registry
            spec.loader.exec_module(msl)
        for r in msl.run_fold(sessions_dir, apply=execute):
            if r.error:
                lines.append(f"  session-fold: {r.date}: ERROR {r.error}")
                continue
            if not (r.folded or r.redundant):
                continue
            verb = "folded" if execute else "would fold"
            lines.append(f"  session-fold: {verb} {len(r.folded)} shard(s), "
                         f"{len(r.redundant)} redundant -> docs/sessions/{r.date}.md")
            if execute and r.folded:
                full = str(r.canonical)
                try:
                    text = open(full, encoding="utf-8").read()
                    fixed = normalize_session_frontmatter(text)
                    if fixed != text:
                        open(full, "w", encoding="utf-8", newline="\n").write(fixed)
                except OSError:
                    pass
    except Exception as ex:
        lines.append(f"  session-fold: skipped ({ex}); shards left as-is")


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
    """Newest mtime across dirty paths. Deleted paths age via their nearest
    existing ancestor directory (never epoch-0, which would bypass quiesce)."""
    newest = 0.0
    repo_norm = os.path.normcase(os.path.normpath(repo))
    for _, rel in entries:
        probe = os.path.join(repo, rel.replace("/", os.sep))
        while not os.path.exists(probe):
            parent = os.path.dirname(probe)
            if parent == probe or os.path.normcase(os.path.normpath(probe)) == repo_norm:
                break
            probe = parent
        try:
            newest = max(newest, os.path.getmtime(probe))
        except OSError:
            pass
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


def is_junk_path(rel: str) -> bool:
    return any(part in JUNK_DIRS for part in rel.rstrip("/").split("/"))


def expand_entry(repo: str, status: str, rel: str) -> list[tuple[str, str]]:
    """Untracked DIRECTORIES arrive as one porcelain entry; expand them to
    per-file entries so the credential and size gates see every file."""
    full = os.path.join(repo, rel.replace("/", os.sep))
    if status.strip() != "??" or not os.path.isdir(full):
        return [(status, rel)]
    out: list[tuple[str, str]] = []
    for root, dirs, files in os.walk(full):
        dirs[:] = [d for d in dirs if d not in JUNK_DIRS]
        for f in files:
            frel = os.path.relpath(os.path.join(root, f), repo).replace(os.sep, "/")
            out.append(("??", frel))
    return out


def plan(repo: str, entries: list[tuple[str, str]]) -> tuple[dict[str, list[str]], list[str]]:
    """(group -> paths to commit, skipped-with-reason lines)."""
    groups: dict[str, list[str]] = {}
    skipped: list[str] = []
    expanded: list[tuple[str, str]] = []
    for status, rel in entries:
        if is_junk_path(rel):
            skipped.append(f"{rel} (regenerable cache/tooling dir)")
            continue
        expanded.extend(expand_entry(repo, status, rel))
    for status, rel in expanded:
        full = os.path.join(repo, rel.replace("/", os.sep))
        if is_junk_path(rel):
            skipped.append(f"{rel} (regenerable cache/tooling dir)")
            continue
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


def normalize_merged_sessions(repo: str, lines: list[str]) -> None:
    """After a union merge, repair frontmatter in session files it touched."""
    diff = git(repo, "diff", "--name-only", "HEAD^1", "HEAD", "--",
               "docs/sessions").stdout.split()
    changed = []
    for rel in diff:
        if not rel.endswith(".md"):
            continue
        full = os.path.join(repo, rel.replace("/", os.sep))
        try:
            text = open(full, encoding="utf-8").read()
        except OSError:
            continue
        fixed = normalize_session_frontmatter(text)
        if fixed != text:
            open(full, "w", encoding="utf-8", newline="\n").write(fixed)
            changed.append(rel)
    if changed:
        git(repo, "add", "--", *changed)
        git(repo, "commit", "-q", "-m",
            "sweep: normalize session frontmatter after union merge\n\n"
            "Automated-by: tools/repo-sweep.py")
        lines.append(f"  normalized session frontmatter: {', '.join(changed)}")


def self_heal_conflict(repo: str, lines: list[str]) -> bool:
    """Merge origin/main into the sweep branch locally (union drivers apply)."""
    git(repo, "fetch", "--quiet", "origin", "main")
    merge = git(repo, "merge", "--no-edit", "origin/main")
    if merge.returncode != 0:
        conflicted = git(repo, "diff", "--name-only",
                         "--diff-filter=U").stdout.split()
        git(repo, "merge", "--abort")
        lines.append("  self-heal: real conflicts, aborted "
                     f"({', '.join(conflicted[:8]) or 'unknown paths'})")
        return False
    normalize_merged_sessions(repo, lines)
    push = git(repo, "push")
    if push.returncode != 0:
        lines.append(f"  self-heal: push failed: {push.stderr.strip()[:140]}")
        return False
    lines.append("  self-heal: merged origin/main cleanly (union) and pushed")
    return True


def supersede_old_sweeps(repo: str, current_branch: str, lines: list[str]) -> None:
    """Adopt older open sweep PRs into this branch, then close them."""
    listed = run(["gh", "pr", "list", "--state", "open",
                  "--json", "number,headRefName"], cwd=repo)
    if listed.returncode != 0:
        return
    try:
        prs = json.loads(listed.stdout or "[]")
    except json.JSONDecodeError:
        return
    for pr in prs:
        branch = pr.get("headRefName", "")
        if not branch.startswith("sys/sweep-") or branch == current_branch:
            continue
        git(repo, "fetch", "--quiet", "origin", branch)
        merge = git(repo, "merge", "--no-edit", f"origin/{branch}")
        if merge.returncode != 0:
            git(repo, "merge", "--abort")
            lines.append(f"  supersede: could not adopt PR #{pr['number']} "
                         f"({branch}); leaving it open")
            continue
        run(["gh", "pr", "close", str(pr["number"]),
             "--comment", f"Superseded by {current_branch}; its commits are "
                          "now contained in the newer sweep PR.",
             "--delete-branch"], cwd=repo)
        git(repo, "branch", "-D", branch)
        lines.append(f"  supersede: adopted + closed PR #{pr['number']} ({branch})")


def wait_for_ci_and_merge(repo: str, branch: str, lines: list[str]) -> bool:
    """Poll structured PR state and act per the decision table. True if merged."""
    pr = run(["gh", "pr", "list", "--head", branch, "--json", "number",
              "--jq", ".[0].number"], cwd=repo).stdout.strip()
    if not pr:
        lines.append(f"  no PR found for {branch}; leaving pushed branch")
        return False
    start = time.time()
    deadline = start + CI_WAIT_SECONDS
    healed = False
    while time.time() < deadline:
        view = run(["gh", "pr", "view", pr, "--json",
                    "mergeable,mergeStateStatus,statusCheckRollup"], cwd=repo)
        if view.returncode != 0:
            time.sleep(60)
            continue
        try:
            data = json.loads(view.stdout)
        except json.JSONDecodeError:
            time.sleep(60)
            continue
        checks = classify_rollup(data.get("statusCheckRollup") or [])
        mergeable = (data.get("mergeable") or "UNKNOWN").upper()
        action = decide_pr_action(checks, mergeable, healed,
                                  time.time() - start > NO_CHECKS_GRACE)
        if action == "merge":
            merge = run(["gh", "pr", "merge", pr, "--squash", "--delete-branch"],
                        cwd=repo)
            if merge.returncode == 0:
                lines.append(f"  PR #{pr}: CI green -> squash-merged")
                return True
            lines.append(f"  PR #{pr}: merge failed "
                         f"(mergeStateStatus={data.get('mergeStateStatus')}): "
                         f"{merge.stderr.strip()[:140]}")
            return False
        if action == "leave_red":
            names = failed_check_names(data.get("statusCheckRollup") or [])
            lines.append(f"  PR #{pr}: CI red ({', '.join(names) or 'unknown'}); "
                         "left open for review")
            return False
        if action == "heal":
            if self_heal_conflict(repo, lines):
                healed = True
                deadline = time.time() + CI_WAIT_SECONDS
                continue
            lines.append(f"  PR #{pr}: CONFLICTING and not auto-healable; left open")
            return False
        if action == "leave_conflict":
            lines.append(f"  PR #{pr}: still CONFLICTING after one heal; left open")
            return False
        if action == "leave_nochecks":
            lines.append(f"  PR #{pr}: NO CHECKS reported after "
                         f"{NO_CHECKS_GRACE}s -- workflow trigger broken? "
                         "NOT merging without CI; left open")
            return False
        time.sleep(60)
    lines.append(f"  PR #{pr}: CI still pending after "
                 f"{CI_WAIT_SECONDS // 60}m; left open")
    return False


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

    # Fold session-log shards into the canonical daily files BEFORE batching
    # docs/, so the sweep commits folded files, not shards. After the quiesce
    # gate on purpose: the fold's fresh writes must not trip it.
    fold_session_shards(repo, execute, lines)
    if execute:
        entries = dirty_entries(repo)  # the fold changed the tree
        if not entries:
            lines.append("  clean after session fold; nothing to sweep")
            return log(lines)

    groups, skipped = plan(repo, entries)
    for s in skipped:
        lines.append(f"  excluded: {s}")
    if not groups:
        lines.append("  nothing committable after exclusions")
        return log(lines)

    now = dt.datetime.now()
    today = now.date().isoformat()
    original_branch = git(repo, "branch", "--show-current").stdout.strip()
    lines.append(f"  plan: {sum(len(v) for v in groups.values())} paths in "
                 f"{len(groups)} commit(s) on branch {original_branch}")
    for g, paths in sorted(groups.items()):
        lines.append(f"    {g}: {len(paths)} paths")
    if not execute:
        lines.append("  DRY-RUN: no changes made")
        return log(lines)

    sweep_branch = original_branch
    merged = False
    try:
        if policy == "pr" and original_branch in ("main", "master"):
            sweep_branch = sweep_branch_name(now)
            co = git(repo, "checkout", "-b", sweep_branch)
            if co.returncode != 0:
                lines.append(f"  abort: checkout -b failed: {co.stderr.strip()[:120]}")
                return
            lines.append(f"  branched {sweep_branch} (never commit on main)")

        for g, paths in sorted(groups.items()):
            git(repo, "add", "-A", "--", *paths)
            msg = f"sweep: {g} backlog {today}\n\nAutomated-by: tools/repo-sweep.py"
            c = git(repo, "commit", "-q", "-m", msg)
            lines.append(f"  commit {g}: {'ok' if c.returncode == 0 else c.stderr.strip()[:100]}")

        if policy == "pr" and sweep_branch != original_branch:
            supersede_old_sweeps(repo, sweep_branch, lines)

        push = git(repo, "push", "-u", "origin", sweep_branch)
        lines.append(f"  push {sweep_branch}: "
                     f"{'ok' if push.returncode == 0 else push.stderr.strip()[:140]}")
        if push.returncode != 0:
            return

        if policy == "pr":
            existing = run(["gh", "pr", "list", "--head", sweep_branch,
                            "--json", "number", "--jq", ".[0].number"],
                           cwd=repo).stdout.strip()
            if not existing:
                pr = run(["gh", "pr", "create", "--fill-first",
                          "--title", f"sweep: uncommitted backlog {today}",
                          "--body", "Automated nightly sweep by tools/repo-sweep.py. "
                                    "Quiesce-gated; credential-shaped and >50MB files "
                                    "excluded; conflicts self-heal via merge=union.\n\n"
                                    "\U0001F916 Generated with [Claude Code]"
                                    "(https://claude.com/claude-code)"],
                         cwd=repo)
                lines.append(f"  PR: {'created' if pr.returncode == 0 else pr.stderr.strip()[:140]}")
            merged = wait_for_ci_and_merge(repo, sweep_branch, lines)
    finally:
        current = git(repo, "branch", "--show-current").stdout.strip()
        if current != original_branch:
            git(repo, "checkout", original_branch)
            pull = git(repo, "pull", "--ff-only")
            lines.append(f"  returned to {original_branch}"
                         f"{'' if pull.returncode == 0 else ' (pull --ff-only failed)'}")
        if merged and sweep_branch != original_branch:
            git(repo, "branch", "-D", sweep_branch)
        log(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--execute", action="store_true", help="act (default: dry-run)")
    ap.add_argument("--quiesce-minutes", type=int, default=120)
    ap.add_argument("--repo", help="sweep only the repo whose folder name matches")
    ap.add_argument("--normalize-sessions", nargs="+", metavar="FILE",
                    help="repair union-merge frontmatter artifacts in session "
                         "files, then exit")
    args = ap.parse_args()

    if args.normalize_sessions:
        for f in args.normalize_sessions:
            text = open(f, encoding="utf-8").read()
            fixed = normalize_session_frontmatter(text)
            if fixed != text:
                open(f, "w", encoding="utf-8", newline="\n").write(fixed)
                print(f"{f}: normalized")
            else:
                print(f"{f}: unchanged")
        return 0

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
