# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "markdown>=3.7",
#   "pyyaml>=6.0",
# ]
# ///
"""Build static HTML doc site for Wärme Wimmer.

Output: platform/public/docs/warme-wimmer/
- index.html   dashboard with live Make REST data + storage from status.yaml
- {slug}.html  one per source markdown page (with status card up top per scenario)

Live data sources:
- Make REST API (org operations, scenario states, recent executions)
- context/maintenance/status.yaml (storage, anything not API-accessible)

The script auto-loads .env so MAKE_API_TOKEN_WARME_WIMMER is available.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import markdown as md_lib
import yaml

REPO = Path.cwd()
SRC_TOOL = REPO / "tools/notion-restructure-v18.py"
OUT_DIR = REPO / "platform/public/docs/warme-wimmer"
BASE_PATH = "/docs/warme-wimmer/"
ACCESS_CODE = "wimmer2026"
LS_PREFIX = "wimmer-docs"
STATUS_YAML = REPO / "workspace/clients/warme-wimmer/context/maintenance/status.yaml"

MAKE_BASE = "https://eu1.make.com/api/v2"
MAKE_ORG_ID = 7209133
MAKE_TEAM_ID = 1421610

# (scenario number, display W2 label, Make scenario ID, German short name)
W2_SCENARIOS = [
    (1,  "W2-01", 5423770, "Aufgabe erledigt"),
    (2,  "W2-02", 5316656, "Aufgaben nach Statuswechsel"),
    (3,  "W2-03", 5423798, "Dokument erstellt"),
    (4,  "W2-04", 5316629, "Outlook nach Hero"),
    (5,  "W2-05", 5316659, "Projekt erstellt"),
    (6,  "W2-06", 5423810, "Projekterinnerung 1 Tag nach Termin"),
    (7,  "W2-07", 5316633, "Rechnungen bezahlt"),
    (8,  "W2-08", 5423817, "Regiebericht fehlt"),
    (9,  "W2-09", 5316635, "Ueberfaellige Aufgaben"),
    (10, "W2-10", 5316617, "Zahlung erhalten"),
]

SCENARIO_BY_NUM = {n: (label, sid, name) for n, label, sid, name in W2_SCENARIOS}


def _load_env():
    env_path = REPO / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


_load_env()
MAKE_TOKEN = os.environ.get("MAKE_API_TOKEN_WARME_WIMMER", "")


def _import_v18():
    spec = importlib.util.spec_from_file_location("v18", SRC_TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ============ Live data fetchers ============


def _fetch_json(url: str, headers: dict, timeout: int = 15):
    # Make REST blocks the default Python urllib User-Agent. Set explicit one.
    full_headers = {"User-Agent": "warme-wimmer-doc-site/1.0", "Accept": "application/json", **headers}
    req = urllib.request.Request(url, headers=full_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _format_schedule(scheduling: dict | None, is_active: bool) -> str:
    if not is_active:
        return "deaktiviert"
    if not scheduling:
        return "—"
    t = scheduling.get("type")
    if t == "immediately":
        return "event-getrieben (Webhook)"
    if t != "indefinitely":
        return t or "—"
    interval_s = scheduling.get("interval", 0)
    restrict = scheduling.get("restrict") or []
    days_str = "Mo–So"
    time_str = "ganztägig"
    if restrict:
        r = restrict[0]
        days = r.get("days") or []
        if days == [1, 2, 3, 4, 5]:
            days_str = "Mo–Fr"
        elif days == [6, 7]:
            days_str = "Sa–So"
        elif days and len(days) == 7:
            days_str = "Mo–So"
        time_window = r.get("time") or []
        if len(time_window) == 2:
            time_str = f"{time_window[0]}–{time_window[1]}"
    if interval_s and interval_s % 86400 == 0:
        intv = "täglich"
    elif interval_s and interval_s % 3600 == 0:
        intv = f"alle {interval_s // 3600} h"
    elif interval_s and interval_s % 60 == 0:
        intv = f"alle {interval_s // 60} min"
    else:
        intv = f"alle {interval_s} s"
    return f"{intv}, {days_str} {time_str}"


def _humanize_dt(iso_str: str | None) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        return iso_str[:19] if iso_str else "—"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def fetch_make_status() -> dict:
    """Fetch live status from Make REST API.

    Returns dict with org info + per-scenario state. If MAKE_TOKEN is missing
    or any call fails, returns a structure with `unavailable` set so the
    build can still produce a site.
    """
    if not MAKE_TOKEN:
        print("WARN: MAKE_API_TOKEN_WARME_WIMMER not set — building without live data", file=sys.stderr)
        return {"unavailable": True, "reason": "no_token"}
    headers = {"Authorization": f"Token {MAKE_TOKEN}"}
    try:
        org_raw = _fetch_json(f"{MAKE_BASE}/organizations/{MAKE_ORG_ID}", headers).get("organization", {})
    except Exception as e:
        print(f"WARN: Make org fetch failed: {e}", file=sys.stderr)
        return {"unavailable": True, "reason": str(e)}

    license_info = org_raw.get("license", {})
    ops_used = int(org_raw.get("operations", 0))
    ops_unused = int(org_raw.get("unusedOperations", 0))
    # Current cycle limit = used + unused (this includes any auto-buy blocks added).
    # license.operations is the base plan only; not the live limit.
    cycle_limit = ops_used + ops_unused if (ops_used + ops_unused) > 0 else int(license_info.get("operations", 0))
    base_plan_limit = int(license_info.get("operations", 0))
    extra_bought = max(0, cycle_limit - base_plan_limit)
    org = {
        "name": org_raw.get("name"),
        "plan": org_raw.get("serviceName") or org_raw.get("productName"),
        "ops_used": ops_used,
        "ops_limit": cycle_limit,
        "ops_unused": ops_unused,
        "base_plan_limit": base_plan_limit,
        "extra_bought": extra_bought,
        "auto_buy": bool(org_raw.get("autoPurchasingActivated")),
        "active_scenarios": org_raw.get("activeScenarios"),
        "last_reset": org_raw.get("lastReset"),
        "next_reset": org_raw.get("nextReset"),
    }
    if cycle_limit:
        org["ops_pct"] = round(100 * ops_used / cycle_limit, 1)
    else:
        org["ops_pct"] = 0

    scenarios = {}
    for n, label, scenario_id, name in W2_SCENARIOS:
        try:
            scn = _fetch_json(f"{MAKE_BASE}/scenarios/{scenario_id}", headers).get("scenario", {})
        except Exception as e:
            print(f"  WARN: scenario {scenario_id} fetch failed: {e}", file=sys.stderr)
            scn = {}
        try:
            logs_resp = _fetch_json(f"{MAKE_BASE}/scenarios/{scenario_id}/logs?pg%5Blimit%5D=50", headers)
            logs = logs_resp.get("scenarioLogs", [])
        except Exception as e:
            print(f"  WARN: scenario {scenario_id} logs fetch failed: {e}", file=sys.stderr)
            logs = []

        runs = [l for l in logs if l.get("type") in ("auto", "manual") and l.get("status") is not None]
        last_ok = next((l for l in runs if l.get("status") == 1), None)
        ok_count = sum(1 for l in runs if l.get("status") == 1)
        warn_count = sum(1 for l in runs if l.get("status") == 5)
        err_count = sum(1 for l in runs if l.get("status") in (2, 3, 4))

        is_active = bool(scn.get("isActive"))
        is_paused = bool(scn.get("isPaused"))
        if not is_active:
            health = "deaktiviert"
        elif is_paused:
            health = "pausiert"
        elif err_count:
            health = "Fehler"
        elif warn_count:
            health = "Warnung"
        elif ok_count:
            health = "läuft"
        else:
            health = "kein Lauf"

        scenarios[n] = {
            "label": label,
            "name": name,
            "id": scenario_id,
            "is_active": is_active,
            "is_paused": is_paused,
            "schedule": _format_schedule(scn.get("scheduling"), is_active),
            "last_run": last_ok.get("timestamp") if last_ok else None,
            "ok_count": ok_count,
            "warn_count": warn_count,
            "err_count": err_count,
            "next_exec": scn.get("nextExec"),
            "health": health,
        }

    return {
        "org": org,
        "scenarios": scenarios,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def read_storage_status() -> dict:
    if not STATUS_YAML.is_file():
        return {}
    return yaml.safe_load(STATUS_YAML.read_text(encoding="utf-8")) or {}


# ============ Body sanitization ============

EMOJI_STRIP = {
    "✅": "OK",
    "❌": "—",
    "🟢": "low",
    "🟡": "mid",
    "🟠": "high",
    "🔴": "kritisch",
    "🚀": "",
    "📌": "",
    "💡": "",
    "📝": "",
    "🔧": "",
    "⚠️": "Achtung:",
    "⚠": "Achtung:",
}


def strip_emojis(text: str) -> str:
    for emoji, replacement in EMOJI_STRIP.items():
        text = text.replace(emoji, replacement)
    return text


def md_to_html_body(md_text: str) -> str:
    """Convert markdown to HTML, preserving mermaid blocks for client-side rendering."""
    md_text = strip_emojis(md_text)
    placeholders: dict[str, str] = {}

    def stash_mermaid(match: re.Match) -> str:
        key = f"@@MERMAID_{len(placeholders)}@@"
        placeholders[key] = match.group(1)
        return key

    md_text = re.sub(r"```mermaid\n(.*?)```", stash_mermaid, md_text, flags=re.DOTALL)

    html = md_lib.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "md_in_html", "attr_list"],
    )

    for key, code in placeholders.items():
        html = html.replace(key, f'<pre class="mermaid">{code.strip()}</pre>')
    for key, code in placeholders.items():
        html = html.replace(f"<p>{key}</p>", f'<pre class="mermaid">{code.strip()}</pre>')

    html = re.sub(r'<a href="([^"]+)\.md(#[^"]*)?">', _rewrite_link_to_html, html)
    return html


def _rewrite_link_to_html(m: re.Match) -> str:
    base = m.group(1)
    fragment = m.group(2) or ""
    slug = page_slug(base + ".md")
    return f'<a href="{BASE_PATH}{slug}.html{fragment}">'


def page_slug(filename: str) -> str:
    return filename.removesuffix(".md").lower()


def page_title(filename: str, content: str) -> str:
    m = re.search(r"^# (.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return filename.removesuffix(".md")


# Page metadata: drives sidebar title + group + drop-list.
# Filename keys are the original-case names from notion-restructure-v18.build_pages().
PAGE_META = {
    "S-00-flowcharts-overview.md":    {"title": "Flowcharts-Übersicht",     "group": "automatisierungen", "order": 0},
    "S-01-aufgabe-erledigt.md":            {"title": "W2-01: Aufgabe erledigt",            "group": "automatisierungen", "order": 1},
    "S-02-aufgaben-nach-statuswechsel.md": {"title": "W2-02: Aufgaben nach Statuswechsel", "group": "automatisierungen", "order": 2},
    "S-03-dokument-erstellt.md":           {"title": "W2-03: Dokument erstellt",           "group": "automatisierungen", "order": 3},
    "S-04-outlook-hero.md":                {"title": "W2-04: Outlook nach Hero",           "group": "automatisierungen", "order": 4},
    "S-05-projekt-erstellt.md":            {"title": "W2-05: Projekt erstellt",            "group": "automatisierungen", "order": 5},
    "S-06-projekterinnerung.md":           {"title": "W2-06: Projekterinnerung",           "group": "automatisierungen", "order": 6},
    "S-07-rechnungen-bezahlt.md":          {"title": "W2-07: Rechnungen bezahlt",          "group": "automatisierungen", "order": 7},
    "S-08-regiebericht-fehlt.md":          {"title": "W2-08: Regiebericht fehlt",          "group": "automatisierungen", "order": 8},
    "S-09-ueberfaellige-aufgaben.md":      {"title": "W2-09: Überfällige Aufgaben",        "group": "automatisierungen", "order": 9},
    "S-10-zahlung-erhalten.md":            {"title": "W2-10: Zahlung erhalten",            "group": "automatisierungen", "order": 10},
    "M-meetings.md":                  {"title": "Meetings",                  "group": "aktivitaet", "order": 1},
    "R-team-updates.md":              {"title": "Wartungs-Updates",          "group": "aktivitaet", "order": 2},
    "R-00-uebersicht.md":             {"title": "Lastenheft (Hintergrund)",  "group": "referenz", "order": 1},
    "R-hero-ids-und-connections.md":  {"title": "Hero-IDs und Connections",  "group": "referenz", "order": 2},
    "R-kosten-und-subscription.md":   {"title": "Kosten und Subscription",   "group": "referenz", "order": 3},
    "R-w2-04-rewrite-design-ist.md":  {"title": "W2-04: Rewrite-Design (IST-Analyse)",   "group": "referenz", "order": 4},
    "R-w2-04-rewrite-design-mockup.md": {"title": "W2-04: Rewrite-Design (Mockup)",      "group": "referenz", "order": 5},
    # Pages dropped from build (drop=True keeps them in source but excludes from output):
    "0-Start-Hier.md":                {"drop": True},
    "R-hero-api-smoketest.md":        {"drop": True},
}

GROUPS = [
    ("automatisierungen", "Automatisierungen"),
    ("referenz",          "Referenz"),
    ("aktivitaet",        "Aktivität"),
]


def display_title(filename: str, content: str) -> str:
    """Return the display title for a page — uses PAGE_META override if set,
    falls back to the H1 of the markdown."""
    meta = PAGE_META.get(filename, {})
    if meta.get("title"):
        return meta["title"]
    return page_title(filename, content)


def page_group(filename: str) -> str | None:
    return PAGE_META.get(filename, {}).get("group")


def page_order(filename: str) -> int:
    return PAGE_META.get(filename, {}).get("order", 999)


def is_dropped(filename: str) -> bool:
    return PAGE_META.get(filename, {}).get("drop") is True


CSS = """
:root{
  --header-height:72px;--sidebar-width:240px;
  --bg:#f8fafc;--surface:#ffffff;--surface2:#f1f5f9;--border:#e2e8f0;
  --text:#0f172a;--text2:#475569;--text3:#94a3b8;
  --blue:#2563eb;--blue-light:#dbeafe;--blue-dark:#1e40af;
  --green:#16a34a;--green-light:#dcfce7;
  --amber:#d97706;--amber-light:#fef3c7;
  --purple:#7c3aed;--purple-light:#ede9fe;
  --red:#dc2626;--red-light:#fee2e2;
  --shadow:0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.05);
  --nav-bg:#ffffff;
}
[data-theme="dark"]{
  --bg:#0f172a;--surface:#1e293b;--surface2:#0f172a;--border:#334155;
  --text:#f1f5f9;--text2:#94a3b8;--text3:#475569;
  --blue:#3b82f6;--blue-light:#1e3a5f;--blue-dark:#93c5fd;
  --green:#22c55e;--green-light:#14532d;
  --amber:#f59e0b;--amber-light:#451a03;
  --purple:#a78bfa;--purple-light:#2e1065;
  --red:#f87171;--red-light:#450a0a;
  --shadow:0 1px 3px rgba(0,0,0,.3);
  --nav-bg:#1e293b;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);font-size:15px;line-height:1.6;min-height:100vh;transition:background .2s,color .2s;padding-top:var(--header-height)}
.sidebar{position:fixed;top:var(--header-height);left:0;width:var(--sidebar-width);height:calc(100vh - var(--header-height));background:var(--surface);border-right:1px solid var(--border);z-index:50;overflow-y:auto;transition:transform .25s ease}
.sidebar-group{padding:8px 0;border-bottom:1px solid var(--border)}
.sidebar-group:last-child{border-bottom:none}
.sidebar-group-label{padding:8px 20px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--text3)}
.sidebar-home{display:block;padding:10px 20px;font-size:13px;font-weight:600;color:var(--text);text-decoration:none;border-left:3px solid transparent;transition:background .15s}
.sidebar-home:hover{background:var(--surface2)}
.sidebar-home.active{background:var(--blue-light);color:var(--blue-dark);border-left-color:var(--blue)}
.sidebar-nav{list-style:none}
.sidebar-nav a{display:flex;align-items:center;gap:8px;padding:8px 20px;font-size:13px;font-weight:500;color:var(--text2);text-decoration:none;border-left:3px solid transparent;transition:background .15s,color .15s,border-color .15s}
.sidebar-nav a:hover{background:var(--surface2);color:var(--text)}
.sidebar-nav a.active{background:var(--blue-light);color:var(--blue-dark);border-left-color:var(--blue);font-weight:700}
.sidebar-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:40}
.sidebar-backdrop.active{display:block}
.hamburger{display:none;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:6px 10px;cursor:pointer;font-size:18px;color:var(--text2);line-height:1}
.header{background:var(--nav-bg);border-bottom:1px solid var(--border);padding:16px 24px;padding-left:calc(var(--sidebar-width) + 24px);display:flex;align-items:center;justify-content:space-between;position:fixed;top:0;left:0;right:0;z-index:1000;box-shadow:var(--shadow);transition:background .2s}
.header-left{display:flex;align-items:center;gap:16px}
.header-logo{display:flex;align-items:center;gap:6px;font-size:18px;letter-spacing:-0.025em}
.header-logo .logo-text{font-weight:700;color:var(--text)}
.header-logo .logo-accent{font-weight:700;color:var(--blue)}
.header-title h1{font-size:16px;font-weight:700;color:var(--text)}
.header-title p{font-size:12px;color:var(--text2);margin-top:1px}
.header-right{display:flex;align-items:center;gap:12px}
.theme-btn{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:6px 12px;cursor:pointer;font-size:13px;color:var(--text2);display:flex;align-items:center;gap:6px;transition:background .15s}
.theme-btn:hover{background:var(--border)}
.badge{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:600}
.badge-green{background:var(--green-light);color:var(--green)}
.badge-dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.page-layout{margin-left:var(--sidebar-width)}
.main{max-width:1100px;margin:0 auto;padding:32px 32px 80px}
.main h1{font-size:30px;font-weight:800;letter-spacing:-0.02em;margin-bottom:8px;color:var(--text)}
.main h2{font-size:22px;font-weight:700;margin:32px 0 12px;color:var(--text);padding-bottom:6px;border-bottom:1px solid var(--border)}
.main h3{font-size:17px;font-weight:700;margin:24px 0 8px;color:var(--text)}
.main h4{font-size:15px;font-weight:700;margin:18px 0 6px;color:var(--text)}
.main p{margin:8px 0 12px;color:var(--text2)}
.main ul,.main ol{margin:8px 0 12px;padding-left:24px;color:var(--text2)}
.main li{margin:3px 0}
.main strong{color:var(--text)}
.main a{color:var(--blue);text-decoration:none}
.main a:hover{text-decoration:underline}
.main blockquote{border-left:4px solid var(--blue);background:var(--surface2);padding:12px 16px;margin:12px 0;border-radius:0 8px 8px 0;color:var(--text2);font-style:normal}
.main blockquote p{margin:0}
.main blockquote em{font-style:normal;color:var(--text2)}
.main code{background:var(--surface2);padding:1px 6px;border-radius:4px;font-size:13px;font-family:'Menlo','Monaco','Consolas',monospace;color:var(--purple)}
.main pre{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px 16px;margin:12px 0;overflow-x:auto;font-size:13px;line-height:1.5}
.main pre code{background:none;padding:0;color:var(--text2)}
.main pre.mermaid{background:var(--surface);border:1px solid var(--border);text-align:center;padding:20px}
.main table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden}
.main th{background:var(--surface2);padding:10px 14px;text-align:left;font-weight:600;color:var(--text);border-bottom:1px solid var(--border)}
.main td{padding:10px 14px;color:var(--text2);border-bottom:1px solid var(--border)}
.main tr:last-child td{border-bottom:none}
.main hr{border:none;border-top:1px solid var(--border);margin:24px 0}
.main details{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px 16px;margin:12px 0}
.main details summary{cursor:pointer;font-weight:600;color:var(--text);padding:4px 0}
.main details[open] summary{margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.main img{max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:8px 0;display:block}
.status-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 20px;margin:0 0 24px;display:grid;grid-template-columns:1fr;gap:6px}
.status-row{display:flex;justify-content:space-between;gap:12px;font-size:13px;padding:6px 0;border-bottom:1px solid var(--border)}
.status-row:last-child{border-bottom:none}
.status-label{color:var(--text2);font-weight:500}
.status-row span:last-child{color:var(--text);text-align:right}
.badge-amber{background:var(--amber-light);color:var(--amber)}
.badge-red{background:var(--red-light);color:var(--red)}
.badge-grey{background:var(--grey-light);color:var(--grey)}
.dashboard-table{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden}
.dashboard-table th{background:var(--surface2);padding:10px 14px;text-align:left;font-weight:600;color:var(--text);border-bottom:1px solid var(--border);font-size:12px;text-transform:uppercase;letter-spacing:0.05em}
.dashboard-table td{padding:10px 14px;color:var(--text2);border-bottom:1px solid var(--border)}
.dashboard-table tr:last-child td{border-bottom:none}
.dashboard-table tr:hover td{background:var(--surface2)}
.dashboard-table a{color:var(--blue);text-decoration:none}
.dashboard-table a:hover{text-decoration:underline}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:24px 0}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 20px}
.kpi-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;color:var(--text3);margin-bottom:6px}
.kpi-value{font-size:24px;font-weight:700;color:var(--text);letter-spacing:-0.02em}
.kpi-sub{font-size:12px;color:var(--text2);margin-top:4px}
.kpi-progress{height:6px;background:var(--surface2);border-radius:3px;margin-top:10px;overflow:hidden}
.kpi-progress-bar{height:100%;background:var(--blue);transition:width .3s}
.kpi-progress-bar.warn{background:var(--amber)}
.kpi-progress-bar.danger{background:var(--red)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin:24px 0}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;transition:border-color .15s,box-shadow .15s;display:block;color:inherit;text-decoration:none}
.card:hover{border-color:var(--blue);box-shadow:var(--shadow);text-decoration:none}
.card-icon{font-size:24px;margin-bottom:8px;display:block}
.card h3{font-size:16px;font-weight:700;margin:0 0 4px;color:var(--text)}
.card p{font-size:13px;color:var(--text2);margin:0}
.support-cards{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:24px 0}
.support-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;display:block;color:inherit;text-decoration:none;transition:border-color .15s}
.support-card:hover{border-color:var(--blue);text-decoration:none}
.support-card h4{margin:8px 0 4px}
.card-tag{display:inline-block;font-size:11px;font-weight:600;padding:3px 8px;border-radius:12px;background:var(--blue-light);color:var(--blue);margin-top:8px}
.footer{padding:24px 32px;border-top:1px solid var(--border);text-align:center;font-size:12px;color:var(--text3);margin-top:48px}
@media (max-width:768px){
  .sidebar{transform:translateX(-100%)}
  .sidebar.open{transform:translateX(0);box-shadow:var(--shadow)}
  .header{padding-left:16px}
  .page-layout{margin-left:0}
  .hamburger{display:block}
  .header-title h1{font-size:14px}
  .main{padding:20px}
}
"""

AUTH_THEME_JS = f"""
var WIMMER_CODE='{ACCESS_CODE}';
function checkAuth(){{var inp=document.getElementById('auth-input').value;if(inp===WIMMER_CODE){{localStorage.setItem('{LS_PREFIX}-access','granted');var g=document.getElementById('auth-gate');g.style.opacity='0';setTimeout(function(){{g.style.display='none'}},300)}}else{{document.getElementById('auth-error').style.display='block';document.getElementById('auth-input').value='';document.getElementById('auth-input').focus()}}}}
(function(){{if(localStorage.getItem('{LS_PREFIX}-access')==='granted'){{var g=document.getElementById('auth-gate');if(g)g.style.display='none'}}else{{var inp=document.getElementById('auth-input');if(inp)inp.focus()}}}})();
function toggleTheme(){{var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';h.setAttribute('data-theme',n);localStorage.setItem('{LS_PREFIX}-theme',n);var i=document.getElementById('theme-icon');if(i)i.innerHTML=n==='dark'?'&#9788;':'&#9790;'}}
var saved=localStorage.getItem('{LS_PREFIX}-theme');
if(saved){{document.documentElement.setAttribute('data-theme',saved);var i=document.getElementById('theme-icon');if(i&&saved==='dark')i.innerHTML='&#9788;'}}
function toggleSidebar(){{document.getElementById('sidebar').classList.toggle('open');document.getElementById('sidebarBackdrop').classList.toggle('active')}}
function closeSidebar(){{document.getElementById('sidebar').classList.remove('open');document.getElementById('sidebarBackdrop').classList.remove('active')}}
"""


def render_sidebar(pages: dict[str, str], current_slug: str) -> str:
    grouped: dict[str, list[tuple[int, str, str]]] = {g: [] for g, _ in GROUPS}
    for fname in pages:
        if is_dropped(fname):
            continue
        g = page_group(fname)
        if not g:
            continue
        grouped[g].append((page_order(fname), fname, display_title(fname, pages[fname])))

    out = ['<nav class="sidebar" id="sidebar">']
    out.append(
        f'<div class="sidebar-group"><a href="{BASE_PATH}" '
        f'class="sidebar-home{(" active" if current_slug == "index" else "")}">Dashboard</a></div>'
    )
    for group_key, group_label in GROUPS:
        items = sorted(grouped.get(group_key, []))
        if not items:
            continue
        out.append(f'<div class="sidebar-group"><div class="sidebar-group-label">{group_label}</div><ul class="sidebar-nav">')
        for _, fname, title in items:
            slug = page_slug(fname)
            cls = ' class="active"' if slug == current_slug else ""
            out.append(f'<li><a href="{BASE_PATH}{slug}.html"{cls}>{title}</a></li>')
        out.append("</ul></div>")
    out.append("</nav>")
    return "\n".join(out)


def _scenario_num_for_file(filename: str) -> int | None:
    """Map an S-XX-*.md filename to scenario number."""
    m = re.match(r"^S-(\d{1,2})-", filename)
    return int(m.group(1)) if m else None


def _health_class(health: str) -> str:
    return {
        "läuft": "badge-green",
        "Warnung": "badge-amber",
        "Fehler": "badge-red",
        "deaktiviert": "badge-grey",
        "pausiert": "badge-grey",
        "kein Lauf": "badge-grey",
    }.get(health, "badge-grey")


def render_scenario_status_card(scn_data: dict) -> str:
    """Status card injected at the top of each S-XX-*.md page."""
    if not scn_data:
        return ""
    last_run = _humanize_dt(scn_data.get("last_run"))
    next_exec = _humanize_dt(scn_data.get("next_exec"))
    schedule = scn_data.get("schedule", "—")
    health = scn_data.get("health", "—")
    label = scn_data.get("label", "")
    total_runs = scn_data.get("ok_count", 0) + scn_data.get("err_count", 0) + scn_data.get("warn_count", 0)
    success_text = f'{scn_data.get("ok_count", 0)} von letzten {total_runs} OK' if total_runs else "keine Läufe in Make-Log"

    return f"""<div class="status-card">
  <div class="status-row"><span class="status-label">Status</span><span class="badge {_health_class(health)}">{health}</span></div>
  <div class="status-row"><span class="status-label">Letzter Lauf</span><span>{last_run}</span></div>
  <div class="status-row"><span class="status-label">Nächster Lauf</span><span>{next_exec}</span></div>
  <div class="status-row"><span class="status-label">Ausführungsplan</span><span>{schedule}</span></div>
  <div class="status-row"><span class="status-label">Letzte Läufe</span><span>{success_text}</span></div>
</div>"""


def render_page(filename: str, content: str, all_pages: dict[str, str], make_status: dict | None = None) -> str:
    title = display_title(filename, content)
    body_md = re.sub(r"^# .+\n+", "", content, count=1)
    body_html = md_to_html_body(body_md)
    sidebar = render_sidebar(all_pages, page_slug(filename))
    status_card = ""
    scenario_num = _scenario_num_for_file(filename)
    if scenario_num and make_status and not make_status.get("unavailable"):
        scn = (make_status.get("scenarios") or {}).get(scenario_num)
        if scn:
            status_card = render_scenario_status_card(scn)

    return f"""<!DOCTYPE html>
<html lang="de" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,nofollow">
<meta name="googlebot" content="noindex,nofollow">
<title>{title} — Wärme Wimmer Hero-Doku</title>
<style>{CSS}</style>
</head>
<body>
<div class="sidebar-backdrop" id="sidebarBackdrop" onclick="closeSidebar()"></div>
{sidebar}
<header class="header">
  <div class="header-left">
    <button class="hamburger" onclick="toggleSidebar()">☰</button>
    <div class="header-logo"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="28" height="28"><rect width="32" height="32" rx="7" fill="#2563eb"/><rect x="9" y="8" width="4.5" height="16" rx="1.5" fill="white"/><polygon points="18,8 23,16 18,24" fill="white"/></svg><span><span class="logo-text">Unpause</span><span class="logo-accent">AI</span></span></div>
    <div class="header-title"><h1>Wärme Wimmer</h1><p>Hero-Automatisierungen Dokumentation</p></div>
  </div>
  <div class="header-right">
    <span class="badge badge-green"><span class="badge-dot"></span>9 von 10 aktiv</span>
    <button class="theme-btn" onclick="toggleTheme()"><span id="theme-icon">&#9790;</span> Theme</button>
  </div>
</header>
<div class="page-layout">
  <main class="main">
    <h1>{title}</h1>
    {status_card}
    {body_html}
  </main>
  <footer class="footer">Wärme Wimmer · Hero-Automatisierungen · Aufgesetzt von <a href="https://unpauseai.com">UnpauseAI</a></footer>
</div>
<div id="auth-gate" style="position:fixed;inset:0;z-index:9999;background:var(--bg);display:flex;align-items:center;justify-content:center;transition:opacity .3s;">
  <div style="text-align:center;max-width:360px;padding:24px;">
    <div style="display:flex;align-items:center;justify-content:center;gap:8px;margin:0 auto 20px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="40" height="40"><rect width="32" height="32" rx="7" fill="#2563eb"/><rect x="9" y="8" width="4.5" height="16" rx="1.5" fill="white"/><polygon points="18,8 23,16 18,24" fill="white"/></svg><span style="font-size:22px;letter-spacing:-0.025em;"><span style="font-weight:700;">Unpause</span><span style="font-weight:700;color:#2563eb;">AI</span></span></div>
    <h2 style="font-size:20px;font-weight:700;color:var(--text);margin-bottom:4px;">Wärme Wimmer Documentation</h2>
    <p style="font-size:14px;color:var(--text2);margin-bottom:24px;">Bitte Zugangscode eingeben.</p>
    <div style="display:flex;gap:8px;">
      <input id="auth-input" type="password" placeholder="Zugangscode" autocomplete="off" style="flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:8px;font-size:15px;background:var(--surface);color:var(--text);outline:none;" onkeydown="if(event.key==='Enter')checkAuth()" />
      <button onclick="checkAuth()" style="padding:10px 20px;border:none;border-radius:8px;background:linear-gradient(135deg,#2563eb,#7c3aed);color:#fff;font-weight:600;font-size:14px;cursor:pointer;">OK</button>
    </div>
    <p id="auth-error" style="color:#dc2626;font-size:13px;margin-top:8px;display:none;">Falscher Code, bitte erneut versuchen.</p>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true,theme:document.documentElement.getAttribute('data-theme')==='dark'?'dark':'default',securityLevel:'loose'}});</script>
<script>{AUTH_THEME_JS}</script>
</body>
</html>
"""


def render_dashboard_kpis(make_status: dict, storage: dict) -> str:
    """KPI strip at the top of the dashboard."""
    if make_status.get("unavailable"):
        return '<div class="status-card"><div class="status-row"><span class="status-label">Live-Status</span><span>nicht verfügbar (Token oder Make REST nicht erreichbar)</span></div></div>'

    org = make_status.get("org", {})
    ops_used = org.get("ops_used", 0)
    ops_limit = org.get("ops_limit", 0)
    ops_pct = org.get("ops_pct", 0)
    auto_buy = "aktiv" if org.get("auto_buy") else "inaktiv"
    next_reset = _humanize_dt(org.get("next_reset"))
    fetched = _humanize_dt(make_status.get("fetched_at"))

    bar_class = "danger" if ops_pct > 85 else ("warn" if ops_pct > 60 else "")

    storage_block = ""
    storage_data = storage.get("storage", {}) if storage else {}
    if storage_data:
        s_pct = storage_data.get("percent", 0)
        s_class = "danger" if s_pct > 85 else ("warn" if s_pct > 60 else "")
        s_used = storage_data.get("used_gb", 0)
        s_total = storage_data.get("total_gb", 0)
        s_date = storage_data.get("date", "—")
        storage_block = f"""
<div class="kpi">
  <div class="kpi-label">Outlook-Speicher</div>
  <div class="kpi-value">{s_pct}%</div>
  <div class="kpi-sub">{s_used} von {s_total} GB · Stand {s_date}</div>
  <div class="kpi-progress"><div class="kpi-progress-bar {s_class}" style="width:{s_pct}%"></div></div>
</div>"""

    scenarios = make_status.get("scenarios", {})
    n_active = sum(1 for s in scenarios.values() if s.get("is_active"))
    n_total = len(scenarios)

    return f"""<div class="kpi-grid">
<div class="kpi">
  <div class="kpi-label">Make-Operations (Cycle)</div>
  <div class="kpi-value">{ops_used:,} / {ops_limit:,}</div>
  <div class="kpi-sub">{ops_pct}% verbraucht{f" · {org.get('extra_bought'):,} Auto-Buy" if org.get('extra_bought') else ""} · Reset {next_reset[:10] if next_reset != "—" else "—"}</div>
  <div class="kpi-progress"><div class="kpi-progress-bar {bar_class}" style="width:{min(ops_pct, 100)}%"></div></div>
</div>
<div class="kpi">
  <div class="kpi-label">Aktive Szenarien</div>
  <div class="kpi-value">{n_active} / {n_total}</div>
  <div class="kpi-sub">Auto-Buy {auto_buy}</div>
</div>{storage_block}
</div>
<p style="color:var(--text3);font-size:11px;margin-top:-12px;margin-bottom:24px;">Live-Daten via Make REST API · Build-Snapshot {fetched}</p>"""


def render_dashboard_table(make_status: dict, all_pages: dict[str, str]) -> str:
    if make_status.get("unavailable"):
        return ""
    rows = []
    rows.append('<table class="dashboard-table">')
    rows.append("<thead><tr><th>Szenario</th><th>Status</th><th>Letzter Lauf</th><th>Plan</th><th>Letzte 50</th></tr></thead>")
    rows.append("<tbody>")
    for n in range(1, 11):
        scn = make_status.get("scenarios", {}).get(n)
        if not scn:
            continue
        # Find filename for link
        target_file = next(
            (f for f in all_pages if f.startswith(f"S-{n:02d}-") and not is_dropped(f)),
            None,
        )
        if target_file:
            link = f'<a href="{BASE_PATH}{page_slug(target_file)}.html">{display_title(target_file, all_pages[target_file])}</a>'
        else:
            link = f"{scn['label']}: {scn['name']}"
        last_run_short = _humanize_dt(scn.get("last_run"))
        if last_run_short != "—":
            last_run_short = last_run_short[:16]  # Trim "UTC" etc
        success = f'{scn.get("ok_count", 0)} OK'
        if scn.get("err_count"):
            success += f' · {scn["err_count"]} Fehler'
        if scn.get("warn_count"):
            success += f' · {scn["warn_count"]} Warnung'
        rows.append(
            f'<tr><td>{link}</td>'
            f'<td><span class="badge {_health_class(scn["health"])}">{scn["health"]}</span></td>'
            f'<td>{last_run_short}</td>'
            f'<td>{scn["schedule"]}</td>'
            f'<td>{success}</td></tr>'
        )
    rows.append("</tbody></table>")
    return "\n".join(rows)


def render_index(all_pages: dict[str, str], make_status: dict, storage: dict) -> str:
    cards_html = [
        '<div class="cards">',
        _card("S-00-flowcharts-overview", "Flowcharts-Übersicht", "Alle 10 Hero-Automationen auf einer Seite, mit Sabine-Sicht und Audit-Sicht."),
        _card("M-meetings", "Meetings", "Chronik aller Meetings mit Decision-Log und Notizen pro Termin."),
        _card("R-team-updates", "Wartungs-Updates", "An das Team kommunizierte Status-Updates inkl. Screenshots."),
        _card("R-00-uebersicht", "Lastenheft (Hintergrund)", "Spezifikations-Dokument aus der Bauphase, post-Go-Live aktualisiert."),
        _card("R-hero-ids-und-connections", "Hero-IDs und Connections", "Referenz-Tabelle aller Tokens, Connection-IDs und Hooks."),
        _card("R-kosten-und-subscription", "Kosten und Subscription", "Make-Tier, OpenAI, weitere Komponenten."),
        "</div>",
    ]

    support = """
<h2>Support</h2>
<div class="support-cards">
  <a class="support-card" href="mailto:nicolas@unpauseai.com?subject=W%C3%A4rme%20Wimmer%20-%20%C3%84nderungs-Anfrage">
    <h4>Änderung anfragen</h4><p>Was soll angepasst oder erweitert werden?</p><span class="card-tag">E-Mail</span>
  </a>
  <a class="support-card" href="mailto:nicolas@unpauseai.com?subject=W%C3%A4rme%20Wimmer%20-%20Problem-Meldung">
    <h4>Problem melden</h4><p>Eine Automatisierung verhält sich nicht wie erwartet?</p><span class="card-tag">E-Mail</span>
  </a>
</div>
"""

    sidebar = render_sidebar(all_pages, "index")
    body = (
        render_dashboard_kpis(make_status, storage)
        + "<h2>Status der Automatisierungen</h2>"
        + render_dashboard_table(make_status, all_pages)
        + "<h2>Weitere Bereiche</h2>"
        + "\n".join(cards_html)
        + support
    )

    return f"""<!DOCTYPE html>
<html lang="de" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,nofollow">
<meta name="googlebot" content="noindex,nofollow">
<title>Wärme Wimmer — Hero-Automatisierungen</title>
<style>{CSS}</style>
</head>
<body>
<div class="sidebar-backdrop" id="sidebarBackdrop" onclick="closeSidebar()"></div>
{sidebar}
<header class="header">
  <div class="header-left">
    <button class="hamburger" onclick="toggleSidebar()">☰</button>
    <div class="header-logo"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="28" height="28"><rect width="32" height="32" rx="7" fill="#2563eb"/><rect x="9" y="8" width="4.5" height="16" rx="1.5" fill="white"/><polygon points="18,8 23,16 18,24" fill="white"/></svg><span><span class="logo-text">Unpause</span><span class="logo-accent">AI</span></span></div>
    <div class="header-title"><h1>Wärme Wimmer</h1><p>Hero-Automatisierungen Dokumentation</p></div>
  </div>
  <div class="header-right">
    <span class="badge badge-green"><span class="badge-dot"></span>9 von 10 aktiv</span>
    <button class="theme-btn" onclick="toggleTheme()"><span id="theme-icon">&#9790;</span> Theme</button>
  </div>
</header>
<div class="page-layout">
  <main class="main">
    <h1>Hero-Automatisierungen — Wärme Wimmer</h1>
    <p style="color:var(--text2);font-size:14px;margin-bottom:24px;">Stand 2026-05-06 · Tag 8 nach Go-Live · 9 von 10 Szenarien aktiv</p>
    {body}
  </main>
  <footer class="footer">Quelle: <code>workspace/clients/warme-wimmer/</code> · UnpauseAI</footer>
</div>
<div id="auth-gate" style="position:fixed;inset:0;z-index:9999;background:var(--bg);display:flex;align-items:center;justify-content:center;transition:opacity .3s;">
  <div style="text-align:center;max-width:360px;padding:24px;">
    <div style="display:flex;align-items:center;justify-content:center;gap:8px;margin:0 auto 20px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="40" height="40"><rect width="32" height="32" rx="7" fill="#2563eb"/><rect x="9" y="8" width="4.5" height="16" rx="1.5" fill="white"/><polygon points="18,8 23,16 18,24" fill="white"/></svg><span style="font-size:22px;letter-spacing:-0.025em;"><span style="font-weight:700;">Unpause</span><span style="font-weight:700;color:#2563eb;">AI</span></span></div>
    <h2 style="font-size:20px;font-weight:700;color:var(--text);margin-bottom:4px;">Wärme Wimmer Documentation</h2>
    <p style="font-size:14px;color:var(--text2);margin-bottom:24px;">Bitte Zugangscode eingeben.</p>
    <div style="display:flex;gap:8px;">
      <input id="auth-input" type="password" placeholder="Zugangscode" autocomplete="off" style="flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:8px;font-size:15px;background:var(--surface);color:var(--text);outline:none;" onkeydown="if(event.key==='Enter')checkAuth()" />
      <button onclick="checkAuth()" style="padding:10px 20px;border:none;border-radius:8px;background:linear-gradient(135deg,#2563eb,#7c3aed);color:#fff;font-weight:600;font-size:14px;cursor:pointer;">OK</button>
    </div>
    <p id="auth-error" style="color:#dc2626;font-size:13px;margin-top:8px;display:none;">Falscher Code, bitte erneut versuchen.</p>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true,theme:document.documentElement.getAttribute('data-theme')==='dark'?'dark':'default',securityLevel:'loose'}});</script>
<script>{AUTH_THEME_JS}</script>
</body>
</html>
"""


def _card(slug: str, title: str, desc: str) -> str:
    return f'<a class="card" href="{BASE_PATH}{slug}.html"><h3>{title}</h3><p>{desc}</p></a>'


def main() -> int:
    if not SRC_TOOL.is_file():
        print(f"ERROR: {SRC_TOOL} not found", file=sys.stderr)
        return 1
    v18 = _import_v18()
    pages = v18.build_pages()
    print(f"Loaded {len(pages)} source pages from notion-restructure-v18")

    print("Fetching live Make REST status...")
    make_status = fetch_make_status()
    if make_status.get("unavailable"):
        print(f"  WARN: live data unavailable ({make_status.get('reason')}); building without status cards")
    else:
        org = make_status.get("org", {})
        print(f"  Org ops: {org.get('ops_used'):,}/{org.get('ops_limit'):,} ({org.get('ops_pct')}%)")
        print(f"  Auto-buy: {'aktiv' if org.get('auto_buy') else 'inaktiv'}")
        print(f"  Scenarios fetched: {len(make_status.get('scenarios', {}))}")

    storage = read_storage_status()
    if storage:
        s = storage.get("storage", {})
        print(f"Storage from status.yaml: {s.get('percent')}% ({s.get('used_gb')}/{s.get('total_gb')} GB), date {s.get('date')}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Clean stale .html files from previous builds (drops, renames).
    # Compute the set of slugs we'll write this build, plus index.
    expected_slugs = {page_slug(fname) for fname in pages if not is_dropped(fname)}
    expected_slugs.add("index")
    removed = 0
    for old in OUT_DIR.glob("*.html"):
        if old.stem not in expected_slugs:
            old.unlink()
            removed += 1
    if removed:
        print(f"Removed {removed} stale .html file(s)")

    written = 0
    skipped = 0
    for fname, content in pages.items():
        if is_dropped(fname):
            skipped += 1
            continue
        slug = page_slug(fname)
        out_path = OUT_DIR / f"{slug}.html"
        out_path.write_text(render_page(fname, content, pages, make_status), encoding="utf-8")
        written += 1
    # Case-insensitive URLs handled by platform/src/proxy.ts which
    # 308-redirects any uppercase chars in /docs/warme-wimmer/* paths.

    index_path = OUT_DIR / "index.html"
    index_path.write_text(render_index(pages, make_status, storage), encoding="utf-8")
    written += 1
    print(f"Skipped {skipped} dropped pages (per PAGE_META drop=True)")

    print(f"Wrote {written} HTML files to {OUT_DIR}")
    print()
    print("Local preview:")
    print(f"  cd platform && npm run dev")
    print(f"  open http://localhost:3000/docs/warme-wimmer/")
    print()
    print(f"Access code: {ACCESS_CODE}")
    print("Subdomain `wimmer.unpauseai.com` requires:")
    print("  1. Vercel UI: add domain alias `wimmer.unpauseai.com` to the platform project")
    print("  2. DNS: add CNAME `wimmer` -> `cname.vercel-dns.com`")
    print("  3. platform/vercel.json: add subdomain rewrite (this script does NOT modify vercel.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
