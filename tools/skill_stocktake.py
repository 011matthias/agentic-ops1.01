# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Skill / command / agent stocktake: inventory joined with real usage.

WHY THIS EXISTS
---------------
The toolkit only ever grows. /comd_system-dev Phase 1.5 asks for overlapping
and overloaded skills, but judged them from descriptions alone, with zero data
on whether anything is used. `session-pressure-meter.py` now records every
Skill and Agent call (tools/telemetry_store.py); this joins those counts with
the static inventory and prints candidates WITH the evidence behind each, so a
human decides. Ported from ECC's skill-stocktake + config-gc, mechanism only.

VERDICTS (candidates, never actions; this tool deletes nothing)
  Retire   non-stub, zero runs across a telemetry window of at least 30 days
  Merge    a consolidation stub that hosts no modules, or a description that
           overlaps another item's closely enough to confuse routing
  Improve  description missing or too short to route on, SKILL.md over the
           500-line norm, or a failure share of 30%+ over 3+ runs
  Keep     everything else

With less than 30 days of telemetry no Retire verdict is issued, and the output
says so. The first run after this ships shows zeros by construction.

USAGE
  uv run tools/skill_stocktake.py [--format text|json] [--repo PATH]
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telemetry_store  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MIN_RETIRE_COVERAGE_DAYS = 30
LINE_NORM = 500
MIN_DESC = 40
OVERLAP_RATIO = 0.75
_STUB = re.compile(r"^\s*Consolidated into\s+([A-Za-z0-9_.-]+)", re.IGNORECASE)
_WORD = re.compile(r"[a-z][a-z0-9-]{3,}")
_COMMON = {
    "when", "with", "that", "this", "from", "into", "your", "user", "wants",
    "also", "skill", "use", "used", "using", "should", "about", "such", "like",
    "mentions", "asks", "including", "other", "each", "their", "they", "them",
}


def frontmatter(text: str) -> dict:
    """Top-level scalar keys of a markdown frontmatter block, including a
    folded or multi-line plain value (`description:` / `description: >` with
    indented continuation lines). Enough for name/description."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict = {}
    key = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            v = m.group(2).strip()
            if v in ("|", ">", "|-", ">-", "|+", ">+"):
                v = ""
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
            meta[key] = v
        elif key and line[:1] in (" ", "\t") and line.strip():
            meta[key] = (meta[key] + " " + line.strip()).strip()
        else:
            key = None
    return meta


def inventory(repo: Path) -> list[dict]:
    items = []
    claude = repo / ".claude"
    for skill_md in sorted((claude / "skills").glob("*/SKILL.md")):
        d = skill_md.parent
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        meta = frontmatter(text)
        desc = meta.get("description", "")
        stub = _STUB.match(desc)
        hosted = [p for p in d.rglob("*") if p.is_file() and p.name != "SKILL.md"]
        items.append({
            "kind": "skill", "name": d.name, "aliases": {meta.get("name", "")} - {""},
            "path": skill_md, "desc": desc, "text": text,
            "stub_of": stub.group(1).rstrip(".") if stub else None, "hosted_files": len(hosted),
        })
    for kind, sub in (("command", "commands"), ("agent", "agents")):
        for md in sorted((claude / sub).glob("*.md")):
            text = md.read_text(encoding="utf-8", errors="ignore")
            meta = frontmatter(text)
            items.append({
                "kind": kind, "name": md.stem, "aliases": {meta.get("name", "")} - {"", md.stem},
                "path": md, "desc": meta.get("description", ""), "text": text,
                "stub_of": None, "hosted_files": 0,
            })
    for it in items:
        st = it["path"].stat()
        it["bytes"] = st.st_size
        it["lines"] = it["text"].count("\n") + 1
        it["mtime"] = datetime.fromtimestamp(st.st_mtime, timezone.utc).date().isoformat()
    return items


def _words(desc: str) -> set[str]:
    return {w for w in _WORD.findall(desc.lower()) if w not in _COMMON}


def overlaps(items: list[dict]) -> dict[str, tuple[str, float]]:
    """Best description-overlap partner per item (same kind, neither a stub)."""
    best: dict[str, tuple[str, float]] = {}
    pool = [i for i in items if i["desc"] and not i["stub_of"]]
    for a_idx, a in enumerate(pool):
        for b in pool[a_idx + 1:]:
            if a["kind"] != b["kind"]:
                continue
            wa, wb = _words(a["desc"]), _words(b["desc"])
            if not wa or not wb:
                continue
            jacc = len(wa & wb) / len(wa | wb)
            if jacc < 0.25:
                continue  # cheap prefilter before difflib
            ratio = difflib.SequenceMatcher(None, a["desc"].lower(), b["desc"].lower()).ratio()
            score = round(max(ratio, jacc), 2)
            if score < OVERLAP_RATIO:
                continue
            for x, y in ((a, b), (b, a)):
                if score > best.get(x["name"], ("", 0.0))[1]:
                    best[x["name"]] = (y["name"], score)
    return best


def usage(items: list[dict]) -> tuple[dict, dict, dict, list[str], float]:
    runs30 = Counter()
    runs90 = Counter()
    fails90 = Counter()
    known = {}
    for it in items:
        known[(it["kind"], it["name"])] = it["name"]
        for alias in it["aliases"]:
            known.setdefault((it["kind"], alias), it["name"])
    unknown = Counter()
    now = datetime.now(timezone.utc)
    for rec in telemetry_store.read(telemetry_store.SKILL_RUNS, since_days=90):
        kind = rec.get("kind")
        raw = str(rec.get("name", ""))
        # Commands are invoked through the Skill tool too.
        target = known.get((kind, raw)) or (known.get(("command", raw)) if kind == "skill" else None)
        if not target:
            unknown[f"{kind}:{raw}"] += 1
            continue
        runs90[target] += 1
        if rec.get("ok") is False:
            fails90[target] += 1
        ts = telemetry_store.parse_ts(rec.get("ts"))
        if ts and (now - ts).days < 30:
            runs30[target] += 1
    coverage = telemetry_store.coverage_days(telemetry_store.SKILL_RUNS)
    return runs30, runs90, fails90, [f"{k} ({n})" for k, n in unknown.most_common()], coverage


def classify(items: list[dict]) -> tuple[list[dict], dict]:
    runs30, runs90, fails90, unknown, coverage = usage(items)
    over = overlaps(items)
    retire_ok = coverage >= MIN_RETIRE_COVERAGE_DAYS
    rows = []
    for it in items:
        n30, n90, f90 = runs30[it["name"]], runs90[it["name"]], fails90[it["name"]]
        evidence = [f"runs 30d/90d {n30}/{n90}", f"{it['lines']} lines", f"desc {len(it['desc'])} chars"]
        verdict, reason = "Keep", ""
        if it["stub_of"]:
            evidence.append(f"stub of {it['stub_of']}, hosts {it['hosted_files']} file(s)")
            if it["hosted_files"] == 0:
                verdict, reason = "Merge", f"consolidation stub hosting nothing; fold into {it['stub_of']}"
            else:
                reason = f"stub hosting {it['hosted_files']} module file(s) for {it['stub_of']}"
        elif it["name"] in over:
            other, score = over[it["name"]]
            verdict, reason = "Merge", f"description overlaps {other} ({score})"
        elif retire_ok and n90 == 0:
            verdict = "Retire"
            reason = f"0 runs in {min(round(coverage), 90)} days of telemetry"
        elif not it["desc"] or len(it["desc"]) < MIN_DESC:
            verdict, reason = "Improve", "description missing or too short to route on"
        elif it["kind"] == "skill" and it["lines"] > LINE_NORM:
            verdict, reason = "Improve", f"SKILL.md over the {LINE_NORM}-line norm; split candidate"
        elif n90 >= 3 and f90 / n90 >= 0.3:
            verdict, reason = "Improve", f"{f90}/{n90} recorded runs failed"
        rows.append({
            "verdict": verdict, "kind": it["kind"], "name": it["name"], "reason": reason,
            "evidence": ", ".join(evidence), "runs_30d": n30, "runs_90d": n90,
            "mtime": it["mtime"], "bytes": it["bytes"],
        })
    order = {"Retire": 0, "Merge": 1, "Improve": 2, "Keep": 3}
    rows.sort(key=lambda r: (order[r["verdict"]], r["kind"], r["name"]))
    meta = {
        "telemetry_dir": str(telemetry_store.telemetry_dir()),
        "coverage_days": round(coverage, 1),
        "total_runs_90d": sum(runs90.values()),
        "retire_verdicts_enabled": retire_ok,
        "invoked_not_in_inventory": unknown,
    }
    return rows, meta


def render(rows: list[dict], meta: dict) -> str:
    out = [
        f"SKILL STOCKTAKE  ({sum(1 for r in rows if r['kind'] == 'skill')} skills, "
        f"{sum(1 for r in rows if r['kind'] == 'command')} commands, "
        f"{sum(1 for r in rows if r['kind'] == 'agent')} agents)",
        f"telemetry: {meta['total_runs_90d']} run(s) in 90d, {meta['coverage_days']} day(s) "
        f"of history, from {meta['telemetry_dir']}",
    ]
    if not meta["retire_verdicts_enabled"]:
        out.append(
            f"  NOTE: under {MIN_RETIRE_COVERAGE_DAYS} days of telemetry, so no Retire verdicts. "
            "Zero runs here mean 'not measured yet', not 'unused'. Merge and Improve rest "
            "on static evidence only."
        )
    counts = Counter(r["verdict"] for r in rows)
    out.append("verdicts: " + ", ".join(f"{v} {counts.get(v, 0)}" for v in ("Retire", "Merge", "Improve", "Keep")))
    for verdict in ("Retire", "Merge", "Improve"):
        group = [r for r in rows if r["verdict"] == verdict]
        if not group:
            continue
        out.append(f"\n{verdict.upper()} candidates")
        for r in group:
            out.append(f"  {r['kind']:7} {r['name']:40} {r['reason']}")
            out.append(f"  {'':7} {'':40} evidence: {r['evidence']}")
    keep = [r for r in rows if r["verdict"] == "Keep"]
    out.append(f"\nKEEP ({len(keep)}): " + ", ".join(r["name"] for r in keep))
    if meta["invoked_not_in_inventory"]:
        out.append("\ninvoked but not in this repo (plugins / built-ins): "
                   + ", ".join(meta["invoked_not_in_inventory"][:20]))
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--repo", type=Path, default=REPO)
    args = ap.parse_args(argv)
    rows, meta = classify(inventory(args.repo))
    if args.format == "json":
        print(json.dumps({"meta": meta, "rows": rows}, indent=2))
    else:
        print(render(rows, meta))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
