#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Universal output validator for client-facing artifacts and comms.

Catches behavioral failure modes the friction register flagged repeatedly:
verification-theater (fabricated stats, unverified claims), brand
misspellings (UnpausAI for UnpauseAI, nicholas.neuman for nicolas.neumann),
em-dash usage (per feedback_no_em_dashes), placeholder leakage, and
LLM-tell phrases that signal generated-not-thought content.

Called by post-write-gate.py for any file in deliverable or comms scope.
Also runnable standalone for ad-hoc auditing.

Usage:
    uv run tools/validate-output.py FILE [FILE ...]
    uv run tools/validate-output.py FILE --format json
    uv run tools/validate-output.py --dir workspace/clients/{client}/...

Suppression:
    Add `<!-- output-allow:CATEGORY -->` on the line BEFORE the hit, with
    a reason. Multi-line: `<!-- output-allow:CATEGORY:N -->` (next N lines).

Exit 0 = no hits. Exit 1 = hits found. Exit 2 = usage error.
JSON output (when --format json) always exits 0 so the hook can parse it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# (regex, category, severity, message)
# Severity: HIGH = ship-blocker, MEDIUM = should fix, LOW = nudge
RULES: list[tuple[str, str, str, str]] = [
    # === Brand accuracy (from friction 2026-03-15: content-error) ===
    (r"\bUnpausAI\b",
     "brand-misspell", "HIGH",
     "Brand is 'UnpauseAI' (with E), not 'UnpausAI'."),
    (r"\bunpaus\.ai\b",
     "brand-misspell", "HIGH",
     "Domain is 'unpauseai.com', not 'unpaus.ai'."),
    (r"\bnicholas\.neuman\b",
     "brand-misspell", "HIGH",
     "Email is 'nicolas.neumann@', not 'nicholas.neuman@'."),
    (r"\bnicholas neumann\b",
     "brand-misspell", "HIGH",
     "Name is 'Nicolas Neumann', not 'Nicholas Neumann'."),
    (r"\bnicolas neuman\b(?!n)",
     "brand-misspell", "HIGH",
     "Surname is 'Neumann' (double-n), not 'Neuman'."),

    # === Em-dash and double-hyphen substitute (feedback_no_em_dashes) ===
    (r" — ",
     "em-dash", "MEDIUM",
     "Em-dash banned in prose. Use comma, semicolon, colon, or period."),
    (r" -- ",
     "em-dash-substitute", "MEDIUM",
     "Double-hyphen as em-dash substitute is banned. Use comma/semicolon/colon."),

    # === Verification-theater patterns (from 2026-03-23) ===
    # Plausible-sounding round-number stats with no source
    (r"\b(?:less than |under |<\s*)\d+\s*s(?:ec(?:onds?)?)?\s+(?:response|delivery|reply)\s+time\b",
     "unverified-claim", "HIGH",
     "Performance claim with no source. Verify against runtime data or remove."),
    (r"\b\d{2,3}%\s+(?:accuracy|uptime|success|reliability|delivery)\b",
     "unverified-claim", "HIGH",
     "Percentage stat with no source. Trace to a queried metric or replace with 'TBD'."),
    (r"\b(?:over|more than|>)\s*\d{3,}\s+(?:leads|customers|users|requests|deliveries)\b",
     "unverified-claim", "MEDIUM",
     "Volume claim with no source. Cite the metric or remove."),

    # === Placeholder leakage ===
    # Doubled-percent placeholders that should have been replaced
    (r"##[A-Za-z_][A-Za-z0-9_]*##",
     "placeholder-leak", "HIGH",
     "Template placeholder leaked into output. Verify replacement chain."),
    (r"\{\{\s*[A-Za-z_][A-Za-z0-9_.]*\s*\}\}",
     "placeholder-leak", "HIGH",
     "Mustache placeholder leaked into output. Verify rendering."),
    # Lorem ipsum
    (r"\blorem ipsum\b",
     "placeholder-leak", "HIGH",
     "Lorem ipsum placeholder in output."),

    # === LLM-tell phrases (selected — not full voice-check, just hard tells) ===
    (r"\b(?:delve|delving) into\b",
     "llm-tell", "MEDIUM",
     "Claude-tell phrase. Replace with a direct verb."),
    (r"\bin today's (?:world|landscape|environment|fast-paced)",
     "llm-tell", "MEDIUM",
     "LLM article-opener. Cut or rewrite."),
    (r"\bit's worth noting that\b",
     "llm-tell", "MEDIUM",
     "LLM hedge. Just state the fact."),
    (r"\b(?:seamless|seamlessly)\b",
     "llm-tell", "LOW",
     "Marketing adjective. Be specific about what's seamless."),
    (r"\bwhether it'?s\b",
     "llm-tell", "LOW",
     "Parallelism filler. Cut."),

    # === Fabrication risk (specific patterns from friction) ===
    # weight_X / score_X field names invented without querying source
    # (friction 2026-03-23: lead-scoring.html fabricated 6 field names)
    # This is hard to detect generically; flag as nudge when patterns appear.
    (r"\bweight_[a-z_]{4,}\b",
     "fabrication-risk", "MEDIUM",
     "Field name like 'weight_X' looks fabricated. Verify against the actual source (data store, DB, config) before publishing."),
]


SUPPRESS_RE = re.compile(r"<!--\s*output-allow:([\w,-]+)(?::(\d+))?(?:\s+(.*?))?\s*-->")


def parse_suppressions(lines: list[str]) -> dict[int, set[str]]:
    """Return {line_no_1based: {category, ...}} of suppressed categories.

    Suppression marker on line N suppresses line N+1. With :K, suppresses
    lines N+1 through N+K.
    """
    suppress: dict[int, set[str]] = {}
    for i, line in enumerate(lines, 1):
        m = SUPPRESS_RE.search(line)
        if not m:
            continue
        cats = {c.strip() for c in m.group(1).split(",") if c.strip()}
        span = int(m.group(2)) if m.group(2) else 1
        for j in range(i + 1, i + 1 + span):
            suppress.setdefault(j, set()).update(cats)
    return suppress


def check_text(text: str) -> list[dict]:
    """Return list of hit dicts."""
    lines = text.splitlines()
    suppress = parse_suppressions(lines)

    hits: list[dict] = []
    in_fence = False
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Skip blockquoted citations
        if stripped.startswith("> "):
            continue
        suppressed_here = suppress.get(i, set())
        for regex, category, severity, message in RULES:
            if category in suppressed_here:
                continue
            if re.search(regex, line, flags=re.IGNORECASE):
                hits.append({
                    "line": i,
                    "category": category,
                    "severity": severity,
                    "message": message,
                    "snippet": line.strip()[:160],
                })
    return hits


def aggregate(hits: list[dict]) -> dict:
    by_cat: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for h in hits:
        by_cat[h["category"]] = by_cat.get(h["category"], 0) + 1
        by_sev[h["severity"]] = by_sev.get(h["severity"], 0) + 1
    return {
        "total": len(hits),
        "hits": hits,
        "by_category": by_cat,
        "by_severity": by_sev,
    }


def emit_text(path: Path, payload: dict) -> None:
    if payload["total"] == 0:
        return
    print(f"\n## {path}")
    print(f"  Total: {payload['total']}  ({', '.join(f'{k}={v}' for k,v in payload['by_severity'].items())})")
    for h in payload["hits"]:
        sev = h.get("severity", "?")
        print(f"  L{h['line']:4d}  [{sev}] [{h['category']}] {h['message']}")
        print(f"        -> {h['snippet']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="Files to check")
    ap.add_argument("--dir", help="Directory to recursively check")
    ap.add_argument("--glob", default="**/*.md", help="Glob within --dir")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    targets: list[Path] = []
    for f in args.files:
        p = Path(f)
        if p.is_file():
            targets.append(p)
    if args.dir:
        d = Path(args.dir)
        if not d.is_dir():
            print(f"ERROR: not a directory: {d}", file=sys.stderr)
            return 2
        targets.extend(d.glob(args.glob))

    if not targets:
        if args.format == "json":
            print(json.dumps({"total": 0, "hits": [], "by_category": {}, "by_severity": {}}))
            return 0
        print("ERROR: no files to check.", file=sys.stderr)
        return 2

    if args.format == "json" and len(targets) == 1:
        # Hook contract: one file in, one JSON payload out.
        try:
            text = targets[0].read_text(encoding="utf-8", errors="replace")
        except OSError:
            print(json.dumps({"total": 0, "hits": [], "by_category": {}, "by_severity": {}}))
            return 0
        payload = aggregate(check_text(text))
        print(json.dumps(payload))
        return 0

    # Text mode (multi-file aggregate)
    grand_total = 0
    grand_cat: dict[str, int] = {}
    grand_sev: dict[str, int] = {}
    for path in sorted(set(targets)):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        payload = aggregate(check_text(text))
        emit_text(path, payload)
        grand_total += payload["total"]
        for k, v in payload["by_category"].items():
            grand_cat[k] = grand_cat.get(k, 0) + v
        for k, v in payload["by_severity"].items():
            grand_sev[k] = grand_sev.get(k, 0) + v

    if args.format == "json":
        print(json.dumps({
            "total": grand_total,
            "hits": [],
            "by_category": grand_cat,
            "by_severity": grand_sev,
        }))
        return 0

    print(f"\n---\nGrand total: {grand_total} hits across {len(targets)} files.")
    if grand_sev:
        print("By severity: " + ", ".join(f"{k}={v}" for k, v in sorted(grand_sev.items())))
    if grand_cat:
        print("By category:")
        for cat, n in sorted(grand_cat.items(), key=lambda kv: -kv[1]):
            print(f"  {n:4d}  {cat}")
    return 1 if grand_total else 0


if __name__ == "__main__":
    sys.exit(main())
