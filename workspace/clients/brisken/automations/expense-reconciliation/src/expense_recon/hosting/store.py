"""Content-addressed receipt hosting (BLUEPRINT 8.4, Path A).

The receipt-URL design fork (8.1): a Zoho Expense line carries either a
``receipt_url`` (the export already hosts the image) or a ``receipt_name``
(only the attachment filename). 8.4 is the fallback side — it gives a
receipt addressed only by filename a STABLE URL, so the Books journal
export (8.5) can carry a link for every line.

The scheme is a content-addressed local file store plus a URL template:

* **Content-addressed.** A receipt file is stored under the SHA-256 of
  its bytes (``root/<hash[:2]>/<hash><ext>``). The address IS the
  content, so the same image re-hosted from a re-export lands on the same
  path (idempotent, deduplicated) and the URL never changes as long as
  the bytes do not. This is the receipt-side parallel of the statement
  table's content fingerprint (8.2). The address includes the file
  extension so the served URL keeps a usable type hint (``.jpg`` vs
  ``.pdf``); identical bytes presented under two different extensions are
  the only case stored twice, which does not happen for a receipt whose
  filename is stable across exports.

* **URL template.** The physical store is decoupled from where the URL is
  served. ``url_template`` maps a stored object to its public URL; the
  default is a host-agnostic root-relative path (``/receipts/<relpath>``)
  that works behind any origin. WHICH origin serves it (Chris-local vs a
  small host) is the deployment decision deferred with 5c (BLUEPRINT
  8.4); when that lands only the template's base changes, never the
  content address.

A missing receipt resolves to ``None``, never a fabricated URL — the
unresolved line is surfaced (reconciliation guarantee, B4), the same way
the folder ingest surfaces an unreadable file instead of inventing data.
"""
from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ..matching.types import Receipt

# Host-agnostic default: a root-relative path that resolves behind any
# origin. The deployment target (Chris-local vs a small host) only changes
# this template's base, never the on-disk content address (BLUEPRINT 8.4).
DEFAULT_URL_TEMPLATE = "/receipts/{relpath}"


@dataclass(frozen=True)
class HostedReceipt:
    """One stored receipt. ``relpath`` is the on-disk path under the store
    root (forward slashes); ``url`` is ``relpath`` run through the store's
    URL template."""

    content_hash: str
    ext: str            # includes the leading dot, or "" when the source had none
    relpath: str        # "<hash[:2]>/<hash><ext>"
    url: str
    source_name: str | None
    size: int


class ReceiptStore:
    """Content-addressed local receipt store. Open it on a root directory,
    ``put_bytes`` / ``put_file`` / ``resolve`` to host a receipt and get a
    stable URL, ``get_path`` / ``url_for`` to read back."""

    def __init__(self, root: str | Path, *, url_template: str = DEFAULT_URL_TEMPLATE):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.url_template = url_template

    def put_bytes(self, content: bytes, *, source_name: str | None = None) -> HostedReceipt:
        """Store ``content`` under its SHA-256. Idempotent: re-putting the
        same bytes (with the same extension) is a no-op that returns the
        same address."""
        h = hashlib.sha256(content).hexdigest()
        ext = _ext_of(source_name)
        relpath = f"{h[:2]}/{h}{ext}"
        dest = self.root / h[:2] / f"{h}{ext}"
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Write to a pid-scoped temp then atomically rename, so a
            # concurrent reader never sees a half-written object.
            tmp = dest.parent / f"{dest.name}.{os.getpid()}.tmp"
            tmp.write_bytes(content)
            os.replace(tmp, dest)
        return HostedReceipt(
            content_hash=h,
            ext=ext,
            relpath=relpath,
            url=self._url(h, ext, relpath),
            source_name=source_name,
            size=len(content),
        )

    def put_file(self, path: str | Path) -> HostedReceipt:
        """Read a file and store it content-addressed (its name supplies
        the extension)."""
        path = Path(path)
        return self.put_bytes(path.read_bytes(), source_name=path.name)

    def resolve(self, receipt_name: str, *, search_dir: str | Path) -> HostedReceipt | None:
        """Find the file named ``receipt_name`` under ``search_dir`` and
        host it. Returns ``None`` if no such file exists (surfaced, never
        fabricated)."""
        src = _find_named(Path(search_dir), receipt_name)
        return self.put_file(src) if src is not None else None

    def get_path(self, content_hash: str, ext: str = "") -> Path | None:
        """The stored file for a content hash, or None if absent. When
        ``ext`` is unknown, the hash prefix is matched."""
        dest = self.root / content_hash[:2] / f"{content_hash}{ext}"
        if dest.exists():
            return dest
        shard = self.root / content_hash[:2]
        if shard.is_dir():
            for p in sorted(shard.glob(f"{content_hash}*")):
                if p.is_file():
                    return p
        return None

    def url_for(self, content_hash: str, ext: str = "") -> str:
        """The URL a content hash (+ extension) would have under this
        store's template, independent of whether it is stored yet."""
        relpath = f"{content_hash[:2]}/{content_hash}{ext}"
        return self._url(content_hash, ext, relpath)

    def _url(self, content_hash: str, ext: str, relpath: str) -> str:
        return self.url_template.format(
            relpath=relpath,
            key=f"{content_hash}{ext}",
            hash=content_hash,
            ext=ext,
        )


def resolve_receipt_urls(
    receipts: Iterable[Receipt],
    *,
    store: ReceiptStore,
    search_dir: str | Path | None = None,
) -> dict[str, str | None]:
    """Map each receipt's ``document_id`` to a receipt URL, per the 8.1 fork.

    * ``receipt_url`` present -> carried through as-is (the export already
      hosts it; the URL side of the fork).
    * else ``receipt_name`` present -> resolved through ``store`` (the
      filename fallback side: find it under ``search_dir``, host it
      content-addressed, return the stable URL). With no ``search_dir`` the
      filename cannot be hosted and resolves to None.
    * neither, or the named file is not found -> None (surfaced, never
      fabricated).

    The returned mapping is what the Books journal export (8.5) carries as
    the receipt-URL column.
    """
    urls: dict[str, str | None] = {}
    for r in receipts:
        if r.receipt_url:
            urls[r.document_id] = r.receipt_url
        elif r.receipt_name and search_dir is not None:
            hosted = store.resolve(r.receipt_name, search_dir=search_dir)
            urls[r.document_id] = hosted.url if hosted is not None else None
        else:
            urls[r.document_id] = None
    return urls


def _ext_of(name: str | None) -> str:
    return Path(name).suffix.lower() if name else ""


def _find_named(search_dir: Path, receipt_name: str) -> Path | None:
    """Locate ``receipt_name`` under ``search_dir``: an exact path match
    first (the flat folder-ingest convention), then a recursive search by
    basename so receipts filed in per-report subfolders still resolve.
    First match wins; None when absent."""
    direct = search_dir / receipt_name
    if direct.is_file():
        return direct
    base = Path(receipt_name).name
    for p in sorted(search_dir.rglob(base)):
        if p.is_file():
            return p
    return None
