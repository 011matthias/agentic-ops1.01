#!/usr/bin/env python3
"""PreToolUse(Bash): B6 backstop -- block ship-class commands without explicit user order.

Enforces rule_no_auto_commit.md (B6). The memory-only fix (feedback_no_auto_commit)
demonstrably failed within hours of being written (PR #57/#58/#60 incidents on
2026-05-26). The rule itself flagged a PreToolUse:Bash hook as the natural Layer 1
evolution and logged it as `infrastructure-deferred`. This is that hook.

WHAT IT DOES
------------
1. Detects ship-class shell commands (git commit, git push, gh pr create/merge,
   git tag, gh release, deploy commands, subtree push).
2. Allows the prototype carve-out (100% local-web scope) silently.
3. Classifies the BAND from the command + the live current branch:
   - Autonomous: commit on a non-main feature branch, push of a feature
     branch with no main refspec and no --force, and gh pr create. Reversible
     / unmerged / the reviewable checkpoint -> allow silently. (The rule
     requires the agent to have verified behavior first; the hook enforces
     only the deterministic scope split.)
   - Auto-merge (CI-gated): gh pr merge -> allow silently WHEN `gh pr checks`
     reports the target PR green; otherwise fall through to the floor scan.
     This is the only band that keys autonomy on an objective external signal.
   - Gated floor: push-to-main, force push, commit-on-main, deploys, tags,
     releases, subtree push, gh pr close, plus any non-green merge. The
     irreversible / outward-facing steps.
4. For the gated floor, scans recent user messages for an explicit ship order.
   If found (push / force / deploy / merge / land / etc.), allow and log the
   matched authorization. If NOT found, return permissionDecision="ask" with a
   plain-language scope-of-effects reason. The user can authorize via the
   prompt; the agent cannot bypass.

NON-GOALS
---------
- This is NOT a hard deny. The user can always proceed via the permission
  prompt. The structural fix is "no SILENT ship"; explicit user approval at
  the prompt is the same as explicit user order in the conversation.
- This does NOT replace rule_no_auto_commit.md as the source of truth. The
  rule is the contract; the hook is the backstop.

DEFENSIVE CONTRACT
------------------
Any error, missing transcript, or unparseable payload -> exit 0, allow the
command. A broken classifier must never block; a missed ship-class command
is cheaper than a fully blocked git workflow.

WHY ASK INSTEAD OF DENY
-----------------------
Mirror instantly-invasive-gate.py. "ask" surfaces the action to the user, who
makes the final call. "deny" would block the user too -- they'd need to disable
the hook to ship anything. "ask" is the correct primitive for "this is
high-blast-radius, the human must consent."
"""
import datetime
import json
import os
import re
import subprocess
import sys

# Optional shared session-state store (tools/, repo-root-relative). Used ONLY
# to persist a friction candidate when this gate fires "ask" -- a pure
# side-effect that never alters the gate's decision. If the import fails the
# gate behaves exactly as before.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
)
try:
    import session_state  # noqa: E402
except Exception:
    session_state = None

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

# Ship-class shell command patterns. Matched against the FULL command string
# (after stripping common wrappers). Order matters only for log clarity.
SHIP_CLASS_PATTERNS = [
    (r"\bgit\s+commit\b(?!.*\bget\b)", "git-commit"),  # exclude `git log ... commit` reads
    (r"\bgit\s+push\b", "git-push"),
    (r"\bgh\s+pr\s+create\b", "gh-pr-create"),
    (r"\bgh\s+pr\s+merge\b", "gh-pr-merge"),
    (r"\bgh\s+pr\s+close\b", "gh-pr-close"),
    (r"\bgh\s+release\s+create\b", "gh-release-create"),
    (r"\bgit\s+tag\b(?!.*\s-l\b|\s--list\b)", "git-tag"),  # exclude `git tag -l` reads
    (r"\bgit\s+subtree\s+push\b", "git-subtree-push"),
    (r"\bflyctl\s+deploy\b", "flyctl-deploy"),
    (r"\bvercel\s+deploy\b", "vercel-deploy"),
    (r"\bvercel-force-deploy\.sh\b", "vercel-force-deploy"),
    (r"\brailway\s+up\b", "railway-up"),
]
SHIP_COMPILED = [(re.compile(p, re.IGNORECASE), tag) for p, tag in SHIP_CLASS_PATTERNS]

# Explicit ship-order tokens in user messages. Matched word-boundary,
# case-insensitive. The rule_no_auto_commit.md "Acceptable orders" set is
# the canonical list; this regex enumerates the same shapes.
AUTHORIZATION_PATTERNS = [
    r"\bcommit\s+(?:this|that|it|the|all|now)?\b",
    r"\bcommit\b",
    r"\bpush\s+(?:this|that|it|now|to|the)?\b",
    r"\bpush\b",
    r"\bship\s+it\b",
    r"\bship\s+(?:this|that|the|to|now)\b",
    r"\bship\b",
    r"\bpr\s+it\b",
    r"\bopen\s+(?:a\s+|the\s+)?pr\b",
    r"\bcreate\s+(?:a\s+|the\s+)?pr\b",
    r"\bmerge\s+(?:it|that|this|the|now)?\b",
    r"\bmerge\b",
    r"\bland\s+it\b",
    r"\bland\s+(?:this|that|the)\b",
    r"\btag\s+(?:it|the\s+release|v\d)",
    r"\brelease\b",
    r"\bdeploy\s+(?:it|now|this|that|to)?\b",
    r"\bdeploy\b",
    # Session-scoped pre-authorization shapes
    r"\bship\s+everything\b",
    r"\bauto[-\s]?(?:commit|ship|push|merge|deploy)\b",
    r"\byou\s+(?:can|may)\s+(?:commit|push|merge|ship|deploy)",
    r"\bgo\s+ahead\s+and\s+(?:commit|push|merge|ship|deploy)",
]
AUTH_COMPILED = [re.compile(p, re.IGNORECASE) for p in AUTHORIZATION_PATTERNS]

# How many most-recent user turns to scan for authorization. The rule says
# "current turn or session pre-authorization", so the immediately-prior user
# message is the highest-signal source. 30 turns covers session-scoped pre-
# authorizations ("ship everything to PR today") given at session start so
# they remain in force across the whole session, not just the next 3 turns.
USER_TURN_LOOKBACK = 30

# Prototype-prefix carve-out (path-scoped exemption to B6).
# When a ship-class command's scope is 100% within this prefix, the hook
# allows it without an explicit user authorization phrase. Reason: this is
# prototype/demo iteration (preemptive local-business demo sites), not
# production client work, and the per-iteration commit gate was creating
# friction without protecting against anything (the B6 incident on
# 2026-05-26 was on system/skill files, not prototype sites).
# rule_no_auto_commit.md "Prototype carve-out" section is the source of
# truth; this constant is the structural backstop.
PROTOTYPE_PATH_PREFIXES = (
    "workspace/projects/local-web/",
    # Backslash variant for Windows-quoted paths in commands
    "workspace\\projects\\local-web\\",
)

# Trunk branch names. Commit / push touching these is Tier 2 (gated).
MAIN_BRANCHES = ("main", "master")


def log(action: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} no-auto-commit-gate {action}\n")
    except Exception:
        pass


def detect_ship_class(cmd: str) -> str | None:
    """Return the tag of the matching ship-class pattern, or None."""
    for rx, tag in SHIP_COMPILED:
        if rx.search(cmd):
            return tag
    return None


def _has_prototype_prefix(path: str) -> bool:
    p = path.lstrip("./").replace("\\", "/")
    return p.startswith("workspace/projects/local-web/")


def is_prototype_scoped(cmd: str, tag: str) -> bool:
    """Return True if the ship-class command's scope is 100% within the
    prototype carve-out path. The carve-out is intentionally narrow: a
    repo-root `git commit` with even one non-prototype file in the staged
    set returns False and the gate fires normally."""
    # Explicit path in the command string is the cheapest signal.
    if any(prefix in cmd for prefix in PROTOTYPE_PATH_PREFIXES):
        # Conservative: only trust explicit-path signal for deploy/subtree
        # commands where the path arg literally scopes the action.
        if tag in ("flyctl-deploy", "git-subtree-push"):
            return True
    # For git commit: inspect staged files. 100% prototype-prefixed -> True.
    if tag == "git-commit":
        try:
            out = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True, text=True, timeout=5,
            )
            files = [f for f in out.stdout.strip().splitlines() if f.strip()]
            if files and all(_has_prototype_prefix(f) for f in files):
                return True
        except Exception:
            return False
    # For git push: examine commits about to be pushed against upstream.
    # If every commit in the push range touches only prototype files, allow.
    if tag == "git-push":
        try:
            # Range: upstream..HEAD (commits being pushed)
            upstream = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "@{u}"],
                capture_output=True, text=True, timeout=5,
            )
            up = upstream.stdout.strip()
            if not up or upstream.returncode != 0:
                # No upstream yet -> compare against origin/HEAD as fallback
                up = "origin/HEAD"
            out = subprocess.run(
                ["git", "diff", "--name-only", f"{up}...HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            files = [f for f in out.stdout.strip().splitlines() if f.strip()]
            if files and all(_has_prototype_prefix(f) for f in files):
                return True
        except Exception:
            return False
    # For gh pr create / merge: same logic as push (branch diff).
    if tag in ("gh-pr-create", "gh-pr-merge"):
        try:
            # Default base = main. The local-web work convention uses
            # feature branches off main, so this is the correct compare.
            out = subprocess.run(
                ["git", "diff", "--name-only", "main...HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            files = [f for f in out.stdout.strip().splitlines() if f.strip()]
            if files and all(_has_prototype_prefix(f) for f in files):
                return True
        except Exception:
            return False
    return False


def current_branch() -> str | None:
    """Return the live current git branch, or None if undeterminable.

    Test seam: NO_AUTO_COMMIT_GATE_BRANCH, when set, forces the returned
    value so the tier classifier can be smoke-tested deterministically
    without checking out branches. Never set in production.
    """
    forced = os.environ.get("NO_AUTO_COMMIT_GATE_BRANCH")
    if forced:
        return forced.strip()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def is_autonomous_lane(cmd: str, tag: str) -> bool:
    """Tier 1 classifier: True if the ship-class command is reversible /
    unmerged feature-branch work that runs without an explicit order.

    Conservative by construction: any uncertainty (unknown branch, main
    refspec, force flag, non-commit/push/PR-open tag) returns False so the
    command falls through to the Tier 2 explicit-order gate. The hook only
    decides SCOPE; the rule requires the agent to have verified behavior
    before relying on this lane.
    """
    # Opening a PR lands nothing on the base branch; it's the reviewable
    # checkpoint. Always Tier 1 regardless of branch.
    if tag == "gh-pr-create":
        return True
    # Only commit / push can be Tier 1. merge, close, deploy, tag, release,
    # subtree push are always Tier 2.
    if tag not in ("git-commit", "git-push"):
        return False
    branch = current_branch()
    if branch is None or branch in MAIN_BRANCHES:
        # On trunk, or branch undeterminable -> gate.
        return False
    if tag == "git-commit":
        # Commit on a feature branch is reversible and unmerged.
        return True
    if tag == "git-push":
        # Force push rewrites remote history irreversibly -> gate.
        if re.search(r"(?:^|\s)(?:--force\b|-f\b|--force-with-lease\b|\+)", cmd):
            return False
        # Explicit main/master refspec means the push targets trunk -> gate.
        if re.search(r"\b(?:main|master)\b", cmd):
            return False
        # Feature-branch push to its own remote.
        return True
    return False


def _merge_pr_selector(cmd: str) -> str:
    """Extract the PR selector (number / url / branch) from a `gh pr merge`
    command. Returns "" when none is given (gh defaults to the current
    branch's PR)."""
    m = re.search(r"\bgh\s+pr\s+merge\b(.*)", cmd, re.IGNORECASE)
    if not m:
        return ""
    for tok in m.group(1).split():
        if tok.startswith("-"):
            continue
        return tok
    return ""


def ci_is_green(cmd: str) -> bool | None:
    """Decide the auto-merge gate from the target PR's CI status.

    True  -> all checks green (auto-merge sanctioned).
    False -> a check is failing or pending (do not auto-merge).
    None  -> undeterminable (gh missing/unauthed/no repo/timeout).

    Auto-merge is the one place autonomy keys on an OBJECTIVE external
    signal rather than the agent's judgment: the merge fires only when the
    user's own CI is green. `gh pr checks` exit codes: 0 = all pass,
    8 = pending, 1 = failure. Test seam: NO_AUTO_COMMIT_GATE_CI in
    {green, red, pending} forces the verdict for deterministic smoke tests
    (never set in production).
    """
    forced = os.environ.get("NO_AUTO_COMMIT_GATE_CI")
    if forced:
        return forced.strip().lower() == "green"
    selector = _merge_pr_selector(cmd)
    args = ["gh", "pr", "checks"]
    if selector:
        args.append(selector)
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=20)
    except Exception:
        return None
    if out.returncode == 0:
        return True
    if out.returncode in (1, 8):
        return False
    return None  # 2/4/other -> error resolving the PR; fail safe to ASK


def recent_user_messages(transcript_path: str, lookback: int = USER_TURN_LOOKBACK) -> list[str]:
    """Return text of the most-recent N user messages, newest-first.

    Transcript is JSONL; each line an event. User turns have
    type=='user' with message.content a string or a list of blocks.
    Robust to schema drift: any failure -> [].
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return []
    user_msgs: list[str] = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                msg = obj.get("message") if isinstance(obj, dict) else None
                role = obj.get("type") or (msg or {}).get("role")
                if role != "user" or not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    user_msgs.append(content)
                elif isinstance(content, list):
                    parts = []
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "text":
                            parts.append(b.get("text", ""))
                        elif isinstance(b, dict) and b.get("type") == "tool_result":
                            # Tool result content is not user authorization
                            continue
                    if parts:
                        user_msgs.append("\n".join(parts))
    except Exception:
        return []
    # Most recent N, newest-first
    return list(reversed(user_msgs))[:lookback]


def has_authorization(user_msgs: list[str]) -> str | None:
    """Return the matched authorization snippet, or None."""
    for msg in user_msgs:
        # Skip system-reminder content and hook-feedback content -- those
        # aren't real user authorization, they're harness/automation text.
        scan = re.sub(r"<system-reminder>.*?</system-reminder>", " ", msg, flags=re.DOTALL)
        scan = re.sub(r"^Stop hook feedback:.*$", " ", scan, flags=re.MULTILINE)
        for rx in AUTH_COMPILED:
            m = rx.search(scan)
            if m:
                start = max(0, m.start() - 20)
                snippet = scan[start:m.end() + 30].strip().replace("\n", " ")
                return snippet[:120]
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not cmd:
        sys.exit(0)

    ship_tag = detect_ship_class(cmd)
    if not ship_tag:
        # Not a ship-class command -> let it run silently.
        sys.exit(0)

    # Prototype carve-out: ship-class commands scoped to local-web demo
    # sites bypass the gate. Production / client / system work still needs
    # explicit authorization. See rule_no_auto_commit.md "Prototype carve-out".
    if is_prototype_scoped(cmd, ship_tag):
        log(f"allow:{ship_tag} scope=prototype (local-web)")
        sys.exit(0)

    # Autonomous lane: reversible / unmerged feature-branch work (commit,
    # non-main non-force push, gh pr create). Runs without an explicit order.
    # See rule_no_auto_commit.md "Autonomous lane".
    if is_autonomous_lane(cmd, ship_tag):
        log(f"allow:{ship_tag} band=autonomous (feature-branch, no order needed)")
        sys.exit(0)

    # Auto-merge band: gh pr merge fires automatically WHEN the target PR's CI
    # is green (objective signal, not agent judgment). Red / pending / unknown
    # falls through to the explicit-order scan below, which preserves a manual
    # override ("merge anyway") and otherwise ASKs.
    if ship_tag == "gh-pr-merge":
        verdict = ci_is_green(cmd)
        if verdict is True:
            log(f"allow:{ship_tag} band=auto-merge ci=green")
            sys.exit(0)
        log(f"fallthrough:{ship_tag} ci={'red/pending' if verdict is False else 'unknown'}")

    # Gated floor (push-to-main, force push, commit-on-main, deploy, tag,
    # release, subtree push, pr-close) + non-green merge: explicit order
    # required. Scan recent user turns for authorization.
    transcript_path = payload.get("transcript_path", "")
    user_msgs = recent_user_messages(transcript_path)
    auth_snippet = has_authorization(user_msgs)

    if auth_snippet:
        log(f"allow:{ship_tag} auth={auth_snippet!r}")
        sys.exit(0)

    # No authorization found -> ask. The user can authorize via the prompt.
    log(f"ASK:{ship_tag} (no user authorization in last {USER_TURN_LOOKBACK} user turns)")
    # Side-effect only: persist a friction candidate. A gate firing here is
    # often the system working (agent paused for an order); the checkpoint
    # drain decides promote-vs-discard. Must never affect the decision below.
    if session_state is not None:
        try:
            session_state.add_candidate(
                "gate-fired-no-auto-commit", "no-auto-commit-gate",
                f"{ship_tag}: {cmd[:240]}",
            )
        except Exception:
            pass
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"GATED-FLOOR SHIP-CLASS COMMAND detected ({ship_tag}). Per "
                "rule_no_auto_commit.md (B6): irreversible / outward-facing actions "
                "(direct push-to-main, force push, commit-on-main, deploy, tag, "
                "release, subtree push to client repos) need an explicit user order "
                "in the current turn (\"push\", \"force push\", \"deploy\", \"land "
                "it\") OR a named session pre-authorization. A `gh pr merge` reaches "
                "this prompt only when its CI is NOT green (red / pending / "
                "undeterminable); auto-merge fires on its own when CI is green. "
                f"Scanned the last {USER_TURN_LOOKBACK} user turns; found no "
                "authorization. (Feature-branch commit / push / PR-open run "
                "autonomously and never reach this prompt.) If the user did "
                "authorize and the scan missed it, approve here. Otherwise, cancel "
                "and ask the user for an explicit ship order before retrying."
            ),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
