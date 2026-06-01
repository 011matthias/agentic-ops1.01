#!/usr/bin/env python3
"""PostToolUse(Write|Edit) dispatcher.

Consolidates three previously-separate PostToolUse(Write|Edit) hooks into
a single entry point that routes by file path:

  comms drafts / proposals / comms-log     -> tools/lint-comms-draft.py
  client-facing deliverables / hero-exports -> tools/validate-deliverable.py
  any of the above + workspace specs        -> tools/validate-output.py

Why one dispatcher instead of three hooks: ordering risk (which hook fires
first, what happens if one blocks but another doesn't) and duplicated
in-scope checks. With one dispatcher we run validators in parallel via
subprocess, collect all advisories, emit one consolidated additionalContext.

Non-blocking: emits additionalContext only, never exitCode=2.
"""
import datetime
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
TOOLS_DIR = REPO / "tools"
HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")


def log_fire(action: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} post-write-gate {action}\n")
    except Exception:
        pass


def normalize_path(file_path: str) -> str:
    if not file_path:
        return file_path
    if len(file_path) >= 3 and file_path[0] == "/" and file_path[2] == "/" and file_path[1].isalpha():
        file_path = f"{file_path[1].upper()}:{file_path[2:]}"
    return file_path


def normalize_for_match(file_path: str) -> str:
    return file_path.replace("\\", "/").lower()


def in_deliverable_scope(file_path: str) -> bool:
    if not file_path:
        return False
    p = normalize_for_match(file_path)
    if not p.endswith((".html", ".htm", ".md", ".markdown", ".mdx")):
        return False
    return any(m in p for m in (
        "/platform/public/",
        "/deliverables/",
        "/hero-exports/",
        "/notion-pages/",
        "/doc-site/",
    ))


def in_comms_scope(file_path: str) -> bool:
    if not file_path:
        return False
    p = normalize_for_match(file_path)
    if not p.endswith((".md", ".markdown", ".mdx")):
        return False
    if "/context/drafts/" in p or "/proposals/" in p:
        return True
    if p.endswith("/comms-log.md"):
        return True
    return False


def in_output_scope(file_path: str) -> bool:
    """Output validator runs whenever deliverable OR comms scope is active.

    Behavioral failures (verification-theater, over-literal) appear in both
    artifact types — same rule set applies.
    """
    return in_deliverable_scope(file_path) or in_comms_scope(file_path)


def in_pilot_routing_scope(file_path: str) -> bool:
    """Pilot-routing cross-wire validator scope: comms drafts in client trees.

    Only fires when the client has a `context/pilot-routing.md` table to
    validate against. The validator itself short-circuits if no routing
    table exists; this scope check is the broader gate (drafts only).
    """
    if not file_path:
        return False
    p = normalize_for_match(file_path)
    if not p.endswith((".md", ".markdown")):
        return False
    return "workspace/clients/" in p and "/context/drafts/" in p


def in_spec_scope(file_path: str) -> bool:
    """Spec frontmatter validator scope: any .md file written under a client's
    specs/ tree. Catches malformed-spec drift at write-time so it doesn't
    accumulate until someone runs /spec-cleanup."""
    if not file_path:
        return False
    p = normalize_for_match(file_path)
    if not p.endswith((".md", ".markdown")):
        return False
    return "/workspace/clients/" in p and "/specs/" in p


def run_tool(tool_name: str, args: list[str], timeout: int = 30) -> tuple[int, dict]:
    tool_path = TOOLS_DIR / tool_name
    if not tool_path.is_file():
        return -1, {}
    try:
        proc = subprocess.run(
            ["uv", "run", str(tool_path), *args, "--format", "json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(REPO),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        log_fire(f"ERROR:{tool_name}-{type(e).__name__}")
        return -1, {}
    if proc.returncode not in (0, 1):
        log_fire(f"ERROR:{tool_name}-exit-{proc.returncode}:{proc.stderr[:80].strip()}")
        return -1, {}
    try:
        payload = json.loads(proc.stdout or "{}") if proc.stdout else {}
    except json.JSONDecodeError:
        log_fire(f"ERROR:{tool_name}-json-decode")
        return -1, {}
    return proc.returncode, payload


def format_advisory(label: str, payload: dict, file_path: str) -> str | None:
    total = payload.get("total", 0)
    if total == 0:
        return None
    hits = payload.get("hits", [])
    by_cat = payload.get("by_category", {})
    by_sev = payload.get("by_severity", {}) or {}
    cat_summary = ", ".join(f"{c}={n}" for c, n in sorted(by_cat.items(), key=lambda kv: -kv[1]))
    sev_summary = " ".join(f"{k}={v}" for k, v in sorted(by_sev.items())) if by_sev else ""

    high_priority = [h for h in hits if h.get("severity") in ("HIGH", None)][:3]
    if not high_priority:
        high_priority = hits[:3]
    top_lines = []
    for h in high_priority:
        line = h.get("line", 0)
        cat = h.get("category", "?")
        sev = h.get("severity")
        sev_tag = f"[{sev}] " if sev else ""
        msg = h.get("message", "")
        top_lines.append(f"  L{line} {sev_tag}[{cat}] {msg}")
    top_block = "\n".join(top_lines) if top_lines else "  (no sample available)"

    parts = [f"[{label}] {total} hit(s) in {file_path} ({cat_summary})."]
    if sev_summary:
        parts[-1] += f" Severity: {sev_summary}."
    parts.append(f"Top:\n{top_block}")
    return "\n".join(parts)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        log_fire("ERROR:stdin")
        json.dump({}, sys.stdout)
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Write", "Edit"):
        log_fire(f"SKIP:not-write-edit-{tool_name}")
        json.dump({}, sys.stdout)
        sys.exit(0)

    file_path = normalize_path(tool_input.get("file_path", "") or "")
    if not file_path:
        log_fire("SKIP:no-path")
        json.dump({}, sys.stdout)
        sys.exit(0)

    # Plan which validators to run
    planned: list[tuple[str, str, list[str], int]] = []  # (label, tool, args, timeout)
    if in_deliverable_scope(file_path):
        planned.append(("DELIVERABLE GATE", "validate-deliverable.py", [file_path], 25))
    if in_comms_scope(file_path):
        planned.append(("COMMS GATE", "lint-comms-draft.py",
                        [file_path, "--skip-em-dash"], 30))
    if in_output_scope(file_path):
        planned.append(("OUTPUT GATE", "validate-output.py", [file_path], 15))
    if in_spec_scope(file_path):
        planned.append(("SPEC GATE", "validate-spec.py", [file_path], 10))
    if in_pilot_routing_scope(file_path):
        planned.append(("PILOT ROUTING GATE", "validate-pilot-routing.py",
                        [file_path], 10))

    if not planned:
        log_fire("SKIP:out-of-scope")
        json.dump({}, sys.stdout)
        sys.exit(0)

    # Run in parallel; the validators are independent
    advisories: list[str] = []
    with ThreadPoolExecutor(max_workers=len(planned)) as ex:
        futures = {ex.submit(run_tool, tool, args, timeout): (label, tool)
                   for (label, tool, args, timeout) in planned}
        for fut in as_completed(futures):
            label, tool = futures[fut]
            try:
                exit_code, payload = fut.result()
            except Exception as e:  # noqa: BLE001 - keep dispatcher robust
                log_fire(f"ERROR:{tool}-runtime-{type(e).__name__}")
                continue
            if exit_code < 0 or not payload:
                continue
            adv = format_advisory(label, payload, file_path)
            if adv:
                advisories.append(adv)

    if not advisories:
        log_fire(f"PASS:{len(planned)}-tools")
        json.dump({}, sys.stdout)
        sys.exit(0)

    combined = "\n\n".join(advisories)
    combined += (
        "\n\nDo NOT mark this artifact done while HIGH-severity hits remain. "
        "Suppress per-line with `<!-- output-allow:CATEGORY -->` (output validator) "
        "or `.deliverable-config.yaml` (deliverable validator) with a reason."
    )

    log_fire(f"FIRED:{len(advisories)}-advisories")
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": combined,
        }
    }
    json.dump(result, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()