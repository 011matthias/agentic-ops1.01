"""local_site_scan: the demo-target finder for the local route.

The negative cases are the contract. Each one is a misreading the 2026-11-19
Sellbird trial showed a US tool making on Karlsruhe sites: "& Partner" in a
firm name read as a decision maker, Doctolib not counted as online booking, a
failed map query reported as complete, a dead site leaving no record.

No network. Run: uv run --with pytest --with httpx pytest tools/tests/test_local_site_scan.py
"""
import asyncio
import csv
import json
import sys

import pytest

httpx = pytest.importorskip("httpx")

from hooklib import TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
import local_site_scan as lss  # noqa: E402


# ------------------------------------------------------------ owner (Impressum)

@pytest.mark.parametrize("text,owner", [
    ("Angaben gemäß § 5 TMG\nPraxis Dr. med. Ulf Lenk\nInhaber: Dr. med. Ulf Lenk\nWinterstraße 29", "Dr. med. Ulf Lenk"),
    ("Inhaberin\nFrau Dr. med. dent. Barbara Kühn\n76133 Karlsruhe", "Dr. med. dent. Barbara Kühn"),
    ("Musterbau GmbH\nvertreten durch den Geschäftsführer Hans-Peter Müller", "Hans-Peter Müller"),
    ("Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV: Rechtsanwalt Dr. Harald Wozniewski, Nowackanlage 2",
     "Dr. Harald Wozniewski"),
    ("Inh. Michael Meinzer Malermeister", "Michael Meinzer"),
    ("Inhaber ist Uwe Bauer.", "Uwe Bauer"),
    ("Geschäftsführer: Dipl.-Ing. Anna von Berg", "Dipl.-Ing. Anna von Berg"),
])
def test_owner_found(text, owner):
    assert lss.owner_from_impressum(text) == owner


@pytest.mark.parametrize("text", [
    "Google Maps — © Kohnle & Partner",                 # Sellbird's top-2 picks came from lines like this
    "Inhaber: Kohnle & Partner Rechtsanwälte",          # a firm, not a person
    "Geschäftsführer: siehe Handelsregister",
    "Verantwortlich: Musterstraße 4, 76133 Karlsruhe",  # an address, not a name
    "Kontakt\nTelefon 0721 123456",
])
def test_owner_not_invented(text):
    assert lss.owner_from_impressum(text) == ""


def test_html_to_text_keeps_line_structure():
    page = "<p>Inhaber:<br>Erika Musterfrau</p><script>var x='Inhaber: Fake Name'</script>"
    assert lss.owner_from_impressum(lss.html_to_text(page)) == "Erika Musterfrau"


# ------------------------------------------------------------ homepage reading

def test_booking_counts_german_vendors():
    assert lss.booking_tools('<a href="https://www.doctolib.de/praxis/karlsruhe/x">Termin</a>') == ["Doctolib"]
    assert lss.booking_tools('<iframe src="https://widget.treatwell.de/x">') == ["Treatwell"]
    assert lss.booking_tools("<a href='/termine'>Jetzt Online-Termin vereinbaren</a>") == ["Termin-Link"]
    assert lss.booking_tools("<p>Rufen Sie uns an.</p>") == []


OLD_SITE = """<html><head><title>Friseur Alt</title></head><body>
<p>Willkommen im Salon.</p><p>Öffnungszeiten Mo-Fr</p>
<a href="/impressum.html">Impressum</a><p>&copy; 2014 Friseur Alt</p></body></html>"""

MODERN_SITE = """<html><head><meta name="viewport" content="width=device-width">
<script type="application/ld+json">{"@type":"MedicalBusiness"}</script></head>
<body><a href="https://www.doctolib.de/x">Termin buchen</a><p>© 2025</p></body></html>"""


def test_read_home_scores_an_old_site():
    r = lss.read_home(OLD_SITE, "http://alt.example/", "friseur", 2026)
    assert r["status"] == "ok"
    assert r["score"] == 6  # no viewport 2, no https 1, ©2014 1, no schema 1, no booking 1
    assert r["copyright_year"] == "2014"
    assert r["impressum"] == "http://alt.example/impressum.html"


def test_read_home_modern_site_scores_zero():
    r = lss.read_home(MODERN_SITE, "https://neu.example/", "physio", 2026)
    assert (r["status"], r["score"], r["booking"]) == ("ok", 0, "Doctolib")


def test_booking_only_counts_where_people_book():
    r = lss.read_home(OLD_SITE, "https://alt.example/", "anwalt", 2026)
    assert "no online booking" not in r["reasons"]


@pytest.mark.parametrize("page,status", [
    ("<html><body>This domain may be for sale. sedo.com</body></html>", "parked"),
    ("<html><body><h1>Hier entsteht eine neue Internetpräsenz</h1></body></html>", "placeholder"),
    ("<html><body>cheap viagra and cialis, best casino</body></html>", "spam_injected"),
])
def test_read_home_dead_shapes(page, status):
    assert lss.read_home(page, "https://x.example/", "maler", 2026)["status"] == status


def test_placeholder_words_on_a_real_page_are_not_a_placeholder():
    page = MODERN_SITE.replace("</body>", "<p>" + "Text " * 200 + "Neue Website im Aufbau</p></body>")
    assert lss.read_home(page, "https://x.example/", "maler", 2026)["status"] == "ok"


# ------------------------------------------------------------ OpenStreetMap query

def test_build_query_area_and_around():
    q = lss.build_query(["zahnarzt", "maler"], area="Karlsruhe")
    assert 'area["name"="Karlsruhe"]' in q and 'nwr["amenity"="dentist"](area.a);' in q
    assert 'nwr["craft"="painter"](area.a);' in q and q.endswith("out center tags;")
    q2 = lss.build_query(["friseur"], around=(49.0, 8.4, 8))
    assert 'nwr["shop"="hairdresser"](around:8000,49.0,8.4);' in q2
    with pytest.raises(ValueError):
        lss.build_query(["maler"], area='Karls"ruhe')


async def _no_sleep(_):
    return None


def test_every_mirror_failing_is_an_error_not_an_empty_list():
    tr = httpx.MockTransport(lambda req: httpx.Response(504))

    async def go():
        async with httpx.AsyncClient(transport=tr) as c:
            await lss.fetch_overpass("q", c, rounds=2, sleep=_no_sleep)
    with pytest.raises(lss.OverpassUnavailable):
        asyncio.run(go())


def test_partial_overpass_answer_is_rejected():
    calls = []

    def handler(req):
        calls.append(req.url.host)
        if len(calls) == 1:  # 200, but Overpass timed out midway and says so in "remark"
            return httpx.Response(200, json={"remark": "runtime error: Query timed out", "elements": [{"id": 1}]})
        return httpx.Response(200, json={"elements": [{"id": 1}, {"id": 2}]})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await lss.fetch_overpass("q", c, sleep=_no_sleep)
    elements, mirror = asyncio.run(go())
    assert len(elements) == 2 and len(calls) == 2 and mirror == lss.MIRRORS[1]


# ------------------------------------------------------------ the whole scan

def _el(i, name, website="", **tags):
    t = {"name": name, "addr:street": "Teststraße", "addr:housenumber": str(i), **tags}
    if website:
        t["website"] = website
    return {"type": "node", "id": i, "tags": t}


ELEMENTS = [
    _el(1, "Kanzlei Kaputt", "http://kaputt.example", office="lawyer"),
    _el(2, "Zahnarzt Weg", "http://gone.example", amenity="dentist"),
    _el(3, "Friseur Alt", "alt.example", shop="hairdresser"),
    _el(4, "Maler Ohne", craft="painter"),
    _el(5, "Physio Neu", "https://neu.example", healthcare="physiotherapist"),
    _el(6, "Praxis Zert", "https://zert.example", amenity="doctors"),
    _el(7, "Bäckerei Fremd", "https://fremd.example", shop="bakery"),   # not a trade we scan
    {"type": "node", "id": 8, "tags": {"craft": "painter"}},           # no name
]


def _main_handler(req):
    host = req.url.host
    if req.method == "POST":
        return httpx.Response(200, json={"elements": ELEMENTS})
    if host == "kaputt.example":
        return httpx.Response(500)
    if host == "alt.example":
        if req.url.path == "/impressum.html":
            return httpx.Response(200, text="<p>Angaben gemäß § 5 TMG</p><p>Inhaberin: Erika Musterfrau</p>")
        return httpx.Response(200, text=OLD_SITE)
    if host == "neu.example":
        return httpx.Response(200, text=MODERN_SITE)
    if host == "zert.example":
        raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired", request=req)
    raise AssertionError(f"unexpected request {req.method} {req.url}")


def _insecure_handler(req):
    return httpx.Response(200, text=MODERN_SITE)


async def _resolver(host):
    return host != "gone.example"


def _scan(elements=None, resolver=_resolver):
    handler = _main_handler
    if elements is not None:
        def handler(req):
            return httpx.Response(200, json={"elements": elements})
    return asyncio.run(lss.scan(
        "q", list(lss.TRADES), transport=httpx.MockTransport(handler),
        insecure_transport=httpx.MockTransport(_insecure_handler),
        resolver=resolver, sleep=_no_sleep, this_year=2026))


def test_scan_end_to_end(tmp_path):
    rows, mirror = _scan()
    by = {r["name"]: r for r in rows}
    assert set(by) == {"Kanzlei Kaputt", "Zahnarzt Weg", "Friseur Alt", "Maler Ohne", "Physio Neu", "Praxis Zert"}
    assert by["Zahnarzt Weg"]["status"] == "domain_gone"
    assert by["Kanzlei Kaputt"]["status"] == "server_error"
    assert by["Praxis Zert"]["status"] == "ssl_broken"
    assert (by["Friseur Alt"]["status"], by["Friseur Alt"]["owner"]) == ("ok", "Erika Musterfrau")
    assert by["Friseur Alt"]["priority"] == "2 weak site"
    assert by["Maler Ohne"]["priority"] == "3 no website listed (unverified)"
    assert by["Physio Neu"]["priority"] == "4 site fine"
    assert [r["priority"][0] for r in rows] == sorted(r["priority"][0] for r in rows)
    assert {r["status"] for r in rows[:3]} == {"domain_gone", "server_error", "ssl_broken"}

    out = tmp_path / "scan.csv"
    lss.write_csv(rows, out)
    with out.open(encoding="utf-8-sig") as fh:
        back = list(csv.DictReader(fh))
    assert list(back[0]) == lss.COLUMNS
    alt = next(r for r in back if r["name"] == "Friseur Alt")
    assert alt["trade"] == "Friseur" and "not mobile-ready" in alt["reasons"]
    assert "email" not in json.dumps(back).lower()  # the tool collects no addresses to mail


def test_slow_site_gets_a_second_chance_before_it_is_called_dead():
    hits = {"slow.example": 0}

    def handler(req):
        if req.method == "POST":
            return httpx.Response(200, json={"elements": [
                _el(1, "Langsam Praxis", "https://slow.example", amenity="dentist"),
                _el(2, "Wirklich Weg", "https://down.example", amenity="dentist")]})
        if req.url.host == "down.example":
            raise httpx.ReadTimeout("timed out", request=req)
        hits["slow.example"] += 1
        if hits["slow.example"] == 1:  # busy under parallel load, answers on the retry
            raise httpx.ReadTimeout("timed out", request=req)
        return httpx.Response(200, text=MODERN_SITE)

    rows, _ = asyncio.run(lss.scan(
        "q", list(lss.TRADES), transport=httpx.MockTransport(handler),
        insecure_transport=httpx.MockTransport(_insecure_handler),
        resolver=_resolver, sleep=_no_sleep, this_year=2026))
    by = {r["name"]: r for r in rows}
    assert by["Langsam Praxis"]["status"] == "ok"
    assert by["Wirklich Weg"]["status"] == "no_answer"
    assert by["Wirklich Weg"]["reasons"] == ["no answer within 45 s"]


def test_scan_with_zero_businesses_stops():
    with pytest.raises(lss.OverpassUnavailable, match="zero businesses"):
        _scan(elements=[])


def test_scan_stops_when_dns_is_blind():
    async def blind(host):
        return False
    with pytest.raises(lss.OverpassUnavailable, match="DNS"):
        _scan(resolver=blind)


# ------------------------------------------------------------ Overpass server quirks (2026-11-25)

def test_overpass_requests_name_the_tool():
    """overpass-api.de answers a browser-looking agent with 406; it must get the tool's own."""
    seen = []

    def handler(req):
        seen.append(req.headers["user-agent"])
        return httpx.Response(200, json={"elements": [{"id": 1}]})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": lss.UA}) as c:
            return await lss.fetch_overpass("q", c, sleep=_no_sleep)
    asyncio.run(go())
    assert seen == [lss.OVERPASS_UA]


def test_one_empty_answer_is_a_server_failure_not_an_empty_town():
    calls = []

    def handler(req):
        calls.append(req.url.host)
        if len(calls) == 1:  # kumi.systems shape: 200, zero elements, area not resolved
            return httpx.Response(200, json={"elements": []})
        return httpx.Response(200, json={"elements": [{"id": 1}, {"id": 2}]})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await lss.fetch_overpass("q", c, sleep=_no_sleep)
    elements, mirror = asyncio.run(go())
    assert len(elements) == 2 and mirror == lss.MIRRORS[1]


# ------------------------------------------------------------ automation lens

HV_HOME = """<html><body><h1>Hausverwaltung Muster</h1>
<p>Telefon 0721 123456 · Telefax: 0721 123457</p>
<a href="/karriere">Karriere</a> <a href="/downloads">Formulare</a>
<a href="https://wa.me/49721123456">WhatsApp</a>
<p>Rückruf vereinbaren</p><a href="/impressum">Impressum</a></body></html>"""
HV_CAREERS = "<h2>Wir suchen</h2><p>Immobilienkaufmann und Bürokauffrau (m/w/d)</p><p>Buchhalter (m/w/d)</p>"
HV_DOWNLOADS = """<a href="/files/Selbstauskunft.pdf">Mieterselbstauskunft</a>
<a href="/files/Schadenmeldung.pdf">Schaden melden</a><a href="/files/Preisliste.pdf">Preise</a>"""


def test_automation_signals_read_a_paper_heavy_office():
    s = lss.automation_signals([(HV_HOME, "https://hv.example/"), (HV_CAREERS, "https://hv.example/karriere"),
                                (HV_DOWNLOADS, "https://hv.example/downloads")], "hausverwaltung")
    assert s["pdf_forms"] == "2"                      # the price list is not a form
    assert s["office_hiring"] == "Büro/Verwaltung, Buchhaltung"
    assert "WhatsApp" in s["tools"]
    # fax 1 + forms 2 + hiring 2 + WhatsApp intake 1 + callback 1; Hausverwaltung is not a booking trade
    assert s["auto_score"] == 7
    assert not any("appointments" in r for r in s["auto_reasons"])


def test_automation_signals_quiet_on_a_digital_practice():
    s = lss.automation_signals([(MODERN_SITE, "https://neu.example/")], "zahnarzt")
    assert (s["auto_score"], s["auto_reasons"]) == (0, [])
    assert "Doctolib" in s["tools"]


def test_hero_on_a_trade_site_is_the_strongest_software_signal():
    page = '<p>Anfrage</p><script src="https://app.hero-software.de/widget.js"></script>'
    s = lss.automation_signals([(page, "https://sanitaer.example/")], "sanitaer")
    assert "HERO" in s["tools"] and s["auto_score"] == 2


def test_a_team_page_is_not_a_job_ad():
    team = "<h2>Unser Team</h2><p>Anna Muster, Medizinische Fachangestellte</p><p>Bürokauffrau Eva Beispiel</p>"
    ad = "<h2>Stellenangebote</h2><p>Medizinische Fachangestellte (m/w/d) in Teilzeit</p>"
    assert lss.automation_signals([(team, "https://x.example/")], "tierarzt")["office_hiring"] == ""
    assert lss.automation_signals([(ad, "https://x.example/")], "tierarzt")["office_hiring"] == "Fachangestellte"


def test_patient_trades_are_not_automation_defaults():
    assert not {"arzt", "zahnarzt", "physio"} & set(lss.LENS_TRADES["automation"])
    assert {"arzt", "zahnarzt", "physio"} <= set(lss.LENS_TRADES["website"])


@pytest.mark.parametrize("text,hit", [
    ("Telefax: 0721 / 12 34 56", True), ("Fax +49 721 123456", True),
    ("Wir haben keine Faxe mehr", False), ("Fax: -", False),
])
def test_fax_pattern(text, hit):
    assert bool(lss.FAX.search(text)) is hit


def test_automation_lens_end_to_end():
    def handler(req):
        if req.method == "POST":
            return httpx.Response(200, json={"elements": [
                _el(1, "Hausverwaltung Muster", "https://hv.example", office="property_management"),
                _el(2, "Zahnarzt Digital", "https://neu.example", amenity="dentist"),
                _el(3, "Kfz Weg", "https://gone.example", shop="car_repair"),
                _el(4, "Hausverwaltung Muster", "https://hv.example", office="property_management",
                    **{"addr:street": "Zweitstraße"}),                       # same office, second map entry
                _el(5, "Versicherung Kette", "https://kette.example", office="insurance",
                    **{"brand:wikidata": "Q123"})]})
        page = {("hv.example", "/"): HV_HOME, ("hv.example", "/karriere"): HV_CAREERS,
                ("hv.example", "/downloads"): HV_DOWNLOADS,
                ("hv.example", "/impressum"): "<p>Geschäftsführer: Max Mustermann</p>",
                ("neu.example", "/"): MODERN_SITE, ("kette.example", "/"): HV_HOME,
                ("kette.example", "/karriere"): HV_CAREERS, ("kette.example", "/downloads"): HV_DOWNLOADS,
                ("kette.example", "/impressum"): "<p>Vorstand</p>"}.get((req.url.host, req.url.path))
        if page is None:
            raise AssertionError(f"unexpected request {req.url}")
        return httpx.Response(200, text=page, headers={"content-type": "text/html"})

    rows, _ = asyncio.run(lss.scan(
        "q", list(lss.TRADES), transport=httpx.MockTransport(handler),
        insecure_transport=httpx.MockTransport(_insecure_handler),
        resolver=_resolver_gone({"gone.example"}), sleep=_no_sleep, this_year=2026, lens="automation"))
    by = {r["name"]: r for r in rows}
    hv = by["Hausverwaltung Muster"]
    assert hv["priority"] == "1 strong automation fit" and hv["score"] == 7
    assert hv["owner"] == "Max Mustermann" and hv["office_hiring"] == "Büro/Verwaltung, Buchhaltung"
    assert by["Zahnarzt Digital"]["priority"] == "3 few signals"
    assert by["Kfz Weg"]["priority"] == "4 site gone or broken"
    assert rows[0]["name"] == "Hausverwaltung Muster"
    assert [r["name"] for r in rows].count("Hausverwaltung Muster") == 1
    # same paper-heavy site, but a brand location: not an owner-run prospect
    assert by["Versicherung Kette"]["priority"] == "8 chain or brand location (not owner-run)"
    assert by["Versicherung Kette"]["reasons"][0].startswith("chain or brand")


def _resolver_gone(gone):
    async def resolve(host):
        return host not in gone
    return resolve


def test_cli_rejects_unknown_trade():
    with pytest.raises(SystemExit):
        lss.main(["--area", "Karlsruhe", "--trades", "baecker"])
