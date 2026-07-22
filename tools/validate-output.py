#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Universal output validator for client-facing artifacts and comms.

Catches behavioral failure modes the friction register flagged repeatedly:
verification-theater (fabricated stats, unverified claims), brand
misspellings (UnpausAI for UnpauseAI, nicholas.neuman for nicolas.neumann),
em-dash usage (per feedback_no_em_dashes), placeholder leakage, and
LLM-tell phrases that signal generated-not-thought content.

Also carries the two structural slop detectors rule_anti_slop specifies:
`symmetry-collapse` and `per-category-narration`, both LOW / advisory, both
markdown-only. See the block above check_structural_slop().

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
    # Four grammatical forms, one rule class (2026-07-22 blind-spot fix: the
    # spaced-only patterns missed tight `word—word`, `&mdash;`, and tight
    # `word--word`, which shipped unflagged).
    (r" — ",
     "em-dash", "MEDIUM",
     "Em-dash banned in prose. Use comma, semicolon, colon, or period."),
    (r"(?<! )—|—(?! )",
     "em-dash", "MEDIUM",
     "Tight em-dash (no surrounding spaces) is still an em-dash. Use comma, semicolon, colon, or period."),
    (r"&mdash;",
     "em-dash", "MEDIUM",
     "&mdash; entity is an em-dash. Use comma, semicolon, colon, or period."),
    (r" -- ",
     "em-dash-substitute", "MEDIUM",
     "Double-hyphen as em-dash substitute is banned. Use comma/semicolon/colon."),
    (r"(?<=\w)--(?=\w)",
     "em-dash-substitute", "MEDIUM",
     "Tight double-hyphen between words is an em-dash substitute. Use comma/semicolon/colon."),

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


# === Cell-scoped voice scan (register #160, 2026-06-01) ===
# AI-tells (em-dashes, parenthetical laundry-lists, slash-joined runs,
# fake-precision counts, formal class-name runs) landed in billing-visible
# hours-tracker.xlsx cells, because every voice-pass gate was extension-gated
# to .html/.md and skipped .xlsx/.csv. These detectors apply the same voice
# standard to structured-data cell content. Kept narrow (terse fragments, not
# prose) to hold false-positives down: slash-runs need 3+ segments (so CI/CD,
# TCP/IP pass), the two case-sensitive detectors are LOW severity. yaml is
# excluded entirely (all repo yaml is config -> guaranteed FP storm).
_EM_DASH = "—"
CELL_RULES: list[tuple[str, str, str, str]] = [
    (_EM_DASH + r"|&mdash;| -- ",
     "em-dash", "MEDIUM",
     "Em-dash / double-hyphen in a cell reads as an AI tell. Use a comma or semicolon, or split."),
    (r"\([^\n]*(?:,\s|\s\+\s)[^\n]*(?:,\s|\s\+\s)[^\n]*\)",
     "parenthetical-laundry-list", "MEDIUM",
     "Parenthetical list of 3+ items is an AI tell. Fold into the sentence or cut."),
    (r"(?i)\b(?:tests?|files?|checks?|cases?|commits?|rows?|cols?|items?)\s*\(\d+\)",
     "fake-precision-count", "LOW",
     "Fake-precision count like 'tests (14)'. Drop the parenthetical number."),
    (r"\b[A-Z][A-Za-z0-9]+(?:/[A-Z][A-Za-z0-9]+){2,}\b",
     "slash-joined-run", "LOW",
     "Slash-joined run like 'BLUEPRINT/README/ANNEALING' reads as an AI tell. List in prose."),
    (r"\b[A-Z][A-Za-z0-9]+ \+ [A-Z][A-Za-z0-9]+(?: \+ [A-Z][A-Za-z0-9]+)*",
     "formal-classname-run", "LOW",
     "Formal class-name run mid-cell ('Protocol + OpenAIClient + Mock') reads as machine output. Rephrase."),
]


def is_cell_file(path: Path) -> bool:
    """Structured-data files whose CELLS carry human text (xlsx/csv/tsv).
    yaml is deliberately excluded: all repo yaml is config, not prose."""
    return path.suffix.lower() in (".xlsx", ".csv", ".tsv")


def read_cells(path: Path) -> list[tuple[str, str]]:
    """Yield (location_label, text) for human-text cells. Skips formulas (`=`),
    `[auto]` machine notes, hidden sheets, and non-string values. Returns []
    on any error or missing dependency (graceful: never crash the hook)."""
    suffix = path.suffix.lower()
    out: list[tuple[str, str]] = []
    if suffix in (".csv", ".tsv"):
        import csv
        delim = "\t" if suffix == ".tsv" else ","
        try:
            with path.open(encoding="utf-8", errors="replace", newline="") as f:
                for r, row in enumerate(csv.reader(f, delimiter=delim), 1):
                    for c, val in enumerate(row, 1):
                        if isinstance(val, str) and val.strip() and not val.lstrip().startswith("="):
                            out.append((f"row{r}col{c}", val))
        except OSError:
            return []
        return out
    if suffix == ".xlsx":
        try:
            import openpyxl
        except Exception:
            return []  # dep absent -> degrade to no cell scan, never crash
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
        except Exception:
            return []
        try:
            for ws in wb.worksheets:
                if getattr(ws, "sheet_state", "visible") != "visible":
                    continue
                for row in ws.iter_rows():
                    for cell in row:
                        v = cell.value
                        if not isinstance(v, str):
                            continue
                        s = v.strip()
                        if not s or s.startswith("=") or s.startswith("[auto]"):
                            continue
                        out.append((f"{ws.title}!{cell.coordinate}", v))
        finally:
            wb.close()
        return out
    return []


def check_cells(path: Path) -> list[dict]:
    """Run CELL_RULES over each human-text cell. line=0 + a `cell` label
    (additive to the JSON contract; consumers read category/severity/message)."""
    hits: list[dict] = []
    for label, text in read_cells(path):
        for regex, category, severity, message in CELL_RULES:
            if re.search(regex, text):
                hits.append({
                    "line": 0,
                    "cell": label,
                    "category": category,
                    "severity": severity,
                    "message": message,
                    "snippet": text.strip()[:160],
                })
    return hits


# === Structural slop detectors (rule_anti_slop.md Enforcement, 2026-07-22) ===
# rule_anti_slop listed two detectors as "future enforcement candidates"; the
# friction register flagged the prose-volume/symmetry one "structural OVERDUE"
# on 2026-06-12 (row 208). Both are heuristics over markdown structure with no
# NLP dependency, so both ship at LOW severity: the tool's own legend calls LOW
# a nudge, and a false MEDIUM/HIGH here would drown the post-write-gate signal
# that the brand / placeholder / unsourced-claim rules carry.
#
# symmetry-collapse       -> "Three-part lists where two work" + protocol step 2
# per-category-narration  -> "Per-category narration on intuitive variance"
#
# Both require TWO independent signals before firing (tight length clustering
# AND a shared literal opening template), because either alone matches ordinary
# prose. The rule's own "What is NOT slop" list is the calibration target:
# variable sentence shape, unique info per row, short factual items, and a
# brief note before a code block must all stay silent.

_STRUCT_SUFFIXES = (".md", ".markdown", ".txt")

MIN_RUN = 3                    # "three-part lists" is the rule's own floor
BULLET_MIN_CHARS = 60          # below this a bullet is a factual item, not prose
BULLET_CV_MAX = 0.12           # stddev/mean of item lengths
PARA_MIN_CHARS = 100
PARA_CV_MAX = 0.12
TABLE_MIN_ROWS = 3
TABLE_CELL_MIN_CHARS = 40      # keeps ID / status / date columns out
TABLE_CELL_MIN_WORDS = 6
DEFLIST_TAIL_MIN_CHARS = 40
DEFLIST_CV_MAX = 0.15
MAX_STRUCT_HITS_PER_CATEGORY = 3

# Function words survive into the skeleton literally: they are what makes a
# shared opening a TEMPLATE rather than a coincidence of parts of speech.
FUNCTION_WORDS = {
    "a", "an", "the", "this", "that", "these", "those", "it", "its", "we",
    "our", "you", "your", "they", "their", "there", "here", "is", "are", "was",
    "were", "be", "been", "being", "has", "have", "had", "do", "does", "did",
    "can", "will", "would", "should", "must", "may", "might", "and", "or",
    "but", "if", "when", "while", "because", "which", "who", "what", "how",
    "of", "in", "on", "to", "for", "with", "by", "from", "at", "as", "into",
    "per", "than", "then", "so", "such", "only", "also", "still", "never",
    "always", "each", "every", "all", "no", "not", "after", "before",
    "during", "without", "within", "one", "two", "three", "now", "once",
}

_HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s")
_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
_HR_RE = re.compile(r"^ {0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
_BULLET_RE = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_ORDERED_RE = re.compile(r"^\s*\d+[.)]\s+")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_DELIM_CELL_RE = re.compile(r"^:?-{2,}:?$")
_CHECKBOX_RE = re.compile(r"^\[[ xX]\]\s")
_BOLD_LEAD_RE = re.compile(r"^\*\*([^*\n]{1,80})\*\*\s*[:.,;)–-]?\s*(.*)$")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*|\d[\d,.]*%?")
_SENTENCE_END_RE = re.compile(r"[.!?](?:\s|$)")
# A bold lead that is a sequence label ("**Week 3:**", "**Phase 2:**") makes the
# run an ordered list in disguise. Numbered lists imply sequence, so their
# symmetry is the point, exactly as for `1.` / `2.` markers.
_SEQ_LEAD_RE = re.compile(
    r"^(?:\d|(?:week|phase|step|day|month|year|quarter|round|sprint|stage|part|"
    r"tier|level|milestone|iteration|wave|batch|session|q|v)\s*\.?\s*\d)",
    re.IGNORECASE,
)


def _cv(values: list[int]) -> float:
    """Coefficient of variation (stddev / mean). 0 == identical lengths."""
    if not values:
        return 1.0
    mean = sum(values) / len(values)
    if mean <= 0:
        return 1.0
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return (var ** 0.5) / mean


def _lead_skeleton(text: str, depth: int = 4) -> str | None:
    """Approximate the opening grammar of `text` with no NLP dependency.

    A bold lead collapses to `**`, numbers to `#`, content words to `X`;
    function words survive literally. Returns None when the text is too short
    to have a shape worth comparing.
    """
    t = text.strip()
    parts: list[str] = []
    m = _BOLD_LEAD_RE.match(t)
    if m:
        parts.append("**")
        t = m.group(2)
    toks = _WORD_RE.findall(t)
    if len(toks) + len(parts) < 3:
        return None
    for tok in toks[: max(0, depth - len(parts))]:
        low = tok.lower()
        if low in FUNCTION_WORDS:
            parts.append(low)
        elif tok[0].isdigit():
            parts.append("#")
        else:
            parts.append("X")
    return " ".join(parts)


def _is_templated(skeletons: list[str | None]) -> bool:
    """One shared skeleton carrying at least one literal anchor.

    `X X X X` is the shape of almost any English sentence, so an all-placeholder
    skeleton is never evidence of a template on its own. Requiring a shared
    function word or a shared bold lead is what keeps "lists with variable
    sentence shape" (rule_anti_slop, What is NOT slop) silent.
    """
    if not skeletons or any(s is None for s in skeletons):
        return False
    if len(set(skeletons)) != 1:
        return False
    return any(part not in ("X", "#") for part in skeletons[0].split())


def _is_enumeration(text: str) -> bool:
    """A comma-separated inventory (deck contents, field lists, slide orders)
    is data, not narration: many commas, at most one sentence terminator."""
    return text.count(",") >= 4 and len(_SENTENCE_END_RE.findall(text)) <= 1


def _is_sentence_shaped(text: str) -> bool:
    """Per-category NARRATION means sentences. A column of noun phrases (a
    routing table, a glossary) is parallel by design and never a hit."""
    return bool(_SENTENCE_END_RE.search(text)) or len(text) >= 90


def _is_sequence_run(run: list[dict]) -> bool:
    """Bold-led run that is an ordered sequence -> exempt.

    Every entry must carry a bold lead and at least two thirds of the leads
    must be sequence labels, so a timeline that ends on a trailing
    `**Retainer phase:**` still reads as the sequence it is.
    """
    leads = []
    for entry in run:
        m = _BOLD_LEAD_RE.match(entry["text"])
        if not m:
            return False
        leads.append(m.group(1).strip())
    seq = sum(1 for lead in leads if _SEQ_LEAD_RE.match(lead))
    return seq * 3 >= len(leads) * 2


def _is_question_run(run: list[dict]) -> bool:
    """A run of questions is a checklist. Parallel by design, same as a
    numbered procedure, so its symmetry is never the slop the rule targets."""
    return all("?" in entry["text"] for entry in run)


def _classify_lines(lines: list[str]) -> list[str]:
    """Per-line structural kind. Fences, frontmatter, blockquotes, HTML and
    comments become barriers so no run can span them."""
    kinds: list[str] = []
    in_fence = False
    in_frontmatter = False
    for i, raw in enumerate(lines):
        s = raw.strip()
        if i == 0 and s == "---":
            in_frontmatter = True
            kinds.append("barrier")
            continue
        if in_frontmatter:
            kinds.append("barrier")
            if s == "---":
                in_frontmatter = False
            continue
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            kinds.append("barrier")
            continue
        if in_fence:
            kinds.append("barrier")
            continue
        if not s:
            kinds.append("blank")
            continue
        if _HR_RE.match(raw) or _HEADING_RE.match(raw):
            kinds.append("heading")
            continue
        if s.startswith(">") or s.startswith("<"):
            kinds.append("barrier")
            continue
        if _TABLE_ROW_RE.match(raw):
            kinds.append("table")
            continue
        if _ORDERED_RE.match(raw):
            # Numbered lists imply a sequence (a procedure, a protocol). Their
            # symmetry is the point, so they are never symmetry-collapse hits.
            kinds.append("ordered")
            continue
        if _BULLET_RE.match(raw):
            kinds.append("bullet")
            continue
        kinds.append("text")
    return kinds


def _only_blank_between(kinds: list[str], a: int, b: int) -> bool:
    """True when every line strictly between indices a and b is blank."""
    return all(kinds[k] == "blank" for k in range(a + 1, b))


def _collect_bullets(lines: list[str], kinds: list[str]) -> tuple[list[dict], set[int]]:
    """Bullet items with lazy-continuation lines folded in, plus the set of
    line indices those continuations consumed (so paragraphs skip them)."""
    items: list[dict] = []
    consumed: set[int] = set()
    i = 0
    n = len(lines)
    while i < n:
        if kinds[i] != "bullet":
            i += 1
            continue
        m = _BULLET_RE.match(lines[i])
        text = m.group(3).strip()
        j = i + 1
        while j < n and kinds[j] == "text":
            text += " " + lines[j].strip()
            consumed.add(j)
            j += 1
        items.append({
            "line": i + 1,
            "start": i,
            "end": j - 1,
            "indent": len(m.group(1).expandtabs(4)),
            "marker": m.group(2),
            "text": text,
            "skip": bool(_CHECKBOX_RE.match(text)),
        })
        i = j
    return items, consumed


def _collect_paragraphs(lines: list[str], kinds: list[str],
                        consumed: set[int]) -> list[dict]:
    """Top-level prose blocks (blank-line separated, zero indent)."""
    paras: list[dict] = []
    i = 0
    n = len(lines)
    while i < n:
        if kinds[i] != "text" or i in consumed or lines[i][:1].isspace():
            i += 1
            continue
        start = i
        buf: list[str] = []
        while i < n and kinds[i] == "text" and i not in consumed:
            buf.append(lines[i].strip())
            i += 1
        paras.append({"line": start + 1, "start": start, "end": i - 1,
                      "text": " ".join(buf)})
    return paras


def _group_runs(entries: list[dict], kinds: list[str], sibling) -> list[list[dict]]:
    """Chain entries into runs of >= MIN_RUN adjacent siblings."""
    runs: list[list[dict]] = []
    current: list[dict] = []
    for entry in entries:
        if current and sibling(current[-1], entry) and _only_blank_between(
                kinds, current[-1]["end"], entry["start"]):
            current.append(entry)
        else:
            if len(current) >= MIN_RUN:
                runs.append(current)
            current = [] if entry.get("skip") else [entry]
    if len(current) >= MIN_RUN:
        runs.append(current)
    return runs


def _deflist_verdict(run: list[dict]) -> str | None:
    """`- **Name** sentence` run where every sentence has near-identical shape
    (rule_anti_slop: per-category narration). Returns the shared shape or None."""
    tails: list[str] = []
    for item in run:
        m = _BOLD_LEAD_RE.match(item["text"])
        if not m or not m.group(2).strip():
            return None
        tails.append(m.group(2).strip())
    if any(len(t) < DEFLIST_TAIL_MIN_CHARS for t in tails):
        return None
    if any(_is_enumeration(t) for t in tails):
        return None
    if _cv([len(t) for t in tails]) > DEFLIST_CV_MAX:
        return None
    firsts = []
    for t in tails:
        toks = _WORD_RE.findall(t)
        if not toks:
            return None
        firsts.append(toks[0].lower())
    skeletons = [_lead_skeleton(t, depth=3) for t in tails]
    if len(set(firsts)) == 1:
        return f"every entry's sentence opens on '{firsts[0]}'"
    if _is_templated(skeletons):
        return f"every entry's sentence matches the skeleton '{skeletons[0]}'"
    return None


def _clustered_verdict(run: list[dict], min_chars: int, cv_max: float) -> str | None:
    """Shared verdict for plain bullet runs and paragraph runs: both length
    clustering AND a shared literal opening template must hold."""
    texts = [e["text"] for e in run]
    if any(len(t) < min_chars for t in texts):
        return None
    if any(_is_enumeration(t) for t in texts):
        return None
    # Narration means sentences. Measure sentence-ness on the body AFTER any
    # bold lead, so `**Complexity flags:** specs, infra, effort, deps` reads as
    # the label-and-items reference row it is, not as three narrated categories.
    for text in texts:
        m = _BOLD_LEAD_RE.match(text)
        if not _is_sentence_shaped(m.group(2).strip() if m else text):
            return None
    lengths = [len(t) for t in texts]
    cv = _cv(lengths)
    if cv > cv_max:
        return None
    skeletons = [_lead_skeleton(t) for t in texts]
    if not _is_templated(skeletons):
        return None
    return (f"lengths cluster (mean {sum(lengths) // len(lengths)} chars, "
            f"variation {cv:.0%}) and every entry opens on the same shape "
            f"'{skeletons[0]}'")


def _split_table_row(raw: str) -> list[str]:
    return [c.strip() for c in raw.strip().strip("|").split("|")]


def _collect_tables(lines: list[str], kinds: list[str]) -> list[list[tuple[int, str]]]:
    tables: list[list[tuple[int, str]]] = []
    i = 0
    while i < len(lines):
        if kinds[i] != "table":
            i += 1
            continue
        block: list[tuple[int, str]] = []
        while i < len(lines) and kinds[i] == "table":
            block.append((i + 1, lines[i]))
            i += 1
        tables.append(block)
    return tables


def _table_hits(block: list[tuple[int, str]]) -> list[dict]:
    """Flag a prose column whose every cell follows one grammar template."""
    delim_at = None
    for idx, (_, raw) in enumerate(block):
        cells = _split_table_row(raw)
        if cells and all(_TABLE_DELIM_CELL_RE.match(c) for c in cells):
            delim_at = idx
            break
    if delim_at is None:
        return []
    header = _split_table_row(block[0][1]) if delim_at > 0 else []
    body = [(ln, _split_table_row(raw)) for ln, raw in block[delim_at + 1:]]
    if len(body) < TABLE_MIN_ROWS:
        return []
    ncols = max((len(c) for _, c in body), default=0)
    hits: list[dict] = []
    for col in range(ncols):
        cells = [c[col] for _, c in body if col < len(c)]
        if len(cells) != len(body):
            continue
        if any(len(c) < TABLE_CELL_MIN_CHARS for c in cells):
            continue
        if any(len(_WORD_RE.findall(c)) < TABLE_CELL_MIN_WORDS for c in cells):
            continue
        if any(not _is_sentence_shaped(c) or _is_enumeration(c) for c in cells):
            continue
        skeletons = [_lead_skeleton(c) for c in cells]
        if not _is_templated(skeletons):
            continue
        label = header[col] if col < len(header) and header[col] else f"column {col + 1}"
        hits.append({
            "line": body[0][0],
            "category": "per-category-narration",
            "severity": "LOW",
            "message": (
                f"Suspected per-category narration: all {len(cells)} body rows of "
                f"column '{label}' open on the same shape '{skeletons[0]}'. "
                "rule_anti_slop 'Per-category narration on intuitive variance': "
                "if one structural rule explains the variance, state it once "
                "instead of giving each row a sentence of the same shape. "
                "Non-obvious operator judgment per row is NOT slop; suppress with "
                "`<!-- output-allow:per-category-narration reason -->`."
            ),
            "snippet": cells[0][:160],
        })
    return hits


def check_structural_slop(text: str) -> list[dict]:
    """symmetry-collapse + per-category-narration over markdown structure."""
    lines = text.splitlines()
    if not lines:
        return []
    kinds = _classify_lines(lines)
    suppress = parse_suppressions(lines)
    hits: list[dict] = []

    bullets, consumed = _collect_bullets(lines, kinds)
    bullet_runs = _group_runs(
        bullets, kinds,
        lambda a, b: (not b["skip"] and not a["skip"]
                      and a["indent"] == b["indent"] and a["marker"] == b["marker"]),
    )
    for run in bullet_runs:
        if _is_sequence_run(run) or _is_question_run(run):
            continue
        deflist = _deflist_verdict(run)
        if deflist:
            hits.append({
                "line": run[0]["line"],
                "category": "per-category-narration",
                "severity": "LOW",
                "message": (
                    f"Suspected per-category narration: {len(run)} consecutive "
                    f"`**Name** sentence` entries and {deflist}. rule_anti_slop "
                    "'Per-category narration on intuitive variance': state the "
                    "structural rule once instead of narrating each entry in the "
                    "same shape. Suppress with "
                    "`<!-- output-allow:per-category-narration reason -->`."
                ),
                "snippet": run[0]["text"][:160],
            })
            continue
        verdict = _clustered_verdict(run, BULLET_MIN_CHARS, BULLET_CV_MAX)
        if verdict:
            hits.append({
                "line": run[0]["line"],
                "category": "symmetry-collapse",
                "severity": "LOW",
                "message": (
                    f"Suspected symmetry slop: {len(run)} sibling bullets where "
                    f"{verdict}. rule_anti_slop 'Three-part lists where two work' "
                    "/ protocol step 2: if the bullets read in the same shape with "
                    "the same information density, collapse them to one statement "
                    "of the underlying rule. Unique information per row is NOT "
                    "slop; suppress with "
                    "`<!-- output-allow:symmetry-collapse reason -->`."
                ),
                "snippet": run[0]["text"][:160],
            })

    paragraphs = _collect_paragraphs(lines, kinds, consumed)
    for run in _group_runs(paragraphs, kinds, lambda a, b: True):
        if _is_sequence_run(run) or _is_question_run(run):
            continue
        verdict = _clustered_verdict(run, PARA_MIN_CHARS, PARA_CV_MAX)
        if verdict:
            hits.append({
                "line": run[0]["line"],
                "category": "symmetry-collapse",
                "severity": "LOW",
                "message": (
                    f"Suspected symmetry slop: {len(run)} consecutive paragraphs "
                    f"where {verdict}. rule_anti_slop protocol step 2 "
                    "(symmetry-collapse): evenly-paced same-shape paragraphs are "
                    "the strongest AI tell. Collapse to the underlying rule, or "
                    "suppress with `<!-- output-allow:symmetry-collapse reason -->`."
                ),
                "snippet": run[0]["text"][:160],
            })

    for block in _collect_tables(lines, kinds):
        hits.extend(_table_hits(block))

    hits = [h for h in hits if h["category"] not in suppress.get(h["line"], set())]
    hits.sort(key=lambda h: h["line"])
    kept: list[dict] = []
    seen: dict[str, int] = {}
    for h in hits:
        n = seen.get(h["category"], 0)
        if n >= MAX_STRUCT_HITS_PER_CATEGORY:
            continue
        seen[h["category"]] = n + 1
        kept.append(h)
    return kept


def check_text(text: str, path: Path | None = None) -> list[dict]:
    """Return list of hit dicts."""
    lines = text.splitlines()
    suppress = parse_suppressions(lines)

    hits: list[dict] = []
    eligible: set[int] = set()

    def scan_line(i: int, line: str) -> None:
        stripped = line.lstrip()
        # Skip blockquoted citations
        if stripped.startswith("> "):
            return
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

    in_fence = False
    last_fence_line = 0
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            last_fence_line = i
            continue
        if in_fence:
            continue
        scan_line(i, line)

    if in_fence and last_fence_line:
        # Unbalanced fence (2026-07-22 blind-spot fix): an opener with no
        # closer used to exempt the whole rest of the file from every rule.
        # The "fence" was decoration, not code — rescan the swallowed tail
        # with fencing disabled, and surface the imbalance itself.
        hits.append({
            "line": last_fence_line,
            "category": "fence-unbalanced",
            "severity": "LOW",
            "message": (
                "Unclosed ``` fence: everything after this line would have "
                "been exempt from all rules. Tail rescanned with fencing "
                "disabled; close the fence if it is a real code block."
            ),
            "snippet": lines[last_fence_line - 1].strip()[:160],
        })
        for i in range(last_fence_line + 1, len(lines) + 1):
            scan_line(i, lines[i - 1])

    # F3: contextual pre-client-message problem-claim gate (needs the
    # +/-2 line window, so it runs after the per-line eligible set is built).
    hits.extend(check_unsourced_claims(lines, suppress, eligible))
    # Cost-anchor drift (register #121, 2026-05-25): needs the file path to
    # locate the client's comms-log.md. Skip when called without a path.
    if path is not None:
        hits.extend(check_cost_anchor(path, lines))
    # Structural slop (symmetry-collapse / per-category-narration): markdown
    # structure only, so gate on a prose suffix. HTML source lines would be
    # read as paragraphs and fire on markup, not prose.
    if path is None or path.suffix.lower() in _STRUCT_SUFFIXES:
        hits.extend(check_structural_slop(text))
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
        loc = f"cell {h['cell']}" if h.get("cell") else f"L{h['line']:4d}"
        print(f"  {loc}  [{sev}] [{h['category']}] {h['message']}")
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
        t = targets[0]
        if is_cell_file(t):
            print(json.dumps(aggregate(check_cells(t))))
            return 0
        try:
            text = t.read_text(encoding="utf-8", errors="replace")
        except OSError:
            print(json.dumps({"total": 0, "hits": [], "by_category": {}, "by_severity": {}}))
            return 0
        payload = aggregate(check_text(text, t))
        print(json.dumps(payload))
        return 0

    # Text mode (multi-file aggregate)
    grand_total = 0
    grand_cat: dict[str, int] = {}
    grand_sev: dict[str, int] = {}
    for path in sorted(set(targets)):
        if is_cell_file(path):
            payload = aggregate(check_cells(path))
        else:
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
