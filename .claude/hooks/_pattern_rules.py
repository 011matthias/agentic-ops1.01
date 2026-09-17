#!/usr/bin/env python3
"""Shared library for declarative pattern rules (`.claude/patterns/*.md`).

WHY THIS EXISTS
---------------
Promoting a fragile memory-only fix to a structural control used to mean a new
Python hook, a pytest module, and a wire-hooks change: a half-day of work, so
most promotions never happened (friction register: 104 rows fixed as
"documented", 17 as "memory", against 25 hooks). A pattern rule is a markdown
file with an event, a regex, and an action, read by ONE generic hook
(`pattern-rules-gate.py`). A checkpoint can promote a regex-shaped lesson in
minutes. Ported from ECC's hookify rules, mechanism only.

This module is the single source of truth for the rule format, shared by the
hook (runtime) and `tools/pattern_rules.py` (new / lint / list / test / digest).
Stdlib only, because hooks run under the bare interpreter. The `_` prefix keeps
it out of the hook-registry disk scan (tools/tests/test_hooks_registry.py).

RULE FILE
---------
    ---
    name: warn-git-add-all            # verb-first: warn-* / block-* / require-*
    enabled: true
    event: bash                       # bash | file | stop | prompt
    pattern: '\\bgit\\s+add\\s+(-A|--all|\\.)'   # or conditions: (below)
    action: warn                      # warn | ask | block
    message: One-line headline shown first.
    source: feedback_worktree_for_concurrent_sessions   # register row or memory slug
    created: 2026-09-17
    ---
    Body: the guidance shown to the agent under the headline.

`conditions:` replaces `pattern:` when more than one field must match; every
condition must match (AND):

    conditions:
      - field: file_path
        operator: regex_match
        pattern: '(/context/drafts/|comms-log\\.md$)'
      - field: new_text
        operator: regex_match
        pattern: '(?i)happy to lower'

Fields per event: bash `command` (normalized by _shell.py); file `file_path`,
`new_text` (Write content / Edit new_string), `old_text`; prompt `user_prompt`;
stop `final_text`. Prompt and stop text have code and short quoted spans
stripped first (stop-b1-gate's strip_code) so a rule never fires on its own
trigger phrase quoted as an example.

Quoting: single quotes keep backslashes literal ('\\s' is regex \\s). Unquoted
values are literal too. Double quotes unescape only \\\\ and \\".
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

EVENTS = ("bash", "file", "stop", "prompt")
ACTIONS = ("warn", "ask", "block")
NAME_PREFIXES = ("warn-", "block-", "require-")

EVENT_FIELDS = {
    "bash": ("command",),
    "file": ("file_path", "new_text", "old_text"),
    "prompt": ("user_prompt",),
    "stop": ("final_text",),
}
# `pattern:` shorthand matches this field.
DEFAULT_FIELD = {
    "bash": "command",
    "file": "new_text",
    "prompt": "user_prompt",
    "stop": "final_text",
}
# Spellings authors reach for, folded onto the canonical field.
FIELD_ALIASES = {
    "content": "new_text",
    "new_string": "new_text",
    "old_string": "old_text",
    "prompt": "user_prompt",
    "text": None,  # resolves to the event's DEFAULT_FIELD
}
OPERATORS = (
    "regex_match", "not_regex_match", "contains", "not_contains",
    "equals", "starts_with", "ends_with",
)
# An action the event cannot express. Stop has no permission prompt and a
# prompt cannot be "asked" about, so these are lint errors, not silent
# downgrades an author would never notice.
UNSUPPORTED = {("stop", "ask"), ("prompt", "ask")}

REQUIRED = ("name", "enabled", "event", "action", "message", "source", "created")
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# A register row reference ("2026-05-19 strategic-gap") or a memory slug.
_SOURCE_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}\s+[a-z][a-z-]+)|(\b(?:feedback|project|reference|user)_[a-z0-9_]+)"
)

ALLOW_MARKER = "pattern-allow:"


class RuleError(ValueError):
    """A rule file that cannot be parsed or is structurally invalid."""


@dataclass
class Condition:
    field: str
    operator: str
    pattern: str
    compiled: re.Pattern | None = None

    def matches(self, value: str) -> bool:
        v = value or ""
        op = self.operator
        if op == "regex_match":
            return bool(self.compiled.search(v))
        if op == "not_regex_match":
            return not self.compiled.search(v)
        if op == "contains":
            return self.pattern in v
        if op == "not_contains":
            return self.pattern not in v
        if op == "equals":
            return v == self.pattern
        if op == "starts_with":
            return v.startswith(self.pattern)
        if op == "ends_with":
            return v.endswith(self.pattern)
        return False


@dataclass
class Rule:
    path: str
    meta: dict
    body: str
    conditions: list = field(default_factory=list)

    @property
    def name(self) -> str:
        return str(self.meta.get("name", ""))

    @property
    def enabled(self) -> bool:
        return self.meta.get("enabled") is True

    @property
    def event(self) -> str:
        return str(self.meta.get("event", ""))

    @property
    def action(self) -> str:
        return str(self.meta.get("action", "warn"))

    @property
    def message(self) -> str:
        return str(self.meta.get("message", ""))

    def matches(self, fields: dict) -> bool:
        if not self.conditions:
            return False
        return all(c.matches(fields.get(c.field, "")) for c in self.conditions)

    def render(self) -> str:
        text = f"[PATTERN {self.action.upper()}: {self.name}] {self.message}"
        if self.body.strip():
            text += "\n" + self.body.strip()
        return text


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------
def _scalar(raw: str):
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] == "'":
        return s[1:-1].replace("''", "'")
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if s == "true":
        return True
    if s == "false":
        return False
    return s


def _split_kv(line: str, lineno: int) -> tuple[str, str]:
    if ":" not in line:
        raise RuleError(f"line {lineno}: expected 'key: value', got {line.strip()!r}")
    key, _, val = line.partition(":")
    key = key.strip()
    if not re.match(r"^[a-z_]+$", key):
        raise RuleError(f"line {lineno}: invalid key {key!r}")
    return key, val


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse the YAML subset rule files use: top-level scalars plus one level
    of list-of-mappings (for `conditions:`). Returns (meta, body)."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise RuleError("missing opening '---' frontmatter fence")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise RuleError("missing closing '---' frontmatter fence") from None

    meta: dict = {}
    current_list: list | None = None
    current_item: dict | None = None
    for idx in range(1, end):
        line = lines[idx]
        lineno = idx + 1
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            key, val = _split_kv(line, lineno)
            if key in meta:
                raise RuleError(f"line {lineno}: duplicate key {key!r}")
            if val.strip() == "":
                current_list = []
                current_item = None
                meta[key] = current_list
            else:
                meta[key] = _scalar(val)
                current_list = None
                current_item = None
            continue
        if current_list is None:
            raise RuleError(f"line {lineno}: indented line outside a list")
        stripped = line.strip()
        if stripped.startswith("- "):
            current_item = {}
            current_list.append(current_item)
            stripped = stripped[2:]
        elif current_item is None:
            raise RuleError(f"line {lineno}: list item must start with '- '")
        key, val = _split_kv(stripped, lineno)
        if key in current_item:
            raise RuleError(f"line {lineno}: duplicate key {key!r} in list item")
        current_item[key] = _scalar(val)
    body = "\n".join(lines[end + 1:]).strip("\n")
    return meta, body


def _resolve_field(name: str, event: str) -> str:
    if name in FIELD_ALIASES:
        alias = FIELD_ALIASES[name]
        return alias if alias is not None else DEFAULT_FIELD.get(event, name)
    return name


def build_rule(path: str, text: str) -> Rule:
    """Parse + compile. Raises RuleError when the rule cannot be evaluated.
    (Style problems that do not stop evaluation are lint findings instead.)"""
    meta, body = parse_frontmatter(text)
    event = str(meta.get("event", ""))
    if event not in EVENTS:
        raise RuleError(f"event must be one of {EVENTS}, got {event!r}")
    has_pattern = "pattern" in meta
    has_conditions = "conditions" in meta
    if has_pattern == has_conditions:
        raise RuleError("exactly one of 'pattern' or 'conditions' is required")
    raw_conditions = (
        [{"field": DEFAULT_FIELD[event], "operator": "regex_match", "pattern": meta["pattern"]}]
        if has_pattern else meta["conditions"]
    )
    if not isinstance(raw_conditions, list) or not raw_conditions:
        raise RuleError("'conditions' must be a non-empty list")
    conditions = []
    for i, c in enumerate(raw_conditions, 1):
        if not isinstance(c, dict):
            raise RuleError(f"condition {i}: must be a mapping")
        fld = _resolve_field(str(c.get("field", "")), event)
        op = str(c.get("operator", "regex_match"))
        pat = c.get("pattern")
        if fld not in EVENT_FIELDS[event]:
            raise RuleError(
                f"condition {i}: field {fld!r} is not available for event {event!r} "
                f"(have {EVENT_FIELDS[event]})"
            )
        if op not in OPERATORS:
            raise RuleError(f"condition {i}: operator {op!r} not in {OPERATORS}")
        if not isinstance(pat, str) or pat == "":
            raise RuleError(f"condition {i}: 'pattern' must be a non-empty string")
        compiled = None
        if op in ("regex_match", "not_regex_match"):
            try:
                compiled = re.compile(pat, re.MULTILINE)
            except re.error as exc:
                raise RuleError(f"condition {i}: regex does not compile: {exc}") from None
        conditions.append(Condition(fld, op, pat, compiled))
    return Rule(path=path, meta=meta, body=body, conditions=conditions)


def rules_dir(repo_root: str) -> str:
    return os.environ.get("PATTERN_RULES_DIR") or os.path.join(repo_root, ".claude", "patterns")


def load_rules(directory: str) -> tuple[list[Rule], list[tuple[str, str]]]:
    """Every *.md rule in `directory` (README.md excluded). Returns
    (rules, errors); a malformed file lands in errors and is skipped."""
    rules: list[Rule] = []
    errors: list[tuple[str, str]] = []
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return rules, errors
    for fname in names:
        if not fname.endswith(".md") or fname.lower() == "readme.md":
            continue
        path = os.path.join(directory, fname)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                rules.append(build_rule(path, fh.read()))
        except (OSError, UnicodeDecodeError, RuleError) as exc:
            errors.append((path, str(exc)))
    return rules, errors


# --------------------------------------------------------------------------
# Lint
# --------------------------------------------------------------------------
def lint_rule(rule: Rule) -> list[str]:
    """Findings that do not stop evaluation but break the contract."""
    out: list[str] = []
    m = rule.meta
    for key in REQUIRED:
        if key not in m or m[key] in ("", None):
            out.append(f"missing required field {key!r}")
    known = set(REQUIRED) | {"pattern", "conditions"}
    for key in m:
        if key not in known:
            out.append(f"unknown field {key!r}")
    name = rule.name
    if name and not _NAME_RE.match(name):
        out.append(f"name {name!r} must be kebab-case")
    if name and not name.startswith(NAME_PREFIXES):
        out.append(f"name {name!r} must be verb-first ({', '.join(NAME_PREFIXES)})")
    stem = os.path.splitext(os.path.basename(rule.path))[0]
    if name and stem != name:
        out.append(f"filename stem {stem!r} must equal name {name!r}")
    if "enabled" in m and not isinstance(m["enabled"], bool):
        out.append("enabled must be true or false")
    action = m.get("action")
    if action not in ACTIONS:
        out.append(f"action must be one of {ACTIONS}, got {action!r}")
    if (rule.event, action) in UNSUPPORTED:
        out.append(
            f"action {action!r} is not expressible on event {rule.event!r} "
            "(stop: use block or warn; prompt: use block or warn)"
        )
    if name.startswith("warn-") and action != "warn":
        out.append(f"warn-* rule must use action warn, got {action!r}")
    if name.startswith("block-") and action != "block":
        out.append(f"block-* rule must use action block, got {action!r}")
    created = m.get("created")
    if created and not _DATE_RE.match(str(created)):
        out.append(f"created must be YYYY-MM-DD, got {created!r}")
    source = m.get("source")
    if source and not _SOURCE_RE.search(str(source)):
        out.append(
            "source must name a register row ('YYYY-MM-DD type') or a memory slug "
            f"(feedback_/project_/reference_/user_), got {source!r}"
        )
    if not rule.body.strip():
        out.append("body (the guidance shown to the agent) is empty")
    return out


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------
_ORDER = {"warn": 1, "ask": 2, "block": 3}


def evaluate(rules: list[Rule], event: str, fields: dict) -> list[Rule]:
    """Enabled rules for `event` whose conditions all match `fields`. A file
    event whose new text carries `pattern-allow:<name>` suppresses that rule
    (visible in the artifact, so a reviewer sees every suppression)."""
    hits = []
    allow_text = fields.get("new_text", "") if event == "file" else ""
    for rule in rules:
        if not rule.enabled or rule.event != event:
            continue
        if allow_text and f"{ALLOW_MARKER}{rule.name}" in allow_text.replace(" ", ""):
            continue
        if rule.matches(fields):
            hits.append(rule)
    return hits


def strongest(hits: list[Rule]) -> str | None:
    if not hits:
        return None
    return max((h.action for h in hits), key=lambda a: _ORDER.get(a, 0))
