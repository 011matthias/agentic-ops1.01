"""validate-deliverable.py check_qol_features comment blindness
(2026-07-22 blind-spot fix).

The QoL checks were whole-file substring tests, so the required feature
strings sitting inside an HTML comment satisfied all three HIGH
ship-blockers. Comments are stripped before matching now; the
`deliverable-allow` suppression markers (which ARE comments) keep working
because the caller parses them from the raw text.
"""
import importlib.util
import sys

from hooklib import TOOLS


def _load():
    path = TOOLS / "validate-deliverable.py"
    spec = importlib.util.spec_from_file_location("validate_deliverable", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


vd = _load()

FEATURES = (
    "<script>"
    "document.documentElement.setAttribute('data-theme','dark');"
    "localStorage.setItem('theme','dark');localStorage.getItem('theme');"
    "navigator.clipboard.writeText(x);"
    "window.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='k'){}});"
    "</script>"
)


def test_real_features_pass():
    text = f"<html><body>{FEATURES}</body></html>"
    assert vd.check_qol_features(text, set()) == []


def test_features_only_in_comment_flag_all_three_high():
    text = f"<html><body><!-- {FEATURES} --></body></html>"
    hits = vd.check_qol_features(text, set())
    high = {h["category"] for h in hits if h["severity"] == "HIGH"}
    assert high == {"dark-mode-toggle", "copy-clipboard", "keyboard-search"}
    # state-persistence is the MEDIUM fourth check; it must flag too.
    assert {h["category"] for h in hits if h["severity"] == "MEDIUM"} == {"state-persistence"}


def test_suppression_markers_still_work():
    # The deliverable-allow marker is itself an HTML comment; stripping
    # comments for feature matching must not break suppression, which the
    # caller parses from the raw text.
    text = "<html><!-- deliverable-allow: dark-mode-toggle, copy-clipboard, keyboard-search, state-persistence --></html>"
    suppressed = vd.parse_suppressions(text)
    assert vd.check_qol_features(text, suppressed) == []


# --- E2 residual (2026-07-22): whole-text link scan + extensionless rule -----

def _rel_hits(text: str):
    return [(h["line"], h["message"].split("'")[1])
            for h in vd.check_relative_paths(text)]


def test_multiline_anchor_is_caught():
    # Line-by-line scanning let `<a\n href="page2.html">` escape entirely.
    text = 'intro\n<a\n  class="nav"\n  href="page2.html">x</a>\n'
    assert _rel_hits(text) == [(2, "page2.html")]


def test_extensionless_relative_href_is_caught():
    # The actual Vercel cleanUrls form that breaks on nested routes.
    assert _rel_hits('<a href="solution">x</a>\n') == [(1, "solution")]


def test_scheme_anchor_and_absolute_pass():
    text = ('<a href="/x">a</a><a href="https://y.z">b</a>'
            '<a href="mailto:a@b.c">c</a><a href="tel:+49">d</a>'
            '<a href="data:text/plain,hi">e</a><a href="#top">f</a>'
            '<a href="javascript:void(0)">g</a>\n')
    assert _rel_hits(text) == []


def test_dot_and_dotdot_relative_still_caught():
    assert [h for _, h in _rel_hits('<a href="./a.html">x</a><a href="../b">y</a>\n')] \
        == ["./a.html", "../b"]


def test_dead_regexes_removed():
    # SCRIPT_SRC_RE / LINK_HREF_RE were defined but never used; they are gone.
    assert not hasattr(vd, "SCRIPT_SRC_RE")
    assert not hasattr(vd, "LINK_HREF_RE")
