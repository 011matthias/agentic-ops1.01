"""validate-pilot-routing.py input-grammar gaps (2026-07-22 blind-spot fixes).

Two confirmed gaps:

  1. parse_routing_table required bold `**Piece N**` and a trailing newline,
     so a plain `| Piece 2 |` row and the last row of a file without a final
     newline were silently dropped from the routing map.
  2. find_piece_attributed_sections only anchored on bold markers or
     line-leading `Piece N`, so the actual 2026-05-30 incident shape — a
     mid-sentence lowercase "piece 1: ..." attribution — was invisible, and
     attributed text before the first strong marker was never scanned.
"""
import importlib.util
import sys
from pathlib import Path

from hooklib import TOOLS


def _load():
    path = TOOLS / "validate-pilot-routing.py"
    spec = importlib.util.spec_from_file_location("validate_pilot_routing", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


vpr = _load()

# Header + separator + one bold row + one PLAIN last row with NO trailing
# newline: both 2026-07-22 parse gaps in one fixture.
TABLE = (
    "| Piece | Audience | Campaign | Mailboxes |\n"
    "|---|---|---|---|\n"
    "| **Piece 1** | warm | `11111111-aaaa-bbbb-cccc-111111111111` | `warm@warmdomain.co` |\n"
    "| Piece 2 | cold | `22222222-aaaa-bbbb-cccc-222222222222` | `cold@colddomain.co` |"
)


def _client_tree(tmp_path: Path, table: str = TABLE) -> Path:
    ctx = tmp_path / "workspace" / "clients" / "meji" / "context"
    (ctx / "drafts").mkdir(parents=True)
    (ctx / "pilot-routing.md").write_text(table, encoding="utf-8")
    return ctx / "drafts"


# --- parse_routing_table ------------------------------------------------------

def test_parse_non_bold_and_last_row_without_newline(tmp_path):
    drafts = _client_tree(tmp_path)
    routing = vpr.parse_routing_table(drafts.parent / "pilot-routing.md")
    assert set(routing) == {"1", "2"}
    assert routing["2"]["mailboxes"] == ["cold@colddomain.co"]
    assert routing["2"]["campaign_ids"] == ["22222222-aaaa-bbbb-cccc-222222222222"]


def test_parse_bold_row_still_works(tmp_path):
    drafts = _client_tree(tmp_path)
    routing = vpr.parse_routing_table(drafts.parent / "pilot-routing.md")
    assert routing["1"]["mailboxes"] == ["warm@warmdomain.co"]


# --- find_piece_attributed_sections + validate --------------------------------

def _findings(drafts: Path, body: str) -> list[dict]:
    f = drafts / "note.md"
    f.write_text(body, encoding="utf-8")
    return vpr.validate(f)


def test_inline_lowercase_attribution_cross_wire(tmp_path):
    # The 2026-05-30 incident shape: mid-sentence, lowercase, before any
    # strong marker. Piece-2 mailbox attributed to piece 1 must flag.
    drafts = _client_tree(tmp_path)
    findings = _findings(
        drafts, "Good news on piece 1: cold@colddomain.co is reconnected.\n"
    )
    assert any(f["category"] == "piece-routing-cross-wire" for f in findings)
    assert all(f["severity"] == "HIGH" for f in findings)


def test_inline_scope_stays_in_its_paragraph(tmp_path):
    # A passing "piece 1" mention must NOT claim later paragraphs; the
    # correctly-attributed piece-2 mailbox in the next paragraph is clean.
    drafts = _client_tree(tmp_path)
    findings = _findings(
        drafts,
        "A quick note about piece 1 today.\n\n"
        "Separately, cold@colddomain.co (piece 2's mailbox) is fine.\n",
    )
    assert findings == []


def test_bold_section_still_detects_cross_wire(tmp_path):
    drafts = _client_tree(tmp_path)
    findings = _findings(
        drafts, "**Piece 1 (warm)**\ncold@colddomain.co reconnected.\n"
    )
    assert any(f["category"] == "piece-routing-cross-wire" for f in findings)


def test_inline_mention_does_not_truncate_strong_section(tmp_path):
    # An inline "piece 1" inside a **Piece 1** section must not un-attribute
    # the text between the mention and the end of the section.
    drafts = _client_tree(tmp_path)
    findings = _findings(
        drafts,
        "**Piece 1 (warm)**\n"
        "Everything within piece 1 is on track today.\n"
        "Also cold@colddomain.co was reconnected.\n",
    )
    assert any(f["category"] == "piece-routing-cross-wire" for f in findings)


def test_clean_draft_stays_clean(tmp_path):
    drafts = _client_tree(tmp_path)
    findings = _findings(
        drafts, "**Piece 1 (warm)**\nwarm@warmdomain.co is reconnected.\n"
    )
    assert findings == []
