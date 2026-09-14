"""Which receipts actually got a page in the built report (item 68).

The Receipt column read "attached" the moment a file was found on disk. That
is a question answered before renderability is known: a password-protected
PDF, a truncated JPEG or a zero-byte upload is a file that exists and a page
that never appears. So the count of covered expenses was an upper bound
presented as a fact, and the caption pages -- which say "this file could not
be rendered into the report" -- were the only place the truth showed.

Renderability is decided in exactly one place, with the bytes in hand:
`output/_pdf_common.prepare_evidence`, the function the builder uses to admit
a page. Calling it per payload is not an option -- decoding every receipt of
a 51-receipt month would put a multi-second image pass in front of the grid
on a 1 GB machine. So the verdict is RECORDED where it is decided (the report
build) and READ where it is rendered (the view).

The key is the file's identity, never its name: `size:mtime_ns`. Replace a
receipt and the fingerprint stops matching, so the stale verdict is not
served and the field goes ABSENT -- unknown again, rather than confidently
wrong. That is the same choice `coverage[].known` had to make: a field that
answers "we have not decided yet" is worth having, and one that answers last
week's question is not.

Every path here is fail-open. A missing, corrupt or unwritable cache costs
the Receipt column its third state; it never costs anybody a report.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

RECEIPT_PAGES_NAME = "receipt-pages.json"


def _fingerprint(path: Path | None) -> str | None:
    """The file's identity for cache purposes: size and modification time.

    Not a content hash: this runs once per receipt per report build, and the
    failure it has to catch is "the bytes behind this document changed",
    which a replace-in-place (item 66's byte overwrite) and an ordinary
    re-upload both move.
    """
    if path is None:
        return None
    try:
        st = path.stat()
    except OSError:
        return None
    return f"{st.st_size}:{st.st_mtime_ns}"


def _cache_path(work_dir: Path | str) -> Path:
    return Path(work_dir) / RECEIPT_PAGES_NAME


def _read(work_dir: Path | str) -> dict:
    try:
        raw = json.loads(_cache_path(work_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def record_receipt_pages(
    work_dir: Path | str, verdicts: dict[str, tuple[Path | None, bool]]
) -> None:
    """Record what a report build just decided: document_id -> (file, page?).

    Merged into whatever is already recorded, so a trip report and a month
    report each contribute what they saw. A document whose file cannot be
    fingerprinted is dropped rather than recorded against nothing: an entry
    that can never be matched would only ever be dead weight.
    """
    stored = _read(work_dir)
    for document_id, (path, in_report) in verdicts.items():
        fp = _fingerprint(path)
        if fp is None:
            # No file behind it. `known_receipt_pages` answers that case
            # without a cache entry, so storing one would add nothing.
            stored.pop(str(document_id), None)
            continue
        stored[str(document_id)] = {"fp": fp, "in_report": bool(in_report)}
    path_out = _cache_path(work_dir)
    tmp = path_out.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(stored, indent=0), encoding="utf-8")
        os.replace(tmp, path_out)
    except OSError:
        # The report is the deliverable; the cache is a convenience. A
        # read-only or full volume loses the column's third state and
        # nothing else.
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def known_receipt_pages(
    work_dir: Path | str, paths: dict[str, Path | None]
) -> dict[str, bool]:
    """document_id -> has a page in the report, for the documents whose
    verdict is known RIGHT NOW. Documents absent from the result are the
    honest "not decided yet".

    A document with NO file is known without any report build: nothing on
    disk cannot become a page. A document WITH a file needs a recorded
    verdict whose fingerprint still matches the file that is there now.
    """
    stored = _read(work_dir)
    out: dict[str, bool] = {}
    for document_id, path in paths.items():
        if path is None:
            out[document_id] = False
            continue
        entry = stored.get(str(document_id))
        if not isinstance(entry, dict):
            continue
        if entry.get("fp") != _fingerprint(path):
            continue
        out[document_id] = bool(entry.get("in_report"))
    return out
