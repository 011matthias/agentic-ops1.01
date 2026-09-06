# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "pyyaml>=6.0"]
# ///
"""Vinted sourcing watcher + price/demand database.

Polls the Vinted catalog API (unofficial, anonymous public-scope session)
for the saved searches in searches.yaml, records every listing seen into
a local SQLite database, scores new listings against accumulated comps,
and pushes deal alerts via ntfy.sh.

The database is the asset: asking prices on insert, favourite/view
deltas on re-sight, and gone-detection (sold-speed proxy) on recheck.

Modes:
  --cycle        one poll cycle over all searches (default; scheduled task entry)
  --test-notify  send a test push to the configured ntfy topic
  --status       print row counts and per-search state
"""

import argparse
import json
import random
import re
import sqlite3
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "vinted.db"
COOKIE_PATH = DATA_DIR / "cookies.json"
LOCK_PATH = DATA_DIR / "cycle.lock"
ENV_PATH = PROJECT_DIR / "context" / ".env"
CONFIG_PATH = SCRIPT_DIR / "searches.yaml"

BASE = "https://www.vinted.de"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

COND_TIERS = {
    "neu mit etikett": "new_tag",
    "neu ohne etikett": "new",
    "sehr gut": "very_good",
    "gut": "good",
    "zufriedenstellend": "fair",
}

# Listings whose title suggests damage or junk are logged but never alerted.
TITLE_BLACKLIST = ["defekt", "kaputt", "loch ", "löcher", "fleck", "bastler", "fake", "replik"]

# Kids' items are a different market; logged but never alerted.
KID_MARKERS = re.compile(
    r"enfant|kinder|kids|girls|boys|fille|gar[cç]on|bambin|b[eé]b[eé]|baby|junior"
    r"|\d+\s*(jahre|jaar|anni|ans\b|yrs|years)"
)

# Comp pools mix apples and oranges without a garment class: a cap scored
# against a jacket median always looks like a deal. Class is derived from the
# title (multilingual keywords, first matching class wins, order matters:
# sweater before jacket catches Sweatjacke/veste polaire, shorts before pants
# catches cargo shorts). Class "other" (bags, caps, shoes) never alerts.
GARMENT_CLASSES: list[tuple[str, re.Pattern]] = [
    ("sweater", re.compile(r"hoodie|hoody|sweat|felpa|pull|strick|trui|fleece|polaire|kapuze")),
    ("shorts", re.compile(r"short|bermuda|pantaloncini")),
    ("pants", re.compile(r"hose|pants|pant\b|jean|pantalon|broek|pantaloni|jogging|legging|chino|cargo")),
    ("jacket", re.compile(r"jacke|jacket|veste|jas\b|giacca|blouson|doudoune|parka|mantel|coat\b|weste|gilet")),
    ("dress", re.compile(r"kleid|dress|robe\b|rock\b|jupe|gonna|vestito")),
    ("shirt", re.compile(r"t-shirt|tshirt|tee\b|shirt|maglietta|maglia|polo\b|hemd|chemise|camicia|bluse|blouse|top\b")),
]

MAX_ALERTS_PER_SEARCH = 3   # per cycle; a real steady-state cycle has 0-2 candidates
BACKLOG_SUPPRESS = 15       # more new items than this = catch-up cycle, data only


def garment_class(title: str | None) -> str:
    t = (title or "").lower()
    for cls, pat in GARMENT_CLASSES:
        if pat.search(t):
            return cls
    return "other"

RECHECK_INTERVAL_MIN = 60
RECHECK_BATCH = 25
RECHECK_MIN_AGE_H = 24


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{now_iso()}] {msg}")


# ---------------------------------------------------------------- config / env

def load_config() -> dict:
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg.setdefault("settings", {})
    s = cfg["settings"]
    s.setdefault("deal_ratio", 0.62)
    s.setdefault("min_comps", 6)
    s.setdefault("comp_window_days", 45)
    s.setdefault("min_price", 5.0)
    s.setdefault("poll_per_page", 48)
    s.setdefault("seed_pages", 2)
    s.setdefault("seed_per_page", 96)
    return cfg


def load_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


# ------------------------------------------------------------------------- db

DDL = """
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY,
    search_tag TEXT NOT NULL,
    title TEXT,
    brand TEXT,
    size TEXT,
    condition TEXT,
    cond_tier TEXT,
    garment_class TEXT,
    price REAL,
    total_price REAL,
    currency TEXT,
    url TEXT,
    photo_url TEXT,
    seller_id INTEGER,
    seller_login TEXT,
    favourites INTEGER,
    views INTEGER,
    promoted INTEGER,
    seed INTEGER DEFAULT 0,
    first_seen TEXT,
    last_seen TEXT,
    gone_at TEXT,
    sold_flag INTEGER DEFAULT 0,
    alerted INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_listings_comp ON listings (search_tag, brand, cond_tier, garment_class);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


def db_connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(DDL)
    return con


def meta_get(con: sqlite3.Connection, k: str) -> str | None:
    row = con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return row[0] if row else None


def meta_set(con: sqlite3.Connection, k: str, v: str) -> None:
    con.execute("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))


# ------------------------------------------------------------------- session

def new_client() -> httpx.Client:
    client = httpx.Client(
        headers={"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9"},
        timeout=25,
        follow_redirects=True,
    )
    if COOKIE_PATH.exists():
        try:
            for name, value in json.loads(COOKIE_PATH.read_text()).items():
                client.cookies.set(name, value, domain=".vinted.de")
        except (json.JSONDecodeError, OSError):
            pass
    return client


def refresh_session(client: httpx.Client) -> None:
    r = client.get(BASE + "/")
    r.raise_for_status()
    COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_PATH.write_text(json.dumps(dict(client.cookies)))
    log("session refreshed")


def api_get(client: httpx.Client, con: sqlite3.Connection, url: str, params: dict) -> dict | None:
    """GET a catalog API URL; refresh the anonymous session once on 401/403.

    A second 401/403 sets a one-hour backoff so a bot-wall never gets hammered.
    """
    for attempt in (1, 2):
        r = client.get(url, params=params, headers={"Accept": "application/json"})
        if r.status_code in (401, 403):
            if attempt == 1:
                refresh_session(client)
                continue
            until = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            meta_set(con, "backoff_until", until)
            con.commit()
            log(f"WARN: {r.status_code} after refresh; backing off until {until}")
            return None
        r.raise_for_status()
        return r.json()
    return None


# ------------------------------------------------------------------- parsing

def parse_item(item: dict, tag: str, seed: int) -> dict:
    price = float((item.get("price") or {}).get("amount") or 0)
    total = float((item.get("total_item_price") or {}).get("amount") or price)
    cond = (item.get("status") or "").strip()
    photo = item.get("photo") or {}
    photos = item.get("photos") or []
    photo_url = photo.get("url") or (photos[0].get("url") if photos else None)
    user = item.get("user") or {}
    return {
        "id": item["id"],
        "search_tag": tag,
        "title": item.get("title"),
        "brand": (item.get("brand_title") or "").strip(),
        "size": item.get("size_title"),
        "condition": cond,
        "cond_tier": COND_TIERS.get(cond.lower(), "unknown"),
        "garment_class": garment_class(item.get("title")),
        "price": price,
        "total_price": total,
        "currency": (item.get("price") or {}).get("currency_code", "EUR"),
        "url": item.get("url"),
        "photo_url": photo_url,
        "seller_id": user.get("id"),
        "seller_login": user.get("login"),
        "favourites": item.get("favourite_count", 0),
        "views": item.get("view_count", 0),
        "promoted": 1 if item.get("promoted") else 0,
        "seed": seed,
    }


def upsert(con: sqlite3.Connection, rec: dict) -> bool:
    """Insert or refresh a listing. Returns True when the id was new."""
    ts = now_iso()
    existing = con.execute("SELECT id FROM listings WHERE id=?", (rec["id"],)).fetchone()
    if existing:
        con.execute(
            "UPDATE listings SET last_seen=?, favourites=?, views=?, price=?, total_price=? WHERE id=?",
            (ts, rec["favourites"], rec["views"], rec["price"], rec["total_price"], rec["id"]),
        )
        return False
    con.execute(
        """INSERT INTO listings (id, search_tag, title, brand, size, condition, cond_tier,
               garment_class, price, total_price, currency, url, photo_url, seller_id,
               seller_login, favourites, views, promoted, seed, first_seen, last_seen)
           VALUES (:id, :search_tag, :title, :brand, :size, :condition, :cond_tier,
               :garment_class, :price, :total_price, :currency, :url, :photo_url, :seller_id,
               :seller_login, :favourites, :views, :promoted, :seed, :first_seen, :last_seen)""",
        {**rec, "first_seen": ts, "last_seen": ts},
    )
    return True


# ------------------------------------------------------------------- scoring

def score_and_alert(con: sqlite3.Connection, rec: dict, search: dict, settings: dict, env: dict) -> bool:
    """Score one new listing against its comp pool; push at most one alert.

    Returns True when an alert was sent (caller enforces the per-cycle cap).
    Comp pool = same search tag + brand + condition tier + garment class,
    within the comp window. Class "other" (bags, caps, shoes) never alerts.
    """
    if rec["price"] < settings["min_price"]:
        return False
    price_max = search.get("price_max")
    if price_max and rec["total_price"] > price_max:
        return False
    if rec["garment_class"] == "other":
        return False
    title_l = (rec["title"] or "").lower()
    if any(w in title_l for w in TITLE_BLACKLIST):
        return False
    size_l = (rec["size"] or "").lower()
    if KID_MARKERS.search(title_l) or KID_MARKERS.search(size_l):
        return False
    if not rec["brand"] or rec["cond_tier"] == "unknown":
        return False
    window = (datetime.now(timezone.utc) - timedelta(days=settings["comp_window_days"])).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    comps = [
        row[0]
        for row in con.execute(
            """SELECT total_price FROM listings
               WHERE search_tag=? AND brand=? AND cond_tier=? AND garment_class=? AND id!=?
                 AND last_seen>=? AND total_price BETWEEN 3 AND 400""",
            (rec["search_tag"], rec["brand"], rec["cond_tier"], rec["garment_class"],
             rec["id"], window),
        ).fetchall()
    ]
    if len(comps) < settings["min_comps"]:
        return False
    med = statistics.median(comps)
    if rec["total_price"] > settings["deal_ratio"] * med:
        return False
    pct = round(100 * (1 - rec["total_price"] / med))
    msg = (
        f"{rec['brand']} | {rec['condition']} | Gr. {rec['size']} | {rec['garment_class']}\n"
        f"{rec['total_price']:.2f} EUR inkl. Gebuehr, Median vergleichbar {med:.2f} EUR ({pct}% drunter)\n"
        f"{len(comps)} Vergleichsangebote im Fenster"
    )
    if notify(env, title=f"Deal: {rec['title']}", message=msg, click=rec["url"]):
        con.execute("UPDATE listings SET alerted=1 WHERE id=?", (rec["id"],))
        log(f"ALERT sent: {rec['id']} {rec['title']} @ {rec['total_price']}")
        return True
    return False


def notify(env: dict, title: str, message: str, click: str | None = None, priority: int = 4) -> bool:
    topic = env.get("NTFY_TOPIC")
    if not topic:
        log("WARN: NTFY_TOPIC not configured; alert not sent")
        return False
    body = {"topic": topic, "title": title, "message": message, "priority": priority, "tags": ["shirt"]}
    if click:
        body["click"] = click
    try:
        r = httpx.post("https://ntfy.sh/", json=body, timeout=15)
        return r.status_code == 200
    except httpx.HTTPError as e:
        log(f"WARN: ntfy send failed: {e}")
        return False


# -------------------------------------------------------------------- cycle

def poll_search(client: httpx.Client, con: sqlite3.Connection, search: dict, settings: dict, env: dict) -> None:
    tag = search["tag"]
    seeded = meta_get(con, f"seeded:{tag}")
    url = BASE + "/api/v2/catalog/items"

    if not seeded:
        for page in range(1, settings["seed_pages"] + 1):
            data = api_get(client, con, url, {
                "search_text": search["query"], "per_page": settings["seed_per_page"], "page": page,
            })
            if data is None:
                return
            for item in data.get("items", []):
                upsert(con, parse_item(item, tag, seed=1))
            time.sleep(random.uniform(1.5, 3.5))
        meta_set(con, f"seeded:{tag}", now_iso())
        con.commit()
        log(f"seeded {tag}")
        return

    data = api_get(client, con, url, {
        "search_text": search["query"], "per_page": settings["poll_per_page"],
        "page": 1, "order": "newest_first",
    })
    if data is None:
        return
    new_recs = []
    for item in data.get("items", []):
        rec = parse_item(item, tag, seed=0)
        if upsert(con, rec):
            new_recs.append(rec)
    if len(new_recs) > BACKLOG_SUPPRESS:
        # Catch-up after a gap (PC off, first poll after seeding): these are
        # not fresh-this-minute listings, so alerting on them races nothing.
        # Record as comp data only.
        log(f"{tag}: {len(new_recs)} new listings (backlog catch-up, alerts suppressed)")
    else:
        alerts = 0
        for rec in new_recs:
            if alerts >= MAX_ALERTS_PER_SEARCH:
                break
            if score_and_alert(con, rec, search, settings, env):
                alerts += 1
        if new_recs:
            log(f"{tag}: {len(new_recs)} new listings, {alerts} alerted")
    con.commit()


def recheck_gone(client: httpx.Client, con: sqlite3.Connection) -> None:
    """Hourly: revisit stale listings to detect sold/removed (sell-speed data).

    Heuristic, marked as such: 404/410 or a redirect off the item page counts
    as gone; a 200 item page containing a sold marker sets sold_flag. A live
    item page bumps last_seen so it is not rechecked again for 24h.
    """
    last = meta_get(con, "last_recheck")
    if last and datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) > \
            datetime.now(timezone.utc) - timedelta(minutes=RECHECK_INTERVAL_MIN):
        return
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=RECHECK_MIN_AGE_H)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = con.execute(
        """SELECT id, url FROM listings WHERE gone_at IS NULL AND last_seen < ?
           ORDER BY last_seen ASC LIMIT ?""",
        (cutoff, RECHECK_BATCH),
    ).fetchall()
    gone = 0
    for item_id, item_url in rows:
        if not item_url:
            continue
        try:
            r = client.get(item_url)
        except httpx.HTTPError:
            continue
        ts = now_iso()
        if r.status_code in (404, 410) or "/items/" not in str(r.url):
            con.execute("UPDATE listings SET gone_at=? WHERE id=?", (ts, item_id))
            gone += 1
        elif r.status_code == 200:
            if re.search(r"Verkauft|is_sold&quot;:true|\"is_sold\":true", r.text):
                con.execute("UPDATE listings SET gone_at=?, sold_flag=1 WHERE id=?", (ts, item_id))
                gone += 1
            else:
                con.execute("UPDATE listings SET last_seen=? WHERE id=?", (ts, item_id))
        time.sleep(random.uniform(1.5, 3.0))
    meta_set(con, "last_recheck", now_iso())
    con.commit()
    if rows:
        log(f"recheck: {len(rows)} visited, {gone} gone")


def acquire_lock() -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        try:
            age = time.time() - LOCK_PATH.stat().st_mtime
            if age < 240:
                log("cycle skipped: previous run still fresh (lock < 4 min)")
                return False
        except OSError:
            pass
    LOCK_PATH.write_text(str(time.time()))
    return True


def run_cycle() -> None:
    if not acquire_lock():
        return
    try:
        cfg = load_config()
        env = load_env()
        con = db_connect()
        backoff = meta_get(con, "backoff_until")
        if backoff and datetime.strptime(backoff, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) > \
                datetime.now(timezone.utc):
            log(f"cycle skipped: in backoff until {backoff}")
            return
        client = new_client()
        if not COOKIE_PATH.exists():
            refresh_session(client)
        for search in cfg["searches"]:
            poll_search(client, con, search, cfg["settings"], env)
            time.sleep(random.uniform(1.5, 3.5))
        recheck_gone(client, con)
        con.close()
    finally:
        LOCK_PATH.unlink(missing_ok=True)


def print_status() -> None:
    con = db_connect()
    total, alerted = con.execute(
        "SELECT COUNT(*), COALESCE(SUM(alerted),0) FROM listings"
    ).fetchone()
    gone, sold = con.execute(
        "SELECT COUNT(*), COALESCE(SUM(sold_flag),0) FROM listings WHERE gone_at IS NOT NULL"
    ).fetchone()
    print(f"listings: {total}  alerted: {alerted}  gone: {gone}  (sold-flagged: {sold})")
    for tag, n, seeds in con.execute(
        "SELECT search_tag, COUNT(*), SUM(seed) FROM listings GROUP BY search_tag ORDER BY 2 DESC"
    ):
        seeded_at = meta_get(con, f"seeded:{tag}") or "-"
        print(f"  {tag:<18} rows={n:<5} seeds={seeds:<4} seeded_at={seeded_at}")
    con.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cycle", action="store_true", help="run one poll cycle (default)")
    ap.add_argument("--test-notify", action="store_true", help="send a test push")
    ap.add_argument("--status", action="store_true", help="print db state")
    args = ap.parse_args()
    if args.test_notify:
        ok = notify(load_env(), "Vinted watcher test",
                    "Wenn du das liest, funktioniert der Alert-Kanal.", click=BASE)
        print("test notify:", "sent" if ok else "FAILED")
        sys.exit(0 if ok else 1)
    if args.status:
        print_status()
        return
    run_cycle()


if __name__ == "__main__":
    main()
