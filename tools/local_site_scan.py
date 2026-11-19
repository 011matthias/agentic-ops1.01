# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27"]
# ///
"""Find demo-site targets: local businesses whose website is gone, broken or weak.

Lists the businesses of one town from OpenStreetMap, then checks each listed
website the way a German prospect's site has to be read: does the domain still
exist, does the page load without a certificate warning, is it parked or a
placeholder, is it mobile-ready, when was the footer year last touched, does
the practice or salon book online (Doctolib, Treatwell, Shore, ...), and who
runs it according to the Impressum.

    uv run tools/local_site_scan.py --area Karlsruhe
    uv run tools/local_site_scan.py --around 49.0094,8.4044,8 --trades arzt,zahnarzt
    uv run tools/local_site_scan.py --area Ettlingen --admin-level 8 --limit 50

Output: a CSV in .scratch/local-site-scan/ (gitignored: it holds owner names),
dead or broken sites first. No email addresses are collected: cold email is
retired for the local route (UWG §7), the approach is demo first, then post
or in person.

Built on the 2026-11-19 Sellbird trial, which showed what a US tool misreads on
German sites. Each guard below exists because that run hit the failure:
- every Overpass mirror throttled at once, and the tool still reported
  "14 of 14 queries" for a run where 7 failed, so here a failed or partial
  answer is an error, never an empty list;
- a site that did not load left no record, so here every check ends in a
  status, and "blocked our check" is kept apart from "dead";
- "no website" only meant OpenStreetMap lacks the link (two demo businesses
  had sites), so that bucket is labelled unverified;
- 29 of 32 "connection failures" were domains that no longer exist, which is
  only trustworthy once DNS is shown to work on this machine (control lookup).
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import html as htmlmod
import re
import socket
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / ".scratch" / "local-site-scan"

MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")

# German trade key -> (label, OpenStreetMap tags). Order decides ties.
TRADES: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "maler": ("Maler", [("craft", "painter")]),
    "physio": ("Physiotherapie", [("healthcare", "physiotherapist"), ("amenity", "physiotherapist")]),
    "zahnarzt": ("Zahnarzt", [("amenity", "dentist"), ("healthcare", "dentist")]),
    "arzt": ("Arztpraxis", [("amenity", "doctors")]),
    "anwalt": ("Rechtsanwalt", [("office", "lawyer")]),
    "steinmetz": ("Steinmetz", [("craft", "stonemason")]),
    "kosmetik": ("Kosmetik", [("shop", "beauty")]),
    "friseur": ("Friseur", [("shop", "hairdresser")]),
    "steuerberater": ("Steuerberater", [("office", "tax_advisor")]),
    "architekt": ("Architekt", [("office", "architect")]),
    "schreiner": ("Schreiner", [("craft", "carpenter"), ("craft", "joiner")]),
    "elektriker": ("Elektriker", [("craft", "electrician")]),
    "sanitaer": ("Sanitär/Heizung", [("craft", "plumber"), ("craft", "hvac")]),
    "dachdecker": ("Dachdecker", [("craft", "roofer")]),
}
BOOKING_TRADES = {"physio", "zahnarzt", "arzt", "kosmetik", "friseur"}

# The tools German practices and salons book through. Sellbird knew only US
# ones and flagged 10-21 of 50 sampled Karlsruhe sites "no online booking" wrongly.
BOOKING_VENDORS = {
    "Doctolib": r"doctolib\.", "Dr. Flex": r"dr-flex|drflex", "Jameda": r"jameda\.de",
    "Doctena": r"doctena", "Samedi": r"samedi\.de", "Treatwell": r"treatwell\.",
    "Planity": r"planity\.", "Shore": r"shore\.com", "Salonized": r"salonized",
    "Studiobookr": r"studiobookr", "Timify": r"timify", "Terminland": r"terminland",
    "eTermin": r"etermin\.net", "SimplyBook": r"simplybook", "Fresha": r"fresha\.com",
    "Booksy": r"booksy\.", "Phorest": r"phorest", "Calendly": r"calendly\.com",
}
BOOKING_TEXT = r"online[- ]?termin|termin[- ]?(?:online[- ]?)?(?:buchen|vereinbaren)|jetzt[- ]buchen"

PARKED = ("sedo.com", "parkingcrew", "bodis.com", "domain kaufen", "domain is for sale",
          "this domain may be for sale", "diese domain steht zum verkauf", "dan.com/buy")
PLACEHOLDER = ("hier entsteht", "under construction", "im aufbau", "coming soon",
               "welcome to nginx", "it works!", "default web site page", "baustelle")
SPAM = ("viagra", "cialis", "casino", "slot gacor", "togel", "replica watches", "porn")
PLATFORMS = {
    "Wix": r"wixstatic\.com|wix\.com", "Jimdo": r"jimdo", "Squarespace": r"squarespace",
    "IONOS MyWebsite": r"mywebsite-editor|ionos", "WordPress": r"wp-content|wordpress",
    "TYPO3": r"typo3", "Joomla": r"joomla", "Webflow": r"webflow",
}

DEAD = {"domain_gone", "parked", "placeholder", "not_found", "server_error",
        "no_answer", "ssl_broken", "spam_injected", "http_error"}
WEAK_AT = 3


class OverpassUnavailable(RuntimeError):
    """No mirror returned a complete answer. Never treated as 'no businesses'."""


# ---------------------------------------------------------------- OpenStreetMap

def build_query(trades: list[str], area: str | None = None, admin_level: str = "6|8",
                around: tuple[float, float, float] | None = None, timeout: int = 180) -> str:
    if area:
        if '"' in area or "\\" in area:
            raise ValueError("area name must not contain quotes or backslashes")
        head = (f'area["name"="{area}"]["boundary"="administrative"]'
                f'["admin_level"~"^({admin_level})$"]->.a;')
        scope = "(area.a)"
    elif around:
        lat, lng, km = around
        head, scope = "", f"(around:{int(km * 1000)},{lat},{lng})"
    else:
        raise ValueError("give --area or --around")
    parts = "".join(f'nwr["{k}"="{v}"]{scope};' for t in trades for k, v in TRADES[t][1])
    return f"[out:json][timeout:{timeout}];{head}({parts});out center tags;"


async def fetch_overpass(query: str, client: httpx.AsyncClient, mirrors=MIRRORS,
                         rounds: int = 4, pause: float = 30, sleep=asyncio.sleep):
    """Return (elements, mirror). Raise OverpassUnavailable rather than return a partial list."""
    errors: list[str] = []
    for rnd in range(rounds):
        for url in mirrors:
            try:
                r = await client.post(url, data={"data": query}, timeout=240)
            except httpx.HTTPError as e:
                errors.append(f"{urlparse(url).hostname}: {type(e).__name__}")
                continue
            if r.status_code != 200:
                errors.append(f"{urlparse(url).hostname}: HTTP {r.status_code}")
                continue
            try:
                data = r.json()
            except ValueError:
                errors.append(f"{urlparse(url).hostname}: not JSON")
                continue
            remark = str(data.get("remark") or "")
            if "error" in remark.lower():
                # Overpass answers 200 with a remark and a PARTIAL element list on timeout.
                errors.append(f"{urlparse(url).hostname}: partial answer ({remark[:60]})")
                continue
            return data.get("elements", []), url
        if rnd < rounds - 1:
            await sleep(pause * (rnd + 1))
    raise OverpassUnavailable("; ".join(errors[-6:]) or "no mirror answered")


def classify(tags: dict, trades: list[str]) -> str:
    for t in trades:
        if any(tags.get(k) == v for k, v in TRADES[t][1]):
            return t
    return ""


def businesses(elements: list[dict], trades: list[str]) -> list[dict]:
    seen, out = set(), []
    for e in elements:
        tags = e.get("tags") or {}
        name, trade = (tags.get("name") or "").strip(), classify(tags, trades)
        if not name or not trade:
            continue
        key = (name.lower(), tags.get("addr:street", ""), tags.get("addr:housenumber", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "name": name, "trade": trade,
            "street": " ".join(x for x in (tags.get("addr:street", ""), tags.get("addr:housenumber", "")) if x),
            "postcode": tags.get("addr:postcode", ""), "city": tags.get("addr:city", ""),
            "website": (tags.get("website") or tags.get("contact:website") or tags.get("url") or "").strip(),
            "osm": f"{e.get('type', '')}/{e.get('id', '')}",
        })
    return out


# ---------------------------------------------------------------- page reading

def html_to_text(page: str) -> str:
    page = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1\s*>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(?:p|div|li|td|tr|h[1-6]|section|address|span)>", "\n", page)
    text = htmlmod.unescape(re.sub(r"<[^>]+>", " ", page))
    lines = (re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in text.splitlines())
    return "\n".join(ln for ln in lines if ln)


def booking_tools(page: str) -> list[str]:
    low = page.lower()
    found = [v for v, pat in BOOKING_VENDORS.items() if re.search(pat, low)]
    if not found and re.search(BOOKING_TEXT, low):
        found.append("Termin-Link")
    return found


def copyright_year(page: str) -> int | None:
    years = [max(int(a), int(b or 0)) for a, b in re.findall(
        r"(?:©|&copy;|\(c\)|copyright)[^0-9<]{0,40}?((?:19|20)\d{2})(?:\s*[-–/]\s*((?:19|20)\d{2}))?",
        page, re.I)]
    return max(years) if years else None


def platform(page: str) -> str:
    low = page.lower()
    gen = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', low)
    hay = (gen.group(1) if gen else "") + " " + low[:200_000]
    return next((p for p, pat in PLATFORMS.items() if re.search(pat, hay)), "")


def impressum_link(page: str, base: str) -> str:
    for href, label in re.findall(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page):
        if "impressum" in href.lower() or "impressum" in label.lower():
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            return urljoin(base, href)
    return ""


_LABEL = re.compile(r"\b(inhaber(?:in)?|inh\.|praxisinhaber(?:in)?|geschäftsführer(?:in)?|"
                    r"geschäftsführung|vertreten durch|verantwortlich[^:\n]{0,70}:)", re.I)
_SKIP = {"herr", "frau", "den", "die", "der", "durch", "geschäftsführer", "geschäftsführerin",
         "rechtsanwalt", "rechtsanwältin", "zahnarzt", "zahnärztin", "steuerberater",
         "steuerberaterin", "architekt", "architektin", "inhaber", "inhaberin", "ist", ":"}
_NAMEWORD = re.compile(r"[A-ZÄÖÜ][a-zäöüßéèáóçñ]+(?:-[A-ZÄÖÜ][a-zäöüßéèáóçñ]+)?")
_PROFESSION = re.compile(r"(meister|arzt|ärztin|anwalt|anwältin|berater|architekt|therapeut|"
                         r"gmbh|praxis|friseur|kosmetik|partner|kanzlei)", re.I)
_STOP = re.compile(r"(straße|strasse|str\.|platz|allee|weg\b|gmbh|karlsruhe|telefon|google|"
                   r"maps|domain|impressum|deutschland|datenschutz|registergericht|angaben|"
                   r"gemäß|kontakt|anschrift|postfach)", re.I)


def _clean_name(raw: str) -> str:
    raw = re.split(r"[,;|(/]| und | & |\s{3,}", raw.strip())[0]
    out: list[str] = []
    names = 0
    for tok in raw.split():
        bare = tok.strip(":,")
        if not out and bare.lower() in _SKIP:
            continue
        if names and bare.endswith(".") and _NAMEWORD.fullmatch(bare[:-1]) and len(bare) > 4:
            out.append(bare[:-1])  # surname that ends the sentence
            names += 1
            break
        if (bare.endswith(".") and len(bare) <= 10) or bare.startswith("Dipl"):
            if names:
                break
            out.append(bare)
        elif _NAMEWORD.fullmatch(bare) and not _PROFESSION.search(bare):
            out.append(bare)
            names += 1
        elif bare in ("von", "van", "de", "zu") and names:
            out.append(bare)
        else:
            break
    while out and out[-1] in ("von", "van", "de", "zu"):
        out.pop()
    name = " ".join(out)
    if names < 2 or _STOP.search(name):
        return ""
    return name


def owner_from_impressum(text: str) -> str:
    """The person the Impressum names as owner or managing director, or ''."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _LABEL.search(line)
        if not m:
            continue
        rest = line[m.end():].strip(" :-–\t")
        for cand in ([rest] if rest else []) + lines[i + 1:i + 2]:
            name = _clean_name(cand)
            if name:
                return name
    return ""


def read_home(page: str, final_url: str, trade: str, this_year: int) -> dict:
    """Judge a homepage that loaded. Pure: no network."""
    low, text = page.lower(), html_to_text(page)
    res = {"status": "ok", "reasons": [], "score": 0, "platform": platform(page),
           "booking": "", "copyright_year": "", "impressum": impressum_link(page, final_url)}
    if any(p in low for p in PARKED):
        res.update(status="parked", reasons=["domain is parked or for sale"])
        return res
    if len(text) < 600 and any(p in low for p in PLACEHOLDER):
        res.update(status="placeholder", reasons=["placeholder page, no real site"])
        return res
    if len({s for s in SPAM if s in low}) >= 2:
        res.update(status="spam_injected", reasons=["spam content on the homepage (possibly hacked)"])
        return res
    if not re.search(r'<meta[^>]+name=["\']viewport["\']', low):
        res["score"] += 2
        res["reasons"].append("not mobile-ready (no viewport)")
    if not final_url.startswith("https://"):
        res["score"] += 1
        res["reasons"].append("no https")
    year = copyright_year(page)
    if year:
        res["copyright_year"] = str(year)
        if year <= this_year - 3:
            res["score"] += 1
            res["reasons"].append(f"footer says ©{year}")
    if "application/ld+json" not in low:
        res["score"] += 1
        res["reasons"].append("no structured data for AI search")
    tools = booking_tools(page)
    res["booking"] = ", ".join(tools)
    if trade in BOOKING_TRADES and not tools:
        res["score"] += 1
        res["reasons"].append("no online booking")
    return res


# ---------------------------------------------------------------- site check

def _is_ssl(err: Exception) -> bool:
    s = str(err).lower()
    return "ssl" in s or "certificate" in s


async def dns_resolves(host: str, attempts: int = 2) -> bool:
    loop = asyncio.get_running_loop()
    for i in range(attempts):
        try:
            await loop.getaddrinfo(host, 443)
            return True
        except socket.gaierror:
            if i < attempts - 1:
                await asyncio.sleep(1.5)
    return False


async def check_site(biz: dict, client, insecure, resolver, this_year: int, timeout: float = 20) -> dict:
    url = biz["website"]
    url = url if re.match(r"(?i)https?://", url) else "http://" + url
    host = urlparse(url).hostname or ""
    base = {"status": "", "reasons": [], "score": 0, "final_url": "", "platform": "",
            "booking": "", "copyright_year": "", "owner": ""}
    if not host:
        return {**base, "status": "http_error", "reasons": ["website tag is not a URL"]}
    if not await resolver(host):
        return {**base, "status": "domain_gone", "reasons": ["domain no longer exists (no DNS record)"]}
    try:
        r = await client.get(url, timeout=timeout)
    except httpx.ConnectError as e:
        if _is_ssl(e):
            try:
                await insecure.get(url, timeout=timeout)
                return {**base, "status": "ssl_broken",
                        "reasons": ["browsers show a security warning (certificate invalid)"]}
            except httpx.HTTPError:
                pass
        return {**base, "status": "no_answer", "reasons": ["server does not answer"]}
    except httpx.TimeoutException:
        return {**base, "status": "no_answer", "reasons": [f"no answer within {int(timeout)} s"]}
    except httpx.HTTPError as e:
        return {**base, "status": "no_answer", "reasons": [f"fetch failed ({type(e).__name__})"]}
    final = str(r.url)
    if r.status_code in (401, 403, 429):
        return {**base, "status": "blocked", "final_url": final,
                "reasons": [f"HTTP {r.status_code}: refused our check, state unknown"]}
    if r.status_code in (404, 410):
        return {**base, "status": "not_found", "final_url": final, "reasons": [f"homepage gives HTTP {r.status_code}"]}
    if r.status_code >= 500:
        return {**base, "status": "server_error", "final_url": final, "reasons": [f"homepage gives HTTP {r.status_code}"]}
    if r.status_code >= 400:
        return {**base, "status": "http_error", "final_url": final, "reasons": [f"homepage gives HTTP {r.status_code}"]}
    home = read_home(r.text, final, biz["trade"], this_year)
    out = {**base, **{k: v for k, v in home.items() if k != "impressum"}, "final_url": final}
    # Only a real site's Impressum names the owner; a parked page's names the parking company.
    if home["status"] == "ok" and home["impressum"]:
        try:
            imp = await client.get(home["impressum"])
            if imp.status_code == 200:
                out["owner"] = owner_from_impressum(html_to_text(imp.text))
        except httpx.HTTPError:
            pass
    return out


# ---------------------------------------------------------------- orchestration

def priority(row: dict) -> int:
    if row["status"] in DEAD:
        return 1
    if row["status"] == "ok" and row["score"] >= WEAK_AT:
        return 2
    if row["status"] == "no_website_listed":
        return 3
    if row["status"] == "ok":
        return 4
    if row["status"] == "blocked":
        return 5
    return 6


PRIORITY_LABEL = {1: "1 dead or broken", 2: "2 weak site", 3: "3 no website listed (unverified)",
                  4: "4 site fine", 5: "5 unknown (blocked our check)", 6: "6 not checked (--limit)"}


async def scan(query: str, trades: list[str], *, limit: int = 0, concurrency: int = 8,
               transport=None, insecure_transport=None, resolver=dns_resolves,
               sleep=asyncio.sleep, this_year: int | None = None, overpass_pause: float = 30):
    this_year = this_year or date.today().year
    if not await resolver("www.openstreetmap.org"):
        raise OverpassUnavailable("DNS does not resolve a known domain here; every site would read as gone")
    transport = transport or httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=1)
    insecure_transport = insecure_transport or httpx.AsyncHTTPTransport(
        local_address="0.0.0.0", retries=1, verify=False)
    common = {"follow_redirects": True, "timeout": 20, "headers": {"User-Agent": UA}}
    async with httpx.AsyncClient(transport=transport, **common) as client, \
            httpx.AsyncClient(transport=insecure_transport, **common) as insecure:
        elements, mirror = await fetch_overpass(query, client, sleep=sleep, pause=overpass_pause)
        found = businesses(elements, trades)
        if not found:
            raise OverpassUnavailable("the map returned zero businesses: check the area name and admin level")
        sem = asyncio.Semaphore(concurrency)
        checked = 0

        async def one(biz):
            nonlocal checked
            if not biz["website"]:
                return {**biz, "status": "no_website_listed", "score": 0, "final_url": "", "platform": "",
                        "booking": "", "copyright_year": "", "owner": "",
                        "reasons": ["OpenStreetMap lists no website (check by hand)"]}
            if limit and checked >= limit:
                return {**biz, "status": "not_checked", "score": 0, "final_url": "", "platform": "",
                        "booking": "", "copyright_year": "", "owner": "", "reasons": ["over --limit"]}
            checked += 1
            async with sem:
                return {**biz, **await check_site(biz, client, insecure, resolver, this_year)}

        rows = await asyncio.gather(*(one(b) for b in found))
        # A busy server times out under parallel load; give every "no answer" one
        # slow, sequential retry before calling it dead (live run 2026-11-19: 1 of 5 recovered).
        for i, biz in enumerate(found):
            if rows[i]["status"] == "no_answer":
                rows[i] = {**biz, **await check_site(biz, client, insecure, resolver, this_year, timeout=45)}
    for row in rows:
        row["priority"] = PRIORITY_LABEL[priority(row)]
    rows.sort(key=lambda r: (r["priority"], -r["score"], r["trade"], r["name"].lower()))
    return rows, mirror


COLUMNS = ["priority", "status", "score", "reasons", "trade", "name", "owner", "street", "postcode",
           "city", "website", "final_url", "platform", "booking", "copyright_year", "osm"]


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "reasons": "; ".join(r["reasons"]), "trade": TRADES[r["trade"]][0]})


def summary(rows: list[dict], mirror: str) -> str:
    from collections import Counter
    by_p = Counter(r["priority"] for r in rows)
    by_s = Counter(r["status"] for r in rows)
    lines = [f"{len(rows)} businesses from {urlparse(mirror).hostname}"]
    lines += [f"  {by_p[label]:>4}  {label}" for label in PRIORITY_LABEL.values() if by_p[label]]
    lines.append("  status: " + ", ".join(f"{s} {n}" for s, n in by_s.most_common()))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--area", help="town name as OpenStreetMap spells it, e.g. Karlsruhe")
    where.add_argument("--around", help="lat,lng,km, e.g. 49.0094,8.4044,8")
    ap.add_argument("--admin-level", default="6|8", help="OSM admin level(s) for --area (default 6|8)")
    ap.add_argument("--trades", default="all", help="comma list of: " + ", ".join(TRADES))
    ap.add_argument("--limit", type=int, default=0, help="check at most N websites (0 = all)")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", help="CSV path (default .scratch/local-site-scan/<area>-<date>.csv)")
    a = ap.parse_args(argv)

    trades = list(TRADES) if a.trades == "all" else [t.strip() for t in a.trades.split(",") if t.strip()]
    bad = [t for t in trades if t not in TRADES]
    if bad:
        ap.error(f"unknown trade(s): {', '.join(bad)}")
    around = tuple(float(x) for x in a.around.split(",")) if a.around else None
    if around and len(around) != 3:
        ap.error("--around needs lat,lng,km")
    query = build_query(trades, area=a.area, admin_level=a.admin_level, around=around)
    slug = re.sub(r"[^a-z0-9]+", "-", (a.area or a.around).lower()).strip("-")
    out = Path(a.out) if a.out else OUT_DIR / f"{slug}-{date.today():%Y-%m-%d}.csv"
    try:
        rows, mirror = asyncio.run(scan(query, trades, limit=a.limit, concurrency=a.concurrency))
    except OverpassUnavailable as e:
        print(f"STOPPED, no list written: {e}", file=sys.stderr)
        return 2
    write_csv(rows, out)
    sys.stdout.reconfigure(encoding="utf-8")
    print(summary(rows, mirror))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
