"""clipengine command line.

    uv run clipengine watch                  new VODs, uploads, viewer clips (last 7 days)
    uv run clipengine list                   what the database holds per streamer
    uv run clipengine suggest --since 48h    top streamers by English GTA VI clip views
    uv run clipengine approve LOGIN          owner said yes: add to the register
    uv run clipengine reject LOGIN           owner said no: never suggest again
    uv run clipengine fetch --dry-run        plan the most-viewed stretches of finished VODs
    uv run clipengine fetch                  ... and download only those, via yt-dlp
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

import httpx

from . import config, db, register, suggest as suggest_mod, watch as watch_mod
from . import fetch as fetch_mod
from .twitch import TokenStore, Twitch, TwitchError


class UsageError(Exception):
    pass


def parse_when(text: str, *, now: datetime) -> datetime:
    """'48h', '7d', '2026-11-19' or a full ISO timestamp (UTC when no offset)."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([hd])", text.strip())
    if match:
        amount = float(match.group(1))
        return now - (timedelta(hours=amount) if match.group(2) == "h" else timedelta(days=amount))
    try:
        moment = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise UsageError(f"cannot read time '{text}': use 48h, 7d or 2026-11-19T00:00Z") from exc
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def open_db() -> sqlite3.Connection:
    return db.connect(config.db_path())


def make_twitch(con: sqlite3.Connection) -> Twitch:
    secrets = config.load_secrets()
    if len(secrets) < 2:
        raise UsageError(
            "Twitch credentials missing: TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET belong in "
            "workspace/projects/gta6-clipping/context/.env of the primary checkout"
        )
    store = TokenStore(lambda: db.meta_get(con, "twitch_app_token"),
                       lambda value: db.meta_set(con, "twitch_app_token", value))
    return Twitch(secrets["TWITCH_CLIENT_ID"], secrets["TWITCH_CLIENT_SECRET"], token_store=store)


def load_and_sync(con: sqlite3.Connection) -> list[register.Streamer]:
    streamers = register.load(config.register_path())
    register.sync(con, streamers)
    return streamers


# --- commands ---------------------------------------------------------------

def cmd_watch(args, con, *, twitch=None, http=None) -> int:
    streamers = load_and_sync(con)
    if not streamers:
        print("register is empty: nothing to watch (see config/streamers.yaml)")
        return 0
    twitch = twitch or make_twitch(con)
    http = http or httpx.Client(timeout=30)
    results = watch_mod.watch(con, twitch, http, days=args.days, max_pages=args.max_pages,
                              chunk_hours=args.chunk_hours,
                              only=[x.lower() for x in args.only] if args.only else None)
    print(f"{'streamer':<24}{'VODs':>6}{'new':>5}{'clips':>7}{'new':>5}{'YT':>4}{'new':>5}")
    failed = 0
    for r in results:
        print(f"{r.login:<24}{r.vods:>6}{r.new_vods:>5}{r.clips:>7}{r.new_clips:>5}"
              f"{r.uploads:>4}{r.new_uploads:>5}")
        for err in r.errors:
            failed += 1
            print(f"  ! {err}")
    print(f"Twitch calls: {twitch.calls}")
    return 1 if failed else 0


def cmd_list(args, con) -> int:
    load_and_sync(con)
    since = db.iso(datetime.now(timezone.utc) - timedelta(days=args.days))
    logins = [args.streamer.lower()] if args.streamer else [
        r["login"] for r in con.execute(
            "SELECT login FROM streamers WHERE active = 1 ORDER BY priority, login")]
    for login in logins:
        print(f"== {login}")
        # Same rule as watch: a VOD shows when any part of it lies in the window.
        videos = con.execute(
            "SELECT * FROM videos WHERE streamer = ? AND "
            "datetime(created_at, '+' || COALESCE(duration_s, 0) || ' seconds') >= datetime(?) "
            "ORDER BY created_at DESC", (login, since)).fetchall()
        for v in videos:
            dur = f"{v['duration_s'] // 60}m" if v["duration_s"] else "?"
            muted = " muted" if v["muted_segments"] else ""
            print(f"  {v['source']:<7} {v['ext_id']:<14} {v['created_at']} {dur:>6}{muted} "
                  f"[{v['status']}] {(v['title'] or '')[:50]}")
        clips = con.execute(
            "SELECT * FROM crowd_clips WHERE streamer = ? AND created_at >= ? "
            "ORDER BY view_count DESC LIMIT ?", (login, since, args.limit)).fetchall()
        total = con.execute(
            "SELECT COUNT(*) FROM crowd_clips WHERE streamer = ? AND created_at >= ?",
            (login, since)).fetchone()[0]
        print(f"  clips: {total} in window, top {len(clips)} by views")
        for c in clips:
            gta = "GTA6" if c["game_id"] == config.GTA6_GAME_ID else (c["game_id"] or "?")
            print(f"    {c['view_count']:>7} views {c['duration_s']:>5.1f}s "
                  f"vod {c['video_id'] or '-'}@{c['vod_offset'] if c['vod_offset'] is not None else '-'}"
                  f" {gta:<10} {c['created_at']} {(c['title'] or '')[:40]}")
    return 0


def cmd_suggest(args, con, *, twitch=None, now: datetime | None = None) -> int:
    load_and_sync(con)
    now = now or datetime.now(timezone.utc)
    start = parse_when(args.since, now=now)
    end = parse_when(args.until, now=now) if args.until else now
    if start >= end:
        raise UsageError("--since must be before --until")
    twitch = twitch or make_twitch(con)
    picked = suggest_mod.suggest(con, twitch, game_id=config.GTA6_GAME_ID, start=start, end=end,
                                 chunk_hours=args.chunk_hours, max_pages=args.max_pages,
                                 lang=args.lang, top=args.top)
    report = suggest_mod.render_report(picked, start=start, end=end, lang=args.lang)
    print(report)
    if not args.no_report:
        path = config.reports_dir() / f"suggest-{now.strftime('%Y%m%d-%H%M')}.md"
        path.write_text(report, encoding="utf-8")
        print(f"report: {path}")
    print(f"Twitch calls: {twitch.calls}")
    return 0


def cmd_approve(args, con, *, twitch=None) -> int:
    path = config.register_path()
    load_and_sync(con)
    for raw in args.logins:
        login = raw.lower()
        row = con.execute("SELECT * FROM suggestions WHERE login = ?", (login,)).fetchone()
        name, language = (row["display_name"], row["language"]) if row else (None, args.language)
        if name is None:
            twitch = twitch or make_twitch(con)
            users = twitch.users(logins=[login])
            if not users:
                raise UsageError(f"Twitch login '{login}' not found")
            name = users[0]["display_name"]
        register.append(path, register.Streamer(
            name=name, twitch=login, language=language, youtube=args.youtube,
            layout=args.layout, priority=args.priority))
        if row:
            with con:
                con.execute("UPDATE suggestions SET status = 'approved', updated_at = ? "
                            "WHERE login = ?", (db.utcnow(), login))
        print(f"added {name} ({login}) to {path}")
    load_and_sync(con)
    return 0


def hms(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def cmd_fetch(args, con, *, twitch=None, downloader=None, probe=None) -> int:
    load_and_sync(con)
    twitch = twitch or make_twitch(con)
    results = fetch_mod.fetch(
        con, twitch, downloader=downloader or fetch_mod.YtDlp(), probe=probe or fetch_mod.ffprobe,
        streamers=[x.lower() for x in args.streamer] if args.streamer else None,
        video_ids=args.video, days=args.days, top=args.top, min_views=args.min_views,
        pad=args.pad, max_len=args.max_len, dry_run=args.dry_run)
    failed = 0
    for res in results:
        muted = f", {res.muted_skipped} muted skipped" if res.muted_skipped else ""
        print(f"== {res.streamer} {res.source}{muted}{': ' + res.note if res.note else ''}")
        for s in res.sections:
            where = (f"{hms(s['win_start_s'])}-{hms(s['win_end_s'])}" if s["kind"] == "vod"
                     else f"clip {s['top_clip_id'][:28]}")
            state = s["status"] if s["status"] != "fetched" else (
                f"{s['file']} {s['file_duration_s']:.1f}s {s['width']}x{s['height']}")
            if s["status"] == "failed":
                failed += 1
                state += f" ({s['last_error']})"
            print(f"  #{s['rank'] or '-'} {where:<20} {s['views']:>8} views "
                  f"{s['clips']:>3} clips  {state}")
    if args.dry_run:
        print("dry run: nothing downloaded")
    return 1 if failed else 0


def cmd_reject(args, con) -> int:
    for raw in args.logins:
        login = raw.lower()
        cur = con.execute("UPDATE suggestions SET status = 'rejected', updated_at = ? "
                          "WHERE login = ?", (db.utcnow(), login))
        con.commit()
        print(f"{login}: {'rejected' if cur.rowcount else 'not in the suggestion list'}")
    return 0


# --- parser -----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="clipengine", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    w = sub.add_parser("watch", help="poll Twitch and YouTube for the register")
    w.add_argument("--days", type=float, default=7, help="lookback window (default 7)")
    w.add_argument("--max-pages", type=int, default=10,
                   help="clip pages of 100 per window chunk (default 10)")
    w.add_argument("--chunk-hours", type=float, default=6,
                   help="clip window chunk; Twitch caps each query near 1,000 (default 6)")
    w.add_argument("--only", nargs="+", metavar="LOGIN", help="watch only these logins")

    ls = sub.add_parser("list", help="show stored VODs and top clips")
    ls.add_argument("--days", type=float, default=7)
    ls.add_argument("--streamer", metavar="LOGIN")
    ls.add_argument("--limit", type=int, default=10, help="clips per streamer (default 10)")

    s = sub.add_parser("suggest", help="rank streamers by viewer-clip views for GTA VI")
    s.add_argument("--since", default="48h", help="window start: 48h, 7d or ISO (default 48h)")
    s.add_argument("--until", help="window end (default now)")
    s.add_argument("--lang", default="en", help="clip language (default en)")
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--chunk-hours", type=float, default=6)
    s.add_argument("--max-pages", type=int, default=10, help="pages of 100 per chunk")
    s.add_argument("--no-report", action="store_true", help="do not write data/reports/")

    a = sub.add_parser("approve", help="add approved streamers to the register")
    a.add_argument("logins", nargs="+", metavar="LOGIN")
    a.add_argument("--youtube", help="YouTube channel id (UC...)")
    a.add_argument("--layout")
    a.add_argument("--priority", type=int, default=3)
    a.add_argument("--language", default="en", help="used when the login was never suggested")

    r = sub.add_parser("reject", help="keep streamers out of future suggestions")
    r.add_argument("logins", nargs="+", metavar="LOGIN")

    f = sub.add_parser("fetch", help="download only the most-viewed stretches of finished VODs")
    f.add_argument("--streamer", nargs="+", metavar="LOGIN", help="only these logins")
    f.add_argument("--video", nargs="+", metavar="VOD_ID", help="only these Twitch VODs")
    f.add_argument("--days", type=float, default=2, help="VODs and clips of the last N days")
    f.add_argument("--top", type=int, default=5, help="strongest intervals per VOD (default 5)")
    f.add_argument("--min-views", type=int, default=50, help="summed clip views (default 50)")
    f.add_argument("--pad", type=float, default=5, help="seconds before and after (default 5)")
    f.add_argument("--max-len", type=float, default=120,
                   help="longest section in seconds (default 120)")
    f.add_argument("--dry-run", action="store_true", help="plan and print, download nothing")
    return p


COMMANDS = {"watch": cmd_watch, "list": cmd_list, "suggest": cmd_suggest,
            "approve": cmd_approve, "reject": cmd_reject, "fetch": cmd_fetch}


def main(argv: list[str] | None = None) -> int:
    try:  # Windows consoles default to cp1252; streamer names are often not
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    args = build_parser().parse_args(argv)
    con = open_db()
    try:
        return COMMANDS[args.command](args, con)
    except (UsageError, register.RegisterError, TwitchError, fetch_mod.FetchError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
