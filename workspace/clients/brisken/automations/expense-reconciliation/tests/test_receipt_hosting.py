"""BLUEPRINT 8.4 — content-addressed receipt hosting. All offline."""
from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

from expense_recon.hosting import (
    DEFAULT_URL_TEMPLATE,
    HostedReceipt,
    ReceiptStore,
    resolve_receipt_urls,
)
from expense_recon.matching.types import Receipt


def _rcpt(
    doc: str,
    *,
    receipt_url: str | None = None,
    receipt_name: str | None = None,
) -> Receipt:
    return Receipt(
        document_id=doc,
        legal_entity_id="brisken-us",
        detected_date=date(2026, 4, 1),
        detected_total=Decimal("10.00"),
        detected_currency="USD",
        detected_vendor="VENDOR",
        receipt_url=receipt_url,
        receipt_name=receipt_name,
    )


# ── content addressing ──────────────────────────────────────────────


def test_put_bytes_is_content_addressed(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    content = b"\xff\xd8jpeg-bytes"
    h = hashlib.sha256(content).hexdigest()
    hosted = store.put_bytes(content, source_name="delancey-1002.jpg")
    assert hosted.content_hash == h
    assert hosted.ext == ".jpg"
    assert hosted.relpath == f"{h[:2]}/{h}.jpg"
    assert hosted.url == f"/receipts/{h[:2]}/{h}.jpg"
    assert hosted.size == len(content)
    # The object is physically on disk under its content address.
    assert store.get_path(h, ".jpg").read_bytes() == content


def test_put_identical_bytes_is_idempotent(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    content = b"same-image"
    a = store.put_bytes(content, source_name="a.png")
    b = store.put_bytes(content, source_name="a.png")
    assert a == b
    # Exactly one object stored (no duplicate file).
    shard = (tmp_path / "store" / a.content_hash[:2])
    assert len(list(shard.glob(f"{a.content_hash}*"))) == 1


def test_different_bytes_different_address(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    a = store.put_bytes(b"one", source_name="r.jpg")
    b = store.put_bytes(b"two", source_name="r.jpg")
    assert a.content_hash != b.content_hash


def test_no_extension_source_stores_and_roundtrips(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    hosted = store.put_bytes(b"no-ext", source_name="receipt")  # no suffix
    assert hosted.ext == ""
    assert store.get_path(hosted.content_hash).read_bytes() == b"no-ext"
    # get_path also resolves when the extension is unknown to the caller.
    assert store.get_path(hosted.content_hash, "").read_bytes() == b"no-ext"


def test_put_file_uses_filename_extension(tmp_path):
    src = tmp_path / "uber-1003.PDF"
    src.write_bytes(b"%PDF-1.7 ...")
    store = ReceiptStore(tmp_path / "store")
    hosted = store.put_file(src)
    assert hosted.ext == ".pdf"  # lowercased
    assert hosted.source_name == "uber-1003.PDF"


# ── URL template ────────────────────────────────────────────────────


def test_custom_url_template_placeholders(tmp_path):
    store = ReceiptStore(
        tmp_path / "store",
        url_template="https://receipts.brisken.example/{hash}{ext}",
    )
    hosted = store.put_bytes(b"img", source_name="x.jpg")
    h = hosted.content_hash
    assert hosted.url == f"https://receipts.brisken.example/{h}.jpg"


def test_url_for_matches_put_and_is_deterministic(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    hosted = store.put_bytes(b"img", source_name="x.jpg")
    assert store.url_for(hosted.content_hash, ".jpg") == hosted.url
    assert DEFAULT_URL_TEMPLATE == "/receipts/{relpath}"


# ── resolve from a folder ───────────────────────────────────────────


def test_resolve_finds_flat_file(tmp_path):
    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "delancey-1002.jpg").write_bytes(b"delancey")
    store = ReceiptStore(tmp_path / "store")
    hosted = store.resolve("delancey-1002.jpg", search_dir=folder)
    assert hosted is not None
    assert hosted.content_hash == hashlib.sha256(b"delancey").hexdigest()


def test_resolve_finds_nested_file(tmp_path):
    folder = tmp_path / "receipts"
    (folder / "ER-00220").mkdir(parents=True)
    (folder / "ER-00220" / "versailles-1005.jpg").write_bytes(b"versailles")
    store = ReceiptStore(tmp_path / "store")
    hosted = store.resolve("versailles-1005.jpg", search_dir=folder)
    assert hosted is not None
    assert hosted.source_name == "versailles-1005.jpg"


def test_resolve_missing_file_returns_none(tmp_path):
    folder = tmp_path / "receipts"
    folder.mkdir()
    store = ReceiptStore(tmp_path / "store")
    assert store.resolve("not-here.jpg", search_dir=folder) is None


# ── the 8.1 fork: resolve_receipt_urls ──────────────────────────────


def test_resolve_receipt_urls_covers_the_fork(tmp_path):
    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "delancey-1002.jpg").write_bytes(b"delancey")
    store = ReceiptStore(tmp_path / "store")

    receipts = [
        _rcpt("EXP-1001", receipt_url="https://expense.zoho.example/r/1001"),  # URL side
        _rcpt("EXP-1002", receipt_name="delancey-1002.jpg"),                   # filename side
        _rcpt("EXP-1003", receipt_name="missing.pdf"),                          # filename, absent
        _rcpt("EXP-1004"),                                                      # neither
    ]
    urls = resolve_receipt_urls(receipts, store=store, search_dir=folder)

    assert urls["EXP-1001"] == "https://expense.zoho.example/r/1001"  # carried through
    h = hashlib.sha256(b"delancey").hexdigest()
    assert urls["EXP-1002"] == f"/receipts/{h[:2]}/{h}.jpg"           # hosted
    assert urls["EXP-1003"] is None                                   # surfaced, not fabricated
    assert urls["EXP-1004"] is None


def test_resolve_receipt_urls_without_search_dir_keeps_url_side(tmp_path):
    # No receipts folder: URL-carrying receipts still resolve; filename-only
    # ones become None instead of erroring.
    store = ReceiptStore(tmp_path / "store")
    receipts = [
        _rcpt("EXP-1001", receipt_url="https://e/r/1"),
        _rcpt("EXP-1002", receipt_name="delancey-1002.jpg"),
    ]
    urls = resolve_receipt_urls(receipts, store=store, search_dir=None)
    assert urls == {"EXP-1001": "https://e/r/1", "EXP-1002": None}


# ── persistence ─────────────────────────────────────────────────────


def test_store_persists_across_reopen(tmp_path):
    root = tmp_path / "store"
    hosted = ReceiptStore(root).put_bytes(b"persist-me", source_name="r.jpg")
    # A fresh store over the same root sees the object (it is on disk, no
    # in-memory index) — the survives-the-Zoho-exit property.
    reopened = ReceiptStore(root)
    assert reopened.get_path(hosted.content_hash, ".jpg").read_bytes() == b"persist-me"
    assert reopened.url_for(hosted.content_hash, ".jpg") == hosted.url


def test_hosted_receipt_is_frozen():
    hosted = HostedReceipt(
        content_hash="abc", ext=".jpg", relpath="ab/abc.jpg",
        url="/receipts/ab/abc.jpg", source_name="r.jpg", size=3,
    )
    import dataclasses
    assert dataclasses.is_dataclass(hosted)
    try:
        hosted.url = "x"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("HostedReceipt should be frozen")
