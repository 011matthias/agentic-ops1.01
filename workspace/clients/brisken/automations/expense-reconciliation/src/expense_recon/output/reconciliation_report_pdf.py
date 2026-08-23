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
2. **Exceptions first**, because they are the only part anyone must act on:
   unmatched charges, unmatched receipts, duplicate groups,
3. the full charge listing, each line with its matched receipt and status,
4. the receipts themselves, behind captions naming the charge they settle.

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
        Table,
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
    story.append(Paragraph("All charges", styles["h2"]))
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
    story.append(table)

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


def _table(data: list[list[str]], widths: list[int], styles: dict):
    from reportlab.platypus import Paragraph, Table

    body = [[Paragraph(esc(c), styles["cellhead"]) for c in data[0]]]
    body += [[Paragraph(esc(c), styles["cell"]) for c in row] for row in data[1:]]
    table = Table(body, colWidths=widths, repeatRows=1)
    table.setStyle(table_style())
    return table
