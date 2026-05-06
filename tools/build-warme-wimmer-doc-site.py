# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "markdown>=3.7",
# ]
# ///
"""Build static HTML doc site for Wärme Wimmer.

Output: platform/public/docs/warme-wimmer/
- index.html   landing with cards
- {slug}.html  one per source markdown page
- mermaid + auth gate + theme toggle + sidebar nav, Meji-Media style

Source content reuses notion-restructure-v18.build_pages().
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import markdown as md_lib

REPO = Path.cwd()
SRC_TOOL = REPO / "tools/notion-restructure-v18.py"
OUT_DIR = REPO / "platform/public/docs/warme-wimmer"
BASE_PATH = "/docs/warme-wimmer/"
ACCESS_CODE = "wimmer2026"
LS_PREFIX = "wimmer-docs"


def _import_v18():
    spec = importlib.util.spec_from_file_location("v18", SRC_TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


GROUP_LABEL = {
    "0-": "Start",
    "M-": "Meetings",
    "S-": "Szenarien",
    "R-": "Referenz",
}


def group_for(filename: str) -> str:
    for prefix, label in GROUP_LABEL.items():
        if filename.startswith(prefix):
            return label
    return "Sonstiges"


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
    grouped: dict[str, list[tuple[str, str]]] = {"0-": [], "M-": [], "S-": [], "R-": []}
    for fname in sorted(pages.keys()):
        for prefix in grouped:
            if fname.startswith(prefix):
                grouped[prefix].append((fname, page_title(fname, pages[fname])))
                break

    out = ['<nav class="sidebar" id="sidebar">']
    out.append(f'<div class="sidebar-group"><a href="{BASE_PATH}" class="sidebar-home{(" active" if current_slug == "index" else "")}">Übersicht</a></div>')
    for prefix, label in GROUP_LABEL.items():
        items = grouped.get(prefix, [])
        if not items:
            continue
        out.append(f'<div class="sidebar-group"><div class="sidebar-group-label">{label}</div><ul class="sidebar-nav">')
        for fname, title in items:
            slug = page_slug(fname)
            cls = ' class="active"' if slug == current_slug else ""
            out.append(f'<li><a href="{BASE_PATH}{slug}.html"{cls}>{title}</a></li>')
        out.append("</ul></div>")
    out.append("</nav>")
    return "\n".join(out)


def render_page(filename: str, content: str, all_pages: dict[str, str]) -> str:
    title = page_title(filename, content)
    body_md = re.sub(r"^# .+\n+", "", content, count=1)
    body_html = md_to_html_body(body_md)
    sidebar = render_sidebar(all_pages, page_slug(filename))

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


def render_index(all_pages: dict[str, str]) -> str:
    cards_html = []
    cards_html.append('<div class="cards">')
    cards_html.append(_card("S-00-flowcharts-overview", "Flowcharts-Übersicht", "Alle 10 Hero-Automationen auf einer Seite. Sabine-Sicht und Audit-Sicht pro Szenario."))
    cards_html.append(_card("M-meetings", "Meetings & Decision-Log", "Chronik aller Meetings vom Onboarding bis Post-Go-Live, mit Entscheidungs-Index."))
    cards_html.append(_card("R-team-updates", "Wartungs-Updates", "Speicher- und Credit-Stand, plus Updates die an das Team gingen."))
    cards_html.append(_card("R-00-uebersicht", "Lastenheft", "Vollständige Dokumentation, post-Go-Live aktualisiert."))
    cards_html.append(_card("R-hero-ids-und-connections", "Hero-IDs und Connections", "Referenz-Tabelle aller Tokens, Connection-IDs und Hooks."))
    cards_html.append(_card("R-kosten-und-subscription", "Kosten und Subscription", "Make-Tier, OpenAI, Mailgun, S3 — Verbrauch und Tarife."))
    cards_html.append("</div>")

    scenarios = []
    scenarios.append("<h2>Szenarien (W2-01 bis W2-10)</h2>")
    scenarios.append('<div class="cards">')
    s_pages = sorted([k for k in all_pages.keys() if k.startswith("S-") and not k.startswith("S-00")])
    for fname in s_pages:
        title = page_title(fname, all_pages[fname])
        scenarios.append(_card(fname.removesuffix(".md"), title, ""))
    scenarios.append("</div>")

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
        "<p>Vollständige Dokumentation der zehn Hero-Make-Automatisierungen, die seit dem 28. April 2026 "
        "die Hero-Workflows von Wärme Wimmer abdecken. Neun Szenarien sind aktiv im Produktivbetrieb; "
        "W2-10 ist auf die n8n-Migration verschoben.</p>"
        "<p style=\"color:var(--text2);font-size:14px;margin-top:8px;\">Diese Seite ersetzt die bisherige Notion-Dokumentation. "
        "Inhalte werden direkt aus der Quelltext-Steuerung gepflegt; Änderungen sind nach kurzer Zeit live.</p>"
        "<h2>Schnell-Einstieg</h2>"
        + "\n".join(cards_html)
        + "\n".join(scenarios)
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

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for fname, content in pages.items():
        slug = page_slug(fname)
        out_path = OUT_DIR / f"{slug}.html"
        out_path.write_text(render_page(fname, content, pages), encoding="utf-8")
        written += 1

    index_path = OUT_DIR / "index.html"
    index_path.write_text(render_index(pages), encoding="utf-8")
    written += 1

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
