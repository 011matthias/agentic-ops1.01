"""Content-addressed receipt hosting (BLUEPRINT 8.4, Path A).

The fallback side of the receipt-URL design fork (8.1): a receipt that the
Zoho Expense export references only by filename (``receipt_name``) is
stored content-addressed and given a stable URL the Books journal export
(8.5) can carry. See ``store`` for the scheme and the deferred deployment
decision.
"""
from __future__ import annotations

from .store import (
    DEFAULT_URL_TEMPLATE,
    HostedReceipt,
    ReceiptStore,
    resolve_receipt_urls,
)

__all__ = [
    "DEFAULT_URL_TEMPLATE",
    "HostedReceipt",
    "ReceiptStore",
    "resolve_receipt_urls",
]
