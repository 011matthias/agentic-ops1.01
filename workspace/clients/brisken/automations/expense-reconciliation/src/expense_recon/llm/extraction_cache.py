"""Per-document extraction cache — "same photo, same answer".

The vision extractor re-reads an identical receipt file differently
across runs even at temperature 0 (vendor spellings MEGA CENTER /
CENTRO / CENTRE from one image; reference numbers, tax labels, and on
2026-08-15 even a BRL→EUR currency flip and a 50.50→50.00 tax drift on
the smoke10 set). Each new spelling starts its own learned-memory row,
so the tool never compounds what Criss teaches it.

The fix is structural, not statistical: once a document's content has
been read, the model's RAW JSON payload is stored keyed on a content
hash, and an identical document is answered from the store instead of
asking the model again. Re-runs become deterministic by construction
and cost nothing.

Two properties are load-bearing:

* The cache stores the raw payload, NOT the parsed ExtractedReceipt —
  `_extraction_from_payload` (and its whitelists / sentinel collapses)
  always runs live, so a parser fix applies to cached readings too.
* The key covers everything that shapes the model's answer EXCEPT the
  file name: prompt template + response schema (via a fingerprint that
  auto-invalidates on any prompt change), the model id, and the
  document content (image bytes or the PDF text layer). Same photo,
  same answer — whatever the file is called this month.

Every operation is fail-open: a broken cache file degrades to plain
API calls, never to a broken run.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("expense_recon")

# Bump to invalidate every stored reading (e.g. a semantic change that the
# prompt/schema fingerprint cannot see, like a rasterization-scale change).
_CACHE_VERSION = "1"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS extraction_cache (
    key        TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    model      TEXT NOT NULL,
    file_name  TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def prompt_fingerprint(instructions_template: str, schema: dict) -> str:
    """Fingerprint of everything prompt-shaped that goes into an
    extraction call: the UNFORMATTED instruction template(s) and the
    strict response schema. Any prompt or schema edit changes the
    fingerprint, so stale readings become unreachable instead of being
    served against a prompt they were never an answer to."""
    h = hashlib.sha256()
    h.update(_CACHE_VERSION.encode("ascii"))
    h.update(b"\x00")
    h.update(instructions_template.encode("utf-8"))
    h.update(b"\x00")
    h.update(json.dumps(schema, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def extraction_cache_key(
    *,
    fingerprint: str,
    model: str,
    images: list[tuple[bytes, str]] | None = None,
    text: str | None = None,
) -> str:
    """Content-addressed key for one extraction call. Deliberately does
    NOT include the file name: content-identical documents get the same
    reading regardless of what the file is called."""
    h = hashlib.sha256()
    h.update(fingerprint.encode("ascii"))
    h.update(b"\x00")
    h.update(model.encode("utf-8"))
    h.update(b"\x00")
    if text is not None:
        h.update(b"text\x00")
        h.update(text.encode("utf-8"))
    else:
        h.update(b"images\x00")
        for raw, mime in images or []:
            h.update(mime.encode("utf-8"))
            h.update(b"\x00")
            h.update(len(raw).to_bytes(8, "big"))
            h.update(raw)
    return h.hexdigest()


class ExtractionCache:
    """SQLite-backed raw-payload store. One short-lived connection per
    operation (safe under the web app's request threads); every failure
    is swallowed to a miss / no-op, because the cache must never break
    a run."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.debug("extraction cache: cannot create %s parent", self.path,
                         exc_info=True)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=5)
        con.execute(_SCHEMA_SQL)
        return con

    def get(self, key: str) -> dict | None:
        """The stored raw payload for `key`, or None (miss / any error)."""
        try:
            with self._connect() as con:
                row = con.execute(
                    "SELECT payload FROM extraction_cache WHERE key = ?", (key,)
                ).fetchone()
            if row is None:
                return None
            payload = json.loads(row[0])
            return payload if isinstance(payload, dict) else None
        except Exception:  # noqa: BLE001 - cache errors degrade to a miss
            logger.debug("extraction cache get failed (%s)", self.path,
                         exc_info=True)
            return None

    def put(self, key: str, payload_json: str, *, model: str, file_name: str) -> None:
        """Store one raw payload. `model` and `file_name` are recorded
        for inspection only; they are not part of the key."""
        try:
            with self._connect() as con:
                con.execute(
                    "INSERT OR REPLACE INTO extraction_cache "
                    "(key, payload, model, file_name) VALUES (?, ?, ?, ?)",
                    (key, payload_json, model, file_name),
                )
        except Exception:  # noqa: BLE001 - cache errors degrade to a no-op
            logger.debug("extraction cache put failed (%s)", self.path,
                         exc_info=True)
