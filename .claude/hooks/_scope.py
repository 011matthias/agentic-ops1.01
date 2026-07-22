"""Canonical path -> category scope predicates for the .claude/hooks layer.

Single source of truth for "which repo location means which category"
(deliverable, comms, human-to-human, protected, reference-anchor). Before
this module the location-segment lists were hand-copied across
post-write-gate, em-dash-strip-gate, reference-anchor-gate and
auto-approve-protected; updating one place silently drifted from the others.
Each hook now imports the predicate it needs.

The per-hook predicates are DELIBERATELY not identical, and the differences
are intentional (kept visible here side-by-side rather than scattered):

- `in_deliverable_scope`  (post-write-gate): extension-gated html/md set,
  runs the deliverable + output validators.
- `in_comms_scope`        (post-write-gate): md-gated drafts/proposals AND
  `comms-log.md`, runs the comms LINTER (advisory) over the sent-message
  record.
- `in_human_to_human_scope` (em-dash-strip-gate): same html/md deliverable
  set + drafts/proposals, but EXCLUDES `comms-log.md` on purpose — that hook
  MUTATES the file (auto-strips em-dashes) and must not rewrite the verbatim
  sent-message record (2026-05-15 scope correction).
- `in_reference_anchor_scope` (reference-anchor-gate): broad, NOT
  extension-gated — fires on any file in a client tree except code/specs/
  context, plus the deliverable + proposal + comms-log segments.
- `in_protected_segment`  (auto-approve-protected): the protected-tree
  membership test (the memory-dir special case stays in that hook).

Pure stdlib, no side effects, importable from a hook run as
`python .claude/hooks/X.py` (the hook directory is sys.path[0]). The
segment data below is the single place to edit when a new deliverable /
comms location is added.
"""
from __future__ import annotations

# --- canonical location segments (the shared data) -------------------------
DELIVERABLE_SEGMENTS = (
    "/platform/public/",
    "/deliverables/",
    "/hero-exports/",
    "/notion-pages/",
    "/doc-site/",
)
PROPOSAL_SEGMENTS = (
    "/platform/src/content/proposals/",
    "/proposals/",
)
COMMS_DRAFT_SEGMENTS = (
    "/context/drafts/",
    "/proposals/",
)
PROTECTED_SEGMENTS = (
    "/.claude/",
    "/tools/",
    "/workspace/",
    "/docs/",
    "/platform/",
)
# reference-anchor fires on a wider net than the deliverable validators.
REFERENCE_ANCHOR_SEGMENTS = DELIVERABLE_SEGMENTS + PROPOSAL_SEGMENTS + ("/comms-log",)

HTML_EXTS = (".html", ".htm")
DOC_EXTS = (".md", ".markdown", ".mdx")
DELIVERABLE_EXTS = HTML_EXTS + DOC_EXTS
# Human-to-human text is frequently plain .txt (Upwork cover letters at
# platform/src/content/proposals/*.txt, plain-text drafts under
# context/drafts/). 2026-07-22 blind-spot fix: .txt bypassed the whole comms
# pipeline because the comms / human-to-human predicates were gated on
# DOC_EXTS / DELIVERABLE_EXTS only.
COMMS_EXTS = DOC_EXTS + (".txt",)
HUMAN_TO_HUMAN_EXTS = DELIVERABLE_EXTS + (".txt",)


def norm(path: str) -> str:
    """Backslash -> forward slash, lowercased. Matches the per-hook
    `normalize_for_match` / `normalize` helpers the segment checks used."""
    return (path or "").replace("\\", "/").lower()


def _any(p: str, segments) -> bool:
    return any(s in p for s in segments)


# --- post-write-gate ------------------------------------------------------
def in_deliverable_scope(path: str) -> bool:
    p = norm(path)
    if not p.endswith(DELIVERABLE_EXTS):
        return False
    return _any(p, DELIVERABLE_SEGMENTS)


def in_comms_scope(path: str) -> bool:
    p = norm(path)
    if not p.endswith(COMMS_EXTS):
        return False
    if "/context/drafts/" in p or "/proposals/" in p:
        return True
    return p.endswith("/comms-log.md")


# --- em-dash-strip-gate (mutating; excludes comms-log.md on purpose) -------
def in_human_to_human_scope(path: str) -> bool:
    p = norm(path)
    if not p.endswith(HUMAN_TO_HUMAN_EXTS):
        return False
    return _any(p, DELIVERABLE_SEGMENTS) or _any(p, COMMS_DRAFT_SEGMENTS)


# --- reference-anchor-gate (broad; not extension-gated) -------------------
def in_reference_anchor_scope(path: str) -> bool:
    p = norm(path)
    if not p:
        return False
    if ("workspace/clients/" in p and "/automations/" not in p
            and "/specs/" not in p and "/context/" not in p):
        return True
    return _any(p, REFERENCE_ANCHOR_SEGMENTS)


# --- auto-approve-protected (segment membership; memory-dir case in-hook) --
def in_protected_segment(path: str) -> bool:
    p = (path or "").replace("\\", "/")  # NOT lowercased — matches the original
    if _any(p, PROTECTED_SEGMENTS):
        return True
    return p.startswith((".claude/", "tools/", "workspace/", "docs/", "platform/"))
