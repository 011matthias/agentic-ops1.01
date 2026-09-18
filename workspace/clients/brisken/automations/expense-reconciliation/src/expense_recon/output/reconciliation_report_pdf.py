"""The statement reconciliation as a document.

Owner directive 2026-08-23: the reconciliation output is not exported into
any application either, so the question is what actually serves the work.
The answer is not a CSV. A reconciliation's product is *evidence that a month
is complete and correct*: every statement charge accounted for, the ones that
are not called out by name, and the receipts that prove the rest. A CSV can
carry the first part and none of the others, and nothing reads it.

So the document is:

1. the header — the month, how many charges matched, what is still
   unreconciled per currency, and what is booked without a receipt,
2. **Per-card coverage**, when the month holds more than one card: which
   statements were loaded for each, over what span, and how far each one
   has got,
3. then **one section per card** (item 138, owner 2026-09-17: "the output
   (PDF) is also not organized in the different cards that were
   reconciled"), because a month is reconciled card by card: one statement,
   one pile of receipts. Each section states that card's statement and its
   figures, then what needs attention on that card (exceptions first,
   because they are the only part anyone must act on), then its charges
   with their receipts, then that card's receipt pages. A last section,
   never dropped, takes the charges no card claims and the receipts with no
   card.

A month with a single card and nothing outside it renders the one flat
document it always did: a heading restating the only card is structure the
content does not earn.

The XLSX stays the working sidecar (Criss works in Excel, and her fill-colour
is real data); the CSV stays available and demoted.
"""
from __future__ import annotations

import io
from collections.abc import Sequence

from ..unmatched_reasons import RECEIPT_REASON_SHORT
from ._pdf_common import (
    PAGE_MARGIN_MM,
    booked_without_receipt,
    caption_mark,
    card_name,
    card_sections,
    card_statement_line,
    esc,
    make_styles,
    prepare_evidence,
    register_fonts,
    stitch,
    table_style,
)

# Column widths in points. Every table fits `TABLE_WIDTH_MAX` (503.9 pt, the
# A4 portrait frame): until item 143 the charge table was 672 pt, so it ran
# off both sides of the paper and its `#`, Date and Account were cut off,
# and the coverage table (572 pt) sat in both margins. Counts, dates and
# amounts fit their values on one line in DejaVu Sans, the widest font
# `register_fonts` picks; the text columns wrap between words. The charge column keeps room
# for a statement descriptor with no space in it (WEB*NETWORKSOLUTIONS).
_COVERAGE = (
    ("Card", 90),
    ("Statements", 110),
    ("Period", 80),
    ("Charges", 46),
    ("Matched", 48),
    ("No receipt", 56),
    ("Unreconciled", 72),
)

_CHARGES = (
    ("#", 24),
    ("Date", 55),
    ("Charge", 118),
    ("Amount", 54),
    ("Ccy", 26),
    ("Status", 64),
    ("Receipt", 80),
    ("Account", 82),
)


def _status_label(row: dict) -> str:
    """One word for what a reader needs: is this charge settled, waiting, or
    deliberately set aside."""
    status = str(row.get("status") or "")
    bucket = str(row.get("effective_bucket") or "")
    if status == "confirmed":
        return "matched (confirmed)"
    if status == "rejected":
        return "rejected"
    if status == "already_posted":
        return "already posted"
    if row.get("chosen_document_id"):
        return "matched"
    if booked_without_receipt(row):
        # Item 96: Criss's yellow row is in her books, and the screen folds it
        # away as already booked. Only the reviewer's verdict reached this
        # word before, so 48 July rows printed "no receipt" as if still open.
        return "already posted"
    if bucket in ("unmatched", ""):
        return "no receipt"
    if bucket == "refund":
        # Item 73: the credit bucket holds card payments too; say which.
        return _CREDIT_STATUS.get(str(row.get("row_type") or ""), "refund")
    return bucket.replace("_", " ")


# Item 73: a credit line's status by its row type. A row built before row
# types existed has none and keeps the word it always printed.
_CREDIT_STATUS = {
    "payment": "card payment",
    "refund": "refund",
    "reversal": "reversal",
}


def build_reconciliation_report_pdf(
    view: dict,
    *,
    title: str,
    evidence: Sequence[dict] | None = None,
    receipt_cards: dict[str, tuple[str, str]] | None = None,
    card_parents: dict[str, str] | None = None,
) -> bytes:
    """Render the reconciliation document from the workbench's OWN view.

    `view` is `build_view`'s payload, so the document states exactly what the
    review screen states — a reader and a reviewer cannot be looking at
    different reconciliations. `evidence` is one entry per receipt document
    (see `month_report_pdf`), captioned with the charge it settles.

    `receipt_cards` (item 138) is `{document_id: (card key, card label)}`
    for every receipt in the pool, the card the tool resolved for it
    (`service.report_receipt_cards`); it decides the section of a receipt no
    charge holds. Omitted, such a receipt files under the no-card section.

    `card_parents` (item 147) is `{subcard key: account key}` from the
    registry (`cards.card_parents`). Given one, an account's section comes
    first and the cards under it follow, its heading states the group's
    figures and names the statement once, and each subcard's heading points
    back at the account instead of repeating the file. Omitted, the sections
    are the flat list they were.
    """
    from reportlab.platypus import Paragraph

    body_font, bold_font = register_fonts()
    styles = make_styles(body_font, bold_font)
    summary = view.get("summary") or {}
    rows = list(view.get("rows") or [])

    n_tx = int(summary.get("n_transactions") or len(rows))
    # `n_reconciled` is what the RENDER summary calls this, and it is the
    # count `match_rate` is computed from, so the two halves of the headline
    # describe one thing. `n_matched` is the STORED pipeline summary's name
    # for the pre-decision count; it is never on a `build_view` payload,
    # which is what this document is built from, so reading it first printed
    # "0 matched (13.8%)" on every reconciliation the app has ever produced.
    # Nothing caught it because the unit fixtures below carried the stored
    # key, which the real payload does not have. Kept as the fallback for a
    # caller that genuinely passes a stored summary.
    n_matched = int(
        summary.get("n_reconciled", summary.get("n_matched")) or 0
    )
    rate = summary.get("match_rate")
    unreconciled = summary.get("unreconciled_by_ccy") or {}

    story: list = [Paragraph(esc(title), styles["title"])]
    headline = f"{n_tx} charges  ·  {n_matched} matched"
    if rate is not None:
        headline += f" ({rate}%)"
    if unreconciled:
        headline += "  ·  unreconciled " + _money(unreconciled)
    # Item 102: booked is not evidenced. The figure sits beside the
    # unreconciled one so neither changes meaning.
    booked = summary.get("booked_no_receipt_by_ccy") or {}
    if booked:
        headline += "  ·  booked without a receipt " + _money(booked)
    story.append(Paragraph(esc(headline), styles["sub"]))

    # ── per-card coverage ───────────────────────────────────────────
    #
    # Only when the month spans more than one card. A one-card month is
    # fully described by the headline already, and a table restating it
    # would be a section the content does not support.
    coverage = [c for c in (view.get("coverage") or []) if c.get("n_transactions")]
    if len(coverage) > 1:
        story.append(Paragraph("Coverage by card", styles["h2"]))
        story.append(_table([
            [name for name, _w in _COVERAGE],
            *[[
                card_name(c),
                ", ".join(c.get("statements") or []) or "not recorded",
                _period(c),
                str(c.get("n_transactions") or 0),
                str(c.get("n_reconciled") or 0),
                str(c.get("n_unmatched_tx") or 0),
                _money(c.get("unreconciled_by_ccy") or {}) or "nothing",
            ] for c in coverage],
        ], [w for _n, w in _COVERAGE], styles))

    items = list(evidence or [])
    cards = dict(receipt_cards or {})
    for item in items:
        cards.setdefault(str(item.get("document_id") or ""), ("", ""))
    cards.pop("", None)
    sections = card_sections(view, cards, card_parents)

    if sum(1 for s in sections if s["key"]) < 2:
        # One card at most (every run older than the card axis, a one-card
        # month, even with receipts that carry no card): the flat document,
        # exactly as before. Its headline already describes the one card,
        # and "What needs attention" already lists the receipts nobody placed.
        _attention(story, view, rows, None, styles)
        story.append(Paragraph("All charges", styles["h2"]))
        story.append(_charge_table(rows, styles))
        prepared = prepare_evidence(items)
        _evidence(story, prepared, styles, None)
        return _build(story, title, prepared, None)

    by_doc = {str(i.get("document_id") or ""): i for i in items}
    section_of = {d: s["key"] for s in sections for d in s["receipt_docs"]}
    ordered: list[dict] = []
    marks: list[int] = []
    story_parts: list[tuple[dict, list[dict]]] = []
    for sec in sections:
        sec_items = [by_doc[d] for d in sec["receipt_docs"] if d in by_doc]
        ordered.extend(sec_items)
        story_parts.append((sec, sec_items))
    placed = {id(i) for i in ordered}
    # An evidence item with no document id cannot be placed by card; it
    # still prints, in the last section, rather than disappearing.
    stray = [i for i in items if id(i) not in placed]
    if stray:
        ordered.extend(stray)
        story_parts[-1][1].extend(stray)
    prepared = prepare_evidence(ordered)
    prepared_by_item = {id(pair[0]): pair for pair in prepared}

    for sec, sec_items in story_parts:
        _card_section(story, view, sec, section_of, styles)
        _evidence(
            story, [prepared_by_item[id(i)] for i in sec_items], styles, marks,
            differ=_differ_by_doc(sec["rows"]),
        )
    return _build(story, title, prepared, marks)


def _card_section(
    story: list, view: dict, sec: dict, section_of: dict[str, str], styles: dict
) -> None:
    """One card: its statement and figures, what needs attention on it, its
    charges. Its receipt pages follow (see `_evidence`)."""
    from reportlab.platypus import PageBreak, Paragraph, Spacer

    story.append(PageBreak())
    story.append(Paragraph(esc(sec["label"]), styles["h2"]))
    n_docs = len(sec["receipt_docs"])
    # Item 147: an account's heading states the GROUP's charges and money
    # (`card_statement_line` sums its subcards), but the receipt pages behind
    # it are its own card's; each subcard's pages follow in its own section
    # below. Saying which stops the count reading as a group figure it is not.
    receipts = f"{n_docs} receipt{'' if n_docs == 1 else 's'}" + (
        " on this card" if sec.get("children") else ""
    )
    line = "  ·  ".join(x for x in (card_statement_line(sec), receipts) if x)
    story.append(Paragraph(esc(line), styles["sub"]))
    story.append(Spacer(1, 4))

    _attention(story, view, sec["rows"], (sec["key"], section_of), styles)
    if sec["rows"]:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Charges", styles["capsub"]))
        story.append(Spacer(1, 3))
        story.append(_charge_table(sec["rows"], styles))
        # Item 137: a receipt held here whose own card is another. It stays
        # with the charge (the statement decides the card a charge is on) and
        # is named, so the reader knows which of the two is wrong.
        for row in sec["rows"]:
            differ = row.get("cards_differ") or {}
            if not differ:
                continue
            story.append(Spacer(1, 4))
            story.append(Paragraph(esc(
                f"{row.get('vendor') or 'A charge'} {row.get('amount') or ''} "
                f"{row.get('currency') or ''} of {row.get('date') or ''}: the "
                f"receipt held on it is on "
                f"{differ.get('receipt_card_label') or 'another card'}, "
                f"not this card."
            ), styles["capsub"]))


def _attention(
    story: list,
    view: dict,
    rows: list[dict],
    scope: tuple[str, dict[str, str]] | None,
    styles: dict,
) -> None:
    """What needs attention, then the charges already booked (one line),
    then the copies set aside. `scope` is
    `(section key, {document_id: section key})` for one card, or None for
    the whole month."""
    from reportlab.platypus import Paragraph, Spacer

    heading = "What needs attention"
    story.append(Paragraph(heading, styles["h2"] if scope is None else styles["capsub"]))
    tx_ids = {str(r.get("transaction_id") or "") for r in rows}
    row_of = {
        str(r.get("transaction_id") or ""): r for r in (view.get("rows") or [])
    }
    unmatched_all = [
        t for t in (view.get("unmatched_transactions") or [])
        if scope is None or str(t.get("transaction_id") or "") in tx_ids
    ]
    # Item 96: a charge already booked in the workbook is not a to-do. The
    # screen folds it away; here it leaves the table for one line below and
    # keeps its place in the listing, labelled already posted.
    booked_tx = [
        t for t in unmatched_all
        if booked_without_receipt(row_of.get(str(t.get("transaction_id") or "")) or t)
    ]
    unmatched_tx = [t for t in unmatched_all if t not in booked_tx]
    unmatched_rec = [
        r for r in (view.get("unmatched_receipts") or [])
        if scope is None or _in_scope(str(r.get("document_id") or ""), scope)
    ]
    # Item 74: only a group nobody has decided is something to act on. The
    # tool decides every group it can and a reviewer's ruling decides the
    # rest; a decided copy leaves this section for the record below it
    # (owner ruling 2026-09-16: resolved items leave the to-do area). A view
    # built before `state` existed reads as today: open unless dismissed.
    # Per card, a group sits with its first member that has a card section.
    all_groups = [
        g for g in (view.get("duplicate_groups") or [])
        if g.get("kind", "receipt") == "receipt"
        and (scope is None or _group_in_scope(g, scope))
    ]
    dup_groups = [
        g for g in all_groups
        if g.get("state", "open") == "open" and g.get("resolution") != "ignore"
    ]
    set_aside_groups = [
        g for g in all_groups
        if g.get("state") == "decided" and g.get("verdict") == "copy"
    ]
    if not (unmatched_tx or unmatched_rec or dup_groups):
        every_charge = (
            "Every charge has a receipt or is already booked"
            if booked_tx else "Every charge has a receipt"
        )
        story.append(Paragraph(
            f"Nothing. {every_charge}, every receipt has a charge, "
            "and no duplicate is left undecided." if scope is None else
            "Nothing on this card.", styles["capsub"],
        ))
    else:
        if unmatched_tx:
            story.append(Paragraph(
                esc(f"{len(unmatched_tx)} charges with no receipt"), styles["capsub"]
            ))
            story.append(Spacer(1, 3))
            story.append(_table([
                ["Date", "Charge", "Amount", "Ccy"],
                *[[
                    str(t.get("date") or ""), str(t.get("vendor") or ""),
                    str(t.get("amount") or ""), str(t.get("currency") or ""),
                ] for t in unmatched_tx],
            ], [60, 250, 80, 40], styles))
            story.append(Spacer(1, 8))
        if unmatched_rec:
            story.append(Paragraph(
                esc(f"{len(unmatched_rec)} receipts with no charge"), styles["capsub"]
            ))
            story.append(Spacer(1, 3))
            # Item 96: the reason the screen prints beside each one.
            story.append(_table([
                ["Date", "Vendor", "Amount", "Ccy", "Why"],
                *[[
                    str(r.get("date") or ""), str(r.get("vendor") or ""),
                    str(r.get("total") or ""), str(r.get("currency") or ""),
                    RECEIPT_REASON_SHORT.get(str(r.get("reason_code") or ""), ""),
                ] for r in unmatched_rec],
            ], [60, 170, 70, 35, 120], styles))
            story.append(Spacer(1, 8))
        if dup_groups:
            story.append(Paragraph(
                esc(f"{len(dup_groups)} possible duplicate"
                    f"{' group' if len(dup_groups) == 1 else ' groups'}"),
                styles["capsub"],
            ))
            story.append(Spacer(1, 3))
            story.append(_table([
                ["What", "Date", "Amount", "Ccy", "Copies"],
                *_duplicate_rows(dup_groups, view),
            ], [230, 60, 80, 40, 50], styles))

    if booked_tx:
        n_booked = len(booked_tx)
        story.append(Spacer(1, 8))
        story.append(Paragraph(esc(
            f"Already booked in your workbook: {n_booked} "
            f"charge{'' if n_booked == 1 else 's'} with no receipt, marked "
            f"already posted in the listing below."
        ), styles["capsub"]))

    # ── copies set aside: decided, recorded, nothing to do ──────────
    #
    # A receipt kept out of the matching as a copy of another is a decision
    # an auditor can ask about, so the document keeps the record of it: which
    # document, and on what evidence (`basis`).
    if set_aside_groups:
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            esc(f"Copies set aside ({len(set_aside_groups)})"), styles["capsub"],
        ))
        story.append(Spacer(1, 3))
        story.append(_table([
            ["What", "Date", "Amount", "Ccy", "Copies", "Why"],
            *[
                [*row, _basis_label(g)]
                for row, g in zip(_duplicate_rows(set_aside_groups, view), set_aside_groups)
            ],
        ], [170, 55, 65, 35, 40, 105], styles))


def _in_scope(doc: str, scope: tuple[str, dict[str, str]]) -> bool:
    key, section_of = scope
    return section_of.get(doc, "") == key


def _group_in_scope(group: dict, scope: tuple[str, dict[str, str]]) -> bool:
    key, section_of = scope
    members = [str(m) for m in (group.get("members") or [])]
    home = next((section_of[m] for m in members if m in section_of), "")
    return home == key


def _differ_by_doc(rows: list[dict]) -> dict[str, dict]:
    return {
        str((r.get("cards_differ") or {}).get("document_id") or ""):
            r["cards_differ"]
        for r in rows if r.get("cards_differ")
    }


def _evidence(
    story: list,
    prepared: list[tuple[dict, bytes | None]],
    styles: dict,
    marks: list[int] | None,
    differ: dict[str, dict] | None = None,
) -> None:
    """One caption page per receipt. With `marks`, each caption records its
    page so `stitch` puts the receipt's own pages right behind it."""
    from reportlab.platypus import PageBreak, Paragraph, Spacer

    for item, pdf_bytes in prepared:
        story.append(PageBreak())
        if marks is not None:
            story.append(caption_mark(marks))
        story.append(Paragraph(
            esc(str(item.get("label") or "Receipt")), styles["caption"]
        ))
        detail = str(item.get("detail") or "")
        own = (differ or {}).get(str(item.get("document_id") or ""))
        if own:
            detail = "  ·  ".join(x for x in (
                detail,
                f"the receipt's own card: {own.get('receipt_card_label') or '?'}",
            ) if x)
        if detail:
            story.append(Paragraph(esc(detail), styles["capsub"]))
        story.append(Spacer(1, 6))
        name = str(item.get("name") or "")
        note = str(item.get("render_note") or "")
        if pdf_bytes is not None:
            story.append(Paragraph(
                esc(f"{name}: {note}" if note else name), styles["capsub"]
            ))
        elif item.get("data"):
            why = note or "this file could not be rendered into the report"
            story.append(Paragraph(
                esc(f"{name}: {why}; open it in the app."),
                styles["capsub"],
            ))
        else:
            story.append(Paragraph("No receipt document.", styles["capsub"]))


def _build(
    story: list,
    title: str,
    prepared: list[tuple[dict, bytes | None]],
    marks: list[int] | None,
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate

    buf = io.BytesIO()
    margin = PAGE_MARGIN_MM * mm
    SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
        title=title,
    ).build(story)
    return stitch(buf.getvalue(), prepared, marks)


def _money(by_ccy: dict) -> str:
    return ", ".join(f"{ccy} {amt}" for ccy, amt in sorted(by_ccy.items()))


def _duplicate_rows(groups: list[dict], view: dict) -> list[list[str]]:
    """One line per flagged duplicate group, named rather than counted.

    "3 possible duplicate groups" is a number a reader can do nothing
    with; the vendor, the date and the amount are what sends somebody to
    look. Names come from the payload's own lists (the duplicate-receipt
    views) so the document cannot describe a receipt differently from the
    rest of the payload, and a group whose members are nowhere in this
    payload still prints, as its member count, rather than being silently
    dropped. Receipts only: charge-side duplicates were deleted (item 74).
    """
    named: dict[str, dict] = {}
    for group in view.get("duplicate_receipts") or []:
        for rec in group:
            named[str(rec.get("document_id") or "")] = rec
    for rec in view.get("unmatched_receipts") or []:
        named.setdefault(str(rec.get("document_id") or ""), rec)

    out: list[list[str]] = []
    for group in groups:
        members = [str(m) for m in (group.get("members") or [])]
        first = next((named[m] for m in members if m in named), None)
        kind = str(group.get("kind") or "")
        if first is None:
            out.append([
                f"{kind or 'item'} ({members[0] if members else '?'})",
                "", "", "", str(len(members)),
            ])
            continue
        amount = first.get("amount") or first.get("total") or ""
        out.append([
            f"{first.get('vendor') or '(no vendor)'} (receipt)",
            str(first.get("date") or ""),
            str(amount),
            str(first.get("currency") or ""),
            str(len(members)),
        ])
    return out


# Item 74: the evidence behind a copy, in the words the record prints. A
# reviewer's ruling prints as that, whatever the tool found.
_BASIS_LABELS = {
    "hash": "identical file",
    "reference": "same document number",
    "printed_reference": "one prints the other's number",
    "vendor_date": "same vendor, date and amount",
}


def _basis_label(group: dict) -> str:
    if group.get("decided_by") == "reviewer":
        return "set aside by a reviewer"
    return _BASIS_LABELS.get(str(group.get("basis") or ""), "copy")


def _period(entry: dict | None) -> str:
    start, end = (entry or {}).get("period_start"), (entry or {}).get("period_end")
    if not (start or end):
        return "no dated charge"
    return f"{start or '?'} to {end or '?'}"


def _charge_table(rows: list[dict], styles: dict):
    from reportlab.platypus import Paragraph, Table

    table_rows: list[list] = [
        [Paragraph(esc(name), styles["cellhead"]) for name, _w in _CHARGES]
    ]
    for n, row in enumerate(rows, start=1):
        # Item 70: a proposed category (a needs-review row's candidate) is
        # not a booking yet, so the document keeps its column blank there.
        posting = (
            {} if row.get("posting_category_proposed")
            else row.get("posting_category") or {}
        )
        matched_vendor = ""
        for cand in row.get("candidates") or []:
            if cand.get("document_id") == row.get("chosen_document_id"):
                matched_vendor = str(
                    (cand.get("receipt") or {}).get("vendor") or ""
                )
                break
        status = _status_label(row)
        if row.get("cards_differ"):
            status += ", cards differ"
        table_rows.append([
            Paragraph(str(n), styles["cell"]),
            Paragraph(esc(row.get("date") or ""), styles["cell"]),
            Paragraph(esc(row.get("vendor") or ""), styles["cell"]),
            Paragraph(esc(row.get("amount") or ""), styles["cellr"]),
            Paragraph(esc(row.get("currency") or ""), styles["cell"]),
            Paragraph(esc(status), styles["cell"]),
            Paragraph(esc(matched_vendor or "none"), styles["cell"]),
            Paragraph(
                esc(posting.get("zoho_account") or posting.get("category") or ""),
                styles["cell"],
            ),
        ])
    table = Table(table_rows, colWidths=[w for _n, w in _CHARGES], repeatRows=1)
    table.setStyle(table_style())
    return table


def _table(data: list[list[str]], widths: list[int], styles: dict):
    from reportlab.platypus import Paragraph, Table

    body = [[Paragraph(esc(c), styles["cellhead"]) for c in data[0]]]
    body += [[Paragraph(esc(c), styles["cell"]) for c in row] for row in data[1:]]
    table = Table(body, colWidths=widths, repeatRows=1)
    table.setStyle(table_style())
    return table
