"""The month's expense report: an organized listing, then every receipt.

Named `month_report_pdf`, not `expense_report_pdf`, because
`ingest/expense_report_pdf.py` already parses Zoho's own expense-report PDFs
on the way IN. One basename for both directions is a trap; this module only
writes.

Owner directive 2026-08-23: the output is no longer an import file for an
accounting system, because there is no longer a system to import it into. It
is a document a human reads and an auditor accepts — "an expense report like
in Zoho with an organized listing, then all the receipts".

So the report is one PDF:

1. a header block (month, entity or entities, totals per currency, count),
2. the listing, one line per exported expense, each numbered, and
3. every receipt, appended in listing order behind a caption that names the
   expense number it proves.

The listing is built from `build_expense_rows` — the SAME rows the CSV
export writes — so the document and the export cannot disagree about money.
Receipts are appended as delivered: an image becomes one page, a PDF receipt
keeps its own pages, and an expense with no receipt is stated as such rather
than silently skipped.

Text-layer output (reportlab), not a rendering: the listing stays selectable,
searchable, and small. Unicode comes from a real TTF — reportlab's built-in
Helvetica is Latin-1 only, which would mangle "Cartão" and "Gebühr" exactly
where this client's receipts live.
"""
from __future__ import annotations

import io
from collections.abc import Sequence

from ._pdf_common import (
    esc as _esc,
    make_styles,
    prepare_evidence,
    register_fonts,
    stitch,
    table_style,
)

# The listing columns, in reading order. Deliberately NOT every export
# column: a reader wants to see what was bought, by whom, for how much, and
# which receipt proves it. The full field set stays in the CSV.
_LISTING = (
    ("#", 26),
    ("Date", 62),
    ("Vendor", 132),
    ("Account", 150),
    ("Entity", 92),
    ("Paid through", 108),
    ("Amount", 74),
    ("Ccy", 34),
    ("Receipt", 54),
)


def build_expense_report_pdf(
    rows: Sequence[Sequence[str]],
    columns: Sequence[str],
    *,
    title: str,
    subtitle: str = "",
    evidence: Sequence[dict] | None = None,
    prepared_note: str = "",
) -> bytes:
    """Render the month's report: listing first, then the receipts.

    `rows` are export rows in `columns` order (pass `build_expense_rows`
    output and `EXPENSE_COLUMNS`), so the document quotes the export rather
    than recomputing it.

    `evidence` is one entry per RECEIPT DOCUMENT, in listing order:

        {"rows": [3, 4], "label": "Trenitalia",
         "detail": "2026-08-01 · 42.50 EUR", "name": "tren.png",
         "data": b"..."}       # `data`/`name` absent = no document

    Per document, not per row, because a receipt that books to two accounts
    writes TWO listing rows and must still appear once — its caption names
    both expense numbers. An expense with no document keeps its caption and
    says so; nothing is silently dropped.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
    )

    body_font, bold_font = register_fonts()
    idx = {name: i for i, name in enumerate(columns)}

    def cell(row: Sequence[str], name: str) -> str:
        i = idx.get(name)
        return str(row[i]) if i is not None and i < len(row) else ""

    styles = make_styles(body_font, bold_font)

    # ── totals, computed from the rows the export writes ────────────
    totals: dict[str, float] = {}
    for row in rows:
        ccy = cell(row, "Currency Code") or "?"
        try:
            totals[ccy] = totals.get(ccy, 0.0) + float(
                (cell(row, "Expense Amount") or "0").replace(",", "")
            )
        except ValueError:
            continue
    totals_line = "  ·  ".join(
        f"{ccy} {amount:,.2f}" for ccy, amount in sorted(totals.items())
    ) or "no expenses"

    story: list = [
        Paragraph(_esc(title), styles["title"]),
        Paragraph(
            _esc(subtitle or f"{len(rows)} expenses  ·  {totals_line}"),
            styles["sub"],
        ),
    ]
    if subtitle:
        story.append(Paragraph(
            _esc(f"{len(rows)} expenses  ·  {totals_line}"), styles["sub"]
        ))

    # Which listing rows actually have a document behind them. The column
    # cannot promise a PAGE number (the captions are laid out after this
    # table is built), so it states the one thing it knows for certain.
    documented: set[int] = set()
    for item in (evidence or []):
        if item.get("data"):
            documented.update(int(n) for n in item.get("rows") or [])

    head = [Paragraph(_esc(name), styles["cellhead"]) for name, _w in _LISTING]
    table_rows: list[list] = [head]
    for n, row in enumerate(rows, start=1):
        table_rows.append([
            Paragraph(str(n), styles["cell"]),
            Paragraph(_esc(cell(row, "Expense Date")), styles["cell"]),
            Paragraph(_esc(cell(row, "Vendor")), styles["cell"]),
            Paragraph(_esc(cell(row, "Expense Account")), styles["cell"]),
            Paragraph(_esc(cell(row, "Legal Entity")), styles["cell"]),
            Paragraph(_esc(cell(row, "Paid Through")), styles["cell"]),
            Paragraph(_esc(cell(row, "Expense Amount")), styles["cellr"]),
            Paragraph(_esc(cell(row, "Currency Code")), styles["cell"]),
            Paragraph("attached" if n in documented else "none", styles["cell"]),
        ])
    table = Table(
        table_rows,
        colWidths=[w for _name, w in _LISTING],
        repeatRows=1,
    )
    table.setStyle(table_style())
    story.append(table)
    if prepared_note:
        story.append(Spacer(1, 8))
        story.append(Paragraph(_esc(prepared_note), styles["sub"]))

    # ── caption pages: one per document, its pages appended behind ─────
    # Renderability is decided BEFORE the caption is written, so a file that
    # exists but cannot be turned into pages says so on its caption instead
    # of leaving a caption with nothing behind it (which reads as "the
    # receipt is here" to anyone flipping through).
    items = list(evidence or [])
    prepared = prepare_evidence(items)

    for item, pdf_bytes in prepared:
        story.append(PageBreak())
        numbers = [int(n) for n in item.get("rows") or []]
        if len(numbers) > 1:
            which = "Expenses " + ", ".join(str(n) for n in numbers)
        elif numbers:
            which = f"Expense {numbers[0]}"
        else:
            which = "Expense"
        label = str(item.get("label") or "(no vendor)")
        story.append(Paragraph(_esc(f"{which} · {label}"), styles["caption"]))
        if item.get("detail"):
            story.append(Paragraph(_esc(str(item["detail"])), styles["capsub"]))
        story.append(Spacer(1, 6))
        name = str(item.get("name") or "")
        if pdf_bytes is not None:
            story.append(Paragraph(_esc(name), styles["capsub"]))
        elif item.get("data"):
            story.append(Paragraph(
                _esc(f"{name}: this file could not be rendered into the "
                     f"report; open it in the app."),
                styles["capsub"],
            ))
        else:
            story.append(Paragraph(
                "No receipt document for this expense.", styles["capsub"]
            ))

    buf = io.BytesIO()
    SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=title,
    ).build(story)

    # ── stitch: listing + (caption page, receipt pages) per expense ──
    return stitch(buf.getvalue(), prepared)
