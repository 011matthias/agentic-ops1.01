"""validate-html.py residual fixes (2026-07-22 audit).

D1  — extensionless relative hrefs (`<a href="solution">`, the form Vercel
      cleanUrls actually produces on nested routes) were invisible: only
      .html/.htm-suffixed or slash-bearing hrefs flagged.
D2  — the docstring promised --dir mode checks cross-page theme-toggle and
      Ctrl/Cmd+K search wiring; check_directory only did nav links. Now
      implemented (all-present / all-absent are uniform; a mixed set flags).
Minors — --dir is recursive (rglob), non-HTML CLI args warn loudly instead
      of dropping silently, nav-inconsistency flags at ONE missing link.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

from hooklib import TOOLS

TOOL = TOOLS / "validate-html.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_html_links", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vh = _load()

HEAD = ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width'>"
        "<title>t</title></head><body>")
FOOT = "</body></html>"
WIRED = ("<script>document.documentElement.setAttribute('data-theme','d');"
         "localStorage.setItem('t','d');"
         "addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='k'){}});"
         "</script>")


def _relative_hrefs(tmp_path: Path, body: str) -> list[str]:
    p = tmp_path / "page.html"
    p.write_text(HEAD + body + FOOT, encoding="utf-8")
    return [h["message"].split("'")[1] for h in vh.check_one(p)
            if h["category"] == "relative-link"]


# --- D1: extensionless relative hrefs ----------------------------------------

def test_extensionless_relative_href_flagged(tmp_path):
    assert _relative_hrefs(tmp_path, '<a href="solution">x</a>') == ["solution"]


def test_html_suffixed_relative_href_still_flagged(tmp_path):
    assert _relative_hrefs(tmp_path, '<a href="page2.html">x</a>') == ["page2.html"]


def test_dot_slash_relative_href_still_flagged(tmp_path):
    assert _relative_hrefs(tmp_path, '<a href="./sub/page">x</a>') == ["./sub/page"]


def test_absolute_scheme_and_anchor_hrefs_pass(tmp_path):
    body = ('<a href="/solution">a</a><a href="https://x.com">b</a>'
            '<a href="mailto:a@b.c">c</a><a href="tel:+491234">d</a>'
            '<a href="data:text/plain,hi">e</a><a href="#section">f</a>'
            '<a href="javascript:void(0)">g</a>')
    assert _relative_hrefs(tmp_path, body) == []


# --- D2 + minors: directory mode ----------------------------------------------

def _page(links: list[str], wired: bool = True) -> str:
    anchors = "".join(f'<a href="/{ln}">{ln}</a>' for ln in links)
    return HEAD + anchors + (WIRED if wired else "") + FOOT


def _write_set(d: Path, pages: dict[str, str]) -> None:
    for rel, content in pages.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="")


def test_uniform_wiring_no_hits(tmp_path):
    _write_set(tmp_path, {
        "a.html": _page(["b", "c"]),
        "b.html": _page(["a", "c"]),
        "c.html": _page(["a", "b"]),
    })
    cats = [h["category"] for h in vh.check_directory(tmp_path)]
    assert cats == []


def test_uniformly_absent_wiring_no_hits(tmp_path):
    _write_set(tmp_path, {
        "a.html": _page(["b", "c"], wired=False),
        "b.html": _page(["a", "c"], wired=False),
        "c.html": _page(["a", "b"], wired=False),
    })
    cats = [h["category"] for h in vh.check_directory(tmp_path)]
    assert cats == []


def test_mixed_wiring_flags_both_features(tmp_path):
    _write_set(tmp_path, {
        "a.html": _page(["b", "c"]),
        "b.html": _page(["a", "c"]),
        "c.html": _page(["a", "b"], wired=False),
    })
    hits = vh.check_directory(tmp_path)
    cats = {h["category"] for h in hits}
    assert cats == {"theme-toggle-inconsistency", "keyboard-search-inconsistency"}
    for h in hits:
        assert "c.html" in h["message"]


def test_single_missing_nav_link_now_flags(tmp_path):
    # b.html misses exactly ONE sibling link; the old >= 2 floor let it ship.
    _write_set(tmp_path, {
        "a.html": _page(["b", "c"]),
        "b.html": _page(["a"]),
        "c.html": _page(["a", "b"]),
    })
    hits = [h for h in vh.check_directory(tmp_path)
            if h["category"] == "nav-inconsistency"]
    assert len(hits) == 1
    assert "b.html" in hits[0]["message"] and "c" in hits[0]["message"]
    assert hits[0]["severity"] == "MEDIUM"


def test_directory_scan_is_recursive(tmp_path):
    # A page in a subdirectory joins the set (rglob, not glob).
    _write_set(tmp_path, {
        "a.html": _page(["b", "sub"]),
        "b.html": _page(["a", "sub"]),
        "sub/sub.html": _page(["a", "b"], wired=False),
    })
    cats = {h["category"] for h in vh.check_directory(tmp_path)}
    assert "theme-toggle-inconsistency" in cats


def test_chromeless_pages_stay_exempt_from_wiring(tmp_path):
    _write_set(tmp_path, {
        "a.html": _page(["b", "c"]),
        "b.html": _page(["a", "c"]),
        "print.html": "<!-- chrome-allow: chromeless -->" + _page([], wired=False),
    })
    cats = [h["category"] for h in vh.check_directory(tmp_path)]
    assert cats == []


# --- minors: CLI warns on non-HTML args ---------------------------------------

def test_non_html_cli_arg_warns_loudly(tmp_path):
    md = tmp_path / "notes.md"
    md.write_text("x", encoding="utf-8")
    ok = tmp_path / "page.html"
    ok.write_text(HEAD + FOOT, encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOL), str(md), str(ok)],
                       capture_output=True, text=True)
    assert "WARNING" in r.stderr and "notes.md" in r.stderr
    assert r.returncode == 0, r.stdout + r.stderr


def test_missing_file_cli_arg_warns_loudly(tmp_path):
    ok = tmp_path / "page.html"
    ok.write_text(HEAD + FOOT, encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOL), str(tmp_path / "gone.html"), str(ok)],
                       capture_output=True, text=True)
    assert "WARNING" in r.stderr and "gone.html" in r.stderr
