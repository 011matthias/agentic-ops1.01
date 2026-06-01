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
2. Scans recent user messages from the transcript for an explicit ship order
   in the current turn or recent context.
3. If an explicit order is found (commit / push / ship / merge / land / deploy /
   etc.), allow the command and log the matched authorization.
4. If NO explicit order is found, return permissionDecision="ask" with a
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

    # Ship-class detected. Scan recent user turns for explicit authorization.
    transcript_path = payload.get("transcript_path", "")
    user_msgs = recent_user_messages(transcript_path)
    auth_snippet = has_authorization(user_msgs)

    if auth_snippet:
        log(f"allow:{ship_tag} auth={auth_snippet!r}")
        sys.exit(0)

    # No authorization found -> ask. The user can authorize via the prompt.
    log(f"ASK:{ship_tag} (no user authorization in last {USER_TURN_LOOKBACK} user turns)")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"SHIP-CLASS COMMAND detected ({ship_tag}). Per rule_no_auto_commit.md "
                "(B6): commits, pushes, PRs, merges, tags, releases, and deploys may "
                "NOT run without an explicit user order in the current turn "
                "(\"commit\", \"push\", \"ship it\", \"PR it\", \"merge\", \"land it\", "
                "\"deploy\") OR a named session-scoped pre-authorization (\"ship "
                f"everything to PR today\"). Scanned the last {USER_TURN_LOOKBACK} user "
                "turns; found no authorization. If the user did authorize and the "
                "scan missed it, approve here. Otherwise, cancel and ask the user "
                "for an explicit ship order before retrying."
            ),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
