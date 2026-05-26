#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic morning-briefing generator + sender.

Runs INSIDE a checkout of agentic-ops. Scans client specs, comms staleness,
upcoming dated items, projects, and the proposal pipeline, renders one
prioritized plain-text briefing, and sends it via the Resend HTTP API.

Design rules learned the hard way:
- No third-party deps (stdlib only) so it runs in any bare sandbox.
- The Resend key is read from $RESEND_API_KEY, never hardcoded — this repo
  is PUBLIC. Recipient is argv[1] or $BRIEFING_TO.
- Failure is LOUD: any exception still triggers an email containing the
  traceback, so a broken run is visible in the inbox, never silent.

Usage:
  RESEND_API_KEY=re_... python3 tools/morning_briefing.py recipient@example.com
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import traceback
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLIENTS = REPO / "workspace" / "clients"
PROJECTS = REPO / "workspace" / "projects"
PROPOSALS = REPO / "platform" / "src" / "content" / "proposals"
ACTIVE_STAGES = ("1-spec", "2-build", "3-test")
DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")


def frontmatter(md: Path) -> dict:
    """Minimal YAML-ish frontmatter parse (no PyYAML in a bare sandbox)."""
    try:
        text = md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    out: dict = {}
    key = None
    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            out[key] = val if val else []
        elif key and re.match(r"^\s*-\s+", line):
            item = re.sub(r"^\s*-\s+", "", line).strip().strip('"').strip("'")
            if isinstance(out.get(key), list):
                out[key].append(item)
    return out


def first_nextstep(fm: dict) -> str | None:
    ns = fm.get("next_steps")
    if isinstance(ns, list) and ns:
        return ns[0]
    if isinstance(ns, str) and ns and ns not in ("[]", "'[]'"):
        return ns
    return None


def scan():
    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=2)
    needs_fix, next_steps, imminent, stale, projects = [], [], [], [], []

    if CLIENTS.is_dir():
        for cdir in sorted(p for p in CLIENTS.iterdir() if p.is_dir()):
            client = cdir.name
            boundaries = (cdir / "PROJECT-BOUNDARIES.md")
            paused_note = ""
            if boundaries.is_file() and "PAUSED" in boundaries.read_text(
                encoding="utf-8", errors="replace"
            ).upper():
                paused_note = client

            specs = cdir / "specs"
            if specs.is_dir():
                for stage in ACTIVE_STAGES:
                    for md in sorted((specs / stage).glob("*.md")) if (
                        specs / stage
                    ).is_dir() else []:
                        fm = frontmatter(md)
                        if str(fm.get("needs_fixes", "")).lower() == "true":
                            needs_fix.append(
                                f"{client} {fm.get('id', md.stem)} - needs_fixes"
                            )
                        ns = first_nextstep(fm)
                        if ns and client != paused_note:
                            next_steps.append((client, ns))
                live = specs / "4-live"
                if live.is_dir():
                    for md in sorted(live.glob("*.md")):
                        fm = frontmatter(md)
                        if str(fm.get("needs_fixes", "")).lower() == "true":
                            needs_fix.append(
                                f"{client} {fm.get('id', md.stem)} - needs_fixes (live)"
                            )

            ctx = cdir / "context"
            for sub in (ctx, ctx / "drafts"):
                if not sub.is_dir():
                    continue
                for md in sorted(sub.glob("*.md")):
                    m = DATE_RE.search(md.name)
                    if not m:
                        continue
                    try:
                        d = datetime.date(int(m[1]), int(m[2]), int(m[3]))
                    except ValueError:
                        continue
                    if today <= d <= horizon:
                        imminent.append(f"{client} - {md.stem} ({d.isoformat()})")

            clog = ctx / "comms-log.md"
            if clog.is_file():
                dates = DATE_RE.findall(
                    clog.read_text(encoding="utf-8", errors="replace")
                )
                if dates:
                    last = max(datetime.date(int(a), int(b), int(c)) for a, b, c in dates)
                    age = (today - last).days
                    tier = (
                        "URGENT" if age >= 15 else "STALE" if age >= 8
                        else "NOTICE" if age >= 4 else None
                    )
                    if tier:
                        stale.append(f"{client} ({tier}, {age}d) - last contact {last}")

    if PROJECTS.is_dir():
        projects = [p.name for p in sorted(PROJECTS.iterdir()) if p.is_dir()]

    counts: dict[str, int] = {}
    if PROPOSALS.is_dir():
        for md in PROPOSALS.glob("*.md"):
            if md.stem.startswith("p000") or "sample" in md.stem:
                continue
            st = str(frontmatter(md).get("status", "")).strip().lower()
            if st:
                counts[st] = counts.get(st, 0) + 1

    return today, needs_fix, next_steps, imminent, stale, projects, counts


def render(today, needs_fix, next_steps, imminent, stale, projects, counts) -> str:
    L = [f"Morning Briefing - {today.strftime('%A %Y-%m-%d')}", ""]

    L.append("TODAY / IMMINENT")
    for i in imminent or ["  • Nothing time-bound in the next 2 days"]:
        L.append(f"  • {i}" if not i.startswith("  ") else i)
    L.append("")

    L.append("DAILY COMMITMENT")
    L.append("  • 2 new proposals today. Pull 2 fresh from the Upwork queue "
             "or refresh+send 2 of the strongest drafts.")
    L.append("")

    if needs_fix:
        L.append("BLOCKED / NEEDS DECISION")
        L += [f"  • {x}" for x in needs_fix]
        L.append("")

    if next_steps:
        L.append("NEXT STEPS (by client)")
        seen = set()
        for client, ns in next_steps:
            if client in seen:
                continue
            seen.add(client)
            L.append(f"  • {client}: {ns}")
        L.append("")

    if projects:
        L.append("PROJECTS")
        L.append("  • " + ", ".join(projects))
        L.append("")

    if stale:
        L.append("STALE COMMS")
        L += [f"  • {x}" for x in stale]
        L.append("")

    if counts:
        L.append("PIPELINE")
        L.append("  • Proposals: " + " · ".join(
            f"{n} {s}" for s, n in sorted(counts.items())))
        L.append("")

    L.append(f"Generated {today.isoformat()} by tools/morning_briefing.py")
    return "\n".join(L)


def send(subject: str, body: str) -> str:
    key = os.environ.get("RESEND_API_KEY")
    to = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BRIEFING_TO"))
    if not key or not to:
        return "NO_SEND: missing RESEND_API_KEY or recipient"
    payload = json.dumps({
        "from": "onboarding@resend.dev", "to": to,
        "subject": subject, "text": body,
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 # Cloudflare in front of api.resend.com 403s (code 1010)
                 # the default Python-urllib User-Agent. A real UA passes.
                 "User-Agent": "agentic-ops-morning-briefing/1.0"},
    )
    try:
        return "RESEND_OK " + urllib.request.urlopen(req, timeout=30).read().decode()
    except Exception as e:  # noqa: BLE001 - want the reason in the inbox
        detail = getattr(e, "read", lambda: b"")()
        return f"RESEND_ERR {e} {detail.decode(errors='replace') if detail else ''}"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    today = datetime.date.today()
    try:
        data = scan()
        body = render(*data)
        subject = f"Morning Briefing - {today.isoformat()}"
    except Exception:  # noqa: BLE001 - loud failure: email the traceback
        body = ("Morning briefing generation FAILED. Traceback:\n\n"
                + traceback.format_exc())
        subject = f"Morning Briefing - {today.isoformat()} (GENERATION FAILED)"
    result = send(subject, body)
    print(result)
    print("---")
    print(body)
    return 0 if result.startswith("RESEND_OK") else 1


if __name__ == "__main__":
    raise SystemExit(main())
