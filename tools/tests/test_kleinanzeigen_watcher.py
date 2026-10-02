"""Regression suite for the Kleinanzeigen bed watcher (Karlsruhe, 180x200).

The expensive failure is a missed bed, so the size cases below are the
spellings real Karlsruhe sellers used on 2026-10-02 ("180 × 200 cm",
"1,80 x 2,00", "180/200", "2,00 m lang, 1,80 m breit"), plus the near
misses that must stay quiet (140x200, 200x200, a 200x180 wardrobe, a
mattress "fuer Boxspringbett 180x200").

The cycle tests drive run_cycle end to end through an httpx MockTransport
that plays both Kleinanzeigen and ntfy.sh, so they assert on the pushes
that would reach the phone, not on helper return values.

No network. Run: uv run --with pytest --with httpx --with pyyaml pytest \
    tools/tests/test_kleinanzeigen_watcher.py
"""

import html
import importlib.util
import json
import re
import sys
from datetime import timedelta
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
WATCHER_PATH = ROOT / "workspace" / "projects" / "kleinanzeigen-watcher" / "watcher" / "ka_watcher.py"
FIXTURES = ROOT / "tools" / "fixtures" / "kleinanzeigen"


@pytest.fixture(scope="module")
def kw():
    spec = importlib.util.spec_from_file_location("ka_watcher_under_test", WATCHER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ size

@pytest.mark.parametrize("text", [
    "Boxspringbett 180x200",
    "Massivholzbett im japanischen Stil 180 × 200 cm inkl. 2 Rollroste",
    "Polsterbett 1,80 x 2,00",
    "Ruf Bett Elektrisch 180/200",
    "Bett 1.8x2m",
    "Doppelbett 200x180",
    "Das Bett ist ca. 2,00 m lang, 1,80 m breit und 50 cm hoch.",
    "Breite: 1,80 m",
    "180er Boxspringbett",
    "Liegefläche 180 cm, Kopfteil gepolstert",
])
def test_size_matches_every_way_sellers_write_it(kw, text):
    assert kw.size_verdict(text)[0] == "match"


@pytest.mark.parametrize("text", [
    "Bett inkl. Matratze mit Stauraum 1,40m x 2,00",
    "140*200 cm Bett mit Matratze",
    "Ikea Metallbett Noresund 140 breit",
    "Boxspringbett 200x200 - 05.10.2026",
    "Doppelbett mit Stapelmöglichkeit 1,90 x 1,90",
    "Bett 180 breit, 220 lang",
])
def test_other_sizes_are_rejected(kw, text):
    assert kw.size_verdict(text)[0] == "other"


@pytest.mark.parametrize("text", [
    "Bett mit Lattenrost",
    "Nachttisch 40x40",               # not a bed dimension
    "Tel. 0176/2001234",              # digits, not a size
    "2 x Kissen",                     # a count, not 2 m
    "ab dem 12.10. abzuholen",
])
def test_no_size_stays_unknown(kw, text):
    assert kw.size_verdict(text)[0] == "unknown"


# ------------------------------------------------------------------- bed

@pytest.mark.parametrize("title,expected", [
    ("Boxspringbett 180x200", "bed"),
    ("Bett inkl. Matratze", "bed"),
    ("Schrank, Bett, Tempur, Nolte, Überbau", "bed"),
    ("JYSK HASLEV Bettgestell 180 × 200 cm", "bed"),
    ("Matratze für Boxspringbett 180x200", "not_bed"),
    ("Spannbettlaken 180x200", "not_bed"),
    ("Bettwäsche 135x200", "not_bed"),
    ("Matratzentopper 180x200cm", "not_bed"),
    ("Lattenrost", "not_bed"),
    ("Kleiderschrank ca. 200x180", "not_bed"),
    ("Ankleidezimmer IKEA Pax Schränke weiß", "not_bed"),
    ("Ikea Hemnes 180x200", "unclear"),
])
def test_bed_verdict(kw, title, expected):
    assert kw.bed_verdict(title) == expected


# --------------------------------------------------------------- storage

@pytest.mark.parametrize("text", [
    "Boxspringbett 180x200 mit Bettkasten",
    "Bett 180x200 mit 2 Bettkästen",
    "Polsterbett mit Stauraum",
    "Stauraumbett 180x200",
    "Bett mit 4 Schubladen",
    "Kommode und Bett mit Schubladen",
    "Lattenrost hochklappbar, darunter viel Platz",
    "Bett mit Hebemechanismus",
    "Bett mit Bettschubladen",
])
def test_storage_found(kw, text):
    assert kw.storage_verdict(text)[0] == "yes"


def test_storage_evidence_is_the_whole_word(kw):
    assert kw.storage_verdict("Bett mit 2 Bettkästen")[1] == "Bettkästen"
    assert kw.storage_verdict("Stauraumbett 180x200")[1] == "Stauraumbett"


@pytest.mark.parametrize("text,expected", [
    ("Boxspringbett 180x200 ohne Bettkasten", "no"),
    ("Bett, kein Stauraum vorhanden", "no"),
    ("Bett 180x200 inkl. 2 Nachttische mit Schublade", "unknown"),
    ("Bett 180x200, Nachttischschublade klemmt", "unknown"),
    ("Bett 180x200 aus Massivholz", "unknown"),
])
def test_storage_absent_or_unsaid(kw, text, expected):
    assert kw.storage_verdict(text)[0] == expected


def test_storage_rule_on_the_card(kw):
    with_box = {"title": "Boxspringbett 180x200 mit Bettkasten", "snippet": ""}
    without = {"title": "Boxspringbett 180x200 ohne Bettkasten", "snippet": ""}
    unsaid = {"title": "Boxspringbett 180x200", "snippet": "Guter Zustand"}
    assert kw.decide_from_card(with_box, 180, 200, storage=True)[0] == "match"
    assert kw.decide_from_card(without, 180, 200, storage=True)[0] == "no_storage"
    assert kw.decide_from_card(unsaid, 180, 200, storage=True)[0] is None   # read its page
    assert kw.decide_from_card(unsaid, 180, 200, storage=False)[0] == "match"


def test_wanted_ads_never_alert(kw):
    ad = {"title": "Suche Boxspringbett 180x200", "snippet": ""}
    assert kw.decide_from_card(ad, 180, 200)[0] == "wanted"


# --------------------------------------------------------------- parsing

def test_parse_cards_on_live_markup(kw):
    cards = kw.parse_cards((FIXTURES / "search_cards.snippet.html").read_text(encoding="utf-8"))
    assert [c["id"] for c in cards] == [1000000001, 1000000002, 1000000003]
    first = cards[0]
    assert first["url"] == "https://www.kleinanzeigen.de/s-anzeige/boxspringbett-180x200/1000000001-81-9188"
    assert first["title"] == "Boxspringbett 180x200"
    assert first["price_text"] == "150 €"
    assert first["plz_ort"] == "76187 Karlsruhe"
    assert first["posted_text"] == "Heute, 09:43"
    assert first["image"].startswith("https://img.kleinanzeigen.de/")
    assert cards[1]["posted_text"] == ""                  # pinned card, no date
    assert cards[2]["price_text"] == "Zu verschenken"     # not "NP war 600€"
    assert kw.price_eur(cards[2]["price_text"]) == 0.0
    assert kw.price_eur("1.350 € VB") == 1350.0


def test_parse_detail_keeps_the_full_description(kw):
    desc = kw.parse_detail((FIXTURES / "ad_detail.snippet.html").read_text(encoding="utf-8"))
    assert "2,00 m lang, 1,80 m breit" in desc
    assert "\n" in desc
    assert kw.decide_from_detail({"title": "Bett mit Lattenrost"}, desc, 180, 200)[0] == "match"


# ----------------------------------------------------------------- cycle

FEED_A = "https://www.kleinanzeigen.de/s-schlafzimmer/karlsruhe/c81l9186"
FEED_B = "https://www.kleinanzeigen.de/s-karlsruhe/180x200/k0l9186"
CFG = {
    "feeds": [{"name": "a", "url": FEED_A}, {"name": "b", "url": FEED_B}],
    "match": {"width_cm": 180, "length_cm": 200, "price_max": None, "require_storage": True},
    "alert_priority": 5,
    "browse_url": "https://www.kleinanzeigen.de/s-karlsruhe/bett-180x200/k0l9186",
}
ENV = {"NTFY_TOPIC": "betten-ka-test"}


def card(adid: int, title: str, desc: str = "", price: str = "150 €") -> str:
    ld = json.dumps({"title": title, "description": desc, "@type": "ImageObject",
                     "contentUrl": f"https://img.kleinanzeigen.de/x/{adid}.jpg"}, ensure_ascii=False)
    href = f"/s-anzeige/x/{adid}-81-9188"
    return (f'<li data-clickable="card"><article class="flex" data-adid="{adid}" data-href="{href}">'
            f'<div><script type="application/ld+json">{ld}</script></div><div><div>'
            f'<div><svg viewBox="0 0 24 24"><path d="M1Z"></path></svg><span>76133 Karlsruhe</span></div>'
            f'<div><svg viewBox="0 0 24 24"><path d="M1Z"></path></svg><span>Heute, 12:00</span></div></div>'
            f'<div><h3><a href="{href}">{html.escape(title)}</a></h3><p>{html.escape(desc[:60])}</p>'
            f'<div><p>{price}</p></div></div></div></article></li>')


def page(*cards: str) -> str:
    return f'<html><body><ul id="srchrslt-adtable">{"".join(cards)}</ul></body></html>'


def detail(desc: str) -> str:
    return ('<p id="viewad-description-text"\n class="text-force-linebreak "\n itemprop="description">\n'
            + desc.replace("\n", "<br />") + "</p>")


class Site:
    """Kleinanzeigen + ntfy.sh behind one MockTransport."""

    def __init__(self):
        self.feeds = {FEED_A: page(card(1, "Boxspringbett 180x200 mit Bettkasten"), card(2, "Lattenrost")),
                      FEED_B: page(card(1, "Boxspringbett 180x200 mit Bettkasten"))}
        self.details: dict[int, str] = {}
        self.feed_status = 200
        self.ntfy_status = 200
        self.pushes: list[dict] = []
        self.detail_hits: list[int] = []
        self.kleinanzeigen_hits = 0

    def handler(self, request):
        if request.url.host == "ntfy.sh":
            body = json.loads(request.content)
            if self.ntfy_status == 200:
                self.pushes.append(body)
            return httpx.Response(self.ntfy_status, json={"code": 42901} if self.ntfy_status != 200 else {})
        self.kleinanzeigen_hits += 1
        url = str(request.url)
        m = re.search(r"/s-anzeige/x/(\d+)-", url)
        if m:
            adid = int(m.group(1))
            self.detail_hits.append(adid)
            return httpx.Response(200, text=self.details.get(adid, "<html></html>"))
        return httpx.Response(self.feed_status, text=self.feeds.get(url, ""))

    def cycle(self, kw, con, dry_run=False):
        with httpx.Client(transport=httpx.MockTransport(self.handler)) as client:
            return kw.run_cycle(client, con, CFG, ENV, dry_run=dry_run, pause=0)

    def ad_pushes(self):
        return [p for p in self.pushes if p.get("click", "").startswith("https://www.kleinanzeigen.de/s-anzeige/")]


@pytest.fixture
def con(kw, tmp_path, monkeypatch):
    monkeypatch.setattr(kw, "DATA_DIR", tmp_path)
    monkeypatch.setattr(kw, "LOG_PATH", tmp_path / "watcher.log")
    c = kw.db_connect(tmp_path / "ads.db")
    yield c
    c.close()


def test_first_cycle_learns_the_market_without_alerting(kw, con):
    site = Site()
    assert site.cycle(kw, con) == 0
    assert site.ad_pushes() == []                      # already-listed beds are not news
    assert [p["title"] for p in site.pushes] == ["Bett-Wächter läuft"]
    assert "1 passende" in site.pushes[0]["message"]
    assert site.pushes[0]["click"] == CFG["browse_url"]
    assert site.detail_hits == []                      # no ad pages fetched for the seed
    assert site.cycle(kw, con) == 0
    assert len(site.pushes) == 1                       # start-up push is sent once


def test_new_hits_push_once_and_only_hits(kw, con):
    site = Site()
    site.cycle(kw, con)
    site.feeds[FEED_A] = page(
        card(11, "Boxspringbett 180x200 mit Bettkasten", "Gut erhalten"),
        card(12, "Bett mit Lattenrost", "Schönes Bett, wenig benutzt.", "40 €"),
        card(13, "Ikea Malm Bett 140x200cm mit Bettkasten"),
        card(14, "Matratze für Boxspringbett 180x200"),
        card(15, "Suche Bett 180x200 mit Stauraum"),
        card(16, "Bett Hemnes", "Gebraucht"),
        card(17, "Boxspringbett 180x200 ohne Bettkasten"),
        card(18, "Polsterbett 180x200", "Guter Zustand"),
        card(19, "Massivholzbett 180x200", "Buche"),
        card(1, "Boxspringbett 180x200 mit Bettkasten"),
        card(2, "Lattenrost"),
    )
    site.details = {12: detail("Verkaufe ein Bett.\nDas Bett ist ca. 2,00 m lang, 1,80 m breit.\n"
                               "Darunter zwei Schubladen."),
                    16: detail("Ikea Hemnes in 140x200, ohne Matratze."),
                    18: detail("Polsterbett mit großem Bettkasten, Gasdruckfedern."),
                    19: detail("Massivholzbett Buche, dazu 2 Nachttische mit Schublade.")}
    assert site.cycle(kw, con) == 0

    pushed = {p["click"].rsplit("/", 1)[1].split("-")[0]: p for p in site.ad_pushes()}
    assert set(pushed) == {"11", "12", "18"}
    # Only beds whose card left the size or the storage open had their page
    # read; "ohne Bettkasten" (17) is decided on the card.
    assert sorted(site.detail_hits) == [12, 16, 18, 19]
    twelve = pushed["12"]
    assert twelve["priority"] == 5
    assert "40 €" in twelve["message"] and "180 breit" in twelve["message"]
    assert "Stauraum (Schubladen)" in twelve["message"]
    assert "Stauraum (Bettkasten)" in pushed["18"]["message"]
    assert twelve["attach"] == "https://img.kleinanzeigen.de/x/12.jpg"
    assert twelve["actions"][0]["url"] == twelve["click"]

    site.cycle(kw, con)
    assert len(site.ad_pushes()) == 3                  # nothing pushed twice


def test_failed_push_is_retried_next_cycle(kw, con):
    site = Site()
    site.cycle(kw, con)
    site.feeds[FEED_A] = page(card(21, "Polsterbett 1,80 x 2,00 mit Stauraum"))
    site.ntfy_status = 429
    site.cycle(kw, con)
    assert site.ad_pushes() == []
    site.ntfy_status = 200
    site.cycle(kw, con)
    assert [p["title"] for p in site.ad_pushes()] == ["Polsterbett 1,80 x 2,00 mit Stauraum"]


def test_block_backs_off_then_warns_then_recovers(kw, con):
    site = Site()
    site.cycle(kw, con)
    site.feed_status = 403
    assert site.cycle(kw, con) == 1
    assert kw.meta_get(con, "backoff_until")
    hits = site.kleinanzeigen_hits
    for _ in range(kw.HEALTH_ALERT_AFTER - 1):
        assert site.cycle(kw, con) == 1
    assert site.kleinanzeigen_hits == hits             # the pause asks nothing
    warnings = [p for p in site.pushes if p["title"] == "Bett-Wächter bekommt keine Daten"]
    assert len(warnings) == 1 and "NICHT gemeldet" in warnings[0]["message"]

    kw.meta_set(con, "backoff_until", kw.iso(kw.utcnow() - timedelta(minutes=1)))
    site.feed_status = 200
    assert site.cycle(kw, con) == 0
    assert site.pushes[-1]["title"] == "Bett-Wächter läuft wieder"


def test_empty_page_is_a_failure_not_a_quiet_market(kw, con):
    site = Site()
    site.cycle(kw, con)
    site.feeds[FEED_A] = "<html><body>neues Layout</body></html>"
    assert site.cycle(kw, con) == 1
    assert kw.meta_get(con, "fail_streak") == "1"


def test_dry_run_writes_and_sends_nothing(kw, con):
    site = Site()
    assert site.cycle(kw, con, dry_run=True) == 0
    assert site.pushes == []
    assert con.execute("SELECT COUNT(*) FROM ads").fetchone()[0] == 0
    assert kw.meta_get(con, "seeded") is None
