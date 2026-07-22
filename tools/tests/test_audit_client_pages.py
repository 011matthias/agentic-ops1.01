"""audit-client-pages.py §3 theme probes (2026-07-22 blind-spot fixes).

Two input-grammar gaps defeated the theme probes:

  1. THEME_KEY/THEME_SET matched single-quoted lowercase keys only, so a
     double-quoted "site-theme" or camelCase 'siteTheme' toggle was invisible
     and the theme-key-collision probe (the 2026-06-03 incident class) never
     fired on exactly the pages it exists for.
  2. boot_count = text.count(CANONICAL_BOOT) counted a boot script inside an
     HTML comment as present.
"""
import importlib.util
import sys

from hooklib import TOOLS


def _load():
    path = TOOLS / "audit-client-pages.py"
    spec = importlib.util.spec_from_file_location("audit_client_pages", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


acp = _load()

BOOT = acp.CANONICAL_BOOT


def _cats(text: str) -> set[str]:
    return {h["category"] for h in acp.audit_text(text)}


# --- theme-key extraction grammar -------------------------------------------

def test_double_quoted_key_collides_with_canonical():
    text = (
        f"<script>{BOOT} localStorage.getItem('theme')</script>"
        '<script>localStorage.setItem("site-theme", c)</script>'
    )
    hits = [h for h in acp.audit_text(text) if h["category"] == "theme-key-collision"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "HIGH"


def test_camelcase_key_collides_with_canonical():
    text = (
        f"<script>{BOOT} localStorage.getItem('theme')</script>"
        "<script>localStorage.setItem('siteTheme', c)</script>"
    )
    assert "theme-key-collision" in _cats(text)


def test_single_canonical_key_no_collision():
    text = (
        f"<script>{BOOT} localStorage.getItem('theme')"
        " localStorage.setItem('theme', c)</script>"
    )
    assert "theme-key-collision" not in _cats(text)


def test_double_quoted_noncanonical_single_key_flagged_medium():
    text = f'<script>{BOOT} localStorage.getItem("site-theme")</script>'
    hits = [h for h in acp.audit_text(text) if h["category"] == "theme-key-noncanonical"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "MEDIUM"


# --- comment-blind boot counting ----------------------------------------------

def test_commented_out_boot_does_not_count():
    text = f"<!-- <script>{BOOT}</script> -->"
    assert "theme-boot-missing" in _cats(text)


def test_live_boot_counts():
    text = f"<script>{BOOT}</script>"
    assert "theme-boot-missing" not in _cats(text)


def test_commented_theme_key_causes_no_false_collision():
    text = (
        f"<script>{BOOT} localStorage.getItem('theme')</script>"
        "<!-- old toggle: localStorage.setItem('legacy-theme', c) -->"
    )
    assert "theme-key-collision" not in _cats(text)
