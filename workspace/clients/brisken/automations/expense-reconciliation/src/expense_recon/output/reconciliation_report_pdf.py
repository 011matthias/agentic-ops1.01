"""The statement reconciliation as a document.

Owner directive 2026-08-23: the reconciliation output is not exported into
any application either, so the question is what actually serves the work.
The answer is not a CSV. A reconciliation's product is *evidence that a month
is complete and correct*: every statement charge accounted for, the ones that
are not called out by name, and the receipts that prove the rest. A CSV can
carry the first part and none of the others, and nothing reads it.

So the document is:

1. the header — the month, the statement account, how many charges matched,
   and what is still unreconciled per currency,
2. **Per-card coverage**, when the month holds more than one card: which
   statements were loaded for each, over what span, and how far each one
   has got. A month is reconciled card by card, and a single unreconciled
   figure over three cards tells the reader nothing about which pile of
   receipts to go and find,
3. **Exceptions first**, because they are the only part anyone must act on:
   unmatched charges, unmatched receipts, duplicate groups,
4. the full charge listing, each line with its matched receipt and status,
   sectioned per card when there is more than one,
5. the receipts themselves, behind captions naming the charge they settle.

The XLSX stays the working sidecar (Criss works in Excel, and her fill-colour
is real data); the CSV stays available and demoted.
"""
from __future__ import annotations

import io
from collections.abc import Sequence

from ._pdf_common import (
    esc,
    make_styles,
    prepare_evidence,
    register_fonts,
    stitch,
    table_style,
)

_COVERAGE = (
    ("Card", 118),
    ("Statements", 118),
    ("Period", 100),
    ("Charges", 46),
    ("Matched", 46),
    ("No receipt", 52),
    ("Unreconciled", 92),
)

_CHARGES = (
    ("#", 24),
    ("Date", 60),
    ("Charge", 150),
    ("Amount", 70),
    ("Ccy", 32),
    ("Status", 74),
    ("Receipt", 140),
    ("Account", 122),
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
    if bucket in ("unmatched", ""):
        return "no receipt"
    return bucket.replace("_", " ")


def build_reconciliation_report_pdf(
    view: dict,
    *,
    title: str,
    evidence: Sequence[dict] | None = None,
) -> bytes:
    """Render the reconciliation document from the workbench's OWN view.

    `view` is `build_view`'s payload, so the document states exactly what the
    review screen states — a reader and a reviewer cannot be looking at
    different reconciliations. `evidence` is one entry per receipt document
    (see `month_report_pdf`), captioned with the charge it settles.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    body_font, bold_font = register_fonts()
    styles = make_styles(body_font, bold_font)
    summary = view.get("summary") or {}
    rows = list(view.get("rows") or [])

    n_tx = int(summary.get("n_transactions") or len(rows))
    n_matched = int(summary.get("n_matched") or 0)
    rate = summary.get("match_rate")
    unreconciled = summary.get("unreconciled_by_ccy") or {}

    story: list = [Paragraph(esc(title), styles["title"])]
    headline = f"{n_tx} charges  ·  {n_matched} matched"
    if rate is not None:
        headline += f" ({rate}%)"
    if unreconciled:
        headline += "  ·  unreconciled " + ", ".join(
            f"{ccy} {amt}" for ccy, amt in sorted(unreconciled.items())
        )
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
                _coverage_name(c),
                ", ".join(c.get("statements") or []) or "not recorded",
                _period(c),
                str(c.get("n_transactions") or 0),
                str(c.get("n_reconciled") or 0),
                str(c.get("n_unmatched_tx") or 0),
                ", ".join(
                    f"{ccy} {amt}"
                    for ccy, amt in sorted(
                        (c.get("unreconciled_by_ccy") or {}).items()
                    )
                ) or "nothing",
            ] for c in coverage],
        ], [w for _n, w in _COVERAGE], styles))

    # ── exceptions first: the only part anyone must act on ──────────
    story.append(Paragraph("What needs attention", styles["h2"]))
    unmatched_tx = list(view.get("unmatched_transactions") or [])
    unmatched_rec = list(view.get("unmatched_receipts") or [])
    dup_groups = list(view.get("duplicate_groups") or [])
    if not (unmatched_tx or unmatched_rec or dup_groups):
        story.append(Paragraph(
            "Nothing. Every charge has a receipt, every receipt has a charge, "
            "and no duplicates were found.", styles["capsub"],
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
            story.append(_table([
                ["Date", "Vendor", "Amount", "Ccy"],
                *[[
                    str(r.get("date") or ""), str(r.get("vendor") or ""),
                    str(r.get("total") or ""), str(r.get("currency") or ""),
                ] for r in unmatched_rec],
            ], [60, 250, 80, 40], styles))
            story.append(Spacer(1, 8))
        if dup_groups:
            story.append(Paragraph(
                esc(f"{len(dup_groups)} possible duplicate groups"),
                styles["capsub"],
            ))

    # ── the full charge listing ─────────────────────────────────────
    #
    # Sectioned per card when the month holds more than one, because that is
    # how the reconciling is done: one card, one statement, one pile of
    # receipts. The grouping key comes off the row (`coverage_key`) rather
    # than being re-derived from `account_id` here, so a section and the
    # coverage table above can never disagree about which card a charge is
    # on. One card, or a payload with no coverage at all (every run older
    # than this), renders exactly the one flat table it always did.
    story.append(Paragraph("All charges", styles["h2"]))
    if len(coverage) > 1:
        by_key: dict[str, list[dict]] = {}
        for row in rows:
            by_key.setdefault(str(row.get("coverage_key") or ""), []).append(row)
        for entry in coverage:
            group = by_key.pop(entry.get("key") or "", [])
            if not group:
                continue
            story.append(Paragraph(esc(_coverage_name(entry)), styles["capsub"]))
            story.append(Spacer(1, 3))
            story.append(_charge_table(group, styles))
            story.append(Spacer(1, 8))
        # Anything the coverage list did not claim still has to be printed:
        # a listing that silently drops charges is worse than an ugly one.
        leftover = [r for group in by_key.values() for r in group]
        if leftover:
            story.append(Paragraph("Other charges", styles["capsub"]))
            story.append(Spacer(1, 3))
            story.append(_charge_table(leftover, styles))
    else:
        story.append(_charge_table(rows, styles))

    # ── evidence ────────────────────────────────────────────────────
    items = list(evidence or [])
    prepared = prepare_evidence(items)
    for item, pdf_bytes in prepared:
        story.append(PageBreak())
        story.append(Paragraph(
            esc(str(item.get("label") or "Receipt")), styles["caption"]
        ))
        if item.get("detail"):
            story.append(Paragraph(esc(str(item["detail"])), styles["capsub"]))
        story.append(Spacer(1, 6))
        name = str(item.get("name") or "")
        if pdf_bytes is not None:
            story.append(Paragraph(esc(name), styles["capsub"]))
        elif item.get("data"):
            story.append(Paragraph(
                esc(f"{name}: this file could not be rendered into the report; "
                    f"open it in the app."),
                styles["capsub"],
            ))
        else:
            story.append(Paragraph("No receipt document.", styles["capsub"]))

    buf = io.BytesIO()
    SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=title,
    ).build(story)
    return stitch(buf.getvalue(), prepared)


def _coverage_name(entry: dict) -> str:
    """A card's name for the document: its label, with the digits beside it
    when they add something the label does not already say."""
    label = str(entry.get("label") or "").strip()
    digits = [str(d) for d in (entry.get("digits") or []) if str(d).strip()]
    extra = [d for d in digits if d not in label]
    return f"{label} ({'/'.join(extra)})" if label and extra else (label or "-")


def _period(entry: dict) -> str:
    start, end = entry.get("period_start"), entry.get("period_end")
    if not (start or end):
        return "no dated charge"
    return f"{start or '?'} to {end or '?'}"


def _charge_table(rows: list[dict], styles: dict):
    from reportlab.platypus import Paragraph, Table

    table_rows: list[list] = [
        [Paragraph(esc(name), styles["cellhead"]) for name, _w in _CHARGES]
    ]
    for n, row in enumerate(rows, start=1):
        posting = row.get("posting_category") or {}
        matched_vendor = ""
        for cand in row.get("candidates") or []:
            if cand.get("document_id") == row.get("chosen_document_id"):
                matched_vendor = str(
                    (cand.get("receipt") or {}).get("vendor") or ""
                )
                break
        table_rows.append([
            Paragraph(str(n), styles["cell"]),
            Paragraph(esc(row.get("date") or ""), styles["cell"]),
            Paragraph(esc(row.get("vendor") or ""), styles["cell"]),
            Paragraph(esc(row.get("amount") or ""), styles["cellr"]),
            Paragraph(esc(row.get("currency") or ""), styles["cell"]),
            Paragraph(esc(_status_label(row)), styles["cell"]),
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
