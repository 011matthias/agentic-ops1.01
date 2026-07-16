# /// script
# requires-python = ">=3.11"
# dependencies = ["pywin32>=306", "openpyxl>=3.1"]
# ///
"""Brisken website-inquiry spreadsheet from the Wix notification emails.

Parses every "You have received a new notification from Brisken" email
(no-reply@crm.wix.com) in Dirk's Outlook inbox into one deduped xlsx the
team can check, with a domain-based read on each row. Re-run any time new
notifications arrive; the file is rewritten in full.

Requires classic Outlook on this machine with dirk.neumann@brisken.com
configured. Output (client PII) goes to the gitignored context tree:

    workspace/clients/brisken/context/lead-generation/website-inquiries.xlsx

Usage:  uv run tools/brisken-website-inquiries.py [--open]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import win32com.client
from openpyxl import Workbook

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "workspace/clients/brisken/context/lead-generation/website-inquiries.xlsx"
MAILBOX = "dirk.neumann@brisken.com"

# Domains seen in the 2026-07-07 triage of the 13 notifications.
DISPOSABLE = {"roastic.com", "burangir.com", "gmali.com"}
FREEMAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "gmx.de", "web.de"}

FIELD_KEYS = {
    "form": ("Form name:",),
    "first": ("Contact first name:", "First name (from 3 forms):"),
    "last": ("Contact last name:", "Last name (from 3 forms):"),
    "company": ("Contact company:", "Company name (from 3 forms):"),
    "email": ("Contact email:", "Email (from 3 forms):"),
    "submitted": ("Submission date and time:",),
    "download": ("Download URL:",),
    "dashboard": ("Submissions Link:",),
}


def parse_body(body: str) -> dict:
    row: dict = {}
    for line in re.split(r"\r\n|\n", body):
        s = line.strip()
        for field, keys in FIELD_KEYS.items():
            for key in keys:
                if s.startswith(key) and not row.get(field):
                    row[field] = s[len(key):].strip()
    return row


def read_on_domain(email: str) -> str:
    domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
    if not domain:
        return "no email"
    if domain in DISPOSABLE:
        return "spam (disposable domain)"
    if domain in FREEMAIL:
        return "check (freemail address)"
    return "REVIEW (corporate domain)"


def main() -> int:
    ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    acct = next((a for a in ns.Accounts if a.SmtpAddress.lower() == MAILBOX), None)
    if acct is None:
        sys.exit(f"ERROR: {MAILBOX} not configured in Outlook on this machine")
    inbox = acct.DeliveryStore.GetDefaultFolder(6)
    items = inbox.Items.Restrict(
        '@SQL="urn:schemas:httpmail:fromemail" LIKE \'%crm.wix.com%\''
    )

    rows, seen = [], set()
    for item in items:
        row = parse_body(item.Body)
        row["received"] = item.ReceivedTime.strftime("%Y-%m-%d %H:%M")
        key = (row.get("email", ""), row.get("form", ""), row.get("submitted", "")[:10])
        if key in seen:
            continue  # Wix sends some notifications twice
        seen.add(key)
        row["read"] = read_on_domain(row.get("email", ""))
        rows.append(row)
    rows.sort(key=lambda r: r["received"], reverse=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Website inquiries"
    header = ["Received", "Form", "First name", "Last name", "Company",
              "Email", "Read", "Wix dashboard (submissions)"]
    ws.append(header)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)
    for r in rows:
        ws.append([r.get("received", ""), r.get("form", ""), r.get("first", ""),
                   r.get("last", ""), r.get("company", ""), r.get("email", ""),
                   r.get("read", ""), r.get("dashboard", "")])
    for col, width in zip("ABCDEFGH", (17, 26, 14, 14, 26, 32, 26, 60)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"Wrote {OUT} ({len(rows)} deduped inquiries)")

    if "--open" in sys.argv:
        import os
        os.startfile(OUT)  # noqa: S606 - explicit user-facing open
    return 0


if __name__ == "__main__":
    sys.exit(main())
