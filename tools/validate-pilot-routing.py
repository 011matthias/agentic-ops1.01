# /// script
# requires-python = ">=3.11"
# ///
"""Validate client-facing drafts against a client's pilot-routing.md table.

Catches piece-attribution cross-wiring (e.g., "Piece 1 (warm Christmas):
Mailboxes are reconnected" when the reconnected mailboxes belong to Piece 2).

The mistake this hook structurally prevents:
  - 2026-05-30: drafted reply to Gurmej attributed mejievent.com reauth to
    Piece 1 (warm Christmas). mejievent.com mailboxes belong to Piece 2
    (corporate cold). Memory failed; canonical pilot-routing.md without
    auto-load failed within the hour. Promoted here as a Layer 1 hook.

USAGE
-----
  uv run tools/validate-pilot-routing.py {file_path} [--format json]

  --format json (default in hook integration) emits the dispatcher-compatible
    contract: {"total", "hits", "by_category", "by_severity"}.
  Bare invocation emits a JSON list for ad-hoc CLI use.

CONTRACT
--------
  - If file_path is not inside `workspace/clients/{client}/`, no-op.
  - If no `pilot-routing.md` exists at `workspace/clients/{client}/context/`,
    no-op.
  - Otherwise, parse the routing table (the canonical markdown table at the
    top of pilot-routing.md) and validate the file content against it.

DEFENSIVE
---------
  Any parsing failure -> emit empty findings. A broken validator must never
  block; a missed cross-wiring is cheaper than a noisy false positive.
"""
import json
import re
import sys
from pathlib import Path


def find_pilot_routing(file_path: Path) -> Path | None:
    """Walk up from file_path looking for {client_root}/context/pilot-routing.md."""
    try:
        resolved = file_path.resolve()
    except Exception:
        return None
    for parent in resolved.parents:
        if parent.name == "context":
            candidate = parent / "pilot-routing.md"
            if candidate.exists():
                return candidate
        # also handle being deeper than context/ (e.g., context/drafts/foo.md)
        ctx = parent / "context" / "pilot-routing.md"
        if ctx.exists():
            return ctx
    return None


def parse_routing_table(routing_md: Path) -> dict[str, dict]:
    """Parse the routing table at the top of pilot-routing.md.

    Returns a dict keyed by piece number ("1", "2", "3") with:
      - label: short label
      - mailboxes: list of email addresses uniquely belonging to this piece
      - domains: list of domains uniquely belonging to this piece
      - campaign_ids: list of campaign IDs
    """
    try:
        text = routing_md.read_text(encoding="utf-8")
    except Exception:
        return {}

    routing: dict[str, dict] = {}

    # The canonical table has rows like:
    # | **Piece 1** | 983 past ... | `1f40cb36-...` | ... | `gurmej@mejimedia.co`, ... | ... |
    row_re = re.compile(
        r"\|\s*\*\*Piece\s*(?P<num>\d)\*\*\s*\|(?P<rest>.+?)\|\s*\n",
        re.IGNORECASE,
    )
    for m in row_re.finditer(text):
        num = m.group("num")
        rest = m.group("rest")
        cells = [c.strip() for c in rest.split("|")]
        emails = re.findall(r"`?([\w.+-]+@[\w.-]+\.\w+)`?", rest)
        ids = re.findall(r"`([a-f0-9]{8}-[a-f0-9-]{20,})`", rest)
        # domains from emails
        domains = sorted({e.split("@", 1)[1].lower() for e in emails})
        routing[num] = {
            "mailboxes": [e.lower() for e in emails],
            "domains": domains,
            "campaign_ids": ids,
            "cells": cells,
        }

    return routing


def find_piece_attributed_sections(content: str) -> list[tuple[str, str]]:
    """Split content into (piece_num, section_text) pairs.

    Looks for paragraphs that lead with "**Piece N**" or "Piece N (".
    Returns each piece-attributed chunk up to the next piece marker.
    """
    # Match either **Piece 1 (foo)** OR **Piece 1.** OR plain "Piece 1" leading a line
    marker_re = re.compile(
        r"(?:\*\*Piece\s*(\d)[^*\n]*\*\*|^Piece\s*(\d)\b)",
        re.MULTILINE | re.IGNORECASE,
    )
    matches = list(marker_re.finditer(content))
    sections: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        piece_num = m.group(1) or m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section = content[start:end]
        sections.append((piece_num, section))
    return sections


def line_of_match(content: str, needle: str) -> int:
    """Return 1-indexed line number of the first occurrence of needle in content, or 0."""
    idx = content.lower().find(needle.lower())
    if idx < 0:
        return 0
    return content[:idx].count("\n") + 1


def validate(file_path: Path) -> list[dict]:
    routing_md = find_pilot_routing(file_path)
    if not routing_md:
        return []
    routing = parse_routing_table(routing_md)
    if not routing:
        return []
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return []

    sections = find_piece_attributed_sections(content)
    if not sections:
        return []

    findings: list[dict] = []
    seen: set[tuple] = set()
    for piece_num, section in sections:
        section_lower = section.lower()
        for other_num, other_infra in routing.items():
            if other_num == piece_num:
                continue
            # Check mailboxes belonging exclusively to other piece
            for mb in other_infra.get("mailboxes", []):
                if mb in section_lower:
                    key = ("mailbox", piece_num, other_num, mb)
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append({
                        "severity": "HIGH",
                        "category": "piece-routing-cross-wire",
                        "line": line_of_match(content, mb),
                        "message": (
                            f"Piece {piece_num} section mentions `{mb}` which "
                            f"belongs to Piece {other_num} per pilot-routing.md. "
                            f"Verify the attribution: did you mean to put this "
                            f"sentence under Piece {other_num}?"
                        ),
                    })
            # Check exclusive domains (i.e., domains not shared across pieces)
            exclusive_domains = set(other_infra.get("domains", [])) - {
                d
                for k, infra in routing.items()
                if k != other_num
                for d in infra.get("domains", [])
            }
            for d in exclusive_domains:
                # Match @domain or 3x domain or just domain in prose
                if (f"@{d}" in section_lower or
                        re.search(rf"\b{re.escape(d)}\b", section_lower)):
                    key = ("domain", piece_num, other_num, d)
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append({
                        "severity": "HIGH",
                        "category": "piece-routing-cross-wire",
                        "line": line_of_match(content, d),
                        "message": (
                            f"Piece {piece_num} section mentions domain "
                            f"`{d}` which is exclusive to Piece {other_num} "
                            f"per pilot-routing.md."
                        ),
                    })
    return findings


def emit_dispatcher_format(findings: list[dict]) -> dict:
    by_cat: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for h in findings:
        by_cat[h.get("category", "?")] = by_cat.get(h.get("category", "?"), 0) + 1
        sev = h.get("severity", "?")
        by_sev[sev] = by_sev.get(sev, 0) + 1
    return {
        "total": len(findings),
        "hits": findings,
        "by_category": by_cat,
        "by_severity": by_sev,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps([]))
        return
    args = sys.argv[1:]
    fmt_dispatcher = "--format" in args and args[args.index("--format") + 1] == "json"
    file_arg = next((a for a in args if not a.startswith("--") and a != "json"), None)
    if not file_arg:
        print(json.dumps([]))
        return
    try:
        file_path = Path(file_arg)
        findings = validate(file_path)
        if fmt_dispatcher:
            print(json.dumps(emit_dispatcher_format(findings)))
        else:
            print(json.dumps(findings))
    except Exception:
        if fmt_dispatcher:
            print(json.dumps({"total": 0, "hits": [], "by_category": {}, "by_severity": {}}))
        else:
            print(json.dumps([]))


if __name__ == "__main__":
    main()
