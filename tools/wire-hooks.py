# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Idempotently wire the canonical enforcement hooks into .claude/settings.local.json.

WHY THIS EXISTS
---------------
The entire .claude/hooks enforcement layer was silently dead on this machine
from 2026-05-18 ~15:41 until 2026-05-19 (friction register, 2026-05-19 system,
infrastructure-deferred). Root cause: hook wiring was committed to TRACKED
settings.json with machine-specific absolute paths; a "sync before switching
devices" commit stripped it; the gitignored settings.local.json on this device
never carried a hooks block. Every "structural" fix that was operationalized as
a hook was inert, while rules kept promising those backstops were running.

F1 re-wired this machine by hand. But settings.local.json is gitignored
(.gitignore:85), so the fix did NOT travel: any OTHER device, or this device
after a settings reset, still boots with ZERO enforcement and no signal that
anything is wrong. This script is the cross-device recurrence kill: it is
TRACKED, it carries the canonical enforcement-hook block as the single source of truth,
and it writes that block into the local (gitignored) settings file on demand
or automatically at session start (--ensure), preserving every other key
(permissions, enabledPlugins, ...) untouched.

MODES
-----
  (default) / --write : write/repair the hooks block. Idempotent. Exit 0.
  --check             : assert only, no mutation. LOUD warning + exit 1 if the
                        block is missing or drifted; exit 0 if intact. Use for
                        a warn-only guard.
  --ensure            : check; if missing/drifted, repair in place; always
                        exit 0. This is the SessionStart self-heal mode -- it
                        makes silent enforcement death impossible to sustain
                        for more than one session on any device.

The canonical block below is authoritative. If a hook is added/removed/rewired,
update CANONICAL_HOOKS here in the same change -- this file is the contract.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_LOCAL = REPO_ROOT / ".claude" / "settings.local.json"

# Absolute, forward-slash repo root baked into every wired hook command. WHY:
# the per-tool-call hooks fire MID-session, when a stray `cd` may have drifted
# the shell cwd. A cwd-relative command (`uv run python .claude/hooks/X.py`)
# then resolves the script against the wrong directory and the hook silently
# fails to load -- which silently unloaded the ENTIRE enforcement layer 8+
# times (friction register 2026-05-18..2026-06-03: #14/#16/#24/#108/#115/
# #124/#162/#168/#170). `uv run --directory <REPO> python .claude/hooks/X.py`
# makes BOTH uv AND the hook subprocess run with cwd = repo root regardless of
# the caller's shell cwd, so drift can no longer brick the layer; it also fixes
# the hooks' own cwd-relative reads (e.g. hook-log.txt). The absolute path is
# safe here ONLY because it lands in the gitignored, per-device-regenerated
# settings.local.json -- it is computed fresh from this device's REPO_ROOT on
# every `--ensure`, so it never travels to another device (that was the
# 2026-05-19 root-cause sin, and it lived in a TRACKED settings.json).
_RD = REPO_ROOT.as_posix()


def _cmd(rel_script: str, extra: str = "") -> str:
    """Build a cwd-independent wired hook command for `rel_script` (a path
    relative to the repo root). `uv run --directory <REPO>` pins the working
    directory so shell-cwd drift can never unload the enforcement layer."""
    suffix = f" {extra}" if extra else ""
    return f'uv run --directory "{_RD}" python {rel_script}{suffix}'


# Single source of truth for the enforcement wiring. Built from `_cmd` so the
# cwd-pinning is uniform and a new hook can't accidentally be wired with a
# bare relative path. This is the shape F1 wired by hand, hardened against
# cwd drift; embedding it here is what makes the fix travel across devices.
CANONICAL_HOOKS = {
    "UserPromptSubmit": [
        {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/input-classifier.py"),
                    "timeout": 10000,
                }
            ],
        }
    ],
    "PreToolUse": [
        {
            "matcher": "Write|Edit",
            "hooks": [
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/auto-approve-protected.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/reference-anchor-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/file-placement-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/branch-isolation-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/scorer-lock-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/optimize-run-gate.py"),
                    "timeout": 10000,
                },
            ],
        },
        {
            "matcher": "Bash|PowerShell",
            "hooks": [
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/instantly-invasive-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/no-auto-commit-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/ruff-push-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/cd-guard.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/vercel-scope-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/optimize-run-gate.py"),
                    "timeout": 10000,
                },
            ],
        },
    ],
    "PostToolUse": [
        {
            "matcher": "Write|Edit",
            "hooks": [
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/em-dash-strip-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/post-write-gate.py"),
                    "timeout": 10000,
                },
            ],
        },
        {
            "matcher": "Bash|PowerShell",
            "hooks": [
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/post-action-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/gate-skip-detector.py"),
                    "timeout": 10000,
                },
            ],
        },
        {
            # All-tools meter: counts tool calls + distinct files and emits a
            # band-crossing pressure advisory once per band. Self-manages the
            # session boundary via the payload session_id (no SessionStart
            # reset hook needed). See rule_session-pressure.md.
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/session-pressure-meter.py"),
                    "timeout": 10000,
                }
            ],
        },
    ],
    "Stop": [
        {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": _cmd(".claude/hooks/stop-b1-gate.py"),
                    "timeout": 10000,
                }
            ],
        }
    ],
    "SessionStart": [
        {
            "matcher": "",
            "hooks": [
                {
                    # Warn when a live sibling session shares THIS working tree
                    # (shared HEAD/index/stash -> concurrent-commit collisions).
                    # Silent unless a sibling is detected. A .claude/hooks gate
                    # (unlike the two tools/ scripts below), so it IS part of
                    # EXPECTED_HOOK_SCRIPTS. See rule/memory
                    # feedback_worktree_for_concurrent_sessions.
                    "type": "command",
                    "command": _cmd(".claude/hooks/sibling-session-gate.py"),
                    "timeout": 10000,
                },
                {
                    "type": "command",
                    "command": _cmd("tools/friction-watch.py", "--once-per-day --quiet"),
                    "timeout": 10000,
                },
                {
                    # Auto-surface stale/malformed per-project status files so
                    # currency does not depend on remembering to run --check.
                    # Fail-open, exit 0 always; advises at most once per day.
                    # tools/ script (not a .claude/hooks gate), like friction-watch
                    # -- not part of EXPECTED_HOOK_SCRIPTS. See rule_project_status.md.
                    "type": "command",
                    "command": _cmd("tools/project_status.py", "--sweep-stale --once-per-day"),
                    "timeout": 10000,
                },
                {
                    # Surface optimize runs that need a decision (ACTIVE,
                    # INTERRUPTED, closed without SUMMARY) instead of relying
                    # on someone remembering to run the fleet view. Silent
                    # when the fleet is clean; fail-open, exit 0 always;
                    # advises at most once per day. tools/ script (not a
                    # .claude/hooks gate), like project_status above -- not
                    # part of EXPECTED_HOOK_SCRIPTS. See rule_optimize_loop.md.
                    "type": "command",
                    "command": _cmd("tools/optimize_overview.py", "--sweep --once-per-day"),
                    "timeout": 10000,
                },
            ],
        }
    ],
}

# Count of distinct hook scripts the layer must run (for the loud assertion).
EXPECTED_HOOK_SCRIPTS = {
    "input-classifier.py",
    "auto-approve-protected.py",
    "reference-anchor-gate.py",
    "file-placement-gate.py",
    "branch-isolation-gate.py",
    "instantly-invasive-gate.py",
    "no-auto-commit-gate.py",
    "ruff-push-gate.py",
    "cd-guard.py",
    "vercel-scope-gate.py",
    "em-dash-strip-gate.py",
    "post-write-gate.py",
    "post-action-gate.py",
    "gate-skip-detector.py",
    "session-pressure-meter.py",
    "stop-b1-gate.py",
    "sibling-session-gate.py",
    "scorer-lock-gate.py",
    "optimize-run-gate.py",
}

# Canonical hook count, derived so the assertion strings can never drift out
# of sync with the set above (the old hardcoded "11"/"10" literals had already
# diverged). Add a hook to CANONICAL_HOOKS + EXPECTED_HOOK_SCRIPTS and this
# updates itself.
HOOK_COUNT = len(EXPECTED_HOOK_SCRIPTS)


def _scripts_in(hooks_block: dict) -> set[str]:
    """Extract the set of hook script basenames referenced in a hooks block."""
    found: set[str] = set()
    if not isinstance(hooks_block, dict):
        return found
    for entries in hooks_block.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            for h in (entry or {}).get("hooks", []) or []:
                cmd = h.get("command", "") if isinstance(h, dict) else ""
                for script in EXPECTED_HOOK_SCRIPTS:
                    if script in cmd:
                        found.add(script)
    return found


def _load_settings() -> dict:
    if not SETTINGS_LOCAL.exists():
        return {}
    try:
        return json.loads(SETTINGS_LOCAL.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _intact(settings: dict) -> tuple[bool, set[str]]:
    """Return (is_intact, missing_scripts). Intact == the wired hooks block is
    byte-equivalent to canonical AND every expected script is referenced."""
    present = settings.get("hooks")
    missing = EXPECTED_HOOK_SCRIPTS - _scripts_in(present or {})
    canonical_match = present == CANONICAL_HOOKS
    return (canonical_match and not missing), missing


def _write(settings: dict) -> None:
    """Replace ONLY the hooks key; preserve permissions, enabledPlugins, etc.
    Create a minimal skeleton if the file is absent or unparseable."""
    settings = dict(settings) if settings else {}
    settings["hooks"] = CANONICAL_HOOKS
    SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_LOCAL.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _loud(msg: str) -> None:
    bar = "!" * 72
    sys.stderr.write(f"\n{bar}\n{msg}\n{bar}\n")


def main(argv: list[str]) -> int:
    mode = "write"
    if "--check" in argv:
        mode = "check"
    elif "--ensure" in argv:
        mode = "ensure"
    elif "--write" in argv or len(argv) == 0:
        mode = "write"

    settings = _load_settings()
    intact, missing = _intact(settings)

    if mode == "check":
        if intact:
            print(f"[wire-hooks] OK: all {HOOK_COUNT} enforcement hooks wired in "
                  ".claude/settings.local.json")
            return 0
        _loud(
            "[wire-hooks] ENFORCEMENT LAYER DOWN\n"
            f"  .claude/settings.local.json hooks block is missing or drifted.\n"
            f"  Missing scripts: {sorted(missing) or '(block absent / not canonical)'}\n"
            "  Every structural gate (B1 stop, em-dash strip, B4/B5, ship-gate,\n"
            "  gate-skip, input-classifier) is INERT until repaired.\n"
            "  Repair:  uv run python tools/wire-hooks.py --write"
        )
        return 1

    if mode == "ensure":
        if intact:
            print(f"[wire-hooks] OK: enforcement layer intact ({HOOK_COUNT}/{HOOK_COUNT} hooks).")
            return 0
        _write(settings)
        _loud(
            "[wire-hooks] ENFORCEMENT LAYER WAS DOWN -- AUTO-REPAIRED\n"
            f"  Rewrote the {HOOK_COUNT}-hook block into .claude/settings.local.json.\n"
            f"  (was missing: {sorted(missing) or 'block absent / drifted'})\n"
            "  Hooks take effect from the NEXT tool call this session.\n"
            "  Root cause if recurring: a device sync or settings reset.\n"
            "  This file (tracked) is the cross-device recurrence kill."
        )
        return 0

    # write / default
    if intact:
        print(f"[wire-hooks] No change: all {HOOK_COUNT} hooks already wired correctly.")
        return 0
    _write(settings)
    print(f"[wire-hooks] Wrote canonical {HOOK_COUNT}-hook block into "
          ".claude/settings.local.json "
          f"(was missing: {sorted(missing) or 'block absent / drifted'}). "
          "Other keys (permissions, enabledPlugins) preserved.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # never hard-fail a session-start hook
        sys.stderr.write(f"[wire-hooks] non-fatal error: {exc}\n")
        sys.exit(0)
