# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Deterministic half of /comd_checkpoint.

Collapses the mechanical checkpoint steps (folder, session log, INDEX row,
context YAML merge, friction-register append, pre-flight data gathering) into
two calls so the agent only authors the judgment content (Checkpoint.md prose
and friction classification). Big ledger files are edited string-level here and
never need to be loaded into agent context.

Subcommands:
  pre               Read-only gathering: target paths, friction candidates,
                    ops status, comms staleness, project-status check,
                    register size advisory + optional type grep.
  finalize          Apply a JSON payload: create folder, bump + append the
                    session log, insert the INDEX row, merge the context YAML,
                    append friction-register rows. Prints the confirm line.
  archive-register  Move resolved rows older than --days to
                    docs/friction-register-archive.md.

Payload shape for finalize (--payload FILE, or '-' for stdin):
{
  "topic": "Topic Name",                  // required
  "date": "YYYY-MM-DD",                   // optional, default today
  "work_type": "client-dev",              // required
  "section": "brisken",                   // INDEX section; default from work_type
  "mini": false,
  "projects": ["brisken"],
  "entry": {"focus": "...", "built": "...", "friction": "None",
             "gates": "B1:1 B2:1 B3:0 skipped:0",
             "autonomy": "0 human interventions", "outcome": "..."},
  "friction_rows": [{"client": "x", "type": "slow-path", "desc": "...",
                      "resolved": "No", "fix": "structural",
                      "regression": "No"}],
  "yaml_clients": {"brisken": {"orchestrator": "fastapi", ...}}
}
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

REGISTER_ADVISORY_BYTES = 200_000
ARCHIVE_HEADER = """# Friction Register — Archive

Resolved rows older than the active window, moved out of
`docs/friction-register.md` by `tools/checkpoint_scaffold.py archive-register`.
Same column format. The active register holds the live working set; this file
is the historical record (grep it the same way).

| Date | Client | Type | Description | Resolved? | Fix |
|------|--------|------|-------------|-----------|-----|
"""

SESSION_ENTRY_FIELDS = [
    ("focus", "Focus"),
    ("projects_line", "Projects"),
    ("built", "Built"),
    ("friction", "Friction"),
    ("gates", "Gates"),
    ("autonomy", "Autonomy"),
    ("outcome", "Outcome"),
]


def _utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def today() -> str:
    return dt.date.today().isoformat()


def folder_for(root: Path, date: str, topic: str) -> Path:
    return root / "docs" / f"{date} - {topic}"


def checkpoint_filename(folder: Path, mini: bool) -> str:
    if not mini:
        return "Checkpoint.md"
    n = len(list(folder.glob("Mini-Checkpoint-*.md"))) + 1 if folder.exists() else 1
    return f"Mini-Checkpoint-{n}.md"


def encode_link(path: str) -> str:
    return quote(path, safe="/")


def sanitize_cell(text: str) -> str:
    return " ".join(str(text).replace("|", "\\|").split())


# ---------------------------------------------------------------- session log


def _parse_flow_list(raw: str) -> list[str]:
    inner = raw.strip().lstrip("[").rstrip("]").strip()
    return [x.strip() for x in inner.split(",") if x.strip()] if inner else []


def update_session_log(root: Path, payload: dict) -> tuple[int, Path]:
    """Bump frontmatter counters and append the session entry. Returns (N, path)."""
    date = payload["date"]
    path = root / "docs" / "sessions" / f"{date}.md"
    projects = payload.get("projects", [])
    work_type = payload["work_type"]
    friction_n = len(payload.get("friction_rows", []))

    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = (
            f"---\ndate: {date}\nsessions: 0\nprojects_touched: []\n"
            f"friction_events: 0\nwork_types: []\n---\n"
        )

    def bump_count(m: re.Match) -> str:
        return f"{m.group(1)}{int(m.group(2)) + (1 if m.group(1).startswith('sessions') else friction_n)}"

    m = re.search(r"^sessions:\s*(\d+)", text, re.M)
    n = (int(m.group(1)) if m else 0) + 1
    text = re.sub(r"^(sessions:\s*)(\d+)", bump_count, text, count=1, flags=re.M)
    text = re.sub(r"^(friction_events:\s*)(\d+)", bump_count, text, count=1, flags=re.M)

    for key, additions in (("projects_touched", projects), ("work_types", [work_type])):
        lm = re.search(rf"^{key}:\s*(\[.*\])\s*$", text, re.M)
        if lm:
            merged = _parse_flow_list(lm.group(1))
            merged += [a for a in additions if a not in merged]
            text = text[: lm.start(1)] + "[" + ", ".join(merged) + "]" + text[lm.end(1):]

    entry = payload.get("entry", {})
    heading_suffix = " (mini)" if payload.get("mini") else ""
    lines = [f"\n### Session {n} — {payload['topic']}{heading_suffix}", f"**Type:** {work_type}"]
    entry = {**entry, "projects_line": ", ".join(projects)} if projects else dict(entry)
    for key, label in SESSION_ENTRY_FIELDS:
        if entry.get(key):
            lines.append(f"**{label}:** {entry[key]}")
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n".join(lines) + "\n", encoding="utf-8")
    return n, path


# ------------------------------------------------------------------ INDEX row


def insert_index_row(root: Path, payload: dict, link_text: str, link_target: str) -> Path:
    path = root / "docs" / "INDEX.md"
    section = payload.get("section") or (
        "system" if payload["work_type"] == "system-infra" else (payload.get("projects") or ["system"])[0]
    )
    row = f"| {payload['date']} | {payload['topic']} | {payload['work_type']} | [{link_text}]({link_target}) |"

    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = "# Session Index\n\n_Auto-updated by /comd_checkpoint. Most recent first within each section._\n"

    heading = f"## {section}"
    lines = text.splitlines()
    out, inserted, i = [], False, 0
    while i < len(lines):
        out.append(lines[i])
        if not inserted and lines[i].strip() == heading:
            # copy through the table header + separator, then insert
            j = i + 1
            while j < len(lines) and (lines[j].startswith("| Date") or lines[j].startswith("|--") or not lines[j].strip()):
                out.append(lines[j])
                j += 1
            out.append(row)
            i = j
            inserted = True
            continue
        i += 1
    if not inserted:
        if out and out[-1].strip():
            out.append("")
        out += [heading, "| Date | Topic | Type | Link |", "|------|-------|------|------|", row]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------- context YAML


def _yaml():
    try:
        import yaml

        return yaml
    except ImportError:
        return None


def load_context_text(text: str) -> dict:
    """Parse the context file: YAML when pyyaml is present, else JSON (a YAML subset)."""
    y = _yaml()
    if y is not None:
        return y.safe_load(text) or {}
    return json.loads(text)


def dump_context(data: dict) -> str:
    y = _yaml()
    if y is not None:
        return y.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main_worktree(root: Path) -> Path:
    """The primary clone's path for a git working tree.

    The gitignored context YAML must live in the primary clone (where /resume
    reads it), never a throwaway linked worktree that gets removed after the
    checkpoint's docs PR merges. When `root` is a linked worktree, git's
    common-dir is `<primary>/.git`, so the primary clone is its parent.
    Fail-open to `root` on any git error (non-repo, git absent, submodule .git
    file) so finalize never dies on this.
    """
    try:
        common = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=15,
        )
        if common.returncode != 0 or not common.stdout.strip():
            return root
        common_dir = Path(common.stdout.strip())
        # common_dir is <primary>/.git (or <primary>/.git/ ...); primary is its parent
        primary = common_dir.parent if common_dir.name == ".git" else root
        return primary if (primary / "docs" / "sessions").is_dir() else root
    except Exception:
        return root


def merge_context_yaml(root: Path, payload: dict, checkpoint_rel: str, context_root: Path | None = None) -> Path:
    base = context_root or root
    path = base / "docs" / "sessions" / f"{payload['date']}-context.yaml"
    data: dict = {}
    if path.exists():
        try:
            data = load_context_text(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"WARN: existing context YAML unparseable ({e}); rewriting fresh")
            data = {}
    data.update(
        checkpoint_date=payload["date"],
        checkpoint_topic=payload["topic"],
        checkpoint_file=checkpoint_rel,
        work_type=payload["work_type"],
    )
    clients = data.setdefault("clients", {})
    for cid, fragment in (payload.get("yaml_clients") or {}).items():
        base = clients.get(cid) or {}
        base.update(fragment)
        clients[cid] = base
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_context(data), encoding="utf-8")
    return path


# ------------------------------------------------------------------- register


def append_register_rows(root: Path, payload: dict) -> Path | None:
    rows = payload.get("friction_rows") or []
    if not rows:
        return None
    path = root / "docs" / "friction-register.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    for r in rows:
        text += (
            f"| {payload['date']} | {sanitize_cell(r.get('client', ''))} | "
            f"{sanitize_cell(r.get('type', ''))} | {sanitize_cell(r.get('desc', ''))} | "
            f"{sanitize_cell(r.get('resolved', 'No'))} | {sanitize_cell(r.get('fix', ''))} | "
            f"{sanitize_cell(r.get('regression', 'No'))} |\n"
        )
    path.write_text(text, encoding="utf-8")
    return path


DATA_ROW = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*(?<!\\)\|")


def archive_register(root: Path, days: int) -> int:
    path = root / "docs" / "friction-register.md"
    if not path.exists():
        print("no friction-register.md")
        return 1
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    keep, move = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = DATA_ROW.match(line)
        if m and m.group(1) < cutoff:
            cells = re.split(r"(?<!\\)\|", line)
            resolved = cells[5].strip() if len(cells) > 6 else ""
            if resolved.startswith("Yes"):
                move.append(line)
                continue
        keep.append(line)
    if not move:
        print(f"nothing to archive (cutoff {cutoff})")
        return 0
    archive = root / "docs" / "friction-register-archive.md"
    atext = archive.read_text(encoding="utf-8") if archive.exists() else ARCHIVE_HEADER
    if not atext.endswith("\n"):
        atext += "\n"
    archive.write_text(atext + "\n".join(move) + "\n", encoding="utf-8")
    path.write_text("\n".join(keep) + "\n", encoding="utf-8")
    print(
        f"archived {len(move)} resolved rows older than {cutoff} -> "
        f"{archive.name}; register now {path.stat().st_size:,} bytes"
    )
    return 0


# ------------------------------------------------------------------------ pre


def _run(cmd: list[str], cwd: Path) -> str:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=60)
        return (p.stdout or "").strip() or (p.stderr or "").strip() or "(no output)"
    except Exception as e:
        return f"unavailable: {e}"


def cmd_pre(root: Path, args: argparse.Namespace) -> int:
    date = args.date or today()
    if args.topic:
        folder = folder_for(root, date, args.topic)
        fname = checkpoint_filename(folder, args.mini)
        print("== target ==")
        print(f"write checkpoint prose to: {folder / fname}")

    print("\n== friction candidates (classify: promote or discard; then --clear-candidates) ==")
    print(_run(["uv", "run", "tools/session_state.py", "--list-candidates"], root))

    for client in args.clients or []:
        cdir = root / "workspace" / "clients" / client
        print(f"\n== {client} ==")
        infra = cdir / "infrastructure.yaml"
        if infra.exists():
            try:
                y = _yaml()
                if y is None:
                    raise RuntimeError("pyyaml unavailable")
                plat = (y.safe_load(infra.read_text(encoding="utf-8")) or {}).get("platform")
                if plat:
                    print(f"platform: {plat.get('tier', '?')} plan, "
                          f"~{plat.get('estimated_ops', '?')}/{plat.get('ops_limit', '?')} ops/mo. "
                          f"Last assessed: {plat.get('last_assessed', '?')}.")
                else:
                    print("platform: no `platform` section in infrastructure.yaml")
            except Exception as e:
                print(f"platform: infrastructure.yaml unreadable ({e})")
        else:
            print("platform: no infrastructure.yaml")
        comms = cdir / "context" / "comms-log.md"
        if comms.exists():
            age = (dt.date.today() - dt.date.fromtimestamp(comms.stat().st_mtime)).days
            print(f"comms-log: last touched {age} day(s) ago"
                  + (" — STALE, ask about unlogged conversations" if age >= 4 else ""))
        else:
            print("comms-log: none")
        if (cdir / "status").exists():
            print(_run(["uv", "run", "tools/project_status.py", "--client", client, "--check"], root))

    reg = root / "docs" / "friction-register.md"
    if reg.exists():
        size = reg.stat().st_size
        print(f"\n== register ==\nfriction-register.md: {size:,} bytes")
        if size > REGISTER_ADVISORY_BYTES:
            print("ADVISORY: register exceeds 200 KB — run "
                  "`uv run tools/checkpoint_scaffold.py archive-register` in this checkpoint's docs PR")
        if args.register_types:
            wanted = [t.strip() for t in args.register_types.split(",") if t.strip()]
            hits = [ln for ln in reg.read_text(encoding="utf-8").splitlines()
                    if any(f"| {t} |" in ln for t in wanted)]
            print(f"regression check — last rows matching {wanted}:")
            for ln in hits[-8:]:
                print(ln[:400])
    return 0


# ------------------------------------------------------------------- finalize


def cmd_finalize(root: Path, args: argparse.Namespace) -> int:
    raw = sys.stdin.read() if args.payload == "-" else Path(args.payload).read_text(encoding="utf-8")
    payload = json.loads(raw)
    for field in ("topic", "work_type"):
        if not payload.get(field):
            print(f"payload missing required field: {field}")
            return 2
    payload.setdefault("date", today())

    folder = folder_for(root, payload["date"], payload["topic"])
    folder.mkdir(parents=True, exist_ok=True)
    fname = checkpoint_filename(folder, payload.get("mini", False))
    rel = f"docs/{payload['date']} - {payload['topic']}/{fname}"

    ctx_root = Path(args.context_root).resolve() if args.context_root else main_worktree(root)

    n, log_path = update_session_log(root, payload)
    link_text = fname.removesuffix(".md") if payload.get("mini") else "→"
    index_path = insert_index_row(root, payload, link_text, encode_link(rel))
    yaml_path = merge_context_yaml(root, payload, rel, context_root=ctx_root)
    reg_path = append_register_rows(root, payload)

    print(f"session entry #{n} appended: {log_path}")
    print(f"INDEX row inserted: {index_path}")
    note = "" if ctx_root == root else f"  (primary clone, not the worktree {root.name})"
    print(f"context YAML merged: {yaml_path}{note}")
    if reg_path:
        print(f"friction rows appended: {reg_path} ({len(payload['friction_rows'])})")
    prose = folder / fname
    print(f"checkpoint prose file: {prose}" + ("" if prose.exists() else "  (NOT WRITTEN YET — write it now)"))
    kind = "Mini-checkpoint" if payload.get("mini") else "Checkpoint"
    print(f"confirm line: {kind} saved → [{fname}]({encode_link(rel)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    ap = argparse.ArgumentParser(description="Deterministic half of /comd_checkpoint.")
    ap.add_argument("--root", default=".", help="repo root (tests)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_pre = sub.add_parser("pre", help="read-only pre-checkpoint gathering")
    p_pre.add_argument("--clients", nargs="*", default=[])
    p_pre.add_argument("--topic")
    p_pre.add_argument("--date")
    p_pre.add_argument("--mini", action="store_true")
    p_pre.add_argument("--register-types", help="comma-separated friction types for the regression grep")

    p_fin = sub.add_parser("finalize", help="apply the checkpoint payload to the ledgers")
    p_fin.add_argument("--payload", required=True, help="JSON file, or '-' for stdin")
    p_fin.add_argument(
        "--context-root",
        help="where the gitignored context YAML is written (default: auto-detected "
        "primary clone, so a linked worktree does not orphan it). Override only to force a path.",
    )

    p_arc = sub.add_parser("archive-register", help="move old resolved rows to the archive")
    p_arc.add_argument("--days", type=int, default=60)

    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    if args.cmd == "pre":
        return cmd_pre(root, args)
    if args.cmd == "finalize":
        return cmd_finalize(root, args)
    return archive_register(root, args.days)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
