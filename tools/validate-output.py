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
    # NOTE: the symbol branches use `(?:\b(?:words)\s+|<\s*)` -- a leading
    # `\b` before a `<`/`>` literal never matches when the symbol follows
    # whitespace (space->`<` is non-word->non-word, no boundary), which is
    # the common phrasing. Pre-F3 these HIGH rules silently no-op'd on
    # `< 30s response time` -- the exact 2026-03-23 #15 shape they exist to
    # catch. Anchor the word branches only; let the symbol branch float.
    (r"(?:\b(?:less than|under)\s+|<\s*)\d+\s*s(?:ec(?:onds?)?)?\s+(?:response|delivery|reply)\s+time\b",
     "unverified-claim", "HIGH",
     "Performance claim with no source. Verify against runtime data or remove."),
    (r"\b\d{2,3}%\s+(?:accuracy|uptime|success|reliability|delivery)\b",
     "unverified-claim", "HIGH",
     "Percentage stat with no source. Trace to a queried metric or replace with 'TBD'."),
    (r"(?:\b(?:over|more than)\s+|>\s*)\d{3,}\s+(?:leads|customers|users|requests|deliveries)\b",
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


# === F3: pre-client-message data-verification gate ===
# The 2026-03-23 stat/field-name fixes above are in RULES, yet the
# 2026-05-19 register #7 verification-theater regressed: a client-facing
# PROBLEM-CLAIM ("the C/D overclaim is actively damaging the campaign",
# recommend a worried client message) was asserted BEFORE querying live
# Instantly analytics; the analytics then refuted it. Memory
# (feedback_verify_against_live_data.md) failed to hold this twice
# (2026-03-23 + 2026-05-19). Register #7's prescribed fix is an enforced
# "query the source before asserting a client-facing problem claim" gate.
#
# Structural mechanism (not detection of whether a query happened -- a hook
# cannot know that): flag any present-tense factual PROBLEM/IMPACT assertion
# in client-facing text that has NO source attribution within a +/-2 line
# window. To pass, the author must either attribute it (which forces the
# query), soften it to a hypothesis, or add an explicit
# `<!-- output-allow:unsourced-claim reason -->` waiver. HIGH severity:
# this shape nearly sent a wrong worried message to a client.
CLAIM_PATTERNS = [
    r"\bis\s+(?:actively\s+)?(?:damaging|hurting|harming|breaking|killing|tanking|crippling|destroying)\b",
    r"\bare\s+(?:actively\s+)?(?:damaging|hurting|harming|breaking|failing)\b",
    r"\bis\s+(?:significantly\s+|seriously\s+|badly\s+)?(?:impacting|affecting|degrading|suffering)\b",
    r"\b(?:is|are)\s+causing\s+(?:a\s+)?(?:problem|issue|drop|loss|damage|harm)\b",
    r"\b(?:deliverability|reputation|open rate|reply rate|performance|the campaign)\s+(?:is|has)\s+(?:dropped|tanked|collapsed|suffered|been hurt|been damaged)\b",
    r"\bthis (?:over\s?claim|mistake|bug|error|issue) is (?:actively |seriously |badly )?(?:damaging|hurting|impacting|costing|affecting)\b",
    r"\b(?:we'?re|we are) (?:losing|bleeding|burning) (?:leads|opportunities|revenue|money|deliverability)\b",
]
CLAIM_RE = [re.compile(p, re.IGNORECASE) for p in CLAIM_PATTERNS]
# Hypothesis / hedge cues -> not the regressed shape (a flat assertion). If
# the claim line is hedged, do not flag.
HEDGE_RE = re.compile(
    r"\b(?:could|would|might|may|possibly|potentially|if\s|risk(?:s|ed)?\b|"
    r"i\s+(?:suspect|think|believe|worry)|seems?\s+to|appears?\s+to|likely|"
    r"probably|hypothes|my\s+(?:guess|hunch))\b", re.IGNORECASE)
# Source-attribution cues. Presence within +/-2 lines == the claim is tied
# to queried evidence -> not flagged.
SOURCE_RE = re.compile(
    r"\b(?:per|according to|based on|queried|i\s+queried|i\s+checked|i\s+pulled|"
    r"we\s+measured|the\s+(?:data\s+store|database|analytics|export|metrics|numbers|logs)\s+(?:show|shows|say|confirm)|"
    r"analytics\s+(?:show|shows|confirm)|live\s+(?:data|analytics|count)|"
    r"mysql|instantly\s+analytics|\(source:|\[source:|measured\s+at|"
    r"as\s+of\s+\d|from\s+the\s+(?:data\s+store|export|dashboard|api))\b",
    re.IGNORECASE)


def check_unsourced_claims(
    lines: list[str], suppress: dict, eligible: set[int]
) -> list[dict]:
    """Flag present-tense client-facing PROBLEM-claims with no source
    attribution within a +/-2 line window. See F3 block above."""
    hits: list[dict] = []
    for i, line in enumerate(lines, 1):
        if i not in eligible:
            continue
        if "unsourced-claim" in suppress.get(i, set()):
            continue
        if not any(rx.search(line) for rx in CLAIM_RE):
            continue
        if HEDGE_RE.search(line):  # a hypothesis is not the regressed shape
            continue
        window = "\n".join(
            lines[j - 1] for j in range(max(1, i - 2), min(len(lines), i + 2) + 1)
        )
        if SOURCE_RE.search(window):
            continue
        hits.append({
            "line": i,
            "category": "unsourced-claim",
            "severity": "HIGH",
            "message": (
                "Client-facing PROBLEM-claim asserted as fact with no source "
                "attribution nearby (B4 / register #7 verification-theater). "
                "Before sending: query the live source (analytics, data store, "
                "DB) and cite it inline, OR soften to a hypothesis, OR add "
                "`<!-- output-allow:unsourced-claim reason -->`."
            ),
            "snippet": line.strip()[:160],
        })
    return hits


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


# === Cost-anchor drift (register 2026-05-25 #121) ===
# When a client-facing draft asserts a cost figure, surface every prior cost
# figure already stated in the same client's comms-log.md so the agent can
# verify the new figure matches prior commitments. Pattern: agent proposed
# Mailforge ~£120-180/yr ignoring £25/yr already committed to Gurmej on
# 2026-05-22 in a separate message. Cross-reference is the agent's job; this
# hook makes the prior figures visible so the agent CAN cross-reference.
COST_FIGURE_RE = re.compile(
    r"(?:[£$€¥]\s?\d[\d,]*(?:\.\d+)?(?:\s*[-–to]+\s*[£$€¥]?\s?\d[\d,]*(?:\.\d+)?)?"
    r"|\b\d[\d,]*(?:\.\d+)?\s*(?:USD|EUR|GBP|CHF|pounds?|dollars?|euros?)\b)"
    r"(?:\s*(?:per|\/|a)\s*(?:year|yr|month|mo|week|wk|hour|hr|day))?",
    re.IGNORECASE,
)


def find_comms_log_for(path: Path) -> Path | None:
    """Walk up from `path` to find a sibling/ancestor comms-log.md within
    a workspace/clients/{client}/ tree. Returns None if not found."""
    for parent in [path.parent, *path.parents]:
        candidate = parent / "comms-log.md"
        if candidate.exists() and candidate.resolve() != path.resolve():
            return candidate
        if parent.name == "workspace":
            break
    return None


def is_clientfacing_draft(path: Path) -> bool:
    s = str(path).replace("\\", "/").lower()
    return (
        "/context/drafts/" in s
        or "/deliverables/" in s
        or "comms-log.md" in s
        or "/proposals/" in s
    )


def check_cost_anchor(path: Path, lines: list[str]) -> list[dict]:
    """If the draft contains a cost figure and a comms-log.md exists in the
    client's tree, emit a MEDIUM advisory listing prior cost figures from
    that log so the agent can confirm alignment."""
    if not is_clientfacing_draft(path):
        return []
    draft_text = "\n".join(lines)
    draft_costs: list[tuple[int, str]] = []
    for i, line in enumerate(lines, 1):
        for m in COST_FIGURE_RE.finditer(line):
            draft_costs.append((i, m.group(0).strip()))
    if not draft_costs:
        return []

    log_path = find_comms_log_for(path)
    if not log_path:
        return []
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    prior_costs = sorted({m.group(0).strip() for m in COST_FIGURE_RE.finditer(log_text)})
    if not prior_costs:
        return []

    # Only emit if the draft figures aren't already verbatim in the log
    # (a perfect string match means the agent is restating, not drifting).
    new_costs = [(ln, c) for (ln, c) in draft_costs if c not in log_text]
    if not new_costs:
        return []

    log_rel = log_path.as_posix()
    listed = ", ".join(prior_costs[:8]) + (" ..." if len(prior_costs) > 8 else "")
    hits = []
    for ln, c in new_costs[:5]:
        hits.append({
            "line": ln,
            "category": "cost-anchor-drift",
            "severity": "MEDIUM",
            "message": (
                f"Draft contains cost figure '{c}' not previously stated in "
                f"{log_rel}. Prior figures in this client's comms-log: "
                f"[{listed}]. Verify the new figure matches what's been "
                f"committed before; if it's a different line-item, mark that "
                f"explicitly. (register #121: 2026-05-25 cost-anchor-drift)"
            ),
            "snippet": c,
        })
    return hits


def check_text(text: str, path: Path | None = None) -> list[dict]:
    """Return list of hit dicts."""
    lines = text.splitlines()
    suppress = parse_suppressions(lines)

    hits: list[dict] = []
    eligible: set[int] = set()
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
        eligible.add(i)
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
    # F3: contextual pre-client-message problem-claim gate (needs the
    # +/-2 line window, so it runs after the per-line eligible set is built).
    hits.extend(check_unsourced_claims(lines, suppress, eligible))
    # Cost-anchor drift (register #121, 2026-05-25): needs the file path to
    # locate the client's comms-log.md. Skip when called without a path.
    if path is not None:
        hits.extend(check_cost_anchor(path, lines))
    hits.sort(key=lambda h: h["line"])
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
        payload = aggregate(check_text(text, targets[0]))
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
        payload = aggregate(check_text(text, path))
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
