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

A company month is reconciled card by card, so its listing is sectioned per
card (item 138, owner 2026-09-17: "the PDFs are not organized by the cards
that were reconciled"): each card gets its caption, a line saying what its
statement settled, its table and sums, and then that card's receipt pages,
before the next card starts. Anything that belongs to no card section (the
reimbursements owed, a copy whose original is gone) keeps its pages at the
end. Trip and cost-center sections keep every receipt at the end, as before.

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
    UNREADABLE_CAPTION,
    caption_mark,
    esc as _esc,
    excluded_note,
    format_totals,
    make_styles,
    prepare_evidence,
    register_fonts,
    stitch,
    sum_amounts,
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
    reimbursements: Sequence[dict] | None = None,
    sections: Sequence[dict] | None = None,
    sections_heading: str = "",
    sections_note: str = "",
    copies_set_aside: Sequence[dict] | None = None,
    copies_set_aside_totals: dict[str, str] | None = None,
    receipts_by_section: bool = False,
    amounts_unreadable: Sequence[int] = (),
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

    `reimbursements` (backlog item 41) is the reimbursements-owed section:
    one entry per person, in section order —

        {"person": "Dirk", "rows": [{"n": 12, "date": "2026-08-02",
         "vendor": "Taxi", "amount": "18.00", "currency": "EUR"}],
         "totals": {"EUR": "18.00"}}

    — rendered between the listing and the receipts. Row numbers continue
    the listing's, so every receipt caption still names a unique number.

    `sections` (item 38, trip reports) partitions the LISTING per person:
    contiguous slices of `rows`, in order —

        {"person": "Dirk", "on_roster": True, "start": 1, "count": 3}

    — one table per section with its own caption and per-currency sums,
    numbering continuous across sections (`start` is the 1-based global
    row number of the slice's first row, and the slices cover `rows`
    exactly). Omitted => the single flat table, unchanged.

    A section may instead carry its own `caption` (the heading over its
    table) and `label` (the name in its sums line); item 47 partitions a
    company month per cost center this way:

        {"caption": "Lidar (project)", "label": "Lidar", "start": 1,
         "count": 3}

    `sections_heading` / `sections_note` render once above the first
    section: a heading for the partition and the standing note that
    qualifies its sums (for cost centers, the stated limit that this is
    card-and-receipt spend, not total project cost).

    Item 138 partitions a company month per card with the same `caption` /
    `label` shape plus two optional keys: `detail`, one line under the
    caption (what the card's statement settled, `card_statement_line`), and
    `notes`, lines under the sums (a receipt held on this card's charge
    whose own card is another). A section without them renders as before.

    `receipts_by_section` puts each section's receipt pages right behind
    that section's sums instead of after the whole document. An evidence
    entry belongs to the section holding its first row number; entries in
    no section (reimbursements, a copy whose original is not listed) keep
    their pages at the end. Off => every caption at the end, as before.

    `copies_set_aside` (item 94) is the documents the tool decided repeat a
    listed expense, already left out of `rows`:

        {"vendor": "Obsidian", "date": "2026-08-30", "amount": "96.00",
         "currency": "USD", "rows": [5]}

    — stated under the listing with `copies_set_aside_totals` (per currency,
    preformatted), one line each naming the expense it repeats. Their
    evidence entries carry `"copy": True` and the original's `rows`, and
    are captioned as the copy. Omitted => nothing printed, as before.

    `amounts_unreadable` (item 97) is the listing numbers of the rows written
    for a receipt whose total was never read. Their Amount cell is blank,
    which a total reads as zero, so the caller names them: each gets the
    "amount unreadable, not in total" caption and a place in the footer,
    the same as a cell that would not parse.
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
    # In Decimal, because the amounts are strings for exactly that reason
    # (item 65; section 12 row 13). `unreadable` is the listing numbers of
    # the rows whose amount would not parse: each one gets a caption on its
    # own row below and a line in the footer, rather than being dropped
    # from the total with nothing on the page saying so.
    totals, unreadable = sum_amounts(
        (n, cell(row, "Currency Code"), cell(row, "Expense Amount"))
        for n, row in enumerate(rows, start=1)
    )
    unreadable = sorted(set(unreadable) | {
        int(n) for n in amounts_unreadable if 1 <= int(n) <= len(rows)
    })
    unreadable_rows = set(unreadable)
    totals_text = format_totals(totals, "no expenses")

    story: list = [
        Paragraph(_esc(title), styles["title"]),
        Paragraph(
            _esc(subtitle or f"{len(rows)} expenses  ·  {totals_text}"),
            styles["sub"],
        ),
    ]
    if subtitle:
        story.append(Paragraph(
            _esc(f"{len(rows)} expenses  ·  {totals_text}"), styles["sub"]
        ))

    # Renderability is decided HERE, before a single row is drawn, because
    # the Receipt column below is an answer to "is the receipt in this
    # report" and that question cannot be answered by the presence of a
    # file (item 68). A password-protected PDF or a truncated image is a
    # file that exists and a page that never appears, and the column used
    # to call it "attached" while the caption page thirty pages later said
    # the file could not be rendered. The caption pages were right.
    items = list(evidence or [])
    prepared = prepare_evidence(items)

    # Which listing rows actually have a page behind them. The column
    # cannot promise a PAGE number (the captions are laid out after this
    # table is built), so it states the one thing it now knows for certain.
    documented: set[int] = set()
    for item, pdf_bytes in prepared:
        if pdf_bytes is None or item.get("copy"):
            # A copy's pages prove nothing about its original's (item 94).
            continue
        documented.update(int(n) for n in item.get("rows") or [])

    head = [Paragraph(_esc(name), styles["cellhead"]) for name, _w in _LISTING]

    def _listing_row(n: int, row: Sequence[str]) -> list:
        # An amount the total could not read says so on its own row, so a
        # reader adding the column up by hand finds the gap where it is
        # rather than a total that is quietly short (item 65).
        amount = _esc(cell(row, "Expense Amount"))
        if n in unreadable_rows:
            amount += f'<br/><font size="6">{_esc(UNREADABLE_CAPTION)}</font>'
        return [
            Paragraph(str(n), styles["cell"]),
            Paragraph(_esc(cell(row, "Expense Date")), styles["cell"]),
            Paragraph(_esc(cell(row, "Vendor")), styles["cell"]),
            Paragraph(_esc(cell(row, "Expense Account")), styles["cell"]),
            Paragraph(_esc(cell(row, "Legal Entity")), styles["cell"]),
            Paragraph(_esc(cell(row, "Paid Through")), styles["cell"]),
            Paragraph(amount, styles["cellr"]),
            Paragraph(_esc(cell(row, "Currency Code")), styles["cell"]),
            Paragraph("attached" if n in documented else "none", styles["cell"]),
        ]

    def _listing_table(numbered: list[tuple[int, Sequence[str]]]):
        t = Table(
            [head] + [_listing_row(n, row) for n, row in numbered],
            colWidths=[w for _name, w in _LISTING],
            repeatRows=1,
        )
        t.setStyle(table_style())
        return t

    # Item 138: which page each evidence caption landed on, one list per
    # entry in `prepared` order, filled by `caption_mark` during the build.
    # Only read when captions sit inside the document.
    marks: list[list[int]] = [[] for _ in prepared]
    placed: set[int] = set()
    # A caption must own its page: set after a section's last caption, so
    # whatever comes next starts on a fresh page instead of sharing it.
    pending_break = False

    def _caption(i: int) -> None:
        # Its own PageBreak opens the page, so a pending one is spent here
        # rather than stacked into an empty page.
        nonlocal pending_break
        pending_break = False
        item, pdf_bytes = prepared[i]
        placed.add(i)
        story.append(PageBreak())
        if receipts_by_section:
            story.append(caption_mark(marks[i]))
        numbers = [int(n) for n in item.get("rows") or []]
        if len(numbers) > 1:
            which = "Expenses " + ", ".join(str(n) for n in numbers)
        elif numbers:
            which = f"Expense {numbers[0]}"
        else:
            # Item 97: a receipt with no listing row is not given a number
            # it does not have; its detail line says why.
            which = "Receipt"
        if item.get("copy"):
            # Item 94: the pages of a copy set aside, behind its original.
            which += " (copy set aside)"
        label = str(item.get("label") or "(no vendor)")
        story.append(Paragraph(_esc(f"{which} · {label}"), styles["caption"]))
        if item.get("detail"):
            story.append(Paragraph(_esc(str(item["detail"])), styles["capsub"]))
        story.append(Spacer(1, 6))
        name = str(item.get("name") or "")
        # `render_note` is what `prepare_evidence` found: the reason a file
        # produced no pages, or (on a file that did) the part of it that was
        # left out. Naming it here is the whole point of the caption for a
        # blocked file: the reviewer has to be able to find the file without
        # reading a log, and the report itself is the only place they look.
        note = str(item.get("render_note") or "")
        if pdf_bytes is not None:
            story.append(Paragraph(
                _esc(f"{name}: {note}" if note else name), styles["capsub"]
            ))
        elif item.get("data"):
            why = note or "this file could not be rendered into the report"
            story.append(Paragraph(
                _esc(f"{name}: {why}; open it in the app."),
                styles["capsub"],
            ))
        else:
            story.append(Paragraph(
                "No receipt document for this expense.", styles["capsub"]
            ))

    def _flow(*flowables) -> None:
        # Content after a section's captions opens a new page first.
        nonlocal pending_break
        if pending_break:
            story.append(PageBreak())
            pending_break = False
        story.extend(flowables)

    if sections:
        # Sectioned listing: one table per section, numbering continuous,
        # per-section sums beneath each; the reimbursements block's shape,
        # applied to the listing itself. A trip sections per person
        # (item 38: `person` / `on_roster`); a company month sections per
        # cost center (item 47: `caption` / `label`) or, when no cost
        # center applies, per card (item 138: `caption` / `label` /
        # `detail` / `notes`, receipts behind each section).
        if sections_heading:
            story.append(Spacer(1, 12))
            story.append(Paragraph(_esc(sections_heading), styles["caption"]))
        if sections_note:
            story.append(Paragraph(_esc(sections_note), styles["capsub"]))
        for sec in sections:
            if sec.get("caption"):
                caption = str(sec["caption"])
                label = str(sec.get("label") or caption)
            else:
                label = str(sec.get("person") or "(person not named)")
                caption = label
                if sec.get("on_roster") is False:
                    caption += "  (not on the trip roster)"
            start = int(sec.get("start") or 1)
            count = int(sec.get("count") or 0)
            numbered = [
                (start + i, rows[start - 1 + i]) for i in range(count)
                if 0 <= start - 1 + i < len(rows)
            ]
            _flow(Spacer(1, 10), Paragraph(_esc(caption), styles["caption"]))
            if sec.get("detail"):
                story.append(Paragraph(_esc(str(sec["detail"])), styles["capsub"]))
            story.append(_listing_table(numbered))
            # Same Decimal sum as the header total, over this slice only,
            # so a per-person line and the month's line cannot disagree.
            sec_totals, _sec_unreadable = sum_amounts(
                (n, cell(row, "Currency Code"), cell(row, "Expense Amount"))
                for n, row in numbered
            )
            sec_line = format_totals(sec_totals, "no amounts read")
            story.append(Paragraph(
                _esc(f"{label}: {len(numbered)} "
                     f"expense{'s' if len(numbered) != 1 else ''}"
                     f"  ·  {sec_line}"),
                styles["sub"],
            ))
            for line in sec.get("notes") or []:
                story.append(Paragraph(_esc(str(line)), styles["capsub"]))
            if receipts_by_section:
                # This section's receipts, before the next section starts.
                in_section = set(range(start, start + len(numbered)))
                for i, (item, _pdf) in enumerate(prepared):
                    first = next(iter(item.get("rows") or []), None)
                    if i in placed or first is None or int(first) not in in_section:
                        continue
                    _caption(i)
                    pending_break = True
    else:
        story.append(_listing_table(list(enumerate(rows, start=1))))

    # The footer half of item 65: the rows the total left out, counted and
    # named. Silent when every amount read.
    excluded = excluded_note(unreadable)
    if excluded:
        _flow(Paragraph(_esc(excluded), styles["sub"]))

    # ── copies set aside (item 94): named, summed, never in the total ──
    if copies_set_aside:
        n_copies = len(copies_set_aside)
        owed = "  ·  ".join(
            f"{ccy} {amount}"
            for ccy, amount in sorted((copies_set_aside_totals or {}).items())
        ) or "no amounts read"
        _flow(Spacer(1, 8))
        story.append(Paragraph(
            _esc(
                f"Copies set aside: {n_copies} "
                f"{'document repeats' if n_copies == 1 else 'documents repeat'}"
                f" an expense listed above, not counted in the listing or "
                f"the totals ({owed}). "
                f"{'Its pages follow' if n_copies == 1 else 'Their pages follow'}"
                f" the original's."
            ),
            styles["sub"],
        ))
        for entry in copies_set_aside:
            numbers = [int(n) for n in entry.get("rows") or []]
            of = (
                "copy of expense " + ", ".join(str(n) for n in numbers)
                if numbers else "copy"
            )
            story.append(Paragraph(
                _esc("  ·  ".join(x for x in (
                    str(entry.get("vendor") or "(no vendor)"),
                    str(entry.get("date") or ""),
                    " ".join(x for x in (
                        str(entry.get("currency") or ""),
                        str(entry.get("amount") or ""),
                    ) if x),
                    of,
                ) if x)),
                styles["capsub"],
            ))

    # ── reimbursements owed (item 41): per person, with sums ────────
    if reimbursements:
        _flow(Spacer(1, 12))
        story.append(Paragraph("Reimbursements owed", styles["caption"]))
        story.append(Paragraph(
            "Private expenses confirmed by the reviewer: paid out of "
            "pocket, owed back to the person named. Not part of the "
            "company listing above.",
            styles["capsub"],
        ))
        r_head = [
            Paragraph(_esc(name), styles["cellhead"])
            for name in ("#", "Date", "Vendor", "Amount", "Ccy")
        ]
        for group in reimbursements:
            person = str(group.get("person") or "(person not named)")
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                _esc(f"Reimburse {person}"), styles["caption"]
            ))
            g_rows: list[list] = [r_head]
            for row in group.get("rows") or []:
                g_rows.append([
                    Paragraph(_esc(str(row.get("n", ""))), styles["cell"]),
                    Paragraph(_esc(str(row.get("date", ""))), styles["cell"]),
                    Paragraph(_esc(str(row.get("vendor", ""))), styles["cell"]),
                    Paragraph(_esc(str(row.get("amount", ""))), styles["cellr"]),
                    Paragraph(_esc(str(row.get("currency", ""))), styles["cell"]),
                ])
            g_table = Table(g_rows, colWidths=[26, 70, 240, 90, 40],
                            repeatRows=1)
            g_table.setStyle(table_style())
            story.append(g_table)
            # Already summed in Decimal by the caller and handed over
            # preformatted, one string per currency; renamed off `totals`
            # so it cannot shadow the listing's own sum above.
            owed = group.get("totals") or {}
            owed_line = "  ·  ".join(
                f"{ccy} {amount}" for ccy, amount in sorted(owed.items())
            ) or "no amounts read"
            story.append(Paragraph(
                _esc(f"Owed to {person}: {owed_line}"), styles["sub"]
            ))

    if prepared_note:
        _flow(Spacer(1, 8))
        story.append(Paragraph(_esc(prepared_note), styles["sub"]))

    # ── caption pages: one per document, its pages appended behind ─────
    # Renderability was decided ABOVE, before the listing was written, so a
    # file that exists but cannot be turned into pages says so on its
    # caption instead of leaving a caption with nothing behind it (which
    # reads as "the receipt is here" to anyone flipping through) — and the
    # Receipt column in the listing says the same thing.
    # With `receipts_by_section` the card sections already placed theirs;
    # what is left (reimbursements, a copy with no listed original) keeps
    # its pages at the end, which is every caption when the option is off.
    for i in range(len(prepared)):
        if i not in placed:
            _caption(i)

    buf = io.BytesIO()
    SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=title,
    ).build(story)

    # ── stitch: listing + (caption page, receipt pages) per expense ──
    if receipts_by_section:
        # One recorded page per caption, in `prepared` order. A caption
        # that recorded none shortens the list, and `stitch` then appends
        # every document at the end: out of place, never dropped.
        return stitch(
            buf.getvalue(), prepared,
            caption_pages=[m[0] for m in marks if m],
        )
    return stitch(buf.getvalue(), prepared)
