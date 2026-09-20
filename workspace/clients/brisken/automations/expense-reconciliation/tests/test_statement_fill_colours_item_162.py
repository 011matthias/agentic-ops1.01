"""Item 162: the reader sees every colour, and infers nothing from the new ones.

Owner directive 2026-09-20: "dont attribute colors in the statements or
receipts any deeper meaning, all i need you to be able to do, is get the
classifier to read all these colors and more."

Before this, the reader understood two colour families and everything else
was indistinguishable from an uncoloured cell. Measured in-machine on the
live workbooks that morning, read-only: of 452 filled cells across July and
August 2026, 174 (88 blue, 85 orange, 1 green) were invisible to it, every
one of them a THIRD annotation channel in the `Card` column beside the
yellow `Amount` and the gray `Description`.

So there are two separable questions, and these tests hold them apart:

* what colour IS this cell  -> `colour_family`, total over the RGB cube
* what does the tool DO about it -> `_FAMILY_ENTRY_STATUS`, still exactly
  two families, still exactly the two marks from the 2026-07-15 walkthrough

`test_no_live_verdict_moves` is the contract that makes the widening safe:
the family map reproduces the pre-item verdict on every colour either live
month contains. The hex tables below are the census of those months, so the
next shade Criss reaches for is a one-line addition here rather than a
re-derivation.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from openpyxl.styles.colors import Color

from expense_recon.ingest.statement_xlsx import (
    _classify_rgb,
    _fill_rgb,
    colour_family,
    parse_statement_xlsx_tolerant,
)
from expense_recon.matching.types import CellFill, MatchOutcome, Transaction
from expense_recon.web.app import create_app
from expense_recon.web.serialize import (
    snapshot_from_dict,
    snapshot_to_dict,
    transaction_from_dict,
    transaction_to_dict,
)
from expense_recon.web.store import RunStore

COLUMN_MAP = {
    "transaction_date": "Date",
    "amount": "Amount",
    "vendor": "Description",
    "card_last4": "Card",
}

# Every fill present in the two live workbooks on 2026-09-20, measured
# in-machine over /data/runs/*/*.xlsx, with the cell count it carried.
# July: 118 FFFF00, 68 D9D9D9, 48 F4B183, 45 B4C7E7, 27 ADADAD, 1 C9C9C9,
# 1 FFFFCC, 1 C6DEB5.  August: 43 B4C7E7, 40 ADADAD, 37 F4B183, 16 D9D9D9,
# 7 FFFF00.
LIVE_FILLS = [
    ("FFFF00", "yellow", "posted"),        # the "already in Zoho" mark
    ("FFFFCC", "yellow", "posted"),        # a paler one, same meaning
    ("D9D9D9", "gray", "subscription"),    # the subscription mark
    ("ADADAD", "gray", "subscription"),    # darker, in the Card column
    ("C9C9C9", "gray", "subscription"),
    ("F4B183", "orange", None),            # SEEN from item 162, means nothing
    ("B4C7E7", "blue", None),              # ditto (also the header row)
    ("C6DEB5", "green", None),             # ditto, one cell in July's Memo
]

# The pre-item-162 table from `test_entry_status.py`, restated as families.
# These verdicts are the ones that must not move; the family column is the
# new half. FFC000 and FFE699 are the same theme colour two tints apart,
# which is why saturation and not hue is what separates gold from a pale
# yellow highlight.
PINNED_FAMILIES = [
    ("FFFF00", "yellow", "posted"),
    ("FFFF99", "yellow", "posted"),
    ("FFE699", "yellow", "posted"),
    ("FFEB9C", "yellow", "posted"),
    ("D9D9D9", "gray", "subscription"),
    ("BFBFBF", "gray", "subscription"),
    ("808080", "gray", "subscription"),
    ("FFFFFF", "white", None),
    ("000000", "black", None),
    ("FFC000", "orange", None),
    ("C6EFCE", "green", None),
]

# Shades neither month has used yet, mostly from the standard Excel
# palette Criss picks from. The point of the hue bands is that these land
# somewhere stable instead of falling off a hand-tuned inequality; none of
# them acquires a verdict by being named.
#
# The families are a COARSE grouping and the hex beside them is the exact
# truth, which is why two entries here may read surprisingly: FFC7CE is the
# fill of Excel's "Bad" cell style, which Excel itself calls light red and
# which sits at hue 352, so `red` is its name here and `pink` is reserved
# for the magenta-leaning hues (290-330). 00B0F0 is Excel's "light blue" at
# hue 196, a blue rather than a cyan; `cyan` holds the genuinely cyan hues
# around 180. Both are named the same way every time, which is the property
# the SPA needs; the swatch it renders comes from the hex, not the name.
UNSEEN_SHADES = [
    ("FF0000", "red"),       # standard red
    ("C00000", "red"),       # dark red
    ("FFC7CE", "red"),       # the "Bad" style: Excel's own "light red"
    ("ED7D31", "orange"),    # theme 5 untinted
    ("A9D08E", "green"),
    ("00B050", "green"),
    ("00FFFF", "cyan"),      # a genuine cyan, hue 180
    ("00B0F0", "blue"),      # Excel "light blue", hue 196
    ("4472C4", "blue"),      # theme 4 untinted
    ("8EA9DB", "blue"),
    ("7030A0", "purple"),
    ("CC99FF", "purple"),
    ("FF00FF", "pink"),      # magenta, hue 300
    ("808000", "olive"),     # a dark yellow is not a highlighter
    ("404040", "black"),
    ("F2F2F2", "white"),
]


def _rgb(hex_rgb: str) -> tuple[int, int, int]:
    return (int(hex_rgb[0:2], 16), int(hex_rgb[2:4], 16), int(hex_rgb[4:6], 16))


# ── the two questions, held apart ────────────────────────────────────


@pytest.mark.parametrize(("hex_rgb", "family", "verdict"), LIVE_FILLS)
def test_every_live_fill_is_named(hex_rgb, family, verdict):
    assert colour_family(*_rgb(hex_rgb)) == family


@pytest.mark.parametrize(("hex_rgb", "family", "verdict"), LIVE_FILLS)
def test_no_live_verdict_moves(hex_rgb, family, verdict):
    """The whole safety argument for the widening, in one line per shade."""
    assert _classify_rgb(*_rgb(hex_rgb)) == verdict


@pytest.mark.parametrize(("hex_rgb", "family", "verdict"), PINNED_FAMILIES)
def test_the_pre_item_table_keeps_its_verdicts(hex_rgb, family, verdict):
    assert _classify_rgb(*_rgb(hex_rgb)) == verdict
    assert colour_family(*_rgb(hex_rgb)) == family


@pytest.mark.parametrize(("hex_rgb", "family"), UNSEEN_SHADES)
def test_unseen_shades_get_a_name_and_no_meaning(hex_rgb, family):
    assert colour_family(*_rgb(hex_rgb)) == family
    assert _classify_rgb(*_rgb(hex_rgb)) is None


def test_only_yellow_and_gray_ever_carry_a_verdict():
    """The directive, as a property over the whole RGB cube rather than a
    list of examples: no third family can acquire a meaning by accident."""
    seen: dict[str, set] = {}
    for r in range(0, 256, 7):
        for g in range(0, 256, 7):
            for b in range(0, 256, 7):
                seen.setdefault(colour_family(r, g, b), set()).add(
                    _classify_rgb(r, g, b)
                )
    assert seen["yellow"] == {"posted"}
    assert seen["gray"] == {"subscription"}
    assert set(seen) - {"yellow", "gray"}, "the sweep must reach other families"
    for family, verdicts in seen.items():
        if family in ("yellow", "gray"):
            continue
        assert verdicts == {None}, f"{family} acquired a verdict: {verdicts}"


def test_colour_family_is_total():
    """Every readable fill gets a name. `None` now means 'no fill', which is
    the distinction the item exists to draw."""
    for r in range(0, 256, 11):
        for g in range(0, 256, 11):
            for b in range(0, 256, 11):
                assert isinstance(colour_family(r, g, b), str)


# ── the parser records what it saw ───────────────────────────────────


def _fill(hex_rgb: str) -> PatternFill:
    return PatternFill(start_color="FF" + hex_rgb, end_color="FF" + hex_rgb,
                       fill_type="solid")


def _theme_fill(theme: int, tint: float) -> PatternFill:
    """A THEME fill, which is what both live workbooks actually use: July's
    orange is theme 5 tint 0.4, its blue theme 4 tint 0.6, its light gray
    theme 0 tint -0.15. A fixture built only from rgb fills would exercise a
    path the live data never takes."""
    fill = PatternFill(fill_type="solid")
    fill.fgColor = Color(theme=theme, tint=tint)
    return fill


def _workbook(path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["Card", "Date", "Amount", "Description", "Memo"])
    ws.append(["2838", "2026-07-01", "10.00", "ORANGE CARD", "n"])
    ws.append(["3645", "2026-07-02", "20.00", "POSTED", "n"])
    ws.append(["3645", "2026-07-03", "30.00", "SUBSCRIPTION", "n"])
    ws.append(["3645", "2026-07-04", "40.00", "PLAIN", "n"])
    ws.append(["2838", "2026-07-05", "50.00", "BLUE CARD", "n"])
    # row 2: orange in the mapped Card column (a THEME fill, as live)
    ws.cell(row=2, column=1).fill = _theme_fill(5, 0.4)      # -> F4B183
    # row 3: yellow in the mapped Amount column + green in UNMAPPED Memo
    ws.cell(row=3, column=3).fill = _fill("FFFF00")
    ws.cell(row=3, column=5).fill = _fill("C6DEB5")
    # row 4: gray in the mapped Description column
    ws.cell(row=4, column=4).fill = _fill("D9D9D9")
    # row 5: nothing at all
    # row 6: blue in the mapped Card column (theme, as live)
    ws.cell(row=6, column=1).fill = _theme_fill(4, 0.6)      # -> B4C7E7
    wb.save(path)


@pytest.fixture
def parsed(tmp_path):
    path = tmp_path / "colours.xlsx"
    _workbook(path)
    txs, issues = parse_statement_xlsx_tolerant(
        path, COLUMN_MAP, "card-1", "le", "USD"
    )
    assert [i for i in issues if i.severity == "error"] == []
    return {t.vendor_from_statement: t for t in txs}


def test_the_theme_path_is_the_one_under_test(tmp_path):
    """Instrument check. `_fill_rgb` returns None for a theme slot it does
    not know, so a theme fixture can silently test nothing while passing.
    Assert the two theme cells resolved to the live hexes before believing
    any assertion that rests on them."""
    path = tmp_path / "colours.xlsx"
    _workbook(path)
    from openpyxl import load_workbook

    ws = load_workbook(path).active
    orange, blue = ws.cell(row=2, column=1), ws.cell(row=6, column=1)
    assert orange.fill.fgColor.type == "theme"
    assert blue.fill.fgColor.type == "theme"
    assert _fill_rgb(orange.fill) == _rgb("F4B183")
    assert _fill_rgb(blue.fill) == _rgb("B4C7E7")


def test_an_unreadable_colour_is_now_distinguishable_from_no_colour(parsed):
    """The actual defect. Both used to be nothing on the row."""
    orange, plain = parsed["ORANGE CARD"], parsed["PLAIN"]
    assert orange.entry_status is None and plain.entry_status is None
    assert [f.family for f in orange.fills] == ["orange"]
    assert plain.fills == ()


def test_a_named_colour_still_votes_on_nothing(parsed):
    for vendor in ("ORANGE CARD", "BLUE CARD"):
        tx = parsed[vendor]
        assert tx.fills, f"{vendor} must record its fill"
        assert tx.entry_status is None, f"{vendor} must not acquire a verdict"


def test_the_two_marks_are_unchanged(parsed):
    assert parsed["POSTED"].entry_status == "posted"
    assert parsed["SUBSCRIPTION"].entry_status == "subscription"


def test_fills_carry_the_column_and_the_hex(parsed):
    assert parsed["ORANGE CARD"].fills == (
        CellFill(column="Card", index=0, hex="F4B183", family="orange"),
    )
    assert parsed["BLUE CARD"].fills == (
        CellFill(column="Card", index=0, hex="B4C7E7", family="blue"),
    )


def test_an_unmapped_column_is_recorded_but_does_not_vote(parsed):
    """July's `Memo` column carries a gray and a green the mapped-column
    scan never reached. Seeing is not voting: the green is on the row, and
    the verdict still comes from the yellow `Amount` cell alone."""
    posted = parsed["POSTED"]
    assert [(f.column, f.family) for f in posted.fills] == [
        ("Amount", "yellow"), ("Memo", "green"),
    ]
    assert posted.entry_status == "posted"


def test_fills_read_left_to_right(parsed):
    for tx in parsed.values():
        assert [f.index for f in tx.fills] == sorted(f.index for f in tx.fills)


# ── it survives the snapshot, and reaches the payload ────────────────


def test_fills_survive_the_snapshot_round_trip(parsed):
    tx = parsed["POSTED"]
    back = transaction_from_dict(transaction_to_dict(tx))
    assert back.fills == tx.fills


def test_a_snapshot_written_before_the_item_still_loads(parsed):
    """Every month already in the store has no `fills` key. It must load,
    and read as 'not recorded' rather than exploding or claiming the sheet
    was uncoloured in a way the payload would show."""
    payload = transaction_to_dict(parsed["POSTED"])
    payload.pop("fills")
    assert transaction_from_dict(payload).fills == ()


def _tx(tid, vendor, amount, **kw) -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="chase",
        transaction_date=date(2026, 7, 1), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor,
        card_last4="2838", **kw,
    )


@pytest.fixture
def view(tmp_path) -> dict:
    charges = [
        _tx("t_orange", "ORANGE CARD", "10.00",
            fills=(CellFill(column="Card", index=0, hex="F4B183",
                            family="orange"),)),
        _tx("t_posted", "POSTED", "20.00", entry_status="posted",
            fills=(CellFill(column="Amount", index=2, hex="FFFF00",
                            family="yellow"),
                   CellFill(column="Memo", index=4, hex="C6DEB5",
                            family="green"))),
        _tx("t_plain", "PLAIN", "30.00"),
    ]
    snapshot = snapshot_to_dict(
        charges, [],
        MatchOutcome(matches=[],
                     unmatched_transactions=[c.transaction_id for c in charges],
                     unmatched_receipts=[]),
        [],
    )
    with TestClient(create_app(tmp_path)) as client:
        db = RunStore(tmp_path / "recon-web.sqlite")
        db.create_run(
            run_id="run162", created_at="2026-07-02T00:00:00",
            label="July 2026", operator=None, summary={}, snapshot=snapshot,
            config={}, work_dir=str(tmp_path), llm_enabled=False,
            has_coa=False,
        )
        db.close()
        resp = client.get("/api/runs/run162")
        assert resp.status_code == 200, resp.text
        return resp.json()


def test_the_route_carries_fills_onto_the_row(view):
    """Route-level, through `GET /api/runs/{id}` — the caller the change
    wired, not the helper it added."""
    rows = {r["transaction_id"]: r for r in view["rows"]}
    assert rows["t_orange"]["fills"] == [
        {"column": "Card", "index": 0, "hex": "F4B183", "family": "orange"},
    ]
    assert rows["t_posted"]["fills"] == [
        {"column": "Amount", "index": 2, "hex": "FFFF00", "family": "yellow"},
        {"column": "Memo", "index": 4, "hex": "C6DEB5", "family": "green"},
    ]


def test_fills_is_absent_not_null_on_an_uncoloured_row(view):
    """Parallel-field contract rule 1: absent, never null."""
    rows = {r["transaction_id"]: r for r in view["rows"]}
    assert "fills" not in rows["t_plain"]


def test_the_payload_states_no_meaning_for_the_new_families(view):
    """A named colour reaches the reviewer WITHOUT a verdict attached, which
    is the directive: the tool sees, the reviewer interprets."""
    rows = {r["transaction_id"]: r for r in view["rows"]}
    assert rows["t_orange"]["entry_status"] is None
    assert rows["t_posted"]["entry_status"] == "posted"


def test_snapshot_round_trip_through_the_matching_layer(parsed):
    txs = list(parsed.values())
    snap = snapshot_to_dict(txs, [], MatchOutcome(
        matches=[], unmatched_transactions=[t.transaction_id for t in txs],
        unmatched_receipts=[]), [])
    back, _, _, _ = snapshot_from_dict(snap)
    assert [t.fills for t in back] == [t.fills for t in txs]
