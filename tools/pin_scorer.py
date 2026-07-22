# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Scorer pin registry tool (tools/scorers/PINS.json).

The optimize loop's metric integrity has two halves: the write-time lock
(scorer-lock-gate.py, optimize-run-gate.py) and this REGISTRY - a committed
name -> {sha, direction} map that binds each scorer to a user-reviewed
content hash. The run engine refuses to start or accept a round unless the
live scorer hash matches its pin, so a scorer rewritten through ANY bypass
vector (shell redirect, interpreter escape) can never produce an accepted
score, and the CI test (test_scorer_pins.py) blocks a drifted pin from
merging.

Hash definition: sha1 git-blob hash over CRLF->LF-normalized bytes. This
checkout runs core.autocrlf=true on Windows (CRLF on disk) while CI checks
out LF; normalizing makes the pin identical everywhere and equal to
`git hash-object` of the LF form. All consumers (this tool, the CI test,
optimize_run.py) import blob_sha() from here - one implementation.

Commands:
  uv run tools/pin_scorer.py pin <name.py> [--pr N]   (needs SCORER_LOCK_ALLOW=1)
  uv run tools/pin_scorer.py check                    (exit 1 on any drift)
  uv run tools/pin_scorer.py list

Re-pin protocol (rule_optimize_loop.md): user approves the metric change ->
edit the scorer under SCORER_LOCK_ALLOW=1 -> `pin` (also gated by the same
seam) -> PR. The PINS.json diff line makes the metric change impossible to
miss in review; reviewer sign-off is the honesty gate.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORERS_DIR = os.path.join(REPO, "tools", "scorers")
PINS_PATH = os.path.join(SCORERS_DIR, "PINS.json")

# Guards carry the whole anti-overfit floor (RECIPES rule 3) but live in
# top-level tools/, outside the always-on scorer lock and outside PINS.json,
# and cmd_start hashed them straight from the live tree. A guard weakened
# BETWEEN runs was therefore locked in at the next `start` with nothing to
# compare against. (During a run the file ACL plus per-round hash re-verify
# already cover it; this closes the between-runs window.)
#
# Separate registry file, on purpose: PINS.json is keyed by bare filename
# inside one directory and every consumer assumes that shape. Guards live
# anywhere under tools/, so they are keyed by repo-relative path.
GUARD_PINS_PATH = os.path.join(REPO, "tools", "guard-pins.json")

DIRECTION_RE = re.compile(r"^#\s*direction:\s*(minimize|maximize)\s*$", re.MULTILINE)


def blob_sha(path: str) -> str:
    """sha1 git-blob hash of the file's CRLF->LF-normalized bytes."""
    with open(path, "rb") as f:
        data = f.read().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def scorer_direction(path: str) -> str | None:
    """The scorer's declared `# direction: minimize|maximize` header, or None."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            m = DIRECTION_RE.search(f.read())
    except OSError:
        return None
    return m.group(1) if m else None


def load_pins() -> dict:
    if not os.path.isfile(PINS_PATH):
        return {}
    with open(PINS_PATH, encoding="utf-8") as f:
        return json.load(f)


def scorer_files() -> list[str]:
    return sorted(
        n for n in os.listdir(SCORERS_DIR)
        if n.endswith(".py") and os.path.isfile(os.path.join(SCORERS_DIR, n))
    )


def load_guard_pins() -> dict:
    if not os.path.isfile(GUARD_PINS_PATH):
        return {}
    with open(GUARD_PINS_PATH, encoding="utf-8") as f:
        return json.load(f)


def cmd_pin_guard(path: str, pr: int | None) -> int:
    """Pin a guard script to a reviewed content hash.

    Same SCORER_LOCK_ALLOW seam as scorer pinning: a guard defines the FLOOR
    an experiment must clear, so moving it is the same class of act as moving
    the metric. No `# direction:` requirement - guards are pass/fail, not
    scalar.
    """
    if not os.environ.get("SCORER_LOCK_ALLOW"):
        print(
            "REFUSED: pinning re-defines a locked guard (the anti-overfit "
            "floor). Set SCORER_LOCK_ALLOW=1 (user-approved maintenance seam) "
            "and re-run.",
            file=sys.stderr,
        )
        return 1
    rel = path.replace("\\", "/").lstrip("./")
    full = os.path.join(REPO, *rel.split("/"))
    if not os.path.isfile(full):
        print(f"REFUSED: {rel} not found.", file=sys.stderr)
        return 1
    if rel.startswith("tools/scorers/"):
        print(f"REFUSED: {rel} is a SCORER; pin it with `pin`, not "
              "`pin-guard`.", file=sys.stderr)
        return 1
    pins = load_guard_pins()
    entry = {"sha": blob_sha(full), "pinned": _dt.date.today().isoformat()}
    if pr is not None:
        entry["pr"] = pr
    elif isinstance(pins.get(rel), dict) and "pr" in pins[rel]:
        entry["pr"] = pins[rel]["pr"]
    pins[rel] = entry
    with open(GUARD_PINS_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pins, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"pinned guard {rel}: sha={entry['sha']}")
    return 0


def guard_failures() -> list[str]:
    """DRIFT / ORPHAN for pinned guards.

    Deliberately NOT "unpinned guard" as a failure: tools/ holds many
    validate-*.py that are guards only when a manifest names them, so
    demanding a pin for every candidate would be noise. Absence is surfaced
    by the run engine at lock-on (which knows the manifest) instead.
    """
    failures = []
    for rel, entry in sorted(load_guard_pins().items()):
        full = os.path.join(REPO, *rel.split("/"))
        if not os.path.isfile(full):
            failures.append(f"ORPHAN GUARD PIN: {rel} pinned but no such file")
            continue
        want, got = entry.get("sha"), blob_sha(full)
        if want != got:
            failures.append(f"GUARD DRIFT: {rel} pin={want} live={got}")
    return failures


def cmd_pin(name: str, pr: int | None) -> int:
    if not os.environ.get("SCORER_LOCK_ALLOW"):
        print(
            "REFUSED: pinning re-defines the locked metric. Set "
            "SCORER_LOCK_ALLOW=1 (user-approved maintenance seam) and re-run.",
            file=sys.stderr,
        )
        return 1
    path = os.path.join(SCORERS_DIR, name)
    if not os.path.isfile(path):
        print(f"REFUSED: {name} not found in tools/scorers/.", file=sys.stderr)
        return 1
    direction = scorer_direction(path)
    if direction is None:
        print(
            f"REFUSED: {name} lacks a `# direction: minimize|maximize` header "
            "(tools/scorers/README.md clause 5).",
            file=sys.stderr,
        )
        return 1
    pins = load_pins()
    entry = {
        "sha": blob_sha(path),
        "direction": direction,
        "pinned": _dt.date.today().isoformat(),
    }
    if pr is not None:
        entry["pr"] = pr
    elif isinstance(pins.get(name), dict) and "pr" in pins[name]:
        entry["pr"] = pins[name]["pr"]
    pins[name] = entry
    with open(PINS_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pins, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"pinned {name}: sha={entry['sha']} direction={direction}")
    return 0


def cmd_check() -> int:
    pins = load_pins()
    files = scorer_files()
    failures = []
    for name in files:
        path = os.path.join(SCORERS_DIR, name)
        if name not in pins:
            failures.append(f"UNPINNED: {name} has no PINS.json entry")
            continue
        want, got = pins[name].get("sha"), blob_sha(path)
        if want != got:
            failures.append(f"DRIFT: {name} pin={want} live={got}")
        direction = scorer_direction(path)
        if direction != pins[name].get("direction"):
            failures.append(
                f"DIRECTION MISMATCH: {name} header={direction} "
                f"pin={pins[name].get('direction')}"
            )
    for name in pins:
        if name not in files:
            failures.append(f"ORPHAN PIN: {name} pinned but no such scorer file")
    guards = guard_failures()
    failures.extend(guards)
    for line in failures:
        print(line)
    if not failures:
        print(f"OK: {len(files)} scorer(s) and {len(load_guard_pins())} "
              "guard(s), all pinned and matching.")
    return 1 if failures else 0


def cmd_list() -> int:
    pins = load_pins()
    for name, entry in sorted(pins.items()):
        print(f"{name}  {entry.get('sha','?')[:12]}  {entry.get('direction','?')}"
              f"  pinned {entry.get('pinned','?')}  pr={entry.get('pr','-')}")
    if not pins:
        print("(no pins)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_pin = sub.add_parser("pin")
    p_pin.add_argument("name")
    p_pin.add_argument("--pr", type=int, default=None)
    p_guard = sub.add_parser("pin-guard")
    p_guard.add_argument("path", help="repo-relative path, e.g. tools/x-guard.py")
    p_guard.add_argument("--pr", type=int, default=None)
    sub.add_parser("check")
    sub.add_parser("list")
    args = ap.parse_args()
    if args.cmd == "pin":
        return cmd_pin(args.name, args.pr)
    if args.cmd == "pin-guard":
        return cmd_pin_guard(args.path, args.pr)
    if args.cmd == "check":
        return cmd_check()
    return cmd_list()


if __name__ == "__main__":
    sys.exit(main())
