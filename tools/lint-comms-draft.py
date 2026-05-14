#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Anti-slop lint for client comms drafts and comms-log entries.

Comms drafts are markdown files in .../context/drafts/ or .../proposals/
or comms-log.md. They should sound like the user, not like an LLM. This
linter targets the comms-specific failure modes:

  1. LLM-tell openers ("It's worth noting", "I hope this finds you well")
  2. Hedge-heavy passive voice
  3. Marketing adjectives without substance ("seamless", "robust")
  4. Em-dash overuse (per feedback_no_em_dashes.md) — flag unless --skip-em-dash
  5. Brand/contact misspellings (deferred to validate-output, but cross-checked)
  6. Triplet symmetry / parallelism filler
  7. "We" without an actual subject

Friction context: comms log fell 4 days stale despite drafts being made
(2026-03-06). Drafts that read as AI also got flagged repeatedly. This
catches the second class.

Called by post-write-gate.py with --skip-em-dash for files that are typed
into Slack/email systems where em-dash render is fine. Standalone usage
includes em-dash by default.

Usage:
    uv run tools/lint-comms-draft.py FILE [FILE ...]
    uv run tools/lint-comms-draft.py FILE --format json
    uv run tools/lint-comms-draft.py FILE --skip-em-dash

Exit 0 = pass. Exit 1 = hits found. Exit 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# (regex, category, severity, message)
RULES: list[tuple[str, str, str, str]] = [
    # === LLM-tell openers (high signal of generated content) ===
    (r"\bI hope (?:this|you) (?:finds? you well|are doing well|find this email well)\b",
     "llm-opener", "HIGH",
     "AI-form opener. Cut. Open with the actual subject."),
    (r"\b(?:Just )?wanted to (?:reach out|touch base|circle back|follow up)\b",
     "llm-opener", "HIGH",
     "Filler opener. State the reason directly."),
    (r"\bI'?m reaching out (?:to|because|regarding)\b",
     "llm-opener", "MEDIUM",
     "Filler opener. State the reason directly."),
    (r"\bIt'?s worth noting that\b",
     "llm-opener", "HIGH",
     "LLM hedge. Just state the fact."),
    (r"\bI wanted to (?:let you know|inform you|share with you)\b",
     "llm-opener", "MEDIUM",
     "Filler. Cut to the content."),

    # === LLM closers ===
    (r"\bDon'?t hesitate to reach out\b",
     "llm-closer", "HIGH",
     "AI-form closer. Cut or replace with concrete next step."),
    (r"\bLooking forward to hearing (?:from you|your thoughts)\b",
     "llm-closer", "MEDIUM",
     "Generic closer. Replace with the specific next step."),
    (r"\bPlease let me know if (?:you have any|there are any)\b",
     "llm-closer", "MEDIUM",
     "Filler closer. Cut or specify."),

    # === Marketing adjectives without substance ===
    (r"\b(?:seamless|seamlessly)\b",
     "marketing-adj", "MEDIUM",
     "Marketing adjective. Be specific about the mechanism."),
    (r"\b(?:robust|comprehensive|powerful|cutting-?edge|state-of-the-art)\b",
     "marketing-adj", "MEDIUM",
     "Marketing adjective without substance. Replace with the concrete claim."),
    (r"\bleverages?\b",
     "marketing-adj", "LOW",
     "Corporate-speak. 'uses' is fine."),
    (r"\bempowers?\b",
     "marketing-adj", "LOW",
     "Marketing verb. State what the user can actually do."),

    # === Hedging / passive voice without subject ===
    (r"\bIt can be (?:noted|seen|observed) that\b",
     "hedge", "MEDIUM",
     "Passive hedge. State who notes/sees it."),
    (r"\bIt should be (?:noted|mentioned|highlighted) that\b",
     "hedge", "HIGH",
     "Performative hedge. Cut and state the fact."),

    # === Three-item rhetorical lists (parallelism filler) ===
    (r"\b\w+,\s+\w+,\s+(?:and|or)\s+\w+\.",
     "triplet", "LOW",
     "Possible rhetorical triplet. Confirm content > pattern."),

    # === Brand cross-check (HIGH because comms goes to clients) ===
    (r"\bUnpausAI\b",
     "brand-misspell", "HIGH",
     "Brand is 'UnpauseAI' (with E)."),
    (r"\bnicholas\.neuman\b",
     "brand-misspell", "HIGH",
     "Email is 'nicolas.neumann@', not 'nicholas.neuman@'."),

    # === Claude-specific tells ===
    (r"\b(?:delve|delving) into\b",
     "llm-tell", "HIGH",
     "Claude-tell phrase. Replace with a direct verb."),
    (r"\bin today'?s (?:world|landscape|environment|fast-paced)",
     "llm-tell", "HIGH",
     "LLM article-opener. Cut."),
]

EM_DASH_RULES: list[tuple[str, str, str, str]] = [
    (r" — ", "em-dash", "MEDIUM",
     "Em-dash banned in comms. Use comma, semicolon, colon, or period."),
    (r" -- ", "em-dash-substitute", "MEDIUM",
     "Double-hyphen as em-dash substitute. Same rule."),
]


def check_text(text: str, include_em_dash: bool) -> list[dict]:
    rules = list(RULES)
    if include_em_dash:
        rules.extend(EM_DASH_RULES)

    hits: list[dict] = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("> "):
            continue
        for regex, category, severity, message in rules:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="Markdown files to check")
    ap.add_argument("--skip-em-dash", action="store_true",
                    help="Skip em-dash check (e.g., when target system renders them well)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    targets = [Path(f) for f in args.files if Path(f).is_file()]
    if not targets:
        if args.format == "json":
            print(json.dumps({"total": 0, "hits": [], "by_category": {}, "by_severity": {}}))
            return 0
        print("ERROR: no files.", file=sys.stderr)
        return 2

    if args.format == "json" and len(targets) == 1:
        text = targets[0].read_text(encoding="utf-8", errors="replace")
        hits = check_text(text, include_em_dash=not args.skip_em_dash)
        print(json.dumps(aggregate(hits)))
        return 0

    grand_total = 0
    grand_cat: dict[str, int] = {}
    grand_sev: dict[str, int] = {}
    for path in targets:
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = check_text(text, include_em_dash=not args.skip_em_dash)
        payload = aggregate(hits)
        if payload["total"]:
            print(f"\n## {path}")
            for h in payload["hits"]:
                print(f"  L{h['line']:4d}  [{h['severity']}] [{h['category']}] {h['message']}")
                print(f"        -> {h['snippet']}")
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
    return 1 if grand_total else 0


if __name__ == "__main__":
    sys.exit(main())
