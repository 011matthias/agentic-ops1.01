"""The Receipts drop reads its pile in parallel (item 148).

Owner, 2026-09-18: "manual receipt injection function is taking way too
long." The drop's wall clock was the routing pass in
`route_dropped_receipts`: one vision round-trip per file, end to end,
before anything was filed. Measured on a stub at 0.2s per read, a 40-file
drop spent 8.2s reading and 0.1s filing; at a real vision round-trip that
is minutes, and the page showed one frozen "reading receipts" throughout.

What is pinned here:

1. The ledger is the SAME ledger. Row order and every field match the
   serial loop's for the same staging folder. That is the contract the
   parallelism is not allowed to bend.
2. A file that explodes mid-read is reported and the rest still file.
3. `month_override` reads nothing at all.
4. The reads overlap, stay inside `_DROP_READ_WORKERS`, and beat the
   serial wall clock.
5. Progress is reported per file (`reading receipts (7/40)`), throttled
   on a big pile.
6. A file pays vision ONCE across the routing pass and the ingest that
   follows, because the routing warms the content-addressed extraction
   cache the ingest reads. The negative twin (cache off, two reads) is
   what makes that count evidence instead of a coincidence.
"""
from __future__ import annotations

import calendar
import json
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient
from expense_recon.web import intake_mail

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000

# Dynamic fixture months (mirrors test_receipts_drop): the plausibility
# clamp measures printed dates against TODAY, so literals would expire.
DAY_M1 = date.today().replace(day=1) - timedelta(days=20)
DAY_M2 = date.today().replace(day=1) - timedelta(days=50)
MONTH_M1 = f"{DAY_M1.year:04d}-{DAY_M1.month:02d}"
MONTH_M2 = f"{DAY_M2.year:04d}-{DAY_M2.month:02d}"
LABEL_M1 = f"{calendar.month_name[DAY_M1.month]} {DAY_M1.year}"


@pytest.fixture(autouse=True)
def _drop_env(monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_EXTRACTION_CACHE", raising=False)


def _ext(day: date | None, vendor="Staples", total="42.50") -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day.isoformat() if day else None, total=total, currency="EUR",
        vendor=vendor, reference="", line_items=(), confidence=0.9, notes="",
    )


class _ByName(MockLLMClient):
    """A mock that answers by the FILE it is reading, never by call order.

    Call order stopped being file order when the reads went onto a pool, so
    a test that wants two files to read as two different months has to name
    them. Doubles as the instrument for the concurrency tests: it records
    the peak number of reads in flight, and can sleep or raise per file.
    `memoize` models the real extraction cache (a re-read of the same file
    costs nothing), so a timing test measures the routing pass.
    """

    def __init__(self, mapping: dict, *, latency: float = 0.0,
                 explode: tuple[str, ...] = (), memoize: bool = False):
        super().__init__()
        self.mapping = mapping
        self.latency = latency
        self.explode = explode
        self.memoize = memoize
        self.seen: list[str] = []
        self._warm: set[str] = set()
        self._lock = threading.Lock()
        self._live = 0
        self.peak = 0

    def extract_receipt(self, *, file_name, images=None, text=None):
        key = str(file_name).split("__")[-1]
        with self._lock:
            self.seen.append(str(file_name))
            cold = key not in self._warm
            self._warm.add(key)
            self._live += 1
            self.peak = max(self.peak, self._live)
        try:
            if self.latency and (cold or not self.memoize):
                time.sleep(self.latency)
            for name in self.explode:
                if key.endswith(name):
                    raise RuntimeError(f"vision exploded on {name}")
            for name, extraction in self.mapping.items():
                if key.endswith(name):
                    return extraction
            return _ext(None)
        finally:
            with self._lock:
                self._live -= 1


def _patch(monkeypatch, mock) -> None:
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _staged(root: Path, files: list[tuple[str, bytes]]) -> Path:
    staging = root / "drops" / "job"
    staging.mkdir(parents=True, exist_ok=True)
    for i, (name, data) in enumerate(files):
        (staging / f"{i:04d}__{name}").write_bytes(data)
    return staging


def _route(root: Path, files, month: str = "", on_stage=None) -> dict:
    return intake_mail.route_dropped_receipts(
        root / "runs.sqlite", None, root, _staged(root, files), month,
        on_stage=on_stage,
    )


def _anonymize(outcome: dict) -> dict:
    """The ledger with the one value that is a fresh uuid on every run (a
    created month's id) dropped, so two runs are comparable at all."""
    out = json.loads(json.dumps(outcome))
    for row in out["files"]:
        row.pop("batch_id", None)
    for entry in out["months"]:
        entry.pop("batch_id", None)
    return out


# A deliberately mixed pile: one of every ledger status, ordered so that a
# reordering bug shows (the two dated files are not adjacent).
MIXED = [
    ("notes.txt", b"plain text"),
    ("empty.jpg", b""),
    ("a.jpg", JPG + b"a"),
    ("mystery.jpg", JPG + b"m"),
    ("b.jpg", JPG + b"b"),
]
MIXED_READS = {"a.jpg": _ext(DAY_M1), "b.jpg": _ext(DAY_M2)}


def test_the_ledger_is_the_one_the_serial_loop_built(tmp_path, monkeypatch):
    """THE contract: same staging folder, same ledger (row order and every
    field) whether the reads ran one at a time or six at a time."""
    monkeypatch.setattr(intake_mail, "_DROP_READ_WORKERS", 1)
    _patch(monkeypatch, _ByName(MIXED_READS))
    serial = _anonymize(_route(tmp_path / "serial", MIXED))

    monkeypatch.setattr(intake_mail, "_DROP_READ_WORKERS", 6)
    _patch(monkeypatch, _ByName(MIXED_READS))
    parallel = _anonymize(_route(tmp_path / "parallel", MIXED))

    assert parallel == serial
    assert [r["file"] for r in parallel["files"]] == [
        "notes.txt", "empty.jpg", "a.jpg", "mystery.jpg", "b.jpg"
    ]
    assert [r["status"] for r in parallel["files"]] == [
        "rejected", "rejected", "filed", "needs_month", "filed"
    ]
    assert parallel["files"][2]["month"] == MONTH_M1
    assert parallel["files"][4]["month"] == MONTH_M2


def test_one_file_that_explodes_leaves_the_rest_filed(tmp_path, monkeypatch):
    """A read that raises is that FILE's problem: it comes back
    `needs_month` (nothing readable was learned about it) and every other
    file in the pile still files."""
    _patch(monkeypatch, _ByName(MIXED_READS, explode=("b.jpg",)))
    out = _route(tmp_path, MIXED)

    by_file = {r["file"]: r for r in out["files"]}
    assert by_file["b.jpg"]["status"] == "needs_month"
    assert by_file["b.jpg"]["reason"] == "no-readable-date"
    assert by_file["a.jpg"]["status"] == "filed"
    assert by_file["a.jpg"]["month"] == MONTH_M1
    assert out["n_filed"] == 1
    assert [m["label"] for m in out["months"]] == [LABEL_M1]


def test_a_read_that_raises_past_the_inner_catch_is_still_per_file(
    tmp_path, monkeypatch
):
    """The guard the POOL needed. `_extract_receipt_dates` has always caught
    a per-file extraction failure, but an exception that escapes it used to
    end the loop and now would ride a Future into the main thread and fail
    the whole job at `.result()`. Raised HERE, from the reader itself, only
    the worker's own guard can contain it — which is what makes that guard
    load-bearing rather than decoration."""
    real = intake_mail._extract_receipt_dates

    def _raises(files, client):
        if any(str(f).endswith("b.jpg") for f in files):
            raise RuntimeError("the reader itself exploded")
        return real(files, client)

    monkeypatch.setattr(intake_mail, "_extract_receipt_dates", _raises)
    _patch(monkeypatch, _ByName(MIXED_READS))

    out = _route(tmp_path, MIXED)

    by_file = {r["file"]: r for r in out["files"]}
    assert by_file["b.jpg"]["status"] == "needs_month"
    assert by_file["a.jpg"]["status"] == "filed"
    assert out["n_filed"] == 1


def test_a_typed_month_never_reads_a_file(tmp_path, monkeypatch):
    """`month_override` short-circuits before any extraction and never
    enters the pool. Spied at `_extract_receipt_dates`, the routing pass's
    only reader — the ingest reads through the folder reader, so this
    counts routing reads and nothing else."""
    reads: list[str] = []
    real = intake_mail._extract_receipt_dates

    def _spy(files, client):
        reads.extend(Path(f).name for f in files)
        return real(files, client)

    monkeypatch.setattr(intake_mail, "_extract_receipt_dates", _spy)
    _patch(monkeypatch, _ByName(MIXED_READS))

    out = _route(tmp_path, [("a.jpg", JPG + b"a"), ("b.jpg", JPG + b"b")],
                 month=MONTH_M1)

    assert reads == []
    assert out["n_filed"] == 2
    assert {r["month_source"] for r in out["files"]} == {"operator"}


def test_the_reads_overlap_and_stay_inside_the_bound(tmp_path, monkeypatch):
    """Concurrency asserted as concurrency rather than as a clock: with
    twelve files and a read that sleeps, more than one read is in flight at
    once and never more than `_DROP_READ_WORKERS` of them."""
    files = [(f"r{i}.jpg", JPG + bytes([i])) for i in range(12)]
    mock = _ByName({f"r{i}.jpg": _ext(DAY_M1) for i in range(12)}, latency=0.1)
    _patch(monkeypatch, mock)

    out = _route(tmp_path, files)

    assert out["n_filed"] == 12
    assert mock.peak > 1, "the reads did not overlap"
    assert mock.peak <= intake_mail._DROP_READ_WORKERS


def test_parallel_beats_the_serial_wall_clock(tmp_path, monkeypatch):
    """The point of the change, with a margin wide enough that a loaded box
    cannot flake it: twelve reads of 0.1s each cost 1.2s end to end and
    about 0.2s on six workers. The gate is 0.7s."""
    files = [(f"r{i}.jpg", JPG + bytes([i])) for i in range(12)]
    mock = _ByName(
        {f"r{i}.jpg": _ext(DAY_M1) for i in range(12)},
        latency=0.1, memoize=True,
    )
    _patch(monkeypatch, mock)

    started = time.perf_counter()
    out = _route(tmp_path, files)
    elapsed = time.perf_counter() - started

    assert out["n_filed"] == 12
    assert elapsed < 0.7, f"the drop took {elapsed:.2f}s"


def test_progress_counts_the_files_as_they_land(tmp_path, monkeypatch):
    """The page showed one frozen "reading receipts" for the whole pass.
    Every file now moves the count, through the same `on_stage` the job row
    already writes, so `GET /jobs/{id}` carries it."""
    files = [(f"r{i}.jpg", JPG + bytes([i])) for i in range(3)]
    _patch(monkeypatch, _ByName({f"r{i}.jpg": _ext(DAY_M1) for i in range(3)}))
    stages: list[str] = []

    _route(tmp_path, files, on_stage=stages.append)

    assert stages[0] == "reading receipts"
    assert stages[1:4] == [
        "reading receipts (1/3)",
        "reading receipts (2/3)",
        "reading receipts (3/3)",
    ]
    assert stages[-1].startswith("filing ")


def test_progress_throttles_a_big_pile():
    """Each report is a short-lived store connection, so a 500-file drop
    does not write 500 of them: every file while each one still reads as
    movement, then every fifth, and always the last."""
    due = [n for n in range(1, 101) if intake_mail._drop_progress_due(n, 100)]
    assert due[:20] == list(range(1, 21))
    assert due[20:] == list(range(25, 101, 5))
    assert due[-1] == 100
    small = [n for n in range(1, 4) if intake_mail._drop_progress_due(n, 3)]
    assert small == [1, 2, 3]


# ── the extraction cache between the two passes ─────────────────────────

_DRIFT_VENDORS = ["MEGA CENTER", "MEGA CENTRO", "MEGA CENTRE"]


def _fake_openai(monkeypatch, calls: list) -> None:
    """The OpenAI SDK object replaced by a fake transport (the
    test_extraction_cache pattern), so the REAL OpenAIClient, the REAL
    `_build_llm_client` wiring and the REAL ExtractionCache all run.
    `calls` collects the EXTRACTION calls only; the answer drifts per call,
    so a second read of one file would change the reading too, not only the
    count."""

    def _create(**kw):
        name = kw["response_format"]["json_schema"]["name"]
        if name == "receipt_extraction":
            calls.append(kw)
            vendor = _DRIFT_VENDORS[(len(calls) - 1) % len(_DRIFT_VENDORS)]
            content = json.dumps({
                "date": DAY_M1.isoformat(), "total": "1350.00",
                "currency": "EUR", "vendor": vendor,
                "vendor_clean": vendor.title(), "reference": "461017",
                "tax": None, "tax_label": None, "payment_hint": None,
                "card_last4": None, "document_type": "receipt",
                "line_items": [], "confidence": 0.95, "notes": "",
            })
        elif name == "vendor_classification":
            content = json.dumps({
                "category": "Office Supplies", "confidence": 0.9,
                "reasoning": "fake transport", "zoho_account": None,
            })
        else:
            content = json.dumps({"results": []})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

    class _FakeOpenAI:
        def __init__(self, **kw):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=_create)
            )

    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")


def test_a_file_pays_vision_once_across_both_passes(tmp_path, monkeypatch):
    """The routing pass runs the FULL extraction deliberately, so the
    content-addressed cache it warms answers the ingest that follows: three
    files, three transport calls, not six."""
    pytest.importorskip("openai")
    calls: list = []
    _fake_openai(monkeypatch, calls)
    monkeypatch.setenv(
        "EXPENSE_RECON_EXTRACTION_CACHE",
        str(tmp_path / "extraction-cache.sqlite"),
    )

    out = _route(tmp_path, [(f"r{i}.jpg", JPG + bytes([i])) for i in range(3)])

    assert out["n_filed"] == 3, out
    assert len(calls) == 3, f"{len(calls)} vision calls for 3 files"


def test_without_the_cache_the_same_file_is_read_twice(tmp_path, monkeypatch):
    """The differential half: the same probe counts six with the cache off.
    Without it, "three" would be a number with nothing to mean."""
    pytest.importorskip("openai")
    calls: list = []
    _fake_openai(monkeypatch, calls)
    monkeypatch.delenv("EXPENSE_RECON_EXTRACTION_CACHE", raising=False)

    out = _route(tmp_path, [(f"r{i}.jpg", JPG + bytes([i])) for i in range(3)])

    assert out["n_filed"] == 3, out
    assert len(calls) == 6, f"{len(calls)} vision calls for 3 files"
