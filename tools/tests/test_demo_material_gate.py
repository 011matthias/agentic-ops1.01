"""DEMO CONTENT GATE wiring: post-write-gate scope predicates for
banned-content (client-directive) scanning, plus the --format json contract
of validate-demo-material.py the dispatcher consumes. Pins the 2026-07-10
wiring so a refactor can't silently drop the gate that closed the
three-BTP-leaks-in-one-day failure mode (2026-07-09).
"""
import importlib.util
import json
import subprocess
import sys

from hooklib import HOOKS

REPO = HOOKS.parent.parent
VALIDATOR = REPO / "tools" / "validate-demo-material.py"


def _load_gate():
    path = HOOKS / "post-write-gate.py"
    spec = importlib.util.spec_from_file_location("post_write_gate", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["post_write_gate"] = mod
    spec.loader.exec_module(mod)
    return mod


G = _load_gate()


# --- in_demo_material_scope: deliverables + resources-site, text suffixes ---
def test_demo_scope_deliverable_html():
    assert G.in_demo_material_scope("workspace/clients/brisken/deliverables/x.html")


def test_demo_scope_resources_site():
    assert G.in_demo_material_scope("workspace/clients/brisken/resources-site/index.html")


def test_demo_scope_captions():
    assert G.in_demo_material_scope("workspace/clients/brisken/deliverables/clip.srt")


def test_demo_scope_rejects_binary_suffix():
    # PDFs land via Bash renders, never Write/Edit; out of dispatcher scope.
    assert not G.in_demo_material_scope("workspace/clients/brisken/deliverables/x.pdf")


def test_demo_scope_rejects_context_tree():
    assert not G.in_demo_material_scope("workspace/clients/brisken/context/notes.md")


def test_demo_scope_rejects_outside_clients():
    assert not G.in_demo_material_scope("docs/sessions/2026-07-10.md")


def test_demo_scope_empty_path():
    assert not G.in_demo_material_scope("")


# --- demo_client_for: fixture-gated client derivation ----------------------
def test_demo_client_known():
    assert G.demo_client_for("workspace/clients/brisken/deliverables/x.md") == "brisken"


def test_demo_client_unknown_returns_none():
    assert G.demo_client_for("workspace/clients/no-such-client/deliverables/x.md") is None


def test_demo_client_outside_clients_returns_none():
    assert G.demo_client_for("platform/public/clients/x/index.html") is None


# --- validate-demo-material --format json: the dispatcher contract ---------
def _run_json(path):
    proc = subprocess.run(
        ["uv", "run", str(VALIDATOR), "--client", "brisken", "--format", "json", str(path)],
        capture_output=True, text=True, timeout=120, cwd=str(REPO),
    )
    return proc.returncode, json.loads(proc.stdout)


def test_json_contract_on_hit(tmp_path):
    f = tmp_path / "plant.txt"
    f.write_text("Runs on SAP BTP as SaaS.\n", encoding="utf-8")
    code, payload = _run_json(f)
    assert code == 1
    assert payload["total"] == 1
    hit = payload["hits"][0]
    assert hit["severity"] == "HIGH"
    assert hit["category"] == "banned-content"
    assert hit["line"] == 1
    assert payload["by_severity"] == {"HIGH": 1}


def test_json_contract_clean(tmp_path):
    f = tmp_path / "clean.txt"
    f.write_text("Nothing banned here.\n", encoding="utf-8")
    code, payload = _run_json(f)
    assert code == 0
    assert payload == {"total": 0, "hits": [], "by_category": {}, "by_severity": {}}


# --- 2026-07-22 blind-spot fixes: speaker notes + multi-word line breaks ----

def _make_pptx(path, parts: dict[str, str]) -> None:
    """Minimal pptx-shaped zip: the validator reads slide/notesSlide XML parts
    with a regex, so no python-pptx and no committed binary fixture needed."""
    import zipfile
    with zipfile.ZipFile(path, "w") as z:
        for name, txt in parts.items():
            z.writestr(name, f"<p:sld><a:t>{txt}</a:t></p:sld>")


def test_notes_slides_are_scanned(tmp_path):
    # Banned term ONLY in the speaker notes; ppt/slides/ is clean.
    f = tmp_path / "deck.pptx"
    _make_pptx(f, {
        "ppt/slides/slide1.xml": "clean visible slide",
        "ppt/notesSlides/notesSlide1.xml": "presenter cue: mention SAP BTP here",
    })
    code, payload = _run_json(f)
    assert code == 1
    assert payload["total"] == 1
    assert "notes slide 1" in payload["hits"][0]["message"]


def test_visible_slides_still_scanned(tmp_path):
    f = tmp_path / "deck.pptx"
    _make_pptx(f, {"ppt/slides/slide2.xml": "runs on SAP BTP"})
    code, payload = _run_json(f)
    assert code == 1
    assert "slide 2" in payload["hits"][0]["message"]


def test_multiword_term_across_line_break(tmp_path):
    # PDF extract_text inserts newlines constantly; the multi-word directive
    # term must match across them ('Business\nTechnology Platform').
    f = tmp_path / "extract.txt"
    f.write_text("built on the Business\nTechnology Platform stack\n", encoding="utf-8")
    code, payload = _run_json(f)
    assert code == 1
    assert payload["total"] == 1
    assert "Business Technology Platform" in payload["hits"][0]["message"]
