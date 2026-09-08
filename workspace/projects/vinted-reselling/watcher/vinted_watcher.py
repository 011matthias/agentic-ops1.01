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
import base64
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

# Kids' items are a different market; logged but never alerted, and kept out
# of comp pools where their lower prices drag an adult median down.
#
# The age-unit list is data-derived, not guessed: Vinted spells kids sizes as
# "24-36 Monate / 92", "12 Jahre / 152", so the size field names the unit
# outright. The v1 list carried the year-words but not the month-words, and
# every kids item that reached a phone alert (15 of 360 on 2026-09-08) was a
# "Monate" size. Numeric size ladders are deliberately NOT used: "W34 | DE 50"
# is an adult men's size that any 50-176 cm ladder test would misread.
KID_MARKERS = re.compile(
    r"enfant|kinder|kids|girls|boys|fille|gar[cç]on|bambin|b[eé]b[eé]|baby|junior|bimb[oa]"
    r"|\d+\s*(jahre|jaar|anni|ans\b|yrs|years|monate|monaten|mois|maanden|mesi|months|mnd)"
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


def is_kid_item(title: str | None, size: str | None) -> int:
    """1 when title or size marks this as children's clothing."""
    return 1 if KID_MARKERS.search(f"{title or ''} {size or ''}".lower()) else 0

RECHECK_INTERVAL_MIN = 60
RECHECK_BATCH = 25
RECHECK_MIN_AGE_H = 24
GONE_RATE_CEILING = 0.40   # a batch reading gone above this is systemic, not sales
STALE_ALERT_MIN = 45       # no successful poll this long -> tell the operator
STALE_RENAG_H = 6          # keep reminding while an outage continues

# A URL that has left the item page for a login/consent/challenge screen.
WALL_URL = re.compile(r"/login|/member/general|captcha|challenge|consent", re.I)

# Only an explicit machine-readable sold flag counts. The bare word "Verkauft"
# appears in ordinary German page chrome, so matching it would mark live
# listings sold, corrupting outcome data in the opposite direction.
SOLD_MARKER = re.compile(r"is_sold(&quot;|\")?\s*:\s*true", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(value: str | None) -> datetime | None:
    """Parse a stored UTC stamp; None when absent or malformed.

    Never raises: a corrupt meta row must not be able to crash a cycle,
    which is how a wedged state used to become permanent.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


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
    is_kid INTEGER DEFAULT 0,
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
    gone_source TEXT,
    sold_flag INTEGER DEFAULT 0,
    alerted INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""

# Indexes are created only AFTER migrate() has added any columns an older
# database predates: CREATE INDEX names its columns, so building it first
# fails outright on a database that has not caught up yet.
DDL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_listings_comp ON listings (search_tag, brand, cond_tier, garment_class);
"""


ADDED_COLUMNS = {                       # column -> DDL fragment, applied to old DBs
    "garment_class": "TEXT",
    "is_kid": "INTEGER DEFAULT 0",
    "gone_source": "TEXT",
}


def migrate(con: sqlite3.Connection) -> None:
    """Add columns an older database predates.

    CREATE TABLE IF NOT EXISTS silently does nothing when the table already
    exists, so a new column would otherwise only reach a fresh database. The
    v1 garment_class column was added by deleting the database, which is not
    an option now that it holds real market history.
    """
    have = {row[1] for row in con.execute("PRAGMA table_info(listings)")}
    for column, decl in ADDED_COLUMNS.items():
        if column not in have:
            con.execute(f"ALTER TABLE listings ADD COLUMN {column} {decl}")
            log(f"migrated: added listings.{column}")
            if column == "is_kid":
                for row_id, title, size in con.execute(
                        "SELECT id, title, size FROM listings").fetchall():
                    if is_kid_item(title, size):
                        con.execute("UPDATE listings SET is_kid=1 WHERE id=?", (row_id,))
            elif column == "garment_class":
                for row_id, title in con.execute("SELECT id, title FROM listings").fetchall():
                    con.execute("UPDATE listings SET garment_class=? WHERE id=?",
                                (garment_class(title), row_id))
            con.commit()


def db_connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(DDL)
    migrate(con)
    con.executescript(DDL_INDEXES)
    return con


def meta_get(con: sqlite3.Connection, k: str) -> str | None:
    row = con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return row[0] if row else None


def meta_set(con: sqlite3.Connection, k: str, v: str) -> None:
    con.execute("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))


# ------------------------------------------------------------------- session

TOKEN_COOKIE = "access_token_web"
TOKEN_MARGIN_MIN = 45   # renew this long before the token's own expiry
AUTH_BACKOFF_MIN = 10   # 401: auth hiccup, self-healing, retry soon
WALL_BACKOFF_MIN = 60   # 403: bot wall, stay away
MAX_BACKOFF_MIN = 360   # ceiling for repeated walls


def jwt_expiry(token: str) -> datetime | None:
    """Expiry claim of a JWT as an aware datetime; None if unreadable.

    Never raises: an unreadable token is treated as "no usable session",
    which routes to a refresh rather than to a crash.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload))["exp"]
        return datetime.fromtimestamp(int(exp), timezone.utc)
    except Exception:
        return None


def cookie_value(client: httpx.Client, name: str) -> str | None:
    """Read a cookie by name, tolerating duplicates across domains.

    httpx's Cookies.get() raises CookieConflict when the same name exists on
    two domains, which Vinted produces routinely (.vinted.de and
    .www.vinted.de). Raising inside a session check would crash the cycle at
    the exact moment the session needs renewing, so read the jar directly and
    take the most recent entry.
    """
    hits = [c.value for c in client.cookies.jar if c.name == name]
    return hits[-1] if hits else None


def token_is_fresh(client: httpx.Client, margin_min: int = TOKEN_MARGIN_MIN) -> bool:
    """True when the jar holds an access token good for at least margin_min."""
    token = cookie_value(client, TOKEN_COOKIE)
    if not token:
        return False
    exp = jwt_expiry(token)
    if exp is None:
        return False
    return exp > datetime.now(timezone.utc) + timedelta(minutes=margin_min)


def save_cookies(client: httpx.Client) -> None:
    """Persist the jar with domain and path intact.

    The v1 format was a bare {name: value} dict, which lost the domain and
    reloaded every cookie onto .vinted.de even though the server sets
    refresh_token_web on .www.vinted.de. load_cookies still reads that shape.
    """
    jar = [
        {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path or "/"}
        for c in client.cookies.jar
    ]
    COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_PATH.write_text(json.dumps(jar))


def load_cookies(client: httpx.Client) -> None:
    try:
        raw = json.loads(COOKIE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return
    if isinstance(raw, dict):                       # legacy {name: value}
        for name, value in raw.items():
            client.cookies.set(name, value, domain=".vinted.de")
        return
    for c in raw:
        try:
            client.cookies.set(c["name"], c["value"], domain=c.get("domain") or ".vinted.de",
                               path=c.get("path") or "/")
        except (KeyError, TypeError):
            continue


def new_client() -> httpx.Client:
    client = httpx.Client(
        headers={"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9"},
        timeout=25,
        follow_redirects=True,
    )
    if COOKIE_PATH.exists():
        load_cookies(client)
    return client


def refresh_session(client: httpx.Client) -> bool:
    """Mint a NEW anonymous session, clean slate. Returns success.

    The jar is CLEARED first, and that clearing is the whole fix. Vinted
    reissues no token when a stale one is presented: the homepage answers
    200 and leaves the expired cookie untouched, so the old
    refresh-then-retry path could never recover. A 24h token expiry on
    2026-09-07 therefore became a 46h silent outage, every cycle retrying
    with the same dead token and backing off again.
    """
    client.cookies.clear()
    r = client.get(BASE + "/")
    r.raise_for_status()
    if not token_is_fresh(client, margin_min=0):
        log("WARN: refresh returned no usable access token")
        return False
    save_cookies(client)
    exp = jwt_expiry(cookie_value(client, TOKEN_COOKIE) or "")
    log(f"session refreshed (token valid until {exp:%Y-%m-%dT%H:%M:%SZ})" if exp else "session refreshed")
    return True


def ensure_session(client: httpx.Client) -> bool:
    """Renew proactively, before expiry, rather than waiting for a 401."""
    if token_is_fresh(client):
        return True
    return refresh_session(client)


class SessionWall(Exception):
    """Raised when the remote has said no. Ends the cycle immediately."""


def set_backoff(con: sqlite3.Connection, minutes: int, why: str, escalate: bool = False) -> None:
    if escalate:
        level = int(meta_get(con, "backoff_level") or 0) + 1
        minutes = min(minutes * (2 ** (level - 1)), MAX_BACKOFF_MIN)
        meta_set(con, "backoff_level", str(level))
    until = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta_set(con, "backoff_until", until)
    con.commit()
    log(f"WARN: {why}; backing off until {until}")


def api_get(client: httpx.Client, con: sqlite3.Connection, url: str, params: dict) -> dict:
    """GET a catalog API URL, healing an expired session once.

    401 and 403 mean different things and get different treatment. A 401 is
    an expired token: clean-slate refresh, retry, and on a second failure
    back off only briefly, because the condition is self-healing. A 403 is
    the bot wall; no refresh helps, so back off hard, escalating if it
    repeats.

    Either way the failure raises SessionWall rather than returning, so the
    cycle STOPS. Returning None merely skipped one search and let the
    remaining eight fire two requests each into a wall that had already
    said no.
    """
    for attempt in (1, 2):
        r = client.get(url, params=params, headers={"Accept": "application/json"})
        if r.status_code in (403, 429):
            wait = WALL_BACKOFF_MIN
            retry_after = r.headers.get("retry-after")
            if retry_after and retry_after.isdigit():
                wait = max(wait, int(retry_after) // 60 + 1)
            set_backoff(con, wait, f"{r.status_code} (bot wall)", escalate=True)
            raise SessionWall(f"HTTP {r.status_code}")
        if r.status_code == 401:
            if attempt == 1 and refresh_session(client):
                continue
            set_backoff(con, AUTH_BACKOFF_MIN, "401 after clean-slate refresh")
            raise SessionWall("HTTP 401")
        r.raise_for_status()
        if "json" not in r.headers.get("content-type", ""):
            # An HTML body on a 200 is an interstitial, not data. Parsing it
            # would raise; treating it as a wall is what it actually is.
            set_backoff(con, WALL_BACKOFF_MIN, "HTML body where JSON expected", escalate=True)
            raise SessionWall("non-JSON body")
        return r.json()
    raise SessionWall("unreachable")


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
        "is_kid": is_kid_item(item.get("title"), item.get("size_title")),
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
        # Seeing a listing in a live search result disproves any earlier
        # "gone" verdict, so clear it. Without this a row wrongly marked gone
        # stayed gone forever, and the outcome data could never self-correct.
        con.execute(
            "UPDATE listings SET last_seen=?, favourites=?, views=?, price=?, total_price=?, "
            "gone_at=NULL, gone_source=NULL, sold_flag=0 WHERE id=?",
            (ts, rec["favourites"], rec["views"], rec["price"], rec["total_price"], rec["id"]),
        )
        return False
    con.execute(
        """INSERT INTO listings (id, search_tag, title, brand, size, condition, cond_tier,
               garment_class, is_kid, price, total_price, currency, url, photo_url, seller_id,
               seller_login, favourites, views, promoted, seed, first_seen, last_seen)
           VALUES (:id, :search_tag, :title, :brand, :size, :condition, :cond_tier,
               :garment_class, :is_kid, :price, :total_price, :currency, :url, :photo_url, :seller_id,
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
    if rec["is_kid"]:
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
                 AND last_seen>=? AND total_price BETWEEN 3 AND 400
                 AND COALESCE(is_kid,0)=0""",
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

def poll_search(client: httpx.Client, con: sqlite3.Connection, search: dict, settings: dict,
                env: dict) -> bool:
    """Poll one search. Returns True when the API actually answered."""
    tag = search["tag"]
    seeded = meta_get(con, f"seeded:{tag}")
    url = BASE + "/api/v2/catalog/items"

    if not seeded:
        for page in range(1, settings["seed_pages"] + 1):
            data = api_get(client, con, url, {
                "search_text": search["query"], "per_page": settings["seed_per_page"], "page": page,
            })
            for item in data.get("items", []):
                upsert(con, parse_item(item, tag, seed=1))
            time.sleep(random.uniform(1.5, 3.5))
        meta_set(con, f"seeded:{tag}", now_iso())
        con.commit()
        log(f"seeded {tag}")
        return True

    data = api_get(client, con, url, {
        "search_text": search["query"], "per_page": settings["poll_per_page"],
        "page": 1, "order": "newest_first",
    })
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
    return True


def recheck_gone(client: httpx.Client, con: sqlite3.Connection, session_proven: bool = False) -> None:
    """Hourly: revisit stale listings to detect sold/removed (sell-speed data).

    Heuristic, marked as such: 404/410 or a redirect off the item page counts
    as gone; a 200 item page containing a sold marker sets sold_flag. A live
    item page bumps last_seen so it is not rechecked again for 24h.
    """
    last = parse_ts(meta_get(con, "last_recheck"))
    if last and last > datetime.now(timezone.utc) - timedelta(minutes=RECHECK_INTERVAL_MIN):
        return
    if not (session_proven and token_is_fresh(client, margin_min=0)):
        # A dead session redirects item pages to a login wall, which this
        # function used to read as "sold": that is how all 375 outcome rows
        # in the database came to be fabricated between 2026-09-07 and
        # 2026-09-08. Outcome data is the whole asset here, so a session that
        # has not just answered a real API call earns no verdicts at all.
        log("recheck skipped: session not proven this cycle")
        return
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=RECHECK_MIN_AGE_H)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = con.execute(
        """SELECT id, url FROM listings WHERE gone_at IS NULL AND last_seen < ?
           ORDER BY last_seen ASC LIMIT ?""",
        (cutoff, RECHECK_BATCH),
    ).fetchall()
    verdicts = []      # (item_id, gone: bool, sold: bool, source: str)
    for item_id, item_url in rows:
        if not item_url:
            continue
        try:
            r = client.get(item_url)
        except httpx.HTTPError:
            continue
        final = str(r.url)
        if r.status_code in (404, 410):
            verdicts.append((item_id, True, False, str(r.status_code)))
        elif "/items/" not in final or WALL_URL.search(final):
            # Bounced off the item page. That is a statement about our
            # session, not about the listing, and it is unknowable which.
            # Abandon the pass with nothing written.
            log(f"WARN: item page bounced to {final}; recheck abandoned, nothing recorded")
            meta_set(con, "last_recheck", now_iso())
            con.commit()
            return
        elif r.status_code == 200:
            sold = bool(SOLD_MARKER.search(r.text))
            verdicts.append((item_id, sold, sold, "sold_marker" if sold else "alive"))
        time.sleep(random.uniform(1.5, 3.0))

    gone_n = sum(1 for _, g, _, _ in verdicts if g)
    if verdicts and gone_n / len(verdicts) > GONE_RATE_CEILING:
        # The batch is drawn from the OLDEST listings not yet marked gone, and
        # those turn over slowly; a large simultaneous sweep is a session
        # symptom every time, never a market event. Discard rather than
        # poison the outcome data.
        log(f"WARN: recheck discarded, {gone_n}/{len(verdicts)} read as gone "
            f"(> {GONE_RATE_CEILING:.0%} is systemic, not sales)")
        meta_set(con, "last_recheck", now_iso())
        con.commit()
        return

    ts = now_iso()
    for item_id, gone, sold, source in verdicts:
        if gone:
            con.execute("UPDATE listings SET gone_at=?, sold_flag=?, gone_source=? WHERE id=?",
                        (ts, 1 if sold else 0, source, item_id))
        else:
            con.execute("UPDATE listings SET last_seen=? WHERE id=?", (ts, item_id))
    meta_set(con, "last_recheck", ts)
    con.commit()
    if rows:
        log(f"recheck: {len(rows)} visited, {gone_n} gone")


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


def check_liveness(con: sqlite3.Connection, env: dict) -> None:
    """Tell the operator when the watcher has stopped collecting.

    The 2026-09-07 outage ran 46 hours unnoticed because the scheduled task
    kept reporting success while every poll failed. Silence from a market
    watcher is indistinguishable from a quiet market, so the watcher has to
    say so itself. One alert per outage, re-armed on recovery.
    """
    last = parse_ts(meta_get(con, "last_success"))
    if last is None:
        return
    stale_min = int((datetime.now(timezone.utc) - last).total_seconds() // 60)
    if stale_min < STALE_ALERT_MIN:
        if meta_get(con, "stale_alerted"):
            meta_set(con, "stale_alerted", "")
            con.commit()
            log(f"recovered after {stale_min} min without data")
        return
    alerted_at = parse_ts(meta_get(con, "stale_alerted"))
    if alerted_at and alerted_at > datetime.now(timezone.utc) - timedelta(hours=STALE_RENAG_H):
        return      # already told; nag again only every STALE_RENAG_H hours
    notify(env, "Vinted watcher steht",
           f"Seit {stale_min} min keine neuen Daten. Letzter Erfolg: "
           f"{last:%Y-%m-%d %H:%M}Z. Log pruefen.",
           priority=5)
    meta_set(con, "stale_alerted", now_iso())
    con.commit()
    log(f"WARN: no successful poll for {stale_min} min; operator alerted")


def run_cycle() -> int:
    """One poll cycle. Returns a process exit code (0 ok, 1 collected nothing)."""
    if not acquire_lock():
        return 0
    con = None
    try:
        cfg = load_config()
        env = load_env()
        con = db_connect()
        check_liveness(con, env)
        backoff = parse_ts(meta_get(con, "backoff_until"))
        if backoff and backoff > datetime.now(timezone.utc):
            log(f"cycle skipped: in backoff until {backoff:%Y-%m-%dT%H:%M:%SZ}")
            return 1
        client = new_client()
        if not ensure_session(client):
            log("WARN: could not establish a session")
            set_backoff(con, AUTH_BACKOFF_MIN, "no session could be established")
            return 1
        ok = False
        try:
            for search in cfg["searches"]:
                try:
                    if poll_search(client, con, search, cfg["settings"], env):
                        ok = True
                except SessionWall:
                    raise
                except (httpx.HTTPError, sqlite3.Error, ValueError, KeyError) as e:
                    # One bad search must not cost the other eight.
                    log(f"WARN: {search['tag']} failed: {type(e).__name__}: {e}")
                time.sleep(random.uniform(1.5, 3.5))
        except SessionWall as e:
            log(f"cycle aborted: {e}")
            return 1
        if ok:
            # A poll got through, so whatever caused an earlier backoff is
            # over; leaving it set would skip cycles for no reason.
            meta_set(con, "last_success", now_iso())
            con.execute("DELETE FROM meta WHERE k IN ('backoff_until','backoff_level')")
            con.commit()
        try:
            recheck_gone(client, con, session_proven=ok)
        except SessionWall as e:
            log(f"recheck aborted: {e}")
        return 0 if ok else 1
    finally:
        if con is not None:
            con.close()
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
    last = parse_ts(meta_get(con, "last_success"))
    if last:
        stale = int((datetime.now(timezone.utc) - last).total_seconds() // 60)
        state = "OK" if stale < STALE_ALERT_MIN else "STALLED"
        print(f"health: {state}  last success {last:%Y-%m-%dT%H:%M:%SZ} ({stale} min ago)")
    else:
        print("health: no successful cycle recorded yet")
    backoff = parse_ts(meta_get(con, "backoff_until"))
    if backoff and backoff > datetime.now(timezone.utc):
        print(f"        in backoff until {backoff:%Y-%m-%dT%H:%M:%SZ}")
    if COOKIE_PATH.exists():
        try:
            c = new_client()
            exp = jwt_expiry(cookie_value(c, TOKEN_COOKIE) or "")
            c.close()
            print(f"        session token expires {exp:%Y-%m-%dT%H:%M:%SZ}" if exp
                  else "        session token unreadable")
        except Exception:
            pass
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
    sys.exit(run_cycle())


if __name__ == "__main__":
    main()
