# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Author, lint, list and test declarative pattern rules (`.claude/patterns/`).

The runtime is `.claude/hooks/pattern-rules-gate.py`; the format and matcher
are `.claude/hooks/_pattern_rules.py` (imported here, so the CLI and the hook
can never disagree about what a rule means).

Subcommands:
  new NAME --event E --pattern P --message M --source S [--action A] [--body B]
      Write `.claude/patterns/NAME.md`, then lint it. Refuses an existing file.
      Action defaults from the name prefix (warn-* -> warn, block-* -> block).
  lint [FILE ...]
      Parse + contract-check every rule (or the named files). Exit 1 on any
      finding. CI runs this (ci.yml hooks job, mirrored in preflight-hooks.py).
  list
      One row per rule: name, enabled, event, action, source.
  test --text T [--event E] [--file-path P] [--rule NAME]
      Show which enabled rules fire on T. For the file event, T is the new text
      and --file-path the target. Prompt/stop text is code-stripped exactly as
      the hook strips it. Exit 0 whether or not anything matched.
  digest --session UUID [--transcript PATH] [--max-chars N]
      Compact, deterministic extract of a session transcript for the
      /comd_checkpoint rule miner: every user turn (tool results and injected
      reminders dropped), each preceded by the tail of the agent text it
      answered, with likely corrections flagged `*`. Prints
      "transcript unavailable" and exits 0 when the file cannot be found, so
      the checkpoint step switches itself off.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOKS = REPO / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))
import _pattern_rules as pr  # noqa: E402


def _dir() -> Path:
    return Path(pr.rules_dir(str(REPO)))


def _strip_code(text: str) -> str:
    spec = importlib.util.spec_from_file_location("stop_b1_gate_cli", HOOKS / "stop-b1-gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.strip_code(text)


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


# --------------------------------------------------------------------- new
def cmd_new(args) -> int:
    name = args.name
    action = args.action or ("block" if name.startswith("block-") else "warn")
    path = _dir() / f"{name}.md"
    if path.exists():
        print(f"refusing: {path} already exists", file=sys.stderr)
        return 1
    body = args.body or "Explain what went wrong, when, and what to do instead."
    text = (
        "---\n"
        f"name: {name}\n"
        "enabled: true\n"
        f"event: {args.event}\n"
        f"action: {action}\n"
        f"message: {args.message}\n"
        f"source: {args.source}\n"
        f"created: {date.today().isoformat()}\n"
        f"pattern: {_quote(args.pattern)}\n"
        "---\n"
        f"{body}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")
    return lint_paths([path])


# -------------------------------------------------------------------- lint
def lint_paths(paths: list[Path]) -> int:
    findings = 0
    names: dict[str, Path] = {}
    for path in paths:
        try:
            rule = pr.build_rule(str(path), path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, pr.RuleError) as exc:
            print(f"FAIL {path.name}: {exc}")
            findings += 1
            continue
        problems = pr.lint_rule(rule)
        if rule.name in names:
            problems.append(f"duplicate name, also in {names[rule.name].name}")
        names[rule.name] = path
        for p in problems:
            print(f"FAIL {path.name}: {p}")
        findings += len(problems)
    print(f"pattern-rules lint: {len(paths)} rule(s), {findings} finding(s)")
    return 1 if findings else 0


def cmd_lint(args) -> int:
    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        d = _dir()
        paths = sorted(p for p in d.glob("*.md") if p.name.lower() != "readme.md") if d.is_dir() else []
    return lint_paths(paths)


# -------------------------------------------------------------------- list
def cmd_list(args) -> int:
    rules, errors = pr.load_rules(str(_dir()))
    print(f"{'name':40} {'on':3} {'event':6} {'action':6} source")
    for r in rules:
        print(f"{r.name:40} {'y' if r.enabled else 'n':3} {r.event:6} {r.action:6} "
              f"{r.meta.get('source', '')}")
    for path, err in errors:
        print(f"MALFORMED {os.path.basename(path)}: {err}")
    return 0


# -------------------------------------------------------------------- test
def cmd_test(args) -> int:
    rules, errors = pr.load_rules(str(_dir()))
    for path, err in errors:
        print(f"MALFORMED {os.path.basename(path)}: {err}")
    if args.rule:
        rules = [r for r in rules if r.name == args.rule]
        if not rules:
            print(f"no rule named {args.rule!r}", file=sys.stderr)
            return 1
    events = [args.event] if args.event else list(pr.EVENTS)
    any_hit = False
    for event in events:
        if event == "file":
            fields = {"file_path": (args.file_path or "").replace("\\", "/"),
                      "new_text": args.text, "old_text": ""}
        elif event in ("prompt", "stop"):
            fields = {pr.DEFAULT_FIELD[event]: _strip_code(args.text)}
        else:
            from _shell import normalize_command
            fields = {"command": normalize_command(args.text)}
        for hit in pr.evaluate(rules, event, fields):
            any_hit = True
            print(f"MATCH [{event}] {hit.name} -> {hit.action}")
    if not any_hit:
        print("no match")
    return 0


# ------------------------------------------------------------------ digest
_CUES = re.compile(
    r"\b(no|nope|don'?t|do not|stop|wrong|not what|i said|again|revert|undo|"
    r"why did you|instead|never|nicht|falsch|nein)\b",
    re.IGNORECASE,
)


def find_transcript(session: str) -> Path | None:
    projects = Path.home() / ".claude" / "projects"
    if not projects.is_dir():
        return None
    for p in projects.glob(f"*/{session}.jsonl"):
        return p
    return None


def _user_text(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        text = "\n".join(parts)
    else:
        return ""
    # Harness-injected context is not the user speaking.
    text = re.sub(r"<system-reminder>.*?</system-reminder>", " ", text, flags=re.S)
    text = re.sub(r"<(command-[a-z-]+|local-command-[a-z-]+|task-notification)>.*?</\1>",
                  " ", text, flags=re.S)
    return text.strip()


def digest(path: Path, max_chars: int) -> str:
    out: list[str] = []
    last_agent = ""
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            msg = obj.get("message") if isinstance(obj, dict) else None
            if not isinstance(msg, dict):
                continue
            role = obj.get("type") or msg.get("role")
            if role == "assistant":
                content = msg.get("content")
                if isinstance(content, list):
                    text = "\n".join(b.get("text", "") for b in content
                                     if isinstance(b, dict) and b.get("type") == "text")
                    if text.strip():
                        last_agent = text.strip()
            elif role == "user" and not obj.get("isMeta"):
                text = _user_text(msg)
                if not text:
                    continue
                flag = "*" if _CUES.search(text) else " "
                agent_tail = " ".join(last_agent.split())[-300:]
                out.append(f"--\n  agent: ...{agent_tail}\n{flag} user: {' '.join(text.split())[:600]}")
    body = "\n".join(out)
    if len(body) > max_chars:
        body = "[earlier turns truncated]\n" + body[-max_chars:]
    return body


def cmd_digest(args) -> int:
    path = Path(args.transcript) if args.transcript else find_transcript(args.session)
    if not path or not path.is_file():
        print("transcript unavailable")
        return 0
    print(digest(path, args.max_chars))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new")
    n.add_argument("name")
    n.add_argument("--event", required=True, choices=pr.EVENTS)
    n.add_argument("--pattern", required=True)
    n.add_argument("--message", required=True)
    n.add_argument("--source", required=True)
    n.add_argument("--action", choices=pr.ACTIONS)
    n.add_argument("--body")
    n.set_defaults(func=cmd_new)

    li = sub.add_parser("lint")
    li.add_argument("files", nargs="*")
    li.set_defaults(func=cmd_lint)

    ls = sub.add_parser("list")
    ls.set_defaults(func=cmd_list)

    t = sub.add_parser("test")
    t.add_argument("--text", required=True)
    t.add_argument("--event", choices=pr.EVENTS)
    t.add_argument("--file-path")
    t.add_argument("--rule")
    t.set_defaults(func=cmd_test)

    d = sub.add_parser("digest")
    d.add_argument("--session", default="")
    d.add_argument("--transcript")
    d.add_argument("--max-chars", type=int, default=40_000)
    d.set_defaults(func=cmd_digest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
