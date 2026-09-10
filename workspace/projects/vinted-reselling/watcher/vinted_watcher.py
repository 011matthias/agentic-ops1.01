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
  --cycle          one poll cycle over all searches (default; scheduled task entry)
  --test-notify    send a test push to the configured ntfy topic
  --status         print row counts and per-search state
  --brand-report   weekly per-brand keep/drop/add evaluation
  --probe-fields   dump one raw catalog item (field census, nothing assumed)
  --probe-search   viability census for a candidate search before it gets a slot
  --image-check    reverse-image-search links for one listing
  --feedback       record a rating by hand: good | bad | bought
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
import urllib.parse
from collections import Counter
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

# Condition strings as the API actually spells them, not as the docs imply.
# The v1 table keyed on "neu mit etikett" / "neu ohne etikett"; the live API
# returns "Neu" and "Neu, mit Etikett" (with a comma). Neither matched, so
# every new-condition listing fell to "unknown" and was excluded from BOTH
# alerting and comp pools: 4,348 rows (14.9%) on 2026-09-08, and not one alert
# ever fired on new stock. cond_tier_of() normalises punctuation and case, so
# both spellings resolve; the DATA_FIXES entry repairs the stored rows.
COND_TIERS = {
    "neu mit etikett": "new_tag",
    "neu ohne etikett": "new",
    "neu": "new",
    "sehr gut": "very_good",
    "gut": "good",
    "zufriedenstellend": "fair",
}


def cond_tier_of(condition: str | None) -> str:
    """Map a Vinted condition string to a comp tier, punctuation-insensitive."""
    key = re.sub(r"[^a-zäöüß ]+", " ", (condition or "").lower())
    key = re.sub(r"\s+", " ", key).strip()
    return COND_TIERS.get(key, "unknown")

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
# What makes a cycle a catch-up run is the GAP since the last successful poll,
# not how many listings it returned. The first version keyed on count alone, and
# measurement against 29,433 real rows showed what that costs: the guard fired on
# 37% of cycles and 67% of all listings were never scored at all, because a busy
# search routinely returns 24 to 48 new items in an ordinary five minutes.
# nike-vintage was suppressed on 77% of its cycles, adidas-vintage 75%,
# tnf-jacke 62%. The scorer was effectively switched off for exactly the
# searches with the most turnover.
#
# The count still matters, but only once time says a gap really happened: after
# the watcher has been down for hours, a pile of listings IS stale, and alerting
# on it races nothing. Within the normal cadence the same pile is simply the
# market moving, and MAX_ALERTS_PER_SEARCH already keeps the phone civil.
BACKLOG_SUPPRESS = 15       # only applied when a real gap preceded the cycle
BACKLOG_GAP_MIN = 25        # minutes since last success that still count as steady state

# What a catch-up cycle may still alert on, by REAL posting time.
#
# The gate above assumed the pile after a gap is old. Measured on the
# 2026-09-10 morning batch, after the machine had slept 669 minutes, it is the
# opposite: of 456 listings collected, 48.9% were under 15 minutes old and
# 76.3% under 45, because page 1 holds the NEWEST 48 per search and the actual
# overnight backlog had long scrolled off it. So the old branch discarded the
# freshest listings of the morning, 223 of them under a quarter of an hour old,
# and kept nothing. Age is knowable now (posted_at, from the photo epoch), so
# the cycle scores what is genuinely fresh and suppresses only what is genuinely
# old. Unknown age stays suppressed during a catch-up: conservative by default.
CATCH_UP_FRESH_MIN = 45

# Which normalised size classes are allowed to reach the phone. The resale
# audience is widest here; everything else still lands in the database as comp
# data. Jeans searches override this per search (W26-W31 for women's denim),
# and edge classes like xl / DE 52 are a per-product config call fed by the
# size-demand column of --brand-report, not a mapping decision.
DEFAULT_SIZE_CLASSES = ["s", "m", "l", "w29", "w30", "w31", "w32", "w33", "w34"]


def garment_class(title: str | None) -> str:
    t = (title or "").lower()
    for cls, pat in GARMENT_CLASSES:
        if pat.search(t):
            return cls
    return "other"


def is_kid_item(title: str | None, size: str | None) -> int:
    """1 when title or size marks this as children's clothing."""
    return 1 if KID_MARKERS.search(f"{title or ''} {size or ''}".lower()) else 0


# The size field carries three incompatible notations at once: bare letters
# ("M"), the combined form ("S / 36 / 8", "M / 38 / 10"), the jeans form
# ("W32 | DE 48"), and kids ladders ("12 Jahre / 152"). 141 distinct strings on
# 2026-09-08, so the alert filter cannot key on the raw value. size_class_of()
# collapses them to one token per garment size. Two deliberate calls:
# the W token wins over the DE number in "W32 | DE 48" (a jeans buyer searches
# W32), and DE 46 resolves to men's s rather than women's xxl, because these
# searches are men's-inventory dominated. Mapping stays truthful (DE 52 is xl,
# not l); which classes actually alert is a config decision, not a mapping one.
SIZE_LETTERS = [
    ("xxl", re.compile(r"^(4xl|3xl|xxxl|xxl|2xl)\b")),
    ("xl", re.compile(r"^xl\b")),
    ("xxs", re.compile(r"^xxs\b")),
    ("xs", re.compile(r"^xs\b")),
    ("s", re.compile(r"^s\b")),
    ("m", re.compile(r"^m\b")),
    ("l", re.compile(r"^l\b")),
]
SIZE_DE_WOMEN = {32: "xxs", 34: "xs", 36: "s", 38: "m", 40: "l", 42: "xl", 44: "xxl"}
SIZE_DE_MEN = {46: "s", 48: "m", 50: "l", 52: "xl", 54: "xxl", 56: "xxl"}


def size_class_of(size: str | None) -> str:
    """Normalise a Vinted size string to one comparable class token."""
    raw = (size or "").strip()
    if not raw:
        return "unknown"
    low = raw.lower()
    if KID_MARKERS.search(low):
        return "kids"
    if re.search(r"einheitsgr|one ?size|onesize|taille unique|unica|universal", low):
        return "one"
    w = re.search(r"\bw ?(\d{2})\b", low)
    if w and 24 <= int(w.group(1)) <= 44:
        return f"w{int(w.group(1))}"
    for cls, pat in SIZE_LETTERS:
        if pat.search(low):
            return cls
    bare = re.match(r"^(\d{2})\s*$", low)
    if bare:
        n = int(bare.group(1))
        if n in SIZE_DE_MEN and n >= 46:
            return SIZE_DE_MEN[n]
        if n in SIZE_DE_WOMEN:
            return SIZE_DE_WOMEN[n]
    return "other"


# Comp pools keyed on the exact brand string starve their own sub-brands:
# "Ralph Lauren", "Polo Ralph Lauren", "LAUREN Ralph Lauren", "Chaps Ralph
# Lauren" and "Ralph Lauren Sport" were five separate pools for one market on
# 2026-09-08, and likewise adidas/adidas Originals and Nike/Nike Air/SB/ACG.
# brand_norm_of() folds each family to one key; anything unrecognised keeps its
# own slug, so a new brand is never silently merged into a neighbour.
BRAND_FAMILIES: list[tuple[str, re.Pattern]] = [
    ("ralph-lauren", re.compile(r"ralph lauren|chaps")),
    ("the-north-face", re.compile(r"north face")),
    ("stone-island", re.compile(r"stone island")),
    ("carhartt", re.compile(r"^carhartt")),
    ("patagonia", re.compile(r"^patagonia")),
    ("levis", re.compile(r"^levi")),
    ("nike", re.compile(r"^nike")),
    ("adidas", re.compile(r"^adidas")),
    ("agolde", re.compile(r"^agolde")),
    ("citizens-of-humanity", re.compile(r"citizens of humanity")),
    ("7-for-all-mankind", re.compile(r"7 ?for ?all ?mankind|seven for all mankind|7fam")),
    ("mother", re.compile(r"^mother\b")),
]


def brand_norm_of(brand: str | None) -> str:
    """Fold a brand string to its comp-pool family key."""
    raw = (brand or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    for key, pat in BRAND_FAMILIES:
        if pat.search(low):
            return key
    return re.sub(r"[^a-z0-9]+", "-", low).strip("-")

RECHECK_INTERVAL_MIN = 60
RECHECK_BATCH = 25
RECHECK_MIN_AGE_H = 12   # too soon to have resolved into anything
RECHECK_MAX_AGE_D = 10   # past this the sold panel gives way to a 404
GONE_RATE_CEILING = 0.40   # a batch reading gone above this is systemic, not sales
STALE_ALERT_MIN = 45       # no successful poll this long -> tell the operator
STALE_RENAG_H = 6          # keep reminding while an outage continues

# A URL that has left the item page for a login/consent/challenge screen.
WALL_URL = re.compile(r"/login|/member/general|captcha|challenge|consent", re.I)

# How a sold listing is actually told apart from a withdrawn one (probed
# 2026-09-09 against the owner's own bought item as ground truth).
#
# The item page is a Next.js app that ships its sidebar as a list of plugins
# inside an escaped-JSON flight payload. Exactly one of two plugins is present,
# and which one IS the verdict:
#
#   sold : buyer_item_status {"item_id":..,"title":"Verkauft","theme":"SUCCESS"}
#   live : item_status       {"is_closed":false,"item_closing_action":null,..}
#
# Three earlier candidates were checked and rejected, each of which would have
# produced silent garbage:
#   - is_sold":true  -- the previous marker. It appears on NO page, sold or
#     live, so the sold branch was unreachable and every sale was recorded as
#     "alive". This is why 3 outcome rows exist and 0 are marked sold.
#   - the word "Verkauft" -- present on every page, live ones included, inside
#     the i18n bundle ("flash_messages.no_longer_available_sold.title"). It
#     would mark 100% of listings sold.
#   - HTTP 404 as a proxy for sold -- a sold listing answers 200 and keeps
#     answering it for days. 404 is deletion, which is not a sale.
BUYER_STATUS = re.compile(
    r'\\"name\\":\\"buyer_item_status\\".{0,240}?\\"title\\":\\"([^"\\]{0,40})\\"'
    r'.{0,80}?\\"theme\\":\\"([A-Z_]{0,20})\\"')
ITEM_STATUS = re.compile(
    r'\\"name\\":\\"item_status\\".{0,400}?\\"is_closed\\":(true|false)'
    r'.{0,80}?\\"item_closing_action\\":(null|\\"[a-z_]{0,30}\\")')
# The sold panel's title is localised, so the theme carries the meaning and the
# title is kept only as evidence. SUCCESS is the sold panel; anything else is a
# closure we have not seen yet and must not guess at.
SOLD_THEME = "SUCCESS"


# The item's own price, as the page carries it. Two price shapes appear in the
# payload and only one is the item: the item price uses snake_case
# `currency_code`, while shipping quotes use camelCase `currencyCode`. Keying on
# that distinction is what separates 8.00 (the Levi's) from 4.19 (its postage).
# Verified against two rows whose stored price is known: 8.0 and 59.0.
PAGE_PRICE = re.compile(r'\\"price\\":\{\\"amount\\":\\"([\d.]+)\\",\\"currency_code\\"')


def item_page_price(body: str) -> float | None:
    """The listing's current asking price, read off its item page.

    This is why it matters: the catalog poll returns newest_first, so a listing
    leaves page one within minutes and the median row is observed for 10
    minutes total, with only 4.2% still seen after an hour. Price cuts happen
    over days, entirely outside that window, so the poll alone would record
    almost none of them. The recheck already fetches this page 12h to 10d
    later, which is exactly when a seller has started cutting, and the price is
    sitting in the response we already paid for.

    Ambiguity is refused rather than guessed: if the page carries more than one
    distinct item-shaped price, none of them is known to be the item's.
    """
    found = {m.group(1) for m in PAGE_PRICE.finditer(body or "")}
    if len(found) != 1:
        return None
    try:
        return float(found.pop())
    except ValueError:
        return None


def item_page_verdict(status_code: int, body: str) -> tuple[str, str]:
    """Read a listing's fate off its item page. Returns (verdict, evidence).

    Verdicts: sold | gone | alive | closed | unknown. `closed` is a real
    closure whose reason is not a sale; `unknown` is a page we could not read,
    which is deliberately NOT folded into any of the others. Guessing here is
    how 375 fabricated sales entered this database on 2026-09-07.
    """
    if status_code in (404, 410):
        return "gone", str(status_code)
    if status_code != 200:
        return "unknown", f"http_{status_code}"
    m = BUYER_STATUS.search(body)
    if m:
        title, theme = m.group(1), m.group(2)
        verdict = "sold" if theme == SOLD_THEME else "closed"
        return verdict, f"buyer_item_status:{theme}:{title}"[:60]
    m = ITEM_STATUS.search(body)
    if m:
        if m.group(1) == "false":
            return "alive", "item_status:open"
        action = m.group(2).strip('\\"') or "null"
        # A closed item whose closing action says it sold is still a sale.
        return ("sold" if "sold" in action and "not" not in action else "closed",
                f"item_status:closed:{action}"[:60])
    return "unknown", "no_status_plugin"


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


LOG_NAME = "watcher.log"
LOG_MAX_BYTES = 2_000_000


def log(msg: str) -> None:
    """Print, and keep a copy on disk.

    The scheduled task runs through run-hidden.vbs, which discards stdout, so
    for a headless run print() writes to nowhere. That is how a warning per
    cycle about a failing INSERT went unseen for two hours on 2026-09-08 while
    the notifications themselves kept arriving. A file is the difference
    between a diagnosable failure and an invisible one. It must never be the
    thing that ends a cycle, hence the swallowed OSError.
    """
    line = f"[{now_iso()}] {msg}"
    print(line)
    try:
        # Resolved per call, not at import: the tests redirect DATA_DIR and a
        # module-level path would write into the real data directory.
        path = DATA_DIR / LOG_NAME
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > LOG_MAX_BYTES:
            path.replace(DATA_DIR / (LOG_NAME + ".1"))
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


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
    s.setdefault("size_classes", list(DEFAULT_SIZE_CLASSES))
    s.setdefault("min_margin", 0)
    s.setdefault("foreign_advantage_eur", 8)
    s.setdefault("fake_risk_suppress", 0.7)
    s.setdefault("fake_risk_flag", 0.4)
    s.setdefault("profile_suppress", 0.15)
    s.setdefault("profile_min_rated", 8)
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
    posted_at TEXT,
    fav_first INTEGER,
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

-- One row per candidate that cleared the deal gate, INCLUDING the ones that
-- were then suppressed. Two reasons this is not optional bookkeeping: upsert()
-- overwrites price/total_price/favourites on every re-sight, so the state a
-- decision was made on is otherwise unrecoverable; and the planned offline
-- backtest scorer replays each decision against its own comp context, which
-- has to be frozen here or it does not exist. listings.alerted stays as the
-- cheap boolean it always was.
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    alerted_at TEXT NOT NULL,
    search_tag TEXT NOT NULL,
    title TEXT, brand TEXT, brand_norm TEXT,
    size TEXT, size_class TEXT,
    condition TEXT, cond_tier TEXT, garment_class TEXT,
    country TEXT,
    price_at_alert REAL, total_at_alert REAL,
    favourites_at_alert INTEGER, promoted INTEGER, seller_id INTEGER,
    listing_age_min REAL, posted_at TEXT,
    comp_n INTEGER, comp_median REAL, comp_p25 REAL, comp_p75 REAL,
    discount_pct REAL, margin_eur REAL,
    deal_ratio_used REAL, min_comps_used INTEGER, comp_window_used INTEGER,
    size_filter TEXT, settings_json TEXT,
    fake_risk REAL, fake_risk_reasons TEXT,
    profile_score REAL, quality REAL, priority INTEGER,
    sent INTEGER NOT NULL DEFAULT 0,
    suppress_reason TEXT,
    cycle_backlog_n INTEGER
);

-- Seller profiles, fetched at most once per seller and only for listings that
-- already look like deals. The catalog response carries no country and no
-- reputation, but /api/v2/users/{id} carries both, and sellers repeat across
-- listings, so a cache turns a per-listing cost into a per-seller one.
CREATE TABLE IF NOT EXISTS sellers (
    seller_id INTEGER PRIMARY KEY,
    login TEXT,
    country TEXT,
    city TEXT,
    feedback_count INTEGER,
    positive_feedback_count INTEGER,
    feedback_reputation REAL,
    item_count INTEGER,
    business INTEGER,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS alert_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    alert_id INTEGER,
    verdict TEXT NOT NULL,
    received_at TEXT NOT NULL,
    source TEXT NOT NULL,
    ntfy_msg_id TEXT UNIQUE,
    raw TEXT
);

-- One row per OBSERVED CHANGE to a listing's price, favourites or views.
-- upsert() overwrites those columns on every re-sight, so before this table
-- the watcher spent every cycle deleting the only history it will ever have:
-- a seller who cuts the price three times wants out, which is a demand signal
-- for the cell and a buying signal for us, and none of it survived. Past
-- changes are gone for good and cannot be backfilled from anywhere.
--
-- Written only when the value actually moved. Writing every sighting instead
-- would add ~13.8k contentless rows a day, and a table that grows without
-- carrying information is a slower way to learn nothing.
CREATE TABLE IF NOT EXISTS listing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    seen_at TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value REAL,
    new_value REAL
);

-- What WE listed, for what, with which keywords, and whether it sold. The
-- market corpus says how sellers describe things; this is the only table that
-- can ever say whether the bot's suggestions worked. Without it every
-- keyword ranking is a hypothesis with no feedback path.
CREATE TABLE IF NOT EXISTS my_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vinted_item_id INTEGER,
    source_listing_id INTEGER,
    title TEXT,
    brand TEXT, brand_norm TEXT,
    garment_class TEXT,
    size TEXT, size_class TEXT,
    condition TEXT, cond_tier TEXT,
    color TEXT, material TEXT,
    keywords TEXT,
    description TEXT,
    buy_price REAL,
    ask_price REAL,
    comp_median_at_listing REAL,
    listed_at TEXT,
    sold_at TEXT,
    sold_price REAL,
    status TEXT NOT NULL DEFAULT 'draft',
    url TEXT,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT
);
"""

# Indexes are created only AFTER migrate() has added any columns an older
# database predates: CREATE INDEX names its columns, so building it first
# fails outright on a database that has not caught up yet.
DDL_INDEXES = """
-- idx_listings_comp keyed the old exact-brand pool. CREATE INDEX IF NOT EXISTS
-- would silently keep that stale definition, so it is dropped by name first.
DROP INDEX IF EXISTS idx_listings_comp;
CREATE INDEX IF NOT EXISTS idx_listings_comp_norm ON listings (search_tag, brand_norm, cond_tier, garment_class);
CREATE INDEX IF NOT EXISTS idx_listings_recheck ON listings (gone_at, last_seen);
CREATE INDEX IF NOT EXISTS idx_alerts_listing ON alerts (listing_id, alerted_at);
CREATE INDEX IF NOT EXISTS idx_alerts_tag ON alerts (search_tag, alerted_at);
CREATE INDEX IF NOT EXISTS idx_feedback_listing ON alert_feedback (listing_id);
CREATE INDEX IF NOT EXISTS idx_events_listing ON listing_events (listing_id, seen_at);
CREATE INDEX IF NOT EXISTS idx_events_field ON listing_events (field, seen_at);
CREATE INDEX IF NOT EXISTS idx_my_listings_status ON my_listings (status, listed_at);
"""


ADDED_COLUMNS = {                       # column -> DDL fragment, applied to old DBs
    "garment_class": "TEXT",
    "is_kid": "INTEGER DEFAULT 0",
    "gone_source": "TEXT",
    "size_class": "TEXT",
    "brand_norm": "TEXT",
    "country": "TEXT",
    "fake_risk": "REAL",
    "fake_risk_reasons": "TEXT",
    "posted_at": "TEXT",
    "fav_first": "INTEGER",
}


def _fix_cond_tier(con: sqlite3.Connection) -> int:
    """Recompute cond_tier for rows the v1 mapping left at 'unknown'."""
    # A data fix reads columns the column loop above does not guarantee, so it
    # checks first: an ancient table shape must skip the repair, not crash the
    # connect that every mode depends on.
    have = {row[1] for row in con.execute("PRAGMA table_info(listings)")}
    if not {"condition", "cond_tier"} <= have:
        return 0
    rows = con.execute(
        "SELECT DISTINCT condition FROM listings WHERE cond_tier='unknown' AND condition!=''"
    ).fetchall()
    fixed = 0
    for (cond,) in rows:
        tier = cond_tier_of(cond)
        if tier == "unknown":
            continue
        cur = con.execute(
            "UPDATE listings SET cond_tier=? WHERE condition=? AND cond_tier='unknown'",
            (tier, cond),
        )
        fixed += cur.rowcount
    return fixed


# Repairs that add no column, so the column loop above cannot carry them. Each
# runs once, guarded by its own meta flag, and reports how many rows it touched.
DATA_FIXES: list[tuple[str, object]] = [
    ("cond_tier_v2", _fix_cond_tier),
]


BACKFILLS = {
    "is_kid": lambda con: [
        con.execute("UPDATE listings SET is_kid=? WHERE id=?",
                    (is_kid_item(title, size), row_id))
        for row_id, title, size in con.execute("SELECT id, title, size FROM listings").fetchall()
    ],
    "garment_class": lambda con: [
        con.execute("UPDATE listings SET garment_class=? WHERE id=?",
                    (garment_class(title), row_id))
        for row_id, title in con.execute("SELECT id, title FROM listings").fetchall()
    ],
    "size_class": lambda con: [
        con.execute("UPDATE listings SET size_class=? WHERE id=?",
                    (size_class_of(size), row_id))
        for row_id, size in con.execute("SELECT id, size FROM listings").fetchall()
    ],
    "brand_norm": lambda con: [
        con.execute("UPDATE listings SET brand_norm=? WHERE id=?",
                    (brand_norm_of(brand), row_id))
        for row_id, brand in con.execute("SELECT id, brand FROM listings").fetchall()
    ],
    # Retroactive over the whole history, because the photo URL was stored from
    # the first row onwards. This is the one field the watcher gains for free
    # and backwards: every listing it ever saw gets a real posting time.
    "posted_at": lambda con: [
        con.execute("UPDATE listings SET posted_at=? WHERE id=?",
                    (posted_at_of(url), row_id))
        for row_id, url in con.execute("SELECT id, photo_url FROM listings").fetchall()
    ],
    # fav_first can only be seeded from the current reading, which for an
    # already-seen row is the LATEST count, not the first. Seeding it anyway
    # would silently invent growth of zero on 35k rows, so old rows stay NULL
    # and the measure starts clean with the next listing the watcher meets.
    "fav_first": lambda con: None,
}

# Which existing column each backfill reads. A very old table shape may not have
# it, and a backfill that cannot read its source must skip rather than crash the
# connect that every mode depends on.
BACKFILL_SOURCE = {"is_kid": "title", "garment_class": "title",
                   "size_class": "size", "brand_norm": "brand",
                   "posted_at": "photo_url"}

# Clause openers that are table constraints rather than columns.
_DDL_CONSTRAINTS = {"primary", "unique", "foreign", "check", "constraint"}


def ddl_columns(ddl: str = "") -> dict[str, list[tuple[str, str]]]:
    """Parse the DDL literal into {table: [(column, declaration), ...]}.

    Deliberately reads the same string the tables are created from, so a
    column added to the DDL cannot be forgotten in a migration list: there is
    one place to edit, and this derives the rest.
    """
    text = ddl or DDL
    out: dict[str, list[tuple[str, str]]] = {}
    for block in re.finditer(
            r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\n?\s*\);", text, re.S):
        table, body = block.group(1), block.group(2)
        body = re.sub(r"--[^\n]*", "", body)            # strip trailing comments
        cols: list[tuple[str, str]] = []
        depth, current = 0, []
        for ch in body:                                  # split on top-level commas
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                cols.append("".join(current))
                current = []
            else:
                current.append(ch)
        cols.append("".join(current))
        parsed = []
        for clause in cols:
            tokens = clause.split()
            if not tokens or tokens[0].lower() in _DDL_CONSTRAINTS:
                continue
            parsed.append((tokens[0], " ".join(tokens[1:])))
        if parsed:
            out[table] = parsed
    return out


def alterable(decl: str) -> bool:
    """Can SQLite add this column to an existing table?

    ALTER TABLE ADD COLUMN refuses a PRIMARY KEY, refuses UNIQUE, refuses
    NOT NULL without a default, and refuses a non-constant default. Each of
    those raises inside the connect that every mode of the watcher depends on,
    so they are reported rather than attempted. The UNIQUE case is not
    hypothetical: alert_feedback.ntfy_msg_id carries it.
    """
    low = decl.lower()
    if "primary key" in low or "unique" in low:
        return False
    if "current_timestamp" in low or "current_date" in low or "current_time" in low:
        return False
    return not ("not null" in low and "default" not in low)


def is_schema_error(exc: BaseException) -> bool:
    """Does this exception mean the code and the database disagree on shape?

    Kept narrow on purpose. "database is locked" is also an OperationalError
    and is transient; a missing column or table is neither transient nor
    survivable, and treating the two the same is what let a broken INSERT hide
    behind a per-search warning.
    """
    if not isinstance(exc, sqlite3.Error):
        return False
    text = str(exc).lower()
    return "no such column" in text or "has no column" in text or "no such table" in text


def reconcile_ddl_columns(con: sqlite3.Connection) -> int:
    """Add columns the DDL declares that an existing table is missing.

    CREATE TABLE IF NOT EXISTS is a no-op once the table exists, so a column
    added later reaches only databases created after it. On 2026-09-08 that
    cost real data: alerts.quality was added to the DDL, the production table
    predated it, and every INSERT into alerts raised OperationalError from
    then on. The insert sits behind the notification, so alerts kept arriving
    on the phone while nothing was recorded, the per-search error handler
    logged a warning into a discarded stdout, and the rating buttons had
    nothing to attach to. Twenty-one alerts and two real taps were lost that
    way in two hours. The listings-only ADDED_COLUMNS loop below could not
    have caught it, so this walks every table in the DDL instead.
    """
    added = 0
    for table, columns in ddl_columns().items():
        live = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        if not live:
            continue                                     # created by the DDL itself
        for column, decl in columns:
            if column in live:
                continue
            if not alterable(decl):
                log(f"WARN: {table}.{column} is missing and cannot be added in place "
                    f"({decl}); the table predates the current schema")
                continue
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
            log(f"migrated: added {table}.{column}")
            added += 1
    if added:
        con.commit()
    return added


def migrate(con: sqlite3.Connection) -> None:
    """Add columns an older database predates, and fill them exactly once.

    CREATE TABLE IF NOT EXISTS silently does nothing when the table already
    exists, so a new column would otherwise only reach a fresh database. The
    v1 garment_class column was added by deleting the database, which is not
    an option now that it holds real market history.

    Completion is recorded in meta rather than inferred from the column being
    there. ALTER TABLE is DDL and commits the open transaction on the spot, so
    a process that dies partway through a backfill leaves the column present
    and empty; keying on presence alone meant the fill was never retried and
    those rows stayed blank for good. On a database that cannot be rebuilt,
    that is the expensive kind of silent damage, and it is invisible.
    """
    reconcile_ddl_columns(con)
    have = {row[1] for row in con.execute("PRAGMA table_info(listings)")}
    for column, decl in ADDED_COLUMNS.items():
        flag = f"backfill:{column}"
        filled = con.execute("SELECT 1 FROM meta WHERE k=?", (flag,)).fetchone()
        if column in have and filled:
            continue
        if column not in have:
            con.execute(f"ALTER TABLE listings ADD COLUMN {column} {decl}")
            log(f"migrated: added listings.{column}")
        elif not filled:
            log(f"migrated: listings.{column} was added but never filled; redoing")

        backfill = BACKFILLS.get(column)
        source = BACKFILL_SOURCE.get(column)
        if backfill and (source is None or source in have):
            backfill(con)
        con.execute("INSERT INTO meta (k, v) VALUES (?, ?)"
                    " ON CONFLICT(k) DO UPDATE SET v=excluded.v", (flag, now_iso()))
        con.commit()

    for name, fix in DATA_FIXES:
        flag = f"datafix:{name}"
        if con.execute("SELECT 1 FROM meta WHERE k=?", (flag,)).fetchone():
            continue
        touched = fix(con)
        con.execute("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                    (flag, f"{now_iso()} rows={touched}"))
        con.commit()
        log(f"migrated: data fix {name} touched {touched} rows")


def db_connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(DDL)
    migrate(con)
    # Statement by statement rather than executescript: an index names its
    # columns, so on a table shape migrate() could not fully repair the whole
    # script aborts and every mode of the watcher dies at connect. A missing
    # index costs speed; a failed connect costs the cycle.
    for statement in DDL_INDEXES.split(";"):
        if not re.sub(r"--[^\n]*", "", statement).strip():
            continue                                 # comment-only tail
        try:
            con.execute(statement)
        except sqlite3.OperationalError as e:
            log(f"WARN: index not created ({e}); the table shape is behind the schema")
    con.commit()
    return con


def meta_get(con: sqlite3.Connection, k: str) -> str | None:
    row = con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return row[0] if row else None


def meta_set(con: sqlite3.Connection, k: str, v: str) -> None:
    con.execute("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))


# ------------------------------------------------------------------- session

TOKEN_COOKIE = "access_token_web"
TOKEN_MARGIN_MIN = 45   # renew this long before the token's own expiry
AUTH_BACKOFF_MIN = 10     # 401: auth hiccup, self-healing, retry soon
SERVER_BACKOFF_MIN = 20   # 5xx: the far end is struggling, stop asking
WALL_BACKOFF_MIN = 60     # 403: bot wall, stay away
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


def egress_proxy() -> str | None:
    """The outbound proxy, if one is configured. Absent by default.

    Vinted refuses datacenter IPs at the door: probed 2026-09-10 from a Fly
    machine in Frankfurt, `GET https://www.vinted.de/` answered 403 on the very
    first request, before a session could be minted. So the watcher cannot be
    moved to a cloud host as-is, and a residential egress is the only route
    that keeps a 24/7 host. This reads it from the environment rather than
    hard-coding one, so the default build has no proxy and no dependency on a
    third party.

    Setting it is a deliberate act with consequences the config file cannot
    carry: it routes around an access control Vinted chose, the traffic leaves
    through somebody else's home connection, and a detection lands on the
    owner's selling account rather than on an anonymous reader. Documented in
    searches.yaml next to the key.
    """
    return load_env().get("EGRESS_PROXY_URL") or None


def new_client() -> httpx.Client:
    proxy = egress_proxy()
    client = httpx.Client(
        headers={"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9"},
        timeout=25,
        follow_redirects=True,
        proxy=proxy,
    )
    if proxy:
        # Host only: the credentials live in the URL and must never reach a log.
        log(f"egress via proxy {redact_proxy(proxy)}")
    if COOKIE_PATH.exists():
        load_cookies(client)
    return client


def redact_proxy(url: str) -> str:
    """A proxy URL with any credentials removed, safe to log."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "<unparseable>"
    host = parts.hostname or "?"
    port = f":{parts.port}" if parts.port else ""
    creds = "<user:pass@>" if (parts.username or parts.password) else ""
    return f"{parts.scheme}://{creds}{host}{port}"


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
        if r.status_code >= 500:
            # A 5xx is the far end struggling, and the polite answer to that is
            # to stop asking for a while rather than to keep the 5-minute
            # cadence pointed at it. It is also how a soft rate limit surfaces
            # here: on 2026-09-08 a burst of one-off probe requests alongside
            # the normal cycle turned every catalog call into a 500, including
            # the searches that had worked minutes earlier. Escalating, so a
            # sustained outage backs further off each time instead of retrying
            # at a fixed rate.
            set_backoff(con, SERVER_BACKOFF_MIN, f"HTTP {r.status_code} (server side)",
                        escalate=True)
            raise SessionWall(f"HTTP {r.status_code}")
        r.raise_for_status()
        if "json" not in r.headers.get("content-type", ""):
            # An HTML body on a 200 is an interstitial, not data. Parsing it
            # would raise; treating it as a wall is what it actually is.
            set_backoff(con, WALL_BACKOFF_MIN, "HTML body where JSON expected", escalate=True)
            raise SessionWall("non-JSON body")
        return r.json()
    raise SessionWall("unreachable")


# ------------------------------------------------------------------- parsing

# Country paths the catalog response might carry. Which of these (if any) is
# actually populated is settled by --probe-fields against the live API, never
# assumed: api-notes.md listed country/shipping fields as unverified, and a
# guessed path would silently mark every listing unknown. Reading several
# candidate paths costs nothing and survives a field rename.
COUNTRY_PATHS = [
    ("user", "country_iso_code"),
    ("user", "countryIsoCode"),
    ("user", "country_code"),
    ("user", "country_title_local"),
    ("country_iso_code",),
    ("country_code",),
]


def item_country(item: dict) -> str | None:
    """Best-effort ISO country of the seller, or None when the API omits it."""
    for path in COUNTRY_PATHS:
        node: object = item
        for key in path:
            node = (node or {}).get(key) if isinstance(node, dict) else None
        if isinstance(node, str) and node.strip():
            val = node.strip().upper()
            return val[:2] if len(val) >= 2 else None
    return None


# Vinted serves listing photos from a path that ends in the image's upload
# epoch: .../f800/1788892725.jpeg, with an optional /r<n>/ revision segment.
# That epoch is the closest thing to a posting time the catalog response
# carries, and it costs nothing: the URL is already stored on every row.
# Validated three ways over 35,393 rows: 35,392 parse; listings found by the
# 5-minute poll come out at a median 3.18 minutes old while the seed crawl's
# come out at a median 3.7 days, which the parser cannot know; there is not one
# negative age; and the ordering agrees with Vinted's own ascending listing ids
# at Spearman 0.993.
PHOTO_EPOCH = re.compile(r"/f\d{2,4}/(?:r\d+/)?(\d{9,11})\.jpe?g")


def posted_at_of(photo_url: str | None) -> str | None:
    """Posting time read off the listing photo URL; None when unreadable.

    Bounded rather than trusted: an epoch in the future or absurdly far in the
    past is a URL shape we have not seen, not a posting time, and returning
    None keeps such a row out of the age logic instead of poisoning it.
    """
    m = PHOTO_EPOCH.search(photo_url or "")
    if not m:
        return None
    try:
        ts = datetime.fromtimestamp(int(m.group(1)), timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    now = datetime.now(timezone.utc)
    if ts > now + timedelta(minutes=10) or ts < now - timedelta(days=3650):
        return None
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


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
        "cond_tier": cond_tier_of(cond),
        "garment_class": garment_class(item.get("title")),
        "is_kid": is_kid_item(item.get("title"), item.get("size_title")),
        "size_class": size_class_of(item.get("size_title")),
        "brand_norm": brand_norm_of(item.get("brand_title")),
        "country": item_country(item),
        "price": price,
        "total_price": total,
        "currency": (item.get("price") or {}).get("currency_code", "EUR"),
        "url": item.get("url"),
        "photo_url": photo_url,
        "posted_at": posted_at_of(photo_url),
        "seller_id": user.get("id"),
        "seller_login": user.get("login"),
        "favourites": item.get("favourite_count", 0),
        "views": item.get("view_count", 0),
        "promoted": 1 if item.get("promoted") else 0,
        "seed": seed,
    }


# Columns upsert() overwrites on every re-sight, and whose movement is the
# signal. Rounded before comparison because the price arrives as a float and
# 26.950000000000003 != 26.95 would log a change that did not happen.
TRACKED_FIELDS = (("price", 2), ("total_price", 2), ("favourites", 0), ("views", 0))


def record_changes(con: sqlite3.Connection, listing_id: int, before: sqlite3.Row | tuple,
                   rec: dict, ts: str) -> int:
    """Append one row per tracked value that actually moved. Returns the count.

    A value that did not move writes nothing: at ~13.8k re-sights a day, logging
    every sighting would grow the table by that much daily while carrying no
    information. A first reading of NULL is skipped too, since "unknown became
    12" is not a change anyone can learn from.
    """
    written = 0
    for i, (field, places) in enumerate(TRACKED_FIELDS):
        old, new = before[i], rec.get(field)
        if old is None or new is None:
            continue
        try:
            if round(float(old), places) == round(float(new), places):
                continue
        except (TypeError, ValueError):
            continue
        con.execute(
            "INSERT INTO listing_events (listing_id, seen_at, field, old_value, new_value)"
            " VALUES (?, ?, ?, ?, ?)",
            (listing_id, ts, field, float(old), float(new)),
        )
        written += 1
    return written


def record_page_price(con: sqlite3.Connection, listing_id: int,
                      page_price: float | None, ts: str) -> int:
    """Record a price read off the item page during a recheck. Returns 1 if moved.

    The catalog poll and this share one table on purpose: a price change is a
    price change whichever observation caught it. What differs is the reach. The
    poll sees a listing for a median of 10 minutes and then never again, so the
    cuts a seller makes on day three are invisible to it; the recheck lands 12h
    to 10d out, which is exactly when they happen.

    total_price is derived rather than read, because the page states the item
    price while every comparison in this database is in buyer-paid totals. The
    fee is 0.70 + 5%, recovered from 36,229 price pairs to within half a cent.
    """
    if page_price is None:
        return 0
    row = con.execute("SELECT price, total_price FROM listings WHERE id=?",
                      (listing_id,)).fetchone()
    if row is None or row[0] is None:
        return 0
    if round(float(row[0]), 2) == round(page_price, 2):
        return 0
    total = round(page_price * 1.05 + 0.70, 2)
    con.execute(
        "INSERT INTO listing_events (listing_id, seen_at, field, old_value, new_value)"
        " VALUES (?, ?, 'price', ?, ?)", (listing_id, ts, float(row[0]), page_price))
    if row[1] is not None:
        con.execute(
            "INSERT INTO listing_events (listing_id, seen_at, field, old_value, new_value)"
            " VALUES (?, ?, 'total_price', ?, ?)", (listing_id, ts, float(row[1]), total))
    con.execute("UPDATE listings SET price=?, total_price=? WHERE id=?",
                (page_price, total, listing_id))
    return 1


def upsert(con: sqlite3.Connection, rec: dict) -> bool:
    """Insert or refresh a listing. Returns True when the id was new."""
    ts = now_iso()
    # Selects the tracked values rather than just the id, so the comparison
    # costs nothing extra: this row has to be read either way.
    existing = con.execute(
        "SELECT price, total_price, favourites, views FROM listings WHERE id=?",
        (rec["id"],)).fetchone()
    if existing:
        # The history has to be captured BEFORE the UPDATE overwrites it. This
        # is the whole point of the ordering here.
        record_changes(con, rec["id"], existing, rec, ts)
        # Seeing a listing in a live search result disproves any earlier
        # "gone" verdict, so clear it. Without this a row wrongly marked gone
        # stayed gone forever, and the outcome data could never self-correct.
        con.execute(
            "UPDATE listings SET last_seen=?, favourites=?, views=?, price=?, total_price=?, "
            "country=COALESCE(?, country), "
            "gone_at=NULL, gone_source=NULL, sold_flag=0 WHERE id=?",
            (ts, rec["favourites"], rec["views"], rec["price"], rec["total_price"],
             rec.get("country"), rec["id"]),
        )
        return False
    con.execute(
        """INSERT INTO listings (id, search_tag, title, brand, brand_norm, size, size_class,
               condition, cond_tier, garment_class, is_kid, country, price, total_price, currency,
               url, photo_url, posted_at, seller_id, seller_login, favourites, fav_first,
               views, promoted, seed, first_seen, last_seen)
           VALUES (:id, :search_tag, :title, :brand, :brand_norm, :size, :size_class,
               :condition, :cond_tier, :garment_class, :is_kid, :country, :price, :total_price, :currency,
               :url, :photo_url, :posted_at, :seller_id, :seller_login, :favourites, :fav_first,
               :views, :promoted, :seed, :first_seen, :last_seen)""",
        # fav_first is written here and never again: the UPDATE branch above
        # overwrites favourites on every re-sight, so without a frozen first
        # reading there is no second point to measure like growth against.
        {**rec, "first_seen": ts, "last_seen": ts, "fav_first": rec.get("favourites")},
    )
    return True


# ------------------------------------------------------------------- scoring

def profile_score(con: sqlite3.Connection, rec: dict) -> float | None:
    """Owner-taste score for this listing's cell, or None when unrated.

    The cell is brand family x garment class x size class. Feedback is sparse
    by nature, so the score is Laplace-smoothed and only returned once the cell
    has been rated at all; callers treat None as "no opinion", never as bad.
    This is a ranking signal layered on top of the explicit gates, never a way
    around them: a fake-risk or size verdict is not undone by a good track.
    """
    row = con.execute(
        """SELECT
               SUM(CASE WHEN f.verdict IN ('good','bought') THEN 1 ELSE 0 END),
               SUM(CASE WHEN f.verdict='bad' THEN 1 ELSE 0 END)
           FROM alert_feedback f JOIN alerts a ON a.id=f.alert_id
           WHERE a.brand_norm=? AND a.garment_class=? AND a.size_class=?""",
        (rec.get("brand_norm") or brand_norm_of(rec.get("brand")),
         rec.get("garment_class"),
         rec.get("size_class") or size_class_of(rec.get("size"))),
    ).fetchone()
    good, bad = (row[0] or 0), (row[1] or 0)
    if good + bad == 0:
        return None
    return (good + 1.0) / (good + bad + 2.0)


FAKE_TITLE_MARKERS = re.compile(
    r"1[:.]1\b|\baaa\+?\b|replic|replik|\brep\b|inspired by|inspiriert von|kopie|"
    r"\bmirror\b|dhgate|pandabuy|weidian|taobao|\bua\b|unauthorized|nachbau"
)
EMOJI_RANGE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF]"
)
# Brands whose fakes are mass-produced and whose price band makes a deep
# discount suspicious rather than lucky.
#
# This started as a guess and is now partly measured. Counting counterfeit slang
# in listing titles across the corpus (listing/keyword_research.py --fake-vocab,
# 2026-09-08) put Stone Island at 0.451% of its listings, adidas at 0.070%, Nike
# at 0.058% and Ralph Lauren at 0.049%; those are lower bounds, since only the
# sellers who write it down get counted. Ralph Lauren and Patagonia were missing
# here despite both being widely counterfeited and both sitting in a price band
# where it pays, so they are in. The premium denim lines are in for the same
# reason: a 300 EUR pair of jeans offered at 30 is the shape this rule exists to
# catch.
HYPE_BRANDS = {"stone-island", "nike", "the-north-face", "carhartt", "adidas",
               "ralph-lauren", "patagonia", "agolde", "citizens-of-humanity",
               "mother", "7-for-all-mankind"}


def fake_risk_score(con: sqlite3.Connection, rec: dict, med: float) -> tuple[float, list[str]]:
    """Rule-based counterfeit risk for one deal candidate, 0.0 to 1.0.

    Runs only on candidates that already cleared the deal gate, so the SQL here
    costs a handful of queries a day, not one per ingested listing. Image
    analysis is deliberately absent: downloading listing photos would multiply
    the request budget for a weak signal, and the reverse-image links in the
    alert do that job better with a human eye behind them.
    """
    score, why = 0.0, []
    total = rec["total_price"]
    brand_key = rec.get("brand_norm") or brand_norm_of(rec.get("brand"))
    title_l = (rec.get("title") or "").lower()

    if med > 0:
        # A hype brand shifts the thresholds rather than adding a term of its
        # own. The two used to be separate and both fired for the same fact:
        # anything under 0.15 of the median is also under 0.30, so a Patagonia
        # at 9% of market scored 0.6 + 0.2 and was suppressed on price alone.
        # That is the opposite of the point. A deep discount is more suspicious
        # on a faked brand, which is a sharper test, not a second one.
        hype = brand_key in HYPE_BRANDS
        absurd_at = 0.20 if hype else 0.15
        too_good_at = 0.30 if hype else 0.25
        if total < absurd_at * med:
            score += 0.6
            why.append("preis_absurd_hype" if hype else "preis_absurd")
        elif total < too_good_at * med:
            score += 0.4
            why.append("preis_zu_gut_hype" if hype else "preis_zu_gut")

    if FAKE_TITLE_MARKERS.search(title_l):
        score += 0.5
        why.append("titel_marker")
    if len(EMOJI_RANGE.findall(rec.get("title") or "")) >= 5:
        score += 0.15
        why.append("emoji_spam")

    # Identical titles across separate sellers is the cheap stand-in for stock
    # photos: a genuine secondhand listing is one person's own wording.
    if rec.get("title"):
        window = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
        others = con.execute(
            """SELECT COUNT(DISTINCT seller_id) FROM listings
               WHERE title=? AND seller_id IS NOT NULL AND seller_id!=? AND last_seen>=?""",
            (rec["title"], rec.get("seller_id") or -1, window),
        ).fetchone()[0]
        if others and others >= 2:
            score += 0.3
            why.append(f"titel_bei_{others}_verkaeufern")

    return min(round(score, 3), 1.0), why


MAX_SELLER_FETCHES = 6      # per cycle; real cycles need 0-2

# Walls that were caught rather than propagated, so the end of the cycle can
# tell the difference between "nothing went wrong" and "something did, and we
# carried on anyway". Cleared at the start of every cycle.
WALL_SEEN: list[str] = []
PROBE_PER_PAGE = 48         # match the poll size; a probe is not a licence to ask for more


def seller_profile(client, con: sqlite3.Connection, seller_id: int | None,
                   budget: list[int] | None = None) -> dict | None:
    """Seller country and reputation, cached, fetched only when it matters.

    The catalog response has neither field, and the item-detail endpoint is 404
    for an anonymous session, but /api/v2/users/{id} answers with both. Calling
    it per listing would multiply the request budget several times over, so it
    is called only for a listing that has already cleared the deal gate, at
    most MAX_SELLER_FETCHES times a cycle, and never twice for the same seller.
    """
    if not seller_id:
        return None
    row = con.execute(
        """SELECT seller_id, login, country, city, feedback_count,
                  positive_feedback_count, feedback_reputation, item_count, business
           FROM sellers WHERE seller_id=?""", (seller_id,)).fetchone()
    if row:
        keys = ("seller_id", "login", "country", "city", "feedback_count",
                "positive_feedback_count", "feedback_reputation", "item_count",
                "business")
        return dict(zip(keys, row))
    if client is None:
        return None
    if budget is not None:
        if budget[0] <= 0:
            return None
        budget[0] -= 1
    try:
        data = api_get(client, con, f"{BASE}/api/v2/users/{seller_id}", {})
    except SessionWall as e:
        # A wall here is about the connection, not about this one seller. The
        # catalog poll is the asset and should not die for a profile lookup, so
        # the cycle continues; but the backoff api_get just set has to SURVIVE
        # the cycle, and run_cycle used to clear it wholesale on any successful
        # poll. Recording it lets that clearing step know a wall was seen.
        log(f"WARN: seller lookup hit a wall ({e}); backoff kept, profile skipped")
        if budget is not None:
            budget[0] = 0          # stop asking this endpoint for the rest of the cycle
        WALL_SEEN.append(str(e))
        return None
    except httpx.HTTPError as e:
        log(f"WARN: seller {seller_id} lookup failed: {type(e).__name__}")
        return None
    u = (data or {}).get("user") or data or {}
    prof = {
        "seller_id": seller_id,
        "login": u.get("login"),
        "country": (u.get("country_iso_code") or u.get("country_code") or "").upper()[:2] or None,
        "city": u.get("city"),
        "feedback_count": u.get("feedback_count"),
        "positive_feedback_count": u.get("positive_feedback_count"),
        "feedback_reputation": u.get("feedback_reputation"),
        "item_count": u.get("item_count"),
        "business": 1 if u.get("business") else 0,
    }
    con.execute(
        """INSERT OR REPLACE INTO sellers (seller_id, login, country, city,
               feedback_count, positive_feedback_count, feedback_reputation,
               item_count, business, fetched_at)
           VALUES (:seller_id, :login, :country, :city, :feedback_count,
               :positive_feedback_count, :feedback_reputation, :item_count,
               :business, :fetched_at)""",
        {**prof, "fetched_at": now_iso()})
    con.commit()
    return prof


def seller_risk(prof: dict | None, brand_key: str, total: float,
                med: float) -> tuple[float, list[str]]:
    """Counterfeit risk contributed by the seller profile.

    A brand-new account with no history selling a hype brand well under the
    market is the classic shape; an established account with real feedback is
    the opposite. Nothing here fires without a profile, so a lookup that failed
    costs no false accusation.
    """
    if not prof:
        return 0.0, []
    score, why = 0.0, []
    feedback = prof.get("feedback_count")
    reputation = prof.get("feedback_reputation")
    if feedback is not None and feedback == 0:
        if brand_key in HYPE_BRANDS and med > 0 and total < 0.4 * med:
            score += 0.35
            why.append("neuer_verkaeufer_hype_billig")
        else:
            score += 0.1
            why.append("keine_bewertungen")
    elif feedback is not None and feedback < 5 and brand_key in HYPE_BRANDS:
        score += 0.15
        why.append("kaum_bewertungen_hype")
    if reputation is not None and feedback and feedback >= 10 and reputation < 0.6:
        score += 0.2
        why.append(f"schlechte_reputation_{reputation:.2f}")
    return score, why


def record_alert(con: sqlite3.Connection, rec: dict, ctx: dict) -> int:
    """Freeze one scoring decision into the alerts table; returns its rowid."""
    row = {
        "listing_id": rec["id"],
        "alerted_at": now_iso(),
        "search_tag": rec["search_tag"],
        "title": rec.get("title"),
        "brand": rec.get("brand"),
        "brand_norm": rec.get("brand_norm") or brand_norm_of(rec.get("brand")),
        "size": rec.get("size"),
        "size_class": rec.get("size_class") or size_class_of(rec.get("size")),
        "condition": rec.get("condition"),
        "cond_tier": rec.get("cond_tier"),
        "garment_class": rec.get("garment_class"),
        "country": rec.get("country"),
        "price_at_alert": rec.get("price"),
        "total_at_alert": rec.get("total_price"),
        "favourites_at_alert": rec.get("favourites"),
        "promoted": rec.get("promoted"),
        "seller_id": rec.get("seller_id"),
        "listing_age_min": ctx.get("listing_age_min"),
        "posted_at": ctx.get("posted_at"),
        "comp_n": ctx.get("comp_n"),
        "comp_median": ctx.get("comp_median"),
        "comp_p25": ctx.get("comp_p25"),
        "comp_p75": ctx.get("comp_p75"),
        "discount_pct": ctx.get("discount_pct"),
        "margin_eur": ctx.get("margin_eur"),
        "deal_ratio_used": ctx.get("deal_ratio_used"),
        "min_comps_used": ctx.get("min_comps_used"),
        "comp_window_used": ctx.get("comp_window_used"),
        "size_filter": ctx.get("size_filter"),
        "settings_json": ctx.get("settings_json"),
        "fake_risk": ctx.get("fake_risk"),
        "fake_risk_reasons": ctx.get("fake_risk_reasons"),
        "profile_score": ctx.get("profile_score"),
        "quality": ctx.get("quality"),
        "priority": ctx.get("priority"),
        "sent": ctx.get("sent", 0),
        "suppress_reason": ctx.get("suppress_reason"),
        "cycle_backlog_n": ctx.get("cycle_backlog_n"),
    }
    cur = con.execute(
        f"""INSERT INTO alerts ({', '.join(row)}) VALUES ({', '.join(':' + k for k in row)})""",
        row,
    )
    return int(cur.lastrowid or 0)


# How many alerts a day are allowed to make a sound, and how many are allowed
# to arrive at all. The second number is the one that was missing: capping
# interruptions while letting the tail through silently produced 319 pushes on
# 2026-09-09 against an owner target of roughly 50, and ntfy's free tier
# answered 429 for the rest of the day. Everything below the send budget is
# still scored and still recorded in the alerts table, so nothing is lost for
# the backtest; it just does not reach the phone.
RING_BUDGET_PER_DAY = 15
SEND_BUDGET_PER_DAY = 60


# A young listing that already carries hearts, per the owner's 2026-09-08
# direction: "wenn junge posts schon paar like haben solls laut klingeln".
# Not a likes-per-time ratio. The bot polls newest_first every five minutes, so
# the age of a freshly found listing is a draw from the poll interval (median
# 3.2 min over 33,231 live rows) rather than a market fact; dividing by it
# reorders the top of the alert list by poll luck. Holding age roughly constant
# and reading the raw count is the same idea without the noisy denominator.
# The count earns its own term: across alert candidates the mean discount is
# 56.0% at zero hearts, 55.7% at one and 55.8% at two, so hearts are not a
# restatement of the deal depth already in q.
YOUNG_POST_MAX_MIN = 60     # older than this is not a "young post" any more
FRESH_LIKE_CAP = 5          # hearts beyond this add nothing
FRESH_LIKE_WEIGHT = 0.35    # the strongest boost a young, liked listing can get


def alert_quality(discount_pct: float, margin_eur: float, fake: float,
                  country: str | None, size_ok_core: bool,
                  prof: float | None, fresh_likes: int = 0) -> float:
    """One number for how good a candidate is, on the criteria the owner named.

    Deal depth and absolute margin carry the weight, because a 60% discount on
    a 12 EUR item is worth less attention than a 45% discount on a 90 EUR one.
    Fake risk, size and location adjust it, hearts on a still-young listing
    lift it, and the learned taste score nudges within that frame rather than
    overriding it.
    """
    q = discount_pct + min(margin_eur, 80.0)
    q *= (1.0 - min(fake, 1.0) * 0.6)
    if size_ok_core:
        q *= 1.15
    if country and country != "DE":
        q *= 0.80
    if fresh_likes > 0:
        q *= 1.0 + FRESH_LIKE_WEIGHT * min(fresh_likes, FRESH_LIKE_CAP) / FRESH_LIKE_CAP
    if prof is not None:
        q *= 0.7 + 0.6 * prof
    return round(q, 3)


def alert_priority(discount_pct: float, fake: float, country: str | None,
                   size_ok_core: bool, prof: float | None,
                   con: sqlite3.Connection | None = None,
                   margin_eur: float = 0.0, fresh_likes: int = 0) -> int:
    """ntfy priority: which alerts are allowed to ring.

    An absolute score cannot do this job. Measured against 27,831 real rows,
    a fixed ladder put 46% of candidates in the ringing tier once country data
    existed, which is 833 ringing notifications a day, and 0% before it, which
    is a ladder that never rings at all. Both are the same mistake: the bar was
    set against an imagined stream rather than the real one.

    So the bar is relative. A candidate rings only if it beats the day's own
    competition, measured on the candidates already recorded in the last 24
    hours. That makes the loud tier self-limiting at roughly RING_BUDGET_PER_DAY
    however the market behaves, and it means "the best of today" rather than
    "above a number someone guessed".

    Returns 0 for "do not send at all". The first version of this capped the
    loud tier and let everything below it through silently, on the reasoning
    that volume should stay where the owner set it. Volume did not stay there:
    the owner asked for roughly 50 a day and the watcher pushed 319 on
    2026-09-09, which was invisible until the alerts table started recording
    the evening before. ntfy counts every message against a daily quota
    whatever its priority, so at 16:40Z the free tier answered 429 and the
    phone went silent for the rest of the day, dropping the good alerts along
    with the filler. A cap on interruptions is not a cap on volume, and this
    function now sets both.

    The baseline deliberately counts every SCORED candidate rather than only
    the sent ones. Ranking against what was sent would ratchet: once the tail
    stops being sent, the worst sent alert becomes the bar to beat, the bar
    collapses towards the best of a shrinking set, and the cap stops capping.

    With no history yet, it falls back to absolute cuts, deliberately generous:
    a cold start should ring for the obvious ones rather than stay silent while
    it learns.
    """
    q = alert_quality(discount_pct, margin_eur, fake, country, size_ok_core, prof,
                      fresh_likes=fresh_likes)
    if con is None:
        return 2 if fake >= 0.4 else (5 if q >= 90 else (3 if q >= 55 else 2))
    try:
        window = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        # The stored quality, not a re-derivation from discount and margin: the
        # score carries multipliers for size, country, fake risk and taste, so
        # comparing a multiplied candidate against an unmultiplied baseline
        # would let ordinary candidates clear the bar on the boost alone.
        recent = [r[0] for r in con.execute(
            """SELECT quality FROM alerts
               WHERE alerted_at >= ? AND quality IS NOT NULL""",
            (window,)).fetchall()]
    except sqlite3.Error:
        recent = []
    if len(recent) < RING_BUDGET_PER_DAY:
        # Too little history to rank against; be generous rather than silent.
        return 2 if fake >= 0.4 else (5 if q >= 90 else (3 if q >= 55 else 2))
    recent.sort(reverse=True)
    ring_bar = recent[min(RING_BUDGET_PER_DAY, len(recent)) - 1]
    send_bar = recent[min(SEND_BUDGET_PER_DAY, len(recent)) - 1]
    if q < send_bar and len(recent) > SEND_BUDGET_PER_DAY:
        return 0          # outside today's send budget; recorded, not pushed
    if fake >= 0.4:
        return 2          # a flagged listing never interrupts, whatever it scores
    if q >= ring_bar:
        return 5
    return 3


CORE_SIZE_CLASSES = {"s", "m", "l"}


def score_and_alert(con: sqlite3.Connection, rec: dict, search: dict, settings: dict,
                    env: dict, backlog_n: int | None = None, client=None,
                    seller_budget: list[int] | None = None) -> bool:
    """Score one new listing against its comp pool; push at most one alert.

    Returns True when an alert was sent (caller enforces the per-cycle cap).
    Comp pool = same search tag + brand family + condition tier + garment
    class, within the comp window. Class "other" (bags, caps, shoes) never
    alerts. Every candidate that clears the deal gate is written to alerts,
    sent or suppressed, so the record of what was decided survives the
    listings row being overwritten on the next re-sight.
    """
    # Both price gates read total_price, the number a buyer actually pays and
    # the one every comp is measured in. The floor used to read the ex-fee
    # price, which let sub-floor items through on the fee alone.
    if rec["total_price"] < settings["min_price"]:
        return False
    price_max = search.get("price_max")
    if price_max is not None and rec["total_price"] > price_max:
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
    if search.get("alerts_disabled"):
        return False

    # Size gate: alerting narrows to the classes that resell fastest, while the
    # comp pool below stays deliberately unfiltered. Every size keeps feeding
    # the price database; only the phone gets the focused set.
    allowed = search.get("size_classes") or settings.get("size_classes") or DEFAULT_SIZE_CLASSES
    size_class = rec.get("size_class") or size_class_of(rec.get("size"))
    if size_class not in allowed:
        return False

    window = (datetime.now(timezone.utc) - timedelta(days=settings["comp_window_days"])).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    brand_key = rec.get("brand_norm") or brand_norm_of(rec["brand"])
    comps = [
        row[0]
        for row in con.execute(
            """SELECT total_price FROM listings
               WHERE search_tag=? AND brand_norm=? AND cond_tier=? AND garment_class=? AND id!=?
                 AND last_seen>=? AND total_price BETWEEN 3 AND 400
                 AND COALESCE(is_kid,0)=0""",
            (rec["search_tag"], brand_key, rec["cond_tier"], rec["garment_class"],
             rec["id"], window),
        ).fetchall()
    ]
    if len(comps) < settings["min_comps"]:
        return False
    med = statistics.median(comps)
    deal_ratio = search.get("deal_ratio", settings["deal_ratio"])
    if rec["total_price"] > deal_ratio * med:
        return False

    # From here the candidate is a decision worth recording, whatever happens.
    quant = sorted(comps)
    p25 = quant[max(0, int(0.25 * (len(quant) - 1)))]
    p75 = quant[min(len(quant) - 1, int(0.75 * (len(quant) - 1)))]
    pct = round(100 * (1 - rec["total_price"] / med))
    fake, why = fake_risk_score(con, rec, med)
    prof = seller_profile(con=con, client=client, seller_id=rec.get("seller_id"),
                          budget=seller_budget)
    s_score, s_why = seller_risk(prof, brand_key, rec["total_price"], med)
    fake, why = min(round(fake + s_score, 3), 1.0), why + s_why
    reasons = ",".join(why)
    con.execute("UPDATE listings SET fake_risk=?, fake_risk_reasons=? WHERE id=?",
                (fake, reasons, rec["id"]))
    taste = profile_score(con, rec)
    # The seller's country is the listing's shipping origin; the catalog
    # response never carries it, so it arrives with the profile above.
    country = rec.get("country") or (prof or {}).get("country")
    if country and not rec.get("country"):
        con.execute("UPDATE listings SET country=? WHERE id=?", (country, rec["id"]))
    min_margin = float(settings.get("min_margin", 0) or 0)

    ctx = {
        "comp_n": len(comps), "comp_median": med, "comp_p25": p25, "comp_p75": p75,
        "discount_pct": pct, "margin_eur": round(med - rec["total_price"], 2),
        "deal_ratio_used": deal_ratio, "min_comps_used": settings["min_comps"],
        "comp_window_used": settings["comp_window_days"],
        "size_filter": ",".join(allowed), "fake_risk": fake, "fake_risk_reasons": reasons,
        "profile_score": taste, "cycle_backlog_n": backlog_n,
        "listing_age_min": listing_age_min(con, rec["id"]),
        "posted_at": rec.get("posted_at"),
        "settings_json": json.dumps({"settings": settings, "search": search}, default=str)[:4000],
    }

    def drop(reason: str) -> bool:
        record_alert(con, rec, {**ctx, "sent": 0, "suppress_reason": reason, "priority": 0})
        log(f"suppressed ({reason}): {rec['id']} {rec['title']} @ {rec['total_price']}")
        return False

    if fake >= float(settings.get("fake_risk_suppress", 0.7)):
        return drop("fake_risk")
    if min_margin and (med - rec["total_price"]) < min_margin:
        return drop("min_margin")
    # A listing outside Germany carries shipping the comp median does not, so
    # it has to beat the same bar with headroom rather than merely reach it.
    # Unknown country is treated as domestic: the field is forward-only, and
    # penalising every pre-country row would silence the watcher for weeks.
    if country and country != "DE":
        headroom = float(settings.get("foreign_advantage_eur", 8))
        if rec["total_price"] + headroom > deal_ratio * med:
            return drop("country")
    if taste is not None and taste < float(settings.get("profile_suppress", 0.15)):
        rated = con.execute(
            """SELECT COUNT(*) FROM alert_feedback f JOIN alerts a ON a.id=f.alert_id
               WHERE a.brand_norm=? AND a.garment_class=? AND a.size_class=?""",
            (brand_key, rec.get("garment_class"),
             rec.get("size_class") or size_class_of(rec.get("size"))),
        ).fetchone()[0]
        if rated >= int(settings.get("profile_min_rated", 8)):
            return drop("learned")

    margin = med - rec["total_price"]
    # Hearts count towards the score only while the listing is still young.
    # An old listing's hearts say the market looked and did not buy; a young
    # one's say demand showed up within minutes. Same number, opposite meaning,
    # and only the second is the signal the owner asked to ring for.
    age = post_age_min(rec.get("posted_at"))
    fresh_likes = (rec.get("favourites") or 0) if (
        age is not None and age <= YOUNG_POST_MAX_MIN) else 0
    quality = alert_quality(pct, margin, fake, country,
                            size_class in CORE_SIZE_CLASSES, taste,
                            fresh_likes=fresh_likes)
    ctx["quality"] = quality
    prio = alert_priority(pct, fake, country, size_class in CORE_SIZE_CLASSES, taste,
                          con=con, margin_eur=margin, fresh_likes=fresh_likes)
    if prio == 0:
        # Scored, ranked, and outside today's send budget. The snapshot is kept
        # with its full context so the backtest sees the whole candidate stream;
        # only the push is withheld.
        return drop("send_budget")
    lines = [
        f"{rec['brand']} | {rec['condition']} | Gr. {rec['size']} | {rec['garment_class']}",
        f"{rec['total_price']:.2f} EUR inkl. Gebuehr, Median vergleichbar {med:.2f} EUR ({pct}% drunter)",
        f"{len(comps)} Vergleichsangebote | Marge {med - rec['total_price']:.2f} EUR"
        + (f" | Land {country}" if country else ""),
        f"{human_age(age)} online"
        + (f" | {rec['favourites']} Herzen" if (rec.get("favourites") or 0) else "")
        + (" | frisch und schon gefragt" if fresh_likes else ""),
    ]
    if fake >= float(settings.get("fake_risk_flag", 0.4)):
        lines.insert(0, f"FAKE-RISIKO {fake:.0%}: {reasons}")
    links = reverse_image_links(rec.get("photo_url"))
    if links:
        lines.append("Bildcheck: " + links["lens"])

    ok = notify(
        env,
        title=f"Deal: {rec['title']}",
        message="\n".join(lines),
        click=rec["url"],
        priority=prio,
        actions=feedback_actions(env, rec["id"]),
    )
    alert_id = record_alert(con, rec, {
        **ctx, "sent": 1 if ok else 0, "priority": prio,
        "suppress_reason": None if ok else "notify_failed",
    })
    if ok:
        con.execute("UPDATE listings SET alerted=1 WHERE id=?", (rec["id"],))
        log(f"ALERT sent (p{prio}, alert {alert_id}): {rec['id']} {rec['title']} @ {rec['total_price']}")
        return True
    return False


def human_age(minutes: float | None) -> str:
    """Listing age for the notification line, in the unit a reader thinks in."""
    if minutes is None:
        return "Alter unbekannt,"
    if minutes < 90:
        return f"seit {int(round(minutes))} Min."
    if minutes < 60 * 36:
        return f"seit {minutes / 60:.1f} Std."
    return f"seit {minutes / 1440:.1f} Tagen"


def post_age_min(posted_at: str | None) -> float | None:
    """Minutes since the listing was actually posted, or None if unknown.

    Distinct from listing_age_min below, which measures time since WE first saw
    it and is therefore ~0 on every alert: the bot polls newest_first, so it
    finds listings within minutes and then believes every one of them is brand
    new. Measured on 2026-09-08, 7 of 107 alerts were on listings between 3.8
    hours and 5.05 days old, four of which went out ringing.
    """
    posted = parse_ts(posted_at)
    if not posted:
        return None
    return round((datetime.now(timezone.utc) - posted).total_seconds() / 60.0, 1)


def listing_age_min(con: sqlite3.Connection, listing_id: int) -> float | None:
    """Minutes between first sighting and now, for backtest replay context."""
    row = con.execute("SELECT first_seen FROM listings WHERE id=?", (listing_id,)).fetchone()
    first = parse_ts(row[0]) if row else None
    if not first:
        return None
    return round((datetime.now(timezone.utc) - first).total_seconds() / 60.0, 1)


def reverse_image_links(photo_url: str | None) -> dict[str, str] | None:
    """Reverse-image-search deep links for one listing photo.

    Deep links rather than browser automation: Lens has no API and driving its
    UI breaks on consent screens, while a URL the phone opens directly works
    every time and costs nothing to build.
    """
    if not photo_url:
        return None
    enc = urllib.parse.quote(photo_url, safe="")
    return {
        "lens": f"https://lens.google.com/uploadbyurl?url={enc}",
        "bing": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{enc}",
        "yandex": f"https://yandex.com/images/search?rpt=imageview&url={enc}",
    }


FEEDBACK_VERDICTS = {"good", "bad", "bought"}


def feedback_actions(env: dict, listing_id: int) -> list[dict] | None:
    """The three rating buttons carried by every alert.

    They publish to a second ntfy topic rather than to this machine: the phone
    is on cellular and cannot reach a local port, and the watcher reads that
    topic on its own schedule. Thumbs up/down is one tap from the notification
    shade, which is the only interaction rate that survives contact with a
    real day.
    """
    topic = env.get("NTFY_FEEDBACK_TOPIC")
    if not topic:
        return None
    def button(label: str, verdict: str) -> dict:
        return {
            "action": "http", "label": label,
            "url": f"https://ntfy.sh/{topic}",
            "method": "POST", "body": f"{verdict} {listing_id}",
            "clear": False,
        }
    return [button("\U0001F44D", "good"), button("\U0001F44E", "bad"), button("Gekauft", "bought")]


def notify(env: dict, title: str, message: str, click: str | None = None,
           priority: int = 4, actions: list[dict] | None = None) -> bool:
    topic = env.get("NTFY_TOPIC")
    if not topic:
        log("WARN: NTFY_TOPIC not configured; alert not sent")
        return False
    body = {"topic": topic, "title": title, "message": message, "priority": priority, "tags": ["shirt"]}
    if click:
        body["click"] = click
    if actions:
        body["actions"] = actions[:3]
    try:
        r = httpx.post("https://ntfy.sh/", json=body, timeout=15)
        if r.status_code != 200:
            # Silence here is how 24 refusals produced no log line at all on
            # 2026-09-09 while the phone stayed quiet: the daily quota was
            # exhausted and nothing said so. 429 is the one worth naming,
            # because it is self-inflicted rather than a network fault.
            detail = r.text.strip()[:200]
            log(f"WARN: ntfy refused the push, HTTP {r.status_code}: {detail}"
                + ("  (daily quota; the send budget is what prevents this)"
                   if r.status_code == 429 else ""))
        return r.status_code == 200
    except httpx.HTTPError as e:
        log(f"WARN: ntfy send failed: {e}")
        return False


# -------------------------------------------------------------------- cycle

def is_catch_up(con: sqlite3.Connection, n_new: int) -> bool:
    """Is this cycle working through a backlog, or just watching a busy market?

    Both look identical from inside one poll: a lot of listings the database has
    not seen. What tells them apart is whether time passed. If the previous
    successful poll was five minutes ago, forty new listings are forty fresh
    listings and racing for them is the entire point. If it was yesterday, the
    same forty are stale and alerting on them wins nothing.
    """
    last = parse_ts(meta_get(con, "last_success"))
    if last is None:
        # No successful poll on record: a fresh database, or the first cycle
        # after a reset. Whatever arrives now has unknown age, so treat a large
        # batch as backlog.
        return n_new > BACKLOG_SUPPRESS
    gap_min = (datetime.now(timezone.utc) - last).total_seconds() / 60.0
    if gap_min <= BACKLOG_GAP_MIN:
        return False
    return n_new > BACKLOG_SUPPRESS


def poll_search(client: httpx.Client, con: sqlite3.Connection, search: dict, settings: dict,
                env: dict, seller_budget: list[int] | None = None) -> bool:
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
    catch_up = is_catch_up(con, len(new_recs))
    if catch_up:
        # A gap preceded this cycle, but the batch is not therefore stale: the
        # catalogue page holds the newest listings, so most of what arrives
        # after a night is minutes old. Keep the genuinely fresh ones and drop
        # only what the clock says is actually old.
        scorable = [r for r in new_recs
                    if (age := post_age_min(r.get("posted_at"))) is not None
                    and age <= CATCH_UP_FRESH_MIN]
        log(f"{tag}: {len(new_recs)} new listings after a gap, "
            f"{len(scorable)} still fresh enough to score")
    else:
        scorable = new_recs
    alerts = 0
    for rec in scorable:
        if alerts >= MAX_ALERTS_PER_SEARCH:
            break
        if score_and_alert(con, rec, search, settings, env, backlog_n=len(new_recs),
                           client=client, seller_budget=seller_budget):
            alerts += 1
    if new_recs and not catch_up:
        log(f"{tag}: {len(new_recs)} new listings, {alerts} alerted")
    elif catch_up and alerts:
        log(f"{tag}: {alerts} alerted from the fresh part of the catch-up")
    con.commit()
    return True


def recheck_queue(con: sqlite3.Connection, limit: int) -> list[tuple[int, str]]:
    """Which listings this hour's fixed page budget is spent on.

    The budget is 25 pages an hour, 600 a day, against a corpus taking in
    ~13.8k listings a day. No policy makes that a census, so the only question
    is which 4% to buy, and oldest-first was the wrong answer twice over: on
    36k rows it needs two months for one pass, and it spends the budget on the
    listings least likely to still be readable.

    Three tiers, in order:

      1. Anything we alerted on. ~50 a day, so it always fits, and it is the
         only cohort that can ever tell us whether the deal gate is right.
      2. A window 12h to 10d after posting. Under 12h too little has happened
         to be worth a page; past 10d the sold panel gives way to a 404 and
         the verdict degrades from "sold" to "gone, cause unknown".
      3. Oldest unresolved, so nothing is stranded forever.

    Ordered by favourites inside tier 2: a listing nobody hearted rarely
    resolves into anything, and the budget is small enough to care.
    """
    now = datetime.now(timezone.utc)
    def stamp(**kw):
        return (now - timedelta(**kw)).strftime("%Y-%m-%dT%H:%M:%SZ")

    picked: dict[int, str] = {}

    def take(sql: str, params: tuple) -> None:
        if len(picked) >= limit:
            return
        for item_id, url in con.execute(sql, params + (limit - len(picked),)):
            if url and item_id not in picked:
                picked[item_id] = url

    # Tier 1: alerted, not yet resolved, given a few hours to actually happen.
    take("""SELECT l.id, l.url FROM listings l
            WHERE l.gone_at IS NULL AND l.url IS NOT NULL
              AND EXISTS (SELECT 1 FROM alerts a WHERE a.listing_id = l.id)
              AND l.first_seen < ?
            ORDER BY l.first_seen ASC LIMIT ?""", (stamp(hours=RECHECK_MIN_AGE_H),))
    # Tier 2: inside the window where the page still distinguishes sold from gone.
    take("""SELECT id, url FROM listings
            WHERE gone_at IS NULL AND url IS NOT NULL
              AND posted_at IS NOT NULL AND posted_at BETWEEN ? AND ?
              AND last_seen < ?
            ORDER BY favourites DESC, posted_at ASC LIMIT ?""",
         (stamp(days=RECHECK_MAX_AGE_D), stamp(hours=RECHECK_MIN_AGE_H),
          stamp(hours=RECHECK_INTERVAL_MIN / 60 * 12)))
    # Tier 3: the old oldest-first sweep, as the tail.
    take("""SELECT id, url FROM listings
            WHERE gone_at IS NULL AND url IS NOT NULL AND last_seen < ?
            ORDER BY last_seen ASC LIMIT ?""", (stamp(hours=RECHECK_MIN_AGE_H),))
    return list(picked.items())


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
    rows = recheck_queue(con, RECHECK_BATCH)
    verdicts = []      # (item_id, verdict: str, source: str)
    for item_id, item_url in rows:
        if not item_url:
            continue
        try:
            r = client.get(item_url)
        except httpx.HTTPError:
            continue
        final = str(r.url)
        if r.status_code in (403, 429) or r.status_code >= 500:
            # This loop fetches item PAGES, not the JSON API, so it cannot go
            # through api_get. Without its own check a refusal was invisible
            # here: 404 and 410 mean gone, a redirect means a wall, 200 means
            # alive, and everything else fell through every branch and simply
            # went round again. That made the largest request block of the
            # cycle, 25 pages, the only one that would walk straight into a
            # 429 twenty-five times and then repeat in an hour.
            wait = SERVER_BACKOFF_MIN if r.status_code >= 500 else WALL_BACKOFF_MIN
            retry_after = r.headers.get("retry-after")
            if retry_after and retry_after.isdigit():
                wait = max(wait, int(retry_after) // 60 + 1)
            set_backoff(con, wait, f"recheck saw HTTP {r.status_code}", escalate=True)
            WALL_SEEN.append(f"recheck HTTP {r.status_code}")
            log(f"WARN: recheck saw HTTP {r.status_code}; pass abandoned, nothing recorded")
            meta_set(con, "last_recheck", now_iso())
            con.commit()
            return
        if "/items/" not in final or WALL_URL.search(final):
            # Bounced off the item page. That is a statement about our
            # session, not about the listing, and it is unknowable which.
            # Abandon the pass with nothing written.
            log(f"WARN: item page bounced to {final}; recheck abandoned, nothing recorded")
            meta_set(con, "last_recheck", now_iso())
            con.commit()
            return
        verdict, source = item_page_verdict(r.status_code, r.text)
        # The page we already fetched carries the current price, so a still-live
        # listing yields a second observation days after the poll lost sight of
        # it. That is where price cuts actually live.
        verdicts.append((item_id, verdict,
                         item_page_price(r.text) if verdict == "alive" else None,
                         source))
        time.sleep(random.uniform(1.5, 3.0))

    counts = Counter(v for _, v, _, _ in verdicts)
    gone_n, sold_n = counts["gone"], counts["sold"]
    if verdicts and gone_n / len(verdicts) > GONE_RATE_CEILING:
        # A large simultaneous sweep of 404s is a session symptom every time,
        # never a market event. The ceiling covers the 404 class ONLY: a sold
        # verdict comes from a named plugin carrying a theme, which a login
        # wall or an error page cannot fabricate, so a high sold rate is real
        # and must not be thrown away with it.
        log(f"WARN: recheck discarded, {gone_n}/{len(verdicts)} read as 404 "
            f"(> {GONE_RATE_CEILING:.0%} is systemic, not deletions)")
        meta_set(con, "last_recheck", now_iso())
        con.commit()
        return
    if verdicts and counts["unknown"] / len(verdicts) > GONE_RATE_CEILING:
        # A page that answers 200 while carrying neither status plugin is not
        # an item page. That is the shape a soft wall takes now that a hard
        # redirect is caught above, so it aborts rather than records.
        log(f"WARN: recheck discarded, {counts['unknown']}/{len(verdicts)} pages "
            f"carried no status plugin; that is a wall, not a market")
        meta_set(con, "last_recheck", now_iso())
        con.commit()
        return

    ts = now_iso()
    price_moves = 0
    for item_id, verdict, page_price, source in verdicts:
        if verdict == "alive":
            price_moves += record_page_price(con, item_id, page_price, ts)
            con.execute("UPDATE listings SET last_seen=? WHERE id=?", (ts, item_id))
        elif verdict == "unknown":
            continue                     # never guess; leave it for the next pass
        else:
            # sold | gone | closed all end the listing's life; only sold is a
            # demand signal, and gone_source keeps the three apart forever.
            con.execute("UPDATE listings SET gone_at=?, sold_flag=?, gone_source=? WHERE id=?",
                        (ts, 1 if verdict == "sold" else 0, source, item_id))
    meta_set(con, "last_recheck", ts)
    con.commit()
    if rows:
        log(f"recheck: {len(rows)} visited, {sold_n} sold, {gone_n} deleted, "
            f"{counts['closed']} closed, {counts['unknown']} unreadable, "
            f"{price_moves} price change(s)")


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


# The length bound is not cosmetic. The feedback topic is public by obscurity,
# so anyone who learns the name can post to it, and an unbounded digit run
# reaches sqlite as an integer too large to bind: OverflowError, raised inside
# the poll, every cycle, until someone notices. A Vinted listing id is ten
# digits; eighteen is already far past any real one and inside SQLite's range.
FEEDBACK_RE = re.compile(r"^(good|bad|bought)\s+(\d{1,18})$", re.I)


def _ntfy_poll(topic: str, since: str) -> list[dict]:
    """One non-streaming read of a ntfy topic. Never raises."""
    try:
        r = httpx.get(f"https://ntfy.sh/{topic}/json",
                      params={"poll": "1", "since": since}, timeout=15)
        if r.status_code != 200:
            log(f"WARN: feedback poll HTTP {r.status_code}")
            return []
        out = []
        for line in r.text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
    except httpx.HTTPError as e:
        log(f"WARN: feedback poll failed: {e}")
        return []


def feedback_target(con: sqlite3.Connection, listing_id: int) -> tuple[bool, int | None]:
    """Is this id one of ours, and which alert does the rating belong to?

    A rating is joined to its alert snapshot when one exists, but a missing
    snapshot must never discard the rating: the tap is the scarce thing here,
    it cannot be repeated, and ntfy forgets the message after about twelve
    hours. Requiring the alert row is what silently dropped the owner's first
    two real taps on 2026-09-08 while the alerts table was failing to record.
    A listing this database has actually seen is proof enough that the id came
    from one of our own notifications; anything else is noise on a public
    topic and is still refused.
    """
    row = con.execute(
        "SELECT id FROM alerts WHERE listing_id=? ORDER BY id DESC LIMIT 1",
        (listing_id,)).fetchone()
    if row:
        return True, int(row[0])
    seen = con.execute("SELECT 1 FROM listings WHERE id=?", (listing_id,)).fetchone()
    return bool(seen), None


def ingest_feedback(con: sqlite3.Connection, env: dict) -> int:
    """Pull rating taps off the feedback topic into alert_feedback.

    The topic is public by obscurity like the alert topic, so the parser is
    strict and every id is checked against a real alert before it is stored:
    anything else on that topic is someone else's noise, not a rating. ntfy
    keeps messages for about twelve hours, so a tap made while this machine is
    off past that window is lost; --feedback is the durable way in.
    """
    topic = env.get("NTFY_FEEDBACK_TOPIC")
    if not topic:
        return 0
    since = meta_get(con, "feedback_since") or "all"
    messages = _ntfy_poll(topic, since)
    inserted, last_id = 0, None
    for m in messages:
        mid = m.get("id")
        if mid:
            last_id = mid
        if m.get("event") != "message":
            continue
        match = FEEDBACK_RE.match((m.get("message") or "").strip())
        if not match:
            continue
        verdict, listing_id = match.group(1).lower(), int(match.group(2))
        try:
            known, alert_id = feedback_target(con, listing_id)
        except (OverflowError, sqlite3.Error):
            # Belt as well as braces: the pattern above bounds the length, and
            # this makes sure no shape of stranger input can end the poll for
            # the messages behind it.
            continue
        if not known:
            log(f"WARN: rating '{verdict} {listing_id}' names a listing this "
                f"database has never seen; ignored as stranger noise")
            continue
        cur = con.execute(
            """INSERT OR IGNORE INTO alert_feedback
                   (listing_id, alert_id, verdict, received_at, source, ntfy_msg_id, raw)
               VALUES (?, ?, ?, ?, 'ntfy', ?, ?)""",
            (listing_id, alert_id, verdict, now_iso(), mid, json.dumps(m)[:2000]),
        )
        inserted += cur.rowcount
    if last_id:
        meta_set(con, "feedback_since", last_id)
    con.commit()
    return inserted


def cli_feedback(listing_id: int, verdict: str) -> int:
    """Record a rating by hand, for when a tap did not make it through."""
    verdict = verdict.lower()
    if verdict not in FEEDBACK_VERDICTS:
        print(f"verdict must be one of {sorted(FEEDBACK_VERDICTS)}")
        return 2
    con = db_connect()
    try:
        row = con.execute(
            "SELECT id FROM alerts WHERE listing_id=? ORDER BY id DESC LIMIT 1", (listing_id,)
        ).fetchone()
        con.execute(
            """INSERT INTO alert_feedback
                   (listing_id, alert_id, verdict, received_at, source, raw)
               VALUES (?, ?, ?, ?, 'cli', NULL)""",
            (listing_id, row[0] if row else None, verdict, now_iso()),
        )
        con.commit()
        print(f"recorded: {verdict} for listing {listing_id}"
              + ("" if row else " (no alert row; feedback stored unlinked)"))
        return 0
    finally:
        con.close()


# Trustworthy outcome data starts after the v2 session fix: the 375 rows before
# it were produced by a dead session against a login wall and were reset.
OUTCOME_EPOCH = "2026-09-08"

# Keep/drop/add thresholds. Judgment values where marked; the sell-through row
# stays unset until enough gone events exist to derive one. Documented in
# status/watcher.md, evaluated here, decided by the owner.
BRAND_RULES = {
    "comp_coverage_min": 0.60,     # judgment: share of candidates reaching min_comps
    "margin_floor_eur": 15.0,      # owner's minimum worthwhile flip
    "spread_min": 1.5,             # judgment: p75/p25, mispricing room
    "precision_drop": 0.20,        # judgment: below this with enough ratings = drop flag
    "precision_min_rated": 10,     # judgment: ratings needed before precision counts
    "fake_risk_manual": 0.50,      # judgment: above this the brand needs a manual check
}


def brand_report(settings: dict | None = None) -> int:
    """Weekly per-brand keep/drop/add evaluation against the database."""
    con = db_connect()
    try:
        cfg_settings = settings or load_config()["settings"]
        window = (datetime.now(timezone.utc)
                  - timedelta(days=cfg_settings["comp_window_days"])).strftime("%Y-%m-%dT%H:%M:%SZ")
        deal_ratio = cfg_settings["deal_ratio"]
        min_comps = cfg_settings["min_comps"]

        print(f"Brand-Report  {now_iso()}")
        print(f"Fenster {cfg_settings['comp_window_days']}d | deal_ratio {deal_ratio} | min_comps {min_comps}")
        print(f"Outcome-Daten gelten ab {OUTCOME_EPOCH} (frueheres wurde als unbrauchbar verworfen)\n")

        brands = [r[0] for r in con.execute(
            """SELECT brand_norm FROM listings
               WHERE brand_norm IS NOT NULL AND brand_norm!='' AND last_seen>=?
               GROUP BY brand_norm HAVING COUNT(*) >= 25 ORDER BY COUNT(*) DESC""",
            (window,),
        ).fetchall()]

        hdr = (f"{'Marke':<22}{'n':>7}{'Median':>9}{'p25':>7}{'p75':>7}{'Spread':>8}"
               f"{'Marge@Gate':>12}{'gone%':>7}{'h→gone':>8}{'Praez.':>8}{'Fake':>7}")
        print(hdr)
        print("-" * len(hdr))
        verdicts = []
        for b in brands:
            prices = [r[0] for r in con.execute(
                """SELECT total_price FROM listings
                   WHERE brand_norm=? AND last_seen>=? AND COALESCE(is_kid,0)=0
                     AND total_price BETWEEN 3 AND 400""", (b, window)).fetchall()]
            if len(prices) < 10:
                continue
            prices.sort()
            med = statistics.median(prices)
            p25 = prices[int(0.25 * (len(prices) - 1))]
            p75 = prices[int(0.75 * (len(prices) - 1))]
            spread = (p75 / p25) if p25 else 0.0
            margin_at_gate = (1 - deal_ratio) * med

            gone_n, gone_hours = con.execute(
                """SELECT COUNT(*), AVG((julianday(gone_at)-julianday(first_seen))*24)
                   FROM listings WHERE brand_norm=? AND gone_at IS NOT NULL
                     AND gone_at >= ? AND gone_source IS NOT NULL""",
                (b, OUTCOME_EPOCH)).fetchone()
            total_n = len(prices)
            gone_rate = (gone_n / total_n) if total_n else 0.0

            good, bad = con.execute(
                """SELECT SUM(CASE WHEN f.verdict IN ('good','bought') THEN 1 ELSE 0 END),
                          SUM(CASE WHEN f.verdict='bad' THEN 1 ELSE 0 END)
                   FROM alert_feedback f JOIN alerts a ON a.id=f.alert_id
                   WHERE a.brand_norm=?""", (b,)).fetchone()
            good, bad = (good or 0), (bad or 0)
            rated = good + bad
            precision = (good / rated) if rated else None

            fake_avg = con.execute(
                "SELECT AVG(fake_risk) FROM listings WHERE brand_norm=? AND fake_risk IS NOT NULL",
                (b,)).fetchone()[0]

            print(f"{b:<22}{total_n:>7}{med:>9.2f}{p25:>7.0f}{p75:>7.0f}{spread:>8.2f}"
                  f"{margin_at_gate:>12.2f}{gone_rate*100:>7.1f}"
                  f"{(gone_hours or 0):>8.1f}"
                  + (f"{precision*100:>7.0f}%" if precision is not None else f"{'n/a':>8}")
                  + (f"{fake_avg:>7.2f}" if fake_avg is not None else f"{'-':>7}"))

            flags = []
            if margin_at_gate < BRAND_RULES["margin_floor_eur"]:
                flags.append(f"R2 Marge {margin_at_gate:.1f} EUR < {BRAND_RULES['margin_floor_eur']:.0f}")
            if spread and spread < BRAND_RULES["spread_min"]:
                flags.append(f"R3 Spread {spread:.2f} < {BRAND_RULES['spread_min']}")
            if precision is not None and rated >= BRAND_RULES["precision_min_rated"] \
                    and precision < BRAND_RULES["precision_drop"]:
                flags.append(f"R5 Praezision {precision:.0%} bei n={rated}")
            if fake_avg is not None and fake_avg > BRAND_RULES["fake_risk_manual"]:
                flags.append(f"R6 Fake-Risiko {fake_avg:.2f} -> manuelle Pruefung")
            verdicts.append((b, flags, rated))

        print("\nGroessen-Nachfrage (Anteil pro Klasse, Fenster):")
        for b, _, _ in verdicts:
            rows = con.execute(
                """SELECT size_class, COUNT(*) FROM listings
                   WHERE brand_norm=? AND last_seen>=? AND COALESCE(is_kid,0)=0
                     AND size_class NOT IN ('unknown','kids','other')
                   GROUP BY size_class ORDER BY COUNT(*) DESC LIMIT 6""",
                (b, window)).fetchall()
            tot = sum(c for _, c in rows) or 1
            share = "  ".join(f"{sc}:{100*c/tot:.0f}%" for sc, c in rows)
            print(f"  {b:<22}{share}")

        print("\nBewertung:")
        for b, flags, rated in verdicts:
            if not flags:
                print(f"  KEEP  {b}" + (f"  (n_bewertet={rated})" if rated else "  (noch keine Bewertungen)"))
            else:
                print(f"  PRUEF {b}: " + "; ".join(flags))
                print(f"        Vorschlag: deal_ratio-Override oder alerts_disabled: true fuer den Tag")
        print("\nEntscheidung liegt beim Owner. Drop heisst alerts_disabled, nicht Search entfernen:")
        print("die Preisdaten laufen weiter, sie sind das eigentliche Asset.")

        no_outcome = con.execute(
            "SELECT COUNT(*) FROM listings WHERE gone_at IS NOT NULL AND gone_at>=? AND gone_source IS NOT NULL",
            (OUTCOME_EPOCH,)).fetchone()[0]
        if no_outcome < 300:
            print(f"\nHINWEIS: erst {no_outcome} vertrauenswuerdige gone-Events. Sell-Through-Regel (R4)")
            print("bleibt bis ~300 Events unbewertet, ebenso die formale Schwellen-Kalibrierung.")
        return 0
    finally:
        con.close()


def probe_fields() -> int:
    """Print one raw catalog item so field availability is read, not assumed."""
    cfg = load_config()
    con = db_connect()
    client = new_client()
    try:
        if not ensure_session(client):
            print("no session")
            return 1
        search = cfg["searches"][0]
        try:
            data = api_get(client, con, f"{BASE}/api/v2/catalog/items",
                           {"search_text": search["query"], "per_page": 1, "page": 1})
        except (SessionWall, httpx.HTTPError) as e:
            print(f"Probe nicht moeglich: {type(e).__name__}: {e}")
            return 1
        items = data.get("items") or []
        if not items:
            print("no items returned")
            return 1
        item = items[0]
        print("=== TOP-LEVEL KEYS ===")
        print(", ".join(sorted(item.keys())))
        print("\n=== FULL ITEM JSON ===")
        print(json.dumps(item, indent=2, ensure_ascii=False)[:12000])
        print("\n=== KEY PATHS ===")
        def walk(node, prefix=""):
            if isinstance(node, dict):
                for k, v in sorted(node.items()):
                    walk(v, f"{prefix}.{k}" if prefix else k)
            elif isinstance(node, list):
                if node:
                    walk(node[0], f"{prefix}[0]")
            else:
                print(f"  {prefix} = {str(node)[:80]}")
        walk(item)
        print("\n=== COUNTRY EXTRACTION ===")
        print(f"item_country() -> {item_country(item)!r}")
        print("\n=== PAGINATION KEYS ===")
        print(", ".join(sorted(k for k in data.keys() if k != "items")))
        for k in ("pagination", "meta"):
            if k in data:
                print(f"{k}: {json.dumps(data[k], ensure_ascii=False)[:600]}")
        return 0
    finally:
        con.close()


def probe_search(query: str) -> int:
    """One-off viability census for a candidate search, before it earns a slot."""
    cfg = load_config()
    con = db_connect()
    client = new_client()
    try:
        if not ensure_session(client):
            print("no session")
            return 1
        try:
            data = api_get(client, con, f"{BASE}/api/v2/catalog/items",
                           {"search_text": query, "per_page": PROBE_PER_PAGE, "page": 1})
        except (SessionWall, httpx.HTTPError) as e:
            print(f"Probe {query!r} nicht moeglich: {type(e).__name__}: {e}")
            print("Die API antwortet gerade nicht; spaeter erneut versuchen.")
            return 1
        items = data.get("items") or []
        if not items:
            print(f"{query!r}: no items")
            return 1
        prices, sizes, brands = [], {}, {}
        for it in items:
            total = float((it.get("total_item_price") or {}).get("amount")
                          or (it.get("price") or {}).get("amount") or 0)
            if total:
                prices.append(total)
            sc = size_class_of(it.get("size_title"))
            sizes[sc] = sizes.get(sc, 0) + 1
            bn = brand_norm_of(it.get("brand_title"))
            brands[bn] = brands.get(bn, 0) + 1
        prices.sort()
        med = statistics.median(prices) if prices else 0.0
        # The resale-friendly band, counted in BOTH notations a market might
        # use. The first version of this counted W-numbers only and reported 0%
        # for premium women's denim, where sellers list XS/S/M instead; that
        # made a strong candidate look unviable for a reason that was about the
        # measurement rather than the market.
        target_classes = {"w26", "w27", "w28", "w29", "w30", "w31",
                          "xs", "s", "m"}
        w_target = sum(c for sc, c in sizes.items() if sc in target_classes)
        top_brand, top_n = max(brands.items(), key=lambda kv: kv[1])
        purity = top_n / len(items)
        # What a flip actually clears at the configured bar, which is the number
        # that decides whether a search is worth a poll slot.
        margin_at_gate = (1 - cfg["settings"]["deal_ratio"]) * med
        pagination = data.get("pagination") or {}
        total_entries = pagination.get("total_entries")

        print(f"Probe: {query!r}")
        print(f"  Seite 1: {len(items)} Artikel" + (f" | Gesamt laut API: {total_entries}" if total_entries else ""))
        print(f"  Preis (inkl. Gebuehr): Median {med:.2f} | p25 {prices[len(prices)//4]:.2f} | p75 {prices[3*len(prices)//4]:.2f}")
        print(f"  Zielgroessen (W26-W31 oder XS/S/M): {w_target}/{len(items)}"
              f" = {100*w_target/len(items):.0f}%")
        print(f"  Marge am Gate bei deal_ratio {cfg['settings']['deal_ratio']}:"
              f" {margin_at_gate:.2f} EUR")
        print(f"  Haeufigste Marke: {top_brand} ({100*purity:.0f}% Reinheit)")
        print("  Groessenklassen: " + ", ".join(f"{k}:{v}" for k, v in
                                                sorted(sizes.items(), key=lambda kv: -kv[1])[:8]))
        checks = {
            "Volumen (Seite voll / >=300 gesamt)": len(items) >= 90 or (total_entries or 0) >= 300,
            "Median >= 30 EUR": med >= 30,
            "Marge am Gate >= 15 EUR": margin_at_gate >= 15,
            "Zielgroessen >= 25%": w_target / len(items) >= 0.25,
            "Marken-Reinheit >= 70%": purity >= 0.70,
        }
        print("  Aufnahme-Kriterien:")
        for name, passed in checks.items():
            print(f"    [{'x' if passed else ' '}] {name}")
        if all(checks.values()):
            print("  => AUFNEHMEN")
        elif not checks["Marge am Gate >= 15 EUR"] and med >= 30:
            tighter = 1 - 15 / med if med else 1
            print(f"  => NUR mit deal_ratio <= {tighter:.2f} (dann traegt die Marge 15 EUR)")
        else:
            print("  => NICHT aufnehmen")
        return 0
    finally:
        con.close()


def image_check(listing_id: int) -> int:
    """Print the reverse-image links for one listing, for a manual legit check."""
    con = db_connect()
    try:
        row = con.execute(
            """SELECT title, brand, size, condition, total_price, url, photo_url, fake_risk,
                      fake_risk_reasons, country
               FROM listings WHERE id=?""", (listing_id,)).fetchone()
        if not row:
            print(f"listing {listing_id} not in database")
            return 1
        (title, brand, size, cond, total, url, photo, fake, why, country) = row
        print(f"{title}")
        print(f"{brand} | {cond} | Gr. {size} | {total:.2f} EUR" + (f" | {country}" if country else ""))
        if fake is not None:
            print(f"Fake-Risiko: {fake:.0%}" + (f" ({why})" if why else ""))
        print(f"Anzeige: {url}")
        links = reverse_image_links(photo)
        if not links:
            print("kein Foto gespeichert")
            return 1
        print(f"Foto:    {photo}")
        for name, link in links.items():
            print(f"{name+':':<9}{link}")
        return 0
    finally:
        con.close()


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
        # Feedback rides on ntfy, not on Vinted, so it is collected before the
        # backoff gate: a Vinted wall must not also silence the rating channel.
        try:
            got = ingest_feedback(con, env)
            if got:
                log(f"feedback: {got} new rating(s)")
        except (httpx.HTTPError, sqlite3.Error, ValueError) as e:
            log(f"WARN: feedback poll failed: {type(e).__name__}: {e}")
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
        WALL_SEEN.clear()
        seller_budget = [MAX_SELLER_FETCHES]
        try:
            for search in cfg["searches"]:
                try:
                    if poll_search(client, con, search, cfg["settings"], env,
                                   seller_budget=seller_budget):
                        ok = True
                except SessionWall:
                    raise
                except (httpx.HTTPError, sqlite3.Error, ValueError, KeyError) as e:
                    if is_schema_error(e):
                        # Not a bad search: the database cannot store what this
                        # code produces, and every remaining search would fail
                        # the same way. Ending the cycle non-zero is what makes
                        # it visible; as a warning it read like one flaky poll.
                        log(f"FATAL: schema mismatch on {search['tag']}: {e}")
                        raise
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
            if WALL_SEEN:
                # Except when a wall fell somewhere else in this same cycle.
                # Vinted rate-limits by client, not by endpoint, so a 429 on the
                # seller endpoint while the catalog still answers is luck rather
                # than permission. Clearing the backoff here would erase the
                # refusal and its escalation level, and the next cycle would
                # poll at full rate five minutes later, indefinitely.
                log(f"backoff kept: {len(WALL_SEEN)} wall(s) during this cycle "
                    f"({WALL_SEEN[0]})")
            else:
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
    ap.add_argument("--brand-report", action="store_true",
                    help="weekly per-brand keep/drop/add evaluation")
    ap.add_argument("--probe-fields", action="store_true",
                    help="print one raw catalog item (country/shipping field census)")
    ap.add_argument("--probe-search", metavar="QUERY",
                    help="one-off viability census for a candidate search")
    ap.add_argument("--image-check", type=int, metavar="LISTING_ID",
                    help="print reverse-image-search links for one listing")
    ap.add_argument("--feedback", nargs=2, metavar=("LISTING_ID", "VERDICT"),
                    help="record a rating by hand: good | bad | bought")
    args = ap.parse_args()
    if args.test_notify:
        env = load_env()
        ok = notify(env, "Vinted watcher test",
                    "Wenn du das liest, funktioniert der Alert-Kanal.\n"
                    "Die drei Knoepfe unten sind der Bewertungskanal.",
                    click=BASE, actions=feedback_actions(env, 0))
        print("test notify:", "sent" if ok else "FAILED")
        if not env.get("NTFY_FEEDBACK_TOPIC"):
            print("NOTE: NTFY_FEEDBACK_TOPIC not set; no rating buttons attached")
        sys.exit(0 if ok else 1)
    if args.status:
        print_status()
        return
    if args.brand_report:
        sys.exit(brand_report())
    if args.probe_fields:
        sys.exit(probe_fields())
    if args.probe_search:
        sys.exit(probe_search(args.probe_search))
    if args.image_check:
        sys.exit(image_check(args.image_check))
    if args.feedback:
        sys.exit(cli_feedback(int(args.feedback[0]), args.feedback[1]))
    sys.exit(run_cycle())


if __name__ == "__main__":
    main()
