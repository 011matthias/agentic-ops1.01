# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "pyyaml>=6.0"]
# ///
"""Kleinanzeigen watcher: a phone push the moment a matching ad appears.

Built 2026-10-02 on the Vinted watcher's pattern: a poller on the home
(residential) line, SQLite to remember what it has seen, ntfy.sh for the
push, a hidden Windows scheduled task every 5 minutes. First search: beds
180x200 in the city of Karlsruhe (searches.yaml).

Each cycle reads page 1 of every feed (newest first), records every ad it
has never seen, decides whether it is a hit, and pushes hits to the ntfy
topic in context/.env. The size test runs here rather than in
Kleinanzeigen's search box, because sellers write the size every way there
is ("180x200", "180 x 200 cm", "1,80 x 2,00", "180er") and some write it
only in the description. The card's preview text stops after ~250
characters, so an ad that names a bed but no size there gets ONE fetch of
its own page before it is decided: the first probe on 2026-10-02 found a
40 EUR "Bett mit Lattenrost" whose size ("ca. 2,00 m lang, 1,80 m breit")
appeared nowhere but in the full description.

The first cycle only learns what is already listed and sends one start-up
push that links the full current list; after that, every new hit pushes.
If the watcher stops getting data (blocked, offline, page layout changed),
it says so by push after 30 minutes instead of going quiet.

Modes:
  --cycle         one poll cycle (default; the scheduled task's entry)
  --dry-run       a full cycle that writes nothing and sends nothing
  --test-notify   send a test push to the configured topic
  --init-topic    create a private ntfy topic in context/.env (once)
  --status        counts, health, recent hits
  --check TEXT    show how a title/description would be judged
"""

import argparse
import html
import json
import os
import random
import re
import secrets
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "ads.db"
LOG_PATH = DATA_DIR / "watcher.log"
LOCK_PATH = DATA_DIR / "cycle.lock"
ENV_PATH = PROJECT_DIR / "context" / ".env"
CONFIG_PATH = SCRIPT_DIR / "searches.yaml"

BASE = "https://www.kleinanzeigen.de"
NTFY = "https://ntfy.sh/"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9",
}

# One page per feed plus at most this many ad pages per cycle. A normal
# cycle needs 0-2; the cap only bites after an outage, and the rest wait
# for the next cycle instead of hammering.
DETAIL_FETCHES_PER_CYCLE = 10
# A hit whose push failed is retried this long, then given up on.
RETRY_PUSH_HOURS = 24
MAX_PUSH_ATTEMPTS = 30
# 6 failed cycles = 30 minutes at the task's 5-minute cadence.
HEALTH_ALERT_AFTER = 6
HEALTH_ALERT_EVERY_H = 12
BACKOFF_BASE_MIN = 30
BACKOFF_MAX_MIN = 360
LOCK_STALE_MIN = 15


class Blocked(Exception):
    """Kleinanzeigen answered 403/429: stop asking for a while."""


# ------------------------------------------------------------------ helpers

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def log(msg: str) -> None:
    line = f"{datetime.now().astimezone():%Y-%m-%d %H:%M:%S%z} {msg}"
    print(line)
    # The scheduled task runs hidden and discards stdout, so the file is the
    # only place a failure is visible afterwards.
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > 1_000_000:
            LOG_PATH.replace(LOG_PATH.with_name(LOG_PATH.name + ".1"))
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_config(path: Path = CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg.setdefault("match", {})
    cfg["match"].setdefault("width_cm", 180)
    cfg["match"].setdefault("length_cm", 200)
    cfg["match"].setdefault("price_max", None)
    cfg["match"].setdefault("require_storage", False)
    cfg.setdefault("alert_priority", 5)
    cfg.setdefault("browse_url", BASE)
    return cfg


def load_env(path: Path = ENV_PATH) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


# ------------------------------------------------------------- size + bed

# A number as sellers write a bed dimension: 180, 1,80, 1.8, 2,00. The unit
# must end on a word boundary so "2 mit" is not read as "2 m".
_DIM = r"(?P<n>\d{1,3}(?:[.,]\d{1,2})?)(?!\d)\s*(?:(?P<u>cm|m)\b)?\.?"
PAIR_RE = re.compile(
    r"(?<![\d.,])(?P<a>\d{1,3}(?:[.,]\d{1,2})?)(?!\d)\s*(?:(?P<ua>cm|m)\b)?\.?"
    r"\s*(?:x|×|\*|/|-)\s*"
    r"(?P<b>\d{1,3}(?:[.,]\d{1,2})?)(?!\d)\s*(?:(?P<ub>cm|m)\b)?",
    re.I,
)
WIDTH_RES = (
    re.compile(rf"(?<![\d.,]){_DIM}\s*(?:breit|breite)\b", re.I),
    re.compile(rf"\b(?:breite|breit|liegefl(?:ä|ae)che)\s*(?::|von|ca\.?|\s)*{_DIM}"
               r"(?!\s*(?:x|×|\*|/))", re.I),
    re.compile(r"(?<![\d.,])(?P<n>\d{2,3})(?P<u>)er\b", re.I),
)
LENGTH_RES = (
    re.compile(rf"(?<![\d.,]){_DIM}\s*(?:lang|l(?:ä|ae)nge)\b", re.I),
    re.compile(rf"\b(?:l(?:ä|ae)nge|lang)\s*(?::|von|ca\.?|\s)*{_DIM}", re.I),
)


def to_cm(num: str, unit: str | None) -> int | None:
    """A written dimension in cm, or None when it cannot be a bed side."""
    v = float(num.replace(",", "."))
    if v < 10:
        # "1,80" or "2 m" is metres. A bare "2" is a count ("2 x 90x200"),
        # not a length.
        if unit and unit.lower() == "m" or re.search(r"[.,]", num):
            v *= 100
        else:
            return None
    v = round(v)
    return v if 60 <= v <= 260 else None


def size_verdict(text: str, width: int = 180, length: int = 200) -> tuple[str, str]:
    """('match' | 'other' | 'unknown', evidence) for one block of text."""
    text = text or ""
    pairs = []
    for m in PAIR_RE.finditer(text):
        a, b = to_cm(m["a"], m["ua"]), to_cm(m["b"], m["ub"])
        if a and b:
            pairs.append((a, b))
    for a, b in pairs:
        if {a, b} == {width, length}:
            return "match", f"{a}x{b}"
    widths = [w for rx in WIDTH_RES for m in rx.finditer(text)
              if (w := to_cm(m["n"], m["u"] or None))]
    lengths = [n for rx in LENGTH_RES for m in rx.finditer(text)
               if (n := to_cm(m["n"], m["u"] or None))]
    if width in widths and (not lengths or length in lengths):
        return "match", f"{width} breit" + (f", {length} lang" if length in lengths else "")
    if pairs:
        return "other", f"{pairs[0][0]}x{pairs[0][1]}"
    if widths:
        return "other", f"{widths[0]} breit"
    return "unknown", ""


# "bett" as a bed, not as the first half of bed linen or a bed box.
BED_RE = re.compile(
    r"bett(?!w(?:ä|ae)sche|laken|decke|bezug|zeug|k(?:ä|ae)st|kissen|feder|"
    r"(?:ü|ue)berwurf|umrandung|rolle|wanze|tuch|h(?:ü|ue)lle|schutz)"
    r"|boxspring|futon",
    re.I,
)
ACCESSORY_RE = re.compile(
    r"matratze|lattenrost|topper|kopfteil|bettk(?:ä|ae)st|bettw(?:ä|ae)sche|laken"
    r"|bezug|auflage|schoner|decke|kissen",
    re.I,
)
OTHER_RE = re.compile(
    r"schr(?:a|ä|ae)nk|kommode|regal|nachttisch|nachtkonsole|spiegel|tisch|stuhl|sessel"
    r"|hocker|couch|lampe|leuchte|teppich|vorhang|gardine|pullover|jacke|hose"
    r"|kleid|schuh",
    re.I,
)
FOR_RE = re.compile(r"\b(?:f(?:ü|ue)r|passend|zu|zum)\b", re.I)
# "Suche Boxspringbett 180x200" is a buyer, not a bed.
WANTED_RE = re.compile(r"^\W*(?:suche|gesucht|wer\s+(?:hat|verkauft))\b", re.I)


def bed_verdict(title: str, text: str = "") -> str:
    """'bed' | 'not_bed' | 'unclear', judged on the title first."""
    title = title or ""
    bed = BED_RE.search(title)
    if bed:
        # "Matratze fuer Boxspringbett 180x200" names a bed and sells a
        # mattress. Only the "fuer/passend/zu" link makes it an accessory:
        # "Schrank, Bett, Nolte" is a bedroom that includes a bed.
        first = min((m for rx in (ACCESSORY_RE, OTHER_RE) if (m := rx.search(title))),
                    key=lambda m: m.start(), default=None)
        if first and first.start() < bed.start() and FOR_RE.search(title[first.end():bed.start()]):
            return "not_bed"
        return "bed"
    if ACCESSORY_RE.search(title) or OTHER_RE.search(title):
        return "not_bed"
    if BED_RE.search(text or ""):
        return "bed"
    return "unclear"


# Storage in or under the bed (owner requirement 2026-10-02: "die Betten
# sollten auch Stauraum haben"). A drawer only counts when it is not a
# nightstand's or dresser's, the usual extras in a bedroom ad.
# Whole words, so the push reads "Bettkasten", not the stem that matched.
STORAGE_RE = re.compile(
    r"\w*(?:stauraum|bettk(?:ä|ae|a)st|schubl(?:a|ä)de|schubk(?:ä|ae|a)st|stauf(?:a|ä)ch"
    r"|aufbewahrung|hochklappbar|hebemechanismus|gasdruck|funktionsbett|storage)\w*",
    re.I,
)
STORAGE_NEGATION_RE = re.compile(r"\b(?:ohne|kein\w*)\s+(?:\S+\s+){0,2}$", re.I)
DRAWER_OWNER_RE = re.compile(r"nacht(?:tisch|schr(?:a|ä)nk|konsole|k(?:ä|ae)stchen)|kommode|schrank|regal",
                             re.I)


def storage_verdict(text: str) -> tuple[str, str]:
    """('yes' | 'no' | 'unknown', the words that decided it)."""
    text = text or ""
    negated = ""
    for m in STORAGE_RE.finditer(text):
        before = text[max(0, m.start() - 40):m.start()]
        if STORAGE_NEGATION_RE.search(before):
            negated = negated or m.group(0)
            continue
        word = m.group(0).lower()
        if "schub" in word and not word.startswith("bett"):
            owner = None
            # The word itself counts too: "Nachttischschublade".
            for owner in DRAWER_OWNER_RE.finditer(before + m.group(0)):
                pass
            # "2 Nachttische mit Schublade": the drawer is the nightstand's.
            # "Kommode und Bett mit Schubladen": a bed sits in between.
            if owner and not BED_RE.search((before + m.group(0))[owner.end():]):
                continue
        return "yes", m.group(0)
    return ("no", "ohne " + negated) if negated else ("unknown", "")


def _field(ad, key: str) -> str:
    try:
        return ad[key] or ""
    except (KeyError, IndexError):
        return ""


def decide_from_card(ad: dict, width: int, length: int,
                     storage: bool = False) -> tuple[str | None, str]:
    """(verdict, evidence) from the search card alone; None = read the ad page."""
    if WANTED_RE.search(ad["title"] or ""):
        return "wanted", ""
    card_text = ad["title"] + "\n" + _field(ad, "snippet")
    bed = bed_verdict(ad["title"], _field(ad, "snippet"))
    if bed == "not_bed":
        return "not_bed", ""
    v, ev = size_verdict(ad["title"], width, length)
    if v == "other":
        # The title is where a seller puts the bed's size; another size
        # there is the answer, whatever the description goes on to list.
        return "other_size", ev
    if v != "match":
        v, ev = size_verdict(card_text, width, length)
        if v != "match":
            return None, ""
    if storage:
        s, sev = storage_verdict(card_text)
        if s == "no":
            return "no_storage", sev
        if s == "unknown":
            return None, ""
        ev += f", Stauraum ({sev})"
    return "match", ev + (" (Titel nennt kein Bett)" if bed == "unclear" else "")


def decide_from_detail(ad: dict, description: str, width: int, length: int,
                       storage: bool = False) -> tuple[str, str]:
    bed = bed_verdict(ad["title"], description)
    if bed == "not_bed":
        return "not_bed", ""
    full = ad["title"] + "\n" + description
    v, ev = size_verdict(full, width, length)
    if v != "match":
        return ("other_size" if v == "other" else "unknown_size"), ev
    if size_verdict(ad["title"] + "\n" + _field(ad, "snippet"), width, length)[0] != "match":
        ev += " (aus der Beschreibung)"
    if storage:
        s, sev = storage_verdict(full)
        if s != "yes":
            return ("no_storage" if s == "no" else "storage_unknown"), sev
        ev += f", Stauraum ({sev})"
    return "match", ev


def price_eur(price_text: str) -> float | None:
    if not price_text:
        return None
    if re.search(r"verschenken|gratis", price_text, re.I):
        return 0.0
    m = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*€", price_text)
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


# ------------------------------------------------------------------ parsing

PRICE_PART_RE = re.compile(
    r"^(?:\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*€(?:\s*VB)?|VB|Zu verschenken|Gratis)$", re.I)


def _text_parts(fragment: str) -> list[str]:
    body = re.sub(r"<script.*?</script>|<svg.*?</svg>", "", fragment, flags=re.S)
    return [p for p in (html.unescape(s).strip() for s in re.split(r"<[^>]+>", body)) if p]


def parse_cards(page: str) -> list[dict]:
    """Every ad card on a search page, in page order."""
    cards = []
    for chunk in page.split("<article ")[1:]:
        chunk = chunk.split("</article>", 1)[0]
        adid = re.search(r'data-adid="(\d+)"', chunk)
        href = re.search(r'data-href="([^"]+)"', chunk)
        if not adid or not href:
            continue
        ld = {}
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', chunk, re.S)
        if m:
            try:
                ld = json.loads(m.group(1))
            except ValueError:
                ld = {}
        parts = _text_parts(chunk)
        title = ld.get("title")
        if not title:
            h = re.search(r"<h[23][^>]*>(.*?)</h[23]>", chunk, re.S)
            title = " ".join(_text_parts(h.group(1))) if h else ""
        snippet = ld.get("description")
        if not snippet:
            p = re.search(r"<p[^>]*>(.*?)</p>", chunk, re.S)
            snippet = " ".join(_text_parts(p.group(1))) if p else ""
        prices = [p for p in parts if PRICE_PART_RE.match(p)]
        cards.append({
            "id": int(adid.group(1)),
            "url": href.group(1) if href.group(1).startswith("http") else BASE + href.group(1),
            "title": html.unescape(title).strip(),
            "snippet": html.unescape(snippet).strip(),
            "price_text": prices[-1] if prices else "",
            "plz_ort": next((p for p in parts if re.match(r"^\d{5}\s", p)), ""),
            "posted_text": next((p for p in parts
                                 if re.match(r"^(?:Heute|Gestern|\d{2}\.\d{2}\.\d{4})", p)), ""),
            "image": ld.get("contentUrl", ""),
        })
    return cards


def parse_detail(page: str) -> str:
    """The full description of an ad page, line breaks kept."""
    m = re.search(r'id="viewad-description-text"[^>]*>(.*?)</p>', page, re.S)
    if not m:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", m.group(1))
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


# ----------------------------------------------------------------------- db

DDL = """
CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY,
    feed TEXT,
    url TEXT,
    title TEXT,
    price_text TEXT,
    price_eur REAL,
    plz_ort TEXT,
    posted_text TEXT,
    image TEXT,
    snippet TEXT,
    first_seen TEXT NOT NULL,
    seed INTEGER NOT NULL DEFAULT 0,
    verdict TEXT,
    evidence TEXT,
    detail_fetched_at TEXT,
    notified_at TEXT,
    notify_attempts INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ads_verdict ON ads(verdict);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


def db_connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(DDL)
    return con


def meta_get(con: sqlite3.Connection, k: str) -> str | None:
    row = con.execute("SELECT v FROM meta WHERE k = ?", (k,)).fetchone()
    return row[0] if row else None


def meta_set(con: sqlite3.Connection, k: str, v: str | None) -> None:
    if v is None:
        con.execute("DELETE FROM meta WHERE k = ?", (k,))
    else:
        con.execute("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v",
                    (k, v))


# -------------------------------------------------------------------- network

def fetch(client: httpx.Client, url: str) -> str:
    r = client.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
    if r.status_code in (403, 429):
        raise Blocked(f"HTTP {r.status_code} auf {url}")
    r.raise_for_status()
    return r.text


def push(client: httpx.Client, env: dict, title: str, message: str, *, click: str | None = None,
         priority: int = 4, attach: str | None = None, tags: list[str] | None = None) -> bool:
    topic = env.get("NTFY_TOPIC")
    if not topic:
        log("WARN: NTFY_TOPIC fehlt in context/.env; Push nicht gesendet")
        return False
    body = {"topic": topic, "title": title[:250], "message": message[:3500],
            "priority": priority, "tags": tags or ["bed"]}
    if click:
        body["click"] = click
        body["actions"] = [{"action": "view", "label": "Anzeige öffnen", "url": click}]
    if attach:
        body["attach"] = attach
    try:
        r = client.post(NTFY, json=body, timeout=15)
    except httpx.HTTPError as e:
        log(f"WARN: ntfy nicht erreichbar: {e}")
        return False
    if r.status_code != 200:
        log(f"WARN: ntfy lehnt ab, HTTP {r.status_code}: {r.text.strip()[:200]}")
        return False
    return True


def set_backoff(con: sqlite3.Connection, why: str) -> None:
    level = int(meta_get(con, "backoff_level") or 0) + 1
    minutes = min(BACKOFF_BASE_MIN * 2 ** (level - 1), BACKOFF_MAX_MIN)
    meta_set(con, "backoff_level", str(level))
    meta_set(con, "backoff_until", iso(utcnow() + timedelta(minutes=minutes)))
    log(f"BLOCKED: {why}; Pause {minutes} Min. (Stufe {level})")


# --------------------------------------------------------------------- cycle

def alert_text(ad: sqlite3.Row | dict) -> tuple[str, str]:
    line1 = " · ".join(p for p in (ad["price_text"] or "Preis ?", ad["plz_ort"], ad["posted_text"]) if p)
    lines = [line1]
    if ad["evidence"]:
        lines.append(f"Passt: {ad['evidence']}")
    if ad["snippet"]:
        lines.append(ad["snippet"][:200])
    return ad["title"] or "Bett", "\n".join(lines)


def record_health(client, con, env, ok: bool, reason: str, dry_run: bool) -> None:
    if ok:
        if meta_get(con, "health_alert_open") and not dry_run:
            if push(client, env, "Bett-Wächter läuft wieder",
                    "Die Anzeigen kommen wieder an; neue Betten werden wieder gemeldet.",
                    priority=3, tags=["white_check_mark"]):
                meta_set(con, "health_alert_open", None)
        meta_set(con, "fail_streak", "0")
        meta_set(con, "last_ok", iso(utcnow()))
        return
    streak = int(meta_get(con, "fail_streak") or 0) + 1
    meta_set(con, "fail_streak", str(streak))
    meta_set(con, "last_fail_reason", reason)
    last = parse_iso(meta_get(con, "health_alert_at"))
    due = last is None or utcnow() - last > timedelta(hours=HEALTH_ALERT_EVERY_H)
    if streak >= HEALTH_ALERT_AFTER and due and not dry_run:
        if push(client, env, "Bett-Wächter bekommt keine Daten",
                f"Seit {streak} Läufen (~{streak * 5} Min.) keine Anzeigen. Grund: {reason}. "
                "Neue Betten werden gerade NICHT gemeldet.",
                priority=4, tags=["warning"]):
            meta_set(con, "health_alert_at", iso(utcnow()))
            meta_set(con, "health_alert_open", "1")


def run_cycle(client: httpx.Client, con: sqlite3.Connection, cfg: dict, env: dict,
              dry_run: bool = False, pause: float = 1.0) -> int:
    """One poll. Returns 0 when every feed was read, 1 otherwise."""
    commit = (lambda: None) if dry_run else con.commit
    width, length = cfg["match"]["width_cm"], cfg["match"]["length_cm"]
    price_max = cfg["match"].get("price_max")
    storage = bool(cfg["match"].get("require_storage"))
    now = utcnow()
    meta_set(con, "last_cycle", iso(now))

    until = parse_iso(meta_get(con, "backoff_until"))
    if until and until > now:
        log(f"Pause wegen Sperre bis {until.astimezone():%H:%M}; nichts abgefragt")
        record_health(client, con, env, False, meta_get(con, "last_fail_reason") or "gesperrt", dry_run)
        commit()
        return 1

    seeding = meta_get(con, "seeded") is None
    feeds = cfg["feeds"]
    ok_feeds, failures, new_ids, blocked = 0, [], [], False
    for i, feed in enumerate(feeds):
        if i and pause:
            time.sleep(pause * random.uniform(2, 4))
        try:
            cards = parse_cards(fetch(client, feed["url"]))
        except Blocked as e:
            set_backoff(con, str(e))
            failures.append(f"gesperrt ({e})")
            blocked = True
            break
        except httpx.HTTPError as e:
            failures.append(f"{feed['name']}: {type(e).__name__} {e}"[:200])
            continue
        if not cards:
            # A 200 page with no ads is a layout change, not a quiet market:
            # this category lists dozens of new ads a day.
            failures.append(f"{feed['name']}: 0 Anzeigen erkannt, Seitenlayout geändert?")
            continue
        ok_feeds += 1
        for c in cards:
            cur = con.execute(
                """INSERT OR IGNORE INTO ads (id, feed, url, title, price_text, price_eur, plz_ort,
                       posted_text, image, snippet, first_seen, seed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (c["id"], feed["name"], c["url"], c["title"], c["price_text"], price_eur(c["price_text"]),
                 c["plz_ort"], c["posted_text"], c["image"], c["snippet"], iso(now), int(seeding)))
            if cur.rowcount:
                new_ids.append(c["id"])
                verdict, ev = decide_from_card(c, width, length, storage)
                if verdict is None and seeding:
                    # Already listed before the watcher started: the start-up
                    # push links the full list, so no ad page is fetched.
                    verdict = "seed_unchecked"
                con.execute("UPDATE ads SET verdict = ?, evidence = ? WHERE id = ?", (verdict, ev, c["id"]))
    commit()

    # Ads that named a bed but no size on the card: read their own page.
    fetched = 0
    if not blocked:
        pending = con.execute(
            "SELECT * FROM ads WHERE verdict IS NULL ORDER BY first_seen LIMIT ?",
            (DETAIL_FETCHES_PER_CYCLE,)).fetchall()
        for ad in pending:
            if pause:
                time.sleep(pause * random.uniform(2, 4))
            try:
                page = fetch(client, ad["url"])
            except Blocked as e:
                set_backoff(con, str(e))
                failures.append(f"gesperrt ({e})")
                blocked = True
                break
            except httpx.HTTPStatusError as e:
                verdict, ev = ("gone", "") if e.response.status_code in (404, 410) else (None, "")
                if verdict is None:
                    continue
            except httpx.HTTPError:
                continue
            else:
                verdict, ev = decide_from_detail(ad, parse_detail(page), width, length, storage)
            fetched += 1
            con.execute("UPDATE ads SET verdict = ?, evidence = ?, detail_fetched_at = ? WHERE id = ?",
                        (verdict, ev, iso(utcnow()), ad["id"]))
        commit()

    if price_max is not None:
        con.execute("UPDATE ads SET verdict = 'too_expensive' WHERE verdict = 'match' AND notified_at IS NULL "
                    "AND price_eur IS NOT NULL AND price_eur > ?", (price_max,))

    # Push every unsent hit, oldest first; a failed push is retried next cycle.
    sent = 0
    due = con.execute(
        """SELECT * FROM ads WHERE verdict = 'match' AND seed = 0 AND notified_at IS NULL
           AND first_seen > ? AND notify_attempts < ? ORDER BY first_seen, id""",
        (iso(now - timedelta(hours=RETRY_PUSH_HOURS)), MAX_PUSH_ATTEMPTS)).fetchall()
    for ad in due:
        title, message = alert_text(ad)
        if dry_run:
            print(f"[dry-run] PUSH {title} | {message.splitlines()[0]} | {ad['url']}")
            continue
        if push(client, env, title, message, click=ad["url"], priority=int(cfg["alert_priority"]),
                attach=ad["image"] or None):
            con.execute("UPDATE ads SET notified_at = ? WHERE id = ?", (iso(utcnow()), ad["id"]))
            sent += 1
        else:
            con.execute("UPDATE ads SET notify_attempts = notify_attempts + 1 WHERE id = ?", (ad["id"],))
        commit()

    if seeding and ok_feeds:
        meta_set(con, "seeded", iso(now))
    if ok_feeds and not meta_get(con, "startup_push_sent"):
        hits = con.execute("SELECT COUNT(*) FROM ads WHERE seed = 1 AND verdict = 'match'").fetchone()[0]
        msg = (f"Ab jetzt kommt jedes neue Bett {width}x{length} in Karlsruhe sofort hierher. "
               f"{hits} passende Anzeigen standen schon drin; tippen für alle aktuellen.")
        if dry_run:
            print(f"[dry-run] PUSH Bett-Wächter läuft | {msg}")
        elif push(client, env, "Bett-Wächter läuft", msg, click=cfg["browse_url"], priority=3,
                  tags=["bed", "white_check_mark"]):
            meta_set(con, "startup_push_sent", iso(utcnow()))

    ok = ok_feeds == len(feeds) and not blocked
    if ok:
        meta_set(con, "backoff_level", "0")
    record_health(client, con, env, ok, "; ".join(failures), dry_run)
    commit()
    log(f"cycle: {ok_feeds}/{len(feeds)} feeds, {len(new_ids)} neu, {fetched} Anzeigenseiten, "
        f"{sent} Push(es)" + (" [Erstlauf]" if seeding else "") + (" [dry-run]" if dry_run else "")
        + (f" FEHLER: {'; '.join(failures)}" if failures else ""))
    if dry_run:
        con.rollback()
    return 0 if ok else 1


def acquire_lock() -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if LOCK_PATH.exists() and time.time() - LOCK_PATH.stat().st_mtime < LOCK_STALE_MIN * 60:
            return False
        LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")
        return True
    except OSError:
        return False


# ------------------------------------------------------------------ commands

def init_topic() -> int:
    env = load_env()
    if env.get("NTFY_TOPIC"):
        print(f"NTFY_TOPIC steht schon: {env['NTFY_TOPIC']}")
        return 0
    # Short enough to type into the ntfy app. The pushes carry only public
    # ad text, so the name needs to be unlisted, not secret.
    topic = "betten-ka-" + secrets.token_hex(3)
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    lines.append(f"NTFY_TOPIC={topic}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Neues Topic: {topic}\nIn der ntfy-App abonnieren: + -> Topic-Name {topic} (Server ntfy.sh)")
    return 0


def print_status(con: sqlite3.Connection, env: dict) -> None:
    print(f"Topic: {env.get('NTFY_TOPIC') or 'FEHLT'}")
    for k in ("seeded", "last_cycle", "last_ok", "fail_streak", "last_fail_reason",
              "backoff_until", "health_alert_open"):
        print(f"  {k}: {meta_get(con, k)}")
    print("Anzeigen nach Urteil:")
    for row in con.execute("SELECT COALESCE(verdict, 'wartet') v, COUNT(*) n FROM ads GROUP BY v ORDER BY n DESC"):
        print(f"  {row['v']}: {row['n']}")
    print("Letzte Treffer:")
    for ad in con.execute("SELECT * FROM ads WHERE verdict = 'match' ORDER BY first_seen DESC LIMIT 10"):
        state = "gemeldet " + ad["notified_at"] if ad["notified_at"] else ("Bestand" if ad["seed"] else "NICHT gemeldet")
        print(f"  {ad['id']} {ad['price_text'] or '':>10} {(ad['title'] or '')[:55]:55} [{ad['evidence']}] {state}")


def main() -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--cycle", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--test-notify", action="store_true")
    g.add_argument("--init-topic", action="store_true")
    g.add_argument("--status", action="store_true")
    g.add_argument("--check", metavar="TEXT")
    args = ap.parse_args()

    if args.init_topic:
        return init_topic()
    cfg, env = load_config(), load_env()
    if args.check:
        m = cfg["match"]
        print("Bett:", bed_verdict(args.check, args.check))
        print("Maß:", size_verdict(args.check, m["width_cm"], m["length_cm"]))
        print("Stauraum:", storage_verdict(args.check))
        return 0
    if args.status:
        print_status(db_connect(), env)
        return 0
    with httpx.Client() as client:
        if args.test_notify:
            ok = push(client, env, "Bett-Wächter: Test",
                      "Wenn das hier ankommt, kommen auch die Bett-Alarme an.",
                      click=cfg["browse_url"], priority=3)
            print("gesendet" if ok else "NICHT gesendet (siehe Log)")
            return 0 if ok else 1
        if not acquire_lock():
            log("Ein anderer Lauf ist aktiv; übersprungen")
            return 0
        try:
            return run_cycle(client, db_connect(), cfg, env, dry_run=args.dry_run)
        finally:
            LOCK_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
